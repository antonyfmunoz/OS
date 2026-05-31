# DEFINITIVE GROUND-TRUTH AUDIT — /opt/OS (UMH)
## 2026-05-31

**Total repository files (excluding .git/node_modules/__pycache__/.mypy_cache/.ruff_cache/.pytest_cache):** 114,817
**Active Python files:** 1,186 | **Active TypeScript/TSX:** 92 (cockpit) + 31 (saas) + 18 (transports/api/http)
**Total disk (excluding .git):** ~2.1 GB
**VPS disk usage:** 80% (21 GB free of 96 GB)
**RAM:** 7.8 GB total, 53% usage

---

## EXECUTIVE SUMMARY

UMH (Universal Mastery Hierarchy) is a pre-revenue AI substrate platform at /opt/OS, built by a solo founder as infrastructure for running business operations through AI agents. The system runs on a single Hostinger VPS with 3 active Docker containers, 5 systemd services, 31 cron jobs, and an active organism daemon at tick 2,463.

**The system is currently in a degraded operational state.** All LLM providers in the Discord bot's fallback chain are exhausted (Gemini 429 free-tier, Groq 429 TPD limit, Perplexity 401 quota exceeded). The bot is alive but functionally brain-dead — it processes signals but cannot generate intelligent responses, defaulting to deterministic fallback. The operator API is healthy on port 8091. The cockpit is deployed to Fly.io (machine running in LAX region) but was unreachable via universalmetaharness.tech during this audit (DNS/routing issue — Fly machine is "started" per flyctl).

The organism subsystem (185 files) generates 17K+ events and ticks every 5 seconds but produces zero execution journal entries — the recording pathway is broken. A 238MB metrics JSONL file and 153MB of logs consume significant disk. The knowledge system (codebase graph, node summaries, memory palace) is 5 days stale with 412 Python files modified since the last rebuild.

The codebase is architecturally sophisticated but over-built for a pre-revenue solo project. The substrate/ package alone has 685 Python files with 10 empty placeholder directories. The project has strong architectural governance (pre-commit hooks enforcing type coherence and instance context boundaries) and a test suite of 1,783 collected tests. However, the gap between documented ambition and operational reality is wide: the system aspires to be a multi-projection universal platform but currently serves a single user with a single Discord bot in degraded state.

---

## CRITICAL ISSUES (immediate action required)

| Priority | Issue | Impact | Fix Effort |
|----------|-------|--------|------------|
| **P0** | ALL LLM providers exhausted (Gemini 429, Groq 429, Perplexity 401) | System is functionally lobotomized — no intelligent responses | Same-day: upgrade Gemini billing or wait for Groq TPD reset |
| **P1** | `execution_journal.jsonl` is 0 lines — spine executes but never records | No evidence trail of what the system actually does | 1 day: wire trace recording to persist |
| **P2** | Only 2/4 pre-commit gates wired (`check_dependency_direction.py` and `check_projection_leak.py` NOT in `.git/hooks/pre-commit`) | CLAUDE.md claims 4 gates; architecture violations can slip in | 1 hour: add to pre-commit hook |
| **P3** | EventBus publishes `loop_cycle_business_ops` with NO HANDLERS REGISTERED | Organism cadence is a no-op — Phase 10.0 goal unachievable | 2-3 days: register handlers or remove dead publish |
| **P4** | `data/umh/mesh/metrics.jsonl`: 238MB (1.3M lines), disk at 80% (21GB free), logs 153MB with no rotation | Will fill disk — becomes critical without intervention | 1 day: implement rotation, archive stale data |

---

## COMPLETE DIRECTORY MAP

| Directory | Files | Disk | Purpose | Status |
|-----------|-------|------|---------|--------|
| `.agents/` | 64 | 1.2 MB | Third-party Claude Code skills (humanizer, last30days) | ACTIVE |
| `.claire/` | 6 | 68 KB | Stale worktree remnant from abandoned "claire" agent | DEAD |
| `.claude/` | 80,233 | 1.1 GB | Claude Code config, settings, 22 worktrees (21 stale) | CONFIG (worktrees: DEAD weight) |
| `.obsidian/` | 8 | 36 KB | Obsidian vault configuration | CONFIG |
| `.planning/` | 32 | 416 KB | GSD workflow planning artifacts for Phase 10.0 | ACTIVE |
| `.playwright-mcp/` | 9 | 44 KB | Browser automation DOM snapshots | DATA |
| `.vscode/` | 1 | 8 KB | VS Code workspace settings | CONFIG |
| `01_Inbox/` | 0 | 8 KB | Obsidian inbox (empty) | DORMANT |
| `03_CRM/` | 0 | 8 KB | Obsidian CRM (empty) | DORMANT |
| `10_Wiki/` | 37 | 176 KB | Duplicate wiki pages (superseded by knowledge/) | DEAD |
| `adapters/` | 89 | 2.3 MB | External system adapters (models, GWS, browser, Notion) | ACTIVE |
| `agents/` | 11 | 88 KB | UMH agent soul documents (10 departments + CU) | ACTIVE |
| `archive/` | 2 | 376 KB | Non-active code preserved for reference | DEAD |
| `cockpit/` | 98 src | 227 MB | Electron + web cockpit (React 19, deployed Fly.io) | ACTIVE |
| `data/` | 9,792 | 357 MB | Runtime state, graphs, proofs, coordinator state | ACTIVE |
| `docker/` | 3 | 20 KB | Computer-use agent Docker setup (Beast) | ACTIVE |
| `docs/` | 583 | 6.5 MB | Architecture specs, audits, operations, contracts | ACTIVE |
| `infra/` | 4 | 32 KB | Docker environment files (SENSITIVE secrets) | CONFIG |
| `knowledge/` | 289 | 1.5 MB | Wiki, memory palace, concept/entity/decision pages | ACTIVE |
| `logs/` | 20,724 | 153 MB | Signal dispatch, decisions, execution, TME research | DATA |
| `media/` | 0 | 8 KB | Media assets (empty) | DORMANT |
| `nodes/` | 44 | 740 KB | Distributed execution (Windows daemon, environments) | ACTIVE |
| `projections/` | 48 | 1.2 MB | Application projections (EOS, CreatorOS, LyfeOS) | ACTIVE |
| `runtime/` | 4 | 34 MB | Runtime state (.substrate_state, .substrate_station inbox) | ACTIVE |
| `saas/` | 31 | 91 MB | EOS TypeScript API (Hono, Drizzle, Neon) | ACTIVE |
| `scripts/` | 162 | 4.7 MB | Cron scripts, hooks, TME, graph, verification | ACTIVE |
| `services/` | 42 | 1.8 MB | Docker service entrypoints + dormant daemons | ACTIVE |
| `skills/` | 466 | 115 MB | UMH skill library (52 business + 96 tools + saas-dev) | ACTIVE |
| `substrate/` | 680 | 28 MB | UMH brain (types, control_plane, execution, organism) | ACTIVE |
| `tests/` | 78 | 5.2 MB | Test suite (unit + integration + phase proofs) | ACTIVE |
| `transports/` | 91 | 2.9 MB | I/O surfaces (Discord, API, node mesh, presence) | ACTIVE |
| `umh/` | 2 | 48 KB | Standalone voice server (WebSocket :8095) | ACTIVE |
| `vault/` | 1,485 | 11 MB | Conversation memory (1,273 sessions + 212 summaries) | DATA |

**Root-level files (26):** .dockerignore, .env, .env.example, .env.sessions, .gitignore, .mcp.json, AGENTS.md, ARCHITECTURE.md, CLAUDE.local.md, CLAUDE.md, Dockerfile, Makefile, PHILOSOPHY.md, PROTOCOLS.md, README.md, cloud.md, cockpit-current.png, cockpit-login.png, cockpit_signin.png, docker-compose.yml, install.sh, patch_pycord.py, pyproject.toml, requirements.txt, setup.sh, skills-lock.json

