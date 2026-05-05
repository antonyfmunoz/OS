# Phase 67 — Contextual Pattern Recognition Layer v1

## Status: COMPLETE

## Summary

Phase 67 adds contextual pattern recognition — append-only memory of composite
dimension states with similarity-based matching. The system records what composite
states have occurred before (PatternKey: trend + risk + stability + urgency) alongside
outcome scores, then recognizes similar states from memory when they recur.

The core constraint: pattern recognition is purely observational. Matching results
are informational only, never influencing scoring (inv 320). This avoids feedback
loops where pattern recognition biases future outcomes.

## Files

| File | Lines | Action | Purpose |
|------|-------|--------|---------|
| `umh/runtime/pattern_memory.py` | 304 | NEW | PatternKey, PatternRecord, PatternMemory, PatternStats, extract_pattern_key, enums |
| `umh/runtime/pattern_matching.py` | 202 | NEW | PatternMatch, PatternResult, match_pattern, _compute_similarity, _compute_pattern_confidence |
| `umh/runtime/__init__.py` | 705 | MODIFIED | 12 new exports |
| `tests/unit/test_phase67_patterns.py` | 1685 | NEW | 177 tests across 68 sections |
| `docs/audits/phase67_pattern_recognition_report.md` | — | NEW | This report |

## Architecture

### Why Pattern Recognition Must Be Observational

Pattern matching that influences scoring creates a feedback loop:
1. Pattern X is recognized as historically successful
2. Scoring boosts pattern X
3. Pattern X succeeds more often (because it was boosted)
4. Memory records more successes for pattern X
5. The loop compounds — the system converges on whatever pattern it
   first got lucky with, regardless of actual environment conditions

Phase 67 breaks this loop by making pattern recognition purely informational.
The system knows "this situation has happened before, and outcomes were X" but
never acts on that knowledge in scoring. This is the foundation for future
phases that may introduce controlled, bounded influence.

### Pattern Key Design

PatternKey uses discrete string enums (no floats):
- `TrendDirection`: UP, DOWN, NEUTRAL
- `RiskLevel`: LOW, MEDIUM, HIGH
- `StabilityLevel`: LOW, MEDIUM, HIGH
- `UrgencyLevel`: LOW, MEDIUM, HIGH

This gives 3 × 3 × 3 × 3 = 81 possible composite states. Discrete keys
are safe for dict lookup and equality comparison — no floating-point hazards.

### Memory Design

PatternMemory is append-only (inv 313):
- Records are never deleted, mutated, or overwritten (inv 314)
- The only write operation is `append()`
- `get_records()` returns an immutable tuple
- Stats are computed on-demand from the full record list

### Similarity Matching

Simple dimension counting (inv 315):
```
similarity = (matching dimensions) / 4
```

No fuzzy ML, no learned similarity weights — pure discrete comparison.
Possible values: 0.0, 0.25, 0.5, 0.75, 1.0.

### Confidence Model

```
confidence = min(1.0, sample_size / min_samples)
```

Low sample size → low confidence (inv 322). Default min_samples = 10.

### Pattern Extraction

`extract_pattern_key()` maps from `AggregatedRegimeState` to `PatternKey`:
- Trend: uses `direction` (DirectionCategory → TrendDirection)
- Risk/Stability/Urgency: uses `regime_label` (string → enum)
- Missing dimensions default to neutral/medium (inv 317)
- None input → None output (inv 317)

## Invariants

| ID | Invariant | Mechanism |
|----|-----------|-----------|
| 313 | Append-only memory | No delete/remove/pop/clear methods |
| 314 | No mutation of records | Frozen dataclasses, tuple returns |
| 315 | Deterministic matching | Pure computation, sorted iteration, no randomness |
| 316 | Discrete keys only | String enums, no floats in PatternKey |
| 317 | Missing data → default/no match | None → None for extract, defaults for missing dims |
| 318 | Bounded similarity [0, 1] | Clamped in PatternMatch.__post_init__ |
| 319 | Bounded confidence [0, 1] | Clamped in PatternResult.__post_init__ |
| 320 | No scoring impact | Observational only — matching never affects scores |
| 321 | No circular dependency | pattern_memory → regime_aggregation only; pattern_matching → pattern_memory only |
| 322 | Low sample → low confidence | confidence = min(1.0, sample_size / min_samples) |

## Backward Compatibility

- No modifications to any existing module's behavior
- Pattern memory and matching are standalone — no upstream integration yet
- All Phase 30-66 tests continue to pass
- 12 new exports added to `__init__.py` (additive only)

## Known Limitations

- No upstream integration — pattern results are not yet used anywhere in the pipeline
- No persistence — PatternMemory is in-memory only, lost on restart
- No temporal decay — old patterns weighted equally with recent ones
- 81 possible keys is a small state space — may need finer granularity later
- Success threshold (0.6) is hardcoded, not configurable

## Test Coverage

177 tests across 68 sections covering:
- PatternKey basics, defaults, equality, to_tuple, to_dict, dimensions property
- PatternKey discrete-only (no float fields)
- PatternRecord immutability, clamping, to_dict
- PatternMemory append-only contract, size, get_records immutability
- PatternMemory get_records_for_key, compute_stats, compute_all_stats
- PatternMemory unique_keys, to_dict
- PatternStats clamping, defaults, to_dict
- Enum values (TrendDirection, RiskLevel, StabilityLevel, UrgencyLevel)
- extract_pattern_key (None, full state, missing dimensions, direction mapping)
- _compute_similarity (exact, partial, no match, symmetric)
- _compute_pattern_confidence (zero, below min, at min, above min, zero min_samples)
- PatternMatch defaults, clamping, to_dict
- PatternResult defaults, clamping, to_dict
- match_pattern: no query key, empty memory, exact match, partial match, no match
- Similarity bounded [0, 1]
- Determinism (100-run consistency)
- Low-sample confidence
- No scoring impact (observational only)
- Explainability (populated explanation strings)
- No combinatorial explosion (81 keys bounded)
- Multiple matches sorted correctly
- Success threshold 0.6
- No circular dependency (import whitelist)
- Exports verification (12 new exports)
- Edge cases (all defaults, single record, large memory)
- Symmetry of similarity
- Custom thresholds (min_similarity, min_samples)
- Roundtrip (record → stats → match consistency)
- Tied similarity (secondary sort by key tuple)
- High volume (27 unique keys)
- All enum combinations (81 keys)
- Confidence bounded [0, 1]
- Idempotent matching (same query twice = same result)

## Regression

| Suite | Tests | Status |
|-------|-------|--------|
| Phase 30-67 | 5011+ | PASS (0 failures through 93%, killed at ~4660) |
| Phase 58-67 | 799 | PASS |
| Phase 67 only | 177 | PASS |

## Composition Stack

```
Phase 59: regime_aggregation   — dimension regime classification
Phase 66: dimension_interactions — cross-dimension interaction factors
Phase 67: pattern_memory        — composite state recording
Phase 67: pattern_matching      — similarity-based state recognition
```

Pattern recognition sits alongside the scoring pipeline as an observational
layer. It reads from regime_aggregation types but does not feed back into
any scoring stage.

## Dependency Graph

```
regime_aggregation
    ↓
pattern_memory (reads AggregatedRegimeState, DimensionRegime types)
    ↓
pattern_matching (reads PatternKey, PatternMemory, PatternStats)
```

No reverse dependencies. No circular imports. No coupling to scoring pipeline.
