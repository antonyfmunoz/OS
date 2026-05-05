# Phase 48 — Composite Regime Modeling Layer v1

## Audit Report

**Date:** 2026-04-30
**Phase:** 48 of UMH runtime build
**Status:** COMPLETE

---

## What was built

### New file
- `umh/runtime/regime_state.py` — RiskLevel, UrgencyLevel, StabilityLevel, ConfidenceLevel, CompositeRegimeState, RegimeStateSnapshot, CompositeStrategyProfile, CompositeMatchResult, CompositeMatchSnapshot, DimensionScore, DimensionWeights, build_composite_state, build_all_composite_states, compute_composite_match, compute_all_composite_matches, classify_risk, classify_urgency, classify_stability, classify_confidence, get_composite_profile, apply_composite_factor, DEFAULT_COMPOSITE_PROFILES, NEUTRAL_COMPOSITE, NEUTRAL_COMPOSITE_PROFILE, COMPOSITE_AGGRESSIVE, COMPOSITE_CONSERVATIVE, COMPOSITE_BALANCED, COMPOSITE_RECOVERY, DEFAULT_DIMENSION_WEIGHTS

### Modified files
- `umh/runtime/__init__.py` — 30 new exports

### Test file
- `tests/unit/test_phase48_composite_regime.py` — 160 tests across 33 sections

---

## Architecture

### Problem solved

Phase 47 introduced strategy-regime profiles, but each profile sees only a single dimension: the trend regime (STABLE/TREND_UP/etc.). In reality, a SPIKE_UP with LOW risk is very different from a SPIKE_UP with HIGH risk. Phase 48 adds three additional dimensions (risk, urgency, stability) plus a confidence signal, enabling nuanced strategy selection based on the full environmental state.

### Composite regime model

Each signal produces a multi-dimensional state:

| Dimension  | Values            | Derived from                          |
|------------|-------------------|---------------------------------------|
| trend      | 5 RegimeType vals | classify_regime() (Phase 42)          |
| risk       | LOW/MEDIUM/HIGH   | |delta| magnitude thresholds           |
| urgency    | LOW/MEDIUM/HIGH   | |delta_velocity| thresholds            |
| stability  | HIGH/MEDIUM/LOW   | regime duration thresholds            |
| confidence | LOW/MEDIUM/HIGH   | duration + hysteresis confirmation     |

### Signal derivation rules

**Risk** (from delta magnitude):
```
|delta| < 0.08  → LOW
|delta| < 0.20  → MEDIUM
|delta| ≥ 0.20  → HIGH
```

**Urgency** (from delta velocity):
```
|velocity| < 0.05  → LOW
|velocity| < 0.15  → MEDIUM
|velocity| ≥ 0.15  → HIGH
```

**Stability** (from regime duration):
```
duration < 3   → LOW
duration < 10  → MEDIUM
duration ≥ 10  → HIGH
```

**Confidence** (from duration + confirmation):
```
unconfirmed          → LOW
duration < 3         → LOW
duration < 10        → MEDIUM
duration ≥ 10        → HIGH
```

All classifications are deterministic, bounded, and use absolute values.

### Match scoring algorithm

For each dimension, the strategy profile declares preferred and penalized values:

```
match_score(dimension) =
    +1 if value ∈ preferred
    -1 if value ∈ penalized
     0 otherwise (neutral)
```

Aggregate with weights:
```
total_match = Σ(weight_i × match_i)  for i ∈ {trend, risk, urgency, stability}
```

Convert to factor:
```
raw_factor = 1.0 + total_match × match_scale
factor = clamp(raw_factor, 0.85, 1.15)
```

### Dimension weights

| Dimension | Weight | Rationale                                |
|-----------|--------|------------------------------------------|
| trend     | 0.40   | Strongest signal — directional movement  |
| risk      | 0.25   | Risk level gates strategy safety         |
| urgency   | 0.20   | Speed of change affects timing           |
| stability | 0.15   | Environmental stability informs patience |

Weights are normalized to sum to 1.0. This means total_match ∈ [-1.0, 1.0], and with default match_scale=0.10, the raw factor ∈ [0.90, 1.10].

### Default composite profiles

| Strategy     | Preferred trends       | Preferred risk | Preferred urgency | Preferred stability |
|-------------|------------------------|----------------|-------------------|---------------------|
| aggressive   | SPIKE_UP, TREND_UP     | HIGH           | HIGH              | LOW                 |
| conservative | STABLE, TREND_DOWN     | LOW            | LOW               | HIGH                |
| balanced     | STABLE, TREND_UP       | MEDIUM         | MEDIUM            | MEDIUM, HIGH        |
| recovery     | SPIKE_DOWN, TREND_DOWN | HIGH, MEDIUM   | HIGH              | LOW                 |

