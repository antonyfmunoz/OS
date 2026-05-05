# Phase 59 — Multi-Signal Regime Aggregation Layer v1

## Audit Report

**Date:** 2026-05-01
**Phase:** 59 of UMH runtime build
**Status:** COMPLETE

---

## Why single regime is insufficient

Through Phase 48, UMH compresses all regime signals into one `CompositeRegimeState` per signal. This works for single-signal decisions but loses critical cross-dimensional information:

1. **Direction blindness** — a signal with trend_up + high_risk looks the same to downstream scoring as one with trend_up + low_risk once collapsed into a factor
2. **Conflict erasure** — when trend says "go" but stability says "wait", the single composite number hides the disagreement
3. **Dominant signal lost** — which dimension is driving the regime? The collapsed factor can't say

Phase 59 preserves per-dimension regime classifications and computes alignment/conflict metrics that express the structural quality of the regime signal, not just its magnitude.

---

## What was built

### New files
- `umh/runtime/regime_aggregation.py` — DimensionName, DirectionCategory, DimensionRegime, AggregatedRegimeState, classify_dimension, aggregate_regimes, aggregate_from_dict

### Modified files
- `umh/runtime/strategy_orchestrator.py` — optional `aggregated_regime` parameter (does not affect scoring)
- `umh/runtime/__init__.py` — 12 new exports, updated docstring

### Test file
- `tests/unit/test_phase59_regime_aggregation.py` — 171 tests across 65 sections

### Also modified
- `tests/unit/test_phase58_strategy_orchestration.py` — Section 44 updated to allow `regime_aggregation` import

---

## Architecture

### Per-dimension classification (inv 242)

Each dimension is classified independently:

| Dimension | Labels | Positive | Neutral | Negative |
|-----------|--------|----------|---------|----------|
| trend | stable, trend_up, trend_down, spike_up, spike_down | trend_up, spike_up | stable | trend_down, spike_down |
| risk | low, medium, high | low | medium | high |
| stability | high, medium, low | high | medium | low |
| urgency | low, medium, high | low | medium | high |

Strength values:
- trend: 0.0 (stable), 0.5 (trend), 1.0 (spike)
- risk/stability/urgency: 0.2 (low-severity), 0.5 (medium), 1.0 (high-severity)

Effective strength = strength × confidence

### Aggregation model

`AggregatedRegimeState`:

| Field | Type | Bounds |
|-------|------|--------|
| regimes | dict[str, DimensionRegime] | always 4 dimensions |
| dominant_dimension | DimensionName or None | — |
| alignment_score | float | [0.0, 1.0] |
| conflict_score | float | [0.0, 1.0] |
| explanation | str | — |

### Alignment vs conflict

Only non-neutral dimensions participate in alignment/conflict computation:

```
non_neutral = [d for d in dimensions if d.direction != NEUTRAL]
pos_count = count(POSITIVE in non_neutral)
neg_count = count(NEGATIVE in non_neutral)
majority = max(pos_count, neg_count)
minority = min(pos_count, neg_count)
alignment = majority / len(non_neutral)
conflict = minority / len(non_neutral)
```

Properties:
- alignment + conflict = 1.0 (when any non-neutral dimensions exist)
- All neutral → alignment=0.0, conflict=0.0
- All agree → alignment=1.0, conflict=0.0
- Even split → alignment=0.5, conflict=0.5

### Dominant dimension

Selected by highest `effective_strength` (strength × confidence).

- Tie-break: lexicographic by dimension name (ascending)
- All zero → None (no dominant)

### No combinatorial explosion (inv 244)

The aggregation model produces exactly one `AggregatedRegimeState` regardless of input complexity:
- 4 dimensions × 1 classification each = 4 `DimensionRegime` objects
- 1 alignment score, 1 conflict score, 1 dominant dimension
- No cross-product, no matrix, no exponential state space

### Missing signals (inv 245)

Any missing dimension defaults to its neutral constant:
- NEUTRAL_TREND: stable, strength=0.0, confidence=0.0
- NEUTRAL_RISK: neutral direction, strength=0.0
- NEUTRAL_STABILITY: neutral direction, strength=0.0
- NEUTRAL_URGENCY: neutral direction, strength=0.0

Unknown labels also produce neutral classification.

### Orchestrator integration (inv 248)

`orchestrate_selection()` now accepts an optional `aggregated_regime` parameter:
- **Does not affect scoring** — the aggregated regime is informational only
- Attached to `StrategySelectionResult.aggregated_regime` field
- Included in explanation string when present
- Included in `to_dict()` output when present
- Omitted from `to_dict()` when None (backward compatible)
- Early-return paths (empty strategies, all invalid) do not propagate it

---

## Hard invariants verified

| # | Invariant | Verified |
|---|-----------|----------|
| 242 | Per-dimension regimes computed independently | Sections 8-11, 46 |
| 243 | Aggregation deterministic | Sections 29, 50, 61 |
| 244 | No combinatorial explosion | Section 30 |
| 245 | Missing signals default to neutral | Sections 21, 22, 58, 59 |
| 246 | Composite state explainable | Sections 31, 45, 54 |
| 247 | No mutation of underlying signals | Section 32 |
| 248 | Aggregation does not affect scoring | Sections 34, 37, 51 |

---

## Test coverage

