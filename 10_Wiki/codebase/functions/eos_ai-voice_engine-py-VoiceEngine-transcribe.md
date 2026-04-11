---
type: codebase-function
file: eos_ai/voice_engine.py
line: 439
generated: 2026-04-11
---

# VoiceEngine.transcribe

**File:** [[eos_ai-voice_engine-py]] | **Line:** 439
**Signature:** `transcribe(audio_path) → str`

**Class:** [[eos_ai-voice_engine-py-VoiceEngine]]

Convert audio file to text. Lazy-loads Whisper on first call.

## Calls

- [[eos_ai-voice_engine-py-VoiceEngine-load_whisper]]

## Called By

- [[eos_ai-voice_engine-py-IntelligentVoiceProcessor-transcribe_fast]]
- [[eos_ai-voice_engine-py-VoiceEngine-transcribe_with_vad]]
