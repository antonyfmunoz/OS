# /opt/OS Exhaustive Codebase Audit — 2026-05-27

**Total files: 18,512** (verified against `find` — live count 18,518, delta from signals accumulating during audit)
**Total size: ~450 MB** (excluding .git, node_modules, caches)

---

## Grand Summary

| Directory | Files | Purpose |
|-----------|------:|---------|
| Root files | 24 | Config, Docker, docs, env |
| `.agents/` | 64 | Installed CC agent skills (humanizer, last30days) |
| `.claire/` | 3 | Dead worktree remnant — safe to remove |
| `.claude/` | 53 | CC project config: 4 agents, 24 commands, 12 skills, 3 rules, 1 hook |
| `.obsidian/` | 8 | Obsidian vault config |
| `.playwright-mcp/` | 3 | Playwright browser automation snapshots |
| `.vscode/` | 1 | VS Code settings (git warning only) |
| `10_Wiki/` | 37 | AI-generated wiki pages (concepts, entities, decisions, syntheses) |
| `adapters/` | 89 | External system adapters (models, GWS, browser, Notion, calendar) |
| `agents/` | 11 | Agent soul documents (10 business + 1 computer use) |
| `archive/` | 2 | Archive readme + 1 stale backup tar |
| `cockpit/` | 91 | Electron + React 19 desktop cockpit (19 panels, 13 stores, voice) |
| `data/` | 8,606 | Generated data, runtime state, proofs, graph, vault |
| `docker/` | 3 | Computer-use container (Xvfb + VNC + noVNC) |
| `docs/` | 497 | Architecture specs, audit reports, operational doctrines, strategy |
| `infra/` | 4 | Docker env templates + secrets |
| `knowledge/` | 289 | Wiki knowledge graph (135 concepts, 29 entities, 38 syntheses, palace) |
| `logs/` | 6,290 | Runtime logs (signals, decisions, execution, tool mastery research) |
| `media/` | 0 | Empty (higgsfield/ subdir exists) |
| `nodes/` | 44 | Distributed execution (Windows daemon, environment bridges, work packets) |
| `projections/` | 48 | App projections (EOS 30 files, CreatorOS 8, LyfeOS 8) |
| `runtime/` | 2 | Live substrate state + workstation inbox (5.6 MB growing) |
| `saas/` | 43 | EOS SaaS API (Hono + Drizzle + Neon + Python bridge) |
| `scripts/` | 148 | Operational scripts (cron, hooks, CLIs, graph, TME, sync) |
| `services/` | 42 | Legacy service entrypoints (Discord bot, operator API, bridges) |
| `skills/` | 466 | Business skills (53) + saas-dev pipeline (146) + tool mastery (253) + meta (14) |
| `substrate/` | 512 | UMH brain (control plane, execution, governance, state, understanding) |
| `tests/` | 63 | Test suite (60 root + 3 substrate/ + 1 fixture) |
| `transports/` | 58 | I/O surfaces (API, Discord, node mesh, presence handlers) |
| `umh/` | 1 | Voice server (WebSocket STT/TTS bridge) |
| `vault/` | 1,010 | Conversation memory (798 transcripts + 212 summaries) |
| **TOTAL** | **18,512** | |

---

## 1. Root-Level Files (24 files)

| File | Lines | Bytes | Description |
|------|------:|------:|-------------|
| `.dockerignore` | 24 | 258 | Docker build exclusion rules |
| `.env` | 122 | 12,825 | Live environment variables — gitignored |
| `.env.example` | 69 | 3,456 | Env template with placeholders |
| `.env.sessions` | 3 | 289 | CC auth helper: OAuth token for Claude Max |
| `.gitignore` | 110 | 1,953 | Git ignore rules |
| `.mcp.json` | 8 | 135 | MCP server config (context7) |
| `AGENTS.md` | 23 | 858 | Cross-agent config doc |
| `ARCHITECTURE.md` | 465 | 24,971 | Master architecture spec |
| `CLAUDE.local.md` | 53 | 2,055 | Local CC preferences (gitignored) |
| `CLAUDE.md` | 416 | 19,574 | Developer Agent soul document |
| `Dockerfile` | 18 | 871 | Python 3.11-slim + Node 20 + ffmpeg + playwright |
| `Makefile` | 7 | 196 | test-migration targets |
| `PHILOSOPHY.md` | 485 | 11,922 | EntrepreneurOS philosophy manifesto |
| `PROTOCOLS.md` | 256 | 8,684 | 4-layer protocol architecture (L0-L3) |
| `README.md` | 116 | 3,522 | Project README |
| `cloud.md` | 78 | 2,768 | Root system-context file |
| `cockpit-current.png` | — | 24,364 | Screenshot of current cockpit UI |
| `docker-compose.yml` | 148 | 4,310 | Docker Compose (os-discord, os-operator, os-webhook, os-scraper) |
| `install.sh` | 69 | 2,159 | One-line curl installer |
| `patch_pycord.py` | 121 | 4,089 | Build-time py-cord voice_client patch |
| `pyproject.toml` | 59 | 1,385 | Python project config (hatchling, deps, ruff, pytest) |
| `requirements.txt` | 22 | 305 | Flat pip requirements |
| `setup.sh` | 65 | 1,836 | First-run setup script |
| `skills-lock.json` | 15 | 426 | CC skills lock (humanizer, last30days) |

