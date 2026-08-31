"""Integration tests against a real Postgres instance (docker compose up -d
postgres). Each test runs in its own transaction that is rolled back at the
end, so tests never see each other's data and the database stays clean.
"""

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import text

from vichara_portfolio.bondlens.adapters.repository import (
    AssetRow,
    BondLensRepository,
    PropertySnapshotRow,
    SourceDocumentRow,
)
from vichara_portfolio.bondlens.domain import (
    Deal,
    Loan,
    ParsedAssetData,
    PropertyAtSecuritization,
    PropertyMostRecent,
    PropertySnapshot,
    ReportingPeriod,
    SecFiling,
)
from vichara_portfolio.settings import Settings
from vichara_portfolio.shared.db import make_engine, make_session_factory
from vichara_portfolio.shared.provenance import SourceRef

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def engine():
    # Keep the optional-service probe bounded when Postgres is not running.
    settings = Settings(
        _env_file=None,
        sec_user_agent="test/0.1 (t@example.com)",
        jwt_secret="x",
        database_url=(
            "postgresql+psycopg://vichara:vichara@localhost:5433/vichara"
            "?connect_timeout=2"
        ),
    )
    eng = make_engine(settings.database_url)
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - environment guard
        pytest.skip(f"Postgres not reachable at {settings.database_url}: {exc}")
    yield eng
    eng.dispose()


@pytest.fixture
def session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    session_factory = make_session_factory(engine)
    sess = session_factory(bind=connection)
    yield sess
    sess.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def repo(session) -> BondLensRepository:
    return BondLensRepository(session)


def _source(*, checksum: str | None = "abc123", record_id: str | None = "rec-1") -> SourceRef:
    return SourceRef(
        source_name="sec_edgar",
        source_url="https://www.sec.gov/Archives/edgar/data/2110410/x/exh_102.xml",
        retrieved_at=datetime(2026, 8, 28, 12, 0, tzinfo=UTC),
        checksum=checksum,
        record_id=record_id,
    )


def _loan(*, asset_number: str = "16", source: SourceRef | None = None) -> Loan:
    return Loan(
        asset_number=asset_number,
        group_id="1",
        originator_name="German American Capital Corporation",
        origination_date=date(2026, 2, 10),
        original_loan_amount=Decimal("45000000.00"),
        original_interest_rate_percentage=Decimal(".05875000"),
        maturity_date=None,
        reporting_period=ReportingPeriod(
            beginning_date=date(2026, 6, 1), ending_date=date(2026, 6, 30)
        ),
        paid_through_date=date(2026, 7, 1),
        scheduled_principal_amount=Decimal("12345.67"),
        scheduled_interest_amount=Decimal("219791.67"),
        actual_balance_amount=Decimal("44832100.55"),
        scheduled_balance_amount=Decimal("44832100.55"),
        payment_status_code="B",
        properties=(
            PropertySnapshot(
                property_name="PWC Pennant",
                property_address="1 Pennant Way",
                property_city="St. Louis",
                property_state="MO",
                property_zip="63101",
                property_county="St. Louis City",
                property_type_code="OF",
                year_built=1998,
                net_rentable_square_feet=Decimal("412000"),
                at_securitization=PropertyAtSecuritization(
                    valuation_amount=Decimal("68000000.00"),
                    valuation_date=date(2026, 1, 15),
                    physical_occupancy_percentage=Decimal(".91200000"),
                    net_rentable_square_feet=None,
                    revenue_amount=Decimal("9800000.00"),
                    operating_expenses_amount=Decimal("4100000.00"),
                    net_operating_income_amount=Decimal("5700000.00"),
                    net_cash_flow_amount=Decimal("5450000.00"),
                ),
                most_recent=None,
                raw_fields={"assetTypeNumber": "1"},
            ),
        ),
        raw_fields={"assetAddedIndicator": "0"},
        source=source or _source(),
    )


def test_upsert_source_document_returns_an_id(repo: BondLensRepository, session) -> None:
    doc_id = repo.upsert_source_document(_source())
    session.flush()
    row = session.get(SourceDocumentRow, doc_id)
    assert row is not None
    assert row.checksum == "abc123"


def test_duplicate_checksum_returns_the_same_row_not_a_new_one(
    repo: BondLensRepository, session
) -> None:
    first_id = repo.upsert_source_document(_source(checksum="dupe-checksum"))
    second_id = repo.upsert_source_document(
        _source(checksum="dupe-checksum", record_id="different-record")
    )

    assert first_id == second_id


