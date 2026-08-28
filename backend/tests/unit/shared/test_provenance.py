from datetime import UTC, datetime

import pytest

from vichara_portfolio.shared.provenance import SourceRef


def test_source_ref_holds_the_required_fields() -> None:
    ref = SourceRef(
        source_name="sec_edgar",
        source_url="https://www.sec.gov/Archives/edgar/data/2110410/000188852426014162/exh_102.xml",
        retrieved_at=datetime(2026, 7, 30, 12, 0, tzinfo=UTC),
        checksum="abc123",
        record_id="0001888524-26-014162",
        field_path="assets[29].mostRecentNetOperatingIncomeAmount",
    )

    assert ref.source_name == "sec_edgar"
    assert ref.checksum == "abc123"
    assert ref.record_id == "0001888524-26-014162"
    assert ref.field_path == "assets[29].mostRecentNetOperatingIncomeAmount"


def test_checksum_field_path_and_record_id_are_optional() -> None:
    ref = SourceRef(
        source_name="treasury",
        source_url="https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/avg_interest_rates",
        retrieved_at=datetime.now(UTC),
    )

    assert ref.checksum is None
    assert ref.record_id is None
    assert ref.field_path is None


def test_naive_datetime_is_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        SourceRef(
            source_name="sec_edgar",
            source_url="https://data.sec.gov/submissions/CIK0002110410.json",
            retrieved_at=datetime(2026, 7, 30, 12, 0),  # naive - no tzinfo
        )


def test_now_factory_produces_timezone_aware_ref() -> None:
    ref = SourceRef.now(
        source_name="sec_edgar",
        source_url="https://data.sec.gov/submissions/CIK0002110410.json",
    )

    assert ref.retrieved_at.tzinfo is not None


def test_source_ref_is_immutable() -> None:
    ref = SourceRef.now(source_name="sec_edgar", source_url="https://data.sec.gov/x")

    with pytest.raises(AttributeError):
        ref.checksum = "changed"  # type: ignore[misc]
