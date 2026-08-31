"""Repo-wide test defaults.

MODEL_PROVIDER defaults to "deterministic" for the whole test session
unless a test explicitly overrides it - real dev use defaults to "ollama"
(Settings.model_provider), but the fixture-backed unit suite must never
depend on Ollama being installed or running.
"""

import os

import pytest

# Collection imports the FastAPI module before fixtures run. Supply safe test-only
# values at module load so a clean checkout never needs a developer's private .env.
os.environ.setdefault("SEC_USER_AGENT", "BondLens-Tests/0.1 (test@example.com)")
os.environ.setdefault("JWT_SECRET", "test-only-secret")
os.environ.setdefault("MODEL_PROVIDER", "deterministic")


@pytest.fixture(autouse=True)
def _default_model_provider_to_deterministic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_PROVIDER", "deterministic")
