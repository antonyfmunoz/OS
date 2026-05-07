---
type: codebase-class
file: core/objective_engine.py
line: 123
generated: 2026-05-07
---

# ObjectiveSet

**File:** [[core-objective_engine-py]] | **Line:** 123

A set of objectives evaluated together with weighted aggregation.

Hard constraints override the weighted score: if any hard constraint
fails, the entire run is marked failed regardless of weighted score.

## Methods

- [[core-objective_engine-py-ObjectiveSet-evaluate]]`(real_data) → list[ObjectiveResult]` — Evaluate all objectives against real data.
- [[core-objective_engine-py-ObjectiveSet-aggregate_score]]`() → float` — Weighted aggregate score across all objectives.
- [[core-objective_engine-py-ObjectiveSet-constraint_violations]]`() → list[ObjectiveResult]` — Return all hard constraints that were violated.
- [[core-objective_engine-py-ObjectiveSet-explain_tradeoffs]]`() → list[dict[str, Any]]` — Explain tradeoffs between objectives.
- [[core-objective_engine-py-ObjectiveSet-ok]]`() → bool` — True if aggregate score > 0 (no hard constraint violations)
- [[core-objective_engine-py-ObjectiveSet-to_dict]]`() → dict[str, Any]` — 

## Decorators

- `@dataclass`
