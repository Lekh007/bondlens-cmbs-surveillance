import json
from pathlib import Path

import httpx
import pytest
import respx

from vichara_portfolio.bondlens.adapters.filing_store import (
    ExhibitResolutionError,
    FilingStore,
    build_accession_txt_url,
    build_exhibit_url,
    parse_document_index,
)
from vichara_portfolio.shared.http import ResilientHttpClient
from vichara_portfolio.shared.storage import RawDocumentStore

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "sec"
MAY_SUBMISSION_TXT = (FIXTURES / "filing_submission_may.txt").read_text(encoding="utf-8")
MAY_INDEX_JSON = json.loads((FIXTURES / "filing_index_missing_exhibit_may.json").read_text())

TEST_USER_AGENT = "Vichara-Portfolio/0.1 (kasarlekhraj@gmail.com)"
CIK = "0002110410"
ACCESSION = "0001888524-26-010373"
TXT_URL = build_accession_txt_url(CIK, ACCESSION)


@pytest.fixture
def filing_store(tmp_path) -> FilingStore:
    http = ResilientHttpClient(httpx.Client(), source_name="sec_edgar")
    store = RawDocumentStore(raw_root=tmp_path)
    return FilingStore(http, store, user_agent=TEST_USER_AGENT)


def test_index_json_omits_the_asset_exhibit_this_is_the_measured_bug() -> None:
    """Documents the actual bug: real index.json for this accession lists only
    the ABS-EE cover .htm. If SEC ever fixes this, this test starts failing
    and the fixture (and this comment) should be revisited."""
    names = {item["name"] for item in MAY_INDEX_JSON["directory"]["item"]}
    assert "exh_102.xml" not in names
    assert "bmk26b42_absee-202605.htm" in names


def test_txt_header_lists_the_exhibit_index_json_omits() -> None:
    documents = parse_document_index(MAY_SUBMISSION_TXT, cik=CIK, accession=ACCESSION)

    filenames = {d.filename for d in documents}
    assert "exh_102.xml" in filenames, "the .txt header must find what index.json hides"


def test_parses_abs_ee_ex102_and_ex103_with_correct_types() -> None:
    documents = parse_document_index(MAY_SUBMISSION_TXT, cik=CIK, accession=ACCESSION)

    by_filename = {d.filename: d for d in documents}
    assert by_filename["bmk26b42_absee-202605.htm"].filing_type == "ABS-EE"
    assert by_filename["exh_102.xml"].filing_type == "EX-102"
    assert by_filename["exh_103.xml"].filing_type == "EX-103"
    assert len(documents) == 3


def test_document_urls_point_at_the_accession_directory() -> None:
    documents = parse_document_index(MAY_SUBMISSION_TXT, cik=CIK, accession=ACCESSION)

    exhibit = next(d for d in documents if d.filename == "exh_102.xml")
    assert (
        exhibit.url
        == "https://www.sec.gov/Archives/edgar/data/2110410/000188852426010373/exh_102.xml"
    )


def test_accession_txt_url_uses_unpadded_cik_and_hyphenated_accession() -> None:
    url = build_accession_txt_url("0002110410", "0001888524-26-010373")
    assert url == (
        "https://www.sec.gov/Archives/edgar/data/2110410/"
        "000188852426010373/0001888524-26-010373.txt"
    )


def test_exhibit_url_uses_accession_without_hyphens_for_the_directory() -> None:
    url = build_exhibit_url("0002110410", "0001888524-26-010373", "exh_102.xml")
    assert "/000188852426010373/exh_102.xml" in url
    assert "-" not in url.split("/")[-2]


def test_empty_document_index_raises() -> None:
    with pytest.raises(ExhibitResolutionError):
        parse_document_index("no documents here", cik=CIK, accession=ACCESSION)


def test_non_sec_host_is_rejected(filing_store: FilingStore) -> None:
    from vichara_portfolio.bondlens.adapters.filing_store import FilingDocument

    evil = FilingDocument(
        filing_type="EX-102", filename="exh_102.xml", url="https://evil.example/exh_102.xml"
    )
    with pytest.raises(ExhibitResolutionError):
        filing_store.download(evil, accession=ACCESSION, allowed_content_types=("text/xml",))


