# Windows Interactive Desktop Adapter v1

**Phase:** 96.8H
**Status:** Active
**Layer:** UMH Substrate — Adapter Boundary Layer
**Module:** `core/environment_bridge/windows_desktop_adapter_contracts.py`

## Why This Exists

WSL/tmux can orchestrate and relay. WSL/tmux must not be trusted as
final Windows GUI authority. Process and window metadata from WSL-spawned
processes is evidence, not proof.

Prior W0 attempts proved:
1. WSL subprocess can launch Chrome but window may not appear on desktop
2. MainWindowHandle != 0 does not guarantee visible foreground window
3. explorer.exe / default-browser routing bypasses application binding
4. Only the logged-in Windows user session has real desktop access

The Windows Interactive Desktop Adapter solves this by running in the
interactive Windows session and owning all GUI actuation.

## Architecture

```
VPS (control/advisor)
  │
  ├── Creates governed work packet with coherence envelope
  │
  ▼
WSL Worker (tmux — orchestrator/relay)
  │
  ├── Validates packet, coherence, execution binding
  ├── Detects gui_actuator requirement → routes to relay client
  ├── Writes JSON request to relay inbox
  │
  ▼
Windows Interactive Desktop Adapter (PowerShell relay)
  │
  ├── Runs in logged-in Windows session (has desktop access)
  ├── Reads request from inbox
  ├── Validates: application, launch method, blocked methods
  ├── Launches Chrome via direct executable only
  ├── Collects process/window metadata as EVIDENCE
  ├── Writes result to outbox with pending_founder_visual_confirmation
  │
  ▼
WSL Worker reads result
  │
  ├── Stops at VISIBLE_CHROME_LAUNCH_PENDING_FOUNDER_CONFIRMATION
  ├── Founder confirms/denies visibility
  │
  ▼
Next gate or blocked
```

## Role Separation

| Component | Role | Can Launch GUI? |
|-----------|------|-----------------|
| VPS | Control/advisor/orchestrator node | NO |
| WSL/tmux | Local relay/orchestration worker | NO (relay only) |
| Windows Desktop Adapter | Windows-native GUI actuator | YES |
| Chrome | Application (exact identity bound) | N/A |
| Google Workspace | Target service family | N/A |
| Founder | Human proof authority | N/A |

## Relay Protocol

Communication is file-based JSON inbox/outbox:

- **Inbox:** `~/eos_relay/inbox/` — worker writes requests here
- **Outbox:** `~/eos_relay/outbox/` — relay writes results here
- **Processed:** `~/eos_relay/processed/` — relay moves handled requests

Request files: `{request_id}.json`
Result files: `{request_id}_result.json`

## Supported v1 Actions

| Action | Purpose |
|--------|---------|
| `ping` | Relay health check → returns `pong` |
| `open_application_url` | Launch Chrome with URL via direct executable |
| `focus_application` | Bring application to foreground (future) |
| `request_founder_visual_confirmation` | Ask founder to confirm (future) |

## Forbidden Actions

- No explorer.exe URL routing
- No default-browser routing
- No generic shell URL open
- No screenshot capture
- No credential/token/cookie access
- No page content reading
- No mutation actions

## Proof in v1

Founder visual confirmation is required. The adapter collects process/window
metadata as evidence but never claims visible proof from metadata alone.

Future: Win32 API-based foreground detection could supplement or replace
founder confirmation for specific gate types.

## Alignment

- **UMH Execution Binding Law:** All 6 layers explicitly bound
- **Application Binding Law:** Direct Chrome executable only
- **External Boundary Law:** WSL/tmux is relay, not GUI authority
- **Canonical Spine Coherence:** Coherence envelope required before execution
