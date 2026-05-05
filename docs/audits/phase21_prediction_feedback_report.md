# Phase 21 Audit Report — Prediction Memory + Accuracy Feedback System v1

**Date:** 2026-04-29
**Status:** PASS — all invariants verified
**Tests:** 78/78 passed | Regression: 795/795 passed (phases 11B–21, zero regressions)

---

## Deliverables

| # | Deliverable | File | Status |
|---|-------------|------|--------|
| 1 | `PredictionRecord` + `PredictionStore` + `record_from_intent` | `umh/prediction/store.py` | DONE |
| 2 | `PredictionEvaluator` + `MatchResult` | `umh/prediction/evaluator.py` | DONE |
| 3 | `PredictionMetrics` + `PredictionAccuracy` + `ConfidenceBucket` + `SourceAccuracy` | `umh/prediction/metrics.py` | DONE |
| 4 | `umh/prediction/__init__.py` updated exports | `umh/prediction/__init__.py` | DONE |
| 5 | Advisor prediction storage + evaluation + expiration | `umh/runtime/advisor.py` | DONE |
| 6 | Loop completed_feedback pass-through | `umh/runtime/loop.py` | DONE |
| 7 | Test suite | `tests/unit/test_phase21_prediction_feedback.py` | DONE — 78 tests |

---

## Architecture

### Prediction Lifecycle

```
Intent generated (Phase 20)
  → PredictionRecord created via record_from_intent()
    → PredictionStore.append() — immutable core fields
      → Each tick: evaluate pending against completed jobs
        → MATCHED: job outcome confirms prediction
        → MISSED: job outcome contradicts prediction
        → EXPIRED: prediction ages past expiry_ticks threshold
          → PredictionMetrics computes accuracy (read-only)
```

### Key Design Principle: Forward-Only Status Transitions

PredictionRecord status transitions are strictly forward:
- PENDING → MATCHED (job confirmed prediction)
- PENDING → MISSED (evaluation found no match)
- PENDING → EXPIRED (aged past threshold)
- MATCHED/MISSED/EXPIRED → (terminal, no further transitions)

Attempting to re-resolve a resolved prediction returns False.

```python
store.mark_matched(pred_id)    # PENDING → MATCHED: True
store.mark_missed(pred_id)     # MATCHED → MISSED: False (blocked)
```

### Prediction Store

```
PredictionRecord:
  prediction_id, intent_id, inferred_goal, confidence
  predicted_actions (tuple), related_entities (tuple)
  source, context_hash, emitted_at
  status (PENDING → MATCHED/MISSED/EXPIRED)
  resolved_at, matched_job_id, tick_emitted, metadata
```

Core fields (prediction_id through emitted_at) are set at creation
and never modified. Only status, resolved_at, and matched_job_id
change during lifecycle transitions.

### Outcome Matching (Evaluator)

Deterministic matching criteria (checked in priority order):
1. **Entity match**: prediction `related_entities` ∩ feedback `task_type`
2. **Action match**: predicted action string contains the task_type
3. **Goal match**: inferred_goal string contains the task_type

Each completed job matches at most one prediction (first match wins).
Case-insensitive. No fuzzy matching, no randomness.

### Accuracy Metrics

```
PredictionAccuracy:
  total_predictions, pending, matched, missed, expired
  accuracy_rate = matched / (matched + missed + expired)
  miss_rate = (missed + expired) / (matched + missed + expired)

ConfidenceBucket:
  bucket_low, bucket_high, count, matched
  actual_accuracy, avg_confidence
  (well-calibrated → actual_accuracy ≈ avg_confidence)

SourceAccuracy:
  source, total, matched, accuracy_rate
  (per prediction source: repeated_workflow, continuation, time_pattern)
```

All computed read-only from PredictionStore records. Stateless —
recomputed from scratch on every call. Never mutates records.

### Advisor Integration

AdvisorRuntime now accepts optional:
- `prediction_store` — stores emitted predictions
- `prediction_evaluator` — matches predictions against outcomes
- `prediction_metrics` — computes accuracy

Extended tick sequence:
1. Signal processing (unchanged)
2. Cell cleanup (unchanged)
3. Prediction generation (Phase 20)
4. **Prediction storage** — new predictions → PredictionStore
5. **Prediction evaluation** — pending predictions vs completed_feedback
6. **Prediction expiration** — age-based expiry of stale predictions

New advisor methods:
- `get_prediction_accuracy()` — compute current accuracy metrics
- `clear_predictions()` — clears store + cache

### Loop Integration

