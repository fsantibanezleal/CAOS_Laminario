# Laminario, step 1: one-stop setup from a fresh clone.
#
# Idempotent: every step checks "already done?" first. -Force rebuilds the virtual environment.
# ASCII-ONLY STRING LITERALS (PowerShell 5.1 reads a .ps1 as CP-1252 without a BOM).
#
#   .\scripts\local\01_init.ps1
#   .\scripts\local\01_init.ps1 -Force

[CmdletBinding()]
param([switch]$Force)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $Root

# A native program's stderr becomes an ErrorRecord in PowerShell 5.1 and would abort the script under
# "Stop"; native calls are judged by their exit code instead.
function Invoke-Native {
    param([Parameter(Mandatory)][string]$Exe, [string[]]$Arguments = @(), [string]$What = "")
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $Exe @Arguments 2>&1 | ForEach-Object { Write-Host $_ }
        $code = $LASTEXITCODE
    } finally { $ErrorActionPreference = $prev }
    if ($code -ne 0) {
        $label = if ($What) { $What } else { "$Exe $($Arguments -join ' ')" }
        throw "$label failed with exit code $code"
    }
}

Write-Host ""
Write-Host "Laminario init" -ForegroundColor Cyan
Write-Host ""

# --- 1. prerequisites -------------------------------------------------------------------------------
if (-not (Get-Command "py" -ErrorAction SilentlyContinue)) {
    Write-Error "The py launcher is missing. Run:  .\scripts\local\00_install-prereqs.ps1"
}
$pyv = (& py -3.12 --version 2>&1 | Out-String).Trim()
if ($pyv -notmatch "3\.12") { Write-Error "Python 3.12 is required. Run:  .\scripts\local\00_install-prereqs.ps1" }
Write-Host "  [1/3] $pyv" -ForegroundColor Green

# --- 2. the virtual environment ---------------------------------------------------------------------
if ($Force -and (Test-Path ".venv")) { Remove-Item -Recurse -Force ".venv" }
if (-not (Test-Path ".venv")) { Invoke-Native "py" @("-3.12", "-m", "venv", ".venv") -What "creating .venv" }
$venvPy = Join-Path $Root ".venv\Scripts\python.exe"
Invoke-Native $venvPy @("-m", "pip", "install", "--upgrade", "pip", "-q") -What "upgrading pip"
Invoke-Native $venvPy @("-m", "pip", "install", "-q", "-r", "requirements-dev.txt") -What "installing requirements-dev.txt"
Write-Host "  [2/3] .venv ready" -ForegroundColor Green

# --- 3. the local .env ------------------------------------------------------------------------------
# Secrets never live in this repository. When LAMINARIO_ENV_SOURCE names an env file (the owner keeps
# the working one in a private vault), it is copied; otherwise the documented defaults are used.
if (-not (Test-Path ".env")) {
    $source = $env:LAMINARIO_ENV_SOURCE
    if ($source -and (Test-Path $source)) {
        Copy-Item $source ".env"
        Write-Host "  [3/3] .env copied from LAMINARIO_ENV_SOURCE" -ForegroundColor Green
    } else {
        Copy-Item ".env.example" ".env"
        Write-Host "  [3/3] .env created from .env.example (local defaults)" -ForegroundColor Green
    }
} else {
    Write-Host "  [3/3] .env already present, left as it is" -ForegroundColor Green
}

Write-Host ""
Write-Host "  Ready. Tests:  .\.venv\Scripts\python.exe -m pytest" -ForegroundColor Green
Write-Host "  Next:         .\scripts\local\03_dev.ps1" -ForegroundColor Green
Write-Host ""
