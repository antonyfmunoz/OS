# UMH Coherent System Layer Map

**Phase:** 14.6B-UMH
**Status:** DRAFT -- awaiting operator ratification
**Provenance:** CODE_RESOLVED_CURRENT_TRUTH + OPERATOR_CORRECTION
**Date:** 2026-06-03

This document classifies the entire UMH codebase into 6 coherent layers per the
operator's corrected ecosystem doctrine. UMH is the Universal Meta Harness -- the
private universal intelligence substrate. All file counts and line counts are
verified against the live codebase.

---

## Layer 1: Universal Substrate (substrate/)

The reusable intelligence and control plane. Universal, instance-agnostic,
projection-agnostic. Works for any operator, any projection, any domain.

**696 Python files. 206,602 lines.**

### Root modules

| File | LOC | Role |
|------|-----|------|
| substrate/__init__.py | 188 | Public API facade (execute, query, register, check_tier, status) |
| substrate/types.py | 1,400 | Canonical type system (30+ Pydantic models, enums including PermissionTier, RiskClass, SignalEnvelope) |
| substrate/canonical_types.py | 262 | Type registry (~80 canonical types, prevents divergence) |
| substrate/self_model.py | 478 | Runtime self-model and instance identity |

### Subsystem directory breakdown

| Directory | Files | LOC | Role |
|-----------|-------|-----|------|
| control_plane/ | 77 | 22,355 | Gateway (1,927 LOC), CognitiveLoop (1,539 LOC), Orchestrator (1,910 LOC), governance engine, identity, context, router, memory, registry, scheduling, signals, strategy, delegation, coordination, events, goals, invariants, onboarding, proactive actions |
| execution/ | 163 | 66,759 | ExecutionSpine (522 LOC), trace recording, feedback capture, ingestion pipeline, bridge/session management, browser agent, voice, workers/workstation, actuation, media, runtime/capability routing |
| organism/ | 201 | 70,126 | Largest subsystem. Runtime graph, coordinator, workcell protocol, autonomous tick, template registry, diagnostic engine, production truth, reliability signals, advisor hierarchy, leverage assimilation, parallel execution, workload placement, permission dialogue, environment discovery, coherence propagation, execution economy, governed spine, mutation registry, propagation graph, self-build queue, universal work queue, world model |
| understanding/ | 54 | 13,491 | Perception, interpretation, deliberation (council), domains, embedding, intelligence, knowledge, ontology, patterns, reality, research, signals, world model, world pulse, breadth expansion |
| state/ | 64 | 10,491 | Context (SubstrateContext), memory, storage (Neon DB), session, business, config, finance, lifecycle, logs, metrics, permissions, preferences, profiles, providers, registries, tenancy, work, stores |
| composition/ | 45 | 10,454 | Mastery registries, knowledge gap trigger, authoring, management, research |
| governance/ | 19 | 3,599 | Policy engine (183 LOC), risk classes (66 LOC), security (219 LOC), authority (27 LOC), accountability, quality, validation, principles |
| sockets/ | 19 | 1,651 | Abstract ports: signal, capability, outcome, view, notification, channel, projection, config, message, approval, sensing, envelopes, protocols, registry |
| intelligence/ | 4 | 1,128 | Finetune harness, training extractor, runtime |
| memory/ | 6 | 1,127 | Memory subsystem |
| reality_model/ | 4 | 733 | Simulation reality, canonical model |
| observability/ | 6 | 602 | Error recorder (centralized, single source of truth) |
| foundation/ | 9 | 546 | Foundation modules |
| integrations/ | 5 | 430 | ProductConnectionManager (205 LOC), bridge, CORS, health |
| ontology/ | 9 | 290 | Laws, primitives (13 business primitives), relationships, domains |
| contracts/ | 5 | 254 | Agent types, agent runtime contracts, adapter contracts, routing contracts |
| workstation/ | 2 | 238 | Workstation profile |

### Dependency direction

substrate/ is the innermost layer. It never reaches outward. When substrate needs
transport functionality, it defines an abstract port in substrate/sockets/ and the
concrete implementation registers at startup. Pre-commit hook
(scripts/check_dependency_direction.py) enforces this.

---

## Layer 2: Cockpit / Private Jarvis Interface

The private operator interface into the full UMH ecosystem. Combines a FastAPI
backend (12 Python route files) with an Electron/React frontend.

### Backend API surface

**276 total endpoints across 12 files, 6,221 backend LOC.**

