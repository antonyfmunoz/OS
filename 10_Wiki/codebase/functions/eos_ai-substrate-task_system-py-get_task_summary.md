---
type: codebase-function
file: eos_ai/substrate/task_system.py
line: 549
generated: 2026-05-07
---

# get_task_summary

**File:** [[eos_ai-substrate-task_system-py]] | **Line:** 549
**Signature:** `get_task_summary() → dict`

Build a summary dict for the open_day briefing.

Returns:
    {
        "completed_overnight": int,
...

## Calls

- [[eos_ai-substrate-task_system-py-TaskStore-all]]
- [[eos_ai-substrate-task_system-py-TaskStore-by_status]]
- [[eos_ai-substrate-task_system-py-TaskStore-default]]

## Called By

- [[eos_ai-substrate-task_queue-py-get_enhanced_task_summary]]
