---
type: codebase-function
file: eos_ai/substrate/task_execution.py
line: 86
generated: 2026-05-07
---

# detect_human_block

**File:** [[eos_ai-substrate-task_execution-py]] | **Line:** 86
**Signature:** `detect_human_block(text) → Optional[str]`

Check execution output for signals that human input is needed.

Returns the matched phrase if a block is detected, None otherwise.
Deterministic regex matching — no LLM calls.

## Called By

- [[eos_ai-substrate-task_execution-py-_execute_legacy]]
