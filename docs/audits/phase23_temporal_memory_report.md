# Phase 23 Audit Report — Cross-Session Memory + Temporal Pattern System v1

**Date:** 2026-04-30
**Status:** PASS — all invariants verified
**Tests:** 83/83 passed | Regression: 951/951 passed (phases 11B–23, zero regressions)

---

## Deliverables

| # | Deliverable | File | Status |
|---|-------------|------|--------|
| 1 | `FilePredictionBackend` + `PersistenceStats` | `umh/prediction/persistence.py` | DONE |
| 2 | `TemporalWeighter` + `DecayResult` | `umh/prediction/temporal.py` | DONE |
| 3 | `PredictionWeight.last_updated` + `WeightStore.restore_weight` | `umh/prediction/weights.py` | DONE |
| 4 | `PredictionBootstrapReport` + `rehydrate_predictions` | `umh/runtime/bootstrap.py` | DONE |
| 5 | Advisor persistence + temporal integration | `umh/runtime/advisor.py` | DONE |
| 6 | `umh/prediction/__init__.py` updated exports | `umh/prediction/__init__.py` | DONE |
| 7 | `umh/runtime/__init__.py` updated exports | `umh/runtime/__init__.py` | DONE |
| 8 | Test suite | `tests/unit/test_phase23_temporal_memory.py` | DONE — 83 tests |

---

## Architecture

### Cross-Session Persistence Pipeline

```
Advisor tick completes
  → _persist_state()
    → FilePredictionBackend.save_records(all_records)   [JSONL, atomic]
    → FilePredictionBackend.save_weights(all_weights)   [JSON, atomic]

Next startup
  → RuntimeBootstrap.rehydrate_predictions(backend, store, weight_store)
    → load records → restore into PredictionStore
    → load weights → restore into WeightStore (via restore_weight)
```

### Atomic Write Pattern

```
save_records / save_weights:
  1. mkstemp(dir=data_dir)           — temp file in same directory
  2. write all data to temp file
  3. f.flush() + os.fsync(fd)        — ensure bytes on disk
  4. os.replace(tmp, target)         — atomic rename (POSIX)
  5. On failure: unlink temp file, return error stats

Result: either old complete file or new complete file, never partial.
```

### JSONL Record Format

```
{"prediction_id":"pred_001","intent_id":"intent_001","inferred_goal":"...","confidence":0.7,...}
{"prediction_id":"pred_002","intent_id":"intent_002","inferred_goal":"...","confidence":0.8,...}
```

One JSON object per line. Corrupted lines skipped on load — partial recovery always works.

### Temporal Decay Model

```
TemporalWeighter:
  apply_decay(weight, age_hours) → DecayResult

Formula:
  decay_factor = exp(-decay_rate * age_hours)
  decayed = baseline + (weight - baseline) * decay_factor

Properties:
  - Decays toward baseline (1.0), not toward zero
  - High weights (e.g. 2.5) decrease toward 1.0 over time
  - Low weights (e.g. 0.3) increase toward 1.0 over time
  - At age=0: decayed = weight (no change)
  - At age=∞: decayed = baseline (full decay)
  - Clamped: weight ∈ [0.1, 3.0]

Default parameters:
  decay_rate = 0.005 (~50% decay at ~139 hours / ~6 days)
  baseline = 1.0
```

### Weight Timestamp Integration

```
PredictionWeight now includes:
  last_updated: str (ISO-8601 timestamp)

Set on every update_weight() call.
Used by TemporalWeighter to compute age.

WeightStore.restore_weight():
  - Restores weight from persistence
  - Clamps weight to [0.1, 3.0]
  - Clamps counts to >= 0
  - Preserves last_updated timestamp
```

### Bootstrap Rehydration

```
RuntimeBootstrap.rehydrate_predictions(backend, store?, weight_store?):

Steps:
  1. Load records from JSONL → skip corrupted lines
  2. Append valid records to PredictionStore
  3. Load weights from JSON → skip invalid entries
  4. Restore weights via WeightStore.restore_weight()
  5. Return PredictionBootstrapReport

Safety:
  - Corrupted entries skipped, never crash
  - Partial recovery always works
  - backend/store/weight_store all optional
  - Returns structured report for diagnostics
```

### Advisor Integration

AdvisorRuntime now accepts optional:
- `persistence_backend` — `FilePredictionBackend` for durable storage
- `temporal_weighter` — `TemporalWeighter` for time decay

Extended tick sequence (persistence runs AFTER adaptation):
1. Signal processing
2. Cell cleanup
3. Prediction generation (Phase 20)
4. Prediction storage (Phase 21)
5. Prediction evaluation (Phase 21)
6. Prediction expiration (Phase 21)
7. Weight adaptation (Phase 22)
8. Threshold adaptation (Phase 22)
9. **State persistence** — save records + weights to disk

New methods:
- `get_decayed_weights()` — returns all weights with temporal decay applied
- `_persist_state()` — persists records and weights, returns success/failure

---

## Stability Guarantees

