# UMH — Architecture & Master Specification

> Every build decision gets checked against this document.
> Last updated: 2026-05-25

---

## Philosophy

See PHILOSOPHY.md — the single source
of truth. Everything derives from it.

---

## 1. Vision

UMH is a modular, AI-native, role-driven business operating system that formalizes how businesses are structured and run. It allows humans and AI agents to operate roles through shared dashboards and workflows, teaches and optimizes the founder and team, integrates with the full software stack, stays current through live intelligence, evolves the organization from startup through scale and exit, and gives any entrepreneur an elite business brain, operating team, and execution system inside one unified platform.

The north star: the user just talks. No commands. No prompts to engineer. No skills to configure. The system already knows what they mean because it knows everything about their businesses, their life, their communication patterns, and their goals. The harness eventually disappears into the substrate.

---

## 2. Core Principles

Every build decision must pass through all of these.

1. **Comprehensive not narrow** — covers the full operating surface of a business, not just one department or workflow
2. **Integrated not fragmented** — one system of record, not a bundle of disconnected tools
3. **Role-centric** — the Role is the atomic unit; everything else is a property or extension of a role
4. **AI-native** — AI is embedded at every layer, not bolted on as a feature
5. **Human-optimizing** — makes the founder and team progressively better, not dependent
6. **Hybrid-operable** — every role and workflow can be run by human, AI, or both in any ratio
7. **Template-driven** — best-in-class blueprints for every role, workflow, and KPI set; synthesized from canonical sources
8. **Modular and composable** — Lego-like units that combine without coupling; stages, agents, skills, workflows are all swappable
9. **Stage-aware** — evolves with the company from validation through scale and exit; inappropriate advice is rejected at the stage level
10. **Reality-grounded** — the system challenges bad thinking, not just executes instructions; truth over comfort
11. **Educational** — teaches the why behind every recommendation so users build judgment, not just compliance
12. **Current** — live intelligence through web search and signal monitoring; domain knowledge updated on a schedule
13. **Secure and owner-controlled** — user owns all data; no forced integrations; cross-product sharing requires explicit permission
14. **Cross-system** — EntrepreneurOS, CreatorOS, and LYFEOS share one intelligence substrate; each works standalone, any two compound, all three multiply
15. **Execution-oriented** — the system closes the loop from insight to action; advisors that cannot execute are incomplete

---

## 3. Entity Model

```
User / Founder
└── Portfolio
    └── Company (Business Instance)
        ├── Business Instance Spec (BIS)
        │   stage, offer, ICP, channels,
        │   financial model, constraints,
        │   north star, proof-to-advance
        ├── Departments
        │   └── Roles  ← atomic operating unit
        │       ├── Responsibilities
        │       ├── Workflows
        │       ├── Metrics / KPIs
        │       ├── Dashboard
        │       ├── Agent
        │       ├── Tools
        │       └── Documents / SOPs
        ├── Knowledge Graph
        ├── Interactions / Memory
        └── Outcomes / RLHF Signal
```

### Key Entity Definitions

**Role** — the atomic operating unit of the system. Contains: responsibilities, workflows, metrics, dashboard, agent, tools, documents. Can be operated by human, AI, or both simultaneously. The role is the unit of authority, delegation, and performance measurement.

**Workflow** — a process for executing repeatable work. Supports: human, AI-assisted, or fully automated execution. Has: triggers, ordered steps, branching logic, approval gates, and output artifacts. Workflows are the operating instructions of a role.

**Agent** — the AI layer for a role. Has: soul document (identity and values), skill set, domain knowledge, autonomy level, and persistent memory context. An agent without a role has no operating surface; a role without an agent requires human execution.

**Dashboard** — the complete UI surface for a role. Not just analytics. Contains: task board, tools, CRM records, documents, workflows, metrics, communications, AI interaction panel, and approval queue. The role owner sees everything they need, nothing they do not.

**Business Instance Spec (BIS)** — the structured configuration of a company at a specific stage. Contains: stage (1-6), current focus, offer details, ICP definition, active channels, financial model, north star target, and proof required to advance. All agent recommendations are filtered through the current BIS.

