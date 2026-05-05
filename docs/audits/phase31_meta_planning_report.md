# Phase 31: Goal Sequencing + Meta-Planning Layer v1 — Audit Report

**Date**: 2026-04-30
**Status**: COMPLETE
**Tests**: 97 passed, 0 failed
**Regression**: 1662 passed (phases 11-31), 0 regressions

---

## Deliverables

### New Modules (1)

| File | Purpose | Lines |
|------|---------|-------|
| `umh/runtime/meta_planner.py` | SequenceStep, ObjectiveSequence, MetaPlanResult, MetaPlanWeights, SequenceGenerator, SequenceEvaluator, MetaPlanner | ~310 |

### Modified Modules (2)

| File | Changes |
|------|---------|
| `umh/runtime/advisor.py` | Added `meta_planner` constructor param, `_last_meta_plan` field, `meta_planner`/`last_meta_plan` properties, `_meta_plan_objectives()` method in tick, `meta_plan_selected` tick key, meta_plan in `get_state()`, reset in `clear()` |
| `umh/runtime/__init__.py` | Added 7 new exports (MetaPlanResult, MetaPlanWeights, MetaPlanner, ObjectiveSequence, SequenceEvaluator, SequenceGenerator, SequenceStep) |

### Test File (1)

| File | Tests |
|------|-------|
| `tests/unit/test_phase31_meta_planning.py` | 97 |

---

## Architecture

```
Objectives (pool of goals)
        │
        ▼
SequenceGenerator.generate(objectives, depth)
        │
        ▼  Top-K filtering by single-step score
        │  Permutations of length min(depth, K)
        │  Capped at MAX_SEQUENCES (30)
        │
        ▼
[[A,B,C], [A,C,B], [B,A,C], ...]
        │
        ▼
SequenceEvaluator.score_sequence(sequence)
        │
        ▼  For each step i:
        │    discounted_score = obj_score × discount^i
        │    total += discounted_score
        │    effort += obj.effort_estimate
        │  combined = w_score × total + w_effort × 1/(1+effort)
        │
        ▼
ObjectiveSequence (steps, total_score, cumulative_effort)
        │
        ▼
SequenceEvaluator.rank(sequences)
        │
        ▼
MetaPlanner.plan() → MetaPlanResult
        │
        ▼
selected.first_objective → next_objective (commit point)
```

---

## Scoring Model

### Temporal Discounting

| Step | Discount (γ=0.85) | Effect |
|------|-------------------|--------|
| 0 | 1.0000 | Full weight |
| 1 | 0.8500 | 85% weight |
| 2 | 0.7225 | 72% weight |
| 3 | 0.6141 | 61% weight |

### Combined Score

```
score = w_score × Σ(obj_score_i × γ^i) + w_effort × 1/(1+Σ effort)
```

| Component | Default Weight | Direction |
|-----------|---------------|-----------|
| Score (discounted) | 0.70 | Higher = better |
| Effort (inverse) | 0.30 | Lower = better |

### Pruning Strategy

| Parameter | Value | Purpose |
|-----------|-------|---------|
| Min depth | 2 | Minimum planning horizon |
| Max depth | 4 | Maximum planning horizon |
| Default depth | 3 | Standard planning horizon |
| Min top K | 2 | Minimum objectives considered |
| Max top K | 6 | Maximum objectives considered |
| Default top K | 3 | Standard pruning level |
| Max sequences | 30 | Absolute cap on candidates |

### Combinatorial Control

| K | Depth | P(K,depth) | After cap |
|---|-------|------------|-----------|
| 3 | 2 | 6 | 6 |
| 3 | 3 | 6 | 6 |
| 4 | 3 | 24 | 24 |
| 5 | 4 | 120 | 30 |
| 6 | 4 | 360 | 30 |

---

## Key Design Principle

**Plan the horizon, act on step one.** The meta-planner evaluates full multi-objective sequences but only exposes `next_objective` as the commit point. This gives the system look-ahead ability (preferring sequences where early objectives set up later ones) without binding future decisions.

---

## Decision Hierarchy (Complete)

```
MetaPlanner     → which SEQUENCE of goals (Phase 31)
ArbitrationEngine → which single GOAL (Phase 30)
TrajectoryPlanner → which multi-step PATH (Phase 29)
StrategySimulator → which STRATEGY variant (Phase 26)
ExecutionStrategy → HOW to execute (Phase 25)
```

---

## Labeling System

| First Objective Priority | Follower Avg Priority | Label Example |
|--------------------------|----------------------|---------------|
| ≥ 8 | ≥ 7 | high-priority-lead-strong-follow-0 |
| ≥ 8 | ≥ 4 | high-priority-lead-balanced-follow-1 |
| ≥ 5 | < 4 | moderate-lead-easy-follow-2 |
| < 5 | — | low-priority-lead-...-3 |

---

## Hard Invariants

| ID | Invariant | Verified |
|----|-----------|----------|
| 90 | Meta-planning must be read-only (no execution state mutation) | YES — test_inv90_meta_planning_read_only, test_inv90_no_io_in_meta_planner |
| 91 | Only NEXT objective may be committed | YES — test_inv91_only_next_objective_committed |
| 92 | Sequence evaluation must be deterministic | YES — test_inv92_deterministic |
| 93 | No exponential explosion (bounded search) | YES — test_inv93_bounded_search, test_inv93_top_k_limits_branching |
| 94 | No direct execution during planning | YES — test_inv94_no_execution_during_planning |

---

## Test Breakdown

| Section | Tests | Coverage |
|---------|-------|----------|
| SequenceStep | 3 | Creation, frozen, to_dict |
| ObjectiveSequence | 7 | Creation, frozen, depth, first_objective, objectives, to_dict, rounding |
| MetaPlanResult | 6 | Creation, frozen, to_dict, explanation, markers, arrow chains |
| MetaPlanWeights | 4 | Defaults, custom, frozen, to_dict |
| SequenceGenerator | 20 | Basic, empty, single, two, depth (3), top K (2), max sequences, deterministic, no dupes, labels (5), properties, clamping (3) |
| SequenceEvaluator | 16 | Basic, empty, discount (5), discounted score, effort, future value, clamping (2), rank (2), deterministic, weights, zero weights, custom evaluator |
| MetaPlanner | 14 | Basic, empty, single, two, best selection, next = first, deterministic, reason, explanation, all scored, to_dict, bounded, properties, depth, narrow margin |
| Advisor integration | 12 | Properties (3), tick keys (2), runs plan, no planner, no objectives, single objective, get_state (2), clear |
| Hard invariants | 7 | INV 90-94 |
| Boundary/exports | 8 | Imports (2), compile (3), exports, end-to-end (2) |
| **Total** | **97** | |

---

## Known Limitations

- Shallow horizon only (2-4 steps)
- No stochastic modeling — same inputs always same result
- No dynamic reweighting across time
- No cross-sequence learning
- No dependency graph between objectives (treats all as independent)
- No resource contention modeling (objectives share effort budget)
- Discount factor is static (not adaptive)
- No partial completion — objectives are all-or-nothing
- Labeling is heuristic (priority-based, not content-aware)
- Single objective produces a degenerate depth-1 plan (valid but trivial)

---

## Cumulative Test Count (Phases 11-31)

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
| 28 | 92 | 1372 |
| 29 | 94 | 1466 |
| 30 | 99 | 1565 |
| **31** | **97** | **1662** |
