---
type: codebase-function
file: eos_ai/substrate/voice_wake.py
line: 195
generated: 2026-05-07
---

# VoiceWakeStore.put

**File:** [[eos_ai-substrate-voice_wake-py]] | **Line:** 195
**Signature:** `put(state) → None`

**Class:** [[eos_ai-substrate-voice_wake-py-VoiceWakeStore]]

Update the state, stamp updated_at, and persist.

## Calls

- [[eos_ai-substrate-voice_wake-py-VoiceWakeStore-_flush]]
- [[eos_ai-substrate-voice_wake-py-_utcnow]]

## Called By

- [[eos_ai-substrate-voice_wake-py-VoiceWakeStore-_flush]]
- [[eos_ai-substrate-voice_wake-py-disable_clap]]
- [[eos_ai-substrate-voice_wake-py-disable_tts]]
- [[eos_ai-substrate-voice_wake-py-disable_wake]]
- [[eos_ai-substrate-voice_wake-py-enable_clap]]
- [[eos_ai-substrate-voice_wake-py-enable_tts]]
- [[eos_ai-substrate-voice_wake-py-enable_wake]]
- [[eos_ai-substrate-voice_wake-py-register_trigger]]
