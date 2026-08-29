from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


ElementType = Literal[
    "heading",
    "paragraph",
    "list",
    "table",
    "table_row",
    "spreadsheet_range",
    "image",
    "email",
    "metadata",
    "code",
]


class CanonicalElement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    element_id: str
    element_type: ElementType
    text: str = ""
    order: int = 0
    hierarchy: str = ""
    page: int | None = None
    slide: int | None = None
    sheet: str | None = None
    cell_range: str | None = None
    json_path: str | None = None
    bbox: tuple[float, float, float, float] | None = None
    confidence: float = 1.0
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ParsedDocument(BaseModel):
    source_name: str
    media_type: str
    parser: str
    parser_version: str
    elements: list[CanonicalElement]
    warnings: list[str] = Field(default_factory=list)
    quality_score: float = 1.0


class Chunk(BaseModel):
    chunk_id: str
    source_id: str
    profile: str
    text: str
    element_ids: list[str]
    parent_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SourceVersion(BaseModel):
    source_id: str
    name: str
    media_type: str
    checksum: str
    size_bytes: int
    parser: str
    status: Literal["ready", "partial", "failed"]
    quality_score: float
    warnings: list[str] = Field(default_factory=list)
    element_count: int
    chunk_count: int
    created_at: datetime = Field(default_factory=utc_now)


class Citation(BaseModel):
    chunk_id: str
    source_id: str
    source_name: str
    label: str
    excerpt: str
    page: int | None = None
    slide: int | None = None
    sheet: str | None = None
    cell_range: str | None = None
    json_path: str | None = None


class QueryRequest(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    profile: Literal["dense", "mmr", "hybrid", "parent", "multi-query"] = "hybrid"
    vector_store: str = "faiss"
    top_k: int = Field(default=6, ge=1, le=20)
    source_ids: list[str] = Field(default_factory=list)


class QueryTrace(BaseModel):
    original_query: str
    rewritten_query: str
    filters: dict[str, Any] = Field(default_factory=dict)
    profile: str
    vector_store: str
    dense_candidates: int
    lexical_candidates: int
    fused_candidates: int
    final_context_chunks: int
    retrieval_ms: float
    generation_ms: float
    total_ms: float
    model: str
    embedding_model: str
    embedding_fallback: bool


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    insufficient_evidence: bool
    conflicting_evidence: bool = False
    trace: QueryTrace
    validator_messages: list[str] = Field(default_factory=list)


class MetricResult(BaseModel):
    name: str
    value: float
    unit: str = "score"


class HealthResponse(BaseModel):
    status: str
    service: str
    embedding_model: str
    embedding_fallback: bool
    indexed_chunks: int
    available_vector_stores: list[dict[str, Any]]
