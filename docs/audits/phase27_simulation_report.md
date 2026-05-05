# Phase 27: Strategy Simulation + Outcome Evaluation Layer v1 — Audit Report

**Date**: 2026-04-30
**Status**: COMPLETE
**Tests**: 80 passed, 0 failed
**Regression**: 1280 passed (phases 11-27), 0 regressions

---

## Deliverables

### New Modules (2)

| File | Purpose | Lines |
|------|---------|-------|
| `umh/runtime/simulation.py` | StrategyGenerator, SimulationEngine, SimulatedOutcome, SimulationResult | ~200 |
| `umh/runtime/evaluator.py` | OutcomeEvaluator, ScoringWeights, StrategySimulator | ~175 |

### Modified Modules (2)

| File | Changes |
|------|---------|
| `umh/runtime/advisor.py` | Added `strategy_simulator` param, `_last_simulation` field, simulation in `_rebuild_strategy()`, simulation in `get_state()`, `clear()` resets simulation |
| `umh/runtime/__init__.py` | Added 7 new exports (SimulatedOutcome, SimulationEngine, SimulationResult, StrategyGenerator, StrategySimulator, OutcomeEvaluator, ScoringWeights) |

### Test File (1)

| File | Tests |
|------|-------|
| `tests/unit/test_phase27_simulation.py` | 80 |

---

## Architecture

```
UserBehaviorModel (read-only)
        │
        ▼
StrategyBuilder.build_strategy()
        │
        ▼
base ExecutionStrategy
        │
        ▼
StrategyGenerator.generate_candidates()
        │
        ▼
[base, smaller-batch, larger-batch, aggressive-retry,
 conservative-pacing, balanced-variant]
        │
        ▼
SimulationEngine.simulate() × N
        │
        ▼
[SimulatedOutcome, SimulatedOutcome, ...]
        │
        ▼
OutcomeEvaluator.rank()
        │
        ▼
SimulationResult (selected + all candidates + reason)
        │
        ▼
AdvisorRuntime._current_strategy = selected.strategy
```

---

## Candidate Generation Strategy

| Variant | Batch | Pacing | Retry | Intent |
|---------|-------|--------|-------|--------|
| base | unchanged | unchanged | unchanged | Baseline comparison |
| smaller-batch | -2 | unchanged | unchanged | Reduce overload risk |
| larger-batch | +2 | unchanged | unchanged | Increase throughput |
| aggressive-retry | unchanged | unchanged | +2 | Improve completion |
| conservative-pacing | unchanged | ×1.3 | unchanged | Buffer for slow responses |
| balanced | -1 | ×0.8 | +1 | Mixed conservative approach |

---

## Simulation Model

| Metric | Formula | Factors |
|--------|---------|---------|
| completion_rate | base + retry_boost - batch_penalty | model.completion_rate, retry_budget, batch_size |
| latency | batch_size × pacing | batch_size, pacing |
| failure_risk | base + batch_risk - retry_reduction | model.volatility_index, batch_size, retry_budget |
| effort | batch_size × 0.12 + retry_budget × 0.05 | batch_size, retry_budget |

---

## Scoring Weights

| Criterion | Weight | Direction |
|-----------|--------|-----------|
| Completion | 0.40 | Higher = better |
| Failure risk | 0.25 | Lower = better (inverted) |
| Latency | 0.20 | Lower = better (inverted) |
| Effort | 0.15 | Lower = better (inverted) |

Score = Σ(weight × normalized_metric)

---

## Hard Invariants

| ID | Invariant | Verified |
|----|-----------|----------|
| 70 | Simulation must NOT execute real tasks | YES — test_inv70_simulation_does_not_execute_tasks, test_inv70_no_io_in_simulation |
| 71 | Simulation must be pure (no side effects) | YES — test_inv71_simulation_pure |
| 72 | Simulation must not mutate system state | YES — test_inv72_simulation_does_not_mutate_model, test_inv72_simulation_does_not_mutate_strategy |
| 73 | Strategy selection must remain deterministic | YES — test_inv73_deterministic_selection |
| 74 | Simulation outputs must be explainable | YES — test_inv74_outcomes_explainable, test_inv74_explanation_lists_alternatives |

---

## Test Breakdown

| Section | Tests | Coverage |
|---------|-------|----------|
| StrategyGenerator | 12 | Candidates, bounds, labels, determinism |
| SimulationEngine | 15 | Metrics, bounds, model influence, determinism |
| OutcomeEvaluator | 12 | Scoring, ranking, weights, custom weights |
| StrategySimulator | 10 | Pipeline, selection, determinism, model influence |
| SimulationResult | 5 | Structure, frozen, labels, scores |
| Advisor integration | 11 | Properties, tick, state, clear, feedback |
| Hard invariants | 10 | INV 70-74 |
| Boundary/exports | 5 | Imports, compile, end-to-end |
| **Total** | **80** | |

---

## Known Limitations

- Heuristic simulation (no ML, no statistical modeling)
- Limited strategy space (6 candidates per run)
- No real-world feedback loop — simulation doesn't learn from outcomes
- No stochastic modeling — always returns same result for same inputs
- Scoring weights are static (configurable but not adaptive)
- No per-task-type differentiation in simulation

---

## Cumulative Test Count (Phases 11-27)

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
| **27** | **80** | **1280** |
