# Vichara GenAI Investment Portfolio — Approved Design

**Date:** 2026-08-28  
**Status:** Approved for implementation - **scope revised 2026-08-28 (see section 0)**  
**Target repository:** `D:\Vichara-GenAI-Portfolio`  
**Deadline:** none external. The original "Sunday 2026-08-30" was self-imposed and is withdrawn.  
**Primary role:** Vichara GenAI Lead Engineer (Investment Data Platforms)

---

## 0. Scope revision - 2026-08-28

Two changes were made after a pre-build data spike against live SEC filings.

**Scope cut to BondLens.** The original three-project scope (BondLens, AltSignal, PrivateAI Ops) is 3-6 weeks of work. Only **BondLens** is in scope for the first release. AltSignal and PrivateAI Ops are retained in this document as designed stretch work and reuse the same ports, provenance, and model seams. Rationale: Vichara is reportedly blocked building a CMBS/RMBS chatbot, so BondLens is the artifact that speaks to the actual opening; the other two are generic to any GenAI posting.

**The G1 acceptance demo moves from property level to loan level.** A field-by-field diff of the real May and July ABS-EE files for Benchmark 2026-B42 (measured 2026-08-28):

| Level | Fields with month-over-month movement |
|---|---|
| Property (123 records) | 3 of 123 changed `mostRecentNetOperatingIncomeAmount`, occupancy, and DSCR - and all three were `None` to first value, not deterioration. Only 29 of 123 have any `mostRecent` financials at all, on a quarterly window. |
| Loan (62 records) | 24 changed balance/principal/interest, **3 changed `paymentStatusLoanCode`**, 3 changed advances outstanding, 62 changed `paidThroughDate`. |

The ABS-EE CMBS schema freezes `*Securitization*` fields at issuance and lets servicers update `mostRecent*` on their own cadence. On a February-2026 deal, almost no servicer has reported yet. Property-level deterioration questions require a seasoned deal (2015-2019 vintage); that is deferred. The demo asks loan-level questions, which the data supports.

---

## 1. Goal

Build three demonstrable GenAI investment-data projects that run locally on Lekhraj Kasar's gaming laptop, use no paid services or credential-gated data APIs, and collectively demonstrate the technical requirements in Vichara's GenAI Lead Engineer job description.

The three projects will be presented separately on the CV, but implemented in one monorepo so they share ingestion, persistence, model-serving, evaluation, authentication, observability, and deployment infrastructure.

## 2. Locked constraints

1. **No paid APIs or cloud resources are required.**
2. **No signup, approval form, or API key is required for any mandatory data source.**
3. **FRED is excluded.** Its official API requires an account and key.
4. **GDELT DOC is excluded from the critical path.** Its bulk host worked, but its API timed out twice during the 2026-08-28 audit.
5. **All LLM inference is local.** The default is a 4-bit, 7–8B Llama-class model served by Ollama on the RTX 4060 Laptop GPU (8 GB VRAM).
6. **Large caches and models live on `D:`.** The target drive had 990.3 GB free at planning time.
7. **The deliverable is a portfolio-grade MVP, not a claim of production HA or real cloud deployment.** Kubernetes and private-cloud artifacts are deployment references validated locally.
8. **Claims stay honest.** These projects demonstrate hands-on capability but do not create two years of GenAI tenure or cross-functional people-management experience.
9. **Engineer-for-hire framing only.** No artifact that could reach Vichara - README, CV bullet, code comment, commit author, demo copy, published repository - may present Lekhraj as a founder or reference NutriCart, Trosky, or any active startup involvement. Vichara would read side-startup involvement as a conflict of interest, and the internal sponsor has pitched him as an AI/full-stack engineer. This is a release-gate check, not a style preference.

## 3. Verified data sources

| Source | Mandatory use | Authentication | Live audit result |
|---|---|---|---|
| SEC EDGAR public data APIs and archives | CMBS filings, XBRL, ABS-EE, 10-D, 8-K | None; declared `User-Agent` only | HTTP 200; real CMBS XML parsed |
| U.S. Treasury Fiscal Data | Interest-rate and debt series | None | HTTP 200 JSON |
| BLS Public Data API v1 | CPI, unemployment, payroll | None | HTTP 200 JSON |
| World Bank Indicators v2 | India/U.S. macro comparisons | None | HTTP 200 JSON |
| Federal Register API | Regulatory documents and events | None | HTTP 200 JSON |
| USAspending API v2 | Contracts, grants, and spending signals | None | GET and filtered POST returned HTTP 200 |

### SEC access policy