---

## 4. Agent Architecture

### Hierarchy

**LEVEL 0: Human / Founder**
Always in control. Can override any action at any level. Configures autonomy at every layer. The system serves the human — not the reverse.

**LEVEL 1: Portfolio Advisor** `✅ BUILT`
Cross-company intelligence layer. Capital allocation guidance. Strategic pattern recognition across ventures. Only visible at portfolio layer. Feeds the CEO agent per company.

**LEVEL 2: CEO Agent (per company)** `✅ BUILT`
Primary orchestrator. Generates org structure. Delegates to department agents. Guides founder from startup through scale to exit. Actively corrects stage-inappropriate thinking. Does not execute — it plans, delegates, and reviews.

**LEVEL 3: Department Agents**

| Agent | Status | Tier | Skills | Notes |
|---|---|---|---|---|
| CEO Agent | ✅ | COMMIT | 8 | Strategic analysis, morning brief, delegation, decisions |
| Sales Agent | ✅ | EXECUTE | 8 | Outreach, pipeline, follow-up, prospect research |
| Marketing Agent | ✅ | EXECUTE | 8 | Content calendar, campaigns, brand audit, analytics |
| Finance Agent | ✅ | COMMIT | 9 | Revenue, expenses, budget, unit economics, cashflow |
| Customer Success Agent | ✅ | EXECUTE | 9 | Tickets, churn detection, onboarding, feedback |
| HR Agent | ✅ | EXECUTE | 8 | Hiring, performance reviews, compensation, culture |
| Legal Agent | ✅ | COMMIT | 8 | Contract review, compliance, entity management |
| Operations Agent | ✅ | EXECUTE | 8 | System health, deployment, incident response |
| Product Agent | ✅ | DRAFT | 8 | Roadmap, ICE scoring, user feedback, specs |
| Engineering Agent | ✅ | EXECUTE | 8 | Code review, deployment, tech debt, architecture |

All 10 agents share a `DepartmentAgent` base class (`projections/eos/agents/base.py`) with skill execution, tier enforcement, and browser capabilities. Each agent inherits `browser_research` (READ tier) and `browser_act` (EXECUTE tier) automatically.

**LEVEL 4: Execution Layer** `✅ WIRED`
Browser and computer control via Playwright. `BrowserAgent` (`substrate/execution/agents/browser_agent.py`) provides: navigate, click, type, fill forms, extract tables, extract page state, and AI-planned multi-step task execution. Wired to ALL department agents via `DepartmentAgent._register_browser_skills()`. Authority engine gates all browser actions — research at READ tier, actions at EXECUTE tier.

### Autonomy Levels

| Level | Behavior |
|---|---|
| 0 | Draft only — human executes everything |
| 1 | Execute low-risk actions, report to Telegram |
| 2 | Execute medium-risk actions, log to Neon |
| 3 | Execute high-risk actions after configurable delay |
| 4 | Execute anything except Commit tier |
| 5 | Full autonomy — never permitted for Finance or Legal |

### Permission Tiers `✅ IMPLEMENTED`

Cumulative 4-tier model — each higher tier includes all capabilities of lower tiers. Implemented in `substrate/types.py` as `PermissionTier` enum with `permits()` method. 52 action types mapped across tiers via `TIER_ACTION_MAP`. Enforced at three layers: `ConcreteGovernanceEngine.check_tier()`, `ExecutionAuthorityEngine.evaluate()` (step 1b), and `DepartmentAgent.execute_skill()`.

| Tier | Rank | Scope | Example Actions |
|---|---|---|---|
| READ | 0 | View data — never modify | analyze, research, report, browser_research |
| DRAFT | 1 | Create drafts — human approves before sending | draft_message, create_task, create_document |
| EXECUTE | 2 | Run workflows, send messages, operate browser | send_dm, post_content, browser_act, bulk_update |
| COMMIT | 3 | Financial actions, contracts — always human approved | execute_payment, production_deployment, credential_access |