---

## 2. `.agents/` (64 source files)

Installed CC agent skills via skills-lock.json.

### humanizer/ (3 files)
- `README.md` (143 lines) — docs for AI writing de-detection
- `SKILL.md` (488 lines) — full prompt for detecting/removing AI writing signs
- `WARP.md` (52 lines) — warp.dev context

### last30days/ (61 files)
30-day topic research skill with modular library.

**Key files:**
- `scripts/last30days.py` (1,200 lines) — main orchestrator
- `scripts/store.py` (654 lines) — persistent storage
- `scripts/lib/` (18 Python files) — bird_x, brave_search, cache, dates, dedupe, entity_extract, env, http, models, normalize, openai_reddit, openrouter_search, parallel_search, reddit_enrich, render, schema, score, ui, websearch, xai_x, youtube_yt
- `scripts/lib/vendor/bird-search/` (13 JS files) — vendored Twitter/X search client
- `tests/` (9 files) — pytest test suite
- `fixtures/` (5 JSON files) — sample test data

---

## 3. `.claire/` (3 files)

Dead worktree from completed full-convergence branch.
- 2 placeholder files (content: "placeholder")
- 1 orphaned test_registry.py (157 lines)
- **Safe to remove entirely.**

---

## 4. `.claude/` (53 files)

### Top-level (6 files)
- `CLAUDE.md` (141 lines) — project instructions
- `settings.json` (211 lines) — model=opus, env, permissions, 11 hook categories
- `settings.local.json` (27 lines) — extra permissions, MCP servers
- `last_cc_version` — version tracker (2.1.122)
- `scheduled_tasks.lock` — scheduled task lock
- `hooks/validate_change.py` (114 lines) — pre-tool-use risk classifier

### agents/ (4 files)
- `eos-code-reviewer.md` (46 lines) — adversarial code review (opus)
- `eos-researcher.md` (33 lines) — ICP/market research (sonnet)
- `eos-simplifier.md` (34 lines) — code simplification (sonnet)
- `eos-verifier.md` (35 lines) — verification (haiku)

### commands/ (24 slash commands)
babysit, browser-task, commit-push-pr, constraint-check, council, deploy, eod-sync, eos-audit, eos-build, eos-deploy, eos-fix, eos-sync, morning-brief, primitive-check, run-outreach, session-start, start-loops, status, test-agent, test-all-agents, test-all, update-skills, use-opusplan, voice-debug

### rules/ (3 files)
- `agents.md` — agent creation rules
- `python.md` — Python coding rules
- `skills.md` — skill creation rules

### skills/ (12 files)
browser-control, claude-code-cli, debug-agent, deploy-service, discord-admin, groq-api, material-list-builder, neon-db, new-agent, new-primitive, new-skill, notion-api

### worktrees/ (4 files)
Stale worktree `close-final-3-gaps/` with only pytest cache artifacts. Safe to remove.

---

## 5. `substrate/` (512 files, 138,777 lines, 5.06 MiB)

The UMH brain. Largest code directory.

### By subdirectory:

