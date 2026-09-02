"""Live compatibility checks across public CMBS Exhibit 99.1 layouts.

Run with:
    $env:EXTERNAL_NETWORK_ENABLED = 'true'
    uv run pytest -m live tests/contract/bondlens/test_exhibit_99_1_live.py -q
"""

from pathlib import Path

import httpx
import pytest

from vichara_portfolio.bondlens.adapters.filing_store import FilingStore
from vichara_portfolio.bondlens.adapters.sec_edgar import SecEdgarClient
from vichara_portfolio.bondlens.monthly_report_ingest import ingest_monthly_reports
from vichara_portfolio.shared.http import ResilientHttpClient, SecRateLimiter
from vichara_portfolio.shared.storage import RawDocumentStore

TEST_USER_AGENT = "BondLens-Live-Validation/0.1 (kasarlekhraj@gmail.com)"


@pytest.mark.live
@pytest.mark.parametrize(
    ("cik", "deal_name", "expects_reconciliation"),
    (
        ("0002110410", "Benchmark 2026-B42", True),
        ("0002006440", "BMO 2024-5C3", True),
        ("0002109998", "Benchmark 2026-V21", True),
        ("0002061838", "BMO 2025-C13", False),
        ("0001617959", "COMM 2014-UBS5", True),
    ),
)
def test_latest_monthly_report_parses_for_multiple_public_cmbs_deals(
    tmp_path: Path, cik: str, deal_name: str, expects_reconciliation: bool
) -> None:
    """Each issuer's latest report must yield real certificate data.

    BMO 2025-C13 intentionally has no standard bond/collateral reconciliation
    table. Its Citigroup distribution-summary layout is still expected to
    produce certificate classes and CUSIPs.
    """
    http = ResilientHttpClient(
        httpx.Client(), source_name="sec_edgar", rate_limiter=SecRateLimiter()
    )
    sec = SecEdgarClient(http, user_agent=TEST_USER_AGENT)
    filing_store = FilingStore(
        http, RawDocumentStore(raw_root=tmp_path / cik), user_agent=TEST_USER_AGENT
    )

    result = ingest_monthly_reports(
        cik=cik, sec=sec, filing_store=filing_store, max_filings=1
    )

    assert result.failed == (), f"{deal_name}: {result.failed}"
    assert len(result.reports) == 1, f"{deal_name}: {result.skipped}"
    report = result.reports[0].report
    assert report.certificate_distributions, f"{deal_name}: no certificate classes parsed"
    assert (report.reconciliation is not None) is expects_reconciliation
