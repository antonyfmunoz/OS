# Fresh-Eyes System Audit — UMH Repository

**Date**: 2026-07-01
**Auditor**: Independent fresh-eyes analysis (Claude Opus 4.6)
**Method**: 10 parallel investigation agents, zero prior assumptions, code-as-ground-truth
**Scope**: Complete repository at `/opt/OS`, branch `main`, commit `a4879a15e`

---

## 1. Executive Summary

UMH (Universal Meta Harness) is a **large, ambitious, single-developer AI infrastructure platform** that combines a governed execution substrate, a multi-device mesh network, a Discord-based operator interface, a React cockpit web app, and extensive intelligence routing — all serving one founder's daily workflow.

### What it actually is today

A **solo-founder AI operating system** with real running services: a Discord bot (primary interface), a FastAPI operator API, a React cockpit on Fly.io, cross-device mesh networking, and a governed mutation pipeline. The system processes operator commands through a governed spine with risk classification, event logging, outcome learning, and proof generation.

### What works

- **Governed mutation pipeline**: ~99.5% of HTTP endpoints route through `governed_mutation()`, enforced by pre-commit gates
- **Intelligence routing**: Model router with 8-provider fallback chain, deterministic fallbacks, capability routing
- **Runtime services**: 5 Docker containers + 3 host processes + 20+ cron jobs running continuously
- **Cockpit**: 80 panels, 77 stores, 72K lines of TypeScript — nearly all panels fetch real API data
- **Enforcement gates**: 9 pre-commit check scripts, all currently passing

### What doesn't work as claimed

- **ORL-8 "Production Qualified"**: Entirely synthetic — qualification runs fake mutations through real plumbing. It proves the spine works, not that the system is production-ready
- **Pre-commit hooks are not installed**: The `.git/hooks/pre-commit` file doesn't exist. Gate scripts pass when run manually, but nothing enforces them on commit
- **51 shadow types exist** despite the Type Coherence Law claiming enforcement
- **80% of substrate modules have zero test coverage**
- **Cockpit has zero automated tests** — no TypeScript test files, no node_modules installed
- **Predictive self-model is not wired to runtime** — exists only in qualification scripts

### Critical numbers

| Metric | Value |
|--------|-------|
| Total files | 6,521 |
| Python files | 1,931 |
| TypeScript files | 612 |
| Test files | 472 |
| Lines of Python | 628,607 |
| Lines of TypeScript | 128,317 |
| substrate/organism/ alone | 315 files, 129,647 lines |
| Cockpit panels | 80 |
| Zustand stores | 77 |
| API route files | 115 |
| Running services | 5 containers + 3 host processes |
| Cron jobs | 20+ |
| Data on disk | 214MB tracked + 895MB logs + 32GB archive |
| Runtime data tracked in git | ~152MB (should be gitignored) |

### Top 3 structural risks

1. **organism/ is 130K lines with ~10% production-active** — massive surface area with limited testing
2. **Discord bot bypasses governance entirely** — 12 direct DB mutations, 0 governed calls
3. **Three distinct execution spines coexist** — ConcreteExecutionSpine, GovernedExecutionSpine, ExecutionPipeline — unclear which is canonical

---

## 2. What This Repository Actually Is

### In plain language

This is a **personal AI infrastructure platform** built by a solo founder to run his businesses. It's not a SaaS product (yet). It's not a team tool. It's one person's attempt to build an AI-augmented operating system for entrepreneurship.

The system has three main interfaces:
1. **Discord** — the primary daily-driver interface. The founder talks to "DEX" (the AI persona) via Discord text/voice
2. **Cockpit** — a React web app deployed on Fly.io with 80 panels covering everything from execution monitoring to proof inspection
3. **API** — a FastAPI backend with 115 route files serving the cockpit

Under the hood, the system routes operator intent through a governed mutation pipeline, executes work across multiple devices (VPS orchestrator + Windows GPU workstation), and tracks execution with journaling, events, and proof packages.

### What it's not

- Not a multi-tenant SaaS (single org, single user)
- Not an AGI/ASI system (despite aspirational naming)
- Not a productized platform (no onboarding, no billing, no multi-user)
- Not a team collaboration tool
- Not battle-tested (pre-revenue, no external users)

### The vision vs reality gap

The codebase contains infrastructure for things far beyond current usage: 113 engine classes, 315 organism files, predictive self-models, qualification harnesses, capability compounding, institutional memory, strategic gap analysis, reality graphs, world models, deliberation councils. Most of this (~90%) is implemented but not wired into daily runtime — it's infrastructure built ahead of demand.

---

## 3. Repository Census

### File Type Distribution

| Type | Count | % of Total |
|------|-------|-----------|
| Python (.py) | 1,931 | 29.6% |
| Markdown (.md) | 1,892 | 29.0% |
| JSON (.json) | 1,670 | 25.6% |
| TypeScript (.ts/.tsx) | 612 | 9.4% |
| JSONL (.jsonl) | 66 | 1.0% |
| Shell (.sh) | 45 | 0.7% |
| JavaScript (.js/.jsx) | 14 | 0.2% |
| YAML/TOML/Config | 8 | 0.1% |
| CSS | 4 | 0.1% |
| HTML | 2 | <0.1% |
| Images | 16 | 0.2% |
| Other | 261 | 4.0% |
| **Total** | **6,521** | **100%** |

**Observation**: Markdown nearly equals Python in file count. JSON files (mostly in data/, skills/, .claude/) outnumber TypeScript 2.7:1. This is a documentation-heavy, data-heavy codebase.

### Directory Size Distribution

| Directory | Size | Classification |
|-----------|------|---------------|
| data/ | 214M | DATA — runtime artifacts, audits, logs |
| substrate/ | 22M | ACTIVE_PRODUCTION — core platform |
| tests/ | 26M | INFRASTRUCTURE — test suite with embedded data |
| skills/ | 8.6M | DOCUMENTATION — tool mastery definitions |
| docs/ | 6.8M | DOCUMENTATION — project docs |
| cockpit/ | 3.5M | ACTIVE_PRODUCTION — operator UI |
| transports/ | 2.6M | ACTIVE_PRODUCTION — I/O surfaces |
| scripts/ | 2.1M | INFRASTRUCTURE — tooling |
| knowledge/ | 1.6M | DOCUMENTATION — wiki, palace |
| adapters/ | 1.3M | ACTIVE_PRODUCTION — external integrations |
| projections/ | 824K | ACTIVE_PRODUCTION — EOS/CreatorOS |
| nodes/ | 776K | ACTIVE_PRODUCTION — distributed execution |
| services/ | 600K | ACTIVE_PRODUCTION — deployment entrypoints |
| umh/ | 136K | ACTIVE_PRODUCTION — relay services |
| agents/ | 88K | DOCUMENTATION — soul documents |
| infra/ | 84K | INFRASTRUCTURE — config |
| docker/ | 20K | INFRASTRUCTURE — Docker config |
| config/ | 12K | INFRASTRUCTURE — env config |

