---
type: codebase-class
file: eos_ai/goal_selector.py
line: 521
generated: 2026-05-07
---

# GoalSelector

**File:** [[eos_ai-goal_selector-py]] | **Line:** 521

Scores, ranks, and selects which goals are ACTIVE.

Pure selection + scoring layer. No execution, no planner mutation.

## Methods

- [[eos_ai-goal_selector-py-GoalSelector-__init__]]`(org_id, focus_budget, weights, opportunity_cost_weight, swap_threshold, swap_sustained_cycles, horizon_weights)` — 
- [[eos_ai-goal_selector-py-GoalSelector-score_goal]]`(goal, all_goals) → Goal` — Compute weighted score for a single goal.
- [[eos_ai-goal_selector-py-GoalSelector-_performance_decay]]`(perf) → float` — Exponential decay: recent outcomes matter more. Returns 0-1.
- [[eos_ai-goal_selector-py-GoalSelector-_count_unlocks]]`(goal_id, all_goals) → int` — Count how many other goals list this goal_id in their blocked_by.
- [[eos_ai-goal_selector-py-GoalSelector-run_selection_cycle]]`(goals) → list[Goal]` — Score all goals, sort, pick top N → ACTIVE, demote rest → DEFERRED.
- [[eos_ai-goal_selector-py-GoalSelector-_blockers_resolved]]`(goal, all_goals) → bool` — True if every goal in blocked_by is COMPLETED or DROPPED.
- [[eos_ai-goal_selector-py-GoalSelector-explain]]`(goal, all_goals) → dict` — Return explainability payload for a single goal.
- [[eos_ai-goal_selector-py-GoalSelector-activate]]`(goal_id) → Goal` — Force a goal to ACTIVE (manual override). Bumps lowest-ranked active goal if at 
- [[eos_ai-goal_selector-py-GoalSelector-defer]]`(goal_id) → Goal` — Manually defer a goal.
- [[eos_ai-goal_selector-py-GoalSelector-complete]]`(goal_id) → Goal` — Mark a goal as completed.
- [[eos_ai-goal_selector-py-GoalSelector-drop]]`(goal_id) → Goal` — Drop a goal permanently.
- [[eos_ai-goal_selector-py-GoalSelector-block]]`(goal_id, blocked_by) → Goal` — Mark a goal as blocked by other goal IDs.
- [[eos_ai-goal_selector-py-GoalSelector-is_active]]`(goal_id) → bool` — The gate: only ACTIVE goals produce tasks.
- [[eos_ai-goal_selector-py-GoalSelector-_find_goal]]`(goal_id, goals) → Goal` — 
- [[eos_ai-goal_selector-py-GoalSelector-add_goal]]`(title, description, priority, expected_impact, estimated_cost, confidence, venture_id, blocked_by) → Goal` — Create a new goal. Starts as DEFERRED — selection cycle activates it.
- [[eos_ai-goal_selector-py-GoalSelector-list_goals]]`(state) → list[Goal]` — List all goals, optionally filtered by state.
- [[eos_ai-goal_selector-py-GoalSelector-get_goal]]`(goal_id) → Goal` — Get a single goal by ID.
- [[eos_ai-goal_selector-py-GoalSelector-_persist_goal]]`(goal) → None` — Upsert a single goal to Neon.
- [[eos_ai-goal_selector-py-GoalSelector-_persist_goals]]`(goals) → None` — Batch persist — one transaction.
- [[eos_ai-goal_selector-py-GoalSelector-load_goals]]`() → list[Goal]` — Load all goals from Neon for this org.
- [[eos_ai-goal_selector-py-GoalSelector-_emit_event]]`(event_type, goal, swap_target) → None` — Publish goal state change to EventBus.
- [[eos_ai-goal_selector-py-GoalSelector-_log_cycle]]`(active, all_scored) → None` — Log selection cycle result to events table.
