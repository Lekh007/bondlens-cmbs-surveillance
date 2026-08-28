import httpx
import pytest
import respx

from vichara_portfolio.shared.http import (
    ContentTypeError,
    IdempotencyRequiredError,
    ResilientHttpClient,
    RetriesExhaustedError,
    SecRateLimiter,
)


@pytest.fixture
def sleeps() -> list[float]:
    return []


@pytest.fixture
def client(sleeps: list[float]) -> ResilientHttpClient:
    raw_client = httpx.Client()
    return ResilientHttpClient(
        raw_client,
        source_name="sec_edgar",
        max_retries=3,
        backoff_seconds=0.01,
        sleep=sleeps.append,
    )


@respx.mock
def test_200_json_returns_payload_and_provenance(client: ResilientHttpClient) -> None:
    url = "https://data.sec.gov/submissions/CIK0002110410.json"
    respx.get(url).mock(
        return_value=httpx.Response(200, json={"name": "Benchmark 2026-B42 Mortgage Trust"})
    )

    result = client.get_json(url, record_id="0002110410")

    assert result.payload == {"name": "Benchmark 2026-B42 Mortgage Trust"}
    assert result.source.source_name == "sec_edgar"
    assert result.source.source_url == url
    assert result.source.record_id == "0002110410"


@respx.mock
def test_429_honors_retry_after_then_succeeds(
    client: ResilientHttpClient, sleeps: list[float]
) -> None:
    url = "https://data.sec.gov/submissions/CIK0002110410.json"
    route = respx.get(url).mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "2"}),
            httpx.Response(200, json={"ok": True}),
        ]
    )

    result = client.get_json(url)

    assert route.call_count == 2
    assert result.payload == {"ok": True}
    assert sleeps == [2.0]


@respx.mock
def test_500_retries_with_backoff_then_succeeds(
    client: ResilientHttpClient, sleeps: list[float]
) -> None:
    url = "https://data.sec.gov/submissions/CIK0002110410.json"
    route = respx.get(url).mock(
        side_effect=[
            httpx.Response(500),
            httpx.Response(500),
            httpx.Response(200, json={"ok": True}),
        ]
    )

    result = client.get_json(url)

    assert route.call_count == 3
    assert result.payload == {"ok": True}
    assert len(sleeps) == 2


@respx.mock
def test_500_exhausts_retries_and_raises(client: ResilientHttpClient) -> None:
    url = "https://data.sec.gov/submissions/CIK0002110410.json"
    respx.get(url).mock(return_value=httpx.Response(500))

    with pytest.raises(RetriesExhaustedError):
        client.get_json(url)


@respx.mock
def test_timeout_retries_then_raises(client: ResilientHttpClient) -> None:
    url = "https://data.sec.gov/submissions/CIK0002110410.json"
    respx.get(url).mock(side_effect=httpx.TimeoutException("timed out"))

    with pytest.raises(RetriesExhaustedError):
        client.get_json(url)


@respx.mock
def test_invalid_content_type_is_rejected_without_retry(client: ResilientHttpClient) -> None:
    url = "https://data.sec.gov/submissions/CIK0002110410.json"
    route = respx.get(url).mock(return_value=httpx.Response(200, text="<html>not json</html>"))

    with pytest.raises(ContentTypeError):
        client.get_json(url)

    assert route.call_count == 1, "a content-type mismatch is not transient and must not be retried"


@respx.mock
def test_get_bytes_rejects_unexpected_content_type(client: ResilientHttpClient) -> None:
    url = "https://www.sec.gov/Archives/edgar/data/2110410/x/exh_102.xml"
    respx.get(url).mock(return_value=httpx.Response(200, headers={"content-type": "text/html"}))

    with pytest.raises(ContentTypeError):
        client.get_bytes(url, allowed_content_types=("application/xml", "text/xml"))


@respx.mock
def test_immutable_get_bytes_is_only_fetched_once(client: ResilientHttpClient) -> None:
    url = "https://www.sec.gov/Archives/edgar/data/2110410/x/exh_102.xml"
    route = respx.get(url).mock(
        return_value=httpx.Response(
            200, content=b"<assetData/>", headers={"content-type": "application/xml"}
        )
    )

    first = client.get_bytes(url, allowed_content_types=("application/xml",), immutable=True)
    second = client.get_bytes(url, allowed_content_types=("application/xml",), immutable=True)

    assert route.call_count == 1, "an immutable resource must not be re-fetched"
    assert first.payload == second.payload == b"<assetData/>"
    assert first.source.retrieved_at == second.source.retrieved_at


@respx.mock
def test_post_without_idempotent_flag_is_never_retried(client: ResilientHttpClient) -> None:
    url = "https://data.sec.gov/some-write-endpoint"
    respx.post(url).mock(return_value=httpx.Response(500))

    with pytest.raises(httpx.HTTPStatusError):
        client.post_json(url, json={"x": 1}, idempotent=False)


@respx.mock
def test_post_requires_explicit_idempotent_flag_to_retry(client: ResilientHttpClient) -> None:
    url = "https://data.sec.gov/some-write-endpoint"
    route = respx.post(url).mock(
        side_effect=[httpx.Response(500), httpx.Response(200, json={"ok": True})]
    )

    result = client.post_json(url, json={"x": 1}, idempotent=True)

    assert route.call_count == 2
    assert result.payload == {"ok": True}


def test_post_raises_without_idempotent_flag_at_all() -> None:
    raw_client = httpx.Client()
    client = ResilientHttpClient(raw_client, source_name="sec_edgar")
    with pytest.raises(IdempotencyRequiredError):
        client.post_json("https://data.sec.gov/x", json={})


def test_sec_rate_limiter_enforces_minimum_interval() -> None:
    clock = iter([0.0, 0.05, 0.05])
    sleeps: list[float] = []
    limiter = SecRateLimiter(requests_per_second=8.0, sleep=sleeps.append)
    limiter._clock = lambda: next(clock)  # type: ignore[attr-defined]

    limiter.wait()
    limiter.wait()

    assert sleeps == [pytest.approx(1 / 8 - 0.05)]


@respx.mock
def test_sec_requests_carry_the_configured_user_agent() -> None:
    url = "https://data.sec.gov/submissions/CIK0002110410.json"
    route = respx.get(url).mock(return_value=httpx.Response(200, json={}))

    raw_client = httpx.Client()
    client = ResilientHttpClient(raw_client, source_name="sec_edgar")
    client.get_json(url, headers={"User-Agent": "Vichara-Portfolio/0.1 (kasarlekhraj@gmail.com)"})

    sent_request = route.calls.last.request
    assert sent_request.headers["User-Agent"] == "Vichara-Portfolio/0.1 (kasarlekhraj@gmail.com)"
