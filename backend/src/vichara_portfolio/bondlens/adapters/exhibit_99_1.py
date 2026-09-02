"""Typed parser for CMBS Exhibit 99.1 monthly distribution reports.

The report is an issuer-rendered HTML document. It is not retrieval context:
certificate distributions and reconciliation figures are authoritative inputs
that must be parsed, reconciled, and exposed through deterministic tools.
This module deliberately targets tables by their visible title and validates
the cross-table balance relationship instead of relying on positional table
numbers or an LLM's interpretation of wide financial tables.
"""

from __future__ import annotations

import re
from dataclasses import replace
from decimal import Decimal, InvalidOperation

from lxml import html as lxml_html

from vichara_portfolio.bondlens.domain import (
    BondCollateralReconciliation,
    CertificateDistribution,
    DataQualityIssue,
    ParsedMonthlyReport,
)
from vichara_portfolio.shared.provenance import SourceRef


class Exhibit99ReconciliationError(ValueError):
    """The certificate and collateral balance relationship is inconsistent."""


class Exhibit99ParseError(ValueError):
    """The report contains no supported certificate-side table layout."""


_CUSIP = re.compile(r"^[A-Z0-9]{9}$")
_TABLE_CERTIFICATE_DISTRIBUTION = "Certificate Distribution Detail"
_TABLE_BALANCE_RECONCILIATION = "Bond / Collateral Reconciliation - Balances"
_TABLE_DISTRIBUTION_SUMMARY = "DISTRIBUTION SUMMARY"
_TABLE_DISTRIBUTION_FACTORS = "DISTRIBUTION SUMMARY - FACTORS"


def parse_exhibit_99_1(content: str | bytes, *, source: SourceRef) -> ParsedMonthlyReport:
    """Parse the certificate-distribution and balance-reconciliation tables.

    The interface returns only typed, validated finance data. HTML layout,
    multi-row headings, display formatting, and label matching remain hidden
    inside this module so callers cannot accidentally mix certificate and
    collateral metrics.
    """
    document = lxml_html.fromstring(content)
    issues: list[DataQualityIssue] = []
    distribution_table = _find_table(
        document, _TABLE_CERTIFICATE_DISTRIBUTION, required_text="CUSIP"
    )
    reconciliation_table = _find_table(
        document,
        _TABLE_BALANCE_RECONCILIATION,
        required_text="Beginning Scheduled Collateral Balance",
    )

    distributions = (
        _parse_certificate_distributions(distribution_table, source=source, issues=issues)
        if distribution_table is not None
        else ()
    )
    if not distributions:
        summary_table = _find_table_after_title(
            document, _TABLE_DISTRIBUTION_SUMMARY, required_text="Pass-Through"
        )
        if summary_table is None:
            summary_table = _find_table(
                document, _TABLE_DISTRIBUTION_SUMMARY, required_text="Pass-Through"
            )
        factors_table = _find_table(document, _TABLE_DISTRIBUTION_FACTORS, required_text="CUSIP")
        if factors_table is None:
            factors_table = _find_table_after_title(
                document, _TABLE_DISTRIBUTION_FACTORS, required_text="CUSIP"
            )
        if summary_table is not None and factors_table is not None:
            distributions = _parse_citigroup_distribution_summary(
                summary_table, factors_table, source=source, issues=issues
            )
    reconciliation = (
        _parse_reconciliation(reconciliation_table, source=source, issues=issues)
        if reconciliation_table is not None
        else None
    )
    if reconciliation is not None:
        _validate_reconciliation(reconciliation)
    if not distributions and reconciliation is None:
        raise Exhibit99ParseError(
            "no supported certificate distribution or balance reconciliation table found"
        )

    return ParsedMonthlyReport(
        certificate_distributions=distributions,
        reconciliation=reconciliation,
        issues=tuple(issues),
    )


def _find_table(
    document: lxml_html.HtmlElement, title: str, *, required_text: str
) -> lxml_html.HtmlElement | None:
    """Find the actual report table, not its similarly named contents entry."""
    return next(
        (
            table
            for table in document.xpath("//table")
            if title in " ".join(table.text_content().split())
            and required_text in " ".join(table.text_content().split())
        ),
        None,
    )


