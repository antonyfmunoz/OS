---
type: codebase-function
file: core/objective_engine.py
line: 164
generated: 2026-05-07
---

# ObjectiveSet.aggregate_score

**File:** [[core-objective_engine-py]] | **Line:** 164
**Signature:** `aggregate_score() → float`

**Class:** [[core-objective_engine-py-ObjectiveSet]]

Weighted aggregate score across all objectives.

Returns 0.0 if any hard constraint is violated.

## Called By

- [[core-objective_engine-py-ObjectiveSet-ok]]
- [[core-objective_engine-py-ObjectiveSet-to_dict]]
