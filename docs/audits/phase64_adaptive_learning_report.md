# Phase 64 — Adaptive Learning Rate Layer v1

## Status: COMPLETE

## Summary

Phase 64 replaces the fixed learning rate in weight evolution with a data-driven
adaptive rate that scales based on confidence (data quality) and stability (signal
consistency). High-confidence, low-variance signals learn faster; low-confidence
or noisy signals learn slower. The system remains bounded, deterministic, and
disabled by default.

## Files

| File | Action | Purpose |
|------|--------|---------|
| `umh/runtime/adaptive_learning.py` | NEW | Core computation: confidence factor, stability factor, adaptive rate |
| `umh/runtime/weight_evolution.py` | MODIFIED | Added optional adaptive_config + dimension_confidences params |
| `umh/runtime/regime_weight_evolution.py` | MODIFIED | Pass-through adaptive params to evolve_weights calls |
| `umh/runtime/__init__.py` | MODIFIED | 4 new exports |
| `tests/unit/test_phase62_weight_evolution.py` | MODIFIED | Updated dependency whitelist for adaptive_learning |
| `tests/unit/test_phase64_adaptive_learning.py` | NEW | 137 tests across 68 sections |
| `docs/audits/phase64_adaptive_learning_report.md` | NEW | This report |

## Architecture

### Why Adaptive Learning Rates

Phase 62's fixed `delta = learning_rate * quality` fails in two scenarios:
- **Strong consistent signal, high confidence**: Fixed rate of 0.05 is too
  conservative. The system has good data but learns slowly.
- **Weak noisy signal, low confidence**: Fixed rate of 0.05 is too aggressive.
  The system has poor data but updates weights the same amount.

Phase 64 solves this by modulating the learning rate based on two factors that
capture data quality and signal reliability.

### Adaptive Rate Formula

```
adaptive_rate = clamp(base_rate * confidence_factor * stability_factor,
                      min_rate, max_rate)
```

### Confidence Factor

```
confidence_factor = clamp(confidence, 0, 1)
```

Simple linear scaling. The caller provides a per-dimension confidence value
(from outcome tracking, attribution, or any upstream signal quality metric).

| Confidence | Factor | Effect |
|------------|--------|--------|
| 0.0 | 0.0 | No learning (inv 286) |
| 0.5 | 0.5 | Half rate |
| 1.0 | 1.0 | Full rate (inv 285) |

### Stability Factor (Smooth Dampening)

```
stability_factor = 1 / (1 + variance / threshold)
```

Smooth sigmoid-like curve instead of Phase 62's binary 0.5 step. Approaches
zero asymptotically as variance grows — never fully kills learning.

| Variance / Threshold | Factor | Behavior |
|---------------------|--------|----------|
| 0.0 | 1.0 | No noise, full rate |
| 1.0 | 0.5 | At threshold, half rate |
| 4.0 | 0.2 | High noise, heavy dampening |

### Rate Clamping (inv 284)

```
min_rate (0.005) <= adaptive_rate <= max_rate (0.10)
```

Even with zero confidence, the floor ensures some minimal learning. Even with
perfect confidence on consistent signals, the ceiling prevents overshooting.

### Safety Mechanisms

1. **Disabled by default**: requires explicit opt-in
2. **Bounded rate**: clamped to [min_rate, max_rate] (inv 284)
3. **No amplification**: max_adjustment from Phase 62 still applies (inv 289)
4. **No cross-dimension contamination**: each dimension gets its own confidence (inv 290)
5. **Deterministic**: no randomness (inv 288)
6. **Fallback**: missing config/confidence/observations → base_rate (inv 292)

### Integration Design

Phase 64 integrates via optional parameters — zero changes to existing call sites:

```
# Phase 62: unchanged call
evolve_weights(observations=obs, current_tick=20, config=cfg)

# Phase 64: opt-in adaptive
evolve_weights(observations=obs, current_tick=20, config=cfg,
               adaptive_config=acfg, dimension_confidences=dim_conf)
```

The `adaptive_config` parameter flows through:
- `evolve_weights()` → `_evolve_single_dimension()` → `compute_adaptive_rate()`
- `evolve_regime_weights()` → `evolve_weights()` (both global and regime-specific)

When `adaptive_config` is None or disabled, behavior is identical to Phase 62/63.

### Interaction with Phase 62 Variance Damping

Phase 62's binary variance damping (`delta *= 0.5` when variance > threshold) and
Phase 64's smooth stability factor both reduce delta under noise. They compound:
- Phase 64 reduces the effective learning rate
- Phase 62 then applies its own 0.5 multiplier on top

This double-dampening is intentional — noisy signals get extra protection. Users
who enable Phase 64 may want to raise Phase 62's variance_damping_threshold to
avoid over-dampening.

## Invariants

