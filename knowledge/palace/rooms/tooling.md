---
type: palace-room
room_id: tooling
wing: scripts
generated: 2026-07-01
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
| 3 | [[scripts-run_c39_simulation-py]] | 10 | `entry` | C39 — Live Gap-Closure Simulation Campaign. |
| 4 | [[scripts-orchestrator_status-py]] | 9 | `entry` | orchestrator_status.py — operator-friendly snapshot of the Control Plane. |
| 5 | [[scripts-run_c40a_campaign-py]] | 9 | `entry` | C40A — Surface Runtime Convergence Campaign. |
| 6 | [[scripts-check_skill_staleness-py]] | 8 | `entry` | check_skill_staleness.py — Tool Mastery Engine staleness audit. |
| 7 | [[scripts-measure_phase8_batch-py]] | 8 | `entry` | Phase 8 batch measurement — full re-extraction. |
| 8 | [[scripts-memory_continuous_sync-py]] | 8 | `entry` | Continuous memory synchronization. |
| 9 | [[scripts-run_c33_benchmarks-py]] | 8 | `entry` | C33 Benchmark Execution — runs all programmatic benchmarks. |
| 10 | [[scripts-run_reconciliation_ingestion-py]] | 8 | `entry` | Multi-document ingestion with reconciliation. |
| 11 | [[scripts-tool_mastery_manager-py]] | 8 | `entry` | Tool Mastery Manager — CLI. |
| 12 | [[scripts-query_graph-py]] | 7 | `entry` | query_graph.py — Retrieval layer over the EOS codebase knowledge graph. |
| 13 | [[scripts-run_reconciliation_replay_validation-py]] | 7 | `entry` | Reconciliation replay validation. |
| 14 | [[scripts-deferred-py]] | 6 | `entry` | deferred.py — operator CLI for the Control Plane deferred queue. |
| 15 | [[scripts-github_trinity_ingest-py]] | 6 | `entry` | github_trinity_ingest.py — Clone and ingest the three core repos via canonical p |

## Traversal

- Back to wing → [[scripts-wing|scripts wing]]
- Up to palace → [[../index|Memory Palace index]]
- Retrieval rules → [[../../retrieval_rules|retrieval_rules.md]]

## Raw Paths

```
  scripts/c40b_phases/campaign_context.py
  scripts/_tme_common.py
  scripts/run_c39_simulation.py
  scripts/orchestrator_status.py
  scripts/run_c40a_campaign.py
  scripts/check_skill_staleness.py
  scripts/measure_phase8_batch.py
  scripts/memory_continuous_sync.py
  scripts/run_c33_benchmarks.py
  scripts/run_reconciliation_ingestion.py
  scripts/tool_mastery_manager.py
  scripts/query_graph.py
  scripts/run_reconciliation_replay_validation.py
  scripts/deferred.py
  scripts/github_trinity_ingest.py
```
