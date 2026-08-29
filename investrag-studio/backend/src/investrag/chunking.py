from __future__ import annotations

import hashlib
import re
from typing import Any

from .domain import CanonicalElement, Chunk


def _chunk_id(source_id: str, profile: str, index: int, text: str) -> str:
    digest = hashlib.sha1(f"{source_id}:{profile}:{index}:{text}".encode()).hexdigest()[:14]
    return f"chunk_{digest}"


def _split_text(text: str, max_chars: int = 1400, overlap: int = 180) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    sentences = re.split(r"(?<=[.!?])\s+", text)
    parts: list[str] = []
    current = ""
    for sentence in sentences:
        if current and len(current) + len(sentence) + 1 > max_chars:
            parts.append(current.strip())
            current = current[-overlap:] + " " + sentence
        else:
            current = f"{current} {sentence}".strip()
    if current.strip():
        parts.append(current.strip())
    return parts


def chunk_elements(elements: list[CanonicalElement], source_id: str, profile: str = "structure-aware") -> list[Chunk]:
    """Create reproducible chunks while retaining element-level provenance."""

    if profile == "recursive-baseline":
        text = "\n".join(element.text for element in elements)
        return [
            Chunk(chunk_id=_chunk_id(source_id, profile, index, part), source_id=source_id, profile=profile, text=part, element_ids=[element.element_id for element in elements], metadata={"strategy": "recursive"})
            for index, part in enumerate(_split_text(text))
        ]

    chunks: list[Chunk] = []
    pending: list[CanonicalElement] = []
    pending_chars = 0
    parent_id: str | None = None

    def flush() -> None:
        nonlocal pending, pending_chars, parent_id
        if not pending:
            return
        text = "\n".join(element.text for element in pending)
        first = pending[0]
        location: dict[str, Any] = {
            key: value
            for key, value in {
                "page": first.page,
                "slide": first.slide,
                "sheet": first.sheet,
                "cell_range": first.cell_range,
                "json_path": first.json_path,
                "bbox": first.bbox,
            }.items()
            if value is not None
        }
        location["source_locations"] = [
            {
                key: value
                for key, value in {
                    "element_id": element.element_id,
                    "page": element.page,
                    "slide": element.slide,
                    "sheet": element.sheet,
                    "cell_range": element.cell_range,
                    "json_path": element.json_path,
                }.items()
                if value is not None
            }
            for element in pending
        ]
        for part in _split_text(text):
            ids = [element.element_id for element in pending if element.text in part or len(pending) == 1]
            if not ids:
                ids = [element.element_id for element in pending]
            chunks.append(
                Chunk(
                    chunk_id=_chunk_id(source_id, profile, len(chunks), part),
                    source_id=source_id,
                    profile=profile,
                    text=part,
                    element_ids=ids,
                    parent_id=parent_id,
                    metadata={"strategy": profile, **location},
                )
            )
        pending = []
        pending_chars = 0

    for element in elements:
        if element.element_type == "heading":
            flush()
            parent_id = element.element_id
        pending.append(element)
        pending_chars += len(element.text) + 1
        if pending_chars >= 1400 or element.element_type in {"table", "spreadsheet_range"}:
            flush()
    flush()
    return chunks
