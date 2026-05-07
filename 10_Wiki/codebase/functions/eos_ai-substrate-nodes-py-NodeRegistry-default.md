---
type: codebase-function
file: eos_ai/substrate/nodes.py
line: 213
generated: 2026-05-07
---

# NodeRegistry.default

**File:** [[eos_ai-substrate-nodes-py]] | **Line:** 213
**Signature:** `default() → 'NodeRegistry'`

**Class:** [[eos_ai-substrate-nodes-py-NodeRegistry]]

Process-wide default registry, seeded with the current VPS as the
sole known node. Safe to call multiple times.

## Calls

- [[eos_ai-substrate-nodes-py-NodeRegistry-get]]
- [[eos_ai-substrate-nodes-py-NodeRegistry-upsert]]

## Called By

- [[eos_ai-substrate-execution_router-py-ExecutionRouter-__init__]]
- [[eos_ai-substrate-local_listener-py-LocalListener-_activate]]
- [[eos_ai-substrate-ritual_body-py-_resolve_station]]
- [[eos_ai-substrate-ritual_body-py-run_close_day_body]]
- [[eos_ai-substrate-ritual_body-py-run_open_day_body]]
- [[eos_ai-substrate-ritual_inference-py-_last_successful_scene_for_node]]
- [[eos_ai-substrate-ritual_inference-py-infer_open_scene_hint]]
- [[eos_ai-substrate-station_daemon-py-StationDaemon-__init__]]
- [[eos_ai-substrate-station_readiness-py-_count_unresolved_for_node]]
- [[eos_ai-substrate-station_readiness-py-station_readiness]]
- [[eos_ai-substrate-voice_session-py-VoiceSessionRuntime-_resolve_role]]
- [[eos_ai-substrate-voice_session-py-VoiceSessionRuntime-start_session]]
- [[scripts-substrate_local_listener_smoke_test-py-_fail_terminal_open_days]]
- [[scripts-substrate_local_listener_smoke_test-py-main]]
- [[scripts-substrate_ptt_binding_smoke_test-py-main]]
- [[scripts-substrate_smoke_test-py-main]]
- [[scripts-substrate_transport_report_smoke_test-py-_register_node]]
- [[scripts-substrate_voice_session_smoke_test-py-main]]

## Decorators

- `@classmethod`
