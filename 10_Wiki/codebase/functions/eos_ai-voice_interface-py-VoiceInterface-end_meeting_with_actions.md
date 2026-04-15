---
type: codebase-function
file: eos_ai/voice_interface.py
line: 550
generated: 2026-04-12
---

# VoiceInterface.end_meeting_with_actions

**File:** [[eos_ai-voice_interface-py]] | **Line:** 550
**Signature:** `end_meeting_with_actions(session_id, meeting_type, venture_id) → dict`

**Class:** [[eos_ai-voice_interface-py-VoiceInterface]]

End meeting and run type-appropriate post-meeting actions.
Wraps end_meeting_session() and routes to correct dept agent.

## Calls

- [[eos_ai-voice_interface-py-VoiceInterface-end_meeting_session]]
