# Exhaustive System Audit — /opt/OS (UMH)

Generated: 2026-05-14
Purpose: Complete inventory of every file and directory for onboarding a new contributor.

---

## Executive Summary

UMH (Universal Meta Harness) is a **governed intelligence operating system** — a single-tenant AI substrate running on a VPS that manages the founder's business operations through an AI persona (DEX) via Discord. It is NOT a chatbot. It is a cognitive executive layer with memory, governance, multi-model routing, scheduled autonomy, and domain-specific intelligence.

### Key Numbers

| Metric | Value |
|--------|-------|
| Active Python files | 874 |
| Total Python LOC | ~273,000 |
| Top-level packages (§24 architecture) | 12 |
| External tools integrated | 96 |
| Agent soul documents | 18 |
| Reusable skills | 165 |
| Cron jobs (scheduled automation) | 30 |
| Docker services | 5 (2 actively running) |
| Neon PostgreSQL tables | ~20 |
| Wiki pages (auto-generated + curated) | 6,035 |
| Documentation files | 430+ |
| Test files | 116 (~48,500 LOC) |

### How It Works (30-Second Version)

1. **Founder types in Discord** → Discord bot (`services/discord_bot.py`) receives message
2. **Intent classification** → routes through EOS Gateway (`control_plane/runtime/gateway.py`)
3. **Cognitive processing** → 8-stage cognitive loop (perceive → remember → reason → plan → execute → learn → reflect → respond)
4. **LLM routing** → `execution/runtime/model_router.py` picks best available model (CC SDK/Opus → Gemini → Groq → Ollama)
5. **Response with governance** → output validated, chunked to Discord limits, posted back
6. **Background automation** → 30 cron jobs handle meetings, inbox, KPIs, research, memory consolidation

### Architecture Diagram (§24 Layer Map)

```
interface/          ← Human-facing surfaces (Discord bot, webhooks, channels)
control_plane/      ← Central coordination (gateway, router, signals, events, strategy)
state/              ← All persistent state (memory, DB, context, stores, metrics)
execution/          ← Work execution (model routing, transport, workers, environments)
adapters/           ← External system boundaries (GWS, Notion, Higgsfield, scrapling)
governance/         ← Policy enforcement (authority, quality, validation, principles)
observability/      ← System health (provider health, dashboards)
understanding/      ← Perception & knowledge (ingestion, intelligence, ontology, research)
composition/        ← Tool Mastery Engine (research, authoring, management)
learning/           ← Self-improvement (feedback loops, evolution, skill rewriting)
distribution/       ← Multi-node (empty, future)
onboarding/         ← New org setup (empty, future)
```

---

## Part 1: Interface Layer (15 files, 6,590 LOC)

The external surface — handles inbound events and outbound communication.

```
interface/
  api/webhooks/calendly_webhook.py     434 LOC  Calendly booking/cancellation handler
  channels/channel.py                  452 LOC  Abstract channel system + ChannelRouter
  discord/discord_utils.py             172 LOC  Discord posting helpers + message chunking
  presence/handlers/
    cc_command_handler.py              563 LOC  Inline Discord bang commands
    intent_handler.py                  380 LOC  Intent classification + gateway routing
    pipeline_handler.py                138 LOC  NL pipeline stage detection → Notion CRM
    substrate_command_handler.py      4424 LOC  UMH substrate commands (!chrome-proof, !ingest, reports)
    voice_handler.py                    22 LOC  Placeholder for voice extraction
```

**Key insight**: `substrate_command_handler.py` is 67% of the layer's code — it's the primary command surface for UMH substrate operations (30+ commands, system reports, governance routing).

---

## Part 2: Control Plane (96 files, ~25,000 LOC)

Central nervous system — coordinates all work through typed protocols, signal hierarchies, and governance invariants.

### control_plane/actions/ (5 files, 1,250 LOC)
Core action lifecycle: propose → classify → approve → execute → log.

| File | LOC | Purpose |
|------|-----|---------|
| `action_types.py` | 300 | ActionType enum (50+ action types across 8 domains) |
| `control_plane.py` | 489 | ControlPlaneAction orchestrator — intake, risk classification, execution |
| `decision_log.py` | 205 | Immutable decision audit trail (Neon `decisions` table) |
| `deferred_queue.py` | 255 | Retry-aware deferred action queue (Neon `deferred_actions` table) |

### control_plane/events/ (3 files, 765 LOC)
Event-driven coordination between subsystems.

| File | LOC | Purpose |
|------|-----|---------|
| `event_bus.py` | 467 | Pub/sub event bus with typed subscribers + Neon persistence |
| `event_types.py` | 298 | Typed event definitions (meeting, pipeline, system, content) |

### control_plane/invariants/ (6 files, 1,850 LOC)
Hard system guarantees that cannot be violated.

| File | LOC | Purpose |
|------|-----|---------|
| `coherence_gate.py` | 42 | Pass/fail coherence check before any execution |
| `spine_coherence_validator.py` | 191 | Validates lineage chain integrity (fail-closed) |
| `spine_lineage_contracts.py` | 364 | 15-stage canonical spine model + typed contracts |
| `spine_lineage_introspection_v1.py` | 408 | Query/analysis over lineage chains |
| `system_invariants.py` | 455 | Hard constraints (no fabrication, no silent override, audit trail) |
| `invariant_enforcement_engine_v1.py` | 390 | Runtime enforcement of declared invariants |

### control_plane/protocols/ (14 files, 5,120 LOC)
Typed interfaces that all components must conform to.

