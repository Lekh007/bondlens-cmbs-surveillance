"""Deterministic BondLens surveillance tools.

These are pure functions over already-parsed Loan tuples - no I/O, no
LLM. Every result carries a formula_version, period boundaries where
applicable, and SourceRef objects, so the LangGraph agent (Task 13) can
cite exactly where each number came from. The agent narrates these
outputs; it never computes an authoritative figure itself.

Property-level "deterioration" ranking is deliberately not a general
change-ranking function that happens to return nothing on this deal -
see rank_properties_by_noi_change, which returns an explicit empty
result with a reason rather than a fabricated ordering, per the
measured finding in design.md section 0 (3 apparent NOI "changes" on
this deal are null-to-first-reported-value, not deterioration).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from vichara_portfolio.bondlens.domain import (
    Loan,
    PropertyAtSecuritization,
    PropertyMostRecent,
)
from vichara_portfolio.shared.provenance import SourceRef

FORMULA_VERSION = "bondlens-analytics-v1"

_CURRENT_STATUS_CODE = "0"


# --------------------------------------------------------------------------
# get_deal_summary
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class DealSummary:
    cik: str
    name: str
    loan_count: int
    property_count: int
    total_original_loan_amount: Decimal
    total_actual_balance_amount: Decimal
    reporting_period_ending_date: date | None
    formula_version: str
    source: SourceRef


def get_deal_summary(
    *, cik: str, name: str, loans: tuple[Loan, ...], source: SourceRef
) -> DealSummary:
    total_original = sum(
        (loan.original_loan_amount or Decimal(0) for loan in loans), start=Decimal(0)
    )
    total_actual = sum(
        (loan.actual_balance_amount or Decimal(0) for loan in loans), start=Decimal(0)
    )
    ending_date = loans[0].reporting_period.ending_date if loans else None
    return DealSummary(
        cik=cik,
        name=name,
        loan_count=len(loans),
        property_count=sum(len(loan.properties) for loan in loans),
        total_original_loan_amount=total_original,
        total_actual_balance_amount=total_actual,
        reporting_period_ending_date=ending_date,
        formula_version=FORMULA_VERSION,
        source=source,
    )


# --------------------------------------------------------------------------
# compare_reporting_periods
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class LoanFieldChange:
    loan_asset_number: str
    field_name: str
    before_value: str | None
    after_value: str | None


@dataclass(frozen=True)
class PeriodComparison:
    period_a_ending_date: date | None
    period_b_ending_date: date | None
    changes: tuple[LoanFieldChange, ...]
    formula_version: str


def _advances_outstanding(loan: Loan) -> Decimal | None:
    """Not a typed Loan field - only fields with an independent query need are
    promoted out of raw_fields (Task 8 design note). Advances is read here,
    directly, by its verified real XML field name."""
    raw = loan.raw_fields.get("totalPrincipalInterestAdvancedOutstandingAmount")
    if raw is None:
        return None
    try:
        return Decimal(raw)
    except InvalidOperation:
        return None


def _stringify(value: object) -> str | None:
    return None if value is None else str(value)


_TRACKED_FIELDS: tuple[tuple[str, Callable[[Loan], object]], ...] = (
    ("paymentStatusLoanCode", lambda loan: loan.payment_status_code),
    ("reportPeriodEndActualBalanceAmount", lambda loan: loan.actual_balance_amount),
    ("reportPeriodEndScheduledLoanBalanceAmount", lambda loan: loan.scheduled_balance_amount),
    ("paidThroughDate", lambda loan: loan.paid_through_date),
    ("totalPrincipalInterestAdvancedOutstandingAmount", _advances_outstanding),
)


def compare_reporting_periods(
    loans_a: tuple[Loan, ...], loans_b: tuple[Loan, ...]
) -> PeriodComparison:
    by_asset_a = {loan.asset_number: loan for loan in loans_a}
    changes: list[LoanFieldChange] = []
    for loan_b in loans_b:
        loan_a = by_asset_a.get(loan_b.asset_number)
        if loan_a is None:
            continue  # newly added loan - no prior period to compare against
        for field_name, getter in _TRACKED_FIELDS:
            before = getter(loan_a)
            after = getter(loan_b)
            if before != after:
                changes.append(
                    LoanFieldChange(
                        loan_b.asset_number, field_name, _stringify(before), _stringify(after)
                    )
                )

    return PeriodComparison(
        period_a_ending_date=loans_a[0].reporting_period.ending_date if loans_a else None,
        period_b_ending_date=loans_b[0].reporting_period.ending_date if loans_b else None,
        changes=tuple(changes),
        formula_version=FORMULA_VERSION,
    )


# --------------------------------------------------------------------------
# rank_loans_by_status_change
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class StatusChangeEntry:
    loan_asset_number: str
    property_names: tuple[str, ...]
    status_before: str | None
    status_after: str | None
    severity_rank: int


@dataclass(frozen=True)
class StatusChangeRanking:
    entries: tuple[StatusChangeEntry, ...]
    period_a_ending_date: date | None
    period_b_ending_date: date | None
    formula_version: str


def _status_severity_rank(before: str | None, after: str | None) -> int:
    """2 = newly delinquent (was current, now isn't). 1 = changed between two
    non-current codes. 0 = cured (now current). Only called for entries
    already known to have changed, so 0 here never means "no change"."""
    if before == _CURRENT_STATUS_CODE and after != _CURRENT_STATUS_CODE:
        return 2
    if after == _CURRENT_STATUS_CODE:
        return 0
    return 1


def rank_loans_by_status_change(
    loans_a: tuple[Loan, ...], loans_b: tuple[Loan, ...]
) -> StatusChangeRanking:
    by_asset_a = {loan.asset_number: loan for loan in loans_a}
    entries: list[StatusChangeEntry] = []
    for loan_b in loans_b:
        loan_a = by_asset_a.get(loan_b.asset_number)
        if loan_a is None or loan_a.payment_status_code == loan_b.payment_status_code:
            continue
        entries.append(
            StatusChangeEntry(
                loan_asset_number=loan_b.asset_number,
                property_names=tuple(p.property_name for p in loan_b.properties),
                status_before=loan_a.payment_status_code,
                status_after=loan_b.payment_status_code,
                severity_rank=_status_severity_rank(
                    loan_a.payment_status_code, loan_b.payment_status_code
                ),
            )
        )

    entries.sort(key=lambda e: (-e.severity_rank, e.loan_asset_number))
    return StatusChangeRanking(
        entries=tuple(entries),
        period_a_ending_date=loans_a[0].reporting_period.ending_date if loans_a else None,
        period_b_ending_date=loans_b[0].reporting_period.ending_date if loans_b else None,
        formula_version=FORMULA_VERSION,
    )


# --------------------------------------------------------------------------
# rank_loans_by_balance_drift
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class BalanceDriftEntry:
    loan_asset_number: str
    property_names: tuple[str, ...]
    actual_balance_amount: Decimal
    scheduled_balance_amount: Decimal
    drift_amount: Decimal
    drift_percentage: Decimal | None


@dataclass(frozen=True)
class BalanceDriftRanking:
    entries: tuple[BalanceDriftEntry, ...]
    as_of_date: date | None
    formula_version: str


def rank_loans_by_balance_drift(loans: tuple[Loan, ...]) -> BalanceDriftRanking:
    entries: list[BalanceDriftEntry] = []
    for loan in loans:
        if loan.actual_balance_amount is None or loan.scheduled_balance_amount is None:
            continue  # excluded, not ranked as zero drift
        drift = loan.actual_balance_amount - loan.scheduled_balance_amount
        pct = (
            (drift / loan.scheduled_balance_amount * 100)
            if loan.scheduled_balance_amount != 0
            else None
        )
        entries.append(
            BalanceDriftEntry(
                loan_asset_number=loan.asset_number,
                property_names=tuple(p.property_name for p in loan.properties),
                actual_balance_amount=loan.actual_balance_amount,
                scheduled_balance_amount=loan.scheduled_balance_amount,
                drift_amount=drift,
                drift_percentage=pct,
            )
        )

    entries.sort(key=lambda e: (-abs(e.drift_amount), e.loan_asset_number))
    return BalanceDriftRanking(
        entries=tuple(entries),
        as_of_date=loans[0].reporting_period.ending_date if loans else None,
        formula_version=FORMULA_VERSION,
    )


# --------------------------------------------------------------------------
# get_loan_history
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class LoanHistoryEntry:
    reporting_period_ending_date: date | None
    payment_status_code: str | None
    actual_balance_amount: Decimal | None
    scheduled_balance_amount: Decimal | None
    advances_outstanding_amount: Decimal | None
    source: SourceRef


@dataclass(frozen=True)
class LoanHistory:
    loan_asset_number: str
    entries: tuple[LoanHistoryEntry, ...]
    formula_version: str


def get_loan_history(asset_number: str, loan_snapshots: tuple[Loan, ...]) -> LoanHistory:
    matching = tuple(loan for loan in loan_snapshots if loan.asset_number == asset_number)
    matching = tuple(
        sorted(matching, key=lambda loan: loan.reporting_period.ending_date or date.min)
    )
    entries = tuple(
        LoanHistoryEntry(
            reporting_period_ending_date=loan.reporting_period.ending_date,
            payment_status_code=loan.payment_status_code,
            actual_balance_amount=loan.actual_balance_amount,
            scheduled_balance_amount=loan.scheduled_balance_amount,
            advances_outstanding_amount=_advances_outstanding(loan),
            source=loan.source,
        )
        for loan in matching
    )
    return LoanHistory(
        loan_asset_number=asset_number, entries=entries, formula_version=FORMULA_VERSION
    )


# --------------------------------------------------------------------------
# get_property_profile - point-in-time, explicitly not a time series
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class PropertyProfile:
    property_name: str
    loan_asset_number: str
    at_securitization: PropertyAtSecuritization
    most_recent: PropertyMostRecent | None
    as_of_date: date | None
    formula_version: str
    source: SourceRef
    note: str


_PROPERTY_PROFILE_NOTE = (
    "Point-in-time profile, not a time series. Property-level financials on "
    "this deal do not vary meaningfully period-to-period (measured 2026-08-28, "
    "design.md section 0) - use rank_loans_by_status_change or "
    "rank_loans_by_balance_drift for surveillance signal."
)


def get_property_profile(
    *, asset_number: str, property_name: str, loans: tuple[Loan, ...]
) -> PropertyProfile | None:
    loan = next((loan for loan in loans if loan.asset_number == asset_number), None)
    if loan is None:
        return None
    prop = next((p for p in loan.properties if p.property_name == property_name), None)
    if prop is None:
        return None
    return PropertyProfile(
        property_name=prop.property_name,
        loan_asset_number=asset_number,
        at_securitization=prop.at_securitization,
        most_recent=prop.most_recent,
        as_of_date=loan.reporting_period.ending_date,
        formula_version=FORMULA_VERSION,
        source=loan.source,
        note=_PROPERTY_PROFILE_NOTE,
    )


# --------------------------------------------------------------------------
# rank_properties_by_noi_change - the "no fabricated ordering" guarantee
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class PropertyNoiChangeEntry:
    loan_asset_number: str
    property_name: str
    noi_before: Decimal
    noi_after: Decimal
    change_amount: Decimal


@dataclass(frozen=True)
class PropertyNoiChangeRanking:
    entries: tuple[PropertyNoiChangeEntry, ...]
    excluded_null_to_value_count: int
    reason: str
    formula_version: str


def rank_properties_by_noi_change(
    loans_a: tuple[Loan, ...], loans_b: tuple[Loan, ...]
) -> PropertyNoiChangeRanking:
    by_asset_a = {loan.asset_number: loan for loan in loans_a}
    entries: list[PropertyNoiChangeEntry] = []
    excluded_null_to_value = 0

    for loan_b in loans_b:
        loan_a = by_asset_a.get(loan_b.asset_number)
        if loan_a is None:
            continue
        properties_a = {p.property_name: p for p in loan_a.properties}
        for prop_b in loan_b.properties:
            prop_a = properties_a.get(prop_b.property_name)
            if prop_a is None:
                continue
            noi_a = prop_a.most_recent.net_operating_income_amount if prop_a.most_recent else None
            noi_b = prop_b.most_recent.net_operating_income_amount if prop_b.most_recent else None
            if noi_a is None and noi_b is not None:
                excluded_null_to_value += 1
                continue
            if noi_a is None or noi_b is None or noi_a == noi_b:
                continue
            entries.append(
                PropertyNoiChangeEntry(
                    loan_asset_number=loan_b.asset_number,
                    property_name=prop_b.property_name,
                    noi_before=noi_a,
                    noi_after=noi_b,
                    change_amount=noi_b - noi_a,
                )
            )

    entries.sort(key=lambda e: (e.change_amount, e.loan_asset_number))  # most negative first
    if entries:
        reason = f"{len(entries)} propert(y/ies) with a genuine mostRecent NOI change."
    else:
        reason = (
            f"No property recorded a genuine NOI change between these periods. "
            f"{excluded_null_to_value} apparent change(s) were null-to-first-reported-value "
            f"and were excluded, not ranked as deterioration."
        )

    return PropertyNoiChangeRanking(
        entries=tuple(entries),
        excluded_null_to_value_count=excluded_null_to_value,
        reason=reason,
        formula_version=FORMULA_VERSION,
    )
