# Visible Chrome Launch Gate v1

**Phase:** 96.8D
**Status:** Active
**Layer:** UMH Substrate — Execution Proof (Adapter Boundary Layer)
**Module:** `core/environment_bridge/chrome_visible_launch.py`

## Purpose

Governs Chrome launch proof for W0-001 CU execution. Process existence
alone is NOT sufficient — visible-window proof is required before the
worker can proceed to VERIFY_ACTIVE_GOOGLE_ACCOUNT.

## The Problem

During manual local test, Chrome processes existed (PIDs found) but
`MainWindowHandle = 0` and `MainWindowTitle` was blank. This means
Chrome was running as background processes (updaters, service workers)
without a visible browser window. The old worker treated process
existence as proof of launch — a false positive.

## Required Proof

VISIBLE_CHROME_LAUNCH passes ONLY if:

1. Chrome launched through direct executable path, AND
2. At least one Chrome process has:
   - `MainWindowHandle != 0`, OR
   - `MainWindowTitle` is nonblank

## Disallowed Launch Methods

| Method | Allowed? | Reason |
|--------|----------|--------|
| Direct Chrome executable | YES | Only governed method |
| WSL interop to Chrome exe | YES | Same executable, WSL path |
| explorer.exe | NO | Default handler, ungoverned |
| Default-browser routing | NO | Not deterministic |
| PowerShell Start-Process (no exe path) | NO | Indirect |

## Chrome Executable Paths

### Windows
- `C:\Program Files\Google\Chrome\Application\chrome.exe`
- `C:\Program Files (x86)\Google\Chrome\Application\chrome.exe`

### WSL
- `/mnt/c/Program Files/Google/Chrome/Application/chrome.exe`
- `/mnt/c/Program Files (x86)/Google/Chrome/Application/chrome.exe`

## Launch Command

```bash
"/mnt/c/Program Files/Google/Chrome/Application/chrome.exe" --new-window "https://drive.google.com/drive/my-drive"
```

## Status Values

| Status | Meaning | Next Gate? |
|--------|---------|------------|
| `VISIBLE_CHROME_LAUNCH` | Visible window confirmed | YES |
| `VISIBLE_CHROME_LAUNCH_UNVERIFIED` | Launch attempted, window state unknown | NO |
| `CHROME_BACKGROUND_PROCESS_ONLY` | Processes exist, no visible window | NO |
| `CHROME_NOT_FOUND` | No Chrome executable or processes | NO |
| `LAUNCH_METHOD_DISALLOWED` | explorer/default-browser used | NO |

## Proof Artifact

The worker writes `chrome_launch_proof_{wo_id}.json` containing:

- `launch_method` — how Chrome was invoked
- `executable_path` — which executable was used
- `requested_url` — what URL was requested
- `process_ids` — PIDs of Chrome processes found
- `main_window_handle_values` — handle values per process
- `main_window_titles` — window titles per process
- `visible_window_detected` — boolean
- `founder_visual_confirmation_required` — whether manual check needed
- `status` — pass/fail

## Gate Flow

```
Chrome launched via direct executable
  → Wait 3s for window
  → Collect process snapshots (PowerShell Get-Process)
  → Evaluate visible-window proof
  → VISIBLE_CHROME_LAUNCH? → VERIFY_ACTIVE_GOOGLE_ACCOUNT
  → CHROME_BACKGROUND_PROCESS_ONLY? → BLOCKED (founder confirmation required)
  → CHROME_NOT_FOUND? → BLOCKED (no silent fallback)
```
