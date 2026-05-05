# Phase 20 Audit Report — Intent Modeling + Predictive Execution v1

**Date:** 2026-04-29
**Status:** PASS — all invariants verified
**Tests:** 71/71 passed | Regression: 717/717 passed (phases 11B–20, zero regressions)

---

## Deliverables

| # | Deliverable | File | Status |
|---|-------------|------|--------|
| 1 | `UserIntent` + `make_intent_id` | `umh/prediction/intent.py` | DONE |
| 2 | `PredictionContext` + `Predictor` | `umh/prediction/predictor.py` | DONE |
| 3 | `PredictedPlan` + `PredictionPolicy` + `PredictivePlanner` | `umh/prediction/planner.py` | DONE |
| 4 | `umh/prediction/__init__.py` | `umh/prediction/__init__.py` | DONE |
| 5 | `AdvisorRuntime` prediction integration | `umh/runtime/advisor.py` | DONE |
| 6 | `RuntimeLoop` prediction context pass-through | `umh/runtime/loop.py` | DONE |
| 7 | `umh/runtime/__init__.py` exports | `umh/runtime/__init__.py` | DONE |
| 8 | Test suite | `tests/unit/test_phase20_prediction.py` | DONE — 71 tests |

---

## Architecture

### Prediction Pipeline

```
FeedbackStore (Phase 19)
  → Predictor.build_context() → PredictionContext (snapshot)
    → Predictor.predict_intent() → List[UserIntent]
      → PredictivePlanner.predict_plans() → List[PredictedPlan]
        → AdvisorRuntime._pending_predictions (cached, never executed)
```

### Key Design Principle: Predictions as Read-Only Artifacts

Predictions are **descriptive, not prescriptive**. They describe what
the system believes the user will do next, but they never act on that
belief without explicit governance. Every PredictedPlan:
- is tagged `speculative=True`
- has `dry_run=True` on the objective
- uses `PlanStatus.DRAFT` (never EXECUTING)
- carries a `PredictionPolicy` governance gate

```python
# Prediction is read-only — never auto-executes
plan = planner.predict_plan(intent)
assert plan.speculative is True
assert plan.can_auto_execute is False  # default: suggest_only
```

### Intent Model

```
UserIntent (frozen dataclass):
  intent_id, inferred_goal, confidence (0–1)
  context_signals (tuple), related_entities (tuple)
  predicted_actions (tuple), source, timestamp, metadata
```

Derived from three heuristic detectors:
1. **Repeated workflows** — task types appearing ≥2 times in recent history
2. **Continuations** — active task types likely needing follow-up
3. **Time patterns** — task types historically executed at current hour

### Predictor Engine

```
Predictor:
  predict_intent(context, now) → List[UserIntent]
  build_context(store, active_tasks, now) → PredictionContext

Detection rules:
  - Repeated: confidence = 0.65 + 0.05 * (count - 2), capped at 1.0
  - Continuation: confidence = 0.7, +0.1 if has prior execution history
  - Time pattern: confidence = 0.6 if ≥2 occurrences at same hour (±1)
```

### Predictive Planner

```
PredictivePlanner:
  predict_plan(intent) → PredictedPlan | None
  predict_plans(intents) → List[PredictedPlan]

Output: PredictedPlan
  - wraps real PlanObjective + ExecutionPlan
  - speculative=True always
  - policy gate controls execution permission
```

### Prediction Policy (Governance)

| Policy | Auto-Execute? | Condition |
|--------|--------------|-----------|
| `DISABLED` | Never | No predictions generated |
| `SUGGEST_ONLY` (default) | Never | Predictions cached, never acted on |
| `AUTO_EXECUTE_LOW_RISK` | Conditional | Only if confidence ≥ 0.8 |
| `REQUIRE_APPROVAL` | Conditional | Only if explicitly approved |

### Advisor Integration

AdvisorRuntime now accepts optional `predictor` and `predictive_planner`.
On each tick:
1. Normal signal processing (unchanged)
2. Cell cleanup (unchanged)
3. Prediction pass: generate intents → generate plans → cache

Predictions are surfaced via `advisor.pending_predictions` but never
auto-executed. The advisor stores them for the caller to inspect.

### Loop Integration

RuntimeLoop.tick() now accepts optional `prediction_context` which
flows through to the advisor's prediction pass. Prediction is
non-blocking — errors in the prediction pass are caught and logged,
never crashing the loop.

---

## Deterministic Design

