<#
.SYNOPSIS
    Task-owned supervisor for the UMH Node Daemon scheduled task.

.DESCRIPTION
    Task Scheduler must own a persistent process, not the transient 1Password
    wrapper. This supervisor starts:

        op.exe run --env-file=<tpl> -- powershell.exe -File <repo>\nodes\windows\umh_node\daemon_child.ps1

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
$childSupervisor = Join-Path $RepoPath "nodes\windows\umh_node\daemon_child.ps1"
if (-not (Test-Path -LiteralPath $launcher)) {
    throw "launcher not found: $launcher"
}
if (-not (Test-Path -LiteralPath $childSupervisor)) {
    throw "daemon child supervisor not found: $childSupervisor"
}
if (-not (Test-Path -LiteralPath $EnvTemplate)) {
    throw "1Password environment template not found: $EnvTemplate"
}

$op = (Get-Command "op.exe" -ErrorAction Stop).Source

function Quote-Arg([string]$Value) {
    if ($Value -notmatch '[\s"]') {
        return $Value
    }
    return '"' + ($Value -replace '"', '\"') + '"'
}

function Resolve-RealPythonw {
    $candidates = @()
    if ($env:UMH_PYTHONW_PATH) {
        $candidates += $env:UMH_PYTHONW_PATH
    }
    $coreRoot = Join-Path $env:LOCALAPPDATA "Python"
    if (Test-Path -LiteralPath $coreRoot) {
        $candidates += @(
            Get-ChildItem -LiteralPath $coreRoot -Filter "pythonw.exe" -Recurse -File -ErrorAction SilentlyContinue |
                Where-Object { $_.FullName -notmatch "\\WindowsApps\\" } |
                Sort-Object FullName -Descending |
                ForEach-Object { $_.FullName }
        )
    }
    $cmd = Get-Command "pythonw.exe" -ErrorAction SilentlyContinue
    if ($cmd) {
        $candidates += $cmd.Source
    }

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate) -and $candidate -notmatch "\\WindowsApps\\") {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }
    throw "no real pythonw.exe found outside WindowsApps; set UMH_PYTHONW_PATH"
}

