"""Self-contained ingestion job body.

Takes only a CIK string and constructs every other dependency (Settings,
DB engine, SEC client, filing store) from scratch inside the function.
That makes it safe for RQ to pickle a reference to this function and
re-run it in a real worker process, not just call it inline - the job
does not close over any live object from the enqueuing process.
"""

from __future__ import annotations

from datetime import date

import httpx

from vichara_portfolio.bondlens.adapters.filing_store import FilingStore
from vichara_portfolio.bondlens.adapters.repository import BondLensRepository
from vichara_portfolio.bondlens.adapters.sec_edgar import SecEdgarClient
from vichara_portfolio.bondlens.deal_cache import DEAL_CACHE, DealCacheEntry
from vichara_portfolio.bondlens.domain import Deal
from vichara_portfolio.bondlens.service import BondLensService
from vichara_portfolio.settings import Settings
from vichara_portfolio.shared.db import make_engine, make_session_factory, session_scope
from vichara_portfolio.shared.http import ResilientHttpClient, SecRateLimiter
from vichara_portfolio.shared.storage import RawDocumentStore


def run_ingestion_job(cik: str) -> dict[str, object]:
    # sec_user_agent/jwt_secret are required fields with no static default,
    # resolved from .env at runtime - mypy can't see that, same pattern as
    # every other real (non-test) Settings() call in this codebase.
    settings = Settings()  # type: ignore[call-arg]

    http = ResilientHttpClient(
        httpx.Client(), source_name="sec_edgar", rate_limiter=SecRateLimiter()
    )
    sec = SecEdgarClient(http, user_agent=settings.sec_user_agent)
    raw_store = RawDocumentStore(raw_root=settings.raw_root)
    filing_store = FilingStore(http, raw_store, user_agent=settings.sec_user_agent)

    engine = make_engine(settings.database_url)
    session_factory = make_session_factory(engine)

    with session_scope(session_factory) as session:
        repository = BondLensRepository(session)
        service = BondLensService(sec, filing_store, repository)
        summary = service.ingest_deal(cik)

    successful = [o for o in summary.outcomes if o.status == "created" and o.loans]
    successful.sort(key=lambda outcome: outcome.report_date or date.min)

    loans_a = successful[-2].loans if len(successful) >= 2 else ()
    loans_b = successful[-1].loans if successful else ()

    DEAL_CACHE[cik] = DealCacheEntry(
        deal=Deal(cik=cik, name=summary.deal_name),
        loans_a=loans_a,
        loans_b=loans_b,
        filing_source=loans_b[0].source if loans_b else None,
    )

    return {
        "deal_name": summary.deal_name,
        "total_filings": summary.total_filings,
        "created_count": summary.created_count,
        "skipped_count": summary.skipped_count,
        "failed_count": summary.failed_count,
        "periods_with_data": len(successful),
    }
