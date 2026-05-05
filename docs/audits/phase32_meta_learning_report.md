# Phase 32: Dependency-Aware Meta Planning + Sequence Learning v1 — Audit Report

**Date**: 2026-04-30
**Status**: COMPLETE
**Tests**: 116 passed, 0 failed
**Regression**: 1778 passed (phases 11-32), 0 regressions

---

## Deliverables

### New Modules (2)

| File | Purpose | Lines |
|------|---------|-------|
| `umh/runtime/dependency.py` | DependencyType enum, ObjectiveDependency dataclass, DependencyGraph class | ~142 |
| `umh/runtime/sequence_memory.py` | ContextSignature, SequenceRecord, make_sequence_record, SequenceMemory class | ~215 |

### Modified Modules (3)

| File | Changes |
|------|---------|
| `umh/runtime/meta_planner.py` | Added TYPE_CHECKING imports for DependencyGraph/SequenceMemory; SequenceGenerator gains `dependency_graph` param with dependency-aligned sorting; SequenceEvaluator gains `dependency_graph`, `sequence_memory`, `enable_learning`, `dep_weight` params with dependency bonus and learning adjustment; MetaPlanner gains `dependency_graph`, `sequence_memory` params; `_build_reason()` includes dependency alignment and historical success rate |
| `umh/runtime/advisor.py` | Added `dependency_graph` and `sequence_memory` constructor params, properties, `get_state()` entries (dependency_edges, sequence_memory_count), `clear()` resets for both |
| `umh/runtime/__init__.py` | Added 7 new exports (DependencyGraph, DependencyType, ObjectiveDependency, ContextSignature, SequenceMemory, SequenceRecord, make_sequence_record) |

### Test File (1)

| File | Tests |
|------|-------|
| `tests/unit/test_phase32_meta_learning.py` | 116 |

---

## Architecture

```
DependencyGraph (directed edges between objectives)
        │
        │  ENABLES (+strength)
        │  BOOSTS  (+strength)
        │  BLOCKS  (-strength)
        │
        ▼
SequenceGenerator.generate(objectives, depth)
        │
        ▼  Top-K filtering → permutations → cap
        │  Sort by dependency alignment (if graph provided)
        │
        ▼
SequenceEvaluator.score_sequence(sequence)
        │
        ▼  Base score: Σ(obj_score × γ^i) weighted with effort
        │  + dep_weight × sequence_dependency_score (if graph)
        │  × adjustment_factor (if learning enabled + memory)
        │
        ▼
MetaPlanner.plan() → MetaPlanResult
        │
        ▼
selected.first_objective → next_objective (commit point)


SequenceMemory (append-only)
        │
        ▼  Records: predicted vs. actual scores
        │  Queries: exact, prefix, contains
        │  Metrics: success_rate, avg_delta, recency_weighted_delta
        │  Output: adjustment_factor ∈ [0.5, 1.5]
```

---

## Dependency Model

### DependencyType

| Type | Score Sign | Meaning |
|------|-----------|---------|
| ENABLES | +strength | Parent must complete before child can start |
| BOOSTS | +strength | Parent completion improves child outcome |
| BLOCKS | -strength | Parent blocks child progress |

### Sequence Dependency Score

```
score = Σ dependency_score(seq[i], seq[i+1])  for i in 0..n-2
```

Consecutive pair scoring — a sequence [A→B→C] scores the sum of dependency(A,B) + dependency(B,C). Higher scores indicate better dependency alignment.

### Dependency Bonus in Scoring

```
combined += dep_weight × sequence_dependency_score(ids)
```

| Parameter | Default | Range | Purpose |
|-----------|---------|-------|---------|
| dep_weight | 0.15 | [0.0, 0.5] | Controls how much dependency alignment influences scoring |

---

## Learning Model

### Sequence Memory

Append-only store of `SequenceRecord` entries. Each record captures:
- `objective_ids` — the sequence executed
- `predicted_score` — what the meta-planner predicted
- `actual_score` — what actually happened
- `delta` — actual - predicted (positive = outperformed)
- `context_signature` — optional hash-based context grouping

### Recency-Weighted Delta

```
weight_i = decay^(n - 1 - i)    (default decay = 0.9)
weighted_delta = Σ(delta_i × weight_i) / Σ(weight_i)
```

### Adjustment Factor

```
adjustment = 1.0 + (success_rate - 0.5) × 0.5 + avg_delta × 0.3
clamped to [0.5, 1.5]
```

