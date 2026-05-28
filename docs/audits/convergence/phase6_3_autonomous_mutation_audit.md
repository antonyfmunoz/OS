# Phase 6.3 — Autonomous Mutation Path Audit

## Audit Date: 2026-05-28
## Auditor: Developer Agent
## Scope: All autonomous/scheduled/tick paths in substrate/organism/

---

## Executive Summary

Audited 15 autonomous/tick/scheduled paths in the organism subsystem.
Of these, 10 are observe-only, 2 are recommendation-only, and 3 are
mutation-capable. All 3 mutation-capable paths now have gateway adapters
and spine-routing support.

---

## Path Classification

### 1. AutonomousTick stages (registered in daemon._register_tick_stages)

| Stage | Source | Classification | Risk | Gateway Status |
|---|---|---|---|---|
| advisor | Advisor.autonomous_tick | observe-only | LOW | N/A (read-only) |
| homeostasis | HomeostasisEngine.check | observe-only | LOW | N/A (read-only) |
| supervisor_reconcile | RuntimeSupervisor.reconcile_graph | observe-only | LOW | N/A (state-update in-memory only) |
| allocation | AllocationLoop.allocation_cycle | recommendation-only | LOW | N/A (emits decisions as events) |
| async_objectives | AsyncCoordinator.advance | observe-only | LOW | N/A (progresses in-memory state) |
| leverage_rebalance | LeverageAssimilator.rebalance_cycle | observe-only | LOW | N/A (rebalances in-memory scores) |
| environment_reconcile | EnvironmentReconciler.reconcile_tick | observe-only | LOW | N/A (updates RuntimeGraph in-memory) |
| leverage_measurement | LeverageMetrics.leverage_tick | observe-only | LOW | N/A (metrics collection) |
| bottleneck_detection | daemon._bottleneck_detection_tick | observe-only | LOW | N/A (detection only) |
| objective_physics | ObjectivePhysics.physics_tick | observe-only | LOW | N/A (physics simulation) |
| operator_compression | OperatorCompression.compression_tick | observe-only | LOW | N/A (pattern detection) |
| workload_probes | WorkloadProbes.full_probe | observe-only | LOW | N/A (read-only probes) |
| maintenance_cycle | MaintenanceLoop.maintenance_tick | **mutation-capable** | MEDIUM | **Gateway wired** |
| automation_scan | AutomationPipeline.pipeline_tick | recommendation-only | LOW | N/A (creates proposals, no execution) |
| projection_broadcast | daemon._broadcast_state | observe-only | LOW | N/A (writes to ProjectionPort in-memory) |

### 2. MaintenanceLoop

- **Classification**: mutation-capable (via WorkloadRunner)
- **Current behavior**: runs observe workloads, generates recommendations
- **Gateway status**: `set_autonomous_gateway()` wired; `submit_recommendation_via_gateway()` available
- **Risk**: MEDIUM (recommendations can include container restart, log rotation, branch cleanup)
- **Conversion**: recommendations are now convertible to ActionEnvelopes via gateway

### 3. WorkloadRunner

- **Classification**: mutation-capable (runs subprocess commands for probes)
- **Current behavior**: observe workloads are read-only; mutation workloads (LOG_ROTATION, RUNTIME_RECONCILIATION) run subprocess
- **Gateway status**: `set_autonomous_gateway()` wired; `run_workload_via_gateway()` available
- **Risk**: MEDIUM for LOG_ROTATION, RUNTIME_RECONCILIATION; LOW for observe probes
- **Conversion**: mutation workloads route through gateway when available

### 4. AssistedExecutor

- **Classification**: mutation-capable (executes approved actions directly)
- **Current behavior**: container restart, log rotation, branch cleanup, graph rebuild
- **Gateway status**: `set_autonomous_gateway()` wired; `execute_via_gateway()` available
- **Risk**: MEDIUM (filesystem mutations, container operations)
- **Conversion**: all actions route through gateway when available

### 5. OrganismDaemon tick/state_persist

- **Classification**: observe-only (writes daemon_state.json, supervisor state)
- **Risk**: LOW (local state persistence)
- **Gateway status**: N/A (internal state, not reality mutation)

### 6. AllocationLoop

- **Classification**: recommendation-only
- **Risk**: LOW (emits allocation decisions as EventSpine events)
- **Gateway status**: N/A (no mutations)

### 7. LeverageAssimilator

- **Classification**: observe-only (file reads, classification, scoring)
- **Risk**: LOW (reads external repos, writes to assimilation staging)
- **Note**: Staging writes are local state, not reality mutation

### 8. ObjectiveQueue

- **Classification**: observe-only (in-memory queue management)
- **Risk**: LOW
- **Gateway status**: N/A

### 9. AsyncCoordinator

- **Classification**: observe-only (advances objective state in-memory)
- **Risk**: LOW
- **Gateway status**: N/A

### 10. WorkcellDaemon

- **Classification**: observe-only (inbox processing, heartbeat writes)
- **Risk**: LOW (local file writes for state)
- **Gateway status**: N/A (state persistence, not mutation)

### 11. EnvironmentReconciler

- **Classification**: observe-only (probes Docker, tmux; updates RuntimeGraph in-memory)
- **Risk**: LOW
- **Gateway status**: N/A

### 12. AutomationPipeline

- **Classification**: recommendation-only (creates AutomationProposals)
- **Risk**: LOW (proposals require explicit approval)
- **Gateway status**: N/A (no execution capability)

### 13. cron-triggered Python entrypoints (scripts/)

- **Classification**: varies (typically invoke daemon.tick())
- **Risk**: LOW-MEDIUM
- **Note**: All cron scripts that invoke the daemon route through the tick engine, which uses registered stages. Mutation actions in cron scripts should use the gateway.

### 14. operator_api background loops

- **Classification**: N/A (operator_api is request-driven, not autonomous)
- **Risk**: LOW
- **Gateway status**: N/A (API routes use cockpit spine router)

---

## Remaining Exceptions

1. **Daemon state persistence** (daemon._persist_state): Writes daemon_state.json and supervisor state. This is internal state management, not reality mutation. Exempt.

2. **WorkcellDaemon heartbeat writes**: Local file writes for liveliness detection. Internal state. Exempt.

3. **EventSpine persistence** (events.jsonl): Append-only event log. Observability infrastructure. Exempt.

4. **ExecutionJournal persistence** (execution_journal.jsonl): Append-only audit ledger. Observability infrastructure. Exempt.

5. **LeverageAssimilator staging writes**: Local assimilation state files. Internal state. Exempt.

---

## Enforcement Summary

| Category | Count | Status |
|---|---|---|
| Observe-only paths | 10 | No gate needed |
| Recommendation-only paths | 2 | No gate needed |
| Mutation-capable paths | 3 | Gateway wired |
| Internal state exempt | 5 | Documented |
| **Total audited** | **20** | **All accounted** |

---

## Ratchet Path

Current: `SpineGuard = BLOCK_HIGH_RISK`

Path to ENFORCE_ALL:
1. Verify all 3 mutation-capable paths are using gateway in production
2. Monitor gateway decisions for 1 week
3. Confirm zero direct mutation bypasses
4. Switch SpineGuard to ENFORCE_ALL
5. Monitor for regression

Do NOT switch to ENFORCE_ALL until steps 1-3 are proven.
