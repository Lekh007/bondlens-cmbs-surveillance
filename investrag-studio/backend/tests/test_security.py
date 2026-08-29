import zipfile
from pathlib import Path

import pytest

from investrag.security import UnsafeArchiveError, safe_extract_zip


def test_safe_zip_rejects_parent_traversal(tmp_path: Path) -> None:
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("../escape.txt", "no")
    with pytest.raises(UnsafeArchiveError):
        safe_extract_zip(archive, tmp_path / "out")
