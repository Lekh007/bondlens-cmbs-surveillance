"""Secret-free, local-first application settings.

Design constraints (see docs/plans/design.md section 2, "Locked constraints"):
  - no paid API keys - there is deliberately no field for FRED or any hosted LLM
    provider (OpenAI, Anthropic, Gemini, ...);
  - every large data path resolves under the repository root on D:;
  - SEC_USER_AGENT is required for live SEC calls but is not a secret - it is a
    declared contact string SEC's fair-access policy expects, safe to log;
  - JWT_SECRET is the one real secret here and is hidden from repr.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_DATA_ROOT = REPO_ROOT / ".data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    data_root: Path = _DEFAULT_DATA_ROOT
    raw_root: Path = _DEFAULT_DATA_ROOT / "raw"
    faiss_root: Path = _DEFAULT_DATA_ROOT / "faiss"
    mlflow_root: Path = _DEFAULT_DATA_ROOT / "mlflow"

    database_url: str = "postgresql+psycopg://vichara:vichara@localhost:5432/vichara"
    redis_url: str = "redis://localhost:6379/0"

    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.1:8b"
    model_provider: Literal["deterministic", "ollama"] = "ollama"

    sec_user_agent: str = Field(
        ...,
        description="Declared User-Agent for data.sec.gov, e.g. 'App/0.1 (contact@example.com)'. Not a secret.",
    )
    jwt_secret: str = Field(..., repr=False)

    external_network_enabled: bool = False

    def model_post_init(self, __context: object) -> None:
        for field_name in ("data_root", "raw_root", "faiss_root", "mlflow_root"):
            resolved = getattr(self, field_name).resolve()
            object.__setattr__(self, field_name, resolved)
            if not resolved.is_relative_to(REPO_ROOT):
                raise ValueError(f"{field_name}={resolved} must resolve under {REPO_ROOT}")
