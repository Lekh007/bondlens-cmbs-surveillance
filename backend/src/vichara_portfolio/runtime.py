"""Runtime capability reporting.

Split into a pure evaluator (`evaluate_readiness`, unit-tested with fixture
probes, no I/O) and an impure prober (`probe_runtime`, does the actual
subprocess/network/filesystem calls). Only `python`, `drive_d`, and
`cache_path` gate `all_required_ready` - those are what fixture-backed unit
tests need. Docker, GPU, and Ollama are reported but never block it, so a
missing model server does not fail the test suite.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

MIN_PYTHON_VERSION = (3, 12)


class Status(str, Enum):
    READY = "ready"
    DEGRADED = "degraded"
    MISSING = "missing"


@dataclass(frozen=True)
class CapabilityStatus:
    name: str
    status: Status
    detail: str
    required: bool = False


@dataclass(frozen=True)
class RuntimeProbe:
    """Raw, already-collected facts about the machine. No I/O happens here."""

    python_version: tuple[int, int, int]
    python_executable: str
    drive_d_writable: bool
    gpu_name: str | None
    docker_reachable: bool
    ollama_reachable: bool
    ollama_models: tuple[str, ...]
    cache_path: Path


@dataclass(frozen=True)
class ReadinessReport:
    capabilities: tuple[CapabilityStatus, ...] = field(default_factory=tuple)

    @property
    def all_required_ready(self) -> bool:
        return all(c.status == Status.READY for c in self.capabilities if c.required)

    def summary(self) -> str:
        lines = [f"{c.name:12s} {c.status.value:9s} {c.detail}" for c in self.capabilities]
        return "\n".join(lines)


def evaluate_readiness(probe: RuntimeProbe) -> ReadinessReport:
    capabilities = (
        _evaluate_python(probe),
        _evaluate_drive_d(probe),
        _evaluate_cache_path(probe),
        _evaluate_gpu(probe),
        _evaluate_docker(probe),
        _evaluate_ollama(probe),
    )
    return ReadinessReport(capabilities=capabilities)


def _evaluate_python(probe: RuntimeProbe) -> CapabilityStatus:
    major, minor, _ = probe.python_version
    if (major, minor) >= MIN_PYTHON_VERSION:
        detail = f"{major}.{minor}.{probe.python_version[2]} at {probe.python_executable}"
        return CapabilityStatus("python", Status.READY, detail, required=True)
    detail = f"{major}.{minor}.{probe.python_version[2]} < {'.'.join(map(str, MIN_PYTHON_VERSION))} required"
    return CapabilityStatus("python", Status.MISSING, detail, required=True)


def _evaluate_drive_d(probe: RuntimeProbe) -> CapabilityStatus:
    if probe.drive_d_writable:
        return CapabilityStatus("drive_d", Status.READY, "D:\\ is writable", required=True)
    return CapabilityStatus("drive_d", Status.MISSING, "D:\\ is not writable", required=True)


def _evaluate_cache_path(probe: RuntimeProbe) -> CapabilityStatus:
    return CapabilityStatus(
        "cache_path", Status.READY, str(probe.cache_path), required=True
    )


def _evaluate_gpu(probe: RuntimeProbe) -> CapabilityStatus:
    if probe.gpu_name:
        return CapabilityStatus("gpu", Status.READY, probe.gpu_name, required=False)
    return CapabilityStatus(
        "gpu", Status.DEGRADED, "no GPU detected; Ollama will run on CPU", required=False
    )


def _evaluate_docker(probe: RuntimeProbe) -> CapabilityStatus:
    if probe.docker_reachable:
        return CapabilityStatus("docker", Status.READY, "docker info succeeded", required=False)
    return CapabilityStatus("docker", Status.MISSING, "docker info failed or timed out", required=False)


def _evaluate_ollama(probe: RuntimeProbe) -> CapabilityStatus:
    if probe.ollama_reachable:
        models = ", ".join(probe.ollama_models) or "no models pulled"
        return CapabilityStatus("ollama", Status.READY, models, required=False)
    return CapabilityStatus(
        "ollama", Status.MISSING, "not reachable on 127.0.0.1:11434", required=False
    )


def probe_runtime(repo_root: Path) -> RuntimeProbe:
    """Impure: actually inspects the machine. Kept thin; logic lives in evaluate_readiness."""
    import sys

    return RuntimeProbe(
        python_version=sys.version_info[:3],
        python_executable=sys.executable,
        drive_d_writable=_check_drive_writable(Path("D:/")),
        gpu_name=_detect_gpu_name(),
        docker_reachable=_check_docker(),
        ollama_reachable=_check_ollama()[0],
        ollama_models=_check_ollama()[1],
        cache_path=repo_root / ".cache" / "huggingface",
    )


def _check_drive_writable(drive: Path) -> bool:
    try:
        with tempfile.NamedTemporaryFile(dir=drive, delete=True):
            pass
        return True
    except OSError:
        return False


def _detect_gpu_name() -> str | None:
    nvidia_smi = shutil.which("nvidia-smi")
    if not nvidia_smi:
        return None
    try:
        result = subprocess.run(
            [nvidia_smi, "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        name = result.stdout.strip().splitlines()[0] if result.stdout.strip() else None
        return name
    except (subprocess.SubprocessError, OSError, IndexError):
        return None


def _check_docker() -> bool:
    docker = shutil.which("docker")
    if not docker:
        return False
    try:
        result = subprocess.run(
            [docker, "info"], capture_output=True, timeout=10
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, OSError):
        return False


def _check_ollama() -> tuple[bool, tuple[str, ...]]:
    try:
        import httpx

        response = httpx.get("http://127.0.0.1:11434/api/tags", timeout=2.0)
        response.raise_for_status()
        models = tuple(m["name"] for m in response.json().get("models", []))
        return True, models
    except Exception:
        return False, ()


if __name__ == "__main__":
    root = Path(os.environ.get("VICHARA_REPO_ROOT", Path(__file__).resolve().parents[3]))
    report = evaluate_readiness(probe_runtime(root))
    print(report.summary())
    print()
    print("all_required_ready:", report.all_required_ready)
