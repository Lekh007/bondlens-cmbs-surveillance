# BondLens

A local-first GenAI copilot for CMBS (commercial mortgage-backed securities) loan
surveillance, built directly on real SEC EDGAR regulatory filings. Every number it shows
is computed by deterministic Python, never by the language model — the model's only job is
to explain what the tools found and cite exactly where each fact came from.

It runs entirely on one workstation: local LLM inference (Ollama), local vector search
(FAISS), local Postgres/Redis. No paid API key anywhere in the stack.

**Status:** the [golden-question evaluation](docs/demo/bondlens-golden-questions.md) gate has
**passed** against the real installed model and real filing data: 5/5 golden questions,
100% tool-routing accuracy, 100% numeric exactness, 100% citation coverage, 100% source-URL
validity. Not a mocked demo — see [Real bugs found by testing against real
things](#real-bugs-found-by-testing-against-real-things) below.

## What it actually does

Point it at a CIK and it ingests every ABS-EE (asset-backed securities exhibit) filing SEC
has for that deal — real bytes downloaded from `sec.gov`, not synthetic fixtures — parses
loan- and property-level asset data out of the XML, and answers surveillance questions like:

- *Which loans changed payment status between two reporting periods?*
- *Whose balance diverged from the amortization schedule?*
- *Which properties deteriorated most in net operating income?*

That last one is the interesting case: on the real deal this was built and tested against
(a February-2026-vintage CMBS trust, 62 loans / 123 properties), **no property genuinely
deteriorated** in the tested window — it's too young for meaningful servicer-reported
financials yet. The correct answer is to say so, not to invent a plausible-looking ranking.
An answer that fabricates deterioration to sound responsive is a hard failure of the
evaluation gate, regardless of how convincing it reads. Getting an LLM to reliably prefer
"the data doesn't support that claim" over a fluent-sounding fabrication is most of what
this project is actually about.

## Tools used, and what building with them actually proved

Every entry below is something the project required working, not just importing — most were
validated by a real bug the tool's own use surfaced, not by assumption.

| Tool | What it's for here | What using it actually achieved |
|---|---|---|
| **LangGraph** | Orchestrates the agent as an explicit graph: plan → run tools → retrieve context → draft → verify → repair → finalize | Tool *routing* is a deterministic keyword classifier, not an LLM decision — which tool gets called is auditable, not emergent. The graph structure is what makes a "reject and refuse" fallback path possible at all: one repair attempt, then finalize hands back raw evidence instead of a possibly-wrong narrative. |
| **Ollama + Llama 3.1 8B** (local, 4-bit) | All text generation, on an 8GB laptop GPU | A complete GenAI product with zero hosted-inference dependency. Live testing also caught a real model failure mode — see below — that a hosted-API demo would have masked behind a provider's own guardrails. |
| **FAISS + sentence-transformers** | Local vector index over narrative filing text | Retrieval-augmented context without a hosted vector database. |
| **A hand-written mechanical verifier** (no LLM grading itself) | Checks every number-shaped token in a drafted answer against the tool evidence it was supposedly drawn from, before the answer is shown | This is the actual anti-hallucination mechanism — not a prompt instruction ("please cite your sources"), a Python function that fails the answer if a number can't be found in evidence. Extended mid-project to also catch degenerate/repetitive generation, once live testing showed a plausible number wasn't the only way an answer could be wrong. |
| **FastAPI + Pydantic** | The HTTP API: ingestion jobs, deal analytics, chat | A typed, self-documenting API surface where a malformed request fails at the boundary, not three functions deep. |
| **PostgreSQL + SQLAlchemy** | Normalized persistence for parsed CMBS domain data | Idempotent re-ingestion (upsert on natural keys) and, after a live bug, per-unit-of-work `SAVEPOINT` isolation — see below. |
| **Redis + RQ (Redis Queue)** | Background ingestion jobs, decoupled from the request/response cycle | Async job processing with a real concurrency bug found and fixed (RQ's signal-handler setup crashing inside a FastAPI worker thread). |
| **React 19 + TypeScript + Vite** | The product UI | A typed component tree where a backend contract change is a compile error, not a runtime surprise. |
| **TanStack Query** | Server-state fetching, caching, and invalidation | No hand-rolled loading/error/stale-cache state machine per screen. |
| **Zod** | Runtime validation of every API response on the client | A backend response that doesn't match its declared shape fails loudly and specifically, instead of silently propagating `undefined` into a chart. |
| **Playwright** | End-to-end browser test of the real user flow | Automated proof that ingest → dashboard → ask a question → open a citation actually works together, not just each piece in isolation. |
| **Docker Compose** | Local Postgres + Redis | Reproducible infrastructure without touching the host machine's other services (this workstation already runs unrelated Postgres/Redis instances on the standard ports). |
| **pytest, ruff, mypy --strict** | Test/lint/type gates | 190+ automated tests, zero lint findings, zero type errors, and a discipline of proving every regression test meaningful by reverting the fix and watching it fail before restoring it. |
| **SEC EDGAR's public data API** | The only data source | Real-world data engineering against an undocumented quirk: EDGAR's `index.json` silently omits the asset-data exhibit for filings where it should be listed — a resolver trusting it alone finds zero data for 3 of 5 real filings on this deal. Fixed by parsing the full submission header instead. |

## Real bugs found by testing against real things

This project's TDD discipline (write a failing test, implement, verify, commit) still
missed things a fake or a fixture can't surface. Every one of these was found by running the
real pipeline against real data, a real model, or a real browser — and fixed at the root
cause, with a regression test proven meaningful by reverting the fix first.

- **A degenerate LLM output that slipped past the safety check.** Asked the flagship
  two-tool question, the local 8B model reproducibly (3 out of 3 runs) fell into a
  repetitive greedy-decoding loop — `"B 7, D 6, C 4, A 5, R 3, A 2, 0 I will 1,"` repeated a
  dozen times. The existing verifier, which checks that every number in a draft appears in
  the evidence it was drawn from, missed it once: every repeated digit happened to already
  be a small loan number that *was* in evidence. Fixed by adding a second, independent
  check for pathological repetition, so degenerate output reliably triggers the
  repair-then-refuse fallback instead of ever reaching a user.
- **An evaluator trusting stale state.** The evaluation harness (and, it turned out, an
  earlier test written for the same agent) read the verifier's error list to decide whether
  an answer was grounded — but that field reflects whichever *draft* got rejected, not
  necessarily the *final* answer, which after a repair failure is a verbatim evidence echo
  that's grounded by construction. The first live evaluation run consequently failed 3-5 of
  5 golden questions that were actually fine. Fixed by re-checking the real delivered
  answer everywhere, not the draft history.
- **A cross-filing transaction bug only visible under multi-filing ingestion.** One shared
  database session across a five-filing ingestion loop meant a single filing's write
  failure poisoned every filing after it — Postgres refuses further statements on a
  transaction until it's explicitly rolled back. Fixed with per-filing `SAVEPOINT`
  isolation, verified by temporarily reverting the fix and confirming the regression test
  failed exactly as expected.
- **Missing CORS headers, invisible to an API-only test suite.** The backend's own test
  suite talks to the app in-process and never exercises a real cross-origin browser
  request — so it never caught that the frontend couldn't call the API at all until it was
  opened in an actual browser.
- **A dropdown that displayed correctly but never actually selected anything.** A
  controlled `<select>` whose value didn't match any of its options silently falls back to
  showing the first option in the browser, without ever firing its change handler — so the
  UI *looked* like a deal was chosen while the app's own state still said none was. Only
  visible by actually clicking through the flow, not by asserting on rendered text.

## Architecture

```text
React (Vite)  ──fetch──►  FastAPI  ──enqueue──►  Redis / RQ worker
                             │                         │
                             ├── PostgreSQL             ├── SEC EDGAR (real filings)
                             ├── FAISS (local vectors)   
                             └── LangGraph agent ──► Ollama (local Llama 3.1 8B)
```

**Two invariants hold everywhere in this codebase:**

1. **No authoritative number comes from the language model.** Deterministic, unit-tested
   Python functions compute every figure shown to a user. The model narrates that output —
   it never computes.
2. **No claim ships without a citation.** A mechanical verifier rejects any answer whose
   numeric claims aren't backed by tool evidence, or whose factual claims have no source.
   One repair attempt is allowed; if that still fails, the system hands back the raw
   evidence instead of a possibly-wrong narrative.

## Running it

```powershell
# One-time
docker compose up -d                              # Postgres + Redis
cd backend; uv sync
cd ../frontend; npm install

# Backend
cd backend
$env:MODEL_PROVIDER = 'ollama'                     # or 'deterministic' for no-GPU/CI
uv run uvicorn vichara_portfolio.main:app --port 8000

# Frontend
cd frontend
npm run dev

# Ingest a real deal and evaluate the agent against it
uv run python backend/scripts/ingest_bondlens.py <CIK>
uv run python backend/scripts/run_evaluations.py   # writes .data/reports/bondlens-evaluation.json
```

Full test/lint/type gates:

```powershell
cd backend; uv run pytest tests/unit tests/integration -q; uv run ruff check src tests; uv run mypy src
cd ../frontend; npm run test -- --run; npm run lint; npm run build; npm run e2e
```

## Layout

```
backend/    FastAPI app + RQ worker. Ports-and-adapters: domain logic never
            imports SEC/Postgres/FAISS/Ollama directly, so the full test
            suite runs with no network, no database, and no GPU.
frontend/   React 19 + TypeScript + Vite.
docs/       Design decisions, implementation plan, golden-question evaluation writeup.
scripts/    One-time setup and runtime checks.
```

## What this is not

A portfolio-grade demonstration, not a production system, and not investment advice.

- No high availability, no multi-tenancy, no disaster recovery.
- Auth (where present) is local seeded users demonstrating role separation, not an identity
  provider.
- Nothing here makes or implies an investment recommendation.
