# Vichara GenAI Investment Portfolio Implementation Plan

> **Execution policy:** Work through this plan in order. Use TDD for domain logic and adapters, keep real-network tests explicitly marked, and commit after every task. Do not publish, deploy externally, or add paid services without the user's approval.

> **SCOPE REVISION 2026-08-28 - read before Task 1.** Only **BondLens (Tasks 1-17)** is in scope for the first release. Tasks 18-28 (AltSignal, PrivateAI Ops) are deferred stretch work; Tasks 29-34 apply to BondLens alone. The Sunday deadline was self-imposed and is withdrawn. The G1 acceptance demo has moved from property-level to **loan-level** surveillance after a measured data spike - see section 0 of the design document. Do not build against the original property-deterioration demo; there is no such signal in this deal.

**Goal (original, superseded in part):** Build three locally runnable, CV-ready GenAI investment-data projects—BondLens AI, AltSignal AI, and PrivateAI Ops—using verified keyless public data and a local GPU-served LLM.

**Architecture:** One monorepo contains a React product shell, a modular FastAPI backend, an RQ worker, PostgreSQL, FAISS, n8n, MLflow, Prometheus, and Grafana. Feature modules expose deep application services behind ports; SEC/API clients, storage, embeddings, Ollama, and workflow infrastructure are adapters. The same Python image runs the API and worker as separate processes in Docker.

**Tech stack:** Python 3.12 in WSL2, uv, FastAPI, SQLAlchemy/Alembic, PostgreSQL 16, Redis/RQ, Polars, lxml/defusedxml, LlamaIndex, LangGraph/LangChain, FAISS, Hugging Face embeddings, Ollama, PyTorch, scikit-learn, MLflow, React 19, TypeScript, Vite, TanStack Query, Plotly, Vitest, Playwright, Docker Compose, n8n, Prometheus, Grafana, Kubernetes manifests, Locust.

**Approved design:** docs/superpowers/specs/2026-08-28-vichara-genai-portfolio-design.md

**Project root:** D:\Vichara-GenAI-Portfolio

**Known machine state at planning time:**

- D: free space: 990.3 GB
- Host Python: 3.11.15
- WSL Ubuntu Python: 3.12.3
- uv: 0.11.20 on Windows and available in WSL
- Node: 24.11.1; npm: 11.6.2
- Git: 2.52.0
- Docker Desktop: installed, currently stopped
- GPU in WSL: RTX 4060 Laptop GPU, 8,188 MiB
- Ollama: not installed

---

## Delivery gates

| Gate | Required evidence | Scope decision |
|---|---|---|
| G0 Foundation | Clean scaffold, locked dependencies, health test, Docker running | Stop and repair before feature work |
| G1 BondLens | Real Benchmark 2026-B42 ingest, deterministic comparison, cited chat, UI | Must pass |
| G2 AltSignal | Five source adapters, n8n run, PyTorch report, cited brief, UI | **DEFERRED** |
| G3 PrivateAI Ops | Local LLM, MLflow eval, metrics, auth/audit, failure behavior | **DEFERRED** (local LLM + MLflow eval move into G1) |
| G4 Portfolio release | Clean start command, automated tests, screenshots, demo scripts, CV bullets | Must pass |
| G5 Framing check | No artifact names Lekhraj as founder or references NutriCart/Trosky - README, CV bullets, code comments, commit author, demo copy | Must pass before anything leaves the machine |

### Deadline order

1. Foundation and BondLens are the whole of the first release.
2. AltSignal is deferred and reuses the same data/provenance/model seams when resumed.
3. PrivateAI Ops is deferred, except the local model gateway (Task 12) and MLflow evaluation (Task 26), which BondLens needs.
4. Kubernetes, load tests, and visual polish come after functional gates.
5. If time compresses, use the approved design's scope cuts; never replace real data or tests with unsupported CV claims.

---

## Repository structure

~~~text
D:\Vichara-GenAI-Portfolio\
├── .env.example
├── .gitignore
├── compose.yaml
├── README.md
├── backend\
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── alembic.ini
│   ├── migrations\
│   ├── src\vichara_portfolio\
│   │   ├── main.py
│   │   ├── settings.py
│   │   ├── shared\
│   │   │   ├── domain.py
│   │   │   ├── provenance.py
│   │   │   ├── http.py
│   │   │   ├── storage.py
│   │   │   ├── jobs.py
│   │   │   └── observability.py
│   │   ├── bondlens\
│   │   │   ├── domain.py
│   │   │   ├── ports.py
│   │   │   ├── service.py
│   │   │   ├── analytics.py
│   │   │   ├── agent.py
│   │   │   ├── api.py
│   │   │   └── adapters\
│   │   │       ├── sec_edgar.py
│   │   │       ├── filing_store.py
│   │   │       ├── abs_ee.py
│   │   │       ├── repository.py
│   │   │       └── faiss_index.py
│   │   ├── altsignal\
│   │   │   ├── domain.py
│   │   │   ├── ports.py
│   │   │   ├── service.py
│   │   │   ├── features.py
│   │   │   ├── model.py
│   │   │   ├── agent.py
│   │   │   ├── api.py
│   │   │   └── adapters\
│   │   │       ├── treasury.py
│   │   │       ├── bls.py
│   │   │       ├── world_bank.py
│   │   │       ├── federal_register.py
│   │   │       ├── usaspending.py
│   │   │       └── repository.py
│   │   ├── model_gateway\
│   │   │   ├── ports.py
│   │   │   ├── ollama.py
│   │   │   ├── deterministic.py
│   │   │   └── circuit_breaker.py
│   │   └── ops\
│   │       ├── auth.py
│   │       ├── audit.py
│   │       ├── evaluation.py
│   │       └── api.py
│   ├── scripts\
│   │   ├── ingest_bondlens.py
│   │   ├── ingest_altsignal.py
│   │   ├── train_regime_model.py
│   │   ├── run_evaluations.py
│   │   └── seed_demo_user.py
│   └── tests\
│       ├── unit\
│       ├── contract\
│       ├── integration\
│       ├── e2e\
│       ├── fixtures\
│       └── golden\
├── frontend\
│   ├── src\
│   │   ├── app\
│   │   ├── api\
│   │   ├── features\bondlens\
│   │   ├── features\altsignal\
│   │   ├── features\ops\
│   │   └── components\
│   └── tests\
├── infra\
│   ├── docker\
│   ├── n8n\workflows\
│   ├── prometheus\
│   ├── grafana\provisioning\
│   ├── k8s\
│   └── locust\
├── docs\
│   ├── architecture\
│   ├── api-audit.md
│   ├── demo\
│   └── cv\
├── scripts\
│   ├── bootstrap.ps1
│   ├── dev.ps1
│   ├── verify.ps1
│   └── stop.ps1
├── .cache\huggingface\               # ignored
├── .data\                            # ignored
└── .models\ollama\                   # ignored
~~~

---

### Task 1: Create the repository safely

**Files:**

- Create: D:\Vichara-GenAI-Portfolio\.gitignore
- Create: D:\Vichara-GenAI-Portfolio\README.md
- Create: D:\Vichara-GenAI-Portfolio\docs\architecture\README.md
- Create: D:\Vichara-GenAI-Portfolio\docs\plans\2026-08-28-vichara-genai-portfolio-design.md
- Create: D:\Vichara-GenAI-Portfolio\docs\plans\2026-08-28-vichara-genai-portfolio-implementation.md

- [ ] **Step 1: Verify the exact target**

