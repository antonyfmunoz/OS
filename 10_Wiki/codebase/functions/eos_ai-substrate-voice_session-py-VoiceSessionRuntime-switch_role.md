---
type: codebase-function
file: eos_ai/substrate/voice_session.py
line: 695
generated: 2026-04-12
---

# VoiceSessionRuntime.switch_role

**File:** [[eos_ai-substrate-voice_session-py]] | **Line:** 695
**Signature:** `switch_role(session_id, new_role_slug) → Optional[VoiceSession]`

**Class:** [[eos_ai-substrate-voice_session-py-VoiceSessionRuntime]]

*No docstring.*

## Calls

- [[eos_ai-substrate-nodes-py-NodeRegistry-get]]
- [[eos_ai-substrate-roles-py-RoleRegistry-get]]
- [[eos_ai-substrate-voice_session-py-VoiceSession-append_turn]]
- [[eos_ai-substrate-voice_session-py-VoiceSession-record_role_switch]]
- [[eos_ai-substrate-voice_session-py-VoiceSessionRuntime-_resolve_role]]
- [[eos_ai-substrate-voice_session-py-VoiceSessionStore-get]]
- [[eos_ai-substrate-voice_session-py-VoiceSessionStore-put]]
- [[eos_ai-substrate-voice_session-py-_new_id]]
- [[eos_ai-substrate-voice_session-py-_utcnow]]

## Called By

- [[scripts-substrate_voice_eos_responder_smoke_test-py-main]]
- [[scripts-substrate_voice_session_cli-py-cmd_switch]]
- [[scripts-substrate_voice_session_smoke_test-py-main]]