| Property | Mechanism | Verified |
|----------|-----------|----------|
| No data loss on crash | Atomic writes (temp → fsync → replace) | TestFilePredictionBackendRecords |
| Corrupted data skipped | Per-line JSON parsing with try/except | test_corrupted_lines_skipped |
| Partial recovery works | JSONL format — each line independent | TestPredictionBootstrap |
| Decay never diverges | exp(-rate * age) ∈ [0, 1], clamped output | TestSafetyControls |
| System works without persistence | All persistence params optional (None default) | test_inv54, test_system_works_without_persistence |
| System works without temporal decay | Temporal weighter optional (None default) | test_system_works_without_temporal |
| Weight bounds preserved on restore | Clamped to [0.1, 3.0] in restore_weight | test_restore_clamps_weight |

---

## Hard Invariants

| # | Invariant | Verified |
|---|-----------|----------|
| 1–49 | All prior phase invariants | YES — 868 prior tests pass |
| 50 | Historical prediction data must never be overwritten | YES — test_inv50 |
| 51 | Persistence must be append-only or atomic-write safe | YES — test_inv51 |
| 52 | Time decay must be deterministic | YES — test_inv52 |
| 53 | Rehydration must not corrupt state | YES — test_inv53 |
| 54 | System must function without persistence (graceful fallback) | YES — test_inv54 |

---

## Test Coverage Summary

| Category | Count | Description |
|----------|-------|-------------|
| Record serialization | 4 | round-trip, statuses, metadata |
| Record persistence | 7 | save/load, empty, atomic, corrupted, empty lines, overwrite, large batch |
| Weight persistence | 5 | save/load, empty, corrupted, not array, missing keys |
| Persistence safety | 4 | nested dir creation, exists check, readonly dir |
| Temporal decay | 10 | zero age, reduce high, increase low, converge, negative age, zero rate, determinism, fields, clamp above/below |
| Temporal age compute | 5 | basic, same time, future, invalid, naive timestamps |
| Temporal config | 3 | negative rate rejected, get_state, to_dict |
| WeightStore timestamp | 5 | update sets timestamp, restore, clamp weight/counts, to_dict |
| Bootstrap rehydration | 6 | records, weights, both, empty, corrupted, report to_dict |
| Advisor persistence | 6 | tick persists, no persistence, state flags, decay rate, decayed weights, no temporal |
| Advisor round trip | 2 | records survive restart, weights survive restart |
| Loop integration | 1 | loop tick persists |
| Safety controls | 5 | bounds sweep, failure no crash, rehydration no crash, works without persistence, works without temporal |
| Determinism | 3 | same decay, same persistence, same rehydration |
| Invariant enforcement | 5 | inv50–inv54 |
| Boundary invariants | 4×2=8 | no cells, no environments, no subprocess, no shell for 2 files |
| Regression | 4 | weight_store, prediction_store, advisor, bootstrap compat |
| **Total** | **83** | |

---

## Regression

Full suite: 951 tests across phases 11B–23. Zero failures.

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
| 23 | 83 | PASS |
| **Total** | **951** | **PASS** |

---

## Known Limitations

- File-based persistence only (no database, no distributed storage)
- No distributed memory sync (single-node only)
- No embedding-based similarity for pattern matching
- No long-horizon pattern clustering
- Temporal decay is global (same rate for all patterns)
- Persistence is full-replace, not incremental append (OK for current scale)
- No compression of old records
- No automatic garbage collection of ancient records

---

## Files Created/Modified

| File | Action |
|------|--------|
| `umh/prediction/persistence.py` | CREATED — FilePredictionBackend + PersistenceStats |
| `umh/prediction/temporal.py` | CREATED — TemporalWeighter + DecayResult |
| `umh/prediction/weights.py` | MODIFIED — added last_updated, restore_weight |
| `umh/prediction/__init__.py` | MODIFIED — added new exports |
| `umh/runtime/bootstrap.py` | MODIFIED — PredictionBootstrapReport + rehydrate_predictions |
| `umh/runtime/advisor.py` | MODIFIED — persistence + temporal integration |
| `umh/runtime/__init__.py` | MODIFIED — added PredictionBootstrapReport export |
| `tests/unit/test_phase23_temporal_memory.py` | CREATED — 83 tests |
| `docs/audits/phase23_temporal_memory_report.md` | CREATED — this file |

---

## Is Phase 24 Safe?

YES. Phase 23 is fully backward compatible:
- `AdvisorRuntime()` without persistence_backend/temporal_weighter works identically to Phase 22
- `tick()` returns `persisted: False` when no persistence configured
- New `umh/prediction/persistence.py` and `temporal.py` are additive
- All Phase 22 tests pass unchanged (73/73)
- `PredictionWeight.last_updated` defaults to empty string — existing weights work as before
- `WeightStore.restore_weight()` is a new method — no existing API changed
- `RuntimeBootstrap.rehydrate_predictions()` is a new method — existing `rehydrate()` unchanged
- `PredictionBootstrapReport` is additive — `BootstrapReport` unchanged
