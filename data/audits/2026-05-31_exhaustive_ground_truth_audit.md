I now have all the verified counts and runtime data. Here is the definitive audit document:

# EXHAUSTIVE GROUND-TRUTH AUDIT — /opt/OS
## Date: 2026-05-31 (Complete Edition)

**Total repository files (excluding .git/node_modules/__pycache__/.mypy_cache/.ruff_cache/.pytest_cache):** 114,817
**Total disk (excluding .git):** ~2.1 GB

---

## SECTION A: COMPLETE DIRECTORY MAP

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

## SECTION B: EVERY PYTHON PACKAGE

### B1. substrate/ (680 .py files, 200,278 lines, 28 MB)

The UMH brain. Innermost architectural layer. Never imports from transports/ or services/.

| Subdirectory | Files | Lines | Key Contents | Runtime Status |
|---|---|---|---|---|
| (root) | 4 | 2,327 | `__init__.py` (Substrate API), `types.py` (77 classes), `canonical_types.py` (80+ registry), `self_model.py` (identity) | PRODUCTION |
| control_plane/ | 77 | 22,322 | gateway.py (1,927L), cognitive_loop.py (1,539L), orchestrator.py (1,910L), goal_selector.py (1,485L), governance.py, registry.py, memory.py, router, scheduling, agents, actions, signals | PRODUCTION |
| execution/ | 164 | 66,759 | spine.py, trace.py, feedback.py, bridge/ (76 files, session/voice/mode transport), runtime/ (17 files, capability routing), workers/workstation/ (37 files, constitutional engines), voice/, agents/, loop/, media/ | PRODUCTION (bridge), DORMANT (workers/workstation) |
| organism/ | 185 | 63,836 | daemon.py (984L), coordinator.py (520L), autonomous_tick.py, governed_spine.py, template_registry.py, pr_factory.py, candidate_supply.py, workcell_protocol.py, world_model.py, tests/ (65 test files) | PRODUCTION |
| understanding/ | 55 | 13,491 | perception/orchestrator.py (1,157L), knowledge/ (graph, layers, domains), research_engine.py, reality_engine.py, world_pulse.py, domains/ (business, creator, life bridges) | PRODUCTION |
| composition/ | 46 | 10,454 | Tool Mastery Engine: mastery/authoring/ (10), mastery/management/ (11), mastery/research/ (17) | PRODUCTION |
| state/ | 65 | 10,491 | context.py, storage/db.py, memory.py (1,039L), registries/ (6), stores/ (14), business/ (BIS), finance/, metrics/ | PRODUCTION |
| governance/ | 20 | 3,599 | policy_engine.py, risk_classes.py, security.py, authority/, quality/, accountability/, validation/ | PRODUCTION |
| sockets/ | 19 | 1,651 | Abstract ports: notification.py, channel_port.py, message_port.py, approval_port.py, sensing_port.py, config_port.py, registry.py | PRODUCTION |
| intelligence/ | 4 | 1,128 | finetune_harness.py, runtime.py, training_extractor.py | DORMANT |
| memory/ | 6 | 1,127 | claude_bridge.py, promoter.py, auto_reconciler.py, watcher.py, candidate_generator.py | PRODUCTION |
| reality_model/ | 4 | 733 | canonical.py, instance.py, simulation.py | DORMANT |
| foundation/ | 9 | 546 | Philosophical primitives: identity, epistemology, persona, perspective, laws | DORMANT (design) |
| contracts/ | 5 | 254 | agent_types.py (TaskType, ModelProvider), routing_contracts.py | PRODUCTION |
| integrations/ | 5 | 430 | product_connections.py, health.py, cors.py, bridge.py | PRODUCTION |
| ontology/ | 9 | 290 | laws.py (LawRegistry), primitives.py, domains/ (stubs) | PARTIAL |
| workstation/ | 2 | 238 | state.py (WorkstationStateManager) | DORMANT |
| deployment/ | 0 | 0 | Empty | DEAD |
| distribution/ | 0 | 0 | Empty | DEAD |

