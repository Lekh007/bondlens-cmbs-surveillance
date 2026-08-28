"""Content-addressed storage for immutable raw source documents.

Every stored file lives at raw_root/<source>/<checksum[:2]>/<checksum>/<filename>.
The checksum is always the SHA-256 of the bytes actually on disk, so a write
either lands at a fresh path or hits an existing one whose content is
verified to still match - it never silently overwrites mismatched content.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


class ChecksumMismatchError(Exception):
    """Raised when declared bytes don't match their expected checksum, or when
    content already cached at a checksum-derived path has diverged on disk."""


@dataclass(frozen=True)
class StoredDocument:
    source: str
    checksum: str
    path: Path
    size: int
    already_cached: bool


class RawDocumentStore:
    def __init__(self, raw_root: Path) -> None:
        self._raw_root = Path(raw_root)

    def path_for(self, *, source: str, checksum: str, filename: str = "") -> Path:
        directory = self._raw_root / source / checksum[:2] / checksum
        return directory / filename if filename else directory

    def write(
        self,
        *,
        source: str,
        filename: str,
        content: bytes,
        expected_checksum: str | None = None,
    ) -> StoredDocument:
        computed = hashlib.sha256(content).hexdigest()
        if expected_checksum is not None and expected_checksum.lower() != computed:
            raise ChecksumMismatchError(
                f"expected checksum {expected_checksum}, computed {computed} for {filename}"
            )

        path = self.path_for(source=source, checksum=computed, filename=filename)

        if path.exists():
            existing = path.read_bytes()
            existing_checksum = hashlib.sha256(existing).hexdigest()
            if existing_checksum != computed:
                raise ChecksumMismatchError(
                    f"cached file at {path} has diverged from its checksum-derived path "
                    f"(expected {computed}, found {existing_checksum})"
                )
            return StoredDocument(
                source=source, checksum=computed, path=path, size=len(existing), already_cached=True
            )

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return StoredDocument(
            source=source, checksum=computed, path=path, size=len(content), already_cached=False
        )
