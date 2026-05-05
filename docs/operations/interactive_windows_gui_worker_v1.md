# Interactive Windows GUI Worker v1

**Phase**: 94D.7S
**Status**: ACTIVE
**Date**: 2026-05-04

---

## Purpose

Defines how GUI-visible actions (like opening Chrome) must be executed
on the local Windows PC to actually appear on the founder's desktop.

## The Problem

Windows OpenSSH runs in Session 0 (service/SYSTEM context). Commands
executed via SSH inherit this non-interactive session. When PowerShell
`Start-Process` runs chrome.exe from Session 0:

- The command may return exit code 0 (success)
- But Chrome opens in Session 0, invisible to the user
- Or Chrome fails silently due to session isolation
- The founder sees nothing on their desktop

This is Windows session isolation, not a bug. Sessions are:
- **Session 0**: Services and non-interactive processes (SSH, scheduled tasks as SYSTEM)
- **Session 1+**: Interactive user desktop sessions (what you see on screen)

## Correct Architecture

GUI-visible actions must execute from within the founder's Session 1+
(interactive desktop session). This requires the worker to be started
by the user, not by SSH.

## MVP Path: Manual Local Terminal Start

1. Founder opens a terminal on the local PC:
   - Windows Terminal
   - VS Code integrated terminal
   - WSL terminal inside Windows
   
2. In that terminal, run the worker:
   ```bash
   cd ~/umh_local_worker
   python3 local_worker_auto_loop.py ~/eos_advisor_messages/wo_001_relay_packet.json
   ```

3. Worker reads launch intent from inbox

4. Worker executes:
   ```powershell
   powershell.exe -NoProfile -Command "Start-Process -FilePath 'C:\Program Files\Google\Chrome\Application\chrome.exe' -ArgumentList 'https://drive.google.com/'"
   ```

5. Because the terminal is in Session 1, Chrome opens visibly

6. Worker writes `ACTION_ATTEMPTED` (not ACTION_EXECUTED)

7. Advisor asks founder for visual confirmation

8. Founder responds:
   - `CONFIRMED_VISIBLE` — Chrome opened Drive, proceed
   - `NOT_VISIBLE` — false positive, retry or investigate
   - `LOGIN_REQUIRED` — Chrome opened but login needed
   - `WRONG_ACCOUNT` — wrong Google account active
   - `CANCEL` — abort

## What SSH CAN Still Do

SSH is still useful for:
- Writing files (intents, packets, configs) to the local PC
- Reading outbox messages
- Checking process status (tasklist)
- Non-GUI commands
- Deploying worker scripts

SSH CANNOT reliably:
- Launch visible GUI windows
- Take screenshots of the desktop
- Simulate mouse/keyboard
- Observe what's on screen

## Future Paths

| Path | Complexity | Reliability |
|------|-----------|-------------|
| A. Manual terminal start | Low | High (proven) |
| B. Task Scheduler at logon | Medium | High |
| C. Desktop daemon service | High | High |
| D. Claude Code local instance | Low | High |

## Modules

| Module | Purpose |
|--------|---------|
| `interactive_gui_worker_contracts.py` | Intent/response contracts |
| `visible_gui_success_criteria.py` | Success evaluation logic |

## Classification of Launch Contexts

| Context | Reliable for GUI? | Reliable for commands? |
|---------|-------------------|----------------------|
| NON_INTERACTIVE_WINDOWS_SSH | NO | YES |
| INTERACTIVE_WINDOWS_DESKTOP | YES | YES |
| INTERACTIVE_WSL_TERMINAL | YES | YES |