**Key entry points:**
- `substrate/__init__.py` — Substrate public API (execute, query, register, status)
- `substrate/types.py` — 77 Pydantic models (SignalEnvelope, RiskClass, WorkPacket, etc.)
- `substrate/control_plane/runtime/gateway.py` — Gateway class (primary runtime entry)
- `substrate/execution/spine.py` — 8-stage ExecutionSpine pipeline
- `substrate/organism/daemon.py` — OrganismDaemon (autonomous tick loop)

### B2. adapters/ (89 files, 16,251 lines, 2.3 MB)

External system adapters. Imported by substrate (deferred) and transports.

| Subdirectory | Files | Lines | Key Contents | Runtime Status |
|---|---|---|---|---|
| models/ | 11+3 | ~3,500 | model_router.py (1,442L, 50+ importers), cc_sdk.py (464L), agent_runtime.py (580L), llm_adapter.py, codex_cli.py, hermes_cli.py, opencode_cli.py, routing/ (capabilities.py, config.py) | PRODUCTION |
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

**Intelligence routing chain (model_router.py call_with_fallback):**
1. CLAUDE_CLI (tmux, priority 0)
2. CC_SDK (Opus 4.6 via claude-agent-sdk, priority 1)
3. GEMINI (gemini-2.5-flash, priority 2)
4. GROQ (llama-3.3-70b, priority 3)
5. ANTHROPIC (haiku/sonnet, priority 4, needs credits)
6. PERPLEXITY (sonar-pro, priority 5)
7. OLLAMA (qwen2.5:0.5b, priority 6, emergency local)
8. CODEX/HERMES/OPENCODE (7-9)

### B3. transports/ (91 files, 19,829 lines, 2.9 MB)

I/O surfaces. Bridges external world to substrate.

| Subdirectory | Files | Lines | Key Contents | Runtime Status |
|---|---|---|---|---|
| api/ | 28 .py | 8,838 | cockpit.py (2,304L), organism_bridge.py (2,134L), app.py (547L), operator.py (567L), + 10 cockpit sub-routers, voice.py, computer_use.py, distribution.py, signal_factory.py, signal_router.py, event_bus.py | PRODUCTION |
| api/http/ | 18 .ts | 1,931 | Hono server (server.ts), DB client/schema/migrate, Python bridge, auth/operator middleware, 8 route files | PRODUCTION |
| api/webhooks/ | 2 | 434 | calendly_webhook.py (Flask, os-webhook container) | PRODUCTION |
| discord/ | 5 | 1,227 | signal_factory.py, approval_bridge.py, discord_utils.py, spine_integration_v1.py, interface_adapter_v1.py (DORMANT) | PRODUCTION |
| node_mesh/ | 11 | 1,156 | server.py (456L, WebSocket :8094), config.py, registry.py, metrics_buffer.py, integration/ (handlers, manifest, outcomes, signals, types) | PRODUCTION |
| presence/ | 21 | 5,791 | substrate_command_handler.py (938L), cc_command_handler.py (563L), intent_handler.py (437L), pipeline_handler.py, reports/ (13 report generators) | PRODUCTION |
| channels/ | 2 | 452 | channel.py (DiscordChannel, TelegramChannel, WebhookChannel, ConsoleChannel, ChannelRouter) | PRODUCTION |

### B4. services/ (42 files, 1.8 MB)

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

### B5. scripts/ (162 files, 4.7 MB)

| Category | Count | Status |
|---|---|---|
| Cron scripts (verified in crontab) | 26 | PRODUCTION |
| Claude Code hooks (verified in settings.json) | 9 | PRODUCTION |
| Pre-commit gates | 9 | PRODUCTION |
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

### B6. nodes/ (44 files, 740 KB)

