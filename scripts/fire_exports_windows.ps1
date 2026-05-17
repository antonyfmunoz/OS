# fire_exports_windows.ps1 — Run browser exports from Windows workstation
#
# Prerequisites:
#   - Python 3.12+ installed
#   - pip install playwright pyotp python-dotenv aiohttp
#   - playwright install chromium
#   - This repo cloned/synced to Windows
#
# Usage (from repo root):
#   .\scripts\fire_exports_windows.ps1 -Service claude
#   .\scripts\fire_exports_windows.ps1 -Service chatgpt
#   .\scripts\fire_exports_windows.ps1 -Service instagram
#   .\scripts\fire_exports_windows.ps1 -Service all
#
# Environment:
#   BROWSER_HEADLESS       — "false" for interactive (default from bridge)
#   PLAYWRIGHT_USER_DATA_DIR — persistent profile dir per service
#   EOS_EXPORT_MFA_CALLBACK_URL — bridge URL for MFA response delivery

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("claude", "chatgpt", "instagram", "all")]
    [string]$Service
)

$ErrorActionPreference = "Stop"
$script:exitCode = 0
$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

# Non-headless on Windows for MFA visibility
if (-not $env:BROWSER_HEADLESS) {
    $env:BROWSER_HEADLESS = "false"
}

# Persistent profiles — survive across runs so MFA only happens once
if (-not $env:PLAYWRIGHT_USER_DATA_DIR) {
    $env:PLAYWRIGHT_USER_DATA_DIR = Join-Path $env:USERPROFILE ".playwright-profiles"
}

if ($Service -eq "all") {
    $services = @("claude", "chatgpt", "instagram")
} else {
    $services = @($Service)
}

foreach ($svc in $services) {
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "  Firing export: $svc" -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan

    # Ensure per-service profile dir exists
    $profileDir = Join-Path $env:PLAYWRIGHT_USER_DATA_DIR $svc
    if (-not (Test-Path $profileDir)) {
        New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
    }
    $env:PLAYWRIGHT_USER_DATA_DIR_SERVICE = $profileDir

    python "$RepoRoot\scripts\fire_export.py" $svc

    if ($LASTEXITCODE -ne 0) {
        Write-Host "`n[ERROR] $svc export failed with exit code $LASTEXITCODE." -ForegroundColor Red
        $script:exitCode = 1
    } else {
        Write-Host "`n[OK] $svc export complete." -ForegroundColor Green
    }
}

Write-Host "`nAll exports attempted." -ForegroundColor Yellow
exit $script:exitCode
