"""Streaming parser for SEC ABS-EE CMBS asset-level XML (EX-102).

Deviation from the plan's literal "defusedxml/lxml" wording: defusedxml's
lxml integration is deprecated and its `iterparse` raises
`NotSupportedError` outright (verified against the installed version
2026-08-28) - it was never usable for this. lxml's own `etree.iterparse`
is used directly instead, with `resolve_entities=False`, `no_network=True`,
`load_dtd=False`, and `huge_tree=False` passed explicitly (verified these
block a `SYSTEM` entity reference in a local check rather than resolving
it), which is the standard hardened configuration for untrusted XML.

Namespace independence: elements are matched by local name only (the part
after `}` in `{uri}localname`), not by a hardcoded namespace URI or
prefix. The real filing uses a default (unprefixed) namespace; the test
fixture deliberately uses a prefixed one to prove this doesn't matter.

Field families are kept separate, never flattened - see the PropertyAtSecuritization
vs PropertyMostRecent docstrings in domain.py and design.md section 0.
"""

from __future__ import annotations

import io
from collections.abc import Iterator
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from lxml import etree

from vichara_portfolio.bondlens.domain import (
    DataQualityIssue,
    Loan,
    ParsedAssetData,
    PropertyAtSecuritization,
    PropertyMostRecent,
    PropertySnapshot,
    ReportingPeriod,
)
from vichara_portfolio.shared.provenance import SourceRef

_MOST_RECENT_FIELDS = (
    "mostRecentFinancialsStartDate",
    "mostRecentFinancialsEndDate",
    "mostRecentRevenueAmount",
    "operatingExpensesAmount",
    "mostRecentNetOperatingIncomeAmount",
    "mostRecentNetCashFlowAmount",
    "mostRecentDebtServiceAmount",
    "mostRecentPhysicalOccupancyPercentage",
    "mostRecentDebtServiceCoverageNetOperatingIncomePercentage",
    "mostRecentDebtServiceCoverageNetCashFlowpercentage",
)


def parse_asset_data(xml_bytes: bytes, *, source: SourceRef) -> ParsedAssetData:
    issues: list[DataQualityIssue] = []
    loans = [
        _parse_loan(element, source=source, issues=issues)
        for element in _iter_local_name(xml_bytes, "assets")
    ]
    return ParsedAssetData(loans=tuple(loans), issues=tuple(issues))


def _iter_local_name(xml_bytes: bytes, local_name: str) -> Iterator[etree._Element]:
    stream = io.BytesIO(xml_bytes)
    context = etree.iterparse(
        stream,
        events=("end",),
        resolve_entities=False,
        no_network=True,
        load_dtd=False,
        huge_tree=False,
        remove_comments=True,
        remove_pis=True,
    )
    for _event, element in context:
        if _local_name(element.tag) != local_name:
            continue
        yield element
        _clear_element(element)


def _clear_element(element: etree._Element) -> None:
    element.clear()
    parent = element.getparent()
    if parent is not None:
        while element.getprevious() is not None:
            del parent[0]


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _collect_leaf_fields(element: etree._Element) -> dict[str, str]:
    fields: dict[str, str] = {}
    for child in element:
        name = _local_name(child.tag)
        if name == "property":
            continue
        if child.text is not None and child.text.strip():
            fields[name] = child.text.strip()
    return fields


def _parse_loan(
    element: etree._Element, *, source: SourceRef, issues: list[DataQualityIssue]
) -> Loan:
    fields = _collect_leaf_fields(element)
    asset_number = fields.get("assetNumber")

    def dec(name: str) -> Decimal | None:
        return _parse_decimal(
            fields.get(name), field_name=name, asset_number=asset_number, issues=issues
        )

    def dt(name: str) -> date | None:
        return _parse_date(
            fields.get(name), field_name=name, asset_number=asset_number, issues=issues
        )

    properties = tuple(
        _parse_property(_collect_leaf_fields(child), asset_number=asset_number, issues=issues)
        for child in element
        if _local_name(child.tag) == "property"
    )
    reporting_period = ReportingPeriod(
        beginning_date=dt("reportingPeriodBeginningDate"), ending_date=dt("reportingPeriodEndDate")
    )
    loan_source = replace(source, field_path=f"assets[assetNumber={asset_number}]")

    return Loan(
        asset_number=asset_number or "",
        group_id=fields.get("GroupID"),
        originator_name=fields.get("originatorName"),
        origination_date=dt("originationDate"),
        original_loan_amount=dec("originalLoanAmount"),
        original_interest_rate_percentage=dec("originalInterestRatePercentage"),
        maturity_date=dt("maturityDate"),
        reporting_period=reporting_period,
        paid_through_date=dt("paidThroughDate"),
        scheduled_principal_amount=dec("scheduledPrincipalAmount"),
        scheduled_interest_amount=dec("scheduledInterestAmount"),
        actual_balance_amount=dec("reportPeriodEndActualBalanceAmount"),
        scheduled_balance_amount=dec("reportPeriodEndScheduledLoanBalanceAmount"),
        payment_status_code=fields.get("paymentStatusLoanCode"),
        properties=properties,
        raw_fields=fields,
        source=loan_source,
    )