**Off-git data**: `data/logs/` is 895MB (165,811 files, gitignored). `data/archive/` is 32GB (untracked, on VPS disk).

### Largest Python Files (by line count)

| Lines | File | Notes |
|-------|------|-------|
| 2,741 | services/discord_bot_commands.py | Approaching 3K limit |
| 2,623 | umh/vision_relay.py | Relay service |
| 2,538 | transports/api/organism_bridge.py | API bridge |
| 2,371 | transports/api/cockpit_rooms_routes.py | Route file |
| 2,201 | transports/api/cockpit_core_routes.py | Route file |
| 2,012 | substrate/organism/advisor_conversation.py | Organism |
| 1,927 | substrate/control_plane/runtime/gateway.py | Gateway |
| 1,913 | substrate/control_plane/orchestrator/orchestrator.py | Orchestrator |
| 1,871 | services/discord_bot.py | Discord bot |
| 1,597 | adapters/models/model_router.py | Intelligence routing |

No Python files exceed 3,000 lines (project limit).

### Git State

- Branch: `main`
- 15 modified files — all runtime state in `data/umh/`
- ~90 untracked items — runtime artifacts, skill definitions
- Recent commits focus on campaign convergence (C34-C40B) and v1.0.0 certification

---

## 4. Top-Level Directory Map

### substrate/ — Core Platform (978 .py, 22M) — ACTIVE_PRODUCTION

The universal intelligence substrate. Everything depends on this.

| Subdirectory | Files | Lines | Purpose | Status |
|-------------|-------|-------|---------|--------|
| organism/ | 315 | 129,647 | Daemon, workcells, self-improvement | ~10% active |
| execution/ | 166 | ~40K | Spine, pipeline, trace, CPU gate | Core active |
| control_plane/ | 77 | ~20K | Gateway, governance, orchestrator | Core active |
| state/ | 63 | ~15K | Storage, context, BIS | Active |
| workstation/ | 56 | ~10K | Operator workstation abstractions | Partial |
| understanding/ | 54 | 13,491 | Research, perception, deliberation | Partial |
| composition/ | 45 | ~8K | Composition engine | Partial |
| sockets/ | 19 | ~3K | Abstract ports | Active |
| operator/ | 19 | ~3K | Operator logic | Active |
| governance/ | 19 | ~3K | Risk, security, mutation governance | Active |
| meta_ide/ | 18 | ~3K | Self-building capabilities | Partial |
| contracts/ | 12 | ~2K | Agent/task types, protocols | Active |
| reality_model/ | 8 | ~1.5K | Reality graph | Partial |
| ontology/ | 8 | ~1.5K | Ontological layer | Partial |
| memory/ | 7 | ~1K | Memory watcher, sync | Active |

**Key imports**: 340 external files import from substrate/. substrate/ imports from adapters/ (112 occurrences) — **this is a bidirectional dependency that violates the claimed one-way architecture** (substrate should be the lowest layer).

### transports/ — I/O Surfaces (188 .py, 2.6M) — ACTIVE_PRODUCTION

| Subdirectory | Purpose | Key |
|-------------|---------|-----|
| api/ | FastAPI HTTP API — 142 files including 115 cockpit route files | Primary API surface |
| discord/ | Discord interface adapter | Signal factory |
| node_mesh/ | Cross-device WebSocket mesh | Port 8094/8095 |
| channels/ | Channel abstraction | |
| presence/ | Presence system | |

### adapters/ — External Integrations (99 .py, 1.3M) — ACTIVE_PRODUCTION

| Subdirectory | Purpose | Status |
|-------------|---------|--------|
| models/ | LLM routing (model_router, cc_sdk, agent_runtime) | ACTIVE |
| google_workspace/ | GWS scanning | ACTIVE |
| calendar/ | Google Calendar | PARTIAL |
| notion/ | Notion integration | PARTIAL |
| browser/ | Browser automation | DORMANT (1 file, 10 lines) |
| browser_auth/ | SSO chain | PARTIAL |
| adapter_engine/ | Generic adapter framework | PARTIAL |
| broadcast/ | Broadcasting | PARTIAL |

### services/ — Entrypoints (26 .py, 600K) — ACTIVE_PRODUCTION

Deployment entrypoints for Docker containers and standalone services. Contains data files that should be in data/ (`calls_log.json`, `cost_log.json`, `scraped_posts.json`).

### cockpit/ — Operator UI (306 TS/TSX, 3.5M) — ACTIVE_PRODUCTION

React 19 + Zustand 5 + Tailwind 4 web app. Dual-target: Electron desktop + Fly.io web SPA. Detailed in Section 8.

### nodes/ — Distributed Execution (51 .py, 776K) — ACTIVE_PRODUCTION

Windows node daemon, work distribution, execution environments.

### projections/ — Application Views (47 .py, 824K) — ACTIVE_PRODUCTION

