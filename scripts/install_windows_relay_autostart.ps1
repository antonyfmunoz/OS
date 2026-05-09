<#
.SYNOPSIS
    Install the Windows Workstation Relay as an autostart scheduled task.

.DESCRIPTION
    Registers the relay node as a Windows Task Scheduler task that:
    - Runs at user login
    - Restarts on failure (up to 3 times, 30s interval)
    - Runs only when user is logged on (interactive desktop required)
    - Writes logs to data/runtime/workstation_relay/logs/
    - Creates a marker file for VPS-side autostart detection

    Run elevated (Administrator) or as the logged-in user.
    Phase 96.8AP.

.PARAMETER RepoPath
    Path to the OS repo on Windows. Default: tries common locations.

.PARAMETER TaskName
    Name for the scheduled task. Default: EOS-WorkstationRelay.

.PARAMETER DelayAfterLogin
    Delay after login before starting relay. Default: 30s.
#>

param(
    [string]$RepoPath = "",
    [string]$TaskName = "EOS-WorkstationRelay",
    [int]$DelayAfterLogin = 30
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
if (-not $repo) {
    Write-Host "[autostart] ERROR: Could not find OS repo. Pass -RepoPath" -ForegroundColor Red
    exit 1
}

Write-Host "[autostart] Repo: $repo"

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

$relayScript = Join-Path $repo "scripts\start_windows_relay_node.ps1"
$logDir = Join-Path $repo "data\runtime\workstation_relay\logs"
$markerPath = Join-Path $repo "data\runtime\workstation_relay\autostart_marker.json"

if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

# ---------------------------------------------------------------------------
# Check existing task
# ---------------------------------------------------------------------------

$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "[autostart] Task '$TaskName' already exists. Removing..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "[autostart] Removed existing task"
}

# ---------------------------------------------------------------------------
# Build scheduled task
# ---------------------------------------------------------------------------

$logFile = Join-Path $logDir "relay_$(Get-Date -Format 'yyyy-MM-dd').log"

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$relayScript`" -RepoPath `"$repo`" *>> `"$logFile`"" `
    -WorkingDirectory $repo

$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

$delaySpan = New-TimeSpan -Seconds $DelayAfterLogin
$trigger.Delay = "PT${DelayAfterLogin}S"

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Seconds 30) `
    -ExecutionTimeLimit (New-TimeSpan -Days 365) `
    -StartWhenAvailable `
    -DontStopOnIdleEnd

$principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Limited

# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "EOS Workstation Relay Node — autostart at login. Phase 96.8AP." `
    -Force | Out-Null

Write-Host "[autostart] Task '$TaskName' registered" -ForegroundColor Green

# ---------------------------------------------------------------------------
# Write marker
# ---------------------------------------------------------------------------

$marker = @{
    task_name         = $TaskName
    repo_path         = $repo
    relay_script      = $relayScript
    log_dir           = $logDir
    delay_seconds     = $DelayAfterLogin
    restart_count     = 3
    restart_interval  = 30
    installed_by      = $env:USERNAME
    installed_at      = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
    machine_name      = $env:COMPUTERNAME
}
$marker | ConvertTo-Json -Depth 3 | Out-File -FilePath $markerPath -Encoding UTF8
Write-Host "[autostart] Marker written: $markerPath"

# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------

$task = Get-ScheduledTask -TaskName $TaskName
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " Autostart Installation Complete" -ForegroundColor Cyan
Write-Host " Phase 96.8AP" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  task:       $TaskName"
Write-Host "  state:      $($task.State)"
Write-Host "  trigger:    AtLogOn ($env:USERNAME)"
Write-Host "  delay:      ${DelayAfterLogin}s after login"
Write-Host "  restart:    3 retries, 30s interval"
Write-Host "  log dir:    $logDir"
Write-Host "  marker:     $markerPath"
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "[autostart] Done. Relay will start automatically at next login." -ForegroundColor Green
Write-Host "[autostart] To test now: Start-ScheduledTask -TaskName '$TaskName'"