Key protocols: `GovernanceProtocol`, `ExecutionProtocol`, `MemoryProtocol`, `ObservabilityProtocol`, `TransportProtocol`, `ValidationProtocol`, `FederationProtocol`, `IntrospectionProtocol`, `CapabilityProtocol`, `AuthorityProtocol`, `EvolutionProtocol`, `CommunicationProtocol`.

### control_plane/router/ (3 files, 1,470 LOC)
Deterministic routing engine — maps capabilities to adapters, validates work packets.

| File | LOC | Purpose |
|------|-----|---------|
| `control_plane_router_v1.py` | 1080 | Main router: capability → adapter resolution, packet validation |
| `routing_types.py` | 210 | Routing enums and typed data contracts |
| `routing_intelligence_v1.py` | 180 | Routing strategy selection |

### control_plane/runtime/ (4 files, 4,700 LOC)
The "hot path" — cognitive loop and gateway.

| File | LOC | Purpose |
|------|-----|---------|
| `cognitive_loop.py` | 1870 | 8-stage cognitive processing (PERCEIVE through RESPOND) |
| `gateway.py` | 2074 | EOSGateway — primary entry point for all AI work |
| `context_engine.py` | 430 | Dynamic context assembly for each LLM call |
| `signal_processor.py` | 326 | Signal classification and priority routing |

### control_plane/signals/ (2 files, 730 LOC)
Priority-based signal system triggering cognitive work.

### control_plane/strategy/ (3 files, 2,100 LOC)
Strategic reasoning: constraint diagnosis, leverage identification, portfolio allocation.

### control_plane/scheduling/ (5 files, 1,870 LOC)
Temporal coordination: schedule management, conflict detection, day structure.

### control_plane/registry/ (3 files, 930 LOC)
Dynamic registry for agents, capabilities, and services.

---

## Part 3: State Layer (61 files, ~18,000 LOC)

All persistent state. Nothing writes to the database without going through this layer.

### state/storage/ (2 files)
| File | LOC | Purpose |
|------|-----|---------|
| `db.py` | 234 | Neon PostgreSQL connection pool (psycopg2) — THE single DB entry point |

### state/memory/ (2 files)
| File | LOC | Purpose |
|------|-----|---------|
| `memory.py` | 812 | AgentMemory + ConversationMemory — canonical memory write path (Law 5.5) |

### state/context/ (2 files)
| File | LOC | Purpose |
|------|-----|---------|
| `context.py` | 584 | SystemContext — BIS (Business Instance State) loaded from Neon at runtime |

### state/stores/ (14 domain stores)
Each wraps a specific Neon table with typed read/write methods:

| Store | Table | Domain |
|-------|-------|--------|
| `approval_store.py` | `approvals` | Human approval queue |
| `conversation_store.py` | `conversations` | Chat history |
| `email_folder_store.py` | `email_folders` | Gmail GPS folders |
| `entity_link_store.py` | `entity_links` | Knowledge graph edges |
| `event_store.py` | `events` | Generic event log |
| `goal_store.py` | `goals` | Goal lifecycle |
| `higgsfield_store.py` | `higgsfield_jobs` | Video generation jobs |
| `lead_store.py` | `leads` | CRM leads |
| `meeting_store.py` | `meetings` | Meeting records |
| `metrics_store.py` | `metrics` | Business metrics |
| `outcome_store.py` | `outcomes` | Action outcomes |
| `pipeline_store.py` | `pipeline` | Sales pipeline |
| `skill_store.py` | `skills` | Skill registry |
| `task_store.py` | `tasks` | Task lifecycle |

### state/business/ (4 files, ~2,200 LOC)
Business context: venture knowledge, BIS loading, stage system.

### state/finance/ (2 files, ~900 LOC)
Financial tracking: expense tracker, buyback time audit.

### state/metrics/ (3 files, ~700 LOC)
Founder performance metrics, KPI aggregation.

### state/providers/ (2 files, ~500 LOC)
LLM provider state: failure tracking, backpressure, budget enforcement.

### state/registries/ (2 files, ~400 LOC)
Runtime registries for skills and agents.

### state/work/ (2 files, ~400 LOC)
Idle/pressure detection for the cognitive loop.

### state/transformation_state_ledger.py (1 file, ~450 LOC)
Ingestion pipeline state machine with lineage, rollback, and replay.

---

## Part 4: Execution Layer (198 files, ~65,000 LOC)

Work execution — the largest layer by file count and LOC.

### execution/runtime/ (28 files, ~13,000 LOC)
Core execution machinery.

| File | LOC | Purpose |
|------|-----|---------|
| `model_router.py` | 890 | Multi-model LLM routing: cc_sdk → Gemini → Groq → Ollama |
| `agent_runtime.py` | 650 | Agent execution with soul doc injection |
| `execution_spine.py` | 480 | Governed execution spine (authority → gate → dispatch → proof) |
| `gateway.py` | 2074 | (Also in control_plane — dual reference) |
| `worker_supervisor_v1.py` | 310 | Autonomous worker lifecycle management |
| `node_sync_gate_v1.py` | 420 | Ensures local state matches canonical before execution |
| `workpacket_execution_gate_v1.py` | 350 | Structural validation before work packet execution |
| `action_execution_contracts.py` | 280 | Typed contracts for action lifecycle |
| `execution_contracts_v1.py` | 250 | Execution environment contracts |
| `worker_runtime_contracts.py` | 180 | Worker authority domains, env types, heartbeats |

### execution/transport/ (68 files, ~23,000 LOC)
Communication and relay infrastructure:
- `storage.py` — SubstrateStorage (file-based transport layer)
- `discord_mode_routing.py` — Maps Discord channels to execution modes
- `session_registry.py` — Active session tracking
- `coordination_intelligence.py` — Multi-agent coordination
- `station_daemon.py` — Background station management
- `temporal_intelligence.py` — Time-aware reasoning
- `resource_context_guard.py` — Memory/token budget enforcement
- Plus 60+ substrate transport modules for voice, relay, execution

