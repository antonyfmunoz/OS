# Phase 96.8BZ — Adaptive Substrate Resilience Coordination

> Completed: 2026-05-09
> Tests: 140/140 pass (0.42s)
> Prior phases: 2115/2115 pass (14.63s)

---

## Objective

Build adaptive resilience coordination that detects instability,
contains faults, interrupts cascading failures, and recommends
recovery actions — without executing autonomous repairs.

Core principle: Resilience coordination preserves integrity and
continuity without autonomous self-repair. All recovery actions
are RECOMMENDATIONS that require operator approval.

---

## What Was Built

### Contracts (core/resilience/adaptive_resilience_contracts_v1.py)
- 14 data contracts: ResilienceState (rstate-), FaultContainmentState (fcon-),
  InstabilitySignal (isig-), CascadingFailureState (casc-),
  RecoveryCoordinationReceipt (rrcpt-), SubsystemHealthState (sheal-),
  RecoveryBoundaryState (rbnd-), ContinuityPreservationState (cpres-),
  CheckpointIntegrityState (cint-), RecoveryReplayState (rrply-),
  SurvivabilityScore (sscore-), IsolationDecision (isodec-),
  RecoveryRecommendation (rrec-), DegradedSurvivabilityState (dsurv-)
- 5 enums: ResilienceLifecycleState (10), ResilienceEventType (10),
  InstabilityClass (5), IsolationScope (5), RecoveryAction (5)

### Coordinator (core/resilience/canonical_resilience_coordination_engine_v1.py)
- Composes lifecycle + instability + cascade + checkpoint + survivability +
  recommendation + observability engines
- Cannot execute repairs, cannot rollback state, cannot heal autonomously
- Key methods: record_success, record_failure, contain_fault,
  isolate_subsystem, create/validate_checkpoint, assess_survivability,
  begin/validate/complete_recovery, approve/reject_recommendation

### Engines
1. **Instability Detection** (instability_detection_engine_v1.py) — Subsystem health
   tracking with consecutive failure threshold (3). 5-class classification:
   transient (0.2), intermittent (0.4), persistent (0.6), cascading (0.8),
   systemic (0.9). Weighted scoring: unhealthy_ratio * 0.6 + degraded_ratio * 0.4.
2. **Cascading Failure Interruption** (cascading_failure_interruption_engine_v1.py) —
   Propagation tracking with bounded depth (max 3), max affected subsystems (10),
   max active cascades (5). Auto-interruption at limits. Fault containment boundaries.
3. **Checkpoint Integrity** (checkpoint_integrity_engine_v1.py) — SHA-256 state
   checksums. Create/validate lifecycle. Bounded per-subsystem (max 10).
   Continuity preservation state tracking.
4. **Degraded Survivability** (degraded_survivability_engine_v1.py) — 3-factor
   scoring: fault_tolerance (40%) + recovery_capacity (35%) +
   isolation_effectiveness (25%). Critical subsystem awareness
   (spine, governance, continuity). Minimum survivability floor (0.3).
5. **Recovery Recommendation** (recovery_recommendation_engine_v1.py) — Severity-to-
   action mapping. All recommendations require operator approval. Max 20 pending.
   Pending/history tracking. No autonomous execution.
6. **Lifecycle** (resilience_lifecycle_engine_v1.py) — 10-state lifecycle with
   validated transitions: stable→monitored→unstable→degraded→isolated→
   recovering→validated→stabilized→suspended→archived.

### Observability (resilience_observability_pipeline_v1.py)
- 10 event types generated from ResilienceEventType enum
- Dynamic EVENT_FILE_MAP, JSONL per type

### Replay (resilience_replay_validator_v1.py)
- 5 determinism checks: instability_detection, fault_containment,
  cascade_interruption, checkpoint_integrity, recovery_recommendation
- Hash comparison methods for each check

### Boundary Policies (resilience_boundary_policies_v1.py)
- 10 limits: max_recovery_attempts=3, max_isolation_depth=3,
  max_cascade_propagation=3, max_affected_subsystems=10,
  max_active_cascades=5, max_pending_recommendations=20,
  max_checkpoints_per_subsystem=10, max_tracked_subsystems=50,
  minimum_survivability_score=0.3, max_instability_score=1.0
- 10 forbidden actions: autonomous_repair, automatic_rollback,
  self_directed_healing, hidden_state_mutation, uncontrolled_restart,
  recursive_recovery_loops, hidden_isolation_bypass,
  automatic_escalation_execution, uncontrolled_checkpoint_restoration,
  hidden_survivability_override
- Override capping: min(override, default)

### Continuity Bridges (resilience_continuity_bridges_v1.py)
- 8 bridges using _BaseBridge pattern: scaling↔resilience,
  environments↔resilience, operations↔resilience, workflows↔resilience,
  sessions↔resilience, replay↔resilience, continuity↔resilience,
  observability↔resilience

