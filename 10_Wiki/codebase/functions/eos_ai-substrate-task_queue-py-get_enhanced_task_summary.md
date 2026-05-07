---
type: codebase-function
file: eos_ai/substrate/task_queue.py
line: 172
generated: 2026-05-07
---

# get_enhanced_task_summary

**File:** [[eos_ai-substrate-task_queue-py]] | **Line:** 172
**Signature:** `get_enhanced_task_summary(store) → dict`

Extended task summary for open_day briefing.

Returns the base get_task_summary() dict plus:
- queued_autonomous: count of READY + OVERNIGHT_QUEUED autonomous tasks
- top_priority_task_title: title of the highest-priority executable task

## Calls

- [[eos_ai-substrate-task_queue-py-get_tasks_sorted_for_execution]]
- [[eos_ai-substrate-task_system-py-TaskStore-default]]
- [[eos_ai-substrate-task_system-py-get_task_summary]]
