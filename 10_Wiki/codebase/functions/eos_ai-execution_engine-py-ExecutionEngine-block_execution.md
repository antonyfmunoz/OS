---
type: codebase-function
file: eos_ai/execution_engine.py
line: 105
generated: 2026-05-07
---

# ExecutionEngine.block_execution

**File:** [[eos_ai-execution_engine-py]] | **Line:** 105
**Signature:** `block_execution(task_id, reason) → bool`

**Class:** [[eos_ai-execution_engine-py-ExecutionEngine]]

Mark a task as blocked and log the blocking reason.
Sends a Telegram alert if the task is assigned to a human.

Updates:
  tasks.status = 'blocked'
...

## Calls

- [[eos_ai-db-py-get_conn]]
- [[eos_ai-execution_engine-py-ExecutionEngine-_log_event]]
- [[eos_ai-execution_engine-py-_notify]]