| Subdirectory | Files | Status | Key Contents |
|---|---|---|---|
| distribution/ | 3 | ACTIVE | distributor.py (357L), first_boot.py (158L) — imported by transports/api/distribution.py |
| environments/ | 19 | MIXED | work_packet.py (ACTIVE, canonical types), execution_binding_contracts.py (ACTIVE), 11 DORMANT design artifacts |
| windows/umh_node/ | 12 | ACTIVE (deployed Beast) | client.py (320L WebSocket), service.py (142L Windows Service), adapters/ (clipboard, container, desktop, filesystem, shell) |
| windows/umh_desktop/ | 2 | ACTIVE (deployed Beast) | tray.py (198L system tray companion) |
| windows/ (support) | 6 | CONFIG | kokoro_server.py (TTS :8880), pyproject.toml, requirements, setup/start scripts |

### B7. projections/ (48 files, 1.2 MB)

| Subdirectory | Files | Status | Key Contents |
|---|---|---|---|
| eos/ | 31 | ACTIVE | agents/ (10 DepartmentAgent subclasses), entities.py (880L), integration/ (poller, handlers, signals, outcomes, tables), views/ (pipeline, kpis, activity), workflows/ (outreach, followup, content) |
| creatoros/ | 8 | ACTIVE | integration/ (correlation, handlers, manifest, outcomes, signals, tables) — registered via product_connections.py |
| lyfeos/ | 8 | ACTIVE | integration/ (same structure as creatoros) — registered via product_connections.py |

---

## SECTION C: EVERY TYPESCRIPT/FRONTEND

### C1. cockpit/ (98 source files, 227 MB with node_modules)

**Deployed at:** umh-cockpit.fly.dev (Fly.io, sjc region, shared-cpu-1x, 512 MB)
**Tech:** React 19, TypeScript 6, Vite 8, Electron 42, Tailwind CSS 4, Zustand 5, Clerk auth
**Dual-mode:** Electron desktop (dev) + nginx static web (production)

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

### C2. saas/ (31 files, 91 MB with node_modules)

**Tech:** TypeScript, Hono v4.12, Drizzle ORM v0.39, Neon serverless, Zod
**Port:** 3000

| Layer | Files | Key Contents |
|---|---|---|
| Server | 1 | api/index.ts — mounts UMH platform routes from transports/api/http/ + 12 EOS routes |
| Routes | 12 | ventures, skills, agents, agent (run/team/brief), analytics, interactions, outcomes, events, approvals, tasks, workflows, activity |
| DB schema | 1 | 13 EOS-specific tables (ventures, agents, skills, events, workflows, interactions, outcomes, clients, transactions, offers, etc.) |
| Migrations | 10 SQL | 0000-0009 progressive schema evolution |
| Seed | 1 | Full Munoz Holdings portfolio seeding |
| Config | 4 | package.json, tsconfig.json, drizzle.config.ts, package-lock.json |

### C3. transports/api/http/ (18 TypeScript files, part of transports/)

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

## SECTION D: CONFIGURATION & DEPLOYMENT

### D1. Docker Compose (4 services)

| Service | Container | Command | Port | Memory | Restart |
|---|---|---|---|---|---|
| os-discord | os-discord | `python3 services/discord_bot.py` | 8765 | 1 GB | on-failure |
| os-operator | os-operator | `uvicorn services.operator_api:app --port 8091` | 8091 | 512 MB | unless-stopped |
| os-webhook | os-webhook | `python3 transports/api/webhooks/calendly_webhook.py` | 8080 | 128 MB | always |
| os-scraper | os-scraper | `python3 services/overnight_scrape.py` | — | — | no |

**Dockerfile:** python:3.11-slim base, system packages (git, curl, ffmpeg, espeak, tmux), Node.js 20, PyTorch CPU, Playwright chromium, @anthropic-ai/claude-code (global npm), py-cord patch.

### D2. Fly.io (cockpit/)

