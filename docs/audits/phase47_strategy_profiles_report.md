# Phase 47 — Regime-Conditioned Strategy Selection Layer v1

## Audit Report

**Date:** 2026-04-30
**Phase:** 47 of UMH runtime build
**Status:** COMPLETE

---

## What was built

### New file
- `umh/runtime/strategy_profile.py` — StrategyRegimeProfile, StrategyRegimeResult, StrategyRegimeSnapshot, compute_strategy_regime_factor, compute_all_strategy_factors, apply_strategy_regime_factor, get_profile, DEFAULT_PROFILES, NEUTRAL_PROFILE, AGGRESSIVE_PROFILE, CONSERVATIVE_PROFILE, BALANCED_PROFILE, RECOVERY_PROFILE

### Modified files
- `umh/runtime/__init__.py` — 14 new exports

### Test file
- `tests/unit/test_phase47_strategy_profiles.py` — 151 tests across 29 sections

---

## Architecture

### Problem solved

Phase 46 adjusts weights based on regime type, but all strategies receive the same adjustment. A SPIKE_UP regime boosts urgency-sensitive scoring equally for aggressive and conservative strategies. Phase 47 introduces per-strategy regime compatibility so that different strategies become preferred under different regime conditions.

### Strategy profile model

Each strategy declares its regime preferences:

```
StrategyRegimeProfile:
    strategy_name        — identifier
    preferred_regimes    — frozenset of RegimeType (boosted)
    neutral_regimes      — frozenset of RegimeType (factor = 1.0)
    penalized_regimes    — frozenset of RegimeType (suppressed)
    max_bonus            — maximum positive adjustment (default 0.10)
    max_penalty          — maximum negative adjustment (default 0.10)
```

### Default profiles

| Strategy     | Preferred                  | Neutral        | Penalized                  |
|-------------|----------------------------|----------------|----------------------------|
| aggressive   | SPIKE_UP, TREND_UP         | STABLE         | SPIKE_DOWN, TREND_DOWN     |
| conservative | STABLE, TREND_DOWN         | TREND_UP       | SPIKE_UP, SPIKE_DOWN       |
| balanced     | STABLE, TREND_UP           | TREND_DOWN     | (none)                     |
| recovery     | SPIKE_DOWN, TREND_DOWN     | STABLE         | SPIKE_UP, TREND_UP         |

### Compatibility scoring

```
if regime in preferred_regimes:
    factor = 1.0 + bonus    (bonus = max_bonus for SPIKE/STABLE, duration-scaled for TREND)
elif regime in penalized_regimes:
    factor = 1.0 - penalty  (penalty = max_penalty for SPIKE, duration-scaled for TREND)
else:
    factor = 1.0
```

### Duration scaling

For TREND regimes (TREND_UP, TREND_DOWN), the bonus/penalty scales linearly from 0 to max over a duration cap (default 10 ticks):

```
scale = min(1.0, duration / duration_cap)
bonus = max_bonus × scale
penalty = max_penalty × scale
```

At duration=0: factor is 1.0 (no effect yet — trend just started)
At duration=5: factor is halfway to max
At duration=10+: factor is at full max

SPIKE and STABLE regimes get flat (immediate) factors — no duration scaling.

### Bounds

All factors clamped to [0.85, 1.15]. Maximum strategy-regime influence is ±15%.

---

## Integration with scoring chain

```
score = base_score × identity_factor × goal_bias × regime_factor × strategy_regime_factor
```

Phase 46's `regime_factor` adjusts based on the signal's regime (same for all strategies). Phase 47's `strategy_regime_factor` adjusts based on the strategy's compatibility with that regime (different per strategy).

Combined maximum influence: 1.15 × 1.15 = 1.3225 (32.25% boost). Combined minimum: 0.85 × 0.85 = 0.7225 (27.75% reduction). These are theoretical extremes requiring both factors at their limits simultaneously.

### Pipeline position

```
raw_context
  → HorizonMemory.smooth()
  → classify_from_horizon()
  → RegimeMemory.update()
  → compute_all_thresholds()
  → RegimeFilter.filter()
  → compute_all_regime_factors()        [Phase 46]
  → compute_all_strategy_factors()      [Phase 47]
  → scoring chain applies both factors
```

---

## Hard invariants

| ID  | Invariant                                              | Status |
|-----|--------------------------------------------------------|--------|
| 171 | Strategy-regime selection must be deterministic        | PASS   |
| 172 | Regime compatibility must be bounded                   | PASS   |
| 173 | Regime profile must not override base strategy quality | PASS   |
| 174 | No execution state mutation                            | PASS   |
| 175 | Missing regime profile must default neutral            | PASS   |

---

## Test results

- **Phase 47 tests:** 151 passed, 0 failed
- **Phase 46 regression:** 155 passed, 0 failed
- **Phase 30-47 regression:** 2635 passed, 0 failed

---

## Dependency boundary

`strategy_profile.py` imports only:
- `__future__.annotations`
- `dataclasses` (dataclass, field)
- `typing` (Any)
- `umh.runtime.regime` (RegimeType)

No imports from `umh/cells`, `umh/environments`, `umh/adapters`. The module depends only on the RegimeType enum.

---

## Design notes

### Why a standalone module (not modifying evaluator.py)

The evaluator's `OutcomeEvaluator.score()` is used by 13+ phases of tests. Modifying it would change scores and break regression. The strategy profile module provides a factor that the scoring chain composes externally — same multiplicative integration, zero regression risk. Consumers call `compute_strategy_regime_factor()` and multiply into their scoring chain.

### Why TREND regimes are duration-scaled but SPIKE/STABLE are not

TREND regimes represent sustained directional movement. A trend that has persisted for 10 ticks is a stronger signal than a fresh trend — the bonus/penalty should scale with conviction. SPIKE regimes are transient by definition; their signal is the event itself, not its duration. STABLE regimes are the default state; when a strategy prefers STABLE (like conservative), the preference is immediate — stability doesn't "accumulate."

### Why the balanced profile has no penalized regimes

The balanced strategy is designed to work adequately in all conditions. It mildly prefers STABLE and TREND_UP (bonus=0.05) but is never penalized. This makes it a safe default that won't be strongly disadvantaged in any regime.

### Why get_profile returns NEUTRAL_PROFILE for unknowns

Unknown strategy names get a neutral profile (factor=1.0 always). This satisfies invariant 175 and ensures that strategies without declared regime preferences aren't penalized or boosted by regime conditions. It's a graceful degradation — the system works correctly with or without profiles.

### Why conservative and recovery tie in TREND_DOWN

Both conservative and recovery have TREND_DOWN as preferred with the same max_bonus (0.10). Under TREND_DOWN at cap duration, both get factor=1.10. This is correct — both strategies are genuinely well-suited for downtrending conditions, for different reasons (conservative protects, recovery exploits). The winner in practice would be determined by the other scoring factors (identity, goal bias, base quality).

---

## Known limitations

- Static profiles — strategy-regime preferences are hardcoded, not learned
- No learned regime compatibility — profiles don't adapt from outcome data
- No cross-signal regime interaction — profile uses a single regime, not multi-signal state
- No per-user strategy profile learning — all users get the same profiles
- Limited to 4 predefined strategies — custom strategies require code changes

---

## Files verified

```
py_compile: strategy_profile.py ✓
py_compile: __init__.py ✓
ruff format: all files ✓
```