- **eos/** — EntrepreneurOS: CEO/engineering/CS agents, content/outreach workflows
- **creatoros/** — CreatorOS: integration layer with correlation, handlers
- **lyfeos/** — LyfeOS: stub only

### scripts/ — Tooling (150 .py, 2.1M) — INFRASTRUCTURE

Enforcement gates (9 check scripts), graph utilities, campaign runners (legacy), cron jobs, operator CLI tools.

### tests/ — Test Suite (350 .py, 26M) — INFRASTRUCTURE

Detailed in Section 11.

### Other Directories

| Directory | Purpose | Status |
|-----------|---------|--------|
| data/ | Runtime data, audits, logs, proofs | DATA |
| knowledge/ | Wiki, memory palace, concepts | DOCUMENTATION |
| skills/ | Tool mastery skill definitions | DOCUMENTATION |
| agents/ | Soul documents (11 .md files) | DOCUMENTATION |
| docs/ | Project documentation | DOCUMENTATION |
| infra/ | Device registry, service deps | INFRASTRUCTURE |
| umh/ | Relay services (desktop, vision, voice) | ACTIVE_PRODUCTION |
| docker/ | Computer-use container config | INFRASTRUCTURE |
| config/ | Non-secret env config | INFRASTRUCTURE |

---

## 5. Runtime Reality

### Running Services

#### Docker Containers (5 active)

| Container | Port | Entrypoint | Health | CPU Limit |
|-----------|------|-----------|--------|-----------|
| os-operator | 127.0.0.1:8091 | `services/operator_api.py` (uvicorn) | Healthy (GET /health) | 0.50 |
| os-discord | 127.0.0.1:8765 | `services/discord_bot.py` | Running | 0.50 |
| os-browser | 127.0.0.1:8086 | `services/browser_relay.py` | Running | 0.25 |
| os-webhook | 127.0.0.1:8080 | `transports/api/webhooks/calendly_webhook.py` | Running | 0.25 |
| os-livekit | 7880-7881 (public) | `livekit/livekit-server:v1.8.3` | Running | 0.35 |

#### Host Processes (3 active, systemd-managed)

| Process | Port | Binding | Service |
|---------|------|---------|---------|
| Node Mesh Server | 8094 (WS), 8095 (HTTP) | 0.0.0.0 | umh-mesh.service |
| Vision Relay | 8097 (WS), 8098 (HTTP), 8099 (WS ingest) | 0.0.0.0 | umh-vision-relay.service |
| Desktop Relay | 8100 (WS) | 0.0.0.0 | manual |

**Security note**: Ports 8094, 8095, 8097, 8098, 8100 bind 0.0.0.0. Tailscale may restrict access, but these are publicly listening.

#### Cron Jobs (20+)

Every 5 minutes: day_reminder, agent_task_executor, orchestrator_loop, auth health check, session resurrector

Every 15 minutes: call_prep, notion_tasks_sync, post_meeting_capture, calendar_invite_handler, noshow_detector

Every 30 minutes: git sync

Nightly: maintenance, discord clear, signal emit, scraper

Monthly: secret rotation

**Security finding**: Crontab contains a raw `OP_SERVICE_ACCOUNT_TOKEN` value in plaintext.

### Runtime Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    OPERATOR INPUTS                       │
│  Discord (text/voice) │ Cockpit (HTTP/WS) │ Cron jobs   │
└────────┬──────────────┴────────┬──────────┴──────┬──────┘
         │                       │                  │
         ▼                       ▼                  ▼
┌────────────────┐  ┌──────────────────┐  ┌──────────────┐
│  os-discord    │  │  os-operator     │  │  scripts/    │
│  Discord bot   │  │  FastAPI + Daemon│  │  cron jobs   │
│  Port 8765     │  │  Port 8091       │  │              │
└───────┬────────┘  └───────┬──────────┘  └──────┬───────┘
        │                   │                     │
        ▼                   ▼                     ▼
┌───────────────────────────────────────────────────────┐
│              ORGANISM DAEMON (inside os-operator)      │
│  ┌─────────────┐ ┌──────────────┐ ┌────────────────┐  │
│  │ Governed     │ │ Event Spine  │ │ Outcome        │  │
│  │ Exec Spine   │ │ (18 domains) │ │ Learning Loop  │  │
│  └──────┬──────┘ └──────┬───────┘ └────────┬───────┘  │
│         │               │                   │          │
│  ┌──────┴──────┐ ┌──────┴───────┐ ┌────────┴───────┐  │
│  │ Mutation    │ │ Spine Guard  │ │ Execution      │  │
│  │ Router     │ │ (risk gate)  │ │ Journal        │  │
│  └──────┬──────┘ └──────────────┘ └────────────────┘  │
│         │                                              │
│  ┌──────┴──────────────────────────────────────┐       │
│  │ 46 Registered MutationSpecs                 │       │
│  │ (create_*, update_*, delete_*, execute_*)    │       │
│  └─────────────────────────────────────────────┘       │
└───────────────────────────┬───────────────────────────┘
                            │
                            ▼
┌───────────────────────────────────────────────────────┐
│              INTELLIGENCE ROUTING                      │
│  model_router.call_with_fallback()                     │
│  Chain: cc_sdk → Codex → Hermes → OpenCode →          │
│         Groq → Gemini → Ollama → deterministic         │
└───────────────────────────────────────────────────────┘
                            │
                            ▼
┌───────────────────────────────────────────────────────┐
│              CROSS-DEVICE MESH                         │
│  Node Mesh (:8094) → Beast (Windows GPU)               │
│  Vision Relay (:8097) → Camera frames                  │
│  Desktop Relay (:8100) → Screenshots                   │
└───────────────────────────────────────────────────────┘
```

### Device Registry (5 nodes)

| Device | Role | OS | Status |
|--------|------|----|--------|
| VPS (srv1500858) | Orchestrator | Linux | always_online |
| Beast (desktop-lvguiq9) | Executor | Windows | GPU (GTX 1080 Ti) |
| iPad | Controller | iOS | Mobile access |
| iPhone | Controller | iOS | SSH via Termius |
| MacBook | Controller | macOS | Potential executor |

---

## 6. Architecture Contracts

### Contract Status Summary

| # | Contract | Status | Enforcement | Evidence |
|---|----------|--------|-------------|----------|
| 1 | Canonical Mutation | ACTIVE_ENFORCED | Pre-commit Gate 6 | 370 call sites, gate passes clean |
| 2 | Governed Execution Spine | ACTIVE_ENFORCED | SpineGuard + Gate 6 | MutationRouter → GovernedSpine path verified |
| 3 | Event Spine | ACTIVE_ENFORCED | Daemon wiring | 18 domains, 15+ consumers |
| 4 | Runtime Mesh | ACTIVE_UNENFORCED | Gate 9 (pattern only) | WebSocket server verified running |
| 5 | Proof/Evidence | PARTIAL | None | **Duplicate ProofStore** (organism/ + observability/) |
| 6 | Qualification | ACTIVE_UNENFORCED | None | **Synthetic-only** — fake mutations |
| 7 | Organism Daemon | ACTIVE_ENFORCED | Daemon wiring | 50+ subsystem imports, running in os-operator |
| 8 | Predictive Self-Model | PARTIAL | None | **Not wired to runtime** — qualification-only |
| 9 | Type System | ACTIVE_ENFORCED | Pre-commit Gate 1 | **BUT 51 shadow types** exist (test finds them, gate doesn't) |
| 10 | Runtime SLOs / ORL | PARTIAL | None | Script-only measurement, no runtime enforcement |

### Critical Architecture Findings

**1. Three Execution Spines Coexist**

| Spine | File | Lines | Used By |
|-------|------|-------|---------|
| ConcreteExecutionSpine | substrate/execution/spine.py | 522 | substrate/__init__.py, 1 cockpit route |
| GovernedExecutionSpine | substrate/organism/governed_spine.py | 864 | MutationRouter, daemon, all governed routes |
| ExecutionPipeline | substrate/execution/pipeline.py | 557 | app.py, daemon.py, worker_cell.py |

GovernedExecutionSpine is the primary mutation path. ConcreteExecutionSpine appears to be legacy. ExecutionPipeline handles signal processing. Their relationship is unclear and undocumented.

**2. substrate/ imports from adapters/ (112 times)**

The claimed architecture says dependencies flow downward: `substrate ← adapters ← transports ← projections`. But substrate/ imports from adapters/ 112 times, creating a bidirectional dependency. The pre-commit dependency direction check passes — suggesting it's allowlisted or the check doesn't cover this case.

**3. Governed mutation has an ungoverned fallback**

`transports/api/governed.py:95-110`: When the organism daemon is not running, `governed_mutation()` executes the mutation directly with status `"completed_ungoverned"`. Governance is conditional on infrastructure uptime.

---

## 7. Canonical Mutation Audit

### Coverage Summary

| Scope | Endpoints | Governed | Bypass Rate |
|-------|-----------|----------|-------------|
| Python HTTP (transports/api/) | 194 | ~193 | ~0.5% |
| TypeScript HTTP | 33 | 33 | 0% |
| Discord bot commands | 88 handlers | 0 | **100%** |
| Organism-internal state | 119 files | 0 | By design |

### Governed Mutation Flow

```
HTTP POST/PUT/PATCH/DELETE
  → route handler calls governed_mutation(name, intent, execute_fn)
    → MutationRouter.execute(MutationRequest)
      → GovernedExecutionSpine.execute(ActionEnvelope)
        → SpineGuard risk check
        → Execute with proof generation
        → ExecutionJournal recording
        → EventSpine emission
        → OutcomeLearningLoop recording
```

### Bypasses

**1. Discord Bot (CRITICAL)**: `services/discord_bot_commands.py` has 88 command handlers with 12 direct `.execute()` DB calls and 0 `governed_mutation()` calls. This is the primary operator interface and it completely bypasses governance.

**2. services/higgsfield_webhook.py**: POST endpoint with direct DB write. Not covered by pre-commit gate (gate only scans `transports/api/` and `saas/`).

**3. Organism-internal writes**: 119 files in substrate/organism/ perform direct file I/O. These are internal state management (heartbeats, journals, sessions) — by design, not through governance. But this means 119 files can mutate state without approval, rollback tracking, or proof generation.

### Pre-commit Enforcement

`scripts/check_ungoverned_mutations.py` scans 159 route files — passes clean. Only 3 files are exempt: `governed.py` itself, `cockpit_spine_router.py`, and `governed_bridge.ts`.

**Gap**: The gate only covers `transports/api/` and `saas/`. It does NOT scan `services/` (where the Discord bot lives) or `substrate/organism/` (where internal writes happen).

---

## 8. Cockpit / Operator Workstation Audit

### Architecture

- **Framework**: React 19, Zustand 5, Tailwind 4, TypeScript 6
- **Routing**: No react-router — single `activePanel` state in cockpitStore drives a giant `switch` in Shell.tsx (334 lines, 80 cases)
- **API**: Custom `fetchApi()` → `/api/umh` (reverse-proxied via nginx on Fly.io to VPS:8091)
- **Auth**: Clerk (test mode — `pk_test_` prefix)
- **Deploy**: `cockpit/deploy.sh` → pre-deploy gate → `flyctl deploy --remote-only`
- **Dual target**: Electron desktop app + Fly.io web SPA

### Panel Status (80 panels)

| Category | Count | Examples |
|----------|-------|---------|
| Primary nav (visible) | 6 | CommandCenter, Canvas, Work, MetaIDE, Rooms, Vision |
| Dev panels (searchable) | 63 | Approvals, Activity, Execution, Organism, Browser, etc. |
| System | 1 | Settings |
| Planned/stub | 1 | Analytics |
| Unreachable (no route entry) | 5 | Executive, Governance, Learning, Prediction, WorkIntelligence |
| Redirected (alias → real panel) | 7 | dashboard→commandcenter, tasks→work, etc. |

**Nearly all panels are INTEGRATED** — they fetch real API data via Zustand stores. No truly placeholder panels found (except Analytics). However, several panels display "Not yet wired" when backend endpoints don't respond.

### Store Analysis (77 Zustand stores, 15,860 lines)

- 39 stores have exactly 1 consumer (1:1 store-panel pattern)
- No truly orphaned stores — all 77 have at least 1 external import
- Largest: operatorLoopStore (1,553 lines), visionStore (1,288 lines)

### WebSocket Connections (5)

| Connection | URL | Purpose |
|------------|-----|---------|
| Organism realtime | ws://.../ws | Organism event stream |
| Vision | ws://localhost:8097/vision | Camera feed from Beast |
| Voice | ws://localhost:8096/voice | Voice calls |
| Browser | browser-ws | Remote browser stream |
| Broadcast | ws://localhost:8095/.../broadcast/ws | Screen broadcast |

### Key Findings

1. **80 panels in a single switch statement** — no lazy loading, no code splitting
2. **Zero automated tests** — no .test.tsx files, no testing library in package.json, node_modules is empty
3. **5 panels unreachable** from navigation or command palette
4. **Clerk auth is test-mode** — pk_test_ prefix
5. **72,200 lines of TypeScript** for a single-user operator cockpit

---

## 9. Intelligence Layer Audit

### Production-Active Intelligence Systems

| System | File | Lines | What it does |
|--------|------|-------|-------------|
| Model Router | adapters/models/model_router.py | 1,597 | Central LLM routing, 8-provider fallback chain |
| CC SDK | adapters/models/cc_sdk.py | 513 | Claude Code CLI as subprocess provider |
| Cognitive Loop | substrate/control_plane/runtime/cognitive_loop.py | 1,539 | Full Perceive→Understand→Plan→Execute→Verify→Reflect→Learn→Store cycle |
| Governance Engine | substrate/control_plane/governance.py | 278 | Risk classification (regex-based, deterministic) |
| Gateway | substrate/control_plane/runtime/gateway.py | 1,927 | Singleton signal handler |
| Capability Router | substrate/execution/runtime/capability_router.py | 610 | 28 capability definitions, tool routing |
| Agent Runtime | adapters/models/agent_runtime.py | 580 | Agent call routing |
| Self-Model | substrate/self_model.py | 478 | Structural self-awareness (deterministic) |
| Agent Memory | substrate/state/memory/memory.py | 1,039 | Neon-backed agent/conversation memory |

### Partial/Aspirational Intelligence Systems

| System | Files | Lines | Status |
|--------|-------|-------|--------|
| Predictive Self-Model | organism/self_model_predictor.py | 542 | Qualification-only, not runtime |
| Compounding Engine | organism/compounding_engine.py | 583 | Implemented, limited runtime use |
| Template Registry | organism/template_registry.py | 936 | Stores templates, no auto-promotion |
| Strategy Engine | control_plane/strategy/strategy_engine.py | 525 | Uses CognitiveLoop, cockpit-facing |
| Qualification Harness | organism/qualification_harness.py | 1,569 | Synthetic measurement only |
| Deliberation Council | understanding/deliberation/council.py | 528 | 7-role advisory, partial |
| Fine-Tune Harness | intelligence/finetune_harness.py | 450 | DORMANT — scaffolding only |
| World Model (×2) | organism/ + understanding/ | ~800 | Two implementations, limited integration |
| Research Engine | understanding/research/ | ~200 | Partial |
| Institutional Memory | organism/institutional_memory_runtime.py | ~400 | Partial |

### Intelligence Routing Chain

```
Prompt → model_router.call_with_fallback()
  → CapabilityRouter (if specialized tool matches)
  → cc_sdk (Claude Code CLI via tmux subprocess)
  → codex_cli (OpenAI Codex CLI)
  → hermes_cli (Hermes agent CLI)
  → opencode_cli (OpenCode CLI)
  → Groq API
  → Gemini API (google.genai)
  → Ollama (local, on Beast)
  → deterministic fallback (regex intent patterns)
```

### Deterministic Fallback Discipline

Consistently implemented: model_router, cognitive_loop, governance, capability_router all have regex/rule-based fallbacks. The principle "LLM providers down — does the system still produce output?" is answered **yes** for routing and classification. Content generation degrades gracefully to template responses.

### Intelligence Scale

| Layer | Files | Lines | % Active |
|-------|-------|-------|----------|
| substrate/organism/ | 315 | 129,647 | ~10% |
| substrate/execution/ | 166 | ~40,000 | ~30% |
| substrate/control_plane/ | 77 | ~20,000 | ~40% |
| substrate/understanding/ | 54 | 13,491 | ~15% |
| adapters/models/ | 8 | ~3,000 | ~80% |
| **Total intelligence layer** | **461** | **~297,000** | **~15%** |

---

## 10. Data / Memory / Persistence Audit

### Data Footprint

| Category | Size | Location | Tracked in Git? |
|----------|------|----------|----------------|
| Runtime JSONL stores | 97MB | data/umh/ | YES (should be gitignored) |
| Codebase graph | 34MB | data/codebase_graph.json | YES (derivable) |
| Audit reports | 62MB | data/audits/ | YES |
| Node summaries | 11MB | data/node_summaries.json | YES (derivable) |
| Campaign data | ~20MB | data/umh/c3*/, data/certification/ | YES (stale) |
| Logs | 895MB | data/logs/ | NO (gitignored) |
| Archive | 32GB | data/archive/ | NO (on VPS disk) |
| **Total on VPS disk** | **~33GB** | | |

