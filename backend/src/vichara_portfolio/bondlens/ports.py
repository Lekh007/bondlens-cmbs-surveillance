"""Ports the BondLens service depends on. Adapters implement these; tests
replace them with fakes so unit/contract tests never touch SEC, Postgres,
or FAISS.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from vichara_portfolio.bondlens.domain import Deal, ParsedAssetData, SecFiling, SubmissionsResult
from vichara_portfolio.shared.provenance import SourceRef

if TYPE_CHECKING:
    from vichara_portfolio.bondlens.adapters.filing_store import FilingDocument
    from vichara_portfolio.shared.storage import StoredDocument


class SecEdgarPort(Protocol):
    def list_filings(
        self, cik: str, *, forms: tuple[str, ...] | None = None
    ) -> SubmissionsResult: ...


class FilingStorePort(Protocol):
    def list_documents(
        self, *, cik: str, accession: str
    ) -> tuple[tuple[FilingDocument, ...], SourceRef]: ...

    def download(
        self,
        document: FilingDocument,
        *,
        accession: str,
        allowed_content_types: tuple[str, ...],
    ) -> tuple[StoredDocument, SourceRef]: ...


class RepositoryPort(Protocol):
    def upsert_deal(self, deal: Deal) -> None: ...

    def upsert_filing(self, filing: SecFiling) -> None: ...

    def upsert_source_document(self, source: SourceRef) -> int: ...

    def save_parsed_asset_data(
        self, *, accession_number: str, parsed: ParsedAssetData, source_document_id: int | None
    ) -> tuple[int, int]: ...