---

## 5. Knowledge Architecture

### The 17 Layers `✅ ALL IMPLEMENTED`

Layers 1-5 are domain knowledge (`substrate/understanding/knowledge/knowledge_domains.py`).
Layers 6-17 are behavioral distillation (`substrate/understanding/knowledge/knowledge_layers.py`).
Both engines inject via CognitiveLoop PERCEIVE step. 12 behavioral layers with 110 principles.

| Layer | Name | Location | Status |
|---|---|---|---|
| 1 | Timeless Principles | `knowledge_domains.py` layers | ✅ |
| 2 | Business History | `knowledge_domains.py` historical | ✅ |
| 3 | Industry Knowledge | `knowledge_domains.py` current_focus | ✅ |
| 4 | Functional Expertise | `knowledge_domains.py` functional_expertise | ✅ |
| 5 | Tactical Execution | `knowledge_domains.py` tactical | ✅ |
| 6 | Psychological Foundations | `knowledge_layers.py` PSYCHOLOGICAL | ✅ |
| 7 | Real-Time Intelligence | `knowledge_layers.py` REAL_TIME_INTELLIGENCE | ✅ |
| 8 | Negotiation Mastery | `knowledge_layers.py` NEGOTIATION | ✅ |
| 9 | Crisis Management | `knowledge_layers.py` CRISIS | ✅ |
| 10 | Network Effects | `knowledge_layers.py` NETWORK_EFFECTS | ✅ |
| 11 | Organizational Design | `knowledge_layers.py` ORGANIZATIONAL_DESIGN | ✅ |
| 12 | Business Model Innovation | `knowledge_layers.py` BUSINESS_MODEL | ✅ |
| 13 | Cultural Intelligence | `knowledge_layers.py` CULTURAL_INTELLIGENCE | ✅ |
| 14 | ESG & Sustainability | `knowledge_layers.py` ESG | ✅ |
| 15 | Personal Productivity | `knowledge_layers.py` PERSONAL_PRODUCTIVITY | ✅ |
| 16 | Partnerships + Storytelling | `knowledge_layers.py` PARTNERSHIP | ✅ |
| 17 | Exits + Innovation Mgmt | `knowledge_layers.py` EXITS_INNOVATION | ✅ |

### Injection Order (CognitiveLoop PERCEIVE + UNDERSTAND steps)

```
0.   PERCEIVE     — resolve multimodal input to text (voice, image, document → text)
1.   PERCEIVE     — unified context assembly via ContextBuilder
     ├── ai_identity, ea_standards, signal_classification
     ├── bis_prompt, north_star
     ├── gws_docs, founder_profile, brand_identity, funnel_strategy
     ├── pattern_context, decision_log, dex_learnings
     └── primitives, hierarchy
2a.  UNDERSTAND   — InputIntelligence: intent detection + pattern matching
2b.  UNDERSTAND   — PatternIntelligence: behavioral pattern enrichment
2b2. UNDERSTAND   — KnowledgeLayerEngine: behavioral layers 6-17 (trigger-matched, top-2)
2c.  UNDERSTAND   — MemoryPromoter: canonical memory query-back (top-3)
3.   PLAN         — authority check (permission tier + risk class)
4.   EXECUTE      — agent runtime with deterministic fallback
5.   VERIFY       — output quality check
6.   STORE        — persist to memory + trace
```

All injection is enhancement only — failure in any step is caught and logged, never blocks execution.

### Domain Knowledge Coverage

21 domains across 8 categories: reality, human, civilization, business, technology, personal, systems, creative. 9 domains have full 6-layer structure (timeless → historical → functional → tactical → psychological → current). 12 domains have core principles only.

---

## 6. Systems Map (post-convergence 2026-05-23)

### Canonical Packages

