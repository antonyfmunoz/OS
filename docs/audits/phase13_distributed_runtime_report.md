# Phase 13 — Distributed Runtime + Remote Node Heartbeats + Resilient Routing v1

**Date:** 2026-04-30
**Status:** COMPLETE
**Tests:** 55 passed (Phase 13) + 259 passed (11B-12 regression)

---

## What Changed After Phase 12

Phase 12 introduced the node registry and a pure routing function.
Phase 13 builds the distributed awareness layer on top:

- Heartbeat protocol for temporal liveness tracking
- Health state machine with defined transitions
- Remote execution abstraction (protocol + mock)
- Failover routing with health-aware selection
- Runtime loop integration for stale-node detection

## Heartbeat Protocol

`umh/nodes/heartbeat.py`

NodeHeartbeat is a frozen dataclass carrying:
- node_id, timestamp, status (OK/DEGRADED/OFFLINE/UNKNOWN)
- telemetry dict, capabilities dict, runtime_version, metadata

HeartbeatMonitor:
- `record_heartbeat()` — stores latest heartbeat per node
- `is_stale()` — compares age against configurable threshold (default 60s)
- `node_status()` — derives OK/DEGRADED/OFFLINE/UNKNOWN from heartbeat
- `list_stale_nodes()` — batch staleness check
- Deterministic: `now` parameter for testable time injection

No network calls. Pure in-memory store.

## Node Health State Machine

`umh/nodes/health.py`

Five states: UNKNOWN → HEALTHY → DEGRADED → OFFLINE → RECOVERING

Transitions:
- OK heartbeat + fresh → HEALTHY
- DEGRADED heartbeat → DEGRADED
- High load (>85%) → DEGRADED
- Stale/missing → OFFLINE (increments failure_count)
- OFFLINE + new OK heartbeat → RECOVERING (increments recovery_count)
- RECOVERING + next OK heartbeat → HEALTHY

NodeHealthManager:
- `update_from_heartbeat()` — drives state machine
- `mark_failure()` / `mark_recovered()` / `mark_stale()` — manual overrides
- `list_healthy()` / `list_available()` — query methods

## Remote Execution Abstraction

`umh/nodes/remote.py`

RemoteNodeClient protocol defines the interface:
- `ping(node)` → bool
- `submit_execution(node, task)` → RemoteExecutionRecord
- `fetch_result(node, task_id)` → RemoteExecutionRecord | None
- `cancel(node, task_id)` → bool

RemoteExecutionStatus: ACCEPTED | RUNNING | SUCCEEDED | FAILED | UNREACHABLE | CANCELLED

Phase 13 implementations:
- MockRemoteNodeClient — fully functional mock with reachability toggle
- Real SSH/WebSocket transport deferred to Phase 14+

This is an **interface boundary**, not fake execution. The mock is explicit
about being a mock. No real remote execution is pretended.

## Failover Routing

`umh/nodes/failover.py`

FailoverPolicy (frozen dataclass):
- max_attempts, allow_vps_fallback, allow_local_fallback
- avoid_degraded_nodes, retry_delay_seconds

FailoverRouter:
- `choose_initial_node()` — health-filtered, load-aware, LOCAL-preferred
- `choose_fallback_node()` — excludes failed node, widens to VPS/LOCAL
- `record_failure()` / `record_success()` — track per-node stats
- Deterministic tie-breaking by node_id for reproducibility

Preserves existing routing rules from Phase 12:
1. LOCAL preferred if load < 0.75
2. VPS as fallback (lowest load)
3. Any node as last resort

Adds health filtering:
- OFFLINE nodes excluded
- DEGRADED nodes optionally excluded (policy-controlled)
- RECOVERING nodes treated as degraded (available but not preferred)

## Runtime Loop Integration

`umh/runtime/loop.py` — extended

New optional constructor parameters:
- `heartbeat_monitor: HeartbeatMonitor | None`
- `health_manager: NodeHealthManager | None`

