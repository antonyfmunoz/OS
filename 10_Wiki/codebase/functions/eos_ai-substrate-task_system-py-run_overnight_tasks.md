---
type: codebase-function
file: eos_ai/substrate/task_system.py
line: 493
generated: 2026-05-07
---

# run_overnight_tasks

**File:** [[eos_ai-substrate-task_system-py]] | **Line:** 493
**Signature:** `run_overnight_tasks() → list[Task]`

Execute all OVERNIGHT_QUEUED tasks.

Called from close_day when the session transitions to OVERNIGHT mode.
Returns the list of tasks that were executed.

...

## Calls

- [[eos_ai-substrate-task_system-py-TaskStore-by_status]]
- [[eos_ai-substrate-task_system-py-TaskStore-default]]
- [[eos_ai-substrate-task_system-py-TaskStore-get]]
- [[eos_ai-substrate-task_system-py-TaskStore-put]]
- [[eos_ai-substrate-task_system-py-_log]]
