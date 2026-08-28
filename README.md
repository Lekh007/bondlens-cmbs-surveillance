# Vichara GenAI Investment Portfolio

A local-first GenAI platform for structured-credit and investment data, built on public
regulatory filings. Everything runs on one workstation with no paid services and no
credential-gated data source.

## Products

| Surface | Status | What it does |
|---|---|---|
| **BondLens AI** (`/bondlens`) | **In scope** | CMBS surveillance copilot over real SEC ABS-EE filings. Deterministic loan analytics with an LLM that explains typed tool output and cites every claim back to a filing. |
| AltSignal AI (`/altsignal`) | Deferred | Macro / regulatory / spending research framework over five keyless public sources. |
| PrivateAI Ops (`/ops`) | Deferred | Model, evaluation, latency, and audit control plane. The local model gateway and MLflow evaluation land early because BondLens needs them. |

Scope was cut to BondLens on 2026-08-28 after a data spike. See
`docs/plans/design.md` section 0 for the measurement that drove it.

## The keyless-data guarantee

No data source in this repository requires an account, an API key, an approval form, or a
paid plan. Every source was verified live before it was designed in:

| Source | Auth | Used for |
|---|---|---|
| SEC EDGAR public data APIs and archives | Declared `User-Agent` only | CMBS filings, ABS-EE asset data, 10-D, 8-K |
| U.S. Treasury Fiscal Data | None | Interest-rate and debt series *(deferred)* |
| BLS Public Data API v1 | None | CPI, unemployment, payroll *(deferred)* |
| World Bank Indicators v2 | None | Macro comparisons *(deferred)* |
| Federal Register API | None | Regulatory events *(deferred)* |
| USAspending API v2 | None | Contract and grant signals *(deferred)* |

FRED is deliberately excluded because its API requires a registered key.

There is no `OPENAI_API_KEY`, no `ANTHROPIC_API_KEY`, and no hosted inference anywhere in
this repository. All generation is local.

## Hardware expectation

Developed against an RTX 4060 Laptop GPU (8 GB VRAM) with the model served by Ollama on the
Windows host and the application stack running in WSL2 / Docker. A 4-bit 7-8B Llama-class
model fits; larger models will not. The system degrades to a clearly-labelled unavailable
state when the model is down rather than answering without it.

## What this is not

This is a portfolio-grade MVP, not a production system.

- Kubernetes manifests are validated references. Nothing has been deployed to a real cluster.
- There is no high availability, no multi-tenancy, and no disaster recovery.
- Auth is local seeded users for demonstrating role separation, not an identity provider.
- The research outputs are engineering demonstrations. They are not investment advice and
  no claim of alpha is made anywhere in this codebase or its documentation.

Every number surfaced to a user is computed by a deterministic, unit-tested Python function.
The language model explains those numbers and retrieves narrative context. It never performs
authoritative arithmetic, and an answer that cannot cite its sources is rejected rather than
shown.

## Getting started

See `docs/plans/implementation.md`. The short version:

```powershell
.\scripts\bootstrap.ps1   # one-time: dependencies, model, database
.\scripts\dev.ps1         # start the stack
.\scripts\verify.ps1      # health checks
```

## Layout

```
backend/    FastAPI app + RQ worker. Ports and adapters: domain logic is
            independent of SEC, PostgreSQL, FAISS, Ollama, and MLflow.
frontend/   React 19 + TypeScript + Vite product shell.
infra/      Docker, Prometheus, Grafana, Kubernetes, Locust.
docs/       Design, implementation plan, API audit, demos.
scripts/    Windows entry points.
```
