---
type: codebase-class
file: eos_ai/substrate/voice_wake.py
line: 140
generated: 2026-05-07
---

# VoiceWakeStore

**File:** [[eos_ai-substrate-voice_wake-py]] | **Line:** 140

Durable, thread-safe singleton store for VoiceWakeState.

Stores a SINGLE VoiceWakeState (not a collection) under the
``voice_wake_state`` key in substrate storage. Dual-layer: in-memory
for speed, flushed to durable storage on every mutation.

## Methods

- [[eos_ai-substrate-voice_wake-py-VoiceWakeStore-__init__]]`() → None` — 
- [[eos_ai-substrate-voice_wake-py-VoiceWakeStore-_load]]`() → None` — 
- [[eos_ai-substrate-voice_wake-py-VoiceWakeStore-_flush]]`() → None` — 
- [[eos_ai-substrate-voice_wake-py-VoiceWakeStore-get]]`() → VoiceWakeState` — Return current state, creating a default if none exists.
- [[eos_ai-substrate-voice_wake-py-VoiceWakeStore-put]]`(state) → None` — Update the state, stamp updated_at, and persist.
- [[eos_ai-substrate-voice_wake-py-VoiceWakeStore-default]]`() → VoiceWakeStore` — Return the process-wide singleton store.
- [[eos_ai-substrate-voice_wake-py-VoiceWakeStore-reset_default_for_tests]]`() → None` — Test hook — drop the singleton so the next default() re-resolves.
