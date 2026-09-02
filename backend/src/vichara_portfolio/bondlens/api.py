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
from vichara_portfolio.bondlens.analytics import (
    compare_reporting_periods,
    get_deal_summary,
    get_geography_distribution,
    get_property_type_distribution,
    rank_loans_by_balance_drift,
    rank_loans_by_status_change,
)
from vichara_portfolio.bondlens.deal_cache import DEAL_CACHE
from vichara_portfolio.bondlens.domain import Loan
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


class CertificateDistributionItem(BaseModel):
    class_name: str
    cusip: str
    pass_through_rate: str | None
    beginning_balance: str | None
    principal_distribution: str | None
    interest_distribution: str | None
    ending_balance: str | None
    source_url: str


class CertificateDistributionResponse(BaseModel):
    report_date: str | None
    source_url: str
    entries: list[CertificateDistributionItem]


class BondCollateralReconciliationResponse(BaseModel):
    report_date: str | None
    ending_scheduled_collateral_balance: str | None
    beginning_actual_collateral_balance: str | None
    ending_actual_collateral_balance: str | None
    beginning_certificate_balance: str | None
    ending_certificate_balance: str | None
    under_over_collateralization: str | None
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


class PropertyTypeEntryItem(BaseModel):
    property_type_code: str
    property_count: int


class PropertyTypeDistributionResponse(BaseModel):
    entries: list[PropertyTypeEntryItem]
    total_properties: int
    properties_missing_type: int


class GeographyEntryItem(BaseModel):
    state: str
    property_count: int


class GeographyDistributionResponse(BaseModel):
    entries: list[GeographyEntryItem]
    total_properties: int
    properties_missing_state: int


class StatusChangeEntryItem(BaseModel):
    loan_asset_number: str
    property_names: list[str]
    status_before: str | None
    status_after: str | None
    severity_rank: int


class StatusChangeRankingResponse(BaseModel):
    entries: list[StatusChangeEntryItem]
    period_a_ending_date: str | None
    period_b_ending_date: str | None


class BalanceDriftEntryItem(BaseModel):
    loan_asset_number: str
    property_names: list[str]
    actual_balance_amount: str
    scheduled_balance_amount: str
    drift_amount: str
    drift_percentage: str | None


class BalanceDriftRankingResponse(BaseModel):
    entries: list[BalanceDriftEntryItem]
    as_of_date: str | None


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


@router.get(
    "/api/bondlens/deals/{deal_id}/certificate-distributions",
    response_model=CertificateDistributionResponse,
)
def certificate_distributions(deal_id: str) -> CertificateDistributionResponse:
    entry = DEAL_CACHE.get(deal_id)
    if entry is None or entry.latest_monthly_report is None:
        raise HTTPException(
            status_code=404, detail=f"deal {deal_id} has no Exhibit 99.1 report yet"
        )
    monthly_report = entry.latest_monthly_report
    return CertificateDistributionResponse(
        report_date=monthly_report.report_date.isoformat() if monthly_report.report_date else None,
        source_url=monthly_report.source.source_url,
        entries=[
            CertificateDistributionItem(
                class_name=item.class_name,
                cusip=item.cusip,
                pass_through_rate=str(item.pass_through_rate)
                if item.pass_through_rate is not None
                else None,
                beginning_balance=str(item.beginning_balance)
                if item.beginning_balance is not None
                else None,
                principal_distribution=str(item.principal_distribution)
                if item.principal_distribution is not None
                else None,
                interest_distribution=str(item.interest_distribution)
                if item.interest_distribution is not None
                else None,
                ending_balance=str(item.ending_balance)
                if item.ending_balance is not None
                else None,
                source_url=item.source.source_url,
            )
            for item in monthly_report.report.certificate_distributions
        ],
    )


