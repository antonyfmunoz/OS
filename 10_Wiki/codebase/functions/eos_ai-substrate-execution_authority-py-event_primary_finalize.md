---
type: codebase-function
file: eos_ai/substrate/execution_authority.py
line: 182
generated: 2026-05-07
---

# event_primary_finalize

**File:** [[eos_ai-substrate-execution_authority-py]] | **Line:** 182
**Signature:** `event_primary_finalize(session_name, source, finalize_fn) → EventPrimaryResult`

Execute finalization via the event scheduler.

Calls finalize_fn() to get the finalization result, then emits
finalization_succeeded if successful. The scheduler chains through
publication_confirmed automatically.

## Calls

- [[eos_ai-substrate-execution_authority-py-_emit_and_drain]]
