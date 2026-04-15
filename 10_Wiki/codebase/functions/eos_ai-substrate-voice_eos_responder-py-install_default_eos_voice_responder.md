---
type: codebase-function
file: eos_ai/substrate/voice_eos_responder.py
line: 315
generated: 2026-04-12
---

# install_default_eos_voice_responder

**File:** [[eos_ai-substrate-voice_eos_responder-py]] | **Line:** 315
**Signature:** `install_default_eos_voice_responder() → None`

Install the EOS-backed responder as the global voice responder.

Idempotent. Safe to call multiple times. Backward compatible: pass
`set_voice_responder(None)` later to restore the substrate stub.

## Calls

- [[eos_ai-substrate-voice_session-py-set_voice_responder]]

## Called By

- [[scripts-substrate_voice_eos_responder_smoke_test-py-main]]
