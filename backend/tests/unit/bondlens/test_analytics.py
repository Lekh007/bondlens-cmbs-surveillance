"""Regression-pinned against the real May and July 2026 Benchmark 2026-B42
ABS-EE filings (backend/tests/fixtures/sec/abs_ee_2026-{05,07}.xml - the
actual downloaded exh_102.xml bytes, not synthetic data). These exact
values were measured during the 2026-08-28 data spike; see design.md
section 0.
"""

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from vichara_portfolio.bondlens.adapters.abs_ee import parse_asset_data
from vichara_portfolio.bondlens.analytics import (
    compare_reporting_periods,
    get_deal_summary,
    get_geography_distribution,
    get_loan_history,
    get_property_profile,
    get_property_type_distribution,
    rank_loans_by_balance_drift,
    rank_loans_by_status_change,
    rank_properties_by_noi_change,
)
from vichara_portfolio.shared.provenance import SourceRef

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "sec"


def _source(label: str) -> SourceRef:
    return SourceRef(
        source_name="sec_edgar",
        source_url=f"https://www.sec.gov/Archives/edgar/data/2110410/x/exh_102-{label}.xml",
        retrieved_at=datetime(2026, 8, 28, 12, 0, tzinfo=UTC),
        checksum=f"checksum-{label}",
    )


@pytest.fixture(scope="module")
def may_loans():
    xml = (FIXTURES / "abs_ee_2026-05.xml").read_bytes()
    return parse_asset_data(xml, source=_source("may")).loans


@pytest.fixture(scope="module")
def july_loans():
    xml = (FIXTURES / "abs_ee_2026-07.xml").read_bytes()
    return parse_asset_data(xml, source=_source("july")).loans


# --------------------------------------------------------------------------
# get_deal_summary
# --------------------------------------------------------------------------


def test_deal_summary_loan_and_property_counts(july_loans) -> None:
    summary = get_deal_summary(
        cik="0002110410",
        name="Benchmark 2026-B42 Mortgage Trust",
        loans=july_loans,
        source=_source("july"),
    )
    assert summary.loan_count == 62
    assert summary.property_count == 123


def test_deal_summary_totals_are_decimal_and_positive(july_loans) -> None:
    summary = get_deal_summary(
        cik="0002110410",
        name="Benchmark 2026-B42 Mortgage Trust",
        loans=july_loans,
        source=_source("july"),
    )
    assert isinstance(summary.total_actual_balance_amount, Decimal)
    assert summary.total_actual_balance_amount > 0
    assert summary.total_original_loan_amount > summary.total_actual_balance_amount


def test_deal_summary_of_empty_deal_has_zero_totals_not_a_crash() -> None:
    summary = get_deal_summary(
        cik="0000000000", name="Empty Deal", loans=(), source=_source("empty")
    )
    assert summary.loan_count == 0
    assert summary.total_actual_balance_amount == Decimal(0)
    assert summary.reporting_period_ending_date is None


# --------------------------------------------------------------------------
# rank_loans_by_status_change - the three pinned real transitions
# --------------------------------------------------------------------------


def test_exactly_three_loans_changed_payment_status(may_loans, july_loans) -> None:
    ranking = rank_loans_by_status_change(may_loans, july_loans)
    assert len(ranking.entries) == 3


def test_loan_30_cummins_station_newly_delinquent(may_loans, july_loans) -> None:
    ranking = rank_loans_by_status_change(may_loans, july_loans)
    entry = next(e for e in ranking.entries if e.loan_asset_number == "30")
    assert entry.status_before == "0"
    assert entry.status_after == "B"
    assert "Cummins Station" in entry.property_names
    assert entry.severity_rank == 2


def test_loan_16_pwc_pennant_cured(may_loans, july_loans) -> None:
    ranking = rank_loans_by_status_change(may_loans, july_loans)
    entry = next(e for e in ranking.entries if e.loan_asset_number == "16")
    assert entry.status_before == "B"
    assert entry.status_after == "0"
    assert "PWC Pennant" in entry.property_names
    assert entry.severity_rank == 0


def test_loan_39_325_east_14th_street_cured(may_loans, july_loans) -> None:
    ranking = rank_loans_by_status_change(may_loans, july_loans)
    entry = next(e for e in ranking.entries if e.loan_asset_number == "39")
    assert entry.status_before == "B"
    assert entry.status_after == "0"
    assert "325 East 14th Street" in entry.property_names
    assert entry.severity_rank == 0


