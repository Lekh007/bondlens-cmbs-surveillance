from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from vichara_portfolio.bondlens.adapters.abs_ee import parse_asset_data
from vichara_portfolio.shared.http import ResilientHttpClient
from vichara_portfolio.shared.provenance import SourceRef

FIXTURE = (
    Path(__file__).resolve().parents[2] / "fixtures" / "sec" / "abs_ee_two_assets.xml"
).read_bytes()


@pytest.fixture
def source() -> SourceRef:
    return SourceRef(
        source_name="sec_edgar",
        source_url="https://www.sec.gov/Archives/edgar/data/2110410/x/exh_102.xml",
        retrieved_at=datetime(2026, 8, 28, 12, 0, tzinfo=UTC),
        checksum="deadbeef",
        record_id="0001888524-26-012270",
    )


def test_parses_exactly_two_loans(source: SourceRef) -> None:
    result = parse_asset_data(FIXTURE, source=source)
    assert len(result.loans) == 2


def test_asset_number_and_group_id_captured(source: SourceRef) -> None:
    result = parse_asset_data(FIXTURE, source=source)
    loan = result.loans[0]
    assert loan.asset_number == "16"
    assert loan.group_id == "1"


def test_decimal_fields_parse_as_decimal_not_float(source: SourceRef) -> None:
    result = parse_asset_data(FIXTURE, source=source)
    loan = result.loans[0]
    assert loan.original_loan_amount == Decimal("45000000.00")
    assert isinstance(loan.original_loan_amount, Decimal)


def test_percentage_fields_keep_the_fractional_source_scale(source: SourceRef) -> None:
    """SEC stores rates/occupancy as fractions (0-1), e.g. .05875000 = 5.875%.
    The parser must not rescale to 0-100 - analytics code depends on the raw
    fractional value for arithmetic (rate * principal = interest)."""
    result = parse_asset_data(FIXTURE, source=source)
    loan = result.loans[0]
    assert loan.original_interest_rate_percentage == Decimal(".05875000")

    occupancy = loan.properties[0].at_securitization.physical_occupancy_percentage
    assert occupancy == Decimal(".91200000")
    assert occupancy < 1  # not 91.2


def test_date_fields_parse_as_date_objects(source: SourceRef) -> None:
    result = parse_asset_data(FIXTURE, source=source)
    loan = result.loans[0]
    assert loan.origination_date == date(2026, 2, 10)
    assert loan.reporting_period.beginning_date == date(2026, 6, 1)
    assert loan.reporting_period.ending_date == date(2026, 6, 30)


def test_mm_dd_yyyy_dates_are_parsed_this_is_the_real_filing_format(source: SourceRef) -> None:
    """Discovered running the live test against the real July filing
    (2026-08-28): the actual ABS-EE asset XML uses MM-DD-YYYY
    ("07-13-2026"), not ISO. The unrelated submissions JSON API (Task 6)
    does use ISO - regression-test both formats so this can't silently
    regress if the fixture ever gets rewritten to look more like the docs
    than the real data."""
    xml_with_real_format_date = FIXTURE.replace(
        b"<ns:originationDate>2026-02-10</ns:originationDate>",
        b"<ns:originationDate>02-10-2026</ns:originationDate>",
    )
    result = parse_asset_data(xml_with_real_format_date, source=source)
    loan = result.loans[0]
    assert loan.origination_date == date(2026, 2, 10)
    assert result.issues == ()


def test_namespace_independence_prefixed_elements_still_parse(source: SourceRef) -> None:
    """The fixture uses a prefixed namespace (ns:assets, ns:assetNumber, ...)
    rather than the real filing's default namespace. If the parser hardcoded
    prefix or exact tag strings instead of matching by local name, this
    fixture alone would parse to zero loans."""
    result = parse_asset_data(FIXTURE, source=source)
    assert len(result.loans) == 2
    assert all(loan.asset_number for loan in result.loans)


def test_raw_fields_preserves_unmapped_source_data(source: SourceRef) -> None:
    result = parse_asset_data(FIXTURE, source=source)
    loan = result.loans[0]
    # assetAddedIndicator and assetTypeNumber are not modeled as typed Loan
    # fields but must survive in raw_fields for forensic/debug purposes.
    assert loan.raw_fields["assetAddedIndicator"] == "0"
    assert loan.raw_fields["assetTypeNumber"] == "1"


def test_missing_optional_field_is_none_not_empty_string(source: SourceRef) -> None:
    """Asset 16's fixture deliberately omits <maturityDate> entirely, matching
    how real filings omit optional elements rather than emitting them empty."""
    result = parse_asset_data(FIXTURE, source=source)
    loan_16 = next(loan for loan in result.loans if loan.asset_number == "16")
    assert loan_16.maturity_date is None

    loan_29 = next(loan for loan in result.loans if loan.asset_number == "29")
    assert loan_29.maturity_date == date(2036, 3, 1)


