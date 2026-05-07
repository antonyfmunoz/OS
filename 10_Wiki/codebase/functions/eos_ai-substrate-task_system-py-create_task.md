---
type: codebase-function
file: eos_ai/substrate/task_system.py
line: 371
generated: 2026-05-07
---

# create_task

**File:** [[eos_ai-substrate-task_system-py]] | **Line:** 371
**Signature:** `create_task(text) → Task`

Create a task from text, classify it, set initial status, and persist.

Args:
    text: The task title / natural language description used for classification.
    session_id: The day_session_id to link this task to (optional).
...

## Calls

- [[eos_ai-substrate-task_system-py-Task-new]]
- [[eos_ai-substrate-task_system-py-TaskStore-default]]
- [[eos_ai-substrate-task_system-py-TaskStore-put]]
- [[eos_ai-substrate-task_system-py-_log]]
- [[eos_ai-substrate-task_system-py-classify_task]]
