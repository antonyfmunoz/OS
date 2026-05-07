---
type: codebase-function
file: eos_ai/substrate/task_system.py
line: 353
generated: 2026-05-07
---

# TaskStore.default

**File:** [[eos_ai-substrate-task_system-py]] | **Line:** 353
**Signature:** `default() → 'TaskStore'`

**Class:** [[eos_ai-substrate-task_system-py-TaskStore]]

Return the process-level singleton, creating it on first call.

## Called By

- [[eos_ai-substrate-task_execution-py-_execute_legacy]]
- [[eos_ai-substrate-task_execution-py-_execute_via_pipeline]]
- [[eos_ai-substrate-task_execution-py-execute_task]]
- [[eos_ai-substrate-task_queue-py-get_enhanced_task_summary]]
- [[eos_ai-substrate-task_queue-py-get_overnight_tasks]]
- [[eos_ai-substrate-task_queue-py-get_ready_tasks]]
- [[eos_ai-substrate-task_queue-py-get_tasks_sorted_for_execution]]
- [[eos_ai-substrate-task_queue-py-get_waiting_on_operator_tasks]]
- [[eos_ai-substrate-task_queue-py-prepare_overnight_queue]]
- [[eos_ai-substrate-task_system-py-create_task]]
- [[eos_ai-substrate-task_system-py-get_task_summary]]
- [[eos_ai-substrate-task_system-py-process_task]]
- [[eos_ai-substrate-task_system-py-run_overnight_tasks]]

## Decorators

- `@classmethod`