def test_newly_delinquent_loan_ranks_above_cured_loans(may_loans, july_loans) -> None:
    ranking = rank_loans_by_status_change(may_loans, july_loans)
    ranked_asset_numbers = [e.loan_asset_number for e in ranking.entries]
    assert ranked_asset_numbers[0] == "30"  # newly delinquent, severity_rank=2, sorts first


def test_status_ranking_ties_break_by_asset_number(may_loans, july_loans) -> None:
    ranking = rank_loans_by_status_change(may_loans, july_loans)
    cured = [e.loan_asset_number for e in ranking.entries if e.severity_rank == 0]
    assert cured == sorted(cured)


def test_status_ranking_carries_period_boundaries(may_loans, july_loans) -> None:
    ranking = rank_loans_by_status_change(may_loans, july_loans)
    assert ranking.period_a_ending_date is not None
    assert ranking.period_b_ending_date is not None
    assert ranking.period_a_ending_date < ranking.period_b_ending_date


def test_loans_absent_from_period_a_are_not_treated_as_a_status_change(
    may_loans, july_loans
) -> None:
    """A loan only present in period B (newly securitized/added mid-deal, if
    any) must not appear as a spurious status change with no prior value."""
    ranking = rank_loans_by_status_change((), july_loans)
    assert ranking.entries == ()


# --------------------------------------------------------------------------
# balance drift
# --------------------------------------------------------------------------


def test_24_of_62_loans_show_balance_drift_movement(may_loans, july_loans) -> None:
    """Pinned from the 2026-08-28 spike: 24 of 62 loans changed
    reportPeriodEndActualBalanceAmount between May and July."""
    comparison = compare_reporting_periods(may_loans, july_loans)
    balance_changes = {
        c.loan_asset_number
        for c in comparison.changes
        if c.field_name == "reportPeriodEndActualBalanceAmount"
    }
    assert len(balance_changes) == 24


def test_balance_drift_ranking_excludes_loans_missing_either_balance(july_loans) -> None:
    ranking = rank_loans_by_balance_drift(july_loans)
    assert len(ranking.entries) <= len(july_loans)
    for entry in ranking.entries:
        assert entry.actual_balance_amount is not None
        assert entry.scheduled_balance_amount is not None


def test_balance_drift_amount_is_actual_minus_scheduled(july_loans) -> None:
    ranking = rank_loans_by_balance_drift(july_loans)
    for entry in ranking.entries:
        assert entry.drift_amount == entry.actual_balance_amount - entry.scheduled_balance_amount


def test_balance_drift_ranking_is_sorted_by_absolute_drift_descending(july_loans) -> None:
    ranking = rank_loans_by_balance_drift(july_loans)
    magnitudes = [abs(e.drift_amount) for e in ranking.entries]
    assert magnitudes == sorted(magnitudes, reverse=True)


def test_zero_scheduled_balance_does_not_crash_percentage_calc() -> None:
    from vichara_portfolio.bondlens.domain import Loan, ReportingPeriod
    from vichara_portfolio.shared.provenance import SourceRef as SR

    loan = Loan(
        asset_number="X",
        group_id=None,
        originator_name=None,
        origination_date=None,
        original_loan_amount=None,
        original_interest_rate_percentage=None,
        maturity_date=None,
        reporting_period=ReportingPeriod(beginning_date=None, ending_date=None),
        paid_through_date=None,
        scheduled_principal_amount=None,
        scheduled_interest_amount=None,
        actual_balance_amount=Decimal("100"),
        scheduled_balance_amount=Decimal("0"),
        payment_status_code=None,
        properties=(),
        raw_fields={},
        source=SR.now(source_name="test", source_url="https://example.test/x"),
    )
    ranking = rank_loans_by_balance_drift((loan,))
    assert ranking.entries[0].drift_percentage is None


# --------------------------------------------------------------------------
# rank_properties_by_noi_change - must return zero, with a reason
# --------------------------------------------------------------------------


def test_property_level_noi_ranking_returns_zero_deteriorations(may_loans, july_loans) -> None:
    ranking = rank_properties_by_noi_change(may_loans, july_loans)
    assert ranking.entries == ()


def test_property_level_noi_ranking_excludes_three_null_to_value_properties(
    may_loans, july_loans
) -> None:
    ranking = rank_properties_by_noi_change(may_loans, july_loans)
    assert ranking.excluded_null_to_value_count == 3