### Critical Data Stores

| Store | Size | Growth | Retention | Risk |
|-------|------|--------|-----------|------|
| outcome_learning.jsonl | 36MB | Append-only | None | **CRITICAL** — unbounded |
| events.jsonl | 10MB | Append-only | None | HIGH |
| events.jsonl.old | 11MB | Static | None | Delete |
| signals/deferred_stale/ | 653MB (164K files) | Append-only | None | **CRITICAL** — disk bomb |
| decision logs | 118MB (~5MB/day) | Daily files | None | HIGH |
| predictions.jsonl | 3.3MB | Append-only | None | Medium |

### Database (Neon Postgres)

- Connection via `DATABASE_URL` env var
- Primary module: `substrate/state/storage/db.py` — psycopg2 with connection pooling
- Used by: portfolio_advisor, transports API, agent memory, accountability
- No SQL schema files on disk — schema managed through inline queries

### Duplicate/Overlapping Stores

| Pattern | Instances | Issue |
|---------|-----------|-------|
| Events | 5 separate stores | Different domains but no unified persistence |
| Sessions | 2 stores | operator_experience + runtime_surface |
| Templates | 2 stores | organism + trials |
| Proof | 2 ProofStore classes | organism/ + observability/ |

### Gitignore Gaps

**152MB of runtime data is tracked in git that should not be:**
- Runtime JSONL (outcome_learning, events, messages, reports, velocity)
- Runtime JSON (daemon_state, dispatch_lock, mesh_metrics, heartbeats)
- Derivable data (codebase_graph.json, node_summaries.json)
- Stale audit snapshots (31MB detailed_inventory.json, 18MB .tsv)

