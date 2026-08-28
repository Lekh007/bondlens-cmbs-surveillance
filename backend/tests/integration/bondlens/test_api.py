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
from vichara_portfolio.bondlens.domain import Deal, Loan, ReportingPeriod
from vichara_portfolio.main import create_app
from vichara_portfolio.model_gateway.deterministic import DeterministicProvider
from vichara_portfolio.model_gateway.ports import GenerateResult, ModelInfo
from vichara_portfolio.settings import Settings
from vichara_portfolio.shared.jobs import InMemoryJobQueue
from vichara_portfolio.shared.provenance import SourceRef


def _settings() -> Settings:
    return Settings(_env_file=None, sec_user_agent="test/0.1 (t@example.com)", jwt_secret="x")


def _source(label: str) -> SourceRef:
    return SourceRef(
        source_name="sec_edgar",
        source_url=f"https://www.sec.gov/x/{label}.xml",
        retrieved_at=datetime(2026, 8, 28, 12, 0, tzinfo=UTC),
    )


def _loan(asset_number: str, *, status: str, ending_date: date) -> Loan:
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
        properties=(),
        raw_fields={},
        source=_source("fixture"),
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
