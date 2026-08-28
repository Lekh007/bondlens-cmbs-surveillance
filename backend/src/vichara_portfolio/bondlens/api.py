"""BondLens FastAPI router. Handlers stay thin: they translate HTTP <->
typed request/response models and delegate everything else to
analytics.py, agent.py, deal_cache.py, and shared/jobs.py.

Only /chat depends on a language model, and only /chat returns a
controlled 503 when the model is unavailable - the deterministic
endpoints (summary, compare) never touch the model provider at all.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from vichara_portfolio.bondlens.agent import build_agent_graph
from vichara_portfolio.bondlens.analytics import compare_reporting_periods, get_deal_summary
from vichara_portfolio.bondlens.deal_cache import DEAL_CACHE
from vichara_portfolio.model_gateway.ports import ModelProvider
from vichara_portfolio.shared.jobs import JobQueuePort, JobRecord, JobStatus

router = APIRouter()


# --------------------------------------------------------------------------
# Request/response models
# --------------------------------------------------------------------------


class IngestionRequest(BaseModel):
    cik: str
    idempotency_key: str | None = None


class JobErrorResponse(BaseModel):
    category: str
    message: str


class IngestionJobResponse(BaseModel):
    job_id: str
    idempotency_key: str
    status: str
    progress: int
    error: JobErrorResponse | None = None
    result: dict[str, object] | None = None


class DealListItem(BaseModel):
    cik: str
    name: str


class DealSummaryResponse(BaseModel):
    cik: str
    name: str
    loan_count: int
    property_count: int
    total_original_loan_amount: str
    total_actual_balance_amount: str
    reporting_period_ending_date: str | None
    source_url: str


class LoanFieldChangeItem(BaseModel):
    loan_asset_number: str
    field_name: str
    before_value: str | None
    after_value: str | None


class CompareResponse(BaseModel):
    period_a_ending_date: str | None
    period_b_ending_date: str | None
    changes: list[LoanFieldChangeItem]


class ChatRequest(BaseModel):
    deal_id: str
    question: str


class CitationItem(BaseModel):
    source_name: str
    source_url: str
    record_id: str | None
    field_path: str | None


class ChatResponse(BaseModel):
    answer: str
    citations: list[CitationItem]
    verification_passed: bool


# --------------------------------------------------------------------------
# Ingestion
# --------------------------------------------------------------------------


@router.post("/api/bondlens/ingestions", response_model=IngestionJobResponse, status_code=202)
def create_ingestion(body: IngestionRequest, request: Request) -> IngestionJobResponse:
    job_queue: JobQueuePort = request.app.state.job_queue
    idempotency_key = body.idempotency_key or body.cik
    job = job_queue.enqueue_ingestion(body.cik, idempotency_key=idempotency_key)
    return _to_job_response(job)


@router.get("/api/bondlens/ingestions/{job_id}", response_model=IngestionJobResponse)
def get_ingestion(job_id: str, request: Request) -> IngestionJobResponse:
    job_queue: JobQueuePort = request.app.state.job_queue
    job = job_queue.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"no job with id {job_id}")
    return _to_job_response(job)


def _to_job_response(job: JobRecord) -> IngestionJobResponse:
    return IngestionJobResponse(
        job_id=job.job_id,
        idempotency_key=job.idempotency_key,
        status=job.status.value if isinstance(job.status, JobStatus) else str(job.status),
        progress=job.progress,
        error=JobErrorResponse(category=job.error.category, message=job.error.message)
        if job.error
        else None,
        result=job.result if isinstance(job.result, dict) else None,
    )


# --------------------------------------------------------------------------
# Deals
# --------------------------------------------------------------------------


@router.get("/api/bondlens/deals", response_model=list[DealListItem])
def list_deals() -> list[DealListItem]:
    return [DealListItem(cik=cik, name=entry.deal.name) for cik, entry in DEAL_CACHE.items()]


@router.get("/api/bondlens/deals/{deal_id}/summary", response_model=DealSummaryResponse)
def deal_summary(deal_id: str) -> DealSummaryResponse:
    entry = DEAL_CACHE.get(deal_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"deal {deal_id} has not been ingested")

    loans = entry.loans_b or entry.loans_a
    if not loans or entry.filing_source is None:
        raise HTTPException(
            status_code=422, detail=f"deal {deal_id} was ingested but has no loan data yet"
        )

    summary = get_deal_summary(
        cik=entry.deal.cik, name=entry.deal.name, loans=loans, source=entry.filing_source
    )
    return DealSummaryResponse(
        cik=summary.cik,
        name=summary.name,
        loan_count=summary.loan_count,
        property_count=summary.property_count,
        total_original_loan_amount=str(summary.total_original_loan_amount),
        total_actual_balance_amount=str(summary.total_actual_balance_amount),
        reporting_period_ending_date=(
            summary.reporting_period_ending_date.isoformat()
            if summary.reporting_period_ending_date
            else None
        ),
        source_url=summary.source.source_url,
    )


@router.get("/api/bondlens/deals/{deal_id}/compare", response_model=CompareResponse)
def deal_compare(deal_id: str) -> CompareResponse:
    entry = DEAL_CACHE.get(deal_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"deal {deal_id} has not been ingested")

    if not entry.loans_a or not entry.loans_b:
        raise HTTPException(
            status_code=422,
            detail=f"deal {deal_id} does not have two reporting periods to compare yet",
        )

    comparison = compare_reporting_periods(entry.loans_a, entry.loans_b)
    return CompareResponse(
        period_a_ending_date=(
            comparison.period_a_ending_date.isoformat() if comparison.period_a_ending_date else None
        ),
        period_b_ending_date=(
            comparison.period_b_ending_date.isoformat() if comparison.period_b_ending_date else None
        ),
        changes=[
            LoanFieldChangeItem(
                loan_asset_number=c.loan_asset_number,
                field_name=c.field_name,
                before_value=c.before_value,
                after_value=c.after_value,
            )
            for c in comparison.changes
        ],
    )


# --------------------------------------------------------------------------
# Chat - the only endpoint that touches the model provider
# --------------------------------------------------------------------------


@router.post("/api/bondlens/chat", response_model=ChatResponse)
def chat(body: ChatRequest, request: Request) -> ChatResponse:
    model: ModelProvider = request.app.state.model_provider
    if not model.health():
        raise HTTPException(status_code=503, detail="model provider is unavailable")

    entry = DEAL_CACHE.get(body.deal_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"deal {body.deal_id} has not been ingested")

    graph = build_agent_graph(
        model=model,
        deal=entry.deal,
        loans_a=entry.loans_a,
        loans_b=entry.loans_b,
        filing_source=entry.filing_source,
    )
    result = graph.invoke({"question": body.question}, config={"recursion_limit": 10})

    return ChatResponse(
        answer=result.get("final_answer", ""),
        citations=[
            CitationItem(
                source_name=c.source_name,
                source_url=c.source_url,
                record_id=c.record_id,
                field_path=c.field_path,
            )
            for c in result.get("citations", [])
        ],
        verification_passed=not result.get("verification_errors"),
    )
