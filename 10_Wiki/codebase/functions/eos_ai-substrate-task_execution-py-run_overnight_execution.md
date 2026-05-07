---
type: codebase-function
file: eos_ai/substrate/task_execution.py
line: 381
generated: 2026-05-07
---

# run_overnight_execution

**File:** [[eos_ai-substrate-task_execution-py]] | **Line:** 381
**Signature:** `run_overnight_execution(session) → dict`

Process queued autonomous tasks in priority order via pipelines.

Called when session.day_mode == OVERNIGHT. Tasks are executed through
their pipelines with advance_all=True so each pipeline progresses as
far as possible. Pipelines that block on operator input are paused.
...

## Calls

- [[eos_ai-substrate-task_execution-py-_execute_via_pipeline]]
- [[eos_ai-substrate-task_execution-py-_log]]
- [[eos_ai-substrate-task_execution-py-execute_task]]
- [[eos_ai-substrate-task_system-py-_log]]
