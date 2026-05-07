---
type: codebase-function
file: eos_ai/substrate/voice_session.py
line: 329
generated: 2026-05-07
---

# VoiceSessionStore.get

**File:** [[eos_ai-substrate-voice_session-py]] | **Line:** 329
**Signature:** `get(session_id) → Optional[VoiceSession]`

**Class:** [[eos_ai-substrate-voice_session-py-VoiceSessionStore]]

*No docstring.*

## Calls

- [[eos_ai-substrate-nodes-py-NodeRegistry-get]]
- [[eos_ai-substrate-roles-py-RoleRegistry-get]]

## Called By

- [[eos_ai-substrate-transcript_inject-py-inject_transcript]]
- [[eos_ai-substrate-voice_eos_responder-py-_system_prompt_for]]
- [[eos_ai-substrate-voice_session-py-VoiceSession-from_dict]]
- [[eos_ai-substrate-voice_session-py-VoiceSessionRuntime-_resolve_role]]
- [[eos_ai-substrate-voice_session-py-VoiceSessionRuntime-end_session]]
- [[eos_ai-substrate-voice_session-py-VoiceSessionRuntime-start_session]]
- [[eos_ai-substrate-voice_session-py-VoiceSessionRuntime-submit_utterance]]
- [[eos_ai-substrate-voice_session-py-VoiceSessionRuntime-switch_role]]
- [[eos_ai-substrate-voice_session-py-VoiceSessionStore-_load]]
- [[eos_ai-substrate-voice_session-py-VoiceSessionStore-stats]]
- [[eos_ai-substrate-voice_session-py-VoiceTurn-from_dict]]
- [[eos_ai-substrate-voice_session-py-voice_session_report]]
- [[eos_ai-substrate-wake_producer-py-WakeProducerHistory-_load]]
- [[eos_ai-substrate-wake_producer-py-WakeProducerHistory-latest]]
- [[eos_ai-substrate-wake_producer-py-WakeProducerRuntime-report]]
- [[scripts-substrate_audio_loop_smoke_test-py-main]]
- [[scripts-substrate_discord_text_tts_smoke_test-py-main]]
- [[scripts-substrate_discord_voice_playback_smoke_test-py-main]]
- [[scripts-substrate_discord_voice_transport_smoke_test-py-main]]
- [[scripts-substrate_google_meet_smoke_test-py-main]]
