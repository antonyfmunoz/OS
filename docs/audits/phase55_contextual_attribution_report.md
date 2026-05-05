# Phase 55 — Contextual Outcome Attribution Layer v1

## Audit Report

**Date:** 2026-04-30
**Phase:** 55 of UMH runtime build
**Status:** COMPLETE

---

## What changed after Phase 51-54

Phases 50-54 gave UMH outcome memory, temporal decay, bounded feedback, learning strength, and exploration. But strategy performance was tracked in aggregate — UMH couldn't distinguish "strategy X works globally" from "strategy X fails under HIGH_RISK + LOW_STABILITY contexts." Phase 55 introduces contextual attribution: per-dimension performance breakdowns that enable future phases to make context-aware decisions.

---

## What was built

### New files
- `umh/runtime/attribution.py` — AttributionDimension, AttributionBucket, ContextAttributionRecord, ContextFeatures, extract_context_features, AttributionEngine

### Modified files
- `umh/runtime/__init__.py` — 6 new exports, updated docstring

### Test file
- `tests/unit/test_phase55_contextual_attribution.py` — 151 tests across 60 sections

---

## Architecture

### Attribution data model

**AttributionDimension** enum (9 members):
STRATEGY, STATE_SIGNATURE, TREND, RISK, URGENCY, STABILITY, CONFIDENCE, OBJECTIVE, GOAL_TYPE

**AttributionBucket** — stats for one dimension-value pair:

| Field | Type | Bounds | Default |
|-------|------|--------|---------|
| dimension | AttributionDimension | — | required |
| value | str | — | required |
| sample_count | int | [0, ∞) | 0 |
| success_count | int | [0, ∞) | 0 |
| failure_count | int | [0, ∞) | 0 |
| partial_count | int | [0, ∞) | 0 |
| average_success_score | float | [0.0, 1.0] | 0.0 |
| average_latency | float | [0.0, ∞) | 0.0 |
| average_effort | float | [0.0, 1.0] | 0.0 |
| confidence | float | [0.0, 1.0] | 0.0 |

Computed property: `bucket_score = average_success_score × confidence`

**ContextAttributionRecord** — full attribution breakdown:
- strategy_name, state_signature
- dimension_buckets (tuple of AttributionBucket)
- overall_score (mean success_score of filtered outcomes)
- confidence (min(1.0, n / required_samples))
- explanation (human-readable summary)

### Context extraction

`extract_context_features(outcome)` extracts from:
- `strategy_name` and `state_signature` (always present)
- `metadata` dict keys: trend, risk, urgency, stability, confidence, objective, goal_type

Missing keys → empty string → dimension omitted from attribution buckets.

### Attribution engine

`AttributionEngine(required_samples=20)`:
- `build_attribution(outcomes, strategy_name=None, state_signature=None)` — filter + group + score
- `compute_global_strategy_attribution(outcomes, strategy_name)` — all outcomes for strategy
- `compute_context_strategy_attribution(outcomes, strategy_name, state_signature)` — context-filtered
- `compare_global_vs_context(outcomes, strategy_name, state_signature)` — side-by-side comparison

### Dimension scoring

```
bucket_score = average_success_score × confidence
confidence = min(1.0, sample_count / required_samples)
```

Insufficient samples → low confidence → low bucket_score → no aggressive conclusions.

### Global vs local attribution

```python
cmp = engine.compare_global_vs_context(outcomes, "aggressive", "high_risk_state")
# Returns: { global: {...}, context: {...}, score_difference: 0.15, summary: "..." }
```

Enables: "Strategy works globally (0.75), but underperforms in HIGH_RISK (0.60)."

### Attribution explanation

Every record includes:
- Outcome count analyzed
- Context identifier (if filtered)
- Strongest positive bucket (dimension + value + score)
- Weakest bucket (if different from strongest)
- Insufficient data caveats
- Overall score and confidence

---

## Hard invariants verified

| # | Invariant | Verified |
|---|-----------|----------|
| 211 | Attribution derived only from recorded outcomes | Section 29 |
| 212 | Attribution does not mutate historical outcomes | Section 30 |
| 213 | Attribution is deterministic | Section 31 |
| 214 | Attribution degrades gracefully with sparse data | Section 22, 32 |
| 215 | Attribution does not directly execute or mutate planning state | Section 33 |
| 216 | Attribution influence remains observational by default | Section 34 |

---

## Test coverage

- **151 tests** across 60 sections
- Data model (enum, bucket, record, features): Sections 1-11 (34 tests)
- Context extraction: Sections 12-14 (13 tests)
- Engine grouping: Sections 15-20 (20 tests)
- Empty/sparse: Sections 21-22 (6 tests)
- Global vs local: Sections 23-25 (8 tests)
- Explanation: Sections 26-28 (8 tests)
- Safety invariants: Sections 29-34 (14 tests)
- Filtering: Sections 35-37 (4 tests)
- Import surface: Section 38 (1 test)
- Integration: Sections 39-40 (3 tests)
- Edge cases: Sections 41-54 (27 tests)
- Additional coverage: Sections 55-60 (13 tests)

---

## Boundary compliance

- No imports from `umh.cells`, `umh.environments`, `umh.adapters`
- No `import os`, `import subprocess`, or `docker` references
- Pure computation module — no I/O

---

## Known limitations

- Observational only — no automatic scoring influence
- No causal proof — correlation between dimension and outcome, not causation
- No sequence-level attribution (outcome chains)
- No learned feature importance (uniform weighting across dimensions)
- No Bayesian or causal graph model
- Metadata-dependent — dimensions beyond strategy/state require metadata population

---

## Regression

- Phase 50: 161 passed, 0 failed
- Phase 51-54: 198 passed, 0 failed
- Phase 55: 151 passed, 0 failed
- Phase 50-55 combined: 510 passed, 0 failed
- Full regression: 1 pre-existing failure in test_umh_wave9_wrapper_removal.py (asserts eos_ai/ directory deleted — directory still active). Unrelated to Phase 55.

---

## Is Phase 56 safe?

Yes. Phase 55:
- Added one new module (`attribution.py`) with no modifications to existing scoring logic
- Exports are purely additive (6 new symbols in `__init__.py`)
- All data structures are frozen and observational
- No existing behavior changed

Phase 56 can safely build on attribution to introduce:
- Attribution-weighted feedback adjustments
- Context-aware exploration policies
- Dimension importance learning
- Attribution persistence for cross-session memory
