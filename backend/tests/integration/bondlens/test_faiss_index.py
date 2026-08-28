"""Integration tests using the real BAAI/bge-small-en-v1.5 embedding model.

Downloads on first run (cached thereafter under Settings.data_root's
sibling .cache/huggingface - see conftest below). No Postgres or network
service is required beyond that one-time model pull.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from vichara_portfolio.bondlens.adapters.faiss_index import FaissVectorIndex
from vichara_portfolio.bondlens.rag import chunk_filing_text
from vichara_portfolio.settings import Settings
from vichara_portfolio.shared.provenance import SourceRef

pytestmark = pytest.mark.integration

FIXTURE_HTML = (
    Path(__file__).resolve().parents[2] / "fixtures" / "sec" / "narrative_filing.html"
).read_text(encoding="utf-8")
ACCESSION = "0001888524-26-012442"


def _source() -> SourceRef:
    return SourceRef(
        source_name="sec_edgar",
        source_url=f"https://www.sec.gov/Archives/edgar/data/2110410/x/{ACCESSION}.htm",
        retrieved_at=datetime(2026, 8, 28, 12, 0, tzinfo=UTC),
    )


@pytest.fixture(scope="module")
def cache_folder() -> Path:
    settings = Settings(_env_file=None, sec_user_agent="test/0.1 (t@example.com)", jwt_secret="x")
    folder = settings.data_root.parent / ".cache" / "huggingface"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


@pytest.fixture(scope="module")
def index(cache_folder: Path) -> FaissVectorIndex:
    return FaissVectorIndex(cache_folder=cache_folder)


@pytest.fixture(scope="module")
def indexed_chunks(index: FaissVectorIndex):
    chunks = chunk_filing_text(
        FIXTURE_HTML, accession_number=ACCESSION, target_tokens=40, overlap_tokens=10
    )
    index.upsert_chunks(chunks, source_by_accession={ACCESSION: _source()})
    return chunks


def test_a_known_query_retrieves_the_matching_chunk_in_top_three(index, indexed_chunks) -> None:
    results = index.search("pooling and servicing agreement amendment special servicing", top_k=3)

    assert len(results) <= 3
    assert any("special servicing" in r.text.lower() for r in results)


def test_search_results_carry_score_metadata_and_source(index, indexed_chunks) -> None:
    results = index.search("financial statements exhibits", top_k=1)

    assert results
    result = results[0]
    assert isinstance(result.score, float)
    assert result.metadata["accession_number"] == ACCESSION
    assert result.source.source_url.endswith(f"{ACCESSION}.htm")


def test_unrelated_query_still_returns_the_closest_available_chunks(index, indexed_chunks) -> None:
    """FAISS always returns the k nearest vectors, even if none are a great
    match - that is a property of the index, not a bug, and callers (the
    agent's retrieval node) are responsible for a relevance threshold."""
    results = index.search("unrelated query about quarterly baking recipes", top_k=2)
    assert len(results) == 2


def test_delete_document_removes_all_its_chunks(cache_folder: Path) -> None:
    fresh_index = FaissVectorIndex(cache_folder=cache_folder)
    chunks = chunk_filing_text(
        FIXTURE_HTML, accession_number=ACCESSION, target_tokens=40, overlap_tokens=10
    )
    fresh_index.upsert_chunks(chunks, source_by_accession={ACCESSION: _source()})
    size_before = fresh_index.size

    removed = fresh_index.delete_document(ACCESSION)

    assert removed == size_before
    assert fresh_index.size == 0
    assert fresh_index.search("special servicing", top_k=3) == ()


def test_upsert_of_the_same_chunk_id_replaces_not_duplicates(cache_folder: Path) -> None:
    fresh_index = FaissVectorIndex(cache_folder=cache_folder)
    chunks = chunk_filing_text(
        FIXTURE_HTML, accession_number=ACCESSION, target_tokens=40, overlap_tokens=10
    )
    source_map = {ACCESSION: _source()}

    fresh_index.upsert_chunks(chunks, source_by_accession=source_map)
    size_after_first = fresh_index.size
    fresh_index.upsert_chunks(chunks, source_by_accession=source_map)

    assert fresh_index.size == size_after_first


def test_persist_and_load_round_trip_preserves_search_results(
    cache_folder: Path, tmp_path: Path
) -> None:
    original = FaissVectorIndex(cache_folder=cache_folder)
    chunks = chunk_filing_text(
        FIXTURE_HTML, accession_number=ACCESSION, target_tokens=40, overlap_tokens=10
    )
    original.upsert_chunks(chunks, source_by_accession={ACCESSION: _source()})

    persist_path = tmp_path / "faiss-index"
    original.persist(persist_path)

    assert (persist_path / "index.faiss").exists()
    assert (persist_path / "sidecar.json").exists()

    reloaded = FaissVectorIndex(
        model=original.model
    )  # reuse the already-loaded model, no re-download
    reloaded.load(persist_path)

    assert reloaded.size == original.size
    results = reloaded.search("special servicing", top_k=1)
    assert results
    assert results[0].source.source_url == _source().source_url