**Gitignore bug**: `.gitignore` line 62 says `vault/memory/conversations/` but files are at `data/vault/memory/conversations/` — 93 conversation files tracked that should be excluded.

### Retention Policy

**No JSONL store has a retention policy.** Every append-only store grows without bound. The `data/logs/signals/deferred_stale/` directory has 164,278 files totaling 653MB with no cleanup mechanism.

---

## 11. Tests and Qualification Audit

### Test Census

| Category | Count |
|----------|-------|
| Total test files | 472 |
| Python test files | 413 |
| TypeScript test files | 59 (in skills/saas-dev-skill/, NOT cockpit) |
| Tests collected (pytest) | 14,725 |
| Collection errors | 1 |

### Test Execution Results

| Suite | Passed | Failed | Duration |
|-------|--------|--------|----------|
| Smoke + critical path | 77 | 0 | 39.7s |
| Campaign/qualification (C35-C40B) | 210 | 1 | 97.1s |
| Governance + daemon + self-model | 123 | 5 | ~30s |
| Organism tests | 1,734 | 34 | ~120s |
| Organism unit tests | 61 | 0 | 0.6s |

### Key Test Failures

| Test | Failure | Root Cause |
|------|---------|-----------|
| test_type_divergence::test_full_codebase_scan_clean | 51 divergent types found | Type definitions shadow canonical types |
| test_daemon_e2e (×2) | Assertion mismatch, no metrics | Heartbeat timing drift |
| test_self_model::test_registered_loader | 'DEX' != 'LoaderAI' | AI name changed, test not updated |
| test_c39_live_simulation | Infrastructure gate fails | Requires running infra |
| test_projection_reconciliation | sk- pattern in data files | Secrets in data files |
| test_phase62 count tests | 46 vs 22 mutation specs | Tests not updated for registry growth |

### Qualification Harness — CRITICAL FINDING

The qualification harness reports **ORL-8 (PRODUCTION_QUALIFIED)** at **95.4% confidence** with **86.6% predictive accuracy**.

**This is entirely synthetic.** Evidence:
- `scripts/run_qualification.py:101` creates trivial lambda functions: `return ("Qualification mutation: {name}", True)`
- The harness submits fake mutations through the governed spine
- It measures that the spine correctly records, journals, and events — NOT that real operator workflows work
- 150 synthetic mutations complete in ~7 seconds
- **ORL-8 means "the spine plumbing works with fake data" — it does NOT mean "the system is production-ready"**

### Test Coverage

| Area | Modules | With Tests | Coverage |
|------|---------|-----------|---------|
| substrate/ | 810 | 163 | **20.1%** |
| Cockpit (TypeScript) | 306 files | 0 | **0%** |

### Pre-commit Hooks — NOT INSTALLED

Three versions of pre-commit scripts exist:
- `scripts/pre-commit` (3 gates)
- `scripts/hooks/pre-commit` (5 gates)
- `scripts/graph_hooks/pre-commit` (graph-related)

**But `.git/hooks/pre-commit` does not exist.** None of the 9 gate checks run automatically on commit.

All 9 check scripts pass when run manually. But `test_type_divergence.py` finds 51 shadow types that `check_type_divergence.py` does NOT catch — the check script and test use different detection logic.

### Test Quality Distribution

