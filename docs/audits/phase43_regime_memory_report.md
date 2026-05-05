# Phase 43 — Regime Memory + Transition Tracking Layer v1

## Audit Report

**Date:** 2026-04-30
**Phase:** 43 of UMH runtime build
**Status:** COMPLETE

---

## What was built

### New file
- `umh/runtime/regime_memory.py` — RegimeState, RegimeTransition, RegimeMemorySnapshot, update_regime_state, RegimeMemory

### Modified files
- `umh/runtime/__init__.py` — 5 new exports

### Test file
- `tests/unit/test_phase43_regime_memory.py` — 131 tests across 26 sections

---

## Architecture

### Problem solved

Phase 42 classified continuous deltas into discrete regime labels (STABLE, TREND_UP, TREND_DOWN, SPIKE_UP, SPIKE_DOWN). But classification is stateless — it doesn't know how long a signal has been in a regime, how many transitions have occurred, or what the previous regime was. Downstream consumers need temporal persistence to distinguish a fresh spike from a sustained one.

Phase 43 adds stateful tracking on top of the stateless classifier.

### Update rules

```
IF new_regime == current_regime:
    duration += 1
ELSE:
    previous_regime = current_regime
    current_regime = new_regime
    duration = 1
    transition_count += 1
    last_transition_tick = tick
```

### Data model

```
RegimeState (mutable dataclass):
    signal_name, current_regime, previous_regime,
    duration, transition_count, last_transition_tick

RegimeTransition (frozen dataclass):
    signal_name, from_regime, to_regime, tick, previous_duration

RegimeMemorySnapshot (frozen dataclass):
    states: dict[str, RegimeState]
    transitions: list[RegimeTransition]
    tick: int
    Methods: get_state(), get_duration(), get_regime(),
             had_transition(), transition_count(), all_stable()

RegimeMemory (class):
    Properties: tick, states, history
    Methods: update(), update_single(), get_state(), get_duration(),
             get_regime(), get_transition_count(), total_transitions(),
             recent_transitions(), reset(), snapshot(), to_dict()

update_regime_state() (pure function):
    Mutates RegimeState, returns RegimeTransition | None
```

### Pipeline integration

```
raw_context
  → HorizonMemory.smooth()
    → HorizonSnapshot (with deltas per signal)
  → classify_from_horizon(snapshot)
    → RegimeSnapshot (with discrete regimes per signal)
  → RegimeMemory.update(regime_snapshot)
    → RegimeMemorySnapshot (with durations, transitions, history)
  → downstream consumers check:
    - snap.get_duration("urgency") → how long in current regime
    - snap.had_transition("urgency") → did it just change
    - snap.all_stable() → safe to proceed
    - mem.recent_transitions(5) → last 5 transitions
```

### Stateful design

RegimeMemory is the only stateful component in the regime pipeline. The classifier (Phase 42) remains pure and stateless. This separation means:
- Classification can be tested independently
- Memory can be reset without affecting classification logic
- Different memory instances can track the same signals independently

### Dynamic signal registration

RegimeMemory auto-registers unknown signals when they appear in a RegimeSnapshot. Signals present in the memory but absent from a snapshot have their duration incremented (they persist in their current regime).

---

## Hard invariants

| ID  | Invariant                                              | Status |
|-----|--------------------------------------------------------|--------|
| 151 | Same regime on consecutive ticks increments duration   | PASS   |
| 152 | Regime change resets duration to 1                     | PASS   |
| 153 | Transition records correct from/to regime              | PASS   |
| 154 | Per-signal transition count is monotonically non-decreasing | PASS   |
| 155 | Signals are mutually independent                       | PASS   |

---

## Test results

- **Phase 43 tests:** 131 passed, 0 failed
- **Phase 42 regression:** 131 passed, 0 failed
- **Phase 30-43 regression:** 2039 passed, 0 failed

---

## Dependency boundary

`regime_memory.py` imports only:
- `__future__.annotations`
- `dataclasses` (dataclass, field)
- `typing` (Any)
- `umh.runtime.regime` (RegimeSnapshot, RegimeType)

No imports from `umh/cells`, `umh/environments`, `umh/adapters`.

---

## Design notes

### Why RegimeState is mutable

Unlike the frozen dataclasses used in Phases 41-42, RegimeState is mutable because it tracks per-tick accumulation (duration, transition_count). Making it frozen would require creating a new instance every tick — wasteful when the purpose is incremental mutation.

### Why update_regime_state is a standalone function

Extracting the single-signal update logic as a pure function (it mutates state but has no other side effects) allows testing the core logic independently from RegimeMemory's multi-signal orchestration.

### Why RegimeMemorySnapshot copies state dict

`RegimeMemory.update()` returns `dict(self._states)` — a shallow copy. This prevents external code from mutating the memory's internal state through the snapshot. The snapshot is frozen, but its `states` dict values are mutable `RegimeState` objects (shared references). This is a known tradeoff: full deep-copy would be more defensive but adds overhead per tick.

### Why absent signals get duration incremented

When a signal exists in RegimeMemory but is absent from a RegimeSnapshot, its duration is incremented. This models "no news is good news" — if a signal isn't reported, it persists in its current regime. This prevents duration resets from incomplete snapshots.

---

## Downstream usage potential

| Consumer               | Uses                                    |
|------------------------|-----------------------------------------|
| Hysteresis layer       | duration > N → confirmed regime         |
| Alert throttling       | transition_count → rate limiting        |
| Strategy adaptation    | duration-weighted regime response        |
| Observability          | to_dict() → structured log per tick     |
| Decision gating        | all_stable() + duration > threshold     |

---

## Known limitations

- No hysteresis — duration is tracked but not used for confirmation gating
- Shallow copy in snapshots — RegimeState objects are shared references
- No maximum history size — history grows unbounded
- No persistence — state is in-memory only
- No time-based windowing — only tick-based duration

---

## Files verified

```
py_compile: regime_memory.py ✓
py_compile: __init__.py ✓
ruff format: all files ✓
```
