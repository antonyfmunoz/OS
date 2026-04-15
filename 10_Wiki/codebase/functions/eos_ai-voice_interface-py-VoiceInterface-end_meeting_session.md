---
type: codebase-function
file: eos_ai/voice_interface.py
line: 647
generated: 2026-04-12
---

# VoiceInterface.end_meeting_session

**File:** [[eos_ai-voice_interface-py]] | **Line:** 647
**Signature:** `end_meeting_session(session_id) → dict`

**Class:** [[eos_ai-voice_interface-py-VoiceInterface]]

Analyze the full session transcript via CognitiveLoop ANALYZE.
Logs the meeting to Neon as interaction type 'meeting'.
Creates tasks in Neon for all action items via CoordinationEngine.

Returns:
...

## Calls

- [[eos_ai-agent_runtime-py-AgentRuntime-run]]
- [[eos_ai-cognitive_loop-py-CognitiveLoop-run]]
- [[eos_ai-voice_interface-py-VoiceInterface-_extract_list]]
- [[eos_ai-voice_interface-py-VoiceInterface-_extract_section]]

## Called By

- [[eos_ai-voice_interface-py-VoiceInterface-end_meeting_with_actions]]
