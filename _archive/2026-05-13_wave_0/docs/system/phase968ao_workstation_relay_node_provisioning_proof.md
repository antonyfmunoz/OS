# Phase 96.8AO — Workstation Relay Node Provisioning Proof

Phase: 96.8AO
Date: 2026-05-09
Status: PROVEN

## What Was Built

Provisioned the real Windows workstation relay node into the UMH substrate so that the control plane can move from L0_SIMULATED to real observed actuation when the founder's Windows desktop relay comes online.

## Architecture

```
VPS Control Plane (Linux)
  └── WorkstationNodeRegistry
       └── reads heartbeat.json ← written by Windows relay
            └── RelayHeartbeat dataclass
                 └── evaluates health (alive/degraded/timeout/dead)
                      └── WorkstationRelayNode
                           └── is_execution_capable?
                                └── maturity_ceiling
```

```
Windows Desktop (PowerShell)
  └── start_windows_relay_node.ps1
       ├── generates node identity (WRN-{sha256[:8]})
       ├── checks Chrome availability
       ├── checks desktop state (session/unlock/monitor)
       ├── starts relay as background job
       └── heartbeat loop (10s interval)
            └── writes heartbeat.json
```

## Files Created

### core/workstation/ (4 modules)

| File | Purpose |
|------|---------|
| workstation_relay_node_v1.py | WorkstationRelayNode dataclass, is_execution_capable property, load from heartbeat |
| workstation_relay_heartbeat_v1.py | RelayHeartbeat dataclass, read/write/evaluate health, is_relay_online |
| workstation_node_registry_v1.py | WorkstationNodeRegistry class, get_relay_status for !relay-status |
| workstation_relay_proof_v1.py | classify_relay_proof, persist_relay_proof, compute_proof_hash |

### scripts/

| File | Purpose |
|------|---------|
| start_windows_relay_node.ps1 | PowerShell startup script for Windows relay node |

### config/

| File | Purpose |
|------|---------|
| w0_workstation_relay_node_v1.json | Relay config (heartbeat interval, stale threshold, paths) |

### tests/

| File | Purpose |
|------|---------|
| test_workstation_relay_node_v1.py | 37 tests across 10 classes |

## Files Modified

| File | Change |
|------|--------|
| core/registry/canonical_command_registry_v1.py | Added !relay-status as 13th command |
| config/control_plane_router_v1.json | Added relay_status to allowed_action_types |
| core/control_plane_router/router_contracts.py | Added relay_status to ALLOWED_ACTION_TYPES frozenset |
| core/control_plane_router/control_plane_router_v1.py | Added relay_status to ACTION_CAPABILITY_MAP |
| data/registries/local_worker_adapter_registry_v1.json | Added relay_status capability to adapter and workers |
| services/handlers/substrate_command_handler.py | Added _handle_relay_status handler |
| tests/test_canonical_registry_bootstrap_v1.py | Updated counts from 12→13, added !relay-status to expected set |
| tests/test_actuator_maturity_v1.py | Updated registry counts from 12→13 |

## Command Registration

`!relay-status` registered at all 6 propagation points:
1. Canonical registry (13th command, router-routed, shell execution)
2. Router config JSON (allowed_action_types)
3. ALLOWED_ACTION_TYPES frozenset
4. ACTION_CAPABILITY_MAP (SHELL_EXECUTION, no GUI required)
5. Adapter registry capabilities
6. Substrate command handler (direct handler, no router dispatch)

## Relay Node Architecture

- Node identity: SHA256 of `machineName:userName:local_windows_desktop`, prefixed with `WRN-`
- Heartbeat path: `data/runtime/workstation_relay/heartbeat.json`
- Stale threshold: 60s (>30s = DEGRADED, >60s = TIMEOUT, no file = DEAD)
- Chrome detection: checks standard install paths
- Desktop state: session active, unlocked, monitor detected
- Capabilities: 7 (launch_chrome, focus_window, navigate_url, capture_screenshot, report_hwnd, report_foreground_window, report_desktop_state)

## Maturity Ceiling Integration

When relay is online with full desktop state:
- chrome_available + desktop_active + desktop_unlocked → up to L5_SCREENSHOT_VERIFIED
- Without founder confirmation → capped at L5
- With founder_confirmed → L6_FOUNDER_CONFIRMED
- Relay offline → L0_SIMULATED

## Test Results

```
116 passed, 0 failed (3 test files)
  - test_workstation_relay_node_v1.py:     37 passed
  - test_canonical_registry_bootstrap_v1.py: 35 passed  
  - test_actuator_maturity_v1.py:          44 passed
```

## Proof

The workstation relay node is provisioned and ready. When the PowerShell startup script runs on the founder's Windows machine, it will:
1. Generate a deterministic node identity
2. Start the existing relay as a background job
3. Begin emitting heartbeats every 10s
4. The VPS control plane will detect the heartbeat and report ONLINE via !relay-status
5. chrome-proof dispatch will be able to verify relay availability before routing
