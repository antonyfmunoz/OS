---
type: codebase-function
file: eos_ai/substrate/task_queue.py
line: 195
generated: 2026-05-07
---

# prepare_overnight_queue

**File:** [[eos_ai-substrate-task_queue-py]] | **Line:** 195
**Signature:** `prepare_overnight_queue(store) → dict`

Move eligible READY autonomous tasks into OVERNIGHT_QUEUED.

Called at close_day. Returns summary:
{
    "moved_to_overnight": int,
...

## Calls

- [[eos_ai-substrate-task_queue-py-_log]]
- [[eos_ai-substrate-task_system-py-TaskStore-by_status]]
- [[eos_ai-substrate-task_system-py-TaskStore-default]]
- [[eos_ai-substrate-task_system-py-TaskStore-put]]
- [[eos_ai-substrate-task_system-py-_log]]
