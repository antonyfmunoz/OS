---
type: codebase-function
file: eos_ai/substrate/task_system.py
line: 84
generated: 2026-05-07
---

# classify_task

**File:** [[eos_ai-substrate-task_system-py]] | **Line:** 84
**Signature:** `classify_task(text) → TaskExecutionPolicy`

Classify a task using deterministic keyword heuristics.

Priority order: needs_operator > needs_approval > autonomous.
No LLM calls — pure regex matching.

## Called By

- [[eos_ai-substrate-task_system-py-create_task]]
