# Laminario, step 0: system-level prerequisites.
#
# Checks what the project needs on this machine and reports what is missing. Checking is the default;
# installing is opt-in with -Install (winget), so a working installation is never replaced.
#
# ASCII-ONLY STRING LITERALS: PowerShell 5.1 reads a .ps1 as CP-1252 without a UTF-8 BOM, and some
# UTF-8 punctuation would silently end a string.
#
#   .\scripts\local\00_install-prereqs.ps1
#   .\scripts\local\00_install-prereqs.ps1 -Install

[CmdletBinding()]
param([switch]$Install)

$ErrorActionPreference = "Stop"

# CI pins Python 3.12; the frontend declares Node 22 to 24.
$PythonWanted = "3.12"
$NodeMin = [version]"22.0"
$NodeMaxExclusive = [version]"25.0"

function Test-Cmd($name) { return [bool](Get-Command $name -ErrorAction SilentlyContinue) }

# Not named $args: that is an automatic variable and would never bind.
function Get-Ver($exe, [string[]]$verArgs) {
    try {
        $raw = & $exe @verArgs 2>&1 | Out-String
        $m = [regex]::Match($raw, "(\d+)\.(\d+)")
        if ($m.Success) { return [version]("{0}.{1}" -f $m.Groups[1].Value, $m.Groups[2].Value) }
    } catch { }
    return $null
}

function Install-Winget($id, $label) {
    if (-not $Install) { return }
    if (-not (Test-Cmd "winget")) { Write-Error "winget is not available; install $label by hand." }
    Write-Host "  installing $label with winget ($id)" -ForegroundColor Yellow
    & winget install --id $id -e --accept-source-agreements --accept-package-agreements
    if ($LASTEXITCODE -ne 0) { Write-Error "winget could not install $label (exit $LASTEXITCODE)" }
}

$missing = $false
Write-Host ""
Write-Host "Laminario prerequisites" -ForegroundColor Cyan
Write-Host ""

# Python 3.12 through the Windows launcher (a bare `python` can be the Store alias stub).
$py = $null
if (Test-Cmd "py") { $py = Get-Ver "py" @("-$PythonWanted", "--version") }
if ($py -and $py -eq [version]$PythonWanted) {
    Write-Host ("  Python {0} (py -{1})" -f $py, $PythonWanted) -ForegroundColor Green
} else {
    Write-Host "  Python $PythonWanted not found through the py launcher" -ForegroundColor Red
    $missing = $true
    Install-Winget "Python.Python.3.12" "Python 3.12"
}

$node = $null
if (Test-Cmd "node") { $node = Get-Ver "node" @("--version") }
if ($node -and $node -ge $NodeMin -and $node -lt $NodeMaxExclusive) {
    Write-Host ("  Node {0}" -f $node) -ForegroundColor Green
} else {
    Write-Host "  Node 22 to 24 not found (found: $node)" -ForegroundColor Red
    $missing = $true
    Install-Winget "OpenJS.NodeJS.LTS" "Node.js LTS"
}

if (Test-Cmd "git") { Write-Host ("  git {0}" -f (Get-Ver "git" @("--version"))) -ForegroundColor Green }
else { Write-Host "  git not found" -ForegroundColor Red; $missing = $true; Install-Winget "Git.Git" "Git" }

# libvips with OpenSlide (the imaging engine, from U2 on): the official Windows build "vips-dev-w64-all",
# unzipped anywhere, its bin folder named by LAMINARIO_VIPS_BIN in the environment or in .env.
$vipsBin = $env:LAMINARIO_VIPS_BIN
$envFile = Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) ".env"
if (-not $vipsBin -and (Test-Path $envFile)) {
    $line = Get-Content $envFile | Where-Object { $_ -match '^LAMINARIO_VIPS_BIN=(.+)$' } | Select-Object -First 1
    if ($line) { $vipsBin = ($line -split '=', 2)[1].Trim() }
}
if ($vipsBin -and (Test-Path (Join-Path $vipsBin "libvips-42.dll")) -and (Test-Path (Join-Path $vipsBin "libopenslide-1.dll"))) {
    Write-Host "  libvips with OpenSlide ($vipsBin)" -ForegroundColor Green
} else {
    Write-Host "  libvips with OpenSlide not found (LAMINARIO_VIPS_BIN: '$vipsBin')" -ForegroundColor Red
    Write-Host "    Download vips-dev-w64-all-<version>.zip from https://github.com/libvips/build-win64-mxe/releases,"
    Write-Host "    unzip it, and set LAMINARIO_VIPS_BIN in .env to its bin folder."
    $missing = $true
}

# Docker runs the IIIF tile server locally (from U3 on).
if (Test-Cmd "docker") { Write-Host ("  Docker {0}" -f (Get-Ver "docker" @("--version"))) -ForegroundColor Green }
else { Write-Host "  Docker not found (needed for the local tile server)" -ForegroundColor Yellow }

Write-Host ""
if ($missing -and -not $Install) {
    Write-Host "  Missing prerequisites. Re-run with -Install to install them with winget:" -ForegroundColor Yellow
    Write-Host "    .\scripts\local\00_install-prereqs.ps1 -Install"
    exit 1
}
Write-Host "  Ready. Next:  .\scripts\local\01_init.ps1" -ForegroundColor Green
Write-Host ""
