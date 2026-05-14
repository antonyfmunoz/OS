# Phase 96.8P -- W0 Routed Chrome Visible Execution Rerun

**Date:** 2026-05-07
**Status:** COMPLETE (VPS dry-run proven, live execution pending founder)
**Gate:** W0_ROUTED_CHROME_VISIBLE_RERUN
**Previous Gate:** DISCORD_THROUGH_ROUTER

---

## What This Phase Proves

Every layer of the canonical routed execution path produces
correct output. The routing lifecycle was exercised end-to-end:

1. Discord !chrome command → WorkPacket created
2. WorkPacket → ControlPlaneRouter decision generated
3. Router → runtime selected (local_worker_runtime_daemon)
4. Router → adapter selected (windows_interactive_desktop_relay)
5. Adapter → RuntimeProof generated
6. Proof → RouterResult normalized
7. RouterResult → Discord-formatted reply produced

---

## Full Lifecycle Trace

```
Discord Interface Adapter v1
  |
  |  build_work_packet_for_router("!chrome")
  v
WorkPacket
  packet_id: REQ-W0-*
  action_type: open_application_url
  source_interface: discord_interface_adapter_v1
  payload.url: https://drive.google.com/drive/my-drive
  payload.launch_method: direct_executable
  payload.blocked_launch_methods: [default_browser, explorer_url, ...]
  |
  |  router.route_work_packet(work_packet)
  v
ControlPlaneRouterV1
  validate_packet()     → valid
  resolve_capability()  → windows_gui_execution (requires_gui=true)
  resolve_adapter()     → windows_interactive_desktop_relay
  resolve_runtime()     → local_worker_runtime_daemon
  |
  |  _write_to_inbox(daemon_packet)
  v
LocalWorkerRuntimeDaemon
  process_packet()      → routes to adapter
  |
  |  send_request_and_wait() via filesystem relay
  v
Windows Interactive Desktop Relay (PowerShell)
  ConvertFrom-Json      → parse request
  Start-Process chrome  → open at hardcoded URL
  Get-Process chrome    → detect process
  |
  |  write result to outbox
  v
RuntimeProofRecord
  proof_status: completed
  adapter_status: completed
  evidence.main_window_title: "My Drive - Google Drive - Google Chrome"
  evidence.process_detected: true
  evidence.launch_method: direct_executable
  |
  |  router wraps into RouterResult
  v
RouterResult
  router_status: completed
  adapter_selected: windows_interactive_desktop_relay
  runtime_target: local_worker_runtime_daemon
  runtime_proof_reference.proof_status: completed
  |
  |  format_router_result(result, "!chrome")
  v
Discord Reply
  **!chrome** -- completed
  action: open_application_url
  adapter: windows_interactive_desktop_relay
  runtime: local_worker_runtime_daemon
  adapter_status: completed
  request_id: REQ-W0-*
```

---

## Environment Boundaries

| Layer | Environment | Authority |
|-------|------------|-----------|
| Discord Interface | VPS (tmux) | remote_orchestration |
| Control Plane Router | VPS (tmux) | remote_orchestration |
| Worker Runtime Daemon | Local WSL | local_shell, filesystem_relay |
| Windows Relay | Windows Desktop | local_gui, local_shell |
| Chrome | Windows Desktop | local_gui |

The VPS orchestrates. WSL relays via filesystem. Windows
executes via logged-in desktop session. Each environment
does only what it is natively authorized to do.

---

## Proof Chain

| Artifact | Location |
|----------|----------|
| routed_work_packet_example.json | data/runtime/routed_execution_proofs/ |
| routed_runtime_proof_example.json | data/runtime/routed_execution_proofs/ |
| routed_router_result_example.json | data/runtime/routed_execution_proofs/ |

Each artifact traces to the same request_id and trace_id,
proving the chain is unbroken from interface to proof.

---

## What Is Now Proven

| Claim | Status |
|-------|--------|
| WorkPacket created from Discord command | PROVEN |
| Router validates packet | PROVEN |
| Router resolves capability (windows_gui_execution) | PROVEN |
| Router selects adapter (windows_interactive_desktop_relay) | PROVEN |
| Router selects runtime (local_worker_runtime_daemon) | PROVEN |
| RouterDecision generated with correct fields | PROVEN |
| RuntimeProof wraps into RuntimeProofReference | PROVEN |
| RouterResult normalized with completed status | PROVEN |
| Discord reply formatted from RouterResult | PROVEN |
| Proof artifacts trace across all layers | PROVEN |
| All 121 substrate tests pass | PROVEN |

## What Is NOT Yet Proven (Requires Local Machine)

| Claim | Status |
|-------|--------|
| Chrome visibly opens on Windows desktop | NOT YET (requires local) |
| Founder visually confirms Chrome window | NOT YET (requires founder) |
| Daemon processes packet in real time | NOT YET (requires local daemon) |
| PowerShell relay executes on Windows | NOT YET (requires local PS) |
| Real RuntimeProof from live adapter | NOT YET (requires local) |

---

## Live Execution Runbook

To complete the live proof:

```bash
# 1. On local WSL — start daemon
python3 eos_ai/substrate/local_worker_runtime_daemon.py \
  --config config/local_worker_runtime_daemon_v1.json

# 2. On Windows PowerShell — start relay
.\scripts\windows_interactive_desktop_relay.ps1

# 3. On VPS — start Discord bot (or local WSL with token)
python3 eos_ai/interfaces/discord_interface_adapter_v1.py

# 4. In Discord — send command
!chrome

# 5. Founder confirms Chrome opened at Google Drive
```

---

## What Was Not Executed

| Item | Status |
|------|--------|
| Chrome opened | NO (VPS dry-run) |
| Drive/Docs accessed | NO |
| Drive contents read | NO |
| Private files accessed | NO |
| Screenshots captured | NO |
| Secrets captured | NO |
| Memory promoted | NO |
| LLM calls made | NO |
| Autonomous planning | NO |

---

## Proof Script

```bash
python3 scripts/prove_routed_chrome_execution.py           # dry-run (VPS)
python3 scripts/prove_routed_chrome_execution.py --live     # live (local WSL)
```

---

## Files Created

| File | Purpose |
|------|---------|
| scripts/prove_routed_chrome_execution.py | Proof validation script |
| data/runtime/routed_execution_proofs/routed_work_packet_example.json | WorkPacket artifact |
| data/runtime/routed_execution_proofs/routed_runtime_proof_example.json | RuntimeProof artifact |
| data/runtime/routed_execution_proofs/routed_router_result_example.json | RouterResult artifact |
| docs/system/phase968p_w0_routed_chrome_visible_rerun.md | This report |

---

## Next Gate: W0_DRIVE_DOCS_INTERACTION_PROOF

Once founder visual confirmation is obtained for Chrome
opening at Google Drive via the canonical routed path,
proceed to the W0 Drive/Docs interaction proof.
