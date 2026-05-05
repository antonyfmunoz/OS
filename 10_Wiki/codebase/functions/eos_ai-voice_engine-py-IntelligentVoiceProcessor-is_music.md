---
type: codebase-function
file: eos_ai/voice_engine.py
line: 123
generated: 2026-04-12
---

# IntelligentVoiceProcessor.is_music

**File:** [[eos_ai-voice_engine-py]] | **Line:** 123
**Signature:** `is_music(audio_path) → float`

**Class:** [[eos_ai-voice_engine-py-IntelligentVoiceProcessor]]

Returns 0.0-1.0 music probability via spectral analysis.
Music has regular periodic patterns; speech has irregular ones.
