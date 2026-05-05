# Phase 33: Goal Persistence + Commitment Engine v1 — Audit Report

**Date**: 2026-04-30
**Status**: COMPLETE
**Tests**: 113 passed, 0 failed
**Regression**: 1891 passed (phases 11-33), 0 regressions

---

## Deliverables

### New Modules (2)

| File | Purpose | Lines |
|------|---------|-------|
| `umh/runtime/goal_state.py` | GoalState (frozen), GoalStateManager (get/set/update/abandon/clear) | ~174 |
| `umh/runtime/commitment.py` | CommitmentDecision enum, SwitchingCost, CommitmentResult, CommitmentEngine | ~343 |

### Modified Modules (2)

| File | Changes |
|------|---------|
| `umh/runtime/advisor.py` | Added `commitment_engine`, `goal_state_manager` constructor params; `_commit_to_goal()` method in tick; `goal_committed`/`goal_decision` tick keys; `goal_state`/`commitment` in `get_state()`; goal manager clear in `clear()` |
| `umh/runtime/__init__.py` | Added 6 new exports (CommitmentDecision, CommitmentEngine, CommitmentResult, GoalState, GoalStateManager, SwitchingCost) |

### Test File (1)

| File | Tests |
|------|-------|
| `tests/unit/test_phase33_goal_persistence.py` | 113 |

---

## Architecture

```
Meta-planner / Arbitration
        │
        ▼  candidate objective (best from planning)
        │
CommitmentEngine.decide(current_state, candidate, tick)
        │
        ├─── CONTINUE → keep active objective
        │
        ├─── SWITCH   → apply penalty, adopt candidate
        │                (only if net improvement > min_improvement
        │                 AND score_gap > switch_threshold)
        │
        └─── ABANDON  → clear active (stalled or low-value)
        
GoalStateManager
        │
        ├─── set_active()        → commit to objective
        ├─── update_progress()   → explicit progress update
        ├─── update_commitment() → explicit commitment update
        ├─── abandon()           → archive and clear
        └─── clear()             → reset all state
```

---

## Goal State Model

### GoalState (frozen dataclass)

| Field | Type | Description |
|-------|------|-------------|
| active_objective | Objective | The currently committed objective |
| start_tick | int | Tick when this objective was committed |
| progress | float | Progress toward completion [0.0, 1.0] |
| commitment_score | float | How committed the system is [0.0, 1.0] |

Methods: `elapsed_ticks(current_tick)`, `with_progress(v)`, `with_commitment(v)`, `to_dict()`

### GoalStateManager

| Method | Effect |
|--------|--------|
| `set_active(obj, tick)` | Archives previous, sets new active |
| `update_progress(v)` | Returns new GoalState with updated progress |
| `update_commitment(v)` | Returns new GoalState with updated commitment |
| `abandon()` | Archives active, clears active |
| `clear()` | Clears all state (active + history) |

---

## Commitment Model

### Switching Cost

```
progress_penalty = progress_weight × clamped_progress
time_penalty     = time_weight × min(1.0, ticks_invested / max_ticks)
total_penalty    = progress_penalty + time_penalty
```

| Parameter | Default | Purpose |
|-----------|---------|---------|
| progress_weight | 0.6 | How much progress factors into penalty |
| time_weight | 0.4 | How much time invested factors into penalty |
| max_ticks | 50 | Normalizer for time investment |

### Decision Logic

```
score_gap = candidate_score - active_score
net_improvement = score_gap - switching_cost

if net_improvement > min_improvement AND score_gap > switch_threshold:
    → SWITCH

elif progress near zero AND ticks > 3 AND (score < 0.2 OR time > 50%):
    → ABANDON

else:
    → CONTINUE
```

| Parameter | Default | Purpose |
|-----------|---------|---------|
| switch_threshold | 0.15 | Minimum raw score gap to consider switching |
| min_improvement | 0.05 | Minimum net improvement after penalty |
| abandon_threshold | 0.20 | Progress floor below which abandon is possible |

### Anti-Thrashing Properties

1. **Progress penalty** — high-progress objectives are expensive to abandon
2. **Time penalty** — long-invested objectives get switching cost protection
3. **Dual threshold** — both raw gap AND net improvement must be positive
4. **No oscillation** — if A→B has moderate gap, B→A cannot also trigger switch (progress/time penalty prevents it)

---

## Advisor Integration

### Tick Flow (Updated)

```
1. Read signals
2. Process signals
3. Cleanup cells
4. Prediction pass
5. Store predictions
6. Evaluate predictions
7. Expire predictions
8. Adapt weights/threshold
9. Update behavior model
10. Rebuild strategy
11. Calibrate simulation
12. Plan trajectory
13. Arbitrate objectives
14. Meta-plan objectives
15. ★ Commit to goal (NEW)    ← commitment engine decides
16. Persist state
```

### Commitment in Tick

