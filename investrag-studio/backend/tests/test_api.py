from pathlib import Path

from fastapi.testclient import TestClient

from investrag.config import Settings
from investrag.main import create_app


def test_health_and_ingestion(tmp_path: Path) -> None:
    app = create_app(Settings(data_dir=tmp_path, embedding_mode="hash", ollama_base_url="http://127.0.0.1:1"))
    client = TestClient(app)
    assert client.get("/health/live").json() == {"status": "live"}
    response = client.post("/api/v1/ingestions", files={"file": ("brief.md", b"# Outlook\nRevenue is stable.", "text/markdown")})
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    health = client.get("/api/v1/health").json()
    assert health["indexed_chunks"] == 1
    answer = client.post("/api/v1/queries", json={"question": "What is the outlook?", "profile": "hybrid"})
    assert answer.status_code == 200
    assert answer.json()["citations"]
