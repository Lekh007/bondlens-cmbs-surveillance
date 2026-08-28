"""SourceRef: the citation every tool output and agent claim must carry.

The verifier (Task 13) rejects any answer whose claims lack one of these. A
SourceRef always has an unambiguous, timezone-aware retrieval timestamp -
a naive datetime is refused at construction rather than silently treated
as local time.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class SourceRef:
    source_name: str
    source_url: str
    retrieved_at: datetime
    checksum: str | None = None
    record_id: str | None = None
    field_path: str | None = None

    def __post_init__(self) -> None:
        if self.retrieved_at.tzinfo is None:
            raise ValueError(
                f"retrieved_at must be timezone-aware, got naive datetime {self.retrieved_at!r}"
            )

    @classmethod
    def now(
        cls,
        *,
        source_name: str,
        source_url: str,
        checksum: str | None = None,
        record_id: str | None = None,
        field_path: str | None = None,
    ) -> SourceRef:
        return cls(
            source_name=source_name,
            source_url=source_url,
            retrieved_at=datetime.now(UTC),
            checksum=checksum,
            record_id=record_id,
            field_path=field_path,
        )
