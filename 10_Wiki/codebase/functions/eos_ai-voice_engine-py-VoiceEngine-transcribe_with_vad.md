---
type: codebase-function
file: eos_ai/voice_engine.py
line: 452
generated: 2026-05-07
---

# VoiceEngine.transcribe_with_vad

**File:** [[eos_ai-voice_engine-py]] | **Line:** 452
**Signature:** `transcribe_with_vad(audio_path) → list[str]`

**Class:** [[eos_ai-voice_engine-py-VoiceEngine]]

Transcribes only speech segments (webrtcvad fallback path).
Returns list of transcribed utterances — silence filtered.
Prefer intelligent.transcribe_fast() for real-time use.

## Calls

- [[eos_ai-voice_engine-py-VADProcessor-extract_speech_segments]]
- [[eos_ai-voice_engine-py-VADProcessor-save_segment]]
- [[eos_ai-voice_engine-py-VoiceEngine-transcribe]]
