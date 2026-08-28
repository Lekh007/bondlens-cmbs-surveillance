"""Fixture-controlled model provider: no network, no GPU. This is the only
provider used in unit/CI tests, matching Settings.model_provider's default
under pytest (see backend/tests/conftest.py).
"""

from __future__ import annotations

import time
from typing import TypeVar

from pydantic import BaseModel

from vichara_portfolio.model_gateway.ports import (
    GenerateResult,
    ModelErrorCategory,
    ModelInfo,
    ModelProviderError,
    StructuredGenerateResult,
)

T = TypeVar("T", bound=BaseModel)

DEFAULT_TEXT_RESPONSE = "This is a deterministic fixture response."


class DeterministicProvider:
    def __init__(
        self,
        *,
        model_name: str = "deterministic-fixture",
        text_responses: dict[str, str] | None = None,
        structured_responses: dict[str, BaseModel] | None = None,
    ) -> None:
        self._model_name = model_name
        self._text_responses = text_responses or {}
        self._structured_responses = structured_responses or {}

    def health(self) -> bool:
        return True

    def model_info(self) -> ModelInfo:
        return ModelInfo(provider_name="deterministic", model_name=self._model_name)

    def generate(
        self, prompt: str, *, temperature: float = 0.0, timeout_seconds: float = 60.0
    ) -> GenerateResult:
        start = time.perf_counter()
        text = self._text_responses.get(prompt, DEFAULT_TEXT_RESPONSE)
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
        fixture = self._structured_responses.get(prompt)
        if fixture is None:
            raise ModelProviderError(
                ModelErrorCategory.INVALID_RESPONSE, f"no fixture registered for prompt: {prompt!r}"
            )
        if not isinstance(fixture, schema):
            actual = type(fixture).__name__
            raise ModelProviderError(
                ModelErrorCategory.INVALID_RESPONSE,
                f"fixture type {actual} does not match requested schema {schema.__name__}",
            )
        return StructuredGenerateResult(
            value=fixture,
            model=self.model_info(),
            latency_seconds=time.perf_counter() - start,
            raw_text=fixture.model_dump_json(),
        )
