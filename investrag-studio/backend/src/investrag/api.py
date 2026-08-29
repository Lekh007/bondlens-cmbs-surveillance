from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from .domain import HealthResponse, QueryRequest, QueryResponse, SourceVersion
from .parser import parser_capabilities
from .service import InvestRAGService
from .vectorstore import vector_store_capabilities


def make_router(service: InvestRAGService) -> APIRouter:
    router = APIRouter(prefix="/api/v1")

    @router.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", service="investrag-studio", embedding_model=service.embeddings.model_name, embedding_fallback=service.embeddings.fallback, indexed_chunks=service.store.count, available_vector_stores=vector_store_capabilities())

    @router.get("/sources", response_model=list[SourceVersion])
    def sources() -> list[SourceVersion]:
        return service.list_sources()

    @router.post("/ingestions", response_model=SourceVersion)
    async def ingest(file: UploadFile = File(...)) -> SourceVersion:
        suffix = Path(file.filename or "upload.bin").suffix
        with tempfile.NamedTemporaryFile(prefix="investrag_", suffix=suffix, delete=False) as handle:
            total = 0
            while chunk := await file.read(1024 * 1024):
                total += len(chunk)
                if total > service.settings.max_upload_bytes:
                    raise HTTPException(status_code=413, detail="upload exceeds configured size limit")
                handle.write(chunk)
            temporary_path = Path(handle.name)
        try:
            return service.ingest(temporary_path, file.filename or temporary_path.name)
        finally:
            temporary_path.unlink(missing_ok=True)

    @router.post("/queries", response_model=QueryResponse)
    def query(request: QueryRequest) -> QueryResponse:
        if request.vector_store != "faiss":
            raise HTTPException(status_code=400, detail="Only FAISS is active in the local vertical slice; other adapters report capability status.")
        return service.query(request)

    @router.get("/vector-stores")
    def vector_stores() -> list[dict[str, object]]:
        return vector_store_capabilities()

    @router.get("/parsers")
    def parsers() -> list[dict[str, object]]:
        return parser_capabilities()

    return router