---

## PYTHON PACKAGES — COMPLETE

### substrate/ (680 .py files, 200,278 lines, 28 MB)

The UMH brain. Innermost architectural layer. Never imports from transports/ or services/.

| Subdirectory | Files | Lines | Key Contents | Runtime Status |
|---|---|---|---|---|
| (root) | 4 | 2,327 | `__init__.py` (Substrate API), `types.py` (87 Pydantic/Enum classes), `canonical_types.py` (134 registered types), `self_model.py` (identity) | PRODUCTION |
| control_plane/ | 77 | 22,322 | gateway.py (1,927L), cognitive_loop.py (1,539L), orchestrator.py (1,910L, CEOAgent at line 73), goal_selector.py (1,485L), governance.py, registry.py, memory.py, router, scheduling, agents, actions, signals | PRODUCTION |
| execution/ | 164 | 66,759 | spine.py (ConcreteExecutionSpine, 419L single public method), trace.py, feedback.py, bridge/ (76 files, session/voice/mode transport), runtime/ (17 files, capability routing), workers/workstation/ (37 files, constitutional engines), voice/, agents/, loop/, media/ | PRODUCTION (bridge), DORMANT (workers/workstation — imported by report handlers only, never executed) |
| organism/ | 185 | 63,836 | daemon.py (984L), coordinator.py (520L), autonomous_tick.py, governed_spine.py, template_registry.py, pr_factory.py, candidate_supply.py, workcell_protocol.py, world_model.py, environment_reconciler.py, tests/ (65 test files) | PRODUCTION (ticking, events growing, journal EMPTY) |
| understanding/ | 55 | 13,491 | perception/orchestrator.py (1,157L), knowledge/ (graph, layers, domains), research_engine.py, reality_engine.py, world_pulse.py, domains/ (business, creator, life bridges) | PRODUCTION |
| composition/ | 46 | 10,454 | Tool Mastery Engine: mastery/authoring/ (10), mastery/management/ (11), mastery/research/ (17) | PRODUCTION |
| state/ | 65 | 10,491 | context.py, storage/db.py, memory.py (1,039L), registries/ (6), stores/ (14), business/ (BIS), finance/, metrics/ | PRODUCTION |
| governance/ | 20 | 3,599 | policy_engine.py, risk_classes.py, security.py, authority/, quality/, accountability/, validation/ | PRODUCTION |
| sockets/ | 19 (16 port files) | 1,651 | Abstract ports: notification.py, channel_port.py, message_port.py, approval_port.py, sensing_port.py, config_port.py, registry.py | PRODUCTION |
| intelligence/ | 4 | 1,128 | finetune_harness.py, runtime.py, training_extractor.py | DORMANT |
| memory/ | 6 | 1,127 | claude_bridge.py, promoter.py, auto_reconciler.py, watcher.py, candidate_generator.py | PRODUCTION |
| reality_model/ | 4 | 733 | canonical.py, instance.py, simulation.py | DORMANT |
| foundation/ | 9 | 546 | Philosophical primitives: identity, epistemology, persona, perspective, laws | DORMANT (design) |
| contracts/ | 5 | 254 | agent_types.py (TaskType, ModelProvider), routing_contracts.py | PRODUCTION |
| integrations/ | 5 | 430 | product_connections.py, health.py, cors.py, bridge.py (NOTE: substrate/integrations/{eos,creatoros,lyfeos,notion,node_mesh} are ALL EMPTY directories) | PRODUCTION (root), DEAD (empty subdirs) |
| ontology/ | 9 | 290 | laws.py (LawRegistry), primitives.py, domains/ (stubs) | PARTIAL |
| workstation/ | 2 | 238 | state.py (WorkstationStateManager) | DORMANT |
| deployment/ | 0 | 0 | Empty | DEAD |
| distribution/ | 0 | 0 | Empty | DEAD |

**Key entry points:**
- `substrate/__init__.py` — Substrate public API (execute, query, register, status)
- `substrate/types.py` — 87 Pydantic models (SignalEnvelope, RiskClass, WorkPacket, etc.)
- `substrate/control_plane/runtime/gateway.py` — Gateway class (primary runtime entry); `EntrepreneurOSGateway` alias at line 1927 (backward-compat debt)
- `substrate/execution/spine.py` — ConcreteExecutionSpine (8-stage pipeline, single public method: execute())
- `substrate/organism/daemon.py` — OrganismDaemon (autonomous tick loop)

### adapters/ (89 files, 16,251 lines, 2.3 MB)

External system adapters. Imported by substrate (deferred) and transports.

| Subdirectory | Files | Lines | Key Contents | Runtime Status |
|---|---|---|---|---|
| models/ | 11+3 | ~3,500 | model_router.py (1,442L, call_with_fallback 457L), cc_sdk.py (464L), agent_runtime.py (580L), llm_adapter.py, codex_cli.py, hermes_cli.py, opencode_cli.py, routing/ (capabilities.py, config.py) | PRODUCTION |
| adapter_engine/ | 16 | ~4,500 | lifecycle_manager.py, adapter_manifest.py, maturity.py, capability_discovery.py, google_docs_adapter_v1.py, live_ingestion_pipeline.py, substrate_decomposer_v1.py | PRODUCTION |
| google_workspace/ | 7 | ~4,700 | gws_connector.py (1,115L), email_gps.py (1,429L), gws_scanner.py (702L), doc_creator.py, document_filer.py, tasks_adapter.py (DORMANT) | PRODUCTION |
| notion/ | 13 | ~2,400 | notion_publisher.py (485L), notion_sync.py (469L), integration/ (poller, handlers, signals, outcomes, watermarks) | PRODUCTION |
| calendar/ | 3 | ~1,200 | meetings.py (836L), travel_manager.py (348L) | PRODUCTION |
| browser_exports/ | 7 | ~1,500 | chatgpt_export, claude_export, instagram_export/parser, gmail_poller, profile_manager | DORMANT |
| data_source_adapters/ | 8 | ~1,200 | gws_source.py, local_file_source.py, github_source.py, conversation_source.py, parsers/ (chatgpt, claude) | PRODUCTION |
| capabilities/ | 6 | ~1,000 | contracts.py (4 abstract capabilities), goose/ui_tars/creative_gen/voice_pro harnesses | DORMANT (harnesses) |
| tool_adapters/ | 6 | ~640 | filesystem.py, git.py, shell.py, tmux.py (governed operations for executor) | PRODUCTION |
| scrapling/ | 2 | ~140 | scrapling_connector.py (stealth web fetch) | PRODUCTION |
| higgsfield/ | 2 | ~110 | higgsfield_client.py (video gen API) | PRODUCTION |
| notebooklm/ | 2 | ~310 | notebooklm_sync.py (bidirectional sync) | PRODUCTION |
| model_adapters/ | 0 | 0 | Empty directory | DEAD |

### transports/ (91 files, 19,829 lines, 2.9 MB)

I/O surfaces. Bridges external world to substrate.

| Subdirectory | Files | Lines | Key Contents | Runtime Status |
|---|---|---|---|---|
| api/ | 28 .py | 8,838 | cockpit.py (2,304L), organism_bridge.py (2,134L), app.py (547L), operator.py (567L), + 10 cockpit sub-routers, voice.py, computer_use.py, distribution.py, signal_factory.py, signal_router.py, event_bus.py | PRODUCTION |
| api/http/ | 18 .ts | 1,931 | Hono server (server.ts), DB client/schema/migrate, Python bridge, auth/operator middleware, 8 route files (system, organism 532L, governance, chat, knowledge, execution, settings, config) | PRODUCTION |
| api/webhooks/ | 2 | 434 | calendly_webhook.py (Flask, os-webhook container) | PRODUCTION |
| discord/ | 5 | 1,227 | signal_factory.py, approval_bridge.py, discord_utils.py, spine_integration_v1.py, interface_adapter_v1.py (DORMANT) | PRODUCTION |
| node_mesh/ | 11 | 1,156 | server.py (456L, WebSocket :8094), config.py, registry.py, metrics_buffer.py, integration/ (handlers, manifest, outcomes, signals, types) | PRODUCTION (process running, port unresponsive to HTTP — likely WebSocket-only) |
| presence/ | 21 | 5,791 | substrate_command_handler.py (938L), cc_command_handler.py (563L), intent_handler.py (437L), pipeline_handler.py, reports/ (13 report generators) | PRODUCTION |
| channels/ | 2 | 452 | channel.py (DiscordChannel, TelegramChannel, WebhookChannel, ConsoleChannel, ChannelRouter) | PRODUCTION |

