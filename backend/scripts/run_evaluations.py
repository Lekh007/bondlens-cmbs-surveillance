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

import httpx
import yaml

from vichara_portfolio.bondlens.adapters.abs_ee import parse_asset_data
from vichara_portfolio.bondlens.agent import AgentState, build_agent_graph
from vichara_portfolio.bondlens.domain import Deal, Loan
from vichara_portfolio.model_gateway.deterministic import DeterministicProvider
from vichara_portfolio.model_gateway.ollama import OllamaProvider
from vichara_portfolio.model_gateway.ports import ModelProvider
from vichara_portfolio.ops.evaluation import (
    EvaluationSummary,
    GoldenCase,
    evaluate_golden_set,
    summary_to_dict,
)
from vichara_portfolio.settings import REPO_ROOT, Settings
from vichara_portfolio.shared.provenance import SourceRef

FIXTURES_DIR = REPO_ROOT / "backend" / "tests" / "fixtures" / "sec"
GOLDEN_PATH = REPO_ROOT / "backend" / "tests" / "golden" / "bondlens_questions.yaml"
REPORT_PATH = REPO_ROOT / ".data" / "reports" / "bondlens-evaluation.json"
DEAL = Deal(cik="0002110410", name="Benchmark 2026-B42 Mortgage Trust")

# Real accession numbers for the two fixture filings (backend/tests/fixtures/sec/) -
# not a placeholder. An earlier version of this script built a fake URL
# (f"https://www.sec.gov/x/{filename}") that happened to satisfy
# evaluation.py's cheap prefix check without resolving to anything real -
# confirmed 404 (measured 2026-08-29, live review finding). These are the
# genuine sec.gov URLs for the exact bytes these fixtures contain, verified
# to return HTTP 200 below in `_verify_citations_resolve`.
MAY_FIXTURE = "abs_ee_2026-05.xml"
JULY_FIXTURE = "abs_ee_2026-07.xml"
_REAL_ACCESSION_URL = {
    MAY_FIXTURE: "https://www.sec.gov/Archives/edgar/data/2110410/000188852426010373/exh_102.xml",
    JULY_FIXTURE: "https://www.sec.gov/Archives/edgar/data/2110410/000188852426014162/exh_102.xml",
}
_SEC_USER_AGENT = "vichara-portfolio-eval evaluation-script@example.com"


def _source(filename: str) -> SourceRef:
    return SourceRef(
        source_name="sec_edgar",
        source_url=_REAL_ACCESSION_URL[filename],
        retrieved_at=datetime(2026, 8, 28, 12, 0, tzinfo=UTC),
    )


def _load_loans(filename: str) -> tuple[Loan, ...]:
    xml = (FIXTURES_DIR / filename).read_bytes()
    return parse_asset_data(xml, source=_source(filename)).loans


def _verify_citations_resolve(summary: EvaluationSummary) -> dict[str, int | str]:
    """Live HTTP check that every citation URL in the report actually
    resolves - not just that it starts with the right prefix (that cheap
    check lives in evaluation.py and stays network-free/unit-testable on
    purpose). This is the network-touching half, deliberately kept in the
    live-run script rather than the pure evaluator."""
    urls = sorted({url for q in summary.questions for url in q.citation_urls})
    results: dict[str, int | str] = {}
    with httpx.Client(headers={"User-Agent": _SEC_USER_AGENT}, timeout=15.0) as client:
        for url in urls:
            try:
                response = client.get(url)
                results[url] = response.status_code
            except httpx.HTTPError as exc:
                results[url] = f"error: {exc}"
    return results


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

    citation_resolution = _verify_citations_resolve(summary)
    all_citations_resolved = all(status == 200 for status in citation_resolution.values())

    report = summary_to_dict(summary)
    report["citation_http_resolution"] = citation_resolution
    report["all_citations_resolved"] = all_citations_resolved

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Report written to {REPORT_PATH}")
    print(f"model: {summary.model_name}")
    print(f"tool_routing_accuracy: {summary.tool_routing_accuracy:.0%}")
    print(f"numeric_exactness_rate: {summary.numeric_exactness_rate:.0%}")
    print(f"source_url_validity_rate: {summary.source_url_validity_rate:.0%} (prefix check only)")
    print(f"citation_coverage_rate: {summary.citation_coverage_rate:.0%}")
    print(f"total_unsupported_claims: {summary.total_unsupported_claims}")
    print(f"average_latency_seconds: {summary.average_latency_seconds:.2f}")
    print(
        f"retrieval_recall_at_k: {summary.retrieval_recall_at_k} ({summary.retrieval_recall_note})"
    )
    print()
    print(f"*** fallback_rate: {summary.fallback_rate:.0%} ***")
    print("    (fraction of answers that are the raw-evidence refusal, not a genuine")
    print("     model narrative - a question can PASS while its answer used the")
    print("     fallback; PASSED means the safety net worked, not that the model")
    print("     succeeded. See is_refusal_fallback in agent.py.)")
    print()
    print("citation HTTP resolution (live check, not just a prefix match):")
    for url, status in citation_resolution.items():
        print(f"  [{status}] {url}")
    print()

    for q in summary.questions:
        status = "PASS" if q.passed else "FAIL"
        fallback_tag = " [FALLBACK]" if q.used_fallback else ""
        print(f"  [{status}]{fallback_tag} {q.question_id}: {q.failure_reasons or 'ok'}")

    gate_failed = not summary.g1_passed or not all_citations_resolved
    if not gate_failed:
        print("G1: PASSED")
    else:
        print("G1: FAILED")
        for reason in summary.g1_failures:
            print(f"  - {reason}")
        if not all_citations_resolved:
            failing = {u: s for u, s in citation_resolution.items() if s != 200}
            print(f"  - citation URLs that did not resolve with HTTP 200: {failing}")
        sys.exit(1)


if __name__ == "__main__":
    main()
