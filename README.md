# BondLens

**A CMBS surveillance copilot where the language model is never allowed to do the arithmetic.**

Point it at a CIK and it ingests every ABS-EE filing the SEC has for that deal — real bytes
from `sec.gov`, not fixtures — parses loan- and property-level data out of the XML, and answers
questions like *which loans changed payment status between two reporting periods?*

Deterministic Python computes every number. The model only narrates what the tools found. Then a
mechanical verifier — a Python function, not a prompt instruction — rejects the answer if any
number in it cannot be found in that evidence.

[![CI](https://github.com/Lekh007/bondlens-cmbs-surveillance/actions/workflows/ci.yml/badge.svg)](https://github.com/Lekh007/bondlens-cmbs-surveillance/actions/workflows/ci.yml)

## The number that matters

Against the real installed model (`llama3.1:8b`, 4-bit) and real SEC data for Benchmark
2026-B42 Mortgage Trust (62 loans, 123 properties), the
[golden-question gate](docs/demo/bondlens-golden-questions.md) passes **5/5 with genuine
model-written narrative answers** — **0% fallback rate**, no repair attempts needed, every
citation live-HTTP-verified against `sec.gov` during the evaluation itself.

It did not start there. It started at **0/5**, and finding out why is most of what this project is:

> The first evaluation reported "5/5, 100%". Every one of those five passing answers was actually
> the deterministic refusal fallback — the pass/fail boolean could not tell a real answer from a
> refusal. Once the report was made honest (`fallback_rate` instead of a boolean), the real problem
> was visible: the model was being handed `70000000.00000000` and `drift 0E-8`, then rejected by
> the numeric verifier the moment it rewrote that readably as `$70 million`. No draft could satisfy
> both the prompt and the check at once, so it degenerated into repetition loops trying.
>
> Three fixes at the cause rather than the symptom — render evidence as human money, teach the
> verifier that `$70,000,000.00` and `70,000,000` are the same number, and say "all 62 loans sit
> exactly on schedule" once instead of printing ten identical zero rows. Accepted narratives went
> **0/5 → 5/5** and the flagship question's evidence shrank from 1,333 characters of noise to 327
> of signal.

## The two invariants

1. **No authoritative number comes from the language model.** Unit-tested Python computes every
   figure a user sees. The model narrates; it never computes.
2. **No claim ships without a citation.** The verifier rejects any answer whose numeric claims
   aren't backed by tool evidence, whose loan references were invented, or that degenerates into
   repetition. One repair attempt; if that fails too, the system hands back the raw evidence rather
   than a possibly-wrong narrative.

The hardest case is a question whose honest answer is "the data doesn't support that." On this
deal, *no* property genuinely deteriorated in the tested window — it is too young for meaningful
servicer-reported financials. An answer that invents a plausible-looking ranking is a hard failure
of the gate no matter how well it reads.

## Architecture

```text
React (Vite)  ──fetch──►  FastAPI  ──enqueue──►  Redis / RQ worker
                             │                         │
                             │                         ├── SEC EDGAR ABS-EE  → PostgreSQL
                             │                         ├── SEC EDGAR 10-D/8-K → FAISS
                             │                         └── 10-D Exhibit 99.1 → typed monthly report
                             │
                             └── LangGraph agent
                                   ├── deterministic tools  ← PostgreSQL / parsed loans
                                   ├── narrative retrieval  ← FAISS (untrusted evidence)
                                   └── drafting + verify    → Ollama (local Llama 3.1 8B)
```

Tool *routing* is a deterministic keyword classifier, not an LLM decision — which tool gets called
is auditable rather than emergent. Retrieved filing text enters the prompt as explicitly untrusted
evidence: it can add context, it can never move a number.

## Running it

```powershell
docker compose up -d                               # Postgres + Redis
cd backend; uv sync
cd ../frontend; npm install

cd backend
$env:MODEL_PROVIDER = 'ollama'                     # or 'deterministic' for no-GPU/CI
uv run uvicorn vichara_portfolio.main:app --port 8000

cd ../frontend; npm run dev
```

Ingest a real deal and score the agent against it:

```powershell
uv run python backend/scripts/ingest_bondlens.py <CIK>
uv run python backend/scripts/run_evaluations.py   # → .data/reports/bondlens-evaluation.json
```

The full gates — `ruff`, `mypy --strict`, `pytest` (242 passing), `vitest`, Playwright — run in
[CI](.github/workflows/ci.yml) on every push and need no network, database, Redis or GPU.

## Going deeper

**[DEEP_DIVE.md](DEEP_DIVE.md)** has the long version: what every tool in the stack actually
proved, the six bugs that only real data, a real model or a real browser could surface (a
degenerate output that slipped past the safety check; EDGAR's `index.json` silently omitting the
asset-data exhibit for 3 of 5 real filings; a transaction that poisoned every filing after the
first failure), the Exhibit 99.1 certificate analytics, and the gaps that are still open.

## What this is not

A portfolio-grade demonstration, not a production system, and not investment advice. No high
availability, no multi-tenancy, no disaster recovery. Auth is local seeded users demonstrating
role separation, not an identity provider. Nothing here makes or implies an investment
recommendation.
