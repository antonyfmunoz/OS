# Windows Interactive Desktop Adapter Requirement v1

**Phase:** 96.8E (documented requirement)
**Status:** FUTURE — not built
**Layer:** UMH Substrate — Adapter Boundary Layer

## Problem

WSL/tmux execution can spawn Windows processes without reliable
foreground visibility. Specifically:

1. `subprocess.Popen` from WSL creates Windows processes via interop
2. The process gets a PID and may have a `MainWindowHandle`
3. But the window may not appear on the founder's desktop
4. The window may be on a different virtual desktop
5. The window may be behind other windows with no foreground ownership
6. Windows interop from tmux-spawned sessions has no desktop access

This means process metadata (`MainWindowHandle`, `MainWindowTitle`)
from `Get-Process` in PowerShell is NOT reliable proof of visible GUI.

## Confirmed False Positive

Phase 96.8D local test: worker reported `VISIBLE_CHROME_LAUNCH` with
nonzero `MainWindowHandle` and `MainWindowTitle`. Founder observed NO
visible Chrome window on the desktop. The metadata lied.

## Current Mitigation

Founder visual confirmation gate (Phase 96.8E):
- Worker stops at `PENDING_FOUNDER_VISUAL_CONFIRMATION`
- Founder manually writes confirmation file
- Only `FOUNDER_CONFIRMED_VISIBLE` advances to next gate

This works but requires the founder to be present and responsive.

## Future Solution: Windows Interactive Desktop Adapter

A Windows Interactive Desktop Adapter would:

1. Run as a Windows service or scheduled task in the interactive session
2. Have access to the actual desktop (Session 1, not Session 0)
3. Use Win32 APIs to check foreground window ownership:
   - `GetForegroundWindow()` → is Chrome the foreground window?
   - `IsWindowVisible()` → is the window actually visible?
   - `GetWindowRect()` → is the window on-screen (not minimized)?
4. Report reliable foreground state back to the worker
5. Optionally bring the Chrome window to the foreground

## Key Win32 APIs

| API | Purpose |
|-----|---------|
| `GetForegroundWindow()` | Returns handle of foreground window |
| `IsWindowVisible()` | Checks if window is visible |
| `GetWindowRect()` | Gets window position and size |
| `SetForegroundWindow()` | Brings window to foreground |
| `BringWindowToTop()` | Moves window to top of z-order |
| `ShowWindow(SW_RESTORE)` | Restores minimized window |

## Architecture

```
WSL Worker (tmux)
  │
  ├── Launches Chrome via direct executable
  ├── Sends "check_foreground" request to adapter
  │
  ▼
Windows Interactive Desktop Adapter (Windows service/agent)
  │
  ├── Runs in interactive session (has desktop access)
  ├── Uses Win32 APIs to check foreground state
  ├── Returns reliable visibility proof
  │
  ▼
Worker receives reliable proof
  → No founder confirmation needed for foreground check
  → Founder confirmation still needed for account verification
```

## Implementation Options

1. **PowerShell script running in interactive session** (simplest)
   - Task Scheduler → run in interactive session
   - Receives check requests via file/named pipe
   - Reports foreground state

2. **Python service with pywin32** (most integrated)
   - `import win32gui`
   - Direct Win32 API access
   - Can both check and set foreground

3. **C# Windows service** (most reliable)
   - Native Win32 interop
   - Runs in user session
   - Best performance

## Prerequisites

- The adapter must run in the interactive desktop session (not Session 0)
- The adapter must be started before the worker attempts Chrome launch
- Communication channel between WSL worker and Windows adapter
- The adapter itself needs governance (what it's allowed to do)

## Priority

LOW — founder visual confirmation works for the W0-001 gate.
Build this when the manual confirmation loop becomes a bottleneck
(e.g., automated recurring CU execution without founder presence).