| File | LOC | Endpoints | Domain |
|------|-----|-----------|--------|
| cockpit.py | 2,304 | 67 | Primary surface: build, pulse, models, containers, agents, knowledge, config, traces, signals, approvals, subscriptions, organism status, dev sessions, WebSocket streaming |
| cockpit_organism_routes.py | 557 | 39 | Organism operations: coordinator, workcells, topology, heartbeats, runtime graph, allocation, delegation, world model |
| cockpit_spine_router.py | 518 | 30 | Governed execution spine: pending/active/completed envelopes, approve/reject/retry, journal, mutations, spine guard, execution doctrine, reliability |
| cockpit_autonomous_routes.py | 586 | 30 | PR factory, autonomous cadence, template governance, template seeder, bottleneck engine, candidate supply |
| cockpit_context_assimilation_routes.py | 551 | 24 | Context ingestion engine, source registry, cross-source reconciliation, contradiction detection, canonical updates |
| cockpit_economy_routes.py | 447 | 21 | Execution economy: budgets, cost tracking, ROI, worker efficiency, economy dashboard |
| cockpit_universal_work_routes.py | 210 | 16 | Work packets, workcell assignments, queue management |
| cockpit_self_build_routes.py | 191 | 11 | Self-build queue: proposals, execution, status, history |
| cockpit_propagation_graph_routes.py | 216 | 10 | Change propagation: graph state, impact analysis, propagation plans |
| cockpit_runtime_surface_routes.py | 163 | 10 | Runtime sessions, adapters, fleet status, handoffs |
| cockpit_entity_routes.py | 333 | 9 | Portfolio/department CRUD |
| cockpit_operator_experience_routes.py | 145 | 9 | Orchestrator sessions, compression, readiness |

All extracted route files use APIRouter with `add_api_route()` and mount under
`/api/umh/` via `include_router` in cockpit.py. Auth dependency is injected via
a `configure()` call before mounting.

### Frontend (Electron/React)

**90 TypeScript/TSX files, 14,271 LOC across renderer/main/preload.**

27 panels:

Activity, Agents, Analytics, Approvals, Comms, Company, Dashboard, Editor,
Execution, Experiments, Infrastructure, Intelligence, Knowledge, Operator,
Organism, Portfolio, Profile, PropagationGraph, Runtime, SelfBuild, Settings,
Skills, Tasks, Tracking, UniversalWork, Workflows, WorldModel

26 components:

AgentCard, ChatDrawer, CommandPalette, ConnectionBanner, ControlPanel,
EventConsole, ExecutionTimeline, FabLarge, FabMedium, FabSmall, GraphView,
HudBar, LeftRail, LivePreview, NavRail, OverlayToggle, RightRail, RingGauge,
Shell, SplitPane, TaskBlock, TimelineView, TitleBar, TopologyMap,
VoiceCommandBar, VoiceWaveform

20 stores:

activity, agent, analytics, approval, chat, cockpit, coherence, config,
editor, execution, intelligence, knowledge, operatorExperience, organism,
realtime, settings, system, task, voice, worldModel

### Operator API

services/operator_api.py (740 LOC) -- FastAPI backend for operator workstation,
separate from cockpit.py.

---

## Layer 3: Projection Runtime / Integration Fabric

The shared integration layer through which public products connect to UMH safely.
Each projection implements an identical socket contract: manifest, signals,
handlers, outcomes, correlation, tables.

### Core integration infrastructure

| File | LOC | Role |
|------|-----|------|
| substrate/integrations/product_connections.py | 205 | ProductConnectionManager: 3 products, connection status, capabilities, signals, cross-product summary |
| substrate/integrations/bridge.py | -- | Integration bridge |
| substrate/integrations/health.py | -- | Integration health checks |
| substrate/integrations/cors.py | -- | CORS configuration |
| substrate/sockets/projection_port.py | 32 | Abstract projection registration port |

### Per-projection integration modules

| Projection | Files | LOC | Modules present |
|------------|-------|-----|-----------------|
| EOS | 8 | ~1,200 | manifest, signals, handlers, outcomes, correlation, tables, poller, __init__ |
| CreatorOS | 7 | ~900 | manifest, signals, handlers, outcomes, correlation, tables, __init__ |
| LyfeOS | 7 | ~1,000 | manifest, signals, handlers, outcomes, correlation, tables, __init__ |

All three projections declare:
- **3 signal types** each (polled from their respective SaaS databases)
- **4-5 capability types** each (actions UMH can take on behalf of the projection)
- Identical socket pattern: manifest defines descriptors, signals emits, handlers
  processes, outcomes records, correlation maps cross-product, tables manages persistence

Integration identifiers: `"eos"`, `"creatoros"`, `"lyfeos"`

---

## Layer 4: Domain Projection Modules

Domain-specific SaaS products that package, constrain, and contextualize UMH
capabilities for particular life/business domains.

**47 Python files, 7,983 LOC total across all projections.**

### EntrepreneurOS (EOS) -- Business / Company / Operations

Most mature projection. **30 files, 5,699 LOC.**

**10 department agents** (all extend DepartmentAgent base class, 198 LOC):
CEO, Sales, Marketing, Finance, CustomerSuccess, HR, Legal, Operations, Product, Engineering