```
substrate/         — the UMH brain (control plane, execution, governance, state, understanding)
  types.py         — single Pydantic type system (30+ models, PermissionTier, entities)
  __init__.py      — Substrate public API (execute, query, register, status, check_tier)
  control_plane/   — identity, context, governance, memory, registry, router
    runtime/       — gateway.py, cognitive_loop.py (core runtime)
  execution/       — 8-stage pipeline (spine.py), trace, feedback, actuation, voice
    agents/        — browser_agent.py (Playwright), computer_use_agent.py
  governance/      — accountability, policies, quality, validation
    policy/        — authority_engine.py, execution_authority_engine_v1.py
  understanding/   — perception, interpretation, knowledge (domains + layers), world model
adapters/          — external system adapters (models, GWS, browser, capabilities)
  models/          — model_router.py (intelligence routing), llm_adapter.py, cc_sdk.py
transports/        — I/O surfaces (discord, API, presence handlers, node mesh)
  api/             — cockpit.py (governance endpoints), operator.py
projections/       — platform-specific views
  eos/             — EOS projection (agents, entities, workflows)
    agents/        — base.py + 10 department agents (all with browser skills)
```

### Key Modules

| Module | Purpose | Status |
|---|---|---|
| `substrate/types.py` | Unified type system — 30+ Pydantic models, PermissionTier, entities | ✅ |
| `substrate/__init__.py` | Public API — execute, query, register, status, check_tier | ✅ |
| `substrate/control_plane/runtime/cognitive_loop.py` | Full Perceive→Understand→Plan→Execute loop | ✅ |
| `substrate/control_plane/runtime/gateway.py` | Single entry point for all external requests | ✅ |
| `substrate/control_plane/governance.py` | Deterministic risk classification + tier checking | ✅ |
| `substrate/execution/spine.py` | 8-stage execution pipeline | ✅ |
| `substrate/execution/agents/browser_agent.py` | Playwright web operator — wired to all agents | ✅ |
| `substrate/governance/policy/execution_authority_engine_v1.py` | 7-class authority model + tier gate | ✅ |
| `substrate/governance/policy/authority_engine.py` | Simple risk + org autonomy + tier gate | ✅ |
| `substrate/understanding/knowledge/knowledge_domains.py` | 21-domain registry, layers 1-5 | ✅ |
| `substrate/understanding/knowledge/knowledge_layers.py` | 12 behavioral layers (6-17), 110 principles | ✅ |
| `adapters/models/model_router.py` | Intelligence routing — cc_sdk → Gemini → Groq → Ollama | ✅ |
| `projections/eos/agents/base.py` | DepartmentAgent base — skills, tiers, browser | ✅ |
| `projections/eos/entities.py` | Entity model — 10 departments, 10 roles | ✅ |
| `transports/api/cockpit.py` | Governance tier check + tier listing endpoints | ✅ |

### Missing — High Priority

| Module | Purpose |
|---|---|
| Stripe billing integration | Subscription plans, usage-based AI cost |
| Firebase public auth | Required before non-founder users |
| Notification engine | Push notifications beyond Discord (email, SMS, push) |

---

## 7. Integrations Map

### Operational

| Integration | Purpose | Status |
|---|---|---|
| Discord Bot API | Primary founder interface — NLP, 40+ commands, voice, media | ✅ |
| Google Calendar | Meeting scheduling, event awareness, morning brief | ✅ |
| Google Gmail | Email inbox, contact extraction, relationship tracking | ✅ |
| Google Drive | Document access for onboarding backfill | ✅ |
| Google Tasks | Task sync and delegation | ✅ |
| Calendly | Sales call booking webhook → auto-brief trigger | ✅ |
| Apify | Instagram comment scraping for signal harvesting | ✅ |
| Anthropic API | Primary LLM — Haiku (classify), Sonnet (generate), Opus (reason) | ✅ |
| Google Gemini | Embeddings (embedding-001, 768-dim) | ✅ |
| OpenAI | Available in stack — not default routing | ⚠️ |

### Partial — Auth Required on VPS

