# Phase 71 — Adaptive Half-Life Layer v1

**Date:** 2026-05-02
**Status:** Complete
**Invariants:** 353-362

## Summary

Phase 71 makes temporal decay environment-responsive. Instead of a fixed
half-life, the system computes half-life dynamically from recent outcome
volatility: stable environments get longer memory, volatile environments
get shorter memory.

## Architecture

### Why variance is used

Outcome score variance measures *predictability*, not *quality*. A consistently
bad environment (low scores, low variance) is still predictable — patterns
from that state are reliable and should be remembered longer. Conversely,
a wildly fluctuating environment makes old patterns unreliable regardless
of their quality.

### Why not use performance

Using mean performance would create a feedback loop: good performance →
longer memory → more influence from old patterns → biased future decisions.
Variance avoids this because it measures dispersion, not direction. A
sequence `[0.9, 0.9, 0.9]` and `[0.1, 0.1, 0.1]` have identical variance
(zero), producing identical half-lives. This satisfies invariant 358.

### Why decay must remain independent

The adaptive half-life adjusts *how quickly* patterns fade, but the decay
function itself (`exp(-ln(2) * age / half_life)`) remains purely a function
of age and half-life. No scoring signals, no performance feedback, no
outcome-dependent behavior inside the decay computation. The half-life
is computed once from recent volatility and then used as a constant for
all patterns in that aggregation cycle.

### How this avoids feedback loops

Three safeguards:
1. **Variance, not mean:** Volatility uses score dispersion, not direction
2. **Window isolation:** Only the most recent N records contribute
3. **Clamped output:** Half-life is bounded by `[min_half_life, max_half_life]`

Even adversarial score sequences can only move the half-life within the
configured bounds — they cannot cause runaway behavior.

## Formula

```
variance = Σ(score_i - mean)² / N
volatility = clamp(variance / max_variance, 0, 1)
half_life = base × (1 + (1 - volatility) × sensitivity)
half_life = clamp(half_life, min, max)
```

- `max_variance = 0.25` (theoretical max for scores in [0, 1])
- Stable (vol=0): `half_life = base × (1 + sensitivity)` → longer
- Volatile (vol=1): `half_life = base × 1.0` → base value

## Files

| File | Action | Description |
|------|--------|-------------|
| `umh/runtime/adaptive_half_life.py` | NEW | Config, volatility, adaptive computation |
| `umh/runtime/pattern_temporal.py` | MODIFIED | Accepts adaptive result, reports effective half-life |
| `umh/runtime/__init__.py` | MODIFIED | New exports |
| `tests/unit/test_phase71_adaptive_half_life.py` | NEW | 137 tests |

## Invariants

| # | Statement | Verified |
|---|-----------|----------|
| 353 | Half-life always bounded | TestInvariant353Bounded |
| 354 | Stable environments increase memory | TestInvariant354StableIncreasesMemory |
| 355 | Volatile environments decrease memory | TestInvariant355VolatileDecreasesMemory |
| 356 | Deterministic (no randomness) | TestInvariant356Deterministic |
| 357 | No mutation of historical records | TestInvariant357NoMutation |
| 358 | No feedback from scoring | TestInvariant358NoFeedbackFromScoring |
| 359 | No abrupt jumps | TestInvariant359NoAbruptJumps |
| 360 | Explainable half-life | TestInvariant360Explainable |
| 361 | Missing data → fallback to base | TestInvariant361MissingDataFallback |
| 362 | No instability introduced | TestInvariant362NoInstability |

## Known Limitations

- No regime-specific adaptation (all regimes share one half-life)
- No per-pattern half-life (all patterns in a cycle share one half-life)
- No burst detection (rapid pattern recurrence doesn't boost weight)
- No directional volatility (upward vs downward variance treated equally)
- No multi-scale memory (single window, not multi-resolution)

## Safety

- Off by default (`enabled: False`)
- Missing/insufficient data → fallback to base_half_life
- Output clamped to `[min_half_life, max_half_life]`
- No mutation of PatternMemory or PatternRecords
- Fully backward compatible: existing callers with no adaptive args unchanged
- All Phase 67-70 tests pass without modification

## Phase 72 Readiness

Phase 72 is safe to proceed. The adaptive layer is:
- Fully isolated behind a config gate
- Pure computation with no side effects
- Backward compatible with all existing callers
- Covered by 137 dedicated tests + 565 tests passing across Phases 67-71