### services/ (42 files, 1.8 MB)

Docker service entrypoints and dormant daemons.

| File | Lines | Docker Container | Status |
|---|---|---|---|
| discord_bot.py | 1,974 | os-discord | PRODUCTION |
| discord_bot_commands.py | 2,740 | (imported by discord_bot) | PRODUCTION |
| discord_message_handlers.py | 1,214 | (imported by discord_bot) | PRODUCTION |
| operator_api.py | 740 | os-operator | PRODUCTION |
| cc_webhook_receiver.py | 309 | (started inside discord_bot on_ready) | PRODUCTION |
| higgsfield_webhook.py | 131 | os-webhook | PRODUCTION |
| overnight_scrape.py | 251 | os-scraper | PRODUCTION |
| icp_scorer.py | 603 | — | DORMANT |
| cost_tracker.py | 414 | — | DORMANT |
| kpi_tracker.py | 411 | — | DORMANT |
| bridge_health.py | 315 | — | DORMANT |
| magic_link_handler.py | 358 | — | DORMANT |
| local_bridge_server.py | 257 | — | DORMANT |
| export_bridge_handler.py | 264 | — | DORMANT |
| oauth_device_flow.py | 304 | — | DORMANT |
| local_bridge_client.py | 172 | — | DORMANT |
| goal_api.py | 194 | — | DORMANT |
| heartbeat.py | 113 | — | DORMANT |
| auth_flows/chatgpt.py | 456 | — | DORMANT |
| auth_flows/claude.py | 210 | — | DORMANT |
| browser_adapter.py | 98 | — | DORMANT |
| trigger_export.py | 128 | — | DORMANT |
| tier_3_fallback.py | 28 | — | DORMANT |
| magic_link_server.py | 59 | — | DORMANT |

**Dead structures:** `services/handlers/` (empty), `services/jarvis/` (14 empty subdirs)

### scripts/ (162 files, 4.7 MB)

| Category | Count | Status |
|---|---|---|
| Cron scripts (verified in crontab) | 26 | PRODUCTION |
| Claude Code hooks (verified in settings.json) | 9 | PRODUCTION |
| Pre-commit gates | 9 | PRODUCTION (4 defined, only 2 wired) |
| Graph/knowledge system | 12 | PRODUCTION |
| TME scripts | 12 | PRODUCTION |
| Notion integration | 10 | MIXED (3 active cron, 7 utility) |
| Auth monitor | 7 | PRODUCTION (4 cron, 3 utility) |
| Substrate CLIs | 9 | PRODUCTION |
| Operator CLIs | 10 | PRODUCTION |
| Verification scripts | 10 | PRODUCTION |
| Windows/cross-node | 7 | ACTIVE (Windows) |
| Ingestion pipelines | 10 | DORMANT |
| Memory/sync | 6 | MIXED (3 active, 3 dormant) |
| Scheduled wrappers | 7 | DORMANT (superseded) |
| Migration/maintenance | 6 | DEAD (historical) |
| Miscellaneous | 12 | MIXED |

**Anomalies:** `agent_executor.log` (41,742 lines) misplaced in scripts/. `wiki_session_start_hook.py` referenced in settings.json but MISSING.

### nodes/ (44 files, 740 KB)

| Subdirectory | Files | Status | Key Contents |
|---|---|---|---|
| distribution/ | 3 | ACTIVE | distributor.py (357L), first_boot.py (158L) — imported by transports/api/distribution.py |
| environments/ | 19 | MIXED | work_packet.py (ACTIVE, canonical types), execution_binding_contracts.py (ACTIVE), 11 DORMANT design artifacts |
| windows/umh_node/ | 12 | ACTIVE (deployed Beast) | client.py (320L WebSocket), service.py (142L Windows Service), adapters/ (clipboard, container, desktop, filesystem, shell) |
| windows/umh_desktop/ | 2 | ACTIVE (deployed Beast) | tray.py (198L system tray companion) |
| windows/ (support) | 6 | CONFIG | kokoro_server.py (TTS :8880), pyproject.toml, requirements, setup/start scripts |

### projections/ (48 files, 1.2 MB)

| Subdirectory | Files | Status | Key Contents |
|---|---|---|---|
| eos/ | 31 | ACTIVE | agents/ (10 DepartmentAgent subclasses), entities.py (880L), integration/ (poller, handlers, signals, outcomes, tables), views/ (pipeline, kpis, activity), workflows/ (outreach, followup, content) |
| creatoros/ | 8 | PARTIAL | integration/ (correlation, handlers, manifest, outcomes, signals, tables) — registered via product_connections.py, no runtime activation |
| lyfeos/ | 8 | PARTIAL | integration/ (same structure as creatoros) — registered via product_connections.py, no runtime activation |

---

## TYPESCRIPT/FRONTEND

### cockpit/ (98 source files, 227 MB with node_modules)

**Deployed at:** umh-cockpit.fly.dev / universalmetaharness.tech (Fly.io, LAX region, shared-cpu-1x, 512 MB)
**Tech:** React 19, TypeScript 6, Vite 8, Electron 42, Tailwind CSS 4, Zustand 5, Clerk auth
**Dual-mode:** Electron desktop (dev) + nginx static web (production)
**Status:** Fly machine "started" but external access timed out during audit — DEGRADED

| Layer | Files | Key Contents |
|---|---|---|
| Electron main | 2 | index.ts (214L: window, IPC, tray), preload/index.ts (33L: context bridge) |
| App shell | 5 | main.tsx, App.tsx, constants.ts, global.d.ts, index.html |
| API | 4 | client.ts (fetchApi), websocket.ts (auto-reconnect), voice-ws.ts (PCM16), voice-controller.ts |
| Components | 26 | Shell.tsx, TitleBar, LeftRail, RightRail, HudBar, ControlPanel, CommandPalette, VoiceCommandBar (413L), ChatDrawer (330L), EventConsole, ExecutionTimeline, GraphView, TopologyMap, LivePreview, SplitPane, FabLarge/Medium/Small, AgentCard, TaskBlock, RingGauge, OverlayToggle, TimelineView, ConnectionBanner, VoiceWaveform |
| Panels | 27 | DashboardPanel (351L), OperatorPanel (529L), IntelligencePanel (657L), WorldModelPanel (603L), RuntimePanel, OrganismPanel, CompanyPanel, ApprovalsPanel, KnowledgePanel, UniversalWorkPanel, SelfBuildPanel, PropagationGraphPanel, PortfolioPanel, EditorPanel, CommsPanel, InfrastructurePanel, SettingsPanel, ExecutionPanel, AgentsPanel, AnalyticsPanel, ActivityPanel, TasksPanel, WorkflowsPanel, SkillsPanel, ExperimentsPanel, ProfilePanel, TrackingPanel |
| Stores | 20 | cockpitStore, chatStore, voiceStore, systemStore, organismStore (474L), realtimeStore, activityStore, agentStore, approvalStore, analyticsStore, coherenceStore (249L), configStore, editorStore, executionStore, intelligenceStore, knowledgeStore, operatorExperienceStore (377L), settingsStore, taskStore, worldModelStore (312L) |
| Hooks | 5 | useKeyboard, useOrganismRealtime (195L), usePolling, useVoiceDetection (117L), useWebSocket |
| Operator | 2 | speechInputAdapter.ts, voiceTypes.ts |
| Types/Styles/Utils | 4 | routes.ts (26 panels), globals.css, tokens.css, lib/time.ts |