| Subdirectory | Files | Lines | % |
|---|---:|---:|---:|
| `execution/` | 168 | 75,345 | 56.1% |
| `control_plane/` | 66 | 22,746 | 16.2% |
| `state/` | 45 | 9,576 | 6.9% |
| `understanding/` | 39 | 9,581 | 7.0% |
| `composition/` | 47 | 7,567 | 5.3% |
| `organism/` | 23 | 2,583 | 1.5% |
| `governance/` | 14 | 2,494 | 1.7% |
| `sockets/` | 15 | 1,440 | 1.0% |
| `foundation/` | 9 | 546 | 0.3% |
| `ontology/` | 8 | 290 | 0.2% |
| `memory/` | 6 | 1,127 | 0.7% |
| `observability/` | 6 | 485 | 0.4% |
| `integrations/` | 5 | 420 | 0.3% |
| `intelligence/` | 4 | 1,128 | 0.7% |
| `reality_model/` | 4 | 733 | 0.5% |
| `contracts/` | 2 | 99 | 0.1% |
| `workstation/` | 2 | 238 | 0.2% |
| Root (`__init__.py`, `types.py`) | 2 | 1,561 | 1.0% |

### Key files:
- `types.py` (1,400 lines) — single Pydantic type system, 30+ models
- `__init__.py` (161 lines) — Substrate public API
- `control_plane/runtime/gateway.py` (1,923 lines) — EntrepreneurOSGateway
- `control_plane/runtime/cognitive_loop.py` (1,530 lines) — full Perceive/Understand/Plan/Execute cycle
- `control_plane/orchestrator/orchestrator.py` (1,906 lines) — strategic intelligence layer
- `control_plane/goals/goal_selector.py` (1,485 lines) — goal selection + focus
- `execution/spine.py` (522 lines) — 8-stage execution pipeline
- `execution/bridge/` (71 files) — session management, voice, task, node orchestration

### execution/workers/workstation/ (42 files)
Constitutional engines and workstation operational embodiment. Largest files:
- `constitutional_strategic_intelligence_engine_v1.py` (1,852 lines)
- `constitutional_substrate_governance_layer_v1.py` (1,559 lines)
- `constitutional_epistemic_intelligence_engine_v1.py` (1,512 lines)
- `constitutional_identity_continuity_engine_v1.py` (1,494 lines)
- `persistent_substrate_continuity_engine_v1.py` (1,469 lines)
- `governed_recursive_orchestration_engine_v1.py` (1,464 lines)
- `distributed_constitutional_substrate_federation_v1.py` (1,444 lines)

### composition/mastery/ (40 files)
Tool Mastery Engine subsystem: research (18 files), management (11 files), authoring (11 files)

### control_plane/ (66 files across 14 subdirs)
actions/ (12), agents/ (7), context/ (3), coordination/ (2), delegation/ (2), events/ (3), goals/ (2), identity/ (2), invariants/ (4), onboarding/ (3), orchestrator/ (9), proactive/ (2), router/ (4), runtime/ (4), scheduling/ (5), signals/ (2), strategy/ (5)

### state/ (45 files across 13 subdirs)
business/ (3), context/ (2), finance/ (3), lifecycle/ (2), logs/ (2), memory/ (7), metrics/ (3), permissions/ (2), preferences/ (2), profiles/ (2), providers/ (2), registries/ (6), session/ (2), storage/ (2), stores/ (15), tenancy/ (2), work/ (2)

### understanding/ (39 files across 13 subdirs)
deliberation/ (2), domains/ (6), embedding/ (3), intelligence/ (6), interpretation/ (2), knowledge/ (6), ontology/ (3), patterns/ (3), perception/ (10), reality/ (3), research/ (2), signals/ (2), world_model/ (2), world_pulse/ (2)

---

## 6. `adapters/` (89 files, 19,173 lines, 679 KiB)

### By subdirectory:

| Subdirectory | Files | Lines | Description |
|---|---:|---:|---|
| Root | 3 | 49 | README, __init__, Adapter Protocol |
| `adapter_engine/` | 16 | 3,533 | Lifecycle, manifest, capability discovery, ingestion pipeline |
| `browser/` | 1 | 10 | BrowserAgent re-export |
| `browser_exports/` | 8 | 1,489 | Playwright export scripts (Claude, ChatGPT, Instagram) |
| `calendar/` | 3 | 1,184 | Meeting lifecycle + travel management |
| `capabilities/` | 6 | 962 | Creative gen, Goose, UI-TARS, Voice-Pro harnesses |
| `data_source_adapters/` | 8 | 992 | Ingestion sources + conversation parsers |
| `google_workspace/` | 7 | 3,837 | EmailGPS, GWSConnector, GWSScanner, doc creator/filer |
| `higgsfield/` | 2 | 112 | Higgsfield video API client |
| `models/` | 11 | 3,513 | model_router.py (1,442 lines), agent_runtime, cc_sdk, codex_cli, hermes_cli, opencode_cli + routing/ |
| `notebooklm/` | 2 | 307 | Neon ↔ NotebookLM sync |
| `notion/` | 14 | 2,404 | Notion publisher, sync + integration (11 files) |
| `scrapling/` | 2 | 141 | Stealth HTTP fetching |
| `tool_adapters/` | 6 | 640 | Governed filesystem, shell, git, tmux adapters |

