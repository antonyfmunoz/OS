---
type: codebase-class
file: eos_ai/coordination_engine.py
line: 44
generated: 2026-05-07
---

# CoordinationEngine

**File:** [[eos_ai-coordination_engine-py]] | **Line:** 44

*No docstring.*

## Methods

- [[eos_ai-coordination_engine-py-CoordinationEngine-__init__]]`(ctx)` — 
- [[eos_ai-coordination_engine-py-CoordinationEngine-_ensure_table]]`() → None` — 
- [[eos_ai-coordination_engine-py-CoordinationEngine-assign_task]]`(task_description, assignee_type, assignee_id, venture_id, priority, due_by, assigned_by) → str` — Create and assign a task to an agent or human.
- [[eos_ai-coordination_engine-py-CoordinationEngine-get_task_queue]]`(assignee_id, status) → list[dict]` — Return tasks filtered by assignee and status.
- [[eos_ai-coordination_engine-py-CoordinationEngine-complete_task]]`(task_id, result) → dict` — Mark a task completed in Neon. Logs to events table.
- [[eos_ai-coordination_engine-py-CoordinationEngine-ceo_delegate]]`(company_objective, venture_id) → dict` — CEO Agent breaks down a company objective into specific tasks