**API surface:** 75+ endpoints called (all under /api/umh/), 2 WebSocket connections, 1 voice WebSocket

### saas/ (31 files, 91 MB with node_modules)

**Tech:** TypeScript, Hono v4.12, Drizzle ORM v0.39, Neon serverless, Zod
**Port:** 3000
**Status:** Route files exist, schema defined, NOT confirmed running

| Layer | Files | Key Contents |
|---|---|---|
| Server | 1 | api/index.ts — mounts UMH platform routes from transports/api/http/ + 12 EOS routes |
| Routes | 12 | ventures, skills, agents, agent (run/team/brief), analytics, interactions, outcomes, events, approvals, tasks, workflows, activity |
| DB schema | 1 | 13 EOS-specific tables (ventures, agents, skills, events, workflows, interactions, outcomes, clients, transactions, offers, etc.) |
| Migrations | 10 SQL | 0000-0009 progressive schema evolution |
| Seed | 1 | Full Munoz Holdings portfolio seeding |
| Config | 4 | package.json, tsconfig.json, drizzle.config.ts, package-lock.json |

### transports/api/http/ (18 TypeScript files)

Hono HTTP server providing UMH platform routes. Imported by saas/ for platform infrastructure.

| File | Lines | Purpose |
|---|---|---|
| server.ts | 62 | Mounts all routes, applies auth middleware |
| db/client.ts | 91 | Neon WebSocket pool, withOrg() RLS helper |
| db/schema.ts | 221 | Platform tables (organizations, org_members, portfolios) |
| db/migrate.ts | 167 | Migration runner with RLS + pgvector |
| lib/python_bridge.ts | 54 | Spawns agent_bridge.py and organism_bridge.py |
| middleware/auth.ts | 34 | x-org-id UUID validation |
| middleware/operator.ts | 37 | Owner-only guard |
| routes/ (8 files) | ~1,200 | system, organism (532L), governance, chat, knowledge, execution, settings, config |

---

## INTELLIGENCE ROUTING

### 10-Provider Fallback Chain (model_router.py, 1,442 lines)

`call_with_fallback()` (457 lines) is the single intelligence entry point for the entire system.

| Priority | Provider | Model | Current Status |
|---|---|---|---|
| 0 | CLAUDE_CLI | Opus 4.6 (tmux) | Available only during dev sessions |
| 1 | CC_SDK | Opus 4.6 (claude-agent-sdk) | Available only during dev sessions |
| 2 | GEMINI | gemini-2.5-flash | **429 — free tier exhausted** |
| 3 | GROQ | llama-3.3-70b | **429 — TPD limit reached** |
| 4 | ANTHROPIC | haiku/sonnet | Needs credits (401 auth) |
| 5 | PERPLEXITY | sonar-pro | **401 — quota exceeded** |
| 6 | OLLAMA | qwen2.5:0.5b (397MB loaded) | Emergency local — minimal capability |
| 7 | CODEX | codex CLI | Reconnect issues |
| 8 | HERMES | hermes CLI | Experimental |
| 9 | OPENCODE | opencode CLI | Experimental |

**Circuit breaker behavior:** Each provider returns None/empty on failure, router falls through to next. When ALL providers exhausted, deterministic fallback produces template-based responses.

**Current operational state:** ALL providers degraded. The Discord bot processes signals but cannot generate intelligent responses. System is "functionally lobotomized."

**Deterministic-first principle:** Rules/regex/lookup tables run first. AI refines when available. The system still produces output when all LLMs are down — just not intelligent output.

---

## AGENT ECOSYSTEM

### UMH Runtime Agents (agents/, 11 files)

Loaded by `scripts/agent_task_executor.py` and `adapters/models/agent_runtime.py`.

| Agent | File | Purpose | Status |
|---|---|---|---|
| CEO | ceo_agent.md | Strategic planning, cross-department coordination | PRODUCTION |
| Computer Use | computer_use_agent.md | Visual automation in containers/native | DORMANT |
| Customer Success | customer_success_agent.md | Retention, onboarding | PRODUCTION |
| Engineering | engineering_agent.md | Code review, architecture, deployment | PRODUCTION |
| Finance | finance_agent.md | Financial modeling, reporting | PRODUCTION |
| HR | hr_agent.md | Hiring, culture, policies | PRODUCTION |
| Legal | legal_agent.md | Contracts, compliance | PRODUCTION |
| Marketing | marketing_agent.md | Brand, content, campaigns | PRODUCTION |
| Operations | operations_agent.md | Process, systems, efficiency | PRODUCTION |
| Product | product_agent.md | Roadmap, features, UX | PRODUCTION |
| Sales | sales_agent.md | Pipeline, outreach, closing | PRODUCTION |

### EOS Projection Agents (projections/eos/agents/, 11 files)

Instantiated as DepartmentAgent subclasses with skill execution + permission tiers.

| Agent | Tier | Skills | Status |
|---|---|---|---|
| CEOAgent | COMMIT | strategic_analysis, decision_brief, delegation, pipeline_review | ACTIVE |
| SalesAgent | EXECUTE | lead_score, outreach_draft, pipeline_report, follow_up | ACTIVE |
| MarketingAgent | DRAFT | content_draft, audience_analysis, campaign_plan | ACTIVE |
| FinanceAgent | COMMIT | (inherited) | ACTIVE |
| CustomerSuccessAgent | DRAFT | (inherited) | ACTIVE |
| HRAgent | DRAFT | (inherited) | ACTIVE |
| LegalAgent | COMMIT | (inherited) | ACTIVE |
| OperationsAgent | DRAFT | (inherited) | ACTIVE |
| ProductAgent | DRAFT | (inherited) | ACTIVE |
| EngineeringAgent | EXECUTE | (inherited) | ACTIVE |

**NOTE:** 3 CEOAgent class definitions exist (type system violation not caught by checks):
1. `substrate/control_plane/orchestrator/orchestrator.py:73`
2. `substrate/control_plane/agents/ceo_agent.py:39`
3. `projections/eos/agents/ceo.py:16`

### Claude Code Subagents (.claude/agents/, 4 files)

Session-scoped, invoked during development only. Require Anthropic credits.

| Agent | Model | Purpose | Status |
|---|---|---|---|
| eos-code-reviewer | opus | Adversarial code review | ACTIVE (when credits available) |
| eos-researcher | sonnet | Market/ICP research | ACTIVE |
| eos-simplifier | sonnet | Post-implementation simplification | ACTIVE |
| eos-verifier | haiku | Import/syntax/runtime verification | ACTIVE |

### Third-Party Skills (.agents/skills/, 2 packages)

| Skill | Source | Purpose | Status |
|---|---|---|---|
| humanizer | blader/humanizer | Remove AI writing patterns | ACTIVE |
| last30days | charlesdove977/goviralbitch | Research trending topics from last 30 days | ACTIVE |

---

## SKILLS & TOOLS

### Business Domain Skills (skills/, 52 SKILL.md files)

| Category | Skills | Status |
|---|---|---|
| Sales | 20 (analyze_conversation, qualify_lead, objection_handling, proof_promise_plan_close, etc.) | ACTIVE |
| Research | 6 (analyze_icp_signal, detect_icp_patterns, generate_market_report, etc.) | ACTIVE |
| Marketing | 4 (campaign_diagnosis, content_calendar, draft_arena_content_post, generate_content_from_intel) | ACTIVE |
| Content | 5 (video_brief, hook_performance, content_performance, discover_angles, generate_script) | ACTIVE |
| Ops | 13 (9 playbooks + communication_templates, war_room, schedule_event, weekly_ceo_report) | ACTIVE |
| CustomerSuccess | 2 (churn_prevention, onboarding_sequence) | ACTIVE |
| Outreach | 2 (dm_opener, reply_handler) | ACTIVE |