- **171 tests** across 65 sections
- DimensionName enum: Section 1 (5 tests)
- DirectionCategory enum: Section 2 (4 tests)
- DimensionRegime defaults/bounds: Section 3 (6 tests)
- Effective strength: Section 4 (3 tests)
- DimensionRegime to_dict: Section 5 (2 tests)
- DimensionRegime frozen: Section 6 (2 tests)
- Neutral constants: Section 7 (4 tests)
- Classify trend: Section 8 (6 tests)
- Classify risk: Section 9 (3 tests)
- Classify stability: Section 10 (3 tests)
- Classify urgency: Section 11 (3 tests)
- Confidence pass-through: Section 12 (3 tests)
- Case insensitive: Section 13 (2 tests)
- AggregatedRegimeState defaults: Section 14 (4 tests)
- AggregatedRegimeState bounds: Section 15 (4 tests)
- AggregatedRegimeState properties: Section 16 (3 tests)
- Get/get_or_neutral: Section 17 (3 tests)
- AggregatedRegimeState to_dict: Section 18 (2 tests)
- AggregatedRegimeState frozen: Section 19 (2 tests)
- NEUTRAL_AGGREGATED: Section 20 (4 tests)
- All missing neutral: Section 21 (4 tests)
- Partial missing: Section 22 (2 tests)
- All positive alignment: Section 23 (3 tests)
- All negative alignment: Section 24 (2 tests)
- Conflict scenarios: Section 25 (3 tests)
- Neutral excluded: Section 26 (2 tests)
- Dominant dimension: Section 27 (3 tests)
- Dominant tie-break: Section 28 (2 tests)
- Determinism: Section 29 (2 tests)
- No combinatorial: Section 30 (2 tests)
- Explainability: Section 31 (4 tests)
- No mutation: Section 32 (2 tests)
- aggregate_from_dict: Section 33 (4 tests)
- No scoring impact: Section 34 (2 tests)
- Boundary compliance: Section 35 (4 tests)
- Import surface: Section 36 (1 test)
- Orchestrator param: Section 37 (3 tests)
- Orchestrator explanation: Section 38 (2 tests)
- Orchestrator to_dict: Section 39 (2 tests)
- Phase 58 unchanged: Section 40 (3 tests)
- Mixed with neutrals: Section 41 (2 tests)
- Alignment/conflict symmetry: Section 42 (2 tests)
- Confidence effects: Section 43 (2 tests)
- Stress all types: Section 44 (2 tests)
- No dominant explanation: Section 45 (2 tests)
- Independence: Section 46 (2 tests)
- Same direction diff strength: Section 47 (2 tests)
- Single non-neutral: Section 48 (2 tests)
- Roundtrip to_dict: Section 49 (3 tests)
- No randomness: Section 50 (2 tests)
- No scoring impact (orchestrator): Section 51 (2 tests)
- Result field: Section 52 (2 tests)
- Alignment formula: Section 53 (2 tests)
- Explanation ordering: Section 54 (1 test)
- Full pipeline: Section 55 (2 tests)
- Phase 57 unchanged: Section 56 (2 tests)
- Phase 58 compat: Section 57 (2 tests)
- Unknown labels: Section 58 (3 tests)
- Empty aggregation: Section 59 (2 tests)
- Regime label storage: Section 60 (2 tests)
- Stress 100 aggregations: Section 61 (1 test)
- No execution methods: Section 62 (2 tests)
- Confidence/alignment interplay: Section 63 (2 tests)
- Empty selection: Section 64 (2 tests)
- Init exports regression: Section 65 (3 tests)

---

## Boundary compliance

- No imports from `umh.cells`, `umh.environments`, `umh.adapters`
- No `import os`, `import subprocess`, `import random`, or `docker` references
- Pure computation module — no I/O, no file access
- No mutation of input data
- regime_aggregation.py has zero imports from other `umh.runtime` modules (fully standalone)
- Orchestrator uses TYPE_CHECKING import to avoid circular dependency

---

## Regression

- Phase 30-49: 2591 passed, 0 failed
- Phase 50: 161 passed, 0 failed
- Phase 51-54: 198 passed, 0 failed
- Phase 55: 151 passed, 0 failed
- Phase 56: 179 passed, 0 failed
- Phase 57: 194 passed, 0 failed
- Phase 58: 167 passed, 0 failed
- Phase 59: 171 passed, 0 failed
- Phase 30-59 combined: 3812 passed, 0 failed

---

## Known limitations

- No weighting by dimension importance (all dimensions equal in alignment/conflict)
- No temporal aggregation (single-tick snapshot only)
- No adaptive dimension selection
- No causal modeling between dimensions
- No cross-session regime memory
- Orchestrator integration is informational only (no scoring impact yet)
- No dimension-specific confidence thresholds
- No regime transition detection at aggregation level

---

## Is Phase 60 safe?

Yes. Phase 59:
- Added one new standalone module (`regime_aggregation.py`) with zero internal runtime dependencies
- Orchestrator changes are backward compatible (new parameter defaults to None, no scoring impact)
- Exports are purely additive (12 new symbols in `__init__.py`)
- All data structures are frozen dataclasses
- Default system behavior completely unchanged
- No dependency on any external library
- 3812 tests pass across Phases 30-59 with zero regressions

Phase 60 can safely build on regime aggregation to introduce:
- Dimension-weighted alignment/conflict (importance-adjusted counts)
- Temporal regime aggregation (multi-tick smoothed aggregation)
- Regime-to-scoring bridge (aggregation-informed strategy factors)
- Cross-session aggregation memory
- Dimension interaction detection (conditional alignment patterns)
