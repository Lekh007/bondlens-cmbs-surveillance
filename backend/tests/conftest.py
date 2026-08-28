"""Repo-wide test defaults.

MODEL_PROVIDER defaults to "deterministic" for the whole test session
unless a test explicitly overrides it - real dev use defaults to "ollama"
(Settings.model_provider), but the fixture-backed unit suite must never
depend on Ollama being installed or running.
"""

import pytest


@pytest.fixture(autouse=True)
def _default_model_provider_to_deterministic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_PROVIDER", "deterministic")
