"""In-process cache of the most recent ingestion per deal, keyed by CIK.

Serves reads (deal summary, compare, chat) without a second round of SEC
calls or a Postgres read-repository. The read-repository (reconstructing
Loan/PropertySnapshot from the persisted JSONB rows) is the intended
long-term design - see the note on FilingIngestOutcome.loans in
service.py. This cache is an explicit, disclosed MVP simplification: it
lives only in this process's memory, is lost on restart, and is not
shared with a separately deployed RQ worker process. Real SEC data still
flows through it - it just isn't durable or cross-process yet.
"""

from __future__ import annotations

from dataclasses import dataclass

from vichara_portfolio.bondlens.domain import Deal, Loan
from vichara_portfolio.shared.provenance import SourceRef


@dataclass(frozen=True)
class DealCacheEntry:
    deal: Deal
    loans_a: tuple[Loan, ...]
    loans_b: tuple[Loan, ...]
    filing_source: SourceRef | None


DEAL_CACHE: dict[str, DealCacheEntry] = {}
