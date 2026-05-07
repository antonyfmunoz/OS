<#
.SYNOPSIS
    Windows Interactive Desktop Relay v1 - Phase 96.8I

.DESCRIPTION
    Watches a relay inbox for JSON action requests from the WSL worker.
    Executes GUI actions in the logged-in Windows desktop session.
    Writes structured result JSON to the relay outbox.

    This script MUST be run from the logged-in Windows user session
    (not from WSL, not from a headless service).

    Compatible with Windows PowerShell 5.1 (no -AsHashtable).

.NOTES
    Supported actions:
      ping                  - returns pong
      open_application_url  - launches Chrome via direct executable

    Blocked methods:
      explorer_url, default_browser, shell_url_open,
      generic_start_url, unknown_browser
#>

param(
    [string]$InboxPath = "$HOME\eos_advisor_messages\windows_desktop_relay\inbox",
    [string]$OutboxPath = "$HOME\eos_advisor_messages\windows_desktop_relay\outbox",
    [int]$PollIntervalSeconds = 2
)

$ErrorActionPreference = "Stop"

$CHROME_EXE = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$CHROME_EXE_X86 = "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

$BLOCKED_LAUNCH_METHODS = @(
    "explorer_url",
    "default_browser",
    "shell_url_open",
    "generic_start_url",
    "unknown_browser"
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

function ConvertTo-Hashtable {
    param([Parameter(ValueFromPipeline=$true)]$InputObject)

    if ($null -eq $InputObject) { return $null }

    if ($InputObject -is [System.Collections.IEnumerable] -and $InputObject -isnot [string]) {
        $list = @()
        foreach ($item in $InputObject) {
            $list += (ConvertTo-Hashtable $item)
        }
        return ,$list
    }

    if ($InputObject -is [PSCustomObject]) {
        $hash = @{}
        foreach ($prop in $InputObject.PSObject.Properties) {
            $hash[$prop.Name] = ConvertTo-Hashtable $prop.Value
        }
        return $hash
    }

    return $InputObject
}

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
    $outPath = Join-Path $OutboxPath $filename
    Write-Log "Writing result: $outPath"
    try {
        $json = $Result | ConvertTo-Json -Depth 10
        $json | Out-File -FilePath $outPath -Encoding UTF8
        Write-Log "Result written OK: $filename ($(( Get-Item $outPath ).Length) bytes)"
    }
    catch {
        Write-Log "ERROR writing result: $($_.Exception.Message)"
    }
}

function Find-ChromeExe {
    Write-Log "Looking for Chrome..."
    if (Test-Path $CHROME_EXE) {
        Write-Log "Found Chrome at: $CHROME_EXE"
        return $CHROME_EXE
    }
    if (Test-Path $CHROME_EXE_X86) {
        Write-Log "Found Chrome at: $CHROME_EXE_X86"
        return $CHROME_EXE_X86
    }
    Write-Log "Chrome not found at either standard path"
    return $null
}

# ---------------------------------------------------------------------------
# Action handlers
# ---------------------------------------------------------------------------

function Handle-Ping {
    param([hashtable]$Request)

    $rid = $Request["request_id"]
    Write-Log "PING received: request_id=$rid"

    Write-Result -RequestId $rid -Result @{
        request_id     = $rid
        trace_id       = $Request["trace_id"]
        action_type    = "ping"
        adapter_status = "pong"
        timestamp      = Get-Timestamp
        notes          = @("Relay is alive and listening")
    }

    Write-Log "PING handled OK for $rid"
}