def test_null_checksum_never_dedupes(repo: BondLensRepository, session) -> None:
    first_id = repo.upsert_source_document(_source(checksum=None))
    second_id = repo.upsert_source_document(_source(checksum=None))

    assert first_id != second_id


def test_upsert_deal_and_filing(repo: BondLensRepository, session) -> None:
    deal = Deal(cik="0002110410", name="Benchmark 2026-B42 Mortgage Trust")
    filing = SecFiling(
        cik="0002110410",
        accession_number="0001888524-26-014162",
        form_type="ABS-EE",
        filing_date=date(2026, 7, 30),
        report_date=date(2026, 7, 17),
        primary_document="bmk26b42_absee-202607.htm",
    )

    repo.upsert_deal(deal)
    repo.upsert_filing(filing)
    session.flush()

    counts = repo.count_rows()
    assert counts["cmbs_deals"] == 1
    assert counts["cmbs_filings"] == 1


def test_save_parsed_asset_data_writes_loan_and_property(repo: BondLensRepository, session) -> None:
    deal = Deal(cik="0002110410", name="Benchmark 2026-B42 Mortgage Trust")
    filing = SecFiling(
        cik="0002110410",
        accession_number="0001888524-26-014162",
        form_type="ABS-EE",
        filing_date=date(2026, 7, 30),
        report_date=date(2026, 7, 17),
        primary_document="bmk26b42_absee-202607.htm",
    )
    repo.upsert_deal(deal)
    repo.upsert_filing(filing)
    source_id = repo.upsert_source_document(_source())
    parsed = ParsedAssetData(loans=(_loan(),), issues=())

    loans_written, properties_written = repo.save_parsed_asset_data(
        accession_number=filing.accession_number, parsed=parsed, source_document_id=source_id
    )
    session.flush()

    assert loans_written == 1
    assert properties_written == 1
    counts = repo.count_rows()
    assert counts["cmbs_assets"] == 1
    assert counts["cmbs_property_snapshots"] == 1
    assert counts["cmbs_reporting_periods"] == 1

    asset = session.query(AssetRow).one()
    assert asset.original_loan_amount == Decimal("45000000.00")
    assert asset.source_document_id == source_id

    prop = session.query(PropertySnapshotRow).one()
    assert prop.at_securitization["valuation_amount"] == "68000000.00"
    assert prop.most_recent is None


def test_reingesting_the_same_filing_does_not_change_row_counts(
    repo: BondLensRepository, session
) -> None:
    deal = Deal(cik="0002110410", name="Benchmark 2026-B42 Mortgage Trust")
    filing = SecFiling(
        cik="0002110410",
        accession_number="0001888524-26-014162",
        form_type="ABS-EE",
        filing_date=date(2026, 7, 30),
        report_date=date(2026, 7, 17),
        primary_document="bmk26b42_absee-202607.htm",
    )
    repo.upsert_deal(deal)
    repo.upsert_filing(filing)
    source_id = repo.upsert_source_document(_source())
    parsed = ParsedAssetData(loans=(_loan(),), issues=())

    repo.save_parsed_asset_data(
        accession_number=filing.accession_number, parsed=parsed, source_document_id=source_id
    )
    session.flush()
    counts_after_first = repo.count_rows()

    # Re-run the exact same ingest.
    repo.upsert_deal(deal)
    repo.upsert_filing(filing)
    repo.save_parsed_asset_data(
        accession_number=filing.accession_number, parsed=parsed, source_document_id=source_id
    )
    session.flush()
    counts_after_second = repo.count_rows()

    assert counts_after_first == counts_after_second


def test_reingesting_with_changed_values_updates_in_place(
    repo: BondLensRepository, session
) -> None:
    deal = Deal(cik="0002110410", name="Benchmark 2026-B42 Mortgage Trust")
    filing = SecFiling(
        cik="0002110410",
        accession_number="0001888524-26-014162",
        form_type="ABS-EE",
        filing_date=date(2026, 7, 30),
        report_date=date(2026, 7, 17),
        primary_document="bmk26b42_absee-202607.htm",
    )
    repo.upsert_deal(deal)
    repo.upsert_filing(filing)
    source_id = repo.upsert_source_document(_source())

    repo.save_parsed_asset_data(
        accession_number=filing.accession_number,
        parsed=ParsedAssetData(loans=(_loan(),), issues=()),
        source_document_id=source_id,
    )
    session.flush()

    changed_loan = replace(_loan(), payment_status_code="0")
    repo.save_parsed_asset_data(
        accession_number=filing.accession_number,
        parsed=ParsedAssetData(loans=(changed_loan,), issues=()),
        source_document_id=source_id,
    )
    session.flush()

    counts = repo.count_rows()
    assert counts["cmbs_assets"] == 1  # still one row, not two

    asset = session.query(AssetRow).one()
    assert asset.payment_status_code == "0"


