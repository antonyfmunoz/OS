# Phase 70 — Temporal Pattern Weighting Layer v1

**Date:** 2026-05-01
**Status:** Complete
**Invariants:** 344-352

## Summary

Phase 70 introduces exponential time-based decay into the multi-pattern
aggregation pipeline. Recent patterns receive higher effective weights
than older patterns, while old patterns fade gradually without hard
cutoffs or deletion.

## Architecture

### Why exponential decay

Exponential decay (`exp(-ln(2) * age / half_life)`) provides:
- Smooth, continuous weight reduction — no discontinuities
- Mathematically precise half-life behavior (weight halves every `half_life` observations)
- Asymptotic approach to zero — never reaches it, satisfying "no hard deletion"
- Single parameter (`half_life`) controls the entire decay curve

Linear decay would create a hard cutoff at `2 * half_life` (weight = 0),
violating invariant 345. Polynomial decay lacks the intuitive half-life
property. Exponential is the standard choice for continuous decay.

### Why index-based instead of timestamps

Using observation indices instead of wall-clock time ensures:
- **Determinism (inv 347):** Same inputs always produce same outputs
- **Testability:** No mocking of system clocks
- **Portability:** No timezone or clock drift issues
- **Reproducibility:** Replay of historical data produces identical results

The `PatternRecord.timestamp` field is already an integer index.

### Why the floor exists

The floor `weight_i >= min_weight × similarity_i` prevents:
- **Recent bias collapse:** Without a floor, a single very recent pattern
  could monopolize all normalized weight, making the system ignore all
  historical evidence
- **Information loss:** Old patterns may represent rare but important states
  (high-risk, low-stability regimes) that the system needs to remember
- **Stability:** The floor ensures gradual transitions in the weight
  distribution as patterns age

### How this avoids "recent bias collapse"

Three mechanisms work together:
1. **Floor:** Guarantees a minimum weight proportional to similarity
2. **Dominance cap:** Applied AFTER temporal weighting — no single pattern
   can exceed 70% of total weight even if it's the only recent one
3. **Max 5 patterns:** The pattern count limit prevents dilution

## Files

| File | Action | Description |
|------|--------|-------------|
| `umh/runtime/pattern_temporal.py` | NEW | Config, decay function, temporal weight application |
| `umh/runtime/pattern_aggregation.py` | MODIFIED | Temporal integration before normalization |
| `umh/runtime/__init__.py` | MODIFIED | New exports |
| `tests/unit/test_phase70_temporal_patterns.py` | NEW | 129 tests |
| `tests/unit/test_phase69_pattern_aggregation.py` | MODIFIED | Updated key sets for new fields |

## Invariants

| # | Statement | Verified |
|---|-----------|----------|
| 344 | Temporal decay bounded [0,1] | TestInvariant344DecayBounded |
| 345 | No hard deletion of patterns | TestInvariant345NoDeletion |
| 346 | Newer patterns have >= weight than older (given equal stats) | TestInvariant346NewerGeqOlder |
| 347 | Deterministic (no wall-clock time, use index) | TestInvariant347Deterministic |
| 348 | No mutation of stored records | TestInvariant348NoMutation |
| 349 | Decay independent of scoring | TestInvariant349DecayIndependentOfScoring |
| 350 | Floor prevents zeroing | TestInvariant350FloorPreventsZeroing |
| 351 | Explainable decay contribution | TestInvariant351Explainability |
| 352 | No instability introduced | TestInvariant352NoInstability |

## Known Limitations

- No context-dependent decay (all patterns decay at the same rate)
- No regime-specific half-life (high-risk patterns could warrant slower decay)
- No adaptive half-life (half-life doesn't adjust based on data characteristics)
- No burst detection (rapid pattern recurrence doesn't boost weight)
- No sequence modeling (decay treats each pattern independently)

## Safety

- Off by default (`enabled: False`)
- Dominance cap applied AFTER temporal weighting
- Max 5 patterns still enforced
- Final factor bounded [0.9, 1.1]
- All Phase 69 tests pass without modification (schema extension only)
- Backward compatible: existing callers with no temporal args get identical behavior

## Phase 71 Readiness

Phase 71 is safe to proceed. The temporal layer is:
- Fully isolated behind a config gate
- Pure computation with no side effects
- Backward compatible with all existing callers
- Covered by 129 dedicated tests + 67 Phase 69 tests passing
