---
type: palace-room
room_id: core_agents
wing: core
generated: 2026-05-07
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
| 1 | [[core-primitives-py]] | 26 | — | L0 Ontological Primitives — the immutable atoms of EOS. |
| 2 | [[core-action_system-control_plane-py]] | 14 | — | Control Plane — the public entry point for the EOS Action System. |
| 3 | [[core-capability-py]] | 14 | — | capability.py — Permission + risk matrix for the unified EOS AI OS. |
| 4 | [[core-action_system-logging-py]] | 12 | — | Append-only JSONL loggers for execution and decision records. |
| 5 | [[core-environment-py]] | 12 | — | environment.py — Execution environment model for the EOS AI OS sandbox layer. |
| 6 | [[core-orchestrator-pipeline-py]] | 10 | — | Pipeline — sequential composition of Control Plane actions. |
| 7 | [[core-composer-py]] | 9 | — | Composition Engine — converts intent + context into executable primitive structu |
| 8 | [[core-domain-eos-py]] | 9 | — | EOS domain compositions — L2 business structures mapped to L0 primitives. |
| 9 | [[core-security-cli-py]] | 9 | `entry` | cli.py — Operator CLI for the EOS security layer. |
| 10 | [[core-orchestrator-steps-py]] | 7 | — | Reusable orchestrator step helpers. |
| 11 | [[core-tool_mastery_manager-coverage-py]] | 7 | — | Unified coverage evaluator for the Tool Mastery Manager. |
| 12 | [[core-action_system-deferred-py]] | 6 | — | Durable persistence for deferred actions. |
| 13 | [[core-connectors-base-py]] | 6 | — | Connector Base — common interface for real data ingestion. |
| 14 | [[core-orchestrator-loop-py]] | 6 | — | Autonomous loop — deterministic orchestration cycle. |
| 15 | [[core-security-environments-py]] | 6 | — | environments.py — Environment policy layer for the security module. |

## Traversal

- Back to wing → [[core-wing|core wing]]
- Up to palace → [[../index|Memory Palace index]]
- Retrieval rules → [[../../retrieval_rules|retrieval_rules.md]]

## Raw Paths

```
  core/primitives.py
  core/action_system/control_plane.py
  core/capability.py
  core/action_system/logging.py
  core/environment.py
  core/orchestrator/pipeline.py
  core/composer.py
  core/domain/eos.py
  core/security/cli.py
  core/orchestrator/steps.py
  core/tool_mastery_manager/coverage.py
  core/action_system/deferred.py
  core/connectors/base.py
  core/orchestrator/loop.py
  core/security/environments.py
```
