"""Ollama-backed model provider: local inference over Ollama's HTTP API.

Design constraints (Task 12 Step 6):
  - bounded context (num_ctx, default 4096 - the 8-B model's practical
    working set on an 8 GB GPU);
  - temperature 0 for analyst tools, passed through by the caller;
  - one concurrent generation on the 8 GB GPU, enforced by a process-local
    lock - two concurrent generate() calls would double VRAM pressure and
    is exactly the failure mode a single laptop GPU cannot absorb;
  - typed JSON validation via pydantic for structured_generate;
  - a hard timeout on every call;
  - no silent fallback - every failure raises ModelProviderError with a
    category. A user-facing answer must never be a fabricated response
    dressed up as a successful one.
"""

from __future__ import annotations

import json
import threading
import time
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from vichara_portfolio.model_gateway.ports import (
    GenerateResult,
    ModelErrorCategory,
    ModelInfo,
    ModelProviderError,
    StructuredGenerateResult,
)

T = TypeVar("T", bound=BaseModel)

DEFAULT_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "llama3.1:8b"
DEFAULT_NUM_CTX = 4096
# Real finding (2026-08-28): with no cap, a temperature-0 llama3.1:8b
# response to an open-ended analyst prompt kept generating past 344
# tokens without naturally stopping, at ~13 tok/s - slow and needlessly
# long for a surveillance answer. Capped rather than just raising the
# client timeout, since an analyst answer should be concise regardless.
DEFAULT_NUM_PREDICT = 400


class OllamaProvider:
    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
        num_ctx: int = DEFAULT_NUM_CTX,
        num_predict: int = DEFAULT_NUM_PREDICT,
        client: httpx.Client | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._num_ctx = num_ctx
        self._num_predict = num_predict
        self._client = client or httpx.Client(base_url=self._base_url)
        # One concurrent generation - see module docstring. A single
        # process-local lock is sufficient because this provider is meant
        # to be instantiated once per worker process, matching the SEC
        # rate limiter's "one process" design in shared/http.py.
        self._generation_lock = threading.Lock()

    def health(self) -> bool:
        try:
            response = self._client.get("/api/tags", timeout=2.0)
            response.raise_for_status()
        except (httpx.HTTPError, httpx.TimeoutException):
            return False
        return True

    def model_info(self) -> ModelInfo:
        return ModelInfo(provider_name="ollama", model_name=self._model)

    def generate(
        self, prompt: str, *, temperature: float = 0.0, timeout_seconds: float = 60.0
    ) -> GenerateResult:
        start = time.perf_counter()
        payload = self._request(
            {
                "model": self._model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_ctx": self._num_ctx,
                    "num_predict": self._num_predict,
                },
            },
            timeout_seconds=timeout_seconds,
        )
        text = str(payload.get("response", ""))
        return GenerateResult(
            text=text, model=self.model_info(), latency_seconds=time.perf_counter() - start
        )

    def structured_generate(
        self,
        prompt: str,
        *,
        schema: type[T],
        temperature: float = 0.0,
        timeout_seconds: float = 60.0,
    ) -> StructuredGenerateResult[T]:
        start = time.perf_counter()
        payload = self._request(
            {
                "model": self._model,
                "prompt": prompt,
                "stream": False,
                "format": schema.model_json_schema(),
                "options": {
                    "temperature": temperature,
                    "num_ctx": self._num_ctx,
                    "num_predict": self._num_predict,
                },
            },
            timeout_seconds=timeout_seconds,
        )
        raw_text = str(payload.get("response", ""))
        try:
            value = schema.model_validate(json.loads(raw_text))
        except (json.JSONDecodeError, ValidationError) as exc:
            raise ModelProviderError(
                ModelErrorCategory.INVALID_RESPONSE,
                f"ollama response did not validate against {schema.__name__}: {exc}",
            ) from exc

        return StructuredGenerateResult(
            value=value,
            model=self.model_info(),
            latency_seconds=time.perf_counter() - start,
            raw_text=raw_text,
        )

    def _request(self, body: dict[str, object], *, timeout_seconds: float) -> dict[str, object]:
        with self._generation_lock:
            try:
                response = self._client.post("/api/generate", json=body, timeout=timeout_seconds)
            except httpx.TimeoutException as exc:
                raise ModelProviderError(
                    ModelErrorCategory.TIMEOUT, f"ollama call timed out after {timeout_seconds}s"
                ) from exc
            except httpx.ConnectError as exc:
                raise ModelProviderError(
                    ModelErrorCategory.UNAVAILABLE, f"ollama not reachable at {self._base_url}"
                ) from exc

        if response.status_code == 429:
            raise ModelProviderError(
                ModelErrorCategory.RATE_LIMITED, "ollama rate limited the request"
            )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ModelProviderError(
                ModelErrorCategory.UNAVAILABLE, f"ollama returned HTTP {response.status_code}"
            ) from exc

        payload: dict[str, object] = response.json()
        return payload
