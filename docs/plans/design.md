# BondLens design

## 0. Scope decision: loan-level surveillance

BondLens is a standalone CMBS surveillance project. The selected SEC ABS-EE demo
deal does not contain a reliable month-to-month property deterioration signal:
property-level `mostRecent*` financial fields are sparse and generally repeat the
same reporting window. Loan balances and payment status do vary across reporting
periods, so the acceptance workflow ranks loan-level changes and treats property
financials as point-in-time profiles.

This distinction is enforced throughout the domain model and analytics. Issuance
fields (`*Securitization*`) are never presented as current observations, and a
request for unsupported property deterioration is refused rather than inferred.

## 1. System shape

The React application calls a FastAPI service. SEC ingestion, PostgreSQL, FAISS,
Ollama, and MLflow are adapters behind application ports. A deterministic model
provider and fixture adapters make the default test suite network-free.

Long-running ingestion runs through a Redis-backed worker. PostgreSQL stores
normalized surveillance data, FAISS stores retrieval vectors, and the model gateway
turns deterministic tool output into cited analyst language.

## 2. Locked constraints

1. Every authoritative number is computed by deterministic Python, with units,
   period boundaries, formula version, quality flags, and source references.
2. Every factual or numeric claim in an answer must resolve to tool evidence or a
   source citation.
3. Retrieved filing content is untrusted evidence and cannot issue instructions.
4. The serving workflow is loan-level surveillance plus point-in-time property
   profiles; it does not manufacture unsupported property trends.
5. Tests use deterministic adapters by default and do not require an LLM, network,
   database, or GPU unless explicitly marked as integration or live tests.

## 3. Agent workflow

The LangGraph workflow classifies the question, invokes allowlisted analytical or
retrieval tools, assembles evidence, drafts an answer, verifies citations and numeric
claims, attempts one repair when allowed, and otherwise refuses the answer. State and
tool results remain inspectable for evaluation.

## 4. Follow-ups

Durable multi-process chat checkpoints and production identity/access controls are
outside this portfolio release. The public README lists the runnable scope and honest
limitations.