RuntimeLoop.tick() now accepts optional `completed_feedback` which
flows through to the advisor's evaluation step. Without feedback,
evaluation is skipped (returns 0 matches).

---

## Tick-Level Data Flow

```
tick(prediction_context=ctx, completed_feedback=jobs)
  1. advisor.tick()
     a. process signals
     b. cleanup cells
     c. predict intents → generate plans → _pending_predictions
     d. store predictions → PredictionStore
     e. evaluate pending vs completed_feedback → mark MATCHED
     f. expire old predictions → mark EXPIRED
  2. poll node health
  3. poll jobs
```

---

## Hard Invariants

| # | Invariant | Verified |
|---|-----------|----------|
| 1–39 | All prior phase invariants | YES — 717 prior tests pass |
| 40 | Predictions stored immutably once emitted | YES — TestInvariants.test_inv40 |
| 41 | Outcomes linked to originating predictions | YES — TestInvariants.test_inv41 |
| 42 | Accuracy computation does not mutate records | YES — TestInvariants.test_inv42 |
| 43 | Prediction evaluation is deterministic | YES — TestInvariants.test_inv43 |
| 44 | No retroactive rewriting of prediction data | YES — TestInvariants.test_inv44 |

---

## Test Coverage Summary

| Category | Count | Description |
|----------|-------|-------------|
| PredictionRecord | 6 | creation, from_intent, serialization, hash determinism, hash variation, unique IDs |
| PredictionStore | 15 | append, list_pending, get_by_id, get_missing, mark_matched, mark_only_pending, mark_missed, mark_missed_only_pending, expiration, expire_no_resolved, list_all, list_resolved, pending_count, eviction, clear, forward_only |
| PredictionEvaluator | 10 | entity_match, action_match, goal_match, no_match, one_to_one, multi_match, case_insensitive, empty_inputs, determinism, serialization |
| PredictionMetrics | 12 | all_matched, mixed, no_resolved, empty, from_store, serialization, calibration, calibration_empty, bucket_serialization, source_accuracy, source_empty, source_serialization, no_mutation |
| Advisor integration | 7 | stored_on_tick, evaluated_against_feedback, expire_over_ticks, accuracy_exposed, state_includes_store, without_store_unchanged, clear_clears_store |
| Loop integration | 2 | passes_completed_feedback, without_feedback_unchanged |
| Determinism | 3 | same_matches, same_accuracy, context_hash |
| Invariant enforcement | 5 | inv40–inv44 |
| Boundary invariants | 4×3=12 | no_cells, no_environments, no_subprocess, no_shell for 3 files |
| Regression | 4 | predictor, planner, feedback_store, advisor_backward_compat |
| **Total** | **78** | |

---

## Regression

Full suite: 795 tests across phases 11B–21. Zero failures.

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
| **Total** | **795** | **PASS** |

---

## Known Limitations

- Simple string-based matching (no embeddings, no semantic similarity)
- No long-term persistence (in-memory only — lost on restart)
- No adaptive confidence threshold tuning (static thresholds)
- No ML model for matching or prediction
- Expiration is tick-based, not time-based
- One-to-one matching only (one job matches one prediction)
- No cross-session prediction memory
- No feedback loop from accuracy back to predictor confidence

---

## Files Created/Modified

| File | Action |
|------|--------|
| `umh/prediction/store.py` | CREATED — PredictionRecord + PredictionStore + record_from_intent |
| `umh/prediction/evaluator.py` | CREATED — PredictionEvaluator + MatchResult |
| `umh/prediction/metrics.py` | CREATED — PredictionMetrics + PredictionAccuracy + ConfidenceBucket + SourceAccuracy |
| `umh/prediction/__init__.py` | MODIFIED — added new exports |
| `umh/runtime/advisor.py` | MODIFIED — prediction storage, evaluation, expiration, accuracy |
| `umh/runtime/loop.py` | MODIFIED — completed_feedback pass-through |
| `tests/unit/test_phase21_prediction_feedback.py` | CREATED — 78 tests |
| `docs/audits/phase21_prediction_feedback_report.md` | CREATED — this file |

---

## Is Phase 22 Safe?

YES. Phase 21 is fully backward compatible:
- `AdvisorRuntime()` without prediction_store/evaluator/metrics works identically to Phase 20
- `RuntimeLoop.tick()` without completed_feedback works identically to Phase 20
- `tick()` returns `predictions_stored/matched/expired: 0` when no store configured
- New `umh/prediction/store.py`, `evaluator.py`, `metrics.py` are additive
- All Phase 20 tests pass unchanged (71/71)
- Prediction store is append-only — never removes or mutates core record fields
