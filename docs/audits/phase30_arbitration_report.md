# Phase 30: Goal Arbitration + Objective Selection Layer v1 — Audit Report

**Date**: 2026-04-30
**Status**: COMPLETE
**Tests**: 99 passed, 0 failed
**Regression**: 1565 passed (phases 11-30), 0 regressions

---

## Deliverables

### New Modules (1)

| File | Purpose | Lines |
|------|---------|-------|
| `umh/runtime/arbitration.py` | Objective, ObjectiveScore, ArbitrationWeights, ArbitrationResult, ObjectiveEvaluator, ObjectiveRanker, ArbitrationEngine | ~321 |

### Modified Modules (2)

| File | Changes |
|------|---------|
| `umh/runtime/advisor.py` | Added `arbitration_engine` constructor param, `_objectives` list, `add_objective()`, `remove_objective()`, `_arbitrate_objectives()` in tick, `last_arbitration` property, `objective_selected` tick key, arbitration in `get_state()`, reset in `clear()` |
| `umh/runtime/__init__.py` | Added 7 new exports (ArbitrationEngine, ArbitrationResult, ArbitrationWeights, Objective, ObjectiveEvaluator, ObjectiveRanker, ObjectiveScore) |

### Test File (1)

| File | Tests |
|------|-------|
| `tests/unit/test_phase30_arbitration.py` | 99 |

---

## Architecture

```
Objective (what to pursue)
        │
        ▼
ObjectiveEvaluator.score(objective)
        │
        ▼  Dimensions:
        │    urgency   — deadline proximity (0.3 no deadline, 1.0 past/today)
        │    importance — priority / 10 (clamped 1-10)
        │    value     — expected_value (clamped 0-1)
        │    effort    — 1/(1+effort_estimate)
        │
        ▼
ObjectiveScore (per-dimension + weighted total)
        │
        ▼
ObjectiveRanker.rank(objectives)
        │
        ▼  Sorted by (-total_score, objective_id)
        │  Deterministic tie-breaking by ID
        │
        ▼
ArbitrationEngine.select(objectives)
        │
        ▼
ArbitrationResult (selected + all_scores + reason + explanation)
        │
        ▼
AdvisorRuntime._arbitrate_objectives() → _last_arbitration
```

---

## Scoring Model

### Dimension Weights (Default)

| Dimension | Weight | Direction | Computation |
|-----------|--------|-----------|-------------|
| Urgency | 0.30 | Higher = better | Deadline proximity heuristic |
| Importance | 0.30 | Higher = better | priority / 10 |
| Value | 0.25 | Higher = better | expected_value (clamped) |
| Effort | 0.15 | Lower = better | 1/(1+effort) |

### Urgency Heuristic

| Condition | Score |
|-----------|-------|
| No deadline | 0.3 |
| Deadline past or today | 1.0 |
| Deadline within ~7 days | 0.8 |
| Deadline further out | 0.5 |

### Explainability

Every ArbitrationResult carries:
- `reason` — semicolon-separated factor list (urgency level, priority respect, margin notes)
- `explanation` — line-by-line breakdown with `>>>` marker on selected objective
- `factors` tuple — per-objective qualitative labels ("high urgency — deadline approaching", etc.)

---

## Hard Invariants

| ID | Invariant | Verified |
|----|-----------|----------|
| 85 | Arbitration evaluation must be pure (no I/O) | YES — test_inv85_arbitration_is_pure, test_inv85_no_io_in_arbitration |
| 86 | No real side effects during arbitration | YES — test_inv86_no_side_effects |
| 87 | Arbitration must be deterministic given inputs | YES — test_inv87_deterministic |
| 88 | No mutation of engine state between calls | YES — test_inv88_no_mutation_of_state |
| 89 | No imports from umh/cells, umh/environments, umh/adapters | YES — test_inv89_no_forbidden_imports |

---

## Test Breakdown

| Section | Tests | Coverage |
|---------|-------|----------|
| Objective | 5 | Creation, full params, frozen, to_dict, rounding |
| ObjectiveScore | 5 | Creation, frozen, to_dict, rounding, factors |
| ArbitrationWeights | 4 | Defaults, custom, frozen, to_dict |
| ArbitrationResult | 5 | Creation, frozen, to_dict, explanation, markers |
| ObjectiveEvaluator | 27 | Score, urgency (6), importance (4), value (3), effort (3), weights (3), factors (6), deterministic, weighted sum |
| ObjectiveRanker | 7 | Basic, empty, single, order, tie-break, deterministic, evaluator property |
| ArbitrationEngine | 16 | Basic, empty, single, all_scores, deterministic, reason (3), explanation, custom evaluator, custom ranker, properties, urgency wins, effort matters, to_dict, multiple |
| Advisor integration | 16 | Properties (3), objectives (5), tick keys (4), get_state (2), clear, copy semantics |
| Hard invariants | 6 | INV 85-89, forbidden imports |
| Boundary/exports | 8 | Imports (2), compile (3), exports, end-to-end (2) |
| **Total** | **99** | |

---

## Known Limitations

- Urgency date arithmetic uses string comparison — breaks for day values > 23 when computing "within 7 days" (falls back to 0.5 which is safe)
- No temporal decay on objective scores
- No dependency modeling between objectives
- No partial completion tracking
- Weights are static (configurable but not adaptive)
- No constraint satisfaction (e.g., "must do X before Y")
- No resource-aware scheduling (objectives compete on score alone)
- Deadline resolution is day-level only (no hour/minute precision)

---

## Cumulative Test Count (Phases 11-30)

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
| **30** | **99** | **1565** |