def test_property_with_no_most_recent_fields_is_none_not_empty_object(source: SourceRef) -> None:
    """PWC Pennant (loan 16) has never had a servicer mostRecent* update in
    the fixture - most_recent must be None, distinguishing 'never reported'
    from 'reported as zero'."""
    result = parse_asset_data(FIXTURE, source=source)
    loan_16 = next(loan for loan in result.loans if loan.asset_number == "16")
    assert loan_16.properties[0].most_recent is None


def test_property_with_most_recent_fields_populates_the_separate_group(source: SourceRef) -> None:
    result = parse_asset_data(FIXTURE, source=source)
    loan_29 = next(loan for loan in result.loans if loan.asset_number == "29")
    most_recent = loan_29.properties[0].most_recent

    assert most_recent is not None
    assert most_recent.net_operating_income_amount == Decimal("2591100.27")
    assert most_recent.financials_start_date == date(2026, 1, 1)
    assert most_recent.financials_end_date == date(2026, 3, 31)


def test_at_securitization_fields_are_never_none_when_present_in_source(source: SourceRef) -> None:
    result = parse_asset_data(FIXTURE, source=source)
    for loan in result.loans:
        at_sec = loan.properties[0].at_securitization
        assert at_sec.valuation_amount is not None
        assert at_sec.net_operating_income_amount is not None


def test_double_flow_field_name_is_matched_exactly(source: SourceRef) -> None:
    """Real SEC schema quirk verified against the live filing: the field is
    literally netCashFlowFlowSecuritizationAmount, not netCashFlowSecuritizationAmount."""
    result = parse_asset_data(FIXTURE, source=source)
    loan = result.loans[0]
    assert loan.properties[0].at_securitization.net_cash_flow_amount == Decimal("5450000.00")


def test_each_loan_gets_its_own_source_ref_with_a_distinguishing_field_path(
    source: SourceRef,
) -> None:
    result = parse_asset_data(FIXTURE, source=source)
    assert result.loans[0].source.field_path != result.loans[1].source.field_path
    for loan in result.loans:
        assert loan.asset_number in (loan.source.field_path or "")
        # everything else about the SourceRef is inherited from the file-level source
        assert loan.source.source_url == source.source_url
        assert loan.source.checksum == source.checksum
        assert loan.source.record_id == source.record_id


def test_no_data_quality_issues_on_clean_fixture(source: SourceRef) -> None:
    result = parse_asset_data(FIXTURE, source=source)
    assert result.issues == ()


def test_malformed_decimal_is_reported_as_a_data_quality_issue_not_a_crash(
    source: SourceRef,
) -> None:
    broken_xml = FIXTURE.replace(
        b"<ns:originalLoanAmount>45000000.00", b"<ns:originalLoanAmount>NOT_A_NUMBER"
    )
    result = parse_asset_data(broken_xml, source=source)

    loan_16 = next(loan for loan in result.loans if loan.asset_number == "16")
    assert loan_16.original_loan_amount is None
    assert any(
        issue.field_name == "originalLoanAmount" and issue.asset_number == "16"
        for issue in result.issues
    )


@pytest.mark.live
def test_live_parses_the_real_july_filing_to_the_measured_shape() -> None:
    """Parses the actual audited July 2026 exh_102.xml (588,639 bytes) for
    Benchmark 2026-B42 and checks it against the shape measured during the
    2026-08-28 data spike: 62 loans, 123 properties. If loan count differs
    from 62, the parser is treating <property> children as top-level assets.

    Run with:
        $env:EXTERNAL_NETWORK_ENABLED = 'true'
        uv run pytest -m live tests/unit/bondlens/test_abs_ee.py -q
    """
    url = "https://www.sec.gov/Archives/edgar/data/2110410/000188852426014162/exh_102.xml"
    http = ResilientHttpClient(httpx.Client(), source_name="sec_edgar")
    result_http = http.get_bytes(
        url,
        headers={"User-Agent": "Vichara-Portfolio/0.1 (kasarlekhraj@gmail.com)"},
        allowed_content_types=("text/xml", "application/xml"),
    )

    assert len(result_http.payload) == 588_639

    parsed = parse_asset_data(result_http.payload, source=result_http.source)

    assert len(parsed.loans) == 62
    total_properties = sum(len(loan.properties) for loan in parsed.loans)
    assert total_properties == 123
    assert parsed.issues == (), f"unexpected data-quality issues on real data: {parsed.issues}"
