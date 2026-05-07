---
type: codebase-function
file: eos_ai/substrate/execution_authority.py
line: 265
generated: 2026-05-07
---

# event_primary_mark_terminal

**File:** [[eos_ai-substrate-execution_authority-py]] | **Line:** 265
**Signature:** `event_primary_mark_terminal(session_name, source) → EventPrimaryResult`

Attempt terminal seal via the event scheduler.

Emits terminal_seal_applied. Guard will block if conditions
(publication + clear) are not met.

## Calls

- [[eos_ai-substrate-execution_authority-py-_emit_and_drain]]
- [[eos_ai-substrate-execution_authority-py-_get_primary_scheduler]]
