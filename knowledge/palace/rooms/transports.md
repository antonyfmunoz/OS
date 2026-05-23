---
type: palace-room
room_id: transports
wing: services
generated: 2026-05-23
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
| 1 | [[services-umh-sockets-envelopes-py]] | 71 | — | Envelope dataclasses — the data shapes that cross the socket boundary. |
| 2 | [[services-umh-governance-risk_classes-py]] | 53 | — | Risk classes — domain-specific action classifications that map to governance ris |
| 3 | [[services-umh-sockets-protocols-py]] | 50 | — | Protocol definitions for integration-side contracts. |
| 4 | [[services-umh-control_plane-pipeline-py]] | 28 | — | ExecutionPipeline — the master success loop. |
| 5 | [[services-umh-protocols-signal-py]] | 28 | — | Signal protocol — the universal intake type. Everything enters as a Signal. |
| 6 | [[services-umh-organism-store-py]] | 19 | — | Organism store — JSONL persistence for deliverables, messages, agent state. |
| 7 | [[services-umh-organism-protocols-py]] | 18 | — | Organism protocols — typed contracts for the agent society. |
| 8 | [[services-umh-execution-executor-py]] | 16 | — | Work packet executor — the governed execution pipeline. |
| 9 | [[services-umh-protocols-capability-py]] | 16 | — | Capability protocol — what the substrate CAN do and how to invoke it. |
| 10 | [[services-umh-organism-worker_cell-py]] | 15 | — | Worker cell — bounded task execution through the existing pipeline. |
| 11 | [[services-umh-integrations-eos-tables-py]] | 14 | — | Typed query helpers for EOS database tables. |
| 12 | [[services-umh-integrations-notion-watermarks-py]] | 14 | — | Watermark persistence — JSONL append-log for per-database poll high-water marks. |
| 13 | [[services-umh-memory-candidate_generator-py]] | 14 | — | MemoryCandidateGenerator — stages memory candidates from completed traces. |
| 14 | [[services-umh-organism-advisor-py]] | 14 | — | DEX Advisor cell — the top-level orchestrator of the organism. |
| 15 | [[services-umh-tests-test_e2e-py]] | 14 | `entry` | End-to-end test for UMH subsystems and ExecutionPipeline. |

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
  services/umh/organism/store.py
  services/umh/organism/protocols.py
  services/umh/execution/executor.py
  services/umh/protocols/capability.py
  services/umh/organism/worker_cell.py
  services/umh/integrations/eos/tables.py
  services/umh/integrations/notion/watermarks.py
  services/umh/memory/candidate_generator.py
  services/umh/organism/advisor.py
  services/umh/tests/test_e2e.py
```
