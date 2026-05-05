# Phase 28: Simulation Calibration + Reality Alignment Layer v1 — Audit Report

**Date**: 2026-04-30
**Status**: COMPLETE
**Tests**: 92 passed, 0 failed
**Regression**: 1372 passed (phases 11-28), 0 regressions

---

## Deliverables

### New Modules (1)

| File | Purpose | Lines |
|------|---------|-------|
| `umh/runtime/calibration.py` | ExecutionOutcome, CalibrationError, CalibrationRecord, CalibrationFactors, CalibrationAdjustment, CalibrationEngine, CalibrationStore, SimulationCalibrator | ~240 |

### Modified Modules (4)

| File | Changes |
|------|---------|
| `umh/runtime/simulation.py` | Added `calibration: CalibrationFactors \| None` param to `SimulationEngine.simulate()`, applies factors to estimates with clamping |
| `umh/runtime/evaluator.py` | Added `calibration: CalibrationFactors \| None` param to `StrategySimulator.run()`, passes through to engine |
| `umh/runtime/advisor.py` | Added `calibration_engine`, `calibration_store`, `simulation_calibrator` constructor params; `calibration_factors` property; `record_outcome()` method; `_calibrate_simulation()` in tick(); calibration in `get_state()`; reset in `clear()` |
| `umh/runtime/__init__.py` | Added 8 new exports (CalibrationAdjustment, CalibrationEngine, CalibrationError, CalibrationFactors, CalibrationRecord, CalibrationStore, ExecutionOutcome, SimulationCalibrator) |

### Test File (1)

| File | Tests |
|------|-------|
| `tests/unit/test_phase28_calibration.py` | 92 |

---

## Architecture

```
SimulationEngine.simulate(strategy, model)
        │
        ▼
raw estimates (completion, latency, risk, effort)
        │
        ▼ (if calibration factors provided)
estimates × factors → clamped
        │
        ▼
SimulatedOutcome
        │
        ▼
StrategySimulator.run(base, model, calibration)
        │
        ▼
SimulationResult (selected strategy)
        │
        ▼
AdvisorRuntime._rebuild_strategy()
        │                           ┌─ CalibrationEngine.compare()
        ▼                           │  CalibrationEngine.build_record()
AdvisorRuntime._calibrate_simulation() ──┤
                                    │  CalibrationStore.append()
                                    │  CalibrationStore.mean_errors()
                                    └─ SimulationCalibrator.calibrate()
                                           │
                                           ▼
                                    CalibrationFactors (adjusted)
                                    CalibrationAdjustment[] (explainable)
```

---

## Calibration Pipeline

| Step | Component | Input | Output |
|------|-----------|-------|--------|
| 1 | CalibrationEngine.compare() | SimulatedOutcome + ExecutionOutcome | CalibrationError (signed) |
| 2 | CalibrationEngine.build_record() | SimulatedOutcome + ExecutionOutcome | CalibrationRecord (immutable) |
| 3 | CalibrationStore.append() | CalibrationRecord | stored (append-only) |
| 4 | CalibrationStore.mean_errors() | n records | CalibrationError (mean) |
| 5 | SimulationCalibrator.calibrate() | CalibrationFactors + mean error | new CalibrationFactors + adjustments |
| 6 | SimulationEngine.simulate() | strategy + factors | calibrated SimulatedOutcome |

---

## Calibration Factors

| Factor | Range | Default | Direction |
|--------|-------|---------|-----------|
| completion_factor | [0.1, 2.0] | 1.0 | Overestimate → decrease |
| latency_factor | [0.1, 2.0] | 1.0 | Overestimate → decrease |
| failure_factor | [0.1, 2.0] | 1.0 | Overestimate → increase (inverted) |
| effort_factor | [0.1, 2.0] | 1.0 | Overestimate → decrease |

Learning rate: configurable [0.01, 0.5], default 0.1.
Minimum adjustment threshold: |error| ≥ 0.01.
Minimum delta threshold: |delta| > 0.001 to generate adjustment record.

---

## Hard Invariants

| ID | Invariant | Verified |
|----|-----------|----------|
| 75 | Calibration records must be immutable | YES — test_inv75_calibration_records_immutable (all 5 types) |
| 76 | Calibration store must be append-only | YES — test_inv76_calibration_store_append_only |
| 77 | Calibration factors must stay within bounds | YES — test_inv77_factors_bounded, test_inv77_factors_bounded_negative |
| 78 | Calibration must be deterministic | YES — test_inv78_calibration_deterministic |
| 79 | No forbidden boundary imports | YES — test_inv79_no_forbidden_imports, test_inv79_simulation_no_forbidden_imports, test_inv79_evaluator_no_forbidden_imports |

---

## Bug Found and Fixed

**Deadlock in `CalibrationStore.to_dict()`**: The method acquired `self._lock` (a `threading.Lock`, non-reentrant) then called `self.mean_errors()` which also tried to acquire the same lock. Fixed by inlining the mean error computation inside the lock scope instead of calling the public method.

---

## Test Breakdown

| Section | Tests | Coverage |
|---------|-------|----------|
| ExecutionOutcome | 6 | Creation, frozen, timestamp, to_dict, rounding |
| CalibrationError | 6 | Creation, frozen, total_error, mean_absolute_error, zero, to_dict |
| CalibrationRecord | 3 | Creation, frozen, to_dict |
| CalibrationFactors | 4 | Defaults, custom, frozen, to_dict |
| CalibrationAdjustment | 3 | Creation, frozen, to_dict |
| CalibrationEngine | 7 | Perfect, overestimate, underestimate, signed, build_record, timestamp, deterministic |
| CalibrationStore | 11 | Empty, append, list, recent, eviction, min_max, mean_errors, mean_errors_n, to_dict, thread_safety |
| SimulationCalibrator | 15 | No adjustment, overestimate, underestimate, latency, failure_inverted, effort, bounded_min, bounded_max, learning_rate (4), deterministic, multiple, reason |
| SimulationEngine calibration | 9 | No calibration, identity, scales (4), clamps (3) |
| StrategySimulator calibration | 3 | Without, with, affects_ranking |
| Advisor integration | 9 | Properties, defaults, tick keys, record_outcome, requires_simulation, get_state, clear, adjusts, no_components |
| Hard invariants | 8 | INV 75-79 |
| Boundary/exports | 7 | Imports (3), compile (4), end-to-end |
| **Total** | **92** | |

---

## Known Limitations

- Calibration uses getattr fallbacks for ExecutionFeedback fields (no native completion_rate/latency/effort fields on feedback)
- No persistence of calibration records or factors to disk (in-memory only)
- No per-task-type calibration — single set of factors for all tasks
- No exponential decay on calibration records — all records weighted equally
- No statistical significance test before adjusting factors (just ≥3 records)
- Learning rate is fixed per calibrator instance (no adaptive learning rate)

---

## Cumulative Test Count (Phases 11-28)

| Phase | Tests | Cumulative |
|-------|-------|------------|
| 11B-11F | 259 | 259 |
| 12 | 49 | 308 |
| 13 | 55 | 363 |
| 14 | 50 | 413 |
| 15 | 17 | 430 |
| 16 | 47 | 477 |
| 17 | 61 | 538 |
| 18 | 57 | 595 |
| 19 | 51 | 646 |
| 20 | 71 | 717 |
| 21 | 78 | 795 |
| 22 | 73 | 868 |
| 23 | 83 | 951 |
| 24 | 82 | 1033 |
| 25 | 88 | 1121 |
| 26 | 79 | 1200 |
| 27 | 80 | 1280 |
| **28** | **92** | **1372** |
