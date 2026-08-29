# InvestRAG Studio — Implementation Plan

**Design:** `docs/plans/2026-08-29-investrag-studio-design.md`  
**Status:** In progress  
**Scope:** standalone `investrag-studio/` application; BondLens remains unchanged

## Progress snapshot — 2026-08-29

The first local vertical slice is implemented and verified: source upload/catalog, native multi-format routing, structure-aware and recursive chunking, provenance-carrying FAISS indexing, BM25/RRF retrieval through LangChain Runnables, local Ollama/extractive answering, citation-label enforcement, safe ZIP extraction, deterministic IR helpers, and the React five-area dashboard. The remaining phases below are intentionally visible and are not represented as active capabilities in the UI.

## Delivery order

### 1. Repository and runtime scaffold — completed

- Add independent Python backend and React/TypeScript frontend.
- Keep raw data and local indexes under the configured D: data directory.
- Add reproducible `uv sync`, `npm install`, local API and UI startup commands.

### 2. Vertical ingestion and retrieval slice — completed

- Add Pydantic source, element, chunk, citation, query and trace contracts.
- Add format detection and native parsers for text, Markdown, HTML, JSON, CSV, XLSX, PDF, DOCX, PPTX and email.
- Add structure-aware and recursive chunking with element-level provenance.
- Add BGE-M3 embedding provider with deterministic offline fallback.
- Add persistent FAISS cosine index and BM25/RRF retrieval.
- Compose retrieval through LangChain Runnables.
- Add local Ollama answerer and extractive fallback.
- Add citation-bearing response and query trace models.
- Add local SQLite catalog adapter as the first metadata implementation.

Acceptance: a mixed-format source can be ingested, indexed, queried and returned with source metadata; no model or database outage causes a fabricated answer.

### 3. Parser quality and trust controls — next

- Add parser confidence and quality-gate policies.
- Add safe archive extraction with traversal, symlink, nesting, file-count and expansion limits.
- Add optional Docling primary adapter and MinerU escalation adapter behind explicit availability checks.
- Add PyMuPDF validation path and parser bake-off fixtures.
- Add recursive email attachment ingestion and image OCR status.
- Add deterministic citation location tests for PDF pages and spreadsheet cells.

Acceptance: low-confidence output is marked partial or escalated; unsupported/unsafe files become visible failures and never silently enter the trusted corpus.

### 4. Vector-store adapter layer — next

- Define a capability/health contract shared by FAISS, Chroma, Qdrant, pgvector, Weaviate and Milvus.
- Preserve one cached embedding set for the portable benchmark.
- Add optional service adapters with explicit startup checks and sequential resource profiles.
- Add native sparse/hybrid implementations only behind the native-feature track.
- Add Pinecone as a later optional adapter without changing domain schemas.

Acceptance: each installed adapter passes contract tests; unavailable services are reported unavailable rather than represented as active; portable and native results remain separate.

### 5. Retrieval and answer hardening — next

- Add validated metadata filters and query rewriting.
- Add MMR, parent-child expansion, multi-query and optional local reranking profiles.
- Add context token limits and source diversity diagnostics.
- Add deterministic citation validity, citation coverage, unit/date and unsupported-number checks.
- Add one bounded repair attempt followed by controlled abstention.

Acceptance: trace shows every retrieval stage, and an unsupported or conflicting question produces an explicit insufficiency/conflict state.

### 6. Evaluation Studio backend — next

- Add golden-dataset schema with stable source-element judgments.
- Add parser metrics, Success@k, Recall@k, MRR, nDCG, citation metrics, abstention metrics and latency/resource measurements.
- Add portable, native and bounded ablation experiment manifests.
- Add checkpointed experiment jobs and CSV/JSON/Markdown export.
- Add optional local RAGAS/Ollama judge metrics, labelled as non-deterministic judge scores.

Acceptance: a benchmark run is reproducible from a corpus checksum, model/config versions and experiment manifest; deterministic metrics remain primary.

### 7. React product surface — first version completed; deepen next

- Add Overview, Data Room, Research Workspace, Retrieval Lab and Evaluation Studio views.
- Add source registry, upload flow, health cards, citations, query traces and ReCharts benchmark fixtures.
- Replace fixture leaderboard values with live experiment results.
- Add source/page/table/cell preview and streamed ingestion/benchmark progress.
- Add explicit empty, partial, error, unavailable-service and degraded-model states.

Acceptance: a reviewer can ingest, query, follow citations, inspect the trace, compare retrieval stages and export a measured benchmark report.

### 8. Verification and portfolio handoff — final

- Run backend Ruff and pytest suites.
- Run frontend TypeScript/Vite build and browser smoke tests.
- Exercise at least one native PDF, scanned/low-confidence document, spreadsheet, slide deck, HTML/JSON input and email attachment.
- Capture a deterministic demo script and screenshots.
- Update README capability/status matrices and measured limitations.
- Produce résumé bullets only from generated evidence.

Acceptance: documented clean-start commands work from the target machine and no claim exceeds the measured implementation.

## File ownership boundaries

- `investrag-studio/backend/`: new Python application only.
- `investrag-studio/frontend/`: new React application only.
- `investrag-studio/.env.example` and `investrag-studio/README.md`: local setup and capability status.
- `docs/plans/2026-08-29-investrag-studio-design.md`: approved design; update only when an implementation decision changes the design.
- Existing BondLens source and tests: do not modify for InvestRAG work unless a shared root configuration change is unavoidable and separately tested.
