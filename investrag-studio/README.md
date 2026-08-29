# InvestRAG Studio

InvestRAG Studio is a local-first document intelligence and RAG evaluation project for investment research. It is intentionally separate from BondLens while living in the same portfolio repository.

## Current vertical slice

- FastAPI backend with an immutable local source catalog (SQLite adapter);
- Markdown, TXT, HTML, JSON, CSV, XLSX, PDF, DOCX, PPTX, EML/MSG and image routing;
- canonical elements with page, slide, sheet, cell-range, JSONPath and bounding-box provenance;
- structure-aware and recursive chunk profiles;
- BGE-M3 embeddings when the local model is available, with a deterministic hash fallback for offline tests;
- persistent FAISS cosine index;
- BM25 plus weighted reciprocal-rank fusion through an explicit LangChain Runnable pipeline;
- local Ollama answer generation with controlled extractive fallback;
- citation-bearing answers and query traces;
- React/TypeScript dashboard with Overview, Data Room, Research Workspace, Retrieval Lab and Evaluation Studio views;
- deterministic Success@k, Recall@k, reciprocal-rank and nDCG metrics.

The API reports Chroma, Qdrant, pgvector, Weaviate, Milvus and Pinecone as planned/unavailable until their adapters and local contract tests are added. They are not represented as active databases by the current slice.

## Run the backend

```powershell
cd D:\Vichara-GenAI-Portfolio\investrag-studio\backend
uv sync
$env:INVESTRAG_EMBEDDING_MODE = "hash"   # quick offline smoke test
uv run uvicorn investrag.main:app --host 127.0.0.1 --port 8000 --reload
```

For the real local embedding model, omit the environment override. The first query will download/load `BAAI/bge-m3`; keep the laptop plugged in and allow sufficient disk space.

## Run the frontend

```powershell
cd D:\Vichara-GenAI-Portfolio\investrag-studio\frontend
npm install
npm run dev
```

Open <http://127.0.0.1:5174>. The frontend calls `http://127.0.0.1:8000/api/v1` by default. Set `VITE_API_BASE` to use another local port.

## CLI ingestion

```powershell
cd D:\Vichara-GenAI-Portfolio\investrag-studio\backend
uv run python scripts/seed_demo.py .\path\to\report.pdf .\path\to\metrics.xlsx
```

Raw artifacts, the SQLite catalog and the FAISS index are stored under the configured `INVESTRAG_DATA_DIR` (default `D:\Vichara-GenAI-Portfolio\.data\investrag`).

## Test

```powershell
cd D:\Vichara-GenAI-Portfolio\investrag-studio\backend
uv run ruff check src tests
uv run pytest

cd ..\frontend
npm run build
```

The current slice deliberately does not claim production-scale throughput, cloud deployment or fully active six-database benchmarking. Those adapters are the next implementation increments, after this vertical path has been visually accepted.
