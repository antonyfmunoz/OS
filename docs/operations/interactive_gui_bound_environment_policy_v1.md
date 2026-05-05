# Interactive GUI-Bound Environment Policy v1

**Phase**: 94D.8
**Status**: ACTIVE
**Date**: 2026-05-04

---

## The WSL Interop Socket Problem (Complete Picture)

For GUI-visible actions on the local Windows PC, the execution environment
must have access to the Windows interop socket. This socket bridges
WSL ↔ Windows and allows WSL processes to call Windows executables
(powershell.exe, cmd.exe, chrome.exe).

### What HAS the interop socket

- WSL launched from Windows Terminal
- WSL launched from Windows Start Menu
- WSL launched via `wsl.exe` from Windows cmd/PowerShell
- WSL launched via Task Scheduler as the logged-in user
- Any tmux session created WITHIN such a WSL instance

### What DOES NOT have the interop socket

- WSL entered via SSH (`ssh ... 'wsl -e bash'`)
- Any tmux session created from an SSH-connected WSL
- Any child process of an SSH-originated WSL session
- The `sshd` service WSL instance itself

### The error when interop is missing

```
<3>WSL (36540 - ) ERROR: UtilAcceptVsock:271: accept4 failed 110
```

This means the Windows VSocket bridge is not connected for this
WSL instance.

## Proven Execution Paths

| Method | Has interop? | Can launch Chrome? | Confirmed? |
|--------|-------------|-------------------|-----------|
| VPS SSH → Windows PowerShell (no WSL) | YES* | YES* | Unconfirmed visual |
| VPS SSH → WSL → powershell.exe | NO | NO | Failed |
| VPS SSH → WSL → tmux → powershell.exe | NO | NO | Failed (94D.8) |
| Local Windows Terminal → WSL → powershell.exe | YES | YES | Expected |
| Local Windows Terminal → PowerShell direct | YES | YES | Expected |

*SSH → Windows PowerShell runs the command but may be in Session 0
(invisible to desktop user). Requires founder visual confirmation.

## Recommended MVP Paths for Visible Chrome Launch

### Path 1: Direct Windows PowerShell via SSH (simplest)

```bash
ssh ... 'powershell.exe -NoProfile -Command "Start-Process -FilePath \"C:\Program Files\Google\Chrome\Application\chrome.exe\" -ArgumentList \"https://drive.google.com/\""'
```

Pros: Already works (94D.7R proved command executes)
Cons: May be Session 0 — requires founder visual confirmation
Status: ATTEMPTED, AWAITING CONFIRMATION

### Path 2: Founder runs from local terminal (guaranteed)

Founder opens any terminal and runs:
```powershell
Start-Process -FilePath "C:\Program Files\Google\Chrome\Application\chrome.exe" -ArgumentList "https://drive.google.com/"
```

Pros: Guaranteed visible (user session)
Cons: Requires manual founder action
Status: FALLBACK if Path 1 confirmed not visible

### Path 3: Windows Task Scheduler (automated, user session)

Create a scheduled task that runs in the user's interactive session:
```powershell
schtasks /create /tn "UMH_ChromeLaunch" /tr "\"C:\Program Files\Google\Chrome\Application\chrome.exe\" https://drive.google.com/" /sc once /st 00:00 /ru "%USERNAME%" /it
schtasks /run /tn "UMH_ChromeLaunch"
```

Pros: Automated, runs in user session (`/it` flag = interactive)
Cons: More complex setup
Status: FUTURE if needed

## Demoted Paths (Confirmed NOT_VISIBLE)

| Path | Status | Why |
|------|--------|-----|
| SSH → WSL → tmux → powershell.exe | DEAD | UtilAcceptVsock (no interop) |
| SSH → powershell.exe Start-Process | DEAD | Session 0 (founder confirmed NOT_VISIBLE) |

## Current Action

**Path 3 (Task Scheduler /IT) has been executed.**

Task created: `UMH_ChromeDriveLaunch`
Task logon mode: Interactive only
Task status after run: Ready (completed)

Awaiting founder visual confirmation:
- CONFIRMED_VISIBLE — Chrome appeared on screen
- NOT_VISIBLE — still invisible (escalate to manual)
- LOGIN_REQUIRED — Chrome appeared but login needed
- WRONG_ACCOUNT — Chrome appeared with wrong account
