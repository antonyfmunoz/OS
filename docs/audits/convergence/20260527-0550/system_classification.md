# System Classification Manifest

**Date:** 2026-05-27
**Branch:** chore/umh-coherence-convergence-20260527-0550

Classification taxonomy:
- **CANONICAL_RUNTIME** — currently running or required by production
- **CANONICAL_FUTURE** — aligned with target architecture, not primary runtime yet
- **EXPERIMENTAL** — valid prototype, not ready
- **HISTORICAL_ARCHIVE** — old but useful reference
- **DEAD_DELETE** — no importers, no runtime path, no unique value

---

## Substrate Layer

| Path | Classification | Evidence |
|------|---------------|----------|
| substrate/types.py | CANONICAL_RUNTIME | Single type system (30+ Pydantic models), imported everywhere |
| substrate/__init__.py | CANONICAL_RUNTIME | Substrate public API, creates governance/router/spine |
| substrate/control_plane/runtime/gateway.py | CANONICAL_RUNTIME | PRIMARY production entry point (Discord → all AI traffic) |
| substrate/control_plane/runtime/cognitive_loop.py | CANONICAL_RUNTIME | Core LLM reasoning engine, inner layer of gateway |
| substrate/control_plane/governance.py | CANONICAL_RUNTIME | ConcreteGovernanceEngine facade |
| substrate/control_plane/router.py | CANONICAL_RUNTIME | Signal lifecycle orchestration |
| substrate/control_plane/memory.py | CANONICAL_RUNTIME | ConcreteMemorySystem wrapper (bugs fixed this session) |
| substrate/control_plane/orchestrator/ | CANONICAL_RUNTIME | Morning/nightly orchestration cycles |
| substrate/control_plane/scheduling/ | CANONICAL_RUNTIME | Daily sync, calendar awareness |
| substrate/control_plane/context/ | CANONICAL_RUNTIME | BIS context loading |
| substrate/execution/spine.py | CANONICAL_RUNTIME | ExecutionSpine Protocol + ConcreteExecutionSpine (async) |
| substrate/execution/trace.py | CANONICAL_RUNTIME | Trace recording + Neon persistence |
| substrate/execution/feedback.py | CANONICAL_RUNTIME | Quality scoring + learning loop |
| substrate/execution/pipeline.py | CANONICAL_FUTURE | Full governed execution pipeline (most complete, not deployed) |
| substrate/execution/runtime/ | CANONICAL_RUNTIME | Worker runtime infra (16 files), used by operator API |
| substrate/execution/bridge/ | CANONICAL_RUNTIME | Session management, memory scope contracts, voice |
| substrate/execution/actuation/ | CANONICAL_FUTURE | Adapter maturity assessment |
| substrate/execution/workers/workstation/ | CANONICAL_FUTURE | Distributed workstation execution (v1 files) |
| substrate/execution/agents/ | CANONICAL_FUTURE | Computer use agent |
| substrate/governance/ | CANONICAL_RUNTIME | 19 files: risk, authority, policy, quality, validation, accountability |
| substrate/state/memory/ | CANONICAL_RUNTIME | AgentMemory + ConversationMemory + canonical store + reconciliation |
| substrate/state/storage/db.py | CANONICAL_RUNTIME | Neon connection layer (RLS-enabled) |
| substrate/state/business/ | CANONICAL_RUNTIME | Business Instance State (BIS) |
| substrate/state/context/ | CANONICAL_RUNTIME | Context loading from env |
| substrate/state/stores/ | CANONICAL_RUNTIME | Embedding store, substrate storage |
| substrate/reality_model/ | CANONICAL_FUTURE | World model + simulation (used by spine for HIGH/CRITICAL risk) |
| substrate/composition/ | CANONICAL_RUNTIME | TME command registry + mastery (45 files) |
| substrate/organism/ | CANONICAL_FUTURE | Multi-agent runtime: daemon, worker cells, handoff, approval |
| substrate/intelligence/ | CANONICAL_FUTURE | IntelligenceRuntime: pattern/decision learning (wired into cognitive_loop) |
| substrate/workstation/ | CANONICAL_FUTURE | Workstation session state management |
| substrate/foundation/ | EXPERIMENTAL | Philosophical layer: identity, beliefs, possibilities, epistemology |
| substrate/memory/ | CANONICAL_FUTURE | Memory lifecycle: candidate generation, promotion, reconciliation, Claude bridge |
| substrate/ontology/ | CANONICAL_RUNTIME | Laws, primitives, relationships |
| substrate/observability/ | CANONICAL_RUNTIME | Error recording, health checks |
| substrate/sockets/ | CANONICAL_RUNTIME | Abstract ports: signal, capability, outcome, view, registry |
| substrate/understanding/ | CANONICAL_RUNTIME | Embedding, deliberation, world model, perception |
| substrate/integrations/ | CANONICAL_RUNTIME | Product connections, health integration |

