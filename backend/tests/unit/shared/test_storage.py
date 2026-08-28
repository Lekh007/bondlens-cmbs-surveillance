import hashlib

import pytest

from vichara_portfolio.shared.storage import ChecksumMismatchError, RawDocumentStore


@pytest.fixture
def store(tmp_path):
    return RawDocumentStore(raw_root=tmp_path)


def test_write_returns_checksum_path_and_size(store, tmp_path) -> None:
    content = b"<ABS-EE>fixture</ABS-EE>"
    doc = store.write(source="sec", filename="bmk26b42_absee-202607.htm", content=content)

    assert doc.checksum == hashlib.sha256(content).hexdigest()
    assert doc.size == len(content)
    assert doc.path.exists()
    assert doc.path.read_bytes() == content
    assert doc.path.is_relative_to(tmp_path)
    assert doc.already_cached is False


def test_identical_content_is_cache_hit_not_rewritten(store) -> None:
    content = b"same bytes every time"
    first = store.write(source="sec", filename="exh_102.xml", content=content)
    mtime_before = first.path.stat().st_mtime_ns

    second = store.write(source="sec", filename="exh_102.xml", content=content)

    assert second.already_cached is True
    assert second.checksum == first.checksum
    assert second.path == first.path
    assert second.path.stat().st_mtime_ns == mtime_before


def test_different_content_never_overwrites_existing_path(store) -> None:
    store.write(source="sec", filename="exh_102.xml", content=b"version one")

    # Different content hashes to a different checksum, hence a different
    # content-addressed path - the original file must be untouched.
    second = store.write(source="sec", filename="exh_102.xml", content=b"version two")

    original_path = store.path_for(
        source="sec", checksum=hashlib.sha256(b"version one").hexdigest(), filename="exh_102.xml"
    )
    assert original_path.read_bytes() == b"version one"
    assert second.path.read_bytes() == b"version two"
    assert original_path != second.path


def test_expected_checksum_mismatch_is_rejected(store) -> None:
    content = b"downloaded bytes"
    wrong_checksum = hashlib.sha256(b"not the same bytes").hexdigest()

    with pytest.raises(ChecksumMismatchError):
        store.write(
            source="sec",
            filename="exh_102.xml",
            content=content,
            expected_checksum=wrong_checksum,
        )


def test_expected_checksum_match_succeeds(store) -> None:
    content = b"downloaded bytes"
    correct_checksum = hashlib.sha256(content).hexdigest()

    doc = store.write(
        source="sec",
        filename="exh_102.xml",
        content=content,
        expected_checksum=correct_checksum,
    )

    assert doc.checksum == correct_checksum


def test_corrupted_cache_on_disk_is_detected_not_silently_served(store) -> None:
    content = b"original"
    doc = store.write(source="sec", filename="f.xml", content=content)

    # Simulate on-disk corruption at the checksum-derived path.
    doc.path.write_bytes(b"corrupted")

    with pytest.raises(ChecksumMismatchError):
        store.write(source="sec", filename="f.xml", content=content)
