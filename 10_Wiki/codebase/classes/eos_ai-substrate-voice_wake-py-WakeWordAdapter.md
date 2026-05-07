---
type: codebase-class
file: eos_ai/substrate/voice_wake.py
line: 229
generated: 2026-05-07
---

# WakeWordAdapter

**File:** [[eos_ai-substrate-voice_wake-py]] | **Line:** 229

Interface for wake word detection.

Override detect() to integrate with a real wake word engine
(e.g., Porcupine, Vosk, etc). Default stub always returns (False, None).

## Methods

- [[eos_ai-substrate-voice_wake-py-WakeWordAdapter-detect]]`(audio_chunk) → tuple[bool, Optional[str]]` — Return (detected, phrase) from audio chunk.