@router.get(
    "/api/bondlens/deals/{deal_id}/bond-collateral-reconciliation",
    response_model=BondCollateralReconciliationResponse,
)
def bond_collateral_reconciliation(deal_id: str) -> BondCollateralReconciliationResponse:
    entry = DEAL_CACHE.get(deal_id)
    if entry is None or entry.latest_monthly_report is None:
        raise HTTPException(
            status_code=404, detail=f"deal {deal_id} has no Exhibit 99.1 report yet"
        )
    monthly_report = entry.latest_monthly_report
    reconciliation = monthly_report.report.reconciliation
    if reconciliation is None:
        raise HTTPException(
            status_code=422, detail="Exhibit 99.1 has no balance reconciliation table"
        )
    return BondCollateralReconciliationResponse(
        report_date=monthly_report.report_date.isoformat() if monthly_report.report_date else None,
        ending_scheduled_collateral_balance=str(reconciliation.ending_scheduled_collateral_balance)
        if reconciliation.ending_scheduled_collateral_balance is not None
        else None,
        beginning_actual_collateral_balance=str(reconciliation.beginning_actual_collateral_balance)
        if reconciliation.beginning_actual_collateral_balance is not None
        else None,
        ending_actual_collateral_balance=str(reconciliation.ending_actual_collateral_balance)
        if reconciliation.ending_actual_collateral_balance is not None
        else None,
        beginning_certificate_balance=str(reconciliation.beginning_certificate_balance)
        if reconciliation.beginning_certificate_balance is not None
        else None,
        ending_certificate_balance=str(reconciliation.ending_certificate_balance)
        if reconciliation.ending_certificate_balance is not None
        else None,
        under_over_collateralization=str(reconciliation.under_over_collateralization)
        if reconciliation.under_over_collateralization is not None
        else None,
        source_url=reconciliation.source.source_url,
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
# Geography and property-type distribution - always derived from the
# latest ingested period (loans_b), since propertyState/propertyTypeCode
# are frozen-at-issuance fields that don't vary period to period.
# --------------------------------------------------------------------------


def _latest_loans_or_404(deal_id: str) -> tuple[Loan, ...]:
    entry = DEAL_CACHE.get(deal_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"deal {deal_id} has not been ingested")
    return entry.loans_b or entry.loans_a


@router.get("/api/bondlens/deals/{deal_id}/geography", response_model=GeographyDistributionResponse)
def deal_geography(deal_id: str) -> GeographyDistributionResponse:
    loans = _latest_loans_or_404(deal_id)
    dist = get_geography_distribution(loans)
    return GeographyDistributionResponse(
        entries=[
            GeographyEntryItem(state=e.state, property_count=e.property_count) for e in dist.entries
        ],
        total_properties=dist.total_properties,
        properties_missing_state=dist.properties_missing_state,
    )


@router.get(
    "/api/bondlens/deals/{deal_id}/property-types", response_model=PropertyTypeDistributionResponse
)
def deal_property_types(deal_id: str) -> PropertyTypeDistributionResponse:
    loans = _latest_loans_or_404(deal_id)
    dist = get_property_type_distribution(loans)
    return PropertyTypeDistributionResponse(
        entries=[
            PropertyTypeEntryItem(
                property_type_code=e.property_type_code, property_count=e.property_count
            )
            for e in dist.entries
        ],
        total_properties=dist.total_properties,
        properties_missing_type=dist.properties_missing_type,
    )


# --------------------------------------------------------------------------
# Status-change and balance-drift rankings
# --------------------------------------------------------------------------


@router.get(
    "/api/bondlens/deals/{deal_id}/status-changes", response_model=StatusChangeRankingResponse
)
def deal_status_changes(deal_id: str) -> StatusChangeRankingResponse:
    entry = DEAL_CACHE.get(deal_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"deal {deal_id} has not been ingested")
    if not entry.loans_a or not entry.loans_b:
        raise HTTPException(
            status_code=422,
            detail=f"deal {deal_id} does not have two reporting periods to compare yet",
        )

    ranking = rank_loans_by_status_change(entry.loans_a, entry.loans_b)
    return StatusChangeRankingResponse(
        entries=[
            StatusChangeEntryItem(
                loan_asset_number=e.loan_asset_number,
                property_names=list(e.property_names),
                status_before=e.status_before,
                status_after=e.status_after,
                severity_rank=e.severity_rank,
            )
            for e in ranking.entries
        ],
        period_a_ending_date=(
            ranking.period_a_ending_date.isoformat() if ranking.period_a_ending_date else None
        ),
        period_b_ending_date=(
            ranking.period_b_ending_date.isoformat() if ranking.period_b_ending_date else None
        ),
    )


@router.get(
    "/api/bondlens/deals/{deal_id}/balance-drift", response_model=BalanceDriftRankingResponse
)
def deal_balance_drift(deal_id: str) -> BalanceDriftRankingResponse:
    loans = _latest_loans_or_404(deal_id)
    ranking = rank_loans_by_balance_drift(loans)
    return BalanceDriftRankingResponse(
        entries=[
            BalanceDriftEntryItem(
                loan_asset_number=e.loan_asset_number,
                property_names=list(e.property_names),
                actual_balance_amount=str(e.actual_balance_amount),
                scheduled_balance_amount=str(e.scheduled_balance_amount),
                drift_amount=str(e.drift_amount),
                drift_percentage=str(e.drift_percentage)
                if e.drift_percentage is not None
                else None,
            )
            for e in ranking.entries
        ],
        as_of_date=ranking.as_of_date.isoformat() if ranking.as_of_date else None,
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
        # The narrative FAISS index built during ingestion. Omitting this
        # was a real bug: retrieval was implemented, unit-tested, and
        # completely inert in the running product because the graph was
        # built without it (found by review, 2026-08-29).
        vector_index=entry.vector_index,
        certificate_distributions=(
            entry.latest_monthly_report.report.certificate_distributions
            if entry.latest_monthly_report is not None
            else ()
        ),
        reconciliation=(
            entry.latest_monthly_report.report.reconciliation
            if entry.latest_monthly_report is not None
            else None
        ),
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
