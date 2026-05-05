# AgentOS — Architecture & Master Specification

> Every build decision gets checked against this document.
> Last updated: 2026-03-23

---

## Philosophy

See PHILOSOPHY.md — the single source
of truth. Everything derives from it.

---

## 1. Vision

AgentOS is a modular, AI-native, role-driven business operating system that formalizes how businesses are structured and run. It allows humans and AI agents to operate roles through shared dashboards and workflows, teaches and optimizes the founder and team, integrates with the full software stack, stays current through live intelligence, evolves the organization from startup through scale and exit, and gives any entrepreneur an elite business brain, operating team, and execution system inside one unified platform.

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
14. **Cross-system** — EntrepreneurOS, CreatorOS, and LyfeOS share one intelligence substrate; each works standalone, any two compound, all three multiply
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

| Agent | Status | Notes |
|---|---|---|
| Sales Agent | ✅ | 11 skills, 8 sub-agents |
| Research Agent | ✅ | market intelligence, ICP analysis |
| Content Agent | ✅ | content creation, hook generation |
| Marketing Agent | ✅ | campaigns, ICP matching, distribution |
| Operations Agent | ✅ | process, bottlenecks, automation |
| Finance Agent | ⚠️ | stub — needs skills |
| Customer Success Agent | ⚠️ | 2 skills — needs more |
| HR Agent | ✗ | not built |
| Legal Agent | ✗ | not built |
| Product Agent | ✗ | not built |
| Engineering Agent | ✗ | not built |

**LEVEL 4: Execution Layer** `⚠️ BUILT, NOT WIRED`
Browser and computer control agent. Can operate any software a human can — fill forms, navigate apps, extract data, take actions. Takes AI from advisor to operator. `browser_agent.py` is built using Playwright; not yet wired to department agents.

### Autonomy Levels

| Level | Behavior |
|---|---|
| 0 | Draft only — human executes everything |
| 1 | Execute low-risk actions, report to Telegram |
| 2 | Execute medium-risk actions, log to Neon |
| 3 | Execute high-risk actions after configurable delay |
| 4 | Execute anything except Commit tier |
| 5 | Full autonomy — never permitted for Finance or Legal |

### Permission Tiers

| Tier | Scope |
|---|---|
| Read | View data — never modify |
| Draft | Create drafts — human approves before sending |
| Execute | Run workflows, send messages, create records, update CRM |
| Commit | Financial actions, contracts, hires — always human approved |

---

## 5. Knowledge Architecture

### The 17 Layers

| Layer | Name | Location | Status |
|---|---|---|---|
| 1 | Timeless Principles | `knowledge_domains.py` layers | ✅ |
| 2 | Business History | `knowledge_domains.py` historical | ✅ |
| 3 | Industry Knowledge | `knowledge_domains.py` current_focus | ✅ |
| 4 | Functional Expertise | `knowledge_domains.py` functional_expertise | ✅ |
| 5 | Tactical Execution | `knowledge_domains.py` tactical | ✅ |
| 6 | Psychological Foundations | `knowledge_layers.py` PSYCHOLOGICAL | ✅ |
| 7 | Real-Time Intelligence | `reality_engine.py` + scraped signals | ✅ |
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

### Injection Order (CognitiveLoop PERCEIVE step)

```
1a. Semantic memory        — top-5 past interactions, similarity > 0.6
1b. Domain knowledge       — KnowledgeDomainRegistry, trigger-matched, top-3 domains
1b2. Layered domain inject — get_layered_injection() via _map_task_to_domain()
1c. Behavioral context     — KnowledgeLayerEngine.get_relevant_layer()
1d. BIS venture context    — BusinessInstanceManager.get_context_for_agents()
```

All injected before execution. Never blocks execution on failure — all injection is enhancement only.

### Domain Knowledge Coverage

21 domains across 6 categories: reality, human, civilization, business, technology, personal, systems, creative. 9 domains have full 6-layer structure (timeless → historical → functional → tactical → psychological → current). 12 domains have core principles only.

---

## 6. Systems Map

### eos_ai/ Modules (44 files)

