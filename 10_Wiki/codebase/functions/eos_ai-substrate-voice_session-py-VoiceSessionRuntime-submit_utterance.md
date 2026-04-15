---
type: codebase-function
file: eos_ai/substrate/voice_session.py
line: 579
generated: 2026-04-12
---

# VoiceSessionRuntime.submit_utterance

**File:** [[eos_ai-substrate-voice_session-py]] | **Line:** 579
**Signature:** `submit_utterance(session_id, text) → Optional[VoiceSession]`

**Class:** [[eos_ai-substrate-voice_session-py-VoiceSessionRuntime]]

Submit a bounded utterance to the active session.

Records the user turn, calls the responder for an agent reply, and
(by default) emits the reply through SPEAK_TEXT so the daemon will
speak it.

## Calls

- [[eos_ai-substrate-nodes-py-NodeRegistry-get]]
- [[eos_ai-substrate-roles-py-RoleRegistry-get]]
- [[eos_ai-substrate-station_helpers-py-propose_speak_text]]
- [[eos_ai-substrate-voice_session-py-VoiceSession-append_turn]]
- [[eos_ai-substrate-voice_session-py-VoiceSessionStore-get]]
- [[eos_ai-substrate-voice_session-py-VoiceSessionStore-put]]
- [[eos_ai-substrate-voice_session-py-_apply_operator_state]]
- [[eos_ai-substrate-voice_session-py-_call_responder]]
- [[eos_ai-substrate-voice_session-py-_log]]
- [[eos_ai-substrate-voice_session-py-_new_id]]
- [[eos_ai-substrate-voice_session-py-_utcnow]]

## Called By

- [[eos_ai-substrate-transcript_inject-py-inject_transcript]]
- [[scripts-substrate_audio_loop_smoke_test-py-main]]
- [[scripts-substrate_operator_state_smoke_test-py-main]]
- [[scripts-substrate_voice_eos_responder_smoke_test-py-main]]
- [[scripts-substrate_voice_session_cli-py-cmd_say]]
- [[scripts-substrate_voice_session_smoke_test-py-main]]
