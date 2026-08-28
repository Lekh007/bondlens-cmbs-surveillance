# Architecture

## Shape

```text
React web shell
├── /bondlens   CMBS surveillance and cited analyst chat   [in scope]
├── /altsignal  Macro/regulatory/spending intelligence     [deferred]
└── /ops        Model, evaluation, latency, audit          [deferred]
          │
          ▼
FastAPI API ── Redis queue ── ingestion/ML worker
    │                 │
    ├── PostgreSQL    ├── verified public APIs
    ├── FAISS         └── local files on D:
    ├── MLflow
    └── local model gateway ── Ollama on host GPU

Prometheus/Grafana ── observe API, worker, retrieval, and LLM behavior
```

## Ports and adapters

Domain and application modules hold the financial and workflow logic. SEC clients,
PostgreSQL, FAISS, Ollama, and MLflow are adapters behind ports. Tests replace every
external adapter with a deterministic fake, so the full BondLens test suite runs with no
network, no database, and no GPU. Docker runs the same processes behind production-like
boundaries.

The consequence worth stating: **the unit and contract suites must never require Ollama.**
The `deterministic` model provider is the only provider used in CI.

## Two invariants

1. **No authoritative number comes from the language model.** Deterministic Python
   functions compute every figure a user sees, and they return values with units, period
   boundaries, a formula version, data-quality flags, and source references. The model
   narrates that output.
2. **No claim ships without a citation.** The verifier node rejects any final answer whose
   numeric claims lack tool evidence or whose factual claims lack a source identifier. One
   repair attempt is allowed, then the answer is refused.

## Untrusted input

SEC filing text and API payloads are evidence, never instructions. Tool-like directives are
stripped from retrieved content and every source block is explicitly labelled as untrusted
in the prompt. A filing that contains text resembling a command must not change agent
behaviour.

## Data-shape notes that drive the design

The CMBS ABS-EE schema carries two families of fields, and conflating them produces silently
wrong comparisons:

- `*Securitization*` — frozen at issuance, identical in every reporting period.
- `mostRecent*` — servicer-updated, sparsely populated, on the servicer's own cadence.

Measured on Benchmark 2026-B42 (2026-08-28): across 123 properties only 29 carry any
`mostRecent` financials, on a quarterly window, and May-to-July movement is zero. The
time-varying data lives at loan level: 24 of 62 loans move balance, 3 change payment status.
BondLens therefore does loan-level surveillance and point-in-time property profiles.

## Documents

- `docs/plans/design.md` — approved design, including the scope revision.
- `docs/plans/implementation.md` — the task-by-task build plan.
- `docs/api-audit.md` — live verification of every external source.
