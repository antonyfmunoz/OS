# Phase 12 — Persistent Advisor Runtime + Session System + Multi-Node Orchestration v1

**Date:** 2026-04-30
**Status:** COMPLETE
**Tests:** 44 passed (Phase 12) + 215 passed (11B-11F regression)

---

## Session System

`umh/runtime/session.py`

Sessions provide temporal boundaries for the organism's operation.

- `SessionType`: DAY | NIGHT
- `SessionState`: ACTIVE | COMPLETED | ABORTED
- `Session`: tracks session_id, type, state, start/end times, active cells
- `SessionManager`: enforces single-active-session invariant

Key constraint: only ONE session may be active at a time. Attempting
to start a second raises RuntimeError.

## Advisor Runtime

`umh/runtime/advisor.py`

The advisor is the organism's persistent decision-maker:
- Spawns and owns a root MONITOR cell as the "advisor cell"
- Monitors brain signals for new information
- Spawns worker cells in response to objectives
- Attaches/detaches cells to the active session
- Tracks tick count and processed signals
- Provides `get_state()` for full snapshot retrieval

The advisor NEVER:
- Imports subprocess or environments
- Executes directly
- Bypasses the control plane

It ONLY:
- Interprets signals
- Spawns cells (via CellRuntime)
- Manages session lifecycle

## Runtime Loop

`umh/runtime/loop.py`

Non-blocking tick-based loop that drives the advisor:

```
tick():
  1. Read new signals from brain signal store
  2. Process each signal through advisor
  3. Cleanup terminated cells
  4. Return tick result
```

Safety: bounded to 10,000 ticks maximum. No blocking operations.
Deterministic: same state produces same actions.

## Node Registry

`umh/nodes/registry.py`

Multi-device node tracking:
- `DeviceNode`: node_id, device_type (LOCAL/VPS), hostname, capabilities, telemetry
- `DeviceNodeRegistry`: register, unregister, list, update telemetry
- `detect_local_node()`: auto-detects the current machine as LOCAL

## Node Routing

`umh/nodes/routing.py`

Pure function for LOCAL vs VPS task placement:

```
route_task(nodes, telemetry, prefer_local, high_compute) -> DeviceNode | None
```

Priority:
1. LOCAL if available and load < 0.75
2. VPS as fallback (lowest load)
3. ANY available node as last resort

Pure function: no global state, no I/O, accepts telemetry as input.

## Workflow Executor

`umh/workflows/executor.py`

Objective decomposition and cell-based execution:
- Accepts an objective string + optional step definitions
- Creates a CellWorkflow and starts it via CellOrchestrator
- Each step spawns a cell that may request_execution()
- No direct environment calls — cells go through the bridge

## Full Execution Flow

```
User Objective
  -> Control Plane (future)
  -> AdvisorRuntime.spawn_worker()
  -> CellRuntime.spawn_cell()
  -> Cell request_execution()
  -> CellControlBridge.submit_request()
  -> Planning Layer
  -> Execution Spine
  -> EnvironmentRuntime.execute()
  -> ContainerManager.run_task()
  -> Result
  -> Signal emitted
  -> Advisor reads signal on next tick
```

## Invariants Preserved

1. Cells NEVER execute — verified by boundary tests
2. Cells NEVER import environments — verified by boundary tests
3. All execution flows through control plane — advisor only spawns cells
4. Execution layer is the ONLY place touching subprocess/docker
5. Scheduler remains pure (no global state) — telemetry passed as input
6. Sandbox always runs before execution — unchanged from 11F
7. Memory writes go through memory subsystem — no new memory paths
8. Cleanup always guaranteed — advisor.stop() terminates all cells
9. No global mutable state introduced — all state in class instances

## Files Created

- `umh/runtime/__init__.py` — package init
- `umh/runtime/session.py` — session system
- `umh/runtime/advisor.py` — persistent advisor
- `umh/runtime/loop.py` — tick-based runtime loop
- `umh/nodes/__init__.py` — package init
- `umh/nodes/registry.py` — multi-device node registry
- `umh/nodes/routing.py` — pure routing function
- `umh/workflows/__init__.py` — package init
- `umh/workflows/executor.py` — workflow executor
- `tests/unit/test_phase12_runtime.py` — 44 tests
- `docs/audits/phase12_runtime_report.md` — this file

## Test Summary

| Suite | Tests | Result |
|-------|-------|--------|
| Phase 12 runtime | 44 | all passed |
| Phase 11F execution | 40 | all passed |
| Phase 11E environment | 37 | all passed |
| Phase 11D orchestration | 41 | all passed |
| Phase 11C cells | 44 | all passed |
| Phase 11C brain context | 14 | all passed |
| Phase 11B brains | 39 | all passed |
| **Total** | **259** | **all passed** |

## Known Limitations

- No distributed node discovery (manual VPS registration)
- No mesh networking
- No GPU scheduling
- No persistent DB-backed sessions (in-memory only)
- Advisor signal processing is a stub (logs signals, no reactive logic yet)
- No remote node execution
- Advisor reconstruction from memory is partial (get_state/clear pattern)

## Is Phase 13 Safe?

Yes. Phase 12 adds three clean packages with no cross-contamination:
- `umh/runtime/` coordinates but never executes
- `umh/nodes/` tracks devices but never calls them
- `umh/workflows/` decomposes objectives through existing orchestrator

Phase 13 can safely build:
- Reactive advisor logic (signal -> cell spawning rules)
- Persistent sessions (DB-backed)
- Remote node heartbeat protocol
- GPU scheduling
- Advisor memory integration
