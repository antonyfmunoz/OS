# Phase 42 — Temporal Regime Classification Layer v1

## Audit Report

**Date:** 2026-04-30
**Phase:** 42 of UMH runtime build
**Status:** COMPLETE

---

## What was built

### New file
- `umh/runtime/regime.py` — RegimeType, RegimeResult, RegimeSnapshot, RegimeThresholds, DEFAULT_THRESHOLDS, classify_regime, classify_all_regimes, classify_from_horizon

### Modified files
- `umh/runtime/__init__.py` — 8 new exports

### Test file
- `tests/unit/test_phase42_regime.py` — 131 tests across 22 sections

---

## Architecture

### Problem solved

Phase 41 introduced dual-horizon EMA with delta = fast - slow. The delta is a continuous value that indicates the difference between short-term and long-term behavior. But continuous values are ambiguous — downstream consumers can't easily distinguish a noise spike from a sustained trend shift without thresholds.

Phase 42 converts the continuous delta into discrete regime labels.

### Classification rules

```
abs_delta = |delta|

if abs_delta < trend_threshold (0.08):
    → STABLE

elif abs_delta >= spike_threshold (0.25):
    → SPIKE_UP (delta > 0) or SPIKE_DOWN (delta < 0)

else:
    → TREND_UP (delta > 0) or TREND_DOWN (delta < 0)
```

### Regime meanings

| Regime       | Delta range        | Meaning                                    |
|-------------|--------------------|--------------------------------------------|
| STABLE      | |δ| < 0.08         | Signal tracking its trend; no action needed |
| TREND_UP    | 0.08 ≤ δ < 0.25   | Signal rising above trend; sustained shift  |
| TREND_DOWN  | -0.25 < δ ≤ -0.08 | Signal falling below trend; sustained shift |
| SPIKE_UP    | δ ≥ 0.25           | Rapid upward spike; may be transient        |
| SPIKE_DOWN  | δ ≤ -0.25          | Rapid downward spike; may be transient      |

### Threshold design

The two thresholds create three non-overlapping bands:

```
STABLE:  [0, 0.08)     — noise floor
TREND:   [0.08, 0.25)  — meaningful sustained change
SPIKE:   [0.25, 1.0]   — rapid transient change
```

The bands are designed so that:
- STABLE band is small (0.08) — signals must be very quiet to be classified as stable
- TREND band is wide (0.08 to 0.25) — catches gradual sustained changes
- SPIKE band starts at 0.25 — requires significant delta to trigger

### Data model

```
RegimeType (Enum):
    STABLE, TREND_UP, TREND_DOWN, SPIKE_UP, SPIKE_DOWN

RegimeResult (frozen dataclass):
    signal_name, regime, delta, magnitude
    is_spike, is_trend
    Properties: is_stable, is_up, is_down

RegimeSnapshot (frozen dataclass):
    regimes: dict[str, RegimeResult]
    tick: int
    Methods: get(), get_regime(), has_any_spike(),
             has_any_trend(), all_stable(),
             spike_signals(), trend_signals()

RegimeThresholds (frozen dataclass):
    spike_threshold (default 0.25)
    trend_threshold (default 0.08)
    Enforced: trend_threshold < spike_threshold
```

### Pipeline integration

```
raw_context
  → HorizonMemory.smooth()
    → HorizonSnapshot (with deltas per signal)
  → classify_from_horizon(snapshot)
    → RegimeSnapshot (with discrete regimes per signal)
  → downstream consumers check:
    - snap.has_any_spike() → trigger alert
    - snap.all_stable()    → no action needed
    - snap.spike_signals() → list of spiking signals
    - snap.get_regime("urgency") → specific signal regime
```

### Stateless design

All classification functions are pure: delta in, regime out. No state, no mutation, no memory. This keeps the regime layer composable — it can be applied to any HorizonSnapshot without side effects.

---

## Hard invariants

| ID  | Invariant                                              | Status |
|-----|--------------------------------------------------------|--------|
| 146 | Deterministic classification                           | PASS   |
| 147 | No state mutation                                      | PASS   |
| 148 | Same delta → same regime                               | PASS   |
| 149 | Neutral delta → STABLE                                 | PASS   |
| 150 | No classification oscillation under small noise        | PASS   |

---

## Test results

- **Phase 42 tests:** 131 passed, 0 failed
- **Phase 39-42 regression:** 394 + 131 = 525 passed, 0 failed
- **Phase 30-42 regression:** 1908 passed, 0 failed

---

## Dependency boundary

`regime.py` imports only:
- `__future__.annotations`
- `dataclasses` (dataclass)
- `enum` (Enum)
- `typing` (Any)
- `umh.runtime.horizon` (HorizonSnapshot) — inside `classify_from_horizon()` only (lazy import)

No imports from `umh/cells`, `umh/environments`, `umh/adapters`.

---

## Design notes

### Why static thresholds instead of adaptive

Static thresholds are deterministic and predictable. Adaptive thresholds (e.g., based on recent volatility) would introduce state and make the classifier non-deterministic across time. The invariant "same delta → same regime" requires static thresholds. Future phases can add hysteresis or adaptive behavior as a separate layer on top.

### Why three bands, not two

Two-band (spike vs. stable) would miss gradual trends. Three bands allow downstream consumers to differentiate:
- A spike in urgency might trigger an immediate override
- A trend in risk_level might adjust strategy parameters
- Stable signals need no action

### Why RegimeThresholds is configurable

Different environments may have different noise floors. A production system with low-variance signals might use tighter thresholds. A system in exploration mode might use wider thresholds. The `classify_from_horizon()` function accepts optional thresholds for this purpose.

### Why trend_threshold < spike_threshold is enforced

If trend_threshold >= spike_threshold, the TREND band would be empty — every non-stable signal would be classified as SPIKE. The enforcement guarantees all three bands exist.

---

## Downstream usage potential

| Consumer               | Uses                                    |
|------------------------|-----------------------------------------|
| Strategy adjustment    | spike → override; trend → adapt         |
| Alerting/monitoring    | has_any_spike() → trigger notification  |
| Weight adaptation      | regime-aware multiplier adjustment      |
| Logging/observability  | regime_snapshot.to_dict() → structured log |
| Decision gating        | all_stable() → safe to proceed          |

---

## Known limitations

- Static thresholds — no adaptation based on signal history
- No hysteresis — classification can change immediately at threshold boundaries
- No learned classification — thresholds are configured, not trained
- No temporal persistence — regime is computed per-tick, not smoothed over time
- No regime transition tracking — no concept of "entering" or "leaving" a regime

---

## Files verified

```
py_compile: regime.py ✓
py_compile: __init__.py ✓
ruff format: all files ✓
```
