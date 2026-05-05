# Phase 56 — Attribution-Guided Feedback Coupling Layer v1

## Audit Report

**Date:** 2026-05-01
**Phase:** 56 of UMH runtime build
**Status:** COMPLETE

---

## What changed after Phase 55

Phase 55 introduced contextual attribution — per-dimension performance breakdowns that explain which context dimensions correlate with strategy outcomes. But attribution was observational only, with no path to influence feedback or scoring. Phase 56 introduces a controlled coupling layer that converts attribution into bounded, confidence-gated feedback factors. The coupling is opt-in, explainable, and never overrides base scores.

---

## What was built

### New files
- `umh/runtime/attribution_feedback.py` — CouplingDirection, AttributionFeedbackPolicy, AttributionFeedbackResult, CombinedFeedbackResult, compute_attribution_feedback_factor, combine_feedback_factors

### Modified files
- `umh/runtime/__init__.py` — 6 new exports, updated docstring

### Test file
- `tests/unit/test_phase56_attribution_feedback.py` — 163 tests across 66 sections

---

## Architecture

### Attribution feedback policy

**AttributionFeedbackPolicy** (frozen dataclass):

| Field | Default | Bounds |
|-------|---------|--------|
| enabled | False | — |
| min_confidence | 0.5 | [0.0, 1.0] |
| max_boost | 0.08 | [0.0, 0.20] |
| max_penalty | 0.08 | [0.0, 0.20] |
| neutral_factor | 1.0 | — |
| required_samples | 20 | ≥ 1 |

Disabled by default — returns neutral (1.0) unless explicitly enabled.

### Factor computation

`compute_attribution_feedback_factor(attribution_record, policy)`:

1. **Disabled** → factor = 1.0, direction = NEUTRAL
2. **Missing/None record** → factor = 1.0, reason explains missing data
3. **No dimension buckets** → factor = 1.0
4. **Find strongest positive bucket** (bucket_score > overall_score, excluding STRATEGY dimension)
5. **Find strongest negative bucket** (bucket_score < overall_score, excluding STRATEGY dimension)
6. **Confidence gate**: combined_confidence = min(record_confidence, bucket_confidence). If < min_confidence → neutral
7. **Compute deviation**: bucket_score - overall_score. Scale by 0.5 and by combined_confidence
8. **Clamp**: factor within [neutral - max_penalty, neutral + max_boost]

With default policy: factor always within [0.92, 1.08].

### Positive / negative dimension detection

- **Positive**: buckets where `bucket_score > overall_score` (highest wins)
- **Negative**: buckets where `bucket_score < overall_score` (lowest wins)
- STRATEGY dimension excluded from detection
- Both are reported in the result for explainability

### Confidence gating

```
combined_confidence = min(record_confidence, strongest_bucket_confidence)
if combined_confidence < policy.min_confidence:
    return neutral
```

Both the overall attribution record AND the specific driving bucket must have sufficient confidence. This prevents small-sample buckets from driving outsized influence.

### Safe composition with existing feedback

`combine_feedback_factors(base_feedback_factor, attribution_factor, max_combined_boost=0.12, max_combined_penalty=0.12)`:

- Multiplicative: `raw = base × attribution`
- Clamped to `[1.0 - max_combined_penalty, 1.0 + max_combined_boost]`
- If attribution_factor == 1.0 → returns base unchanged
- Explanation includes both factors and clamping bounds

Default combined range: [0.88, 1.12].

### Explainability

Every `AttributionFeedbackResult` includes:
- Whether coupling was enabled
- Combined confidence used
- Strongest positive dimension (e.g., "trend=up")
- Strongest negative dimension (e.g., "risk=high")
- Final factor
- Reason explaining disabled/missing/low-confidence/boost/penalty

---

## Hard invariants verified

| # | Invariant | Verified |
|---|-----------|----------|
| 217 | Attribution coupling opt-in only | Sections 14, 31, 62 |
| 218 | Attribution coupling bounded | Sections 20, 63 |
| 219 | Low-confidence attribution neutral | Sections 16, 43 |
| 220 | Coupling does not mutate historical outcomes or attribution records | Sections 33, 34 |
| 221 | Coupling is deterministic | Sections 35, 42 |
| 222 | Coupling does not execute or mutate planning state | Section 36 |
| 223 | Attribution factor never overrides base score | Section 37 |
| 224 | Missing attribution data degrades gracefully | Sections 15, 64 |

---

## Test coverage