def _find_table_after_title(
    document: lxml_html.HtmlElement, title: str, *, required_text: str
) -> lxml_html.HtmlElement | None:
    """Resolve layouts where a page title and its data grid are sibling tables."""
    tables = document.xpath("//table")
    title_index = next(
        (
            index
            for index, table in enumerate(tables)
            if title in " ".join(table.text_content().split())
        ),
        None,
    )
    if title_index is None:
        return None
    return next(
        (
            table
            for table in tables[title_index + 1 :]
            if required_text in " ".join(table.text_content().split())
        ),
        None,
    )


def _cells(row: lxml_html.HtmlElement) -> list[str]:
    return [" ".join(cell.text_content().split()) for cell in row.xpath("./th|./td")]


def _parse_certificate_distributions(
    table: lxml_html.HtmlElement, *, source: SourceRef, issues: list[DataQualityIssue]
) -> tuple[CertificateDistribution, ...]:
    entries: list[CertificateDistribution] = []
    for row in table.xpath(".//tr"):
        cells = _cells(row)
        if len(cells) < 13 or not _CUSIP.fullmatch(cells[1]):
            continue
        class_name = cells[0].rstrip("*").strip()
        entries.append(
            CertificateDistribution(
                class_name=class_name,
                cusip=cells[1],
                pass_through_rate=_decimal(
                    cells[2], "pass_through_rate", class_name, issues, percent=True
                ),
                original_balance=_decimal(cells[3], "original_balance", class_name, issues),
                beginning_balance=_decimal(cells[4], "beginning_balance", class_name, issues),
                principal_distribution=_decimal(
                    cells[5], "principal_distribution", class_name, issues
                ),
                interest_distribution=_decimal(
                    cells[6], "interest_distribution", class_name, issues
                ),
                prepayment_penalties=_decimal(cells[7], "prepayment_penalties", class_name, issues),
                realized_losses=_decimal(cells[8], "realized_losses", class_name, issues),
                total_distribution=_decimal(cells[9], "total_distribution", class_name, issues),
                ending_balance=_decimal(cells[10], "ending_balance", class_name, issues),
                current_credit_support=_decimal(
                    cells[11], "current_credit_support", class_name, issues, percent=True
                ),
                original_credit_support=_decimal(
                    cells[12], "original_credit_support", class_name, issues, percent=True
                ),
                source=replace(source, field_path=f"certificate_distribution[class={class_name}]"),
            )
        )
    return tuple(entries)


def _parse_citigroup_distribution_summary(
    summary_table: lxml_html.HtmlElement,
    factors_table: lxml_html.HtmlElement,
    *,
    source: SourceRef,
    issues: list[DataQualityIssue],
) -> tuple[CertificateDistribution, ...]:
    """Parse Citigroup's distribution-summary layout.

    Unlike the Benchmark/Computershare layout, this issuer publishes the
    cash distributions and CUSIPs in separate tables. Joining by class is
    deliberate: class labels are the stable certificate identifier across
    both tables, while their visual column positions vary by issuer.
    """
    cusips_by_class: dict[str, str] = {}
    for row in factors_table.xpath(".//tr"):
        cells = _cells(row)
        if len(cells) < 2:
            continue
        cusip = re.sub(r"[^A-Z0-9]", "", cells[1].upper())
        if not _CUSIP.fullmatch(cusip) and len(cells) >= 3:
            cusip = re.sub(r"[^A-Z0-9]", "", f"{cells[1]}{cells[2]}".upper())
        if _CUSIP.fullmatch(cusip):
            cusips_by_class[cells[0].strip()] = cusip

    entries: list[CertificateDistribution] = []
    for row in summary_table.xpath(".//tr"):
        cells = _cells(row)
        if len(cells) < 14:
            continue
        class_name = cells[0].strip()
        class_cusip = cusips_by_class.get(class_name)
        if class_cusip is None:
            continue
        entries.append(
            CertificateDistribution(
                class_name=class_name,
                cusip=class_cusip,
                pass_through_rate=_decimal(
                    cells[3], "pass_through_rate", class_name, issues, percent=True
                ),
                original_balance=_decimal(cells[1], "original_balance", class_name, issues),
                beginning_balance=_decimal(cells[2], "beginning_balance", class_name, issues),
                principal_distribution=_decimal(
                    cells[8], "principal_distribution", class_name, issues
                ),
                interest_distribution=_decimal(
                    cells[6], "interest_distribution", class_name, issues
                ),
                prepayment_penalties=None,
                realized_losses=_decimal(cells[10], "realized_losses", class_name, issues),
                total_distribution=_decimal(cells[9], "total_distribution", class_name, issues),
                ending_balance=_decimal(cells[13], "ending_balance", class_name, issues),
                current_credit_support=None,
                original_credit_support=None,
                source=replace(source, field_path=f"certificate_distribution[class={class_name}]"),
            )
        )
    return tuple(entries)


