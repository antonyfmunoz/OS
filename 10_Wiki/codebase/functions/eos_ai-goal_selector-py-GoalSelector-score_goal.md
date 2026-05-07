---
type: codebase-function
file: eos_ai/goal_selector.py
line: 553
generated: 2026-05-07
---

# GoalSelector.score_goal

**File:** [[eos_ai-goal_selector-py]] | **Line:** 553
**Signature:** `score_goal(goal, all_goals) → Goal`

**Class:** [[eos_ai-goal_selector-py-GoalSelector]]

Compute weighted score for a single goal.
Mutates goal.score, goal.base_score, goal.performance_adjustment,
and goal.score_explanation in place.

## Calls

- [[eos_ai-goal_selector-py-GoalSelector-_count_unlocks]]
- [[eos_ai-goal_selector-py-StrategicHorizonLayer-build_explanation]]
- [[eos_ai-goal_selector-py-StrategicHorizonLayer-compute_horizon_adjustment]]

## Called By

- [[eos_ai-goal_selector-py-GoalSelector-run_selection_cycle]]
- [[scripts-goals-py-cmd_goal_explain]]
- [[services-goal_api-py-get_goal]]
