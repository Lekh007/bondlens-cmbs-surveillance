"""Shared contract for every ModelProvider implementation: health,
generate, structured_generate, model_info, latency, and error categories.

DeterministicProvider is exercised fully here with no network. OllamaProvider
is exercised against a mocked httpx client (respx) for the same contract
plus its specific error paths - no real Ollama server needed for these.
The one test that needs the real server is @pytest.mark.live, at the
bottom of this file.
"""

from __future__ import annotations

import httpx
import pytest
import respx
from pydantic import BaseModel

from vichara_portfolio.model_gateway.deterministic import DeterministicProvider
from vichara_portfolio.model_gateway.ollama import OllamaProvider
from vichara_portfolio.model_gateway.ports import ModelErrorCategory, ModelProviderError


class Verdict(BaseModel):
    label: str
    confidence: float


# --------------------------------------------------------------------------
# DeterministicProvider - the full contract, no network
# --------------------------------------------------------------------------


def test_deterministic_health_is_always_true() -> None:
    assert DeterministicProvider().health() is True


def test_deterministic_model_info() -> None:
    info = DeterministicProvider(model_name="fixture-v1").model_info()
    assert info.provider_name == "deterministic"
    assert info.model_name == "fixture-v1"


def test_deterministic_generate_returns_registered_response() -> None:
    provider = DeterministicProvider(text_responses={"hello": "world"})
    result = provider.generate("hello")
    assert result.text == "world"
    assert result.model.provider_name == "deterministic"
    assert result.latency_seconds >= 0


def test_deterministic_generate_falls_back_to_default_for_unregistered_prompt() -> None:
    result = DeterministicProvider().generate("anything")
    assert result.text


def test_deterministic_structured_generate_returns_registered_fixture() -> None:
    verdict = Verdict(label="current", confidence=0.9)
    provider = DeterministicProvider(structured_responses={"assess loan 30": verdict})
    result = provider.structured_generate("assess loan 30", schema=Verdict)
    assert result.value == verdict
    assert result.raw_text == verdict.model_dump_json()


def test_deterministic_structured_generate_raises_for_unregistered_prompt() -> None:
    with pytest.raises(ModelProviderError) as exc_info:
        DeterministicProvider().structured_generate("unregistered", schema=Verdict)
    assert exc_info.value.category == ModelErrorCategory.INVALID_RESPONSE


def test_deterministic_structured_generate_raises_for_schema_mismatch() -> None:
    class OtherSchema(BaseModel):
        x: int

    provider = DeterministicProvider(structured_responses={"p": Verdict(label="x", confidence=0.1)})
    with pytest.raises(ModelProviderError) as exc_info:
        provider.structured_generate("p", schema=OtherSchema)
    assert exc_info.value.category == ModelErrorCategory.INVALID_RESPONSE


# --------------------------------------------------------------------------
# OllamaProvider - same contract, mocked HTTP
# --------------------------------------------------------------------------


@pytest.fixture
def ollama() -> OllamaProvider:
    return OllamaProvider(client=httpx.Client(base_url="http://127.0.0.1:11434"))


@respx.mock
def test_ollama_health_true_when_reachable(ollama: OllamaProvider) -> None:
    respx.get("http://127.0.0.1:11434/api/tags").mock(
        return_value=httpx.Response(200, json={"models": []})
    )
    assert ollama.health() is True


@respx.mock
def test_ollama_health_false_when_unreachable(ollama: OllamaProvider) -> None:
    respx.get("http://127.0.0.1:11434/api/tags").mock(side_effect=httpx.ConnectError("refused"))
    assert ollama.health() is False


def test_ollama_model_info() -> None:
    info = OllamaProvider(model="llama3.1:8b").model_info()
    assert info.provider_name == "ollama"
    assert info.model_name == "llama3.1:8b"


@respx.mock
def test_ollama_generate_success(ollama: OllamaProvider) -> None:
    respx.post("http://127.0.0.1:11434/api/generate").mock(
        return_value=httpx.Response(200, json={"response": "the answer"})
    )
    result = ollama.generate("question", temperature=0.0)
    assert result.text == "the answer"
    assert result.model.provider_name == "ollama"


@respx.mock
def test_ollama_generate_sends_temperature_and_num_ctx(ollama: OllamaProvider) -> None:
    route = respx.post("http://127.0.0.1:11434/api/generate").mock(
        return_value=httpx.Response(200, json={"response": "ok"})
    )
    ollama.generate("question", temperature=0.0)
    sent = route.calls.last.request.content
    import json as _json

    body = _json.loads(sent)
    assert body["options"]["temperature"] == 0.0
    assert body["options"]["num_ctx"] == 4096
    assert body["options"]["num_predict"] == 400


@respx.mock
def test_ollama_generate_timeout_raises_timeout_category(ollama: OllamaProvider) -> None:
    respx.post("http://127.0.0.1:11434/api/generate").mock(
        side_effect=httpx.TimeoutException("slow")
    )
    with pytest.raises(ModelProviderError) as exc_info:
        ollama.generate("question", timeout_seconds=1.0)
    assert exc_info.value.category == ModelErrorCategory.TIMEOUT


