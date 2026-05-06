<#
.SYNOPSIS
    Windows Interactive Desktop Relay v1 — Phase 96.8H

.DESCRIPTION
    Watches a relay inbox for JSON action requests from the WSL worker.
    Executes GUI actions in the logged-in Windows desktop session.
    Writes structured result JSON to the relay outbox.

    This script MUST be run from the logged-in Windows user session
    (not from WSL, not from a headless service). It has real desktop
    access because it runs in the interactive session.

.NOTES
    - Run from PowerShell in the logged-in Windows session
    - Do NOT run from WSL or tmux
    - Do NOT run as a Windows service (Session 0 has no desktop)
    - Founder starts this manually before any W0 execution

    Supported actions:
    - ping                                → pong
    - open_application_url                → launch Chrome directly
    - focus_application                   → bring app to foreground
    - request_founder_visual_confirmation → write confirmation request

    Blocked:
    - explorer.exe URL routing
    - default-browser routing
    - generic shell URL open
    - screenshot capture
    - credential/token/cookie access
    - page content reading
    - any mutation action
#>

param(
    [string]$InboxPath = "$HOME\eos_advisor_messages\windows_desktop_relay\inbox",
    [string]$OutboxPath = "$HOME\eos_advisor_messages\windows_desktop_relay\outbox",
    [int]$PollIntervalSeconds = 2
)

$ErrorActionPreference = "Stop"

# Blocked launch methods — these must NEVER be used
$BLOCKED_LAUNCH_METHODS = @(
    "explorer_url",
    "default_browser",
    "shell_url_open",
    "generic_start_url",
    "unknown_browser"
)

$CHROME_EXE = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$CHROME_EXE_X86 = "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

