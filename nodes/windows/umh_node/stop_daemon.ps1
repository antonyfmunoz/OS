<#
.SYNOPSIS
    Governed stop helper for the UMH Node Daemon scheduled task.

.DESCRIPTION
    Signals the daemon's named shutdown event first so the node can close the
    mesh connection and flush logs. If the bounded graceful window expires, it
    asks Task Scheduler to end the task. The task-owned supervisor's Job Object
    then removes only the governed wrapper/launcher/descendant tree.
#>

param(
    [string]$TaskName = "UMH Node Daemon",
    [string]$StopEventName = "Global\UMHNodeDaemonStop",
    [int]$GraceSeconds = 20
)

$ErrorActionPreference = "Stop"

function Get-UMHLauncher {
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.Name -match '^pythonw?\.exe$' -and
            $_.CommandLine -match 'nodes\\windows\\umh_node\\launcher\.py'
        }
}

$native = @"
using System;
using System.Runtime.InteropServices;

public static class UMHStopNative {
  [DllImport("kernel32.dll", CharSet = CharSet.Unicode)]
  public static extern IntPtr OpenEvent(UInt32 dwDesiredAccess, bool bInheritHandle, string lpName);

  [DllImport("kernel32.dll")]
  public static extern bool SetEvent(IntPtr hEvent);

  [DllImport("kernel32.dll")]
  public static extern bool CloseHandle(IntPtr hObject);
}
"@

Add-Type -TypeDefinition $native

$before = @(Get-UMHLauncher)
$EVENT_MODIFY_STATE = 0x0002
$event = [UMHStopNative]::OpenEvent($EVENT_MODIFY_STATE, $false, $StopEventName)
$eventSignaled = $false
if ($event -ne [IntPtr]::Zero) {
    $eventSignaled = [UMHStopNative]::SetEvent($event)
    [void][UMHStopNative]::CloseHandle($event)
}

$deadline = (Get-Date).AddSeconds($GraceSeconds)
do {
    Start-Sleep -Milliseconds 500
    $remaining = @(Get-UMHLauncher)
    if ($remaining.Count -eq 0) {
        break
    }
} while ((Get-Date) -lt $deadline)

$afterGrace = @(Get-UMHLauncher)
$endedTask = $false
if ($afterGrace.Count -gt 0) {
    schtasks /End /TN $TaskName | Out-Null
    $endedTask = $true
    $deadline = (Get-Date).AddSeconds(15)
    do {
        Start-Sleep -Milliseconds 500
        $remaining = @(Get-UMHLauncher)
        if ($remaining.Count -eq 0) {
            break
        }
    } while ((Get-Date) -lt $deadline)
}

$final = @(Get-UMHLauncher)
[pscustomobject]@{
    ok = ($final.Count -eq 0)
    event_signaled = $eventSignaled
    task_end_requested = $endedTask
    before_launcher_pids = @($before | ForEach-Object { $_.ProcessId })
    final_launcher_pids = @($final | ForEach-Object { $_.ProcessId })
} | ConvertTo-Json -Compress

if ($final.Count -ne 0) {
    exit 2
}
