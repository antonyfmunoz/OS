---
type: codebase-function
file: eos_ai/substrate/task_queue.py
line: 151
generated: 2026-05-07
---

# get_waiting_on_operator_tasks

**File:** [[eos_ai-substrate-task_queue-py]] | **Line:** 151
**Signature:** `get_waiting_on_operator_tasks(store) → list[Task]`

Return WAITING_ON_OPERATOR tasks sorted by priority desc, created_at asc.

## Calls

- [[eos_ai-substrate-task_queue-py-_priority_sort]]
- [[eos_ai-substrate-task_system-py-TaskStore-by_status]]
- [[eos_ai-substrate-task_system-py-TaskStore-default]]
