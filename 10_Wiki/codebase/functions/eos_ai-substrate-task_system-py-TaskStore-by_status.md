---
type: codebase-function
file: eos_ai/substrate/task_system.py
line: 329
generated: 2026-05-07
---

# TaskStore.by_status

**File:** [[eos_ai-substrate-task_system-py]] | **Line:** 329
**Signature:** `by_status(status) → list[Task]`

**Class:** [[eos_ai-substrate-task_system-py-TaskStore]]

Return tasks with the given status.

## Called By

- [[eos_ai-substrate-task_queue-py-get_overnight_tasks]]
- [[eos_ai-substrate-task_queue-py-get_ready_tasks]]
- [[eos_ai-substrate-task_queue-py-get_tasks_sorted_for_execution]]
- [[eos_ai-substrate-task_queue-py-get_waiting_on_operator_tasks]]
- [[eos_ai-substrate-task_queue-py-prepare_overnight_queue]]
- [[eos_ai-substrate-task_system-py-get_task_summary]]
- [[eos_ai-substrate-task_system-py-run_overnight_tasks]]
