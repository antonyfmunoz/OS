---
type: codebase-function
file: eos_ai/coordination_engine.py
line: 87
generated: 2026-04-12
---

# CoordinationEngine.assign_task

**File:** [[eos_ai-coordination_engine-py]] | **Line:** 87
**Signature:** `assign_task(task_description, assignee_type, assignee_id, venture_id, priority, due_by, assigned_by) → str`

**Class:** [[eos_ai-coordination_engine-py-CoordinationEngine]]

Create and assign a task to an agent or human.
- agent: published to event bus immediately.
- human: Telegram notification sent.
Returns task_id (UUID string).

## Calls

- [[eos_ai-coordination_engine-py-_notify]]
- [[eos_ai-db-py-get_conn]]
- [[eos_ai-db-py-resolve_venture]]
- [[eos_ai-event_bus-py-EventBus-publish_async]]

## Called By

- [[eos_ai-coordination_engine-py-CoordinationEngine-ceo_delegate]]
