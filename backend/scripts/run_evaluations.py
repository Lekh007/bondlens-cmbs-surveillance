#!/usr/bin/env python
"""Task 17: run the full BondLens golden set and enforce the G1 gate.

Runs against the real pinned May/July 2026 Benchmark 2026-B42 ABS-EE
fixtures (backend/tests/fixtures/sec) - the same real downloaded filing
bytes the unit tests are pinned against, not synthetic data - and the
real model provider (Ollama by default; set MODEL_PROVIDER=deterministic
to run without a live model, e.g. in CI).

Writes .data/reports/bondlens-evaluation.json and exits non-zero if the
G1 gate fails, so this can run as a CI/release check.

Usage:
    uv run python scripts/run_evaluations.py
    $env:MODEL_PROVIDER = 'deterministic'; uv run python scripts/run_evaluations.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC, datetime

import yaml

from vichara_portfolio.bondlens.adapters.abs_ee import parse_asset_data
from vichara_portfolio.bondlens.agent import AgentState, build_agent_graph
from vichara_portfolio.bondlens.domain import Deal, Loan
from vichara_portfolio.model_gateway.deterministic import DeterministicProvider
from vichara_portfolio.model_gateway.ollama import OllamaProvider
from vichara_portfolio.model_gateway.ports import ModelProvider
from vichara_portfolio.ops.evaluation import GoldenCase, evaluate_golden_set, summary_to_dict
from vichara_portfolio.settings import REPO_ROOT, Settings
from vichara_portfolio.shared.provenance import SourceRef

FIXTURES_DIR = REPO_ROOT / "backend" / "tests" / "fixtures" / "sec"
GOLDEN_PATH = REPO_ROOT / "backend" / "tests" / "golden" / "bondlens_questions.yaml"
REPORT_PATH = REPO_ROOT / ".data" / "reports" / "bondlens-evaluation.json"
DEAL = Deal(cik="0002110410", name="Benchmark 2026-B42 Mortgage Trust")
MAY_FIXTURE = "abs_ee_2026-05.xml"
JULY_FIXTURE = "abs_ee_2026-07.xml"


def _source(filename: str) -> SourceRef:
    return SourceRef(
        source_name="sec_edgar",
        source_url=f"https://www.sec.gov/x/{filename}",
        retrieved_at=datetime(2026, 8, 28, 12, 0, tzinfo=UTC),
    )


def _load_loans(filename: str) -> tuple[Loan, ...]:
    xml = (FIXTURES_DIR / filename).read_bytes()
    return parse_asset_data(xml, source=_source(filename)).loans


def _data_snapshot() -> str:
    """Hash of the exact fixture bytes this run used, so a report can be
    tied back to precisely which data snapshot produced it."""
    digest = hashlib.sha256()
    for filename in (MAY_FIXTURE, JULY_FIXTURE):
        digest.update((FIXTURES_DIR / filename).read_bytes())
    return f"{MAY_FIXTURE}+{JULY_FIXTURE} sha256:{digest.hexdigest()[:16]}"


def _model_provider(settings: Settings) -> ModelProvider:
    if settings.model_provider == "deterministic":
        return DeterministicProvider()
    return OllamaProvider(base_url=settings.ollama_base_url, model=settings.ollama_model)


def _load_golden_cases() -> list[GoldenCase]:
    raw_cases = yaml.safe_load(GOLDEN_PATH.read_text(encoding="utf-8"))
    return [
        GoldenCase(
            id=case["id"],
            question=case["question"],
            expected_tools=tuple(case["expected_tools"]),
            expected_facts=tuple(case["expected_facts"]),
        )
        for case in raw_cases
    ]


def main() -> None:
    settings = Settings()  # type: ignore[call-arg]  # resolved from .env at runtime
    model = _model_provider(settings)

    loans_a = _load_loans(MAY_FIXTURE)
    loans_b = _load_loans(JULY_FIXTURE)
    graph = build_agent_graph(
        model=model,
        deal=DEAL,
        loans_a=loans_a,
        loans_b=loans_b,
        filing_source=_source(JULY_FIXTURE),
    )

    def invoke(question: str) -> AgentState:
        # langgraph's compiled-graph stubs don't propagate the AgentState
        # TypeVar through invoke() (same stub-resolution quirk noted in
        # agent.py's build_agent_graph) - the runtime shape is correct.
        return graph.invoke(  # type: ignore[return-value]
            {"question": question}, config={"recursion_limit": 10}
        )

    cases = _load_golden_cases()
    summary = evaluate_golden_set(
        invoke=invoke,
        cases=cases,
        model_name=f"{model.model_info().provider_name}/{model.model_info().model_name}",
        data_snapshot=_data_snapshot(),
    )

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(summary_to_dict(summary), indent=2), encoding="utf-8")

    print(f"Report written to {REPORT_PATH}")
    print(f"model: {summary.model_name}")
    print(f"tool_routing_accuracy: {summary.tool_routing_accuracy:.0%}")
    print(f"numeric_exactness_rate: {summary.numeric_exactness_rate:.0%}")
    print(f"source_url_validity_rate: {summary.source_url_validity_rate:.0%}")
    print(f"citation_coverage_rate: {summary.citation_coverage_rate:.0%}")
    print(f"total_unsupported_claims: {summary.total_unsupported_claims}")
    print(f"average_latency_seconds: {summary.average_latency_seconds:.2f}")
    print(
        f"retrieval_recall_at_k: {summary.retrieval_recall_at_k} ({summary.retrieval_recall_note})"
    )
    for q in summary.questions:
        status = "PASS" if q.passed else "FAIL"
        print(f"  [{status}] {q.question_id}: {q.failure_reasons or 'ok'}")

    if summary.g1_passed:
        print("G1: PASSED")
    else:
        print("G1: FAILED")
        for reason in summary.g1_failures:
            print(f"  - {reason}")
        sys.exit(1)


if __name__ == "__main__":
    main()