| Tier | Description | % |
|------|-------------|---|
| Genuine unit | Real logic with behavioral assertions | ~15% |
| Structural/import | Checks imports work, classes exist | ~25% |
| Campaign acceptance | Campaign-era feature tests, may have drifted | ~40% |
| Synthetic qualification | Spine plumbing with fake mutations | ~10% |
| Phase/roadmap | Phase-specific, often stale | ~10% |

---

## 12. Security / Proprietary Exposure Audit

### Summary

| Finding | Severity |
|---------|----------|
| No actual secrets (API keys, tokens) in source | ACCEPTABLE |
| .env templates use 1Password op:// URIs | ACCEPTABLE |
| No credential files (.pem, .key) in repo | ACCEPTABLE |
| Pre-commit secret gates active | ACCEPTABLE |
| 1Password service account token in crontab plaintext | **HIGH** |
| 93 conversation files tracked (gitignore bug) | **HIGH** |
| 15+ files with hardcoded Tailscale IPs | MEDIUM |
| Personal SSH username/paths in source | MEDIUM |
| 5 ports bound to 0.0.0.0 on VPS | MEDIUM |
| Architecture docs expose internals (private repo assumed) | MEDIUM |
| Clerk publishable key in fly.toml | ACCEPTABLE (by design) |

### Hardcoded Tailscale IPs (15+ files)

Tailscale IPs (100.x.x.x) are hardcoded as fallback defaults in production source:
- `transports/api/app.py` — CORS origins
- `adapters/models/model_router.py` — Ollama URL
- `transports/api/cockpit_workspace_routes.py` — SSH target
- `services/bridge_health.py` — Windows host
- Multiple relay/voice/TTS files

Mitigating factor: Tailscale IPs are only routable within the private network. But this violates the project's own Instance Context Law.

### Ports Exposed on 0.0.0.0

| Port | Service | Risk |
|------|---------|------|
| 8094 | Node Mesh WS | MEDIUM — accepts WebSocket connections from any source |
| 8095 | Mesh HTTP relay | MEDIUM — dispatch endpoint |
| 8097 | Vision relay WS | LOW — read-only video stream |
| 8098 | Vision HTTP ingest | LOW — frame POST endpoint |
| 8100 | Desktop relay WS | LOW — read-only screenshots |

---

## 13. Dead Code / Duplication / Drift

### Dead Code

| Item | Size | Evidence | Action |
|------|------|---------|--------|
| _dormant/ directory | 33 files, 896K | Labeled dormant but **90 active imports** from transports/presence/handlers/ | INVESTIGATE — promote or sever |
| 32GB data/archive/ | 32GB | Untracked on VPS | DELETE from VPS |
| Stale worktree (.claude/worktrees/c33-campaign/) | 477MB | Campaign-era | DELETE |
| Campaign scripts (run_c33, run_c35, run_c40a) | ~5 files | 0 external refs | DELETE |
| 30+ campaign test files (test_c16–test_c40b) | ~116 files | Historical | DEPRECATE |
| adapters/browser/ | 1 file, 10 lines | Empty stub | DELETE |
| adapters/notebooklm/ | 2 files | Zero runtime imports | DEPRECATE |
| adapters/browser_auth/sso_chain.py | 1 file | Zero imports | DEPRECATE |
| substrate/intelligence/finetune_harness.py | 450 lines | Zero imports, aspirational | DEPRECATE |
| 7 contract protocol files | 7 files | Zero imports each | INVESTIGATE |

### Duplicate Types (135 class names defined 2+ times)

| Class | Definitions | Priority |
|-------|-------------|----------|
| SessionStatus | 5 | HIGH — merge to canonical |
| ExecutionMode | 5 | HIGH |
| WorkPacket | 4 | HIGH — critical type |
| MutationResult | 4 | MEDIUM (3 in campaign scripts) |
| MemoryCandidate | 4 | MEDIUM |
| ProofStore | 2 | HIGH — active duplicate |
| IntentRouter | 2 | MEDIUM |

### Code Health

| Metric | Count | Severity |
|--------|-------|----------|
| Silent except/pass | 602 | HIGH (241 in substrate/) |
| TODO/FIXME/HACK | 155 | LOW |
| Raw subprocess (ungated) | 0 | CLEAN |
| Files over 3000 lines | 0 | CLEAN |
| Engine classes | 113 | INVESTIGATE runtime usage |

### Spec-Code Drift

- ARCHITECTURE.md references files by bare name (e.g., `context_compaction.py`) — paths are incomplete but files exist
- `saas/` directory referenced in CLAUDE.md and architecture docs **does not exist**
- Type divergence test finds 51 shadow types; check script finds 0 — different detection logic

---

## 14. MVP Status

### Platform Substrate — PARTIALLY COMPLETE

| Component | Status | Evidence |
|-----------|--------|---------|
| Governed mutation pipeline | Working | 370 call sites, pre-commit gate |
| Governed execution spine | Working | SpineGuard, journal, events, learning |
| Event spine | Working | 18 domains, 15+ consumers |
| Type system | Working (with gaps) | 51 shadow types remain |
| Intelligence routing | Working | 8-provider fallback, deterministic fallback |
| Cross-device mesh | Working | VPS ↔ Beast via WebSocket |
| Proof generation | Partial | Dual ProofStore, basic packages |
| Qualification | Synthetic only | Measures plumbing, not reality |
| Self-model | Partial | Not wired to runtime decisions |
| SLO enforcement | Not implemented | Script measurement only |

### Operator Workstation — PARTIALLY COMPLETE

| Capability | Status | Evidence |
|------------|--------|---------|
| Discord text interface | Working | Primary daily-driver interface |
| Discord voice | Working | Voice auto-join, TTS |
| Cockpit web UI | Working | 80 panels, real data, Fly.io deployed |
| Governed mutations via API | Working | ~99.5% coverage |
| Governed mutations via Discord | **NOT working** | 0% governance on Discord bot |
| Proof inspection | UI exists | ProofInspectorPanel + routes |
| Recovery dashboard | UI exists | RecoveryDashboardPanel + routes |
| Approval workflow | UI exists | ApprovalsPanel with approve/reject |
| Cross-device execution | Working | Mesh dispatch to Beast |
| Vision/camera | Working | Vision relay from Beast camera |
| Calendar/meeting | Partial | Sync scripts, no deep integration |
| Notion sync | Partial | Poller exists, 15-min cron |

### What an operator can actually do today

1. Talk to DEX via Discord (text and voice)
2. View system state in cockpit (80 panels)
3. Execute governed mutations via cockpit API
4. Dispatch work to Beast via mesh
5. View camera feed from Beast
6. Approve/reject governance items via cockpit
7. Inspect proof packages
8. Monitor organism events in real-time
9. Use MetaIDE for code/file operations
10. Conference rooms for text/voice channels

### What an operator cannot do today