1. **Same context → same intents**: `predict_intent()` is a pure function.
   No randomness (intent IDs are generated fresh but goals/confidence are
   deterministic). Intents are sorted by (-confidence, intent_id).

2. **Same intent → same plan structure**: `predict_plan()` produces
   identical plan structure for the same intent (plan_id differs but
   objective title, steps, and flags are identical).

3. **Predictions are isolated**: They never affect running jobs,
   feedback stores, or scheduler weights.

4. **Predictions are discardable**: `discard_plan()`, `clear_cache()`,
   `clear_predictions()`, and `clear()` all remove prediction state.

---

## Hard Invariants

| # | Invariant | Verified |
|---|-----------|----------|
| 1–34 | All prior phase invariants | YES — 646 prior tests pass |
| 35 | Predictions NEVER auto-execute without governance | YES — TestPredictionPolicy (4 tests) |
| 36 | Predictive plans clearly marked speculative | YES — TestBoundaryInvariants.test_predicted_plan_always_speculative |
| 37 | Predictions do NOT mutate system state | YES — test_predictions_do_not_mutate_feedback_store |
| 38 | Predictive outputs are discardable | YES — TestDiscardability (2 tests) |
| 39 | No hallucinated memory writes | YES — test_no_hallucinated_memory_writes |

---

## Test Coverage Summary

| Category | Count | Description |
|----------|-------|-------------|
| Intent model | 7 | creation, immutability, validation, timestamp, serialization, IDs, edge values |
| Prediction context | 3 | creation, immutability, serialization |
| Predictor engine | 11 | defaults, validation, empty context, repeated workflows, confidence scaling, continuations, continuation confidence, time patterns, threshold filtering, max predictions, context builder, determinism |
| Predictive planner | 14 | valid objective, speculative flag, steps, draft status, dry_run, disabled policy, multiple plans, cache, eviction, discard, clear, serialization, set_policy, state, no-action fallback |
| Prediction policy | 4 | suggest_only, disabled, require_approval, auto_execute_low_risk |
| Advisor integration | 5 | without predictor, with predictor, not auto-executed, clear predictions, state |
| Loop integration | 2 | with prediction context, without prediction context |
| Determinism | 2 | same context → same intents, same intent → same plan |
| Discardability | 2 | individual discard, clear all |
| Boundary invariants | 8 | no cells import (×3), no environments import (×3), no subprocess (×3), no shell=True (×3), speculative marking, no store mutation, no memory writes |
| Regression | 4 | advisor unchanged, loop unchanged, planning models, learning feedback |
| **Total** | **71** | |

---

## Regression

Full suite: 717 tests across phases 11B–20. Zero failures.

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
| **Total** | **717** | **PASS** |

---

## Known Limitations

- Heuristic prediction only (no ML, no neural models)
- No long-term behavioral modeling (only recent feedback window)
- No cross-session deep intent memory
- No multi-user pattern sharing
- Intent deduplication by goal name only (not semantic)
- Time pattern detection limited to ±1 hour window
- No prediction accuracy tracking (no feedback loop on predictions)
- No prediction persistence (in-memory only — lost on restart)
- Confidence scores are additive heuristics, not probabilistic

---

## Files Created/Modified

| File | Action |
|------|--------|
| `umh/prediction/__init__.py` | CREATED — package init with exports |
| `umh/prediction/intent.py` | CREATED — UserIntent + make_intent_id |
| `umh/prediction/predictor.py` | CREATED — Predictor + PredictionContext |
| `umh/prediction/planner.py` | CREATED — PredictedPlan + PredictionPolicy + PredictivePlanner |
| `umh/runtime/advisor.py` | MODIFIED — prediction integration (predictor, planner, pending_predictions) |
| `umh/runtime/loop.py` | MODIFIED — prediction_context pass-through on tick() |
| `umh/runtime/__init__.py` | MODIFIED — updated docstring |
| `tests/unit/test_phase20_prediction.py` | CREATED — 71 tests |
| `docs/audits/phase20_prediction_report.md` | CREATED — this file |

---

## Is Phase 21 Safe?

YES. Phase 20 is fully backward compatible:
- `AdvisorRuntime()` without predictor/planner works identically to Phase 19
- `RuntimeLoop.tick()` without prediction_context works identically to Phase 19
- `tick()` returns `predictions_generated: 0` when no predictor configured
- New `umh/prediction/` package is additive — no existing modules broken
- All Phase 19 tests pass unchanged
- Prediction never writes to FeedbackStore, JobStore, or SchedulerWeights
