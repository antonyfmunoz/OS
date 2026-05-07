---
type: codebase-function
file: eos_ai/substrate/station_bus.py
line: 122
generated: 2026-05-07
---

# StationBus.daemon_take_outbox

**File:** [[eos_ai-substrate-station_bus-py]] | **Line:** 122
**Signature:** `daemon_take_outbox(node_id) → list[dict]`

**Class:** [[eos_ai-substrate-station_bus-py-StationBus]]

Daemon-side: read and clear the outbox in one atomic swap.

## Calls

- [[eos_ai-substrate-station_bus-py-StationBus-_outbox]]
- [[eos_ai-substrate-station_bus-py-_atomic_write_json]]
- [[eos_ai-substrate-station_bus-py-_read_json]]

## Called By

- [[eos_ai-substrate-station_daemon-py-StationDaemon-_tick]]
- [[scripts-substrate_audio_loop_smoke_test-py-main]]
- [[scripts-substrate_discord_text_tts_smoke_test-py-_bootstrap_shared_node]]
- [[scripts-substrate_discord_voice_playback_smoke_test-py-main]]
- [[scripts-substrate_discord_voice_transport_smoke_test-py-main]]
- [[scripts-substrate_drainer_smoke_test-py-main]]
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