### execution/workers/workstation/ (35 files, ~22,500 LOC)
Constitutional governance engines (proof-only, not runtime-enforced):
- `constitutional_substrate_governance_layer_v1.py` — 4-layer governance (safety, authority, continuity, emergency)
- `constitutional_antifragility_resilience_engine_v1.py` — Evolutionary resilience patterns
- `constitutional_epistemic_intelligence_engine_v1.py` — Knowledge quality tracking
- `constitutional_identity_continuity_engine_v1.py` — Identity preservation
- `constitutional_resource_economics_engine_v1.py` — Resource allocation
- `constitutional_strategic_intelligence_engine_v1.py` — Strategic forecasting
- `constitutional_telos_alignment_engine_v1.py` — Purpose alignment
- Plus adaptive governance, federation, operationalization, and continuity engines

### execution/environments/ (26 files, ~7,500 LOC)
Multi-environment execution support:
- Work packets (typed work units with risk classification)
- VPS-local bridge (Windows workstation relay)
- Chrome/GUI actuation (visible browser operations with proof)
- Heartbeat and health monitoring
- Environment mapping (platform/account discovery)

### execution/agents/ (5 files, ~3,000 LOC)
Specialized agent implementations: browser agent, content agent, research agent.

---

## Part 5: Adapters Layer (34 files, ~8,600 LOC)

External system boundaries. Each adapter wraps ONE external API and exposes a clean internal interface.

### adapter_engine/ (9 files, 2,663 LOC)
Adapter infrastructure: lifecycle management, registry, ingestion pipelines, decomposition engines.

Key files:
- `adapter_lifecycle_manager_v1.py` — Health states (AVAILABLE/BUSY/DEGRADED/OFFLINE)
- `live_drive_docs_ingestion_pipeline_v1.py` — Full governed ingestion from Drive/Docs (735 LOC)
- `google_docs_adapter_v1.py` — Dual extraction paths (CU + API)
- `google_drive_adapter_v1.py` — Bounded metadata reads

### google_workspace/ (6 files, 3,570 LOC)
Core GWS integration:
- `gws_connector.py` (1,034 LOC) — Wraps `npx @googleworkspace/cli` for Calendar/Drive/Gmail/Tasks
- `email_gps.py` (1,431 LOC) — Dan Martell's 7-folder email system
- `gws_scanner.py` (702 LOC) — Document discovery + relevance assessment + ingestion
- `doc_creator.py` (366 LOC) — Briefing doc generation
- `document_filer.py` (137 LOC) — Attachment classification

### Other Adapters

| Subdirectory | Files | Purpose | External System |
|--------------|-------|---------|-----------------|
| `calendar/` | 2 | Meeting lifecycle + travel logistics | Google Calendar |
| `data_source_adapters/` | 2 | Ingestion source protocol wrappers | GWS, local files |
| `higgsfield/` | 1 | Video/image generation | Higgsfield Cloud API |
| `model_adapters/` | 1 | Claude Code CLI wrapper (464 LOC) | Anthropic (via Max subscription) |
| `notebooklm/` | 1 | Bidirectional memory sync | Google NotebookLM |
| `notion/` | 2 | CRM + content write layer | Notion API |
| `scrapling/` | 1 | Stealth web scraping | HTTP targets |

---

## Part 6: Governance Layer (15 files, ~2,524 LOC)

Policy enforcement — ensures authority, quality, and accountability on all actions.

| Subdirectory | Files | Purpose |
|--------------|-------|---------|
| `accountability/` | 1 | Founder commitment tracking |
| `policies/` | 1 | Confidentiality detection |
| `policy/` | 3 | Authority engine (risk classification), authority tiers (T1-T9), execution authority (multi-dimensional evaluation) |
| `principles/` | 1 | Principle injection into every AI decision (ROOT_RULE + domain principles) |
| `quality/` | 1 | 4-value quality gate (Reality/Intelligence/Personalization/Execution) |
| `validation/` | 1 | Pre-ship output validation (length, empty, generic, hardcoded values) |

---

## Part 7: Observability Layer (6 files, ~967 LOC)

System monitoring and health.

| File | LOC | Purpose |
|------|-----|---------|
| `health/provider_health.py` | 200 | LLM provider availability gate (Gemini, Groq, Ollama, CC SDK) |
| `health/system_health.py` | 438 | Full system health monitor (quality, chain, feedback, training data) |
| `status/status.py` | 329 | Daily operational dashboard (venture progress, skill stats, orchestrator history) |

---

## Part 8: Understanding Layer (46 files, ~10,300 LOC)

Perception, interpretation, knowledge management, and ontological decomposition.

### perception/ (9 files, ~1,720 LOC)
The canonical ingestion pipeline — single entry point for all document ingestion:

- `orchestrator.py` (1,151 LOC) — **GenericIngestionOrchestrator**: perceive → interpret → decompose → bridge → map → persist → query_back
- `source.py` (33 LOC) — Source protocol
- `parsers/` (7 files) — Language-specific code parsers (Python AST, JS/TS regex, SQL, config)

### domains/ (4 files, ~356 LOC)
Domain bridge system — maps ontology observations to domain-typed projections:
- `contract.py` — DomainBridge protocol + DomainProjection dataclass
- `registry.py` — Plugin registry for bridges
- `business.py` — Business domain bridge (sales, hiring, marketing mapping)

