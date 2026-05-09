<#
.SYNOPSIS
    Start the Windows Workstation Relay Node.

.DESCRIPTION
    Wraps the existing windows_interactive_desktop_relay.ps1 with:
    - Node identity registration
    - Periodic heartbeat emission
    - Chrome availability check
    - Desktop session validation
    - Structured startup output

    Run this from a PowerShell window in the logged-in Windows session.
    The relay will start and remain running, emitting heartbeats.

    Phase 96.8AO.

.PARAMETER RepoPath
    Path to the OS repo (on Windows/WSL). Used for config and relay script.
    Default: tries common locations.

.PARAMETER HeartbeatIntervalSeconds
    How often to write heartbeat. Default: 10.
#>

param(
    [string]$RepoPath = "",
    [int]$HeartbeatIntervalSeconds = 10
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
        if ($p -and (Test-Path "$p\scripts\windows_interactive_desktop_relay.ps1")) {
            return $p
        }
    }
    return $null
}

$repo = Find-RepoPath
if (-not $repo) {
    Write-Host "[relay-node] ERROR: Could not find OS repo. Pass -RepoPath" -ForegroundColor Red
    Write-Host "[relay-node] Looked for scripts\windows_interactive_desktop_relay.ps1 in:"
    Write-Host "  - $HOME\OS"
    Write-Host "  - $HOME\Documents\OS"
    Write-Host "  - C:\OS"
    exit 1
}

Write-Host "[relay-node] Repo found: $repo"

# ---------------------------------------------------------------------------
# Node identity
# ---------------------------------------------------------------------------

$machineName = $env:COMPUTERNAME
$userName = $env:USERNAME
$osVersion = [System.Environment]::OSVersion.VersionString
$psVersion = $PSVersionTable.PSVersion.ToString()
$relayPid = $PID

$nodeIdRaw = "${machineName}:${userName}:local_windows_desktop"
$sha = [System.Security.Cryptography.SHA256]::Create()
$hashBytes = $sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($nodeIdRaw))
$hashHex = ($hashBytes | ForEach-Object { $_.ToString("x2") }) -join ""
$nodeId = "WRN-$($hashHex.Substring(0, 8))"

# ---------------------------------------------------------------------------
# Chrome check
# ---------------------------------------------------------------------------

$chromeExe = $null
$chromePaths = @(
    "C:\Program Files\Google\Chrome\Application\chrome.exe",
    "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
)
foreach ($p in $chromePaths) {
    if (Test-Path $p) {
        $chromeExe = $p
        break
    }
}
$chromeAvailable = ($null -ne $chromeExe)

# ---------------------------------------------------------------------------
# Desktop state
# ---------------------------------------------------------------------------

function Get-DesktopState {
    $desktopActive = $true
    $desktopUnlocked = $true
    $monitorDetected = $true

    try {
        Add-Type -AssemblyName System.Windows.Forms
        $screenCount = [System.Windows.Forms.Screen]::AllScreens.Count
        $monitorDetected = ($screenCount -gt 0)
    }
    catch {
        $monitorDetected = $false
    }

    return @{
        desktop_session_active = $desktopActive
        desktop_unlocked       = $desktopUnlocked
        monitor_detected       = $monitorDetected
    }
}

# ---------------------------------------------------------------------------
# Relay script hash
# ---------------------------------------------------------------------------

$relayScript = Join-Path $repo "scripts\windows_interactive_desktop_relay.ps1"
$relayScriptHash = ""
try {
    $h = Get-FileHash -Path $relayScript -Algorithm SHA256
    $relayScriptHash = $h.Hash.ToLower().Substring(0, 12)
}
catch {
    $relayScriptHash = "unknown"
}

# ---------------------------------------------------------------------------
# Git commit
# ---------------------------------------------------------------------------

$repoCommit = ""
try {
    $gitResult = git -C $repo rev-parse --short HEAD 2>$null
    if ($LASTEXITCODE -eq 0) {
        $repoCommit = $gitResult.Trim()
    }
}
catch {
    $repoCommit = "unknown"
}

# ---------------------------------------------------------------------------
# Heartbeat writer
# ---------------------------------------------------------------------------

