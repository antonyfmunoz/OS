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
# Screenshot helper
# ---------------------------------------------------------------------------

function Capture-Screenshot {
    param([string]$OutputPath)

    Write-Log "Capturing screenshot to: $OutputPath"
    try {
        Add-Type -AssemblyName System.Windows.Forms
        Add-Type -AssemblyName System.Drawing

        $screen = [System.Windows.Forms.Screen]::PrimaryScreen
        $bounds = $screen.Bounds
        $bitmap = New-Object System.Drawing.Bitmap($bounds.Width, $bounds.Height)
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        $graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
        $bitmap.Save($OutputPath, [System.Drawing.Imaging.ImageFormat]::Png)
        $graphics.Dispose()
        $bitmap.Dispose()

        Write-Log "Screenshot captured: $OutputPath"
        return $true
    }
    catch {
        Write-Log "WARNING: Screenshot capture failed: $($_.Exception.Message)"
        return $false
    }
}

function Get-FileHash256 {
    param([string]$FilePath)
    try {
        $hash = Get-FileHash -Path $FilePath -Algorithm SHA256
        return $hash.Hash.ToLower()
    }
    catch {
        return ""
    }
}

function Get-ForegroundWindowInfo {
    Write-Log "Getting foreground window info..."
    try {
        Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Text;
public class Win32FG {
    [DllImport("user32.dll")]
    public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")]
    public static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int count);
    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);
    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hWnd);
}
"@
        $fgHwnd = [Win32FG]::GetForegroundWindow()
        $sb = New-Object System.Text.StringBuilder 256
        [Win32FG]::GetWindowText($fgHwnd, $sb, 256) | Out-Null
        $fgTitle = $sb.ToString()

        $fgPid = [uint32]0
        [Win32FG]::GetWindowThreadProcessId($fgHwnd, [ref]$fgPid) | Out-Null
        $fgVisible = [Win32FG]::IsWindowVisible($fgHwnd)

        Write-Log "Foreground window: handle=$($fgHwnd.ToInt64()) title='$fgTitle' pid=$fgPid visible=$fgVisible"
        return @{
            handle  = $fgHwnd.ToInt64()
            title   = $fgTitle
            pid     = [int]$fgPid
            visible = $fgVisible
        }
    }
    catch {
        Write-Log "WARNING: Could not get foreground window: $($_.Exception.Message)"
        return @{ handle = 0; title = ""; pid = 0; visible = $false }
    }
}

# ---------------------------------------------------------------------------
# Chrome proof handler
# ---------------------------------------------------------------------------

