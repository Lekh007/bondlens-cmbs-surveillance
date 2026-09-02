from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from vichara_portfolio.bondlens.adapters.filing_store import FilingDocument
from vichara_portfolio.bondlens.domain import SecFiling, SubmissionsResult
from vichara_portfolio.bondlens.monthly_report_ingest import ingest_monthly_reports
from vichara_portfolio.shared.provenance import SourceRef
from vichara_portfolio.shared.storage import StoredDocument

_REPORT = """
<table><tr><td>Certificate Distribution Detail</td></tr>
<tr><td>Class</td><td>CUSIP</td><td>Pass-Through Rate</td><td>Original Balance</td>
<td>Beginning Balance</td></tr>
<tr><td>A-1</td><td>08164FAA9</td><td>4.216170%</td><td>8,602,000.00</td><td>7,890,836.42</td>
<td>166,693.42</td><td>27,724.26</td><td>0.00</td><td>0.00</td><td>194,417.68</td>
<td>7,724,143.00</td><td>30.04%</td><td>30.00%</td></tr></table>
"""


def _source(label: str) -> SourceRef:
    return SourceRef(
        source_name="sec_edgar",
        source_url=f"https://www.sec.gov/{label}",
        retrieved_at=datetime(2026, 9, 2, 12, 0, tzinfo=UTC),
    )


@dataclass
class _Sec:
    def list_filings(self, cik: str, *, forms: tuple[str, ...] | None = None) -> SubmissionsResult:
        filing = SecFiling(
            cik=cik,
            accession_number="0001888524-26-016277",
            form_type="10-D",
            filing_date=date(2026, 8, 31),
            report_date=date(2026, 8, 17),
            primary_document="bmk26b42_10d-202608.htm",
        )
        return SubmissionsResult(
            entity_name="Benchmark 2026-B42 Mortgage Trust",
            filings=(filing,),
            source=_source("submissions"),
        )


class _Store:
    def __init__(self, path: Path) -> None:
        self._path = path

    def list_documents(self, *, cik: str, accession: str):
        return (
            (FilingDocument("EX-99.1", "bmk26b42_ex991-202608.htm", "https://www.sec.gov/ex991"),),
            _source("header"),
        )

    def download(
        self, document: FilingDocument, *, accession: str, allowed_content_types: tuple[str, ...]
    ):
        self._path.write_text(_REPORT, encoding="utf-8")
        return (
            StoredDocument(
                source="sec",
                checksum="fixture",
                path=self._path,
                size=len(_REPORT),
                already_cached=False,
            ),
            _source("ex991"),
        )


def test_ingests_the_latest_exhibit_99_1_as_typed_certificate_data(tmp_path: Path) -> None:
    result = ingest_monthly_reports(
        cik="0002110410", sec=_Sec(), filing_store=_Store(tmp_path / "report.html")
    )

    assert result.failed == ()
    assert len(result.reports) == 1
    latest = result.reports[0]
    assert latest.report_date == date(2026, 8, 17)
    assert latest.report.certificate_distributions[0].class_name == "A-1"
