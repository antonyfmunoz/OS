---
type: codebase-function
file: eos_ai/substrate/execution_authority.py
line: 247
generated: 2026-05-07
---

# event_primary_confirm_clear

**File:** [[eos_ai-substrate-execution_authority-py]] | **Line:** 247
**Signature:** `event_primary_confirm_clear(session_name, source) → EventPrimaryResult`

Confirm clear via the event scheduler.

Emits clear_confirmed. The scheduler chains to terminal_seal_applied.

## Calls

- [[eos_ai-substrate-execution_authority-py-_emit_and_drain]]
