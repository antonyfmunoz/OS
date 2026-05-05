# Phase 37 — Multi-Objective Tradeoff Resolution Layer v1

## Audit Report

**Date:** 2026-04-30
**Phase:** 37 of UMH runtime build
**Status:** COMPLETE

---

## What was built

### New file
- `umh/runtime/tradeoff.py` — TradeoffDimension, TradeoffProfile, CandidateScore, TradeoffResult, TradeoffInfluence, TradeoffEngine, TradeoffScorer, normalize_value, compute_weighted_score, is_dominated, pareto_filter

### Modified files
- `umh/runtime/goal_hierarchy.py` — added `HierarchyScorer.collect_meta_scores()` for feeding tradeoff dimensions
- `umh/runtime/meta_planner.py` — added `tradeoff_scorer` to SequenceEvaluator and MetaPlanner, applied in score_sequence and _build_reason
- `umh/runtime/__init__.py` — 7 new exports (CandidateScore, TradeoffDimension, TradeoffEngine, TradeoffInfluence, TradeoffProfile, TradeoffResult, TradeoffScorer)

### Test file
- `tests/unit/test_phase37_tradeoff.py` — 132 tests across 19 sections

---

## Architecture

### Tradeoff model
```
TradeoffDimension: name, direction (maximize/minimize), weight, tolerance
TradeoffProfile: tuple of dimensions, normalization rules
```

### Normalization
```
maximize: normalized = (value - min) / (max - min)
minimize: normalized = 1.0 - (value - min) / (max - min)
equal range: 0.5
clamped to [0, 1]
```

### Scoring
```
weighted_score = Σ(normalized_i × weight_i) / Σ(weight_i)
```

### Pareto filtering
```
Candidate A dominated by B iff:
  B >= A in all normalized dimensions AND
  B > A in at least one dimension
```

### Scoring chain (5 multipliers now)
```
total = base × identity[0.80,1.20] × goal_bias[0.85,1.15] × hierarchy[0.90,1.10] × tradeoff[0.85,1.15]
```

Compound range: 0.520 – 1.746

### TradeoffScorer factor formula
```
deviation = weighted_score - 0.5
factor = clamp(1.0 + deviation × 0.3, 0.85, 1.15)
```

---

## Data flow
```
HierarchyScorer.collect_meta_scores(goal_type)
  → dict[meta_goal_name, aggregated_score]
  → TradeoffScorer.compute_factor(meta_goal_scores, candidate_id)
  → TradeoffEngine.resolve(candidates, profile)
    → normalize all dimensions
    → Pareto filter (remove dominated)
    → weighted scoring
    → tolerance filtering
    → deterministic tie-break (by candidate_id)
  → TradeoffInfluence(factor, result, reason)
  → combined *= factor
```

### Single-candidate behavior
With one candidate per score_sequence call, all dimensions normalize to 0.5 (equal min/max), producing factor = 1.0. This is correct — single candidates have no tradeoff to resolve. The tradeoff becomes meaningful when comparing multiple candidates through the engine directly.

---

## Hard invariants

| ID | Invariant | Status |
|----|-----------|--------|
| 121 | Tradeoff resolution must be pure (no state mutation) | PASS |
| 122 | No stochastic decision making | PASS |
| 123 | Deterministic tie-breaking required | PASS |
| 124 | No override of base score (only weighting) | PASS |
| 125 | Tradeoff layer must be explainable | PASS |

---

## Test results

- **Phase 37 tests:** 132 passed, 0 failed
- **Full regression (phases 11-37):** 2361 passed, 0 failed
- **Test growth:** +132 (from 2229 to 2361)

---

## Dependency boundary

`tradeoff.py` imports only:
- `__future__.annotations`
- `dataclasses` (dataclass, field)
- `typing` (Any)

No imports from `umh/cells`, `umh/environments`, `umh/adapters`.

---

## Known limitations

- Static weights — no adaptive tradeoffs yet
- No temporal tradeoff learning
- Single-candidate scoring produces neutral factor (by design)
- Pareto filtering is O(n²) — acceptable for small candidate sets

---

## Files verified

```
py_compile: tradeoff.py ✓
py_compile: goal_hierarchy.py ✓
py_compile: meta_planner.py ✓
py_compile: __init__.py ✓
ruff format: all files ✓
```
