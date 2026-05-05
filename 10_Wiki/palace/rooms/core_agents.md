---
type: palace-room
room_id: core_agents
wing: core
generated: 2026-04-11
---

# Room — Core Agents

**Wing:** [[core-wing|core]]  
**Palace:** [[../index|EOS Memory Palace]]

## Purpose

Tool mastery author/research agents, execution contract.

## Core Loci

Top-ranked files by dependency centrality, criticality, and entry status.
These are the files you most often need; open them before grepping.

| # | Locus | Score | Flags | One-liner |
|---|-------|-------|-------|-----------|
| 1 | [[core-action_system-control_plane-py]] | 12 | — | Control Plane — the public entry point for the EOS Action System. |
| 2 | [[core-action_system-logging-py]] | 10 | — | Append-only JSONL loggers for execution and decision records. |
| 3 | [[core-orchestrator-steps-py]] | 7 | — | Reusable orchestrator step helpers. |
| 4 | [[core-tool_mastery_manager-coverage-py]] | 7 | — | Unified coverage evaluator for the Tool Mastery Manager. |
| 5 | [[core-action_system-deferred-py]] | 6 | — | Durable persistence for deferred actions. |
| 6 | [[core-orchestrator-loop-py]] | 6 | — | Autonomous loop — deterministic orchestration cycle. |
| 7 | [[core-execution_contract-py]] | 5 | — | ExecutionContract — unified execution entry point for all EOS AI operations. |
| 8 | [[core-orchestrator-orchestrator-py]] | 5 | — | Orchestrator — execution coordinator for named workflows. |
| 9 | [[core-orchestrator-signals-py]] | 4 | — | Signals — filesystem-backed event layer for the orchestrator. |
| 10 | [[core-orchestrator-workflows-py]] | 4 | — | Workflow registry — wires existing Control Plane workflows into the orchestrator |
| 11 | [[core-tool_mastery_author_agent-__main__-py]] | 3 | `entry` |  |
| 12 | [[core-tool_mastery_author_agent-cli-py]] | 3 | `entry` | CLI entry for the Tool Mastery Author Agent. |
| 13 | [[core-tool_mastery_manager-ensure-py]] | 3 | — | ensure_mastery — the primary entry point of the Tool Mastery Manager. |
| 14 | [[core-tool_mastery_research_agent-__main__-py]] | 3 | `entry` |  |
| 15 | [[core-tool_mastery_research_agent-cli-py]] | 3 | `entry` | CLI entry for the Tool Mastery Research Agent. |

## Traversal

- Back to wing → [[core-wing|core wing]]
- Up to palace → [[../index|Memory Palace index]]
- Retrieval rules → [[../../retrieval_rules|retrieval_rules.md]]

## Raw Paths

```
  core/action_system/control_plane.py
  core/action_system/logging.py
  core/orchestrator/steps.py
  core/tool_mastery_manager/coverage.py
  core/action_system/deferred.py
  core/orchestrator/loop.py
  core/execution_contract.py
  core/orchestrator/orchestrator.py
  core/orchestrator/signals.py
  core/orchestrator/workflows.py
  core/tool_mastery_author_agent/__main__.py
  core/tool_mastery_author_agent/cli.py
  core/tool_mastery_manager/ensure.py
  core/tool_mastery_research_agent/__main__.py
  core/tool_mastery_research_agent/cli.py
```