### Largest files:
- `google_workspace/email_gps.py` (1,429 lines)
- `models/model_router.py` (1,442 lines)
- `google_workspace/gws_connector.py` (1,115 lines)

### Note: `model_adapters/` exists but contains only __pycache__ — candidate for cleanup.

---

## 7. `transports/` (58 files, 13,053 lines, 466 KiB)

| Subdirectory | Files | Lines | Description |
|---|---:|---:|---|
| Root | 1 | 0 | Package init |
| `api/` | 13 | 4,097 | FastAPI surface (signal intake, cockpit, computer use, distribution, operator, voice, workstation) |
| `api/webhooks/` | 2 | 434 | Calendly webhook handler (Flask) |
| `channels/` | 2 | 452 | Two-way channel system (Discord, Telegram, Webhook, Console) |
| `discord/` | 5 | 1,026 | Discord utils, interface adapter, signal factory, spine integration |
| `node_mesh/` | 6 | 813 | WebSocket mesh server (:8094), config, metrics buffer, registry |
| `node_mesh/integration/` | 6 | 343 | Capability handler, manifest, outcomes, signals, types |
| `presence/` | 1 | 0 | Package init |
| `presence/handlers/` | 7 | 2,124 | cc_command_handler, intent_handler, pipeline_handler, substrate_command_handler (938 lines), voice_handler |
| `presence/handlers/reports/` | 15 | 3,764 | 13 report handlers (adapter, capability, constitution, continuity, economics, epistemic, federation, governance_intelligence, identity, orchestration, resilience, strategy, telos) |

---

## 8. `services/` (42 files, 12,988 lines, 721 KiB)

### Python services (21 files):
- `discord_bot.py` (1,930 lines) — DEX Discord bot entrypoint
- `discord_bot_commands.py` (2,740 lines) — extracted @bot.command handlers
- `discord_message_handlers.py` (1,087 lines) — on_message dispatch
- `operator_api.py` (593 lines) — FastAPI operator workstation backend
- `icp_scorer.py` (603 lines) — ICP lead scoring
- `cost_tracker.py` (414 lines) — API cost tracking
- `kpi_tracker.py` (411 lines) — KPI pipeline metrics
- `cc_webhook_receiver.py` (309 lines) — CC reply webhook → Discord
- `bridge_health.py` (315 lines) — VPS watchdog for Windows bridge
- `magic_link_handler.py` (358 lines) — Gmail magic-link interceptor
- `oauth_device_flow.py` (304 lines) — headless OAuth re-auth
- `local_bridge_server.py` (257 lines) — Windows-side bridge
- `export_bridge_handler.py` (264 lines) — Windows export handler
- `overnight_scrape.py` (251 lines) — overnight lead scraping
- `goal_api.py` (194 lines) — goal selection REST API
- `local_bridge_client.py` (172 lines) — VPS bridge client
- `higgsfield_webhook.py` (131 lines) — Higgsfield media callbacks
- `trigger_export.py` (128 lines) — browser export trigger
- `heartbeat.py` (113 lines) — health monitoring
- `browser_adapter.py` (98 lines) — Camoufox anti-detect browser
- `magic_link_server.py` (59 lines) — magic-link server (:8769)

### auth_flows/ (3 files): chatgpt.py (456 lines), claude.py (210 lines)
### Data files (10): .env, export_profiles.yaml, requirements.txt, JSON state files
### Docs (4): CLAUDE.md, LOCAL_BRIDGE_SETUP.md, setup_scheduler.bat, local_bridge_send_to_discord.sh
### umh/data/ (2): watermark JSONL files

### Note: `jarvis/` is completely empty (14 subdirs, 0 files) — abandoned scaffolding. `handlers/` also empty.

