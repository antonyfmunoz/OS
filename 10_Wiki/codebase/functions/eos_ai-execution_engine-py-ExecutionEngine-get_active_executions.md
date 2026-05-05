---
type: codebase-function
file: eos_ai/execution_engine.py
line: 297
generated: 2026-04-12
---

# ExecutionEngine.get_active_executions

**File:** [[eos_ai-execution_engine-py]] | **Line:** 297
**Signature:** `get_active_executions() → list[dict]`

**Class:** [[eos_ai-execution_engine-py-ExecutionEngine]]

Return all in_progress tasks with runtime duration.
Flags tasks stuck longer than _STUCK_THRESHOLD_MINUTES.

Returns:
    List of dicts: task_id, description, agent, started_at,
...

## Calls

- [[eos_ai-db-py-get_conn]]
