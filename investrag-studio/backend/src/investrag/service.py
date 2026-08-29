from __future__ import annotations

import hashlib
import re
import shutil
import tempfile
import time
from pathlib import Path
from typing import Literal

from .catalog import Catalog
from .chunking import chunk_elements
from .config import Settings
from .domain import Citation, QueryRequest, QueryResponse, QueryTrace, SourceVersion
from .embeddings import EmbeddingProvider
from .llm import LocalAnswerer
from .parser import parse_document
from .retrieval import LangChainRetriever
from .security import safe_extract_zip
from .vectorstore import FaissVectorStore


class InvestRAGService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        settings.raw_dir.mkdir(parents=True, exist_ok=True)
        settings.index_dir.mkdir(parents=True, exist_ok=True)
        self.catalog = Catalog(settings.catalog_path)
        self.embeddings = EmbeddingProvider(settings.embedding_model, settings.embedding_mode, settings.embedding_fallback_dimension)
        self.store = FaissVectorStore(settings.index_dir)
        self.retriever = LangChainRetriever(self.store, self.embeddings)
        self.answerer = LocalAnswerer(settings.ollama_base_url, settings.ollama_model)
        self._chunks_by_id = {chunk.chunk_id: chunk for chunk in self.store.all_records()}

    def ingest(self, path: Path, original_name: str | None = None) -> SourceVersion:
        started = time.perf_counter()
        source_name = original_name or path.name
        checksum = hashlib.sha256(path.read_bytes()).hexdigest()
        source_id = f"src_{checksum[:16]}"
        if path.suffix.lower() == ".zip":
            return self._ingest_archive(path, source_name, checksum, source_id)
        destination = self.settings.raw_dir / f"{source_id}_{Path(source_name).name}"
        if path.resolve() != destination.resolve():
            shutil.copy2(path, destination)
        try:
            parsed = parse_document(destination, source_name)
            chunks = chunk_elements(parsed.elements, source_id)
            if chunks:
                vectors = self.embeddings.embed([chunk.text for chunk in chunks]).vectors
                self.store.upsert(chunks, vectors)
                self.catalog.save_chunks(chunks)
                self._chunks_by_id.update({chunk.chunk_id: chunk for chunk in chunks})
            status: Literal["ready", "partial"] = "ready" if parsed.quality_score >= 0.65 and parsed.elements else "partial"
            source = SourceVersion(source_id=source_id, name=source_name, media_type=parsed.media_type, checksum=checksum, size_bytes=destination.stat().st_size, parser=parsed.parser, status=status, quality_score=parsed.quality_score, warnings=parsed.warnings, element_count=len(parsed.elements), chunk_count=len(chunks))
        except Exception as exc:
            source = SourceVersion(source_id=source_id, name=source_name, media_type="application/octet-stream", checksum=checksum, size_bytes=destination.stat().st_size, parser="failed", status="failed", quality_score=0.0, warnings=[f"{exc.__class__.__name__}: {exc}"], element_count=0, chunk_count=0)
        self.catalog.save_source(source)
        _ = (time.perf_counter() - started) * 1000
        return source

    def _ingest_archive(self, path: Path, source_name: str, checksum: str, source_id: str) -> SourceVersion:
        child_sources: list[SourceVersion] = []
        warnings: list[str] = []
        try:
            with tempfile.TemporaryDirectory(prefix="investrag_zip_") as directory:
                extracted = safe_extract_zip(path, Path(directory))
                for child in extracted:
                    try:
                        child_sources.append(self.ingest(child, child.name))
                    except Exception as exc:  # continue with visible partial success
                        warnings.append(f"{child.name}: {exc.__class__.__name__}: {exc}")
            warnings.extend(f"{source.name}: {warning}" for source in child_sources for warning in source.warnings)
            status: Literal["ready", "partial"] = "ready" if child_sources and all(source.status == "ready" for source in child_sources) else "partial"
            source = SourceVersion(source_id=source_id, name=source_name, media_type="application/zip", checksum=checksum, size_bytes=path.stat().st_size, parser="safe-zip-recursive", status=status, quality_score=sum(source.quality_score for source in child_sources) / len(child_sources) if child_sources else 0.0, warnings=warnings, element_count=sum(source.element_count for source in child_sources), chunk_count=sum(source.chunk_count for source in child_sources))
        except Exception as exc:
            source = SourceVersion(source_id=source_id, name=source_name, media_type="application/zip", checksum=checksum, size_bytes=path.stat().st_size, parser="safe-zip-rejected", status="failed", quality_score=0.0, warnings=[f"{exc.__class__.__name__}: {exc}"], element_count=0, chunk_count=0)
        self.catalog.save_source(source)
        return source

    def list_sources(self) -> list[SourceVersion]:
        return self.catalog.list_sources()

    def query(self, request: QueryRequest) -> QueryResponse:
        started = time.perf_counter()
        retrieval_started = time.perf_counter()
        results = self.retriever.search(request.question, request.profile, request.top_k, request.source_ids)
        retrieval_ms = (time.perf_counter() - retrieval_started) * 1000
        contexts: list[dict[str, str]] = []
        citations: list[Citation] = []
        for index, result in enumerate(results, start=1):
            chunk = result.chunk
            label = f"S{index}"
            contexts.append({"label": label, "text": chunk.text})
            citations.append(Citation(chunk_id=chunk.chunk_id, source_id=chunk.source_id, source_name=self._source_name(chunk.source_id), label=label, excerpt=chunk.text[:500], page=chunk.metadata.get("page"), slide=chunk.metadata.get("slide"), sheet=chunk.metadata.get("sheet"), cell_range=chunk.metadata.get("cell_range"), json_path=chunk.metadata.get("json_path")))
        answer, generation_ms, _used_fallback = self.answerer.answer(request.question, contexts)
        used_labels = set(re.findall(r"\[(S\d+)\]", answer))
        validator_messages: list[str] = []
        unknown_labels = used_labels - {citation.label for citation in citations}
        if contexts and not used_labels:
            validator_messages.append("The answer returned no resolvable citation labels; evidence is shown separately.")
        if unknown_labels:
            validator_messages.append(f"The answer referenced unknown citation labels: {sorted(unknown_labels)}")
        insufficient = not bool(results)
        if contexts and (not used_labels or unknown_labels):
            answer = "I cannot safely return a grounded answer because the generated response did not contain resolvable citations."
            insufficient = True
        if insufficient:
            validator_messages.append("No indexed evidence matched the question.")
        trace = QueryTrace(original_query=request.question, rewritten_query=request.question, profile=request.profile, vector_store=request.vector_store, dense_candidates=max(0, min(20, len(self.store.all_records()))), lexical_candidates=max(0, min(20, len(self.store.all_records())) if request.profile == "hybrid" else 0), fused_candidates=len(results), final_context_chunks=len(contexts), retrieval_ms=round(retrieval_ms, 2), generation_ms=round(generation_ms, 2), total_ms=round((time.perf_counter() - started) * 1000, 2), model=self.settings.ollama_model, embedding_model=self.embeddings.model_name, embedding_fallback=self.embeddings.fallback)
        return QueryResponse(answer=answer, citations=citations, insufficient_evidence=insufficient, trace=trace, validator_messages=validator_messages)

    def _source_name(self, source_id: str) -> str:
        for source in self.list_sources():
            if source.source_id == source_id:
                return source.name
        return source_id
