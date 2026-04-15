---
type: codebase-class
file: eos_ai/voice_interface.py
line: 37
generated: 2026-04-12
---

# VoiceInterface

**File:** [[eos_ai-voice_interface-py]] | **Line:** 37

*No docstring.*

## Methods

- [[eos_ai-voice_interface-py-VoiceInterface-__init__]]`(ctx) → None` — 
- [[eos_ai-voice_interface-py-VoiceInterface-transcribe]]`(audio_path) → str` — Transcribe audio file to text via local Whisper.
- [[eos_ai-voice_interface-py-VoiceInterface-synthesize]]`(text, output_path) → str | None` — Convert text to speech. Markdown stripping is handled inside
- [[eos_ai-voice_interface-py-VoiceInterface-process_voice_turn]]`(audio_path, agent, venture_id) → dict` — Full voice conversation turn:
- [[eos_ai-voice_interface-py-VoiceInterface-get_meeting_brief]]`(meeting_type, venture_id, attendee_context) → str` — Generate a type-appropriate pre-meeting brief using the correct dept agent.
- [[eos_ai-voice_interface-py-VoiceInterface-get_during_meeting_context]]`(meeting_type, query, session_id, venture_id) → str` — Answer real-time queries during a meeting — text only, silent to call.
- [[eos_ai-voice_interface-py-VoiceInterface-end_meeting_with_actions]]`(session_id, meeting_type, venture_id) → dict` — End meeting and run type-appropriate post-meeting actions.
- [[eos_ai-voice_interface-py-VoiceInterface-start_meeting_session]]`(meeting_name) → str` — Create a new meeting session. Clears any prior transcript.
- [[eos_ai-voice_interface-py-VoiceInterface-process_meeting_audio]]`(audio_path, session_id) → dict` — Transcribe an audio chunk and add to session transcript.
- [[eos_ai-voice_interface-py-VoiceInterface-end_meeting_session]]`(session_id) → dict` — Analyze the full session transcript via CognitiveLoop ANALYZE.
- [[eos_ai-voice_interface-py-VoiceInterface-get_session_transcript]]`() → list[dict]` — 
- [[eos_ai-voice_interface-py-VoiceInterface-clear_session]]`() → None` — 
- [[eos_ai-voice_interface-py-VoiceInterface-_extract_section]]`(text, section) → str` — Extract the content block under a named section header.
- [[eos_ai-voice_interface-py-VoiceInterface-_extract_list]]`(text, section) → list[str]` — Return list of items from a named section.
