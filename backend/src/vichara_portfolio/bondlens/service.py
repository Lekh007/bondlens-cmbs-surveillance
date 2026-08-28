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
from datetime import date

from vichara_portfolio.bondlens.adapters.abs_ee import parse_asset_data
from vichara_portfolio.bondlens.domain import Deal, Loan, ParsedAssetData, SecFiling
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
    report_date: date | None = None
    # Carries the freshly-parsed loans back to the caller so it can serve
    # reads (deal summary, compare, chat) without a second round of SEC
    # calls. This is an MVP simplification, not the final architecture:
    # the intended design is a repository read-path that reconstructs
    # Loan/PropertySnapshot from the persisted Postgres rows so reads work
    # across processes (a real RQ worker vs. the API process) and survive
    # a restart. Deferred - see docs/plans/design.md follow-ups.
    loans: tuple[Loan, ...] = ()


@dataclass(frozen=True)
class IngestSummary:
    deal_cik: str
    deal_name: str
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

        outcomes = tuple(self._ingest_one_filing(cik, filing) for filing in submissions.filings)
        created = sum(1 for o in outcomes if o.status == "created")
        skipped = sum(1 for o in outcomes if o.status == "skipped")
        failed = sum(1 for o in outcomes if o.status == "failed")

        return IngestSummary(
            deal_cik=cik,
            deal_name=submissions.entity_name,
            total_filings=len(submissions.filings),
            created_count=created,
            skipped_count=skipped,
            failed_count=failed,
            outcomes=outcomes,
        )

    def _ingest_one_filing(self, cik: str, filing: SecFiling) -> FilingIngestOutcome:
        accession_number = filing.accession_number
        report_date = filing.report_date
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
            # One filing's DB writes are one atomic unit. Without this, a
            # failure partway through poisons the shared session/
            # transaction for every filing still to come in this loop -
            # Postgres requires an explicit rollback before it accepts
            # another statement (measured 2026-08-28: a single bad filing
            # cascaded PendingRollbackError onto the whole ingest run).
            with self._repository.savepoint():
                self._repository.upsert_filing(filing)
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
            report_date=report_date,
            loans=parsed.loans,
        )
