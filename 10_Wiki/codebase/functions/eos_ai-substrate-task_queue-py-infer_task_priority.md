---
type: codebase-function
file: eos_ai/substrate/task_queue.py
line: 68
generated: 2026-05-07
---

# infer_task_priority

**File:** [[eos_ai-substrate-task_queue-py]] | **Line:** 68
**Signature:** `infer_task_priority(task, session) → int`

Assign a priority score to a task. Deterministic keyword matching.

Rules:
- Urgency keywords in text → CRITICAL (100)
- NEEDS_OPERATOR tasks → HIGH (75) — operator bottleneck, surface quickly
...

## Called By

- [[eos_ai-substrate-task_queue-py-prioritize_and_queue]]
