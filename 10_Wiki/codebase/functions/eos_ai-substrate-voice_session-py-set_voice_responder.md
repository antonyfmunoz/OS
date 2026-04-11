---
type: codebase-function
file: eos_ai/substrate/voice_session.py
line: 431
generated: 2026-04-11
---

# set_voice_responder

**File:** [[eos_ai-substrate-voice_session-py]] | **Line:** 431
**Signature:** `set_voice_responder(responder) → None`

Replace the default echo responder with a real implementation.

Pass `None` to reset back to the default. Callers (e.g. an EA-aware
bridge) own all LLM/intelligence concerns; the substrate stays clean.

## Called By

- [[eos_ai-substrate-voice_eos_responder-py-install_default_eos_voice_responder]]
- [[eos_ai-substrate-voice_eos_responder-py-uninstall_eos_voice_responder]]
