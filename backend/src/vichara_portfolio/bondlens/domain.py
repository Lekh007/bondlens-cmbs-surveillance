"""BondLens domain types.

Scope note (see docs/plans/design.md section 0): the time-varying CMBS
signal on a fresh deal lives at loan level, not property level, so `Loan`
and `PropertySnapshot` are modeled separately rather than flattened - a
property record's `most_recent_*` fields update on the servicer's own
cadence and are frequently absent, while `*_at_securitization` fields are
frozen at issuance and identical in every period.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from vichara_portfolio.shared.provenance import SourceRef


@dataclass(frozen=True)
class SecFiling:
    cik: str
    accession_number: str
    form_type: str
    filing_date: date
    report_date: date | None
    primary_document: str


@dataclass(frozen=True)
class SubmissionsResult:
    entity_name: str
    filings: tuple[SecFiling, ...]
    source: SourceRef


@dataclass(frozen=True)
class Deal:
    cik: str
    name: str


@dataclass(frozen=True)
class ReportingPeriod:
    beginning_date: date | None
    ending_date: date | None


@dataclass(frozen=True)
class PropertyAtSecuritization:
    """Frozen at issuance - identical in every reporting period for a given
    property. Always populated in the source data (measured: 123/123)."""

    valuation_amount: Decimal | None
    valuation_date: date | None
    physical_occupancy_percentage: Decimal | None
    net_rentable_square_feet: Decimal | None
    revenue_amount: Decimal | None
    operating_expenses_amount: Decimal | None
    net_operating_income_amount: Decimal | None
    net_cash_flow_amount: Decimal | None


@dataclass(frozen=True)
class PropertyMostRecent:
    """Servicer-updated on its own cadence, not tied to the filing's
    reporting period. Sparse by design - measured: 29/123 properties on
    this deal, quarterly window. None means the servicer has never
    reported since securitization, not that the property has no data."""

    financials_start_date: date | None
    financials_end_date: date | None
    revenue_amount: Decimal | None
    operating_expenses_amount: Decimal | None
    net_operating_income_amount: Decimal | None
    net_cash_flow_amount: Decimal | None
    debt_service_amount: Decimal | None
    physical_occupancy_percentage: Decimal | None
    debt_service_coverage_noi_percentage: Decimal | None
    debt_service_coverage_ncf_percentage: Decimal | None


@dataclass(frozen=True)
class PropertySnapshot:
    property_name: str
    property_address: str | None
    property_city: str | None
    property_state: str | None
    property_zip: str | None
    property_county: str | None
    property_type_code: str | None
    year_built: int | None
    net_rentable_square_feet: Decimal | None
    at_securitization: PropertyAtSecuritization
    most_recent: PropertyMostRecent | None
    raw_fields: dict[str, str]


@dataclass(frozen=True)
class Loan:
    asset_number: str
    group_id: str | None
    originator_name: str | None
    origination_date: date | None
    original_loan_amount: Decimal | None
    original_interest_rate_percentage: Decimal | None
    maturity_date: date | None
    reporting_period: ReportingPeriod
    paid_through_date: date | None
    scheduled_principal_amount: Decimal | None
    scheduled_interest_amount: Decimal | None
    actual_balance_amount: Decimal | None
    scheduled_balance_amount: Decimal | None
    payment_status_code: str | None
    properties: tuple[PropertySnapshot, ...]
    raw_fields: dict[str, str]
    source: SourceRef


@dataclass(frozen=True)
class DataQualityIssue:
    asset_number: str | None
    field_name: str
    message: str
    raw_value: str | None


@dataclass(frozen=True)
class ParsedAssetData:
    loans: tuple[Loan, ...]
    issues: tuple[DataQualityIssue, ...]


@dataclass(frozen=True)
class CertificateDistribution:
    """One certificate class from an Exhibit 99.1 monthly distribution report.

    These are certificate-side figures. They must never be substituted for
    collateral balances from ABS-EE asset data: the two can differ because of
    under/over-collateralization or other certificate-level adjustments.
    """

    class_name: str
    cusip: str
    pass_through_rate: Decimal | None
    original_balance: Decimal | None
    beginning_balance: Decimal | None
    principal_distribution: Decimal | None
    interest_distribution: Decimal | None
    prepayment_penalties: Decimal | None
    realized_losses: Decimal | None
    total_distribution: Decimal | None
    ending_balance: Decimal | None
    current_credit_support: Decimal | None
    original_credit_support: Decimal | None
    source: SourceRef


@dataclass(frozen=True)
class BondCollateralReconciliation:
    """Deal-level balance reconciliation from Exhibit 99.1.

    Under/over-collateralization reconciles the scheduled collateral and
    certificate balances. Actual collateral is a separate servicing measure
    and can legitimately differ from both, so it must not be used in that
    equality check.
    """

    beginning_scheduled_collateral_balance: Decimal | None
    scheduled_principal_collections: Decimal | None
    ending_scheduled_collateral_balance: Decimal | None
    beginning_actual_collateral_balance: Decimal | None
    ending_actual_collateral_balance: Decimal | None
    beginning_certificate_balance: Decimal | None
    principal_distributions: Decimal | None
    ending_certificate_balance: Decimal | None
    under_over_collateralization: Decimal | None
    source: SourceRef


@dataclass(frozen=True)
class ParsedMonthlyReport:
    certificate_distributions: tuple[CertificateDistribution, ...]
    reconciliation: BondCollateralReconciliation | None
    issues: tuple[DataQualityIssue, ...]