| Integration | Status | Notes |
|---|---|---|
| Notion | ⚠️ | MCP connected on claude.ai — VPS needs OAuth |
| Slack | ⚠️ | MCP connected on claude.ai — VPS needs auth |
| Gmail MCP | ⚠️ | MCP connected on claude.ai — VPS needs auth |
| Google Calendar MCP | ⚠️ | MCP connected on claude.ai — VPS needs auth |

### Missing — High Priority

| Integration | Notes |
|---|---|
| Browser control (execution) | ✅ Wired to all 10 department agents via `DepartmentAgent` base class |
| Stripe | billing not started — required for public launch |
| Firebase Auth | public auth not started — required for non-founder users |

### Missing — Future

HubSpot, Salesforce, QuickBooks, Zapier/n8n, GitHub, Slack (deep), LinkedIn, WhatsApp Business

---

## 8. Memory Model

### Neon Database (primary persistent store)

| Table | Contents |
|---|---|
| `interactions` | Every AI call — input, output, model, tokens, cost (~329 rows) |
| `embeddings` | Semantic vectors for interaction memory (~329 vectors, 768-dim) |
| `outcomes` | RLHF signals — thumbs up/down, outcome type, notes |
| `human_profiles` | Behavioral profiles of leads and contacts |
| `agents` | Registered agent definitions — soul, skills, autonomy level |
| `skills` | 23 skills at 8-component spec — injected by skill_registry |
| `tasks` | Task queue — lifecycle from queued through outcome |
| `entity_links` | Knowledge graph edges — 489 relationship links |
| `events` | Event bus log — all system events with payload |
| `ventures` | Venture config including BIS JSON |
| `organizations` | Org-level isolation boundary (RLS) |
| `approvals` | Authority queue — pending human approvals |

### OS Trinity (harness layer, cross-product)

| Table | Contents |
|---|---|
| `user_intelligence_profiles` | Behavioral profile that survives product boundaries |
| `cross_product_permissions` | User-granted data sharing between EOS / CreatorOS / LYFEOS |
| `product_connections` | Registered product instances per user |

### Business Instance Spec (BIS)

Stored as JSON in `ventures.config_json`. Per-venture structured config: stage (1-6), current focus, proof to advance, offer name and price, ICP description, primary channels, financial targets, constraints, TAM estimate, runway months.

### Knowledge Layers (in-memory at runtime)

17-layer architecture. Layers 1-5: domain knowledge in `knowledge_domains.py`. Layers 6-17: behavioral distillation in `knowledge_layers.py` — 12 layers, 110 principles. Both injected at CognitiveLoop PERCEIVE step via trigger-matched selection. Not persisted to DB.

### Agent Memory (per-session)

`CognitiveLoop` maintains conversation context per session. `session_state.py` handles crash recovery and cross-session context. `context_compaction.py` compresses at 80% window capacity.

---

## 9. UX Surfaces

### Discord (current, operational)

Single founder access. Full system control. NLP routing with 40+ commands. Handles: text, voice, images, documents. Morning brief, proactive alerts, approval queue. Always-on via Docker (`os-discord` container). Telegram available as outbound notification channel only.

### Web Dashboard (Phase 2)

| View | Contents |
|---|---|
| Portfolio | All companies, P&L overview, strategic summary, Portfolio Advisor |
| Company | BIS status, stage guidance, CEO Agent, department overview |
| Department | Role boards, task queues, workflows, metrics, department agent |
| Role | Specific role surface, tools, documents, AI copilot, approval queue |

Permission model: Founder sees all. Manager sees own department and below. Team member sees own role only.

### Mobile App (Phase 3)

Quick decisions, approvals, notifications. AI chat, brief consumption, voice interface. Designed for running the business from a phone.

### Voice Interface (built, not primary)

`VoiceOutput` in `umh/voice.py` with persona/cloned voice profiles and streaming TTS. `substrate/execution/bridge/voice_session.py` handles live sessions. 11 meeting types with pre-meeting brief, during-meeting assist, and post-meeting action routing. Activated via `/meeting [type]` in Discord.

---

## 10. Endpoint vs MVP

### Endpoint (full vision)

