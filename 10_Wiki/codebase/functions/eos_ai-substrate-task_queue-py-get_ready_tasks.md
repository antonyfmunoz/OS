---
type: codebase-function
file: eos_ai/substrate/task_queue.py
line: 139
generated: 2026-05-07
---

# get_ready_tasks

**File:** [[eos_ai-substrate-task_queue-py]] | **Line:** 139
**Signature:** `get_ready_tasks(store) → list[Task]`

Return READY tasks sorted by priority desc, created_at asc.

## Calls

- [[eos_ai-substrate-task_queue-py-_priority_sort]]
- [[eos_ai-substrate-task_system-py-TaskStore-by_status]]
- [[eos_ai-substrate-task_system-py-TaskStore-default]]
