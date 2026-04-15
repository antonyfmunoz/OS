---
type: codebase-class
file: eos_ai/voice_engine.py
line: 43
generated: 2026-04-12
---

# IntelligentVoiceProcessor

**File:** [[eos_ai-voice_engine-py]] | **Line:** 43

Neural speech understanding layer.

Silero VAD → faster-whisper → speech classification.
Filters noise, music, and thinking-aloud from actionable utterances.
Maintains conversation context window for response continuity.
...

## Methods

- [[eos_ai-voice_engine-py-IntelligentVoiceProcessor-__init__]]`(voice_engine) → None` — 
- [[eos_ai-voice_engine-py-IntelligentVoiceProcessor-load_silero]]`() → bool` — Load Silero VAD model via torch.hub.
- [[eos_ai-voice_engine-py-IntelligentVoiceProcessor-load_faster_whisper]]`(model_size) → bool` — Load faster-whisper model (CTranslate2 — no torch required).
- [[eos_ai-voice_engine-py-IntelligentVoiceProcessor-is_speech_frame]]`(audio_chunk, sample_rate) → float` — Returns confidence 0.0-1.0 that this frame contains speech.
- [[eos_ai-voice_engine-py-IntelligentVoiceProcessor-is_music]]`(audio_path) → float` — Returns 0.0-1.0 music probability via spectral analysis.
- [[eos_ai-voice_engine-py-IntelligentVoiceProcessor-transcribe_fast]]`(audio_path) → str` — faster-whisper transcription with built-in VAD filter.
- [[eos_ai-voice_engine-py-IntelligentVoiceProcessor-classify_speech]]`(text, audio_confidence) → str` — Classify what type of communication this transcribed text is.
- [[eos_ai-voice_engine-py-IntelligentVoiceProcessor-is_utterance_complete]]`(text) → bool` — Determines if an utterance is complete or if the speaker is mid-thought.
- [[eos_ai-voice_engine-py-IntelligentVoiceProcessor-detect_meeting_context]]`(text, recent_context) → dict | None` — Detects meeting situations from natural language cues.
- [[eos_ai-voice_engine-py-IntelligentVoiceProcessor-add_to_context]]`(utterance, classification, response) → None` — 
- [[eos_ai-voice_engine-py-IntelligentVoiceProcessor-get_context_summary]]`() → str` — Returns recent conversation context for response continuity.
