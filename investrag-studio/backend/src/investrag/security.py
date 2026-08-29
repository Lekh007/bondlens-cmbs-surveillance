from __future__ import annotations

import shutil
import zipfile
from pathlib import Path


class UnsafeArchiveError(ValueError):
    pass


def safe_extract_zip(
    archive_path: Path,
    destination: Path,
    *,
    max_files: int = 500,
    max_uncompressed_bytes: int = 250 * 1024 * 1024,
    max_depth: int = 12,
) -> list[Path]:
    """Extract a ZIP without path traversal, symlink or expansion-bomb surprises."""

    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    extracted: list[Path] = []
    total_bytes = 0
    with zipfile.ZipFile(archive_path) as archive:
        members = archive.infolist()
        if len(members) > max_files:
            raise UnsafeArchiveError(f"archive contains {len(members)} files; limit is {max_files}")
        for member in members:
            raw_name = member.filename.replace("\\", "/")
            path = Path(raw_name)
            if path.is_absolute() or ".." in path.parts:
                raise UnsafeArchiveError(f"archive member escapes extraction directory: {member.filename}")
            if len(path.parts) > max_depth:
                raise UnsafeArchiveError(f"archive member exceeds nesting limit: {member.filename}")
            is_symlink = (member.external_attr >> 16) & 0o170000 == 0o120000
            if is_symlink:
                raise UnsafeArchiveError(f"symlink archive member is not allowed: {member.filename}")
            total_bytes += member.file_size
            if total_bytes > max_uncompressed_bytes:
                raise UnsafeArchiveError("archive exceeds uncompressed-size limit")
            target = (destination / path).resolve()
            if destination not in target.parents and target != destination:
                raise UnsafeArchiveError(f"archive member resolves outside destination: {member.filename}")
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)
            extracted.append(target)
    return extracted
