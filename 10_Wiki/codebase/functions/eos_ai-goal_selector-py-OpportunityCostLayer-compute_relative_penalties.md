---
type: codebase-function
file: eos_ai/goal_selector.py
line: 289
generated: 2026-05-07
---

# OpportunityCostLayer.compute_relative_penalties

**File:** [[eos_ai-goal_selector-py]] | **Line:** 289
**Signature:** `compute_relative_penalties(goals, focus_budget) → list[Goal]`

**Class:** [[eos_ai-goal_selector-py-OpportunityCostLayer]]

For each active goal, compare its performance composite against
the mean performance of deferred goals. Penalize if below average.

Mutates goal.opportunity_cost_adjustment and appends to score_explanation.

## Calls

- [[eos_ai-goal_selector-py-PerformanceProfile-composite]]

## Called By

- [[eos_ai-goal_selector-py-GoalSelector-run_selection_cycle]]