### Tool Mastery Packs (skills/tools/, 96 directories, ~253 files)

Each contains SKILL.md + references/best_practices.md (minimum). Extended packs (5+ files): claude_code (15), react, shadcn_ui, tailwind, typescript, vite, vitest, zod, radix_ui, tanstack_react_query, tanstack_table, sonner, react_hook_form.

**4 incomplete (.creating marker):** nodejs, systemd, tailscale, tmux

### Meta/System Skills (skills/meta/, 14 files)

| Skill | Purpose | Status |
|---|---|---|
| tool_mastery_engine | TME core (v4.0) — tool skill lifecycle | ACTIVE |
| ceo_framework | CEO operational framework | ACTIVE |
| ea_framework | EA operational framework | ACTIVE |
| portfolio_framework | Portfolio management | ACTIVE |
| claude_code_best_practices | CC session patterns | ACTIVE |
| operationalization_principle | Capture successful executions | ACTIVE |
| check_cc_updates | Weekly CC changelog check | ACTIVE |
| notion_discord_pattern | Integration pattern | ACTIVE |
| plugin_skill_audit | Plugin surface audit | ACTIVE |

### SaaS Dev Skill (skills/saas-dev-skill/, 146 files)

Standalone multi-agent SaaS builder pipeline. 8 agents: Product Intel > Architecture > Design System > Copy > Component Library > Page Agents > Backend > QA. Full test suite (43 unit tests).

### Claude Code Skills (.claude/skills/, 13 files)

On-demand skill definitions loaded during development sessions: browser-control, claude-code-cli, debug-agent, deploy-service, discord-admin, groq-api, instance-context-gate, material-list-builder, neon-db, new-agent, new-primitive, new-skill, notion-api.

---

## ORGANISM STATUS

### Daemon State (VERIFIED — actively ticking)

- **tick_count:** 2,463 (incrementing every ~5 seconds)
- **Runs inside:** os-operator container
- **Behavior:** Reconciles environments, publishes events to EventBus
- **Events recorded:** `data/umh/organism/events.jsonl` — 17,152 lines (active, growing)
- **Execution journal:** `data/umh/organism/execution_journal.jsonl` — **0 lines (BROKEN)**
- **Coordinator state:** `data/umh/coordinator/` — 493 files (work units + objectives)
- **Assimilation artifacts:** `data/umh/assimilation/` — 387 files

### EventBus Problem

The organism daemon publishes `loop_cycle_business_ops` events to the EventBus, but:
```
[EventBus] loop_cycle_business_ops published -- no handlers registered
```

This means the Phase 10.0 goal (template library + candidate supply + cadence execution) cannot work — the bus has no subscribers. The cadence is a no-op.

### Execution Recording Failure

The execution spine (`ConcreteExecutionSpine.execute()`) is called by the governance router, but the execution journal records nothing. The trace pathway exists in code but never persists output. Without this, there is no evidence trail of what the system actually does.

---

## CRON & AUTOMATION

### Every Cron Job (31 entries, verified against `crontab -l`)

| Schedule | Script | Purpose |
|---|---|---|
| */5 (0,5,10...) | scripts/day_reminder.py | Calendar event reminders |
| */5 (1,6,11...) | scripts/agent_task_executor.py | Poll + execute tasks |
| */5 (2,7,12...) | scripts/orchestrator_loop.py | 1 orchestrator cycle |
| */5 (3,8,13...) | scripts/auth_monitor/health_check.sh | CC auth validation |
| */5 (4,9,14...) | scripts/auth_monitor/session_resurrector.sh | CC session death alerting |
| */15 (0) | scripts/call_prep.py | Meeting prep briefs |
| */15 (2) | scripts/notion_tasks_sync.py | Notion > Neon tasks |
| */15 (4) | scripts/post_meeting_capture.py | Post-meeting outcomes |
| */15 (6) | scripts/calendar_invite_handler.py | Auto accept/decline invites |
| */15 (8) | scripts/noshow_detector.py | No-show detection |
| */15 (10) | scripts/notion_sync_poller.py | Bidirectional task sync |
| */30 | scripts/sync_all.sh | Cross-device git sync |
| 0 */6 | scripts/auth_monitor/cc_keepalive.sh | OAuth token refresh |
| 0 2 | scripts/scheduled/nightly_maintenance.sh | Nightly maintenance |
| 0 3 | scripts/discord_daily_clear.py | Clear Discord channels |
| 0 3 | scripts/emit_signal.py nightly_cycle | Emit nightly signal |
| 0 4 | docker-compose run os-scraper | Overnight Instagram scrape |
| 30 5 | scripts/emit_signal.py morning_ready | Emit morning signal |
| 45 5 | scripts/morning_intel.py | Morning intelligence brief |
| 0 6 | substrate/control_plane/orchestrator/orchestrator.py | Full orchestrator cycle |
| 5 6 | scripts/waiting_on_checker.py | Stale WAITING_ON emails |
| 10 6 | scripts/deadline_monitor.py | Approaching deadlines |
| 30 12 | scripts/midday_checkin.py | Afternoon priorities |
| 0 15 | scripts/inbox_gps_afternoon.py | Email GPS afternoon |
| 0 18 | scripts/eod_sync.py | EOD closing loop |
| 0 6 Sun | scripts/emit_signal.py weekly_cycle | Emit weekly signal |
| 0 6 Sun | scripts/portfolio_brief.py | Portfolio review |
| 0 7 Mon | scripts/relationship_nurture.py | Contact nurture check |
| 0 19 Sun | scripts/weekly_review.py | Full weekly review |
| 0 20 Sun | scripts/week_architect.py | Week planning |
| * * * * * | tailscale status --json | Network status refresh |

### Claude Code Hooks (verified in settings.json)

| Hook Type | Script | Purpose |
|---|---|---|
| PreToolUse | scripts/pre_tool_use_log.py | Log every tool call |
| PostToolUse (Edit/Write) | scripts/memory_instant_sync.py | Sync memory files |
| SessionStart | scripts/session_start_context.py | Inject dynamic context |
| SessionStart | scripts/wiki_session_start_hook.py | **(MISSING FILE)** |
| Stop | scripts/check_stop_condition.py | Validate stop decision |
| Stop | scripts/wiki_stop_hook.py | Capture conversation content |
| Stop | scripts/auto_report_dispatch.py | Report to cockpit/Discord |
| PermissionRequest | scripts/permission_notify.py | Notification on permission |
| SubagentStart | scripts/subagent_start_context.py | Agent-specific context |
| UserPromptSubmit | scripts/user_prompt_capture.py | Capture user messages |

### Pre-commit Gates

| Script | Purpose | In .git/hooks/pre-commit? |
|---|---|---|
| scripts/check_type_divergence.py | Block shadow types | **YES** |
| scripts/check_instance_leak.py | Block hardcoded instance values | **YES** |
| scripts/check_projection_leak.py | Block projection names in substrate | **NO** |
| scripts/check_dependency_direction.py | Block architecture violations | **NO** |

---

## RUNTIME STATE

### Docker Containers (verified `docker ps`)

| Container | Status | Port | Uptime | Function |
|---|---|---|---|---|
| os-discord | Up | 8765 (ws) | 2-3 hours | Discord bot + cognitive loop |
| os-operator | Up | 8091 | 8-9 hours | FastAPI operator API + organism daemon |
| os-webhook | Up | 8080 | 42-43 hours | Calendly webhook receiver |
| os-scraper | NOT running | — | — | On-demand via nightly cron (4am) |

### Systemd Services

| Service | Status | Function |
|---|---|---|
| caddy.service | running | Reverse proxy / TLS |
| ollama.service | running | Local LLM (only qwen2.5:0.5b loaded, 397MB) |
| tailscaled.service | running | Tailscale mesh agent |
| ttyd.service | running | Terminal web access |
| umh-mesh.service | running (DEGRADED) | Node mesh server (:8094, NOT responding to HTTP) |

