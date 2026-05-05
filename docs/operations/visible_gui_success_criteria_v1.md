# Visible GUI Success Criteria v1

**Phase**: 94D.7S
**Status**: ACTIVE
**Date**: 2026-05-04

---

## Core Rule

**A visible GUI action is NOT successful unless it appears in the active
user desktop session AND receives explicit founder visual confirmation.**

## What Is NOT Sufficient

- Command exit code 0
- Process PID returned
- No error in stderr
- PowerShell Start-Process returning without exception
- SSH command completing successfully

These indicate "command ran" not "GUI appeared on screen."

## What IS Sufficient

1. **Founder visual confirmation** — founder looks at screen, confirms Chrome opened
2. **Interactive worker confirms + founder confirms** — worker runs in Session 1, launches GUI, founder sees it
3. **Approved screenshot/observation backend** — captures screen, sees Chrome window (future, requires separate approval)

## Status Flow

```
COMMAND_EXECUTED (exit code 0)
    ↓
ACTION_ATTEMPTED (not yet confirmed visible)
    ↓
WAITING_FOR_FOUNDER_VISUAL_CONFIRMATION
    ↓
┌─────────────────────────────────────┐
│ Founder responds:                    │
│ ├─ CONFIRMED_VISIBLE → success       │
│ ├─ NOT_VISIBLE → false positive      │
│ ├─ LOGIN_REQUIRED → pause for login  │
│ ├─ WRONG_ACCOUNT → pause for switch  │
│ └─ CANCEL → abort                    │
└─────────────────────────────────────┘
```

## Why Phase 94D.7R Was a False Positive

Phase 94D.7R executed via SSH:
```
ssh ... 'powershell.exe -NoProfile -Command "... Start-Process -FilePath $chrome ..."'
```

PowerShell returned exit code 0 and output the chrome.exe path.
The system marked this as "Drive opened in Chrome: YES."

But Chrome did not appear on the founder's screen because SSH runs
in Session 0 (non-interactive Windows service session).

## Module

`eos_ai/substrate/visible_gui_success_criteria.py`

## Valid Confirmation Responses

| Response | Meaning | Next Action |
|----------|---------|-------------|
| CONFIRMED_VISIBLE | Chrome opened Drive on screen | Proceed to account verification |
| NOT_VISIBLE | Chrome not visible | Retry via interactive path |
| LOGIN_REQUIRED | Chrome opened but login needed | Pause, founder logs in manually |
| WRONG_ACCOUNT | Wrong Google account active | Pause, manual account switch |
| CANCEL | Abort test | Stop all automation |
