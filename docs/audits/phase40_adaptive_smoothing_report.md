# Phase 40 — Adaptive Temporal Smoothing Layer v1

## Audit Report

**Date:** 2026-04-30
**Phase:** 40 of UMH runtime build
**Status:** COMPLETE

---

## What was built

### New file
- `umh/runtime/context_profile.py` — SignalProfile, AdaptedAlpha, AdaptationSnapshot, compute_adapted_alpha, compute_all_adapted_alphas, DEFAULT_SIGNAL_PROFILES

### Modified files
- `umh/runtime/context_memory.py` — added adaptive_smooth_context(), ContextMemory.smooth_adaptive(), TYPE_CHECKING imports
- `umh/runtime/__init__.py` — 7 new exports (AdaptationSnapshot, AdaptedAlpha, DEFAULT_SIGNAL_PROFILES, SignalProfile, adaptive_smooth_context, compute_adapted_alpha, compute_all_adapted_alphas)

### Test file
- `tests/unit/test_phase40_adaptive_smoothing.py` — 131 tests across 28 sections

---

## Architecture

### Per-signal adaptive alpha

Phase 39 used a single fixed alpha for all four context signals. Phase 40 replaces this with per-signal adaptive alpha:

```
delta = |current - previous|
adjustment = (delta - 0.25) * adaptation_strength
adapted_alpha = clamp(base_alpha + adjustment, 0.2, 0.8)
```

Where:
- `base_alpha` — derived from the signal's volatility class
- `delta` — recent change magnitude for this specific signal
- `adaptation_strength` — how aggressively alpha responds to delta (default 0.3)
- `0.25` — delta midpoint: below → decrease alpha; above → increase alpha

### Volatility classes

| Class  | Base alpha | Signals                          | Behavior          |
|--------|-----------|----------------------------------|--------------------|
| high   | 0.7       | urgency                          | Fast response      |
| medium | 0.5       | resource_pressure                | Balanced           |
| low    | 0.3       | risk_level, stability_mode       | Heavy smoothing    |

### Signal profiles

```python
DEFAULT_SIGNAL_PROFILES = {
    "urgency":           SignalProfile(name="urgency",           volatility_class="high"),
    "risk_level":        SignalProfile(name="risk_level",        volatility_class="low"),
    "resource_pressure": SignalProfile(name="resource_pressure", volatility_class="medium"),
    "stability_mode":    SignalProfile(name="stability_mode",    volatility_class="low"),
}
```

### Key properties

- **Cross-signal independence**: Each signal's alpha depends only on its own delta
- **Direction tracking**: Step responses track monotonically toward target
- **Oscillation dampening**: Smoothing reduces variance of alternating signals
- **Fast convergence for urgent signals**: urgency converges ~2× faster than risk_level to same step input

### First-tick behavior (preserved from Phase 39)

On the first call to `smooth_adaptive()`, raw context passes through directly. The returned AdaptationSnapshot contains base alphas with zero adjustment — no adaptation occurs because there is no meaningful delta on tick 1.

### Pipeline integration (updated from Phase 39)

```
raw_context (per-tick signal)
  → ContextMemory.smooth_adaptive()
    → (SmoothingResult, AdaptationSnapshot)
    → per-signal adapted alphas
    → smoothed ExecutionContext (frozen)
  → WeightAdapter.adjust()
    → adapted TradeoffProfile
  → TradeoffEngine.resolve()
    → TradeoffResult
```

---

## Adaptation formula walkthrough

Example: urgency jumps from 0.2 to 0.9 (delta = 0.7)

```
base_alpha = 0.7 (high volatility)
adjustment = (0.7 - 0.25) * 0.3 = 0.135
adapted_alpha = clamp(0.7 + 0.135, 0.2, 0.8) = 0.8
```

Result: urgency gets maximum responsiveness when it changes rapidly.

Example: stability_mode holds at 0.1 → 0.12 (delta = 0.02)

```
base_alpha = 0.3 (low volatility)
adjustment = (0.02 - 0.25) * 0.3 = -0.069
adapted_alpha = clamp(0.3 - 0.069, 0.2, 0.8) = 0.231
```

Result: stability_mode gets heavy smoothing when barely changing.

---

## Hard invariants

| ID  | Invariant                                              | Status |
|-----|--------------------------------------------------------|--------|
| 136 | Adapted alpha stays in [0.2, 0.8]                     | PASS   |
| 137 | Per-signal alpha is independent (no cross-contamination)| PASS   |
| 138 | Adaptive smoothing is deterministic                    | PASS   |
| 139 | Phase 39 fixed-alpha smooth() is backward compatible   | PASS   |
| 140 | Neutral context through adaptive smoothing stays neutral| PASS   |

---

## Test results

- **Phase 40 tests:** 131 passed, 0 failed
- **Phase 38-40 regression:** 376 passed, 0 failed
- **Phase 30-40 regression:** 1370 passed, 0 failed

---

## Dependency boundary

`context_profile.py` imports only:
- `__future__.annotations`
- `dataclasses` (dataclass)
- `typing` (Any)

No imports from `umh/runtime`, `umh/cells`, `umh/environments`, `umh/adapters`.

`context_memory.py` adaptive additions import from `context_profile` only inside function bodies (lazy import) or behind TYPE_CHECKING guards.

---

## Design notes

### Why per-signal alpha

Fixed alpha (Phase 39) smooths all signals identically:
- urgency (fast-changing) gets over-smoothed → delayed response to emergencies
- stability_mode (slow-changing) gets under-smoothed → unnecessary oscillation

Per-signal alpha solves both: urgency gets α≈0.7-0.8, stability gets α≈0.2-0.3.

### Why delta-based adaptation

A signal that just changed a lot should be tracked closely (high alpha). A signal that barely moved should be smoothed heavily (low alpha). The delta midpoint (0.25) is the crossover — above it, alpha increases; below, it decreases.

### Why TYPE_CHECKING guards

`context_memory.py` and `context_profile.py` would create a circular import if `context_memory` imported `context_profile` at module level while `context_profile` is a standalone module. The TYPE_CHECKING guard ensures type annotations work without runtime circular imports.

### Why SmoothingResult.alpha = 0.0 for adaptive calls

In adaptive mode, there is no single alpha — each signal has its own. Setting alpha=0.0 in SmoothingResult signals "check the AdaptationSnapshot for per-signal values." This avoids a misleading aggregate.

---

## Known limitations

- No multi-horizon memory (single EMA per signal, no fast+slow blend)
- Not thread-safe — designed for single-threaded tick loops
- No hysteresis — small signals still propagate (just smoothed more)
- No trend detection — adaptation responds to magnitude, not direction
- Adaptation strength is fixed per profile — no runtime adaptation of the adaptation itself
- Delta midpoint (0.25) is hardcoded — not configurable per signal

---

## Files verified

```
py_compile: context_profile.py ✓
py_compile: context_memory.py ✓
py_compile: __init__.py ✓
ruff format: all files ✓
```