| Module | Purpose | Status |
|---|---|---|
| `agent_runtime.py` | Multi-model router — Claude Haiku/Sonnet/Opus selection by task cost | ✅ |
| `agent_teams.py` | Domain sub-agents and team router — 6 teams, 25 sub-agents | ✅ |
| `authority_engine.py` | 4-tier permission system — Read / Draft / Execute / Commit | ✅ |
| `browser_agent.py` | Playwright web operator — agents can operate any website | ⚠️ built, not wired |
| `business_instance.py` | BIS stage tracker — 6-stage lifecycle, Neon-backed | ✅ |
| `cognitive_loop.py` | 8-stage Perceive→Store loop — wraps all agent execution | ✅ |
| `context.py` | Environment loading and EOSContext construction | ✅ |
| `context_compaction.py` | Seamless context window compression at 80% capacity | ✅ |
| `coordination_engine.py` | Task assignment and CEO delegation across agents and humans | ✅ |
| `db.py` | Neon PostgreSQL connection with row-level security | ✅ |
| `embedder.py` | BAAI/bge-small-en-v1.5 embedding singleton (384-dim) | ✅ |
| `embedding_engine.py` | Semantic search and vector storage for interaction memory | ✅ |
| `error_handler.py` | Self-healing error recovery with Telegram alerting | ✅ |
| `event_bus.py` | Reactive coordination — decouples producers from consumers | ✅ |
| `evolution_engine.py` | Weekly self-improvement — workflow evolution, agent proposals | ✅ |
| `execution_engine.py` | Formal task lifecycle tracking — queued → completed → outcome | ⚠️ built, not wired |
| `gateway.py` | Single entry point for all external requests (known: raw_prompt param) | ✅ |
| `gws_connector.py` | Google Workspace — Calendar, Gmail, Drive, Tasks OAuth | ✅ |
| `human_intelligence.py` | Behavioral profiling of every person the system interacts with | ✅ |
| `identity_engine.py` | System persona management across interface contexts | ✅ |
| `integration_test.py` | Integration test suite | — |
| `knowledge_domains.py` | 21-domain registry with 6-layer structure and trigger matching | ✅ |
| `knowledge_graph.py` | Entity relationship graph — leads, signals, outcomes, agents | ✅ |
| `knowledge_layers.py` | 17-layer behavioral distillation — 148 principles, 11 foundation dicts | ✅ |
| `media_processor.py` | Voice synthesis and Whisper transcription — 303KB voice confirmed | ✅ |
| `memory.py` | All Neon writes — interactions, events, outcomes, profiles | ✅ |
| `model_preferences.py` | Business context routing — maps venture + task to model config | ✅ |
| `onboarding_backfill.py` | Reads all connected integrations on first connect — GWS backfill | ✅ |
| `orchestrator.py` | 6am cron + proactive triggers — morning cycle + event-driven | ✅ |
| `os_trinity.py` | Cross-product permissions and user intelligence profiles | ✅ |
| `portfolio_advisor.py` | Board-level view across all ventures — P&L, stage, patterns | ✅ |
| `principle_engine.py` | Root rule injection into every AI decision | ✅ |
| `reality_engine.py` | Market intelligence — scans every 6h, classifies by priority | ✅ |
| `research_engine.py` | Autonomous research — detects knowledge gaps, fills them, stores | ✅ |
| `session_state.py` | Session crash recovery and cross-session context | ✅ |
| `skill_improvement.py` | RLHF-driven skill rewriting from outcome data | ✅ |
| `skill_registry.py` | Loads and indexes 23 skills — keyword + semantic search | ✅ |
| `status.py` | Daily system health check dashboard | ✅ |
| `strategy_engine.py` | First-principles strategic reasoning and decision evaluation | ✅ |
| `system_context.py` | Interface-aware validation — Telegram vs Claude Code vs API | ✅ |
| `user_model.py` | Founder behavior modeling — closes the intent-expression gap | ✅ |
| `venture_knowledge.py` | Per-venture knowledge base — skills, signals, context per org | ✅ |
| `voice_interface.py` | Voice turns, 11 meeting types, pre/during/post meeting support | ✅ |
| `workflow_engine.py` | Multi-step workflow execution and state tracking | ✅ |

### Missing — High Priority

| Module | Purpose |
|---|---|
| `billing_connector.py` | Stripe integration — subscription plans, usage-based AI cost |
| `auth_layer.py` | Firebase public auth — required before non-founder users |
| `notification_engine.py` | Push notifications and scheduled alerts beyond Telegram |

---

## 7. Integrations Map

### Operational

| Integration | Purpose | Status |
|---|---|---|
| Telegram Bot API | Primary founder interface — NLP, 40+ commands, voice, media | ✅ |
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
| Browser control (execution) | Playwright installed; `browser_agent.py` built; not wired to agents |
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
| `cross_product_permissions` | User-granted data sharing between EOS / CreatorOS / LyfeOS |
| `product_connections` | Registered product instances per user |