~~~powershell
$repoRoot = 'D:\Vichara-GenAI-Portfolio'
$resolvedDrive = (Resolve-Path -LiteralPath 'D:\').Path
if ($resolvedDrive -ne 'D:\') { throw 'Unexpected D drive resolution' }
if (Test-Path -LiteralPath $repoRoot) { throw 'Target already exists; inspect before continuing' }
~~~

Expected: no output and no exception.

- [ ] **Step 2: Create the root and initialize Git**

~~~powershell
New-Item -ItemType Directory -Path $repoRoot | Out-Null
Set-Location -LiteralPath $repoRoot
git init -b main
~~~

Expected: initialized empty repository on main.

- [ ] **Step 3: Create the planned directory tree**

Use New-Item only for directories. Use apply_patch for all hand-authored files.

- [ ] **Step 4: Copy the approved design and implementation plan into the new repository**

Copy these two planning artifacts mechanically without modifying their knowledge-base originals:

- C:\Users\kasar\Documents\Javis Knowledge Base\docs\superpowers\specs\2026-08-28-vichara-genai-portfolio-design.md
- C:\Users\kasar\Documents\Javis Knowledge Base\docs\plans\2026-08-28-vichara-genai-portfolio.md

- [ ] **Step 5: Write the root .gitignore**

It must ignore .env, local data, model files, caches, Python/Node build output, MLflow artifacts, n8n state, Grafana state, and Playwright reports while preserving .env.example and fixture data.

- [ ] **Step 6: Add a repository-purpose README**

State the three products, keyless-data guarantee, local-first status, hardware expectation, and honest non-production boundary.

- [ ] **Step 7: Verify only intended scaffold files exist**

~~~powershell
git status --short
~~~

Expected: only new repository scaffold files.

- [ ] **Step 8: Commit**

~~~powershell
git add -A
git commit -m "chore: scaffold Vichara GenAI portfolio"
~~~

---

### Task 2: Bootstrap Python and frontend dependency locks

**Files:**

- Create: backend\pyproject.toml
- Create: backend\src\vichara_portfolio\__init__.py
- Create: backend\tests\unit\test_smoke.py
- Create: frontend\package.json and Vite scaffold
- Create: scripts\bootstrap.ps1

> **Filesystem gotcha:** the project lives on `/mnt/d`, which is a 9p mount. Creating the uv venv there makes installing torch, faiss, sentence-transformers, and mlflow extremely slow and prone to partial writes. Set `UV_PROJECT_ENVIRONMENT=$HOME/.venvs/vichara` (WSL-native ext4) so source stays on D: but the environment does not. Same reasoning applies to `node_modules` if the frontend install crawls.

> **torch weight:** torch is used only for a small MLP in the deferred AltSignal work. It is not needed for the BondLens release. Defer `uv add torch` until Task 22 rather than pulling ~2.5 GB of CUDA wheels now.

- [ ] **Step 1: Initialize the backend in WSL**

~~~powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/d/Vichara-GenAI-Portfolio && uv init --package --name vichara-portfolio --python 3.12 --vcs none backend"
~~~

- [ ] **Step 2: Add core backend packages**

~~~powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/d/Vichara-GenAI-Portfolio/backend && uv add fastapi 'uvicorn[standard]' pydantic-settings httpx tenacity aiolimiter structlog sqlalchemy 'psycopg[binary]' alembic redis rq prometheus-client pyjwt pwdlib lxml defusedxml polars numpy"
wsl -d Ubuntu -- bash -lc "cd /mnt/d/Vichara-GenAI-Portfolio/backend && uv add --dev pytest pytest-asyncio pytest-cov respx fakeredis locust ruff mypy"
~~~

- [ ] **Step 3: Add GenAI and ML packages**

~~~powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/d/Vichara-GenAI-Portfolio/backend && uv add langgraph langchain-core langchain-ollama llama-index-core llama-index-embeddings-huggingface llama-index-vector-stores-faiss faiss-cpu sentence-transformers torch scikit-learn mlflow"
~~~

If Linux wheel resolution fails, stop and resolve it; do not silently swap FAISS or PyTorch out of the deliverable.

- [ ] **Step 4: Initialize React/Vite**

~~~powershell
Set-Location -LiteralPath 'D:\Vichara-GenAI-Portfolio'
npm create vite@latest frontend -- --template react-ts
Set-Location -LiteralPath '.\frontend'
npm install
npm install react-router-dom @tanstack/react-query zod lucide-react react-plotly.js plotly.js-dist-min
npm install --save-dev vitest @vitest/coverage-v8 jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event @types/plotly.js @playwright/test
npx playwright install chromium
~~~

- [ ] **Step 5: Configure test scripts and write one backend and one frontend smoke test**

Add Vitest scripts to frontend/package.json:

~~~json
{
  "scripts": {
    "test": "vitest",
    "test:coverage": "vitest run --coverage",
    "e2e": "playwright test"
  }
}
~~~

Configure Vitest for jsdom and a shared testing-library setup file. Add pytest, Ruff, and mypy sections to backend/pyproject.toml so all tools use src and tests consistently.

Backend expected test:

~~~python
def test_test_runner_is_alive() -> None:
    assert 2 + 2 == 4
~~~

Frontend expected test:

~~~typescript
import { describe, expect, it } from "vitest";

describe("test runner", () => {
  it("is alive", () => expect(2 + 2).toBe(4));
});
~~~

- [ ] **Step 6: Run both test runners**

~~~powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/d/Vichara-GenAI-Portfolio/backend && uv run pytest -q"
Set-Location -LiteralPath 'D:\Vichara-GenAI-Portfolio\frontend'
npm run test -- --run
~~~

Expected: both pass.

- [ ] **Step 7: Commit**

~~~powershell
git add -A
git commit -m "chore: lock Python and React toolchains"
~~~

---

### Task 3: Start Docker Desktop and create deterministic runtime checks

**Files:**

- Create: scripts\check-runtime.ps1
- Create: backend\src\vichara_portfolio\runtime.py
- Create: backend\tests\unit\test_runtime.py

- [ ] **Step 1: Write a failing runtime capability test**

Test a pure function that turns discovered capabilities into explicit readiness statuses. Docker and Ollama must be separate statuses; missing Ollama must not prevent fixture-backed unit tests.

- [ ] **Step 2: Run and confirm failure**

~~~powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/d/Vichara-GenAI-Portfolio/backend && uv run pytest tests/unit/test_runtime.py -q"
~~~

Expected: import failure.

- [ ] **Step 3: Implement capability reporting**

Return typed results for WSL Python, D-drive writability, GPU visibility, Docker availability, Ollama availability, and API cache path.

- [ ] **Step 4: Start Docker Desktop**

~~~powershell
$dockerDesktop = 'C:\Program Files\Docker\Docker\Docker Desktop.exe'
if (-not (Test-Path -LiteralPath $dockerDesktop)) { throw 'Docker Desktop executable not found' }
Start-Process -FilePath $dockerDesktop -WindowStyle Hidden
~~~

Poll docker info for at most 60 seconds in ten-second tool waits. Do not block silently beyond 60 seconds.

- [ ] **Step 5: Re-run tests and runtime script**

Expected: tests pass; Docker reports ready. Ollama may still report missing.

- [ ] **Step 6: Commit**

~~~powershell
git add -A
git commit -m "chore: add runtime readiness checks"
~~~

---

### Task 4: Define settings, storage, and secret-free configuration

**Files:**

- Create: .env.example
- Create: backend\src\vichara_portfolio\settings.py
- Create: backend\src\vichara_portfolio\shared\storage.py
- Create: backend\tests\unit\shared\test_settings.py
- Create: backend\tests\unit\shared\test_storage.py

- [ ] **Step 1: Write failing settings tests**

Verify:

- all large paths resolve below D:\Vichara-GenAI-Portfolio;
- SEC_USER_AGENT is required for live SEC calls but is not treated as a secret;
- live external calls default off in tests;
- model provider defaults to deterministic in tests and Ollama in local development;
- no FRED or external LLM key setting exists.

- [ ] **Step 2: Implement Pydantic settings**

Required settings include data_root, raw_root, faiss_root, mlflow_root, database_url, redis_url, ollama_base_url, ollama_model, sec_user_agent, jwt_secret, and external_network_enabled.

- [ ] **Step 3: Implement content-addressed raw storage**

The store writes bytes under source/checksum, returns checksum/path/size, and never overwrites mismatched content.

- [ ] **Step 4: Run tests**

Expected: settings and storage tests pass.

- [ ] **Step 5: Create local .env**

Populate SEC_USER_AGENT from the existing CV contact email. Generate JWT_SECRET locally. Never commit .env.

- [ ] **Step 6: Commit**

~~~powershell
git add -A
git commit -m "feat: add local-first settings and immutable source storage"
~~~

---

### Task 5: Build shared provenance and resilient HTTP seams

**Files:**

- Create: backend\src\vichara_portfolio\shared\provenance.py
- Create: backend\src\vichara_portfolio\shared\http.py
- Create: backend\tests\unit\shared\test_provenance.py
- Create: backend\tests\unit\shared\test_http.py

- [ ] **Step 1: Write failing provenance tests**

Define SourceRef with source_name, source_url, retrieved_at, checksum, filing accession or external record ID, and optional field path.

- [ ] **Step 2: Write failing HTTP tests using respx**

Cover 200 JSON, 429 Retry-After, 500 retry, timeout, invalid content type, immutable cache hit, and SEC request headers/rate ceiling.

- [ ] **Step 3: Implement ResilientHttpClient**

GET retries must be bounded. POST retries must require an idempotency flag. Every successful response returns payload plus provenance metadata.

- [ ] **Step 4: Implement SEC-specific limiter**

Use a process-local limiter set to 8 requests/second. Worker concurrency for SEC jobs must remain one.

- [ ] **Step 5: Run tests**

Expected: all network behavior is deterministic with no live request.

- [ ] **Step 6: Commit**

~~~powershell
git add -A
git commit -m "feat: add provenance and resilient HTTP foundation"
~~~

---

### Task 6: Implement SEC submissions discovery

**Files:**

- Create: backend\src\vichara_portfolio\bondlens\domain.py
- Create: backend\src\vichara_portfolio\bondlens\ports.py
- Create: backend\src\vichara_portfolio\bondlens\adapters\sec_edgar.py
- Create: backend\tests\fixtures\sec\submissions_minimal.json
- Create: backend\tests\contract\bondlens\test_sec_submissions.py

- [ ] **Step 1: Write a minimal Benchmark 2026-B42 fixture**

Include CIK 0002110410 and representative ABS-EE, 10-D, and 8-K rows with accession, filing date, report date, and primary document.

- [ ] **Step 2: Write failing adapter contract tests**

Verify CIK zero-padding, form filtering, accession normalization, chronological ordering, and SourceRef creation.

- [ ] **Step 3: Implement SecEdgarClient.list_filings**

Use https://data.sec.gov/submissions/CIK##########.json and map parallel SEC arrays safely.

- [ ] **Step 4: Run fixture-backed contract test**

Expected: PASS without network.

- [ ] **Step 5: Run one explicitly marked live test**

~~~powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/d/Vichara-GenAI-Portfolio/backend && VICHARA_EXTERNAL_NETWORK_ENABLED=true uv run pytest -m live tests/contract/bondlens/test_sec_submissions.py -q"
~~~

Expected: entity name contains Benchmark 2026-B42 and at least one ABS-EE filing.

- [ ] **Step 6: Commit**

~~~powershell
git add -A
git commit -m "feat(bondlens): discover SEC filings by CIK"
~~~

---

### Task 7: Resolve filing exhibits and persist raw documents

**Files:**

- Create: backend\src\vichara_portfolio\bondlens\adapters\filing_store.py
- Create: backend\tests\fixtures\sec\filing_index.html
- Create: backend\tests\contract\bondlens\test_filing_store.py

> **MEASURED BUG - this is why the task exists.** EDGAR's `index.json` silently omits exhibits. For accessions `0001888524-26-007544` (Apr), `-010373` (May), and `-012270` (Jun) it lists only the ABS-EE cover `.htm`; `exh_102.xml` is absent from the listing but exists and returns HTTP 200 at 585,970 bytes. Only the July accession lists all three documents. The authoritative document list is the `<TYPE>` / `<FILENAME>` pairs in the full `<accession>.txt` submission header, which is correct for all five filings. **Resolve from the `.txt` header; treat `index.json` as a hint only.** A resolver built on `index.json` finds zero assets for three of five periods and looks like a parser bug.

- [ ] **Step 1: Write failing exhibit-resolution tests**

Given a full `.txt` submission header, select the ABS-EE primary document, EX-102 asset XML, and EX-103 explanatory document. Include a fixture where `index.json` is missing EX-102 but the `.txt` header lists it, and assert the resolver still finds it.

- [ ] **Step 2: Implement filing-index URL construction**

Use unpadded CIK, accession without hyphens for the directory, and accession with hyphens for the `.txt` filename. Verified pattern: `https://www.sec.gov/Archives/edgar/data/2110410/000188852426010373/0001888524-26-010373.txt`, and exhibits at `.../000188852426010373/exh_102.xml`.

- [ ] **Step 3: Implement exhibit resolution and immutable download**

Validate sec.gov host, allowed content type, declared size where available, and checksum. Reject path traversal and non-SEC links.

- [ ] **Step 4: Run contract tests**

Expected: all fixture documents resolve to typed FilingDocument objects.

- [ ] **Step 5: Run a live smoke for one small CMBS EX-102**

Store under .data/raw/sec; output path, checksum, and byte count. Never redownload if checksum metadata confirms a cache hit.

- [ ] **Step 6: Commit**

~~~powershell
git add -A
git commit -m "feat(bondlens): resolve and cache SEC filing exhibits"
~~~

---

### Task 8: Parse ABS-EE CMBS asset data

**Files:**

- Create: backend\src\vichara_portfolio\bondlens\adapters\abs_ee.py
- Create: backend\tests\fixtures\sec\abs_ee_two_assets.xml
- Create: backend\tests\unit\bondlens\test_abs_ee.py

- [ ] **Step 1: Write a two-asset XML fixture**

Include namespace variation, missing optional values, property fields, occupancy, valuation, revenue, expenses, NOI, NCF, asset number, and reporting-period dates.

- [ ] **Step 2: Write failing parser tests**

Verify Decimal parsing, percentage normalization, date parsing, namespace independence, raw-field preservation, missing-value handling, and one SourceRef per normalized asset.

- [ ] **Step 3: Implement streaming XML parsing**

Use defusedxml/lxml iterparse, clear processed elements, and avoid loading large 100 MB files into a full DOM.

- [ ] **Step 4: Define normalized models**

Create Deal, Filing, ReportingPeriod, Loan, PropertySnapshot, and DataQualityIssue types. Preserve unmapped source fields in a JSON-compatible dictionary.

**Do not flatten the two field families.** The CMBS ABS-EE schema carries `*Securitization*` fields (frozen at issuance, identical in every period) alongside `mostRecent*` fields (servicer-updated, sparsely populated). Model them separately and mark which family each value came from, or every comparison tool will report false zeros. Measured on this deal: `mostRecent*` property financials are populated for 29 of 123 properties, on a quarterly window.

- [ ] **Step 5: Run tests**

Expected: two assets parsed and memory-safe code path exercised.

- [ ] **Step 6: Parse the audited real filing**

Expected, measured against the July 2026 `exh_102.xml` (588,639 bytes): **62 loan records and 123 property records**, root element `assetData` in namespace `http://www.sec.gov/edgar/document/absee/cmbs/assetdata`, and no fatal data-quality errors. The May file parses to the same 62/123 shape. If loan count differs from 62, the parser is treating `property` children as top-level assets.

- [ ] **Step 7: Commit**

~~~powershell
git add -A
git commit -m "feat(bondlens): parse SEC ABS-EE property snapshots"
~~~

---

### Task 9: Add relational schema, migrations, and repositories

**Files:**

- Create: backend\src\vichara_portfolio\shared\db.py
- Create: backend\src\vichara_portfolio\bondlens\adapters\repository.py
- Create: backend\migrations\versions\0001_core_and_bondlens.py
- Create: backend\tests\integration\bondlens\test_repository.py
- Create: infra\docker\postgres-init.sql

- [ ] **Step 1: Add PostgreSQL and Redis to compose.yaml**

Use postgres:16-alpine and redis:7-alpine.

> **Do not bind-mount the PostgreSQL data directory to a Windows path.** `PGDATA` on a `/mnt/d` bind mount under WSL2 Docker Desktop fails on ownership and fsync semantics. Use a **named Docker volume** for `postgres` (and for `n8n` and `grafana` state, which have the same problem). Large read-mostly artifacts that are not databases - raw SEC downloads, the FAISS index, HuggingFace cache, Ollama models - can stay on D: as bind mounts as designed.

- [ ] **Step 2: Start only database dependencies**

~~~powershell
Set-Location -LiteralPath 'D:\Vichara-GenAI-Portfolio'
docker compose up -d postgres redis
docker compose ps
~~~

Expected: both healthy.

- [ ] **Step 3: Write failing repository integration tests**

Cover idempotent filing upsert, reporting periods, assets, property snapshots, provenance, duplicate checksum handling, and transaction rollback.

- [ ] **Step 4: Create SQLAlchemy models and Alembic migration**

Tables: source_documents, ingestion_runs, cmbs_deals, cmbs_filings, cmbs_reporting_periods, cmbs_assets, cmbs_property_snapshots, data_quality_issues, audit_events.

- [ ] **Step 5: Run migration and tests**

~~~powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/d/Vichara-GenAI-Portfolio/backend && uv run alembic upgrade head && uv run pytest tests/integration/bondlens/test_repository.py -q"
~~~

Expected: PASS and rerunning the same ingest changes no row counts.

- [ ] **Step 6: Commit**

~~~powershell
git add -A
git commit -m "feat(bondlens): persist normalized CMBS data"
~~~

---

### Task 10: Implement deterministic BondLens analytics tools

**Files:**

- Create: backend\src\vichara_portfolio\bondlens\analytics.py
- Create: backend\src\vichara_portfolio\bondlens\service.py
- Create: backend\tests\unit\bondlens\test_analytics.py
- Create: backend\tests\unit\bondlens\test_service.py

- [ ] **Step 1: Write failing pure-function tests**

Cover deal summary, loan-level reporting-period comparison, payment-status migration, balance-versus-schedule drift, advances outstanding, missing-period behavior, rank ordering, ties, null values, and deterministic distress score explanation.

Pin these as exact-value regression tests from the measured May-to-July window:

| Loan | Property | `paymentStatusLoanCode` |
|---|---|---|
| 30 | Cummins Station, Nashville TN | `0` to `B` (newly late) |
| 16 | PWC Pennant, St. Louis MO | `B` to `0` (cured) |
| 39 | 325 East 14th Street, New York NY | `B` to `0` (cured) |

Also assert 24 of 62 loans show movement in `reportPeriodEndActualBalanceAmount`, and that property-level NOI comparison over the same window returns **zero** deteriorations - the three properties whose NOI "changed" went from null to a first reported value and must not be ranked as deterioration.

- [ ] **Step 2: Define tool output schemas**

Every tool returns values, units, period boundaries, formula version, data-quality flags, and SourceRef objects.

- [ ] **Step 3: Implement tools**

Implement `get_deal_summary`, `compare_reporting_periods`, `rank_loans_by_status_change`, `rank_loans_by_balance_drift`, `get_loan_history`, and `get_property_profile`. Use Decimal for authoritative financial arithmetic.

`get_property_profile` returns a point-in-time profile, not a time series - the underlying fields do not vary on this deal. Any tool that would rank properties by change must return an explicit empty result with a reason, never a fabricated ordering.

- [ ] **Step 4: Add service orchestration**

The service accepts ports, not concrete SEC/Postgres adapters. Live ingestion is idempotent and reports created/skipped/failed counts.

- [ ] **Step 5: Run tests**

Expected: exact numeric assertions pass; no LLM dependency exists.

- [ ] **Step 6: Commit**

~~~powershell
git add -A
git commit -m "feat(bondlens): add deterministic surveillance tools"
~~~

---

### Task 11: Build narrative ingestion and FAISS retrieval

**Files:**

- Create: backend\src\vichara_portfolio\bondlens\adapters\faiss_index.py
- Create: backend\src\vichara_portfolio\bondlens\rag.py
- Create: backend\tests\unit\bondlens\test_chunking.py
- Create: backend\tests\integration\bondlens\test_faiss_index.py

- [ ] **Step 1: Write failing chunking tests**

Verify heading-aware text extraction, stable chunk IDs, accession metadata, 800-token target, overlap, empty-document rejection, and source offsets.

- [ ] **Step 2: Define VectorIndex port**

Methods: upsert_chunks, search, delete_document, persist, load. SearchResult includes score, text, metadata, and SourceRef.

- [ ] **Step 3: Implement local embeddings and FAISS adapter**

Use BAAI/bge-small-en-v1.5, cache under .cache/huggingface, normalize embeddings, and persist index plus an atomic metadata sidecar under .data/faiss.

- [ ] **Step 4: Run WSL integration test**

Expected: a known query retrieves the matching fixture chunk in top three.

- [ ] **Step 5: Index the seed deal's narrative filings**

Record document count, chunk count, model name, embedding dimension, checksum, and elapsed time.

- [ ] **Step 6: Commit**

~~~powershell
git add -A
git commit -m "feat(bondlens): add local FAISS filing retrieval"
~~~

---

### Task 12: Install Ollama on D: and implement the model-provider port

**Files:**

- Create: backend\src\vichara_portfolio\model_gateway\ports.py
- Create: backend\src\vichara_portfolio\model_gateway\deterministic.py
- Create: backend\src\vichara_portfolio\model_gateway\ollama.py
- Create: backend\tests\contract\model_gateway\test_provider_contract.py
- Modify: scripts\bootstrap.ps1

- [ ] **Step 1: Write provider contract tests**

Both deterministic and Ollama providers must expose health, generate, structured_generate, model metadata, latency, and error categories.

- [ ] **Step 2: Implement deterministic provider**

It returns fixture-controlled structured responses and is the only provider used in unit/CI tests.

- [ ] **Step 3: Set model storage before installation**

~~~powershell
$modelRoot = 'D:\Vichara-GenAI-Portfolio\.models\ollama'
New-Item -ItemType Directory -Force -Path $modelRoot | Out-Null
$env:OLLAMA_MODELS = $modelRoot
[Environment]::SetEnvironmentVariable('OLLAMA_MODELS', $modelRoot, 'User')
~~~

- [ ] **Step 4: Install Ollama**

~~~powershell
winget install --id Ollama.Ollama --exact --accept-source-agreements --accept-package-agreements
~~~

**User checkpoint:** approve UAC only if Windows displays it.

- [ ] **Step 5: Start Ollama hidden and pull the model**

~~~powershell
$installedOllama = Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'
$ollamaExe = if (Test-Path -LiteralPath $installedOllama) {
    $installedOllama
} else {
    (Get-Command ollama -ErrorAction Stop).Source
}
Get-Process -Name 'ollama' -ErrorAction SilentlyContinue | Stop-Process
Start-Process -FilePath $ollamaExe -ArgumentList 'serve' -WindowStyle Hidden
& $ollamaExe pull llama3.1:8b
& $ollamaExe list
~~~

Expected: llama3.1:8b is present under D: and Ollama responds on localhost:11434.

> **WSL cannot reach the host on `localhost`.** Ollama runs on the Windows host GPU while the dev backend runs inside WSL. Set `OLLAMA_HOST=0.0.0.0:11434` before starting the server, allow the port through Windows Firewall for the WSL subnet, and point the backend at the host IP from `/etc/resolv.conf` (or `$(hostname).local`) rather than `localhost`. The Docker path already handles this via `host.docker.internal` in Task 29; the dev path does not. If the exact tag has changed, inspect the official Ollama library and record the resolved compatible tag before changing configuration.

- [ ] **Step 6: Implement Ollama adapter**

Use bounded context, temperature 0 for analyst tools, one concurrent generation on the 8 GB GPU, typed JSON validation, timeout, and no silent fallback for user-facing answers.

- [ ] **Step 7: Run provider contract and one live inference**

Expected: structured response validates; nvidia-smi shows GPU use; model metadata is recorded.

- [ ] **Step 8: Commit**

~~~powershell
git add -A
git commit -m "feat: add local Ollama model gateway"
~~~

---

### Task 13: Implement the BondLens LangGraph workflow

**Files:**

- Create: backend\src\vichara_portfolio\bondlens\agent.py
- Create: backend\tests\unit\bondlens\test_agent.py
- Create: backend\tests\golden\bondlens_questions.yaml

- [ ] **Step 1: Write failing routing tests**

Questions requesting amounts/comparisons must route to deterministic analytics; narrative questions may route to retrieval; mixed questions use both.

- [ ] **Step 2: Define typed graph state**

State contains question, deal ID, periods, planned tools, tool evidence, retrieved chunks, draft, verification errors, citations, and final answer.

- [ ] **Step 3: Implement graph nodes**

Nodes: plan, execute_tools, retrieve_context, draft, verify, repair_once, finalize. Reject finalization when numeric claims lack tool evidence or factual claims lack citations.

- [ ] **Step 4: Add injection-safe prompt boundaries**

Treat filing content and API payloads as untrusted evidence, never instructions. Strip tool-like directives from sources and label them clearly in prompts.

- [ ] **Step 5: Run deterministic-provider tests**

Expected: routing, rejection, citation, and single-repair behavior pass without Ollama.

- [ ] **Step 6: Run five live golden questions**

Expected: valid citations, no unsupported property names, exact deterministic numbers.

- [ ] **Step 7: Commit**

~~~powershell
git add -A
git commit -m "feat(bondlens): add verified LangGraph analyst"
~~~

---

### Task 14: Expose BondLens API and background jobs

**Files:**

- Create: backend\src\vichara_portfolio\main.py
- Create: backend\src\vichara_portfolio\shared\jobs.py
- Create: backend\src\vichara_portfolio\bondlens\api.py
- Create: backend\tests\integration\bondlens\test_api.py
- Create: backend\scripts\ingest_bondlens.py

- [ ] **Step 1: Write failing API tests**

Endpoints:

- GET /health/live
- GET /health/ready
- POST /api/bondlens/ingestions
- GET /api/bondlens/ingestions/{job_id}
- GET /api/bondlens/deals
- GET /api/bondlens/deals/{deal_id}/summary
- GET /api/bondlens/deals/{deal_id}/compare
- POST /api/bondlens/chat

- [ ] **Step 2: Implement RQ job envelope**

Jobs have idempotency key, status, progress, structured error, timestamps, and audit correlation ID.

- [ ] **Step 3: Implement routers and dependency wiring**

Keep FastAPI handlers thin. Return typed response models and source URLs.

- [ ] **Step 4: Run integration tests**

Expected: fake ports pass; invalid periods return 422; missing model returns controlled 503 only for chat.

- [ ] **Step 5: Run real seed ingestion through the job API**

Expected: completed job, at least three reporting periods if SEC has them, and repeat request is idempotent.

- [ ] **Step 6: Commit**

~~~powershell
git add -A
git commit -m "feat(bondlens): expose ingestion analytics and chat API"
~~~

---

### Task 15: Build the React product shell from the existing CMBS base

**Files:**

- Copy mechanically from: C:\Users\kasar\Documents\Javis Knowledge Base\wiki\analyses\vichara-cmbs-react\src
- Create: frontend\src\app\router.tsx
- Create: frontend\src\app\providers.tsx
- Create: frontend\src\api\client.ts
- Create: frontend\src\features\bondlens\BondLensPage.tsx
- Create: frontend\tests\app\router.test.tsx

- [ ] **Step 1: Copy the existing UI into a temporary feature directory**

Preserve the knowledge-base source. Do not modify or delete it.

- [ ] **Step 2: Write failing router tests**

Verify /bondlens, /altsignal, and /ops routes plus a default redirect to /bondlens.

- [ ] **Step 3: Add React Router, QueryClient, typed API client, and error boundary**

The API client must parse Zod schemas and show source/service errors instead of accepting malformed JSON.

- [ ] **Step 4: Adapt the existing visual shell**

Keep its established layout/components, move static deal data behind feature adapters, and retain fixtures only for Story/demo loading states.

- [ ] **Step 5: Run unit tests and production build**

~~~powershell
Set-Location -LiteralPath 'D:\Vichara-GenAI-Portfolio\frontend'
npm run test -- --run
npm run build
~~~

Expected: PASS and successful Vite build.

- [ ] **Step 6: Commit**

~~~powershell
git add -A
git commit -m "feat(web): establish three-product React shell"
~~~

---

### Task 16: Connect BondLens UI and replace canned chat

**Files:**

- Create: frontend\src\features\bondlens\api.ts
- Create: frontend\src\features\bondlens\hooks.ts
- Create: frontend\src\features\bondlens\components\DealSelector.tsx
- Create: frontend\src\features\bondlens\components\PeriodComparison.tsx
- Create: frontend\src\features\bondlens\components\EvidenceDrawer.tsx
- Modify: migrated ChatPanel.tsx
- Remove from runtime imports: migrated cannedResponses.ts
- Create: frontend\tests\bondlens\chat.test.tsx
- Create: frontend\tests\bondlens\dashboard.test.tsx

- [ ] **Step 1: Write failing component tests**

Cover real deal loading, period selection, comparison rendering, citation click, chat pending/error/success, and no canned-response path.

- [ ] **Step 2: Implement query hooks and typed view models**

Preserve units and source IDs. Never format null as zero.

- [ ] **Step 3: Connect dashboard panels**

Use backend summary/comparison data for KPI, geography, property types, occupancy/NOI changes, and deterioration ranking. Label fields unavailable in ABS-EE instead of inventing them.

- [ ] **Step 4: Replace canned chat**

POST to /api/bondlens/chat, render tool-derived tables, citations, warnings, and controlled model-unavailable state.

- [ ] **Step 5: Add Playwright BondLens flow**

Open /bondlens, select deal/periods, run comparison, ask a golden question, and open one SEC citation.

- [ ] **Step 6: Run tests/build/e2e**

Expected: all pass against fixture server, then one pass against local API.

- [ ] **Step 7: Commit**

~~~powershell
git add -A
git commit -m "feat(bondlens): connect real CMBS dashboard and cited chat"
~~~

---

### Task 17: Create BondLens evaluation and G1 report

**Files:**

- Create: backend\src\vichara_portfolio\ops\evaluation.py
- Create: backend\scripts\run_evaluations.py
- Create: backend\tests\unit\ops\test_evaluation.py
- Create: docs\demo\bondlens-golden-questions.md
- Generate: .data\reports\bondlens-evaluation.json

- [ ] **Step 1: Write failing metric tests**

Metrics: tool routing accuracy, numeric exactness, citation coverage, source validity, retrieval recall@k, latency, and unsupported-claim count.

- [ ] **Step 2: Implement evaluator**

Separate deterministic checks from optional local-LLM judging. Store question, configuration, evidence IDs, output, metrics, and failures.

- [ ] **Step 3: Run the full BondLens golden set**

Do not tune on the held-out questions. Record model, prompt version, index checksum, and data snapshot.

- [ ] **Step 4: Enforce G1**

Required: 100% source URL validity, 100% deterministic numeric exactness, zero uncited final factual paragraphs, and successful Playwright flow.

Include at least one **negative golden question** that has no answer in the data - for example, "which properties deteriorated most between May and July?" The correct behaviour is to report that the deal's property financials do not vary over that window and to name the three loan-level status changes instead. An answer that invents property deterioration fails G1 outright.

- [ ] **Step 5: Commit**

~~~powershell
git add -A
git commit -m "test(bondlens): add golden evaluation and G1 evidence"
~~~

---

### Task 18: Implement Treasury, BLS v1, and World Bank adapters

**Files:**

- Create: backend\src\vichara_portfolio\altsignal\domain.py
- Create: backend\src\vichara_portfolio\altsignal\ports.py
- Create: backend\src\vichara_portfolio\altsignal\adapters\treasury.py
- Create: backend\src\vichara_portfolio\altsignal\adapters\bls.py
- Create: backend\src\vichara_portfolio\altsignal\adapters\world_bank.py
- Create: backend\tests\contract\altsignal\test_macro_adapters.py
- Create: backend\tests\fixtures\altsignal\macro\

- [ ] **Step 1: Write frozen response fixtures from the audited endpoints**

Remove irrelevant rows but retain authentic response shapes and metadata.

- [ ] **Step 2: Write failing adapter contracts**

All adapters return MacroObservation with series ID, label, geography, frequency, observation date, value, unit, release/retrieval time, and SourceRef.

- [ ] **Step 3: Implement Treasury client**

Use avg_interest_rates and debt_to_penny with pagination/filter support.

- [ ] **Step 4: Implement BLS v1 client**

Use the unregistered endpoint only. Batch at most 25 series, cache responses, enforce at most 25 daily live queries in local state, and cover CUUR0000SA0, LNS14000000, and CES0000000001.

- [ ] **Step 5: Implement World Bank v2 client**

Cover India and U.S. GDP, GDP growth, and inflation indicators. Preserve missing observations.

- [ ] **Step 6: Run fixture tests and one live smoke per source**

Expected: all three return non-empty typed observations with no authorization header.

- [ ] **Step 7: Commit**

~~~powershell
git add -A
git commit -m "feat(altsignal): ingest keyless macro data"
~~~

---

### Task 19: Implement Federal Register and USAspending adapters

**Files:**

- Create: backend\src\vichara_portfolio\altsignal\adapters\federal_register.py
- Create: backend\src\vichara_portfolio\altsignal\adapters\usaspending.py
- Create: backend\tests\contract\altsignal\test_event_adapters.py
- Create: backend\tests\fixtures\altsignal\events\

- [ ] **Step 1: Write failing Federal Register contract tests**

Normalize document number, title, agencies, type, publication date, abstract, HTML/PDF URLs, topics, and SourceRef. Date-window pagination must stay below the first-2,000-results restriction.

- [ ] **Step 2: Implement Federal Register client**

Default filters target securities, banking, mortgages, investment management, and AI-related regulatory terms. Caching makes demos deterministic.

- [ ] **Step 3: Write failing USAspending contract tests**

Normalize award ID, recipient, description, amount, agencies, action/start/end dates, award type, NAICS, and SourceRef.

- [ ] **Step 4: Implement USAspending client**

Use the documented v2 filtered POST endpoint, explicit timeout, limited page size, and idempotent retry policy.

- [ ] **Step 5: Run fixtures and live smokes**

Expected: Federal Register documents and at least one filtered award; no authorization header.

- [ ] **Step 6: Commit**

~~~powershell
git add -A
git commit -m "feat(altsignal): ingest regulatory and spending events"
~~~

---

### Task 20: Persist AltSignal data and build leakage-safe monthly features

**Files:**

- Create: backend\src\vichara_portfolio\altsignal\adapters\repository.py
- Create: backend\src\vichara_portfolio\altsignal\features.py
- Create: backend\migrations\versions\0002_altsignal.py
- Create: backend\tests\unit\altsignal\test_features.py
- Create: backend\tests\integration\altsignal\test_repository.py

- [ ] **Step 1: Add schema**

Tables: macro_series, macro_observations, regulatory_events, spending_awards, altsignal_snapshots, feature_sets, model_runs, research_briefs.

- [ ] **Step 2: Write failing feature tests**

Verify as-of joins, release-date availability, monthly resampling, lag creation, missingness flags, training-only scaler fit, future-label isolation, and deterministic feature order.

- [ ] **Step 3: Implement feature builder**

Produce versioned monthly rows for rate levels/changes, CPI changes, unemployment, payroll growth, regulatory event counts/materiality, and spending amount/anomaly features.

- [ ] **Step 4: Implement target**

Label next-month Treasury-rate direction as up/flat/down using a documented basis-point threshold. Keep target code separate from features.

- [ ] **Step 5: Run migration and tests**

Expected: no future timestamp can influence an earlier feature row.

- [ ] **Step 6: Commit**

~~~powershell
git add -A
git commit -m "feat(altsignal): persist data and build leakage-safe features"
~~~

---

### Task 21: Add n8n orchestration without hiding business logic

**Files:**

- Create: infra\n8n\workflows\altsignal-ingestion.json
- Create: infra\n8n\workflows\bondlens-ingestion.json
- Create: backend\src\vichara_portfolio\altsignal\api.py
- Create: backend\scripts\ingest_altsignal.py
- Create: docs\architecture\n8n-workflows.md

- [ ] **Step 1: Add n8n to compose**

Pin a current n8nio/n8n major tag, bind .data/n8n, disable telemetry, and keep schedules disabled by default.

- [ ] **Step 2: Expose idempotent ingestion endpoints**

One endpoint per source plus an aggregate job. Return job IDs, not long-running HTTP connections.

- [ ] **Step 3: Build workflow**

Manual Trigger/Schedule Trigger → source ingestion calls → wait/poll job status → merge results → call feature build → emit run summary.

- [ ] **Step 4: Import and execute manually**

Expected: all five source nodes complete or report a typed cached/degraded status; feature-set version is returned.

- [ ] **Step 5: Export the final workflow JSON**

Re-import it into a clean n8n state to prove portability.

- [ ] **Step 6: Commit**

~~~powershell
git add -A
git commit -m "feat(altsignal): orchestrate ingestion with n8n"
~~~

---

### Task 22: Train and evaluate the PyTorch regime classifier

**Files:**

- Create: backend\src\vichara_portfolio\altsignal\model.py
- Create: backend\scripts\train_regime_model.py
- Create: backend\tests\unit\altsignal\test_model.py
- Generate: .data\models\altsignal\
- Generate: .data\reports\altsignal-model.json

- [ ] **Step 1: Write failing model tests**

Cover deterministic seeding, tensor shapes, forward pass, class probabilities summing to one, temporal split boundaries, scaler isolation, checkpoint save/load, and inference schema.

- [ ] **Step 2: Implement baseline and MLP**

Baseline: majority class. MLP: two hidden layers, dropout, three output classes, weighted cross-entropy if imbalance warrants it.

- [ ] **Step 3: Implement temporal evaluation**

Use contiguous train/validation/test partitions. Report macro-F1, balanced accuracy, confusion matrix, calibration summary, and comparison to baseline.

- [ ] **Step 4: Train**

~~~powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/d/Vichara-GenAI-Portfolio/backend && uv run python scripts/train_regime_model.py --feature-version latest --seed 42"
~~~

- [ ] **Step 5: Inspect results honestly**

The pipeline must complete and report leakage-safe metrics. Do not require or claim alpha. If performance is below baseline, retain the result, diagnose it, and present the model as a reproducible research experiment.

- [ ] **Step 6: Save checkpoint and inference card**

Record feature schema, training interval, test interval, baseline, metrics, limitations, and SHA-256 checksum.

- [ ] **Step 7: Commit code and report metadata, not large binary checkpoint**

~~~powershell
git add -A
git commit -m "feat(altsignal): add PyTorch regime research model"
~~~

---

### Task 23: Implement verified AltSignal research agent and API

**Files:**

- Create: backend\src\vichara_portfolio\altsignal\service.py
- Create: backend\src\vichara_portfolio\altsignal\agent.py
- Modify: backend\src\vichara_portfolio\altsignal\api.py
- Create: backend\tests\unit\altsignal\test_agent.py
- Create: backend\tests\integration\altsignal\test_api.py
- Create: backend\tests\golden\altsignal_questions.yaml

- [ ] **Step 1: Define research-brief schema**

Fields: question, as_of_date, thesis, evidence, counter_evidence, model_signal, caveats, source_list, generated_at, model/retriever versions.

- [ ] **Step 2: Write failing verifier tests**

Reject missing source IDs, future-dated evidence, unsupported model claims, omitted caveats, and instructions embedded in source text.

- [ ] **Step 3: Implement LangGraph workflow**

Planner → structured-data tools → event retrieval → model inference → analyst → verifier → one repair → formatter.

- [ ] **Step 4: Expose API**

Endpoints for refresh, observations, events, model latest/run, briefs, and chat/research.

- [ ] **Step 5: Run deterministic and live-model golden tests**

Expected: all claims trace to typed evidence; model limitations appear in every model-referencing brief.

- [ ] **Step 6: Commit**

~~~powershell
git add -A
git commit -m "feat(altsignal): add cited investment research workflow"
~~~

---

### Task 24: Build AltSignal dashboard and G2 evaluation

**Files:**

- Create: frontend\src\features\altsignal\AltSignalPage.tsx
- Create: frontend\src\features\altsignal\api.ts
- Create: frontend\src\features\altsignal\components\MacroDashboard.tsx
- Create: frontend\src\features\altsignal\components\EventTimeline.tsx
- Create: frontend\src\features\altsignal\components\SpendingSignals.tsx
- Create: frontend\src\features\altsignal\components\ModelCard.tsx
- Create: frontend\src\features\altsignal\components\ResearchBrief.tsx
- Create: frontend\tests\altsignal\
- Generate: .data\reports\altsignal-evaluation.json

- [ ] **Step 1: Write failing component tests**

Cover source refresh, Plotly traces, missing-data display, event filters, model limitations, brief citations, and ingestion errors.

- [ ] **Step 2: Implement charts**

Use Plotly for rates, CPI/unemployment, regulatory volume, spending anomalies, regime probabilities, and confusion matrix.

- [ ] **Step 3: Implement research workflow UI**

Show plan/status, evidence, counter-evidence, caveats, and expandable source links.

- [ ] **Step 4: Add Playwright AltSignal flow**

Trigger cached refresh, inspect five source statuses, open the model report, generate a brief, and open one source.

- [ ] **Step 5: Run G2 evaluation**

Required: all five adapters have fixture and live evidence, n8n workflow exports/imports, PyTorch report exists, all golden briefs cite sources, and Playwright flow passes.

- [ ] **Step 6: Commit**

~~~powershell
git add -A
git commit -m "feat(altsignal): deliver dashboard research flow and G2 evidence"
~~~

---

### Task 25: Add JWT roles, rate limiting, and append-only audit

**Files:**

- Create: backend\src\vichara_portfolio\ops\auth.py
- Create: backend\src\vichara_portfolio\ops\audit.py
- Create: backend\migrations\versions\0003_ops_security.py
- Create: backend\scripts\seed_demo_user.py
- Create: backend\tests\integration\ops\test_auth_audit.py

- [ ] **Step 1: Write failing security tests**

Cover login success/failure, password hashing, expired/tampered JWT, analyst/operator permissions, Redis rate limit, and immutable audit events.

- [ ] **Step 2: Implement local users and roles**

Seed credentials from ignored environment variables. Never hardcode a real password.

- [ ] **Step 3: Implement rate limits**

Use Redis and return standards-compliant 429 plus Retry-After. Separate ingestion, chat, and evaluation buckets.

- [ ] **Step 4: Implement audit**

Record actor, action, object, correlation ID, timestamp, config/checksum references, and success/failure. Do not log prompts containing secrets.

- [ ] **Step 5: Run migration and tests**

Expected: unauthorized actions fail and all protected mutations produce an audit row.

- [ ] **Step 6: Commit**

~~~powershell
git add -A
git commit -m "feat(ops): add local RBAC rate limits and audit trail"
~~~

---

### Task 26: Add MLflow tracking and Prometheus metrics

**Files:**

- Create: backend\src\vichara_portfolio\shared\observability.py
- Modify: backend\src\vichara_portfolio\ops\evaluation.py
- Create: infra\prometheus\prometheus.yml
- Create: infra\grafana\provisioning\datasources\prometheus.yml
- Create: infra\grafana\provisioning\dashboards\dashboard.yml
- Create: infra\grafana\dashboards\vichara-genai.json
- Create: backend\tests\unit\shared\test_metrics.py

- [ ] **Step 1: Write failing metric tests**

Verify counters/histograms for HTTP, jobs, external adapters, retrieval, LLM latency/errors, tokens when available, evaluation scores, and circuit state. Ensure labels cannot contain question text or high-cardinality IDs.

- [ ] **Step 2: Add MLflow service to compose**

Use local backend store and .data/mlflow artifacts. No account or remote tracking server.

- [ ] **Step 3: Log evaluation runs**

Parameters: model, prompt version, embedding model, index checksum, dataset/golden-set checksum. Metrics and reports become artifacts.

- [ ] **Step 4: Configure Prometheus and Grafana**

Provision one dashboard automatically; no manual clicking required.

- [ ] **Step 5: Run one BondLens and one AltSignal evaluation**

Expected: both appear in MLflow and metrics are visible to Prometheus.

- [ ] **Step 6: Commit**

~~~powershell
git add -A
git commit -m "feat(ops): track quality latency and service health"
~~~

---

### Task 27: Implement model circuit breaker and degraded behavior

**Files:**

- Create: backend\src\vichara_portfolio\model_gateway\circuit_breaker.py
- Create: backend\tests\unit\model_gateway\test_circuit_breaker.py
- Create: backend\tests\integration\model_gateway\test_degraded_mode.py

- [ ] **Step 1: Write failing state-machine tests**

Cover closed, open, half-open, recovery, concurrent failures, timeout category, and reset.

- [ ] **Step 2: Implement circuit breaker**

The API may still serve deterministic analytics, cached dashboards, and retrieved excerpts when Ollama is down. It must not synthesize a fake LLM answer.

- [ ] **Step 3: Add readiness semantics**

Liveness stays healthy when optional model inference is down. Readiness reports degraded with component detail.

- [ ] **Step 4: Run failure integration**

Stop or redirect Ollama, call BondLens summary and chat, then restore it. Expected: summary 200, chat controlled 503/degraded payload, circuit telemetry, then recovery.

- [ ] **Step 5: Commit**

~~~powershell
git add -A
git commit -m "feat(ops): add safe model failure and recovery behavior"
~~~

---

### Task 28: Build PrivateAI Ops UI and G3 evaluation

**Files:**

- Create: frontend\src\features\ops\OpsPage.tsx
- Create: frontend\src\features\ops\api.ts
- Create: frontend\src\features\ops\components\RuntimeHealth.tsx
- Create: frontend\src\features\ops\components\EvaluationRuns.tsx
- Create: frontend\src\features\ops\components\ModelComparison.tsx
- Create: frontend\src\features\ops\components\AuditLog.tsx
- Create: frontend\src\features\ops\components\FailureControls.tsx
- Create: frontend\tests\ops\

- [ ] **Step 1: Write failing UI tests**

Cover health states, model metadata, eval comparison, audit pagination, operator-only controls, 429, and degraded model status.

- [ ] **Step 2: Expose ops API**

Endpoints for runtime, model health, evaluation runs, comparison, audit, and operator circuit reset.

- [ ] **Step 3: Implement UI**

Render quality/latency charts and configuration differences; clearly distinguish deterministic test runs from Ollama runs.

- [ ] **Step 4: Add Playwright Ops flow**

Login as analyst/operator, view health, compare two runs, inspect audit, simulate model failure, verify recovery.

- [ ] **Step 5: Enforce G3**

Required: local LLM works, MLflow holds both project evals, metrics scrape, security tests pass, and degraded mode is truthful.

- [ ] **Step 6: Commit**

~~~powershell
git add -A
git commit -m "feat(ops): deliver private LLM operations control plane"
~~~

---

### Task 29: Complete Docker Compose deployment

**Files:**

- Create: backend\Dockerfile
- Create: frontend\Dockerfile
- Create: frontend\nginx.conf
- Complete: compose.yaml
- Create: scripts\dev.ps1
- Create: scripts\stop.ps1
- Create: scripts\verify.ps1

- [ ] **Step 1: Build minimal images**

Use multi-stage builds, non-root runtime users, health checks, pinned Python/Node bases, and no source-data/model copies inside images.

- [ ] **Step 2: Define services**

postgres, redis, api, worker, web, n8n, mlflow, prometheus, grafana. Ollama remains on the host GPU and is reached through host.docker.internal.

- [ ] **Step 3: Add dependency health ordering**

API waits for PostgreSQL/Redis migrations; worker waits for the same; web waits only for its own static build.

- [ ] **Step 4: Build and start**

~~~powershell
Set-Location -LiteralPath 'D:\Vichara-GenAI-Portfolio'
docker compose build
docker compose up -d
docker compose ps
~~~

Expected: all containerized services healthy.

- [ ] **Step 5: Run verification script**

Verify health, login, seed deal summary, cached AltSignal sources, MLflow, Prometheus targets, Grafana provisioning, n8n workflow presence, and web routes.

- [ ] **Step 6: Restart test**

Stop compose normally, start again, and verify persisted data/evaluation runs remain.

- [ ] **Step 7: Commit**

~~~powershell
git add -A
git commit -m "ops: package the suite with Docker Compose"
~~~

---

### Task 30: Add Kubernetes/private-GPU reference deployment

**Files:**

- Create: infra\k8s\namespace.yaml
- Create: infra\k8s\configmap.yaml
- Create: infra\k8s\secret.example.yaml
- Create: infra\k8s\api.yaml
- Create: infra\k8s\worker.yaml
- Create: infra\k8s\model-gateway-gpu.yaml
- Create: infra\k8s\postgres.yaml
- Create: infra\k8s\redis.yaml
- Create: infra\k8s\web.yaml
- Create: infra\k8s\hpa.yaml
- Create: infra\k8s\network-policy.yaml
- Create: docs\architecture\private-cloud-deployment.md

- [ ] **Step 1: Write manifests**

Include probes, requests/limits, persistent volumes, one GPU request using nvidia.com/gpu: 1, non-root security context, config/secret separation, and network policy.

- [ ] **Step 2: Document provider mapping**

Explain how the same GPU pod maps to CoreWeave, AWS, Azure, GCP, and on-prem Kubernetes without claiming an actual deployment.

- [ ] **Step 3: Validate locally**

Install kubectl with winget if absent, then:

~~~powershell
kubectl apply --dry-run=client --validate=false -f 'D:\Vichara-GenAI-Portfolio\infra\k8s'
~~~

Expected: all resources accepted by client-side parsing.

- [ ] **Step 4: Scan manifests for accidental credentials**

Expected: only placeholders in secret.example.yaml.

- [ ] **Step 5: Commit**

~~~powershell
git add -A
git commit -m "ops: add private GPU Kubernetes reference"
~~~

---

### Task 31: Add load, failure, and offline tests

**Files:**

- Create: infra\locust\locustfile.py
- Create: backend\tests\e2e\test_offline_demo.py
- Create: docs\demo\load-test.md
- Generate: .data\reports\locust\

- [ ] **Step 1: Write Locust scenarios**

Mix health, deal summary, comparisons, AltSignal dashboard, cached research brief, and limited chat. Keep model concurrency at one and queue excess work.

- [ ] **Step 2: Run baseline load**

Use a laptop-safe user count. Record p50/p95/p99 latency, error rate, throughput, CPU/RAM/GPU, and model queue time.

- [ ] **Step 3: Run failure scenarios**

Temporarily disable each external source through adapter configuration, stop Ollama, and restart the worker. Verify typed degraded states, retries, audit, and no corrupted jobs.

- [ ] **Step 4: Run offline demo**

Disable external network. The UI must load cached seed data, deterministic analytics, recorded source links, model/eval reports, and a clearly labeled inability to perform new live ingestion.

- [ ] **Step 5: Commit**

~~~powershell
git add -A
git commit -m "test: add load failure and offline evidence"
~~~

---

### Task 32: Add continuous integration

**Files:**

- Create: .github\workflows\ci.yml
- Create: .github\dependabot.yml
- Modify: scripts\verify.ps1

- [ ] **Step 1: Configure fixture-only CI**

Jobs: backend lint/type/unit/contract, frontend lint/test/build, Playwright fixture mode, Docker build, secret scan, and manifest syntax check. Never call public APIs or require Ollama in CI.

- [ ] **Step 2: Pin resolved dependencies**

Commit uv.lock and package-lock.json. Pin Docker image digests after the successful local build where practical.

- [ ] **Step 3: Run the exact CI commands locally**

Expected: all exit zero from a clean checkout state.

- [ ] **Step 4: Review workflow permissions**

Use read-only contents permission; no deployment token or package publish permission.

- [ ] **Step 5: Commit**

~~~powershell
git add -A
git commit -m "ci: verify backend frontend containers and manifests"
~~~

---

### Task 33: Write portfolio documentation and demo scripts

**Files:**

- Create: docs\api-audit.md
- Create: docs\architecture\system.md
- Create: docs\architecture\bondlens.md
- Create: docs\architecture\altsignal.md
- Create: docs\architecture\privateai-ops.md
- Create: docs\demo\README.md
- Create: docs\demo\bondlens.md
- Create: docs\demo\altsignal.md
- Create: docs\demo\privateai-ops.md
- Create: docs\cv\project-bullets.md
- Create: each project README section in root README.md

- [ ] **Step 1: Document reproducible setup**

Include exact Windows/WSL prerequisites, model size/time expectation, D-drive paths, start/stop/verify commands, ports, demo credentials creation, and troubleshooting.

- [ ] **Step 2: Document data access**

For every source: official docs, endpoint used, no-auth evidence, limits, cache policy, provenance fields, and license/usage caveats. Explicitly document FRED and GDELT exclusions.

- [ ] **Step 3: Add Mermaid architecture diagrams**

Show process boundaries, ingestion flow, agent verification, evaluation loop, deployment, and failure paths.

- [ ] **Step 4: Write three deterministic five-minute demos**

Each script states starting state, clicks/commands, expected visible result, likely failure, and recovery.

- [ ] **Step 5: Draft honest CV bullets**

Use built/architected/implemented/validated language. Include measured data volume, test/eval metrics, and laptop deployment only after verified. Do not claim team leadership, years of GenAI experience, cloud production, or investment alpha.

- [ ] **Step 6: Commit**

~~~powershell
git add -A
git commit -m "docs: package architecture demos and CV evidence"
~~~

---

### Task 34: Run the final G4 release gate

**Files:**

- Generate: docs\demo\final-verification-2026-08-30.md
- Generate: docs\demo\screenshots\
- Modify only if failures require fixes: relevant code/tests/docs

- [ ] **Step 1: Verify Git and secret state**

~~~powershell
Set-Location -LiteralPath 'D:\Vichara-GenAI-Portfolio'
git status --short
git log --oneline --decorate -15
git grep -n -I -E '(api[_-]?key|secret|password|token)[[:space:]]*=' -- ':!*.example*' ':!package-lock.json' ':!uv.lock'
~~~

Expected: clean working tree and no committed credentials.

- [ ] **Step 2: Start from stopped services**

Run scripts\dev.ps1, wait through bounded readiness checks, then scripts\verify.ps1.

- [ ] **Step 3: Run all automated tests**

~~~powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/d/Vichara-GenAI-Portfolio/backend && uv run ruff check . && uv run mypy src && uv run pytest -m 'not live' --cov=src --cov-report=term-missing"
Set-Location -LiteralPath 'D:\Vichara-GenAI-Portfolio\frontend'
npm run lint
npm run test -- --run
npm run build
npx playwright test
~~~

Expected: all pass. Set a pragmatic coverage floor around critical modules, not superficial 100% line coverage.

- [ ] **Step 4: Run live-source audit**

One low-volume request per mandatory source. Record timestamp/status/content type and verify no authorization header or secret configuration.

- [ ] **Step 5: Run three user-facing demos**

Capture screenshots for BondLens, AltSignal, and Ops. Verify citations open, numbers match tools, charts label units, and model limitations are visible.

**User checkpoint:** perform the supplied visual checklist and report anything confusing or visually broken.

- [ ] **Step 6: Record measured resume evidence**

Fill CV bullets only with actual counts: parsed properties/periods/documents/chunks, source connectors, golden-test results, model metrics, p95 latency, test counts, and deployment components.

- [ ] **Step 7: Create the local release commit**

~~~powershell
git add -A
git commit -m "release: complete Vichara GenAI portfolio MVP"
git tag -a v0.1.0 -m "Portfolio-grade local MVP"
~~~

- [ ] **Step 8: Stop before external publication**

Show the user the local result. Creating a GitHub repository, pushing code, deploying a public demo, or sending the CV requires a separate explicit instruction.

---

## Definition of done

The plan is complete only when:

1. D:\Vichara-GenAI-Portfolio starts through documented commands.
2. BondLens uses real SEC CMBS data and answers with deterministic numbers plus citations.
3. AltSignal ingests all five verified sources, runs n8n, trains/evaluates PyTorch, and creates cited briefs.
4. PrivateAI Ops serves the local LLM, records MLflow evaluations, exposes metrics, enforces local auth/rate limits, and survives tested failures.
5. Unit, contract, integration, frontend, and Playwright tests pass.
6. Docker Compose restarts without data loss.
7. Kubernetes reference manifests validate locally without claiming real cloud deployment.
8. API audit, architecture, demos, limitations, and measured CV bullets are documented.
9. No external API credential or paid resource is required.
10. The user has visually accepted the three demos.
