# Project Exploration Audit: /opt/OS

> Date: 2026-05-13
> Mode: READ-ONLY static analysis
> Approach: Fresh-eyes orientation — no prior context assumed

---

## Executive Summary

This is a **~275K-LOC Python project** (plus ~28K LOC TypeScript, ~27K LOC Markdown)
living at `/opt/OS/` on a VPS. It appears to be a **single-founder AI-powered business
operating system** — a layer that wraps LLMs (currently Gemini 2.5 Flash, Ollama, and
Claude via CLI subprocess) with contextual intelligence (agent hierarchy, business stage
awareness, memory, knowledge domains) and exposes them through Discord and cron-scheduled
automations.

The project uses **at least four names for itself**: UMH (Universal Mastery Hierarchy),
EntrepreneurOS/EOS, AgentOS, and universal-meta-harness. Documentation settles on "UMH"
as the substrate and "EOS" as one application projection, but older docs use "EOS" for
everything.

**What's actually running:** 2 of 5 defined Docker services (Discord bot + Calendly webhook),
~30 cron jobs, a Neon PostgreSQL database, and a Claude Code CLI session on the VPS.
The Discord bot is the primary interface — confirmed in daily use.

**Scale of ambition vs. state of execution:** The documentation describes a 14-stage governed
runtime spine, 48 core subsystem directories, constitutional governance, federation readiness,
and sovereign operational accountability. The working code is a Discord bot that routes
messages through an LLM with context injection, plus an ingestion pipeline with test proofs.
The gap between documentation and working software is the project's defining characteristic.

**Key numbers:**
- 3,488 Python files (274K LOC)
- 8,102 Markdown files (27K LOC)
- 3,183 JSON files (297K LOC — mostly generated data/proofs)
- 165 skill definitions, 18 agent soul documents, 24 Claude Code commands
- 639 test files (423 legacy, 216 active)
- 493 files in `core/` (392 follow a `_v1.py` pattern)
- 234 MB in `data/` directory (accumulated runtime artifacts)

---

## Phase 0: Structural Facts

### Directory Tree (depth 3, significant dirs only)

```
/opt/OS/                          (repository root)
├── .agents/skills/               (plugin skills: humanizer, last30days)
├── .claude/                      (Claude Code config)
│   ├── agents/                   (4 subagents: code-reviewer, researcher, simplifier, verifier)
│   ├── commands/                 (24 slash commands)
│   ├── hooks/                    (1 pre-tool validation hook)
│   ├── rules/                    (4 rule files: python, agents, skills, ?)
│   └── skills/                   (13 Claude Code skills)
├── .planning/codebase/           (7 planning docs)
├── 01_Inbox/                     (185 files — signals, notes)
├── 04_Offers/                    (1 file — Initiate Arena)
├── 05_Workflows/                 (25 files — Sales, Ops, Marketing, Research)
├── 07_Knowledge/                 (16 files — ICP, Market Reports)
├── 09_Content/                   (2 files — Content Ideas)
├── 10_Wiki/                      (5,998 files)
│   ├── codebase/                 (5,804 auto-generated graph wiki pages)
│   ├── concepts/                 (111 concept pages)
│   ├── palace/rooms/             (7 memory palace rooms)
│   └── synthesis/                (33 synthesis pages)
├── 14_Templates/                 (13 Notion-style templates)
├── agents/                       (18 agent soul documents)
├── archive/                      (17 MB — umh_reference, tools_duplicate, core_legacy, etc.)
├── config/                       (17 JSON/YAML config files)
├── core/                         (493 Python files, 118K LOC — "substrate contracts")
│   ├── [45 subdirectories]       (ontology, governance, workstation, runtime, etc.)
│   └── workstation/              (41 files, 26K LOC — largest core subdir)
├── data/                         (234 MB)
│   ├── audits/                   (audit reports)
│   ├── runtime/                  (52 MB — memory store, proofs, continuity, reconciliation)
│   ├── drive_doc_ingestion_tab_aware/ (111 MB — GWS doc ingestion cache)
│   └── semantic_space/           (41 MB)
├── docs/                         (623 markdown files, 7 MB)
│   ├── system/                   (96 phase968XX files + contracts)
│   └── operations/               (182 operational docs)
├── eos_ai/                       (459 Python files — ALL are 4-line import shims to runtime/)
├── frontend/                     (3 files — minimal web UI stub)
├── infra/docker/                 (alternate Docker setup)
├── knowledge/                    (TypeScript knowledge module stub)
├── logs/                         (33 MB — operational logs)
├── orchestrator/                 (Markdown-only — no Python)
├── parsers/                      (7 Python files, 448 LOC)
├── runtime/                      (465 Python files, 113K LOC — "live runtime")
│   ├── [125 top-level modules]   (cognitive_loop, model_router, gateway, memory, etc.)
│   ├── transport/                (164 files, 55K LOC — session/voice/meeting/daemon layer)
│   ├── substrate/                (164 files — ALL are 1-line re-exports from transport/)
│   ├── ingestion/                (6 files, 1.4K LOC — canonical ingestion pipeline)
│   └── domain_bridge/            (4 files, 356 LOC — domain projection layer)
├── saas/                         (TypeScript Hono API + Drizzle ORM, v0.1.0)
├── scripts/                      (187 Python files, 52K LOC — operator tooling + cron)
├── services/                     (21 Python files, 19K LOC — Discord bot, DM monitor, etc.)
├── skills/                       (165 SKILL.md files across 12 categories)
│   ├── tools/                    (96 tool skills — external tool expertise)
│   └── [Sales, Ops, Research, Marketing, etc.]
├── templates/                    (1 Python file)
├── tests/                        (639 Python files, 82 MB)
│   ├── legacy/                   (423 files — older test suites)
│   └── [216 active test files]
├── umh/                          (1 Python file — __init__.py stub)
├── vault/                        (612 files — daily notes, conversations, insights)
└── ventures/                     (README + lyfe-institute stub)
```

