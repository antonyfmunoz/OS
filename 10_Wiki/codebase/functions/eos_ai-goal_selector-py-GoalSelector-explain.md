---
type: codebase-function
file: eos_ai/goal_selector.py
line: 717
generated: 2026-05-07
---

# GoalSelector.explain

**File:** [[eos_ai-goal_selector-py]] | **Line:** 717
**Signature:** `explain(goal, all_goals) → dict`

**Class:** [[eos_ai-goal_selector-py-GoalSelector]]

Return explainability payload for a single goal.

## Calls

- [[eos_ai-goal_selector-py-MultiHorizonProfile-to_dict]]
- [[eos_ai-goal_selector-py-OpportunityCostLayer-explain_goal]]
- [[eos_ai-goal_selector-py-PerformanceProfile-to_dict]]
- [[eos_ai-goal_selector-py-StrategicHorizonLayer-explain_goal]]

## Called By

- [[scripts-goals-py-cmd_goal_explain]]
- [[services-goal_api-py-get_goal]]
