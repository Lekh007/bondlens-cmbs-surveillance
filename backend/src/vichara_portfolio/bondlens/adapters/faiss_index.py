"""Local FAISS retrieval over chunked narrative filing text.

Embeddings: BAAI/bge-small-en-v1.5 via sentence-transformers, cached under
Settings.data_root's sibling .cache/huggingface (never re-downloaded once
cached). Embeddings are L2-normalized, indexed with faiss.IndexFlatIP
(inner product on normalized vectors == cosine similarity), wrapped in
IndexIDMap so individual chunks can be removed by id - needed for both
upsert (re-embedding an unchanged accession must replace, not duplicate)
and delete_document.

FAISS stores vectors only, not payload, so a JSON sidecar carries chunk
text/metadata/SourceRef keyed by the same integer ids. Both the index file
and the sidecar are written atomically (temp file + os.replace) so a crash
mid-persist never leaves a half-written index on disk.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import cast

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from vichara_portfolio.bondlens.rag import Chunk
from vichara_portfolio.shared.provenance import SourceRef

EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"


@dataclass(frozen=True)
class SearchResult:
    chunk_id: str
    score: float
    text: str
    metadata: dict[str, str]
    source: SourceRef


@dataclass
class _IndexedChunk:
    chunk_id: str
    accession_number: str
    section_heading: str | None
    text: str
    source: SourceRef


def _source_to_json(source: SourceRef) -> dict[str, str | None]:
    return {
        "source_name": source.source_name,
        "source_url": source.source_url,
        "retrieved_at": source.retrieved_at.isoformat(),
        "checksum": source.checksum,
        "record_id": source.record_id,
        "field_path": source.field_path,
    }


def _source_from_json(payload: dict[str, str | None]) -> SourceRef:
    return SourceRef(
        source_name=payload["source_name"],  # type: ignore[arg-type]
        source_url=payload["source_url"],  # type: ignore[arg-type]
        retrieved_at=datetime.fromisoformat(payload["retrieved_at"]),  # type: ignore[arg-type]
        checksum=payload.get("checksum"),
        record_id=payload.get("record_id"),
        field_path=payload.get("field_path"),
    )


class FaissVectorIndex:
    def __init__(
        self,
        *,
        model: SentenceTransformer | None = None,
        cache_folder: Path | None = None,
        model_name: str = EMBEDDING_MODEL_NAME,
    ) -> None:
        self._model = model or SentenceTransformer(
            model_name, cache_folder=str(cache_folder) if cache_folder else None
        )
        self._model_name = model_name
        dimension = self._model.get_embedding_dimension()
        assert dimension is not None, f"{model_name} did not report an embedding dimension"
        self._dimension: int = dimension
        self._index = faiss.IndexIDMap(faiss.IndexFlatIP(self._dimension))
        self._chunks: dict[int, _IndexedChunk] = {}
        self._id_by_chunk_id: dict[str, int] = {}
        self._next_id = 0

    @property
    def model(self) -> SentenceTransformer:
        """Exposed so a second index can reuse an already-loaded model
        instead of re-loading it from cache."""
        return self._model

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def size(self) -> int:
        return self._index.ntotal

    def upsert_chunks(
        self, chunks: tuple[Chunk, ...], *, source_by_accession: dict[str, SourceRef]
    ) -> None:
        if not chunks:
            return

        ids_to_remove = [
            self._id_by_chunk_id[c.chunk_id] for c in chunks if c.chunk_id in self._id_by_chunk_id
        ]
        if ids_to_remove:
            # faiss's stub wants an IDSelector; a plain int64 ndarray works
            # at runtime (verified against the real integration test).
            self._index.remove_ids(np.array(ids_to_remove, dtype="int64"))  # type: ignore[arg-type]
            for internal_id in ids_to_remove:
                chunk_id = self._chunks.pop(internal_id).chunk_id
                del self._id_by_chunk_id[chunk_id]

        embeddings = self._model.encode(
            [c.text for c in chunks], normalize_embeddings=True, convert_to_numpy=True
        ).astype("float32")

        new_ids = []
        for chunk in chunks:
            internal_id = self._next_id
            self._next_id += 1
            new_ids.append(internal_id)
            self._id_by_chunk_id[chunk.chunk_id] = internal_id
            self._chunks[internal_id] = _IndexedChunk(
                chunk_id=chunk.chunk_id,
                accession_number=chunk.accession_number,
                section_heading=chunk.section_heading,
                text=chunk.text,
                source=source_by_accession[chunk.accession_number],
            )

        self._index.add_with_ids(embeddings, np.array(new_ids, dtype="int64"))

    def search(self, query: str, *, top_k: int = 5) -> tuple[SearchResult, ...]:
        if self._index.ntotal == 0:
            return ()
        query_embedding = self._model.encode(
            [query], normalize_embeddings=True, convert_to_numpy=True
        ).astype("float32")
        k = min(top_k, self._index.ntotal)
        scores, ids = self._index.search(query_embedding, k)

        results = []
        for score, internal_id in zip(scores[0], ids[0], strict=True):
            if internal_id == -1:
                continue
            entry = self._chunks[int(internal_id)]
            results.append(
                SearchResult(
                    chunk_id=entry.chunk_id,
                    score=float(score),
                    text=entry.text,
                    metadata={
                        "accession_number": entry.accession_number,
                        "section_heading": entry.section_heading or "",
                    },
                    source=entry.source,
                )
            )
        return tuple(results)

    def delete_document(self, accession_number: str) -> int:
        ids_to_remove = [
            internal_id
            for internal_id, entry in self._chunks.items()
            if entry.accession_number == accession_number
        ]
        if not ids_to_remove:
            return 0
        self._index.remove_ids(np.array(ids_to_remove, dtype="int64"))  # type: ignore[arg-type]
        for internal_id in ids_to_remove:
            chunk_id = self._chunks.pop(internal_id).chunk_id
            del self._id_by_chunk_id[chunk_id]
        return len(ids_to_remove)

    def persist(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        index_path = path / "index.faiss"
        sidecar_path = path / "sidecar.json"

        tmp_index = index_path.with_name(index_path.name + ".tmp")
        faiss.write_index(self._index, str(tmp_index))
        os.replace(tmp_index, index_path)

        payload = {
            "model_name": self._model_name,
            "dimension": self._dimension,
            "next_id": self._next_id,
            "chunks": {
                str(internal_id): {
                    "chunk_id": entry.chunk_id,
                    "accession_number": entry.accession_number,
                    "section_heading": entry.section_heading,
                    "text": entry.text,
                    "source": _source_to_json(entry.source),
                }
                for internal_id, entry in self._chunks.items()
            },
        }
        tmp_sidecar = sidecar_path.with_name(sidecar_path.name + ".tmp")
        tmp_sidecar.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(tmp_sidecar, sidecar_path)

    def load(self, path: Path) -> None:
        index_path = path / "index.faiss"
        sidecar_path = path / "sidecar.json"

        # read_index's stub returns the base Index type; persist() only ever
        # wrote an IndexIDMap, so the cast reflects an invariant this class
        # itself maintains, not an unchecked assumption about the file.
        self._index = cast("faiss.IndexIDMap", faiss.read_index(str(index_path)))
        payload = json.loads(sidecar_path.read_text(encoding="utf-8"))
        self._model_name = payload["model_name"]
        self._dimension = payload["dimension"]
        self._next_id = payload["next_id"]
        self._chunks = {
            int(internal_id): _IndexedChunk(
                chunk_id=entry["chunk_id"],
                accession_number=entry["accession_number"],
                section_heading=entry["section_heading"],
                text=entry["text"],
                source=_source_from_json(entry["source"]),
            )
            for internal_id, entry in payload["chunks"].items()
        }
        self._id_by_chunk_id = {
            entry.chunk_id: internal_id for internal_id, entry in self._chunks.items()
        }
