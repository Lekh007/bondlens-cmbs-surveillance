"""BondLens ingestion orchestration.

Depends only on ports (SecEdgarPort, FilingStorePort, RepositoryPort), not
concrete SEC/Postgres adapters, so it is unit-testable with plain fakes.
Ingestion is idempotent (RepositoryPort.save_parsed_asset_data upserts on
natural keys) and reports created/skipped/failed counts per filing rather
than raising on the first failure.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from vichara_portfolio.bondlens.adapters.abs_ee import parse_asset_data
from vichara_portfolio.bondlens.domain import Deal, ParsedAssetData
from vichara_portfolio.bondlens.ports import FilingStorePort, RepositoryPort, SecEdgarPort

_ASSET_EXHIBIT_TYPE = "EX-102"
_ASSET_EXHIBIT_CONTENT_TYPES = ("text/xml", "application/xml")


@dataclass(frozen=True)
class FilingIngestOutcome:
    accession_number: str
    status: str  # "created" | "skipped" | "failed"
    reason: str | None = None
    loans_written: int = 0
    properties_written: int = 0


@dataclass(frozen=True)
class IngestSummary:
    deal_cik: str
    total_filings: int
    created_count: int
    skipped_count: int
    failed_count: int
    outcomes: tuple[FilingIngestOutcome, ...]


class BondLensService:
    def __init__(
        self,
        sec: SecEdgarPort,
        filing_store: FilingStorePort,
        repository: RepositoryPort,
        *,
        parse: Callable[..., ParsedAssetData] = parse_asset_data,
    ) -> None:
        self._sec = sec
        self._filing_store = filing_store
        self._repository = repository
        self._parse = parse

    def ingest_deal(self, cik: str, *, forms: tuple[str, ...] = ("ABS-EE",)) -> IngestSummary:
        submissions = self._sec.list_filings(cik, forms=forms)
        self._repository.upsert_deal(Deal(cik=cik, name=submissions.entity_name))

        outcomes = tuple(
            self._ingest_one_filing(cik, filing.accession_number) for filing in submissions.filings
        )
        created = sum(1 for o in outcomes if o.status == "created")
        skipped = sum(1 for o in outcomes if o.status == "skipped")
        failed = sum(1 for o in outcomes if o.status == "failed")

        return IngestSummary(
            deal_cik=cik,
            total_filings=len(submissions.filings),
            created_count=created,
            skipped_count=skipped,
            failed_count=failed,
            outcomes=outcomes,
        )

    def _ingest_one_filing(self, cik: str, accession_number: str) -> FilingIngestOutcome:
        try:
            documents, _list_source = self._filing_store.list_documents(
                cik=cik, accession=accession_number
            )
        except Exception as exc:
            return FilingIngestOutcome(accession_number, "failed", reason=str(exc))

        exhibit = next((d for d in documents if d.filing_type == _ASSET_EXHIBIT_TYPE), None)
        if exhibit is None:
            return FilingIngestOutcome(
                accession_number,
                "skipped",
                reason=f"no {_ASSET_EXHIBIT_TYPE} exhibit in this filing",
            )

        try:
            stored, exhibit_source = self._filing_store.download(
                exhibit,
                accession=accession_number,
                allowed_content_types=_ASSET_EXHIBIT_CONTENT_TYPES,
            )
            parsed = self._parse(stored.path.read_bytes(), source=exhibit_source)
            source_document_id = self._repository.upsert_source_document(exhibit_source)
            loans_written, properties_written = self._repository.save_parsed_asset_data(
                accession_number=accession_number,
                parsed=parsed,
                source_document_id=source_document_id,
            )
        except Exception as exc:
            return FilingIngestOutcome(accession_number, "failed", reason=str(exc))

        return FilingIngestOutcome(
            accession_number,
            "created",
            loans_written=loans_written,
            properties_written=properties_written,
        )
