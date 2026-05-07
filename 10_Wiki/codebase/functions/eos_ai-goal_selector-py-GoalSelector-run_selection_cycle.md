---
type: codebase-function
file: eos_ai/goal_selector.py
line: 637
generated: 2026-05-07
---

# GoalSelector.run_selection_cycle

**File:** [[eos_ai-goal_selector-py]] | **Line:** 637
**Signature:** `run_selection_cycle(goals) → list[Goal]`

**Class:** [[eos_ai-goal_selector-py-GoalSelector]]

Score all goals, sort, pick top N → ACTIVE, demote rest → DEFERRED.

Returns only the ACTIVE goals. Mutates state on all scorable goals.
Blocked/completed/dropped goals are untouched.

## Calls

- [[eos_ai-goal_selector-py-GoalSelector-_blockers_resolved]]
- [[eos_ai-goal_selector-py-GoalSelector-_emit_event]]
- [[eos_ai-goal_selector-py-GoalSelector-_log_cycle]]
- [[eos_ai-goal_selector-py-GoalSelector-_persist_goals]]
- [[eos_ai-goal_selector-py-GoalSelector-load_goals]]
- [[eos_ai-goal_selector-py-GoalSelector-score_goal]]
- [[eos_ai-goal_selector-py-OpportunityCostLayer-compute_relative_penalties]]
- [[eos_ai-goal_selector-py-OpportunityCostLayer-evaluate_swap_pressure]]

## Called By

- [[eos_ai-execution_loop-py-ExecutionLoop-run_cycle]]
- [[scripts-goals-py-cmd_goal_cycle]]
- [[services-goal_api-py-run_cycle]]
