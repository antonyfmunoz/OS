---
type: codebase-function
file: eos_ai/goal_selector.py
line: 976
generated: 2026-05-07
---

# GoalSelector.load_goals

**File:** [[eos_ai-goal_selector-py]] | **Line:** 976
**Signature:** `load_goals() → list[Goal]`

**Class:** [[eos_ai-goal_selector-py-GoalSelector]]

Load all goals from Neon for this org.

## Calls

- [[eos_ai-db-py-get_conn]]
- [[eos_ai-goal_selector-py-MultiHorizonProfile-from_dict]]
- [[eos_ai-goal_selector-py-PerformanceProfile-from_dict]]

## Called By

- [[eos_ai-goal_selector-py-GoalSelector-activate]]
- [[eos_ai-goal_selector-py-GoalSelector-block]]
- [[eos_ai-goal_selector-py-GoalSelector-complete]]
- [[eos_ai-goal_selector-py-GoalSelector-defer]]
- [[eos_ai-goal_selector-py-GoalSelector-drop]]
- [[eos_ai-goal_selector-py-GoalSelector-get_goal]]
- [[eos_ai-goal_selector-py-GoalSelector-is_active]]
- [[eos_ai-goal_selector-py-GoalSelector-list_goals]]
- [[eos_ai-goal_selector-py-GoalSelector-run_selection_cycle]]
- [[scripts-goals-py-cmd_goal_explain]]
- [[services-goal_api-py-get_goal]]
