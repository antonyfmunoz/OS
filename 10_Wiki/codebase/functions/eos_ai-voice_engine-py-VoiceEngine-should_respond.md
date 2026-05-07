---
type: codebase-function
file: eos_ai/voice_engine.py
line: 478
generated: 2026-05-07
---

# VoiceEngine.should_respond

**File:** [[eos_ai-voice_engine-py]] | **Line:** 478
**Signature:** `should_respond(text, music_score) → tuple[bool, str]`

**Class:** [[eos_ai-voice_engine-py-VoiceEngine]]

Returns (should_respond, classification).
Suppresses response for thinking aloud, singing, music, and silence.

## Calls

- [[eos_ai-voice_engine-py-IntelligentVoiceProcessor-classify_speech]]
