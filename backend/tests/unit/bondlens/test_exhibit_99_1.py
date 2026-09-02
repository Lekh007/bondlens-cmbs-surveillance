# ruff: noqa: E501

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from vichara_portfolio.bondlens.adapters.exhibit_99_1 import (
    Exhibit99ParseError,
    Exhibit99ReconciliationError,
    parse_exhibit_99_1,
)
from vichara_portfolio.shared.provenance import SourceRef


def _source() -> SourceRef:
    return SourceRef(
        source_name="sec_edgar",
        source_url="https://www.sec.gov/Archives/edgar/data/2110410/x/ex991.htm",
        retrieved_at=datetime(2026, 9, 2, 12, 0, tzinfo=UTC),
        record_id="0001888524-26-016277",
    )


_AUGUST_REPORT = """
<html><body>
  <table>
    <tr><td>Certificate Distribution Detail</td></tr>
    <tr><td>Class</td><td>CUSIP</td><td>Pass-Through Rate</td><td>Original Balance</td>
        <td>Beginning Balance</td><td>Principal Distribution</td><td>Interest Distribution</td>
        <td>Prepayment Penalties</td><td>Realized Losses</td><td>Total Distribution</td>
        <td>Ending Balance</td><td>Current Credit Support</td><td>Original Credit Support</td></tr>
    <tr><td>A-1</td><td>08164FAA9</td><td>4.216170%</td><td>8,602,000.00</td>
        <td>7,890,836.42</td><td>166,693.42</td><td>27,724.26</td><td>0.00</td>
        <td>0.00</td><td>194,417.68</td><td>7,724,143.00</td><td>30.04%</td><td>30.00%</td></tr>
  </table>
  <table>
    <tr><td>Bond / Collateral Reconciliation - Balances</td></tr>
    <tr><td>Beginning Scheduled Collateral Balance</td><td>728,470,251.29</td><td>728,470,251.29</td><td>Beginning Certificate Balance</td><td>728,470,250.36</td></tr>
    <tr><td>(-) Scheduled Principal Collections</td><td>171,451.19</td><td>171,451.19</td><td>(-) Principal Distributions</td><td>171,451.19</td></tr>
    <tr><td>Ending Scheduled Collateral Balance</td><td>728,298,800.10</td><td>728,298,800.10</td><td>Certificate Other Adjustments</td><td>0.00</td></tr>
    <tr><td>Beginning Actual Collateral Balance</td><td>728,470,251.29</td><td>728,470,251.29</td><td>Ending Certificate Balance</td><td>728,298,799.17</td></tr>
    <tr><td>Ending Actual Collateral Balance</td><td>728,298,800.10</td><td>728,298,800.10</td></tr>
    <tr><td>Ending UC / (OC)</td><td>(0.93)</td></tr>
  </table>
</body></html>
"""


_CITIGROUP_REPORT = """
<html><body>
  <table><tr><td>BMO 2025-C13 Mortgage Trust</td></tr><tr><td>DISTRIBUTION SUMMARY</td></tr>
    <tr><td>Class</td><td>Original Balance</td><td>Prior Balance</td><td>Pass-Through Rate</td>
      <td>%</td><td>Day Count</td><td>Interest Distributed</td><td>Accrual</td>
      <td>Principal Distributed</td><td>Total Distributed</td><td>Realized Loss</td>
      <td>Increase/Decrease</td><td></td><td>Current Balance</td></tr>
    <tr><td>A1</td><td>4,159,000.00</td><td>4,005,442.88</td><td>4.333500</td><td>%</td>
      <td>30/360</td><td>14,464.66</td><td>-</td><td>28,891.13</td><td>43,355.79</td>
      <td>-</td><td>-</td><td></td><td>3,976,551.75</td></tr>
  </table>
  <table><tr><td>BMO 2025-C13 Mortgage Trust</td></tr><tr><td>DISTRIBUTION SUMMARY - FACTORS</td></tr></table>
  <table>
    <tr><td>Class</td><td>CUSIP</td><td>Record Date</td></tr>
    <tr><td>A1</td><td>05592 YAA6</td><td>12/31/2025</td></tr>
  </table>
</body></html>
"""


def test_parses_a_certificate_distribution_and_reconciles_to_collateral() -> None:
    report = parse_exhibit_99_1(_AUGUST_REPORT, source=_source())

    assert len(report.certificate_distributions) == 1
    a1 = report.certificate_distributions[0]
    assert a1.class_name == "A-1"
    assert a1.cusip == "08164FAA9"
    assert a1.beginning_balance == Decimal("7890836.42")
    assert a1.principal_distribution == Decimal("166693.42")
    assert a1.interest_distribution == Decimal("27724.26")
    assert a1.ending_balance == Decimal("7724143.00")
    assert a1.source.field_path == "certificate_distribution[class=A-1]"

    reconciliation = report.reconciliation
    assert reconciliation is not None
    assert reconciliation.ending_actual_collateral_balance == Decimal("728298800.10")
    assert reconciliation.ending_certificate_balance == Decimal("728298799.17")
    assert reconciliation.under_over_collateralization == Decimal("-0.93")
    assert report.issues == ()


def test_rejects_a_reconciliation_that_does_not_explain_the_balance_difference() -> None:
    invalid_report = _AUGUST_REPORT.replace("(0.93)</td>", "(0.92)</td>")

    with pytest.raises(Exhibit99ReconciliationError, match="under/over-collateralization"):
        parse_exhibit_99_1(invalid_report, source=_source())


def test_allows_actual_collateral_to_differ_from_the_certificate_balance() -> None:
    report_with_actual_servicing_difference = _AUGUST_REPORT.replace(
        "Ending Actual Collateral Balance</td><td>728,298,800.10",
        "Ending Actual Collateral Balance</td><td>728,268,000.10",
    )

    report = parse_exhibit_99_1(report_with_actual_servicing_difference, source=_source())

    assert report.reconciliation is not None
    assert report.reconciliation.ending_actual_collateral_balance == Decimal("728268000.10")


def test_parses_citigroup_distribution_summary_with_a_separate_cusip_table() -> None:
    report = parse_exhibit_99_1(_CITIGROUP_REPORT, source=_source())

    assert len(report.certificate_distributions) == 1
    a1 = report.certificate_distributions[0]
    assert a1.class_name == "A1"
    assert a1.cusip == "05592YAA6"
    assert a1.pass_through_rate == Decimal("0.043335")
    assert a1.beginning_balance == Decimal("4005442.88")
    assert a1.principal_distribution == Decimal("28891.13")
    assert a1.interest_distribution == Decimal("14464.66")
    assert a1.ending_balance == Decimal("3976551.75")


def test_rejects_an_unrecognised_monthly_report_layout() -> None:
    with pytest.raises(Exhibit99ParseError, match="no supported certificate distribution"):
        parse_exhibit_99_1("<html><table><tr><td>Unknown report</td></tr></table></html>", source=_source())