def test_path_traversal_is_rejected(filing_store: FilingStore) -> None:
    from vichara_portfolio.bondlens.adapters.filing_store import FilingDocument

    traversal = FilingDocument(
        filing_type="EX-102",
        filename="exh_102.xml",
        url="https://www.sec.gov/Archives/edgar/data/2110410/../../../etc/passwd",
    )
    with pytest.raises(ExhibitResolutionError):
        filing_store.download(traversal, accession=ACCESSION, allowed_content_types=("text/xml",))


@respx.mock
def test_list_documents_fetches_the_txt_header_not_index_json(filing_store: FilingStore) -> None:
    route = respx.get(TXT_URL).mock(
        return_value=httpx.Response(
            200, text=MAY_SUBMISSION_TXT, headers={"content-type": "text/plain"}
        )
    )

    documents, source = filing_store.list_documents(cik=CIK, accession=ACCESSION)

    assert route.called
    assert any(d.filename == "exh_102.xml" for d in documents)
    assert source.source_url == TXT_URL


@respx.mock
def test_download_writes_to_content_addressed_storage_and_returns_source(
    filing_store: FilingStore,
) -> None:
    from vichara_portfolio.bondlens.adapters.filing_store import FilingDocument

    exhibit_url = build_exhibit_url(CIK, ACCESSION, "exh_102.xml")
    content = b"<assetData>fixture</assetData>"
    respx.get(exhibit_url).mock(
        return_value=httpx.Response(200, content=content, headers={"content-type": "text/xml"})
    )
    document = FilingDocument(filing_type="EX-102", filename="exh_102.xml", url=exhibit_url)

    stored, source = filing_store.download(
        document, accession=ACCESSION, allowed_content_types=("text/xml",)
    )

    assert stored.path.read_bytes() == content
    assert stored.already_cached is False
    assert source.source_url == exhibit_url


@respx.mock
def test_download_is_a_cache_hit_on_second_call_no_second_request(
    filing_store: FilingStore,
) -> None:
    from vichara_portfolio.bondlens.adapters.filing_store import FilingDocument

    exhibit_url = build_exhibit_url(CIK, ACCESSION, "exh_102.xml")
    route = respx.get(exhibit_url).mock(
        return_value=httpx.Response(
            200, content=b"same bytes", headers={"content-type": "text/xml"}
        )
    )
    document = FilingDocument(filing_type="EX-102", filename="exh_102.xml", url=exhibit_url)

    first, _ = filing_store.download(
        document, accession=ACCESSION, allowed_content_types=("text/xml",)
    )
    second, _ = filing_store.download(
        document, accession=ACCESSION, allowed_content_types=("text/xml",)
    )

    assert route.call_count == 1, (
        "immutable=True on the HTTP layer must prevent a second network call"
    )
    assert second.already_cached is True
    assert first.path == second.path


@pytest.mark.live
def test_live_may_filing_exhibit_download(tmp_path) -> None:
    """Live SEC round-trip against the exact accession where index.json is
    measured to omit the asset exhibit.

    Run with:
        $env:EXTERNAL_NETWORK_ENABLED = 'true'
        uv run pytest -m live tests/contract/bondlens/test_filing_store.py -q
    """
    http = ResilientHttpClient(httpx.Client(), source_name="sec_edgar")
    store = RawDocumentStore(raw_root=tmp_path)
    live_store = FilingStore(http, store, user_agent=TEST_USER_AGENT)

    documents, _source = live_store.list_documents(cik=CIK, accession=ACCESSION)
    exhibit = next(d for d in documents if d.filing_type == "EX-102")

    stored, source = live_store.download(
        exhibit, accession=ACCESSION, allowed_content_types=("text/xml", "application/xml")
    )

    assert stored.size > 500_000, "the real May exh_102.xml is 585,970 bytes"
    assert stored.path.exists()
    assert source.source_url == exhibit.url
