<#
.SYNOPSIS
    One-time setup: backend Python deps, frontend Node deps, Playwright browsers.

.DESCRIPTION
    Idempotent - safe to re-run. Installs into backend\.venv (uv-managed, native
    Windows Python 3.12) and frontend\node_modules. Does not install Ollama or pull
    a model (see Task 12) and does not start Docker services (see scripts\dev.ps1).
#>

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot

Write-Host '== Backend: syncing Python dependencies (uv) ==' -ForegroundColor Cyan
Set-Location -LiteralPath (Join-Path $repoRoot 'backend')
uv sync

Write-Host '== Frontend: installing Node dependencies (npm) ==' -ForegroundColor Cyan
Set-Location -LiteralPath (Join-Path $repoRoot 'frontend')
npm install

Write-Host '== Frontend: installing Playwright Chromium ==' -ForegroundColor Cyan
npx playwright install chromium

Set-Location -LiteralPath $repoRoot
Write-Host '== Bootstrap complete ==' -ForegroundColor Green
Write-Host 'Next: .\scripts\dev.ps1 to start the stack (once Task 29 lands the compose services).'
