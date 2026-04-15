---
type: codebase-function
file: eos_ai/voice_interface.py
line: 623
generated: 2026-04-12
---

# VoiceInterface.process_meeting_audio

**File:** [[eos_ai-voice_interface-py]] | **Line:** 623
**Signature:** `process_meeting_audio(audio_path, session_id) → dict`

**Class:** [[eos_ai-voice_interface-py-VoiceInterface]]

Transcribe an audio chunk and add to session transcript.
Does NOT synthesize a response — capture only.

Returns:
    {transcript: str, session_id: str}

## Calls

- [[eos_ai-media_processor-py-MediaProcessor-_local_transcribe]]