- **App:** umh-cockpit
- **Region:** sjc (San Jose)
- **Machine:** shared-cpu-1x, 512 MB
- **Image:** nginx:alpine + tailscale
- **Routing:** nginx proxies /api/* to VPS 100.77.233.50:8091 via Tailscale socat bridge

### D3. Dependencies

**Python (requirements.txt, 24 packages):** requests, python-dotenv, openai, playwright, python-telegram-bot, anthropic, google-genai, flask, fastapi, psutil, psycopg2-binary, openai-whisper, yt-dlp, py-cord[voice], webrtcvad, faster-whisper, numpy, librosa, silero-vad, fastembed, claude-agent-sdk, groq, notion-client

**Cockpit (package.json):** @clerk/clerk-react, lucide-react, react 19, react-dom 19, react-markdown, remark-gfm, zustand 5, tailwindcss 4, typescript 6, vite 8, electron 42, electron-vite

**SaaS (package.json):** @hono/node-server, @neondatabase/serverless, drizzle-orm, hono, ws, zod

### D4. Environment Variables (names only)

**Core:** AI_NAME, FOUNDER_NAME, DATABASE_URL, NEON_ORG_ID, EOS_ORG_ID, EOS_USER_ID, UMH_ORG_ID, UMH_USER_ID, UMH_OPERATOR_API_KEY, UMH_WS_TOKEN, VENTURES_JSON
**AI:** ANTHROPIC_API_KEY, GEMINI_API_KEY, GROQ_API_KEY, OPENAI_API_KEY, PERPLEXITY_API_KEY, OLLAMA_BASE_URL, CC_SDK_TIMEOUT_SECONDS
**Services:** DISCORD_BOT_TOKEN, FOUNDER_DISCORD_ID, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, APIFY_API_TOKEN, INSTAGRAM_USERNAME/PASSWORD, CALENDLY_SIGNING_KEY, HIGGSFIELD_API_KEY, STITCH_API_KEY, NOTION_API_KEY
**Router:** EOS_ROUTER_CLAUDE_CLI_ENABLED, EOS_ROUTER_CLAUDE_CLI_TARGET, EOS_ROUTER_CLAUDE_CLI_SESSION, EOS_DISCORD_TEXT_TRANSPORT_ENABLED, EOS_DISCORD_TEXT_REPLY_TTS_ENABLED
**Claude Code:** CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS, MCP_CONNECTION_NONBLOCKING, CLAUDE_CODE_OAUTH_TOKEN

### D5. MCP Servers

- **context7** — `npx -y @upstash/context7-mcp@latest` (library documentation on demand)

### D6. Makefile Targets

- `test-migration` — `pytest tests/migration/ -v --tb=short`
- `test-migration-offline` — `pytest tests/migration/ -m "not external and not llm" -v`

---

## SECTION E: DATA & STATE

### E1. Active State Files

| Path | Size | Purpose | Written by |
|---|---|---|---|
| `data/codebase_graph.json` | 148,821 lines | Knowledge graph | scripts/codebase_graph.py |
| `data/node_summaries.json` | 76,869 lines | Per-node summaries | scripts/summarize_nodes.py |
| `data/umh/organism/daemon_state.json` | ~200 bytes | Daemon tick_count: 2478 | substrate/organism/daemon.py |
| `data/umh/coordinator/` | 493 files | Work units + objectives | substrate/organism/coordinator.py |
| `data/umh/assimilation/` | 387 files | Context assimilation artifacts | substrate/organism/context_ingestion_engine.py |
| `data/umh/intelligence/` | 2 files | decisions.jsonl, patterns.json | substrate/intelligence/ |
| `data/runtime/approvals.sqlite` | 20 KB | Approval records | substrate/state/stores/approval_store.py |
| `data/runtime/tailscale_status.json` | 6.8 KB | Network status | cron (every minute) |
| `runtime/.substrate_state.json` | 8 KB | Audio loop state | substrate/execution/bridge/storage.py |
| `runtime/.substrate_station/.inbox.json` | 18 MB | Node event inbox | substrate/execution/bridge/station_bus.py |

### E2. Log Volume

| Directory | Files | Size | Growth |
|---|---|---|---|
| logs/signals/deferred_stale/processed/ | 19,556 | 79 MB | STALE (last write Apr 23) |
| logs/decisions/ | 37 | 17 MB | ~300 lines/day |
| logs/tool_mastery_research/ | 775 | 4.8 MB | Per TME session |
| logs/execution/ | 37 | 336 KB | Daily |
| logs/ (top-level .log) | 80 | ~5 MB | Per cron job |

### E3. Knowledge System Structure

```
Layer 1: Palace     → knowledge/palace/ (19 files, auto-generated from graph)
Layer 2: Graph      → data/codebase_graph.json (148K lines, queryable via scripts/query_graph.py)
Layer 3: Summaries  → data/node_summaries.json (76K lines, one-line per entity)
Layer 4: Raw Source → actual .py/.ts files
Layer 5: Logs       → vault/memory/ + logs/
```

**Retrieval hierarchy (enforced):** Palace > Graph > Summaries > Raw Source > Logs

---

## SECTION F: AGENT ECOSYSTEM

### F1. UMH Runtime Agents (agents/, 11 files)

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

### F2. EOS Projection Agents (projections/eos/agents/, 11 files)

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

### F3. Claude Code Subagents (.claude/agents/, 4 files)

Session-scoped, invoked during development only. Require Anthropic credits.

| Agent | Model | Purpose | Status |
|---|---|---|---|
| eos-code-reviewer | opus | Adversarial code review | ACTIVE (when credits available) |
| eos-researcher | sonnet | Market/ICP research | ACTIVE |
| eos-simplifier | sonnet | Post-implementation simplification | ACTIVE |
| eos-verifier | haiku | Import/syntax/runtime verification | ACTIVE |

### F4. Third-Party Skills (.agents/skills/, 2 packages)

| Skill | Source | Purpose | Status |
|---|---|---|---|
| humanizer | blader/humanizer | Remove AI writing patterns | ACTIVE |
| last30days | charlesdove977/goviralbitch | Research trending topics from last 30 days | ACTIVE |

---

## SECTION G: SKILLS & TOOLS

### G1. Business Domain Skills (skills/, 52 SKILL.md files)

| Category | Skills | Status |
|---|---|---|
| Sales | 20 (analyze_conversation, qualify_lead, objection_handling, proof_promise_plan_close, etc.) | ACTIVE |
| Research | 6 (analyze_icp_signal, detect_icp_patterns, generate_market_report, etc.) | ACTIVE |
| Marketing | 4 (campaign_diagnosis, content_calendar, draft_arena_content_post, generate_content_from_intel) | ACTIVE |
| Content | 5 (video_brief, hook_performance, content_performance, discover_angles, generate_script) | ACTIVE |
| Ops | 13 (9 playbooks + communication_templates, war_room, schedule_event, weekly_ceo_report) | ACTIVE |
| CustomerSuccess | 2 (churn_prevention, onboarding_sequence) | ACTIVE |
| Outreach | 2 (dm_opener, reply_handler) | ACTIVE |

### G2. Tool Mastery Packs (skills/tools/, 96 directories, ~253 files)

Each contains SKILL.md + references/best_practices.md (minimum). Extended packs (5+ files): claude_code (15), react, shadcn_ui, tailwind, typescript, vite, vitest, zod, radix_ui, tanstack_react_query, tanstack_table, sonner, react_hook_form.

**4 incomplete (.creating marker):** nodejs, systemd, tailscale, tmux

### G3. Meta/System Skills (skills/meta/, 14 files)

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

### G4. SaaS Dev Skill (skills/saas-dev-skill/, 146 files)

Standalone multi-agent SaaS builder pipeline. 8 agents: Product Intel > Architecture > Design System > Copy > Component Library > Page Agents > Backend > QA. Full test suite (43 unit tests).

### G5. Claude Code Skills (.claude/skills/, 13 files)

On-demand skill definitions loaded during development sessions: browser-control, claude-code-cli, debug-agent, deploy-service, discord-admin, groq-api, instance-context-gate, material-list-builder, neon-db, new-agent, new-primitive, new-skill, notion-api.

---

## SECTION H: CRON & AUTOMATION

### H1. Every Cron Job (verified against `crontab -l`)

| Schedule | Script | Purpose | Verified |
|---|---|---|---|
| */5 (0,5,10...) | scripts/day_reminder.py | Calendar event reminders | YES |
| */5 (1,6,11...) | scripts/agent_task_executor.py | Poll + execute tasks | YES |
| */5 (2,7,12...) | scripts/orchestrator_loop.py | 1 orchestrator cycle | YES |
| */5 (3,8,13...) | scripts/auth_monitor/health_check.sh | CC auth validation | YES |
| */5 (4,9,14...) | scripts/auth_monitor/session_resurrector.sh | CC session death alerting | YES |
| */15 (0) | scripts/call_prep.py | Meeting prep briefs | YES |
| */15 (2) | scripts/notion_tasks_sync.py | Notion > Neon tasks | YES |
| */15 (4) | scripts/post_meeting_capture.py | Post-meeting outcomes | YES |
| */15 (6) | scripts/calendar_invite_handler.py | Auto accept/decline invites | YES |
| */15 (8) | scripts/noshow_detector.py | No-show detection | YES |
| */15 (10) | scripts/notion_sync_poller.py | Bidirectional task sync | YES |
| */30 | scripts/sync_all.sh | Cross-device git sync | YES |
| 0 */6 | scripts/auth_monitor/cc_keepalive.sh | OAuth token refresh | YES |
| 0 2 | scripts/scheduled/nightly_maintenance.sh | Nightly maintenance | YES |
| 0 3 | scripts/discord_daily_clear.py | Clear Discord channels | YES |
| 0 3 | scripts/emit_signal.py nightly_cycle | Emit nightly signal | YES |
| 0 4 | docker-compose run os-scraper | Overnight Instagram scrape | YES |
| 30 5 | scripts/emit_signal.py morning_ready | Emit morning signal | YES |
| 45 5 | scripts/morning_intel.py | Morning intelligence brief | YES |
| 0 6 | substrate/control_plane/orchestrator/orchestrator.py | Full orchestrator cycle | YES |
| 5 6 | scripts/waiting_on_checker.py | Stale WAITING_ON emails | YES |
| 10 6 | scripts/deadline_monitor.py | Approaching deadlines | YES |
| 30 12 | scripts/midday_checkin.py | Afternoon priorities | YES |
| 0 15 | scripts/inbox_gps_afternoon.py | Email GPS afternoon | YES |
| 0 18 | scripts/eod_sync.py | EOD closing loop | YES |
| 0 6 Sun | scripts/emit_signal.py weekly_cycle | Emit weekly signal | YES |
| 0 6 Sun | scripts/portfolio_brief.py | Portfolio review | YES |
| 0 7 Mon | scripts/relationship_nurture.py | Contact nurture check | YES |
| 0 19 Sun | scripts/weekly_review.py | Full weekly review | YES |
| 0 20 Sun | scripts/week_architect.py | Week planning | YES |
| * * * * * | tailscale status --json | Network status refresh | YES |

