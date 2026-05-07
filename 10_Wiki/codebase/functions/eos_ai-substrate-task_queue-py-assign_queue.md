---
type: codebase-function
file: eos_ai/substrate/task_queue.py
line: 97
generated: 2026-05-07
---

# assign_queue

**File:** [[eos_ai-substrate-task_queue-py]] | **Line:** 97
**Signature:** `assign_queue(task, is_day_open) → str`

Assign a queue name based on task policy and session state.

Rules:
- NEEDS_OPERATOR or WAITING_ON_OPERATOR → operator_blocked
- NEEDS_APPROVAL → approval_waiting
...

## Called By

- [[eos_ai-substrate-task_queue-py-prioritize_and_queue]]