$pythonw = Resolve-RealPythonw

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

  [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
  public struct STARTUPINFO {
    public UInt32 cb;
    public string lpReserved;
    public string lpDesktop;
    public string lpTitle;
    public UInt32 dwX;
    public UInt32 dwY;
    public UInt32 dwXSize;
    public UInt32 dwYSize;
    public UInt32 dwXCountChars;
    public UInt32 dwYCountChars;
    public UInt32 dwFillAttribute;
    public UInt32 dwFlags;
    public UInt16 wShowWindow;
    public UInt16 cbReserved2;
    public IntPtr lpReserved2;
    public IntPtr hStdInput;
    public IntPtr hStdOutput;
    public IntPtr hStdError;
  }

  [StructLayout(LayoutKind.Sequential)]
  public struct PROCESS_INFORMATION {
    public IntPtr hProcess;
    public IntPtr hThread;
    public UInt32 dwProcessId;
    public UInt32 dwThreadId;
  }

  [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
  public static extern IntPtr CreateJobObject(IntPtr lpJobAttributes, string lpName);

  [DllImport("kernel32.dll", SetLastError = true)]
  public static extern bool SetInformationJobObject(
    IntPtr hJob,
    int JobObjectInfoClass,
    IntPtr lpJobObjectInfo,
    uint cbJobObjectInfoLength);

  [DllImport("kernel32.dll", SetLastError = true)]
  public static extern bool QueryInformationJobObject(
    IntPtr hJob,
    int JobObjectInfoClass,
    IntPtr lpJobObjectInfo,
    uint cbJobObjectInfoLength,
    out uint lpReturnLength);

  [DllImport("kernel32.dll", SetLastError = true)]
  public static extern bool AssignProcessToJobObject(IntPtr hJob, IntPtr hProcess);

  [DllImport("kernel32.dll", SetLastError = true)]
  public static extern bool IsProcessInJob(IntPtr ProcessHandle, IntPtr JobHandle, out bool Result);

  [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
  public static extern bool CreateProcess(
    string lpApplicationName,
    string lpCommandLine,
    IntPtr lpProcessAttributes,
    IntPtr lpThreadAttributes,
    bool bInheritHandles,
    UInt32 dwCreationFlags,
    IntPtr lpEnvironment,
    string lpCurrentDirectory,
    ref STARTUPINFO lpStartupInfo,
    out PROCESS_INFORMATION lpProcessInformation);

  [DllImport("kernel32.dll", SetLastError = true)]
  public static extern UInt32 ResumeThread(IntPtr hThread);

  [DllImport("kernel32.dll", SetLastError = true)]
  public static extern UInt32 WaitForSingleObject(IntPtr hHandle, UInt32 dwMilliseconds);

  [DllImport("kernel32.dll", SetLastError = true)]
  public static extern bool GetExitCodeProcess(IntPtr hProcess, out UInt32 lpExitCode);

  [DllImport("kernel32.dll", SetLastError = true)]
  public static extern IntPtr OpenProcess(UInt32 dwDesiredAccess, bool bInheritHandle, UInt32 dwProcessId);

  [DllImport("kernel32.dll", SetLastError = true)]
  public static extern bool TerminateJobObject(IntPtr hJob, UInt32 uExitCode);

  [DllImport("kernel32.dll", SetLastError = true)]
  public static extern bool SetHandleInformation(IntPtr hObject, UInt32 dwMask, UInt32 dwFlags);

  [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
  public static extern IntPtr CreateEvent(IntPtr lpEventAttributes, bool bManualReset, bool bInitialState, string lpName);

  [DllImport("kernel32.dll", SetLastError = true)]
  public static extern bool ResetEvent(IntPtr hEvent);

  [DllImport("kernel32.dll", SetLastError = true)]
  public static extern bool CloseHandle(IntPtr hObject);
}
"@

Add-Type -TypeDefinition $native

$JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
$JobObjectExtendedLimitInformation = 9
$CREATE_SUSPENDED = 0x00000004
$CREATE_NO_WINDOW = 0x08000000
$HANDLE_FLAG_INHERIT = 0x00000001
$PROCESS_QUERY_LIMITED_INFORMATION = 0x00001000
$SYNCHRONIZE = 0x00100000
$INFINITE = 0xFFFFFFFF

$job = [UMHJobNative]::CreateJobObject([IntPtr]::Zero, "UMHNodeDaemon-$PID")
if ($job -eq [IntPtr]::Zero) {
    throw "CreateJobObject failed win32=$([Runtime.InteropServices.Marshal]::GetLastWin32Error())"
}
if (-not [UMHJobNative]::SetHandleInformation($job, $HANDLE_FLAG_INHERIT, 0)) {
    throw "SetHandleInformation(job, non-inheritable) failed win32=$([Runtime.InteropServices.Marshal]::GetLastWin32Error())"
}

$stopEvent = [UMHJobNative]::CreateEvent([IntPtr]::Zero, $true, $false, $StopEventName)
if ($stopEvent -eq [IntPtr]::Zero) {
    throw "CreateEvent failed win32=$([Runtime.InteropServices.Marshal]::GetLastWin32Error())"
}
if (-not [UMHJobNative]::SetHandleInformation($stopEvent, $HANDLE_FLAG_INHERIT, 0)) {
    throw "SetHandleInformation(stopEvent, non-inheritable) failed win32=$([Runtime.InteropServices.Marshal]::GetLastWin32Error())"
}
[void][UMHJobNative]::ResetEvent($stopEvent)

$limits = New-Object UMHJobNative+JOBOBJECT_EXTENDED_LIMIT_INFORMATION
$basicLimits = New-Object UMHJobNative+JOBOBJECT_BASIC_LIMIT_INFORMATION
$basicLimits.LimitFlags = $JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
$limits.BasicLimitInformation = $basicLimits
$size = [Runtime.InteropServices.Marshal]::SizeOf($limits)
$ptr = [Runtime.InteropServices.Marshal]::AllocHGlobal($size)
$launcherWaitHandle = [IntPtr]::Zero

try {
    [Runtime.InteropServices.Marshal]::StructureToPtr($limits, $ptr, $false)
    if (-not [UMHJobNative]::SetInformationJobObject($job, $JobObjectExtendedLimitInformation, $ptr, [uint32]$size)) {
        throw "SetInformationJobObject(KILL_ON_JOB_CLOSE) failed win32=$([Runtime.InteropServices.Marshal]::GetLastWin32Error())"
    }
    $verifyPtr = [Runtime.InteropServices.Marshal]::AllocHGlobal($size)
    try {
        $returned = [uint32]0
        if (-not [UMHJobNative]::QueryInformationJobObject($job, $JobObjectExtendedLimitInformation, $verifyPtr, [uint32]$size, [ref]$returned)) {
            throw "QueryInformationJobObject(limits) failed win32=$([Runtime.InteropServices.Marshal]::GetLastWin32Error())"
        }
        $verifiedLimits = [Runtime.InteropServices.Marshal]::PtrToStructure($verifyPtr, [type][UMHJobNative+JOBOBJECT_EXTENDED_LIMIT_INFORMATION])
        if (($verifiedLimits.BasicLimitInformation.LimitFlags -band $JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE) -eq 0) {
            throw "Job limit verification failed: KILL_ON_JOB_CLOSE not active"
        }
    }
    finally {
        if ($verifyPtr -ne [IntPtr]::Zero) {
            [Runtime.InteropServices.Marshal]::FreeHGlobal($verifyPtr)
        }
    }

    Set-Location -LiteralPath $runRoot
    $env:UMH_DAEMON_STOP_EVENT = $StopEventName
    $env:UMH_DAEMON_SUPERVISOR_PID = "$PID"

    $args = @(
        $op,
        "run",
        "--env-file=$EnvTemplate",
        "--",
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        $childSupervisor,
        "-RepoPath",
        $RepoPath,
        "-StopEventName",
        $StopEventName
    ) |
        ForEach-Object { Quote-Arg $_ }
    $commandLine = $args -join " "
    $startup = New-Object UMHJobNative+STARTUPINFO
    $startup.cb = [Runtime.InteropServices.Marshal]::SizeOf([type][UMHJobNative+STARTUPINFO])
    $procInfo = New-Object UMHJobNative+PROCESS_INFORMATION

    if (-not [UMHJobNative]::CreateProcess($op, $commandLine, [IntPtr]::Zero, [IntPtr]::Zero, $false, ($CREATE_SUSPENDED -bor $CREATE_NO_WINDOW), [IntPtr]::Zero, $runRoot, [ref]$startup, [ref]$procInfo)) {
        throw "CreateProcess(op.exe suspended) failed win32=$([Runtime.InteropServices.Marshal]::GetLastWin32Error())"
    }

    $childAssigned = $false
    try {
        if (-not [UMHJobNative]::AssignProcessToJobObject($job, $procInfo.hProcess)) {
            [void][UMHJobNative]::TerminateJobObject($job, 2)
            throw "AssignProcessToJobObject failed for suspended op.exe pid=$($procInfo.dwProcessId) win32=$([Runtime.InteropServices.Marshal]::GetLastWin32Error())"
        }
        $inJob = $false
        if (-not [UMHJobNative]::IsProcessInJob($procInfo.hProcess, $job, [ref]$inJob)) {
            [void][UMHJobNative]::TerminateJobObject($job, 2)
            throw "IsProcessInJob(op.exe) failed win32=$([Runtime.InteropServices.Marshal]::GetLastWin32Error())"
        }
        if (-not $inJob) {
            [void][UMHJobNative]::TerminateJobObject($job, 2)
            throw "op.exe pid=$($procInfo.dwProcessId) is not in supervisor Job"
        }
        $childAssigned = $true
        $resumed = [UMHJobNative]::ResumeThread($procInfo.hThread)
        if ($resumed -eq 0xFFFFFFFF) {
            [void][UMHJobNative]::TerminateJobObject($job, 2)
            throw "ResumeThread(op.exe) failed win32=$([Runtime.InteropServices.Marshal]::GetLastWin32Error())"
        }
    }
    finally {
        if (-not $childAssigned) {
            try { [void][UMHJobNative]::TerminateJobObject($job, 2) } catch {}
        }
    }

    $stamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
    $candidateSha = ""
    try {
        $candidateSha = (& git -C $RepoPath rev-parse HEAD 2>$null | Select-Object -First 1).Trim()
    } catch {
        $candidateSha = ""
    }
    $launcherPid = $null
    $launcherInJob = $false
    $deadline = (Get-Date).AddSeconds(20)
    do {
        Start-Sleep -Milliseconds 500
        $launcherProc = Get-CimInstance Win32_Process |
            Where-Object {
                $_.Name -match '^pythonw?\.exe$' -and
                $_.CommandLine -match [regex]::Escape($launcher)
            } |
            Select-Object -First 1
        if ($launcherProc) {
            $launcherPid = [int]$launcherProc.ProcessId
            $launcherHandle = [UMHJobNative]::OpenProcess(($PROCESS_QUERY_LIMITED_INFORMATION -bor $SYNCHRONIZE), $false, [uint32]$launcherPid)
            if ($launcherHandle -ne [IntPtr]::Zero) {
                try {
                    $tmp = $false
                    if ([UMHJobNative]::IsProcessInJob($launcherHandle, $job, [ref]$tmp)) {
                        $launcherInJob = $tmp
                    }
                    if ($launcherInJob) {
                        $launcherWaitHandle = $launcherHandle
                        $launcherHandle = [IntPtr]::Zero
                    }
                }
                finally {
                    if ($launcherHandle -ne [IntPtr]::Zero) {
                        [void][UMHJobNative]::CloseHandle($launcherHandle)
                    }
                }
            }
            break
        }
    } while ((Get-Date) -lt $deadline)
    if (-not $launcherPid -or -not $launcherInJob) {
        [void][UMHJobNative]::TerminateJobObject($job, 2)
        throw "launcher containment verification failed op_pid=$($procInfo.dwProcessId) launcher_pid=$launcherPid in_job=$launcherInJob"
    }

    @{
        task = $TaskName
        supervisor_pid = $PID
        job_name = "UMHNodeDaemon-$PID"
        op_pid = [int]$procInfo.dwProcessId
        launcher_pid = $launcherPid
        candidate_sha = $candidateSha
        repo_path = $RepoPath
        launcher = $launcher
        env_template = $EnvTemplate
        stop_event = $StopEventName
        containment_verified = @{
            op_in_job = $true
            launcher_in_job = $launcherInJob
            create_suspended = $true
            kill_on_job_close = $true
            handles_inheritable = $false
            waits_for_launcher = $true
            supervisor_parent_pid = $PID
        }
        started_at = $stamp
    } | ConvertTo-Json -Depth 3 -Compress | Set-Content -Path (Join-Path $runRoot "umh-node-supervisor.json") -Encoding UTF8

    [void][UMHJobNative]::WaitForSingleObject($launcherWaitHandle, $INFINITE)
    $exitCode = [uint32]0
    if (-not [UMHJobNative]::GetExitCodeProcess($launcherWaitHandle, [ref]$exitCode)) {
        $exitCode = 1
    }
    exit $exitCode
}
finally {
    if ($launcherWaitHandle -ne [IntPtr]::Zero) {
        [void][UMHJobNative]::CloseHandle($launcherWaitHandle)
    }
    if ($procInfo.hThread -and $procInfo.hThread -ne [IntPtr]::Zero) {
        [void][UMHJobNative]::CloseHandle($procInfo.hThread)
    }
    if ($procInfo.hProcess -and $procInfo.hProcess -ne [IntPtr]::Zero) {
        [void][UMHJobNative]::CloseHandle($procInfo.hProcess)
    }
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
