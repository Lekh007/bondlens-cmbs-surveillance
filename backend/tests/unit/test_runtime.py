from pathlib import Path

from vichara_portfolio.runtime import RuntimeProbe, Status, evaluate_readiness


def _probe(**overrides: object) -> RuntimeProbe:
    base = dict(
        python_version=(3, 12, 13),
        python_executable="D:/Vichara-GenAI-Portfolio/backend/.venv/Scripts/python.exe",
        drive_d_writable=True,
        gpu_name="RTX 4060 Laptop GPU",
        docker_reachable=True,
        ollama_reachable=True,
        ollama_models=("llama3.1:8b",),
        cache_path=Path("D:/Vichara-GenAI-Portfolio/.cache/huggingface"),
    )
    base.update(overrides)
    return RuntimeProbe(**base)  # type: ignore[arg-type]


def test_all_capabilities_ready_when_everything_present() -> None:
    report = evaluate_readiness(_probe())

    statuses = {c.name: c.status for c in report.capabilities}
    assert statuses["python"] == Status.READY
    assert statuses["drive_d"] == Status.READY
    assert statuses["gpu"] == Status.READY
    assert statuses["docker"] == Status.READY
    assert statuses["ollama"] == Status.READY
    assert report.all_required_ready is True


def test_missing_ollama_does_not_block_required_readiness() -> None:
    report = evaluate_readiness(_probe(ollama_reachable=False, ollama_models=()))

    statuses = {c.name: c.status for c in report.capabilities}
    assert statuses["ollama"] == Status.MISSING
    assert statuses["docker"] == Status.READY
    assert report.all_required_ready is True, (
        "Ollama is optional for fixture-backed unit tests and must not gate readiness"
    )


def test_missing_docker_is_reported_separately_from_ollama() -> None:
    report = evaluate_readiness(_probe(docker_reachable=False, ollama_reachable=False))

    statuses = {c.name: c.status for c in report.capabilities}
    assert statuses["docker"] == Status.MISSING
    assert statuses["ollama"] == Status.MISSING
    # Docker and Ollama are independent signals - one being down must not change the other.
    assert statuses["docker"] != statuses["python"]


def test_missing_gpu_is_degraded_not_missing() -> None:
    report = evaluate_readiness(_probe(gpu_name=None))

    statuses = {c.name: c.status for c in report.capabilities}
    assert statuses["gpu"] == Status.DEGRADED
    assert report.all_required_ready is True


def test_unwritable_drive_d_blocks_required_readiness() -> None:
    report = evaluate_readiness(_probe(drive_d_writable=False))

    statuses = {c.name: c.status for c in report.capabilities}
    assert statuses["drive_d"] == Status.MISSING
    assert report.all_required_ready is False


def test_python_version_below_3_12_is_missing() -> None:
    report = evaluate_readiness(_probe(python_version=(3, 11, 15)))

    statuses = {c.name: c.status for c in report.capabilities}
    assert statuses["python"] == Status.MISSING
    assert report.all_required_ready is False


def test_report_includes_cache_path_detail() -> None:
    report = evaluate_readiness(_probe())

    cache = next(c for c in report.capabilities if c.name == "cache_path")
    assert "huggingface" in cache.detail
