---
type: codebase-class
file: eos_ai/execution_engine.py
line: 49
generated: 2026-04-12
---

# ExecutionEngine

**File:** [[eos_ai-execution_engine-py]] | **Line:** 49

Tracks task lifecycle from creation to outcome.

All state changes are persisted to Neon tasks + events tables.
Human-assigned tasks that become blocked trigger Telegram alerts.

## Methods

- [[eos_ai-execution_engine-py-ExecutionEngine-__init__]]`(ctx) → None` — 
- [[eos_ai-execution_engine-py-ExecutionEngine-start_execution]]`(task_id, agent) → bool` — Mark a task as in_progress and record who picked it up.
- [[eos_ai-execution_engine-py-ExecutionEngine-block_execution]]`(task_id, reason) → bool` — Mark a task as blocked and log the blocking reason.
- [[eos_ai-execution_engine-py-ExecutionEngine-complete_execution]]`(task_id, result, outcome_type, outcome_score) → bool` — Mark a task as completed and optionally log an outcome.
- [[eos_ai-execution_engine-py-ExecutionEngine-get_execution_trace]]`(task_id) → list[dict]` — Return the full lifecycle history for a task.
- [[eos_ai-execution_engine-py-ExecutionEngine-get_active_executions]]`() → list[dict]` — Return all in_progress tasks with runtime duration.
- [[eos_ai-execution_engine-py-ExecutionEngine-_log_event]]`(task_id, event_type, payload) → None` — Write a lifecycle event to the events table (best-effort).
