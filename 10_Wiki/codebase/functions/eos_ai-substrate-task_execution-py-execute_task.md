---
type: codebase-function
file: eos_ai/substrate/task_execution.py
line: 101
generated: 2026-05-07
---

# execute_task

**File:** [[eos_ai-substrate-task_execution-py]] | **Line:** 101
**Signature:** `execute_task(task, session) → Task`

Execute a single autonomous task, optionally through the pipeline engine.

When use_pipeline=True (default), tasks are decomposed into multi-step
pipelines and executed step-by-step. Pipeline state is mirrored back to
the task. When use_pipeline=False, falls through to legacy single-shot
...

## Calls

- [[eos_ai-substrate-task_execution-py-_execute_legacy]]
- [[eos_ai-substrate-task_execution-py-_execute_via_pipeline]]
- [[eos_ai-substrate-task_execution-py-_log]]
- [[eos_ai-substrate-task_system-py-TaskStore-default]]
- [[eos_ai-substrate-task_system-py-_log]]

## Called By

- [[eos_ai-substrate-task_execution-py-run_overnight_execution]]
