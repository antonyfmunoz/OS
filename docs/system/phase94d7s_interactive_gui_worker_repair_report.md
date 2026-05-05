# Phase 94D.7S — Interactive GUI Worker Repair Report

**Phase**: 94D.7S
**Status**: PARTIAL — BLOCKED ON FOUNDER INTERACTIVE LAUNCH
**Date**: 2026-05-04
**Author**: Developer Agent

---

## 1. Why 94D.7R Was a False Positive

Phase 94D.7R executed Chrome launch via VPS SSH → PowerShell:
```
ssh ... 'powershell.exe -NoProfile -Command "... Start-Process chrome.exe ..."'
```

PowerShell returned exit code 0 and reported the chrome.exe path.
The system treated this as visible success.

**But Chrome did not appear on the founder's desktop.**

The command ran in Windows Session 0 (non-interactive service context).
GUI processes launched from Session 0 are invisible to the desktop user
in Session 1.

## 2. Why SSH-Launched GUI Actions Are Unreliable on Windows

Windows uses session isolation:

| Session | Context | GUI Visible? |
|---------|---------|-------------|
| Session 0 | Services, SYSTEM, SSH | NO |
| Session 1+ | Interactive user desktop | YES |

Windows OpenSSH server runs as a service in Session 0. All commands
executed through it inherit Session 0. This includes:
- `powershell.exe Start-Process`
- `cmd.exe /c start`
- Direct executable launch

The process may "start" in Session 0 but:
- Its window is isolated from the desktop
- The user cannot see it
- It may be immediately terminated
- Exit code 0 is returned regardless

This is Windows architecture, not a bug or configuration issue.

## 3. Correct Visible GUI Success Criteria

A visible GUI action requires ALL of:
1. Command executes from an interactive session (Session 1+)
2. Exit code 0 (necessary but not sufficient)
3. **Founder visual confirmation** (the actual proof)

Status flow:
```
COMMAND_EXECUTED → ACTION_ATTEMPTED → WAITING_FOR_CONFIRMATION → [founder responds]
```

Exit code 0 alone is `ACTION_ATTEMPTED`, not `ACTION_EXECUTED_VISIBLE`.

## 4. Interactive GUI Worker Options

| Option | Description | Complexity |
|--------|-------------|-----------|
| A | Manual terminal start by founder | Low |
| B | Windows Task Scheduler at logon | Medium |
| C | Desktop daemon started at login | High |
| D | Existing local terminal | Low |

## 5. Recommended MVP Path

**Option A: Founder starts worker from local terminal.**

This is the simplest reliable path:
1. Founder opens terminal on local PC (any terminal — VS Code, Windows Terminal, WSL)
2. Terminal runs in Session 1 (interactive desktop)
3. Processes launched from this terminal are visible on screen
4. No additional infrastructure needed

Alternative one-shot (even simpler):
```powershell
powershell.exe -NoProfile -Command "Start-Process -FilePath 'C:\Program Files\Google\Chrome\Application\chrome.exe' -ArgumentList 'https://drive.google.com/'"
```
Run this in any local terminal and Chrome opens visibly.

## 6. Whether Drive Was Retried Through Interactive Path

**NOT YET.** The VPS cannot start processes in the founder's interactive
session. A launch intent has been written to the local inbox:
```
~/eos_advisor_messages/inbox/launch_intent_WO-LOCAL-PILOT-GDRIVE-GDOCS-001.json
```

The founder must either:
- Start the worker from a local terminal, OR
- Run the one-shot PowerShell command in any local terminal

## 7. Whether Founder Visually Confirmed

**NOT YET.** Phase is blocked waiting for founder interactive action.

## 8. Next Exact Action

**FOUNDER_INTERACTIVE_CHROME_LAUNCH**

Founder must run from a local terminal on the PC:
```powershell
powershell.exe -NoProfile -Command "Start-Process -FilePath 'C:\Program Files\Google\Chrome\Application\chrome.exe' -ArgumentList 'https://drive.google.com/'"
```

Then report to advisor one of:
- CONFIRMED_VISIBLE
- NOT_VISIBLE
- LOGIN_REQUIRED
- WRONG_ACCOUNT
- CANCEL

---

## Test Results

```
132 passed (29 + 32 + 39 + 11 + 21 = 132 total)
```

| Test File | Count |
|-----------|-------|
| `test_phase94d6_local_worker_auto_loop.py` | 29 |
| `test_phase94d7_approved_action_executor.py` | 32 |
| `test_phase94d7_visible_browser_launch_backend.py` | 39 |
| `test_phase94d7r_chrome_login_safe_gate.py` | 11 |
| `test_phase94d7s_visible_gui_success_criteria.py` | 21 |

## Code Modules Created

| Module | Location |
|--------|----------|
| Visible GUI success criteria | `eos_ai/substrate/visible_gui_success_criteria.py` |
| Interactive GUI worker contracts | `eos_ai/substrate/interactive_gui_worker_contracts.py` |

## Documentation Created

| Document | Location |
|----------|----------|
| Interactive Windows GUI worker | `docs/operations/interactive_windows_gui_worker_v1.md` |
| Visible GUI success criteria | `docs/operations/visible_gui_success_criteria_v1.md` |
| False positive repair | `docs/operations/w0_001_false_positive_chrome_launch_repair_v1.md` |
| This report | `docs/system/phase94d7s_interactive_gui_worker_repair_report.md` |

## Hard Rules Compliance

- No computer use attempted in this phase: YES
- No Playwright: YES
- No Gmail: YES
- No account switching: YES
- No document access: YES
- No credential capture: YES
- No memory promotion: YES
- No governance bypass: YES
- False positive corrected: YES
- SSH launch demoted: YES
