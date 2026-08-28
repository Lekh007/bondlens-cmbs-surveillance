<#
.SYNOPSIS
    Print the runtime readiness report: Python, D:\, GPU, Docker, Ollama, cache path.

.DESCRIPTION
    Thin wrapper over vichara_portfolio.runtime. Docker and Ollama are reported
    but never block readiness - only Python/D:\/cache_path do, since those are
    what the fixture-backed unit test suite needs.
#>

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot

Set-Location -LiteralPath (Join-Path $repoRoot 'backend')
$env:VICHARA_REPO_ROOT = $repoRoot
uv run python -m vichara_portfolio.runtime
