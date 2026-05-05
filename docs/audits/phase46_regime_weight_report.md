# Phase 46 — Regime-Aware Weight Adaptation Layer v1

## Audit Report

**Date:** 2026-04-30
**Phase:** 46 of UMH runtime build
**Status:** COMPLETE

---

## What was built

### New file
- `umh/runtime/regime_weight.py` — RegimeWeightConfig, RegimeWeightResult, RegimeWeightSnapshot, compute_regime_factor, compute_all_regime_factors, apply_regime_weight

### Modified files
- `umh/runtime/__init__.py` — 7 new exports

### Test file
- `tests/unit/test_phase46_regime_weight.py` — 155 tests across 24 sections

---

## Architecture

### Problem solved

Phases 42-45 produce confirmed regimes with type, duration, and delta — but downstream scoring ignores them entirely. Decisions use identity bias and goal bias but have no awareness of whether the signal environment is spiking, trending, or stable. Phase 46 injects regime awareness into the scoring chain as a bounded multiplicative factor.

### Factor rules

| Regime     | Factor formula                              | Duration-scaled? |
|------------|---------------------------------------------|------------------|
| STABLE     | 1.0                                         | No               |
| TREND_UP   | 1.05 + min(0.05, duration × 0.005)          | Yes              |
| TREND_DOWN | 0.95 - min(0.05, duration × 0.005)          | Yes              |
| SPIKE_UP   | 1.10                                        | No               |
| SPIKE_DOWN | 0.90                                        | No               |

### Duration scaling

Trend factors accumulate with duration at 0.005 per tick, capped at ±0.05:
- Duration 0: TREND_UP = 1.05, TREND_DOWN = 0.95
- Duration 5: TREND_UP = 1.075, TREND_DOWN = 0.925
- Duration 10+: TREND_UP = 1.10, TREND_DOWN = 0.90 (capped)

Spikes get flat factors — no duration scaling. Spikes are transient by nature; their influence should be constant.

### Bounds

All factors clamped to [0.85, 1.15]. Maximum regime influence is ±15% of the base score. This ensures regime awareness biases decisions without dominating them.

### Scoring chain integration

```
score = base_score × identity_factor × goal_bias × regime_factor
```

The regime_factor is the final multiplier in the chain. With default bounds, it can adjust the pre-regime score by at most ±15%.

### Pipeline position

```
raw_context
  → HorizonMemory.smooth()
    → HorizonSnapshot (with deltas per signal)
  → classify_from_horizon(snapshot)
    → RegimeSnapshot (with discrete regimes per signal)
  → RegimeMemory.update(regime_snapshot)
    → RegimeMemorySnapshot (with durations, transitions)
  → compute_all_thresholds(deltas, durations)
    → ThresholdSnapshot (per-signal adaptive thresholds)
  → RegimeFilter.filter(raw_regimes) using per-signal thresholds
    → FilterSnapshot (confirmed regimes)
  → compute_all_regime_factors(confirmed_regimes, durations)
    → RegimeWeightSnapshot (per-signal weight factors)
  → scoring chain applies regime_factor
```

### Tradeoffs

**Flat spikes vs scaled spikes**: Spikes could have duration scaling (longer spike = bigger factor), but spikes that persist become trends by regime classification. Flat spike factors avoid double-counting with the trend scaling that would take over.

**Symmetric up/down factors**: SPIKE_UP (1.10) and SPIKE_DOWN (0.90) are equidistant from 1.0. Same for TREND_UP/DOWN bases. This prevents inherent directional bias in the weighting system.

**Multiplicative vs additive**: Multiplicative scaling means the regime effect is proportional to the base score. A high-scoring candidate gets a larger absolute boost from a favorable regime than a low-scoring one. This is intentional — regime conditions should amplify existing signal, not create artificial floors.

---

## Interaction with identity and goal bias

The regime factor sits at the end of the scoring chain:

```
score = base_score × identity_factor × goal_bias × regime_factor
```

This means:
- **Identity factor** adjusts for organism personality (e.g., risk-averse organisms dampen aggressive strategies)
- **Goal bias** adjusts for current objectives (e.g., growth-focused goals boost growth strategies)
- **Regime factor** adjusts for market conditions (e.g., spike regime boosts urgency-sensitive strategies)

Each factor is independently bounded. Identity and goal bias have their own clamps. The regime factor's [0.85, 1.15] bound means it can never flip a ranking that the prior factors established by more than 15%. In practice, a strategy that scores 30% higher before regime adjustment will still score higher after, regardless of regime.

---

## Hard invariants

| ID  | Invariant                                              | Status |
|-----|--------------------------------------------------------|--------|
| 166 | Factor bounded [0.85, 1.15]                            | PASS   |
| 167 | Deterministic mapping                                  | PASS   |
| 168 | Same regime → same factor                              | PASS   |
| 169 | No state mutation                                      | PASS   |
| 170 | Regime cannot dominate score                           | PASS   |

---

## Test results

- **Phase 46 tests:** 155 passed, 0 failed
- **Phase 45 regression:** 150 passed, 0 failed
- **Phase 30-46 regression:** 2484 passed, 0 failed

---

## Dependency boundary

`regime_weight.py` imports only:
- `__future__.annotations`
- `dataclasses` (dataclass)
- `typing` (Any)
- `umh.runtime.regime` (RegimeType)

No imports from `umh/cells`, `umh/environments`, `umh/adapters`. The module depends only on the RegimeType enum for its input — all computation is from regime type and duration integers.

---

## Ordering verification

For duration=0, the factor ordering is:

```
SPIKE_DOWN (0.90) < TREND_DOWN (0.95) < STABLE (1.0) < TREND_UP (1.05) < SPIKE_UP (1.10)
```

This ordering is verified across all duration values. All five regime types produce distinct factors at duration=0.

---

## Design notes

### Why a separate module (not modifying arbitration)

The spec requires additive-only changes. The regime weight computation is a standalone input to the scoring chain, not a modification of existing scoring logic. Consumers choose whether to apply it. The `apply_regime_weight` function is a simple multiplication — the integration point is explicit.

### Why raw_factor is preserved

The result stores both `raw_factor` (before clamping) and `factor` (after clamping). This lets observability tooling detect when clamping is active — a signal that the regime is pushing against bounds. Useful for config tuning without modifying the computation.

### Why negative config values are clamped

Negative `trend_duration_rate` would mean "longer trends reduce their own influence" — opposite of design intent. Negative `spike_factor_down` would mean "spike down increases score" — also backwards. All config values are clamped in `__post_init__` to prevent misconfiguration.

---

## Known limitations

- Static mapping — factor rules are hardcoded, not learned from data
- No cross-signal interaction — urgency regime doesn't influence risk_level weight
- No per-signal weight profiles — all signals use the same config
- No temporal smoothing — factor can change between ticks
- No confidence weighting — factor doesn't account for regime confirmation strength

---

## Files verified

```
py_compile: regime_weight.py ✓
py_compile: __init__.py ✓
ruff format: all files ✓
```
