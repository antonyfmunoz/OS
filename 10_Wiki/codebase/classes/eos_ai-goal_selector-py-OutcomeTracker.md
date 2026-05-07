---
type: codebase-class
file: eos_ai/goal_selector.py
line: 1137
generated: 2026-05-07
---

# OutcomeTracker

**File:** [[eos_ai-goal_selector-py]] | **Line:** 1137

Records execution outcomes and recomputes performance profiles.

Hooks into EventBus (task_completed, task_failed) to update goal
performance in real time. The GoalSelector reads these profiles
during the next selection cycle.

## Methods

- [[eos_ai-goal_selector-py-OutcomeTracker-__init__]]`(org_id)` — 
- [[eos_ai-goal_selector-py-OutcomeTracker-record_outcome]]`(goal_id, outcome_type, execution_time, impact_delta, task_type, metadata) → None` — Record a single outcome and recompute the goal's performance profile.
- [[eos_ai-goal_selector-py-OutcomeTracker-_update_failure_decay]]`(goal_id, outcome_type) → tuple[int, float]` — Update failure streak and priority decay multiplier (Phase 9H).
- [[eos_ai-goal_selector-py-OutcomeTracker-_emit_decay_event]]`(goal_id, failure_streak, new_multiplier) → None` — Emit goal_priority_decayed event via EventBus.
- [[eos_ai-goal_selector-py-OutcomeTracker-_load_outcome_rows]]`(goal_id) → list[dict]` — Load raw outcome rows from DB.
- [[eos_ai-goal_selector-py-OutcomeTracker-_compute_profile_from_rows]]`(rows, half_life) → PerformanceProfile` — Compute performance profile from outcome rows with a given decay half-life.
- [[eos_ai-goal_selector-py-OutcomeTracker-_compute_profile]]`(goal_id, half_life) → PerformanceProfile` — Recompute a single-horizon performance profile.
- [[eos_ai-goal_selector-py-OutcomeTracker-_compute_horizons]]`(goal_id) → MultiHorizonProfile` — Compute performance across short/medium/long horizons.
- [[eos_ai-goal_selector-py-OutcomeTracker-get_profile]]`(goal_id) → PerformanceProfile` — Get current medium-term performance profile for a goal.
- [[eos_ai-goal_selector-py-OutcomeTracker-get_horizons]]`(goal_id) → MultiHorizonProfile` — Get multi-horizon performance profile for a goal.
- [[eos_ai-goal_selector-py-OutcomeTracker-get_outcome_history]]`(goal_id, limit) → list[dict]` — Get raw outcome history for a goal.
