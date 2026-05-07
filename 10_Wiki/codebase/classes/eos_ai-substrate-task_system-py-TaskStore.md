---
type: codebase-class
file: eos_ai/substrate/task_system.py
line: 248
generated: 2026-05-07
---

# TaskStore

**File:** [[eos_ai-substrate-task_system-py]] | **Line:** 248

Durable, thread-safe, singleton store for Task records.

Dual-layer: in-memory dict + substrate.storage (Neon-backed, JSON fallback).
Best-effort persistence — flush failures log and the in-memory state
remains correct.
...

## Methods

- [[eos_ai-substrate-task_system-py-TaskStore-__init__]]`() → None` — 
- [[eos_ai-substrate-task_system-py-TaskStore-_load]]`() → None` — 
- [[eos_ai-substrate-task_system-py-TaskStore-_flush]]`() → None` — 
- [[eos_ai-substrate-task_system-py-TaskStore-_prune_if_needed]]`() → None` — Remove oldest completed tasks if store exceeds _MAX_TASKS.
- [[eos_ai-substrate-task_system-py-TaskStore-get]]`(task_id) → Optional[Task]` — Return a task by ID, or None.
- [[eos_ai-substrate-task_system-py-TaskStore-put]]`(task) → None` — Insert or update a task. Flushes to storage.
- [[eos_ai-substrate-task_system-py-TaskStore-all]]`() → list[Task]` — Return all tasks, ordered by created_at ascending.
- [[eos_ai-substrate-task_system-py-TaskStore-by_status]]`(status) → list[Task]` — Return tasks with the given status.
- [[eos_ai-substrate-task_system-py-TaskStore-by_policy]]`(policy) → list[Task]` — Return tasks with the given execution policy.
- [[eos_ai-substrate-task_system-py-TaskStore-count_by_status]]`() → dict[str, int]` — Return a {status_value: count} summary dict.
- [[eos_ai-substrate-task_system-py-TaskStore-default]]`() → 'TaskStore'` — Return the process-level singleton, creating it on first call.
- [[eos_ai-substrate-task_system-py-TaskStore-reset_default_for_tests]]`() → None` — Tear down the singleton so the next call to default() creates a fresh instance.
