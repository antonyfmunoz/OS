---
type: codebase-class
file: eos_ai/execution_loop.py
line: 124
generated: 2026-05-07
---

# ExecutionLoop

**File:** [[eos_ai-execution_loop-py]] | **Line:** 124

Closed-loop execution: select → plan → execute → record → reselect.

Hard constraints:
- No parallel execution
- No agent mutation
...

## Methods

- [[eos_ai-execution_loop-py-ExecutionLoop-__init__]]`(selector, planner, executor, outcome_tracker, event_publisher) → None` — 
- [[eos_ai-execution_loop-py-ExecutionLoop-_default_publish]]`(event_type, payload) → None` — 
- [[eos_ai-execution_loop-py-ExecutionLoop-run_cycle]]`(cycle_num) → CycleResult` — Execute one full cycle: select → plan → execute → record → reselect.
- [[eos_ai-execution_loop-py-ExecutionLoop-_execute_goal]]`(goal) → ExecutionResult` — Plan → execute → record outcome for a single goal.
- [[eos_ai-execution_loop-py-ExecutionLoop-run]]`(cycles) → list[CycleResult]` — Run multiple execution cycles sequentially.
- [[eos_ai-execution_loop-py-ExecutionLoop-cycle_history]]`() → list[CycleResult]` — 
- [[eos_ai-execution_loop-py-ExecutionLoop-_print_cycle_summary]]`(cr) → None` — 
