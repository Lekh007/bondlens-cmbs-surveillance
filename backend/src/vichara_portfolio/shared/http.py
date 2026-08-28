"""Resilient HTTP client with bounded retries, provenance capture, and a
process-local rate limiter for SEC's 8 req/s self-imposed ceiling (design
doc section 3, SEC access policy - below the published 10 req/s limit).

Retries never mask a content-type mismatch: that is a business-logic
error (wrong endpoint, unexpected redirect to an HTML error page), not a
transient one, and retrying it wastes the retry budget on something that
will never change.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx

from vichara_portfolio.shared.provenance import SourceRef

DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_SECONDS = 0.5
SEC_REQUESTS_PER_SECOND = 8.0


class ContentTypeError(Exception):
    """A response's Content-Type did not match what was expected. Never retried."""


class RetriesExhaustedError(Exception):
    """All retry attempts failed."""


class IdempotencyRequiredError(Exception):
    """A POST was issued without an explicit idempotent=True/False decision."""


@dataclass(frozen=True)
class HttpResult:
    payload: Any
    source: SourceRef


class SecRateLimiter:
    """Process-local token-bucket limiter, one call gate per process.

    Not distributed - this is why the design doc requires SEC ingestion
    worker concurrency to remain one; two processes each running their own
    limiter would double the effective rate.
    """

    def __init__(
        self,
        requests_per_second: float = SEC_REQUESTS_PER_SECOND,
        *,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._min_interval = 1.0 / requests_per_second
        self._sleep = sleep
        self._clock: Callable[[], float] = time.monotonic
        self._last_call: float | None = None

    def wait(self) -> None:
        now = self._clock()
        if self._last_call is not None:
            remaining = self._min_interval - (now - self._last_call)
            if remaining > 0:
                self._sleep(remaining)
        self._last_call = now


class ResilientHttpClient:
    def __init__(
        self,
        client: httpx.Client,
        *,
        source_name: str,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_seconds: float = DEFAULT_BACKOFF_SECONDS,
        sleep: Callable[[float], None] = time.sleep,
        rate_limiter: SecRateLimiter | None = None,
    ) -> None:
        self._client = client
        self._source_name = source_name
        self._max_retries = max_retries
        self._backoff_seconds = backoff_seconds
        self._sleep = sleep
        self._rate_limiter = rate_limiter
        self._immutable_cache: dict[str, HttpResult] = {}

    def get_json(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        record_id: str | None = None,
    ) -> HttpResult:
        response = self._request_with_retries("GET", url, headers=headers)
        return self._json_result(response, url, record_id=record_id)

    def get_bytes(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        allowed_content_types: tuple[str, ...] | None = None,
        record_id: str | None = None,
        immutable: bool = False,
    ) -> HttpResult:
        if immutable and url in self._immutable_cache:
            return self._immutable_cache[url]

        response = self._request_with_retries("GET", url, headers=headers)
        content_type = response.headers.get("content-type", "")
        if allowed_content_types and not any(a in content_type for a in allowed_content_types):
            raise ContentTypeError(
                f"expected one of {allowed_content_types}, got {content_type!r} from {url}"
            )
        source = SourceRef.now(source_name=self._source_name, source_url=url, record_id=record_id)
        result = HttpResult(payload=response.content, source=source)
        if immutable:
            self._immutable_cache[url] = result
        return result

    def post_json(
        self,
        url: str,
        *,
        json: Any,
        idempotent: bool | None = None,
        headers: dict[str, str] | None = None,
    ) -> HttpResult:
        if idempotent is None:
            raise IdempotencyRequiredError(
                f"post_json({url}) requires an explicit idempotent=True/False decision"
            )
        if idempotent:
            response = self._request_with_retries("POST", url, headers=headers, json=json)
        else:
            response = self._dispatch("POST", url, headers=headers, json=json)
            response.raise_for_status()
        return self._json_result(response, url)

    def _json_result(
        self, response: httpx.Response, url: str, *, record_id: str | None = None
    ) -> HttpResult:
        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            raise ContentTypeError(f"expected application/json, got {content_type!r} from {url}")
        source = SourceRef.now(source_name=self._source_name, source_url=url, record_id=record_id)
        return HttpResult(payload=response.json(), source=source)

    def _dispatch(
        self, method: str, url: str, *, headers: dict[str, str] | None, json: Any = None
    ) -> httpx.Response:
        if self._rate_limiter is not None:
            self._rate_limiter.wait()
        return self._client.request(method, url, headers=headers, json=json)

    def _request_with_retries(
        self, method: str, url: str, *, headers: dict[str, str] | None = None, json: Any = None
    ) -> httpx.Response:
        attempt = 0
        while True:
            attempt += 1
            try:
                response = self._dispatch(method, url, headers=headers, json=json)
            except httpx.TimeoutException:
                if attempt > self._max_retries:
                    msg = f"timed out after {attempt} attempts: {url}"
                    raise RetriesExhaustedError(msg) from None
                self._sleep(self._backoff_seconds * attempt)
                continue

            if response.status_code == 429:
                if attempt > self._max_retries:
                    raise RetriesExhaustedError(f"rate limited after {attempt} attempts: {url}")
                retry_after = response.headers.get("retry-after")
                delay = float(retry_after) if retry_after else self._backoff_seconds * attempt
                self._sleep(delay)
                continue

            if response.status_code >= 500:
                if attempt > self._max_retries:
                    raise RetriesExhaustedError(
                        f"server error {response.status_code} after {attempt} attempts: {url}"
                    )
                self._sleep(self._backoff_seconds * attempt)
                continue

            response.raise_for_status()
            return response
