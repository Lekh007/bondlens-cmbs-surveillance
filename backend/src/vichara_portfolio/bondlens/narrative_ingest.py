"""Ingest narrative filings (10-D distribution reports, 8-K events) into a
local FAISS index, so the agent's retrieval path has a real corpus to
answer from.

Why this exists as its own step: the ABS-EE exhibits ingested by
service.py are *structured* asset data - loan and property rows - which
the deterministic analytics tools read directly. They contain no prose.
Questions like "why did loan 30 go delinquent" or "what did the servicer
report this month" can only be answered from the narrative documents SEC
files alongside them, and those need chunking + embedding + vector search
rather than a typed query.

Retrieval is deliberately additive, never authoritative: retrieved prose
enters the prompt as clearly-labelled untrusted evidence (agent.py
sanitizes it and the verifier still requires every number to trace to
deterministic tool output). A filing that says something wrong, or that
contains text shaped like an instruction, cannot move a number.
"""

from __future__ import annotations

from dataclasses import dataclass

from vichara_portfolio.bondlens.adapters.faiss_index import FaissVectorIndex
from vichara_portfolio.bondlens.adapters.filing_store import FilingStore
from vichara_portfolio.bondlens.adapters.sec_edgar import SecEdgarClient
from vichara_portfolio.bondlens.rag import EmptyDocumentError, chunk_filing_text
from vichara_portfolio.shared.provenance import SourceRef

# 10-D is the monthly distribution report for an ABS trust and 8-K carries
# material events - together they are the narrative record that sits
# alongside the ABS-EE asset data for the same deal.
NARRATIVE_FORMS = ("10-D", "8-K")
_HTML_CONTENT_TYPES = ("text/html", "application/xhtml+xml", "text/plain")
# Cap the corpus: this is a portfolio-scale local index, and each filing
# costs an embedding pass. The most recent filings are the relevant ones
# for surveillance questions.
DEFAULT_MAX_FILINGS = 8


@dataclass(frozen=True)
class NarrativeIngestResult:
    filings_indexed: int
    chunks_indexed: int
    skipped: tuple[str, ...]


def ingest_narrative_filings(
    *,
    cik: str,
    sec: SecEdgarClient,
    filing_store: FilingStore,
    index: FaissVectorIndex,
    forms: tuple[str, ...] = NARRATIVE_FORMS,
    max_filings: int = DEFAULT_MAX_FILINGS,
) -> NarrativeIngestResult:
    submissions = sec.list_filings(cik, forms=forms)
    # Most recent first - list_filings sorts ascending by filing_date.
    recent = tuple(reversed(submissions.filings))[:max_filings]

    filings_indexed = 0
    chunks_indexed = 0
    skipped: list[str] = []

    for filing in recent:
        accession = filing.accession_number
        try:
            documents, _ = filing_store.list_documents(cik=cik, accession=accession)
        except Exception as exc:  # a single unreadable filing must not abort the corpus
            skipped.append(f"{accession}: {exc}")
            continue

        primary = next(
            (d for d in documents if d.filename == filing.primary_document),
            None,
        ) or next((d for d in documents if d.filename.lower().endswith(".htm")), None)
        if primary is None:
            skipped.append(f"{accession}: no HTML primary document")
            continue

        try:
            stored, source = filing_store.download(
                primary, accession=accession, allowed_content_types=_HTML_CONTENT_TYPES
            )
            html = stored.path.read_bytes().decode("utf-8", errors="replace")
            chunks = chunk_filing_text(html, accession_number=accession)
        except EmptyDocumentError as exc:
            skipped.append(f"{accession}: {exc}")
            continue
        except Exception as exc:
            skipped.append(f"{accession}: {exc}")
            continue

        source_by_accession: dict[str, SourceRef] = {accession: source}
        index.upsert_chunks(chunks, source_by_accession=source_by_accession)
        filings_indexed += 1
        chunks_indexed += len(chunks)

    return NarrativeIngestResult(
        filings_indexed=filings_indexed,
        chunks_indexed=chunks_indexed,
        skipped=tuple(skipped),
    )
