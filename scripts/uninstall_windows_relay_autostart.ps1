<#
.SYNOPSIS
    Uninstall the Windows Workstation Relay autostart scheduled task.

.DESCRIPTION
    Removes the scheduled task and autostart marker file.
    Phase 96.8AP.

.PARAMETER RepoPath
    Path to the OS repo. Default: tries common locations.

.PARAMETER TaskName
    Name of the scheduled task. Default: EOS-WorkstationRelay.
#>

param(
    [string]$RepoPath = "",
    [string]$TaskName = "EOS-WorkstationRelay"
)

$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Find repo
# ---------------------------------------------------------------------------

function Find-RepoPath {
    $candidates = @(
        $RepoPath,
        "$HOME\OS",
        "$HOME\Documents\OS",
        "C:\OS",
        "$HOME\repos\OS"
    )
    foreach ($p in $candidates) {
        if ($p -and (Test-Path "$p\scripts\start_windows_relay_node.ps1")) {
            return $p
        }
    }
    return $null
}

$repo = Find-RepoPath

# ---------------------------------------------------------------------------
# Remove task
# ---------------------------------------------------------------------------

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($task) {
    if ($task.State -eq "Running") {
        Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        Write-Host "[uninstall] Stopped running task"
    }
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "[uninstall] Task '$TaskName' removed" -ForegroundColor Green
} else {
    Write-Host "[uninstall] Task '$TaskName' not found — nothing to remove" -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# Remove marker
# ---------------------------------------------------------------------------

if ($repo) {
    $markerPath = Join-Path $repo "data\runtime\workstation_relay\autostart_marker.json"
    if (Test-Path $markerPath) {
        Remove-Item $markerPath -Force
        Write-Host "[uninstall] Marker removed: $markerPath"
    }
}

Write-Host "[uninstall] Autostart uninstalled" -ForegroundColor Green