### Listening Ports (verified `ss -tlnp`)

| Port | Process | Purpose |
|---|---|---|
| 8080 | docker-proxy (os-webhook) | Calendly webhook (Flask) |
| 8091 | docker-proxy (os-operator) | Operator API + cockpit proxy (FastAPI) |
| 8094 | python3 (PID 651413) | Node Mesh WebSocket server (HTTP unresponsive — WebSocket-only protocol) |
| 8765 | docker-proxy (os-discord) | CC webhook receiver (aiohttp) |

### Disk Usage

- **Total:** 96 GB, 80% used (21 GB free)
- **Largest consumers:** .claude/worktrees (1.1 GB stale), cockpit/node_modules (227 MB), data/ (357 MB), logs/ (153 MB), skills/ (115 MB), saas/node_modules (91 MB)
- **Unbounded growth:** `data/umh/mesh/metrics.jsonl` (238 MB, 1.3M lines, no rotation)

### Tailscale Mesh

- VPS (this machine): online
- DESKTOP-LVGUIQ9 (Windows Beast): online
- 2 nodes connected out of 3 registered

### Ollama

- Loaded model: qwen2.5:0.5b (397 MB) — emergency fallback only, minimal capability
- No larger models loaded (VPS memory constraint)

---

## GOVERNANCE

### Architecture Layer Enforcement

**Four-layer dependency model (pre-commit enforced):**
```
projections/ (47 .py) --> transports/ (72 .py) --> adapters/ (95 .py) --> substrate/ (685 .py)
```

**Verified compliance:**
- substrate/ uses only deferred (in-function) imports from adapters/. No substrate/ file imports from transports/ or services/ at module level.
- 3 imports from adapters/ in substrate/ (all `from adapters.models.agent_runtime import AgentRuntime`) — minor violation
- 10 imports from projections/ in transports/ (lazy imports in cockpit entity routes and app.py) — technically violations but passing checks

### Pre-commit Gate Status

| Gate | Script | Wired? | Passes? |
|---|---|---|---|
| Type Coherence | check_type_divergence.py | YES | Clean (0 violations) |
| Instance Context | check_instance_leak.py | YES | Clean (0 violations) |
| Projection Boundary | check_projection_leak.py | **NO** | Passes when run manually |
| Dependency Direction | check_dependency_direction.py | **NO** | Passes when run manually (exemptions exist) |

### Structural Governance (runtime)

- `ConcreteSignalRouter.route()` calls `GovernanceEngine.classify()` — confirmed via source inspection
- Execution blocked on governance verdict — structural enforcement, not optional
- `STRUCTURALLY_DENIED_ACTIONS` prevents financial/credential operations unconditionally
- 4-tier permission enforcement (READ/DRAFT/EXECUTE/COMMIT)

### Governance Gaps

- Execution journal recording — pathway exists but produces 0 output
- Organism work processing — daemon ticks but `loop_cycle_business_ops` has no handlers
- `approval_counters` table has 3 rows but nothing consumes them

### Known Violations

1. `adapters/google_workspace/gws_scanner.py` imports from `transports.discord.discord_utils` — sideways violation (adapters importing from transports)
2. `transports/api/signal_factory.py` contains hardcoded `organization_id="munoz-holdings"` — instance context leak (legacy, grandfathered)
3. `umh/voice_server.py` is architecturally misplaced — should be in services/ or transports/ per layer law
4. `transports/api/cockpit_entity_routes.py` imports from `projections.eos` (8 imports) — upward violation
5. `transports/api/app.py` imports `projections.eos.integration` (2 imports) — upward violation
6. `EntrepreneurOSGateway = Gateway` alias in gateway.py:1927 — backward-compat debt

---

## KNOWLEDGE SYSTEM

### Structure

```
Layer 1: Palace     -> knowledge/palace/ (19 files, auto-generated from graph)
Layer 2: Graph      -> data/codebase_graph.json (148K lines, 4.5 MB, queryable via scripts/query_graph.py)
Layer 3: Summaries  -> data/node_summaries.json (76K lines, 3.5 MB, one-line per entity)
Layer 4: Raw Source -> actual .py/.ts files
Layer 5: Logs       -> vault/memory/ + logs/
```

**Retrieval hierarchy (enforced):** Palace > Graph > Summaries > Raw Source > Logs

### Current Status: STALE (5 days)

- **Last rebuild:** 2026-05-26
- **Files modified since:** 412 Python files
- **Impact:** Graph queries return stale results; entire retrieval hierarchy compromised
- **Fix:** Run `scripts/update-graph` (30 min)
- **Query CLI:** `scripts/query_graph.py` — functional but returning outdated data

### Wiki & Documentation

- `knowledge/` — 273 markdown wiki pages (289 files total including palace)
- `data/codebase_pages/` — 6,292 documentation pages
- `vault/` — 1,485 conversation archives (1,273 sessions + 212 summaries)

---

## DATA & PERSISTENCE

### Neon PostgreSQL (PARTIAL — no runtime connectivity verification)

- Connection string in `infra/docker/umh.env` (NOT git-tracked, properly gitignored)
- Code references: interactions, outcomes, embeddings (pgvector 384-dim), skills, ventures with RLS
- Platform tables: organizations, org_members, portfolios (in transports/api/http/db/schema.ts)
- EOS tables: 13 (ventures, agents, skills, events, workflows, interactions, outcomes, clients, transactions, offers)

### Local JSONL Persistence (VERIFIED)

| File | Lines | Size | Status |
|---|---|---|---|
| data/umh/mesh/metrics.jsonl | 1,307,164 | 238 MB | **UNBOUNDED GROWTH — no rotation** |
| data/umh/organism/events.jsonl | 17,152 | active | Growing (17K+ lines) |
| logs/pipeline_trace.jsonl | 43,959 | — | Active |
| data/umh/organism/execution_journal.jsonl | 0 | 0 | **BROKEN** |

### Local SQLite (DEAD)

4 databases at `data/runtime/`, effectively empty:
- approvals.sqlite: 0 rows (approval_counters has 3 rows but nothing reads them)
- identities: 1 row
- memory: 0 rows
- tasks: 0 rows

### Embeddings (PARTIAL)

- `[EmbeddingEngine] Active: fastembed (local)` — confirmed in Discord bot logs
- Uses fastembed for local embeddings, pgvector for storage in Neon

### Knowledge Graph Data

| File | Size | Purpose |
|---|---|---|
| data/codebase_graph.json | 148,821 lines (4.5 MB) | Knowledge graph |
| data/node_summaries.json | 76,869 lines (3.5 MB) | Per-node summaries |

### Log Volume

| Directory | Files | Size | Growth |
|---|---|---|---|
| logs/signals/deferred_stale/processed/ | 19,556 | 79 MB | STALE (last write Apr 23) |
| logs/decisions/ | 37 | 17 MB | ~300 lines/day |
| logs/tool_mastery_research/ | 775 | 4.8 MB | Per TME session |
| logs/execution/ | 37 | 336 KB | Daily |
| logs/ (top-level .log) | 80 | ~5 MB | Per cron job |

---

## DEPLOYMENT

### Docker Compose (4 services)

| Service | Container | Command | Port | Memory | Restart |
|---|---|---|---|---|---|
| os-discord | os-discord | `python3 services/discord_bot.py` | 8765 | 1 GB | on-failure |
| os-operator | os-operator | `uvicorn services.operator_api:app --port 8091` | 8091 | 512 MB | unless-stopped |
| os-webhook | os-webhook | `python3 transports/api/webhooks/calendly_webhook.py` | 8080 | 128 MB | always |
| os-scraper | os-scraper | `python3 services/overnight_scrape.py` | — | — | no |

**Dockerfile:** python:3.11-slim base, system packages (git, curl, ffmpeg, espeak, tmux), Node.js 20, PyTorch CPU, Playwright chromium, @anthropic-ai/claude-code (global npm), py-cord patch.

