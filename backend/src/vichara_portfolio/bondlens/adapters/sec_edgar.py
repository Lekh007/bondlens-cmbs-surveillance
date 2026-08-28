"""SEC EDGAR submissions discovery: which filings exist for a given CIK.

Uses data.sec.gov, not the EDGAR filer/submission UI APIs, per the design
doc's SEC access policy. Exhibit resolution (which document within a
filing to download) is a separate concern - see Task 7's filing_store,
which resolves from the full accession .txt submission header rather than
index.json (the latter silently omits exhibits for some periods; measured
2026-08-28 against this same deal).
"""

from __future__ import annotations

from datetime import date

from vichara_portfolio.bondlens.domain import SecFiling, SubmissionsResult
from vichara_portfolio.shared.http import ResilientHttpClient

SUBMISSIONS_URL_TEMPLATE = "https://data.sec.gov/submissions/CIK{cik}.json"
ACCESSION_LENGTH = 18  # 10-digit filer id + 2-digit year + 6-digit sequence, no hyphens


class SecEdgarClient:
    def __init__(self, http: ResilientHttpClient, *, user_agent: str) -> None:
        self._http = http
        self._user_agent = user_agent

    def list_filings(
        self, cik: str, *, forms: tuple[str, ...] | None = None
    ) -> SubmissionsResult:
        padded_cik = _pad_cik(cik)
        url = SUBMISSIONS_URL_TEMPLATE.format(cik=padded_cik)
        result = self._http.get_json(
            url, headers={"User-Agent": self._user_agent}, record_id=padded_cik
        )
        payload = result.payload

        filings = tuple(
            sorted(
                _parse_filings(padded_cik, payload["filings"]["recent"], forms=forms),
                key=lambda f: f.filing_date,
            )
        )
        return SubmissionsResult(
            entity_name=payload.get("name", ""), filings=filings, source=result.source
        )


def _pad_cik(cik: str) -> str:
    digits = cik.strip().lstrip("0") or "0"
    if not digits.isdigit():
        raise ValueError(f"CIK must be numeric, got {cik!r}")
    return cik.strip().zfill(10)


def _parse_filings(
    cik: str, recent: dict[str, list[str]], *, forms: tuple[str, ...] | None
) -> list[SecFiling]:
    count = len(recent["form"])
    report_dates = recent.get("reportDate", [""] * count)
    filings = []
    for i in range(count):
        form_type = recent["form"][i]
        if forms is not None and form_type not in forms:
            continue
        report_date_raw = report_dates[i] if i < len(report_dates) else ""
        filings.append(
            SecFiling(
                cik=cik,
                accession_number=_normalize_accession(recent["accessionNumber"][i]),
                form_type=form_type,
                filing_date=date.fromisoformat(recent["filingDate"][i]),
                report_date=date.fromisoformat(report_date_raw) if report_date_raw else None,
                primary_document=recent["primaryDocument"][i],
            )
        )
    return filings


def _normalize_accession(raw: str) -> str:
    digits = raw.replace("-", "")
    if len(digits) != ACCESSION_LENGTH:
        raise ValueError(f"unexpected accession number {raw!r}, expected {ACCESSION_LENGTH} digits")
    return f"{digits[:10]}-{digits[10:12]}-{digits[12:]}"
