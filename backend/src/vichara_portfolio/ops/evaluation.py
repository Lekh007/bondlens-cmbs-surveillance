"""BondLens golden-question evaluator (Task 17).

Deliberately decoupled from LangGraph: `evaluate_question`/`evaluate_golden_set`
take an `invoke: Callable[[str], AgentState]` - the same shape as
`CompiledStateGraph.invoke` partially applied to a question - rather than a
graph object directly. That keeps every metric here unit-testable against
fixed AgentState-shaped dicts (see agent.py ToolEvidence/verify_node/
_collect_citations) without touching Ollama, LangGraph, or real SEC data.

Every check reuses signal the agent graph already computes deterministically
(verify_node's unsupported-number detection, _collect_citations) rather than
re-deriving it - this evaluator aggregates and gates, it does not re-judge.

"Optional local-LLM judging" (Task 17 Step 2) is a real but separate
extension point: pass `judge` to score a question's answer quality with a
local model. It never affects `passed`/`g1_passed` - G1 is deterministic
checks only, per design.md's core rule that arithmetic (and here,
correctness gating) is never delegated to an LLM.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from vichara_portfolio.bondlens.agent import (
    AgentState,
    find_unsupported_numbers,
    is_refusal_fallback,
)
from vichara_portfolio.shared.provenance import SourceRef

_VALID_CITATION_URL_PREFIXES = ("https://www.sec.gov/", "https://data.sec.gov/")


@dataclass(frozen=True)
class GoldenCase:
    id: str
    question: str
    expected_tools: tuple[str, ...]
    expected_facts: tuple[str, ...]


@dataclass(frozen=True)
class QuestionResult:
    question_id: str
    question: str
    expected_tools: tuple[str, ...]
    actual_tools: tuple[str, ...]
    tool_routing_correct: bool
    expected_facts: tuple[str, ...]
    facts_covered: bool
    missing_facts: tuple[str, ...]
    unsupported_claim_count: int
    numeric_exact: bool
    citation_count: int
    citation_urls: tuple[str, ...]
    all_citations_valid: bool
    invalid_citation_urls: tuple[str, ...]
    latency_seconds: float
    final_answer: str
    used_fallback: bool
    judge_score: float | None
    passed: bool
    failure_reasons: tuple[str, ...]


@dataclass(frozen=True)
class EvaluationSummary:
    model_name: str
    prompt_version: str
    index_checksum: str | None
    data_snapshot: str
    generated_at: str
    questions: tuple[QuestionResult, ...]
    tool_routing_accuracy: float
    numeric_exactness_rate: float
    citation_coverage_rate: float
    source_url_validity_rate: float
    retrieval_recall_at_k: float | None
    retrieval_recall_note: str
    total_unsupported_claims: int
    average_latency_seconds: float
    fallback_rate: float
    g1_passed: bool
    g1_failures: tuple[str, ...] = field(default_factory=tuple)


def _is_valid_citation_url(url: str) -> bool:
    return url.startswith(_VALID_CITATION_URL_PREFIXES)


def evaluate_question(
    *,
    invoke: Callable[[str], AgentState],
    case: GoldenCase,
    judge: Callable[[str, str], float] | None = None,
) -> QuestionResult:
    started = time.perf_counter()
    result = invoke(case.question)
    latency = time.perf_counter() - started

    tool_evidence = result.get("tool_evidence") or []
    actual_tools = tuple(dict.fromkeys(evidence.tool_name for evidence in tool_evidence))
    tool_routing_correct = set(actual_tools) == set(case.expected_tools)

    final_answer = str(result.get("final_answer", ""))
    answer_lower = final_answer.lower()
    missing_facts = tuple(fact for fact in case.expected_facts if fact.lower() not in answer_lower)
    facts_covered = len(missing_facts) == 0

    # Re-checked against the actual delivered final_answer, not
    # state["verification_errors"] - that field reflects whatever draft
    # verify_node last rejected, which after a repair failure is not the
    # same text as finalize_node's evidence-echo fallback. See
    # find_unsupported_numbers' docstring for the bug this fixes.
    unsupported_numbers = find_unsupported_numbers(final_answer, result)
    unsupported_claim_count = len(unsupported_numbers)
    numeric_exact = unsupported_claim_count == 0

    citations: list[SourceRef] = result.get("citations") or []
    citation_urls = tuple(c.source_url for c in citations)
    invalid_citation_urls = tuple(url for url in citation_urls if not _is_valid_citation_url(url))
    all_citations_valid = len(invalid_citation_urls) == 0

    evidence_gathered = bool(tool_evidence) or bool(result.get("retrieved_chunks"))
    has_citations = len(citations) > 0
    used_fallback = is_refusal_fallback(final_answer)

    judge_score = judge(case.question, final_answer) if judge is not None else None

    failure_reasons: list[str] = []
    if not tool_routing_correct:
        failure_reasons.append(f"tool routing: expected {case.expected_tools}, got {actual_tools}")
    if not facts_covered:
        failure_reasons.append(f"missing expected facts: {missing_facts}")
    if not numeric_exact:
        failure_reasons.append(f"unsupported numeric claims: {unsupported_numbers}")
    if not all_citations_valid:
        failure_reasons.append(f"invalid citation URLs: {invalid_citation_urls}")
    if evidence_gathered and not has_citations:
        failure_reasons.append("evidence gathered but final answer is uncited")

    return QuestionResult(
        question_id=case.id,
        question=case.question,
        expected_tools=case.expected_tools,
        actual_tools=actual_tools,
        tool_routing_correct=tool_routing_correct,
        expected_facts=case.expected_facts,
        facts_covered=facts_covered,
        missing_facts=missing_facts,
        unsupported_claim_count=unsupported_claim_count,
        numeric_exact=numeric_exact,
        citation_count=len(citations),
        citation_urls=citation_urls,
        all_citations_valid=all_citations_valid,
        invalid_citation_urls=invalid_citation_urls,
        latency_seconds=latency,
        final_answer=final_answer,
        used_fallback=used_fallback,
        judge_score=judge_score,
        passed=len(failure_reasons) == 0,
        failure_reasons=tuple(failure_reasons),
    )


def evaluate_golden_set(
    *,
    invoke: Callable[[str], AgentState],
    cases: list[GoldenCase],
    model_name: str,
    data_snapshot: str,
    prompt_version: str = "bondlens-agent-v1",
    index_checksum: str | None = None,
    judge: Callable[[str, str], float] | None = None,
) -> EvaluationSummary:
    questions = tuple(evaluate_question(invoke=invoke, case=case, judge=judge) for case in cases)

    n = len(questions) or 1  # guard div-by-zero; an empty golden set has 0% everywhere below
    tool_routing_accuracy = sum(q.tool_routing_correct for q in questions) / n
    numeric_exactness_rate = sum(q.numeric_exact for q in questions) / n
    citation_coverage_rate = sum(q.citation_count > 0 for q in questions) / n
    total_unsupported_claims = sum(q.unsupported_claim_count for q in questions)
    average_latency_seconds = sum(q.latency_seconds for q in questions) / n
    # Fraction of answers that are finalize_node's raw-evidence refusal, not
    # a genuine model narrative. A question can be `passed` while its answer
    # used the fallback - this metric is what makes that distinction
    # impossible to miss in a saved report (see is_refusal_fallback).
    fallback_rate = sum(q.used_fallback for q in questions) / n

    all_citation_urls = [url for q in questions for url in q.citation_urls]
    source_url_validity_rate = (
        sum(_is_valid_citation_url(u) for u in all_citation_urls) / len(all_citation_urls)
        if all_citation_urls
        else 1.0  # vacuously valid: no citations were issued at all
    )

    g1_failures: list[str] = []
    if source_url_validity_rate < 1.0:
        g1_failures.append(f"source URL validity is {source_url_validity_rate:.0%}, must be 100%")
    if numeric_exactness_rate < 1.0:
        g1_failures.append(
            f"deterministic numeric exactness is {numeric_exactness_rate:.0%}, must be 100%"
        )
    uncited_with_evidence = [
        q.question_id for q in questions if "uncited" in " ".join(q.failure_reasons)
    ]
    if uncited_with_evidence:
        g1_failures.append(
            f"final answer has zero citations despite evidence gathered: {uncited_with_evidence}"
        )
    failed_questions = [q.question_id for q in questions if not q.passed]
    if failed_questions:
        # Catches everything the three checks above don't, chiefly missing
        # expected facts and tool-routing mismatches - G1 requires the
        # whole golden set to pass, not just its three narrowest signals.
        g1_failures.append(f"golden questions failed: {failed_questions}")

    return EvaluationSummary(
        model_name=model_name,
        prompt_version=prompt_version,
        index_checksum=index_checksum,
        data_snapshot=data_snapshot,
        generated_at=datetime.now(UTC).isoformat(),
        questions=questions,
        tool_routing_accuracy=tool_routing_accuracy,
        numeric_exactness_rate=numeric_exactness_rate,
        citation_coverage_rate=citation_coverage_rate,
        source_url_validity_rate=source_url_validity_rate,
        retrieval_recall_at_k=None,
        retrieval_recall_note=(
            "Not applicable to this golden set: every question is answered by "
            "deterministic loan/property tools, not narrative-filing retrieval. "
            "BondLens's ingested corpus is ABS-EE asset data, not 8-K/10-D "
            "narrative text, so no golden question exercises the retrieval path."
        ),
        total_unsupported_claims=total_unsupported_claims,
        average_latency_seconds=average_latency_seconds,
        fallback_rate=fallback_rate,
        g1_passed=len(g1_failures) == 0,
        g1_failures=tuple(g1_failures),
    )


def summary_to_dict(summary: EvaluationSummary) -> dict[str, object]:
    return {
        "model_name": summary.model_name,
        "prompt_version": summary.prompt_version,
        "index_checksum": summary.index_checksum,
        "data_snapshot": summary.data_snapshot,
        "generated_at": summary.generated_at,
        "tool_routing_accuracy": summary.tool_routing_accuracy,
        "numeric_exactness_rate": summary.numeric_exactness_rate,
        "citation_coverage_rate": summary.citation_coverage_rate,
        "source_url_validity_rate": summary.source_url_validity_rate,
        "retrieval_recall_at_k": summary.retrieval_recall_at_k,
        "retrieval_recall_note": summary.retrieval_recall_note,
        "total_unsupported_claims": summary.total_unsupported_claims,
        "average_latency_seconds": summary.average_latency_seconds,
        "fallback_rate": summary.fallback_rate,
        "g1_passed": summary.g1_passed,
        "g1_failures": list(summary.g1_failures),
        "questions": [
            {
                "question_id": q.question_id,
                "question": q.question,
                "expected_tools": list(q.expected_tools),
                "actual_tools": list(q.actual_tools),
                "tool_routing_correct": q.tool_routing_correct,
                "expected_facts": list(q.expected_facts),
                "facts_covered": q.facts_covered,
                "missing_facts": list(q.missing_facts),
                "unsupported_claim_count": q.unsupported_claim_count,
                "numeric_exact": q.numeric_exact,
                "citation_count": q.citation_count,
                "citation_urls": list(q.citation_urls),
                "all_citations_valid": q.all_citations_valid,
                "invalid_citation_urls": list(q.invalid_citation_urls),
                "latency_seconds": q.latency_seconds,
                "final_answer": q.final_answer,
                "used_fallback": q.used_fallback,
                "judge_score": q.judge_score,
                "passed": q.passed,
                "failure_reasons": list(q.failure_reasons),
            }
            for q in summary.questions
        ],
    }
