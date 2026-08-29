from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda, RunnablePassthrough

from .domain import Chunk
from .embeddings import EmbeddingProvider
from .vectorstore import FaissVectorStore


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9][a-z0-9_.-]*", text.lower())


class BM25:
    def __init__(self, records: list[Chunk]) -> None:
        self.records = records
        self.tokenized = [_tokens(record.text) for record in records]
        self.doc_frequency = Counter(token for tokens in self.tokenized for token in set(tokens))
        self.avgdl = sum(map(len, self.tokenized)) / len(self.tokenized) if self.tokenized else 1.0

    def search(self, query: str, k: int = 20, source_ids: list[str] | None = None) -> list[tuple[Chunk, float]]:
        query_tokens = _tokens(query)
        n = len(self.records)
        allowed = set(source_ids or [])
        results: list[tuple[Chunk, float]] = []
        for record, tokens in zip(self.records, self.tokenized, strict=True):
            if allowed and record.source_id not in allowed:
                continue
            counts = Counter(tokens)
            score = 0.0
            for token in query_tokens:
                if token not in counts:
                    continue
                idf = math.log(1 + (n - self.doc_frequency[token] + 0.5) / (self.doc_frequency[token] + 0.5))
                denominator = counts[token] + 1.5 * (0.25 + 0.75 * len(tokens) / max(self.avgdl, 1))
                score += idf * counts[token] * 2.5 / denominator
            if score > 0:
                results.append((record, score))
        return sorted(results, key=lambda item: item[1], reverse=True)[:k]


@dataclass
class Retrieved:
    chunk: Chunk
    score: float
    stage: str

    def document(self) -> Document:
        return Document(page_content=self.chunk.text, metadata={**self.chunk.metadata, "chunk_id": self.chunk.chunk_id, "source_id": self.chunk.source_id})


class LangChainRetriever:
    """Explicit Runnable retrieval pipeline; no LangGraph state machine is used."""

    def __init__(self, store: FaissVectorStore, embeddings: EmbeddingProvider) -> None:
        self.store = store
        self.embeddings = embeddings
        self.chain: Any = RunnablePassthrough() | RunnableLambda(self._retrieve_for_chain)

    def _retrieve_for_chain(self, question: str) -> list[Document]:
        return [item.document() for item in self.search(question, profile="hybrid", k=6)]

    def search(self, question: str, profile: str, k: int, source_ids: list[str] | None = None) -> list[Retrieved]:
        if profile == "multi-query":
            variants = [question, f"key facts and figures about {question}", f"source evidence for {question}"]
            merged: dict[str, Retrieved] = {}
            for variant in variants:
                for rank, item in enumerate(self.search(variant, "hybrid", k * 2, source_ids), start=1):
                    if item.chunk.chunk_id not in merged:
                        merged[item.chunk.chunk_id] = Retrieved(item.chunk, 0.0, "multi-query")
                    merged[item.chunk.chunk_id].score += 1 / (60 + rank)
            return sorted(merged.values(), key=lambda item: item.score, reverse=True)[:k]
        query_vector = self.embeddings.embed([question]).vectors[0]
        dense = [Retrieved(chunk, score, "dense") for chunk, score in self.store.search(query_vector, k=max(20, k * 4), source_ids=source_ids)]
        if profile == "dense":
            return dense[:k]
        if profile == "parent":
            parent_selected: list[Retrieved] = []
            seen_parents: set[str] = set()
            for candidate in dense:
                parent_key = candidate.chunk.parent_id or candidate.chunk.chunk_id
                if parent_key in seen_parents:
                    continue
                parent_selected.append(candidate)
                seen_parents.add(parent_key)
                if len(parent_selected) >= k:
                    break
            return parent_selected
        if profile == "mmr":
            pool = dense[: max(20, k * 4)]
            mmr_selected: list[Retrieved] = []
            while pool and len(mmr_selected) < k:
                def mmr_score(candidate: Retrieved) -> float:
                    candidate_vector = self.store.vector_for(candidate.chunk.chunk_id)
                    similarities = [
                        float(candidate_vector @ selected_vector)
                        for item in mmr_selected
                        if candidate_vector is not None
                        and (selected_vector := self.store.vector_for(item.chunk.chunk_id)) is not None
                    ]
                    diversity = max(similarities, default=0.0)
                    return 0.75 * candidate.score - 0.25 * diversity if mmr_selected else candidate.score

                best = max(pool, key=mmr_score)
                mmr_selected.append(best)
                pool.remove(best)
            return mmr_selected
        lexical = [Retrieved(chunk, score, "bm25") for chunk, score in BM25(self.store.all_records()).search(question, k=max(20, k * 4), source_ids=source_ids)]
        by_id: dict[str, Retrieved] = {}
        for rank, item in enumerate(dense, start=1):
            by_id.setdefault(item.chunk.chunk_id, Retrieved(item.chunk, 1 / (60 + rank), "rrf"))
            by_id[item.chunk.chunk_id].score += 1 / (60 + rank)
        for rank, item in enumerate(lexical, start=1):
            by_id.setdefault(item.chunk.chunk_id, Retrieved(item.chunk, 1 / (60 + rank), "rrf"))
            by_id[item.chunk.chunk_id].score += 1 / (60 + rank)
        return sorted(by_id.values(), key=lambda item: item.score, reverse=True)[:k]
