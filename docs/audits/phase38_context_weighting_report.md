# Phase 38 — Context-Aware Tradeoff Weighting Layer v1

## Audit Report

**Date:** 2026-04-30
**Phase:** 38 of UMH runtime build
**Status:** COMPLETE

---

## What was built

### New files
- `umh/runtime/context.py` — ExecutionContext frozen dataclass, NEUTRAL_CONTEXT constant
- `umh/runtime/weighting.py` — WeightAdapter, WeightAdjustment, WeightAdaptationResult, apply_context_weights

### Modified files
- `umh/runtime/tradeoff.py` — added `context` and `adapter` parameters to `TradeoffEngine.resolve()` and `TradeoffScorer.compute_factor()`
- `umh/runtime/__init__.py` — 6 new exports (ExecutionContext, NEUTRAL_CONTEXT, WeightAdapter, WeightAdaptationResult, WeightAdjustment, apply_context_weights)

### Test file
- `tests/unit/test_phase38_context_weighting.py` — 123 tests across 29 sections

---

## Architecture

### ExecutionContext model
```
ExecutionContext(frozen dataclass):
  urgency: float [0,1] — time criticality
  risk_level: float [0,1] — failure consequence
  resource_pressure: float [0,1] — resource scarcity
  stability_mode: float [0,1] — preference for conservative choices

All values clamped to [0,1] via __post_init__
is_neutral: True iff all values equal defaults (0.5, 0.5, 0.5, 0.0)
```

### Weight adaptation rules
```
urgency signal → boosts latency/speed/time/fast/quick/urgent dimensions
risk signal → boosts success/stability/safety/reliable/quality/risk dimensions
pressure signal → boosts efficiency/cost/resource/effort/budget/cheap dimensions
stability mode → dampens all deviations toward 1.0
```

### Multiplier formula
```
For each matching dimension:
  delta = context_signal - 0.5
  if |delta| > 0.05:
    multiplier += delta × strength_factor

Strength factors:
  urgency: 0.6, risk: 0.6, pressure: 0.4

Stability dampening:
  deviation = multiplier - 1.0
  dampened = deviation × (1.0 - stability_mode × 0.5)
  multiplier = 1.0 + dampened

Final clamping: [0.5, 2.0]
```

### Deadzone
```
|context_signal - 0.5| <= 0.05 → no adjustment (avoids noise)
```

### Integration into TradeoffEngine
```
TradeoffEngine.resolve(candidates, profile, context, adapter)
  if context provided:
    apply_context_weights(profile, context, adapter) → adapted_profile
    use adapted_profile for all downstream operations
  else:
    use original profile (backward compatible)
```

### Scoring chain (still 5 multipliers)
```
total = base × identity[0.80,1.20] × goal_bias[0.85,1.15] × hierarchy[0.90,1.10] × tradeoff[0.85,1.15]
```

Context-aware weighting changes the tradeoff factor by adjusting which dimensions receive more weight, which shifts the weighted score, which shifts the factor. The chain structure is unchanged.

---

## Data flow
```
ExecutionContext (urgency, risk, pressure, stability)
  → WeightAdapter.adjust(profile, context)
    → for each dimension:
        keyword match → compute multiplier
        stability dampening
        clamp [0.5, 2.0]
    → WeightAdaptationResult
  → apply_context_weights()
    → new TradeoffProfile with adjusted weights
  → TradeoffEngine.resolve()
    → normalize → Pareto → weighted score → tolerance → sort
  → TradeoffResult
```

### Neutral context behavior
With neutral context (all defaults), no weights change, profile passes through unmodified, engine produces identical results to no-context calls.

---

## Hard invariants

| ID | Invariant | Status |
|----|-----------|--------|
| 126 | Weight adaptation must be pure (no state mutation) | PASS |
| 127 | No stochastic weight adaptation | PASS |
| 128 | Weight multipliers bounded to [0.5, 2.0] | PASS |
| 129 | Every weight adjustment must be explainable | PASS |
| 130 | No I/O or subprocess in weighting or context modules | PASS |

---

## Test results

- **Phase 38 tests:** 123 passed, 0 failed
- **Phase 37 regression:** 132 passed, 0 failed
- **Phase 30-38 regression:** 896 passed, 0 failed
- **Total tests collected:** 5145
- **Test growth:** +123 (from 5022 to 5145)

---

## Dependency boundary

`context.py` imports only:
- `__future__.annotations`
- `dataclasses` (dataclass)
- `typing` (Any)

`weighting.py` imports only:
- `__future__.annotations`
- `dataclasses` (dataclass)
- `typing` (TYPE_CHECKING, Any)
- TYPE_CHECKING only: `umh.runtime.context`, `umh.runtime.tradeoff`

No imports from `umh/cells`, `umh/environments`, `umh/adapters`.

---

## Known limitations

- Static keyword sets — no learning which keywords matter
- No temporal context decay (context is per-call snapshot)
- Single-candidate scoring still produces neutral factor (by design)
- Keyword matching is substring-based — "cost" matches "cost_efficiency" but also "costly_mistake"

---

## Files verified

```
py_compile: context.py ✓
py_compile: weighting.py ✓
py_compile: tradeoff.py ✓
py_compile: __init__.py ✓
ruff format: all files ✓
```
