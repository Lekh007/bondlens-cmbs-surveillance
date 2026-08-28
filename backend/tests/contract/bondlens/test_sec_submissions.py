import json
from datetime import date
from pathlib import Path

import httpx
import pytest
import respx

from vichara_portfolio.bondlens.adapters.sec_edgar import SecEdgarClient
from vichara_portfolio.shared.http import ResilientHttpClient

FIXTURE_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "sec" / "submissions_minimal.json"
FIXTURE_JSON = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
TEST_USER_AGENT = "Vichara-Portfolio/0.1 (kasarlekhraj@gmail.com)"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK0002110410.json"


@pytest.fixture
def sec_client() -> SecEdgarClient:
    http = ResilientHttpClient(httpx.Client(), source_name="sec_edgar")
    return SecEdgarClient(http, user_agent=TEST_USER_AGENT)


@respx.mock
def test_cik_is_zero_padded_to_ten_digits(sec_client: SecEdgarClient) -> None:
    route = respx.get(SUBMISSIONS_URL).mock(return_value=httpx.Response(200, json=FIXTURE_JSON))

    sec_client.list_filings("2110410")

    assert route.called


@respx.mock
def test_entity_name_is_captured(sec_client: SecEdgarClient) -> None:
    respx.get(SUBMISSIONS_URL).mock(return_value=httpx.Response(200, json=FIXTURE_JSON))

    result = sec_client.list_filings("2110410")

    assert "Benchmark 2026-B42" in result.entity_name


@respx.mock
def test_form_filter_returns_only_requested_forms(sec_client: SecEdgarClient) -> None:
    respx.get(SUBMISSIONS_URL).mock(return_value=httpx.Response(200, json=FIXTURE_JSON))

    result = sec_client.list_filings("0002110410", forms=("ABS-EE",))

    assert result.filings, "expected at least one ABS-EE filing"
    assert all(f.form_type == "ABS-EE" for f in result.filings)
    assert len(result.filings) == 3


@respx.mock
def test_accession_number_is_normalized_with_hyphens(sec_client: SecEdgarClient) -> None:
    respx.get(SUBMISSIONS_URL).mock(return_value=httpx.Response(200, json=FIXTURE_JSON))

    result = sec_client.list_filings("2110410", forms=("8-K",))

    assert result.filings[0].accession_number == "0001888524-26-012442"


@respx.mock
def test_filings_are_returned_in_chronological_order(sec_client: SecEdgarClient) -> None:
    respx.get(SUBMISSIONS_URL).mock(return_value=httpx.Response(200, json=FIXTURE_JSON))

    result = sec_client.list_filings("2110410", forms=("ABS-EE",))

    dates = [f.filing_date for f in result.filings]
    assert dates == sorted(dates), "fixture is newest-first; client must return oldest-first"
    assert dates == [date(2026, 5, 29), date(2026, 6, 30), date(2026, 7, 30)]


@respx.mock
def test_report_date_and_primary_document_are_captured(sec_client: SecEdgarClient) -> None:
    respx.get(SUBMISSIONS_URL).mock(return_value=httpx.Response(200, json=FIXTURE_JSON))

    result = sec_client.list_filings("2110410", forms=("ABS-EE",))
    july = next(f for f in result.filings if f.filing_date == date(2026, 7, 30))

    assert july.report_date == date(2026, 7, 17)
    assert july.primary_document == "bmk26b42_absee-202607.htm"


@respx.mock
def test_missing_report_date_is_none_not_empty_string(sec_client: SecEdgarClient) -> None:
    respx.get(SUBMISSIONS_URL).mock(return_value=httpx.Response(200, json=FIXTURE_JSON))

    result = sec_client.list_filings("2110410", forms=("FWP",))

    assert result.filings[0].report_date is None


@respx.mock
def test_list_filings_returns_a_source_ref(sec_client: SecEdgarClient) -> None:
    respx.get(SUBMISSIONS_URL).mock(return_value=httpx.Response(200, json=FIXTURE_JSON))

    result = sec_client.list_filings("2110410")

    assert result.source.source_name == "sec_edgar"
    assert result.source.source_url == SUBMISSIONS_URL
    assert result.source.record_id == "0002110410"


@respx.mock
def test_request_carries_the_configured_user_agent(sec_client: SecEdgarClient) -> None:
    route = respx.get(SUBMISSIONS_URL).mock(return_value=httpx.Response(200, json=FIXTURE_JSON))

    sec_client.list_filings("2110410")

    assert route.calls.last.request.headers["User-Agent"] == TEST_USER_AGENT


@pytest.mark.live
def test_live_benchmark_2026_b42_submissions(sec_client: SecEdgarClient) -> None:
    """Live SEC call - excluded by default (pytest addopts = -m 'not live').

    Run with:
        $env:EXTERNAL_NETWORK_ENABLED = 'true'
        uv run pytest -m live tests/contract/bondlens/test_sec_submissions.py -q
    """
    result = sec_client.list_filings("0002110410", forms=("ABS-EE",))

    assert "Benchmark 2026-B42" in result.entity_name
    assert result.filings, "expected at least one live ABS-EE filing for Benchmark 2026-B42"
    assert len(result.filings) >= 4
    assert result.source.source_url == SUBMISSIONS_URL
