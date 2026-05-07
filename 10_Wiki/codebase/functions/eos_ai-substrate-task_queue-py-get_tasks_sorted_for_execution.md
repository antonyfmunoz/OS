---
type: codebase-function
file: eos_ai/substrate/task_queue.py
line: 157
generated: 2026-05-07
---

# get_tasks_sorted_for_execution

**File:** [[eos_ai-substrate-task_queue-py]] | **Line:** 157
**Signature:** `get_tasks_sorted_for_execution(store) → list[Task]`

Return all executable tasks (READY + OVERNIGHT_QUEUED), priority-sorted.

This is the primary retrieval for the execution pipeline — gives the
executor the next-best task to run regardless of queue name.

## Calls

- [[eos_ai-substrate-task_queue-py-_priority_sort]]
- [[eos_ai-substrate-task_system-py-TaskStore-by_status]]
- [[eos_ai-substrate-task_system-py-TaskStore-default]]

## Called By

- [[eos_ai-substrate-task_queue-py-get_enhanced_task_summary]]
