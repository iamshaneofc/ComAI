# Run FastAPI + Celery locally (no Docker). Requires PostgreSQL + Redis already running.
# Usage (from repo root, PowerShell):
#   .\scripts\run_local.ps1
#
# Starts API and worker as background jobs in this session. Logs: Receive-Job -Keep -Id <id>
# Stop: Get-Job | Stop-Job; Get-Job | Remove-Job

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

python scripts/check_local_services.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Running migrations..."
python -m alembic upgrade head

Write-Host "Starting uvicorn (job: api)..."
$api = Start-Job -Name api -ScriptBlock {
    Set-Location $using:PWD
    python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 2>&1
}

Start-Sleep -Seconds 2

Write-Host "Starting Celery worker (job: worker)..."
$wk = Start-Job -Name worker -ScriptBlock {
    Set-Location $using:PWD
    python -m celery -A app.core.celery_app worker --loglevel=info 2>&1
}

Write-Host ""
Write-Host "Jobs started. API: http://127.0.0.1:8000/docs"
Write-Host "Stream API logs:  Receive-Job -Id $($api.Id) -Keep"
Write-Host "Stream worker logs: Receive-Job -Id $($wk.Id) -Keep"
Write-Host "Stop jobs: Get-Job | Stop-Job; Get-Job | Remove-Job"
