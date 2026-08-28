"""Resolve which documents exist within an SEC filing accession, and
download them into content-addressed immutable storage.

Resolution goes through the full <accession>.txt submission header, never
index.json. Measured 2026-08-28: for the May, April, and June ABS-EE
accessions on Benchmark 2026-B42, index.json lists only the ABS-EE cover
.htm and omits exh_102.xml entirely - although the file exists and
returns HTTP 200. The .txt header's <TYPE>/<FILENAME> pairs are correct
for all five filings. A resolver trusting index.json finds zero assets
for three of five periods and looks like a parser bug.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from vichara_portfolio.shared.http import ResilientHttpClient
from vichara_portfolio.shared.provenance import SourceRef
from vichara_portfolio.shared.storage import RawDocumentStore, StoredDocument

ALLOWED_HOST = "www.sec.gov"

# Matches each <DOCUMENT> block's <TYPE> and <FILENAME> lines. <SEQUENCE> is
# optional between them (present in real filings, absent in some minimal
# fixtures) - we only need the type/filename pair to build a download URL.
_DOCUMENT_HEADER_PATTERN = re.compile(
    r"^<TYPE>(?P<type>\S+)\r?\n(?:<SEQUENCE>.*\r?\n)?<FILENAME>(?P<filename>\S+)",
    re.MULTILINE,
)


@dataclass(frozen=True)
class FilingDocument:
    filing_type: str
    filename: str
    url: str


class ExhibitResolutionError(Exception):
    """A document list could not be parsed, or a resolved link failed
    host/path validation. Never silently skipped."""


def build_accession_txt_url(cik: str, accession: str) -> str:
    unpadded_cik = cik.lstrip("0") or "0"
    accession_no_hyphens = accession.replace("-", "")
    return (
        f"https://www.sec.gov/Archives/edgar/data/{unpadded_cik}/"
        f"{accession_no_hyphens}/{accession}.txt"
    )


def build_exhibit_url(cik: str, accession: str, filename: str) -> str:
    unpadded_cik = cik.lstrip("0") or "0"
    accession_no_hyphens = accession.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{unpadded_cik}/{accession_no_hyphens}/{filename}"


def parse_document_index(
    txt_content: str, *, cik: str, accession: str
) -> tuple[FilingDocument, ...]:
    matches = _DOCUMENT_HEADER_PATTERN.findall(txt_content)
    if not matches:
        raise ExhibitResolutionError(
            f"no <TYPE>/<FILENAME> pairs found in submission header for {accession}"
        )

    documents = []
    seen_filenames: set[str] = set()
    for filing_type, filename in matches:
        if filename in seen_filenames:
            continue
        seen_filenames.add(filename)
        documents.append(
            FilingDocument(
                filing_type=filing_type,
                filename=filename,
                url=build_exhibit_url(cik, accession, filename),
            )
        )
    return tuple(documents)


def _validate_url(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc != ALLOWED_HOST:
        raise ExhibitResolutionError(f"refusing non-SEC URL: {url}")
    if ".." in parsed.path.split("/"):
        raise ExhibitResolutionError(f"refusing path traversal: {url}")


class FilingStore:
    def __init__(
        self, http: ResilientHttpClient, store: RawDocumentStore, *, user_agent: str
    ) -> None:
        self._http = http
        self._store = store
        self._user_agent = user_agent

    def list_documents(
        self, *, cik: str, accession: str
    ) -> tuple[tuple[FilingDocument, ...], SourceRef]:
        url = build_accession_txt_url(cik, accession)
        _validate_url(url)
        result = self._http.get_bytes(
            url,
            headers={"User-Agent": self._user_agent},
            allowed_content_types=("text/plain",),
            record_id=accession,
            immutable=True,
        )
        text = result.payload.decode("utf-8", errors="replace")
        documents = parse_document_index(text, cik=cik, accession=accession)
        return documents, result.source

    def download(
        self,
        document: FilingDocument,
        *,
        accession: str,
        allowed_content_types: tuple[str, ...],
    ) -> tuple[StoredDocument, SourceRef]:
        _validate_url(document.url)
        result = self._http.get_bytes(
            document.url,
            headers={"User-Agent": self._user_agent},
            allowed_content_types=allowed_content_types,
            record_id=accession,
            immutable=True,
        )
        stored = self._store.write(
            source="sec", filename=document.filename, content=result.payload
        )
        return stored, result.source
