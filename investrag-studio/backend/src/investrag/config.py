from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed settings with safe local defaults."""

    model_config = SettingsConfigDict(env_prefix="INVESTRAG_", env_file=".env", extra="ignore")

    data_dir: Path = Path("D:/Vichara-GenAI-Portfolio/.data/investrag")
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.1:8b"
    embedding_model: str = "BAAI/bge-m3"
    embedding_mode: str = "auto"
    embedding_fallback_dimension: int = 512
    max_upload_bytes: int = 100 * 1024 * 1024
    cors_origins: str = "http://localhost:5174,http://127.0.0.1:5174"

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def index_dir(self) -> Path:
        return self.data_dir / "faiss"

    @property
    def catalog_path(self) -> Path:
        return self.data_dir / "catalog.db"

    @property
    def allowed_origins(self) -> list[str]:
        return [value.strip() for value in self.cors_origins.split(",") if value.strip()]
