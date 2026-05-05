# Phase 69 — Multi-Pattern Aggregation Layer v1

**Status**: COMPLETE
**Date**: 2026-05-01
**Tests**: 67/67 passing
**Regression**: 647/647 (phases 58, 66, 67, 68, 69)

## What was built

Multi-pattern aggregation layer that extends Phase 68's single-pattern
influence to blend multiple pattern matches into a single scoring factor.

### New module: `umh/runtime/pattern_aggregation.py`

- `PatternContribution` — frozen dataclass for one pattern's weighted contribution
- `PatternAggregationResult` — frozen dataclass for final aggregated result
- `compute_pattern_aggregation()` — main entry point
- `_compute_individual_factor()` — per-pattern signal computation
- `_apply_dominance_cap()` — iterative cap-and-redistribute algorithm

### Modified: `umh/runtime/strategy_orchestrator.py`

- STEP 6 now branches: `len(all_matches) > 1` → aggregation path, else → single influence path
- `StrategySelectionResult` includes `pattern_aggregation_result` field
- `_build_explanation()` extended with pattern aggregation info

### Modified: `umh/runtime/__init__.py`

- Exports: `PatternAggregationResult`, `PatternContribution`, `compute_pattern_aggregation`

## Design decisions

### Dominance cap algorithm
Iterative cap-and-redistribute: lock any weight ≥ 0.7 at exactly 0.7,
redistribute remaining budget proportionally among uncapped weights.
Converges in at most N iterations (N = number of weights). Guarantees
`max(weights) <= 0.7` after completion.

Initial single-pass cap+renormalize was insufficient — renormalization
could push weights back above the cap.

### Weighting scheme
`raw_weight_i = similarity_i × confidence` (global confidence from PatternResult).
Normalized to sum=1.0 before dominance cap.

### Gate ordering
Per-pattern gates (sample_size, similarity, stats) filter first.
Global confidence gate applied after filtering to avoid rejecting
individually-qualifying patterns due to a global threshold.

## Invariants (334–343)

| Inv | Description | Enforced by |
|-----|-------------|-------------|
| 334 | Max 5 patterns | `qualifying[:_MAX_PATTERNS]` |
| 335 | Weights normalized to sum=1.0 | normalization + dominance cap |
| 336 | No single pattern > 70% weight | `_apply_dominance_cap()` |
| 337 | Deterministic ordering | sorted by (-similarity, key tuple) |
| 338 | Factor bounded [0.9, 1.1] | `__post_init__` clamp + computation clamp |
| 339 | Read-only from pattern memory | no PatternMemory mutation |
| 340 | All Phase 68 gates apply per-pattern | gate checks in qualifying loop |
| 341 | Neutral on failure | `_neutral()` returns factor=1.0 |
| 342 | Explainability via contributions | `PatternContribution` + `to_dict()` |
| 343 | Composable with all 5 other factors | multiplicative in `final_score` |

## Test coverage

17 test classes, 67 tests:

- Gating (5): disabled, no result, no match, empty matches, default config
- Per-pattern gating (4): low samples, low similarity, no stats, low confidence
- Multiple patterns (4): returned, sorted, capped at 5, single still works
- Weighting (4): normalize to 1, higher sim → more weight, low conf → low weight, equal
- Aggregation (5): influence result, bounded high, bounded low, contributions sum, neutral
- Dominance (6): below cap, above cap, constant value, direct function tests, empty
- Safety (3): can't flip winner, always in bounds, max patterns limit
- Neutral (2): no patterns, all filtered
- Determinism (2): repeat runs, ordering
- Explainability (5): all fields, to_dict, result keys, contribution keys, gated reason
- Individual factor (7): positive/negative/neutral signal, clamped high/low, hard ceiling/floor
- Isolation (2): no mutation of memory, no mutation of result
- StrategyCandidate compat (2): factor from aggregation, default neutral
- Orchestrator integration (8): multi-pattern path, single-pattern path, disabled, to_dict, explanation, regime compat, six-factor composition, no config
- Edge cases (4): same similarity, zero baseline, high baseline, mixed directions
- E2E (2): from memory through aggregation, through orchestrator
- Phase 68 compat (2): single pattern uses Phase 68, same bounds

## Files changed

| File | Action |
|------|--------|
| `umh/runtime/pattern_aggregation.py` | Created |
| `umh/runtime/strategy_orchestrator.py` | Modified |
| `umh/runtime/__init__.py` | Modified |
| `tests/unit/test_phase69_pattern_aggregation.py` | Created |
| `tests/unit/test_phase58_strategy_orchestration.py` | Modified (import allowlist) |
| `docs/audits/phase69_pattern_aggregation_report.md` | Created |