### ontology/ (2 files, ~1,058 LOC)
Core UMH substrate ontology:
- `primitive_decomposition_v1.py` — 10 primitive types (state/change/constraint/resource/signal/action/outcome/feedback/goal/time)
- `primitives.py` — Stage-aware business rules engine with 20+ populated primitives

### intelligence/ (5 files, ~2,049 LOC)
Active intelligence gathering:
- `person_recognition.py` (614 LOC) — Cross-channel person identification
- `human_intelligence.py` (708 LOC) — Behavioral profiling engine
- `input_intelligence.py` (339 LOC) — Input quality assessment + enhancement
- `competitive_intel.py` (143 LOC) — Competitor signal tracking
- `stakeholder_map.py` (245 LOC) — Stakeholder tracking per venture

### knowledge/ (3 files, ~1,887 LOC)
Knowledge accumulation and domain awareness:
- `knowledge_domains.py` (1,126 LOC) — 30 knowledge domains with trigger words
- `knowledge_graph.py` (521 LOC) — Entity relationship graph layer
- `knowledge_integrator.py` (240 LOC) — Permanent knowledge storage + embedding

### interpretation/ (1 file, 551 LOC)
5-stage interpretation pipeline: observation → pattern → primitive → hypothesis → uncertainty.

### embedding/ (2 files, 469 LOC)
Three-tier hybrid embedding: fastembed local → Gemini cloud → keyword fallback.

### Other Subdirectories

| Subdirectory | Files | Purpose |
|--------------|-------|---------|
| `patterns/` | 2 | Behavioral pattern detection (leverage killers, avoidance) |
| `reality/` | 2 | Market intelligence layer (6-hour scan cycle) |
| `research/` | 1 | Autonomous knowledge gap detection + research |
| `signals/` | 1 | Task/idea/reminder capture from Discord |
| `world_model/` | 1 | Two-layer world model (canonical + instance) |
| `world_pulse/` | 1 | Market + creator monitoring (daily + Saturday full scan) |

---

## Part 9: Composition Layer (44 files, ~7,930 LOC)

The Tool Mastery Engine (TME) — research, author, manage, and verify tool skill knowledge.

### mastery/research/ (18 files, ~4,990 LOC)
Source-grounded research — discovers, fetches, and structures primary documentation for tools. No fabrication.

Key files:
- `agent.py` — Research Agent orchestrator
- `extraction.py` (1,265 LOC) — Structured knowledge extraction via pure-Python regex
- `artifact.py` (608 LOC) — Produces research_artifact.json + summary.md + sources.md
- `source_discovery.py` (362 LOC) — Multi-source discovery (URLs, registry, GitHub, sitemap)
- `structured_crawl.py` (436 LOC) — Bounded 1-hop link following from approved entry points
- `docs_site_discovery.py` (609 LOC) — Sitemap.xml + /llms.txt probing

### mastery/authoring/ (10 files, ~2,030 LOC)
Consumes research artifacts, drafts/refreshes tool skill files. Every claim traceable to a raw capture.

Key files:
- `agent.py` — Author Agent orchestrator (loader → mapping → draft → reconcile → verify)
- `mapping.py` (609 LOC) — Section-to-evidence mapping via keyword scanning (no LLM)
- `draft.py` (451 LOC) — Renders evidence as markdown with `[SOURCE: url]` markers

### mastery/management/ (11 files, ~1,832 LOC)
Unification layer: discovery, coverage evaluation, scaffolding, queue, mastery assurance gating.

Key files:
- `ensure.py` — Primary entry point (evaluate coverage → scaffold → queue action)
- `mastery_assurance.py` (265 LOC) — Gate blocking tool execution without fresh mastery pack
- `tool_mastery_resolver.py` (325 LOC) — NL tool detection from text

### registries/ (1 file, 425 LOC)
`canonical_command_registry_v1.py` — Single source of truth for all substrate commands.

---

## Part 10: Learning Layer (9 files, ~2,400 LOC)

Self-improvement — closes the loop between recommendations and outcomes.

| Subdirectory | File | LOC | Purpose |
|--------------|------|-----|---------|
| `evolution/` | `evolution_engine.py` | 852 | Stage-primitive lifecycle + weekly system evolution (Saturdays) |
| `feedback/` | `feedback_loop.py` | 446 | Recommendation → outcome tracking + effectiveness stats |
| `self_model/` | `self_awareness.py` | 666 | Auto-reorganization on state changes (14 ChangeTypes) |
| `skills/` | `skill_improvement.py` | 440 | RLHF-driven skill rewriting from outcome data (Mondays) |

---

## Part 11: Services (11 files, 7,954 LOC)

Production daemons — the entrypoints. Intelligence lives in the layers above.

| File | LOC | Container | Purpose |
|------|-----|-----------|---------|
| `discord_bot.py` | 5,223 | `os-discord` | Primary AI interface (DEX). 60+ commands, voice recording, substrate routing |
| `icp_scorer.py` | 603 | `os-scraper` | Scores Instagram comments against ICP using Haiku |
| `overnight_scrape.py` | 251 | `os-scraper` | Nightly scrape orchestration with cost budgets |
| `cost_tracker.py` | 414 | (library) | API cost tracking (Anthropic, Apify, Gemini) |
| `kpi_tracker.py` | 411 | (library) | Sales KPI tracking + EOD Telegram reports |
| `cc_webhook_receiver.py` | 239 | `os-discord` | Receives CC stop-hook replies → Discord channel |
| `heartbeat.py` | 113 | (cron) | Periodic health monitoring |
| `goal_api.py` | 194 | (Flask) | Goal management REST API on port 8090 |
| `higgsfield_webhook.py` | 131 | `os-webhook` | Higgsfield Cloud API webhook receiver |
| `local_bridge_client.py` | 133 | `os-discord` | Forwards Discord messages to local Windows machine via Tailscale |
| `local_bridge_server.py` | 242 | (local) | Receives forwarded messages on Windows, injects into CC tmux |