### Fly.io (cockpit/)

- **App:** umh-cockpit
- **Region:** LAX (machine d8976eec9e1258)
- **Machine:** shared-cpu-1x, 512 MB
- **Image:** nginx:alpine + tailscale
- **Routing:** nginx proxies /api/* to VPS 100.77.233.50:8091 via Tailscale socat bridge
- **Domain:** universalmetaharness.tech
- **Status:** Machine "started" (version 36), last updated 2026-05-30T08:03:37Z — external access TIMED OUT during audit

### No CI/CD Pipeline

No evidence of GitHub Actions, CircleCI, or any CI system. Deployment is manual (`docker restart`, `flyctl deploy`).

### Dependencies

**Python (requirements.txt, 24 packages):** requests, python-dotenv, openai, playwright, python-telegram-bot, anthropic, google-genai, flask, fastapi, psutil, psycopg2-binary, openai-whisper, yt-dlp, py-cord[voice], webrtcvad, faster-whisper, numpy, librosa, silero-vad, fastembed, claude-agent-sdk, groq, notion-client

**Cockpit (package.json):** @clerk/clerk-react, lucide-react, react 19, react-dom 19, react-markdown, remark-gfm, zustand 5, tailwindcss 4, typescript 6, vite 8, electron 42, electron-vite

**SaaS (package.json):** @hono/node-server, @neondatabase/serverless, drizzle-orm, hono, ws, zod

### Environment Variables (names only)

**Core:** AI_NAME, FOUNDER_NAME, DATABASE_URL, NEON_ORG_ID, EOS_ORG_ID, EOS_USER_ID, UMH_ORG_ID, UMH_USER_ID, UMH_OPERATOR_API_KEY, UMH_WS_TOKEN, VENTURES_JSON
**AI:** ANTHROPIC_API_KEY, GEMINI_API_KEY, GROQ_API_KEY, OPENAI_API_KEY, PERPLEXITY_API_KEY, OLLAMA_BASE_URL, CC_SDK_TIMEOUT_SECONDS
**Services:** DISCORD_BOT_TOKEN, FOUNDER_DISCORD_ID, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, APIFY_API_TOKEN, INSTAGRAM_USERNAME/PASSWORD, CALENDLY_SIGNING_KEY, HIGGSFIELD_API_KEY, STITCH_API_KEY, NOTION_API_KEY
**Router:** EOS_ROUTER_CLAUDE_CLI_ENABLED, EOS_ROUTER_CLAUDE_CLI_TARGET, EOS_ROUTER_CLAUDE_CLI_SESSION, EOS_DISCORD_TEXT_TRANSPORT_ENABLED, EOS_DISCORD_TEXT_REPLY_TTS_ENABLED
**Claude Code:** CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS, MCP_CONNECTION_NONBLOCKING, CLAUDE_CODE_OAUTH_TOKEN

### MCP Servers

- **context7** — `npx -y @upstash/context7-mcp@latest` (library documentation on demand)

### Makefile Targets

- `test-migration` — `pytest tests/migration/ -v --tb=short`
- `test-migration-offline` — `pytest tests/migration/ -m "not external and not llm" -v`

---

## DISTRIBUTED SYSTEM

### Tailscale Mesh (VERIFIED)

- VPS (this machine): online
- DESKTOP-LVGUIQ9 (Windows Beast): online, reachable
- 2 nodes connected out of 3 registered

### umh-mesh.service (DEGRADED)

- systemd says: running (PID 651413)
- Port 8094: process listening, does NOT respond to HTTP
- Likely WebSocket-only protocol (transports/node_mesh/server.py uses WebSocket)
- No evidence of active cross-node communication during audit

### Windows Node Daemon (PARTIAL)

- Code exists at `nodes/windows/umh_node/` (12 files)
- Deployed as Windows Service (AUTO_START) on Beast
- Adapters: clipboard, container, desktop, filesystem, shell
- Beast is reachable via Tailscale but no verification of daemon actually running

### Cross-Node Execution (STUBBED)

- `substrate/execution/workers/workstation/` has 42 "constitutional engine" files
- Report handlers in transports/presence import them
- No evidence of actual cross-node execution occurring in production

---

## DEAD CODE MAP

| Path | Files | Size | Reason | Recommendation |
|---|---|---|---|---|
| `.claire/` | 6 | 68 KB | Abandoned worktree remnant, placeholder files | DELETE |
| `10_Wiki/` | 37 | 176 KB | Duplicate of knowledge/ pages | DELETE |
| `archive/stale_backups/` | 1 | 340 KB | March 2026 backup tar | DELETE |
| `services/jarvis/` | 14 empty dirs | 0 | Never-populated skeleton | DELETE |
| `services/handlers/` | 1 empty dir | 0 | Empty | DELETE |
| `adapters/model_adapters/` | empty dir | 0 | Code lives in adapters/models/ | DELETE |
| `substrate/deployment/` | empty dir | 0 | Empty | DELETE |
| `substrate/distribution/` | empty dir | 0 | Empty | DELETE |
| `substrate/execution/environments/` | empty dir | 0 | Empty | DELETE |
| `substrate/integrations/{eos,creatoros,lyfeos,notion,node_mesh}` | 5 empty dirs | 0 | All empty | DELETE |
| `substrate/control_plane/orchestrator/approvals/{approved,pending}` | 2 empty dirs | 0 | Empty | DELETE |
| `.claude/worktrees/` | 21 stale | ~1 GB | Stale worktrees at main HEAD | DELETE |
| `logs/signals/deferred_stale/processed/` | 19,556 | 79 MB | Last modified Apr 23, no longer written | ARCHIVE |
| `scripts/phase75a_classifier.py` | 1 | 280 lines | References non-existent directory | DELETE |
| `scripts/phase75a_dep_scanner.py` | 1 | 232 lines | Same | DELETE |
| `scripts/shim_retirement_monitor.py` | 1 | 272 lines | Convergence complete | DELETE |
| `scripts/measure_phase8_batch.py` | 1 | 339 lines | Historical | DELETE |
| `scripts/migrate_module.sh` | 1 | 78 lines | Completed migration | DELETE |
| `data/repos/` | 191 | — | Stale source snapshots (89-TSX reference of earlier SaaS frontend) | ARCHIVE |
| `runtime/` top-level | 0 .py | 34 MB | Zero imports in production code; only state files remain | RECLASSIFY (state files to data/) |
| 4 SQLite DBs at `data/runtime/` | 4 | 20 KB | Effectively empty (0-1 rows), nothing reads them | DELETE |

**Total recoverable disk:** ~1.2 GB (primarily from stale worktrees + archived logs)

### Shadow/Duplicate Code

| Item | Locations | Issue |
|---|---|---|
| CEOAgent class | 3 definitions (orchestrator.py:73, ceo_agent.py:39, projections/eos/agents/ceo.py:16) | Type system violation not caught by checks |
| EntrepreneurOSGateway | gateway.py:1927 (alias to Gateway) | Backward-compat debt |
| 9 shadow enums | SessionStatus, SignalType, GovernanceDecision duplicated across modules | Grandfathered existing; blocked for new code |
| 42 workstation engine files | substrate/execution/workers/workstation/ | Imported only by report handlers, never executed in production |
| 26 orphaned modules | Various | Nothing imports them |

---

## CONTRADICTIONS (docs vs reality)

| # | Documentation says | Reality | Severity |
|---|---|---|---|
| 1 | "72 legacy files in LEGACY_INSTANCE_LEAKS" (CLAUDE.md) | 0 legacy leaks exist; all cleaned | LOW (stale docs) |
| 2 | "4 pre-commit gates" (CLAUDE.md) | Only 2 gates in actual .git/hooks/pre-commit (type_divergence + instance_leak). dependency_direction and projection_leak are NOT wired. | HIGH |
| 3 | "execution_journal records traces" (implied by architecture) | execution_journal.jsonl has 0 lines | HIGH (broken recording) |
| 4 | "Organism autonomous cadence" (Phase 10.0) | EventBus publishes `loop_cycle_business_ops` with NO HANDLERS REGISTERED | HIGH (no-op cadence) |
| 5 | "umh-mesh.service" (running per systemd) | Port 8094 does not respond to HTTP (WebSocket-only?) | MEDIUM |
| 6 | "cockpit reachable at universalmetaharness.tech" | Timed out externally during audit (Fly machine says "started") | MEDIUM |
| 7 | "No Python file over 3,000 lines" (quality standard) | No violations found — standard is met | OK |
| 8 | "Graph-first retrieval hierarchy" (CLAUDE.md) | Graph is 5 days stale (412 files modified since rebuild) | MEDIUM |
| 9 | "10-provider fallback chain" (model_router) | ALL providers exhausted — system is brain-dead for LLM tasks | CRITICAL |
| 10 | "substrate/ never imports from transports/" | True for actual import statements; 3 adapter imports exist (minor) | LOW |

---

## WHAT IS PRODUCTION-REAL

These components are confirmed running, processing data, and producing observable output:

1. **Discord bot** (`services/discord_bot.py` in os-discord container) — VERIFIED running, processes signals, but LLM-degraded
2. **Operator API** (FastAPI on port 8091 in os-operator container) — VERIFIED healthy, serves cockpit HTML + 101+ JSON endpoints
3. **Organism daemon** (tick 2,463, 5s interval) — VERIFIED ticking, writing events.jsonl, reconciling environments
4. **Cron system** (31 jobs) — VERIFIED scheduled and executing
5. **Pre-commit governance** (type coherence + instance leak gates) — VERIFIED enforced
6. **Signal routing + governance gating** (ConcreteSignalRouter + GovernanceEngine) — VERIFIED in code path
7. **Fastembed local embeddings** — VERIFIED active in Discord bot logs
8. **Tailscale mesh** (VPS + Beast connected) — VERIFIED
9. **Webhook receiver** (os-webhook on 8080) — VERIFIED running 42+ hours
10. **Cockpit Fly.io machine** — VERIFIED started (reachability intermittent)

---

## WHAT IS PARTIAL

1. **Organism cadence** — daemon ticks, events recorded (17K+), but no handlers process business_ops. execution_journal empty.
2. **Workstation engines** (42 files) — code exists, report handlers import them, no runtime execution proof.
3. **Node mesh** — systemd service running, port unresponsive to HTTP, Beast reachable via Tailscale but no proof of daemon on Beast.
4. **CreatorOS/LyfeOS projections** — integration packages exist (1K+ lines each), no runtime activation.
5. **saas/ TypeScript API** — route files exist, schema defined, not confirmed running.
6. **Cockpit external access** — Fly machine started, HTML served locally, external timeout.
7. **Neon PostgreSQL** — connection configured, code references tables, no runtime verification possible without DB access.
8. **Execution spine 8-stage pipeline** — class exists (419 lines), governance calls it, but execution_journal records nothing.
9. **Knowledge retrieval system** — scripts functional but graph 5 days stale.
10. **Intelligence routing** — code is sophisticated (10 providers, circuit breaker, quality escalation) but ALL providers currently exhausted.

---

## TRUE CANONICAL CORE

The smallest set of files that constitute the real, running, production UMH (~25-30 files out of 1,186 Python files = 2.5%):

**Brain (intelligence + routing):**
- `adapters/models/model_router.py` (1,442 lines) — single intelligence entry point
- `substrate/control_plane/runtime/gateway.py` (1,927 lines) — Gateway class
- `substrate/control_plane/runtime/cognitive_loop.py` (1,539 lines) — thinking loop
- `substrate/types.py` — 87 canonical types

**Governance:**
- `substrate/control_plane/governance.py` — risk classification
- `substrate/control_plane/router/__init__.py` — signal lifecycle with governance gating
- `substrate/execution/spine.py` (419 lines) — execution pipeline

**Production entrypoints:**
- `services/discord_bot.py` (1,974 lines) — Discord bot
- `services/discord_bot_commands.py` (2,740 lines) — command handlers
- `services/discord_message_handlers.py` — message processing
- `transports/api/cockpit.py` (2,304 lines) — operator API routes
- `services/operator_api.py` — API entrypoint

**Organism (alive but incomplete):**
- `substrate/organism/daemon.py` — tick driver
- `substrate/organism/environment_reconciler.py` — actually executing
- `data/umh/organism/events.jsonl` — growing log

**Infrastructure:**
- `docker-compose.yml` — service definitions
- `infra/docker/umh.env` — secrets (gitignored)
- `.git/hooks/pre-commit` — governance gates

The remaining 97.5% is either support infrastructure (scripts, knowledge, tests), aspirational architecture (workstation engines, projections, mesh), or generated data.

---

## RECOMMENDED ACTIONS

| Priority | Action | Effort | Impact |
|---|---|---|---|
| **P0** | Restore LLM Intelligence — upgrade Gemini billing or add paid tier; wait for Groq TPD reset | Same-day | System is functionally lobotomized without LLM providers |
| **P1** | Fix Broken Recording — wire execution trace to actually persist to execution_journal.jsonl | 1 day | No evidence trail of system actions without this |
| **P2** | Wire Missing Pre-commit Gates — add check_dependency_direction.py and check_projection_leak.py to .git/hooks/pre-commit | 1 hour | CLAUDE.md claims 4 gates; only 2 are real |
| **P3** | Organism Cadence Completion — register handlers for loop_cycle_business_ops or remove dead publish | 2-3 days | Phase 10.0 goal impossible without subscribers |
| **P4** | Data Hygiene — implement rotation for metrics.jsonl (238MB), archive stale logs (79MB processed/), clean worktrees (1GB) | 1 day | Disk at 80%, will become critical |
| **P5** | Knowledge System Rebuild — run scripts/update-graph | 30 min | Retrieval hierarchy compromised when stale |
| **P6** | Resolve Cockpit External Access — investigate DNS/Fly networking/certificate for universalmetaharness.tech | Investigation | External users cannot reach cockpit |

---

## EXECUTION SPINES (verified code paths)

**Canonical execution path:**
```
Signal arrives --> ConcreteSignalRouter.route() [57 lines]
  --> GovernanceEngine.classify() [risk classification]
  --> GovernanceVerdict gates execution
  --> ConcreteExecutionSpine.execute() [419 lines, single public method]
  --> 8-stage pipeline
```
Located at: `substrate/execution/spine.py`

**Secondary execution path — Discord cognitive loop:**
```
Discord message --> signal_factory.py --> Gateway.process()
  --> cognitive_loop.py --> model_router.call_with_fallback()
  --> Response back to Discord
```
Located at: `substrate/control_plane/runtime/cognitive_loop.py`

**Organism autonomous cadence (PARTIAL):**
```
Organism daemon tick (every 5s) --> environment_reconciler
  --> publishes events to EventBus --> NO HANDLERS REGISTERED
```
Events recorded to `data/umh/organism/events.jsonl` (17K+ lines) but execution_journal.jsonl is empty.

**Intelligence routing:**
```
call_with_fallback() --> cc_sdk (Claude CLI) --> Gemini --> Groq --> Perplexity --> Ollama
  --> deterministic fallback on ALL_DOWN
```
Currently: ALL providers exhausted. Deterministic fallback active.

---

**END OF DEFINITIVE AUDIT**

Total verified file count: 114,817 files (excluding .git/node_modules/__pycache__/.mypy_cache/.ruff_cache/.pytest_cache).
Verification method: `find /opt/OS -type f -not -path '*/.git/*' -not -path '*/node_modules/*' -not -path '*/__pycache__/*' -not -path '*/.mypy_cache/*' -not -path '*/.ruff_cache/*' -not -path '*/.pytest_cache/*' | wc -l`
