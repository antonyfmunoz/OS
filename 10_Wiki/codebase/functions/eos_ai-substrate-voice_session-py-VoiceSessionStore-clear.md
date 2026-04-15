---
type: codebase-function
file: eos_ai/substrate/voice_session.py
line: 379
generated: 2026-04-12
---

# VoiceSessionStore.clear

**File:** [[eos_ai-substrate-voice_session-py]] | **Line:** 379
**Signature:** `clear() → None`

**Class:** [[eos_ai-substrate-voice_session-py-VoiceSessionStore]]

Test helper. Drops in-memory rows AND the durable payload.

## Calls

- [[eos_ai-substrate-nodes-py-NodeRegistry-_flush]]
- [[eos_ai-substrate-voice_session-py-VoiceSessionStore-_flush]]

## Called By

- [[scripts-substrate_audio_loop_smoke_test-py-main]]
- [[scripts-substrate_discord_text_tts_smoke_test-py-main]]
- [[scripts-substrate_discord_voice_playback_smoke_test-py-main]]
- [[scripts-substrate_discord_voice_transport_smoke_test-py-main]]
- [[scripts-substrate_google_meet_smoke_test-py-main]]
- [[scripts-substrate_meeting_attachment_smoke_test-py-main]]
- [[scripts-substrate_meeting_transport_smoke_test-py-main]]
- [[scripts-substrate_operator_state_smoke_test-py-main]]
- [[scripts-substrate_ptt_binding_smoke_test-py-main]]
- [[scripts-substrate_stt_producer_smoke_test-py-main]]
- [[scripts-substrate_transport_report_smoke_test-py-main]]
- [[scripts-substrate_voice_eos_responder_smoke_test-py-main]]
- [[scripts-substrate_voice_session_smoke_test-py-main]]
- [[scripts-substrate_wake_producer_smoke_test-py-main]]
