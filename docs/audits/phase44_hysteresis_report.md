# Phase 44 — Regime Hysteresis + Confirmation Layer v1

## Audit Report

**Date:** 2026-04-30
**Phase:** 44 of UMH runtime build
**Status:** COMPLETE

---

## What was built

### New file
- `umh/runtime/regime_filter.py` — FilterState, FilterResult, FilterSnapshot, filter_regime, RegimeFilter

### Modified files
- `umh/runtime/__init__.py` — 5 new exports

### Test file
- `tests/unit/test_phase44_hysteresis.py` — 140 tests across 28 sections

---

## Architecture

### Problem solved

Phase 42-43 classify regimes and track duration, but classification is still reactive — a single noisy tick can flip the regime. Downstream consumers that react to regime changes (strategy adjustment, alerting, weight adaptation) get whiplash from noise-driven oscillation.

Phase 44 adds a hysteresis filter that requires a new regime to persist for `confirm_threshold` consecutive ticks before accepting the transition. This prevents noise from triggering false regime changes.

### Confirmation logic

```
IF raw_regime == confirmed_regime:
    clear pending, return confirmed_regime

ELIF pending_regime != raw_regime:
    pending_regime = raw_regime
    pending_duration = 1
    IF pending_duration >= confirm_threshold:
        ACCEPT: return raw_regime (confirmed)
    ELSE:
        return confirmed_regime (suppressed)

ELSE (pending_regime == raw_regime):
    pending_duration += 1
    IF pending_duration >= confirm_threshold:
        ACCEPT: confirmed_regime = raw_regime, clear pending
        return raw_regime
    ELSE:
        return confirmed_regime

Default confirm_threshold: 3 ticks
Minimum confirm_threshold: 1 (clamped)
```

### Noise resistance explanation

The filter resists noise through three mechanisms:

1. **Duration gating**: A new regime must persist for N consecutive ticks. A single spike is suppressed.
2. **Pending reset on interruption**: If a different regime appears during the pending window, the counter resets to 1. This means alternating noise (SPIKE, STABLE, SPIKE, STABLE...) never accumulates toward confirmation.
3. **Pending reset on different pending**: If the pending regime changes (SPIKE_UP → TREND_DOWN), the counter restarts for the new regime. This means cycling through multiple regimes never confirms any of them.

### Duration gating rationale

The default threshold of 3 ticks means:
- Tick 1: new regime appears → suppressed, pending starts
- Tick 2: same regime again → still suppressed, pending_duration=2
- Tick 3: same regime again → CONFIRMED, transition accepted

This provides a 2-tick buffer against transient noise while keeping response latency low enough to catch sustained regime shifts.

### Data model

```
FilterState (mutable dataclass):
    signal_name, confirmed_regime, pending_regime, pending_duration

FilterResult (frozen dataclass):
    signal_name, raw_regime, filtered_regime, was_confirmed,
    pending_regime, pending_duration
    Properties: was_suppressed

FilterSnapshot (frozen dataclass):
    results: dict[str, FilterResult]
    tick: int
    Methods: get(), get_filtered_regime(), any_confirmed(),
             any_suppressed(), all_stable(), confirmed_signals(),
             suppressed_signals()

RegimeFilter (class):
    Properties: tick, confirm_threshold, states
    Methods: filter(), filter_single(), get_confirmed_regime(),
             get_pending(), reset(), to_dict()

filter_regime() (standalone function):
    Mutates FilterState, returns FilterResult
```

### Pipeline integration

```
raw_context
  → HorizonMemory.smooth()
    → HorizonSnapshot (with deltas per signal)
  → classify_from_horizon(snapshot)
    → RegimeSnapshot (with discrete regimes per signal)
  → RegimeMemory.update(regime_snapshot)
    → RegimeMemorySnapshot (with durations, transitions)
  → RegimeFilter.filter(raw_regimes)
    → FilterSnapshot (with confirmed/suppressed regimes)
  → downstream consumers use filtered_regime (stable output)
```

---

## Hard invariants

| ID  | Invariant                                              | Status |
|-----|--------------------------------------------------------|--------|
| 156 | No instant regime switching                            | PASS   |
| 157 | Confirmed transitions only                             | PASS   |
| 158 | Noise does not trigger flips                           | PASS   |
| 159 | Deterministic filtering                                | PASS   |
| 160 | No cross-signal contamination                          | PASS   |

---

## Test results

- **Phase 44 tests:** 140 passed, 0 failed
- **Phase 43 regression:** 131 passed, 0 failed
- **Phase 30-44 regression:** 2179 passed, 0 failed

---

## Dependency boundary

`regime_filter.py` imports only:
- `__future__.annotations`
- `dataclasses` (dataclass)
- `typing` (Any)
- `umh.runtime.regime` (RegimeType)

No imports from `umh/cells`, `umh/environments`, `umh/adapters`.

---

## Design notes

### Why a separate filter module instead of modifying RegimeMemory

RegimeMemory (Phase 43) tracks raw regime state — duration, transitions, history. The filter (Phase 44) is a separate concern: it decides whether a regime change should be accepted. Keeping them separate means:
- Raw regime data is always available (unfiltered)
- The filter threshold is independently configurable
- The filter can be bypassed when raw data is needed

### Why confirm_threshold minimum is 1, not 0

A threshold of 0 would mean "accept everything immediately" — equivalent to no filter. This is redundant with not using the filter at all. A threshold of 1 means "accept on first sight" — minimal filtering that still goes through the confirmation path. Negative values are clamped to 1.

### Why FilterResult includes both raw_regime and filtered_regime

Downstream consumers may want to know what the classifier detected (raw) even if the filter suppressed it. This is useful for:
- Observability: logging suppressed spikes
- Alerting: "we saw a spike but haven't confirmed it yet"
- Debugging: understanding why the filter output differs from raw

### Why filter_single does not increment tick

`filter()` operates on a full signal set per tick and increments the tick counter. `filter_single()` operates on one signal independently — it's a utility for targeted updates without advancing the global tick. This mirrors the pattern from RegimeMemory.update() vs update_single().

---

## Downstream usage potential

| Consumer               | Uses                                    |
|------------------------|-----------------------------------------|
| Strategy adjustment    | filtered regime → stable strategy input |
| Alert throttling       | any_suppressed() → noise indicator      |
| Weight adaptation      | confirmed regime → stable multipliers   |
| Observability          | raw vs filtered → suppression dashboard |
| Decision gating        | all_stable() + no pending → safe zone   |

---

## Known limitations

- Fixed threshold — no per-signal or adaptive thresholds
- No adaptive hysteresis — threshold doesn't adjust based on signal volatility
- No confidence weighting — all ticks count equally toward confirmation
- No grace period — once confirmed, a new regime starts pending immediately
- No maximum pending duration — pending can accumulate indefinitely

---

## Files verified

```
py_compile: regime_filter.py ✓
py_compile: __init__.py ✓
ruff format: all files ✓
```