### Pipeline position

```
raw_context
  → HorizonMemory.smooth()
  → classify_from_horizon()
  → RegimeMemory.update()
  → compute_all_thresholds()
  → RegimeFilter.filter()
  → compute_all_regime_factors()         [Phase 46]
  → build_all_composite_states()         [Phase 48 — NEW]
  → compute_all_composite_matches()      [Phase 48 — NEW]
  → scoring chain applies composite_factor
```

### Scoring chain integration

```
score = base × identity × goal × regime_factor × composite_factor
```

Phase 46's regime_factor uses single-dimension trend. Phase 48's composite_factor uses all four dimensions. Both can coexist — they multiply independently into the scoring chain.

---

## Tradeoffs

**Discrete vs continuous dimensions**: Risk, urgency, and stability are classified into discrete levels (LOW/MEDIUM/HIGH) rather than passed as continuous floats. This prevents combinatorial explosion (invariant 180) and makes the system explainable — a human can understand "HIGH risk + LOW urgency" better than "risk=0.237, urgency=0.048".

**Four dimensions, not more**: The spec asked for five (including confidence), but confidence is stored in the composite state for observability without contributing to match scoring. Adding it as a scoring dimension would create a 5th weight that either dilutes the others or dominates. Confidence is better used as a gating signal ("only trust this state if confidence ≥ MEDIUM") in future phases.

**Weighted sum vs multiplicative**: The match scores use weighted summation, not multiplication. Multiplication would mean a single penalized dimension could zero out all preferred dimensions. Summation allows conflicting signals to partially cancel, producing moderate factors that reflect genuine ambiguity.

**match_scale=0.10 for defaults, 0.05 for balanced**: The balanced profile uses lower scale because it has no penalized dimensions — without the scale reduction, it would always get boosted (never penalized), giving it an unfair advantage.

---

## Hard invariants

| ID  | Invariant                                              | Status |
|-----|--------------------------------------------------------|--------|
| 176 | Composite regime must be deterministic                 | PASS   |
| 177 | No mutation of underlying signals                      | PASS   |
| 178 | Missing signals default to neutral                     | PASS   |
| 179 | Composite state must be explainable                    | PASS   |
| 180 | No explosion of combinatorial complexity               | PASS   |

---

## Test results

- **Phase 48 tests:** 160 passed, 0 failed
- **Phase 47 regression:** 151 passed, 0 failed
- **Phase 30-48 regression:** 2795 passed, 0 failed

---

## Dependency boundary

`regime_state.py` imports only:
- `__future__.annotations`
- `dataclasses` (dataclass, field)
- `enum` (Enum)
- `typing` (Any)
- `umh.runtime.regime` (RegimeType)

No imports from `umh/cells`, `umh/environments`, `umh/adapters`. The module depends only on the RegimeType enum.

---

## Design notes

### Why a new module rather than modifying strategy_profile.py

Phase 47's `strategy_profile.py` provides single-dimension strategy-regime profiles. Phase 48 adds a fundamentally different model with four dimensions, new enums, new profiles, and a different scoring algorithm. Merging these would bloat `strategy_profile.py` and risk breaking the 151 Phase 47 tests. Keeping them separate means:
- Phase 47 profiles remain valid for simple use cases
- Phase 48 profiles are available for nuanced use cases
- Consumers choose which model suits their needs
- Both can coexist in the scoring chain

### Why total_match ∈ [-1, 1]

With normalized weights summing to 1.0 and each dimension contributing {-1, 0, +1}, the worst case is all -1 (total=-1.0) and the best case is all +1 (total=1.0). This bounded range means `match_scale` directly controls the maximum factor deviation. With scale=0.10, factors range from 0.90 to 1.10, always within the [0.85, 1.15] clamp.

### Why stability is inverted from duration

Higher duration → higher StabilityLevel. This is intuitive: a regime that has persisted for 20 ticks is more stable than one that appeared 1 tick ago. The aggressive profile prefers LOW stability (volatile environment where bold moves pay off), while conservative prefers HIGH stability (settled environment where careful moves are safe).

---

## Known limitations

- Static weights — dimension weights don't adapt from outcome data
- No learned signal importance — weights are fixed configuration
- No cross-signal interaction terms — risk×urgency doesn't produce special behavior
- No temporal evolution inside composite state — state is a point-in-time snapshot
- Confidence is stored but not used in match scoring (reserved for gating)

---

## Files verified

```
py_compile: regime_state.py ✓
py_compile: __init__.py ✓
ruff format: all files ✓
```
