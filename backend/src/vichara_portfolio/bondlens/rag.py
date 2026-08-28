"""Narrative filing chunking for FAISS retrieval.

Token counting is a simple whitespace/punctuation approximation, not the
embedding model's exact tokenizer. Chunk-size budgeting only needs to be
monotonic and consistent, not exact, and pulling in a separate tokenizer
(tiktoken is OpenAI's, irrelevant to a local BGE model, and its encoding
files are fetched from a CDN on first use) would add a network dependency
this local-first project doesn't need for something this approximate.

Heading-aware: HTML is split on <h1>-<h6> boundaries into sections before
chunking, so a chunk never silently spans two unrelated sections. Content
before the first heading is its own section with heading=None.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from lxml import html as lxml_html

DEFAULT_TARGET_TOKENS = 800
DEFAULT_OVERLAP_TOKENS = 100
_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
_CONTENT_TAGS = {"p", "li", "td"}
_WORD_PATTERN = re.compile(r"\S+")


class EmptyDocumentError(Exception):
    """Raised when a filing document has no extractable narrative text."""


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    accession_number: str
    section_heading: str | None
    text: str
    start_offset: int
    end_offset: int
    token_count: int


def approximate_token_count(text: str) -> int:
    return len(_WORD_PATTERN.findall(text))


def _stable_chunk_id(accession_number: str, start_offset: int, end_offset: int) -> str:
    digest_input = f"{accession_number}:{start_offset}:{end_offset}"
    return hashlib.sha256(digest_input.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class _Section:
    heading: str | None
    text: str


def _extract_sections(html: str) -> tuple[_Section, ...]:
    """Split HTML into (heading, text) sections on <h1>-<h6> boundaries."""
    tree = lxml_html.fromstring(html)
    for tag in tree.xpath("//script | //style"):
        tag.drop_tree()

    sections: list[_Section] = []
    current_heading: str | None = None
    current_parts: list[str] = []

    def flush() -> None:
        text = " ".join(part.strip() for part in current_parts if part and part.strip())
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            sections.append(_Section(heading=current_heading, text=text))
        current_parts.clear()

    # Real SEC filings wrap essentially all text in nested <font>/<b>/<u>
    # tags rather than putting it directly inside <p> (verified against the
    # live 2026-07-02 8-K for this deal), and content tags themselves nest
    # (<td><p>...</p></td>, <div><p>...</p></div>). A flat element.text walk
    # misses the former; naively calling the recursive text_content() on
    # every matching tag double-counts the latter. So this walks the tree
    # depth-first and stops descending the moment a content tag is
    # captured - each piece of text is claimed by exactly one node.
    def visit(element: lxml_html.HtmlElement) -> None:
        nonlocal current_heading
        tag = element.tag if isinstance(element.tag, str) else ""
        if tag in _HEADING_TAGS:
            flush()
            current_heading = (element.text_content() or "").strip() or None
            return
        if tag in _CONTENT_TAGS:
            text = element.text_content() or ""
            if text.strip():
                current_parts.append(text)
            return  # do not descend - this subtree's text is already captured
        for child in element:
            visit(child)

    body = tree.find("body")
    visit(body if body is not None else tree)
    flush()

    return tuple(sections)


def chunk_filing_text(
    html: str,
    *,
    accession_number: str,
    target_tokens: int = DEFAULT_TARGET_TOKENS,
    overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
) -> tuple[Chunk, ...]:
    sections = _extract_sections(html)
    if not sections:
        raise EmptyDocumentError(f"no extractable narrative text in filing {accession_number}")

    chunks: list[Chunk] = []
    document_offset = 0

    for section in sections:
        words = _WORD_PATTERN.finditer(section.text)
        word_spans = [(m.start(), m.end()) for m in words]
        if not word_spans:
            continue

        step = max(target_tokens - overlap_tokens, 1)
        index = 0
        while index < len(word_spans):
            window = word_spans[index : index + target_tokens]
            if not window:
                break
            local_start = window[0][0]
            local_end = window[-1][1]
            chunk_text = section.text[local_start:local_end]
            start_offset = document_offset + local_start
            end_offset = document_offset + local_end
            chunks.append(
                Chunk(
                    chunk_id=_stable_chunk_id(accession_number, start_offset, end_offset),
                    accession_number=accession_number,
                    section_heading=section.heading,
                    text=chunk_text,
                    start_offset=start_offset,
                    end_offset=end_offset,
                    token_count=len(window),
                )
            )
            if index + target_tokens >= len(word_spans):
                break
            index += step

        document_offset += len(section.text) + 1  # +1 for the space joining sections

    if not chunks:
        raise EmptyDocumentError(f"no extractable narrative text in filing {accession_number}")

    return tuple(chunks)