- If no commitment engine → skip (returns `goal_committed=False`)
- If no active objective → adopt candidate from meta-planner or arbitration (first selection = "switch")
- If active exists → run `CommitmentEngine.decide()`
  - Same objective as candidate → treated as no candidate → CONTINUE
  - SWITCH → adopt candidate via `set_active()`
  - ABANDON → clear via `abandon()`
  - CONTINUE → no state change

---

## Hard Invariants

| ID | Invariant | Verified |
|----|-----------|----------|
| 101 | Goal state must be isolated from execution layer | YES — test_inv101_goal_state_isolated, test_inv101_commitment_isolated (AST import analysis) |
| 102 | Commitment logic must be deterministic | YES — test_inv102_commitment_deterministic (10 identical runs) |
| 103 | Progress updates must be explicit (no hidden mutation) | YES — test_inv103_progress_updates_explicit |
| 104 | Switching must be explainable | YES — test_inv104_switching_explainable, test_inv104_continue_explainable, test_inv104_abandon_explainable |
| 105 | No execution side effects during decision phase | YES — test_inv105_no_execution_side_effects, test_inv105_no_subprocess_in_goal_state, test_inv105_no_subprocess_in_commitment |

---

## Test Breakdown

| Section | Tests | Coverage |
|---------|-------|----------|
| GoalState | 15 | Creation, frozen, objective_id, elapsed_ticks (2), clamping (4), with_progress, with_commitment, to_dict (2), constants (2) |
| GoalStateManager | 16 | Empty, set_active, get_active, archives previous, update_progress (2), update_commitment (2), abandon (2), clear, history copy, to_dict (2), custom commitment, multiple archives |
| SwitchingCost | 3 | Creation, frozen, to_dict |
| CommitmentDecision | 2 | Values, count |
| CommitmentResult | 7 | Creation, frozen, to_dict (3), explanation (2) |
| Switching cost computation | 8 | Zero/zero, full/full, half progress, half time, higher progress, more time, progress clamped, time capped |
| decide() | 14 | Continue no candidate, not better enough, switch much better, suppressed by progress, abandon low score, abandon stalled, no abandon early, no abandon with progress, switching cost present, score gap, reason, same objective, deterministic, explanation |
| Properties | 10 | Default weights, custom weights, switch threshold, abandon threshold, max ticks, min improvement, evaluator (2), clamping (2) |
| Advisor integration | 14 | Engine property, manager property, last commitment, tick keys, no objectives, selects first, persists, continues, switches, get_state (2), clear, no engine, default manager |
| Anti-thrashing | 4 | Moderate suppressed, near completion, oscillation prevented, low progress allows |
| Hard invariants 101-105 | 10 | INV 101 (2), 102, 103, 104 (3), 105 (3) |
| Boundary/exports | 10 | Imports (3), compile (4), all exports, end-to-end pipeline, end-to-end advisor |
| **Total** | **113** | |

---

## Decision Hierarchy (Complete)

```
CommitmentEngine   → PERSIST or SWITCH goal (Phase 33) ←── new top layer
MetaPlanner        → which SEQUENCE of goals (Phase 31)
ArbitrationEngine  → which single GOAL (Phase 30)
TrajectoryPlanner  → which multi-step PATH (Phase 29)
StrategySimulator  → which STRATEGY variant (Phase 26)
ExecutionStrategy  → HOW to execute (Phase 25)
```

---

## Known Limitations

- Simple progress model (single scalar, no breakdown)
- No multi-objective persistence (one active at a time)
- No long-term identity shaping from goal history
- Progress not auto-updated from execution results (caller must call `update_progress`)
- Abandon conditions are heuristic (threshold-based, not learned)
- No goal priority decay over time
- No resource-aware commitment (doesn't consider budget/capacity)
- History grows without bound (no eviction policy)
- Switching cost formula is linear (not adaptive)
- No partial goal completion tracking

---

## Cumulative Test Count (Phases 11-33)

| Phase | Tests | Cumulative |
|-------|-------|------------|
| 11B-11F | 259 | 259 |
| 12 | 49 | 308 |
| 13 | 55 | 363 |
| 14 | 50 | 413 |
| 15 | 17 | 430 |
| 16 | 47 | 477 |
| 17 | 61 | 538 |
| 18 | 57 | 595 |
| 19 | 51 | 646 |
| 20 | 71 | 717 |
| 21 | 78 | 795 |
| 22 | 73 | 868 |
| 23 | 83 | 951 |
| 24 | 82 | 1033 |
| 25 | 88 | 1121 |
| 26 | 79 | 1200 |
| 27 | 80 | 1280 |
| 28 | 92 | 1372 |
| 29 | 94 | 1466 |
| 30 | 99 | 1565 |
| 31 | 97 | 1662 |
| 32 | 116 | 1778 |
| **33** | **113** | **1891** |
