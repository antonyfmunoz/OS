# Visible Chrome Launch Gate v1

**Phase:** 96.8E (updated from 96.8D)
**Status:** Active
**Layer:** UMH Substrate — Execution Proof (Adapter Boundary Layer)
**Module:** `core/environment_bridge/chrome_visible_launch.py`

## Purpose

Governs Chrome launch proof for W0-001 CU execution. Process existence
and window metadata are recorded as evidence but are NOT sufficient
proof. Only founder visual confirmation constitutes proof.

## The Problem (Phase 96.8D → 96.8E)

Phase 96.8D discovered that process existence with `MainWindowHandle = 0`
is insufficient. Phase 96.8E discovered that even `MainWindowHandle != 0`
and `MainWindowTitle` nonblank are insufficient — WSL/tmux can spawn
Windows processes that report window metadata but never appear as
visible foreground windows on the desktop.

## Required Proof

Chrome launch gate passes ONLY with explicit founder visual confirmation.
Process/window metadata is evidence (recorded in proof artifact) but
CANNOT finalize the gate.

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
| `pending_founder_visual_confirmation` | Waiting for founder | NO |
| `founder_confirmed_visible` | Founder confirmed visible | YES |
| `founder_denied_visible` | Founder denied visible | NO |
| `chrome_not_found` | No Chrome processes | NO |
| `launch_method_disallowed` | explorer/default-browser used | NO |

## Metadata Evidence Levels

| Level | Meaning | Proof? |
|-------|---------|--------|
| `none` | No Chrome processes found | NO |
| `process_detected_only` | PIDs exist, no window metadata | NO |
| `window_metadata_detected` | MainWindowHandle/Title nonzero | NO |

## Proof Artifact

The worker writes `chrome_launch_proof_{wo_id}.json` containing:

- `launch_method` — how Chrome was invoked
- `executable_path` — which executable was used
- `requested_url` — what URL was requested
- `process_ids` — PIDs of Chrome processes found
- `main_window_handle_values` — handle values per process
- `main_window_titles` — window titles per process
- `metadata_evidence` — evidence classification level
- `founder_visual_confirmation_required` — always true for GUI
- `founder_visual_confirmation_received` — whether founder responded
- `founder_confirmed` — founder's answer
- `status` — gate status

## Gate Flow

```
Chrome launched via direct executable
  → Wait 3s
  → Collect process snapshots (PowerShell Get-Process)
  → Classify metadata as evidence (NOT proof)
  → Write chrome_launch_proof
  → Write visible_chrome_confirmation_request
  → PENDING_FOUNDER_VISUAL_CONFIRMATION (BLOCKED)
  → Poll inbox for founder confirmation

Founder confirms (confirmed=true)
  → FOUNDER_CONFIRMED_VISIBLE
  → VERIFY_ACTIVE_GOOGLE_ACCOUNT

Founder denies (confirmed=false)
  → FOUNDER_DENIED_VISIBLE
  → BLOCKED (investigation required)
```
