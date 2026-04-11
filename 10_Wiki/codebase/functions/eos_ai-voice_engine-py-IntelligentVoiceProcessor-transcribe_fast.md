---
type: codebase-function
file: eos_ai/voice_engine.py
line: 148
generated: 2026-04-11
---

# IntelligentVoiceProcessor.transcribe_fast

**File:** [[eos_ai-voice_engine-py]] | **Line:** 148
**Signature:** `transcribe_fast(audio_path) → str`

**Class:** [[eos_ai-voice_engine-py-IntelligentVoiceProcessor]]

faster-whisper transcription with built-in VAD filter.
Falls back to regular Whisper via VoiceEngine reference.

## Calls

- [[eos_ai-voice_engine-py-IntelligentVoiceProcessor-load_faster_whisper]]
- [[eos_ai-voice_engine-py-VoiceEngine-transcribe]]
