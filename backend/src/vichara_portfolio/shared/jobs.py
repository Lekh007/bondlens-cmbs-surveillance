"""Background ingestion job envelope.

Domain-specific on purpose (enqueue_ingestion(cik), not a generic task
queue) - this MVP has exactly one job type, and a generic envelope would
be premature abstraction for a single use.

Two implementations of the same JobQueuePort:
  - InMemoryJobQueue: runs the job body synchronously, inline, in-process.
    No Redis - used by every test (deterministic, no worker to race).
  - RQJobQueue: real rq.Queue over Redis, referencing
    bondlens.ingestion_job.run_ingestion_job by import path (picklable,
    re-importable in a real worker process). For this single-process MVP
    it also drains the job inline via rq.SimpleWorker(burst=True) right
    after enqueueing, so the API process's in-memory DealCache
    (bondlens/deal_cache.py) stays consistent with what was just
    ingested. A real deployed worker (Task 29's compose `worker` service)
    can consume the same queue name later without changing this class;
    cross-process cache consistency is the deferred read-repository work
    noted on FilingIngestOutcome.loans in bondlens/service.py.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol

from vichara_portfolio.bondlens.ingestion_job import run_ingestion_job

DEFAULT_QUEUE_NAME = "bondlens-ingestion"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class JobError:
    category: str
    message: str


@dataclass
class JobRecord:
    job_id: str
    idempotency_key: str
    status: JobStatus
    correlation_id: str
    created_at: datetime
    updated_at: datetime
    progress: int = 0
    error: JobError | None = None
    result: object | None = None


class JobQueuePort(Protocol):
    def enqueue_ingestion(self, cik: str, *, idempotency_key: str) -> JobRecord: ...

    def get_job(self, job_id: str) -> JobRecord | None: ...


def _new_job(idempotency_key: str) -> JobRecord:
    now = datetime.now(UTC)
    return JobRecord(
        job_id=str(uuid.uuid4()),
        idempotency_key=idempotency_key,
        status=JobStatus.QUEUED,
        correlation_id=str(uuid.uuid4()),
        created_at=now,
        updated_at=now,
    )


def _existing_active_job(
    jobs: dict[str, JobRecord], by_key: dict[str, str], idempotency_key: str
) -> JobRecord | None:
    job_id = by_key.get(idempotency_key)
    if job_id is None:
        return None
    existing = jobs[job_id]
    if existing.status in (JobStatus.QUEUED, JobStatus.RUNNING):
        return existing
    return None


@dataclass
class InMemoryJobQueue:
    """run defaults to the real ingestion job body, but tests inject a fake
    (e.g. a stub that returns a canned result or raises) so the fake-ports
    contract tests never touch SEC, Postgres, or the model provider."""

    run: Callable[[str], object] = run_ingestion_job
    jobs: dict[str, JobRecord] = field(default_factory=dict)
    _by_idempotency_key: dict[str, str] = field(default_factory=dict)

    def enqueue_ingestion(self, cik: str, *, idempotency_key: str) -> JobRecord:
        existing = _existing_active_job(self.jobs, self._by_idempotency_key, idempotency_key)
        if existing is not None:
            return existing

        job = _new_job(idempotency_key)
        self.jobs[job.job_id] = job
        self._by_idempotency_key[idempotency_key] = job.job_id

        job.status = JobStatus.RUNNING
        job.updated_at = datetime.now(UTC)
        try:
            job.result = self.run(cik)
            job.status = JobStatus.COMPLETED
            job.progress = 100
        except Exception as exc:  # noqa: BLE001 - job errors are data, not a crash
            job.status = JobStatus.FAILED
            job.error = JobError(category=type(exc).__name__, message=str(exc))
        job.updated_at = datetime.now(UTC)
        return job

    def get_job(self, job_id: str) -> JobRecord | None:
        return self.jobs.get(job_id)


@dataclass
class RQJobQueue:
    redis_url: str
    queue_name: str = DEFAULT_QUEUE_NAME
    jobs: dict[str, JobRecord] = field(default_factory=dict)
    _by_idempotency_key: dict[str, str] = field(default_factory=dict)

    def enqueue_ingestion(self, cik: str, *, idempotency_key: str) -> JobRecord:
        existing = _existing_active_job(self.jobs, self._by_idempotency_key, idempotency_key)
        if existing is not None:
            return existing

        from redis import Redis
        from rq import Queue, SimpleWorker

        job = _new_job(idempotency_key)
        self.jobs[job.job_id] = job
        self._by_idempotency_key[idempotency_key] = job.job_id
        job.status = JobStatus.RUNNING
        job.updated_at = datetime.now(UTC)

        connection = Redis.from_url(self.redis_url)
        queue = Queue(self.queue_name, connection=connection)
        rq_job = queue.enqueue(run_ingestion_job, cik)
        # SimpleWorker.work() installs SIGINT/SIGTERM handlers, which only
        # works on the main thread - but FastAPI runs sync endpoints in a
        # worker thread (measured: ValueError from signal.signal there).
        # perform_job() is the same per-job execution work() calls
        # internally, without its main-loop/signal setup.
        worker = SimpleWorker([queue], connection=connection)
        worker.perform_job(rq_job, queue)
        rq_job.refresh()  # type: ignore[no-untyped-call]  # rq's own stub, not ours

        if rq_job.is_finished:
            job.status = JobStatus.COMPLETED
            job.progress = 100
            job.result = rq_job.result
        else:
            job.status = JobStatus.FAILED
            job.error = JobError(
                category="JobExecutionError",
                message=str(rq_job.exc_info or "ingestion job did not complete"),
            )
        job.updated_at = datetime.now(UTC)
        return job

    def get_job(self, job_id: str) -> JobRecord | None:
        return self.jobs.get(job_id)
