---
type: codebase-function
file: eos_ai/substrate/voice_session.py
line: 480
generated: 2026-04-12
---

# VoiceSessionRuntime.start_session

**File:** [[eos_ai-substrate-voice_session-py]] | **Line:** 480
**Signature:** `start_session(node_id, role_slug) → VoiceSession`

**Class:** [[eos_ai-substrate-voice_session-py-VoiceSessionRuntime]]

Start a new voice session targeting `node_id` with `role_slug`.

Validates: node exists in the registry, role exists in the role
registry. Either failure produces an ERROR session that is still
persisted so the operator can see what happened.

## Calls

- [[eos_ai-substrate-nodes-py-NodeRegistry-default]]
- [[eos_ai-substrate-nodes-py-NodeRegistry-get]]
- [[eos_ai-substrate-roles-py-RoleRegistry-default]]
- [[eos_ai-substrate-roles-py-RoleRegistry-get]]
- [[eos_ai-substrate-voice_session-py-VoiceSession-append_turn]]
- [[eos_ai-substrate-voice_session-py-VoiceSessionRuntime-_resolve_role]]
- [[eos_ai-substrate-voice_session-py-VoiceSessionStore-get]]
- [[eos_ai-substrate-voice_session-py-VoiceSessionStore-put]]
- [[eos_ai-substrate-voice_session-py-_apply_operator_state]]
- [[eos_ai-substrate-voice_session-py-_new_id]]
- [[eos_ai-substrate-voice_session-py-_utcnow]]

## Called By

- [[eos_ai-substrate-transcript_inject-py-inject_transcript]]
- [[eos_ai-substrate-wake_producer-py-WakeProducerRuntime-_handle_wake_word]]
- [[scripts-substrate_discord_voice_playback_smoke_test-py-main]]
- [[scripts-substrate_discord_voice_transport_smoke_test-py-main]]
- [[scripts-substrate_meeting_transport_smoke_test-py-main]]
- [[scripts-substrate_transport_report_smoke_test-py-main]]
- [[scripts-substrate_voice_eos_responder_smoke_test-py-main]]
- [[scripts-substrate_voice_session_cli-py-cmd_start]]
- [[scripts-substrate_voice_session_smoke_test-py-main]]
