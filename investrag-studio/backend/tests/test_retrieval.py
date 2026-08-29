import numpy as np

from investrag.domain import Chunk
from investrag.embeddings import EmbeddingProvider
from investrag.retrieval import BM25, LangChainRetriever
from investrag.vectorstore import FaissVectorStore


def _chunks() -> list[Chunk]:
    return [
        Chunk(chunk_id="a", source_id="source-a", profile="structure-aware", text="revenue increased", element_ids=["a"]),
        Chunk(chunk_id="b", source_id="source-b", profile="structure-aware", text="revenue declined", element_ids=["b"]),
    ]


def test_bm25_honors_source_filter() -> None:
    records = _chunks()
    results = BM25(records).search("revenue", source_ids=["source-b"])
    assert [record.source_id for record, _ in results] == ["source-b"]


def test_mmr_returns_requested_count(tmp_path) -> None:
    records = _chunks()
    vectors = EmbeddingProvider("unused", mode="hash", fallback_dimension=16).embed([record.text for record in records]).vectors
    store = FaissVectorStore(tmp_path)
    store.upsert(records, np.asarray(vectors, dtype=np.float32))
    retriever = LangChainRetriever(store, EmbeddingProvider("unused", mode="hash", fallback_dimension=16))
    assert len(retriever.search("revenue", "mmr", 2)) == 2
