# fire_exports_windows.ps1 — Run browser exports from Windows workstation
#
# Prerequisites:
#   - Python 3.12+ installed
#   - pip install playwright pyotp python-dotenv
#   - playwright install chromium
#   - This repo cloned/synced to Windows
#
# Usage (from repo root):
#   .\scripts\fire_exports_windows.ps1 claude
#   .\scripts\fire_exports_windows.ps1 chatgpt
#   .\scripts\fire_exports_windows.ps1 instagram
#   .\scripts\fire_exports_windows.ps1 all

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("claude", "chatgpt", "instagram", "all")]
    [string]$Service
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

# Use non-headless on Windows so you can see and interact with MFA
$env:BROWSER_HEADLESS = "false"

if ($Service -eq "all") {
    $services = @("claude", "chatgpt", "instagram")
} else {
    $services = @($Service)
}

foreach ($svc in $services) {
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "  Firing export: $svc" -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan

    python "$RepoRoot\scripts\fire_export.py" $svc

    if ($LASTEXITCODE -ne 0) {
        Write-Host "`n[ERROR] $svc export failed." -ForegroundColor Red
    } else {
        Write-Host "`n[OK] $svc export complete." -ForegroundColor Green
    }
}

Write-Host "`nAll exports attempted. Check /logs/exports/ for screenshots and MFA observations." -ForegroundColor Yellow
