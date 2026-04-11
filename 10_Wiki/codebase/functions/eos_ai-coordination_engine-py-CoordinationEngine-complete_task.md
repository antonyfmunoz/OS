---
type: codebase-function
file: eos_ai/coordination_engine.py
line: 240
generated: 2026-04-11
---

# CoordinationEngine.complete_task

**File:** [[eos_ai-coordination_engine-py]] | **Line:** 240
**Signature:** `complete_task(task_id, result) → dict`

**Class:** [[eos_ai-coordination_engine-py-CoordinationEngine]]

Mark a task completed in Neon. Logs to events table.
Accepts full UUID or first 8 chars.
Returns updated task dict.

## Calls

- [[eos_ai-db-py-get_conn]]
