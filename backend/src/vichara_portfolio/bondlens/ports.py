"""Ports the BondLens service depends on. Adapters implement these; tests
replace them with fakes so unit/contract tests never touch SEC, Postgres,
or FAISS.
"""

from __future__ import annotations

from typing import Protocol

from vichara_portfolio.bondlens.domain import SubmissionsResult


class SecEdgarPort(Protocol):
    def list_filings(
        self, cik: str, *, forms: tuple[str, ...] | None = None
    ) -> SubmissionsResult: ...