### discord_bot.py Architecture (5,223 LOC)

The single most important file. Running 24/7 in `os-discord` container:
- Auto-joins founder's voice channel, uses Groq Whisper for STT
- 900+ line `on_message` handler with multi-part accumulation, pipeline detection, venture disambiguation
- 60+ commands: meetings, day ops, calendar, email, CRM, Notion sync, content, finances, approvals, system
- `DiscordServerManager` — idempotent channel/category structure creation
- CC reply webhook receiver (port 8765) for bidirectional Claude Code ↔ Discord
- Session watcher for tmux pane monitoring (plan mode, permission requests)

---

## Part 12: Operations (7 files, 2,436 LOC)

Memory consolidation pipeline — the "sleep/dream" layer.

| File | LOC | Purpose |
|------|-----|---------|
| `memory/salience.py` | 600 | Deterministic heuristic scoring (no LLM) — weighted signals |
| `memory/memory_neon.py` | 565 | Neon DB helpers for memory pipeline |
| `memory/summarize_conversations.py` | 508 | LLM-powered conversation summarization |
| `memory/promote_to_wiki.py` | 438 | Promotes durable knowledge from summaries → 10_Wiki/ |
| `memory/nightly_consolidation.py` | 325 | Full nightly pipeline orchestrator |

---

## Part 13: Scripts (155 files, 38,878 LOC)

Operator tooling — the largest directory by file count.

### Cron-Triggered (22 scripts)

| Schedule | Script | What |
|----------|--------|------|
| `*/5` | `orchestrator_loop.py` | Signal drain + orchestration cycle |
| `*/5` | `agent_task_executor.py` | Pending AI task execution |
| `*/5` | `day_reminder.py` | Event reminders |
| `*/15` | `call_prep.py` | Pre-call briefings |
| `*/15` | `notion_tasks_sync.py` | Notion ↔ Neon sync |
| `*/15` | `post_meeting_capture.py` | Post-meeting outcome prompts |
| `*/15` | `calendar_invite_handler.py` | Calendar invite triage |
| `*/15` | `noshow_detector.py` | No-show detection + recovery |
| `*/15` | `notion_sync_poller.py` | Notion push/pull |
| `0 3` | `discord_daily_clear.py` | Channel cleanup |
| `0 3` | `emit_signal.py nightly_cycle` | Nightly consolidation trigger |
| `30 3` | `shim_retirement_monitor.py` | Shim usage monitoring |
| `45 5` | `morning_intel.py` | Morning intelligence brief |
| `30 5` | `emit_signal.py morning_ready` | Morning prep trigger |
| `5 6` | `waiting_on_checker.py` | Stale email alerts |
| `10 6` | `deadline_monitor.py` | Deadline alerts |
| `30 12` | `midday_checkin.py` | Midday check-in |
| `0 15` | `inbox_gps_afternoon.py` | Afternoon inbox pass |
| `0 18` | `eod_sync.py` | End-of-day closing loop |
| `0 6 Sun` | `portfolio_brief.py` | Sunday portfolio brief |
| `0 7 Mon` | `relationship_nurture.py` | Monday relationship check |
| `0 19 Sun` | `weekly_review.py` | Sunday weekly review |

### Other Script Categories

| Category | Count | Total LOC | Examples |
|----------|-------|-----------|---------|
| Substrate smoke tests | 38 | ~11,000 | Audio loop, voice transport, execution trace, meeting intelligence |
| Codebase graph/knowledge | 14 | ~4,900 | `codebase_graph.py` (1,213 LOC), `build_palace.py`, `query_graph.py` |
| TME scripts | 11 | ~2,000 | Research dispatcher, author, staleness sweep, quality audit |
| Orchestration/execution | 10 | ~4,100 | `orchestrator.py` (1,124 LOC), `workflow_engine.py` (1,177 LOC), `action_system.py` (1,240 LOC) |
| Notion setup | 8 | ~4,200 | Per-venture database creation, seeding, workspace building |
| Proof scripts (W0) | 7 | ~2,900 | Routed Chrome execution, memory query, doc extraction |
| CC hooks | 8 | ~870 | Session start/stop, prompt capture, permission notify |
| Operator CLIs | 11 | ~1,900 | Substrate operator, audio, session, voice, trace, EOS unified |
| Validation/reconciliation | 6 | ~1,400 | Continuity, operationalization, replay |
| Sandbox | 3 | ~1,400 | Runner, safety verifier, smoke test |
| Utilities | 8 | ~600 | Env upsert, fix merge conflicts, BIS context |

---

## Part 14: Tests (116 files, ~48,500 LOC)

Comprehensive test suite organized by domain:

| Category | Files | LOC | What They Cover |
|----------|-------|-----|-----------------|
| Constitutional engines | 10 | ~12,800 | Governance, resilience, epistemic, identity, economics, strategy, telos, federation |
| Workstation/relay | 13 | ~5,300 | Heartbeat, packet validation, bridge, relay transport, GUI embodiment |
| Ingestion pipeline | 13 | ~5,100 | Orchestrator E2E, decomposition, authority tier, domain bridge, GWS source |
| Execution fabric | 9 | ~3,700 | Control plane router, action contracts, execution loop, authority engine |
| W0 proof tests | 4 | ~1,200 | Drive/Docs interaction, extraction, ingestion candidates, packet routing |
| Adapter/registry | 7 | ~2,400 | Registry contracts, autogeneration, propagation, command sync |
| CC SDK | 4 | ~500 | Error leak, subprocess env, timeout, provider state |
| Memory/state | 7 | ~2,500 | Canonical query, reconciliation, domain stores, ledger |
| Goal/cognitive | 6 | ~3,100 | Goal selector, priority decay, cross-goal learning, strategic horizon |
| Migration-pinning | 8 | ~1,100 | Pins completed migrations against regression |
| TME | 4 | ~800 | Active tool context, mastery assurance, NL resolver |
| Substrate runtime | 9 | ~5,500 | Live runtime, identity, operationalization, wiring, continuity |
| Discord/interface | 3 | ~1,500 | Interface adapter, Discord-to-local execution, day detection |
| Windows/GUI | 8 | ~3,000 | Desktop adapter, Chrome launch, visible actuation, maturity model |

