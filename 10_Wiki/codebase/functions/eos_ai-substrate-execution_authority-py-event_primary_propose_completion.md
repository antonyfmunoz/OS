---
type: codebase-function
file: eos_ai/substrate/execution_authority.py
line: 160
generated: 2026-05-07
---

# event_primary_propose_completion

**File:** [[eos_ai-substrate-execution_authority-py]] | **Line:** 160
**Signature:** `event_primary_propose_completion(session_name, source) → EventPrimaryResult`

Propose run completion via the event scheduler.

Emits run_completion_proposed. If finalization_result is in payload
and success=True, the handler chains through finalization_succeeded
automatically.

## Calls

- [[eos_ai-substrate-execution_authority-py-_emit_and_drain]]
