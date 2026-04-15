---
type: codebase-class
file: eos_ai/voice_engine.py
line: 407
generated: 2026-04-12
---

# VoiceEngine

**File:** [[eos_ai-voice_engine-py]] | **Line:** 407

*No docstring.*

## Methods

- [[eos_ai-voice_engine-py-VoiceEngine-__init__]]`() → None` — 
- [[eos_ai-voice_engine-py-VoiceEngine-load_whisper]]`(model_size) → bool` — Load Whisper model into memory.
- [[eos_ai-voice_engine-py-VoiceEngine-transcribe]]`(audio_path) → str` — Convert audio file to text. Lazy-loads Whisper on first call.
- [[eos_ai-voice_engine-py-VoiceEngine-transcribe_with_vad]]`(audio_path) → list[str]` — Transcribes only speech segments (webrtcvad fallback path).
- [[eos_ai-voice_engine-py-VoiceEngine-should_respond]]`(text, music_score) → tuple[bool, str]` — Returns (should_respond, classification).
- [[eos_ai-voice_engine-py-VoiceEngine-speak]]`(text, output_path) → str` — Convert text to a WAV audio file.
- [[eos_ai-voice_engine-py-VoiceEngine-query_local]]`(prompt, system) → str` — Query Qwen2.5:7b locally via Ollama.
- [[eos_ai-voice_engine-py-VoiceEngine-is_simple_query]]`(text) → bool` — Determine if query can be handled locally (Ollama) vs Claude (EOS).
- [[eos_ai-voice_engine-py-VoiceEngine-route_query]]`(text, ctx) → str` — Route query to right inference backend.
- [[eos_ai-voice_engine-py-VoiceEngine-is_running]]`() → bool` — Check if Ollama is reachable.
