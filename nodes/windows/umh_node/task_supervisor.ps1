<#
.SYNOPSIS
    Task-owned supervisor for the UMH Node Daemon scheduled task.

.DESCRIPTION
    Task Scheduler must own a persistent process, not the transient 1Password
    wrapper. This supervisor starts:

        op.exe run --env-file=<tpl> -- pythonw.exe <repo>\nodes\windows\umh_node\launcher.py

    inside a Windows Job Object with KILL_ON_JOB_CLOSE. If Task Scheduler ends
    the supervisor directly, Windows closes the job handle and removes the
    wrapper, launcher and descendants instead of orphaning pythonw.exe.
#>

param(
    [string]$RepoPath = "C:\dev\dev\OS",
    [string]$EnvTemplate = "C:\ProgramData\UMH\.env.op.tpl",
    [string]$TaskName = "UMH Node Daemon",
    [string]$StopEventName = "Global\UMHNodeDaemonStop"
)

$ErrorActionPreference = "Stop"

$runtimeRoot = Join-Path $env:ProgramData "UMH"
$runRoot = Join-Path $runtimeRoot "run"
$logRoot = Join-Path $runtimeRoot "logs"
New-Item -ItemType Directory -Force -Path $runRoot, $logRoot | Out-Null

$launcher = Join-Path $RepoPath "nodes\windows\umh_node\launcher.py"
if (-not (Test-Path -LiteralPath $launcher)) {
    throw "launcher not found: $launcher"
}
if (-not (Test-Path -LiteralPath $EnvTemplate)) {
    throw "1Password environment template not found: $EnvTemplate"
}

$op = (Get-Command "op.exe" -ErrorAction Stop).Source
$pythonw = (Get-Command "pythonw.exe" -ErrorAction Stop).Source

function Quote-Arg([string]$Value) {
    if ($Value -notmatch '[\s"]') {
        return $Value
    }
    return '"' + ($Value -replace '"', '\"') + '"'
}

$native = @"
using System;
using System.Runtime.InteropServices;

public static class UMHJobNative {
  [StructLayout(LayoutKind.Sequential)]
  public struct IO_COUNTERS {
    public UInt64 ReadOperationCount;
    public UInt64 WriteOperationCount;
    public UInt64 OtherOperationCount;
    public UInt64 ReadTransferCount;
    public UInt64 WriteTransferCount;
    public UInt64 OtherTransferCount;
  }

  [StructLayout(LayoutKind.Sequential)]
  public struct JOBOBJECT_BASIC_LIMIT_INFORMATION {
    public Int64 PerProcessUserTimeLimit;
    public Int64 PerJobUserTimeLimit;
    public UInt32 LimitFlags;
    public UIntPtr MinimumWorkingSetSize;
    public UIntPtr MaximumWorkingSetSize;
    public UInt32 ActiveProcessLimit;
    public UIntPtr Affinity;
    public UInt32 PriorityClass;
    public UInt32 SchedulingClass;
  }

  [StructLayout(LayoutKind.Sequential)]
  public struct JOBOBJECT_EXTENDED_LIMIT_INFORMATION {
    public JOBOBJECT_BASIC_LIMIT_INFORMATION BasicLimitInformation;
    public IO_COUNTERS IoInfo;
    public UIntPtr ProcessMemoryLimit;
    public UIntPtr JobMemoryLimit;
    public UIntPtr PeakProcessMemoryUsed;
    public UIntPtr PeakJobMemoryUsed;
  }

  [DllImport("kernel32.dll", CharSet = CharSet.Unicode)]
  public static extern IntPtr CreateJobObject(IntPtr lpJobAttributes, string lpName);

  [DllImport("kernel32.dll")]
  public static extern bool SetInformationJobObject(
    IntPtr hJob,
    int JobObjectInfoClass,
    IntPtr lpJobObjectInfo,
    uint cbJobObjectInfoLength);

  [DllImport("kernel32.dll")]
  public static extern bool AssignProcessToJobObject(IntPtr hJob, IntPtr hProcess);

  [DllImport("kernel32.dll", CharSet = CharSet.Unicode)]
  public static extern IntPtr CreateEvent(IntPtr lpEventAttributes, bool bManualReset, bool bInitialState, string lpName);

  [DllImport("kernel32.dll")]
  public static extern bool ResetEvent(IntPtr hEvent);

  [DllImport("kernel32.dll")]
  public static extern bool CloseHandle(IntPtr hObject);
}
"@

Add-Type -TypeDefinition $native

$JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
$JobObjectExtendedLimitInformation = 9

$job = [UMHJobNative]::CreateJobObject([IntPtr]::Zero, "UMHNodeDaemon-$PID")
if ($job -eq [IntPtr]::Zero) {
    throw "CreateJobObject failed"
}

$stopEvent = [UMHJobNative]::CreateEvent([IntPtr]::Zero, $true, $false, $StopEventName)
if ($stopEvent -eq [IntPtr]::Zero) {
    throw "CreateEvent failed"
}
[void][UMHJobNative]::ResetEvent($stopEvent)

$limits = New-Object UMHJobNative+JOBOBJECT_EXTENDED_LIMIT_INFORMATION
$limits.BasicLimitInformation.LimitFlags = $JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
$size = [Runtime.InteropServices.Marshal]::SizeOf($limits)
$ptr = [Runtime.InteropServices.Marshal]::AllocHGlobal($size)

try {
    [Runtime.InteropServices.Marshal]::StructureToPtr($limits, $ptr, $false)
    if (-not [UMHJobNative]::SetInformationJobObject($job, $JobObjectExtendedLimitInformation, $ptr, [uint32]$size)) {
        throw "SetInformationJobObject(KILL_ON_JOB_CLOSE) failed"
    }

    Set-Location -LiteralPath $runRoot
    $env:UMH_DAEMON_STOP_EVENT = $StopEventName

    $args = @("run", "--env-file=$EnvTemplate", "--", $pythonw, $launcher) |
        ForEach-Object { Quote-Arg $_ }
    $proc = Start-Process -FilePath $op -ArgumentList ($args -join " ") -WorkingDirectory $runRoot -WindowStyle Hidden -PassThru
    if (-not [UMHJobNative]::AssignProcessToJobObject($job, $proc.Handle)) {
        try { $proc.Kill() } catch {}
        throw "AssignProcessToJobObject failed for op.exe pid=$($proc.Id)"
    }

    $stamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
    @{
        task = $TaskName
        supervisor_pid = $PID
        op_pid = $proc.Id
        repo_path = $RepoPath
        launcher = $launcher
        env_template = $EnvTemplate
        stop_event = $StopEventName
        started_at = $stamp
    } | ConvertTo-Json -Depth 3 -Compress | Set-Content -Path (Join-Path $runRoot "umh-node-supervisor.json") -Encoding UTF8

    $proc.WaitForExit()
    exit $proc.ExitCode
}
finally {
    if ($ptr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::FreeHGlobal($ptr)
    }
    if ($stopEvent -ne [IntPtr]::Zero) {
        [void][UMHJobNative]::CloseHandle($stopEvent)
    }
    if ($job -ne [IntPtr]::Zero) {
        [void][UMHJobNative]::CloseHandle($job)
    }
}
