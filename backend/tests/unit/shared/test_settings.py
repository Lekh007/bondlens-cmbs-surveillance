from pathlib import Path

import pydantic
import pytest

from vichara_portfolio.settings import REPO_ROOT, Settings


def _settings(**overrides: object) -> Settings:
    base = dict(sec_user_agent="Vichara-Portfolio/0.1 (test@example.com)", jwt_secret="test-secret")
    base.update(overrides)
    return Settings(_env_file=None, **base)  # type: ignore[call-arg]


def test_large_paths_resolve_under_repo_root() -> None:
    settings = _settings()
    for path in (
        settings.data_root,
        settings.raw_root,
        settings.faiss_root,
        settings.mlflow_root,
    ):
        assert path.is_relative_to(REPO_ROOT), f"{path} must resolve under {REPO_ROOT}"


def test_path_outside_repo_root_is_rejected(tmp_path: Path) -> None:
    # Must be an *absolute* path outside the repo on every platform. A literal
    # like "C:/Windows/Temp/..." is absolute only on Windows; on POSIX it is a
    # relative path that resolves under the repo root, so the validator is right
    # not to reject it and the assertion below would fail for the wrong reason.
    outside = tmp_path / "vichara-raw"
    assert not outside.resolve().is_relative_to(REPO_ROOT), (
        f"precondition: {outside} must sit outside {REPO_ROOT} for this test to mean anything"
    )
    with pytest.raises(pydantic.ValidationError):
        _settings(raw_root=str(outside))


def test_sec_user_agent_is_required_but_not_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    # The repo-wide conftest supplies a safe import-time value so app modules can
    # be collected from a clean checkout. Remove it here to test the required
    # field contract itself.
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    with pytest.raises(pydantic.ValidationError):
        Settings(_env_file=None, jwt_secret="test-secret")  # type: ignore[call-arg]

    settings = _settings(sec_user_agent="Vichara-Portfolio/0.1 (kasarlekhraj@gmail.com)")
    assert "kasarlekhraj@gmail.com" in repr(settings)
    assert "kasarlekhraj@gmail.com" in settings.sec_user_agent


def test_jwt_secret_is_required_and_hidden_from_repr() -> None:
    settings = _settings(jwt_secret="do-not-print-me")
    assert "do-not-print-me" not in repr(settings)


def test_live_external_calls_default_off() -> None:
    settings = _settings()
    assert settings.external_network_enabled is False


def test_model_provider_defaults_to_ollama(monkeypatch: pytest.MonkeyPatch) -> None:
    # The repo-wide conftest forces MODEL_PROVIDER=deterministic for the
    # whole test session (Task 12) - this test verifies the actual class
    # default beneath that override, so it must clear the env var itself.
    monkeypatch.delenv("MODEL_PROVIDER", raising=False)
    settings = _settings()
    assert settings.model_provider == "ollama"


def test_model_provider_can_be_forced_deterministic() -> None:
    settings = _settings(model_provider="deterministic")
    assert settings.model_provider == "deterministic"


def test_no_fred_or_external_llm_key_setting_exists() -> None:
    forbidden_substrings = ("fred", "openai", "anthropic", "claude", "gemini")
    for field_name in Settings.model_fields:
        lowered = field_name.lower()
        assert not any(bad in lowered for bad in forbidden_substrings), (
            f"forbidden setting field: {field_name}"
        )
