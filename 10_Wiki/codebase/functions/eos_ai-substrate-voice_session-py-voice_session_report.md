---
type: codebase-function
file: eos_ai/substrate/voice_session.py
line: 762
generated: 2026-04-11
---

# voice_session_report

**File:** [[eos_ai-substrate-voice_session-py]] | **Line:** 762
**Signature:** `voice_session_report(node_id, limit) → dict`

Compact, JSON-friendly operator report on voice presence activity.

## Calls

- [[eos_ai-substrate-nodes-py-NodeRegistry-get]]
- [[eos_ai-substrate-roles-py-RoleRegistry-get]]
- [[eos_ai-substrate-voice_session-py-VoiceSession-as_dict]]
- [[eos_ai-substrate-voice_session-py-VoiceSessionStore-active]]
- [[eos_ai-substrate-voice_session-py-VoiceSessionStore-get]]
- [[eos_ai-substrate-voice_session-py-VoiceSessionStore-latest]]
- [[eos_ai-substrate-voice_session-py-VoiceSessionStore-stats]]
- [[eos_ai-substrate-voice_session-py-VoiceTurn-as_dict]]
- [[eos_ai-substrate-voice_session-py-get_voice_session_store]]

## Called By

- [[scripts-substrate_voice_eos_responder_smoke_test-py-main]]
- [[scripts-substrate_voice_session_cli-py-cmd_report]]
- [[scripts-substrate_voice_session_smoke_test-py-main]]