- Use `data.sec.gov`, not EDGAR filer/submission APIs.
- **Resolve exhibits from the full `<accession>.txt` submission header, never from `index.json` alone.** Measured 2026-08-28: for accessions `0001888524-26-007544` (Apr), `-010373` (May), and `-012270` (Jun), `index.json` lists only the ABS-EE cover `.htm` and omits `exh_102.xml` entirely - although the file exists and returns HTTP 200 at 585,970 bytes. The `.txt` header lists `<TYPE>EX-102` correctly for all five filings. A resolver trusting `index.json` finds zero assets for three of five periods.
- Send a descriptive `User-Agent` containing the application name and a contact email.
- Enforce an application-side limit of 8 requests/second, below SEC's published 10 requests/second ceiling.
- Cache immutable filing documents locally and retry transient failures with exponential backoff.
- Call SEC from FastAPI/worker processes because `data.sec.gov` does not support browser CORS.

### Seed CMBS deal

Use **Benchmark 2026-B42 Mortgage Trust**, CIK `0002110410`.

Five ABS-EE filings exist: issuance (2026-02-18) plus monthly periods for April, May, June, and July 2026.

Measured contents of the July `exh_102.xml` (588,639 bytes):

- 62 loan (`assets`) records and 123 property records;
- loan identity, balances, payment status, advances, and paid-through dates;
- property identity, location, at-issuance valuation/occupancy/NOI, and tenant rollover;
- `mostRecent*` property financials populated for only 29 of 123 properties, on a quarterly window.

The time-varying data is at loan level. See section 0.

## 4. System boundary

The monorepo exposes three product surfaces through one React shell and one public FastAPI API, while maintaining deep feature modules and deployable process boundaries.

```text
React web shell
├── /bondlens   CMBS surveillance and cited analyst chat
├── /altsignal  Macro/regulatory/spending intelligence
└── /ops        Model, evaluation, latency, and audit control plane
          │
          ▼
FastAPI API ── Redis queue ── ingestion/ML worker
    │                 │
    ├── PostgreSQL    ├── verified public APIs
    ├── FAISS         └── local files on D:
    ├── MLflow
    └── local model gateway ── Ollama on host GPU

n8n ── calls idempotent FastAPI ingestion endpoints
Prometheus/Grafana ── observe API, worker, retrieval, and LLM behavior
```

The Python code uses ports and adapters:

- domain/application modules contain financial and workflow logic;
- API clients, PostgreSQL, FAISS, Ollama, and MLflow are adapters;
- tests replace every external adapter with deterministic fakes;
- Docker starts the same processes behind production-like boundaries.

## 5. Project 1 — BondLens AI

### Purpose

Turn the existing static CMBS React concept into a working structured-credit surveillance copilot grounded in real SEC filings.

### Core flow

1. Given a CIK, fetch the submissions history.
2. Identify ABS-EE, 10-D, and 8-K filings.
3. Resolve filing document links **from the `.txt` submission header** and download immutable source artifacts.
4. Parse ABS-EE XML into deal, reporting-period, loan, and property snapshots, preserving the `*Securitization*` (frozen at issuance) versus `mostRecent*` (servicer-updated) distinction rather than flattening them together.
5. Extract narrative filing text, chunk it, embed locally, and index it in FAISS.
6. Calculate deal/property comparisons deterministically.
7. Let a LangGraph workflow choose calculation or retrieval tools.
8. Verify that every answer contains traceable source citations.

### Agent tools

- `get_deal_summary` - point-in-time deal profile
- `compare_reporting_periods` - loan-level deltas between two periods
- `rank_loans_by_status_change` - payment-status migrations, ranked by severity
- `rank_loans_by_balance_drift` - actual versus scheduled balance divergence
- `get_loan_history` - one loan across all five periods
- `get_property_profile` - point-in-time property detail (at-issuance figures; explicitly *not* a time series)
- `search_filing_text`
- `get_source_excerpt`

The LLM never performs authoritative portfolio arithmetic. It explains typed tool outputs.

### Acceptance demo

The user selects Benchmark 2026-B42 and asks:

> Which loans changed payment status between May and July, whose balances diverged from schedule, and which SEC records support the answer?

The system returns a ranked, numerically correct answer with links to filing accession, exhibit, reporting period, and loan. Verified ground truth for that window: loan 30 (Cummins Station, Nashville TN) moved `0` to `B`; loans 16 (PWC Pennant, St. Louis MO) and 39 (325 East 14th Street, New York NY) moved `B` to `0`; 24 of 62 loans show balance movement.

If the model reports property-level deterioration for this deal, that is a hallucination and the verifier must reject it - there is none in the data.

## 6. Project 2 — AltSignal AI

### Purpose

Demonstrate a modular alternate-data investment research framework with structured and unstructured ingestion, orchestration, PyTorch modeling, agentic analysis, and an interactive frontend.

### Data products

