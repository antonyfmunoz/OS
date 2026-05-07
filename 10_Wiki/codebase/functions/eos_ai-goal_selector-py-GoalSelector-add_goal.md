---
type: codebase-function
file: eos_ai/goal_selector.py
line: 832
generated: 2026-05-07
---

# GoalSelector.add_goal

**File:** [[eos_ai-goal_selector-py]] | **Line:** 832
**Signature:** `add_goal(title, description, priority, expected_impact, estimated_cost, confidence, venture_id, blocked_by) → Goal`

**Class:** [[eos_ai-goal_selector-py-GoalSelector]]

Create a new goal. Starts as DEFERRED — selection cycle activates it.

## Calls

- [[eos_ai-goal_selector-py-GoalSelector-_persist_goal]]

## Called By

- [[scripts-goals-py-cmd_goal_add]]
- [[services-goal_api-py-create_goal]]
