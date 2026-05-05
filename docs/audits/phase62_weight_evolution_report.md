# Phase 62 — Temporal Weight Evolution Layer v1

## Status: COMPLETE

## Summary

Phase 62 introduces time-aware evolution of dimension weights. Weights now
strengthen when a dimension consistently predicts outcomes, weaken when
inconsistent, and decay toward neutral over time. The system remains bounded,
deterministic, and disabled by default.

## Files

| File | Action | Purpose |
|------|--------|---------|
| `umh/runtime/weight_evolution.py` | NEW | Core computation: decayed quality, evolution, variance damping |
| `umh/runtime/__init__.py` | MODIFIED | 6 new exports |
| `tests/unit/test_phase62_weight_evolution.py` | NEW | 169 tests across 67 sections |
| `docs/audits/phase62_weight_evolution_report.md` | NEW | This report |

## Architecture

### Why Temporal Evolution

Static weights (Phase 60) are computed from a snapshot of outcome history.
They don't account for:
- Regime changes over time (a dimension that was predictive may stop being so)
- Recency bias (recent outcomes are more informative than old ones)
- Progressive learning (weights should gradually adapt, not jump)

Phase 62 solves these by introducing exponential time decay and bounded
incremental updates.

### Signal Quality Model

For each dimension, quality is computed as the time-decayed weighted mean of
`outcome_score * direction_signal`:

```
quality = Σ(signal_i * decay^age_i) / Σ(decay^age_i)

where:
    signal_i = outcome_score_i * direction_signal_i
    age_i = current_tick - obs_tick_i
    decay = decay_rate (default 0.98)
```

Quality ranges from -1.0 (dimension anti-predicts outcomes) to +1.0
(dimension perfectly predicts outcomes).

### Update Rule

```
delta = learning_rate * quality
evolved_weight = base_weight + delta
clamped to [base_weight - max_adj, base_weight + max_adj]
```

### Safety Mechanisms

1. **Sample gate**: < min_samples → neutral (no evolution)
2. **Variance damping**: high variance in signals → delta *= 0.5
3. **Max adjustment**: evolved weight bounded within ±max_adjustment of base
4. **Disabled by default**: requires explicit opt-in

### Decay vs Memory Tradeoff

| Decay Rate | Behavior | Use Case |
|------------|----------|----------|
| 0.50 | Aggressive: old data barely counts | Rapidly changing environments |
| 0.90 | Moderate: ~10% loss per tick | Normal operation |
| 0.98 | Conservative (default): slow fade | Stable environments |
| 1.00 | No decay: all data equal | Controlled experiments |

The weighted-mean formulation means decay only affects the *relative importance*
of observations, not the absolute quality score. A single observation produces
the same quality regardless of its age — decay only changes results when multiple
observations at different ticks compete for influence.

### Stability vs Adaptability

The learning_rate × max_adjustment combination controls this tradeoff:

| learning_rate | max_adjustment | Behavior |
|---------------|---------------|----------|
| 0.01 | 0.05 | Very stable: tiny, tightly clamped changes |
| 0.05 | 0.15 | Default: moderate adaptation |
| 0.10 | 0.30 | Responsive: larger swings allowed |
| 0.50 | 0.50 | Aggressive: approaches full adaptation |

Sequential evolution (feeding evolved weights back as base) compounds, but
each step is individually bounded by max_adjustment, preventing runaway.

## Invariants

| # | Statement | Verification |
|---|-----------|-------------|
| 265 | Weight evolution must be bounded | Clamped to [base - max_adj, base + max_adj]; never negative; never > 1.0 |
| 266 | No runaway amplification | Each step bounded by max_adjustment; 10-step sequential test passes |
| 267 | Recent data > old data | Exponential decay: decay_rate^age; demonstrated with mixed old+new observations |
| 268 | Sparse data → neutral behavior | Sample gate: count < min_samples → no evolution |
| 269 | Deterministic updates | No random; 100-run determinism test passes |
| 270 | No mutation of historical outcomes | Observations are frozen dataclasses; mutation test verifies |
| 271 | Evolution must be explainable | Every DimensionEvolution has quality, delta, samples, decay info |
| 272 | Missing history → default weights | None base/observations → default_weight_vector() |
| 273 | No cross-dimension contamination | Each dimension evolves from its own observations only |

## No Circular Dependencies

```
weight_evolution.py
  ├── imports from: dimension_weighting (DimensionWeight, DimensionWeightVector)
  └── imports from: regime_aggregation (DimensionName)
```

Never imports from strategy_orchestrator, feedback_selection, weighted_decision,
or any scoring module.

## Integration Path

The evolved weights feed naturally into the existing pipeline:

```
Phase 62: evolve_weights(base, observations, tick, config)
    → DimensionWeightVector (evolved)
        → Phase 61: weighted_decision_policy + evolved weights
            → Phase 58: orchestrate_selection(dimension_weights=evolved)
```

No modifications to dimension_weighting.py were needed — weight_evolution.py
produces a standard DimensionWeightVector that drops into the existing pipeline.

## Known Limitations

1. **Still correlation-based**: quality_score is a correlation proxy, not causal inference
2. **No causal inference**: can't distinguish "dimension predicted outcome" from "dimension correlated with outcome"
3. **No multi-step sequence learning**: each observation is independent, no temporal patterns
4. **No contextual bandit**: doesn't explore alternative weightings to improve learning
5. **No regime-specific weight evolution**: same evolution applies regardless of current regime
6. **No cross-dimension interaction**: dimensions evolve independently, missing synergies

## Test Coverage

- 169 tests across 67 sections
- Coverage areas: config defaults/bounds/dict/frozen, observation defaults/bounds/dict/frozen,
  evolution defaults/bounds/dict/frozen/delta, result defaults/dict/get, decayed_quality
  (empty/single/time_decay/multiple_ticks), signal_variance, disabled/no_history,
  positive/negative outcomes, decay influence (old vs recent, flag, no_decay),
  bounded (above/below/never_negative), no_runaway (repeated/10-step), sample_gate
  (below/at/above), mixed outcomes, variance damping, determinism (100-run),
  dimension isolation (2-dim/untouched/4-dim), no_mutation, explainability
  (result/dimension/gated/disabled), missing weights, dependency checks, no_randomness,
  no_execution, Phase 61/60/59/58 regression, init exports, roundtrips,
  zero_learning_rate, zero_max_adjustment, stress (500 obs, 2000 obs),
  evolved type/source, custom base weights, decay curve, sparse data, single_dimension,
  full pipeline, zero outcomes, neutral signals, init regression, learning_rate sensitivity,
  max_adjustment sensitivity, decay_rate sensitivity, partial signals, multi-dimension history,
  custom min_samples, symmetry, evolution chain, sequential stability, convergence, config custom

## Phase 63 Safety

Phase 63 is safe to proceed. Potential directions:
- Regime-specific weight evolution (different learning per regime state)
- Cross-dimension correlation discovery
- Adaptive learning rate (faster learning when quality is high)
- Evolution memory persistence (save/load evolved state across sessions)