---

## Part 15: Core (13 files, 5,974 LOC) — Legacy

Architecturally dead weight from pre-migration era. Only `core/paths.py` (61 LOC) remains actively used.

| File | LOC | Replaced By |
|------|-----|-------------|
| `paths.py` | 61 | Still active — canonical path resolver |
| `advisor.py` | 864 | `execution/runtime/model_router.py` |
| `agent_harness.py` | 741 | `execution/runtime/model_router.py` + direct calls |
| `capability.py` | 510 | `governance/policy/*` |
| `coord_assignment.py` | 416 | Graph-first retrieval hierarchy |
| `environment.py` | 534 | `execution/environments/*` |
| `execution_contract.py` | 385 | `execution/runtime/execution_spine.py` |
| `observability.py` | 408 | Discord bot status commands |
| `optimizer.py` | 652 | `scripts/orchestrator.py` |
| `persistent_agents.py` | 566 | Cognitive loop handles agent work |
| `semantic_space.py` | 509 | Palace → Graph → Summaries hierarchy |
| `wiki_navigation.py` | 328 | Palace/room system |

Plus 20 empty subdirectories (scaffolded for namespace migration, never populated).

---

## Part 16: Runtime (4 files, 808 LOC) — Shim Layer

| File | LOC | Status |
|------|-----|--------|
| `transport/__init__.py` | 28 | Active shim → proxies to `execution.transport` |
| `ingestion/__init__.py` | 1 | Vestigial (real ingestion at `understanding.perception.orchestrator`) |
| `interfaces/discord_interface_adapter_v1.py` | 503 | Active — Discord commands → ControlPlaneRouter via WorkPackets |
| `interfaces/discord_spine_integration_v1.py` | 276 | Active — Full governed spine execution from Discord |

---

## Part 17: Non-Python — Configuration & Infrastructure

### Root Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | 5 services: os-bot, os-monitor, os-scraper, os-webhook, os-discord |
| `Dockerfile` | Python 3.11-slim + git + ffmpeg + Node 20 + torch + whisper + Playwright + Claude Code CLI |
| `pyproject.toml` | Package def for `universal-meta-harness` v0.1.0. Core + voice + telegram + scraping + agents optional groups |
| `Makefile` | `test-migration` and `test-migration-offline` targets |
| `ARCHITECTURE.md` | Master spec: 15 principles, entity model, intelligence layers, agent hierarchy, stage system (23KB) |
| `PHILOSOPHY.md` | Foundation: Reality is Unity, 4 meta-patterns, cross-system vision (12KB) |
| `PROTOCOLS.md` | 4-layer protocol architecture (L0-L3) (8.5KB) |
| `cloud.md` | Session bootstrap context (knowledge system layers + query commands) |
| `patch_pycord.py` | Build-time fix for py-cord `_MissingSentinel` crashes |

### config/ (17 files)
Governance/proof configurations for workpacket zero + tool mastery seeds/exclusions + runtime configs for router, Discord adapter, and local worker.

### .claude/ (Claude Code Configuration)
- **4 subagents**: code-reviewer, researcher, simplifier, verifier
- **22 slash commands**: session-start, morning-brief, deploy, status, build, audit, fix, sync, council, outreach, etc.
- **11 CC-native skills**: browser-control, deploy-service, discord-admin, neon-db, new-agent, etc.
- **8 hooks**: PreToolUse (risk warning), PostToolUse (import check + ruff format), SessionStart (context load), Stop (condition check), PermissionRequest (notify), SubagentStart, UserPromptSubmit (capture)
- **3 rules**: python.md, agents.md, skills.md

### infra/
- `cron/crontab.current` — 25+ scheduled jobs
- `docker/` — .env files, compose, Dockerfile (mirrors root)

---

## Part 18: Non-Python — Knowledge & Content

### 10_Wiki/ (6,035 files)
LLM-maintained knowledge base following Karpathy's RAW > WIKI > SCHEMA pattern:
- `codebase/` (5,804 files) — Auto-generated from codebase graph (one .md per node)
- `concepts/` (135 files) — Recurring ideas and frameworks
- `synthesis/` (37 files) — Cross-topic synthesis
- `entities/` (29 files) — People, companies, products
- `palace/` (18 files) — Memory palace rooms (navigation aids for retrieval)
- `decisions/` (6 files) — Recorded decisions with rationale

### vault/ (752 files)
Obsidian vault for operational dashboards + agent memory:
- `dashboard/` — Dataview-powered dashboards (Home, Clients, Content, Product, Sales)
- `memory/conversations/` — 700+ conversation memory files
- `memory/summaries/` — Conversation summaries
- `daily/` — Daily notes

### agents/ (19 files)
18 agent soul documents + index. Each defines character, judgment, role boundary, communication standard, hard stops. Not mechanics — those live in Python.

Key agents: CEO, EA, Developer, Content, Sales, Outreach, Research, Intelligence, Finance, Operations, Customer Success, Marketing, Portfolio Advisor + 3 venture-specific CEOs.