All three OS products live. All 15 department agents with full skill sets. Browser and computer control operational. Real users with Firebase auth and Stripe billing. Mobile app. Cross-product intelligence compounding across EOS + CreatorOS + LYFEOS. RLHF meaningfully improving skills over time. Proprietary dataset accumulating. Local/offline execution option. $100K/month net profit.

### MVP Phase 1 `✅ COMPLETE` (2026-05-25)

- Full convergence: 4 canonical packages (substrate, adapters, transports, projections)
- 10 department agents with full skill sets, browser capabilities, and tier enforcement
- 4-tier permission model (READ/DRAFT/EXECUTE/COMMIT) enforced at 3 layers
- 17 knowledge layers (110 principles) injected at cognitive loop PERCEIVE step
- Entity model: Role, Department, Portfolio as typed Pydantic models
- Browser control wired to all agents via DepartmentAgent base class
- 778+ tests passing, 0 failures
- Production deployed: Discord bot, Cockpit Electron app, API

### MVP Phase 2 (current)

- Cockpit Electron desktop app — window modes, execution substrate panel
- SaaS product connections (EOS, CreatorOS, LYFEOS)
- Firebase auth — public users can sign up
- Stripe billing
- Notification engine (push, email, SMS beyond Discord)

### MVP Phase 3 (following)

- CreatorOS frontend + backend connection
- LYFEOS frontend + backend connection
- Mobile app
- Cross-product intelligence compounding

---

## 11. Open Decisions

Architectural decisions not yet made that will affect future builds.

**1. Browser control implementation** `✅ DECIDED`
- Decision: Playwright agents via `BrowserAgent` in `substrate/execution/agents/browser_agent.py`
- Wired to all 10 department agents via `DepartmentAgent` base class
- Computer use API available as future enhancement via `ComputerUseAgent` (Phase 2 cockpit execution panel)

**2. Frontend framework confirmation**
- README and structure reference Stitch for all three frontends
- Stitch uses Google's Gemini-backed design-to-code workflow
- Confirmation needed before Phase 2 frontend build begins

**3. Public auth architecture**
- Firebase confirmed as auth layer
- Open questions: Google OAuth only or email/password? Multi-tenant org model for teams? Invite flow?
- Decision needed before any non-founder user can sign up

**4. Billing architecture**
- Stripe confirmed
- Open questions: per-seat vs per-company vs usage-based? AI cost pass-through? Plan tiers?
- Decision needed before public launch

**5. Hosting for public product**
- Current: single VPS (100.77.233.50) — sufficient for founder-only validation
- Public scale requires: cloud infra, CDN, geographic distribution, autoscaling
- Decision needed 60-90 days before public launch

**6. CreatorOS / LYFEOS integration protocol**
- OS Trinity tables exist in Neon but are unpopulated
- Open questions: what data flows between products? User controls what crosses?
- Definition needed before any cross-product feature is built

**7. Local / offline execution path**
- Long-term confirmed direction: user owns data, can run locally
- No architecture defined yet
- Not blocking any current phase

---

## 13. Protocol Architecture

UMH uses a four-layer protocol system.
See `PROTOCOLS.md` for full documentation.

Quick reference:

```
Layer 0 — AI identity     substrate/control_plane/identity/ai_identity.py
Layer 1 — Platform        substrate/control_plane/runtime/cognitive_loop.py
Layer 2 — OS modules      per subscription
Layer 3 — Instance        database at runtime
```

This is why swapping the underlying model does not break the system.
The intelligence lives in the layers, not in the model.

---

## 12. Immediate Next Actions

In priority order:

1. **SaaS product connections** — wire EOS, CreatorOS, LYFEOS codebases to UMH substrate
2. **Cockpit Electron app** — window modes + execution substrate panel (Phase 2)
3. **Notification engine** — push, email, SMS beyond Discord
4. **Firebase auth** — implement public sign-up flow
5. **Stripe billing** — implement subscription and usage billing
6. **First public user** — onboard external founder to validate the system

---

*This document is the canonical specification. When in doubt, return to Section 2.*
