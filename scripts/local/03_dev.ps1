# Laminario, step 3: run the API locally with auto-reload.
#
#   .\scripts\local\03_dev.ps1
#   .\scripts\local\03_dev.ps1 -Port 8150

[CmdletBinding()]
param([int]$Port = 8147)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $Root
$venvPy = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) { Write-Error "No .venv yet. Run:  .\scripts\local\01_init.ps1" }

# Refuse a port someone else already holds: a gate that reuses a listening port tests another product.
$busy = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
if ($busy) { Write-Error "Port $Port is already in use (process $($busy[0].OwningProcess)). Pass -Port." }

Write-Host "Laminario API on http://127.0.0.1:$Port  (health: /api/health, docs: /api/docs)" -ForegroundColor Cyan
& $venvPy -m uvicorn app.main:app --reload --host 127.0.0.1 --port $Port
