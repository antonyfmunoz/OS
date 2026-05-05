---
type: codebase-function
file: eos_ai/voice_interface.py
line: 327
generated: 2026-04-12
---

# VoiceInterface.get_meeting_brief

**File:** [[eos_ai-voice_interface-py]] | **Line:** 327
**Signature:** `get_meeting_brief(meeting_type, venture_id, attendee_context) → str`

**Class:** [[eos_ai-voice_interface-py-VoiceInterface]]

Generate a type-appropriate pre-meeting brief using the correct dept agent.
Injects BIS context and returns a formatted brief for Telegram.

## Calls

- [[eos_ai-agent_runtime-py-AgentRuntime-run]]
- [[eos_ai-cognitive_loop-py-CognitiveLoop-run]]
