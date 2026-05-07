---
type: codebase-function
file: eos_ai/goal_selector.py
line: 342
generated: 2026-05-07
---

# OpportunityCostLayer.evaluate_swap_pressure

**File:** [[eos_ai-goal_selector-py]] | **Line:** 342
**Signature:** `evaluate_swap_pressure(active_goals, deferred_goals) → list[tuple[Goal, Goal]]`

**Class:** [[eos_ai-goal_selector-py-OpportunityCostLayer]]

Identify (active, deferred) pairs where the deferred goal should
replace the active one, subject to hysteresis.

Returns list of (demote, promote) pairs.

## Called By

- [[eos_ai-goal_selector-py-GoalSelector-run_selection_cycle]]