function Handle-OpenApplicationUrl {
    param([hashtable]$Request)

    $rid         = $Request["request_id"]
    $traceId     = $Request["trace_id"]
    $workOrderId = $Request["work_order_id"]
    $appId       = $Request["application_id"]
    $launchMethod = $Request["launch_method"]
    $url         = $Request["url"]
    $isDryRun    = $Request["dry_run"] -eq $true

    Write-Log "OPEN_APPLICATION_URL: rid=$rid app=$appId method=$launchMethod url=$url dry_run=$isDryRun"

    # --- gate: blocked launch methods ---
    if ($BLOCKED_LAUNCH_METHODS -contains $launchMethod) {
        Write-Log "REJECTED: blocked launch method '$launchMethod'"
        Write-Result -RequestId $rid -Result @{
            request_id     = $rid
            trace_id       = $traceId
            work_order_id  = $workOrderId
            action_type    = "open_application_url"
            adapter_status = "rejected"
            error          = "BLOCKED_LAUNCH_METHOD: $launchMethod"
            timestamp      = Get-Timestamp
        }
        return
    }

    # --- gate: only direct_executable ---
    if ($launchMethod -ne "direct_executable") {
        Write-Log "REJECTED: only direct_executable allowed, got '$launchMethod'"
        Write-Result -RequestId $rid -Result @{
            request_id     = $rid
            trace_id       = $traceId
            work_order_id  = $workOrderId
            action_type    = "open_application_url"
            adapter_status = "rejected"
            error          = "INVALID_LAUNCH_METHOD: only direct_executable allowed"
            timestamp      = Get-Timestamp
        }
        return
    }

    # --- gate: only Chrome ---
    if ($appId -ne "google_chrome_windows") {
        Write-Log "REJECTED: unsupported application '$appId'"
        Write-Result -RequestId $rid -Result @{
            request_id     = $rid
            trace_id       = $traceId
            work_order_id  = $workOrderId
            action_type    = "open_application_url"
            adapter_status = "rejected"
            error          = "UNSUPPORTED_APPLICATION: $appId"
            timestamp      = Get-Timestamp
        }
        return
    }

    # --- find Chrome executable ---
    $chromeExe = Find-ChromeExe
    if (-not $chromeExe) {
        Write-Log "FAILED: Chrome not found"
        Write-Result -RequestId $rid -Result @{
            request_id     = $rid
            trace_id       = $traceId
            work_order_id  = $workOrderId
            action_type    = "open_application_url"
            adapter_status = "failed"
            error          = "CHROME_NOT_FOUND"
            timestamp      = Get-Timestamp
        }
        return
    }

    # --- dry run ---
    if ($isDryRun) {
        Write-Log "DRY RUN: would launch $chromeExe --new-window $url"
        Write-Result -RequestId $rid -Result @{
            request_id     = $rid
            trace_id       = $traceId
            work_order_id  = $workOrderId
            action_type    = "open_application_url"
            adapter_status = "completed"
            command_issued = "$chromeExe --new-window $url"
            process_detected = $false
            visible_proof_status = "no_proof"
            founder_visual_confirmation_required = $true
            timestamp      = Get-Timestamp
            notes          = @("Dry run only - no Chrome launch")
        }
        return
    }

    # --- actual launch ---
    Write-Log "Launching Chrome: $chromeExe --new-window $url"
    $commandIssued = "$chromeExe --new-window $url"

    try {
        $process = Start-Process -FilePath $chromeExe -ArgumentList "--new-window", $url -PassThru
        Start-Sleep -Seconds 3

        $processDetected = -not $process.HasExited
        $processId = $process.Id

        Write-Log "Chrome launched. PID=$processId running=$processDetected"

        # Collect window metadata as evidence (NOT proof)
        $windowMeta = @{}
        try {
            $chromeProcs = Get-Process chrome -ErrorAction SilentlyContinue
            if ($chromeProcs) {
                $mainProc = $chromeProcs | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
                if ($mainProc) {
                    $windowMeta = @{
                        main_window_handle = $mainProc.MainWindowHandle.ToInt64()
                        main_window_title  = $mainProc.MainWindowTitle
                        note               = "Window metadata is EVIDENCE only, not proof"
                    }
                    Write-Log "Window metadata collected: handle=$($windowMeta['main_window_handle'])"
                }
            }
        }
        catch {
            Write-Log "WARNING: Could not collect window metadata: $($_.Exception.Message)"
            $windowMeta = @{ error = "Failed to collect window metadata" }
        }

        Write-Result -RequestId $rid -Result @{
            request_id     = $rid
            trace_id       = $traceId
            work_order_id  = $workOrderId
            action_type    = "open_application_url"
            adapter_status = "completed"
            command_issued = $commandIssued
            process_detected = $processDetected
            process_id     = $processId
            window_metadata = $windowMeta
            visible_proof_status = "pending_founder_visual_confirmation"
            founder_visual_confirmation_required = $true
            timestamp      = Get-Timestamp
            notes          = @(
                "Chrome launched via direct executable",
                "Window metadata is evidence only - NOT proof",
                "Founder must visually confirm Chrome is visible"
            )
        }
    }
    catch {
        Write-Log "ERROR: Chrome launch failed: $($_.Exception.Message)"
        Write-Result -RequestId $rid -Result @{
            request_id     = $rid
            trace_id       = $traceId
            work_order_id  = $workOrderId
            action_type    = "open_application_url"
            adapter_status = "failed"
            command_issued = $commandIssued
            error          = "CHROME_LAUNCH_FAILED: $($_.Exception.Message)"
            timestamp      = Get-Timestamp
        }
    }
}