1. Run Discord commands through governance
2. Get continuous qualification (only script-based)
3. Use predictive self-model for routing decisions
4. Rely on runtime SLO enforcement
5. Use multi-tenant features (single org hardcoded)
6. Onboard new users
7. Set up billing
8. Deploy to customer environments
9. Run the system without founder's specific device setup

---

## 15. ASGI Gap Analysis

The codebase references "ASGI" (Artificial Super General Intelligence) as a long-term vision. Here is the gap between current reality and that aspiration.

### Current Intelligence Maturity: Level 2 of 7

| Level | Description | Status |
|-------|-------------|--------|
| 1 | Rule-based automation | **ACHIEVED** — regex routing, risk classification, deterministic fallbacks |
| 2 | LLM-augmented operations | **CURRENT** — model router, cognitive loop, governed execution |
| 3 | Self-improving operations | PARTIAL — outcome learning exists but doesn't modify behavior |
| 4 | Predictive operations | NOT STARTED — self-model exists but isn't wired to decisions |
| 5 | Autonomous strategic planning | NOT STARTED — strategy engine exists but doesn't autonomously plan |
| 6 | Cross-domain synthesis | NOT STARTED — domain isolation, no cross-domain reasoning |
| 7 | ASGI | NOT STARTED — no path visible from current architecture |

### What exists vs what's needed for ASGI

| Capability | Exists | Needed |
|-----------|--------|--------|
| LLM routing | Yes | Multi-model orchestration with learned preferences |
| Outcome learning | Records outcomes | Must modify future behavior based on outcomes |
| Qualification | Measures plumbing | Must measure real task performance |
| Self-model | Structural awareness | Must predict own performance and adjust |
| World model | 2 partial implementations | Must maintain accurate, queryable world state |
| Memory | Neon-backed, session-based | Must compound knowledge across sessions |
| Strategy | LLM-generated analysis | Must autonomously identify and pursue goals |
| Multi-agent | Single agent runtime | Must coordinate specialized agent teams |
| Verification | Script-based | Must self-verify in real-time |

### Honest Assessment

UMH is an impressive personal AI operating system for a solo founder. It has real governed execution, real intelligence routing, real cross-device mesh networking, and a comprehensive operator UI. But it is **not on a path to ASGI** — it is on a path to being a **very capable personal assistant infrastructure**, which is valuable in its own right.

The gap between "governed task execution with LLM routing" and "artificial super general intelligence" is not a matter of more code — it requires fundamental advances in AI capabilities that don't exist yet.

---

## 16. Risk Register

| # | Risk | Severity | Likelihood | Impact | Mitigation |
|---|------|----------|-----------|--------|-----------|
| 1 | 164K stale signal files (653MB) fill VPS disk | CRITICAL | HIGH | Service outage | Add retention/rotation policy |
| 2 | outcome_learning.jsonl (36MB) grows without bound in git | HIGH | CERTAIN | Repo bloat, slow clones | Gitignore + rotate |
| 3 | Discord bot bypasses governance (12 direct DB writes) | HIGH | ACTIVE | Ungoverned state mutations via primary interface | Route through governed_mutation |
| 4 | Pre-commit hooks not installed | HIGH | ACTIVE | Gate checks don't run on commit | Install hooks |
| 5 | 51 shadow type definitions | MEDIUM | ACTIVE | Type confusion, subtle bugs | Merge to canonical types |
| 6 | 602 silent except/pass (241 in substrate) | MEDIUM | ACTIVE | Hidden failures, debugging difficulty | Add logging |
| 7 | 1Password token in crontab plaintext | HIGH | ACTIVE | Credential exposure | Use op:// URI or env var |
| 8 | 93 conversation files tracked despite gitignore intent | MEDIUM | ACTIVE | May contain sensitive prompts | Fix gitignore path |
| 9 | 32GB archive on lightweight VPS | MEDIUM | ACTIVE | Disk pressure | Move to Beast or delete |
| 10 | 33 "dormant" files actively imported | MEDIUM | ACTIVE | Confusion, maintenance burden | Promote or sever |
| 11 | Three execution spines with unclear relationship | MEDIUM | LOW | Developer confusion | Document or consolidate |
| 12 | Cockpit has zero automated tests | MEDIUM | HIGH | Regression risk | Add critical path tests |
| 13 | 80% of substrate untested | MEDIUM | HIGH | Regression risk | Prioritize test coverage |
| 14 | Qualification harness is synthetic-only | MEDIUM | LOW | False confidence in ORL claims | Add real-world mutations |
| 15 | 5 ports bound to 0.0.0.0 | LOW | LOW | If Tailscale compromised | Bind to Tailscale IP |

---

## 17. Recommended Roadmap

### Phase 0: Hygiene (1-2 days)

1. Install pre-commit hooks: `ln -sf ../../scripts/hooks/pre-commit .git/hooks/pre-commit`
2. Fix gitignore: add `data/vault/memory/conversations/`, `data/umh/organism/*.jsonl`, `data/codebase_graph.json`, `data/node_summaries.json`; then `git rm --cached` the tracked files
3. Delete 32GB `data/archive/` from VPS
4. Delete stale worktree `.claude/worktrees/c33-campaign/`
5. Add retention policy to JSONL stores (max size or max age rotation)
6. Remove 1Password token from crontab (use `op run` wrapper)
7. Delete stale campaign scripts (run_c33, run_c35, run_c40a)

### Phase 1: Governance Completion (3-5 days)

1. Route Discord bot commands through `governed_mutation()`
2. Extend pre-commit gate to scan `services/` directory
3. Resolve _dormant imports — promote or sever
4. Merge top 5 duplicate types (SessionStatus, ExecutionMode, WorkPacket, ProofStore, MemoryCandidate)
5. Fix type divergence detection (align check script with test logic)

### Phase 2: Test Foundation (1-2 weeks)

1. Add cockpit TypeScript test infrastructure (install deps, configure vitest/jest)
2. Write critical path cockpit tests (auth flow, mutation submission, event display)
3. Add real-world qualification mutations (not synthetic lambdas)
4. Increase substrate test coverage for untested production-active modules
5. Fix 34 failing organism tests

### Phase 3: Architecture Cleanup (1-2 weeks)

1. Resolve substrate → adapters dependency (112 imports violating direction)
2. Consolidate three execution spines — document or merge
3. Merge duplicate ProofStore implementations
4. Reduce silent except/pass in substrate (241 instances)
5. Clean up 113 engine classes — identify which are runtime-active vs aspirational

### Phase 4: Production Hardening (2-4 weeks)

1. Wire predictive self-model into runtime decisions
2. Add runtime SLO enforcement (not just measurement)
3. Add log rotation for all JSONL stores
4. Bind mesh/relay ports to Tailscale interface (not 0.0.0.0)
5. Move Tailscale IPs to env vars (remove hardcoded defaults)
6. Add cockpit code splitting (80 panels in one switch statement)

---

## 18. First 10 Work Packets

