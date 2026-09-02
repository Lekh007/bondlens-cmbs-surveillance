"""Ingest typed CMBS monthly-report data from Exhibit 99.1.

ABS-EE supplies the authoritative loan and property records. A 10-D's
Exhibit 99.1 supplies the complementary certificate-side report: tranches,
distributions, and collateral-to-certificate reconciliation. Keeping this
as a separate ingestion path prevents callers from silently treating a
certificate balance as a loan-pool balance.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date

from vichara_portfolio.bondlens.adapters.exhibit_99_1 import parse_exhibit_99_1
from vichara_portfolio.bondlens.domain import ParsedMonthlyReport
from vichara_portfolio.bondlens.ports import FilingStorePort, SecEdgarPort
from vichara_portfolio.shared.provenance import SourceRef

_REPORT_EXHIBIT_TYPE = "EX-99.1"
_HTML_CONTENT_TYPES = ("text/html", "application/xhtml+xml", "text/plain")
DEFAULT_MAX_FILINGS = 8


@dataclass(frozen=True)
class IngestedMonthlyReport:
    accession_number: str
    report_date: date | None
    report: ParsedMonthlyReport
    source: SourceRef


@dataclass(frozen=True)
class MonthlyReportIngestResult:
    reports: tuple[IngestedMonthlyReport, ...]
    skipped: tuple[str, ...]
    failed: tuple[str, ...]


def ingest_monthly_reports(
    *,
    cik: str,
    sec: SecEdgarPort,
    filing_store: FilingStorePort,
    max_filings: int = DEFAULT_MAX_FILINGS,
) -> MonthlyReportIngestResult:
    """Fetch recent 10-D Exhibit 99.1 reports and return typed report data.

    A bad report is isolated to its own accession. The caller still receives
    the remaining valid periods, plus an explicit failure record rather than
    an incomplete dataset that looks successful.
    """
    submissions = sec.list_filings(cik, forms=("10-D",))
    recent = tuple(reversed(submissions.filings))[:max_filings]
    reports: list[IngestedMonthlyReport] = []
    skipped: list[str] = []
    failed: list[str] = []

    for filing in recent:
        accession = filing.accession_number
        try:
            documents, _ = filing_store.list_documents(cik=cik, accession=accession)
            exhibit = next(
                (doc for doc in documents if doc.filing_type == _REPORT_EXHIBIT_TYPE), None
            )
            if exhibit is None:
                skipped.append(f"{accession}: no {_REPORT_EXHIBIT_TYPE} exhibit")
                continue
            stored, source = filing_store.download(
                exhibit, accession=accession, allowed_content_types=_HTML_CONTENT_TYPES
            )
            report_source = replace(source, record_id=accession, field_path="exhibit_99_1")
            report = parse_exhibit_99_1(stored.path.read_bytes(), source=report_source)
            reports.append(
                IngestedMonthlyReport(
                    accession_number=accession,
                    report_date=filing.report_date,
                    report=report,
                    source=report_source,
                )
            )
        except Exception as exc:  # one corrupt issuer report must not suppress other periods
            failed.append(f"{accession}: {exc}")

    reports.sort(key=lambda item: item.report_date or date.min)
    return MonthlyReportIngestResult(
        reports=tuple(reports), skipped=tuple(skipped), failed=tuple(failed)
    )