def _parse_property(
    fields: dict[str, str], *, asset_number: str | None, issues: list[DataQualityIssue]
) -> PropertySnapshot:
    def dec(name: str) -> Decimal | None:
        return _parse_decimal(
            fields.get(name), field_name=name, asset_number=asset_number, issues=issues
        )

    def dt(name: str) -> date | None:
        return _parse_date(
            fields.get(name), field_name=name, asset_number=asset_number, issues=issues
        )

    def integer(name: str) -> int | None:
        return _parse_int(
            fields.get(name), field_name=name, asset_number=asset_number, issues=issues
        )

    at_securitization = PropertyAtSecuritization(
        valuation_amount=dec("valuationSecuritizationAmount"),
        valuation_date=dt("valuationSecuritizationDate"),
        physical_occupancy_percentage=dec("physicalOccupancySecuritizationPercentage"),
        net_rentable_square_feet=dec("netRentableSquareFeetSecuritizationNumber"),
        revenue_amount=dec("revenueSecuritizationAmount"),
        operating_expenses_amount=dec("operatingExpensesSecuritizationAmount"),
        net_operating_income_amount=dec("netOperatingIncomeSecuritizationAmount"),
        # Real SEC schema field name, verified against the live filing: "Flow" appears twice.
        net_cash_flow_amount=dec("netCashFlowFlowSecuritizationAmount"),
    )

    most_recent = None
    if any(fields.get(name) for name in _MOST_RECENT_FIELDS):
        most_recent = PropertyMostRecent(
            financials_start_date=dt("mostRecentFinancialsStartDate"),
            financials_end_date=dt("mostRecentFinancialsEndDate"),
            revenue_amount=dec("mostRecentRevenueAmount"),
            operating_expenses_amount=dec("operatingExpensesAmount"),
            net_operating_income_amount=dec("mostRecentNetOperatingIncomeAmount"),
            net_cash_flow_amount=dec("mostRecentNetCashFlowAmount"),
            debt_service_amount=dec("mostRecentDebtServiceAmount"),
            physical_occupancy_percentage=dec("mostRecentPhysicalOccupancyPercentage"),
            debt_service_coverage_noi_percentage=dec(
                "mostRecentDebtServiceCoverageNetOperatingIncomePercentage"
            ),
            debt_service_coverage_ncf_percentage=dec(
                "mostRecentDebtServiceCoverageNetCashFlowpercentage"
            ),
        )

    return PropertySnapshot(
        property_name=fields.get("propertyName", ""),
        property_address=fields.get("propertyAddress"),
        property_city=fields.get("propertyCity"),
        property_state=fields.get("propertyState"),
        property_zip=fields.get("propertyZip"),
        property_county=fields.get("propertyCounty"),
        property_type_code=fields.get("propertyTypeCode"),
        year_built=integer("yearBuiltNumber"),
        net_rentable_square_feet=dec("netRentableSquareFeetNumber"),
        at_securitization=at_securitization,
        most_recent=most_recent,
        raw_fields=dict(fields),
    )


def _parse_decimal(
    raw: str | None, *, field_name: str, asset_number: str | None, issues: list[DataQualityIssue]
) -> Decimal | None:
    if raw is None:
        return None
    try:
        return Decimal(raw)
    except InvalidOperation:
        issues.append(
            DataQualityIssue(
                asset_number=asset_number,
                field_name=field_name,
                message="could not parse as Decimal",
                raw_value=raw,
            )
        )
        return None


def _parse_date(
    raw: str | None, *, field_name: str, asset_number: str | None, issues: list[DataQualityIssue]
) -> date | None:
    if raw is None:
        return None
    # The live ABS-EE asset XML uses MM-DD-YYYY (verified 2026-08-28 against
    # the real July filing: "07-13-2026"), not ISO. The unrelated submissions
    # JSON API (Task 6) does use ISO - the two SEC data sources disagree.
    # ISO is tried second for robustness against a future schema change.
    for parser in (lambda s: datetime.strptime(s, "%m-%d-%Y").date(), date.fromisoformat):
        try:
            return parser(raw)
        except ValueError:
            continue
    issues.append(
        DataQualityIssue(
            asset_number=asset_number,
            field_name=field_name,
            message="could not parse as MM-DD-YYYY or ISO date",
            raw_value=raw,
        )
    )
    return None


def _parse_int(
    raw: str | None, *, field_name: str, asset_number: str | None, issues: list[DataQualityIssue]
) -> int | None:
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        issues.append(
            DataQualityIssue(
                asset_number=asset_number,
                field_name=field_name,
                message="could not parse as int",
                raw_value=raw,
            )
        )
        return None