### File Counts by Extension

| Extension | Count |
|-----------|-------|
| .md | 8,102 |
| .py | 3,488 |
| .json | 3,183 |
| .ts | 147 |
| .jsonl | 96 |
| .log | 62 |
| .sh | 40 |
| .txt | 18 |
| .js | 13 |

### LOC by Language

| Language | LOC |
|----------|-----|
| Python | 274,494 |
| JSON | 297,377 |
| Markdown | 27,108 |
| TypeScript | 27,998 |
| JavaScript | 4,074 |
| Shell | 3,499 |
| YAML | 545 |
| SQL | 505 |

### Top-Level Directory Sizes

| Directory | Size | Last Modified |
|-----------|------|---------------|
| data/ | 234 MB | 2026-05-13 |
| saas/ | 114 MB | 2026-05-12 (mostly node_modules) |
| tests/ | 82 MB | 2026-05-13 |
| logs/ | 33 MB | 2026-05-13 |
| 10_Wiki/ | 25 MB | 2026-05-11 |
| archive/ | 17 MB | 2026-05-11 |
| runtime/ | 13 MB | 2026-05-13 |
| core/ | 12 MB | 2026-05-12 |
| skills/ | 8.6 MB | 2026-05-11 |
| docs/ | 7.0 MB | 2026-05-12 |
| scripts/ | 6.4 MB | 2026-05-13 |
| eos_ai/ | 5.3 MB | 2026-05-10 |
| vault/ | 4.3 MB | 2026-05-13 |
| services/ | 2.1 MB | 2026-05-11 |

### Git State

- **Branch:** main (up to date with origin/main)
- **Last 30 commits:** Focus on ingestion pipeline, cc_sdk fixes, namespace migration
- **Two other branches:** `dev`, `feature/ea-system` (not merged)
- **Repo size:** 137 MB (.git/)
- **Commit style:** lowercase imperative, specific, often multi-line

---

## Phase 1: What the Project Claims to Be

### Self-description (from README.md)

> "UMH — Universal Mastery Hierarchy: A governed intelligence substrate
> for autonomous business operations"

### Architecture claim (from ARCHITECTURE.md)

The document (titled "AgentOS — Architecture & Master Specification") describes:
- An 8-layer context injection system wrapping any LLM
- A hierarchy of AI agents: Portfolio Advisor → CEO Agent → Department Agents
- 17 knowledge layers with 148 behavioral principles
- Business stage tracking (6 stages: Validation through Portfolio)
- Voice interface with 11 meeting types
- Planned SaaS frontend with Firebase auth, Stripe billing

### Philosophy claim (from PHILOSOPHY.md)

> "EntrepreneurOS: The Operating System That Makes Business Plug and Play"

Four pillars: Reality, Intelligence, Personalization, Execution.

### Identity confusion

The project uses at least four names:

| Name | Where | Meaning |
|------|-------|---------|
| UMH (Universal Mastery Hierarchy) | README, CLAUDE.md, canonical_terminology.md | The substrate / intelligence control plane |
| EntrepreneurOS / EOS | PHILOSOPHY.md, ARCHITECTURE.md, PROTOCOLS.md | Either the whole system OR one "application projection" |
| AgentOS | ARCHITECTURE.md title | Used once, nowhere else |
| universal-meta-harness | pyproject.toml `name` field | Package identity |

