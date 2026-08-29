"""Task 17: the evaluator is pure over an injectable `invoke` callable
(same shape as CompiledStateGraph.invoke), so these tests never touch
Ollama, LangGraph, or real SEC data - only fixed AgentState-shaped dicts,
the same shape build_agent_graph's nodes actually merge and return (see
agent.py ToolEvidence/verify_node/_collect_citations).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from vichara_portfolio.bondlens.agent import REFUSAL_PREAMBLE, ToolEvidence
from vichara_portfolio.ops.evaluation import (
    GoldenCase,
    evaluate_golden_set,
    evaluate_question,
    summary_to_dict,
)
from vichara_portfolio.shared.provenance import SourceRef


def _source(url: str = "https://www.sec.gov/x/exh_102.xml") -> SourceRef:
    return SourceRef(
        source_name="sec_edgar", source_url=url, retrieved_at=datetime(2026, 8, 28, tzinfo=UTC)
    )


def _case(
    *,
    case_id: str = "case-1",
    expected_tools=("rank_loans_by_status_change",),
    expected_facts=("loan 30",),
) -> GoldenCase:
    return GoldenCase(
        id=case_id,
        question="Which loans changed status?",
        expected_tools=tuple(expected_tools),
        expected_facts=tuple(expected_facts),
    )


def _clean_result(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "planned_tools": ["rank_loans_by_status_change"],
        "tool_evidence": [
            ToolEvidence(
                tool_name="rank_loans_by_status_change",
                rendered="loan 30: 0 -> B",
                sources=(_source(),),
            )
        ],
        "citations": [_source()],
        "verification_errors": [],
        "final_answer": "Loan 30 moved from status 0 to B.",
    }
    base.update(overrides)
    return base


def test_tool_routing_correct_when_actual_matches_expected() -> None:
    result = evaluate_question(invoke=lambda _q: _clean_result(), case=_case())
    assert result.tool_routing_correct is True
    assert result.actual_tools == ("rank_loans_by_status_change",)


def test_tool_routing_incorrect_when_wrong_tool_called() -> None:
    result = evaluate_question(
        invoke=lambda _q: _clean_result(
            tool_evidence=[
                ToolEvidence(
                    tool_name="get_deal_summary", rendered="62 loans", sources=(_source(),)
                )
            ]
        ),
        case=_case(),
    )
    assert result.tool_routing_correct is False
    assert result.actual_tools == ("get_deal_summary",)


def test_numeric_exact_true_when_no_verification_errors() -> None:
    result = evaluate_question(invoke=lambda _q: _clean_result(), case=_case())
    assert result.numeric_exact is True
    assert result.unsupported_claim_count == 0


def test_numeric_exact_false_when_final_answer_has_a_number_absent_from_evidence() -> None:
    # Deliberately re-checked against final_answer + evidence, not against
    # state["verification_errors"] - see find_unsupported_numbers' docstring
    # (agent.py) for the real bug this evaluator behavior fixes: that field
    # reflects a rejected draft, not necessarily the delivered final_answer.
    result = evaluate_question(
        invoke=lambda _q: _clean_result(
            final_answer="Loan 30 moved from status 0 to B, a $999 change."
        ),
        case=_case(),
    )
    assert result.numeric_exact is False
    assert result.unsupported_claim_count == 1


def test_numeric_exact_true_for_a_refusal_fallback_despite_stale_verification_errors() -> None:
    """The refusal-fallback path (finalize_node echoing evidence verbatim
    after a repair failure) must never be penalized using the rejected
    draft's stale verification_errors - it can only ever contain numbers
    already in evidence, by construction."""
    result = evaluate_question(
        invoke=lambda _q: _clean_result(
            final_answer="loan 30: 0 -> B",  # verbatim evidence echo
            verification_errors=["numbers not present in evidence: 999"],  # stale, from the draft
        ),
        case=_case(),
    )
    assert result.numeric_exact is True
    assert result.unsupported_claim_count == 0


def test_citation_coverage_and_source_validity_for_a_real_sec_url() -> None:
    result = evaluate_question(invoke=lambda _q: _clean_result(), case=_case())
    assert result.citation_count == 1
    assert result.all_citations_valid is True
    assert result.invalid_citation_urls == ()


def test_source_validity_flags_a_non_sec_url() -> None:
    result = evaluate_question(
        invoke=lambda _q: _clean_result(citations=[_source("https://example.com/not-sec")]),
        case=_case(),
    )
    assert result.all_citations_valid is False
    assert result.invalid_citation_urls == ("https://example.com/not-sec",)


def test_missing_expected_fact_is_recorded() -> None:
    result = evaluate_question(
        invoke=lambda _q: _clean_result(final_answer="Nothing relevant here."),
        case=_case(expected_facts=("loan 30", "cummins station")),
    )
    assert result.facts_covered is False
    assert result.missing_facts == ("loan 30", "cummins station")


def test_facts_covered_is_case_insensitive() -> None:
    result = evaluate_question(
        invoke=lambda _q: _clean_result(final_answer="LOAN 30 changed status."),
        case=_case(expected_facts=("loan 30",)),
    )
    assert result.facts_covered is True
    assert result.missing_facts == ()


def test_evidence_gathered_with_zero_citations_fails_the_question() -> None:
    """The one G1-relevant failure mode: evidence exists but nothing cites it."""
    result = evaluate_question(
        invoke=lambda _q: _clean_result(citations=[]),
        case=_case(),
    )
    assert result.passed is False


def test_a_fully_clean_question_passes() -> None:
    result = evaluate_question(invoke=lambda _q: _clean_result(), case=_case())
    assert result.passed is True


def test_latency_is_measured_and_non_negative() -> None:
    result = evaluate_question(invoke=lambda _q: _clean_result(), case=_case())
    assert result.latency_seconds >= 0.0


def test_used_fallback_false_for_a_genuine_narrative_answer() -> None:
    result = evaluate_question(invoke=lambda _q: _clean_result(), case=_case())
    assert result.used_fallback is False


def test_used_fallback_true_for_the_refusal_answer() -> None:
    """A question can pass G1's mechanical checks (grounded, cited) while the
    model itself produced nothing usable - finalize_node's refusal is
    grounded by construction, not because the model succeeded. `passed` and
    `used_fallback` measure different things and a report must show both,
    not let a PASS imply the model actually narrated an answer (the exact
    gap that made an earlier report read as "5/5 passed" when live testing
    2026-08-29 showed 0 of those 5 were genuine narrative answers, 3 runs in
    a row)."""
    result = evaluate_question(
        invoke=lambda _q: _clean_result(
            final_answer=f"{REFUSAL_PREAMBLE}\n[rank_loans_by_status_change] loan 30: 0 -> B"
        ),
        case=_case(),
    )
    assert result.passed is True
    assert result.used_fallback is True


def test_evaluate_golden_set_aggregates_across_questions() -> None:
    cases = [_case(case_id="a"), _case(case_id="b", expected_tools=("get_deal_summary",))]

    # First case's tools match ("rank_loans_by_status_change"), second
    # case expects a different tool than the fixed clean result returns.
    summary = evaluate_golden_set(
        invoke=lambda _q: _clean_result(),
        cases=cases,
        model_name="deterministic",
        data_snapshot="2026-07-13",
    )

    assert len(summary.questions) == 2
    assert summary.tool_routing_accuracy == 0.5  # case "a" matches, case "b" does not
    assert summary.numeric_exactness_rate == 1.0
    assert summary.source_url_validity_rate == 1.0
    assert summary.citation_coverage_rate == 1.0
    assert summary.total_unsupported_claims == 0


def test_fallback_rate_reflects_how_many_answers_were_genuine_narrative() -> None:
    cases = [_case(case_id="a"), _case(case_id="b")]
    refusal = f"{REFUSAL_PREAMBLE}\n[rank_loans_by_status_change] loan 30: 0 -> B"
    # evaluate_question is called once per case, in list order - case "a"
    # gets a genuine narrative, case "b" gets the refusal.
    answers = iter([_clean_result(), _clean_result(final_answer=refusal)])

    summary = evaluate_golden_set(
        invoke=lambda _q: next(answers),
        cases=cases,
        model_name="ollama/llama3.1:8b",
        data_snapshot="2026-07-13",
    )

    assert summary.fallback_rate == 0.5
    assert [q.used_fallback for q in summary.questions] == [False, True]


def test_g1_passes_when_every_metric_is_clean() -> None:
    cases = [_case()]
    summary = evaluate_golden_set(
        invoke=lambda _q: _clean_result(),
        cases=cases,
        model_name="deterministic",
        data_snapshot="2026-07-13",
    )
    assert summary.g1_passed is True
    assert summary.g1_failures == ()


def test_g1_fails_on_an_invalid_citation_url() -> None:
    cases = [_case()]
    summary = evaluate_golden_set(
        invoke=lambda _q: _clean_result(citations=[_source("https://not-sec.example/x")]),
        cases=cases,
        model_name="deterministic",
        data_snapshot="2026-07-13",
    )
    assert summary.g1_passed is False
    assert any("source url" in f.lower() for f in summary.g1_failures)


def test_g1_fails_on_unsupported_numbers() -> None:
    cases = [_case()]
    summary = evaluate_golden_set(
        invoke=lambda _q: _clean_result(
            final_answer="Loan 30 moved from status 0 to B, a $999 change."
        ),
        cases=cases,
        model_name="deterministic",
        data_snapshot="2026-07-13",
    )
    assert summary.g1_passed is False
    assert any("numeric" in f.lower() for f in summary.g1_failures)


def test_g1_fails_when_evidence_gathered_but_uncited() -> None:
    cases = [_case()]
    summary = evaluate_golden_set(
        invoke=lambda _q: _clean_result(citations=[]),
        cases=cases,
        model_name="deterministic",
        data_snapshot="2026-07-13",
    )
    assert summary.g1_passed is False
    assert any("citation" in f.lower() for f in summary.g1_failures)


def test_g1_fails_when_a_question_is_missing_expected_facts_even_if_otherwise_clean() -> None:
    """Regression test for a real bug (2026-08-29): every golden question
    failed (missing expected facts against a stub model that just echoes
    a fixed sentence) yet g1_passed still came back True, because the
    G1 gate only checked source validity / numeric exactness / uncited
    evidence and never looked at each question's own `passed` flag."""
    cases = [_case(expected_facts=("loan 30", "cummins station"))]
    summary = evaluate_golden_set(
        invoke=lambda _q: _clean_result(final_answer="Nothing relevant."),
        cases=cases,
        model_name="deterministic",
        data_snapshot="2026-07-13",
    )
    assert summary.questions[0].passed is False
    assert summary.g1_passed is False
    assert any("golden questions failed" in f.lower() for f in summary.g1_failures)


def test_summary_to_dict_round_trips_through_json() -> None:
    cases = [_case()]
    summary = evaluate_golden_set(
        invoke=lambda _q: _clean_result(),
        cases=cases,
        model_name="deterministic",
        data_snapshot="2026-07-13",
    )
    payload = summary_to_dict(summary)
    reparsed = json.loads(json.dumps(payload))
    assert reparsed["model_name"] == "deterministic"
    assert reparsed["g1_passed"] is True
    assert len(reparsed["questions"]) == 1
    assert reparsed["questions"][0]["question_id"] == "case-1"