### skills/ (165 total)
| Category | Count | Purpose |
|----------|-------|---------|
| `tools/` | 96 | External tool mastery (one per tool/API/platform) |
| `Sales/` | 20 | Qualify, DM, follow-up, close, objection handling |
| `Ops/` | 13 | Deal closed, investor inquiry, no-show recovery |
| `meta/` | 9 | TME, operationalization, CC best practices |
| `saas-dev-skill/` | 7 | TypeScript/React patterns |
| `Research/` | 6 | ICP signal detection, market reports |
| `Marketing/` | 4 | Campaign diagnosis, content calendar |
| `content/` | 3 | Performance analysis, script generation |
| Others | 7 | Customer success, outreach, developer, legacy |

### docs/ (430+ files)
| Subdirectory | Files | Content |
|--------------|-------|---------|
| `system/` | 93 | Architecture, ingestion contracts, TME, governance, W0 work orders |
| `operations/` | 182 | Adapter doctrines, GWS, worker bridge, Computer Use, Initiate Arena |
| `audits/` | 155 | Historical audit reports from Phase 0 through current |
| `strategy/` | 10 | Company map, empire architecture, product map |
| `canonical/` | 1 | `umh_synthesis.md` — THE canonical reference (226KB source) |
| `migrations/` | 6 | Migration plans (core→substrate, eos_ai→substrate, etc.) |
| `plans/` | 3 | Execution backend, unification, phase 1 wiring |
| `superpowers/` | 10 | Plans + specs for operator session spine, runtime workstation |
| `mvp/` | 2 | Golden paths, operator guide |

### Obsidian Directories

| Directory | Purpose |
|-----------|---------|
| `01_Inbox/` | Raw signal capture inbox |
| `03_CRM/` | Pipeline and lead management (markdown files per lead) |
| `04_Offers/` | Offer definitions (Initiate Arena = $750 90-day program) |
| `05_Workflows/` | Multi-step workflow definitions for agents |
| `07_Knowledge/` | ICP intelligence + market research outputs |
| `09_Content/` | Content ideas and filming briefs |
| `14_Templates/` | Obsidian note templates |

---

## Part 19: SaaS Projection (TypeScript)

Early-stage EntrepreneurOS web application:
- **Stack**: Hono (API framework) + Drizzle ORM + Neon PostgreSQL + TypeScript
- **Files**: ~8 source files (api/index.ts, db/schema.ts, db/client.ts, etc.)
- **Status**: Schema defined, API scaffolded, not in production

---

## Part 20: Data Directory (Runtime State)

### Canonical Memory Store
`data/runtime/canonical_memory_store/memories.jsonl` — 63 entries:
- 43 STRUCTURED (full ontology observations)
- 10 TEXT_BLOB (legacy, preserved)
- 2 PARTIAL
- 8 domain projections (business:sales)
- 10 proof directories documenting pipeline validation

### File-Based Message Bus
```
data/runtime/local_worker_runtime/    inbox/ processed/ failed/
data/runtime/spine_dispatch_queue/    inbox/ outbox/ archive/ results/
data/work_queue/                      inbox/ outbox/ archive/ results/ heartbeats/
```

### Knowledge Graph
- `data/codebase_graph.json` — Full AST-derived dependency graph
- `data/node_summaries.json` — One-line summary per graph node
- `data/palace.json` — Memory palace serialization

### Operational Logs
```
data/control_plane_log.jsonl    data/advisor_log.jsonl
data/workflow_log.jsonl          data/harness_log.jsonl
data/orchestrator_log.jsonl      data/orchestrator_state.json
```

---

## Part 21: External System Dependencies

| System | Adapter | Env Vars | Purpose |
|--------|---------|----------|---------|
| Neon PostgreSQL | `state/storage/db.py` | `DATABASE_URL` | All persistent state |
| Claude Code CLI | `adapters/model_adapters/cc_sdk.py` | `CLAUDE_CODE_OAUTH_TOKEN` | Primary LLM (Opus 4.6 via Max subscription, no API cost) |
| Google Gemini | via `model_router.py` | `GEMINI_API_KEY` | Fallback LLM (2.5 Flash) |
| Groq | via `model_router.py` | `GROQ_API_KEY` | Fast LLM fallback + Whisper STT |
| Ollama | via `model_router.py` | `OLLAMA_BASE_URL` | Local LLM fallback (gemma3:4b) |
| Google Workspace | `adapters/google_workspace/` | via GWS CLI auth | Calendar, Drive, Gmail, Tasks |
| Discord | `services/discord_bot.py` | `DISCORD_TOKEN` | Primary human interface |
| Notion | `adapters/notion/` | `NOTION_API_KEY` + DB IDs | CRM, tasks, documents, briefs |
| Higgsfield | `adapters/higgsfield/` | `HIGGSFIELD_API_KEY` | AI video generation |
| Google NotebookLM | `adapters/notebooklm/` | `NOTEBOOKLM_*_ID` | Memory sync |
| Perplexity | via scripts | `PERPLEXITY_API_KEY` | Market research |
| Apify | via scraper | `APIFY_TOKEN` | Instagram scraping |

---

## Part 22: How to Navigate This System

### "I want to understand how a message flows through the system"
1. `services/discord_bot.py` → `on_message` handler (line ~500)
2. → `interface/presence/handlers/intent_handler.py` (intent classification)
3. → `control_plane/runtime/gateway.py` → `EOSGateway.route()`
4. → `control_plane/runtime/cognitive_loop.py` (8 stages)
5. → `execution/runtime/model_router.py` → `call_with_fallback()`
6. → Response back through `interface/discord/discord_utils.py`

