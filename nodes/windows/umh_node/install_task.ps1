<#
.SYNOPSIS
    Install or update the canonical UMH Node Daemon scheduled task.
#>

param(
    [string]$RepoPath = "C:\dev\dev\OS",
    [string]$EnvTemplate = "C:\ProgramData\UMH\.env.op.tpl",
    [string]$TaskName = "UMH Node Daemon"
)

$ErrorActionPreference = "Stop"

$supervisor = Join-Path $RepoPath "nodes\windows\umh_node\task_supervisor.ps1"
$runRoot = Join-Path $env:ProgramData "UMH\run"
New-Item -ItemType Directory -Force -Path $runRoot | Out-Null

if (-not (Test-Path -LiteralPath $supervisor)) {
    throw "supervisor not found: $supervisor"
}
if (-not (Test-Path -LiteralPath $EnvTemplate)) {
    throw "1Password environment template not found: $EnvTemplate"
}

$argument = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$supervisor`" -RepoPath `"$RepoPath`" -EnvTemplate `"$EnvTemplate`" -TaskName `"$TaskName`""
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argument -WorkingDirectory $runRoot

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Set-ScheduledTask -TaskName $TaskName -Action $action | Out-Null
    $state = (Get-ScheduledTask -TaskName $TaskName).State
    [pscustomobject]@{ ok = $true; task = $TaskName; action = "updated"; state = "$state"; supervisor = $supervisor } |
        ConvertTo-Json -Compress
    exit 0
}

$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Seconds 30) `
    -ExecutionTimeLimit (New-TimeSpan -Days 365) `
    -StartWhenAvailable `
    -DontStopOnIdleEnd
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "UMH Node Daemon - supervised task-owned launcher with 1Password env injection." `
    -Force | Out-Null

[pscustomobject]@{ ok = $true; task = $TaskName; action = "created"; state = "Ready"; supervisor = $supervisor } |
    ConvertTo-Json -Compress
