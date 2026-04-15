---
type: codebase-function
file: eos_ai/substrate/voice_eos_responder.py
line: 302
generated: 2026-04-12
---

# build_eos_voice_responder

**File:** [[eos_ai-substrate-voice_eos_responder-py]] | **Line:** 302
**Signature:** `build_eos_voice_responder() → VoiceResponder`

Return the EOS-backed responder callable.

Useful when a caller wants to install a customized variant or test the
bridge in isolation without flipping the global responder.
