---
type: codebase-function
file: eos_ai/substrate/station_bus.py
line: 105
generated: 2026-05-07
---

# StationBus.drain_inbox

**File:** [[eos_ai-substrate-station_bus-py]] | **Line:** 105
**Signature:** `drain_inbox(node_id) → list[dict]`

**Class:** [[eos_ai-substrate-station_bus-py-StationBus]]

Read and clear the node's inbox, returning everything the daemon
wrote since the last drain. Each entry has a `"type"` discriminator
of either `"result"` or `"event"`.

## Calls

- [[eos_ai-substrate-station_bus-py-StationBus-_inbox]]
- [[eos_ai-substrate-station_bus-py-_atomic_write_json]]
- [[eos_ai-substrate-station_bus-py-_read_json]]

## Called By

- [[eos_ai-substrate-station_drainer-py-drain_all]]
- [[eos_ai-substrate-station_drainer-py-drain_node]]
- [[eos_ai-substrate-station_drainer-py-drain_results]]
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
