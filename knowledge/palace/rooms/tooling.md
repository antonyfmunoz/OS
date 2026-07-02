---
type: palace-room
room_id: tooling
wing: scripts
generated: 2026-07-02
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
| 1 | [[scripts-c40b_phases-campaign_context-py]] | 22 | — | C40B Campaign Context — shared state across all phases. |
| 2 | [[scripts-_tme_common-py]] | 16 | — | Shared helpers for Tool Mastery Engine system scripts. |
| 3 | [[scripts-orchestrator_status-py]] | 9 | `entry` | orchestrator_status.py — operator-friendly snapshot of the Control Plane. |
| 4 | [[scripts-check_skill_staleness-py]] | 8 | `entry` | check_skill_staleness.py — Tool Mastery Engine staleness audit. |
| 5 | [[scripts-measure_phase8_batch-py]] | 8 | `entry` | Phase 8 batch measurement — full re-extraction. |
| 6 | [[scripts-memory_continuous_sync-py]] | 8 | `entry` | Continuous memory synchronization. |
| 7 | [[scripts-run_reconciliation_ingestion-py]] | 8 | `entry` | Multi-document ingestion with reconciliation. |
| 8 | [[scripts-tool_mastery_manager-py]] | 8 | `entry` | Tool Mastery Manager — CLI. |
| 9 | [[scripts-validate_w0_coherence_dry-py]] | 8 | `entry` | W0 Dry Validation with Coherence Envelope. |
| 10 | [[scripts-query_graph-py]] | 7 | `entry` | query_graph.py — Retrieval layer over the EOS codebase knowledge graph. |
| 11 | [[scripts-run_reconciliation_replay_validation-py]] | 7 | `entry` | Reconciliation replay validation. |
| 12 | [[scripts-deferred-py]] | 6 | `entry` | deferred.py — operator CLI for the Control Plane deferred queue. |
| 13 | [[scripts-github_trinity_ingest-py]] | 6 | `entry` | github_trinity_ingest.py — Clone and ingest the three core repos via canonical p |
| 14 | [[scripts-incremental_graph-py]] | 6 | `entry` | incremental_graph.py — Dirty-set incremental updates for the codebase graph. |
| 15 | [[scripts-ingest_conversations-py]] | 6 | `entry` | Batch ingest conversation exports into UMH canonical memory store. |

## Traversal

- Back to wing → [[scripts-wing|scripts wing]]
- Up to palace → [[../index|Memory Palace index]]
- Retrieval rules → [[../../retrieval_rules|retrieval_rules.md]]

## Raw Paths

```
  scripts/c40b_phases/campaign_context.py
  scripts/_tme_common.py
  scripts/orchestrator_status.py
  scripts/check_skill_staleness.py
  scripts/measure_phase8_batch.py
  scripts/memory_continuous_sync.py
  scripts/run_reconciliation_ingestion.py
  scripts/tool_mastery_manager.py
  scripts/validate_w0_coherence_dry.py
  scripts/query_graph.py
  scripts/run_reconciliation_replay_validation.py
  scripts/deferred.py
  scripts/github_trinity_ingest.py
  scripts/incremental_graph.py
  scripts/ingest_conversations.py
```