---

## 9. `projections/` (48 files, 9,446 lines, 347 KiB)

### eos/ — EntrepreneurOS (30 files)
- `entities.py` (879 lines) — full entity hierarchy
- `agents/` (12 files) — base + 10 department agents (CEO, Sales, Marketing, Finance, CustomerSuccess, HR, Legal, Operations, Product, Engineering)
- `integration/` (8 files) — EOS-UMH bridge (poller, signals, handlers, outcomes, tables)
- `views/` (4 files) — pipeline, KPI, activity views
- `workflows/` (4 files) — outreach, followup, content calendar

### creatoros/ — CreatorOS (8 files)
Integration: correlation, handlers, manifest, outcomes, signals, tables

### lyfeos/ — LyfeOS (8 files)
Integration: correlation, handlers, manifest, outcomes, signals, tables

---

## 10. `scripts/` (148 files, 69,835 lines, 2.8 MiB)

### Root scripts (126 files) — key ones:
- `orchestrator.py` (1,124 lines) — continuous autonomous execution
- `codebase_graph.py` (1,215 lines) — persistent codebase knowledge graph
- `notion_setup.py` (1,082 lines) — Notion database architecture
- `notion_seed_all.py` (933 lines) — venture seeding
- `incremental_graph.py` (772 lines) — dirty-set incremental graph updates
- `build_notion_workspace.py` (713 lines) — full Notion workspace builder
- `windows_interactive_desktop_relay.ps1` (1,358 lines) — Windows GUI relay
- `watch_graph.py` (526 lines) — real-time file watcher for graph
- `run_graphify.py` (526 lines) — enrichment layer
- `build_palace.py` (484 lines) — memory palace generator

### Subdirectories:
- `auth_monitor/` (7 files) — CC credential management, health checks, session isolation
- `cron/` (1 file) — sync ritual crontab
- `graph_hooks/` (2 files) — post-merge + pre-commit hooks
- `hooks/` (1 file) — post-merge sync
- `scheduled/` (6 files) — morning prep, nightly consolidation, weekly review (shell + CP wrappers)
- `workers/` (1 file) — Discord approval worker

### Note: `agent_executor.log` (39,536 lines, 1.7 MB) is a runtime log — should be gitignored.

---

## 11. `tests/` (63 files, 13,452 lines, 472 KiB)

60 root-level test files covering:
- Convergence acceptance, sprint 1-5 smoke/boundary/recovery/hygiene/doc tests
- Execution: spine, authority engine, pipeline, trace, feedback
- Ingestion: GWS source, canonical memory reconciliation, generic orchestrator, authority tier
- Substrate: types, entity store, feedback loop
- Domain bridges: business, life, creator
- Node mesh: registry, WS integration, daemon E2E
- TME: active tool context, mastery assurance gate, natural language resolver
- Governance, knowledge layers, ontology, philosophy lenses, product connections
- Persistent loops, provider state, work state, transformation state ledger

Plus `fixtures/ingestion_fixture.md` and `substrate/` subdir (3 test files).

---

## 12. `docker/` (3 files)

`docker/computer-use/`:
- `Dockerfile` (41 lines) — Ubuntu 22.04 + Xvfb + VNC + noVNC + Chromium
- `docker-compose.beast.yml` (38 lines) — 3 CU agent containers
- `start.sh` (13 lines) — entrypoint

---

## 13. `infra/` (4 files)

`infra/docker/`:
- `.env.example` (69 lines) — env template
- `.env.sessions` (3 lines) — CC OAuth token
- `services.env` (44 lines) — **CONTAINS LIVE SECRETS**
- `umh.env` (108 lines) — **CONTAINS LIVE SECRETS**

---

## 14. `data/` (8,606 files, 329 MB)

### Root files (15): codebase_graph.json (4.5 MB), node_summaries.json (3.5 MB), graphify_overlay.json (361 KB), + 12 smaller files

### By subdirectory:

| Subdirectory | Files | Size | Description |
|---|---:|---:|---|
| `codebase_pages/` | 6,292 | 26 MB | Generated graph docs (4,299 functions, 1,302 classes, 683 files, 6 modules) |
| `runtime/` | 1,819 | 48 MB | Runtime state, proofs, test artifacts, 4 SQLite DBs, 17 empty subdirs |
| `vault/memory/` | 104 | 764 KB | 93 conversations + 11 summaries |
| `umh/` | 9 | 238 MB | **Dominated by mesh/metrics.jsonl at 238 MB — needs rotation** |
| `repos/` | 191 | 4.4 MB | SaaS repo data (EntrepreneurOS, LYFEOS, CreatorOS) |
| `audits/` | 32 | 708 KB | Audit markdown/text files |
| `canonical_source_records/` | 32 | 260 KB | w0_001/ Google Doc JSON records |
| `drive_doc_ingestion/` | 31 | 276 KB | Document ingestion JSON files |
| `migration/` | 30 | 1.6 MB | Migration artifacts (r8b through r8h) |
| `playgrounds/` | 9 | 72 KB | Play sessions |
| `voice_acks/` | 6 | 264 KB | 6 WAV acknowledgment files |
| `snapshots/` | 6 | 40 KB | 2026-05-25 system snapshots |
| `system/` | 4 | 100 KB | Classification indices |
| `workflow_state/` | 4 | 20 KB | Workflow JSON files |
| `agent_state/` | 3 | 16 KB | Agent state (healer, librarian, observer) |
| `sandboxes/` | 3 | 28 KB | Sandbox markers |
| Smaller dirs (1-2 files each) | ~15 | ~200 KB | backups, config, drive inventories, proposals, registries |
| Empty dirs (0 files) | 6 | 0 | browser_profiles, environment_maps, exports, onboarding, permissions, voice |

---

## 15. `knowledge/` (289 files, 454 KiB)

| Subdirectory | Files | Description |
|---|---:|---|
| Root | 8 | WIKI_RULES, index, log, retrieval_rules, cloud_palace, Layer 3 specs |
| `concepts/` | 135 | Auto-promoted concept pages with YAML frontmatter |
| `synthesis/` | 38 | Cross-session synthesized insights |
| `entities/` | 29 | Named system entities |
| `palace/` | 19 | Memory palace (index + 6 candidates + 7 rooms + 5 wings) |
| `decisions/` | 6 | Strategic/architectural decisions |
| `skills/marketing/content/remotion/` | 52 | Remotion video composition skill + best practices |
| `domains/` | 1 | Domain catalog template |
| `sources/` | 1 | .gitkeep placeholder |

---

## 16. `docs/` (497 files, 4.9 MiB)

| Subdirectory | Files | Description |
|---|---:|---|
| Root | 5 | SYSTEM_ARCHITECTURE, brand-identity, corporate-structure, deploy, phase77 report |
| `audits/` | 153 | Phase audit reports (phases 0-74 + tool mastery + convergence + essentialism) |
| `audits/convergence/` | 11 | Sprint 1-5 + final convergence reports |
| `audits/rollback/` | 2 | Pre-phase crontab snapshots |
| `operations/` | 182 | Versioned operational doctrines, work orders, adapter policies |
| `system/` | 100 | Module inventory (13K lines), dependency data (7K lines), status docs, contracts |
| `strategy/` | 11 | Company map, empire architecture, master intention lock, doctrine index |
| `superpowers/plans/` | 4 | Major convergence/unification plans (up to 3,378 lines each) |
| `superpowers/specs/` | 7 | Architecture design specs (up to 1,627 lines) |
| `sessions/` | 6 | Build session notes |
| `migrations/` | 6 | Migration plans (core→substrate, eos_ai→substrate, etc.) |
| `plans/` | 3 | Execution backend/unification/wiring plans |
| `design-system/` | 2 | Three-state discipline, WorldView reference |
| `mvp/` | 2 | Golden paths, operator guide |
| `canonical/` | 1 | umh_synthesis.md (1,998 lines — largest single doc) |
| `changes/` | 1 | Gateway/cogloop removal changelog |
| `setup/` | 1 | Windows bridge autostart guide |

---

## 17. `vault/` (1,010 files, 5.7 MiB)

### conversations/ (798 files)
UUID-named markdown files with YAML frontmatter. Full CC session transcripts. 18-7,697 lines each.

### summaries/ (212 files)
LLM-generated session summaries with salience scoring (low/medium/high/critical) and promotion recommendations.

---

## 18. `agents/` (11 files, 50 KiB)

Soul documents for 10 business department agents + 1 computer use agent:
ceo_agent, computer_use_agent, customer_success_agent, engineering_agent, finance_agent, hr_agent, legal_agent, marketing_agent, operations_agent, product_agent, sales_agent