### Business Instance Spec (BIS)

Stored as JSON in `ventures.config_json`. Per-venture structured config: stage (1-6), current focus, proof to advance, offer name and price, ICP description, primary channels, financial targets, constraints, TAM estimate, runway months.

### Knowledge Layers (in-memory at runtime)

17-layer distillation in `knowledge_layers.py`. 148 behavioral principles across 11 foundation dicts. Injected at runtime — not persisted to DB.

### Agent Memory (per-session)

`CognitiveLoop` maintains conversation context per session. `session_state.py` handles crash recovery and cross-session context. `context_compaction.py` compresses at 80% window capacity.

---

## 9. UX Surfaces

### Telegram (current, operational)

Single founder access. Full system control. NLP routing with 40+ commands. Handles: text, voice, images, documents. Morning brief, proactive alerts, approval queue. Always-on via Docker.

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

`VoiceInterface` in `eos_ai/` operational. 11 meeting types with pre-meeting brief, during-meeting real-time assist (10 shortcuts), and post-meeting action routing. Activated via `/meeting [type]` in Telegram.

---

## 10. Endpoint vs MVP

### Endpoint (full vision)

All three OS products live. All 15 department agents with full skill sets. Browser and computer control operational. Real users with Firebase auth and Stripe billing. Mobile app. Cross-product intelligence compounding across EOS + CreatorOS + LyfeOS. RLHF meaningfully improving skills over time. Proprietary dataset accumulating. Local/offline execution option. $100K/month net profit.

### MVP Phase 1 (current — mostly built)

- VPS harness running — 4 Docker services, always-on
- Telegram as founder interface — 40+ commands, voice, media
- 44 eos_ai modules, all importing clean
- 12 agents, 23 skills, 17 knowledge layers (148 principles)
- BIS seeded for Lyfe Institute (Stage 1, Initiate Arena $750)
- GWS integrations operational (Calendar, Gmail, Drive, Tasks)
- Morning brief and proactive triggers (6am cron)
- 6-stage BIS system — proof-gated advancement
- 11 meeting types with voice interface
- Knowledge injection at PERCEIVE (4 layers)

### MVP Phase 2 (next)

- Stitch frontend for EntrepreneurOS
- Firebase auth — public users can sign up
- Notion OAuth — interim dashboard live
- Browser control wired to department agents
- Finance and CS agent skills completed
- Stripe billing

### MVP Phase 3 (following)

- CreatorOS frontend
- LyfeOS frontend
- Mobile app
- Cross-product compounding
- All department agents complete with full skill sets

---

## 11. Open Decisions

Architectural decisions not yet made that will affect future builds.

**1. Browser control implementation**
- Option A: Playwright agents — already in stack, `browser_agent.py` built, used by `dm_monitor.py`
- Option B: Anthropic computer use API — newer, more capable, higher cost
- Decision required before execution layer wiring begins

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

**6. CreatorOS / LyfeOS integration protocol**
- OS Trinity tables exist in Neon but are unpopulated
- Open questions: what data flows between products? User controls what crosses?
- Definition needed before any cross-product feature is built

**7. Local / offline execution path**
- Long-term confirmed direction: user owns data, can run locally
- No architecture defined yet
- Not blocking any current phase

---

## 13. Protocol Architecture

EOS uses a four-layer protocol system.
See `PROTOCOLS.md` for full documentation.

Quick reference:

```
Layer 0 — AI identity     eos_ai/ai_identity.py
Layer 1 — Platform        eos_ai/cognitive_loop.py
Layer 2 — OS modules      per subscription
Layer 3 — Instance        database at runtime
```

This is why swapping the underlying model does not break the system.
The intelligence lives in the layers, not in the model.

---

## 12. Immediate Next Actions

In priority order:

1. **ARCHITECTURE.md** — this document ✅
2. **Notion OAuth** — activate on VPS — interim dashboard live today
3. **Browser control decision** — Playwright vs computer-use API, then wire to agents
4. **Finance + CS agent skills** — fill skill gaps in both departments
5. **Stitch frontend Phase 2** — scope and begin EntrepreneurOS web dashboard
6. **Firebase auth** — implement public sign-up flow
7. **Stripe billing** — implement subscription and usage billing
8. **First public user** — onboard external founder to validate the system

---

*This document is the canonical specification. When in doubt, return to Section 2.*
