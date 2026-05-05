# Phase 41 — Multi-Horizon Temporal Context Layer v1

## Audit Report

**Date:** 2026-04-30
**Phase:** 41 of UMH runtime build
**Status:** COMPLETE

---

## What was built

### New file
- `umh/runtime/horizon.py` — HorizonValue, HorizonSnapshot, HorizonAlphas, HorizonResult, HorizonMemory, compute_horizon_value, compute_all_horizon_values

### Modified files
- `umh/runtime/context_memory.py` — added ContextMemory.smooth_horizon(), TYPE_CHECKING import for HorizonMemory/HorizonResult/HorizonSnapshot, _horizon_memory state field, reset() now resets horizon memory
- `umh/runtime/__init__.py` — 7 new exports (HorizonAlphas, HorizonMemory, HorizonResult, HorizonSnapshot, HorizonValue, compute_all_horizon_values, compute_horizon_value)

### Test file
- `tests/unit/test_phase41_multi_horizon.py` — 141 tests across 30 sections

---

## Architecture

### Dual-horizon EMA model

Phase 40 provided per-signal adaptive alpha with a single EMA per signal. Phase 41 adds a second EMA per signal — one fast, one slow — enabling temporal decomposition:

```
fast_value = α_fast * current + (1 - α_fast) * prev_fast
slow_value = α_slow * current + (1 - α_slow) * prev_slow
delta = fast - slow
```

Constraints:
- α_fast > α_slow always (enforced: if α_fast ≤ α_slow, α_fast = min(α_slow + 0.1, 0.8))
- All alpha values clamped to [0.2, 0.8]
- All output values clamped to [0, 1]
- Delta clamped to [-1, 1]

### Default alpha configuration

| Signal             | Fast α | Slow α | Rationale                           |
|--------------------|--------|--------|-------------------------------------|
| urgency            | 0.7    | 0.3    | Highest spread — urgency is volatile |
| risk_level         | 0.5    | 0.2    | Risk changes slowly                 |
| resource_pressure  | 0.6    | 0.25   | Moderate volatility                  |
| stability_mode     | 0.5    | 0.2    | Very slow signal                     |

### Delta interpretation

```
delta > 0 → spike: signal rising faster than its trend
delta < 0 → drop: signal falling faster than its trend
delta ≈ 0 → stable: signal tracking its trend
```

The delta naturally decays:
- If the spike is sustained, the slow EMA catches up → delta → 0
- If the spike reverts, both EMAs pull back → delta returns to 0

### Temporal decomposition

```
Signal = Trend (slow EMA) + Deviation (delta)
```

This separation enables downstream consumers to:
- React to spikes without changing long-term strategy
- Detect regime changes (sustained delta shift)
- Distinguish noise from trend

### First-tick behavior (preserved from Phase 39-40)

On the first call to `HorizonMemory.smooth()`, raw context passes through to both fast and slow horizons. Delta is 0 for all signals. This prevents false neutral-pull artifacts.

### Pipeline integration (updated from Phase 40)

```
raw_context (per-tick signal)
  ├── ContextMemory.smooth()            # Phase 39: fixed alpha EMA
  ├── ContextMemory.smooth_adaptive()   # Phase 40: per-signal adaptive alpha
  └── ContextMemory.smooth_horizon()    # Phase 41: dual EMA fast+slow
       → (SmoothingResult, HorizonSnapshot)
       → SmoothingResult.smoothed = fast context
       → HorizonSnapshot.get_delta() for spike detection
  → WeightAdapter.adjust()
    → adapted TradeoffProfile
  → TradeoffEngine.resolve()
    → TradeoffResult
```

All three smoothing modes coexist in ContextMemory and share the same tick counter.

---

## Data model

### HorizonValue (frozen dataclass)
Per-signal dual EMA output: signal_name, fast, slow, delta.

### HorizonSnapshot (frozen dataclass)
Complete multi-horizon state for all signals at one tick. Accessors: get(), get_delta(), get_fast(), get_slow().

### HorizonAlphas (frozen dataclass)
Per-signal fast/slow alpha pair configuration.

### HorizonResult (frozen dataclass)
Full output of a smoothing operation: snapshot, fast_context, slow_context, raw, tick, was_reset.

### HorizonMemory (stateful class)
Dual-horizon temporal context with fast and slow EMA. Operations: smooth(), reset(), override(), set_alphas(), to_dict().

---

## Hard invariants

| ID  | Invariant                                              | Status |
|-----|--------------------------------------------------------|--------|
| 141 | Fast and slow EMA independent                          | PASS   |
| 142 | No cross-signal contamination                          | PASS   |
| 143 | Deterministic dual smoothing                           | PASS   |
| 144 | Neutral input produces neutral output                  | PASS   |
| 145 | No amplification beyond bounds                         | PASS   |

---

## Test results

- **Phase 41 tests:** 141 passed, 0 failed
- **Phase 38-41 regression:** 376+141 = 517 passed, 0 failed
- **Phase 30-41 regression:** 1777 passed, 0 failed

---

## Dependency boundary

`horizon.py` imports only:
- `__future__.annotations`
- `dataclasses` (dataclass)
- `typing` (TYPE_CHECKING, Any)
- `umh.runtime.context` (NEUTRAL_CONTEXT, ExecutionContext)
- `umh.runtime.context_profile` (SignalProfile) — TYPE_CHECKING only

No imports from `umh/cells`, `umh/environments`, `umh/adapters`.

`context_memory.py` imports `HorizonMemory` via lazy import inside `smooth_horizon()` and TYPE_CHECKING guard.

---

## Design notes

### Why dual EMA instead of a window-based approach

Window-based methods (e.g., moving average over N ticks) require storing N values per signal. Dual EMA achieves temporal decomposition with O(1) memory per signal — just two previous values. The fast EMA approximates a short window, the slow EMA approximates a long window, and their difference approximates the derivative.

### Why fast context is used as smoothed output

The fast EMA is more responsive and better represents the current state of the system. The slow EMA and delta are available in the HorizonSnapshot for downstream consumers that need trend information. Using fast as the "smoothed" output maintains backward compatibility with existing pipeline consumers that expect a single smoothed context.

### Why α_fast > α_slow is enforced

If α_fast ≤ α_slow, the "fast" EMA would actually be slower than the "slow" one, making the delta meaningless. The enforcement (α_fast = min(α_slow + 0.1, 0.8)) guarantees the temporal hierarchy is always maintained.

### Why three smoothing modes coexist

ContextMemory now offers smooth() (Phase 39), smooth_adaptive() (Phase 40), and smooth_horizon() (Phase 41). Each serves a different use case:
- smooth(): simple, fixed alpha — good for stable environments
- smooth_adaptive(): per-signal alpha based on volatility — good for mixed-signal environments
- smooth_horizon(): dual EMA with spike/trend detection — good for environments requiring temporal decomposition

Callers choose the mode appropriate to their needs.

---

## Known limitations

- No regime classification yet — delta is raw, not classified into spike/drop/stable
- No multi-level hierarchy (only two horizons: fast and slow)
- No learning — alphas are configured, not adapted based on historical accuracy
- Not thread-safe — designed for single-threaded tick loops
- HorizonMemory is lazily initialized inside ContextMemory — first smooth_horizon() call allocates it

---

## Files verified

```
py_compile: horizon.py ✓
py_compile: context_memory.py ✓
py_compile: __init__.py ✓
ruff format: all files ✓
```
