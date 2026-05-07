---
type: codebase-function
file: eos_ai/goal_selector.py
line: 422
generated: 2026-05-07
---

# StrategicHorizonLayer.compute_horizon_adjustment

**File:** [[eos_ai-goal_selector-py]] | **Line:** 422
**Signature:** `compute_horizon_adjustment(goal) → float`

**Class:** [[eos_ai-goal_selector-py-StrategicHorizonLayer]]

Compute multi-horizon performance adjustment for a single goal.

Replaces the single-decay performance_adjustment from 9E.
Returns the total adjustment and mutates goal.horizon_adjustments,
goal.stability_bonus, and goal.performance_adjustment.
...

## Calls

- [[eos_ai-goal_selector-py-MultiHorizonProfile-composites]]
- [[eos_ai-goal_selector-py-MultiHorizonProfile-has_outcomes]]
- [[eos_ai-goal_selector-py-StrategicHorizonLayer-_compute_stability_bonus]]

## Called By

- [[eos_ai-goal_selector-py-GoalSelector-score_goal]]
