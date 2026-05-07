---
type: codebase-function
file: eos_ai/substrate/station_daemon.py
line: 165
generated: 2026-05-07
---

# StationDaemon.register

**File:** [[eos_ai-substrate-station_daemon-py]] | **Line:** 165
**Signature:** `register() → Node`

**Class:** [[eos_ai-substrate-station_daemon-py-StationDaemon]]

Upsert this node into NodeRegistry so EOS can see it as alive.

## Calls

- [[eos_ai-substrate-nodes-py-NodeRegistry-upsert]]
- [[eos_ai-substrate-station_bus-py-_log]]
- [[eos_ai-substrate-station_daemon-py-_log]]

## Called By

- [[eos_ai-substrate-station_daemon-py-StationDaemon-_emit_heartbeat]]
- [[eos_ai-substrate-station_daemon-py-StationDaemon-run]]
- [[scripts-substrate_audio_loop_smoke_test-py-main]]
- [[scripts-substrate_discord_text_tts_smoke_test-py-_bootstrap_shared_node]]
- [[scripts-substrate_discord_voice_playback_smoke_test-py-main]]
- [[scripts-substrate_discord_voice_transport_smoke_test-py-main]]
- [[scripts-substrate_durable_result_smoke_test-py-main]]
- [[scripts-substrate_google_meet_smoke_test-py-main]]
- [[scripts-substrate_local_listener_smoke_test-py-main]]
- [[scripts-substrate_meeting_attachment_smoke_test-py-main]]
- [[scripts-substrate_meeting_transport_smoke_test-py-main]]
- [[scripts-substrate_operator_state_smoke_test-py-main]]
- [[scripts-substrate_ptt_binding_smoke_test-py-main]]
- [[scripts-substrate_result_loop_smoke_test-py-main]]
- [[scripts-substrate_smoke_test-py-main]]
- [[scripts-substrate_stt_producer_smoke_test-py-main]]
- [[scripts-substrate_transport_report_smoke_test-py-_register_node]]
- [[scripts-substrate_voice_eos_responder_smoke_test-py-main]]
- [[scripts-substrate_voice_session_smoke_test-py-main]]
- [[scripts-substrate_wake_producer_smoke_test-py-main]]
