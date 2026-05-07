---
type: codebase-function
file: eos_ai/execution_loop.py
line: 161
generated: 2026-05-07
---

# ExecutionLoop.run_cycle

**File:** [[eos_ai-execution_loop-py]] | **Line:** 161
**Signature:** `run_cycle(cycle_num) → CycleResult`

**Class:** [[eos_ai-execution_loop-py-ExecutionLoop]]

Execute one full cycle: select → plan → execute → record → reselect.

## Calls

- [[eos_ai-execution_loop-py-ExecutionLoop-_execute_goal]]
- [[eos_ai-goal_selector-py-GoalSelector-run_selection_cycle]]

## Called By

- [[eos_ai-execution_loop-py-ExecutionLoop-run]]
