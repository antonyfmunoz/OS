---
type: codebase-function
file: eos_ai/voice_interface.py
line: 598
generated: 2026-04-12
---

# VoiceInterface.start_meeting_session

**File:** [[eos_ai-voice_interface-py]] | **Line:** 598
**Signature:** `start_meeting_session(meeting_name) → str`

**Class:** [[eos_ai-voice_interface-py-VoiceInterface]]

Create a new meeting session. Clears any prior transcript.
Logs meeting_start event to Neon.
Returns session_id.

## Calls

- [[eos_ai-voice_interface-py-VoiceInterface-clear_session]]
