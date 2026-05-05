# Phase 36 — Goal Hierarchies + Abstraction Layer v1

## Audit Report

**Date:** 2026-04-30
**Phase:** 36 of UMH runtime build
**Status:** COMPLETE

---

## What was built

### New file
- `umh/runtime/goal_hierarchy.py` — MetaGoal, MetaGoalScore, HierarchyInfluence, CycleError, GoalHierarchy, HierarchyScorer

### Modified files
- `umh/runtime/goal_memory.py` — type-to-meta mappings, query_by_meta_goal, compute_grouped_stats
- `umh/runtime/meta_planner.py` — hierarchy_scorer integration in SequenceEvaluator and MetaPlanner
- `umh/runtime/__init__.py` — 6 new exports (CycleError, GoalHierarchy, HierarchyInfluence, HierarchyScorer, MetaGoal, MetaGoalScore)

### Test file
- `tests/unit/test_phase36_goal_hierarchy.py` — 124 tests across 16 sections

---

## Architecture

### Data flow
```
GoalMemory (records) → ReinforcementScorer (per-type signals)
  → GoalHierarchy.compute_meta_score (weighted average)
  → HierarchyScorer.compute_factor (multiplicative factor [0.9, 1.1])
  → SequenceEvaluator.score_sequence (combined *= factor)
  → MetaPlanner._build_reason (explainability)
```

### Scoring chain (4 multipliers)
```
total = base × identity_factor[0.80,1.20] × goal_bias_factor[0.85,1.15] × meta_goal_factor[0.90,1.10]
```

Compound range: 0.612 – 1.518

### Key formulas
- `meta_score = Σ(child_reinforcement_i) / count`, clamped [0.5, 1.5]
- `factor = clamp(1.0 + (meta_score - 1.0) × meta_weight, 0.9, 1.1)`
- `reinforcement = success_rate × identity_alignment × duration_factor`, clamped [0.5, 1.0]

### Important design property
Since reinforcement components cap at 1.0, the hierarchy factor can only produce penalties (factor < 1.0) or neutral (factor = 1.0), never boosts. This is intentional — hierarchy is the most abstract signal and should be conservative.

---

## Cycle detection

DFS-based graph reachability validated at registration time.
Prevents: self-references, direct cycles (A→B, B→A), transitive cycles (A→B→C→A).
Allows: diamond patterns (A→X, B→X), shared children, independent subgraphs.

---

## Hard invariants

| ID | Invariant | Status |
|----|-----------|--------|
| 116 | GoalHierarchy read-only during execution | PASS |
| 117 | No child mutation from parent operations | PASS |
| 118 | Aggregation is deterministic (same in → same out) | PASS |
| 119 | No circular dependencies in hierarchy | PASS |
| 120 | Hierarchy factor does not override direct scores | PASS |

---

## Test results

- **Phase 36 tests:** 124 passed, 0 failed
- **Full regression (phases 11-36):** 2229 passed, 0 failed
- **Test growth:** +124 (from 2105 to 2229)

---

## Dependency boundary

`goal_hierarchy.py` imports only:
- `__future__.annotations`
- `dataclasses` (dataclass, field)
- `typing` (TYPE_CHECKING, Any)
- `umh.runtime.goal_memory` (TYPE_CHECKING only)
- `umh.runtime.goals` (TYPE_CHECKING only)

No imports from `umh/cells`, `umh/environments`, `umh/adapters`.

---

## Files verified

```
py_compile: goal_hierarchy.py ✓
py_compile: goal_memory.py ✓
py_compile: meta_planner.py ✓
py_compile: __init__.py ✓
ruff format: all files ✓
```