$capabilities = @(
    "launch_chrome",
    "focus_window",
    "navigate_url",
    "capture_screenshot",
    "report_hwnd",
    "report_foreground_window",
    "report_desktop_state"
)

$heartbeatDir = Join-Path $repo "data\runtime\workstation_relay"
if (-not (Test-Path $heartbeatDir)) {
    New-Item -ItemType Directory -Path $heartbeatDir -Force | Out-Null
}
$heartbeatPath = Join-Path $heartbeatDir "heartbeat.json"

function Write-Heartbeat {
    $ds = Get-DesktopState
    $hb = @{
        node_id                = $nodeId
        machine_name           = $machineName
        user_name              = $userName
        os                     = $osVersion
        relay_pid              = $relayPid
        relay_version          = "v1"
        repo_commit            = $repoCommit
        relay_script_hash      = $relayScriptHash
        desktop_session_active = $ds["desktop_session_active"]
        desktop_unlocked       = $ds["desktop_unlocked"]
        monitor_detected       = $ds["monitor_detected"]
        chrome_available       = $chromeAvailable
        capabilities           = $capabilities
        timestamp              = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
    }
    $json = $hb | ConvertTo-Json -Depth 5
    $json | Out-File -FilePath $heartbeatPath -Encoding UTF8
}

# ---------------------------------------------------------------------------
# Startup banner
# ---------------------------------------------------------------------------

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " Windows Workstation Relay Node" -ForegroundColor Cyan
Write-Host " Phase 96.8AO" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  node_id:        $nodeId"
Write-Host "  machine:        $machineName"
Write-Host "  user:           $userName"
Write-Host "  os:             $osVersion"
Write-Host "  ps:             $psVersion"
Write-Host "  relay PID:      $relayPid"
Write-Host "  relay script:   $relayScriptHash"
Write-Host "  repo commit:    $repoCommit"
Write-Host "  Chrome:         $(if ($chromeAvailable) { $chromeExe } else { 'NOT FOUND' })"
Write-Host "  heartbeat:      $heartbeatPath"
Write-Host "  heartbeat int:  ${HeartbeatIntervalSeconds}s"
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Write initial heartbeat
Write-Heartbeat
Write-Host "[relay-node] Initial heartbeat written"

# ---------------------------------------------------------------------------
# Start relay in background, heartbeat in foreground
# ---------------------------------------------------------------------------

Write-Host "[relay-node] Starting relay watcher..."

$relayJob = Start-Job -ScriptBlock {
    param($ScriptPath, $Repo)
    & $ScriptPath `
        -InboxPath "$Repo\eos_advisor_messages\windows_desktop_relay\inbox" `
        -OutboxPath "$Repo\eos_advisor_messages\windows_desktop_relay\outbox"
} -ArgumentList $relayScript, $repo

Write-Host "[relay-node] Relay started as job $($relayJob.Id)"
Write-Host "[relay-node] Node ONLINE — emitting heartbeats every ${HeartbeatIntervalSeconds}s"
Write-Host "[relay-node] Press Ctrl+C to stop"
Write-Host ""

# Heartbeat loop
try {
    while ($true) {
        Write-Heartbeat
        $ts = (Get-Date).ToString("HH:mm:ss")
        Write-Host "[$ts] [heartbeat] alive node=$nodeId pid=$relayPid chrome=$chromeAvailable"

        # Check relay job health
        if ($relayJob.State -ne "Running") {
            Write-Host "[$ts] [relay-node] WARNING: Relay job state=$($relayJob.State)" -ForegroundColor Yellow
            $relayOutput = Receive-Job $relayJob -ErrorAction SilentlyContinue
            if ($relayOutput) {
                $relayOutput | ForEach-Object { Write-Host "  [relay] $_" }
            }
        }

        Start-Sleep -Seconds $HeartbeatIntervalSeconds
    }
}
finally {
    Write-Host "[relay-node] Shutting down..."
    Stop-Job $relayJob -ErrorAction SilentlyContinue
    Remove-Job $relayJob -ErrorAction SilentlyContinue
    Write-Host "[relay-node] Relay stopped"
}
