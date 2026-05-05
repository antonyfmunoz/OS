# Phase 49 — Composite State Dynamics Layer v1

## Audit Report

**Date:** 2026-04-30
**Phase:** 49 of UMH runtime build
**Status:** COMPLETE

---

## What was built

### New file
- `umh/runtime/regime_dynamics.py` — DimensionDirection, CompositeDimensionDelta, CompositeStateDynamics, CompositeStateMemory, compute_trend_direction, compute_risk_direction, compute_urgency_direction, compute_stability_direction, compute_confidence_direction, compute_dimension_deltas

### Modified files
- `umh/runtime/__init__.py` — 10 new exports

### Test file
- `tests/unit/test_phase49_regime_dynamics.py` — 161 tests across 36 sections

---

## Architecture

### Problem solved

Phase 48 introduced multi-dimensional composite regime states (trend + risk + urgency + stability + confidence), but each state is a point-in-time snapshot. There is no way to ask "is risk increasing or decreasing?" or "how many times has the composite state changed?" Phase 49 adds temporal evolution tracking — observational dynamics that describe how composite states change over time without influencing strategy selection or execution.

### Temporal dynamics model

Each call to `CompositeStateMemory.update()` produces a `CompositeStateDynamics` snapshot describing:

| Property | Type | Description |
|----------|------|-------------|
| dimension_deltas | tuple[CompositeDimensionDelta, ...] | Per-dimension direction between previous and current |
| transition_count | int | Cumulative number of state changes |
| persistence_duration | int | Ticks the current state has held |
| is_first_update | bool | True on the very first update |

### Direction computation

**Ordered dimensions** (risk, urgency, stability, confidence) use a numeric ordering:

```
LOW=0, MEDIUM=1, HIGH=2
prev_ord < curr_ord → INCREASING
prev_ord > curr_ord → DECREASING
prev_ord == curr_ord → FLAT
```

**Trend dimension** uses semantic ordering:

```
SPIKE_DOWN=-2, TREND_DOWN=-1, STABLE=0, TREND_UP=1, SPIKE_UP=2
Higher semantic value → INCREASING
Lower semantic value → DECREASING
Same value → FLAT
Unknown/missing mapping → CHANGED
```

### DimensionDirection enum

| Value | Meaning |
|-------|---------|
| INCREASING | Dimension moved to a higher level |
| DECREASING | Dimension moved to a lower level |
| FLAT | Dimension unchanged |
| CHANGED | Dimension changed but has no ordered direction |
| UNKNOWN | Direction cannot be determined |

### Memory model

`CompositeStateMemory` maintains:
- `_previous`: last state before current
- `_current`: most recent state
- `_transition_count`: cumulative state changes
- `_persistence_duration`: consecutive ticks at current state
- `_tick`: total updates received

**First update:** previous = current = state, persistence = 1, transitions = 0.
**Same state:** persistence += 1.
**Changed state:** transition_count += 1, persistence = 1.

### Pipeline position

```
raw_context
  → HorizonMemory.smooth()
  → classify_from_horizon()
  → RegimeMemory.update()
  → compute_all_thresholds()
  → RegimeFilter.filter()
  → compute_all_regime_factors()         [Phase 46]
  → build_all_composite_states()         [Phase 48]
  → CompositeStateMemory.update()        [Phase 49 — NEW]
  → compute_all_composite_matches()      [Phase 48]
  → scoring chain applies composite_factor
```

Phase 49 sits between composite state construction and composite matching. Dynamics are observational — they describe what happened but do not modify the scoring chain.

---

## Tradeoffs

**Observational-only design**: Dynamics do not influence strategy scoring. This is deliberate — temporal evolution is useful for logging, diagnostics, and future gating logic, but injecting it into the scoring chain would add a feedback loop where past dynamics affect current scores, which affect future dynamics. Keeping it observational avoids this coupling.

**Five dimensions tracked, not four**: Confidence is included in dimension delta tracking even though Phase 48 excluded it from match scoring. Tracking confidence direction is valuable for observability ("confidence is increasing" is meaningful even if it doesn't affect the score directly).

**signal_name excluded from state equality**: `_states_equal()` compares only the five dimensions, not signal_name. This means states from different signals are considered equal if their dimensions match. This is correct — the memory tracks how the environmental state evolves, regardless of which signal produced it.

**Semantic ordering for trends**: RegimeType values don't have a natural numeric ordering (they're enum members). The semantic mapping (SPIKE_DOWN=-2 through SPIKE_UP=2) captures the directional meaning: moving from TREND_DOWN to TREND_UP is an increase, even though both are non-STABLE. Without this mapping, we could only say "CHANGED" — not whether the change was toward more or less intensity.

---

## Hard invariants

| ID  | Invariant                                              | Status |
|-----|--------------------------------------------------------|--------|
| 181 | Dynamics must be deterministic                         | PASS   |
| 182 | Snapshots must be immutable                            | PASS   |
| 183 | Missing previous state defaults to neutral             | PASS   |
| 184 | Dimensions must be independent                         | PASS   |
| 185 | Dynamics must not mutate planning/execution            | PASS   |

---

## Test results

- **Phase 49 tests:** 161 passed, 0 failed
- **Phase 48 regression:** 160 passed, 0 failed
- **Phase 30-49 regression:** 2956 passed, 0 failed

---

## Dependency boundary

`regime_dynamics.py` imports only:
- `__future__.annotations`
- `dataclasses` (dataclass)
- `enum` (Enum)
- `typing` (Any)
- `umh.runtime.regime` (RegimeType)
- `umh.runtime.regime_state` (CompositeRegimeState, ConfidenceLevel, RiskLevel, StabilityLevel, UrgencyLevel)

No imports from `umh/cells`, `umh/environments`, `umh/adapters`. The module depends only on the RegimeType enum and the Phase 48 composite state types.

---

## Design notes

### Why a memory class, not a pure function

Direction computation is pure (`compute_dimension_deltas` is stateless), but tracking persistence and transition count requires state. The `CompositeStateMemory` class encapsulates this state while keeping direction computation pure. Consumers who only need point-in-time deltas can call `compute_dimension_deltas` directly without instantiating memory.

### Why the CHANGED direction exists

For trend, the semantic mapping covers all five RegimeType values. But if a future RegimeType were added without a mapping, `compute_trend_direction` would return CHANGED rather than crashing. This is defensive design — the system degrades to "something changed" rather than raising an exception.

### Why is_first_update is explicit

On the first update, previous = current = state, so all deltas are FLAT and no transition is counted. Consumers need to know this is the bootstrapping case, not a genuine "nothing changed" result. The `is_first_update` flag distinguishes these.

---

## Known limitations

- No windowed statistics (e.g., "3 of last 5 transitions were risk increases")
- No velocity tracking (how fast dimensions are changing)
- No decay or aging of transition history
- No cross-dimension correlation detection
- Observational only — no influence on scoring chain

---

## Files verified

```
py_compile: regime_dynamics.py ✓
py_compile: __init__.py ✓
ruff format: all files ✓
```