tick() now includes `_poll_node_health()`:
1. Lists stale nodes from heartbeat monitor
2. Marks stale nodes offline via health manager
3. Emits `node.offline` events
4. Never crashes — wrapped in try/except
5. Returns node_updates in tick result

Backward compatible: without heartbeat/health args, loop ticks exactly as Phase 12.

## Full Execution Flow (Updated)

```
User Objective
  -> Control Plane (future)
  -> AdvisorRuntime.spawn_worker()
  -> CellRuntime.spawn_cell()
  -> Cell request_execution()
  -> CellControlBridge.submit_request()
  -> Planning Layer
  -> FailoverRouter.choose_initial_node()    ← NEW
  ->   NodeHealthManager.list_available()    ← NEW
  ->   HeartbeatMonitor.is_stale()           ← NEW
  -> Execution Spine
  -> EnvironmentRuntime.execute()
  -> ContainerManager.run_task()
  -> Result (or failover to choose_fallback_node()) ← NEW
  -> Signal emitted
  -> Advisor reads signal on next tick
  -> RuntimeLoop._poll_node_health()         ← NEW
```

## What Is Real vs Stubbed

| Component | Status |
|-----------|--------|
| Heartbeat recording/staleness | Real |
| Health state machine transitions | Real |
| Failover routing with health | Real |
| Deterministic time injection | Real |
| Remote execution protocol | Interface only |
| MockRemoteNodeClient | Real mock (test use) |
| SSH/WebSocket transport | Not implemented |
| Network heartbeat collection | Not implemented |
| Runtime loop health polling | Real |

## Invariants Preserved

1. Cells NEVER execute — verified by boundary tests
2. Cells NEVER import environments — verified by boundary tests
3. Cells NEVER import nodes — verified by boundary tests
4. All execution flows through control plane — advisor only spawns cells
5. Environment layer is the ONLY place touching subprocess/docker — verified
6. Scheduler/router remain pure functions — telemetry passed as input
7. Sandbox always runs before execution — unchanged from 11F
8. Memory writes go through memory subsystem — no new memory paths
9. No global mutable state — all state in class instances
10. Remote node failure degrades safely — loop catches all exceptions

## Files Created

- `umh/nodes/heartbeat.py` — heartbeat protocol
- `umh/nodes/health.py` — health state machine
- `umh/nodes/remote.py` — remote execution abstraction
- `umh/nodes/failover.py` — failover routing
- `tests/unit/test_phase13_distributed_runtime.py` — 55 tests
- `docs/audits/phase13_distributed_runtime_report.md` — this file

## Files Modified

- `umh/nodes/__init__.py` — added Phase 13 exports
- `umh/runtime/loop.py` — added optional health polling in tick

## Test Summary

| Suite | Tests | Result |
|-------|-------|--------|
| Phase 13 distributed | 55 | all passed |
| Phase 12 runtime | 44 | all passed |
| Phase 11F execution | 40 | all passed |
| Phase 11E environment | 37 | all passed |
| Phase 11D orchestration | 45 | all passed |
| Phase 11C cells + brain | 54 | all passed |
| Phase 11B brains | 39 | all passed |
| **Total** | **314** | **all passed** |

## Known Limitations

- No real SSH/WebSocket node transport yet
- No P2P mesh networking
- No remote Docker execution
- No encrypted node identity
- No durable DB-backed node registry (in-memory only)
- No GPU scheduling
- No automatic heartbeat emission (nodes must push heartbeats)
- No distributed consensus for health state
- Failover retry is policy-defined but not automatically executed (caller drives retries)

## Is Phase 14 Safe?

Yes. Phase 13 adds four clean modules with no cross-contamination:
- `heartbeat.py` stores and checks liveness data
- `health.py` tracks state transitions, imports only heartbeat
- `remote.py` defines protocol + mock, imports only registry
- `failover.py` routes with health awareness, imports health + registry

Phase 14 can safely build:
- Real SSH/WebSocket transport implementing RemoteNodeClient
- Automatic heartbeat emission from nodes
- DB-backed health persistence
- GPU scheduling via capabilities dict
- Automatic failover retry in execution runtime
- Remote container management