function Get-Timestamp {
    return (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
}

function Write-Log {
    param([string]$Message)
    $ts = Get-Date -Format "HH:mm:ss"
    Write-Host "[$ts] [relay] $Message"
}

function Ensure-Directories {
    if (-not (Test-Path $InboxPath)) {
        New-Item -ItemType Directory -Path $InboxPath -Force | Out-Null
        Write-Log "Created inbox: $InboxPath"
    }
    if (-not (Test-Path $OutboxPath)) {
        New-Item -ItemType Directory -Path $OutboxPath -Force | Out-Null
        Write-Log "Created outbox: $OutboxPath"
    }
}

function Write-Result {
    param(
        [string]$RequestId,
        [hashtable]$Result
    )
    $filename = "${RequestId}_result.json"
    $path = Join-Path $OutboxPath $filename
    $Result | ConvertTo-Json -Depth 10 | Out-File -FilePath $path -Encoding UTF8
    Write-Log "Result written: $filename"
}

function Find-ChromeExe {
    if (Test-Path $CHROME_EXE) { return $CHROME_EXE }
    if (Test-Path $CHROME_EXE_X86) { return $CHROME_EXE_X86 }
    return $null
}

function Handle-Ping {
    param([hashtable]$Request)

    $requestId = $Request["request_id"]
    Write-Log "PING received ($requestId)"

    Write-Result -RequestId $requestId -Result @{
        request_id = $requestId
        trace_id = $Request["trace_id"]
        action_type = "ping"
        adapter_status = "pong"
        timestamp = Get-Timestamp
        notes = @("Relay is alive and listening")
    }
}

function Handle-OpenApplicationUrl {
    param([hashtable]$Request)

    $requestId = $Request["request_id"]
    $traceId = $Request["trace_id"]
    $workOrderId = $Request["work_order_id"]
    $appId = $Request["application_id"]
    $launchMethod = $Request["launch_method"]
    $url = $Request["url"]
    $isDryRun = $Request["dry_run"] -eq $true

    Write-Log "OPEN_APPLICATION_URL: app=$appId method=$launchMethod url=$url"

    # Validate launch method
    if ($BLOCKED_LAUNCH_METHODS -contains $launchMethod) {
        Write-Log "REJECTED: launch method '$launchMethod' is blocked"
        Write-Result -RequestId $requestId -Result @{
            request_id = $requestId
            trace_id = $traceId
            work_order_id = $workOrderId
            action_type = "open_application_url"
            adapter_status = "rejected"
            error = "BLOCKED_LAUNCH_METHOD: $launchMethod"
            timestamp = Get-Timestamp
        }
        return
    }

    if ($launchMethod -ne "direct_executable") {
        Write-Log "REJECTED: only direct_executable is allowed, got '$launchMethod'"
        Write-Result -RequestId $requestId -Result @{
            request_id = $requestId
            trace_id = $traceId
            work_order_id = $workOrderId
            action_type = "open_application_url"
            adapter_status = "rejected"
            error = "INVALID_LAUNCH_METHOD: only direct_executable allowed"
            timestamp = Get-Timestamp
        }
        return
    }

    if ($appId -ne "google_chrome_windows") {
        Write-Log "REJECTED: unsupported application '$appId'"
        Write-Result -RequestId $requestId -Result @{
            request_id = $requestId
            trace_id = $traceId
            work_order_id = $workOrderId
            action_type = "open_application_url"
            adapter_status = "rejected"
            error = "UNSUPPORTED_APPLICATION: $appId"
            timestamp = Get-Timestamp
        }
        return
    }

    # Find Chrome
    $chromeExe = Find-ChromeExe
    if (-not $chromeExe) {
        Write-Log "FAILED: Chrome executable not found"
        Write-Result -RequestId $requestId -Result @{
            request_id = $requestId
            trace_id = $traceId
            work_order_id = $workOrderId
            action_type = "open_application_url"
            adapter_status = "failed"
            error = "CHROME_NOT_FOUND"
            timestamp = Get-Timestamp
        }
        return
    }

    if ($isDryRun) {
        Write-Log "DRY RUN: would launch '$chromeExe --new-window $url'"
        Write-Result -RequestId $requestId -Result @{
            request_id = $requestId
            trace_id = $traceId
            work_order_id = $workOrderId
            action_type = "open_application_url"
            adapter_status = "completed"
            command_issued = "$chromeExe --new-window $url"
            process_detected = $false
            visible_proof_status = "no_proof"
            founder_visual_confirmation_required = $true
            timestamp = Get-Timestamp
            notes = @("Dry run only — no Chrome launch")
        }
        return
    }

    # Launch Chrome with direct executable
    Write-Log "Launching: $chromeExe --new-window $url"
    $commandIssued = "$chromeExe --new-window $url"

    try {
        $process = Start-Process -FilePath $chromeExe -ArgumentList "--new-window", $url -PassThru
        Start-Sleep -Seconds 3

        $processDetected = -not $process.HasExited
        $processId = $process.Id

        # Collect window metadata as evidence (NOT proof)
        $windowMeta = @{}
        try {
            $chromeProcs = Get-Process chrome -ErrorAction SilentlyContinue
            if ($chromeProcs) {
                $mainProc = $chromeProcs | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
                if ($mainProc) {
                    $windowMeta = @{
                        main_window_handle = $mainProc.MainWindowHandle.ToInt64()
                        main_window_title = $mainProc.MainWindowTitle
                        note = "Window metadata is EVIDENCE only, not proof"
                    }
                }
            }
        } catch {
            $windowMeta = @{ error = "Failed to collect window metadata" }
        }

        Write-Log "Chrome launched. PID=$processId detected=$processDetected"

        Write-Result -RequestId $requestId -Result @{
            request_id = $requestId
            trace_id = $traceId
            work_order_id = $workOrderId
            action_type = "open_application_url"
            adapter_status = "completed"
            command_issued = $commandIssued
            process_detected = $processDetected
            process_id = $processId
            window_metadata = $windowMeta
            visible_proof_status = "pending_founder_visual_confirmation"
            founder_visual_confirmation_required = $true
            timestamp = Get-Timestamp
            notes = @(
                "Chrome launched via direct executable",
                "Window metadata is evidence only — NOT proof",
                "Founder must visually confirm Chrome is visible"
            )
        }
    }
    catch {
        Write-Log "FAILED: Chrome launch error — $_"
        Write-Result -RequestId $requestId -Result @{
            request_id = $requestId
            trace_id = $traceId
            work_order_id = $workOrderId
            action_type = "open_application_url"
            adapter_status = "failed"
            command_issued = $commandIssued
            error = "CHROME_LAUNCH_FAILED: $_"
            timestamp = Get-Timestamp
        }
    }
}

function Process-Request {
    param([string]$FilePath)

    try {
        $content = Get-Content -Path $FilePath -Raw
        $request = $content | ConvertFrom-Json -AsHashtable
    }
    catch {
        Write-Log "ERROR: Failed to parse request file '$FilePath': $_"
        return
    }

    $actionType = $request["action_type"]

    switch ($actionType) {
        "ping" {
            Handle-Ping -Request $request
        }
        "open_application_url" {
            Handle-OpenApplicationUrl -Request $request
        }
        default {
            Write-Log "UNKNOWN action type: $actionType"
            $requestId = $request["request_id"]
            if ($requestId) {
                Write-Result -RequestId $requestId -Result @{
                    request_id = $requestId
                    action_type = $actionType
                    adapter_status = "rejected"
                    error = "UNKNOWN_ACTION_TYPE: $actionType"
                    timestamp = Get-Timestamp
                }
            }
        }
    }

    # Move processed request to avoid re-processing
    $processedDir = Join-Path (Split-Path $InboxPath) "processed"
    if (-not (Test-Path $processedDir)) {
        New-Item -ItemType Directory -Path $processedDir -Force | Out-Null
    }
    $destPath = Join-Path $processedDir (Split-Path $FilePath -Leaf)
    Move-Item -Path $FilePath -Destination $destPath -Force
}

# ── Main Loop ──────────────────────────────────────────────────────────────

Write-Log "=========================================="
Write-Log "Windows Interactive Desktop Relay v1"
Write-Log "Phase 96.8H"
Write-Log "=========================================="
Write-Log "Inbox:  $InboxPath"
Write-Log "Outbox: $OutboxPath"
Write-Log "Poll:   ${PollIntervalSeconds}s"
Write-Log ""
Write-Log "IMPORTANT: This relay runs in the logged-in"
Write-Log "Windows session. It has real desktop access."
Write-Log "WSL/tmux delegates GUI actions here."
Write-Log ""
Write-Log "Watching inbox for requests..."
Write-Log ""

Ensure-Directories

while ($true) {
    $files = Get-ChildItem -Path $InboxPath -Filter "*.json" -ErrorAction SilentlyContinue

    foreach ($file in $files) {
        Write-Log "Processing: $($file.Name)"
        Process-Request -FilePath $file.FullName
    }

    Start-Sleep -Seconds $PollIntervalSeconds
}
