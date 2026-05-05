# Phase 63 — Regime-Scoped Weight Evolution Layer v1

## Status: COMPLETE

## Summary

Phase 63 extends Phase 62's global temporal weight evolution with regime-conditioned
learning. Weights now evolve independently per regime (STABLE, TREND_UP, TREND_DOWN,
SPIKE_UP, SPIKE_DOWN), with smooth blending between regime-specific and global weights
based on regime sample availability. Step-change clamping prevents discontinuities on
regime switches. The system remains bounded, deterministic, and disabled by default.

## Files

| File | Action | Purpose |
|------|--------|---------|
| `umh/runtime/regime_weight_evolution.py` | NEW | Core computation: regime-scoped evolution, blending, step clamping |
| `umh/runtime/__init__.py` | MODIFIED | 6 new exports |
| `tests/unit/test_phase63_regime_weights.py` | NEW | 165 tests across 68 sections |
| `docs/audits/phase63_regime_weight_evolution_report.md` | NEW | This report |

## Architecture

### Why Regime-Scoped Evolution

Phase 62's global evolution treats all observations equally regardless of the regime
in which they occurred. This fails to capture:
- Regime-specific patterns (a dimension predictive in TREND_UP may not be in SPIKE_DOWN)
- Sample scarcity in rare regimes (SPIKE regimes have fewer observations)
- Transition smoothness (abrupt weight changes on regime switch cause instability)

Phase 63 solves these by introducing per-regime observation partitioning, blend-factor
interpolation, and step-change clamping.

### Regime-Specific Learning

Each observation is tagged with its regime context via `RegimeObservation`. During
evolution, observations are partitioned by regime:

```
Global evolution:  evolve_weights(all_observations)
Regime evolution:  evolve_weights(regime_observations_only)
```

Both paths reuse Phase 62's `evolve_weights()` — no algorithm duplication.

### Blending Model

The blend factor controls the mix between regime-specific and global weights:

```
blend = clamp(regime_samples / (blend_scale * min_samples), 0, 1)
final_weight = blend * regime_weight + (1 - blend) * global_weight
```

| Regime Samples | blend_scale=2, min_samples=5 | Behavior |
|---------------|------------------------------|----------|
| 0 | blend=0.0 | Pure global |
| 5 | blend=0.5 | Half regime, half global |
| 10+ | blend=1.0 | Pure regime-specific |

This provides smooth data-driven transition from global (sparse regime data) to
regime-specific (abundant regime data).

### Neutral Regime (inv 282)

STABLE regime is designated as neutral. When active_regime is STABLE, regime-specific
evolution is bypassed entirely — only global weights are used (with step clamping).
Rationale: STABLE is the baseline state; regime-specific divergence adds noise
without signal.

### Step-Change Clamping (inv 281)

To prevent discontinuities on regime switches:

```
|weight_t - weight_t-1| <= max_step_change (default 0.05)
```

When `previous_weights` are provided, the final weight is clamped so it cannot
change by more than `max_step_change` per evolution step, regardless of how
different the regime-specific weight is from the previous weight.

### Safety Mechanisms

1. **Disabled by default**: requires explicit opt-in (inv 274)
2. **Bounded evolution**: all weights clamped to [0.0, 1.0] and within ±max_adjustment of base (inv 274)
3. **No runaway amplification**: each step bounded by max_adjustment and max_step_change (inv 275)
4. **Sample gate**: < min_samples → neutral (Phase 62 gate applies per partition)
5. **Variance damping**: high variance → delta *= 0.5 (Phase 62 damping)
6. **Step-change clamping**: prevents discontinuities (inv 281)
7. **Neutral regime**: STABLE bypasses regime-specific evolution (inv 282)

### Decay vs Memory Tradeoff

Inherits Phase 62's decay model. Decay rate applies independently to global and
regime-specific partitions. With `blend_scale=2.0`, regime evolution only reaches
full influence when regime_samples >= 2 * min_samples.

## Invariants