def _parse_reconciliation(
    table: lxml_html.HtmlElement, *, source: SourceRef, issues: list[DataQualityIssue]
) -> BondCollateralReconciliation:
    values: dict[str, str] = {}
    for row in table.xpath(".//tr"):
        cells = _cells(row)
        if len(cells) >= 2 and cells[0]:
            values[cells[0]] = cells[1]
        if len(cells) >= 5 and cells[3]:
            values[cells[3]] = cells[4]

    def value(label: str, field_name: str) -> Decimal | None:
        return _decimal(values.get(label), field_name, None, issues)

    return BondCollateralReconciliation(
        beginning_scheduled_collateral_balance=value(
            "Beginning Scheduled Collateral Balance", "beginning_scheduled_collateral_balance"
        ),
        scheduled_principal_collections=value(
            "(-) Scheduled Principal Collections", "scheduled_principal_collections"
        ),
        ending_scheduled_collateral_balance=value(
            "Ending Scheduled Collateral Balance", "ending_scheduled_collateral_balance"
        ),
        beginning_actual_collateral_balance=value(
            "Beginning Actual Collateral Balance", "beginning_actual_collateral_balance"
        ),
        ending_actual_collateral_balance=value(
            "Ending Actual Collateral Balance", "ending_actual_collateral_balance"
        ),
        beginning_certificate_balance=value(
            "Beginning Certificate Balance", "beginning_certificate_balance"
        ),
        principal_distributions=value("(-) Principal Distributions", "principal_distributions"),
        ending_certificate_balance=value(
            "Ending Certificate Balance", "ending_certificate_balance"
        ),
        under_over_collateralization=value("Ending UC / (OC)", "under_over_collateralization"),
        source=replace(source, field_path="bond_collateral_reconciliation"),
    )


def _decimal(
    raw: str | None,
    field_name: str,
    record_id: str | None,
    issues: list[DataQualityIssue],
    *,
    percent: bool = False,
) -> Decimal | None:
    if raw is None or raw in {"", "--", "N/A"}:
        return None
    normalized = raw.replace(",", "").replace("$", "").replace("%", "").strip()
    if normalized.startswith("(") and normalized.endswith(")"):
        normalized = f"-{normalized[1:-1]}"
    try:
        value = Decimal(normalized)
    except InvalidOperation:
        issues.append(
            DataQualityIssue(
                asset_number=record_id,
                field_name=field_name,
                message="could not parse Exhibit 99.1 value as Decimal",
                raw_value=raw,
            )
        )
        return None
    return value / Decimal("100") if percent else value


def _validate_reconciliation(reconciliation: BondCollateralReconciliation) -> None:
    scheduled = reconciliation.ending_scheduled_collateral_balance
    certificate = reconciliation.ending_certificate_balance
    under_over = reconciliation.under_over_collateralization
    if scheduled is None or certificate is None or under_over is None:
        return
    if certificate - scheduled != under_over:
        raise Exhibit99ReconciliationError(
            "ending certificate balance minus ending scheduled collateral balance must equal "
            "the reported under/over-collateralization"
        )
