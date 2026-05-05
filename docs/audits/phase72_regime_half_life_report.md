# Phase 72 — Regime-Specific Half-Life Layer v1

**Date:** 2026-05-02
**Status:** Complete
**Invariants:** 363-372

## Summary

Phase 72 adds per-regime half-life adjustment on top of the adaptive
half-life (Phase 71). Different market regimes get different memory speeds:
stable regimes multiply the half-life up (longer memory), spike/chaos
regimes multiply it down (faster forgetting of old patterns).

## Architecture

### Why multiplicative composition

Additive composition would lose the volatility signal: a `+10` offset
on a half-life of 20 is a 50% change, but on a half-life of 100 it's
only 10%. Multiplicative composition (`final = vol_hl × multiplier`)
preserves the *ratio* regardless of the volatility-adjusted base.

### Why four categories, not five

The `RegimeType` enum has five values (STABLE, TREND_UP, TREND_DOWN,
SPIKE_UP, SPIKE_DOWN). For half-life purposes, direction doesn't matter —
an upward spike and a downward spike both signal unreliable old patterns.
The `RegimeCategory` enum collapses these into four: STABLE, TREND,
SPIKE, CHAOS. CHAOS has no direct `RegimeType` mapping but is reachable
via string labels, leaving room for future regime detection.

### Priority chain

```
regime_result.final_half_life  >  adaptive_result.computed_half_life  >  config.half_life
```

The temporal weighting module checks in this order and uses the first
applied result. This is a clean override chain — no blending.

### Default multipliers

| Category | Multiplier | Effect |
|----------|-----------|--------|
| STABLE   | 1.5       | +50% memory |
| TREND    | 1.0       | neutral |
| SPIKE    | 0.6       | −40% memory |
| CHAOS    | 0.4       | −60% memory |

These satisfy invariant 364: STABLE ≥ TREND ≥ SPIKE ≥ CHAOS.

## Formula

```
category = classify_regime_category(regime_type, regime_label)
multiplier = config.regime_multipliers[category]
raw = volatility_half_life × multiplier
final = clamp(raw, min_half_life, max_half_life)
```

Where `volatility_half_life` comes from Phase 71 adaptive result
(or falls back to `base_half_life` if adaptive is disabled/unapplied).

## Files

| File | Action | Description |
|------|--------|-------------|
| `umh/runtime/regime_half_life.py` | NEW | Config, classification, regime computation |
| `umh/runtime/pattern_temporal.py` | MODIFIED | Accepts regime result, priority chain |
| `umh/runtime/__init__.py` | MODIFIED | New exports |
| `tests/unit/test_phase72_regime_half_life.py` | NEW | 118 tests |

## Invariants

| # | Statement | Verified |
|---|-----------|----------|
| 363 | Multiplicative composition | TestInvariant363Multiplicative |
| 364 | STABLE ≥ TREND ≥ SPIKE ≥ CHAOS ordering | TestInvariant364Ordering |
| 365 | No negative or zero half-life | TestInvariant365NoNegativeOrZero |
| 366 | Deterministic (no randomness) | TestInvariant366Deterministic |
| 367 | No mutation of historical records | TestInvariant367NoMutation |
| 368 | No feedback coupling | TestInvariant368NoFeedbackCoupling |
| 369 | Missing regime → multiplier = 1.0 | TestInvariant369MissingRegime |
| 370 | Explainable result fields | TestInvariant370Explainable |
| 371 | Smooth transitions (bounded ratio) | TestInvariant371SmoothTransitions |
| 372 | Clamped to [min, max] | TestInvariant372Bounded |

## Known Limitations

- No per-pattern regime (all patterns share one regime per cycle)
- No regime transition smoothing (step change on regime switch)
- No regime confidence weighting (binary classification)
- No multi-regime blending (single category per step)
- No historical regime memory (current regime only)
- CHAOS not reachable from RegimeType enum (requires string label)

## Safety

- Off by default (`enabled: False`)
- Missing regime → TREND (neutral multiplier 1.0)
- Output clamped to `[min_half_life, max_half_life]`
- No mutation of AdaptiveHalfLifeResult or pattern records
- Fully backward compatible: existing callers with no regime args unchanged
- All Phase 67-72 tests pass (683 total)

## Composition Stack

```
Phase 70: temporal decay    — exp(-ln2 × age / half_life)
Phase 71: adaptive hl       — base × (1 + (1-vol) × sens)
Phase 72: regime hl          — adaptive_hl × regime_multiplier
```

Each layer is independently gated. Any subset can be enabled.
