# Phase 29: Multi-Step Planning + Trajectory Simulation Layer v1 — Audit Report

**Date**: 2026-04-30
**Status**: COMPLETE
**Tests**: 94 passed, 0 failed
**Regression**: 1466 passed (phases 11-29), 0 regressions

---

## Deliverables

### New Modules (1)

| File | Purpose | Lines |
|------|---------|-------|
| `umh/runtime/trajectory.py` | TrajectoryStep, Trajectory, TrajectoryResult, TrajectoryWeights, TrajectoryGenerator, TrajectorySimulator, TrajectoryEvaluator, TrajectoryPlanner | ~340 |

### Modified Modules (3)

| File | Changes |
|------|---------|
| `umh/runtime/simulation.py` | Added `simulate_trajectory()` method to SimulationEngine — convenience wrapper for sequenced strategy simulation |
| `umh/runtime/advisor.py` | Added `trajectory_planner` constructor param, `last_trajectory` property, `_plan_trajectory()` method in tick, trajectory in `get_state()`, reset in `clear()` |
| `umh/runtime/__init__.py` | Added 8 new exports (Trajectory, TrajectoryEvaluator, TrajectoryGenerator, TrajectoryPlanner, TrajectoryResult, TrajectorySimulator, TrajectoryStep, TrajectoryWeights) |

### Test File (1)

| File | Tests |
|------|-------|
| `tests/unit/test_phase29_trajectory.py` | 94 |

---

## Architecture

```
ExecutionStrategy (base)
        │
        ▼
TrajectoryGenerator.generate_paths(base, depth=3)
        │
        ▼
[[s1a, s2a, s3a], [s1a, s2b, s3b], ...]
        │                                    ┌─ Step-by-step branching
        │                                    │  Representative selection (3 per branch)
        │                                    └─ Max trajectory cap (default 50)
        ▼
TrajectorySimulator.simulate(path, model, calibration)
        │
        ▼  For each step:
        │    completion *= step.completion_rate
        │    latency += step.latency
        │    no_failure *= (1 - step.risk)
        │    effort += step.effort
        │
        ▼
Trajectory (steps, cumulative metrics)
        │
        ▼
TrajectoryEvaluator.rank(trajectories)
        │
        ▼
TrajectoryResult (selected + all candidates + reason)
        │
        ▼
selected.first_strategy → AdvisorRuntime._current_strategy
```

---

## Trajectory Model

### Cumulative Metric Accumulation

| Metric | Accumulation | Formula |
|--------|-------------|---------|
| completion | multiplicative | Π(step_completion_rate) |
| latency | additive | Σ(step_latency) |
| risk | compound probability | 1 - Π(1 - step_risk) |
| effort | additive | Σ(step_effort) |

### Scoring Weights

| Criterion | Weight | Direction |
|-----------|--------|-----------|
| Completion | 0.40 | Higher = better |
| Risk | 0.25 | Lower = better (inverted) |
| Latency | 0.20 | Lower = better (1/(1+x)) |
| Effort | 0.15 | Lower = better (1/(1+x)) |

### Key Principle

**Plan to the horizon, act on step one.** The planner evaluates full multi-step trajectories but only extracts `selected.first_strategy` for immediate execution. This gives the system look-ahead ability without committing to future decisions.

---

## Generation Strategy

| Parameter | Value | Purpose |
|-----------|-------|---------|
| Min depth | 2 | Minimum planning horizon |
| Max depth | 5 | Maximum planning horizon |
| Default depth | 3 | Standard planning horizon |
| Max trajectories | 50 | Cap on combinatorial growth |
| Branches per step | 3 (representative) | Limits growth: first, middle, last candidate |

### Combinatorial Control

Without pruning, 6 candidates × 6 × 6 = 216 trajectories at depth 3. Representative selection (3 per branch) reduces this to ~54, capped at 50. This keeps trajectory evaluation tractable while preserving strategy diversity.

---

## Hard Invariants

| ID | Invariant | Verified |
|----|-----------|----------|
| 80 | Trajectory simulation must be pure (no execution) | YES — test_inv80_trajectory_simulation_pure, test_inv80_no_io_in_trajectory |
| 81 | No real side effects during simulation | YES — test_inv81_no_side_effects |
| 82 | Trajectories must be deterministic given inputs | YES — test_inv82_deterministic |
| 83 | No mutation of execution state | YES — test_inv83_no_mutation |
| 84 | Calibration remains read-only to execution | YES — test_inv84_calibration_read_only |

---

## Labeling System

Trajectories receive human-readable labels based on start and end strategy characteristics:

| Start | End | Label Example |
|-------|-----|---------------|
| batch < base | batch > start | conservative-start-ramp-up-0 |
| batch > base | batch < start | aggressive-start-ramp-down-1 |
| batch = base | batch = start | steady-start-stable-2 |

---

## Test Breakdown

| Section | Tests | Coverage |
|---------|-------|----------|
| TrajectoryStep | 3 | Creation, frozen, to_dict |
| Trajectory | 7 | Creation, frozen, depth, first_strategy, to_dict, rounding, metrics |
| TrajectoryResult | 5 | Creation, frozen, to_dict, explanation, markers |
| TrajectoryWeights | 4 | Defaults, custom, frozen, to_dict |
| TrajectoryGenerator | 14 | Paths, depth (3), clamping (2), deterministic, max limit, multiple, strategies, labels (5) |
| TrajectorySimulator | 12 | Basic, completion, latency, risk, effort, label, single, three, calibration, deterministic, different, bounds |
| TrajectoryEvaluator | 10 | Score, completion, risk, latency, effort, rank, scores, deterministic, custom weights, normalized |
| TrajectoryPlanner | 11 | Basic, depth, selects best, deterministic, calibration, reason, first_strategy, multiple, all_scored, explanation, properties |
| SimulationEngine.simulate_trajectory | 4 | Basic, calibration, empty, single |
| Advisor integration | 8 | Properties, tick key, plans, first strategy, get_state, clear, no planner, no strategy |
| Hard invariants | 6 | INV 80-84, forbidden imports |
| Boundary/exports | 8 | Imports (3), compile (3), end-to-end (2) |
| **Total** | **94** | |

---

## Known Limitations

- Small depth only (2-5 steps)
- Heuristic simulation (no ML, no statistical modeling)
- No branch pruning optimization (evaluates all generated trajectories)
- No probabilistic modeling — always returns same result for same inputs
- Trajectory weights are static (configurable but not adaptive)
- No per-task-type differentiation in trajectory simulation
- Representative selection is positional (first/mid/last), not quality-based
- No early termination if a trajectory is clearly dominated

---

## Cumulative Test Count (Phases 11-29)

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
| **29** | **94** | **1466** |
