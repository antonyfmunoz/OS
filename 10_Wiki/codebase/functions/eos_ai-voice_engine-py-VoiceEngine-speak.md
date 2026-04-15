---
type: codebase-function
file: eos_ai/voice_engine.py
line: 502
generated: 2026-04-12
---

# VoiceEngine.speak

**File:** [[eos_ai-voice_engine-py]] | **Line:** 502
**Signature:** `speak(text, output_path) → str`

**Class:** [[eos_ai-voice_engine-py-VoiceEngine]]

Convert text to a WAV audio file.

Tries Coqui TTS first; falls back to espeak (always available).
Returns path to the generated audio file, or empty string on failure.
