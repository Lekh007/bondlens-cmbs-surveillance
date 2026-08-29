from __future__ import annotations

import sqlite3
from pathlib import Path

from .domain import Chunk, SourceVersion


class Catalog:
    """Small local metadata adapter; its interface is ready for a PostgreSQL adapter."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS sources (
              source_id TEXT PRIMARY KEY, name TEXT NOT NULL, payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS chunks (
              chunk_id TEXT PRIMARY KEY, source_id TEXT NOT NULL, payload TEXT NOT NULL
            );
            """
        )
        self.connection.commit()

    def save_source(self, source: SourceVersion) -> None:
        self.connection.execute("INSERT OR REPLACE INTO sources(source_id,name,payload) VALUES(?,?,?)", (source.source_id, source.name, source.model_dump_json()))
        self.connection.commit()

    def list_sources(self) -> list[SourceVersion]:
        rows = self.connection.execute("SELECT payload FROM sources ORDER BY rowid DESC").fetchall()
        return [SourceVersion.model_validate_json(row[0]) for row in rows]

    def save_chunks(self, chunks: list[Chunk]) -> None:
        self.connection.executemany("INSERT OR REPLACE INTO chunks(chunk_id,source_id,payload) VALUES(?,?,?)", [(chunk.chunk_id, chunk.source_id, chunk.model_dump_json()) for chunk in chunks])
        self.connection.commit()
