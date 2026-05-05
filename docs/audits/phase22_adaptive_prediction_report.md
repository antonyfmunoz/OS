# Phase 22 Audit Report — Adaptive Prediction Weighting + Threshold System v1

**Date:** 2026-04-30
**Status:** PASS — all invariants verified
**Tests:** 73/73 passed | Regression: 868/868 passed (phases 11B–22, zero regressions)

---

## Deliverables

| # | Deliverable | File | Status |
|---|-------------|------|--------|
| 1 | `PredictionWeight` + `WeightStore` | `umh/prediction/weights.py` | DONE |
| 2 | `ConfidenceCalibrator` + `CalibrationResult` + `ThresholdAdapter` | `umh/prediction/calibrator.py` | DONE |
| 3 | `umh/prediction/__init__.py` updated exports | `umh/prediction/__init__.py` | DONE |
| 4 | Advisor weight adaptation + threshold adaptation | `umh/runtime/advisor.py` | DONE |
| 5 | Test suite | `tests/unit/test_phase22_adaptive_prediction.py` | DONE — 73 tests |

---

## Architecture

### Adaptive Prediction Pipeline

```
Phase 21: Prediction evaluated → MATCHED / MISSED / EXPIRED
  ↓
Phase 22: Adaptation pass (runs AFTER evaluation)
  → WeightStore.update_weight(pattern_key, matched)
    → EMA: weight += lr * (target - weight), clamped
  → ThresholdAdapter.adapt(accuracy_rate)
    → threshold ± step, clamped to [0.4, 0.9]
  → Next tick: ConfidenceCalibrator.adjust_confidence(raw, pattern_key)
    → calibrated = raw * weight, clamped to [0.01, 0.99]
```

### Weight Model

```
PredictionWeight:
  pattern_key (e.g. "repeated_workflow", "continuation")
  weight (float, default 1.0, range [0.1, 3.0])
  success_count, failure_count
  success_rate (computed)

Update rule: Exponential Moving Average (EMA)
  target = max_weight (3.0) if matched, min_weight (0.1) if missed
  raw_delta = learning_rate * (target - weight)
  clamped_delta = clamp(raw_delta, -max_delta, max_delta)
  new_weight = clamp(weight + clamped_delta, min_weight, max_weight)
```

Key properties:
- **Bounded**: weight ∈ [0.1, 3.0], never diverges
- **Convergent**: EMA naturally converges, delta decreases as weight approaches target
- **Deterministic**: same update sequence → same weights
- **Sample-gated**: no weight changes until ≥ 2 samples (prevents noise)

### Confidence Calibration

```
ConfidenceCalibrator:
  adjust_confidence(raw_confidence, pattern_key) → CalibrationResult

Formula:
  calibrated = raw_confidence * pattern_weight

Additional correction when success_rate data available:
  if success_rate < raw_confidence (overconfident):
    calibrated = min(calibrated, (success_rate + raw_confidence) / 2)

Clamped: calibrated ∈ [0.01, 0.99]
(Epistemic humility: no prediction is certain or impossible)
```

### Threshold Adaptation

```
ThresholdAdapter:
  adapt(accuracy_rate) → new_threshold

Rules:
  accuracy < 0.3 → threshold += step (be more selective)
  accuracy > 0.7 → threshold -= step (allow more predictions)
  otherwise → no change

Bounds: threshold ∈ [0.4, 0.9]
Step: 0.02 per update (configurable)
```

### Advisor Integration

AdvisorRuntime now accepts optional:
- `weight_store` — stores per-pattern prediction weights
- `confidence_calibrator` — adjusts confidence using learned weights
- `threshold_adapter` — dynamically adjusts confidence threshold

Extended tick sequence (adaptation runs AFTER evaluation):
1. Signal processing
2. Cell cleanup
3. Prediction generation (Phase 20)
4. Prediction storage (Phase 21)
5. Prediction evaluation (Phase 21)
6. Prediction expiration (Phase 21)
7. **Weight adaptation** — update weights from resolved predictions
8. **Threshold adaptation** — adjust threshold from overall accuracy

---

## Stability Guarantees

| Property | Mechanism | Verified |
|----------|-----------|----------|
| No divergent weights | EMA + [0.1, 3.0] clamp | TestSafetyControls (8 tests) |
| No divergent threshold | [0.4, 0.9] clamp + fixed step | TestSafetyControls |
| No single-update spike | max_delta clamp (0.3 default) | test_delta_clamped |
| Stable under 0% accuracy | Weights floor at 0.1, threshold caps at 0.9 | test_inv49 |
| Stable under 100% accuracy | Weights cap at 3.0, threshold floors at 0.4 | test_system_stable_under_all_matches |
| Stable under alternating | EMA converges to midpoint | test_alternating_outcomes_converge |
| No division by zero | success_rate defaults to 0.5 when no data | test_no_division_by_zero_in_calibrator |

