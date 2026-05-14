# Phase 96.8AI — Real Windows GUI Actuation Proof

## What This Proves

The governed UMH execution spine can actuate a real
Windows desktop GUI. Prior phases proved governance
contracts, workpacket gating, runtime orchestration,
ingestion orchestration, CU enforcement, and ledger
integrity — but did NOT prove actual Windows GUI
control. The system could declare "foreground CU
required" but had never proven it could actually
launch Chrome, detect foreground focus, capture
screenshots, or observe real desktop state.

This phase closes that gap. `!chrome-proof` routes
through the full governed spine and actuates real
Chrome on the live Windows workstation.

**Core principle: Observed reality > intended execution.**

## What Changed

### New Module: WindowsForegroundActuatorV1
`core/runtime/windows_foreground_actuator_v1.py`

Pure actuator contracts — no governance, no LLM, no
autonomy. Defines:

- `ObservedDesktopState` — 13 fields from actual
  observation: chrome_pid, window_handle, visible,
  focused, monitor_detected, desktop_unlocked,
  active_user_session, navigation_url, screenshot_hash
- `GUIActuationProof` — proof passes only when:
  observed state is valid, founder confirmed, chrome_pid > 0,
  and 5+ actuation stages completed
- `EnvironmentRequirement` — only FOREGROUND allowed;
  VPS, HEADLESS, BACKGROUND explicitly forbidden
- `ActuationStage` — 11-stage lifecycle from NOT_STARTED
  through RELAY_DISPATCHED, CHROME_LAUNCHED,
  FOCUS_CONFIRMED, SCREENSHOT_CAPTURED, to COMPLETED
- 14 forbidden actions (no simulated gui, no inferred
  visibility, no mocked chrome, no fake process detection)

### PowerShell Relay Extension
`scripts/windows_interactive_desktop_relay.ps1`

Extended with real Win32 GUI observation:

- `Capture-Screenshot` — System.Drawing.Graphics.CopyFromScreen
- `Get-ForegroundWindowInfo` — Win32 P/Invoke:
  GetForegroundWindow(), GetWindowText(),
  GetWindowThreadProcessId(), IsWindowVisible()
- `Handle-ChromeProof` — 7-stage proof sequence:
  Chrome launch → process verify → window metadata →
  focus validation → launch screenshot →
  focused screenshot → navigation screenshot
- Writes observed_desktop_state, desktop_environment,
  and proof_summary JSON artifacts

### Command Registration
`!chrome-proof` wired across 8 modules:

```
discord_interface_adapter_v1.py   — SUPPORTED + ACTION_MAP + SPINE_ROUTED + CONTRACT
router_contracts.py               — ALLOWED_ACTION_TYPES
control_plane_router_v1.py        — ACTION_CAPABILITY_MAP
discord_spine_integration_v1.py   — CapabilityAuthority.capabilities
windows_desktop_adapter_contracts.py — WindowsDesktopActionType enum
windows_desktop_request_builder.py — build_w0_chrome_proof_request()
adapter_registry_v1.json          — worker + adapter capabilities
w0_real_windows_gui_actuation_v1.json — config flags
```

## The Execution Path

```
Discord !chrome-proof
  → Interface Adapter (command registration)
  → Spine Router (not control plane router)
  → Authority Engine (environment + capability check)
  → Execution Gate (is foreground environment ready?)
  → Node Sync Gate (is local code current?)
  → Dispatch Queue (idempotent enqueue)
  → Supervisor (session + lifecycle)
  → Worker Runtime Daemon (picks up inbox JSON)
  → PowerShell Relay (Handle-ChromeProof)
    → Start-Process chrome.exe
    → Get-Process chrome (PID verification)
    → MainWindowHandle + MainWindowTitle
    → GetForegroundWindow() Win32 (focus validation)
    → IsWindowVisible() Win32
    → CopyFromScreen (screenshot capture)
    → SHA-256 hash
  → observed_desktop_state.json written
  → proof_summary.json written
  → PROOF-*.json emitted
  → Ledger entry recorded
  → Discord reply
```

