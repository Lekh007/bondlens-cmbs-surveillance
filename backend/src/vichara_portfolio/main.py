"""FastAPI app factory.

create_app() defaults to real dependencies wired from Settings (RQJobQueue
over Redis, the model provider Settings.model_provider selects). Tests
override job_queue/model_provider with fakes - see
tests/integration/bondlens/test_api.py.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from sqlalchemy import text

from vichara_portfolio.bondlens.api import router as bondlens_router
from vichara_portfolio.model_gateway.deterministic import DeterministicProvider
from vichara_portfolio.model_gateway.ollama import OllamaProvider
from vichara_portfolio.model_gateway.ports import ModelProvider
from vichara_portfolio.settings import Settings
from vichara_portfolio.shared.db import make_engine
from vichara_portfolio.shared.jobs import JobQueuePort, RQJobQueue


def _default_model_provider(settings: Settings) -> ModelProvider:
    if settings.model_provider == "deterministic":
        return DeterministicProvider()
    return OllamaProvider(base_url=settings.ollama_base_url, model=settings.ollama_model)


def create_app(
    *,
    settings: Settings | None = None,
    job_queue: JobQueuePort | None = None,
    model_provider: ModelProvider | None = None,
) -> FastAPI:
    settings = settings or Settings()  # type: ignore[call-arg]  # resolved from .env at runtime
    app = FastAPI(title="Vichara BondLens API")

    app.state.settings = settings
    app.state.job_queue = job_queue or RQJobQueue(redis_url=settings.redis_url)
    app.state.model_provider = model_provider or _default_model_provider(settings)

    app.include_router(bondlens_router)

    @app.get("/health/live")
    def health_live() -> dict[str, str]:
        return {"status": "live"}

    @app.get("/health/ready")
    def health_ready() -> dict[str, str]:
        try:
            engine = make_engine(settings.database_url)
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"database not ready: {exc}") from exc
        return {"status": "ready"}

    return app


app = create_app()
