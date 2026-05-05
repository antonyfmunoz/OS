---
type: codebase-function
file: eos_ai/voice_interface.py
line: 230
generated: 2026-04-12
---

# VoiceInterface.transcribe

**File:** [[eos_ai-voice_interface-py]] | **Line:** 230
**Signature:** `transcribe(audio_path) → str`

**Class:** [[eos_ai-voice_interface-py-VoiceInterface]]

Transcribe audio file to text via local Whisper.
Logs the entry to session transcript.
Returns transcript text.

## Calls

- [[eos_ai-media_processor-py-MediaProcessor-_local_transcribe]]

## Called By

- [[eos_ai-voice_interface-py-VoiceInterface-process_voice_turn]]
