---
type: codebase-function
file: eos_ai/substrate/task_system.py
line: 420
generated: 2026-05-07
---

# process_task

**File:** [[eos_ai-substrate-task_system-py]] | **Line:** 420
**Signature:** `process_task(task) → Task`

Dispatch a task based on its policy and current session state.

For AUTONOMOUS tasks:
  - Day open + use_v2_execution → real execution via task_execution
  - Day open (v1 fallback) → immediate completion stub
...

## Calls

- [[eos_ai-substrate-task_system-py-TaskStore-default]]
- [[eos_ai-substrate-task_system-py-TaskStore-put]]
- [[eos_ai-substrate-task_system-py-_log]]