def test_multiple_properties_on_one_loan_are_all_saved(repo: BondLensRepository, session) -> None:
    deal = Deal(cik="0002110410", name="Benchmark 2026-B42 Mortgage Trust")
    filing = SecFiling(
        cik="0002110410",
        accession_number="0001888524-26-014162",
        form_type="ABS-EE",
        filing_date=date(2026, 7, 30),
        report_date=date(2026, 7, 17),
        primary_document="bmk26b42_absee-202607.htm",
    )
    repo.upsert_deal(deal)
    repo.upsert_filing(filing)
    source_id = repo.upsert_source_document(_source())

    base = _loan()
    second_property = PropertySnapshot(
        property_name="UOVO Evergreen",
        property_address="200 Evergreen Ave",
        property_city="Brooklyn",
        property_state="NY",
        property_zip="11221",
        property_county="Kings",
        property_type_code="SS",
        year_built=2019,
        net_rentable_square_feet=Decimal("185000"),
        at_securitization=base.properties[0].at_securitization,
        most_recent=PropertyMostRecent(
            financials_start_date=date(2026, 1, 1),
            financials_end_date=date(2026, 3, 31),
            revenue_amount=Decimal("1950000.00"),
            operating_expenses_amount=Decimal("820000.00"),
            net_operating_income_amount=Decimal("2591100.27"),
            net_cash_flow_amount=Decimal("2510000.00"),
            debt_service_amount=Decimal("1522000.00"),
            physical_occupancy_percentage=Decimal(".90480000"),
            debt_service_coverage_noi_percentage=Decimal("1.70240000"),
            debt_service_coverage_ncf_percentage=Decimal("1.64850000"),
        ),
        raw_fields={},
    )
    two_property_loan = replace(base, properties=(base.properties[0], second_property))

    _loans_written, properties_written = repo.save_parsed_asset_data(
        accession_number=filing.accession_number,
        parsed=ParsedAssetData(loans=(two_property_loan,), issues=()),
        source_document_id=source_id,
    )
    session.flush()

    assert properties_written == 2
    counts = repo.count_rows()
    assert counts["cmbs_property_snapshots"] == 2

    saved = session.query(PropertySnapshotRow).order_by(PropertySnapshotRow.property_index).all()
    assert saved[0].property_name == "PWC Pennant"
    assert saved[1].property_name == "UOVO Evergreen"
    assert saved[1].most_recent["net_operating_income_amount"] == "2591100.27"


def test_data_quality_issues_are_persisted(repo: BondLensRepository, session) -> None:
    from vichara_portfolio.bondlens.adapters.repository import DataQualityIssueRow
    from vichara_portfolio.bondlens.domain import DataQualityIssue

    deal = Deal(cik="0002110410", name="Benchmark 2026-B42 Mortgage Trust")
    filing = SecFiling(
        cik="0002110410",
        accession_number="0001888524-26-014162",
        form_type="ABS-EE",
        filing_date=date(2026, 7, 30),
        report_date=date(2026, 7, 17),
        primary_document="bmk26b42_absee-202607.htm",
    )
    repo.upsert_deal(deal)
    repo.upsert_filing(filing)
    source_id = repo.upsert_source_document(_source())

    issue = DataQualityIssue(
        asset_number="16", field_name="maturityDate", message="could not parse", raw_value="garbage"
    )
    repo.save_parsed_asset_data(
        accession_number=filing.accession_number,
        parsed=ParsedAssetData(loans=(_loan(),), issues=(issue,)),
        source_document_id=source_id,
    )
    session.flush()

    saved_issue = session.query(DataQualityIssueRow).one()
    assert saved_issue.field_name == "maturityDate"
    assert saved_issue.raw_value == "garbage"


def test_transaction_rollback_leaves_no_trace(engine) -> None:
    """Proves the fixture's rollback-per-test isolation actually works:
    a prior test's data must not be visible here."""
    session_factory = make_session_factory(engine)
    with session_factory() as verify_session:
        count = verify_session.execute(text("SELECT count(*) FROM cmbs_deals")).scalar_one()
        assert count == 0, "a previous test's transaction leaked past its rollback"
