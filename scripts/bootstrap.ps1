<#
.SYNOPSIS
    One-time setup: backend Python deps, frontend Node deps, Playwright
    browsers, Ollama + the local model.

.DESCRIPTION
    Idempotent - safe to re-run. Installs into backend\.venv (uv-managed,
    native Windows Python 3.12) and frontend\node_modules. Does not start
    Docker services (see scripts\dev.ps1).
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

Write-Host '== Ollama: model storage on D: ==' -ForegroundColor Cyan
$modelRoot = Join-Path $repoRoot '.models\ollama'
New-Item -ItemType Directory -Force -Path $modelRoot | Out-Null
$env:OLLAMA_MODELS = $modelRoot
[Environment]::SetEnvironmentVariable('OLLAMA_MODELS', $modelRoot, 'User')

$installedOllama = Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'
$ollamaExe = if (Test-Path -LiteralPath $installedOllama) {
    $installedOllama
} else {
    $onPath = Get-Command ollama -ErrorAction SilentlyContinue
    if ($onPath) {
        $onPath.Source
    } else {
        Write-Host '== Ollama: installing (winget) ==' -ForegroundColor Cyan
        winget install --id Ollama.Ollama --exact --accept-source-agreements --accept-package-agreements
        $installedOllama
    }
}

# Measured 2026-08-28: the winget-installed app auto-launches its own
# tray-managed server on install, using the *default* per-user model
# path - before this script's SetEnvironmentVariable call can affect an
# already-running process. `ollama pull` is a thin client that just talks
# to whatever is already bound to :11434, so a pull silently landed 4.6 GB
# in the default per-user Ollama directory instead of D:. Always kill any existing
# server first so the one this script starts is guaranteed to be reading
# OLLAMA_MODELS=D:\...\.models\ollama.
Get-Process -Name 'ollama*' -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2
Write-Host '== Ollama: starting server (D: model storage) ==' -ForegroundColor Cyan
Start-Process -FilePath $ollamaExe -ArgumentList 'serve' -WindowStyle Hidden
Start-Sleep -Seconds 3

$modelPresent = (& $ollamaExe list) -match 'llama3\.1:8b'
if (-not $modelPresent) {
    Write-Host '== Ollama: pulling llama3.1:8b (~4.9 GB) ==' -ForegroundColor Cyan
    & $ollamaExe pull llama3.1:8b
}

# Guard against the same race on a from-scratch machine: if a stray
# default-path install slipped in anyway, surface it instead of silently
# eating 4.6+ GB on C:.
$strayDefault = Join-Path $env:USERPROFILE '.ollama\models\blobs'
if (Test-Path -LiteralPath $strayDefault) {
    $strayBytes = (Get-ChildItem -LiteralPath $strayDefault -File -ErrorAction SilentlyContinue |
        Measure-Object -Property Length -Sum).Sum
    if ($strayBytes -gt 0) {
        Write-Host ("== WARNING: {0:N2} GB of Ollama blobs found on C: at {1} - move them into {2} and delete the C: copy ==" -f ($strayBytes / 1GB), $strayDefault, $modelRoot) -ForegroundColor Yellow
    }
}

Set-Location -LiteralPath $repoRoot
Write-Host '== Bootstrap complete ==' -ForegroundColor Green
Write-Host 'Next: .\scripts\dev.ps1 to start the stack (once Task 29 lands the compose services).'