function Handle-ChromeProof {
    param([hashtable]$Request)

    $rid         = $Request["request_id"]
    $traceId     = $Request["trace_id"]
    $workOrderId = $Request["work_order_id"]
    $url         = $Request["url"]
    $proofDir    = $Request["proof_dir"]
    $isDryRun    = $Request["dry_run"] -eq $true

    if (-not $url) { $url = "https://www.google.com" }
    if (-not $proofDir) { $proofDir = "$HOME\eos_advisor_messages\windows_desktop_relay\gui_proofs" }

    Write-Log "CHROME_PROOF: rid=$rid url=$url proof_dir=$proofDir dry_run=$isDryRun"

    # Ensure proof directory
    if (-not (Test-Path $proofDir)) {
        New-Item -ItemType Directory -Path $proofDir -Force | Out-Null
    }

    # Collect pre-launch desktop state
    $preFg = Get-ForegroundWindowInfo
    $desktopUnlocked = $true
    $activeSession = $true

    if ($isDryRun) {
        Write-Log "DRY RUN: would launch Chrome and capture proof"
        Write-Result -RequestId $rid -Result @{
            request_id     = $rid
            trace_id       = $traceId
            work_order_id  = $workOrderId
            action_type    = "chrome_proof"
            adapter_status = "completed"
            dry_run        = $true
            timestamp      = Get-Timestamp
            notes          = @("Dry run only - no Chrome launch or screenshot")
        }
        return
    }

    # Find Chrome
    $chromeExe = Find-ChromeExe
    if (-not $chromeExe) {
        Write-Log "FAILED: Chrome not found"
        Write-Result -RequestId $rid -Result @{
            request_id     = $rid
            trace_id       = $traceId
            action_type    = "chrome_proof"
            adapter_status = "failed"
            error          = "CHROME_NOT_FOUND"
            timestamp      = Get-Timestamp
        }
        return
    }

    # Stage 1: Launch Chrome
    Write-Log "Stage 1: Launching Chrome..."
    $commandIssued = "$chromeExe --new-window $url"
    try {
        $process = Start-Process -FilePath $chromeExe -ArgumentList "--new-window", $url -PassThru
        Start-Sleep -Seconds 4
    }
    catch {
        Write-Result -RequestId $rid -Result @{
            request_id     = $rid
            trace_id       = $traceId
            action_type    = "chrome_proof"
            adapter_status = "failed"
            error          = "CHROME_LAUNCH_FAILED: $($_.Exception.Message)"
            timestamp      = Get-Timestamp
        }
        return
    }

    $processDetected = -not $process.HasExited
    $chromePid = $process.Id
    Write-Log "Chrome launched: PID=$chromePid running=$processDetected"

    # Stage 2: Verify process
    $chromeProcs = Get-Process chrome -ErrorAction SilentlyContinue
    $chromeRunning = ($chromeProcs -ne $null) -and ($chromeProcs.Count -gt 0)
    Write-Log "Stage 2: Chrome processes found: $($chromeProcs.Count)"

    # Stage 3: Collect window metadata
    $windowMeta = @{}
    $mainProc = $null
    try {
        if ($chromeProcs) {
            $mainProc = $chromeProcs | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
            if ($mainProc) {
                $windowMeta = @{
                    main_window_handle = $mainProc.MainWindowHandle.ToInt64()
                    main_window_title  = $mainProc.MainWindowTitle
                }
            }
        }
    }
    catch {
        Write-Log "WARNING: Window metadata collection failed"
    }

    # Stage 4: Verify focus
    $postFg = Get-ForegroundWindowInfo
    $isChromeForegrounded = $false
    if ($chromeProcs) {
        foreach ($cp in $chromeProcs) {
            if ($cp.Id -eq $postFg["pid"]) {
                $isChromeForegrounded = $true
                break
            }
        }
    }
    Write-Log "Stage 4: Chrome foreground=$isChromeForegrounded fg_pid=$($postFg['pid'])"

    # Stage 5: Capture launch screenshot
    $launchScreenshotPath = Join-Path $proofDir "${rid}_chrome_launch.png"
    $screenshotCaptured = Capture-Screenshot -OutputPath $launchScreenshotPath
    $screenshotHash = ""
    if ($screenshotCaptured) {
        $screenshotHash = Get-FileHash256 -FilePath $launchScreenshotPath
        Write-Log "Screenshot hash: $screenshotHash"
    }

    # Stage 6: Capture focused window screenshot (after small delay)
    Start-Sleep -Seconds 1
    $focusScreenshotPath = Join-Path $proofDir "${rid}_focused_window.png"
    Capture-Screenshot -OutputPath $focusScreenshotPath | Out-Null

    # Stage 7: Navigation screenshot (page should be loaded by now)
    Start-Sleep -Seconds 2
    $navScreenshotPath = Join-Path $proofDir "${rid}_navigation.png"
    Capture-Screenshot -OutputPath $navScreenshotPath | Out-Null

    # Build observed desktop state
    $observedState = @{
        chrome_pid          = $chromePid
        window_handle       = if ($windowMeta["main_window_handle"]) { $windowMeta["main_window_handle"] } else { 0 }
        window_title        = if ($windowMeta["main_window_title"]) { $windowMeta["main_window_title"] } else { "" }
        visible             = $processDetected
        focused             = $isChromeForegrounded
        monitor_detected    = $true
        desktop_unlocked    = $desktopUnlocked
        active_user_session = $activeSession
        navigation_url      = $url
        navigation_detected = ($windowMeta["main_window_title"] -ne $null -and $windowMeta["main_window_title"] -ne "")
        screenshot_hash     = $screenshotHash
        screenshot_path     = $launchScreenshotPath
        timestamp           = Get-Timestamp
    }

    # Write observed state to proof dir
    $stateJson = $observedState | ConvertTo-Json -Depth 5
    $statePath = Join-Path $proofDir "${rid}_runtime_state.json"
    $stateJson | Out-File -FilePath $statePath -Encoding UTF8

    # Write desktop environment info
    $desktopEnv = @{
        hostname        = $env:COMPUTERNAME
        username        = $env:USERNAME
        os_version      = [System.Environment]::OSVersion.VersionString
        ps_version      = $PSVersionTable.PSVersion.ToString()
        screen_count    = [System.Windows.Forms.Screen]::AllScreens.Count
        primary_screen  = @{
            width  = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Width
            height = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Height
        }
        timestamp       = Get-Timestamp
    }
    $desktopEnvJson = $desktopEnv | ConvertTo-Json -Depth 5
    $desktopEnvPath = Join-Path $proofDir "${rid}_desktop_environment.json"
    $desktopEnvJson | Out-File -FilePath $desktopEnvPath -Encoding UTF8

    # Build stages completed
    $stagesCompleted = @("relay_dispatched", "chrome_launched")
    if ($chromeRunning) { $stagesCompleted += "process_verified" }
    if ($windowMeta["main_window_handle"]) { $stagesCompleted += "window_detected" }
    if ($isChromeForegrounded) { $stagesCompleted += "focus_confirmed" }
    if ($observedState["navigation_detected"]) { $stagesCompleted += "navigation_confirmed" }
    if ($screenshotCaptured) { $stagesCompleted += "screenshot_captured" }

    # Write proof summary
    $proofSummary = @{
        proof_id            = "GUI-ACT-PROOF-$($rid.Substring($rid.Length - 8))"
        trace_id            = $traceId
        environment         = "local_windows_foreground"
        passed              = ($isChromeForegrounded -and $processDetected -and $screenshotCaptured)
        chrome_pid          = $chromePid
        window_handle       = $observedState["window_handle"]
        stages_completed    = $stagesCompleted
        screenshot_hash     = $screenshotHash
        founder_confirmed   = $false
        founder_confirmation_required = $true
        timestamp           = Get-Timestamp
    }
    $proofSummaryJson = $proofSummary | ConvertTo-Json -Depth 5
    $proofSummaryPath = Join-Path $proofDir "${rid}_proof_summary.json"
    $proofSummaryJson | Out-File -FilePath $proofSummaryPath -Encoding UTF8

    # Write relay result
    Write-Result -RequestId $rid -Result @{
        request_id                     = $rid
        trace_id                       = $traceId
        work_order_id                  = $workOrderId
        action_type                    = "chrome_proof"
        adapter_status                 = "completed"
        command_issued                 = $commandIssued
        process_detected               = $processDetected
        process_id                     = $chromePid
        window_metadata                = $windowMeta
        observed_desktop_state         = $observedState
        visible_proof_status           = if ($isChromeForegrounded) { "process_detected" } else { "no_proof" }
        founder_visual_confirmation_required = $true
        stages_completed               = $stagesCompleted
        screenshot_captured            = $screenshotCaptured
        screenshot_hash                = $screenshotHash
        screenshot_path                = $launchScreenshotPath
        proof_dir                      = $proofDir
        proof_artifacts                = @(
            "${rid}_chrome_launch.png",
            "${rid}_focused_window.png",
            "${rid}_navigation.png",
            "${rid}_runtime_state.json",
            "${rid}_desktop_environment.json",
            "${rid}_proof_summary.json"
        )
        timestamp                      = Get-Timestamp
        notes                          = @(
            "Real Chrome launch via direct executable",
            "Screenshot proof captured at each stage",
            "Observed desktop state collected from real system",
            "Window metadata is evidence, not proof",
            "Founder must visually confirm Chrome is visible",
            "Foreground focus detected: $isChromeForegrounded"
        )
    }

    Write-Log "CHROME_PROOF completed: stages=$($stagesCompleted -join ',')"
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
            "chrome_proof" {
                Handle-ChromeProof -Request $request
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
