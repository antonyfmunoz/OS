# Phase 65 — Regime-Dependent Adaptive Learning Layer v1

## Status: COMPLETE

## Summary

Phase 65 extends Phase 64's adaptive learning rate with regime-specific modulation.
Different regimes get different learning speeds: SPIKE regimes adapt faster (1.5x),
TREND regimes at baseline (1.0x), STABLE regimes slower (0.5x). Transition smoothing
prevents abrupt factor changes on regime switches. The system remains bounded,
deterministic, backward-compatible, and disabled by default.

## Files

| File | Action | Purpose |
|------|--------|---------|
| `umh/runtime/regime_adaptive_learning.py` | NEW | Regime factor resolution, transition smoothing, regime-adaptive rate computation |
| `umh/runtime/adaptive_learning.py` | MODIFIED | Added regime_factor field + param to compute_adaptive_rate |
| `umh/runtime/weight_evolution.py` | MODIFIED | Added regime_factor pass-through to _evolve_single_dimension and evolve_weights |
| `umh/runtime/regime_weight_evolution.py` | MODIFIED | Computes regime factor via lazy import, passes to evolve_weights |
| `umh/runtime/__init__.py` | MODIFIED | 4 new exports (RegimeAdaptiveConfig, RegimeAdaptiveResult, compute_regime_adaptive_rate, DEFAULT_REGIME_ADAPTIVE_CONFIG) |
| `tests/unit/test_phase64_adaptive_learning.py` | MODIFIED | Added regime_factor to expected to_dict keys |
| `tests/unit/test_phase65_regime_adaptive.py` | NEW | 121 tests across 68 sections |
| `docs/audits/phase65_regime_adaptive_learning_report.md` | NEW | This report |

## Architecture

### Why Regime-Dependent Learning Rates

Phase 64's adaptive rate scales by confidence and stability but treats all regimes
equally. This fails in two scenarios:
- **SPIKE regimes**: Short-lived events that require fast reaction. A standard
  learning rate misses the window before the regime ends.
- **STABLE regimes**: Long periods of noise where aggressive learning amplifies
  random fluctuations. Slower adaptation filters noise.

Phase 65 solves this by multiplying a regime-specific factor into the adaptive rate
formula.

### Extended Adaptive Rate Formula

```
adaptive_rate = clamp(base_rate * confidence_factor * stability_factor * regime_factor,
                      min_rate, max_rate)
```

### Regime Factors (defaults)

| Regime | Factor | Rationale |
|--------|--------|-----------|
| STABLE | 0.5 | Slow adaptation, noise suppression |
| TREND_UP | 1.0 | Baseline, track steadily |
| TREND_DOWN | 1.0 | Baseline, track steadily |
| SPIKE_UP | 1.5 | Fast adaptation, short-lived signals |
| SPIKE_DOWN | 1.5 | Fast adaptation, short-lived signals |

### Factor Resolution Rules

1. `regime is None` → factor = 1.0 (neutral, inv 302)
2. `regime_sample_count < min_regime_samples` → factor = 1.0 (insufficient data, inv 296)
3. `regime is STABLE` → uses config factor regardless of sample count (inv 300)
4. Otherwise → config factor for that regime

### Transition Smoothing

Prevents abrupt factor changes when regime switches:
```
delta = target_factor - previous_factor
if abs(delta) <= max_delta:
    smoothed = target_factor  (no smoothing needed)
else:
    smoothed = previous_factor + max_delta * sign(delta)
```

Default `max_factor_delta = 0.2` means a jump from STABLE (0.5) to SPIKE_UP (1.5)
takes 5 steps to fully transition, not 1.

### Factor Bounds

All regime factors are clamped to [0.1, 3.0] in both config and result.

## Invariants

| ID | Invariant | Mechanism |
|----|-----------|-----------|
| 294 | Adaptive rate bounded [min_rate, max_rate] | clamp in compute_regime_adaptive_rate |
| 295 | Regime factor bounded [0.1, 3.0] | __post_init__ clamping on config and result |
| 296 | Insufficient regime samples → neutral factor | _resolve_regime_factor returns 1.0 when count < min |
| 297 | Smoothing prevents abrupt transitions | _smooth_regime_factor clamps delta to max_factor_delta |
| 298 | Deterministic — same inputs → same output | Pure computation, no randomness, no I/O |
| 299 | Explainable — explanation field traces every factor | explanation string in RegimeAdaptiveResult |
| 300 | STABLE regime uses config factor regardless of samples | Explicit check in _resolve_regime_factor |
| 301 | Disabled config → delegates to Phase 64 base | rcfg.enabled=False → compute_adaptive_rate passthrough |
| 302 | Missing regime → factor = 1.0 | _resolve_regime_factor returns 1.0 for None |

## Backward Compatibility

- `RegimeAdaptiveConfig.enabled` defaults to `False` — no behavior change unless opted in
- `regime_factor=1.0` default in adaptive_learning.py is multiplicative identity
- `regime_factor=1.0` default in weight_evolution.py preserves Phase 64 behavior exactly
- All Phase 64 tests pass (137/137) with no modifications beyond to_dict key addition
- All Phase 62-63 tests pass (334/334) unchanged

## Circular Dependency Strategy

```
regime_adaptive_learning.py ──imports──→ adaptive_learning.py
regime_adaptive_learning.py ──imports──→ weight_evolution.py (WeightObservation, _compute_signal_variance)
regime_weight_evolution.py  ──lazy──→ regime_adaptive_learning.py (_resolve_regime_factor, _smooth_regime_factor)
weight_evolution.py         ──lazy──→ adaptive_learning.py (compute_adaptive_rate)
```

Lazy imports inside `if` blocks break potential cycles. No module-level circular dependencies.

## Test Coverage

121 tests across 68 sections covering:
- Config defaults, bounds, frozen, to_dict
- Result defaults, frozen, bounds, to_dict
- Factor resolution (all regime types, None, insufficient samples)
- Transition smoothing (within delta, exceeding delta, direction)
- Disabled behavior (passthrough to Phase 64)
- No observations fallback
- Regime ordering (SPIKE > TREND > STABLE)
- max_rate bounding
- Determinism (100-run consistency)
- Explainability (explanation field populated)
- Isolation (no cross-dimension contamination)
- Composition with Phase 64 adaptive learning
- evolve_weights integration
- regime_weight_evolution integration
- No mutation (frozen dataclasses)
- Variance/confidence interaction
- Full pipeline (all 3 layers enabled)
- No oscillation / no runaway (multi-step)
- Edge cases (zero base rate, single observation, partial factor maps)

## Regression

| Suite | Tests | Status |
|-------|-------|--------|
| Phase 30-57 | 3474 | PASS |
| Phase 58-65 | 1200 | PASS |
| **Total** | **4674** | **ALL PASS** |

## Composition Stack

```
Phase 62: weight_evolution     — delta = learning_rate * quality
Phase 64: adaptive_learning    — adaptive_rate = base * confidence * stability
Phase 65: regime_adaptive      — regime_rate = base * confidence * stability * regime_factor
```

Each layer wraps the previous. All three can be enabled simultaneously.
When all enabled: regime factor modulates the adaptive rate which replaces the fixed rate.