`canonical_terminology.md` (2026-05-09) establishes that UMH is the system and EOS is
one application projection. But older docs (ARCHITECTURE.md, 2026-03-23) treat EOS as
the system itself. The repository path is `/opt/OS/` with a noted "pending rename to
/opt/UMH".

### Dependencies declared

**Python:** anthropic, google-genai, groq, openai, fastembed, psycopg2-binary, flask,
fastapi, py-cord, playwright, claude-agent-sdk, python-telegram-bot, openai-whisper, etc.

**TypeScript SaaS:** hono (web framework), @neondatabase/serverless, drizzle-orm, zod, ws.

**Infrastructure:** Docker (compose v3.8), Neon PostgreSQL, Ollama (local LLM).

### Apparent stage

Pre-revenue, single-founder validation phase. The SaaS layer is `v0.1.0` with only
a backend API — no frontend. Documentation describes "MVP Phase 1 (current — mostly
built)" with Phase 2 items (Firebase, Stripe, frontend) not started.

### Key contradiction

Documentation volume vastly exceeds working software. `docs/system/` contains 96 phase
report files with names like `phase968cn_substrate_sovereign_federation_readiness.md`.
The confirmed working runtime is: 1 Discord bot, 1 LLM routing chain, 1 memory layer,
1 ingestion pipeline with test proofs.

---

## Phase 2: Executable Entry Points

### Docker Services (5 defined, 2 running)

| Service | Container | Status | Purpose |
|---------|-----------|--------|---------|
| os-discord | os-discord | **UP** | Discord bot — primary interface (2GB memory limit) |
| os-webhook | os-webhook | **UP** | Calendly + Higgsfield webhooks (Flask, port 8080) |
| os-bot | os-bot | STOPPED | Telegram bot (marked DORMANT) |
| os-monitor | os-monitor | STOPPED | Instagram DM monitor (Playwright) |
| os-scraper | os-scraper | STOPPED | Overnight Instagram scraping |

### Cron Jobs (~30 entries)

Active cron schedule runs scripts every 5-15 minutes:
- `orchestrator_loop.py` (5 min) — signal-driven orchestrator
- `agent_task_executor.py` (5 min) — task polling
- `auth_monitor/health_check.sh` (5 min) — CC auth monitoring
- `call_prep.py`, `notion_tasks_sync.py`, `post_meeting_capture.py` (15 min each)
- `morning_intel.py` (5:45am), `eod_sync.py` (6pm), `weekly_review.py` (Sun 7pm)

### Flask Web Apps (3)

- `services/calendly_webhook.py` — port 8080, active
- `services/goal_api.py` — port 8090, utility
- `services/higgsfield_webhook.py` — embedded in calendly_webhook

### Total Entry Points

| Category | Count |
|----------|-------|
| Production-facing (running or cron) | ~35 |
| Infrastructure / operator tooling | ~40 |
| Test / proof / smoke test | ~240 |
| Setup / utility | ~15 |
| **Total** | **~330** (non-test Python `__main__` + shell + Docker) |

---

## Phase 3: Reachability Trace

### Reachable from production entry points

The Discord bot (`services/discord_bot.py`, 5,212 LOC) is the primary entry point
and the heaviest importer, with 117 `from runtime.*` imports. It reaches into:

- `runtime/agent_runtime.py` — LLM dispatch + fallback
- `runtime/gateway.py` — message classification (1,972 LOC)
- `runtime/cognitive_loop.py` — 8-stage perceive/generate/act loop (1,263 LOC)
- `runtime/model_router.py` — multi-provider LLM routing (1,194 LOC)
- `runtime/memory.py` — Neon-backed agent memory (1,018 LOC)
- `runtime/cc_sdk.py` — Claude Code CLI subprocess wrapper (464 LOC)
- `runtime/db.py` — Neon PostgreSQL connection (123 LOC)
- `runtime/work_state.py` — pressure tracking (220 LOC)
- `runtime/business_instance.py` — BIS venture context (489 LOC)
- Various knowledge, context, and identity modules

The ingestion pipeline (`runtime/ingestion/orchestrator.py`) is reachable from
test scripts and the canary test harness, not from the Discord bot directly.

### Reachability by directory

| Directory | Reachable | Total | Ratio |
|-----------|-----------|-------|-------|
| `runtime/` (top-level) | 105 | 125 | **84%** |
| `runtime/transport/` | 71 | 164 | **43%** |
| `services/` | 12 | 15 | **80%** |
| `scripts/` | 18 | 183 | **10%** |
| `parsers/` | 7 | 7 | **100%** |
| `core/` | 12 | 499 | **2.4%** |