**Total: 31 cron entries verified running.**

### H2. Claude Code Hooks (verified in settings.json)

| Hook Type | Script | Purpose |
|---|---|---|
| PreToolUse | scripts/pre_tool_use_log.py | Log every tool call |
| PostToolUse (Edit/Write) | scripts/memory_instant_sync.py | Sync memory files |
| SessionStart | scripts/session_start_context.py | Inject dynamic context |
| SessionStart | scripts/wiki_session_start_hook.py | (MISSING FILE) |
| Stop | scripts/check_stop_condition.py | Validate stop decision |
| Stop | scripts/wiki_stop_hook.py | Capture conversation content |
| Stop | scripts/auto_report_dispatch.py | Report to cockpit/Discord |
| PermissionRequest | scripts/permission_notify.py | Notification on permission |
| SubagentStart | scripts/subagent_start_context.py | Agent-specific context |
| UserPromptSubmit | scripts/user_prompt_capture.py | Capture user messages |

### H3. Pre-commit Gates

| Script | Purpose | Verified |
|---|---|---|
| scripts/check_type_divergence.py | Block shadow types | YES (installed) |
| scripts/check_instance_leak.py | Block hardcoded instance values | YES (installed) |
| scripts/check_projection_leak.py | Block projection names in substrate | YES (installed) |
| scripts/check_dependency_direction.py | Block architecture violations | YES (installed) |

