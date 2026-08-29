# BondLens Golden Questions

Five questions BondLens's G1 acceptance gate is scored against. All five are
pinned to the real May and July 2026 ABS-EE filings for **Benchmark
2026-B42 Mortgage Trust** (CIK 0002110410) - the same bytes committed at
`backend/tests/fixtures/sec/abs_ee_2026-{05,07}.xml`, not synthetic data.
Source of truth for the question list is `backend/tests/golden/bondlens_questions.yaml`;
this page explains *why* each one is here.

The evaluator that runs these is `backend/src/vichara_portfolio/ops/evaluation.py`
(`uv run python backend/scripts/run_evaluations.py`), which writes
`.data/reports/bondlens-evaluation.json` and exits non-zero if the G1 gate
fails. See design.md section 0 for why the demo is scoped to loan-level
surveillance rather than property-level deterioration.

## 1. flagship-status-and-balance

> Which loans changed payment status between May and July, and whose
> balances diverged from schedule?

The headline question: it exercises two deterministic tools in one turn
(`rank_loans_by_status_change` + `rank_loans_by_balance_drift`) and must
surface loan 30 (Cummins Station), the one loan that went delinquent in
this window.

**What live testing found here (2026-08-29):** this is also the question
most likely to break the model. Combining both tools' evidence produces a
long, numerically repetitive prompt, and `llama3.1:8b` at Q4_K_M
quantization reproducibly degenerated into a repetitive greedy-decoding
loop three times in a row when drafting an answer to it (e.g. `"B 7, D 6,
C 4, A 5, R 3, A 2, 0 I will 1,"` repeated ~12 times). The mechanical
numeric verifier alone didn't always catch this - the gibberish's digits
happened to already be small loan numbers present in evidence - so a
second, independent check for pathological repetition was added to
`verify_node` (`agent.py`). When the model degenerates, the graph now
reliably falls back to `finalize_node`'s verbatim evidence echo instead of
delivering nonsense dressed as an answer.

## 2. cured-loans

> Which loans were cured (delinquent then current) between May and July?

Tests that "cured" is recognized as a real signal, not just delinquency -
loans 16 (PWC Pennant) and 39 (325 East 14th Street) both moved back to
current status in this window.

## 3. deal-summary

> Give me a deal summary for Benchmark 2026-B42 as of July.

The simplest question in the set: one deterministic tool
(`get_deal_summary`), exact loan/property counts (62 loans, 123
properties). A model that can't get this right can't be trusted on
anything harder.

## 4. loan-30-history

> What is the payment history of loan 30 across the periods you have?

Single-loan time series via `get_loan_history` - checks the agent can
narrate a change over time for one asset, not just a pool-wide ranking.

## 5. property-noi-honest-negative - the flagship *negative* case

> Which properties deteriorated most in net operating income between May
> and July?

**The most important question in the set.** Benchmark 2026-B42 is a
February-2026 vintage deal - too young and too sparsely serviced for
genuine property-level financial deterioration to exist yet (measured
2026-08-28: of 123 properties, only 3 showed any `mostRecent` NOI change
at all, and all three were null-to-first-reported-value, not real
deterioration - see design.md section 0). The correct answer is that
**no property genuinely deteriorated in this window**, and the three
apparent changes are a reporting artifact, not a finding. An answer that
invents a property-deterioration ranking to sound responsive fails G1
outright, regardless of how plausible it reads. This question exists
specifically to catch a model performing confidence instead of reporting
what the data actually supports.

## G1 gate

Enforced by `evaluate_golden_set()`/`enforce`-equivalent logic in
`evaluation.py`, required for BondLens's first-release sign-off:

- **100% source URL validity** - every citation resolves to a real
  `sec.gov` URL.
- **100% deterministic numeric exactness** - every number in the delivered
  final answer (not a rejected draft) traces back to tool evidence.
- **Zero uncited final factual paragraphs** - if evidence was gathered,
  the answer cites it.
- **Every golden question passes** - correct tool routing and all expected
  facts present in the final answer, including the negative case above.
- **A successful Playwright flow** - `frontend/tests/e2e/bondlens.spec.ts`.

Per Task 17's own instruction, this set is not tuned to pass after the
fact - see the flagship question's writeup above for a case where a real
model weakness was fixed at the verifier level (a general robustness
improvement) rather than by loosening what the golden set requires.
