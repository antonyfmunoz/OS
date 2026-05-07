---
type: codebase-function
file: eos_ai/substrate/execution_authority.py
line: 228
generated: 2026-05-07
---

# event_primary_request_clear

**File:** [[eos_ai-substrate-execution_authority-py]] | **Line:** 228
**Signature:** `event_primary_request_clear(session_name, source) → EventPrimaryResult`

Request clear via the event scheduler.

Emits clear_requested. The scheduler chains through clear_confirmed
and terminal_seal_applied automatically.

## Calls

- [[eos_ai-substrate-execution_authority-py-_emit_and_drain]]