| Input | Effect |
|-------|--------|
| success_rate > 0.5 | Boosts score (historically reliable) |
| success_rate < 0.5 | Penalizes score (historically unreliable) |
| avg_delta > 0 | Boosts (outperforms predictions) |
| avg_delta < 0 | Penalizes (underperforms predictions) |
| < 3 records | Returns 1.0 (insufficient data) |

### Opt-in Learning (Invariant 97)

Learning is **disabled by default**. The adjustment factor only applies when:
1. `enable_learning=True` on SequenceEvaluator
2. A SequenceMemory instance is provided
3. At least 3 matching records exist

Without all three conditions, scoring is fully deterministic.

---

## Context Signature

```python
ContextSignature(features=("time:morning", "energy:high"))
# hash_value = SHA-256 of sorted "|"-joined features, truncated to 16 chars
```

Order-independent hashing enables grouping outcomes by planning context without strict equality. Two signatures with the same features in any order produce the same hash.

---

## Hard Invariants

| ID | Invariant | Verified |
|----|-----------|----------|
| 95 | Sequence memory must be append-only | YES — test_inv95_sequence_memory_append_only |
| 96 | No mutation of stored sequence records | YES — test_inv96_no_mutation_of_records |
| 97 | Learning must NOT affect determinism unless explicitly enabled | YES — test_inv97_learning_disabled_deterministic |
| 98 | Dependency graph must be read-only during planning | YES — test_inv98_dependency_graph_read_only_during_planning |
| 99 | No execution state mutation during meta-planning | YES — test_inv99_no_execution_state_mutation |
| 100 | Meta-planning pipeline must be side-effect free | YES — test_inv100_meta_planning_side_effect_free, test_inv100_no_forbidden_module_imports |

---

## Test Breakdown

| Section | Tests | Coverage |
|---------|-------|----------|
| ObjectiveDependency | 7 | Creation, frozen, strength clamped, types, to_dict, equality, defaults |
| DependencyGraph | 22 | Empty, add/get, children, parents, has/get dependency, score (4), sequence score (3), idempotent, edges, clear, to_dict, edge_count, properties |
| ContextSignature | 7 | Creation, hash computed, deterministic, order-independent, frozen, to_dict, custom hash |
| SequenceRecord | 5 | Creation, frozen, to_dict rounds, with context, no context |
| MakeSequenceRecord | 4 | Basic, delta computed, with context, with timestamp |
| SequenceMemory | 22 | Empty, append, query exact/miss, prefix/full, contains/miss, success rate/none, avg delta/none, recency weighted/none, adjustment (5), list_all/copy, clear, to_dict, decay property/clamped |
| DependencyAwareGenerator | 6 | Property, no graph, dependency sorting, block penalized, empty graph, three-way chain |
| MemoryInformedEvaluator | 10 | No memory, learning disabled, learning boosts, learning penalizes, dep bonus, block penalizes, single item no dep, properties, learning disabled default, combined |
| ExtendedMetaPlanner | 5 | Plan with dependencies, plan with memory, reason includes dependency, reason includes history, properties |
| Advisor integration | 8 | Graph property, memory property, no graph, no memory, get_state with graph, get_state with memory, clear resets, tick with dependencies |
| Hard invariants 95-100 | 8 | INV 95-100 (7 tests, 1 double-coverage for INV 100) |
| Boundary/exports | 11 | Imports (3), compile (5), all exports, end-to-end full pipeline, end-to-end advisor |
| **Total** | **116** | |

---

## Decision Hierarchy (Complete)

```
MetaPlanner        → which SEQUENCE of goals (Phase 31)
  + DependencyGraph  → respects goal prerequisites (Phase 32)
  + SequenceMemory   → learns from outcomes (Phase 32)
ArbitrationEngine  → which single GOAL (Phase 30)
TrajectoryPlanner  → which multi-step PATH (Phase 29)
StrategySimulator  → which STRATEGY variant (Phase 26)
ExecutionStrategy  → HOW to execute (Phase 25)
```

---

## Known Limitations

- Dependency graph is in-memory only (no persistence layer yet)
- Sequence memory is in-memory only (no persistence layer yet)
- No cycle detection in dependency graph (caller responsibility)
- No transitive dependency resolution (only direct edges considered)
- Context signature is content-hash only (no semantic similarity)
- Adjustment factor uses simple linear combination (not learned weights)
- No decay/expiry of old sequence records
- No cross-context transfer learning
- Recency weighting assumes chronological append order
- Minimum 3 records threshold is hardcoded

---

## Cumulative Test Count (Phases 11-32)

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
| 31 | 97 | 1662 |
| **32** | **116** | **1778** |
