---
type: codebase-function
file: eos_ai/execution_engine.py
line: 157
generated: 2026-04-12
---

# ExecutionEngine.complete_execution

**File:** [[eos_ai-execution_engine-py]] | **Line:** 157
**Signature:** `complete_execution(task_id, result, outcome_type, outcome_score) → bool`

**Class:** [[eos_ai-execution_engine-py-ExecutionEngine]]

Mark a task as completed and optionally log an outcome.

Updates:
  tasks.status       = 'completed'
  tasks.completed_at = now()
...

## Calls

- [[eos_ai-db-py-get_conn]]
- [[eos_ai-execution_engine-py-ExecutionEngine-_log_event]]
