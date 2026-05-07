---
type: codebase-function
file: eos_ai/substrate/execution_authority.py
line: 207
generated: 2026-05-07
---

# event_primary_record_publication

**File:** [[eos_ai-substrate-execution_authority-py]] | **Line:** 207
**Signature:** `event_primary_record_publication(session_name, source) → EventPrimaryResult`

Record publication via the event scheduler.

Emits publication_confirmed. The scheduler chains through
clear_requested automatically.

## Calls

- [[eos_ai-substrate-execution_authority-py-_emit_and_drain]]