---

## Hard Invariants

| # | Invariant | Verified |
|---|-----------|----------|
| 1–44 | All prior phase invariants | YES — 795 prior tests pass |
| 45 | Adaptation based ONLY on observed outcomes | YES — test_inv45 |
| 46 | No retroactive mutation of prediction history | YES — test_inv46 |
| 47 | Weight updates are deterministic | YES — test_inv47 |
| 48 | Adaptation is bounded (no runaway amplification) | YES — test_inv48 |
| 49 | System remains stable under poor accuracy | YES — test_inv49 |

---

## Test Coverage Summary

| Category | Count | Description |
|----------|-------|-------------|
| PredictionWeight | 4 | creation, success_rate no data, success_rate with data, serialization |
| WeightStore | 14 | get default, get value, match increase, miss decrease, bounded above/below, min samples, delta clamped, determinism, lr validation, list, state, clear, independence |
| ConfidenceCalibrator | 7 | no history, high weight, low weight, clamped min/max, success_rate correction, serialization |
| ThresholdAdapter | 11 | default, low accuracy, high accuracy, mid accuracy, bounded above/below, step size, update count, state, reset, initial clamped |
| Calibrator + Predictor integration | 3 | reduces overconfident, boosts underconfident, evolves with outcomes |
| Advisor integration | 5 | weights updated, threshold adapts, state includes new fields, without adaptation, clear resets |
| Loop integration | 1 | adaptation flows through |
| Safety controls | 8 | weight bounds (×2), threshold bounds (×2), all misses stable, all matches stable, no div zero, alternating converge |
| Determinism | 3 | same weights, same threshold, same calibration |
| Invariant enforcement | 5 | inv45–inv49 |
| Boundary invariants | 4×2=8 | no cells, no environments, no subprocess, no shell for 2 files |
| Regression | 4 | phase21 store, phase20 predictor, phase19 feedback, advisor backward compat |
| **Total** | **73** | |

---

## Regression

Full suite: 868 tests across phases 11B–22. Zero failures.

| Phase | Tests | Result |
|-------|-------|--------|
| 11B–11F | 259 | PASS |
| 12 | 49 | PASS |
| 13 | 55 | PASS |
| 14 | 50 | PASS |
| 15 | 17 | PASS |
| 16 | 47 | PASS |
| 17 | 61 | PASS |
| 18 | 57 | PASS |
| 19 | 51 | PASS |
| 20 | 71 | PASS |
| 21 | 78 | PASS |
| 22 | 73 | PASS |
| **Total** | **868** | **PASS** |

---

## Known Limitations

- Simple pattern keys (no embeddings, no semantic grouping)
- No long-term persistence (in-memory only — lost on restart)
- No cross-user learning
- No ML model (heuristic EMA only)
- Calibrator doesn't yet feed back into the Predictor's confidence calculation at prediction time (the wiring exists but the Predictor uses raw confidence internally)
- No time-decay on weight history (old outcomes weigh same as recent)
- Threshold adaptation is global (not per-source or per-pattern)

---

## Files Created/Modified

| File | Action |
|------|--------|
| `umh/prediction/weights.py` | CREATED — PredictionWeight + WeightStore |
| `umh/prediction/calibrator.py` | CREATED — ConfidenceCalibrator + CalibrationResult + ThresholdAdapter |
| `umh/prediction/__init__.py` | MODIFIED — added new exports |
| `umh/runtime/advisor.py` | MODIFIED — weight adaptation, threshold adaptation, calibrator integration |
| `tests/unit/test_phase22_adaptive_prediction.py` | CREATED — 73 tests |
| `docs/audits/phase22_adaptive_prediction_report.md` | CREATED — this file |

---

## Is Phase 23 Safe?

YES. Phase 22 is fully backward compatible:
- `AdvisorRuntime()` without weight_store/calibrator/threshold_adapter works identically to Phase 21
- `tick()` returns `weights_updated: 0, threshold_adapted: False` when no adaptation configured
- New `umh/prediction/weights.py` and `calibrator.py` are additive
- All Phase 21 tests pass unchanged (78/78)
- Weight store and threshold adapter are self-contained — no impact on scheduler weights (Phase 19) or prediction store (Phase 21)