| # | Statement | Verification |
|---|-----------|-------------|
| 274 | Regime-scoped evolution bounded to [0.0, 1.0] | Clamping at every stage; never negative; never > 1.0 |
| 275 | No runaway even across many regime switches | 10-step sequential test; max_adjustment + max_step_change bounds compound |
| 276 | Observations partition cleanly by regime | Each RegimeObservation tagged with regime; dict[RegimeType, list] partitioning |
| 277 | Regime with < min_samples → global fallback | Blend factor = 0 when regime_samples = 0; sample gate in evolve_weights |
| 278 | Deterministic updates | No random; 100-run determinism test passes |
| 279 | No mutation of historical observations | RegimeObservation and WeightObservation are frozen dataclasses |
| 280 | Every result is explainable | RegimeDimensionEvolution has blend_factor, regime/global quality, step_clamped, explanation |
| 281 | Step-change clamp prevents weight discontinuity | |weight_t - weight_t-1| <= max_step_change; verified with previous_weights |
| 282 | Neutral regime always uses global weights | STABLE → _is_neutral_regime → bypass regime evolution; blend_factor=0 |
| 283 | No algorithm duplication with Phase 62 | Reuses evolve_weights() and all internal functions via import |

## No Circular Dependencies

```
regime_weight_evolution.py
  ├── imports from: weight_evolution (evolve_weights, _evolve_single_dimension, etc.)
  ├── imports from: dimension_weighting (DimensionWeight, DimensionWeightVector)
  ├── imports from: regime (RegimeType)
  └── imports from: regime_aggregation (DimensionName)
```

Never imports from strategy_orchestrator, feedback_selection, weighted_decision,
or any scoring module. Phase 62's weight_evolution.py is not modified.

## Integration Path

The regime-evolved weights feed into the existing pipeline:

```
Phase 63: evolve_regime_weights(base, observations, tick, regime, prev, config)
    → DimensionWeightVector (regime-evolved)
        → Phase 61: weighted_decision_policy + evolved weights
            → Phase 58: orchestrate_selection(dimension_weights=evolved)
```

No modifications to any prior phase module were needed — regime_weight_evolution.py
produces a standard DimensionWeightVector that drops into the existing pipeline.

## Known Limitations

1. **No cross-regime transfer learning**: regime evolutions are fully independent
2. **No regime transition prediction**: doesn't anticipate upcoming regime changes
3. **Fixed blend_scale**: same blend curve for all regimes; rare regimes might
   benefit from slower blending
4. **No regime-specific learning rates**: all regimes share the same learning_rate
5. **Binary neutral regime**: only STABLE is neutral; no partial neutrality for
   low-volatility regimes
6. **No regime confidence weighting**: blend factor based only on sample count,
   not on regime classification confidence

## Test Coverage

- 165 tests across 68 sections
- Coverage areas: config defaults/bounds/dict/frozen, RegimeObservation creation/dict,
  evolution defaults/frozen/bounded, result defaults/dict/get, blend factor computation
  (zero/partial/full/boundary), step-change clamping (within/exceeds/negative),
  neutral regime behavior, disabled behavior, no regime data, regime-specific learning,
  different regimes (all 5 types), blending with low/high samples, stability/smoothness,
  dimension isolation, max_adjustment clamping, 100-run determinism, neutral regime
  invariant, no mutation, explainability (result/dimension/gated/disabled), observation
  counts, missing weights, dependency checks, no randomness, no subprocess,
  Phase 62/61/60/59/58 regression, init exports, roundtrips, zero learning rate,
  zero max adjustment, stress (500/2000 obs), evolved source tag, custom base weights,
  full pipeline, blend progression, multi-regime history, evolution chain convergence,
  symmetry, config custom, decay influence, all regime types, active regime tracking,
  variance damping, single dimension, regime vs global divergence, previous weights
  step clamp, empty observations, sample gate, neutral signals, learning rate sensitivity,
  decay rate sensitivity, to_dict completeness, regime observation dict, multi-dim per
  regime, no runaway, disabled with regime, cross-regime stress, blend edge cases,
  regime switch transition, partial signals, init regression

## Phase 64 Safety

Phase 64 is safe to proceed. Potential directions:
- Cross-regime transfer learning (share signal across similar regimes)
- Adaptive blend scale (different blending rates per regime)
- Regime-specific learning rates
- Regime transition prediction (pre-adapt weights to anticipated regime)
- Evolution memory persistence (save/load evolved state across sessions)
- Regime confidence integration (weight blending by classification confidence)
