"""API tests against fake ports (InMemoryJobQueue with a stub job body,
DeterministicProvider) - no SEC, Postgres, or Ollama needed. health/ready
is the one test that needs real Postgres, marked integration and
skip-on-unreachable like Task 9's repository tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from vichara_portfolio.bondlens.deal_cache import DEAL_CACHE, DealCacheEntry
from vichara_portfolio.bondlens.domain import (
    BondCollateralReconciliation,
    CertificateDistribution,
    Deal,
    Loan,
    ParsedMonthlyReport,
    PropertyAtSecuritization,
    PropertySnapshot,
    ReportingPeriod,
)
from vichara_portfolio.bondlens.monthly_report_ingest import IngestedMonthlyReport
from vichara_portfolio.main import create_app
from vichara_portfolio.model_gateway.deterministic import DeterministicProvider
from vichara_portfolio.model_gateway.ports import GenerateResult, ModelInfo
from vichara_portfolio.settings import Settings
from vichara_portfolio.shared.jobs import InMemoryJobQueue
from vichara_portfolio.shared.provenance import SourceRef


def _settings() -> Settings:
    # Keep the skip-on-unreachable probe bounded when the optional local
    # Postgres service is not running (the default psycopg timeout can be
    # several minutes on Windows).
    return Settings(
        _env_file=None,
        sec_user_agent="test/0.1 (t@example.com)",
        jwt_secret="x",
        database_url=(
            "postgresql+psycopg://vichara:vichara@localhost:5433/vichara"
            "?connect_timeout=2"
        ),
    )


def _source(label: str) -> SourceRef:
    return SourceRef(
        source_name="sec_edgar",
        source_url=f"https://www.sec.gov/x/{label}.xml",
        retrieved_at=datetime(2026, 8, 28, 12, 0, tzinfo=UTC),
    )


def _property(name: str, *, state: str | None, type_code: str | None) -> PropertySnapshot:
    return PropertySnapshot(
        property_name=name,
        property_address=None,
        property_city=None,
        property_state=state,
        property_zip=None,
        property_county=None,
        property_type_code=type_code,
        year_built=None,
        net_rentable_square_feet=None,
        at_securitization=PropertyAtSecuritization(
            valuation_amount=None,
            valuation_date=None,
            physical_occupancy_percentage=None,
            net_rentable_square_feet=None,
            revenue_amount=None,
            operating_expenses_amount=None,
            net_operating_income_amount=None,
            net_cash_flow_amount=None,
        ),
        most_recent=None,
        raw_fields={},
    )


def _loan(
    asset_number: str,
    *,
    status: str,
    ending_date: date,
    properties: tuple[PropertySnapshot, ...] = (),
) -> Loan:
    return Loan(
        asset_number=asset_number,
        group_id=None,
        originator_name=None,
        origination_date=None,
        original_loan_amount=Decimal("1000000.00"),
        original_interest_rate_percentage=None,
        maturity_date=None,
        reporting_period=ReportingPeriod(beginning_date=None, ending_date=ending_date),
        paid_through_date=None,
        scheduled_principal_amount=None,
        scheduled_interest_amount=None,
        actual_balance_amount=Decimal("900000.00"),
        scheduled_balance_amount=Decimal("900000.00"),
        payment_status_code=status,
        properties=properties,
        raw_fields={},
        source=_source("fixture"),
    )


def _monthly_report() -> IngestedMonthlyReport:
    source = _source("exhibit-99-1")
    return IngestedMonthlyReport(
        accession_number="0002110410-26-000001",
        report_date=date(2026, 8, 17),
        source=source,
        report=ParsedMonthlyReport(
            certificate_distributions=(
                CertificateDistribution(
                    class_name="A-1",
                    cusip="08164FAA9",
                    pass_through_rate=Decimal("0.04216170"),
                    original_balance=Decimal("8602000.00"),
                    beginning_balance=Decimal("7890836.42"),
                    principal_distribution=Decimal("166693.42"),
                    interest_distribution=Decimal("27724.26"),
                    prepayment_penalties=Decimal("0"),
                    realized_losses=Decimal("0"),
                    total_distribution=Decimal("194417.68"),
                    ending_balance=Decimal("7724143.00"),
                    current_credit_support=Decimal("0.3004"),
                    original_credit_support=Decimal("0.30"),
                    source=source,
                ),
            ),
            reconciliation=BondCollateralReconciliation(
                beginning_scheduled_collateral_balance=Decimal("728470250.36"),
                scheduled_principal_collections=Decimal("171451.19"),
                ending_scheduled_collateral_balance=Decimal("728298799.17"),
                beginning_actual_collateral_balance=Decimal("728470250.36"),
                ending_actual_collateral_balance=Decimal("728298800.10"),
                beginning_certificate_balance=Decimal("728470250.36"),
                principal_distributions=Decimal("171451.19"),
                ending_certificate_balance=Decimal("728298799.17"),
                under_over_collateralization=Decimal("-0.93"),
                source=source,
            ),
            issues=(),
        ),
    )


@pytest.fixture(autouse=True)
def _clear_deal_cache():
    DEAL_CACHE.clear()
    yield
    DEAL_CACHE.clear()


@dataclass
class _NeverHealthyProvider:
    """Reports unavailable - exercises the chat-only 503 path."""

    calls: list[str] = field(default_factory=list)

    def health(self) -> bool:
        return False

    def model_info(self) -> ModelInfo:
        return ModelInfo(provider_name="unavailable", model_name="none")

    def generate(self, prompt: str, *, temperature: float = 0.0, timeout_seconds: float = 60.0):
        raise AssertionError("must not be called when health() is False")

    def structured_generate(self, *args, **kwargs):
        raise AssertionError("must not be called when health() is False")


def _client(*, job_queue=None, model_provider=None) -> TestClient:
    app = create_app(
        settings=_settings(),
        job_queue=job_queue or InMemoryJobQueue(run=lambda cik: {"created_count": 1}),
        model_provider=model_provider or DeterministicProvider(),
    )
    return TestClient(app)


# --------------------------------------------------------------------------
# Health
# --------------------------------------------------------------------------


def test_health_live_is_always_200() -> None:
    client = _client()
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "live"}


def test_cors_allows_the_local_vite_dev_origin() -> None:
    """Regression test for a real bug (2026-08-29, live browser
    verification): the browser blocked every frontend request with
    'No Access-Control-Allow-Origin header' because create_app() had no
    CORS middleware at all."""
    client = _client()
    response = client.options(
        "/api/bondlens/deals",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


@pytest.mark.integration
def test_health_ready_against_real_postgres() -> None:
    settings = _settings()
    try:
        from vichara_portfolio.shared.db import make_engine

        with make_engine(settings.database_url).connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - environment guard
        pytest.skip(f"Postgres not reachable: {exc}")

    client = _client()
    response = client.get("/health/ready")
    assert response.status_code == 200


# --------------------------------------------------------------------------
# Ingestion - fake ports
# --------------------------------------------------------------------------


def test_create_ingestion_returns_202_and_a_job_id() -> None:
    client = _client()
    response = client.post("/api/bondlens/ingestions", json={"cik": "0002110410"})
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "completed"
    assert body["result"] == {"created_count": 1}


def test_get_unknown_job_returns_404() -> None:
    client = _client()
    response = client.get("/api/bondlens/ingestions/does-not-exist")
    assert response.status_code == 404


def test_ingestion_failure_is_reported_as_a_structured_error() -> None:
    def failing_run(cik: str) -> object:
        raise ValueError("simulated SEC failure")

    client = _client(job_queue=InMemoryJobQueue(run=failing_run))
    response = client.post("/api/bondlens/ingestions", json={"cik": "0002110410"})
    body = response.json()
    assert body["status"] == "failed"
    assert body["error"]["category"] == "ValueError"
    assert "simulated SEC failure" in body["error"]["message"]


def test_second_request_reuses_a_still_active_job_with_the_same_idempotency_key() -> None:
    """InMemoryJobQueue runs synchronously, so a real request/response pair
    can never observe an in-flight job - exercise the reuse branch directly
    by pre-seeding a queued job, the way a concurrent second request would
    find it against the real RQJobQueue."""
    from vichara_portfolio.shared.jobs import JobStatus, _new_job

    queue = InMemoryJobQueue(run=lambda cik: {"created_count": 1})
    seeded = _new_job("same-key")
    seeded.status = JobStatus.RUNNING
    queue.jobs[seeded.job_id] = seeded
    queue._by_idempotency_key["same-key"] = seeded.job_id

    client = _client(job_queue=queue)
    response = client.post(
        "/api/bondlens/ingestions", json={"cik": "0002110410", "idempotency_key": "same-key"}
    )

    assert response.json()["job_id"] == seeded.job_id
    assert response.json()["status"] == "running"


# --------------------------------------------------------------------------
# Deals - fake ports, DEAL_CACHE populated directly
# --------------------------------------------------------------------------


def test_deals_list_is_empty_before_any_ingestion() -> None:
    client = _client()
    response = client.get("/api/bondlens/deals")
    assert response.status_code == 200
    assert response.json() == []


def test_deal_summary_for_unknown_deal_is_404() -> None:
    client = _client()
    response = client.get("/api/bondlens/deals/9999999999/summary")
    assert response.status_code == 404


def test_deal_summary_returns_computed_totals() -> None:
    loans = (_loan("1", status="0", ending_date=date(2026, 7, 13)),)
    DEAL_CACHE["0002110410"] = DealCacheEntry(
        deal=Deal(cik="0002110410", name="Benchmark 2026-B42 Mortgage Trust"),
        loans_a=(),
        loans_b=loans,
        filing_source=_source("july"),
    )

    client = _client()
    response = client.get("/api/bondlens/deals/0002110410/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["loan_count"] == 1
    assert body["total_actual_balance_amount"] == "900000.00"


def test_certificate_distribution_returns_typed_exhibit_99_1_data() -> None:
    DEAL_CACHE["0002110410"] = DealCacheEntry(
        deal=Deal(cik="0002110410", name="Benchmark 2026-B42 Mortgage Trust"),
        loans_a=(),
        loans_b=(),
        filing_source=None,
        latest_monthly_report=_monthly_report(),
    )

    response = _client().get("/api/bondlens/deals/0002110410/certificate-distributions")

    assert response.status_code == 200
    body = response.json()
    assert body["report_date"] == "2026-08-17"
    assert body["entries"] == [
        {
            "class_name": "A-1",
            "cusip": "08164FAA9",
            "pass_through_rate": "0.04216170",
            "beginning_balance": "7890836.42",
            "principal_distribution": "166693.42",
            "interest_distribution": "27724.26",
            "ending_balance": "7724143.00",
            "source_url": "https://www.sec.gov/x/exhibit-99-1.xml",
        }
    ]


def test_bond_collateral_reconciliation_returns_nonzero_difference() -> None:
    DEAL_CACHE["0002110410"] = DealCacheEntry(
        deal=Deal(cik="0002110410", name="Benchmark 2026-B42 Mortgage Trust"),
        loans_a=(),
        loans_b=(),
        filing_source=None,
        latest_monthly_report=_monthly_report(),
    )

    response = _client().get("/api/bondlens/deals/0002110410/bond-collateral-reconciliation")

    assert response.status_code == 200
    body = response.json()
    assert body["ending_scheduled_collateral_balance"] == "728298799.17"
    assert body["ending_actual_collateral_balance"] == "728298800.10"
    assert body["ending_certificate_balance"] == "728298799.17"
    assert body["under_over_collateralization"] == "-0.93"


def test_deal_compare_with_only_one_period_returns_422() -> None:
    DEAL_CACHE["0002110410"] = DealCacheEntry(
        deal=Deal(cik="0002110410", name="Benchmark 2026-B42 Mortgage Trust"),
        loans_a=(),
        loans_b=(_loan("1", status="0", ending_date=date(2026, 7, 13)),),
        filing_source=_source("july"),
    )

    client = _client()
    response = client.get("/api/bondlens/deals/0002110410/compare")

    assert response.status_code == 422


def test_deal_compare_with_two_periods_returns_changes() -> None:
    DEAL_CACHE["0002110410"] = DealCacheEntry(
        deal=Deal(cik="0002110410", name="Benchmark 2026-B42 Mortgage Trust"),
        loans_a=(_loan("30", status="0", ending_date=date(2026, 5, 11)),),
        loans_b=(_loan("30", status="B", ending_date=date(2026, 7, 13)),),
        filing_source=_source("july"),
    )

    client = _client()
    response = client.get("/api/bondlens/deals/0002110410/compare")

    assert response.status_code == 200
    changes = response.json()["changes"]
    assert any(c["field_name"] == "paymentStatusLoanCode" for c in changes)


# --------------------------------------------------------------------------
# Geography and property-type distribution
# --------------------------------------------------------------------------


def test_geography_for_unknown_deal_is_404() -> None:
    client = _client()
    response = client.get("/api/bondlens/deals/nope/geography")
    assert response.status_code == 404


def test_geography_returns_state_counts() -> None:
    loans = (
        _loan(
            "1",
            status="0",
            ending_date=date(2026, 7, 13),
            properties=(
                _property("A", state="NY", type_code="MF"),
                _property("B", state="NY", type_code="OF"),
                _property("C", state="CA", type_code=None),
            ),
        ),
    )
    DEAL_CACHE["0002110410"] = DealCacheEntry(
        deal=Deal(cik="0002110410", name="Benchmark 2026-B42 Mortgage Trust"),
        loans_a=(),
        loans_b=loans,
        filing_source=_source("july"),
    )

    client = _client()
    response = client.get("/api/bondlens/deals/0002110410/geography")

    assert response.status_code == 200
    body = response.json()
    assert body["total_properties"] == 3
    assert body["properties_missing_state"] == 0
    assert {e["state"]: e["property_count"] for e in body["entries"]} == {"NY": 2, "CA": 1}


def test_property_types_returns_code_counts() -> None:
    loans = (
        _loan(
            "1",
            status="0",
            ending_date=date(2026, 7, 13),
            properties=(
                _property("A", state="NY", type_code="MF"),
                _property("B", state="NY", type_code="OF"),
                _property("C", state="CA", type_code=None),
            ),
        ),
    )
    DEAL_CACHE["0002110410"] = DealCacheEntry(
        deal=Deal(cik="0002110410", name="Benchmark 2026-B42 Mortgage Trust"),
        loans_a=(),
        loans_b=loans,
        filing_source=_source("july"),
    )

    client = _client()
    response = client.get("/api/bondlens/deals/0002110410/property-types")

    assert response.status_code == 200
    body = response.json()
    assert body["total_properties"] == 3
    assert body["properties_missing_type"] == 1
    assert {e["property_type_code"]: e["property_count"] for e in body["entries"]} == {
        "MF": 1,
        "OF": 1,
    }


# --------------------------------------------------------------------------
# Status-change and balance-drift rankings
# --------------------------------------------------------------------------


def test_status_changes_with_only_one_period_returns_422() -> None:
    DEAL_CACHE["0002110410"] = DealCacheEntry(
        deal=Deal(cik="0002110410", name="Benchmark 2026-B42 Mortgage Trust"),
        loans_a=(),
        loans_b=(_loan("1", status="0", ending_date=date(2026, 7, 13)),),
        filing_source=_source("july"),
    )

    client = _client()
    response = client.get("/api/bondlens/deals/0002110410/status-changes")

    assert response.status_code == 422


def test_status_changes_returns_ranked_entries() -> None:
    DEAL_CACHE["0002110410"] = DealCacheEntry(
        deal=Deal(cik="0002110410", name="Benchmark 2026-B42 Mortgage Trust"),
        loans_a=(_loan("30", status="0", ending_date=date(2026, 5, 11)),),
        loans_b=(_loan("30", status="B", ending_date=date(2026, 7, 13)),),
        filing_source=_source("july"),
    )

    client = _client()
    response = client.get("/api/bondlens/deals/0002110410/status-changes")

    assert response.status_code == 200
    entries = response.json()["entries"]
    assert entries[0]["loan_asset_number"] == "30"
    assert entries[0]["status_before"] == "0"
    assert entries[0]["status_after"] == "B"


def test_balance_drift_for_unknown_deal_is_404() -> None:
    client = _client()
    response = client.get("/api/bondlens/deals/nope/balance-drift")
    assert response.status_code == 404


def test_balance_drift_returns_ranked_entries() -> None:
    DEAL_CACHE["0002110410"] = DealCacheEntry(
        deal=Deal(cik="0002110410", name="Benchmark 2026-B42 Mortgage Trust"),
        loans_a=(),
        loans_b=(_loan("1", status="0", ending_date=date(2026, 7, 13)),),
        filing_source=_source("july"),
    )

    client = _client()
    response = client.get("/api/bondlens/deals/0002110410/balance-drift")

    assert response.status_code == 200
    entries = response.json()["entries"]
    assert entries[0]["loan_asset_number"] == "1"
    assert entries[0]["actual_balance_amount"] == "900000.00"


# --------------------------------------------------------------------------
# Chat - the only endpoint touching the model provider
# --------------------------------------------------------------------------


def test_chat_returns_503_when_model_is_unavailable() -> None:
    DEAL_CACHE["0002110410"] = DealCacheEntry(
        deal=Deal(cik="0002110410", name="Benchmark 2026-B42 Mortgage Trust"),
        loans_a=(),
        loans_b=(_loan("30", status="0", ending_date=date(2026, 7, 13)),),
        filing_source=_source("july"),
    )
    client = _client(model_provider=_NeverHealthyProvider())

    response = client.post(
        "/api/bondlens/chat", json={"deal_id": "0002110410", "question": "How many loans?"}
    )

    assert response.status_code == 503


def test_deal_summary_never_touches_the_model_provider() -> None:
    """The deterministic endpoints must work even if the model is down -
    only /chat is allowed to depend on it."""
    DEAL_CACHE["0002110410"] = DealCacheEntry(
        deal=Deal(cik="0002110410", name="Benchmark 2026-B42 Mortgage Trust"),
        loans_a=(),
        loans_b=(_loan("30", status="0", ending_date=date(2026, 7, 13)),),
        filing_source=_source("july"),
    )
    client = _client(model_provider=_NeverHealthyProvider())

    response = client.get("/api/bondlens/deals/0002110410/summary")

    assert response.status_code == 200


def test_chat_for_unknown_deal_is_404() -> None:
    client = _client()
    response = client.post(
        "/api/bondlens/chat", json={"deal_id": "does-not-exist", "question": "x"}
    )
    assert response.status_code == 404


def test_chat_returns_answer_and_citations() -> None:
    loans_a = (_loan("30", status="0", ending_date=date(2026, 5, 11)),)
    loans_b = (_loan("30", status="B", ending_date=date(2026, 7, 13)),)
    DEAL_CACHE["0002110410"] = DealCacheEntry(
        deal=Deal(cik="0002110410", name="Benchmark 2026-B42 Mortgage Trust"),
        loans_a=loans_a,
        loans_b=loans_b,
        filing_source=_source("july"),
    )

    class QueuedProvider:
        def health(self) -> bool:
            return True

        def model_info(self) -> ModelInfo:
            return ModelInfo(provider_name="fake", model_name="fake")

        def generate(self, prompt, *, temperature=0.0, timeout_seconds=60.0):
            return GenerateResult(
                text="Loan 30 moved from status 0 to B.",
                model=self.model_info(),
                latency_seconds=0.0,
            )

        def structured_generate(self, *args, **kwargs):
            raise NotImplementedError

    client = _client(model_provider=QueuedProvider())
    response = client.post(
        "/api/bondlens/chat",
        json={"deal_id": "0002110410", "question": "Which loans changed payment status?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "30" in body["answer"]
    assert body["citations"]
    assert body["verification_passed"] is True
