# W0-001 Tmux Shell Chrome Launch Test v1

**Phase**: 94D.8
**Status**: PARTIAL — AWAITING FOUNDER VISUAL CONFIRMATION
**Date**: 2026-05-04

---

## Test Objective

Route the OPEN_GOOGLE_DRIVE action through an interactive tmux shell
environment to open Chrome visibly on the local PC.

## Test Results

| Step | Status | Evidence |
|------|--------|----------|
| Inspect local tmux panes | DONE | 3 panes found |
| Classify panes | DONE | bridge=busy, test_interop=shell, umh_core=shell |
| Select shell pane | DONE | test_interop:1.1 |
| Deploy launch script | DONE | ~/umh_local_worker/open_drive_chrome.sh |
| Send command to tmux pane | DONE | tmux send-keys |
| Script executed | DONE | UtilAcceptVsock:271 error |
| Chrome opened via tmux? | NO | WSL interop socket missing |
| Fallback: direct Windows SSH | DONE | powershell.exe Start-Process → LAUNCH_SENT |
| Chrome opened via SSH? | UNKNOWN | Awaiting founder confirmation |
| ACTION_ATTEMPTED written | DONE | action_attempted_WO-*.json |
| Founder confirmed? | PENDING | — |

## Key Discovery

Tmux sessions created via SSH lack the WSL Windows interop socket.
The `powershell.exe` command fails with:
```
<3>WSL (36540 - ) ERROR: UtilAcceptVsock:271: accept4 failed 110
```

This is not specific to the command — ANY Windows executable call
fails from SSH-originated WSL instances, including tmux panes.

## Fallback Executed

After tmux path failed, fell back to direct Windows SSH PowerShell:
```bash
ssh ... 'powershell.exe -NoProfile -Command "Start-Process chrome.exe ..."'
```

This bypasses WSL entirely and runs PowerShell natively on Windows.
Exit code was 0 and "LAUNCH_SENT" was reported.

However, this may still be Session 0 (invisible) — same as 94D.7R.

## SSH PowerShell Path: CONFIRMED NOT_VISIBLE

Founder confirmed: Chrome did NOT visibly open via direct SSH PowerShell.
Both SSH-based paths (direct + tmux) are now demoted.

## Escalation: Windows Task Scheduler /IT

After NOT_VISIBLE confirmation, escalated to Task Scheduler:
```
schtasks /create /tn "UMH_ChromeDriveLaunch" /tr "chrome.exe url" /sc once /st 00:00 /f /rl highest /it
schtasks /run /tn "UMH_ChromeDriveLaunch"
```

Task created: SUCCESS
Task run: SUCCESS (Attempted)
Task status: Ready
Logon mode: Interactive only

## Current Status

ACTION_ATTEMPTED via Task Scheduler. Awaiting founder visual confirmation:
- CONFIRMED_VISIBLE
- NOT_VISIBLE
- LOGIN_REQUIRED
- WRONG_ACCOUNT
- CANCEL

## Timeline

| Time (UTC) | Event |
|------------|-------|
| ~22:XX:00 | Tmux panes inspected (3 found) |
| ~22:XX:05 | Launch script deployed to local PC |
| ~22:XX:10 | Command sent into test_interop:1.1 |
| ~22:XX:13 | UtilAcceptVsock error (tmux path failed) |
| ~22:XX:20 | Fallback: direct SSH PowerShell → LAUNCH_SENT |
| ~22:XX:25 | ACTION_ATTEMPTED written |
| — | WAITING_FOR_FOUNDER_VISUAL_CONFIRMATION |
