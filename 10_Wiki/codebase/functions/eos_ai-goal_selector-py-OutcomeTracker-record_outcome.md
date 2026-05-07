---
type: codebase-function
file: eos_ai/goal_selector.py
line: 1149
generated: 2026-05-07
---

# OutcomeTracker.record_outcome

**File:** [[eos_ai-goal_selector-py]] | **Line:** 1149
**Signature:** `record_outcome(goal_id, outcome_type, execution_time, impact_delta, task_type, metadata) → None`

**Class:** [[eos_ai-goal_selector-py-OutcomeTracker]]

Record a single outcome and recompute the goal's performance profile.

outcome_type: 'success' | 'failure' | 'partial'

## Calls

- [[eos_ai-db-py-get_conn]]
- [[eos_ai-goal_selector-py-MultiHorizonProfile-to_dict]]
- [[eos_ai-goal_selector-py-OutcomeTracker-_compute_horizons]]
- [[eos_ai-goal_selector-py-OutcomeTracker-_compute_profile]]
- [[eos_ai-goal_selector-py-OutcomeTracker-_update_failure_decay]]
- [[eos_ai-goal_selector-py-PerformanceProfile-to_dict]]

## Called By

- [[eos_ai-execution_loop-py-ExecutionLoop-_execute_goal]]
