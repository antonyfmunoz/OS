---
type: codebase-function
file: eos_ai/substrate/execution_authority.py
line: 293
generated: 2026-05-07
---

# event_primary_full_lifecycle

**File:** [[eos_ai-substrate-execution_authority-py]] | **Line:** 293
**Signature:** `event_primary_full_lifecycle(session_name, source, finalize_fn) → EventPrimaryResult`

Execute the FULL lifecycle via a single scheduler drain.

Emits run_completion_proposed with finalization_result embedded.
The handler chain cascades: proposal → finalization → publication
→ clear → terminal seal. One emit, one drain, full lifecycle.
...

## Calls

- [[eos_ai-substrate-execution_authority-py-_emit_and_drain]]
- [[eos_ai-substrate-execution_authority-py-_get_primary_scheduler]]
