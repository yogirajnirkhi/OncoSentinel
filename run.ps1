# OncoSentinel v2.0 — Windows PowerShell Startup Script
$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$V1Dir = Join-Path $RootDir "v1"
$env:PYTHONPATH = $V1Dir

if (-not $env:ONCO_DATABASE_URL) {
    $DbPath = ($V1Dir -replace '\\', '/') + "/oncosentinel.db"
    $env:ONCO_DATABASE_URL = "sqlite+aiosqlite:///$DbPath"
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  OncoSentinel v2.0 — Unified Clinical AI & HMS Platform" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Portal & HMS Workspace : http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "  Interactive API Docs   : http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan

Push-Location $V1Dir
try {
    python run.py
} finally {
    Pop-Location
}
