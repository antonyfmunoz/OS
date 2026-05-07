---
type: codebase-function
file: eos_ai/substrate/task_queue.py
line: 145
generated: 2026-05-07
---

# get_overnight_tasks

**File:** [[eos_ai-substrate-task_queue-py]] | **Line:** 145
**Signature:** `get_overnight_tasks(store) → list[Task]`

Return OVERNIGHT_QUEUED tasks sorted by priority desc, created_at asc.

## Calls

- [[eos_ai-substrate-task_queue-py-_priority_sort]]
- [[eos_ai-substrate-task_system-py-TaskStore-by_status]]
- [[eos_ai-substrate-task_system-py-TaskStore-default]]
