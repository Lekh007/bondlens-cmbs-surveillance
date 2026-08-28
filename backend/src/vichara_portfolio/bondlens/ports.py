"""Ports the BondLens service depends on. Adapters implement these; tests
replace them with fakes so unit/contract tests never touch SEC, Postgres,
or FAISS.
"""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import TYPE_CHECKING, Protocol

from vichara_portfolio.bondlens.domain import Deal, ParsedAssetData, SecFiling, SubmissionsResult
from vichara_portfolio.shared.provenance import SourceRef

if TYPE_CHECKING:
    from pathlib import Path

    from vichara_portfolio.bondlens.adapters.faiss_index import SearchResult
    from vichara_portfolio.bondlens.adapters.filing_store import FilingDocument
    from vichara_portfolio.bondlens.rag import Chunk
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

    def savepoint(self) -> AbstractContextManager[None]:
        """One atomic unit of work. Real implementations wrap a DB
        SAVEPOINT so a failure partway through one filing's writes (in a
        multi-filing ingest sharing one session/transaction) rolls back
        only that filing, not every filing already committed in this run -
        Postgres otherwise poisons the whole transaction until an explicit
        rollback (measured 2026-08-28: a mid-loop failure cascaded
        PendingRollbackError onto every subsequent filing)."""
        ...


class VectorIndexPort(Protocol):
    def upsert_chunks(
        self, chunks: tuple[Chunk, ...], *, source_by_accession: dict[str, SourceRef]
    ) -> None: ...

    def search(self, query: str, *, top_k: int = 5) -> tuple[SearchResult, ...]: ...

    def delete_document(self, accession_number: str) -> int: ...

    def persist(self, path: Path) -> None: ...

    def load(self, path: Path) -> None: ...
