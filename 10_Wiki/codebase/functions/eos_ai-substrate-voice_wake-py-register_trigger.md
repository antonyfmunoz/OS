---
type: codebase-function
file: eos_ai/substrate/voice_wake.py
line: 326
generated: 2026-05-07
---

# register_trigger

**File:** [[eos_ai-substrate-voice_wake-py]] | **Line:** 326
**Signature:** `register_trigger(trigger) → VoiceWakeState`

Register that a wake/clap/manual trigger has fired.

Updates last_trigger, last_trigger_at, last_phrase, and sets
station_mode to ACTIVE. Returns updated state.

## Calls

- [[eos_ai-substrate-voice_wake-py-VoiceWakeStore-default]]
- [[eos_ai-substrate-voice_wake-py-VoiceWakeStore-get]]
- [[eos_ai-substrate-voice_wake-py-VoiceWakeStore-put]]
- [[eos_ai-substrate-voice_wake-py-_log]]
- [[eos_ai-substrate-voice_wake-py-_utcnow]]