---

## Instability Classification Model

| Class | Threshold | Description |
|-------|-----------|-------------|
| Stable | < 0.2 | No instability detected |
| Transient | 0.2–0.4 | Brief, self-resolving |
| Intermittent | 0.4–0.6 | Recurring, pattern forming |
| Persistent | 0.6–0.8 | Sustained, requires intervention |
| Cascading | 0.8–0.9 | Spreading across subsystems |
| Systemic | >= 0.9 | System-wide instability |

## Survivability Scoring Model

| Factor | Weight | Description |
|--------|--------|-------------|
| Fault tolerance | 40% | Ratio of functional subsystems |
| Recovery capacity | 35% | Available recovery resources |
| Isolation effectiveness | 25% | Containment success rate |

Critical subsystems (spine, governance, continuity): degradation
halves the overall score via 0.5 multiplier.

Minimum survivability floor: 0.3 — below this, can_continue=False.

---

## Constraint Verification

| # | Constraint | Status |
|---|-----------|--------|
| 1 | No autonomous repair | PASS — forbidden action, no repair/fix/heal methods |
| 2 | No automatic rollback | PASS — forbidden action, no rollback/revert methods |
| 3 | No self-directed healing | PASS — forbidden action |
| 4 | No hidden state mutation | PASS — forbidden action, no mutate/force/override methods |
| 5 | No uncontrolled restart | PASS — forbidden action, no restart/reboot methods |
| 6 | No recursive recovery loops | PASS — forbidden action |
| 7 | No execute recovery | PASS — no execute/run/dispatch/invoke methods |
| 8 | Recommendations require approval | PASS — approved=False by default, operator approval required |
| 9 | Bounded cascade propagation | PASS — max depth=3, auto-interruption |
| 10 | Bounded recovery attempts | PASS — max 3 via boundary policy |
| 11 | Bounded isolation depth | PASS — max 3 via boundary policy |
| 12 | Deterministic instability replay | PASS — hash stable |
| 13 | Deterministic containment replay | PASS — hash stable |
| 14 | Deterministic cascade replay | PASS — hash stable |
| 15 | Deterministic checkpoint replay | PASS — hash stable |
| 16 | Deterministic recommendation replay | PASS — hash stable |
| 17 | All forbidden actions enforced | PASS — all 10 forbidden actions checked |
| 18 | No execution outside spine | PASS — no execute/dispatch methods |

---

## Files Created

| File | Purpose |
|------|---------|
| core/resilience/adaptive_resilience_contracts_v1.py | 14 contracts, 5 enums |
| core/resilience/canonical_resilience_coordination_engine_v1.py | Central coordinator |
| core/resilience/resilience_lifecycle_engine_v1.py | 10-state lifecycle |
| core/resilience/instability_detection_engine_v1.py | Subsystem health + classification |
| core/resilience/cascading_failure_interruption_engine_v1.py | Cascade interruption |
| core/resilience/checkpoint_integrity_engine_v1.py | State checkpoints |
| core/resilience/degraded_survivability_engine_v1.py | Survivability assessment |
| core/resilience/recovery_recommendation_engine_v1.py | Recovery recommendations |
| core/resilience/resilience_observability_pipeline_v1.py | 10 event types |
| core/resilience/resilience_replay_validator_v1.py | 5 determinism checks |
| core/resilience/resilience_boundary_policies_v1.py | 10 limits, 10 forbidden |
| core/resilience/resilience_continuity_bridges_v1.py | 8 bridges |
| tests/test_adaptive_substrate_resilience_coordination_v1.py | 140 tests |

---

## Architectural Decisions

1. **Recommendation-only recovery** — The coordinator can detect, classify, contain,
   and recommend — but never repair. This prevents autonomous self-healing that
   could mask systemic issues. The operator reviews recommendations and approves
   action. This is the same "regulation without authority" pattern from 96.8BY.

2. **Consecutive failure threshold (3)** — A subsystem must fail 3 consecutive times
   before being flagged as unhealthy. This filters transient errors from genuine
   instability. The threshold is explicit and fixed, not adaptive.

3. **Critical subsystem awareness** — spine, governance, and continuity are hardcoded
   as critical. Their degradation halves the survivability score via a 0.5 multiplier.
   Total shutdown of critical subsystems forces can_continue=False.

4. **Bounded cascade interruption** — Max propagation depth of 3, max affected
   subsystems of 10, max active cascades of 5. These are the same bounded-resource
   patterns used throughout the substrate. When limits are hit, the cascade is
   automatically interrupted — containment over continuation.

5. **Checkpoint hash integrity** — SHA-256 truncated to 16 characters for state
   checksums. The same data produces the same hash, enabling validation that
   subsystem state hasn't drifted since checkpoint creation.