### Shim layers (reachable but content-free)

- `eos_ai/` — 459 files, ALL are 4-line shims: `import runtime.X as _mod; sys.modules[__name__] = _mod`
- `runtime/substrate/` — 164 files, ALL are 1-line re-exports: `from runtime.transport.X import *`

These are compatibility shims from a namespace migration (`eos_ai/` → `runtime/`,
`runtime/substrate/` → `runtime/transport/`). They contain zero logic. Together
they are **623 files (27% of all Python files)** that are pure forwards.

### Phantom imports

The Discord bot imports 8 modules from `runtime.substrate.*` that do not exist
anywhere in the project: `discord_ingress_adapter`, `discord_output_policy`,
`event_store`, `interaction_archive`, `message_framing`, `operator_trace`,
`run_lifecycle`, `task_finalization`. All are guarded by try/except so they
fail silently rather than crashing the bot. These appear to be aspirational
imports for planned substrate features.

Additionally, `services/handlers/substrate_command_handler.py` imports
`runtime.session_registry` which does not exist — another broken import.

### Orphan candidates (not reachable from production entry points)

**`core/` — 487 orphan files out of 499 total (97.6% unreachable):**
The largest directory by file count. Only 12 files are reachable (action_system,
orchestrator, paths, ontology). The 45 subdirectories appear to be pre-built
architectural scaffold — contract/specification modules for a planned "substrate"
architecture that is not wired into production runtime.

Key `core/` subdirectories and their apparent purpose:
- `core/workstation/` (41 files, 26K LOC) — browser/workstation operational embodiment
- `core/runtime/` (44 files, 12K LOC) — canonical runtime spine contracts
- `core/tool_mastery_research_agent/` (18 files, 6K LOC) — tool skill research agent
- `core/environment_bridge/` (18 files, 3.7K LOC) — multi-environment bridge
- `core/convergence/` (15 files, 1.6K LOC) — repository topology convergence
- 30+ more subdirectories, each 1-14 files

392 of 493 `core/` files follow the `_v1.py` naming convention. 38 of 45 subdirectories
lack `__init__.py`, suggesting they're not designed as importable packages.

**`runtime/transport/` — 93 orphan files out of 164 (57% unreachable):**
71 files are reachable (including Discord text transport, some session management).
93 files are not imported by any running service — including execution workers,
LLM planners, meeting intelligence, and various backend contracts.

**`scripts/` — 165 orphan files out of 183 (90% not cron-scheduled):**
Includes 54 smoke tests, 15 substrate CLI tools, 7 proof scripts, and 89 other
standalone utilities. These are legitimate standalone tools, not meant to be imported.

### Reachability summary

| Category | Files | Status |
|----------|-------|--------|
| Reachable from production | ~255 | Active |
| Shim layers (eos_ai/ + substrate/) | ~623 | Content-free forwards |
| Core contracts (core/) | ~487 | Orphan — aspirational scaffold |
| Transport orphans | ~93 | Orphan — built but unwired |
| Scripts (standalone) | ~165 | Standalone tools |
| Tests | ~639 | Test-only |
| **Total** | **~2,262** | |

**~255 files are reachable from production entry points.
~623 files are content-free compatibility shims.
~745 files are orphan candidates (built but not connected to production).**

Note: "orphan" by static import analysis only. Modules may be invoked via cron,
shell scripts, dynamic imports, or Claude Code commands.

---

## Phase 4: Emergent Categorization

Categories emerged from observation of what files actually do:

### Category 1: LLM Intelligence Layer
**What it does:** Routes prompts through multiple LLM providers with context injection.

| Module | LOC | Reachable? |
|--------|-----|------------|
| runtime/model_router.py | 1,194 | YES |
| runtime/cc_sdk.py | 464 | YES |
| runtime/agent_runtime.py | 527 | YES |
| runtime/cognitive_loop.py | 1,263 | YES |
| runtime/gateway.py | 1,972 | YES |
| runtime/model_preferences.py | 471 | YES |
| runtime/provider_state.py | 287 | YES |
| runtime/provider_health.py | 200 | YES |

**Status: MATURE / IN DAILY USE.** This is the project's core functional layer.
Model router handles cc_sdk (Opus 4.6 via subscription) → Gemini → Groq → Ollama
fallback chain. Recent commits show active hardening (error leak detection, auth
fixes, timeout tuning).

### Category 2: Memory + Knowledge
**What it does:** Persistent memory via Neon PostgreSQL, knowledge domain management.

