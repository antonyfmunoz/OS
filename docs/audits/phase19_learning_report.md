# Phase 19 Audit Report — Adaptive Scheduling + Feedback Learning v1

**Date:** 2026-04-29
**Status:** PASS — all invariants verified
**Tests:** 51/51 passed | Regression: 646/646 passed (phases 11B–19, zero regressions)

---

## Deliverables

| # | Deliverable | File | Status |
|---|-------------|------|--------|
| 1 | `ExecutionFeedback` + `FeedbackStore` | `umh/learning/feedback.py` | DONE |
| 2 | `NodeMetrics` + `JobTypeMetrics` + `MetricsAggregator` | `umh/learning/metrics.py` | DONE |
| 3 | `SchedulerWeights` + `WeightAdapter` | `umh/learning/weights.py` | DONE |
| 4 | `adaptive_score()` + planner integration | `umh/runtime/planner.py` | DONE |
| 5 | `umh/learning/__init__.py` | `umh/learning/__init__.py` | DONE |
| 6 | `umh/runtime/__init__.py` exports | `umh/runtime/__init__.py` | DONE |
| 7 | Test suite | `tests/unit/test_phase19_learning.py` | DONE — 51 tests |

---

## Architecture

### Feedback Loop

```
Job completes
  → ExecutionFeedback recorded to FeedbackStore
    → MetricsAggregator computes NodeMetrics / JobTypeMetrics
      → WeightAdapter adjusts SchedulerWeights
        → adaptive_score() uses weights as explicit input
          → Future scheduling decisions reflect learned performance
```

### Key Design Principle: Weights as Explicit Input

The scheduler remains a **pure function**. Learning state (weights) is
passed as an explicit parameter — never as global mutable state. This
preserves determinism: same jobs + same weights = same decision.

```python
# Phase 18 (no learning):
score = score_job(job, node, now=ref)

# Phase 19 (with learning):
score = adaptive_score(job, node, weights=learned_weights, now=ref)

# Without weights, falls through to base score_job()
score = adaptive_score(job, node, now=ref)  # identical to score_job()
```

### Feedback Model

```
ExecutionFeedback (frozen dataclass):
  job_id, node_id, task_type
  success (bool), duration_ms (int), retries (int)
  resource_usage (dict), timestamp, metadata
```

Recorded AFTER job completion. Immutable once created. FeedbackStore
maintains insertion order and indexes by node_id and task_type.

### Metrics Aggregation

```
NodeMetrics:                    JobTypeMetrics:
  total_jobs                      total_jobs
  successful_jobs                 successful_jobs
  failed_jobs                     failed_jobs
  avg_duration_ms                 avg_duration_ms
  success_rate                    failure_rate
  retry_rate                      avg_retries
  avg_retries
```

Computed on-demand from FeedbackStore. Stateless — recomputed every call.

### Weight Adaptation Rules

| Condition | Action | Threshold |
|-----------|--------|-----------|
| Node success rate >= 90% | Bonus +3.0 | min 3 samples |
| Node success rate < 50% | Penalty +5.0 | min 3 samples |
| Node avg duration > 5000ms | Penalty +2.5 | min 3 samples |
| Node avg duration < 500ms | Bonus +1.5 | min 3 samples |

Caps: max bonus = 30.0, max penalty = 50.0.
Minimum 3 samples required before any adjustment (prevents noise).

### Adaptive Score Formula

```
score = (priority_weight * w.priority_weight)
      + (wait_bonus * w.wait_time_weight)
      + urgency_bonus
      + (node_fit * w.node_fit_weight)
      - (cost_penalty * w.cost_weight)
      + node_adjustment(bonus - penalty)
```

---

## Deterministic Learning Design

1. **Same feedback store → same weights**: `compute_fresh()` starts
   from default weights and applies adaptation deterministically.
   Node iteration is sorted by node_id for determinism.

2. **Same weights → same score**: `adaptive_score()` is a pure function.
   No randomness, no time-dependent behavior (time injected via `now`).

3. **Learning is isolated**: Weights only affect future decisions.
   Currently running jobs are unaffected. Past job records are never mutated.

4. **Learning is reversible**: `weights.reset()` returns to defaults.
   `compute_fresh()` recomputes from scratch.

---

## Hard Invariants

| # | Invariant | Verified |
|---|-----------|----------|
| 1–29 | All prior phase invariants | YES — 595 prior tests pass |
| 30 | Learning does not introduce nondeterministic execution | YES — TestDeterminism (3 tests) |
| 31 | Feedback recorded AFTER execution completes | YES — test_feedback_recorded_after_completion |
| 32 | Scheduler remains pure (weights are input, not global) | YES — test_scheduler_remains_pure_with_weights |
| 33 | No mutation of past job records | YES — test_feedback_does_not_mutate_past_jobs |
| 34 | Learning is reversible/resettable | YES — test_learning_is_reversible |

---

## Test Coverage Summary

| Category | Count | Description |
|----------|-------|-------------|
| Feedback model | 8 | creation, immutability, store, indexing, eviction |
| Metrics | 6 | node metrics, job type metrics, aggregator, defaults |
| Weights | 10 | defaults, reset, adaptation, determinism, caps |
| Adaptive scoring | 4 | base fallback, node bonus/penalty, determinism |
| Planner integration | 3 | weights preference, backward compat, candidates |
| Feedback loop | 5 | end-to-end, faster node, failing node, immutability, reversibility |
| Determinism | 3 | weights, scoring, ranker |
| Boundary invariants | 8 | no cells/environments/subprocess imports, purity |
| Regression | 4 | ranker, planner, claim_job, base scoring |
| **Total** | **51** | |

---

## Regression

Full suite: 646 tests across phases 11B–19. Zero failures.

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
| **Total** | **646** | **PASS** |

---

## Known Limitations

- Simple heuristics (threshold-based), not ML
- No long-term memory compression (feedback store is bounded but not summarized)
- No cross-user learning (single-instance only)
- No predictive modeling (reactive adjustment only)
- Weight adaptation is additive (multiple calls to adapt() stack, not converge)
- No feedback persistence (in-memory only — lost on restart)
- No time-decay on feedback (old feedback has same weight as recent)

---

## Files Created/Modified

| File | Action |
|------|--------|
| `umh/learning/__init__.py` | CREATED — package init with exports |
| `umh/learning/feedback.py` | CREATED — ExecutionFeedback + FeedbackStore |
| `umh/learning/metrics.py` | CREATED — NodeMetrics + JobTypeMetrics + MetricsAggregator |
| `umh/learning/weights.py` | CREATED — SchedulerWeights + WeightAdapter |
| `umh/runtime/planner.py` | MODIFIED — added adaptive_score(), weights support |
| `umh/runtime/__init__.py` | MODIFIED — added adaptive_score export |
| `tests/unit/test_phase19_learning.py` | CREATED — 51 tests |
| `docs/audits/phase19_learning_report.md` | CREATED — this file |

---

## Is Phase 20 Safe?

YES. Phase 19 is fully backward compatible:
- `make_ranker()` weights parameter is optional (default None)
- `adaptive_score()` without weights delegates to `score_job()` exactly
- `plan_next()` and `score_candidates()` weights parameter is optional
- All Phase 18 tests pass unchanged
- New `umh/learning/` package is additive — no existing modules touched
