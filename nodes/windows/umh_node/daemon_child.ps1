<#
.SYNOPSIS
    Job-contained child process for the UMH Node Daemon supervisor.

.DESCRIPTION
    The task supervisor launches this script through 1Password `op run`.
    This avoids passing a space-containing Python executable path through
    `op` command parsing. Because this process is inside the supervisor Job,
    the launched daemon process and its descendants inherit Job containment.
#>

param(
    [string]$RepoPath = "C:\dev\dev\OS",
    [string]$StopEventName = "Global\UMHNodeDaemonStop"
)

$ErrorActionPreference = "Stop"

$runtimeRoot = Join-Path $env:ProgramData "UMH"
$runRoot = Join-Path $runtimeRoot "run"
New-Item -ItemType Directory -Force -Path $runRoot | Out-Null

$launcher = Join-Path $RepoPath "nodes\windows\umh_node\launcher.py"
if (-not (Test-Path -LiteralPath $launcher)) {
    throw "launcher not found: $launcher"
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
Set-Location -LiteralPath $runRoot
$env:UMH_DAEMON_STOP_EVENT = $StopEventName

$process = New-Object System.Diagnostics.Process
$process.StartInfo.FileName = $pythonw
$process.StartInfo.Arguments = '"' + ($launcher -replace '"', '\"') + '"'
$process.StartInfo.WorkingDirectory = $runRoot
$process.StartInfo.UseShellExecute = $false
$process.StartInfo.CreateNoWindow = $true

if (-not $process.Start()) {
    throw "failed to start launcher"
}

$process.WaitForExit()
exit $process.ExitCode