---

## 19. `skills/` (466 files, 6.9 MiB)

### Business skills (53 SKILL.md files across 7 domains):
- Content/ (2), CustomerSuccess/ (2), Marketing/ (4), Ops/ (13), Outreach/ (2), Research/ (6), Sales/ (20), content/ (3), developer/ (1)

### meta/ (14 files):
ceo_framework, ea_framework, claude_code_best_practices, tool_mastery_engine (+ 3 references + 1 script), operationalization_principle, portfolio_framework, notion_discord_pattern, plugin_skill_audit (+ registry), check_cc_updates

### saas-dev-skill/ (146 files):
Multi-agent SaaS product engineering pipeline (TypeScript):
- 12 agents (architecture, backend, component-library, copy, design-system, page, pm-orchestrator, product-intel, qa + runner + types + store)
- 8 analytics-delivery modules
- 9 backend-wirer modules
- 3 copy-planner modules
- 6 intake modules
- 5 orchestrator modules
- 8 react-gen modules
- 10 spec-parser modules
- 57 unit tests
- CC skills (7), templates (3), scripts (2), shared schemas (2)

### tools/ (253 files):
Tool Mastery Engine skills for 93 tools. Each tool has SKILL.md + references/best_practices.md. Some have additional reference files (anti_patterns, examples, integrations). Tools include: acrobat, amazon_ads, amazon_associates, amazon_seller_central, anthropic_api, apify, aws, bash, brave_search, calendly, canva, claude_agent_sdk, claude_code (+ 10 extra refs), clo3d, cron, davinci_resolve, defuddle, discord, docker, drizzle_orm, fastembed, firecrawl, fl_studio, flask, git, github_api, gmail, google_ads, google_analytics, google_gemini, google_workspace, groq, gusto, higgsfield, hono, illustrator, instagram, json_canvas, kick, kit, lightroom, mercury, meta_ads, meta_graph_api, neon_postgres, nodejs, notebooklm, notebooklm_mcp, notion, obs, obsidian_bases, obsidian_cli, obsidian_markdown, ollama, openai, openrouter, perplexity, photoshop, pinterest, playwright, posthog, python, quickbooks, radix_ui, react, react_hook_form, reddit_api, relay, remotion, rumble, shadcn_ui, shopify, sonner, stitch, stripe, systemd, tailscale, tailwind, tanstack_react_query, tanstack_table, telegram, tiktok, tiktok_ads, tmux, twitch, typescript, vite, vitest, voice_pipeline, whisper, whop, x_twitter_api, youtube, youtube_ads, yt_dlp, zod

---

## 20. `saas/` (43 files, 259 KiB)

EOS SaaS API backend:
- `api/index.ts` (96 lines) — Hono entrypoint mounting all routers (:8091)
- `api/routes/` (18 route files) — activity, agent, agents, analytics, approvals, dex, events, execution, governance, interactions, knowledge, organism, outcomes, settings, skills, system, tasks, ventures, workflows
- `api/middleware/auth.ts` — x-org-id header validation
- `api/lib/python_bridge.ts` — stdin/stdout JSON bridge to Python AI
- `bridge/agent_bridge.py` (138 lines) — Python-side bridge
- `db/schema.ts` (570 lines) — full Drizzle ORM schema
- `db/client.ts` (91 lines) — RLS-aware Drizzle client
- `db/migrate.ts` (167 lines) — migration runner (pgvector, RLS, eos_app role)
- `db/seed.ts` (563 lines) — Munoz Holdings portfolio seed
- `db/migrations/` (10 SQL files + meta) — 0000-0009

---

## 21. `nodes/` (44 files, 204 KiB)

### distribution/ (3 files): distributor, first_boot
### environments/ (18 files): bootstrap, chrome launch, execution bindings, heartbeat, packet validation, pull protocol, queue paths, result ingestion, tmux surface, VPS bridge, work packets, Windows desktop adapter
### windows/ (23 files):
- `kokoro_server.py` (123 lines) — Kokoro TTS on Beast GPU
- `umh_desktop/tray.py` (197 lines) — system tray companion
- `umh_node/` (6 files) — WebSocket client, config, governance, metrics, service, workspace
- `umh_node/adapters/` (6 files) — clipboard, container, desktop, filesystem, shell

---

## 22. `cockpit/` (91 files, 965 KiB)