- Treasury average-interest-rate and debt observations;
- BLS CPI, unemployment, and payroll observations;
- World Bank GDP, inflation, and growth indicators for India and the U.S.;
- Federal Register regulatory events relevant to securities, banking, mortgage finance, and AI;
- USAspending contracts/grants, including technology and financial-sector categories.

### Orchestration

n8n holds schedules and operator-visible workflows. It calls idempotent FastAPI ingestion endpoints; business logic remains in Python, not buried in workflow-node expressions.

### PyTorch model

Train a small monthly risk-regime classifier using only information available at each timestamp. Candidate features include rate level/change, CPI change, unemployment, payroll growth, event volume/materiality, and spending anomalies. The target is next-month Treasury-rate direction (`up`, `flat`, `down`) using a documented threshold.

Evaluation uses a temporal train/validation/test split and compares against a majority-class baseline. The UI labels the output as a research signal, not investment advice or demonstrated alpha.

### Agent workflow

1. Planner translates a research question into required tools.
2. Retriever gathers structured observations and source documents.
3. Analyst produces a typed draft brief.
4. Verifier rejects uncited or unsupported claims.
5. Formatter returns thesis, evidence, counter-evidence, caveats, and citations.

### Acceptance demo

One click refreshes all five data sources, trains or loads the regime model, and generates a cited research brief explaining the current macro/regulatory regime and its caveats.

## 7. Project 3 — PrivateAI Ops

### Purpose

Demonstrate local/private LLM deployment, MLOps, security, observability, failure handling, load testing, and cloud-ready deployment design.

### Capabilities

- local Ollama provider and deterministic test provider behind one model port;
- prompt, retrieval, model, and dataset version logging in MLflow;
- golden-set evaluation for citation coverage, retrieval recall, numeric exactness, and latency;
- Prometheus metrics and Grafana dashboards;
- JWT roles (`analyst`, `operator`) and local seeded users;
- Redis-backed request throttling and job queue;
- append-only audit events for ingestion, inference, evaluation, and model configuration changes;
- timeouts, retries, circuit breaker, readiness/liveness checks, and graceful degraded mode;
- Docker Compose deployment and validated Kubernetes GPU reference manifests;
- Locust load and failure scenarios.

### Acceptance demo

An operator can compare two model/retrieval configurations, run the golden evaluation set, view quality and latency in the Ops UI, stop the local model, and see a controlled degraded response rather than a fabricated answer or crashed application.

## 8. Persistence and local storage

```text
D:\Vichara-GenAI-Portfolio\
├── .cache\huggingface\
├── .data\
│   ├── raw\sec\
│   ├── raw\altdata\
│   ├── faiss\
│   ├── mlflow\
│   ├── n8n\
│   └── postgres\
└── .models\ollama\
```

PostgreSQL stores normalized relational data. FAISS stores embeddings and a sidecar metadata map. Raw payloads are content-addressed and never silently overwritten. Every normalized row keeps source, retrieval time, source URL, and checksum.

## 9. Evaluation and evidence policy

The weekend MVP is complete only when the demos work from clean commands and the following evidence is generated:

- unit, contract, and integration test output;
- API health output;
- successful real-data ingestion manifest;
- BondLens golden-question report;
- AltSignal model metrics and baseline comparison;
- Ops evaluation/latency report;
- Docker Compose health status;
- screenshots and a deterministic demo script;
- three honest CV-ready project entries.

No answer may claim a source was used unless its source identifier is present in the response. No calculated field may come from free-form LLM arithmetic.

## 10. Scope cuts if time compresses

**Already cut as of section 0:** AltSignal (section 6) and PrivateAI Ops (section 7) in their entirety, plus any second CMBS deal.

The following may be deferred without weakening the core CV evidence:

1. a live Kubernetes cluster (manifests and validation remain);
2. GDELT bulk ingestion;
3. multi-user administration UI;
4. model fine-tuning;
5. more than one CMBS deal;
6. automatic cloud deployment.

The following may not be cut from the BondLens release:

1. real SEC CMBS ingestion across all five reporting periods;
2. deterministic financial tools and citations;
3. local LLM inference or a clearly reported hardware blocker;
4. a runnable UI and documented startup commands;
5. automated tests for all critical paths;
6. the verifier that rejects uncited or unsupported claims.

## 11. User responsibilities

Codex handles coding, API integration, installation commands, data ingestion, tests, documentation, and debugging.

The user is only expected to:

1. approve a Windows UAC dialog if Ollama installation requests it;
2. keep the laptop plugged in and prevent sleep during model download/training;
3. perform final visual acceptance using the supplied checklist;
4. choose whether/where to publish the repository after local completion;
5. confirm final CV wording before it is used externally;
6. confirm that no artifact violates the engineer-for-hire framing in constraint 2.9 before anything leaves the machine.

