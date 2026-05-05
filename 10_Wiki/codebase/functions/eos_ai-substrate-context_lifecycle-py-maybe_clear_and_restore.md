---
type: codebase-function
file: eos_ai/substrate/context_lifecycle.py
line: 232
generated: 2026-04-12
---

# maybe_clear_and_restore

**File:** [[eos_ai-substrate-context_lifecycle-py]] | **Line:** 232
**Signature:** `maybe_clear_and_restore(session_name, target, mode) → dict[str, Any]`

Orchestrate pressure detection, checkpoint, clear, and restore.

1. Detect context pressure.
2. If below threshold, return early with cleared=False.
3. Build checkpoint.
...

## Calls

- [[eos_ai-substrate-context_lifecycle-py-_log]]
- [[eos_ai-substrate-context_lifecycle-py-build_context_checkpoint]]
- [[eos_ai-substrate-context_lifecycle-py-detect_context_pressure]]
- [[eos_ai-substrate-context_lifecycle-py-restore_from_checkpoint]]

## Called By

- [[eos_ai-substrate-discord_text_transport-py-maybe_mirror_discord_text_message]]
