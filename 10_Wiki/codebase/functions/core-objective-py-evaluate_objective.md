---
type: codebase-function
file: core/objective.py
line: 169
generated: 2026-05-07
---

# evaluate_objective

**File:** [[core-objective-py]] | **Line:** 169
**Signature:** `evaluate_objective(result, real_data, objective) → ObjectiveScore`

Evaluate a pipeline result against a real-world objective.

This is the override mechanism: the objective score replaces the
pipeline's internal self-assessment when they disagree.

...

## Calls

- [[core-objective-py-Objective-evaluate]]
