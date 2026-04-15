---
type: codebase-class
file: eos_ai/voice_engine.py
line: 330
generated: 2026-04-12
---

# VADProcessor

**File:** [[eos_ai-voice_engine-py]] | **Line:** 330

webrtcvad-based Voice Activity Detection.
Used as fallback when Silero VAD is unavailable.

## Methods

- [[eos_ai-voice_engine-py-VADProcessor-__init__]]`(aggressiveness) → None` — 
- [[eos_ai-voice_engine-py-VADProcessor-is_speech]]`(audio_chunk, sample_rate) → bool` — 
- [[eos_ai-voice_engine-py-VADProcessor-extract_speech_segments]]`(audio_path) → list[bytes]` — 
- [[eos_ai-voice_engine-py-VADProcessor-save_segment]]`(segment, path) → bool` — 
