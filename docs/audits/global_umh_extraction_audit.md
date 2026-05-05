# Global UMH Extraction Audit

**Generated:** 2026-04-24
**Scope:** Everything outside `/opt/OS/umh/`
**Method:** Static analysis, file inventory, AST review, targeted reads across 4 parallel audit agents
**Status:** Read-only. No files modified, moved, or deleted.

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Total files scanned (non-UMH) | 42,278 |
| Total Python files | 1,040 (418K LOC) |
| Total Markdown files | 5,538 |
| Total TypeScript files | 1,273 |
| UMH current state | 49 Python files (9.7K LOC), 14 modules |
| Extraction candidates found | 147 |
| EXTRACT_NOW | 31 |
| EXTRACT_AFTER_ADAPTER | 24 |
| EXTRACT_PATTERN_ONLY | 28 |
| KEEP_OUT_OF_UMH | 42 |
| ARCHIVE_OR_DELETE_CANDIDATE | 14 |
| NEEDS_MANUAL_REVIEW | 8 |

---

## Table of Contents

1. [Candidate Registry](#1-candidate-registry)
2. [Top 25 Highest-Value Extraction Candidates](#2-top-25-highest-value-extraction-candidates)
3. [Top 25 Patterns to Preserve](#3-top-25-patterns-to-preserve)
4. [Top 25 Things That Must Stay Out of UMH](#4-top-25-things-that-must-stay-out-of-umh)
5. [Top 25 Stale/Dead/Archive Candidates](#5-top-25-staledead-archive-candidates)
6. [Dependency Risk Map](#6-dependency-risk-map)
7. [Recommended Extraction Sequence](#7-recommended-extraction-sequence)
8. [Do Not Touch Yet List](#8-do-not-touch-yet-list)
9. [Proposed Final UMH Product Tree](#9-proposed-final-umh-product-tree)
10. [Proposed Repository Separation](#10-proposed-repository-separation)

---

## 1. Candidate Registry

### 1.1 Primitives / Laws

| # | Source Path | Bucket | UMH Destination | Value | Priority | Confidence |
|---|-----------|--------|----------------|-------|----------|------------|
| 1 | `runtime_legacy/eos_ai/primitives.py` | EXTRACT_PATTERN_ONLY | `umh/primitives/` (already exists) | 13 business primitives library structure | P2 | HIGH |
| 2 | `eos_product/agents/ceo_agent.md` | EXTRACT_PATTERN_ONLY | `umh/docs/patterns/` | Constraint-first objective selection pattern | P2 | HIGH |
| 3 | `knowledge_vault/10_Wiki/concepts/icp-signals.md` | KEEP_OUT_OF_UMH | n/a | ICP-specific psychology (EOS product) | P3 | HIGH |
| 4 | `claude_code_harnessing/PHILOSOPHY.md` | EXTRACT_PATTERN_ONLY | `umh/docs/philosophy.md` | Reality-based principles, unity concept | P3 | MEDIUM |

### 1.2 Signals / Ingestion

| # | Source Path | Bucket | UMH Destination | Value | Priority | Confidence |
|---|-----------|--------|----------------|-------|----------|------------|
| 5 | `runtime_legacy/eos_ai/signal_ingestion.py` | EXTRACT_PATTERN_ONLY | `umh/signal/` (already exists) | Signal normalization protocol | P2 | HIGH |
| 6 | `runtime_legacy/core/connectors/base.py` | EXTRACT_NOW | `umh/signal/connectors/` | Abstract connector + file adapters (JSON, CSV, JSONL) | P1 | HIGH |
| 7 | `runtime_legacy/core/connectors/email.py` | EXTRACT_AFTER_ADAPTER | `umh/signal/connectors/email.py` | Email signal ingestion; needs metric abstraction | P2 | MEDIUM |
| 8 | `runtime_legacy/core/connectors/crm.py` | EXTRACT_AFTER_ADAPTER | `umh/signal/connectors/crm.py` | CRM pipeline connector; needs schema abstraction | P3 | MEDIUM |
| 9 | `runtime_legacy/core/connectors/content.py` | EXTRACT_AFTER_ADAPTER | `umh/signal/connectors/content.py` | Content performance connector | P3 | MEDIUM |
| 10 | `knowledge_vault/01_Inbox/` | KEEP_OUT_OF_UMH | n/a | 600+ processed signals (instance data) | n/a | HIGH |

### 1.3 Intent / Objectives

| # | Source Path | Bucket | UMH Destination | Value | Priority | Confidence |
|---|-----------|--------|----------------|-------|----------|------------|
| 11 | `runtime_legacy/eos_ai/stages/authority.py` | EXTRACT_PATTERN_ONLY | `umh/governance/` | Authority stage pattern (governance check in pipeline) | P2 | HIGH |
| 12 | `runtime_legacy/services/handlers/intent_handler.py` | EXTRACT_PATTERN_ONLY | `umh/intent/` | Intent classification to action dispatch pattern | P2 | MEDIUM |

### 1.4 Context / Composition

| # | Source Path | Bucket | UMH Destination | Value | Priority | Confidence |
|---|-----------|--------|----------------|-------|----------|------------|
| 13 | `runtime_legacy/eos_ai/context_builder.py` | EXTRACT_PATTERN_ONLY | `umh/context/` (done Wave 1A) | 16-layer fault-isolated assembly | P0 | HIGH |
| 14 | `runtime_legacy/eos_ai/platforms/eos/context_builder.py` | KEEP_OUT_OF_UMH | n/a | Role-specific context (EA, CEO, portfolio) | n/a | HIGH |

### 1.5 World Model

| # | Source Path | Bucket | UMH Destination | Value | Priority | Confidence |
|---|-----------|--------|----------------|-------|----------|------------|
| 15 | `runtime_legacy/eos_ai/world_model.py` | EXTRACT_PATTERN_ONLY | `umh/world/` (already exists) | Entity-relation-observation substrate | P1 | HIGH |

### 1.6 Memory / Storage / Retrieval

| # | Source Path | Bucket | UMH Destination | Value | Priority | Confidence |
|---|-----------|--------|----------------|-------|----------|------------|
| 16 | `runtime_legacy/eos_ai/memory.py` | EXTRACT_AFTER_ADAPTER | `umh/memory/` | AgentMemory: persistent logging, token accounting, semantic search | P1 | HIGH |
| 17 | `runtime_legacy/eos_ai/substrate/event_store.py` | EXTRACT_AFTER_ADAPTER | `umh/memory/events.py` | Append-only event store, replay capability | P1 | HIGH |
| 18 | `infra_ops/docs/EVENT_SOURCED_RUNTIME.md` | EXTRACT_PATTERN_ONLY | `umh/docs/patterns/` | Event sourcing: "state is computed, not stored" | P1 | HIGH |
| 19 | `knowledge_vault/10_Wiki/WIKI_RULES.md` | EXTRACT_PATTERN_ONLY | `umh/docs/patterns/` | RAW -> WIKI -> SCHEMA knowledge lifecycle | P2 | HIGH |
| 20 | `knowledge_vault/10_Wiki/palace/` | EXTRACT_PATTERN_ONLY | `umh/docs/patterns/` | Memory palace navigation for large codebases | P3 | MEDIUM |
| 21 | `knowledge_vault/vault/memory/` | KEEP_OUT_OF_UMH | n/a | Conversation logs (instance data) | n/a | HIGH |

### 1.7 Feedback / Learning / Evolution

| # | Source Path | Bucket | UMH Destination | Value | Priority | Confidence |
|---|-----------|--------|----------------|-------|----------|------------|
| 22 | `runtime_legacy/core/optimizer.py` | EXTRACT_NOW | `umh/feedback/optimizer.py` | Self-improvement loop: logs -> proposals -> actions | P1 | HIGH |
| 23 | `eos_product/saas/db/schema.ts` (outcomes) | EXTRACT_PATTERN_ONLY | `umh/feedback/` | Outcome evaluation schema (positive/negative/neutral/skipped) | P2 | HIGH |
| 24 | `eos_product/saas/api/routes/skills.ts` | EXTRACT_PATTERN_ONLY | `umh/feedback/` | Skill versioning + AI-driven improvement suggestions | P2 | MEDIUM |

### 1.8 Capability Routing

| # | Source Path | Bucket | UMH Destination | Value | Priority | Confidence |
|---|-----------|--------|----------------|-------|----------|------------|
| 25 | `runtime_legacy/core/capability.py` | EXTRACT_NOW | `umh/governance/capability.py` | 4-level capability lattice, 13 operation kinds, risk tiers. Pure (no I/O). | P0 | HIGH |
| 26 | `runtime_legacy/core/agent_harness.py` | EXTRACT_NOW | `umh/execution/harness.py` | Unified LLM + action dispatch. HarnessResult contract. | P0 | HIGH |

### 1.9 Governance / Authority / Security

| # | Source Path | Bucket | UMH Destination | Value | Priority | Confidence |
|---|-----------|--------|----------------|-------|----------|------------|
| 27 | `runtime_legacy/core/security/rbac.py` | EXTRACT_NOW | `umh/governance/rbac.py` | Role-based access: admin/operator/viewer/agent | P1 | HIGH |
| 28 | `runtime_legacy/core/security/audit.py` | EXTRACT_NOW | `umh/governance/audit.py` | Append-only hash-chained audit log | P1 | HIGH |
| 29 | `runtime_legacy/core/security/approval.py` | EXTRACT_NOW | `umh/governance/approval.py` | Approval queue + lifecycle for high-risk actions | P1 | HIGH |
| 30 | `runtime_legacy/core/security/execution.py` | EXTRACT_AFTER_ADAPTER | `umh/governance/sandbox.py` | Restricted execution contexts, environment isolation | P2 | MEDIUM |
| 31 | `runtime_legacy/core/security/environments.py` | EXTRACT_AFTER_ADAPTER | `umh/governance/environments.py` | Environment selection (sandbox/production/test) | P2 | MEDIUM |
| 32 | `.claude/hooks/validate_change.py` | EXTRACT_PATTERN_ONLY | `umh/docs/patterns/` | Pre-tool-use risk detection hook | P2 | HIGH |

### 1.10 Execution / Event Systems

| # | Source Path | Bucket | UMH Destination | Value | Priority | Confidence |
|---|-----------|--------|----------------|-------|----------|------------|
| 33 | `runtime_legacy/scripts/action_system.py` | EXTRACT_NOW | `umh/execution/actions/` | Propose -> assess -> approve -> execute -> log. 800 LOC. | P0 | HIGH |
| 34 | `runtime_legacy/core/action_system/` (11 files) | EXTRACT_NOW | `umh/execution/actions/` | Control plane, executor, idempotency, policy, validator, logging | P0 | HIGH |
| 35 | `runtime_legacy/scripts/workflow_engine.py` | EXTRACT_NOW | `umh/execution/workflows.py` | DAG builder + executor. Step models. | P1 | HIGH |
| 36 | `runtime_legacy/scripts/orchestrator.py` | EXTRACT_NOW | `umh/execution/scheduler.py` | Time + event triggers, job queue, retry, auto-disable | P1 | HIGH |
| 37 | `runtime_legacy/eos_ai/execution_spine.py` | EXTRACT_PATTERN_ONLY | `umh/execution/` | 9-stage composable pipeline. SpineResult. | P2 | HIGH |
| 38 | `runtime_legacy/eos_ai/substrate/event_spine.py` | EXTRACT_AFTER_ADAPTER | `umh/execution/events.py` | Event bus + replay | P2 | MEDIUM |
| 39 | `infra_ops/docs/ORCHESTRATOR_DESIGN.md` | EXTRACT_PATTERN_ONLY | `umh/docs/patterns/` | Primitive contract system: requires/produces/guard/idempotent | P1 | HIGH |
| 40 | `runtime_legacy/eos_ai/substrate/task_queue.py` | EXTRACT_AFTER_ADAPTER | `umh/execution/queue.py` | Task queueing + execution | P2 | MEDIUM |

### 1.11 Adapters / Connectors

| # | Source Path | Bucket | UMH Destination | Value | Priority | Confidence |
|---|-----------|--------|----------------|-------|----------|------------|
| 41 | `runtime_legacy/eos_ai/adapters/contracts.py` | EXTRACT_NOW | `umh/adapters/protocol.py` | Adapter protocol: supports() + handle(). AdapterContext. | P1 | HIGH |
| 42 | `runtime_legacy/eos_ai/adapters/umh_execution.py` | EXTRACT_NOW | `umh/adapters/` | UMH execution backend -> spine bridge | P1 | HIGH |
| 43 | `runtime_legacy/eos_ai/adapters/umh_storage.py` | EXTRACT_NOW | `umh/adapters/` | UMH memory <-> Neon bridge | P1 | HIGH |
| 44 | `runtime_legacy/eos_ai/adapters/umh_goals.py` | EXTRACT_NOW | `umh/adapters/` | UMH goals -> EOS objective engine | P1 | HIGH |
| 45 | `runtime_legacy/eos_ai/adapters/umh_strategy.py` | EXTRACT_NOW | `umh/adapters/` | UMH strategy <- EOS goal engine | P1 | HIGH |
| 46 | `eos_product/saas/bridge/agent_bridge.py` | EXTRACT_NOW | `umh/adapters/bridge.py` | REST-to-Python IPC bridge (JSON/stdin/stdout) | P1 | HIGH |
| 47 | `runtime_legacy/eos_ai/adapters/discord_adapter.py` | KEEP_OUT_OF_UMH | n/a | Discord-specific event handling | n/a | HIGH |
| 48 | `runtime_legacy/eos_ai/adapters/notion_adapter.py` | KEEP_OUT_OF_UMH | n/a | Notion-specific API integration | n/a | HIGH |
| 49 | `runtime_legacy/eos_ai/adapters/voice_adapter.py` | EXTRACT_AFTER_ADAPTER | `umh/adapters/voice.py` | STT/TTS protocol (provider-neutral) | P3 | MEDIUM |

### 1.12 LLM / Harnessing

| # | Source Path | Bucket | UMH Destination | Value | Priority | Confidence |
|---|-----------|--------|----------------|-------|----------|------------|
| 50 | `runtime_legacy/eos_ai/model_router.py` | EXTRACT_AFTER_ADAPTER | `umh/adapters/llm_router.py` | Multi-model dispatch + task-type selection + fallback chain | P1 | HIGH |
| 51 | `runtime_legacy/eos_ai/agent_runtime.py` | EXTRACT_PATTERN_ONLY | `umh/execution/` | High-level agent dispatch wrapping spine + memory | P2 | MEDIUM |
| 52 | `claude_code_harnessing/skills/tools/` (122 files) | KEEP_OUT_OF_UMH | separate repo | Tool mastery library (per-tool best practices) | n/a | HIGH |
| 53 | `claude_code_harnessing/skills/meta/tool_mastery_engine/` | EXTRACT_PATTERN_ONLY | `umh/docs/patterns/` | Self-improving tool documentation system | P2 | MEDIUM |
| 54 | `.claude/skills/claude-code-cli.md` | KEEP_OUT_OF_UMH | n/a | Claude Code harness-specific patterns | n/a | HIGH |

### 1.13 Observability / Logging / Testing

| # | Source Path | Bucket | UMH Destination | Value | Priority | Confidence |
|---|-----------|--------|----------------|-------|----------|------------|
| 55 | `runtime_legacy/core/observability.py` | EXTRACT_NOW | `umh/observability/` | Read-only system snapshot. Query logs, agents, proposals. | P1 | HIGH |
| 56 | `runtime_legacy/core/persistent_agents.py` | EXTRACT_NOW | `umh/execution/persistent.py` | PersistentAgent ABC, tick(), state-to-disk, TickResult | P1 | HIGH |
| 57 | `runtime_legacy/tests/test_umh_*.py` (6 files) | EXTRACT_NOW | `tests/` | 267 UMH tests, import isolation, boundary enforcement | P0 | HIGH |
| 58 | `runtime_legacy/parsers/` (6 files) | EXTRACT_NOW | `umh/analysis/parsers/` | Language-agnostic code parsers (Python, JS, TS, SQL, YAML) | P2 | HIGH |
| 59 | `data_artifacts/logs/` | KEEP_OUT_OF_UMH | n/a | Operational telemetry (JSONL, heartbeat) | n/a | HIGH |
| 60 | `logs/orchestrator_heartbeat.json` | EXTRACT_PATTERN_ONLY | `umh/docs/patterns/` | Health heartbeat schema | P3 | MEDIUM |

### 1.14 Configuration / Secrets / Environment

| # | Source Path | Bucket | UMH Destination | Value | Priority | Confidence |
|---|-----------|--------|----------------|-------|----------|------------|
| 61 | `.claude/settings.json` | EXTRACT_PATTERN_ONLY | `umh/docs/patterns/` | Hook architecture (12 trigger types), permission model | P2 | HIGH |
| 62 | `.claude/rules/agents.md` | EXTRACT_PATTERN_ONLY | `umh/docs/patterns/` | Agent definition structure (soul doc vs CC subagent) | P2 | HIGH |
| 63 | `.claude/rules/skills.md` | EXTRACT_PATTERN_ONLY | `umh/docs/patterns/` | Skill metadata structure (trigger/effort/gotchas/verification) | P2 | HIGH |
| 64 | `infra_ops/.env.example` | KEEP_OUT_OF_UMH | n/a | EOS-specific environment variables | n/a | HIGH |

### 1.15 Deployment / Distribution

| # | Source Path | Bucket | UMH Destination | Value | Priority | Confidence |
|---|-----------|--------|----------------|-------|----------|------------|
| 65 | `infra_ops/Dockerfile` | KEEP_OUT_OF_UMH | n/a | EOS-specific Docker build | n/a | HIGH |
| 66 | `infra_ops/docker-compose.yml` | KEEP_OUT_OF_UMH | n/a | 5 EOS services | n/a | HIGH |
| 67 | `infra_ops/setup.sh` | EXTRACT_PATTERN_ONLY | `umh/docs/patterns/` | Interactive setup wizard pattern | P3 | MEDIUM |
| 68 | `.claude/skills/deploy-service.md` | EXTRACT_PATTERN_ONLY | `umh/docs/patterns/` | Deployment decision tree | P3 | MEDIUM |

### 1.16 Knowledge / Templates / Docs

| # | Source Path | Bucket | UMH Destination | Value | Priority | Confidence |
|---|-----------|--------|----------------|-------|----------|------------|
| 69 | `knowledge_vault/14_Templates/` (13 files) | EXTRACT_PATTERN_ONLY | `umh/docs/patterns/` | Note type templates (ICP, lead, client, skill, workflow, daily) | P3 | MEDIUM |
| 70 | `knowledge_vault/05_Workflows/` (12 files) | EXTRACT_PATTERN_ONLY | `umh/docs/patterns/` | Multi-step workflow definitions with triggers | P2 | MEDIUM |
| 71 | `knowledge_vault/10_Wiki/retrieval_rules.md` | EXTRACT_PATTERN_ONLY | `umh/docs/patterns/` | Hierarchical knowledge retrieval strategy | P2 | HIGH |
| 72 | `runtime_legacy/core/ARCHITECTURE_FINAL.md` | EXTRACT_PATTERN_ONLY | `umh/docs/patterns/` | L0-L6 layer architecture, safety model, observability CLI | P1 | HIGH |
| 73 | `CLAUDE.md` (cognition stack) | EXTRACT_PATTERN_ONLY | `umh/docs/patterns/` | 5-layer knowledge hierarchy, retrieval protocol | P1 | HIGH |

### 1.17 Agent Specifications

| # | Source Path | Bucket | UMH Destination | Value | Priority | Confidence |
|---|-----------|--------|----------------|-------|----------|------------|
| 74 | `eos_product/agents/research_agent.md` | EXTRACT_PATTERN_ONLY | `umh/docs/patterns/` | Signal confidence model (3+ sources = high) | P2 | HIGH |
| 75 | `eos_product/agents/executive_assistant.md` | KEEP_OUT_OF_UMH | n/a | Founder attention filter (EOS product) | n/a | HIGH |
| 76 | `eos_product/agents/` (19 total) | KEEP_OUT_OF_UMH | n/a | EOS-specific agent identities | n/a | HIGH |

### 1.18 SaaS / Product Layer

| # | Source Path | Bucket | UMH Destination | Value | Priority | Confidence |
|---|-----------|--------|----------------|-------|----------|------------|
| 77 | `eos_product/saas/db/schema.ts` | EXTRACT_PATTERN_ONLY | `umh/docs/patterns/` | Multi-tenant agent/skill/workflow/outcome data model | P1 | HIGH |
| 78 | `eos_product/saas/api/routes/` (7 files) | KEEP_OUT_OF_UMH | n/a | EOS-specific REST API | n/a | HIGH |
| 79 | `eos_product/saas/db/client.ts` | EXTRACT_PATTERN_ONLY | `umh/docs/patterns/` | withOrg() wrapper for org-scoped transactions | P2 | MEDIUM |
| 80 | `eos_product/products/` (3 stubs) | KEEP_OUT_OF_UMH | n/a | EntrepreneurOS/CreatorOS/LyfeOS product shells | n/a | HIGH |

### 1.19 Orchestrator / Scheduling

| # | Source Path | Bucket | UMH Destination | Value | Priority | Confidence |
|---|-----------|--------|----------------|-------|----------|------------|
| 81 | `orchestrator/approvals/` | EXTRACT_PATTERN_ONLY | `umh/docs/patterns/` | Approval state machine (pending -> approved) | P2 | HIGH |
| 82 | `logs/signals/bindings.json` | EXTRACT_PATTERN_ONLY | `umh/docs/patterns/` | Signal-to-handler binding registry | P2 | MEDIUM |

### 1.20 Substrate / Session / Runtime (200+ files)

| # | Source Path | Bucket | UMH Destination | Value | Priority | Confidence |
|---|-----------|--------|----------------|-------|----------|------------|
| 83 | `runtime_legacy/eos_ai/substrate/session.py` | EXTRACT_PATTERN_ONLY | `umh/execution/session.py` | Session lifecycle pattern | P2 | MEDIUM |
| 84 | `runtime_legacy/eos_ai/substrate/task_system.py` | EXTRACT_AFTER_ADAPTER | `umh/execution/tasks.py` | Task decomposition + execution | P2 | MEDIUM |
| 85 | `runtime_legacy/eos_ai/runtime/lifecycle.py` | EXTRACT_PATTERN_ONLY | `umh/execution/` | Session start -> active -> end lifecycle | P2 | MEDIUM |
| 86 | `runtime_legacy/eos_ai/runtime/lifecycle_hooks.py` | EXTRACT_PATTERN_ONLY | `umh/execution/` | Lifecycle event hooks | P2 | MEDIUM |
| 87-110 | `runtime_legacy/eos_ai/substrate/*` (remaining) | KEEP_OUT_OF_UMH | n/a | Discord/voice/meeting/ritual transport, deeply coupled | n/a | HIGH |

### 1.21 Domain Skills (Claude Code Harnessing)

| # | Source Path | Bucket | UMH Destination | Value | Priority | Confidence |
|---|-----------|--------|----------------|-------|----------|------------|
| 111 | `claude_code_harnessing/skills/Sales/` (27 skills) | KEEP_OUT_OF_UMH | EOS product | Sales workflows (qualify, objection, close) | n/a | HIGH |
| 112 | `claude_code_harnessing/skills/Operations/` (12 skills) | KEEP_OUT_OF_UMH | EOS product | Ops playbooks (lead, investor, deal, issue) | n/a | HIGH |
| 113 | `claude_code_harnessing/skills/Research/` (6 skills) | KEEP_OUT_OF_UMH | EOS product | ICP signal detection, market reports | n/a | HIGH |
| 114 | `claude_code_harnessing/skills/Meta/tool_mastery_engine/` | EXTRACT_PATTERN_ONLY | `umh/docs/patterns/` | Self-improving documentation engine | P2 | HIGH |
| 115 | `claude_code_harnessing/.agents/skills/last30days/` (149 files) | NEEDS_MANUAL_REVIEW | separate repo? | Complex multi-LLM research pipeline | P3 | MEDIUM |

### 1.22 Remaining Candidates (116-147)

| Range | Source Area | Bucket | Summary |
|-------|-----------|--------|---------|
| 116-122 | `runtime_legacy/eos_ai/stages/` (9 stages) | EXTRACT_PATTERN_ONLY | Composable pipeline stage architecture |
| 123-128 | `runtime_legacy/services/` (16 files) | KEEP_OUT_OF_UMH | Discord/Telegram/Instagram bots |
| 129-133 | `runtime_legacy/scripts/scheduled/` | KEEP_OUT_OF_UMH | Cron-safe wrappers for EOS tasks |
| 134-138 | `runtime_legacy/scripts/notion_*` (12 files) | KEEP_OUT_OF_UMH | Notion integration scripts |
| 139-141 | `runtime_legacy/scripts/query_graph.py` etc. | EXTRACT_AFTER_ADAPTER | Graph query CLI |
| 142-145 | `data_artifacts/data/` (state files) | ARCHIVE_OR_DELETE_CANDIDATE | Agent/workflow state snapshots |
| 146-147 | `data_artifacts/backups/` | ARCHIVE_OR_DELETE_CANDIDATE | System backup |

---

## 2. Top 25 Highest-Value Extraction Candidates

Ranked by `(domain independence * production readiness * UMH impact)`.

| Rank | Candidate | Source | Bucket | LOC | Priority | Why |
|------|----------|--------|--------|-----|----------|-----|
| 1 | **Capability System** | `core/capability.py` | EXTRACT_NOW | 300 | P0 | Pure module. 4-level lattice, 13 op kinds, risk tiers. Zero I/O. Drop-in. |
| 2 | **Agent Harness** | `core/agent_harness.py` | EXTRACT_NOW | 400 | P0 | Unified entry point. LLM + action dispatch. HarnessResult contract. |
| 3 | **Action System** | `scripts/action_system.py` + `core/action_system/` | EXTRACT_NOW | 1600 | P0 | Propose -> assess -> approve -> execute -> log. Battle-tested. |
| 4 | **RBAC + Audit** | `core/security/rbac.py` + `audit.py` | EXTRACT_NOW | 500 | P1 | Role-based access + hash-chained audit. Clean separation. |
| 5 | **Approval Queue** | `core/security/approval.py` | EXTRACT_NOW | 250 | P1 | Human consent gate for high-risk actions. |
| 6 | **Optimizer** | `core/optimizer.py` | EXTRACT_NOW | 350 | P1 | Self-improvement: logs -> proposals -> actions. Never mutates directly. |
| 7 | **Observability** | `core/observability.py` | EXTRACT_NOW | 350 | P1 | Read-only system snapshot. Multiple query methods. |
| 8 | **Persistent Agents** | `core/persistent_agents.py` | EXTRACT_NOW | 400 | P1 | PersistentAgent ABC. tick(), state-to-disk, TickResult. |
| 9 | **Adapter Protocol** | `eos_ai/adapters/contracts.py` | EXTRACT_NOW | 50 | P1 | supports() + handle() protocol. AdapterContext. |
| 10 | **UMH Bridge Adapters** | `eos_ai/adapters/umh_*.py` (4 files) | EXTRACT_NOW | 400 | P1 | Execution/storage/goals/strategy bridges. Already UMH-shaped. |
| 11 | **REST-to-Python Bridge** | `eos_product/saas/bridge/agent_bridge.py` | EXTRACT_NOW | 140 | P1 | JSON/stdin IPC. Language-agnostic. |
| 12 | **Workflow Engine** | `scripts/workflow_engine.py` | EXTRACT_NOW | 500 | P1 | DAG builder + executor with step models. |
| 13 | **Orchestrator Scheduler** | `scripts/orchestrator.py` | EXTRACT_NOW | 600 | P1 | Time + event triggers, queue, retry, auto-disable. |
| 14 | **Connector Base** | `core/connectors/base.py` | EXTRACT_NOW | 150 | P1 | Abstract connector + file adapters. |
| 15 | **Code Parsers** | `parsers/` (6 files) | EXTRACT_NOW | 600 | P2 | Python/JS/TS/SQL/YAML parsers. Language-agnostic. |
| 16 | **Model Router** | `eos_ai/model_router.py` | EXTRACT_AFTER_ADAPTER | 300 | P1 | Multi-provider dispatch + fallback chain. Needs provider abstraction. |
| 17 | **Event Store** | `eos_ai/substrate/event_store.py` | EXTRACT_AFTER_ADAPTER | 300 | P1 | Append-only event log + replay. Needs storage abstraction. |
| 18 | **Memory Interface** | `eos_ai/memory.py` | EXTRACT_AFTER_ADAPTER | 200 | P1 | Persistent logging + token accounting + semantic search. Needs DB abstraction. |
| 19 | **Event Sourcing Design** | `infra_ops/docs/EVENT_SOURCED_RUNTIME.md` | EXTRACT_PATTERN_ONLY | doc | P1 | "State is computed, not stored." Full event schema. |
| 20 | **Orchestrator Design** | `infra_ops/docs/ORCHESTRATOR_DESIGN.md` | EXTRACT_PATTERN_ONLY | doc | P1 | Primitive contracts: requires/produces/guard/idempotent/phases. |
| 21 | **L0-L6 Architecture** | `core/ARCHITECTURE_FINAL.md` | EXTRACT_PATTERN_ONLY | doc | P1 | 6-layer architecture, safety model, observability CLI. |
| 22 | **Data Model** | `eos_product/saas/db/schema.ts` | EXTRACT_PATTERN_ONLY | 540 | P1 | Multi-tenant agent/skill/workflow/outcome/interaction schema. |
| 23 | **Cognition Stack** | `CLAUDE.md` (lines 50-74) | EXTRACT_PATTERN_ONLY | 25 | P1 | 5-layer knowledge hierarchy. Retrieval protocol. |
| 24 | **Execution Spine** | `eos_ai/execution_spine.py` | EXTRACT_PATTERN_ONLY | 300 | P2 | 9-stage composable pipeline. SpineResult metadata wrapper. |
| 25 | **Skill Versioning** | `eos_product/saas/api/routes/skills.ts` | EXTRACT_PATTERN_ONLY | 106 | P2 | Version tracking + AI-driven improvement + fitness functions. |

---

## 3. Top 25 Patterns to Preserve

Even where implementation is too coupled for direct extraction, these architectural patterns should be recreated in UMH.

| # | Pattern | Source | Why Preserve |
|---|---------|--------|-------------|
| 1 | **Fault-isolated section assembly** | `context_builder.py` | Each context source in own try/except. One failure never kills the build. |
| 2 | **Propose-assess-approve-execute lifecycle** | `action_system.py` | No uncontrolled mutations. Every change goes through impact assessment. |
| 3 | **Priority-based token budget** | Wave 1A (already in UMH) | Lower-priority sections dropped first when budget exceeded. |
| 4 | **Graph-aware impact assessment** | `action_system/policy.py` | Changes to high-centrality nodes require higher approval. |
| 5 | **Append-only hash-chained audit** | `security/audit.py` | Every authorization decision is immutable and tamper-evident. |
| 6 | **PersistentAgent tick pattern** | `persistent_agents.py` | Long-running agents with state-to-disk. Scheduler calls tick(). |
| 7 | **Composable pipeline stages** | `execution_spine.py` | Stages are independent modules. Can add/remove/reorder. |
| 8 | **Event sourcing (state = computed)** | `EVENT_SOURCED_RUNTIME.md` | Never store derived state. Replay events to rebuild. |
| 9 | **Primitive contracts** | `ORCHESTRATOR_DESIGN.md` | requires/produces/reads/guard/idempotent/side_effects/phase. |
| 10 | **4-level capability lattice** | `capability.py` | READ -> WRITE -> EXECUTE -> CRITICAL with risk tiers. |
| 11 | **Multi-model fallback chain** | `model_router.py` | Try primary -> fallback -> local. Task-type-aware selection. |
| 12 | **Connector normalization protocol** | `connectors/base.py` | fetch_signals() -> normalize() -> RealSignal. Provider-neutral. |
| 13 | **Self-improvement via optimizer** | `optimizer.py` | Reads logs -> proposes improvements -> submits as actions. Never mutates directly. |
| 14 | **Council mode (multi-perspective)** | `.claude/skills/council.md` | N branches, independent agents, diff, synthesize. Disagreement = complexity. |
| 15 | **RAW -> WIKI -> SCHEMA lifecycle** | `WIKI_RULES.md` | Immutable sources -> curated wiki -> structured extraction. |
| 16 | **Memory palace navigation** | `10_Wiki/palace/` | Wings (modules) -> rooms (clusters) -> loci (files). Centrality-ranked. |
| 17 | **Signal confidence calibration** | `research_agent.md` | High (3+ sources), Medium (2), Low (1). |
| 18 | **Session lifecycle hooks** | `runtime/lifecycle_hooks.py` | Start -> active -> end with hooks at each transition. |
| 19 | **Skill metadata structure** | `.claude/rules/skills.md` | Trigger condition, effort level, gotchas, verification step. |
| 20 | **Agent definition duality** | `.claude/rules/agents.md` | Soul doc (identity) vs subagent (mechanics). Never duplicate between them. |
| 21 | **Risk classification hierarchy** | `.claude/CLAUDE.md` | LOW/MEDIUM/HIGH/CRITICAL with specific examples per tier. |
| 22 | **Dynamic context injection** | Skills `!` command pattern | Execute commands at skill-read-time for live context. |
| 23 | **Constraint-first objective selection** | `ceo_agent.md` | One constraint -> one objective per day. Volume before pivoting. |
| 24 | **withOrg() transaction wrapper** | `eos_product/saas/db/client.ts` | Every DB operation scoped to org_id automatically. |
| 25 | **Verification principle** | `CLAUDE.md` (Boris Cherny) | Every task needs a verification step before marking complete. |

---

## 4. Top 25 Things That Must Stay Out of UMH

| # | Item | Source | Why Exclude |
|---|------|--------|-------------|
| 1 | Discord bot code | `services/discord_bot.py` | Platform-specific transport |
| 2 | Telegram control | `services/telegram_control.py` | Platform-specific transport |
| 3 | Instagram DM monitor | `services/dm_monitor.py` | Platform-specific scraping |
| 4 | Notion sync scripts | `scripts/notion_*.py` (12 files) | Product-specific integration |
| 5 | Founder profile data | `data/founder_profile.md` | Instance data |
| 6 | Brand identity content | `data/brand_identity.md` | Instance data |
| 7 | GWS context | `data/gws_context.md` | Instance data |
| 8 | ICP signal database | `knowledge_vault/01_Inbox/` (600+ files) | Instance intelligence |
| 9 | Initiate Arena offer | `knowledge_vault/04_Offers/` | Product-specific |
| 10 | Client profiles | `knowledge_vault/vault/clients/` | Instance CRM data |
| 11 | Venture-specific CEOs | `eos_product/agents/lyfe_institute_ceo.md` etc. | Product-specific agents |
| 12 | Executive assistant soul | `eos_product/agents/executive_assistant.md` | EOS-specific role |
| 13 | Portfolio advisor soul | `eos_product/agents/portfolio_advisor.md` | EOS-specific role |
| 14 | Sales skills library | `claude_code_harnessing/skills/Sales/` | Product-specific workflows |
| 15 | Tool mastery library | `claude_code_harnessing/skills/tools/` (122 files) | CC-harness-specific |
| 16 | Docker compose config | `infra_ops/docker-compose.yml` | EOS-specific deployment |
| 17 | Py-cord voice patch | `infra_ops/patch_pycord.py` | Discord-specific workaround |
| 18 | Operational logs | `data_artifacts/logs/` | Runtime telemetry |
| 19 | Decision logs | `data_artifacts/logs/decisions/` (17 days) | Instance decisions |
| 20 | Codebase graph data | `data_artifacts/data/codebase_graph.json` | Generated artifact |
| 21 | Morning/nightly logs | `data_artifacts/logs/morning_*.log` etc. | Operational output |
| 22 | Substrate transport layer | `eos_ai/substrate/discord_*`, `voice_*`, `meeting_*` | Platform coupling |
| 23 | EOS platform runtime | `eos_ai/platforms/eos/` (11 files) | Platform-specific |
| 24 | Business Instance Spec | `eos_ai/bis.py` | EOS 6-stage model |
| 25 | Venture templates | `claude_code_harnessing/templates/*.json` | EOS product configs |

---

## 5. Top 25 Stale/Dead/Archive Candidates

| # | Item | Source | Status | Evidence |
|---|------|--------|--------|----------|
| 1 | Portfolio Agent (deprecated) | `eos_product/agents/portfolio_agent.md` | DEAD | Replaced by portfolio_advisor |
| 2 | CognitiveLoop | `runtime_legacy/eos_ai/cognitive_loop.py` | DEPRECATED | Only `format_response_footer` used |
| 3 | Execution Bridge (legacy) | `runtime_legacy/core/execution_bridge.py` | DEPRECATED | Superseded by agent_harness |
| 4 | Execution Contract (legacy) | `runtime_legacy/core/execution_contract.py` | DEPRECATED | Wrapped by action_system |
| 5 | Twitter handles list | `archive_candidates/Untitled.md` | STALE | Unknown purpose, 6 handles |
| 6 | Agent state snapshots | `data_artifacts/data/agent_state/` | STALE | Superseded by Neon storage |
| 7 | Workflow state files | `data_artifacts/data/workflow_state/` | STALE | Research/test/retry state files |
| 8 | Action snapshots | `data_artifacts/data/action_snapshots/` | ARCHIVE | Pre-mutation backups (operational) |
| 9 | Optimizer state | `data_artifacts/data/optimizer_state.json` | STALE | Point-in-time snapshot |
| 10 | Orchestrator state | `data_artifacts/data/orchestrator_state.json` | STALE | Point-in-time snapshot |
| 11 | Sandbox smoke report | `data_artifacts/data/sandbox_smoke_report.json` | STALE | One-time test result |
| 12 | Gmail audit | `data_artifacts/data/gmail_audit.json` | STALE | Label inventory snapshot |
| 13 | Morning logs (pre-April) | `data_artifacts/logs/morning_*.log` (early) | ARCHIVE | Historical operational data |
| 14 | Nightly logs (pre-April) | `data_artifacts/logs/nightly_*.log` (early) | ARCHIVE | Historical operational data |
| 15 | Browser test screenshots | `logs/browser_test.png`, `instagram_*.png` | STALE | One-time test artifacts |
| 16 | Crontab rollback snapshots | `infra_ops/docs/audits/rollback/crontab-*.txt` | ARCHIVE | Pre-phase cron backups |
| 17 | Playwright MCP cache | `infra_ops/.playwright-mcp/` (6 files) | STALE | Cached browser sessions |
| 18 | Improvement proposals | `data_artifacts/data/improvement_proposals/` | ARCHIVE | Timestamped snapshots |
| 19 | Tool mastery backlogs | `data_artifacts/logs/tool_mastery_manager/` (12 files) | STALE | Bootstrap snapshots |
| 20 | System backup (March) | `data_artifacts/backups/eos_backup_20260326.tar.gz` | ARCHIVE | Pre-UMH full backup |
| 21 | Graphify overlay | `data_artifacts/data/graphify_overlay.json` | STALE | Visualization state |
| 22 | Memory evolution runs | `data_artifacts/logs/memory_evolution/runs.jsonl` | ARCHIVE | Historical evolution data |
| 23 | Substrate smoke tests | `runtime_legacy/scripts/substrate_*_smoke_test.py` (60+) | ARCHIVE | EOS-specific, not for UMH |
| 24 | Overnight scrape script | `runtime_legacy/services/overnight_scrape.py` | STALE | Scheduled scraper (Instagram) |
| 25 | Skills lock file | `claude_code_harnessing/skills-lock.json` | STALE | External references |

---

## 6. Dependency Risk Map

### Critical Dependency Chains

```
UMH run() 
  ├── umh/context/ (Wave 1A) ──── CLEAN, no external deps
  ├── umh/signal/ ──── CLEAN
  ├── umh/intent/ ──── CLEAN  
  ├── umh/world/ ──── CLEAN
  ├── umh/governance/ ──── CLEAN
  ├── umh/capability/ ──── CLEAN
  ├── umh/feedback/ ──── CLEAN
  └── umh/adapters/base.py ──── get_adapter("llm") → NullLLMAdapter (safe)
```

### Extraction Risk: Runtime Legacy -> UMH

```
core/agent_harness.py
  ├── imports core.capability (CLEAN — extract together)
  ├── imports core.action_system (MODERATE — graph interface abstracted)
  └── lazy-imports eos_ai.memory (HIGH — Neon-coupled)

core/action_system/
  ├── imports core.capability (CLEAN)
  ├── uses graph queries (MODERATE — interface-based)
  └── uses JSONL logging (CLEAN — file-based)

core/security/
  ├── self-contained (CLEAN)
  └── audit.py uses hash chains (CLEAN — stdlib only)

core/optimizer.py
  ├── reads JSONL logs (CLEAN)
  └── submits through action_system (MODERATE — needs action_system first)

scripts/orchestrator.py
  ├── uses watchdog (CLEAN — pip install)
  ├── uses eos_ai.memory (HIGH — Neon-coupled)
  └── uses scripts.workflow_engine (MODERATE — extract together)
```

### Coupling Risk Levels

| Risk | Count | Description |
|------|-------|-------------|
| CLEAN (no external deps) | 8 | capability, observability, parsers, rbac, audit, approval, adapter protocol, connector base |
| MODERATE (interface-based deps) | 6 | agent_harness, action_system, optimizer, workflow_engine, persistent_agents, bridge |
| HIGH (Neon/provider coupling) | 4 | memory, model_router, event_store, orchestrator scheduler |
| BLOCKED (deep integration) | 2+ | substrate transport, platform runtime |

---

## 7. Recommended Extraction Sequence

### Wave 2A: Capability + Governance (P0, CLEAN)
- `core/capability.py` -> `umh/governance/capability.py`
- `core/security/rbac.py` -> `umh/governance/rbac.py`
- `core/security/audit.py` -> `umh/governance/audit.py`
- `core/security/approval.py` -> `umh/governance/approval.py`
- **Effort:** Low. Pure modules, zero I/O, no external deps.
- **Tests needed:** Capability lattice, RBAC enforcement, audit chain integrity, approval lifecycle.

### Wave 2B: Agent Harness (P0, MODERATE)
- `core/agent_harness.py` -> `umh/execution/harness.py`
- **Depends on:** Wave 2A (capability system)
- **Purification:** Replace eos_ai.memory with UMH memory interface. Abstract graph queries.
- **Effort:** Medium. Lazy imports need conversion to UMH protocols.

### Wave 2C: Action System (P0, MODERATE)
- `scripts/action_system.py` + `core/action_system/` -> `umh/execution/actions/`
- **Depends on:** Wave 2A (capability/risk), Wave 2B (harness)
- **Purification:** Graph queries already abstracted. Replace JSONL paths with configurable log path.
- **Effort:** Medium. 1600 LOC but well-modularized.

### Wave 3A: Observability + Optimizer (P1, CLEAN/MODERATE)
- `core/observability.py` -> `umh/observability/`
- `core/optimizer.py` -> `umh/feedback/optimizer.py`
- **Depends on:** Wave 2C (action system for optimizer submission)
- **Effort:** Low-Medium.

### Wave 3B: Scheduling + Workflows (P1, MODERATE)
- `scripts/orchestrator.py` (L6 scheduler) -> `umh/execution/scheduler.py`
- `scripts/workflow_engine.py` -> `umh/execution/workflows.py`
- **Depends on:** Wave 2C (action system)
- **Purification:** Replace eos_ai.memory with UMH memory. Replace watchdog with optional dep.
- **Effort:** Medium.

### Wave 3C: Adapter Protocol + Bridges (P1, CLEAN)
- `eos_ai/adapters/contracts.py` -> `umh/adapters/protocol.py`
- `eos_ai/adapters/umh_*.py` (4 files) -> `umh/adapters/`
- `eos_product/saas/bridge/agent_bridge.py` -> `umh/adapters/bridge.py`
- **Effort:** Low. Already UMH-shaped.

### Wave 4A: Persistent Agents + Connectors (P1-P2)
- `core/persistent_agents.py` -> `umh/execution/persistent.py`
- `core/connectors/base.py` -> `umh/signal/connectors/`
- `parsers/` -> `umh/analysis/parsers/`
- **Effort:** Low. Clean extraction.

### Wave 4B: Storage Adapters (P1, HIGH)
- `eos_ai/memory.py` (interface only) -> `umh/memory/`
- `eos_ai/substrate/event_store.py` -> `umh/memory/events.py`
- `eos_ai/model_router.py` -> `umh/adapters/llm_router.py`
- **Purification:** Abstract Neon to storage protocol. Abstract providers to LLM protocol.
- **Effort:** High. Requires adapter boundary design first.

### Wave 5+: Patterns Only (P2-P3)
- Event sourcing architecture
- Primitive contracts
- Session lifecycle
- Knowledge retrieval hierarchy
- Tool mastery engine pattern

---

## 8. Do Not Touch Yet List

| Item | Reason | When |
|------|--------|------|
| `eos_ai/substrate/` (200+ files) | Too deeply integrated with Discord/voice/meeting. No clean extraction surface. | After UMH has its own session/transport layer. |
| `eos_ai/platforms/eos/` (11 files) | Platform-specific runtime. | Never for UMH; stays in EOS product. |
| `services/` (16 files) | Running production bots. Any touch risks downtime. | After UMH replaces EOS execution layer. |
| `data_artifacts/` (30K files) | Operational telemetry. Reading is fine; moving/deleting risks log continuity. | Archive after UMH is production primary. |
| `knowledge_vault/01_Inbox/` (600+ signals) | Active intelligence pipeline. Instance data, not platform. | Keep in EOS product vault. |
| `claude_code_harnessing/skills/tools/` (122 files) | Active CC harness skills. Touching breaks current CC workflow. | After UMH has its own skill format. |
| `infra_ops/Dockerfile` + `docker-compose.yml` | Running production infrastructure. | After UMH has its own deploy model. |
| `eos_product/saas/` | Active SaaS backend. Shared schema with running Neon DB. | After UMH has its own data layer. |

---

## 9. Proposed Final UMH Product Tree

After all extraction waves complete:

```
umh/
├── __init__.py              # Public API: run()
├── run.py                   # 9-stage execution loop
├── adapters/                # Execution surface bridges
│   ├── base.py              # Adapter registry + null defaults
│   ├── protocol.py          # Adapter protocol (Wave 3C)
│   ├── llm_router.py        # Multi-model dispatch (Wave 4B)
│   ├── bridge.py            # REST-to-Python IPC (Wave 3C)
│   └── voice.py             # STT/TTS protocol (future)
├── analysis/                # Code analysis
│   └── parsers/             # Python/JS/TS/SQL/YAML (Wave 4A)
├── capability/              # Capability routing
│   ├── registry.py          # (existing)
│   └── router.py            # (existing)
├── context/                 # Context composition (Wave 1A - DONE)
│   ├── builder.py           # Fault-isolated assembly
│   ├── budget.py            # Priority-based token truncation
│   └── types.py             # ContextSection, ContextResult, ContextPriority
├── decision/                # Decision tracing (existing)
├── execution/               # Execution layer
│   ├── engine.py            # (existing)
│   ├── harness.py           # Unified LLM + action dispatch (Wave 2B)
│   ├── actions/             # Action system (Wave 2C)
│   │   ├── system.py        # Propose/assess/approve/execute/log
│   │   ├── executor.py      # Filesystem mutation
│   │   ├── policy.py        # Risk assessment
│   │   ├── validator.py     # Pre-execution safety
│   │   ├── idempotency.py   # Deduplication
│   │   └── logging.py       # JSONL audit trail
│   ├── scheduler.py         # Time + event triggers (Wave 3B)
│   ├── workflows.py         # DAG builder + executor (Wave 3B)
│   ├── persistent.py        # PersistentAgent ABC (Wave 4A)
│   └── session.py           # Session lifecycle (future)
├── feedback/                # Feedback + learning
│   ├── loop.py              # (existing)
│   └── optimizer.py         # Self-improvement loop (Wave 3A)
├── goals/                   # Goal management (existing)
├── governance/              # Authority + security
│   ├── authority.py         # (existing)
│   ├── capability.py        # 4-level lattice (Wave 2A)
│   ├── rbac.py              # Role-based access (Wave 2A)
│   ├── audit.py             # Hash-chained audit log (Wave 2A)
│   └── approval.py          # Approval queue (Wave 2A)
├── intent/                  # Intent compilation (existing)
├── memory/                  # Storage + retrieval
│   ├── storage.py           # (existing)
│   ├── events.py            # Event store + replay (Wave 4B)
│   └── interfaces.py        # (existing)
├── observability/           # System monitoring (Wave 3A)
│   └── snapshot.py          # Read-only system state
├── primitives/              # Business primitives (existing)
├── signal/                  # Signal ingestion
│   ├── ingest.py            # (existing)
│   ├── types.py             # (existing)
│   └── connectors/          # Real data ingestion (Wave 4A)
│       └── base.py          # Abstract connector protocol
├── strategy/                # Strategy selection (existing)
└── world/                   # World model (existing)
```

**Post-extraction metrics:**
- Modules: 14 -> 22+
- Python files: 49 -> ~85
- LOC: 9.7K -> ~18K
- Capabilities: 9-stage run loop -> full execution platform with actions, scheduling, workflows, governance, observability

---

## 10. Proposed Repository Separation

### 10.1 UMH (Universal Meta Harness)
**Repo:** `umh` (standalone PyPI package)
**Contents:** Everything in `umh/` after extraction
**Dependencies:** Python stdlib + optional extras (watchdog for scheduler, psycopg2 for Neon adapter)
**Install:** `pip install umh` (core) / `pip install umh[neon]` / `pip install umh[full]`

### 10.2 EOS (EntrepreneurOS Platform)
**Repo:** `eos` (private, depends on UMH)
**Contents:**
- Agent soul documents (19 agents)
- EOS-specific adapters (Discord, Notion, voice)
- Substrate layer (session/task/transport)
- Platform runtime (platforms/eos/)
- Services (bots, webhooks)
- Business primitives content
- Venture templates
**Install:** Uses UMH as library. `from umh import run` replaces `from eos_ai.execution_spine import ExecutionSpine`.

### 10.3 EOS SaaS Frontend
**Repo:** `eos-saas` (TypeScript, depends on EOS API)
**Contents:**
- `eos_product/saas/` (Hono API + Drizzle schema)
- `eos_product/products/` (EntrepreneurOS/CreatorOS/LyfeOS shells)
- Bridge to Python layer

### 10.4 Knowledge Vault (Instance Data)
**Repo:** Private or gitignored
**Contents:**
- `knowledge_vault/` (signals, ICP intelligence, wiki, templates)
- `data_artifacts/` (logs, state, graphs)
- Operational dashboards
**Note:** Never in a shared package. Per-installation.

### 10.5 Claude Code Harnessing
**Repo:** `cc-skills` or bundled with EOS
**Contents:**
- `claude_code_harnessing/skills/` (domain skills + tool skills)
- `.claude/agents/` (CC subagent definitions)
- `.claude/skills/` (harness skills)
- `.claude/rules/` (harness rules)
**Note:** CC-specific. Loads into Claude Code via `.claude/` convention.

### 10.6 LyfeOS / CreatorOS (Future)
**Repos:** `lyfe-os`, `creator-os`
**Depends on:** UMH (core runtime) + EOS SaaS (shared backend)
**Contents:** Product-specific agents, workflows, UI

---

## Confidence Notes

| Area | Confidence | Reason |
|------|-----------|--------|
| Runtime legacy extraction candidates | HIGH | All files read, AST analyzed, dependencies traced |
| EOS product extraction candidates | HIGH | Schema, API, agents fully inventoried |
| Knowledge vault classification | HIGH | Structure mapped, content sampled |
| Claude Code harnessing classification | MEDIUM | 384 files, sampled ~30%. Tool skills not individually read. |
| Data artifacts classification | MEDIUM | 30K files, mostly logs. Sampled structure only. |
| Substrate coupling assessment | MEDIUM | 200+ files. Pattern-level assessment, not line-by-line. |
| LOC estimates | HIGH | Automated counting via find + wc |
| Priority rankings | HIGH | Based on domain independence + production readiness + UMH impact |
| Archive candidates | MEDIUM | Based on naming/dating. Some may have hidden dependencies. |

---

## Biggest Risks

1. **Substrate coupling leak** — Substrate's 200+ files touch everything. Any extraction that accidentally pulls a substrate import breaks UMH's standalone guarantee. Mitigation: AST import scanning on every extraction (existing `test_umh_boundaries.py` pattern).

2. **Neon storage assumption** — 4+ candidates assume psycopg2/Neon. UMH must define a storage protocol first, then adapt Neon as one implementation. Extracting before the protocol exists creates hidden coupling.

3. **Graph query interface** — Action system uses graph queries for impact assessment. The graph is EOS-specific (codebase_graph.json). UMH needs an abstract graph protocol, or the action system's impact assessment degrades to a no-op.

4. **Test coverage gap** — Existing 267 UMH tests cover the current 14 modules. Each extraction wave adds ~2 modules. At current test density (~19 tests/module), each wave needs ~40 new tests. Budget accordingly.

5. **Circular dependency risk** — `agent_harness -> action_system -> capability` is a clean chain. But `orchestrator -> workflow_engine -> action_system -> harness` creates a 4-deep chain. Extract in order or use lazy imports.

---

*Audit complete. 42,278 files scanned. 147 candidates classified. Report written to `docs/audits/global_umh_extraction_audit.md`.*