Each agent inherits skill execution, permission tiers, and browser capabilities from the base.

**3 views:** Activity, KPIs, Pipeline

**3 workflow classes:** Outreach (114 LOC), FollowUp (93 LOC), ContentCalendar (100 LOC)

**Entity hierarchy** (entities.py, 879 LOC):
User > Portfolio > Company > Department > Role, plus Workflows and Dashboards.
Defines 10 default departments, 10 default workflows, 1 dashboard template.
All entity types imported from substrate/types.py (canonical location).

**Integration layer:** 3 signal types (contact_created, deal_created, activity_logged),
5 capability types (noop, create_contact, create_deal, log_activity, update_deal_stage),
polling-based signal ingestion via dedicated poller.

### CreatorOS -- Creator / Content / Community / Commerce

Integration-complete projection. **8 files, 1,099 LOC.**

Integration layer fully implemented:
- 3 signal types: post_created, product_listed, revenue_recorded
- 4 capability types: noop, create_post, create_product, record_revenue
- Full socket contract: manifest, signals, handlers, outcomes, correlation, tables

No agents, views, or workflows yet. Domain logic lives in the external SaaS codebase.

### LyfeOS -- Personal Life / Transformation

Integration-complete projection. **8 files, 1,184 LOC.**

Integration layer fully implemented:
- 3 signal types: quest_completed, daily_log_created, stats_updated
- 4 capability types: noop, create_quest, complete_quest, log_daily_reflection
- Full socket contract: manifest, signals, handlers, outcomes, correlation, tables

No agents, views, or workflows yet. Separate SaaS codebase at lyfeos.net
(35 tables, deployed on Replit).

---

## Layer 5: External Tool Layer

Software and services operated through adapters, APIs, CLI wrappers, MCP, and
capability harnesses.

**87 Python files, 18,723 LOC across adapters/.**

### Adapter categories

| Category | Files | Contents |
|----------|-------|----------|
| adapter_engine/ | 15 | Lifecycle manager, manifest, maturity model, registry contracts, capability catalog/discovery, Google Docs/Drive adapters, GWS scanner bridge, live ingestion pipeline, modality, participant, substrate candidate generator, substrate decomposer |
| models/ | 9 | model_router (call_with_fallback), agent_runtime, llm_adapter, cc_sdk (Claude CLI), codex_cli, hermes_cli, opencode_cli, capabilities, config |
| notion/ | 11 | Publisher, sync, poller, auth, correlation, handlers, manifest, outcomes, signals, transforms, watermarks |
| browser_exports/ | 7 | ChatGPT, Claude, Instagram, Gmail export parsers, profile_manager, contract |
| google_workspace/ | 6 | GWS connector, scanner, email GPS, doc creator, document filer, tasks adapter |
| data_source_adapters/ | 6 | Local file source, GWS source, GitHub source, conversation source, ChatGPT/Claude parsers |
| capabilities/ | 5 | Goose harness, UI-TARS harness, Kokoro voice harness, creative generation, contracts |
| tool_adapters/ | 5 | Filesystem, git, shell, tmux, base |
| calendar/ | 2 | Meetings, travel manager |
| higgsfield/ | 1 | Video generation webhook client |
| notebooklm/ | 1 | NotebookLM sync |
| scrapling/ | 1 | Web scraping connector |
| browser/ | 0 | Empty placeholder (browser/computer-use adapter not yet built) |

### Model provider chain (current)

1. cc_sdk (Claude Code CLI, Opus 4.6 via Max subscription, no API cost) -- option 0
2. Gemini 2.5 Flash (via google.genai SDK)
3. Groq
4. Ollama (local fallback, gemma3:4b)

### Transport layer (transports/)

**72 Python files, 19,986 LOC.**

| Subdirectory | Files | Role |
|--------------|-------|------|
| api/ | 27 | Cockpit API (12 files), agent bridge, event bus, signal factory/router, organism bridge, voice, workstation, distribution, computer use, webhooks (Calendly) |
| presence/handlers/ | 15 | Substrate command dispatch, report handlers (12 report types: adapter, capability, constitution, continuity, economics, epistemic, federation, governance intelligence, identity, orchestration, resilience, strategy, telos), CC command handler, intent handler, pipeline handler, voice handler |
| node_mesh/ | 10 | Multi-node coordination: server, registry, config, metrics buffer, integration socket (manifest, signals, handlers, outcomes, types) |
| discord/ | 5 | Signal factory, approval bridge, spine integration, interface adapter, utils |
| channels/ | 1 | Abstract channel |

### Not yet implemented

- Stripe payment adapter
- Meta Ads / Google Ads adapters
- Slack adapter
- Direct browser/computer-use adapter (placeholder directory exists)

---

## Layer 6: Governance / Data Boundary Layer

