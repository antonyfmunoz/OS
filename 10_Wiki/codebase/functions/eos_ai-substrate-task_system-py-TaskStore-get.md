---
type: codebase-function
file: eos_ai/substrate/task_system.py
line: 311
generated: 2026-05-07
---

# TaskStore.get

**File:** [[eos_ai-substrate-task_system-py]] | **Line:** 311
**Signature:** `get(task_id) → Optional[Task]`

**Class:** [[eos_ai-substrate-task_system-py-TaskStore]]

Return a task by ID, or None.

## Called By

- [[eos_ai-substrate-task_execution-py-_execute_legacy]]
- [[eos_ai-substrate-task_execution-py-_execute_via_pipeline]]
- [[eos_ai-substrate-task_execution-py-_sync_pipeline_to_task]]
- [[eos_ai-substrate-task_system-py-Task-from_dict]]
- [[eos_ai-substrate-task_system-py-TaskStore-_load]]
- [[eos_ai-substrate-task_system-py-TaskStore-count_by_status]]
- [[eos_ai-substrate-task_system-py-run_overnight_tasks]]