## Services Layer

| Path | Classification | Evidence |
|------|---------------|----------|
| services/discord_bot.py | CANONICAL_RUNTIME | Primary bot entrypoint, os-discord container |
| services/discord_bot_commands.py | CANONICAL_RUNTIME | Extracted bot commands, imported by discord_bot.py |
| services/discord_message_handlers.py | CANONICAL_RUNTIME | Extracted message handlers |
| services/operator_api.py | CANONICAL_RUNTIME | Operator API, os-operator container |
| services/overnight_scrape.py | CANONICAL_RUNTIME | os-scraper container |
| services/higgsfield_webhook.py | CANONICAL_RUNTIME | Mounted on calendly webhook Flask app |
| services/bridge_health.py | CANONICAL_RUNTIME | Windows bridge health |
| services/trigger_export.py | CANONICAL_RUNTIME | Export trigger |
| services/local_bridge_client.py | CANONICAL_RUNTIME | Windows bridge client |
| services/cc_webhook_receiver.py | HISTORICAL_ARCHIVE | Not imported by production |
| services/cost_tracker.py | HISTORICAL_ARCHIVE | Not imported by production |
| services/export_bridge_handler.py | HISTORICAL_ARCHIVE | Not imported by production |
| services/goal_api.py | HISTORICAL_ARCHIVE | Not imported by production |
| services/heartbeat.py | HISTORICAL_ARCHIVE | Not imported by production |
| services/icp_scorer.py | HISTORICAL_ARCHIVE | Not imported by production |
| services/kpi_tracker.py | HISTORICAL_ARCHIVE | Not imported by production |
| services/local_bridge_server.py | HISTORICAL_ARCHIVE | Not imported by production |
| services/magic_link_handler.py | HISTORICAL_ARCHIVE | Not imported by production |
| services/magic_link_server.py | HISTORICAL_ARCHIVE | Not imported by production |
| services/oauth_device_flow.py | HISTORICAL_ARCHIVE | Not imported by production |
| services/tier_3_fallback.py | HISTORICAL_ARCHIVE | Not imported by production |
| services/browser_adapter.py | HISTORICAL_ARCHIVE | Not imported by production |
| services/auth_flows/ | HISTORICAL_ARCHIVE | Only imported by scripts/fire_export.py |
| services/handlers/ | DEAD_DELETE | Empty directory |
| services/jarvis/ | DEAD_DELETE | Empty directory |
| services/umh/ | DEAD_DELETE | Only contains stale data files, no .py |

## Transports Layer

| Path | Classification | Evidence |
|------|---------------|----------|
| transports/api/cockpit.py | CANONICAL_RUNTIME | Cockpit endpoints, mounted in os-operator |
| transports/api/app.py | CANONICAL_FUTURE | FastAPI app factory (more complete, not deployed) |
| transports/api/operator.py | CANONICAL_RUNTIME | Operator routes |
| transports/api/webhooks/ | CANONICAL_RUNTIME | Calendly webhook (os-webhook container) |
| transports/api/voice.py | CANONICAL_FUTURE | Voice API routes |
| transports/api/computer_use.py | CANONICAL_FUTURE | Computer use API |
| transports/api/distribution.py | CANONICAL_FUTURE | Work distribution API |
| transports/api/workstation.py | CANONICAL_FUTURE | Workstation API |
| transports/node_mesh/ | CANONICAL_RUNTIME | WebSocket mesh server (12 files), umh-mesh systemd service |
| transports/presence/ | CANONICAL_RUNTIME | Discord command dispatch + report handlers |
| transports/discord/ | CANONICAL_RUNTIME | Signal factory, spine integration, utils |

## Projections Layer

| Path | Classification | Evidence |
|------|---------------|----------|
| projections/eos/ | CANONICAL_RUNTIME | EntrepreneurOS projection (30 files): agents, views, workflows, integration |
| projections/creatoros/ | CANONICAL_FUTURE | CreatorOS projection (8 files), structurally complete |
| projections/lyfeos/ | CANONICAL_FUTURE | LyfeOS projection (8 files), structurally complete |

## Application Layer

| Path | Classification | Evidence |
|------|---------------|----------|
| cockpit/ | CANONICAL_RUNTIME | TypeScript/React Electron app, deployed to Fly.io |
| saas/ | CANONICAL_FUTURE | TypeScript Hono API + Drizzle ORM, productized SaaS layer |

## Infrastructure

| Path | Classification | Evidence |
|------|---------------|----------|
| nodes/windows/ | CANONICAL_RUNTIME | Windows node daemon, runs on Beast via Windows Service |
| nodes/environments/ | CANONICAL_FUTURE | Work packet execution environment contracts |
| nodes/distribution/ | CANONICAL_FUTURE | Distributed execution first boot |
| adapters/ | CANONICAL_RUNTIME | 87 files: model routing, GWS, browser, calendar, Notion |
| agents/ | CANONICAL_RUNTIME | Agent soul documents (11 .md files) |