def test_property_level_noi_ranking_reason_explains_the_empty_result(may_loans, july_loans) -> None:
    ranking = rank_properties_by_noi_change(may_loans, july_loans)
    assert "excluded" in ranking.reason
    assert "3" in ranking.reason


# --------------------------------------------------------------------------
# get_loan_history
# --------------------------------------------------------------------------


def test_loan_history_is_chronologically_ordered(may_loans, july_loans) -> None:
    history = get_loan_history("30", may_loans + july_loans)
    assert len(history.entries) == 2
    assert (
        history.entries[0].reporting_period_ending_date
        < history.entries[1].reporting_period_ending_date
    )
    assert history.entries[0].payment_status_code == "0"
    assert history.entries[1].payment_status_code == "B"


def test_loan_history_captures_advances_outstanding_for_loan_30(may_loans, july_loans) -> None:
    history = get_loan_history("30", may_loans + july_loans)
    assert history.entries[0].advances_outstanding_amount == Decimal("0.00000000")
    assert history.entries[1].advances_outstanding_amount == Decimal("44695.31000000")


def test_loan_history_for_unknown_asset_number_is_empty(may_loans) -> None:
    history = get_loan_history("does-not-exist", may_loans)
    assert history.entries == ()


# --------------------------------------------------------------------------
# get_property_profile - point in time, not a series
# --------------------------------------------------------------------------


def test_property_profile_returns_at_securitization_and_most_recent(july_loans) -> None:
    profile = get_property_profile(
        asset_number="30", property_name="Cummins Station", loans=july_loans
    )
    assert profile is not None
    assert profile.property_name == "Cummins Station"
    assert profile.at_securitization.valuation_amount is not None
    assert "not a time series" in profile.note


def test_property_profile_for_unknown_loan_is_none(july_loans) -> None:
    assert get_property_profile(asset_number="9999", property_name="X", loans=july_loans) is None


def test_property_profile_for_unknown_property_name_is_none(july_loans) -> None:
    assert (
        get_property_profile(
            asset_number="30", property_name="Not A Real Property", loans=july_loans
        )
        is None
    )


# --------------------------------------------------------------------------
# get_property_type_distribution - real SEC ABS-EE propertyTypeCode values,
# not decorated with invented full-name labels (raw codes only)
# --------------------------------------------------------------------------


def test_property_type_distribution_counts_match_the_real_july_filing(july_loans) -> None:
    dist = get_property_type_distribution(july_loans)
    counts = {e.property_type_code: e.property_count for e in dist.entries}

    assert dist.total_properties == 123
    assert dist.properties_missing_type == 0
    assert counts == {
        "SS": 52,
        "CH": 25,
        "RT": 20,
        "MU": 15,
        "MH": 6,
        "OF": 3,
        "MF": 1,
        "LO": 1,
    }


def test_property_type_distribution_is_sorted_by_count_descending(july_loans) -> None:
    dist = get_property_type_distribution(july_loans)
    counts = [e.property_count for e in dist.entries]
    assert counts == sorted(counts, reverse=True)
    assert dist.entries[0].property_type_code == "SS"


def test_property_type_distribution_of_no_loans_is_empty_not_a_crash() -> None:
    dist = get_property_type_distribution(())
    assert dist.entries == ()
    assert dist.total_properties == 0
    assert dist.properties_missing_type == 0


# --------------------------------------------------------------------------
# get_geography_distribution - real propertyState values (USPS codes)
# --------------------------------------------------------------------------


def test_geography_distribution_counts_match_the_real_july_filing(july_loans) -> None:
    dist = get_geography_distribution(july_loans)
    counts = {e.state: e.property_count for e in dist.entries}

    assert dist.total_properties == 123
    assert dist.properties_missing_state == 0
    assert len(dist.entries) == 34
    assert counts["NY"] == 31
    assert counts["CA"] == 13
    assert counts["TX"] == 12


def test_geography_distribution_is_sorted_by_count_descending(july_loans) -> None:
    dist = get_geography_distribution(july_loans)
    counts = [e.property_count for e in dist.entries]
    assert counts == sorted(counts, reverse=True)
    assert dist.entries[0].state == "NY"


def test_geography_distribution_of_no_loans_is_empty_not_a_crash() -> None:
    dist = get_geography_distribution(())
    assert dist.entries == ()
    assert dist.total_properties == 0
    assert dist.properties_missing_state == 0
