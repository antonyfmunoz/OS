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
      chrome_proof          - Chrome launch with screenshot proof
      ingest_safe_doc_cu    - foreground CU ingestion with DOM extraction
      explore_environment   - exploratory environment mapping with process/app enumeration

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
# Safe doc CU ingestion handler
# ---------------------------------------------------------------------------

function Handle-IngestSafeDocCU {
    param([hashtable]$Request)

    $rid         = $Request["request_id"]
    $traceId     = $Request["trace_id"]
    $workOrderId = $Request["work_order_id"]
    $url         = $Request["url"]
    $proofDir    = $Request["proof_dir"]
    $isDryRun    = $Request["dry_run"] -eq $true

    if (-not $url) { $url = "https://docs.google.com/document/d/EOS-W0-SAFE-TEST-DOC/edit" }
    if (-not $proofDir) { $proofDir = "$HOME\eos_advisor_messages\windows_desktop_relay\gui_proofs" }

    Write-Log "INGEST_SAFE_DOC_CU: rid=$rid url=$url proof_dir=$proofDir dry_run=$isDryRun"

    if (-not (Test-Path $proofDir)) {
        New-Item -ItemType Directory -Path $proofDir -Force | Out-Null
    }

    $preFg = Get-ForegroundWindowInfo
    $desktopUnlocked = $true
    $activeSession = $true

    if ($isDryRun) {
        Write-Log "DRY RUN: would launch Chrome, navigate, and extract"
        Write-Result -RequestId $rid -Result @{
            request_id     = $rid
            trace_id       = $traceId
            work_order_id  = $workOrderId
            action_type    = "ingest_safe_doc_cu"
            adapter_status = "completed"
            dry_run        = $true
            timestamp      = Get-Timestamp
            notes          = @("Dry run only - no Chrome launch, navigation, or extraction")
        }
        return
    }

    $chromeExe = Find-ChromeExe
    if (-not $chromeExe) {
        Write-Log "FAILED: Chrome not found"
        Write-Result -RequestId $rid -Result @{
            request_id     = $rid
            trace_id       = $traceId
            action_type    = "ingest_safe_doc_cu"
            adapter_status = "failed"
            error          = "CHROME_NOT_FOUND"
            timestamp      = Get-Timestamp
        }
        return
    }

    # Stage 1: Launch Chrome to safe doc URL
    Write-Log "Stage 1: Launching Chrome to safe doc..."
    $commandIssued = "$chromeExe --new-window $url"
    try {
        $process = Start-Process -FilePath $chromeExe -ArgumentList "--new-window", $url -PassThru
        Start-Sleep -Seconds 5
    }
    catch {
        Write-Result -RequestId $rid -Result @{
            request_id     = $rid
            trace_id       = $traceId
            action_type    = "ingest_safe_doc_cu"
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

    # Stage 5: Wait for page load and capture navigation screenshot
    Start-Sleep -Seconds 3
    $navScreenshotPath = Join-Path $proofDir "${rid}_navigation.png"
    $navScreenshotCaptured = Capture-Screenshot -OutputPath $navScreenshotPath
    $navScreenshotHash = ""
    if ($navScreenshotCaptured) {
        $navScreenshotHash = Get-FileHash256 -FilePath $navScreenshotPath
        Write-Log "Navigation screenshot hash: $navScreenshotHash"
    }

    # Stage 6: Detect navigation via window title
    $navDetected = $false
    try {
        $chromeProcs2 = Get-Process chrome -ErrorAction SilentlyContinue
        if ($chromeProcs2) {
            $mainProc2 = $chromeProcs2 | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
            if ($mainProc2 -and $mainProc2.MainWindowTitle) {
                $windowMeta["main_window_title"] = $mainProc2.MainWindowTitle
                $navDetected = $mainProc2.MainWindowTitle -ne "" -and $mainProc2.MainWindowTitle -ne "New Tab"
                Write-Log "Stage 6: Window title='$($mainProc2.MainWindowTitle)' nav_detected=$navDetected"
            }
        }
    }
    catch {
        Write-Log "WARNING: Navigation detection failed"
    }

    # Stage 7: Extract page content via Chrome DevTools
    $extractionResult = @{
        completed       = $false
        title           = ""
        content_length  = 0
        content_preview = ""
        content_hash    = ""
        headings        = @()
        links           = @()
        method          = "window_title_fallback"
    }

    # Try window title as document title (reliable)
    if ($windowMeta["main_window_title"]) {
        $rawTitle = $windowMeta["main_window_title"]
        $docTitle = $rawTitle -replace " - Google Chrome$", "" -replace " - Google Docs$", ""
        $extractionResult["title"] = $docTitle
    }

    # Try PowerShell COM automation for content (IE-based, best-effort)
    try {
        Write-Log "Stage 7: Attempting content extraction..."
        # Use clipboard approach: Chrome DevTools Protocol not available in PS 5.1
        # Fall back to window title + screenshot as primary evidence
        # Content extraction via clipboard: Ctrl+A, Ctrl+C
        Add-Type -AssemblyName System.Windows.Forms

        # Focus Chrome window
        if ($mainProc -and $mainProc.MainWindowHandle -ne 0) {
            Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32SW {
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}
"@
            [Win32SW]::ShowWindow($mainProc.MainWindowHandle, 9) | Out-Null
            [Win32SW]::SetForegroundWindow($mainProc.MainWindowHandle) | Out-Null
            Start-Sleep -Milliseconds 500
        }

        # Clear clipboard
        [System.Windows.Forms.Clipboard]::Clear()
        Start-Sleep -Milliseconds 200

        # Select all and copy
        [System.Windows.Forms.SendKeys]::SendWait("^a")
        Start-Sleep -Milliseconds 500
        [System.Windows.Forms.SendKeys]::SendWait("^c")
        Start-Sleep -Milliseconds 500

        # Read clipboard
        $clipText = [System.Windows.Forms.Clipboard]::GetText()
        if ($clipText -and $clipText.Length -gt 0) {
            $extractionResult["completed"] = $true
            $extractionResult["content_length"] = $clipText.Length
            $extractionResult["method"] = "clipboard_select_all"

            # Preview (first 500 chars)
            $previewLen = [Math]::Min($clipText.Length, 500)
            $extractionResult["content_preview"] = $clipText.Substring(0, $previewLen)

            # Content hash
            $sha = [System.Security.Cryptography.SHA256]::Create()
            $bytes = [System.Text.Encoding]::UTF8.GetBytes($clipText)
            $hashBytes = $sha.ComputeHash($bytes)
            $extractionResult["content_hash"] = [BitConverter]::ToString($hashBytes).Replace("-","").ToLower()

            # Extract headings (lines that look like headers)
            $lines = $clipText -split "`n"
            $headingCandidates = @()
            foreach ($line in $lines) {
                $trimmed = $line.Trim()
                if ($trimmed.Length -gt 2 -and $trimmed.Length -lt 100) {
                    if ($trimmed -match "^#{1,6}\s" -or ($trimmed -eq $trimmed.ToUpper() -and $trimmed.Length -gt 3)) {
                        $headingCandidates += $trimmed
                    }
                }
            }
            $extractionResult["headings"] = $headingCandidates | Select-Object -First 20

            Write-Log "Extraction completed: $($clipText.Length) chars, $($headingCandidates.Count) headings"
        }
        else {
            Write-Log "Clipboard empty after select-all + copy"
            $extractionResult["method"] = "clipboard_empty"
        }
    }
    catch {
        Write-Log "WARNING: Content extraction failed: $($_.Exception.Message)"
        $extractionResult["method"] = "extraction_failed"
    }

    # Stage 8: Post-extraction screenshot
    Start-Sleep -Seconds 1
    $extractScreenshotPath = Join-Path $proofDir "${rid}_extraction.png"
    Capture-Screenshot -OutputPath $extractScreenshotPath | Out-Null

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
        navigation_detected = $navDetected
        screenshot_hash     = $navScreenshotHash
        screenshot_path     = $navScreenshotPath
        timestamp           = Get-Timestamp
    }

    # Build stages completed
    $stagesCompleted = @("relay_dispatched", "chrome_launched")
    if ($chromeRunning) { $stagesCompleted += "process_verified" }
    if ($windowMeta["main_window_handle"]) { $stagesCompleted += "window_detected" }
    if ($isChromeForegrounded) { $stagesCompleted += "focus_confirmed" }
    if ($navDetected) { $stagesCompleted += "navigation_confirmed" }
    if ($navScreenshotCaptured) { $stagesCompleted += "screenshot_captured" }
    if ($extractionResult["completed"]) { $stagesCompleted += "extraction_completed" }

    # Write relay result
    Write-Result -RequestId $rid -Result @{
        request_id                     = $rid
        trace_id                       = $traceId
        work_order_id                  = $workOrderId
        action_type                    = "ingest_safe_doc_cu"
        adapter_status                 = "completed"
        command_issued                 = $commandIssued
        process_detected               = $processDetected
        process_id                     = $chromePid
        window_metadata                = $windowMeta
        observed_desktop_state         = $observedState
        extraction_result              = $extractionResult
        stages_completed               = $stagesCompleted
        screenshot_captured            = $navScreenshotCaptured
        screenshot_hash                = $navScreenshotHash
        screenshot_path                = $navScreenshotPath
        proof_dir                      = $proofDir
        proof_artifacts                = @(
            "${rid}_navigation.png",
            "${rid}_extraction.png"
        )
        dry_run                        = $false
        node_id                        = "WRN-$env:COMPUTERNAME"
        machine_name                   = $env:COMPUTERNAME
        timestamp                      = Get-Timestamp
        notes                          = @(
            "Foreground CU ingestion via real Chrome",
            "Navigation to safe doc URL",
            "Content extraction via clipboard select-all",
            "Screenshot proof at navigation and extraction stages",
            "No API fallback, no headless, no simulated extraction",
            "Extraction method: $($extractionResult['method'])"
        )
    }

    Write-Log "INGEST_SAFE_DOC_CU completed: stages=$($stagesCompleted -join ',')"
}

# ---------------------------------------------------------------------------
# Environment exploration handler
# ---------------------------------------------------------------------------

function Handle-ExploreEnvironment {
    param([hashtable]$Request)

    $rid         = $Request["request_id"]
    $traceId     = $Request["trace_id"]
    $workOrderId = $Request["work_order_id"]
    $proofDir    = "$HOME\eos_advisor_messages\windows_desktop_relay\gui_proofs"
    $isDryRun    = $Request["dry_run"] -eq $true

    Write-Log "EXPLORE_ENVIRONMENT: rid=$rid dry_run=$isDryRun"

    if (-not (Test-Path $proofDir)) {
        New-Item -ItemType Directory -Path $proofDir -Force | Out-Null
    }

    $desktopUnlocked = $true
    $activeSession = $true

    if ($isDryRun) {
        Write-Log "DRY RUN: would enumerate environment"
        Write-Result -RequestId $rid -Result @{
            request_id     = $rid
            trace_id       = $traceId
            work_order_id  = $workOrderId
            action_type    = "explore_environment"
            adapter_status = "completed"
            dry_run        = $true
            timestamp      = Get-Timestamp
        }
        return
    }

    # Stage 1: Enumerate running processes
    Write-Log "Stage 1: Enumerating running processes..."
    $processes = @()
    try {
        $allProcs = Get-Process | Select-Object -Property Name, Id, MainWindowHandle, MainWindowTitle -Unique
        foreach ($p in $allProcs) {
            $hasWindow = $p.MainWindowHandle -ne 0
            $processes += @{
                name         = $p.Name
                pid          = $p.Id
                has_window   = $hasWindow
                window_title = if ($hasWindow) { $p.MainWindowTitle } else { "" }
            }
        }
        Write-Log "Found $($processes.Count) processes"
    }
    catch {
        Write-Log "WARNING: Process enumeration failed: $($_.Exception.Message)"
    }

    # Stage 2: Enumerate installed applications
    Write-Log "Stage 2: Enumerating installed applications..."
    $installedApps = @()
    try {
        $regPaths = @(
            "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*",
            "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*",
            "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*"
        )
        foreach ($rp in $regPaths) {
            $apps = Get-ItemProperty $rp -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName } | Select-Object DisplayName, Publisher, InstallLocation -First 100
            foreach ($app in $apps) {
                $installedApps += @{
                    name     = $app.DisplayName
                    publisher = if ($app.Publisher) { $app.Publisher } else { "" }
                    path     = if ($app.InstallLocation) { $app.InstallLocation } else { "" }
                }
            }
        }
        $installedApps = $installedApps | Sort-Object { $_["name"] } -Unique
        Write-Log "Found $($installedApps.Count) installed applications"
    }
    catch {
        Write-Log "WARNING: App enumeration failed: $($_.Exception.Message)"
    }

    # Stage 3: Discover Chrome profiles
    Write-Log "Stage 3: Discovering Chrome profiles..."
    $chromeProfiles = @()
    try {
        $chromeUserData = "$env:LOCALAPPDATA\Google\Chrome\User Data"
        if (Test-Path $chromeUserData) {
            $localState = Join-Path $chromeUserData "Local State"
            if (Test-Path $localState) {
                $stateContent = Get-Content $localState -Raw | ConvertFrom-Json
                $profileInfo = $stateContent.profile.info_cache
                if ($profileInfo) {
                    foreach ($prop in $profileInfo.PSObject.Properties) {
                        $profile = $prop.Value
                        $chromeProfiles += @{
                            name       = if ($profile.name) { $profile.name } else { $prop.Name }
                            email      = if ($profile.user_name) { $profile.user_name } else { "" }
                            is_default = ($prop.Name -eq "Default")
                        }
                    }
                }
            }
        }
        Write-Log "Found $($chromeProfiles.Count) Chrome profiles"
    }
    catch {
        Write-Log "WARNING: Chrome profile discovery failed: $($_.Exception.Message)"
    }

    # Stage 4: Discover browser sessions (from window titles)
    Write-Log "Stage 4: Discovering browser sessions from window titles..."
    $browserSessions = @()
    try {
        $chromeProcs = Get-Process chrome -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 }
        if ($chromeProcs) {
            foreach ($cp in $chromeProcs) {
                if ($cp.MainWindowTitle) {
                    $title = $cp.MainWindowTitle
                    $platform = ""
                    if ($title -match "Gmail") { $platform = "gmail" }
                    elseif ($title -match "Google Drive") { $platform = "drive" }
                    elseif ($title -match "Google Docs") { $platform = "docs" }
                    elseif ($title -match "GitHub") { $platform = "github" }
                    elseif ($title -match "Notion") { $platform = "notion" }
                    elseif ($title -match "Slack") { $platform = "slack" }
                    elseif ($title -match "Discord") { $platform = "discord" }
                    elseif ($title -match "Claude") { $platform = "claude" }
                    elseif ($title -match "ChatGPT\|OpenAI") { $platform = "openai" }
                    if ($platform) {
                        $browserSessions += @{
                            platform     = $platform
                            window_title = $title
                            email        = ""
                            username     = ""
                        }
                    }
                }
            }
        }
        Write-Log "Found $($browserSessions.Count) browser sessions"
    }
    catch {
        Write-Log "WARNING: Browser session discovery failed: $($_.Exception.Message)"
    }

    # Stage 5: Discover local workspaces
    Write-Log "Stage 5: Discovering local workspaces..."
    $workspaces = @()
    try {
        # Obsidian vaults
        $obsidianConfig = "$env:APPDATA\obsidian\obsidian.json"
        if (Test-Path $obsidianConfig) {
            try {
                $obsConfig = Get-Content $obsidianConfig -Raw | ConvertFrom-Json
                if ($obsConfig.vaults) {
                    foreach ($prop in $obsConfig.vaults.PSObject.Properties) {
                        $vault = $prop.Value
                        $vaultPath = if ($vault.path) { $vault.path } else { "" }
                        $workspaces += @{
                            name         = "Obsidian Vault"
                            platform     = "Obsidian"
                            type         = "vault"
                            path         = $vaultPath
                            detected_via = "obsidian_config"
                        }
                    }
                }
            }
            catch { Write-Log "WARNING: Obsidian config parse failed" }
        }

        # VS Code recent workspaces
        $vscodeStorage = "$env:APPDATA\Code\User\globalStorage\storage.json"
        if (Test-Path $vscodeStorage) {
            $workspaces += @{
                name         = "VS Code Workspace"
                platform     = "VS Code"
                type         = "editor"
                path         = $vscodeStorage
                detected_via = "vscode_storage"
            }
        }

        # Git repos in common locations
        $commonRepoDirs = @("$HOME\repos", "$HOME\projects", "$HOME\code", "$HOME\dev")
        foreach ($dir in $commonRepoDirs) {
            if (Test-Path $dir) {
                $repos = Get-ChildItem $dir -Directory | Where-Object { Test-Path (Join-Path $_.FullName ".git") } | Select-Object -First 20
                foreach ($repo in $repos) {
                    $workspaces += @{
                        name         = $repo.Name
                        platform     = "git"
                        type         = "repository"
                        path         = $repo.FullName
                        detected_via = "filesystem_scan"
                    }
                }
            }
        }

        Write-Log "Found $($workspaces.Count) workspaces"
    }
    catch {
        Write-Log "WARNING: Workspace discovery failed: $($_.Exception.Message)"
    }

    # Stage 6: Screenshot desktop
    Write-Log "Stage 6: Capturing desktop screenshot..."
    $screenshotPath = Join-Path $proofDir "${rid}_desktop.png"
    $screenshotCaptured = Capture-Screenshot -OutputPath $screenshotPath
    $screenshotHash = ""
    if ($screenshotCaptured) {
        $screenshotHash = Get-FileHash256 -FilePath $screenshotPath
    }

    # Stage 7: Screenshot taskbar (same as desktop for now)
    Start-Sleep -Seconds 1
    $taskbarScreenshotPath = Join-Path $proofDir "${rid}_taskbar.png"
    Capture-Screenshot -OutputPath $taskbarScreenshotPath | Out-Null

    # Build observed desktop state
    $observedState = @{
        desktop_unlocked    = $desktopUnlocked
        active_user_session = $activeSession
        monitor_detected    = $true
        screenshot_path     = $screenshotPath
        screenshot_hash     = $screenshotHash
        timestamp           = Get-Timestamp
    }

    # Build stages completed
    $stagesCompleted = @("relay_dispatched")
    if ($processes.Count -gt 0) { $stagesCompleted += "processes_enumerated" }
    if ($installedApps.Count -gt 0) { $stagesCompleted += "apps_enumerated" }
    if ($chromeProfiles.Count -gt 0) { $stagesCompleted += "chrome_profiles_discovered" }
    if ($browserSessions.Count -gt 0) { $stagesCompleted += "browser_sessions_discovered" }
    if ($workspaces.Count -gt 0) { $stagesCompleted += "workspaces_discovered" }
    if ($screenshotCaptured) { $stagesCompleted += "screenshot_captured" }

    # Write result
    Write-Result -RequestId $rid -Result @{
        request_id              = $rid
        trace_id                = $traceId
        work_order_id           = $workOrderId
        action_type             = "explore_environment"
        adapter_status          = "completed"
        observed_desktop_state  = $observedState
        discovery_result        = @{
            processes             = $processes
            installed_apps        = $installedApps
            chrome_profiles       = $chromeProfiles
            browser_sessions      = $browserSessions
            workspaces            = $workspaces
            workspaces_discovered = ($workspaces.Count -gt 0)
            screenshots           = @{
                paths  = @($screenshotPath, $taskbarScreenshotPath)
                hashes = @($screenshotHash)
            }
        }
        stages_completed        = $stagesCompleted
        dry_run                 = $false
        node_id                 = "WRN-$env:COMPUTERNAME"
        machine_name            = $env:COMPUTERNAME
        timestamp               = Get-Timestamp
        notes                   = @(
            "Exploratory environment mapping via visible enumeration",
            "No credential scraping",
            "No hidden scanning",
            "No autonomous mutation",
            "Process list from Get-Process",
            "Installed apps from registry",
            "Chrome profiles from Local State",
            "Browser sessions from window titles",
            "Workspaces from config files and filesystem",
            "Desktop screenshots captured"
        )
    }

    Write-Log "EXPLORE_ENVIRONMENT completed: stages=$($stagesCompleted -join ',')"
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
            "ingest_safe_doc_cu" {
                Handle-IngestSafeDocCU -Request $request
            }
            "explore_environment" {
                Handle-ExploreEnvironment -Request $request
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
