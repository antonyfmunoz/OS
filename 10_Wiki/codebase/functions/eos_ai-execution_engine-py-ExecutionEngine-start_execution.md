---
type: codebase-function
file: eos_ai/execution_engine.py
line: 64
generated: 2026-05-07
---

# ExecutionEngine.start_execution

**File:** [[eos_ai-execution_engine-py]] | **Line:** 64
**Signature:** `start_execution(task_id, agent) → bool`

**Class:** [[eos_ai-execution_engine-py-ExecutionEngine]]

Mark a task as in_progress and record who picked it up.

Updates:
  tasks.status      = 'in_progress'
  tasks.started_at  = now()
...

## Calls

- [[eos_ai-db-py-get_conn]]
- [[eos_ai-execution_engine-py-ExecutionEngine-_log_event]]