## Operational

| Path | Classification | Evidence |
|------|---------------|----------|
| scripts/ | CANONICAL_RUNTIME | 109 .py + 26 .sh operational scripts |
| scripts/wiki_session_start_hook.py | DEAD_DELETE | Explicitly a no-op |
| scripts/fix_founder_refs.py | DEAD_DELETE | One-time fixer, job done |
| scripts/fix_merge_conflicts.py | DEAD_DELETE | One-time fixer, job done |
| skills/ | CANONICAL_RUNTIME | TME skills (481 .md files), note: skills/saas-dev-skill/ at 5171 files needs audit |
| knowledge/ | CANONICAL_RUNTIME | Wiki, palace, concepts (289 files) |
| knowledge/agents/business | DEAD_DELETE | Broken symlink to /opt/OS/12_Agents |
| knowledge/workflows/business | DEAD_DELETE | Broken symlink to /opt/OS/05_Workflows |
| docs/ | CANONICAL_RUNTIME | Architecture specs, contracts, audits (481 files) |
| data/ | CANONICAL_RUNTIME | Runtime state, proofs, generated data |

## Execution Path Classification

| Path | Name | Status | Classification |
|------|------|--------|---------------|
| A | Gateway → CognitiveLoop | Running (Discord) | CANONICAL_RUNTIME |
| B | CognitiveLoop (inner) | Running (via Gateway) | CANONICAL_RUNTIME |
| C | ConcreteExecutionSpine | Loaded, not deployed | CANONICAL_FUTURE |
| D | ExecutionPipeline | Not deployed | CANONICAL_FUTURE |
| E | Legacy ExecutionSpine | Running (operator API) | CANONICAL_RUNTIME (migrate to C) |

## Governance Classification

| System | Status | Classification |
|--------|--------|---------------|
| ConcreteGovernanceEngine | Production facade | CANONICAL_RUNTIME |
| AuthorityEngine | Production (cognitive loop) | CANONICAL_RUNTIME |
| PolicyEngine | Production (facade + cockpit) | CANONICAL_RUNTIME |
| QualityTransformationGate | Production (gateway output) | CANONICAL_RUNTIME |
| ExecutionAuthorityEngine | WorkPacket path only | CANONICAL_FUTURE |
| SimulationReality | Used by spine for HIGH/CRITICAL | CANONICAL_FUTURE |
| DeliberationCouncil | Used by spine for HIGH/CRITICAL | CANONICAL_FUTURE |
| OutputValidator | Limited wiring | CANONICAL_FUTURE |
| LawRegistry | Wired into understanding bridge | CANONICAL_FUTURE |
| AccountabilityEngine | Production (gateway) | CANONICAL_RUNTIME |
| PrincipleEngine | Production (gateway) | CANONICAL_RUNTIME |
| CompletenessEngine | Pipeline path only | CANONICAL_FUTURE |
| Security module | Production (API) | CANONICAL_RUNTIME |

## Memory Classification

| System | Status | Classification |
|--------|--------|---------------|
| AgentMemory | Production (Neon-backed) | CANONICAL_RUNTIME |
| ConversationMemory | Production (Neon-backed) | CANONICAL_RUNTIME |
| ConcreteMemorySystem | Production wrapper (bugs fixed) | CANONICAL_RUNTIME |
| CanonicalMemoryStore | Append-only JSONL | CANONICAL_FUTURE |
| ReconciliationEngine | JSONL-based reconciliation | CANONICAL_FUTURE |
| MemoryPromoter | Candidate promotion gate | CANONICAL_FUTURE |
| MemoryCandidateGenerator | Candidate staging | CANONICAL_FUTURE |
| AutoReconciler | Bridge to canonical store | CANONICAL_FUTURE |
| ClaudeMemoryBridge | Claude CC → substrate sync | CANONICAL_FUTURE |
| MemoryWatcher | Filesystem watcher daemon | CANONICAL_FUTURE |
| WorldModel | Two-layer world model | CANONICAL_FUTURE |
| RealityModel (canonical/instance) | Graph-based reality | CANONICAL_FUTURE |
| EmbeddingEngine | 3-tier hybrid embedding | CANONICAL_RUNTIME |
| IntelligenceRuntime | Pattern/decision learning | CANONICAL_FUTURE |
| Memory Conflict Governance | Conflict resolution | CANONICAL_FUTURE |

---

## Summary Counts

| Classification | Count |
|---------------|-------|
| CANONICAL_RUNTIME | ~55 subsystems |
| CANONICAL_FUTURE | ~30 subsystems |
| EXPERIMENTAL | 1 (substrate/foundation/) |
| HISTORICAL_ARCHIVE | ~13 (unimported services files) |
| DEAD_DELETE | 6 (empty dirs, broken symlinks, no-op scripts) |