| Module | LOC | Reachable? |
|--------|-----|------------|
| runtime/memory.py | 1,018 | YES |
| runtime/db.py | 123 | YES |
| runtime/knowledge_domains.py | 1,143 | YES |
| runtime/knowledge_graph.py | 529 | YES |
| runtime/knowledge_integrator.py | 240 | YES |
| runtime/knowledge_layers.py | 413 | YES |
| runtime/venture_knowledge.py | 376 | YES |
| runtime/embedding_engine.py | 415 | YES |

**Status: FUNCTIONAL.** db.py and memory.py confirmed in production use by Discord bot.
Knowledge domain modules are large but their runtime activation level is unclear.

### Category 3: Agent Hierarchy + Identity
**What it does:** Defines AI agent roles, soul documents, and organizational structure.

| Module | LOC | Reachable? |
|--------|-----|------------|
| runtime/agent_hierarchy.py | 437 | YES |
| runtime/ai_identity.py | 267 | YES |
| runtime/agent_teams.py | 395 | YES |
| runtime/ceo_agent.py | 376 | YES |
| runtime/ceo_intelligence.py | 726 | YES |
| agents/*.md (18 files) | — | N/A |

**Status: IN-PROGRESS.** Agent soul docs exist for 18 roles. Python modules define
the hierarchy and routing. Whether agents beyond the CEO agent are active in
production is unclear from static analysis.

### Category 4: Ingestion Pipeline
**What it does:** Canonical document ingestion: perceive → interpret → decompose →
bridge → map → persist → query_back.

| Module | LOC | Reachable? |
|--------|-----|------------|
| runtime/ingestion/orchestrator.py | ~600 | Test/CLI |
| runtime/ingestion/local_file_source.py | ~150 | Test/CLI |
| runtime/ingestion/gws_source.py | ~200 | Test/CLI |
| runtime/ingestion/authority_tier.py | ~100 | Test/CLI |
| runtime/domain_bridge/ (4 files) | 356 | Test/CLI |
| core/ontology/primitive_decomposition_v1.py | 127 | YES |

**Status: RECENTLY BUILT, PROVEN, NOT IN PRODUCTION LOOP.** Last 10 commits
are dominated by ingestion pipeline work. Has proof artifacts demonstrating
end-to-end function. Not yet triggered from the Discord bot or cron.

### Category 5: Services + Interfaces
**What it does:** Discord bot, DM monitoring, webhooks, Telegram.

| Module | LOC | Reachable? |
|--------|-----|------------|
| services/discord_bot.py | 5,212 | YES (running) |
| services/dm_monitor.py | 1,472 | YES (defined, not running) |
| services/telegram_control.py | 3,148 | DORMANT |
| services/calendly_webhook.py | 444 | YES (running) |
| services/apify_scraper.py | 909 | YES (defined, not running) |

**Status: PARTIAL.** Discord bot is the only service in confirmed daily use.
Calendly webhook is running. Others are defined but stopped.

### Category 6: Scheduled Operations
**What it does:** Cron-scheduled intelligence gathering, briefings, sync.

~30 cron entries across `scripts/` and `runtime/orchestrator.py`.
Key scripts: morning_intel, eod_sync, weekly_review, call_prep,
agent_task_executor, orchestrator_loop.

**Status: ACTIVE.** These run on schedule and appear functional based on
log file presence.

### Category 7: Transport / Voice / Meeting
**What it does:** Voice processing, meeting intelligence, session management.

| Directory | Files | LOC |
|-----------|-------|-----|
| runtime/transport/ | 164 | 55,794 |

Key modules: meeting_intelligence.py (2,180), discord_text_transport.py (1,680),
stt_producer.py (1,146), voice_session.py (789), station_daemon.py (860).

**Status: BUILT, LARGELY DORMANT.** The Discord bot's text transport is active.
Voice/meeting transport exists as code but evidence of production use is unclear.
This is the single largest subdirectory by LOC.

### Category 8: Business Operations Modules
**What it does:** Business-specific functionality: CRM, expenses, travel, deals.

| Module | LOC | Reachable? |
|--------|-----|------------|
| runtime/email_gps.py | 1,465 | Unclear |
| runtime/goal_selector.py | 1,555 | Unclear |
| runtime/portfolio_advisor.py | 787 | Unclear |
| runtime/expense_tracker.py | 451 | Unclear |
| runtime/travel_manager.py | 358 | Unclear |
| runtime/workflow_engine.py | 1,012 | Unclear |
| runtime/strategy_engine.py | 525 | Unclear |
| runtime/feedback_loop.py | 467 | Unclear |

**Status: BUILT, UNKNOWN ACTIVATION.** These modules exist with substantial
code but their production activation status is hard to determine from static
analysis. They may be invoked via agent commands or cron jobs.

### Category 9: Substrate Contracts (core/)
**What it does:** Defines contracts, state shapes, and governance rules for a
planned "canonical substrate" architecture.

- 493 files, 118K LOC across 45 subdirectories
- 392 files follow `_v1.py` naming
- 38 subdirectories lack `__init__.py`
- 730 internal cross-imports, 16 imports from runtime/
- Only 27 runtime files import from core/

**Status: SPECIFICATION-HEAVY, MOSTLY DISCONNECTED.** These appear to be
formally structured dataclass/contract definitions for a future substrate
architecture. The code compiles (has `__pycache__` dirs) but is not wired
into the production runtime beyond the ontology module. This is ~43% of
all Python LOC.

### Category 10: Knowledge System / Wiki
**What it does:** Auto-generated codebase knowledge graph with Obsidian-style wiki pages.

- 5,804 auto-generated codebase wiki pages
- 111 concept pages, 33 synthesis pages
- 7 memory palace rooms
- Scripts: codebase_graph.py, build_palace.py, query_graph.py

**Status: FUNCTIONAL.** The graph builder and palace system work. Referenced
in CLAUDE.md as a mandatory session-start protocol.

### Category 11: Skills System
**What it does:** Reusable expertise templates for tools and business operations.

- 165 SKILL.md files across 12 categories
- Largest category: tools/ (96 skills for external tools)
- Business skills: Sales (20), Ops (13), Research (6), Marketing (4)
- Meta skills: tool mastery engine, Claude Code best practices

**Status: LARGE, DOCUMENTATION-HEAVY.** Skills are markdown templates —
they define expertise but don't execute code directly. Referenced by
Claude Code commands and agent prompts.

### Category 12: Compatibility Shims
**What it does:** Nothing — re-exports for namespace migration.

- `eos_ai/` — 459 files, all `import runtime.X; sys.modules[__name__] = _mod`
- `runtime/substrate/` — 164 files, all `from runtime.transport.X import *`

**Status: DEAD WEIGHT.** 623 files containing zero logic. Exist purely for
backward compatibility during a namespace migration (`eos_ai/` → `runtime/`,
`substrate/` → `transport/`).

---

## Phase 5: Anomalies + Observations

### Top 20 Largest Python Files

| LOC | File | Category |
|-----|------|----------|
| 5,339 | archive/umh_reference/interfaces/discord/bot.py | Archived |
| 5,212 | services/discord_bot.py | Production |
| 4,424 | services/handlers/substrate_command_handler.py | Production-adjacent |
| 3,685 | archive/umh_reference/runtime_engine/session_runtime.py | Archived |
| 3,404 | archive/umh_reference/interfaces/telegram/bot.py | Archived |
| 3,148 | services/telegram_control.py | Dormant |
| 2,180 | runtime/transport/meeting_intelligence.py | Dormant |
| 1,972 | runtime/gateway.py | Production |
| 1,866 | runtime/orchestrator.py | Production |
| 1,555 | runtime/goal_selector.py | Unknown |
| 1,465 | runtime/email_gps.py | Unknown |
| 1,263 | runtime/cognitive_loop.py | Production |
| 1,240 | scripts/action_system.py | Utility |
| 1,213 | scripts/codebase_graph.py | Utility |
| 1,194 | runtime/model_router.py | Production |
| 1,177 | scripts/workflow_engine.py | Utility |
| 1,143 | runtime/knowledge_domains.py | Production-adjacent |
| 1,034 | runtime/gws_connector.py | Production-adjacent |
| 1,018 | runtime/memory.py | Production |
| 1,012 | runtime/workflow_engine.py | Unknown |

### Environment Files (9 found — values redacted)

- `/opt/OS/.env.sessions` — OAuth token exports
- `/opt/OS/.env.example` — template
- `/opt/OS/runtime/.env` — runtime API keys
- `/opt/OS/eos_ai/.env` — legacy copy
- `/opt/OS/services/.env` — service API keys
- `/opt/OS/infra/docker/` — 4 env files (services.env, umh.env, .env.example, .env.sessions)

### Triple Duplication Pattern

The same module set exists in three places:
1. `runtime/` — real code
2. `runtime/substrate/` — 164 one-line stubs forwarding to `runtime/transport/`
3. `eos_ai/` — 459 four-line shims forwarding to `runtime/`

That is 164 + 459 = **623 files that are pure forwards/shims**, representing
**27% of all Python files** in the project. For comparison, the production
`services/` directory contains 21 files. The shim-to-production ratio is 30:1.

### TODO/FIXME/HACK Count

22 occurrences across non-archive Python files — all in `runtime/venture_knowledge.py`,
all business-data TODOs (missing revenue figures, ICP language), not technical debt.

### Empty Python Files

18 files with <5 lines — all are `__init__.py` package markers or minimal stubs.
No anomalous empty modules found outside shim layers.

### Data Directory Accumulation

| Directory | Size | Contents |
|-----------|------|----------|
| data/drive_doc_ingestion_tab_aware/ | 111 MB | GWS document ingestion cache |
| data/runtime/ | 52 MB | Memory store, proofs, continuity, reconciliation |
| data/semantic_space/ | 41 MB | Embedding/semantic analysis data |
| data/logs/ | 33 MB | Structured logs |
| data/runtime/substrate_continuity/ | 20 MB | Substrate state continuity |
| data/runtime/sync_proofs/ | 7.7 MB | Sync verification proofs |

### Docs Directory

- `docs/system/` — 96 phase files (`phase968XX_*`), plus contract specs
- `docs/operations/` — 182 operational docs
- `docs/mvp/`, `docs/plans/`, `docs/strategy/` — planning docs
- Total: 623 markdown files

The phase file naming extends from `phase968a` through `phase968cn` — 96 phases
in a single sequence. Titles progress from concrete ("runtime_domain_architecture_plan")
to increasingly abstract ("substrate_sovereign_operational_accountability_proving",
"substrate_constitutional_epistemic_intelligence").

### Test Suite

- 639 total test files (626 excluding `__init__.py`)
- 423 in `tests/legacy/` (66% of all tests)
- 216 active test files
- 12 tests explicitly in `tests/legacy/broken/` — acknowledged broken
- Legacy tests reference phases 57-77 and include substrate/platform/runtime splits
- Active tests include cc_sdk, ingestion, and transport tests
- Legacy test files dominate the "largest files" list (6 of the top 20)

### Active Work (modified in last 48 hours)

Most recent modifications concentrated in:
- `runtime/cc_sdk.py` — provider fixes
- `data/runtime/canonical_memory_store/` — ingestion proofs
- `data/audits/` — audit reports
- `CLAUDE.md` and `.claude/CLAUDE.md` — context updates

### Backup/Archive Artifacts

`archive/` directory (17 MB) contains:
- `umh_reference/` (13 MB) — prior iteration of the entire system with 50+ subdirectories
- `tools_duplicate/` (2.3 MB) — duplicated tool scripts
- `core_legacy/` (840 KB) — older core modules
- `eos_ai_platforms/` (176 KB) — platform experiment
- Various small archive directories

---

## Phase 6: Synthesis

### What is this project?

A **single-founder AI business operating system** that wraps LLMs with contextual
intelligence layers and exposes them through Discord. It is built in Python, runs
on a VPS, stores data in Neon PostgreSQL, and uses Claude (via CLI subprocess),
Gemini, Groq, and Ollama as LLM providers.

The system is designed to act as an "executive assistant" and "CEO agent" — routing
business questions through the right agent persona, injecting relevant context
(business stage, knowledge domains, agent identity), and delivering responses via
Discord.

### What does it appear to do (in practice)?

Based on what's actually running:
1. **Discord bot** that receives messages, routes through LLM with context injection,
   and responds — the primary interface
2. **Cron-scheduled briefings** (morning intel, EOD sync, weekly review) posted to Discord
3. **Calendly webhook** that processes meeting notifications
4. **Ingestion pipeline** (recently built, proven via test, not yet in production loop)
   that decomposes documents into structured ontology observations
5. **Knowledge graph** that indexes the codebase for AI-navigable wiki pages

### Major components by maturity

| Component | Maturity | Evidence |
|-----------|----------|----------|
| LLM routing (model_router, cc_sdk) | **Production** | Running daily, recently hardened |
| Discord bot | **Production** | Running, 5.2K LOC, in daily use |
| Memory/DB layer | **Production** | Neon writes confirmed |
| Cron automations | **Production** | ~30 active cron jobs |
| Ingestion pipeline | **Recently built** | 10 commits, proof artifacts, not in prod loop |
| Knowledge graph/wiki | **Functional** | 5,804 generated pages, scripts work |
| Skills system | **Documentation** | 165 SKILL.md files, markdown-only |
| Agent hierarchy | **In-progress** | 18 soul docs, Python modules exist |
| Voice/meeting transport | **Dormant** | 55K LOC built, no evidence of production use |
| Substrate contracts (core/) | **Speculative** | 118K LOC, mostly disconnected |
| SaaS frontend | **Stub** | v0.1.0, API only, no frontend |
| Telegram bot | **Dormant** | Service defined, not running |

### What appears wired together vs. disconnected

**Wired together:**
- Discord bot → gateway → cognitive loop → model router → LLM providers → memory → Neon
- Cron scripts → Discord webhooks → notification delivery
- cc_sdk → Claude CLI → OAuth token propagation

**Disconnected:**
- `core/` (118K LOC) is largely disconnected from `runtime/` (27 cross-imports)
- Ingestion pipeline exists but is not triggered from any running service
- SaaS TypeScript API is not connected to the running Python services
- `runtime/transport/` (55K LOC) is mostly not imported by running services
- 623 compatibility shim files add zero functionality

### Where is documentation strong, where absent?

**Strong:**
- CLAUDE.md / .claude/CLAUDE.md — detailed context for AI developer agent
- Agent soul documents — 18 well-structured identity files
- Ingestion pipeline — contract specs and proof artifacts
- Skills — 165 skill definitions with trigger conditions

**Absent:**
- No user-facing documentation (README references non-existent install.sh)
- No API reference for the SaaS layer
- No contributor guide
- No architectural decision records (ADRs)
- `core/` has no README explaining what the 45 subdirectories are or how they relate

**Potentially misleading:**
- 96 phase reports in `docs/system/` suggest a progression of completed phases, but
  many correspond to `core/` contract modules that are not connected to production runtime
- ARCHITECTURE.md marks components as "BUILT" that are only partially verified

### Open questions

1. **What percentage of `core/` is intended for use vs. exploratory specification?**
   118K LOC (43% of all Python) sitting in 45 subdirectories with minimal
   connection to production runtime. Is this planned architecture, abandoned
   experiment, or AI-generated specification?

2. **What triggers the cron scripts' business logic?** The ~30 cron entries run
   frequently, but without executing them, it's unclear how much business logic
   they actually perform vs. checking conditions and exiting early.

3. **What is the relationship between `archive/umh_reference/` and the current codebase?**
   The 13 MB archive contains a parallel system with 50+ subdirectories. Is this a
   prior iteration that was rewritten, or a reference implementation?

4. **How much of `runtime/transport/` (55K LOC) is in active use?** The Discord
   text transport is active. Voice, meeting, station daemon, and local worker
   modules appear dormant but represent significant investment.

5. **What's the actual volume of LLM calls per day?** With cc_sdk, Gemini, Groq,
   and Ollama in the fallback chain, plus ~30 cron scripts, the operational cost
   profile is unclear.

6. **Why are there 423 legacy test files?** `tests/legacy/` is 66% of all test
   files. Do they test code that still exists, or are they orphaned from prior
   architectural iterations?

7. **Is the `core/` directory AI-generated?** The naming patterns (`_v1.py`,
   45 thematic subdirectories, highly structured docstrings) and the gap between
   specification quality and production wiring suggest possible AI-generated
   contract definitions.

---

## Appendix: Additional Observations

### Naming Pattern Analysis

The `core/` subdirectory names follow a systematic taxonomy:
accountability, action_system, actuation, adapters, applications,
certification, cognition, coherence, constitutional, convergence,
deployment, environment_bridge, environments, execution, explainability,
federation, governance, ingress, intelligence, interpretation,
knowledge, learning, memory, ontology, operations, orchestration,
orchestrator, planning, registry, resilience, runtime, scaling,
sessions, stabilization, state, tool_mastery_*, trust, validation,
workflows, workstation, world_model.

This reads like a complete ontology of possible system concerns rather
than an emergent directory structure that grew with the codebase.

### Shim Layer Scale

The two shim layers (`eos_ai/` and `runtime/substrate/`) together
contain **623 files** with virtually zero logic. For comparison, the
production `services/` directory contains **21 files**. The shim-to-production
ratio is 30:1 by file count.

### Phase Numbering

Phase identifiers in `docs/system/` use a non-sequential scheme:
`phase968a` through `phase968cn` (96 phases). The `968` prefix is
unexplained. Phases after `phase968bj` increasingly abstract:
"constitutional_runtime_consolidation", "sovereign_operational_validation",
"sovereign_operational_trust_proving", "sovereign_federation_readiness".

### Proof Artifacts

The `data/runtime/canonical_memory_store/proofs/` directory contains
structured proof bundles with JSON artifacts documenting specific
pipeline executions. This is a methodical approach to validation —
each proof bundle contains perceive, interpret, decompose, bridge,
map, persist, and query-back artifacts.

### Skills Distribution

96 of 165 skills are in `skills/tools/` — expertise profiles for
external tools (Acrobat, Amazon Ads, AWS, Bash, Brave Search, Calendly,
Canva, Claude Code, Docker, Git, Gmail, Google Ads, Instagram, etc.).
This is a "tool mastery" system where the AI builds expertise profiles
for tools it uses.