Electron 42 + React 19 + Tailwind 4 + Zustand desktop cockpit.

### Architecture:
- `src/main/index.ts` (213 lines) — Electron main process
- `src/preload/index.ts` (33 lines) — IPC bridge
- `src/renderer/App.tsx` (93 lines) — root with Clerk auth

### Components (22):
Shell, LeftRail, RightRail, NavRail, TitleBar, HudBar, ChatDrawer, CommandPalette, VoiceCommandBar (403 lines), GraphView, AgentCard, TaskBlock, TimelineView, RingGauge, SplitPane, ControlPanel, LivePreview, OverlayToggle, FabSmall, FabMedium, FabLarge, VoiceWaveform

### Panels (19):
Dashboard, Agents, Tasks, Activity, Analytics, Settings, Execution, Knowledge, Company, Editor, Portfolio, Approvals, Workflows, Infrastructure, Comms, Skills, Profile, Tracking, Experiments

### Stores (13):
cockpit, agent, task, activity, voice, chat, system, execution, settings, analytics, knowledge, editor, approval

### API (4): client, websocket, voice-controller, voice-ws
### Hooks (4): usePolling, useKeyboard, useWebSocket, useVoiceDetection
### Styles (2): tokens.css, globals.css

### Built artifacts:
- `dist-web/` — production HTML + CSS + JS bundles (284 KB JS)

---

## 23. `umh/` (1 file)

`voice_server.py` (458 lines) — cockpit voice WebSocket bridge (:8095) with Groq Whisper STT, Kokoro TTS (Beast GPU), rolling conversation memory, instant ack, always-on listening.

---

## 24. Remaining small directories

### `.obsidian/` (8 files)
Obsidian vault config: appearance, app, community-plugins (dataview, kanban, tasks, templater, git), core-plugins, daily-notes, graph, templates, types

### `.playwright-mcp/` (3 files)
Browser automation snapshots: Instagram login page, UMH app initializing, console log

### `.vscode/` (1 file)
`settings.json` — `git.ignoreLimitWarning: true`

### `10_Wiki/` (37 files)
AI-generated wiki pages from 2026-05-14: 24 concepts, 6 entities, 4 syntheses, 3 decisions

### `archive/` (2 files)
README_STATUS.md + stale_backups/eos_backup_20260326.tar.gz (333 KB)

### `logs/` (6,290 files, 76 MB)
- Root (74 files): 32 .log files, 11 .jsonl/.json structured logs, 12 morning_*.log, 13 nightly_*.log, 2 weekly_*.log, 4 debug PNGs, 2 export files
- `decisions/` (33 files) — daily JSONL decision logs
- `execution/` (33 files) — daily JSONL execution traces
- `signals/` (5,434 files) — signal lifecycle receipts (5,326 in deferred_stale/processed/ alone)
- `tool_mastery_research/` (637 files) — TME research sessions (105 test_tool sessions + 1 google_drive)
- `idempotency/` (70 files) — SHA-hash dedup guards
- `deferred/` (6 files) — deferred action envelopes
- `relay_queue/` (1 file) — outbound relay queue

### `media/` (0 files)
Empty. `higgsfield/` subdir exists.

---

## Critical Findings

### Security
- `infra/docker/services.env` and `infra/docker/umh.env` contain live production secrets in plain text
- `services/.env` contains live API keys (untracked, gitignored)

### Cleanup candidates
- `.claire/` — dead worktree, 3 files, safe to remove
- `.claude/worktrees/close-final-3-gaps/` — dead worktree, pytest cache only
- `adapters/model_adapters/` — empty dir (only __pycache__)
- `services/jarvis/` — empty scaffolding (14 subdirs, 0 files)
- `services/handlers/` — empty dir
- `scripts/agent_executor.log` — 1.7 MB runtime log, should be gitignored
- `data/umh/mesh/metrics.jsonl` — 238 MB, needs rotation
- `runtime/.substrate_station/antony-workstation.inbox.json` — 5.6 MB and growing, needs rotation

### Architecture notes
- No files exceed the 3,000-line quality gate
- `substrate/` is 56% execution code — execution/bridge/ alone is 71 files
- `execution/workers/workstation/` has 42 files averaging 1,000+ lines — heaviest concentration
- 93 tool mastery skills covering the full tech/business stack
- 3 SaaS projections (EOS, CreatorOS, LyfeOS) follow identical socket-based integration pattern
