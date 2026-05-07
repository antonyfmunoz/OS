---
type: codebase-function
file: eos_ai/substrate/task_system.py
line: 316
generated: 2026-05-07
---

# TaskStore.put

**File:** [[eos_ai-substrate-task_system-py]] | **Line:** 316
**Signature:** `put(task) → None`

**Class:** [[eos_ai-substrate-task_system-py-TaskStore]]

Insert or update a task. Flushes to storage.

## Calls

- [[eos_ai-substrate-task_system-py-TaskStore-_flush]]
- [[eos_ai-substrate-task_system-py-TaskStore-_prune_if_needed]]
- [[eos_ai-substrate-task_system-py-_utcnow]]

## Called By

- [[eos_ai-substrate-task_execution-py-_execute_legacy]]
- [[eos_ai-substrate-task_execution-py-_execute_via_pipeline]]
- [[eos_ai-substrate-task_queue-py-prepare_overnight_queue]]
- [[eos_ai-substrate-task_system-py-TaskStore-_flush]]
- [[eos_ai-substrate-task_system-py-create_task]]
- [[eos_ai-substrate-task_system-py-process_task]]
- [[eos_ai-substrate-task_system-py-run_overnight_tasks]]