### "I want to add a new external integration"
1. Create adapter at `adapters/{name}/{name}_client.py`
2. Follow Law 5.9 pattern: `translate_request()` / `normalize_result()`
3. Register in adapter registry if it exposes substrate capabilities
4. Add env vars to `infra/docker/umh.env`

### "I want to understand the ingestion pipeline"
1. `understanding/perception/orchestrator.py` — GenericIngestionOrchestrator
2. Sources: `adapters/data_source_adapters/` (GWSSource, LocalFileSource)
3. Decomposition: LLM extraction (model_router) with heuristic fallback
4. Domain bridge: `understanding/domains/business.py`
5. Persistence: `state/memory/memory.py` (Law 5.5 path)
6. Proofs: `data/runtime/canonical_memory_store/proofs/`

### "I want to add a new cron job"
1. Write script in `scripts/`
2. Add to `infra/cron/crontab.current`
3. Run `crontab infra/cron/crontab.current` to install
4. If it should go through Control Plane: use `scripts/emit_signal.py` + wrapper in `scripts/scheduled/`

### "I want to run tests"
```bash
make test-migration           # Quick: migration-pinning tests only
pytest tests/ -x              # Full suite (requires Neon connection for some)
pytest tests/migration/ -x    # Offline-safe subset
```

---

## Part 23: Key Architectural Decisions

1. **Single memory write path (Law 5.5)** — All memory writes go through `state/memory/memory.py`. No direct SQL inserts to memory tables.

2. **External boundary contract (Law 5.9)** — Every external system gets an adapter with `translate_request()`/`normalize_result()`. Internal code never touches raw external APIs.

3. **Multi-model routing chain** — cc_sdk (Opus 4.6, free via subscription) → Gemini 2.5 Flash → Groq → Ollama. Each returns None on failure, next tried.

4. **File-based transport** — Inter-process communication uses JSONL files in inbox/outbox directories, not HTTP or queues. Simple, debuggable, survives restarts.

5. **Governance-first execution** — Every action classified by risk (LOW/MEDIUM/HIGH/CRITICAL). HIGH+ requires human approval. No silent autonomous execution of risky operations.

6. **Cognition Stack retrieval hierarchy** — Palace → Graph → Summaries → Raw Source → Logs. Never skip layers.

7. **Authority tiers (T1-T9)** — Every piece of knowledge carries a credibility tier from T1_CANONICAL (verified truth) to T9_OLD_CHATS (lowest confidence).

8. **Constitutional engines (proof-only)** — The 7 constitutional engines in `execution/workers/workstation/` generate reports proving system properties but don't enforce at runtime yet.

9. **Operationalization principle** — After anything works: document → skill/template → never rebuild from scratch → always improvable.

10. **Tool Mastery Engine** — Before using any external tool: check if mastery exists → research if missing → create skill → apply. 96 tool skills and growing.

---

## Appendix A: File Count by Top-Level Directory

| Directory | .py Files | Other Files | Total |
|-----------|-----------|-------------|-------|
| execution/ | 198 | — | 198 |
| scripts/ | 155 | — | 155 |
| tests/ | 116 | — | 116 |
| understanding/ | 46 | — | 46 |
| composition/ | 44 | — | 44 |
| adapters/ | 34 | — | 34 |
| control_plane/ | 96 | — | 96 |
| state/ | 61 | — | 61 |
| governance/ | 15 | — | 15 |
| interface/ | 15 | — | 15 |
| core/ | 13 | — | 13 |
| services/ | 11 | — | 11 |
| learning/ | 9 | — | 9 |
| operations/ | 7 | — | 7 |
| observability/ | 6 | — | 6 |
| runtime/ | 4 | — | 4 |
| 10_Wiki/ | — | 6,035 | 6,035 |
| docs/ | — | 430+ | 430+ |
| vault/ | — | 752 | 752 |
| skills/ | — | 165 | 165 |
| agents/ | — | 19 | 19 |
| config/ | — | 17 | 17 |
| data/ | — | ~200 | ~200 |
| saas/ | — | ~15 | ~15 |

---

## Appendix B: Docker Service Map

| Container | Entry Point | Status | Port |
|-----------|-------------|--------|------|
| `os-discord` | `services/discord_bot.py` | **Running** | 8765 |
| `os-webhook` | `interface/api/webhooks/calendly_webhook.py` | **Running** | 8080 |
| `os-scraper` | `services/overnight_scrape.py` | Available | — |
| `os-monitor` | `services/dm_monitor.py` | Available | — |
| `os-bot` | `services/telegram_control.py` | Dormant | — |

---

## Appendix C: LLM Routing Chain

```
call_with_fallback(prompt, agent_type, ...)
  │
  ├─ Option 0: cc_sdk (Claude Code CLI)
  │    ├─ Model: Opus 4.6 via Max subscription (no API cost)
  │    ├─ Timeout: 120s (configurable via CC_SDK_TIMEOUT_SECONDS)
  │    ├─ Auth: OAuth token from ancestor CC process via /proc walk
  │    └─ Validation: _is_error_leak() catches auth/quota errors leaked as text
  │
  ├─ Option 1: Gemini 2.5 Flash (google.genai SDK)
  │    └─ Spending cap applies (429 when exceeded)
  │
  ├─ Option 2: Groq (groq SDK)
  │    └─ Also used for Whisper STT
  │
  └─ Option 3: Ollama gemma3:4b (local, ~3.3 GiB RAM)
       └─ Needs os-bot stopped to fit in memory
```

CEO/strategic agents: always routed to Option 0 (pass `agent_type='ceo'` or `force_opus=True`).
