"""Model provider contract. Both providers (deterministic, ollama) implement
the exact same shape so the LangGraph agent (Task 13) never needs to know
which one is behind it - deterministic is the only one used in unit/CI
tests, ollama is real local inference. Errors are always raised as a
ModelProviderError with a category; a provider must never silently
substitute a fallback answer for a user-facing response.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class ModelErrorCategory(StrEnum):
    TIMEOUT = "timeout"
    UNAVAILABLE = "unavailable"
    RATE_LIMITED = "rate_limited"
    INVALID_RESPONSE = "invalid_response"


class ModelProviderError(Exception):
    def __init__(self, category: ModelErrorCategory, message: str) -> None:
        super().__init__(message)
        self.category = category


@dataclass(frozen=True)
class ModelInfo:
    provider_name: str
    model_name: str


@dataclass(frozen=True)
class GenerateResult:
    text: str
    model: ModelInfo
    latency_seconds: float


@dataclass(frozen=True)
class StructuredGenerateResult[T: BaseModel]:
    value: T
    model: ModelInfo
    latency_seconds: float
    raw_text: str


class ModelProvider(Protocol):
    def health(self) -> bool: ...

    def model_info(self) -> ModelInfo: ...

    def generate(
        self, prompt: str, *, temperature: float = 0.0, timeout_seconds: float = 60.0
    ) -> GenerateResult: ...

    def structured_generate(
        self,
        prompt: str,
        *,
        schema: type[T],
        temperature: float = 0.0,
        timeout_seconds: float = 60.0,
    ) -> StructuredGenerateResult[T]: ...
