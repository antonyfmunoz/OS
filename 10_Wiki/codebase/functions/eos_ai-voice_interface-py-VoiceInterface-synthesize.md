---
type: codebase-function
file: eos_ai/voice_interface.py
line: 247
generated: 2026-04-11
---

# VoiceInterface.synthesize

**File:** [[eos_ai-voice_interface-py]] | **Line:** 247
**Signature:** `synthesize(text, output_path) → str | None`

**Class:** [[eos_ai-voice_interface-py-VoiceInterface]]

Convert text to speech. Markdown stripping is handled inside
MediaProcessor.synthesize_speech(). Returns path to audio or None.

## Calls

- [[eos_ai-media_processor-py-MediaProcessor-synthesize_speech]]

## Called By

- [[eos_ai-voice_interface-py-VoiceInterface-process_voice_turn]]
