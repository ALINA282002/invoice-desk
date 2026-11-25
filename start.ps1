# Starts Invoice Desk on http://localhost:8765
# First run creates a virtual environment and installs dependencies (~2 minutes).
# Optional: $env:ANTHROPIC_API_KEY = "sk-ant-..."  before running, to use Claude for field extraction.

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Creating virtual environment..."
    python -m venv .venv
    & .venv\Scripts\python.exe -m pip install --upgrade pip
    & .venv\Scripts\pip.exe install -r requirements.txt
}

$port = 8765
Write-Host ""
Write-Host "Invoice Desk -> http://localhost:$port   (Ctrl+C to stop)"
if ($env:ANTHROPIC_API_KEY) { Write-Host "Extraction: Claude" } else { Write-Host "Extraction: on-device parser (set ANTHROPIC_API_KEY to use Claude)" }
Write-Host "Test invoices and master data: $PSScriptRoot\test-pack  (see TEST-GUIDE.md)"
Start-Job -ScriptBlock { Start-Sleep -Seconds 4; Start-Process "http://localhost:8765" } | Out-Null
& .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port $port