- **179 tests** across 70 sections
- CouplingDirection enum: Section 1 (4 tests)
- Policy defaults/bounds/dict/frozen: Sections 2-5 (18 tests)
- Result defaults/bounds/dict/frozen: Sections 6-9 (16 tests)
- CombinedFeedbackResult: Sections 10-13 (7 tests)
- Disabled policy: Section 14 (6 tests)
- Missing attribution: Section 15 (4 tests)
- Low confidence: Section 16 (4 tests)
- Positive boost: Section 17 (4 tests)
- Negative penalty: Section 18 (4 tests)
- Neutral attribution: Section 19 (2 tests)
- Factor clamping: Section 20 (3 tests)
- Dimension detection: Sections 21-24 (6 tests)
- Combined confidence: Section 25 (3 tests)
- Combine factors: Sections 26-30 (12 tests)
- Bridge unchanged: Section 31 (2 tests)
- Optional composition: Section 32 (1 test)
- Immutability: Sections 33-34 (3 tests)
- Determinism: Section 35 (2 tests)
- No execution: Section 36 (3 tests)
- No override: Section 37 (2 tests)
- Boundary compliance: Section 38 (4 tests)
- Import surface: Section 39 (1 test)
- Integration: Section 40 (2 tests)
- Edge cases: Sections 41-58 (29 tests)
- Combine edges: Sections 59-60 (3 tests)
- End-to-end: Section 61 (1 test)
- Opt-in real: Section 62 (1 test)
- Bounded stress: Section 63 (2 tests)
- Graceful degradation: Section 64 (3 tests)
- Custom neutral: Section 65 (1 test)
- Param clamping: Section 66 (3 tests)
- Epsilon comparators: Section 67 (10 tests)
- Near-equal false signal prevention: Section 68 (3 tests)
- All-equal buckets neutral: Section 69 (1 test)
- Meaningful differences preserved: Section 70 (2 tests)

---

## Boundary compliance

- No imports from `umh.cells`, `umh.environments`, `umh.adapters`
- No `import os`, `import subprocess`, or `docker` references
- Pure computation module — no I/O

---

## Precision Safety Patch

**Date:** 2026-05-01

### Problem

Raw float comparisons (`bucket_score > overall_score`, `bucket_score < overall_score`) could classify semantically equal scores as positive or negative attribution signals due to IEEE 754 floating-point drift.

Example: `0.7 * 0.8` evaluates to `0.5599999999999999`, not `0.56`. Raw `<` against `0.56` returns `True`, creating a false negative attribution signal.

### Fix

Added `EPSILON = 1e-9` and tolerance-aware comparators:
- `is_greater(a, b)` — true only if `a > b + epsilon`
- `is_less(a, b)` — true only if `a < b - epsilon`
- `is_equal(a, b)` — true if `abs(a - b) <= epsilon`
- `compare_scores(a, b)` — returns `"greater"`, `"less"`, or `"equal"`

Replaced raw `>` / `<` in `_find_strongest_positive` and `_find_strongest_negative` with `is_greater` / `is_less`.

### Guarantee

Semantic equality (values within `1e-9`) maps to neutral attribution. No false positive or negative signals from floating-point representation drift.

### Tests added

16 new tests across 4 sections (67-70):
- Section 67: Epsilon comparator unit tests (10 tests)
- Section 68: Near-equal bucket does not produce false signal (3 tests)
- Section 69: All-equal buckets produce neutral attribution (1 test)
- Section 70: Meaningful differences still boost/penalize (2 tests)

### Behavior changes

None except eliminating false precision-driven attribution signals. All existing tests pass unchanged. Public API, exports, bounds, and default disabled behavior are identical.

---

## Known limitations

- Correlation-based, not causal
- Observational attribution only — no automatic planner influence
- No learned feature importance (uniform weighting)
- No sequence-level attribution
- No Bayesian confidence model
- Coupling factor scaled linearly (0.5 × deviation × confidence)
- No cross-strategy attribution comparison

---

## Regression

- Phase 50: 161 passed, 0 failed
- Phase 51-54: 198 passed, 0 failed
- Phase 55: 151 passed, 0 failed
- Phase 56: 179 passed, 0 failed (163 original + 16 precision safety)
- Phase 50-56 combined: 689 passed, 0 failed
- Phase 30-49: 2591 passed, 0 failed
- Phase 30-56 total: 3280 passed, 0 failed

---

## Is Phase 57 safe?

Yes. Phase 56:
- Added one new module (`attribution_feedback.py`) with no modifications to existing modules
- Exports are purely additive (6 new symbols in `__init__.py`)
- All data structures are frozen dataclasses
- Feedback bridge behavior completely unchanged
- Default system behavior completely unchanged (coupling disabled by default)

Phase 57 can safely build on attribution-guided feedback to introduce:
- Attribution persistence for cross-session memory
- Learned feature importance (non-uniform dimension weighting)
- Attribution-aware exploration policies
- Causal attribution models
- Automatic coupling activation based on data sufficiency
