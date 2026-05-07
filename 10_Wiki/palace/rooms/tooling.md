---
type: palace-room
room_id: tooling
wing: scripts
generated: 2026-05-07
---

# Room — Tooling & Scripts

**Wing:** [[scripts-wing|scripts]]  
**Palace:** [[../index|EOS Memory Palace]]

## Purpose

Automation, graph updates, build/verify scripts.

## Core Loci

Top-ranked files by dependency centrality, criticality, and entry status.
These are the files you most often need; open them before grepping.

| # | Locus | Score | Flags | One-liner |
|---|-------|-------|-------|-----------|
| 1 | [[scripts-_tme_common-py]] | 16 | — |  |
| 2 | [[scripts-substrate_audio_loop_smoke_test-py]] | 13 | `entry` | Audio loop smoke test. |
| 3 | [[scripts-substrate_durable_result_smoke_test-py]] | 13 | `entry` | Substrate durable-result smoke test. |
| 4 | [[scripts-substrate_operator_state_smoke_test-py]] | 13 | `entry` | Operator state engine smoke test. |
| 5 | [[scripts-substrate_result_loop_smoke_test-py]] | 12 | `entry` | Substrate station full round-trip smoke test. |
| 6 | [[scripts-substrate_transport_report_smoke_test-py]] | 12 | `entry` | Unified transport report smoke test. |
| 7 | [[scripts-security_smoke_test-py]] | 11 | `entry` | security_smoke_test.py — End-to-end smoke test for core.security. |
| 8 | [[scripts-substrate_stt_producer_smoke_test-py]] | 11 | `entry` | STT producer smoke test. |
| 9 | [[scripts-substrate_voice_session_smoke_test-py]] | 11 | `entry` | Voice session smoke test. |
| 10 | [[scripts-action_system-py]] | 10 | `entry` | action_system.py — Controlled execution layer on top of the EOS cognition stack. |
| 11 | [[scripts-substrate_google_meet_smoke_test-py]] | 10 | `entry` | Google Meet source adapter smoke test. |
| 12 | [[scripts-substrate_ptt_binding_smoke_test-py]] | 10 | `entry` | PTT binding smoke test. |
| 13 | [[scripts-substrate_smoke_test-py]] | 10 | `entry` | Substrate station MVP smoke test. |
| 14 | [[scripts-workflow_engine-py]] | 10 | `entry` | WorkflowEngine — goal-driven, graph-aware, agent-executed workflows. |
| 15 | [[scripts-orchestrator_status-py]] | 9 | `entry` | orchestrator_status.py — operator-friendly snapshot of the Control Plane. |

## Traversal

- Back to wing → [[scripts-wing|scripts wing]]
- Up to palace → [[../index|Memory Palace index]]
- Retrieval rules → [[../../retrieval_rules|retrieval_rules.md]]

## Raw Paths

```
  scripts/_tme_common.py
  scripts/substrate_audio_loop_smoke_test.py
  scripts/substrate_durable_result_smoke_test.py
  scripts/substrate_operator_state_smoke_test.py
  scripts/substrate_result_loop_smoke_test.py
  scripts/substrate_transport_report_smoke_test.py
  scripts/security_smoke_test.py
  scripts/substrate_stt_producer_smoke_test.py
  scripts/substrate_voice_session_smoke_test.py
  scripts/action_system.py
  scripts/substrate_google_meet_smoke_test.py
  scripts/substrate_ptt_binding_smoke_test.py
  scripts/substrate_smoke_test.py
  scripts/workflow_engine.py
  scripts/orchestrator_status.py
```
