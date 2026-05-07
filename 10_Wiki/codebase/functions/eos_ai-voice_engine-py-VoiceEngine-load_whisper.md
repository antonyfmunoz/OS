---
type: codebase-function
file: eos_ai/voice_engine.py
line: 419
generated: 2026-05-07
---

# VoiceEngine.load_whisper

**File:** [[eos_ai-voice_engine-py]] | **Line:** 419
**Signature:** `load_whisper(model_size) → bool`

**Class:** [[eos_ai-voice_engine-py-VoiceEngine]]

Load Whisper model into memory.

Sizes and trade-offs:
  tiny   — fastest, lower accuracy (~1 GB VRAM)
  base   — good balance, ~1 GB VRAM  ← default
...

## Called By

- [[eos_ai-voice_engine-py-VoiceEngine-transcribe]]
