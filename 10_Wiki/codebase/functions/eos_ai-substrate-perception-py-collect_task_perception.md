---
type: codebase-function
file: eos_ai/substrate/perception.py
line: 325
generated: 2026-05-07
---

# collect_task_perception

**File:** [[eos_ai-substrate-perception-py]] | **Line:** 325
**Signature:** `collect_task_perception() → list[PerceptionRecord]`

Inspect task system for actionable state.

Detects:
- Tasks stuck in WAITING_ON_OPERATOR for > 4 hours
- Failed tasks (COMPLETED with execution_error)
...

## Calls

- [[eos_ai-substrate-perception-py-PerceptionRecord-new]]
- [[eos_ai-substrate-perception-py-PerceptionStore-default]]
- [[eos_ai-substrate-perception-py-_log]]
- [[eos_ai-substrate-perception-py-_now]]