# ---------------------------------------------------------------------------
# Request processor
# ---------------------------------------------------------------------------

function Process-Request {
    param([string]$FilePath)

    Write-Log "--- Begin processing: $FilePath ---"

    # Step 1: Read and parse JSON
    $request = $null
    try {
        Write-Log "Reading file..."
        $content = Get-Content -Path $FilePath -Raw
        Write-Log "File read OK ($(($content).Length) chars)"

        Write-Log "Parsing JSON (PS 5.1 compatible, no -AsHashtable)..."
        $parsed = $content | ConvertFrom-Json
        Write-Log "ConvertFrom-Json OK, converting PSCustomObject to hashtable..."
        $request = ConvertTo-Hashtable $parsed
        Write-Log "Hashtable conversion OK"
    }
    catch {
        Write-Log "ERROR: Failed to read/parse '$FilePath': $($_.Exception.Message)"
        Write-Log "ERROR: Type: $($_.Exception.GetType().FullName)"
        return
    }

    # Step 2: Extract action type
    $actionType = $request["action_type"]
    $rid = $request["request_id"]
    Write-Log "Parsed: action_type=$actionType request_id=$rid"

    # Step 3: Dispatch to handler
    try {
        switch ($actionType) {
            "ping" {
                Handle-Ping -Request $request
            }
            "open_application_url" {
                Handle-OpenApplicationUrl -Request $request
            }
            default {
                Write-Log "UNKNOWN action_type: $actionType"
                if ($rid) {
                    Write-Result -RequestId $rid -Result @{
                        request_id     = $rid
                        action_type    = $actionType
                        adapter_status = "rejected"
                        error          = "UNKNOWN_ACTION_TYPE: $actionType"
                        timestamp      = Get-Timestamp
                    }
                }
            }
        }
    }
    catch {
        Write-Log "ERROR: Handler failed for action_type=$actionType : $($_.Exception.Message)"
        Write-Log "ERROR: Stack: $($_.ScriptStackTrace)"
        if ($rid) {
            try {
                Write-Result -RequestId $rid -Result @{
                    request_id     = $rid
                    action_type    = $actionType
                    adapter_status = "failed"
                    error          = "HANDLER_EXCEPTION: $($_.Exception.Message)"
                    timestamp      = Get-Timestamp
                }
            }
            catch {
                Write-Log "ERROR: Could not write error result: $($_.Exception.Message)"
            }
        }
    }

    # Step 4: Move to processed
    try {
        $processedDir = Join-Path (Split-Path $InboxPath) "processed"
        if (-not (Test-Path $processedDir)) {
            New-Item -ItemType Directory -Path $processedDir -Force | Out-Null
        }
        $destPath = Join-Path $processedDir (Split-Path $FilePath -Leaf)
        Move-Item -Path $FilePath -Destination $destPath -Force
        Write-Log "Moved to processed: $destPath"
    }
    catch {
        Write-Log "WARNING: Could not move to processed: $($_.Exception.Message)"
    }

    Write-Log "--- Done processing: $(Split-Path $FilePath -Leaf) ---"
}

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

Write-Log "=========================================="
Write-Log "Windows Interactive Desktop Relay v1"
Write-Log "Phase 96.8I (PS 5.1 compatible)"
Write-Log "=========================================="
Write-Log "Inbox:  $InboxPath"
Write-Log "Outbox: $OutboxPath"
Write-Log "Poll:   ${PollIntervalSeconds}s"
Write-Log "PowerShell version: $($PSVersionTable.PSVersion)"
Write-Log ""
Write-Log "This relay runs in the logged-in Windows session."
Write-Log "WSL/tmux delegates GUI actions here."
Write-Log ""
Write-Log "Watching inbox for requests..."
Write-Log ""

Ensure-Directories

while ($true) {
    $files = Get-ChildItem -Path $InboxPath -Filter "*.json" -ErrorAction SilentlyContinue

    foreach ($file in $files) {
        Write-Log "Found request file: $($file.Name)"
        Process-Request -FilePath $file.FullName
    }

    Start-Sleep -Seconds $PollIntervalSeconds
}
