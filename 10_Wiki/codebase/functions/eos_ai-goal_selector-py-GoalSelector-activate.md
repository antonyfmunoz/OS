---
type: codebase-function
file: eos_ai/goal_selector.py
line: 750
generated: 2026-05-07
---

# GoalSelector.activate

**File:** [[eos_ai-goal_selector-py]] | **Line:** 750
**Signature:** `activate(goal_id) → Goal`

**Class:** [[eos_ai-goal_selector-py-GoalSelector]]

Force a goal to ACTIVE (manual override). Bumps lowest-ranked active goal if at budget.

## Calls

- [[eos_ai-goal_selector-py-GoalSelector-_emit_event]]
- [[eos_ai-goal_selector-py-GoalSelector-_find_goal]]
- [[eos_ai-goal_selector-py-GoalSelector-_persist_goal]]
- [[eos_ai-goal_selector-py-GoalSelector-load_goals]]

## Called By

- [[scripts-goals-py-cmd_goal_activate]]
- [[services-goal_api-py-activate_goal]]
