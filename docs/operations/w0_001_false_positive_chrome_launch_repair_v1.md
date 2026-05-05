# W0-001 False Positive Chrome Launch Repair v1

**Phase**: 94D.7S
**Status**: BLOCKED — AWAITING INTERACTIVE LAUNCH
**Date**: 2026-05-04

---

## What Happened in 94D.7R

1. VPS executed PowerShell via SSH: `Start-Process -FilePath chrome.exe -ArgumentList 'https://drive.google.com/'`
2. PowerShell returned exit code 0
3. PowerShell output: `C:\Program Files\Google\Chrome\Application\chrome.exe`
4. System marked: "Drive opened in Chrome: YES"
5. **Founder did NOT see Chrome open on the local PC**

## Root Cause

Windows OpenSSH runs in Session 0 (non-interactive service context).
Processes launched from Session 0 either:
- Open in Session 0 (invisible to desktop user)
- Fail silently due to session isolation
- Start but are immediately terminated by session boundary

The command "succeeds" from PowerShell's perspective but the GUI
window never appears in Session 1 (the founder's interactive desktop).

## Correction

1. SSH launch path demoted to `NON_INTERACTIVE_WINDOWS_SSH_LAUNCH`
2. Exit code 0 is no longer sufficient for visible GUI success
3. New success criteria require founder visual confirmation
4. Interactive GUI worker path defined (runs in Session 1)
5. Launch intent written to inbox for interactive worker

## Current State

A launch intent file has been written to the local PC:
```
~/eos_advisor_messages/inbox/launch_intent_WO-LOCAL-PILOT-GDRIVE-GDOCS-001.json
```

## What Founder Must Do

1. Open a terminal on the local PC (Windows Terminal, VS Code, or WSL)
2. Run from the terminal:
   ```bash
   cd ~/umh_local_worker
   python3 local_worker_auto_loop.py ~/eos_advisor_messages/wo_001_relay_packet.json
   ```
   
   OR manually execute (simplest one-shot):
   ```powershell
   powershell.exe -NoProfile -Command "Start-Process -FilePath 'C:\Program Files\Google\Chrome\Application\chrome.exe' -ArgumentList 'https://drive.google.com/'"
   ```

3. Report what happened:
   - `CONFIRMED_VISIBLE` — Chrome opened Google Drive visibly
   - `NOT_VISIBLE` — Chrome did not appear
   - `LOGIN_REQUIRED` — Chrome opened but login page shows
   - `WRONG_ACCOUNT` — Chrome opened but wrong account active

## Blocked Until

Founder confirms visual result through advisor.

## Next Exact Action After This Phase

One of:
- `CONFIRM_ACTIVE_GOOGLE_ACCOUNT` (if Chrome opened successfully)
- `FIX_INTERACTIVE_LAUNCH` (if still not visible)
- `LOGIN_REQUIRED_MANUAL_INTERVENTION` (if login needed)
- `WRONG_ACCOUNT_PAUSE` (if wrong account)
