---
type: codebase-function
file: eos_ai/execution_engine.py
line: 234
generated: 2026-04-11
---

# ExecutionEngine.get_execution_trace

**File:** [[eos_ai-execution_engine-py]] | **Line:** 234
**Signature:** `get_execution_trace(task_id) → list[dict]`

**Class:** [[eos_ai-execution_engine-py-ExecutionEngine]]

Return the full lifecycle history for a task.

Reads from events table filtered by task_id reference in payload,
plus the current task row for base state.

...

## Calls

- [[eos_ai-db-py-get_conn]]