---

## SECTION I: RUNTIME VERIFICATION

### I1. Docker Containers (verified `docker ps`)

| Container | Status | Port | Uptime |
|---|---|---|---|
| os-discord | Up | 8765 | 3 hours |
| os-operator | Up | 8091 | 9 hours |
| os-webhook | Up | 8080 | 43 hours |
| os-scraper | — | — | Runs nightly at 4am then exits |

### I2. Listening Ports (verified `ss -tlnp`)

| Port | Process | Purpose |
|---|---|---|
| 8080 | docker-proxy (os-webhook) | Calendly webhook (Flask) |
| 8091 | docker-proxy (os-operator) | Operator API + cockpit proxy (FastAPI) |
| 8094 | python3 (PID 651413) | Node Mesh WebSocket server |
| 8765 | docker-proxy (os-discord) | CC webhook receiver (aiohttp) |

### I3. Key Processes

- **Node Mesh server** (python3, PID 651413) — standalone process on :8094
- **Docker containers** — 3 running (discord, operator, webhook)
- **Tailscale** — writing status every minute to data/runtime/tailscale_status.json
- **Cron** — 31 jobs active

### I4. Cockpit Deployment

- **Fly.io app:** umh-cockpit (sjc region)
- **Domain:** universalmetaharness.tech
- **Architecture:** nginx serves static React build, proxies /api/* through Tailscale socat to VPS :8091

---

## SECTION J: ARCHITECTURAL TRUTH

### J1. Real Dependency Graph

```
projections/ (EOS, CreatorOS, LyfeOS)
    ↓ imports from
transports/ (Discord, API/HTTP, node mesh, presence)
    ↓ imports from
adapters/ (models, GWS, browser, Notion, calendar, capabilities)
    ↓ imports from
substrate/ (types, control_plane, execution, organism, governance, state, sockets)
```

**Verified compliance:** substrate/ uses only deferred (in-function) imports from adapters/. No substrate/ file imports from transports/ or services/ at module level. Pre-commit hooks enforce this mechanically.

### J2. Violations Found

1. **adapters/google_workspace/gws_scanner.py** imports from `transports.discord.discord_utils` — minor sideways violation (adapters importing from transports)
2. **transports/api/signal_factory.py** contains hardcoded `organization_id="munoz-holdings"` — instance context leak (legacy, grandfathered)
3. **umh/voice_server.py** is architecturally misplaced — should be in services/ or transports/ per layer law

### J3. Dead Code Map

| Path | Reason | Recommendation |
|---|---|---|
| `.claire/` (6 files) | Abandoned worktree remnant, placeholder files | DELETE |
| `10_Wiki/` (37 files) | Duplicate of knowledge/ pages | DELETE |
| `archive/stale_backups/` (1 file, 340 KB) | March 2026 backup tar | DELETE |
| `services/jarvis/` (14 empty dirs) | Never-populated skeleton | DELETE |
| `services/handlers/` (1 empty dir) | Empty | DELETE |
| `adapters/model_adapters/` (empty dir) | Code lives in adapters/models/ | DELETE |
| `substrate/deployment/` (empty dir) | Empty | DELETE |
| `substrate/distribution/` (empty dir) | Empty | DELETE |
| `.claude/worktrees/` (21 stale, ~1 GB) | Stale worktrees at main HEAD | DELETE |
| `logs/signals/deferred_stale/processed/` (19,556 files, 79 MB) | Last modified Apr 23, no longer written | ARCHIVE |
| `scripts/phase75a_classifier.py` (280 lines) | References non-existent directory | DELETE |
| `scripts/phase75a_dep_scanner.py` (232 lines) | Same | DELETE |
| `scripts/shim_retirement_monitor.py` (272 lines) | Convergence complete | DELETE |
| `scripts/measure_phase8_batch.py` (339 lines) | Historical | DELETE |
| `scripts/migrate_module.sh` (78 lines) | Completed migration | DELETE |
| `data/repos/` (191 files) | Stale source snapshots, not synced | ARCHIVE |

**Total recoverable disk:** ~1.2 GB (primarily from stale worktrees)

### J4. What the System Actually IS

**UMH (Universal Mastery Hierarchy)** is a production AI intelligence substrate running on a single VPS (Hostinger, Tailscale-networked). It consists of:

1. **A Discord bot** (os-discord) that is the primary user interface — handles voice (Groq Whisper STT + Kokoro TTS), text commands (60+), pipeline updates, calendar integration, email management, and routes all intelligence through a governed execution spine.

2. **An operator API** (os-operator, FastAPI on :8091) serving both a web cockpit (React, deployed on Fly.io) and programmatic access to the full organism state.

3. **An autonomous organism** (substrate/organism/) with a daemon that ticks continuously (2,478+ ticks), coordinates work units, manages workcells (advisor, executor, researcher, reviewer), propagates changes through dependency graphs, and maintains a world model.

4. **A multi-model intelligence router** (adapters/models/model_router.py) that chains through 10 LLM providers with circuit breaking, quality scoring, and escalation — primarily using Claude Opus 4.6 via CC Agent SDK (free via Max subscription) and Gemini 2.5 Flash as fallback.

5. **A Windows workstation node** (nodes/windows/) deployed as a Windows Service on "Beast" (GPU workstation), connected via WebSocket mesh (:8094), providing desktop automation, clipboard, container management, and Kokoro TTS.

6. **31 cron jobs** managing calendar awareness, email GPS, meeting prep/capture, task execution, deadline monitoring, daily/weekly cycles, and overnight lead scraping.

7. **A knowledge system** with a 148K-line codebase graph, memory palace, 289 wiki pages, and 1,485 conversation archives — all queryable through a 5-layer retrieval hierarchy.

8. **Three application projections** (EOS, CreatorOS, LyfeOS) registered as integration adapters, with EOS fully active (Postgres poller, signal emitter, capability handler, outcome writeback) and the other two defined but awaiting activation.

9. **A governed execution model** with 4-tier permission enforcement (READ/DRAFT/EXECUTE/COMMIT), risk classification, approval workflows, and constitutional principles preventing the system from taking unauthorized actions.

10. **Pre-revenue status.** The system is built to serve Initiate Arena (Lyfe Institute's first product) and the founder's personal workflow. Revenue target: $10K/month net. Current: $0.

---

**END OF AUDIT**

File path of this audit: returned as text output (no file written per instructions).
Total verified file count: 114,817 files (excluding .git/node_modules/__pycache__/.mypy_cache/.ruff_cache/.pytest_cache).
Verification method: `find /opt/OS -type f -not -path '*/.git/*' -not -path '*/node_modules/*' -not -path '*/__pycache__/*' -not -path '*/.mypy_cache/*' -not -path '*/.ruff_cache/*' -not -path '*/.pytest_cache/*' | wc -l`