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
