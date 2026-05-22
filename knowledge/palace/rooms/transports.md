---
type: palace-room
room_id: transports
wing: services
generated: 2026-05-21
---

# Room — Transports

**Wing:** [[services-wing|services]]  
**Palace:** [[../index|EOS Memory Palace]]

## Purpose

Discord, Telegram, webhooks — how EOS reaches the founder.

## Core Loci

Top-ranked files by dependency centrality, criticality, and entry status.
These are the files you most often need; open them before grepping.

| # | Locus | Score | Flags | One-liner |
|---|-------|-------|-------|-----------|
| 1 | [[services-umh-sockets-envelopes-py]] | 49 | — | Envelope dataclasses — the data shapes that cross the socket boundary. |
| 2 | [[services-umh-governance-risk_classes-py]] | 43 | — | Risk classes — domain-specific action classifications that map to governance ris |
| 3 | [[services-umh-sockets-protocols-py]] | 34 | — | Protocol definitions for integration-side contracts. |
| 4 | [[services-umh-control_plane-pipeline-py]] | 24 | — | ExecutionPipeline — the master success loop. |
| 5 | [[services-umh-protocols-signal-py]] | 16 | — | Signal protocol — the universal intake type. Everything enters as a Signal. |
| 6 | [[services-umh-integrations-eos-tables-py]] | 14 | — | Typed query helpers for EOS database tables. |
| 7 | [[services-umh-integrations-notion-watermarks-py]] | 14 | — | Watermark persistence — JSONL append-log for per-database poll high-water marks. |
| 8 | [[services-umh-memory-candidate_generator-py]] | 14 | — | MemoryCandidateGenerator — stages memory candidates from completed traces. |
| 9 | [[services-umh-tests-test_e2e-py]] | 14 | `entry` | End-to-end test for UMH subsystems and ExecutionPipeline. |
| 10 | [[services-discord_bot-py]] | 13 | `critical` `entry` | EntrepreneurOS Discord Bot — DEX conversational layer. |
| 11 | [[services-umh-observability-trace_store-py]] | 12 | — | TraceStore — append-only JSONL trace persistence. |
| 12 | [[services-umh-protocols-governance-py]] | 12 | — | Governance protocol — decisions about whether and how to execute. |
| 13 | [[services-umh-tests-test_integration-py]] | 12 | `entry` | Integration test — full end-to-end pipeline validation. |
| 14 | [[services-umh-governance-policy_engine-py]] | 11 | — | Policy engine — evaluates risk class + context to produce governance verdicts. |
| 15 | [[services-umh-memory-promoter-py]] | 11 | — | MemoryPromoter — evaluates candidates for promotion to durable storage. |

## Traversal

- Back to wing → [[services-wing|services wing]]
- Up to palace → [[../index|Memory Palace index]]
- Retrieval rules → [[../../retrieval_rules|retrieval_rules.md]]

## Raw Paths

```
  services/umh/sockets/envelopes.py
  services/umh/governance/risk_classes.py
  services/umh/sockets/protocols.py
  services/umh/control_plane/pipeline.py
  services/umh/protocols/signal.py
  services/umh/integrations/eos/tables.py
  services/umh/integrations/notion/watermarks.py
  services/umh/memory/candidate_generator.py
  services/umh/tests/test_e2e.py
  services/discord_bot.py
  services/umh/observability/trace_store.py
  services/umh/protocols/governance.py
  services/umh/tests/test_integration.py
  services/umh/governance/policy_engine.py
  services/umh/memory/promoter.py
```
