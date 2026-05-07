---
type: codebase-class
file: eos_ai/goal_selector.py
line: 270
generated: 2026-05-07
---

# OpportunityCostLayer

**File:** [[eos_ai-goal_selector-py]] | **Line:** 270

Cross-goal relative scoring: penalizes active goals when deferred
alternatives have stronger historical performance.

Operates on a scored list of goals (base + performance already computed).
Adds opportunity_cost_adjustment to each scorable goal.

## Methods

- [[eos_ai-goal_selector-py-OpportunityCostLayer-__init__]]`(weight, swap_threshold, sustained_cycles)` — 
- [[eos_ai-goal_selector-py-OpportunityCostLayer-compute_relative_penalties]]`(goals, focus_budget) → list[Goal]` — For each active goal, compare its performance composite against
- [[eos_ai-goal_selector-py-OpportunityCostLayer-evaluate_swap_pressure]]`(active_goals, deferred_goals) → list[tuple[Goal, Goal]]` — Identify (active, deferred) pairs where the deferred goal should
- [[eos_ai-goal_selector-py-OpportunityCostLayer-explain_goal]]`(goal, all_goals) → dict` — Opportunity cost explanation for a single goal.