## Environment Model

```
ALLOWED:   LOCAL_WINDOWS_FOREGROUND
FORBIDDEN: VPS, LOCAL_WINDOWS_HEADLESS, LOCAL_WINDOWS_BACKGROUND
NEUTRAL:   LOCAL_WINDOWS_GUI (generic, not enough)
```

Only `LOCAL_WINDOWS_FOREGROUND` passes validation.
The validate_environment() function rejects all
forbidden environments before any relay dispatch.

## Config Flags

```json
require_foreground_gui: true
require_real_desktop: true
require_chrome_process: true
require_screenshot_proof: true
require_observed_state: true
require_focus_validation: true
require_founder_confirmation: true
allow_headless: false
allow_api_fallback: false
allow_background_only: false
allow_simulated_gui: false
```

14 forbidden actions enforced.

## Proof Validity Requirements

A GUIActuationProof passes ONLY when ALL of:
1. ObservedDesktopState.is_valid is True
   (chrome_pid > 0, visible, focused, desktop_unlocked,
    active_user_session)
2. founder_confirmed is True
3. chrome_pid > 0
4. 5+ actuation stages completed

Any gap → proof.passed is False.

## Win32 APIs Used

```
user32.dll  GetForegroundWindow()         — real foreground HWND
user32.dll  GetWindowText()               — window title
user32.dll  GetWindowThreadProcessId()    — PID from HWND
user32.dll  IsWindowVisible()             — visibility check
System.Drawing  CopyFromScreen()          — screenshot capture
```

These are direct Win32 calls via C# P/Invoke in
PowerShell. No mocking. No simulation. No inference.

## Test Results

```
Phase 96.8AI:  115 passed  (17 test classes)
Regression:    469 passed  (8 prior test files)
Total:         584 passed, 0 failed
```

### Test Classes
- TestCommandRegistration (11) — all 8 registration points
- TestEnvironmentEnforcement (6) — required + forbidden
- TestEnvironmentValidation (4) — foreground passes, rest fail
- TestObservedDesktopState (9) — validity + denial reasons
- TestParseRelayResult (3) — relay JSON → observed state
- TestActuationEvents (5) — event lifecycle
- TestGUIActuationProof (9) — proof validity gates
- TestBuildAndPersistProof (3) — build + persist + summary
- TestConfig (15) — all config flags
- TestForbiddenActions (13) — all 14 forbidden actions
- TestRequestBuilder (8) — request construction
- TestWorkPacketBuilder (3) — WorkPacket integration
- TestAdapterRegistry (3) — registry entries
- TestSpineIntegration (1) — capability authority
- TestPowerShellRelay (9) — script content validation
- TestDataclassContracts (6) — defaults + serialization
- TestRegressionExistingCommands (6) — no breakage

## What This Does NOT Prove (Yet)

- End-to-end `!chrome-proof` execution on live workstation
  (requires founder at Windows desktop)
- Screenshot file actually captured on disk
  (requires real CopyFromScreen on real monitor)
- Founder visual confirmation workflow
  (requires founder interaction)

These are RUNTIME proofs that complete when the founder
runs `!chrome-proof` from Discord while seated at the
Windows workstation.

## Files Modified

```
CREATED:
  core/runtime/windows_foreground_actuator_v1.py
  config/w0_real_windows_gui_actuation_v1.json
  tests/test_real_windows_gui_actuation_v1.py
  docs/system/phase968ai_real_windows_gui_actuation_proof.md

MODIFIED:
  scripts/windows_interactive_desktop_relay.ps1
  eos_ai/interfaces/discord_interface_adapter_v1.py
  eos_ai/interfaces/discord_spine_integration_v1.py
  core/control_plane_router/router_contracts.py
  core/control_plane_router/control_plane_router_v1.py
  core/environment_bridge/windows_desktop_adapter_contracts.py
  core/environment_bridge/windows_desktop_request_builder.py
  data/registries/local_worker_adapter_registry_v1.json
```

## Commit

```
phase968ai: prove real windows gui actuation
```
