from pathlib import Path

import pytest

from vichara_portfolio.bondlens.rag import (
    Chunk,
    EmptyDocumentError,
    approximate_token_count,
    chunk_filing_text,
)

FIXTURE_HTML = (
    Path(__file__).resolve().parents[2] / "fixtures" / "sec" / "narrative_filing.html"
).read_text(encoding="utf-8")

ACCESSION = "0001888524-26-012442"


def test_heading_aware_extraction_assigns_correct_section_headings() -> None:
    chunks = chunk_filing_text(
        FIXTURE_HTML, accession_number=ACCESSION, target_tokens=20, overlap_tokens=5
    )

    headings = {c.section_heading for c in chunks}
    assert "Item 1.01 Entry into a Material Definitive Agreement" in headings
    assert "Background" in headings
    assert "Item 9.01 Financial Statements and Exhibits" in headings


def test_script_and_style_content_is_never_included() -> None:
    chunks = chunk_filing_text(
        FIXTURE_HTML, accession_number=ACCESSION, target_tokens=20, overlap_tokens=5
    )
    combined = " ".join(c.text for c in chunks)
    assert "trackingIgnored" not in combined
    assert "display:none" not in combined


def test_accession_number_is_stamped_on_every_chunk() -> None:
    chunks = chunk_filing_text(
        FIXTURE_HTML, accession_number=ACCESSION, target_tokens=20, overlap_tokens=5
    )
    assert all(c.accession_number == ACCESSION for c in chunks)


def test_chunk_ids_are_stable_across_repeated_calls() -> None:
    first = chunk_filing_text(
        FIXTURE_HTML, accession_number=ACCESSION, target_tokens=20, overlap_tokens=5
    )
    second = chunk_filing_text(
        FIXTURE_HTML, accession_number=ACCESSION, target_tokens=20, overlap_tokens=5
    )
    assert [c.chunk_id for c in first] == [c.chunk_id for c in second]


def test_chunk_ids_are_unique_within_a_document() -> None:
    chunks = chunk_filing_text(
        FIXTURE_HTML, accession_number=ACCESSION, target_tokens=20, overlap_tokens=5
    )
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))


def test_different_accession_numbers_produce_different_chunk_ids() -> None:
    a = chunk_filing_text(
        FIXTURE_HTML, accession_number="acc-a", target_tokens=20, overlap_tokens=5
    )
    b = chunk_filing_text(
        FIXTURE_HTML, accession_number="acc-b", target_tokens=20, overlap_tokens=5
    )
    assert a[0].chunk_id != b[0].chunk_id


def test_default_800_token_target_produces_reasonable_chunk_sizes() -> None:
    chunks = chunk_filing_text(FIXTURE_HTML, accession_number=ACCESSION)
    for chunk in chunks:
        assert chunk.token_count <= 800
        assert approximate_token_count(chunk.text) == chunk.token_count


def test_consecutive_chunks_within_a_section_overlap() -> None:
    """The Background section has ~85 words - with target=20/overlap=5 it
    must split into multiple chunks that share trailing/leading words."""
    chunks = chunk_filing_text(
        FIXTURE_HTML, accession_number=ACCESSION, target_tokens=20, overlap_tokens=5
    )
    background_chunks = [c for c in chunks if c.section_heading == "Background"]
    assert len(background_chunks) >= 2

    first_words = background_chunks[0].text.split()
    second_words = background_chunks[1].text.split()
    overlap = set(first_words[-5:]) & set(second_words[:5])
    assert overlap, "expected shared words between consecutive overlapping chunks"


def test_a_section_shorter_than_the_target_produces_exactly_one_chunk() -> None:
    chunks = chunk_filing_text(
        FIXTURE_HTML, accession_number=ACCESSION, target_tokens=800, overlap_tokens=100
    )
    item_901 = [
        c for c in chunks if c.section_heading == "Item 9.01 Financial Statements and Exhibits"
    ]
    assert len(item_901) == 1


def test_empty_document_is_rejected() -> None:
    with pytest.raises(EmptyDocumentError):
        chunk_filing_text("<html><body></body></html>", accession_number=ACCESSION)


def test_whitespace_only_document_is_rejected() -> None:
    with pytest.raises(EmptyDocumentError):
        chunk_filing_text("<html><body><p>   </p></body></html>", accession_number=ACCESSION)


def test_source_offsets_are_internally_consistent() -> None:
    chunks = chunk_filing_text(
        FIXTURE_HTML, accession_number=ACCESSION, target_tokens=20, overlap_tokens=5
    )
    for chunk in chunks:
        assert chunk.end_offset > chunk.start_offset
        assert chunk.end_offset - chunk.start_offset == len(chunk.text)


def test_offsets_increase_monotonically_within_a_section() -> None:
    chunks = chunk_filing_text(
        FIXTURE_HTML, accession_number=ACCESSION, target_tokens=20, overlap_tokens=5
    )
    background_chunks = [c for c in chunks if c.section_heading == "Background"]
    starts = [c.start_offset for c in background_chunks]
    assert starts == sorted(starts)


def test_content_before_first_heading_has_no_section_heading() -> None:
    html = (
        "<html><body><p>Preamble text before any heading appears here.</p>"
        "<h1>Title</h1><p>Body.</p></body></html>"
    )
    chunks = chunk_filing_text(
        html, accession_number=ACCESSION, target_tokens=800, overlap_tokens=100
    )
    assert chunks[0].section_heading is None
    assert "Preamble" in chunks[0].text


def test_approximate_token_count_is_word_based() -> None:
    assert approximate_token_count("one two three") == 3
    assert approximate_token_count("") == 0


def test_chunk_is_a_frozen_dataclass() -> None:
    chunks = chunk_filing_text(
        FIXTURE_HTML, accession_number=ACCESSION, target_tokens=20, overlap_tokens=5
    )
    with pytest.raises(AttributeError):
        chunks[0].text = "mutated"  # type: ignore[misc]
    assert isinstance(chunks[0], Chunk)