Permissions, risk classification, approval gates, and audit controls. This layer
is distributed across the substrate rather than isolated in a single directory --
governance is woven into every execution path.

### Permission model

**PermissionTier** (substrate/types.py, cumulative):

| Tier | Value | Scope |
|------|-------|-------|
| READ | `read` | View data, query state |
| DRAFT | `draft` | Create proposals, stage changes |
| EXECUTE | `execute` | Run approved actions |
| COMMIT | `commit` | Mutate production state |

### Risk classification

**RiskClass** (substrate/types.py):

| Level | Value |
|-------|-------|
| NEGLIGIBLE | Read-only operations |
| LOW | Safe writes |
| MEDIUM | Reversible writes |
| HIGH | Irreversible writes, external communication |
| CRITICAL | Financial, security-sensitive, physical world |
| FORBIDDEN | Never permitted |

**ActionRiskCategory** (substrate/governance/risk_classes.py) -- 8 semantic
categories that map to the 5 risk levels:

| Category | Maps to | Blocking? |
|----------|---------|-----------|
| READ_ONLY | NEGLIGIBLE | No |
| SAFE_WRITE | LOW | No |
| REVERSIBLE_WRITE | MEDIUM | No |
| IRREVERSIBLE_WRITE | HIGH | Yes |
| EXTERNAL_COMMUNICATION | HIGH | Yes |
| FINANCIAL | CRITICAL | Yes |
| SECURITY_SENSITIVE | CRITICAL | Yes |
| PHYSICAL_WORLD | CRITICAL | Yes |

Blocking categories require explicit operator approval before execution.

### Governance components

| File | LOC | Role |
|------|-----|------|
| substrate/control_plane/governance.py | 278 | ConcreteGovernanceEngine -- deterministic risk classification |
| substrate/governance/policy_engine.py | 183 | Policy engine |
| substrate/governance/security.py | 219 | Security controls |
| substrate/governance/risk_classes.py | 66 | ActionRiskCategory enum and mapping |
| substrate/governance/authority.py | 27 | Authority model |
| substrate/organism/autonomous_action_gateway.py | 422 | Autonomous action governance |
| substrate/organism/permission_dialogue.py | 394 | Permission dialogue system |
| substrate/organism/operator_acceptance_mode.py | 378 | Operator acceptance mode |
| substrate/organism/spine_guard.py | 240 | Spine execution guard |
| substrate/execution/spine.py | 522 | Simulation dry-run for HIGH/CRITICAL, DeliberationCouncil for HIGH/CRITICAL |
| transports/discord/approval_bridge.py | 201 | Discord-based approval flow |

### Authentication model (cockpit)

| Mechanism | Env var | Purpose |
|-----------|---------|---------|
| API Key | UMH_OPERATOR_API_KEY | Required for all cockpit routes |
| Operator Token | UMH_OPERATOR_TOKEN | Required for mutation endpoints |
| Dev Bypass | UMH_DEV_BYPASS=true | Token-free from private IPs (Tailscale/RFC1918) |
| WebSocket auth | Sec-WebSocket-Protocol | Bearer token for real-time streams |

### Rate limiting

In-memory per-action cooldown windows:

| Action | Window |
|--------|--------|
| promote | 60s |
| execute | 30s |
| approve | 30s |

### Pre-commit governance hooks

4 scripts enforce architectural invariants at commit time:

| Hook | Enforces |
|------|----------|
| scripts/check_dependency_direction.py | Dependency direction (Layer Law) |
| scripts/check_type_divergence.py | Type coherence (no shadow types) |
| scripts/check_instance_leak.py | Instance context boundary |
| scripts/check_projection_leak.py | Projection boundary (no projection names in substrate/) |

---

## Cross-layer summary

| Layer | Primary location | Python files | LOC | Purpose |
|-------|-----------------|--------------|-----|---------|
| 1. Universal Substrate | substrate/ | 696 | 206,602 | Reusable intelligence/control plane |
| 2. Cockpit Interface | transports/api/cockpit*.py + cockpit/src/ | 12 + 90 TS/TSX | 6,221 + 14,271 | Private operator Jarvis |
| 3. Integration Fabric | projections/*/integration/ + substrate/integrations/ | 27 | ~3,530 | Projection-to-substrate bridge |
| 4. Domain Projections | projections/ | 47 | 7,983 | Domain-specific SaaS modules |
| 5. External Tools | adapters/ + transports/ | 87 + 72 | 18,723 + 19,986 | External system adapters and I/O |
| 6. Governance | distributed across substrate/ | -- | -- | Permissions, risk, approvals, audit |

Total UMH codebase: substrate (206,602) + transports (19,986) + adapters (18,723) +
projections (7,983) + cockpit frontend (14,271) + services (11,077) = ~278,642 LOC
of authored code (excluding tests, scripts, data, docs, config).
