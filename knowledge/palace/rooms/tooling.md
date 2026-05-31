---
type: palace-room
room_id: tooling
wing: scripts
generated: 2026-05-31
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
| 1 | [[scripts-_tme_common-py]] | 16 | — | Shared helpers for Tool Mastery Engine system scripts. |
| 2 | [[scripts-orchestrator_status-py]] | 9 | `entry` | orchestrator_status.py — operator-friendly snapshot of the Control Plane. |
| 3 | [[scripts-check_skill_staleness-py]] | 8 | `entry` | check_skill_staleness.py — Tool Mastery Engine staleness audit. |
| 4 | [[scripts-measure_phase8_batch-py]] | 8 | `entry` | Phase 8 batch measurement — full re-extraction. |
| 5 | [[scripts-memory_continuous_sync-py]] | 8 | `entry` | Continuous memory synchronization. |
| 6 | [[scripts-run_reconciliation_ingestion-py]] | 8 | `entry` | Multi-document ingestion with reconciliation. |
| 7 | [[scripts-tool_mastery_manager-py]] | 8 | `entry` | Tool Mastery Manager — CLI. |
| 8 | [[scripts-query_graph-py]] | 7 | `entry` | query_graph.py — Retrieval layer over the EOS codebase knowledge graph. |
| 9 | [[scripts-run_reconciliation_replay_validation-py]] | 7 | `entry` | Reconciliation replay validation. |
| 10 | [[scripts-deferred-py]] | 6 | `entry` | deferred.py — operator CLI for the Control Plane deferred queue. |
| 11 | [[scripts-github_trinity_ingest-py]] | 6 | `entry` | github_trinity_ingest.py — Clone and ingest the three core repos via canonical p |
| 12 | [[scripts-incremental_graph-py]] | 6 | `entry` | incremental_graph.py — Dirty-set incremental updates for the codebase graph. |
| 13 | [[scripts-ingest_conversations-py]] | 6 | `entry` | Batch ingest conversation exports into UMH canonical memory store. |
| 14 | [[scripts-orchestrator_loop-py]] | 6 | `entry` | Orchestrator loop runner. |
| 15 | [[scripts-seed_eos_watermarks_to_now-py]] | 6 | `entry` | Seed EOS watermarks to NOW — skip historical replay on next poller start. |

## Traversal

- Back to wing → [[scripts-wing|scripts wing]]
- Up to palace → [[../index|Memory Palace index]]
- Retrieval rules → [[../../retrieval_rules|retrieval_rules.md]]

## Raw Paths

```
  scripts/_tme_common.py
  scripts/orchestrator_status.py
  scripts/check_skill_staleness.py
  scripts/measure_phase8_batch.py
  scripts/memory_continuous_sync.py
  scripts/run_reconciliation_ingestion.py
  scripts/tool_mastery_manager.py
  scripts/query_graph.py
  scripts/run_reconciliation_replay_validation.py
  scripts/deferred.py
  scripts/github_trinity_ingest.py
  scripts/incremental_graph.py
  scripts/ingest_conversations.py
  scripts/orchestrator_loop.py
  scripts/seed_eos_watermarks_to_now.py
```
