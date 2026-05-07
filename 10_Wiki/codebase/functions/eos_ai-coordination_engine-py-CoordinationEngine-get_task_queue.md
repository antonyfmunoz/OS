---
type: codebase-function
file: eos_ai/coordination_engine.py
line: 175
generated: 2026-05-07
---

# CoordinationEngine.get_task_queue

**File:** [[eos_ai-coordination_engine-py]] | **Line:** 175
**Signature:** `get_task_queue(assignee_id, status) → list[dict]`

**Class:** [[eos_ai-coordination_engine-py-CoordinationEngine]]

Return tasks filtered by assignee and status.
Sorted by priority (critical → high → normal → low), then created_at.

## Calls

- [[eos_ai-db-py-get_conn]]