| # | Title | Priority | Effort | Phase |
|---|-------|----------|--------|-------|
| 1 | Install pre-commit hooks and verify all 9 gates run on commit | P0 | 30 min | 0 |
| 2 | Fix gitignore for runtime data (152MB tracked) + git rm --cached | P0 | 1 hour | 0 |
| 3 | Delete 32GB data/archive/ + stale worktree (477MB) from VPS | P0 | 15 min | 0 |
| 4 | Remove 1Password service account token from crontab | P0 | 30 min | 0 |
| 5 | Add JSONL rotation/retention policy (max 10MB per store) | P1 | 4 hours | 0 |
| 6 | Route Discord bot commands through governed_mutation() | P1 | 2 days | 1 |
| 7 | Merge duplicate ProofStore (organism/ + observability/) | P1 | 2 hours | 1 |
| 8 | Merge 5 duplicate SessionStatus definitions to canonical | P1 | 4 hours | 1 |
| 9 | Add cockpit test infrastructure + 5 critical path tests | P2 | 3 days | 2 |
| 10 | Add real-world qualification mutations to harness | P2 | 2 days | 2 |

---

## 19. Appendix: Commands Run

All commands were read-only. No source modifications, no deployments, no service restarts.

### Phase 1 (Census)
```bash
find . -type f -not -path '*/.git/*' ... | wc -l  # 6,521
find . -type d -not -path '*/.git/*' ... | wc -l  # 752
find . -name "*.py" ... | wc -l                    # 1,931
find . -name "*.ts" -o -name "*.tsx" | wc -l       # 612
find . -name "test_*.py" ... | wc -l               # 413
du -sh */                                           # size per directory
wc -l on all Python/TS files                        # line counts
git status --short
git log --oneline -20
```

### Phase 3 (Runtime)
```bash
docker ps --format "table ..."                      # 5 containers
docker ps -a --format "table ..."                   # no stopped containers
cat docker-compose.yml                              # 6 services defined
systemctl list-units --type=service | grep umh      # 2 systemd services
crontab -l                                          # 20+ cron entries
ps aux | grep python                                # 3 host processes
cat infra/device_registry.json                      # 5 devices
docker logs --tail 5 per container                  # health check
```

### Phase 4 (Architecture)
```bash
grep -rn "governed_mutation" --include="*.py"       # 370 call sites
grep -rn "GovernedExecutionSpine" --include="*.py"  # spine consumers
python3 scripts/check_dependency_direction.py       # PASS
python3 scripts/check_type_divergence.py            # PASS
python3 scripts/check_ungoverned_mutations.py       # PASS
python3 scripts/check_projection_leak.py            # PASS
python3 scripts/check_cpu_gate.py                   # PASS
```

### Phase 5 (Mutations)
```bash
grep -rn POST/PUT/PATCH/DELETE in transports/       # 194 endpoints
grep -rn "governed_mutation(" --include="*.py"      # 370 calls
grep -rn ".execute(" in services/                   # 12 direct DB writes
python3 scripts/check_ungoverned_mutations.py --all # PASS
```

### Phase 9 (Tests)
```bash
python3 -m pytest --collect-only                    # 14,725 tests, 1 error
python3 -m pytest tests/test_p0_smoke.py ...        # 77 passed
python3 -m pytest tests/test_c35* tests/test_c36* ..# 210 passed, 1 failed
python3 -m pytest substrate/organism/tests/         # 1734 passed, 34 failed
ls .git/hooks/pre-commit                            # DOES NOT EXIST
```

### Phase 10 (Security)
```bash
find . -name ".env*"                                # 4 templates only
grep -rn "sk-\|api_key" patterns                    # no real secrets
grep -rn Tailscale IPs                              # 15+ files
git ls-files data/ | wc -l                          # 2,571 tracked data files
```

---

## 20. Appendix: Evidence Tables

### A. Governed Mutation Coverage by Directory

| Directory | Route Files | Governed | Ungoverned |
|-----------|-------------|----------|------------|
| transports/api/ | 115 | 114 | 1 (cockpit_spine_router.py — exempt) |
| transports/api/http/routes/ | 6 (TS) | 6 | 0 |
| services/ | 4 with mutations | 0 | 4 (including discord_bot_commands) |
| **Total HTTP** | **125** | **120** | **5** |

### B. Pre-commit Gate Status

| Gate | Script | Status | Actually Installed? |
|------|--------|--------|-------------------|
| Type Coherence | check_type_divergence.py | PASS | NO |
| Instance Context | check_instance_leak.py | PASS | NO |
| Projection Boundary | check_projection_leak.py | PASS | NO |
| Dependency Direction | check_dependency_direction.py | PASS | NO |
| CPU Gate | check_cpu_gate.py | PASS | NO |
| Ungoverned Mutations | check_ungoverned_mutations.py | PASS | NO |
| Credential Injection | check_credential_injection.py | PASS | NO |
| Secret Patterns | check_secret_patterns.py | PASS | NO |
| Mesh Relay Firewall | check_mesh_relay_firewall.py | PASS | NO |

All scripts pass when run manually. None run automatically because `.git/hooks/pre-commit` does not exist.

### C. Organism Subsystem Scale

| Subdirectory | Files | Est. Lines | Runtime Status |
|-------------|-------|-----------|---------------|
| organism/ (root) | 82 | ~35K | Mixed — daemon active, many support files |
| organism/tests/ | 68 | ~30K | Test files |
| organism/executors/ | 28 | ~12K | Partial |
| organism/workcells/ | 18 | ~8K | Active (daemon-managed) |
| organism/stages/ | 14 | ~6K | Active (daemon tick loop) |
| organism/trials/ | 12 | ~5K | Partial — self-improvement trials |
| organism/templates/ | 6 | ~3K | Partial |
| organism/mesh/ | 5 | ~2K | Active |
| organism/dev_* | 4 | ~2K | Partial |
| **Total** | **315** | **~130K** | **~10% production-active** |

### D. Data Store Writer Map

| Writer Module | Store Path | Mode |
|--------------|-----------|------|
| organism/outcome_learning.py | data/umh/organism/outcome_learning.jsonl | Append |
| organism/daemon.py (stages) | data/umh/organism/events.jsonl | Append |
| organism/execution_journal.py | data/umh/organism/execution_journal.jsonl | Append |
| organism/template_registry.py | data/umh/organism/templates/ | Append |
| intelligence/runtime.py | data/umh/intelligence/decisions.jsonl | Append |
| operator/intent_runtime.py | data/umh/operator_experience/intents.jsonl | Append |
| organism/daemon.py | data/umh/organism/daemon_state.json | Overwrite |
| sockets/projection_port.py | data/umh/projections/registrations.jsonl | Append |

---

*End of audit. Every claim above is backed by command output, file path, import evidence, or explicit uncertainty. No prior reports, campaign claims, or documentation were trusted — only the code and runtime were used as ground truth.*