@respx.mock
def test_ollama_generate_connection_error_raises_unavailable_category(
    ollama: OllamaProvider,
) -> None:
    respx.post("http://127.0.0.1:11434/api/generate").mock(
        side_effect=httpx.ConnectError("refused")
    )
    with pytest.raises(ModelProviderError) as exc_info:
        ollama.generate("question")
    assert exc_info.value.category == ModelErrorCategory.UNAVAILABLE


@respx.mock
def test_ollama_generate_429_raises_rate_limited_category(ollama: OllamaProvider) -> None:
    respx.post("http://127.0.0.1:11434/api/generate").mock(return_value=httpx.Response(429))
    with pytest.raises(ModelProviderError) as exc_info:
        ollama.generate("question")
    assert exc_info.value.category == ModelErrorCategory.RATE_LIMITED


@respx.mock
def test_ollama_generate_5xx_raises_unavailable_category(ollama: OllamaProvider) -> None:
    respx.post("http://127.0.0.1:11434/api/generate").mock(return_value=httpx.Response(500))
    with pytest.raises(ModelProviderError) as exc_info:
        ollama.generate("question")
    assert exc_info.value.category == ModelErrorCategory.UNAVAILABLE


@respx.mock
def test_ollama_structured_generate_success(ollama: OllamaProvider) -> None:
    respx.post("http://127.0.0.1:11434/api/generate").mock(
        return_value=httpx.Response(
            200, json={"response": '{"label": "delinquent", "confidence": 0.8}'}
        )
    )
    result = ollama.structured_generate("assess", schema=Verdict)
    assert result.value == Verdict(label="delinquent", confidence=0.8)


@respx.mock
def test_ollama_structured_generate_sends_json_schema_as_format(ollama: OllamaProvider) -> None:
    route = respx.post("http://127.0.0.1:11434/api/generate").mock(
        return_value=httpx.Response(200, json={"response": '{"label": "x", "confidence": 0.1}'})
    )
    ollama.structured_generate("assess", schema=Verdict)
    import json as _json

    body = _json.loads(route.calls.last.request.content)
    assert body["format"] == Verdict.model_json_schema()


@respx.mock
def test_ollama_structured_generate_invalid_json_raises_invalid_response(
    ollama: OllamaProvider,
) -> None:
    respx.post("http://127.0.0.1:11434/api/generate").mock(
        return_value=httpx.Response(200, json={"response": "not json at all"})
    )
    with pytest.raises(ModelProviderError) as exc_info:
        ollama.structured_generate("assess", schema=Verdict)
    assert exc_info.value.category == ModelErrorCategory.INVALID_RESPONSE


@respx.mock
def test_ollama_structured_generate_schema_mismatch_raises_invalid_response(
    ollama: OllamaProvider,
) -> None:
    respx.post("http://127.0.0.1:11434/api/generate").mock(
        return_value=httpx.Response(200, json={"response": '{"unrelated_field": true}'})
    )
    with pytest.raises(ModelProviderError) as exc_info:
        ollama.structured_generate("assess", schema=Verdict)
    assert exc_info.value.category == ModelErrorCategory.INVALID_RESPONSE


@respx.mock
def test_ollama_generation_is_serialized_not_concurrent(ollama: OllamaProvider) -> None:
    """One concurrent generation on the 8 GB GPU (Task 12 design note).
    Spawns two real generate() calls from separate threads against a mock
    that sleeps mid-response; without the lock the two would interleave as
    start/start/end/end. With it, the second call cannot enter the mock
    until the first has fully returned."""
    import threading
    import time

    events: list[str] = []
    first_call_started = threading.Event()

    def slow_response(request: httpx.Request) -> httpx.Response:
        events.append("start")
        first_call_started.set()
        time.sleep(0.2)
        events.append("end")
        return httpx.Response(200, json={"response": "ok"})

    respx.post("http://127.0.0.1:11434/api/generate").mock(side_effect=slow_response)

    first_thread = threading.Thread(target=ollama.generate, args=("q1",))
    second_thread = threading.Thread(target=ollama.generate, args=("q2",))
    first_thread.start()
    first_call_started.wait(timeout=2.0)
    second_thread.start()
    first_thread.join(timeout=3.0)
    second_thread.join(timeout=3.0)

    assert events == ["start", "end", "start", "end"]


# --------------------------------------------------------------------------
# Live: the real installed Ollama server + pulled model
# --------------------------------------------------------------------------


@pytest.mark.live
def test_live_ollama_health_and_generate() -> None:
    """Run with:
    $env:EXTERNAL_NETWORK_ENABLED = 'true'
    uv run pytest -m live tests/contract/model_gateway/test_provider_contract.py -q
    """
    provider = OllamaProvider()
    assert provider.health() is True

    result = provider.generate(
        "Reply with exactly the word: ready", temperature=0.0, timeout_seconds=60.0
    )
    assert result.text.strip()
    assert result.model.model_name == "llama3.1:8b"
    assert result.latency_seconds > 0


@pytest.mark.live
def test_live_ollama_structured_generate() -> None:
    provider = OllamaProvider()
    result = provider.structured_generate(
        "A CMBS loan's payment status changed from current to delinquent. "
        "Respond with JSON matching the schema, describing this as a status "
        "change with label 'delinquent' and a confidence between 0 and 1.",
        schema=Verdict,
        temperature=0.0,
        timeout_seconds=90.0,
    )
    assert isinstance(result.value, Verdict)
    assert 0.0 <= result.value.confidence <= 1.0
