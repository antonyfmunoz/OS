---
type: palace-room
room_id: tooling
wing: scripts
generated: 2026-05-23
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
| 1 | [[scripts-_tme_common-py]] | 14 | — | Shared helpers for Tool Mastery Engine system scripts. |
| 2 | [[scripts-query_graph-py]] | 9 | `entry` | query_graph.py — Retrieval layer over the EOS codebase knowledge graph. |
| 3 | [[scripts-workflow_engine-py]] | 9 | `entry` | WorkflowEngine — goal-driven, graph-aware, agent-executed workflows. |
| 4 | [[scripts-action_system-py]] | 8 | `entry` | action_system.py — Controlled execution layer on top of the EOS cognition stack. |
| 5 | [[scripts-smoke_eos-py]] | 8 | `entry` | Smoke test — exercises EOS integration polling against a real EOS database. |
| 6 | [[scripts-smoke_eos_phase3-py]] | 7 | `entry` | Smoke test — exercises EOS Phase 3 outcome writeback against a real database. |
| 7 | [[scripts-check_skill_staleness-py]] | 6 | `entry` | check_skill_staleness.py — Tool Mastery Engine staleness audit. |
| 8 | [[scripts-incremental_graph-py]] | 6 | `entry` | incremental_graph.py — Dirty-set incremental updates for the codebase graph. |
| 9 | [[scripts-seed_eos_watermarks_to_now-py]] | 6 | `entry` | Seed EOS watermarks to NOW — skip historical replay on next poller start. |
| 10 | [[scripts-codebase_graph-py]] | 5 | `entry` | codebase_graph.py — Persistent codebase knowledge graph for EOS. |
| 11 | [[scripts-query_skills-py]] | 5 | `entry` | query_skills.py — Tool Mastery Engine CLI registry. |
| 12 | [[scripts-sandbox_safety_verifier-py]] | 5 | `entry` | sandbox_safety_verifier.py — Adversarial tests for the sandbox boundary. |
| 13 | [[scripts-sandbox_smoke_test-py]] | 5 | `entry` | sandbox_smoke_test.py — End-to-end proof that the sandbox layer works. |
| 14 | [[scripts-smoke_notion-py]] | 5 | `entry` | Smoke test — exercises Notion integration operations against a real workspace. |
| 15 | [[scripts-build_palace-py]] | 4 | `entry` | build_palace.py — Generates the EOS memory palace from the graph. |

## Traversal

- Back to wing → [[scripts-wing|scripts wing]]
- Up to palace → [[../index|Memory Palace index]]
- Retrieval rules → [[../../retrieval_rules|retrieval_rules.md]]

## Raw Paths

```
  scripts/_tme_common.py
  scripts/query_graph.py
  scripts/workflow_engine.py
  scripts/action_system.py
  scripts/smoke_eos.py
  scripts/smoke_eos_phase3.py
  scripts/check_skill_staleness.py
  scripts/incremental_graph.py
  scripts/seed_eos_watermarks_to_now.py
  scripts/codebase_graph.py
  scripts/query_skills.py
  scripts/sandbox_safety_verifier.py
  scripts/sandbox_smoke_test.py
  scripts/smoke_notion.py
  scripts/build_palace.py
```
