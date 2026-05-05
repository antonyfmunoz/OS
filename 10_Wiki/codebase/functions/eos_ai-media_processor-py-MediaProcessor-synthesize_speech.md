---
type: codebase-function
file: eos_ai/media_processor.py
line: 259
generated: 2026-04-12
---

# MediaProcessor.synthesize_speech

**File:** [[eos_ai-media_processor-py]] | **Line:** 259
**Signature:** `synthesize_speech(text, output_path) → str | None`

**Class:** [[eos_ai-media_processor-py-MediaProcessor]]

Convert text to speech locally.
Cleans markdown before synthesis.
Returns path to audio file or None on failure.

## Called By

- [[eos_ai-voice_interface-py-VoiceInterface-synthesize]]
