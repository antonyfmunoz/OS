# Phase 96.8D — Local Worker Chrome Visibility + Tmux Relay Hardening Report

**Date:** 2026-05-06
**Status:** COMPLETE
**Gate:** COMMIT_PHASE_968D_LOCAL_WORKER_HARDENING

---

## What Failed in Local Test

During manual local test of the W0-001 CU rerun:

1. **Packet missing routing fields** — the generated packet lacked
   `target_account`, `worker_mode`, `approval_routing`, `preferred_backend`.
   The local worker validation rejected the packet until the founder
   manually patched it. This should never happen.

2. **Chrome visible launch false positive** — Chrome processes existed
   (PIDs found via Get-Process), but `MainWindowHandle = 0` and
   `MainWindowTitle` was blank for all processes. This means Chrome was
   running as background processes (updaters, service workers) without
   a visible browser window. The old worker treated process existence
   as proof of launch.

---

## Why Process Existence Is Insufficient Proof

Chrome on Windows runs multiple processes:
- GPU process
- Utility processes
- Service worker processes
- Update checker
- Browser UI process

Only the browser UI process has a visible window with `MainWindowHandle != 0`.
Background processes have `MainWindowHandle = 0` and blank `MainWindowTitle`.

Treating "any chrome.exe process exists" as "Chrome is open and visible"
is a false positive that would allow VERIFY_ACTIVE_GOOGLE_ACCOUNT to
proceed without an actual browser window being visible.

---

## Why explorer.exe / Default-Browser Routing Is Not Allowed

`explorer.exe` and default-browser routing (Start-Process URL, xdg-open, etc.)
are not deterministic:
- They may open a different browser
- They may open a different Chrome profile
- They don't guarantee `--new-window` behavior
- They can't be audited for governance compliance
- The actual executable launched is unknown to the worker

For governed CU execution, the exact Chrome executable path must be used.

---

## Corrected Direct Chrome Executable Doctrine

Allowed launch command (WSL):
```bash
"/mnt/c/Program Files/Google/Chrome/Application/chrome.exe" --new-window "https://drive.google.com/drive/my-drive"
```

The worker now:
1. Calls Chrome directly via `subprocess.Popen` with the WSL path
2. Waits 3 seconds for the window to appear
3. Collects process snapshots via PowerShell `Get-Process chrome`
4. Evaluates `MainWindowHandle` and `MainWindowTitle` per process
5. Writes `chrome_launch_proof_{wo_id}.json` with full proof artifact
6. Only proceeds to VERIFY_ACTIVE_GOOGLE_ACCOUNT if visible window detected

---

## Packet Schema Correction

Created `core/environment_bridge/w0_packet_builder.py` with `build_w0_001_packet()`
that generates the complete W0-001 packet with all routing fields:

| Field | Value |
|-------|-------|
| target_account | antonyfm@empyreanstudios.co |
| worker_mode | auto |
| approval_routing | advisor_relay |
| preferred_backend | GUI_COMPUTER_USE |
| playwright_enabled | false |
| screenshot_capture | false |
| cdp_enabled | false |

Added routing fields to `WorkPacket` dataclass and `to_dict()`.
Added `_check_routing_fields()` to `packet_validator.py`.
Regenerated the W0-001 packet JSON file.

---

## Local Pull Worker as Tmux Relay Doctrine

The local pull worker IS the permanent "VPS sends to local tmux" system:

- VPS creates governed packet → places in outbox
- Local worker pulls packet → validates → executes through Chrome
- Founder role is only approval/visual confirmation at gates
- Founder does NOT manually patch packets or launch Chrome

---

## Tests Passed

| Test File | Tests | Status |
|-----------|-------|--------|
| test_chrome_visible_launch.py | 23 | PASS |
| test_w0_packet_required_routing.py | 20 | PASS |
| test_local_worker_visible_chrome_gate.py | 14 | PASS |
| test_environment_work_packet.py | (existing) | PASS |
| test_environment_packet_validator.py | (existing + updated) | PASS |
| test_local_pull_protocol.py | (existing) | PASS |
| test_vps_local_bridge.py | (existing) | PASS |
| test_tmux_surface.py | (existing) | PASS |
| test_local_worker_bootstrap_status.py | (existing) | PASS |
| test_w_gdrive_cu_001_maturity.py | (existing) | PASS |
| test_w_gdocs_cu_001_maturity.py | (existing) | PASS |
| **Total** | **177** | **ALL PASS** |

---

## Files Created

| File | Purpose |
|------|---------|
| core/environment_bridge/chrome_visible_launch.py | Chrome visible launch gate module |
| core/environment_bridge/w0_packet_builder.py | W0-001 packet builder |
| tests/test_chrome_visible_launch.py | 23 tests for visible launch |
| tests/test_w0_packet_required_routing.py | 20 tests for packet routing |
| tests/test_local_worker_visible_chrome_gate.py | 14 tests for gate logic |
| docs/operations/visible_chrome_launch_gate_v1.md | Gate doctrine |
| docs/operations/local_pull_worker_as_tmux_relay_v1.md | Relay doctrine |

## Files Updated

| File | Change |
|------|--------|
| eos_ai/substrate/local_worker_auto_loop.py | Direct Chrome launch, visible-window proof, gate blocking |
| core/environment_bridge/work_packet.py | Added routing fields to WorkPacket |
| core/environment_bridge/packet_validator.py | Added routing field validation |
| data/work_queue/outbox/w0_001_cu_rerun_while_present_packet.json | Regenerated with all fields |
| tests/test_environment_packet_validator.py | Added routing fields to valid CU test |
| docs/system/w0_001_cu_execution_observation_checklist.md | Added Chrome visible launch pre-check |
| docs/system/phase968b_local_worker_bootstrap_packet.md | Updated status table |

---

## Remaining Next Steps

1. Commit Phase 96.8D
2. Push to origin
3. Pull on local WSL
4. Recopy regenerated packet to local inbox
5. Rerun local worker
6. Verify Chrome direct visible launch
7. Proceed to VERIFY_ACTIVE_GOOGLE_ACCOUNT after visible window confirmed

---

## Status

| Item | Status |
|------|--------|
| Memory promoted | NO |
| Committed | NO (awaiting explicit instruction) |
| Pushed | NO |
| W0-001 CU executed | NO |
| Drive/Docs accessed | NO |
| Secrets captured | NO |
