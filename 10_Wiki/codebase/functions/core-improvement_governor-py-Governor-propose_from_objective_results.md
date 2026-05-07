---
type: codebase-function
file: core/improvement_governor.py
line: 201
generated: 2026-05-07
---

# Governor.propose_from_objective_results

**File:** [[core-improvement_governor-py]] | **Line:** 201
**Signature:** `propose_from_objective_results(objective_results, aggregate_score) → list[ImprovementProposal]`

**Class:** [[core-improvement_governor-py-Governor]]

Generate proposals based on multi-objective evaluation results.

Analyses which objectives failed and proposes weight/threshold adjustments.

## Calls

- [[core-improvement_governor-py-Governor-propose]]
