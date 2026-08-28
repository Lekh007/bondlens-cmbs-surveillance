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


def test_path_outside_repo_root_is_rejected() -> None:
    with pytest.raises(pydantic.ValidationError):
        _settings(raw_root="C:/Windows/Temp/vichara-raw")


def test_sec_user_agent_is_required_but_not_secret() -> None:
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


def test_model_provider_defaults_to_ollama() -> None:
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
