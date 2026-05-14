# Phase 96.8BW — Governed Long-Horizon Operational Execution

> Completed: 2026-05-09
> Tests: 113/113 pass (0.39s)
> Prior phases: 330/330 pass (0.79s)

---

## Objective

Build governed long-horizon operational execution: bounded sequences of spine
traversals across time. Campaigns with staged execution, dependency tracking,
deferred execution, approval gates, checkpoints, continuation, and full
observability — all without autonomous objective generation or direct adapter
execution.

---

## What Was Built

### Contracts (core/operations/long_horizon_operational_contracts_v1.py)
- 12 data contracts: OperationalObjective (opobj-), OperationalCampaign (opcmp-),
  ExecutionStage (opstg-), DeferredExecutionState (opdef-), ExecutionDependency (opdep-),
  OperationalCheckpoint (opchkp-), OperationalConstraint (opcon-),
  OperationalApprovalState (opapv-), OperationalExecutionReceipt (oprcpt-),
  OperationalProgressState, OperationalWaitingState (opwait-),
  OperationalContinuationState (opcont-)
- 4 enums: OperationalLifecycleState (12 states), OperationalEventType (12 types),
  DependencyType (6 types), ChronologyEventKind (10 kinds)

### Coordinator (core/operations/canonical_long_horizon_execution_coordinator_v1.py)
- Composes lifecycle + dependencies + deferred + continuation + chronology + graph engines
- Cannot execute adapters directly, cannot generate objectives
- Dispatches ONLY through spine.process()
- Key methods: create_objective (hardcodes set_by="operator"), create_campaign,
  start_stage, complete_stage, fail_stage, defer_stage, request_approval,
  grant_approval, suspend/resume/terminate_campaign, checkpoint_campaign

### Engines
1. **Lifecycle** (operational_lifecycle_engine_v1.py) — 12-state lifecycle with
   validated transitions. Terminal: terminated. Final: completed, failed, archived, terminated.
2. **Dependencies** (operational_dependency_engine_v1.py) — Dependency tracking with
   DFS cycle prevention, topological execution ordering, satisfaction propagation.
3. **Deferred** (deferred_execution_engine_v1.py) — Governed deferral with resume
   conditions, waiting state management, active tracking, JSONL persistence.
4. **Continuation** (operational_continuation_engine_v1.py) — Checkpoint creation with
   deterministic content hashes, continuation states, hash verification, JSON + JSONL.
5. **Chronology** (operational_chronology_engine_v1.py) — 10 event kinds, monotonic
   sequence numbers, per-campaign isolation, JSONL persistence.
6. **Execution Graph** (operational_execution_graph_engine_v1.py) — Objective→campaign→stage
   graph, deterministic hashes, JSON individual files + JSONL ledger.

### Observability (core/operations/operational_observability_pipeline_v1.py)
- 12 event types generated from OperationalEventType enum
- Dynamic EVENT_FILE_MAP, JSONL per type, convenience emit methods

### Replay (core/operations/operational_replay_validator_v1.py)
- 6 determinism checks: chronology_replay, dependency_progression, deferred_restoration,
  continuation_replay, stage_transitions, approval_routing
- Session-level validation, proof file generation

### Boundary Policies (core/operations/operational_boundary_policies_v1.py)
- 8 limits: max_stages_per_campaign=20, max_active_campaigns=5, max_execution_depth=10,
  max_continuation_depth=5, max_deferred_per_campaign=10, max_fanout=3,
  max_approval_wait_hours=72, max_campaign_duration_hours=168
- 10 forbidden actions: self_generated_objective, autonomous_campaign_creation,
  recursive_continuation, hidden_deferred_execution, uncontrolled_fanout,
  infinite_progression, orphan_execution_graph, background_autonomous_execution,
  self_directed_execution, independent_task_spawning
- Override capping: min(override, default) — can only tighten

### Continuation Bridges (core/operations/operational_continuation_bridges_v1.py)
- 7 bridges using _BaseBridge pattern: session↔ops, workflow↔ops, cognition↔ops,
  embodiment↔ops, observability↔ops, replay↔ops, ingress↔ops
- JSONL persistence for cross-layer operational lineage

---

## Constraint Verification

| # | Constraint | Status |
|---|-----------|--------|
| 1 | No autonomous objective generation | PASS — set_by="operator" hardcoded |
| 2 | No recursive continuation | PASS — boundary limits continuation_depth |
| 3 | No uncontrolled deferred execution | PASS — boundary limits deferred_per_campaign |
| 4 | No hidden scheduling | PASS — hidden_deferred_execution + background_autonomous_execution forbidden |
| 5 | No execution outside spine | PASS — coordinator has no execute/dispatch methods |
| 6 | Deterministic dependency replay | PASS — topological order stable across runs |
| 7 | Deterministic chronology replay | PASS — content hashes stable |
| 8 | Deterministic continuation replay | PASS — checkpoint hashes deterministic |
| 9 | Bounded execution fanout | PASS — boundary limits fanout |
| 10 | Bounded continuation depth | PASS — boundary limits continuation_depth |
| 11 | Explicit approval enforcement | PASS — unapproved stages cannot start |
| 12 | No orphan execution graphs | PASS — campaign creation always creates graph |
| 13 | No workflow-owned objectives | PASS — self_generated_objective + autonomous_campaign_creation forbidden |
| 14 | No cognition-owned execution | PASS — self_directed_execution forbidden |
| 15 | No session-owned intentionality | PASS — self_directed_execution + independent_task_spawning forbidden |
| 16 | No autonomous operational escalation | PASS — infinite_progression + uncontrolled_fanout forbidden |

---

## Files Created

| File | Purpose |
|------|---------|
| core/operations/long_horizon_operational_contracts_v1.py | 12 contracts, 4 enums |
| core/operations/canonical_long_horizon_execution_coordinator_v1.py | Central coordinator |
| core/operations/operational_lifecycle_engine_v1.py | 12-state lifecycle |
| core/operations/operational_dependency_engine_v1.py | Dependency tracking + cycle prevention |
| core/operations/deferred_execution_engine_v1.py | Deferred execution + waiting states |
| core/operations/operational_continuation_engine_v1.py | Checkpoints + continuations |
| core/operations/operational_chronology_engine_v1.py | Chronology with 10 event kinds |
| core/operations/operational_observability_pipeline_v1.py | 12 event types, JSONL |
| core/operations/operational_replay_validator_v1.py | 6 determinism checks |
| core/operations/operational_boundary_policies_v1.py | 8 limits, 10 forbidden actions |
| core/operations/operational_execution_graph_engine_v1.py | Execution graph management |
| core/operations/operational_continuation_bridges_v1.py | 7 continuation bridges |
| tests/test_governed_long_horizon_operational_execution_v1.py | 113 tests |

---

## Architectural Decisions

1. **Override capping via min()** — Operator overrides can only tighten boundaries, never
   loosen them. min(override, default) pattern prevents escalation.

2. **DFS cycle prevention** — Dependencies checked for cycles before insertion using depth-first
   search, preventing cyclic execution graphs from ever forming.

3. **Campaign auto-completion** — When all stages reach terminal state, campaign transitions
   automatically. If any stage failed, campaign fails; otherwise completes.

4. **12-state lifecycle** — Most granular lifecycle in the substrate. Includes waiting, approved,
   deferred, resumed, suspended, and archived states to model every real operational transition.

5. **Dynamic EVENT_FILE_MAP** — Generated from OperationalEventType enum values rather than
   hardcoded, ensuring every event type always has a persistence target.