| # | Statement | Verification |
|---|-----------|-------------|
| 284 | Learning rate bounded to [min_rate, max_rate] | Clamped after computation; tested with edge configs |
| 285 | High confidence → faster learning | confidence=1.0 produces higher rate than 0.1; monotonic test |
| 286 | Low confidence → near-zero learning | confidence=0.0 produces min_rate; tested |
| 287 | High variance → dampened learning | stability_factor < 0.5 for high-variance signals; smooth curve test |
| 288 | Deterministic computation | 100-run identical results; no random import |
| 289 | No amplification beyond max_adjustment | Evolved weight bounded by Phase 62's max_adjustment regardless of adaptive rate |
| 290 | No cross-dimension contamination | Each dimension uses its own confidence; 4-dim test verifies |
| 291 | No mutation of historical outcomes | Frozen dataclasses; observation values unchanged after compute |
| 292 | Missing data → fallback to base_rate | None observations/config → base_rate; tested |
| 293 | Adaptive rate must be explainable | Result includes base_rate, confidence_factor, stability_factor, variance, explanation string |

## No Circular Dependencies

```
adaptive_learning.py
  └── imports from: weight_evolution (WeightObservation, _compute_signal_variance)

weight_evolution.py
  ├── imports from: dimension_weighting
  ├── imports from: regime_aggregation
  └── lazy import from: adaptive_learning (inside _evolve_single_dimension, only when enabled)

regime_weight_evolution.py
  ├── imports from: weight_evolution (evolve_weights, etc.)
  ├── imports from: dimension_weighting
  ├── imports from: regime (RegimeType)
  └── imports from: regime_aggregation (DimensionName)
  (adaptive_config passed through to evolve_weights, no direct import)
```

The lazy import in weight_evolution.py prevents a circular dependency:
adaptive_learning imports from weight_evolution, so weight_evolution cannot
import from adaptive_learning at module level.

## Integration Path

```
Phase 64: compute_adaptive_rate(observations, confidence, config)
    → AdaptiveLearningResult.adaptive_rate
        → Phase 62: _evolve_single_dimension uses adaptive_rate instead of fixed learning_rate
            → Phase 63: evolve_regime_weights passes adaptive_config through
                → Phase 61: weighted_decision_policy
                    → Phase 58: orchestrate_selection
```

## Known Limitations

1. **Still correlation-based**: adaptive rate improves learning speed, not signal quality
2. **No regime-dependent learning rate**: same adaptive config for all regimes
3. **No cross-dimension coupling**: confidence is per-dimension, no synergy modeling
4. **No long-term meta-learning**: doesn't learn optimal rates over time
5. **Confidence must be provided externally**: no built-in confidence computation
6. **Double-dampening possible**: Phase 62 variance damping + Phase 64 stability factor
   can over-dampen; users should tune thresholds when both are active

## Test Coverage

- 137 tests across 68 sections
- Coverage areas: config defaults/bounds/frozen/dict, result defaults/frozen/bounds/dict,
  confidence factor (zero/full/half/negative/above), stability factor
  (zero/threshold/high/low/zero_threshold/very_high), disabled behavior,
  no observations fallback, high confidence → higher rate, low confidence → near zero,
  high variance → dampened, rate bounded (min/max/non-negative), 100-run determinism,
  no mutation, explainability (factors/rates/dict), fallback (missing config/observations),
  evolve_single_dimension integration (disabled/enabled/high_conf/zero_conf/explanation),
  evolve_weights integration (none/modulation/disabled), dimension isolation
  (independent/untouched), no amplification (bounded/10-step), convergence
  (strong signal fast/noisy slow), regime integration (adaptive/fixed comparison),
  default config, dependencies, no randomness, no child processes,
  Phase 62/63/61/60/59/58 regression, init exports, roundtrips, zero learning rate,
  stress (500/2000 obs), confidence spectrum (monotonic/range), variance spectrum,
  full pipeline, custom configs (aggressive/conservative/tight), symmetry,
  adaptive + variance damping compound, single observation, neutral signals,
  learning rate sensitivity, decay interaction, partial confidences,
  min equals max, multi-dim independent rates, sample gate + adaptive,
  negative signals, zero outcomes, all-zero config, stability curve
  (smooth/asymptotic), source tag, sequential stability, mixed confidence,
  init regression, variance threshold sensitivity, confidence input preserved,
  disabled with observations, compound integration (regime + adaptive + step clamp),
  max < base edge, mixed outcomes, no oscillation, to_dict completeness

## Phase 65 Safety

Phase 65 is safe to proceed. Potential directions:
- Built-in confidence computation (derive confidence from outcome history)
- Regime-specific adaptive configs (different learning curves per regime)
- Meta-learning (adapt the adaptive rate parameters over time)
- Cross-dimension confidence coupling
- Adaptive threshold auto-tuning
