---
phase: "14.6C"
status: "DRAFT"
operator_approved: false
allows_implementation: false
date: "2026-06-04"
provenance: "SYNTHESIZED_CANON"
description: "Cross-product boundary matrix across all 8 entities in the UMH ecosystem. Synthesized from all 166 Phase 14.6B canon artifacts across EOS, CreatorOS, LyfeOS, and UMH."
sources:
  - "umh_cross_product_integration_architecture.md"
  - "umh_eos_creatoros_lyfeos_integration_map.md"
  - "umh_execution_boundary_model.md"
  - "umh_coherent_system_layer_map.md"
  - "umh_full_end_state_canon.md"
  - "umh_projection_data_boundary_privacy_model.md"
  - "umh_cockpit_jarvis_doctrine.md"
  - "phase14_6b_creatoros_eos_boundary_canon.md"
  - "phase14_6b_eos_agent_architecture_spec.json"
  - "phase14_6b_eos_auth_security_truth.json"
  - "phase14_6b_creatoros_automation_ai_canon.json"
  - "lyfeos_ai_companion_architecture.md"
  - "lyfeos_full_end_state_canon.md"
  - "lyfeos_auth_session_security_truth.md"
  - "lyfeos_data_ontology.json"
---


# Phase 14.6C: Cross-Product Boundary Matrix

This document maps every boundary dimension across all 8 entities in the UMH ecosystem. Every claim traces to a Phase 14.6B canon artifact. Where boundaries are uncertain, the document flags OPEN_QUESTION_OPERATOR_DECISION_REQUIRED rather than inventing a resolution.


## 1. Entities

Eight entities define the full ecosystem. Six exist today in code or canon. Two are future architectural positions documented in the UMH end-state canon.

| # | Entity | Current State | Canon Source |
|---|--------|---------------|--------------|
| 1 | **UMH Substrate** | 696 Python files, 206,602 LOC. Production runtime (os-discord, os-operator, os-webhook, os-scraper). | umh_coherent_system_layer_map.md Layer 1 |
| 2 | **Cockpit** | 276 API endpoints, 27 panels, Electron/React frontend. Deployed at universalmetaharness.tech (Fly.io). | umh_cockpit_jarvis_doctrine.md, umh_coherent_system_layer_map.md Layer 2 |
| 3 | **EOS (EntrepreneurOS)** | Most mature projection. 30 Python files, 5,699 LOC. SaaS in saas/ (TypeScript/React). 10 department agents. | umh_eos_creatoros_lyfeos_integration_map.md, phase14_6b_eos_lossless_product_canon.md |
| 4 | **CreatorOS** | Integration-complete projection. 8 Python files, 1,099 LOC. External SaaS at antonyfmunoz/CreatorOS (296 files). | phase14_6b_creatoros_lossless_product_canon.md |
| 5 | **LyfeOS** | Partial integration projection. 8 Python files, 1,184 LOC. External SaaS at lyfeos.net (35 tables, Replit). | lyfeos_full_end_state_canon.md |
| 6 | **External Tools** | 87 adapter files, 18,723 LOC. Model routing, Google Workspace, Notion, browser exports, calendar, capabilities. | umh_coherent_system_layer_map.md Layer 5 |
| 7 | **Future Native OS** | Forked VS Code IDE embedded in cockpit. Governed commit flows. Agent-assisted development. | umh_full_end_state_canon.md (Meta-IDE Integration) |
| 8 | **Future Native Models** | Fine-tuned intelligence layer. Training extractor + finetune harness at substrate/intelligence/. | umh_coherent_system_layer_map.md (intelligence/ subsystem) |


## 2. Boundary Matrix

### 2A. Visibility and Access

| Dimension | UMH Substrate | Cockpit | EOS | CreatorOS | LyfeOS | External Tools | Future OS | Future Models |
|-----------|---------------|---------|-----|-----------|--------|----------------|-----------|---------------|
| **Public/Private** | Private infrastructure | Private operator-only | Public SaaS (target) | Public SaaS (target) | Public SaaS (target) | Private adapters | Private operator tool | Private substrate component |
| **Primary User** | No direct users. Consumed by all other entities. | Operator (Antony). Single user. | Founders, operators, teams. Multi-tenant. | Creators, consumers, advertisers. Multi-tenant. | Individuals seeking life optimization. Multi-tenant. | No direct users. Consumed by substrate. | Operator (Antony). Single user. | No direct users. Consumed by substrate. |
| **Product Role** | Universal intelligence substrate. Domain-agnostic execution platform. | Private Jarvis command center. Full-stack observation + control surface. | Business operations OS. Structure, operate, optimize, scale economic activity. | Creator product/distribution/community OS. Produce, distribute, monetize content. | Personal life OS. Measure, plan, execute, reflect, progress across life domains. | External system connectivity. Adapters, APIs, CLI wrappers, MCP. | Substrate-aware code editing + governed development sessions. | Custom intelligence trained on operator's operational data. |

### 2B. Ownership

| Dimension | UMH Substrate | Cockpit | EOS | CreatorOS | LyfeOS | External Tools | Future OS | Future Models |
|-----------|---------------|---------|-----|-----------|--------|----------------|-----------|---------------|
| **Data Ownership** | Execution traces, governance logs, memory store, organism graph, observation pipeline, production truth. | Operator preferences, session state, layout config, panel positions. | Portfolios, companies, departments, roles, CRM, tasks, workflows, KPIs, agent actions. | Posts, products, communities, courses, orders, conversations, creator analytics, UGC campaigns. | Profiles, quests, stats, daily logs, vision goals, AI conversations, knowledge dismissals, integrations. | Adapter state, connection manifests, sync watermarks. | Development session state, governed commit history. | Training data, model weights, evaluation metrics. |
| **Capability Ownership** | Execution pipeline (8-stage spine), governance engine (risk classification), signal routing, memory management, organism coordination, domain bridging, type system. | Observation (276 endpoints), approval/rejection flows, organism control, infrastructure inspection, voice/text command dispatch. | Org chart generation, department agents (10), workflow/SOP engine, KPI tracking, CRM pipeline, financial dashboard, portfolio management, capital allocation, business templates. | Content creation/distribution, community hosting, course builder, marketplace, checkout, UGC campaigns, ads platform, visual automation builder, email/newsletters. | Quest/mission system, daily logging, gamification (XP/levels/streaks/tokens), AI companion (NOVA), vision goals, chronilog, knowledge base (16 domains), voice input. | Model routing (4-provider fallback chain), Google Workspace sync, Notion sync, browser exports, calendar, Kokoro TTS, web scraping. | Substrate-aware code intelligence, pre-commit gate integration, agent-assisted sessions. | Domain-specific fine-tuned inference, learned preference application. |
| **UX Ownership** | None. UMH has no end-user interface. Abstract ports only. | WorldView design system (wv-* classes, 240px LeftRail, visible borders). Electron shell. 27 panels + 26 components. | Executive command center aesthetic. Finance-grade clarity. Dark theme. Corporate precision. | X/Twitter-inspired minimalism. Professional variant. Light theme default. Clean, fast, functional. | Gamified life dashboard. Mobile-first PWA. Bright/motivational. Quest-based progression. | None. Adapter layer has no UI. | VS Code fork. Substrate-aware extensions. Cockpit-embedded. | None. Model layer has no UI. Consumed by other entities. |

### 2C. Auth Model

| Dimension | UMH Substrate | Cockpit | EOS | CreatorOS | LyfeOS | External Tools | Future OS | Future Models |
|-----------|---------------|---------|-----|-----------|--------|----------------|-----------|---------------|
| **Current Auth** | N/A (consumed by services, not users). PermissionTier (READ/DRAFT/EXECUTE/COMMIT) + RiskClass (6 levels) for agent governance. | API Key (X-API-Key) + Operator Token (X-Operator-Token) + Dev Bypass from private IPs + WebSocket bearer. Rate-limited per action. | GitHub main: Passport.js + Firebase (STALE). Beast branch: Clerk (TARGET). No RLS on GitHub main. 14-table RLS in UMH platform layer. | Passport.js (BROKEN -- comparePasswords returns true for all). No RLS. | Passport.js + Firebase (Google/Apple/Facebook OAuth + 2FA). Express sessions (7-day, PostgreSQL store). | Per-adapter auth (OAuth tokens, API keys). Stored in adapter state, not user-facing. | Inherits cockpit auth. Operator-only. | N/A. Substrate-internal only. |
| **Target Auth** | Same substrate governance model. PermissionTier + RiskClass unchanged. | Same API Key + Operator Token model. Potentially Clerk SSO integration. | Clerk. Multi-tenant org switching. RBAC+ABAC hybrid. | Clerk. Shared SSO with EOS via UMH platform identity. | Clerk. Shared SSO with EOS and CreatorOS via UMH platform identity. | Same per-adapter model. OAuth tokens managed by adapter engine. | Cockpit auth passthrough. | N/A. |

### 2D. Agent Model

| Dimension | UMH Substrate | Cockpit | EOS | CreatorOS | LyfeOS | External Tools | Future OS | Future Models |
|-----------|---------------|---------|-----|-----------|--------|----------------|-----------|---------------|
| **Agent Architecture** | Substrate agents: organism coordinator, workcell protocol, execution governance, autonomous tick, template registry, diagnostic engine. Infrastructure-level. Not user-facing. | DEX: operator-facing AI interface to the reality model. Voice + text + visual interaction modes. Routes through substrate intelligence. | Full multi-agent hierarchy. 3 tiers (Strategic/Planning/Execution). 12 agents: EA, Portfolio Advisor, CEO, Sales, Marketing, Finance, CustomerSuccess, HR, Legal, Operations, Product, Engineering. 62 skills. Permission tiers. Delegation chain. | AI is UTILITY-LEVEL. Creator-defined chatbots (ai_agents table) are products sold to consumers. Content assistant, moderation, analytics insights -- all desired but NOT IMPLEMENTED. No autonomous agents. No delegation chain. No permission tiers. | NOVA companion: single AI relationship per user. Advisor + Coach + Executive Assistant. 6 tools (web search, read webpage, create vision goal, batch missions, uncomplete, knowledge lookup). Haiku default, auto-upgrade to Sonnet. Not autonomous -- user-initiated only. | No agents. Adapters are passive connectors invoked by substrate. | Development session agent (DevelopmentSessionBridge). Governed organ within organism. Tracked as organism work unit. | No agents. Model inference layer consumed by agents in other entities. |
| **Agent Governance** | SpineGuard pre-validation. Autonomous action gateway. Governed execution spine. | Operator approval/rejection for HIGH+ risk. Approval bridge to Discord. | READ/DRAFT/EXECUTE/COMMIT permission tiers per agent. Delegation: Operator -> EA -> CEO -> Department -> CEO -> EA -> Operator. | No agent governance. AI agents are user-facing products with system prompts. No risk classification on AI actions. | No formal governance. AI tool actions (create goals, batch missions) execute without approval model. INFERRED_PROFESSIONAL_GAP. | N/A. | Inherits substrate governance. Pre-commit gates. | N/A. |

### 2E. Integration and Deployment

| Dimension | UMH Substrate | Cockpit | EOS | CreatorOS | LyfeOS | External Tools | Future OS | Future Models |
|-----------|---------------|---------|-----|-----------|--------|----------------|-----------|---------------|
| **Integration Path** | IS the integration substrate. All other entities connect through it. Abstract ports in substrate/sockets/. | Direct import from substrate. FastAPI backend in transports/api/. | Projection registration via projections/eos/integration/manifest.py. 3 signal types, 5 capabilities, polling-based ingestion. Integration ID: "eos". Full 7/7 socket components. | Projection registration via projections/creatoros/integration/manifest.py. 3 signal types, 4 capabilities. Integration ID: "creatoros". 6/7 socket components (no poller). | Projection registration via projections/lyfeos/integration/manifest.py. 3 signal types, 4 capabilities. Integration ID: "lyfeos". 2/7 socket components active (manifest + signals). | Adapter engine lifecycle. Manifests, maturity model, capability catalog. Per-adapter registration. | DevelopmentSessionBridge registers as organism organ. Cockpit endpoint at organism.dev_sessions. | substrate/intelligence/ finetune harness. Training extractor feeds model weights. |
| **Deployment Target** | Docker on VPS (4 containers: os-discord, os-operator, os-webhook, os-scraper). Always-on coordination brain. | Fly.io (universalmetaharness.tech). Electron app for local use. | Target: Fly.io (saas/ TypeScript app). Not deployed yet. | Target: Fly.io or similar PaaS. Not deployed yet (local dev only). | Currently: Replit (lyfeos.net). Target: Fly.io. | Runs within substrate Docker containers. Some adapters invoke external APIs (Google, Notion, Groq). | Embedded in cockpit. Same Fly.io deployment. | Runs on Beast (GPU). Weights served to substrate via API. |
| **Revenue Model** | None. Private infrastructure. Cost center. | None. Private operator tool. Cost center. | SaaS subscription. Tiered: Solo ($49), Growth ($149), Scale ($499), Portfolio ($999). Target: $10K/month net. | SaaS subscription. Tiered: Free, Pro ($29), Business ($79), Enterprise ($199). Platform takes percentage of creator commerce. Ads revenue share. | SaaS subscription. Tiered: Free (basic), Premium ($9.99), Pro ($19.99). | None. Infrastructure cost absorbed by substrate. | None. Extension of cockpit. | None. Training cost absorbed by substrate. |

### 2F. Identity Boundaries

| Dimension | UMH Substrate | Cockpit | EOS | CreatorOS | LyfeOS | External Tools | Future OS | Future Models |
|-----------|---------------|---------|-----|-----------|--------|----------------|-----------|---------------|
| **What It Must NOT Become** | Must NOT become an application. Must NOT contain projection-specific logic. Must NOT hardcode instance context (AI names, user names, IPs, company names). Must NOT import from transports/ or services/. Must NOT contain EOS/CreatorOS/LyfeOS branded identifiers. | Must NOT become a public-facing product. Must NOT become a customer-facing dashboard. Must NOT contain business logic (that belongs in substrate). Must NOT expose end-user data without audit logging. | Must NOT absorb content creation (that is CreatorOS). Must NOT absorb community hosting (that is CreatorOS). Must NOT absorb life tracking (that is LyfeOS). Must NOT have a consumer feed. Must NOT gamify with XP/levels. | Must NOT absorb business operations (org charts, department agents, workflow governance, KPIs, CRM pipelines -- all EOS). Must NOT build autonomous agent hierarchies. Must NOT absorb life tracking (that is LyfeOS). | Must NOT absorb business operations (that is EOS). Must NOT absorb content distribution (that is CreatorOS). Must NOT build autonomous business agents. Must NOT become a productivity app without the gamification/transformation identity. | Must NOT contain business logic. Must NOT maintain user-facing state. Must NOT become an application layer. | Must NOT become a general-purpose IDE. Must remain substrate-aware and governed. | Must NOT become a general-purpose model provider. Must remain operator-specific and private. |


## 3. Data Boundary Detail

### 3A. What Each Entity Owns Exclusively

**UMH Substrate**
- Execution traces (TraceRecord with 18 event types, Neon persistence)
- Governance decisions (GovernanceVerdict, approval lifecycle)
- Organism graph (runtime graph, coordinator state, workcell assignments)
- Memory store (conversation memory, agent memory, canonical memory)
- Observation pipeline output (decomposed primitives, domain-bridged observations)
- Production truth (source truth registry, truth promotion records)
- Signal envelopes (all signals from all projections pass through here)
- Type system (substrate/types.py -- 30+ canonical Pydantic models)
- Self-model (substrate/self_model.py -- runtime identity and instance context)

**Cockpit**
- Operator preferences (panel layout, theme, view modes)
- Session state (active panel, drawer state, command palette history)
- Layout configuration (WorldView panel positions, split pane ratios)
- Approval queue display state (which items viewed, dismissed)
- Voice command history (local to cockpit session)

**EOS**
- Users (text PK, email, company fields -- different schema from other products)
- CRM: crm_contacts, crm_deals, crm_activities (pipeline management)
- Tasks (workflow-generated task tracking)
- Agent actions (execution audit trail for 12 agents, 62 skills)
- UMH outcomes (audit table for pipeline outcome writeback)
- Beast branch: companies, portfolios, departments, roles, workflows, SOPs, onboarding
- Financial data: revenue, expenses, cash_flow (Beast branch)

**CreatorOS**
- Users (20 current tables, 30+ target)
- Content: posts, comments, tagged_users, stories, scheduled_posts
- Social: followers, saved_posts, bookmarks
- Community: communities, channels, channel_messages, memberships
- Messaging: conversations, conversation_participants, direct_messages
- Notifications: notifications, notification_preferences
- Commerce: products, revenue, contacts, orders, subscriptions
- AI: ai_agents, ai_chats (creator-built chatbot products)
- Automation: automation_flows, automation_runs (target)
- Courses: courses, modules, lessons, enrollments, progress (target)
- UGC: ugc_campaigns, applications, deliverables, payments (target)
- Ads: ad_campaigns, ad_groups, ad_creatives, ad_impressions (target)

**LyfeOS**
- Users (41-column core table with auth, verification, subscription, Stripe stubs)
- userStats (XP, level, 6 stat tokens, streaks, efficiency scores)
- userProfile (100+ columns: archetypes, beliefs, shadow patterns, financial, health, relationships)
- userDailyLogs (mental/physical/emotional scores, gratitude, goals, reflections)
- Quests/missions (difficulty ranks S-D, resource costs, XP rewards)
- Vision goals (5 time horizons, milestone tracking)
- AI conversations + messages (threaded, with soft delete)
- AI legacy messages (flat aiMessages table)
- Knowledge base dismissals (dismissed sources per user)
- Integrations (Google Calendar, Google Docs flags)
- Documents, media items, calendar events, contacts, kanban, spreadsheets, canvases, graphs

### 3B. Shared via UMH

| Data Type | Owner | Access Pattern | Who Consumes |
|-----------|-------|----------------|--------------|
| Platform users/orgs/portfolios | UMH (transports/api/http/db/schema.ts) | Both authenticate against UMH user records | All projections |
| Signal envelopes | UMH substrate | Projections emit, substrate routes | All projections (read-only) |
| Execution traces | UMH substrate | Produced during signal processing | Cockpit (observation), projections (outcome) |
| Governance decisions | UMH substrate | Produced during risk classification | Cockpit (approval queue), projections (gate) |
| Memory store | UMH substrate | Written by CognitiveLoop + spine | Cockpit (inspection), agents (context) |
| Cross-product synthesis | UMH substrate | Computed from multi-projection signals | Cockpit (operator intelligence) |

### 3C. Sensitive Data Exclusions (HARD BOUNDARY)

These data categories MUST NOT enter UMH under any circumstances:

| Product | Excluded Data | Reason |
|---------|---------------|--------|
| LyfeOS | Therapy session content, trauma narratives, self-harm indicators, medication details, relationship intimate details | Personal health/safety data. Regulatory risk. |
| CreatorOS | Audience personal identifiers (beyond what creators share), payment card details | PII/PCI compliance. |
| EOS | Employee SSNs, salary details, termination records, legal case details | Employment law. Regulatory risk. |
| All | Raw passwords, session secrets, OAuth tokens | Security fundamentals. |

**Source: umh_projection_data_boundary_privacy_model.md (Section: Sensitive Excluded Data)**

**Implementation status: NOT IMPLEMENTED.** No sensitive data filtering mechanism exists in signal emitters. This is a P0 gap that must be resolved before any projection-to-substrate data flow is activated in production.


## 4. Agent Boundary Detail

### 4A. EOS: Full Autonomous Agent Hierarchy

| Tier | Agent | Permission Level | Primary Skills |
|------|-------|-----------------|----------------|
| Strategic | EA Agent | EXECUTE | Triage, routing, operator interface, next-best-action |
| Strategic | Portfolio Advisor | READ | Portfolio analytics, cross-entity intelligence, capital allocation guidance |
| Planning | CEO Agent | EXECUTE | Entity strategy, department coordination, delegation, approval |
| Execution | Sales Agent | EXECUTE | Lead qualification, outreach, pipeline management |
| Execution | Marketing Agent | EXECUTE | Content strategy, campaign management, brand monitoring |
| Execution | Finance Agent | EXECUTE | P&L analysis, cash flow, unit economics, forecasting |
| Execution | Customer Success Agent | EXECUTE | Retention, satisfaction, onboarding, support |
| Execution | HR Agent | DRAFT | Hiring, team structure, performance tracking |
| Execution | Legal Agent | READ | Compliance, contract review, risk assessment |
| Execution | Operations Agent | EXECUTE | Process optimization, SOP management, efficiency |
| Execution | Product Agent | EXECUTE | Feature planning, roadmap, user feedback analysis |
| Execution | Engineering Agent | EXECUTE | Technical execution, code review, architecture decisions |

Total: 12 agents. 62 skills across all agents. Delegation chain: Operator -> EA -> CEO -> Department -> CEO -> EA -> Operator. All agents extend DepartmentAgent base class (198 LOC).

**Source: phase14_6b_eos_agent_architecture_spec.json**

### 4B. CreatorOS: AI Utility Layer (NOT an Agent Hierarchy)

| Feature | What It Is | What It Is NOT |
|---------|-----------|----------------|
| Custom AI agents | Creator-built chatbots with custom system prompts, sold as products to consumers via ai_agents table | NOT operational agents that run the creator's business |
| AI content assistant | Desired: AI-powered content generation, caption writing, hashtag suggestions | NOT autonomous content publishing |
| AI community moderation | Desired: auto-moderation, spam detection, content classification | NOT a governance engine |
| AI analytics insights | Desired: intelligent analytics summaries and recommendations | NOT KPI anomaly detection or business intelligence |
| Visual automation builder | Manychat-style trigger/action flows for content/commerce | NOT governed business workflows with approval chains |

**Boundary rule:** EOS agents OPERATE ON businesses. CreatorOS AI agents are PRODUCTS OF creators. If a creator wants AI-assisted business operations, that capability lives in EOS. If a creator wants AI-powered content tools, that capability lives in CreatorOS.

**Source: phase14_6b_creatoros_eos_boundary_canon.md Section 4**

### 4C. LyfeOS: NOVA Companion (Single AI Relationship)

| Attribute | Value |
|-----------|-------|
| Default name | NOVA (user-renamable via userStats.aiAssistantName) |
| Roles | Advisor, Coach, Executive Assistant |
| Model routing | Haiku (default) -> Sonnet (auto-upgrade on tool use, complexity, images) |
| Tools | web_search, read_webpage, create_vision_goal, batch_create_missions, uncomplete_mission, lookup_knowledge_base |
| Knowledge | 16-domain knowledge base (Philosophy through Supplementation) |
| Context | Full user data salience: profile, stats, missions, logs, vision, calendar, history |
| Conversation | Threaded with soft delete. SSE streaming. Image analysis. Voice input. |
| Governance | NONE. No risk classification. No approval model. INFERRED_PROFESSIONAL_GAP. |

**Boundary rule:** NOVA is a COMPANION, not an autonomous agent. User-initiated only. No delegation chain. No permission tiers. If LyfeOS needs governed autonomous actions (proactive alerts, background processing), those must route through UMH substrate governance.

**Source: lyfeos_ai_companion_architecture.md**

### 4D. UMH Substrate: Infrastructure Agents

| Component | Role | Scope |
|-----------|------|-------|
| Organism Coordinator | Orchestrates workcells, manages topology, heartbeats | System-wide coordination |
| Workcell Protocol | Work unit assignment, completion tracking, role management | Per-workcell execution |
| Autonomous Tick | Scheduled cadence execution (dry_run_only currently) | Background processing |
| Template Registry | Governed template library for low-risk autonomous actions | Template governance |
| Diagnostic Engine | System health diagnostics, bottleneck detection | Observability |
| SpineGuard | Pre-validates execution requests against governance policy | Execution gateway |
| DevelopmentSessionBridge | Makes coding harness a governed organ | Dev session tracking |

These are NOT user-facing agents. They are infrastructure mechanisms that govern how other agents (EOS, LyfeOS NOVA) operate within the substrate.

### 4E. Cockpit: DEX (Operator Interface Agent)

DEX is the operator's interface to the entire UMH reality model. It is unique: not a product agent (EOS), not a utility (CreatorOS), not a companion (LyfeOS), not infrastructure (substrate). DEX is the operator's voice-and-text command surface that sits above all projections.

| Attribute | Value |
|-----------|-------|
| Interaction modes | Voice, text, visual (ambient display) |
| Scope | Full ecosystem: all projections, all agents, all infrastructure |
| Governance | Operator-level: COMMIT tier. Can approve/reject any action. |
| Intelligence | Routes through model_router. Uses best-available model (agent_type='ceo'). |


## 5. Integration Points

### 5A. How Each Product Connects to UMH

All projections connect through the same socket contract pattern: manifest, signals, handlers, outcomes, correlation, tables.

| Projection | Integration ID | Registration File | Signal Types | Capability Types | Socket Completeness |
|------------|---------------|-------------------|--------------|-----------------|-------------------|
| EOS | `"eos"` | projections/eos/integration/manifest.py | eos_contact_created, eos_deal_created, eos_activity_logged | noop, create_contact, create_deal, update_deal_stage, log_activity | 7/7 (full) |
| CreatorOS | `"creatoros"` | projections/creatoros/integration/manifest.py | creatoros_post_created, creatoros_product_listed, creatoros_revenue_recorded | noop, create_post, create_product, record_revenue | 6/7 (no poller) |
| LyfeOS | `"lyfeos"` | projections/lyfeos/integration/manifest.py | lyfeos_quest_completed, lyfeos_daily_log_created, lyfeos_stats_updated | noop, create_quest, complete_quest, log_daily_reflection | 2/7 (manifest + signals only) |

### 5B. Abstract Ports (substrate/sockets/)

| Port | File | Purpose | Who Registers Concrete Implementation |
|------|------|---------|--------------------------------------|
| Signal Port | substrate/sockets/signal_port.py | Signal emission and routing | transports/discord/signal_factory.py |
| Capability Port | substrate/sockets/capability_port.py | Capability declaration and invocation | Each projection's manifest |
| Outcome Port | substrate/sockets/outcome_port.py | Outcome notification and writeback | Each projection's outcomes module |
| View Port | substrate/sockets/view_port.py | View rendering and data serving | projections/eos/views/ |
| Notification Port | substrate/sockets/notification.py | Abstract notification dispatch | transports register at boot |
| Channel Port | substrate/sockets/channel_port.py | Abstract channel routing | transports register at boot |
| Projection Port | substrate/sockets/projection_port.py | Projection registration | Each projection's manifest |
| Config Port | substrate/sockets/config_port.py | Configuration access | Runtime config store |
| Message Port | substrate/sockets/message_port.py | Message dispatch | transports register at boot |
| Approval Port | substrate/sockets/approval_port.py | Approval flow management | transports/discord/approval_bridge.py |

### 5C. Domain Bridges

Substrate domain bridges translate raw projection signals into ontology-typed observations:

| Bridge | File | LOC | Source Projection |
|--------|------|-----|-------------------|
| Business domain | substrate/understanding/domains/business.py | ~500 | EOS signals |
| Creator domain | substrate/understanding/domains/creator.py | 516 | CreatorOS signals |
| Personal domain | substrate/understanding/domains/personal.py | (exists) | LyfeOS signals |

### 5D. Cross-Product Signal Flow Example

1. Creator sells a course in CreatorOS -> `creatoros_revenue_recorded` signal emitted
2. UMH pipeline processes signal through creator domain bridge
3. If creator also runs an EOS entity, revenue event triggers EOS capability (log_activity)
4. EOS Finance Agent sees new revenue data in morning briefing
5. Outcome written back to both CreatorOS (revenue confirmed) and EOS (activity logged)

**Status: Architecturally possible but NOT currently wired end-to-end.** Integration code exists in both projections. Cross-product routing logic in substrate has not been activated.

**Source: phase14_6b_creatoros_eos_boundary_canon.md Section 6**


## 6. Conflict Resolution

When two products could own the same capability, apply these resolution rules in order:

### 6A. The Litmus Test (from phase14_6b_creatoros_eos_boundary_canon.md Section 7)

1. "Does this serve the creator's product/audience/community?" -> **CreatorOS**
2. "Does this serve the operator's business structure/operations/intelligence?" -> **EOS**
3. "Does this serve the individual's personal life measurement/growth/reflection?" -> **LyfeOS**
4. "Does this serve both equally and is infrastructure-level?" -> **UMH substrate**
5. "Am I unsure?" -> **Flag as OPEN_QUESTION_OPERATOR_DECISION_REQUIRED**

### 6B. Known Contested Boundaries

| Contested Capability | Product A Claim | Product B Claim | Resolution Status |
|---------------------|----------------|----------------|-------------------|
| Team management for creator businesses | CreatorOS (creator platform feature, competitors have it) | EOS (team governance is business operations) | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED (OQ-1) |
| Analytics depth boundary | CreatorOS (content performance, creator revenue) | EOS (business intelligence, KPI anomaly detection, P&L) | Proposed: surface analytics = CreatorOS, deep BI = EOS. NEEDS_OPERATOR_APPROVAL (OQ-2) |
| Automation engine | CreatorOS (visual content/commerce triggers) | EOS (governed business workflows) | Proposed: separate systems or shared substrate with projection-specific registries. NEEDS_OPERATOR_APPROVAL (OQ-3) |
| Contact list vs CRM | CreatorOS (customer list, purchase history) | EOS (deals, stages, probability, pipeline forecasting) | Proposed: customer list = CreatorOS, sales pipeline = EOS. NEEDS_OPERATOR_APPROVAL (OQ-4) |
| Codebase strategy | Separate repos (current) | Monorepo with shared infrastructure (potential) | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED (OQ-5) |
| Account unification | One account (UMH platform identity implies this) | Two accounts (separate products) | Implied one-account via UMH platform layer. SSO not implemented. (OQ-6) |
| Financial tracking | CreatorOS (revenue tracking for creators) | EOS (full P&L, cash flow, unit economics) | De facto: CreatorOS = revenue surface, EOS = financial depth. Not formally ratified. |
| Notification system | Each product has its own | Shared UMH notification substrate | OPEN_QUESTION. Notification port exists (substrate/sockets/notification.py) but concrete routing per projection undefined. |
| LyfeOS quest creation governance | LyfeOS NOVA (executes create_vision_goal without approval) | UMH (should govern tool actions via risk classification) | INFERRED_PROFESSIONAL_GAP. No approval model on LyfeOS AI actions. |

### 6C. Resolution Principles

1. **No capability duplication.** If two products need the same underlying mechanism, it belongs in UMH substrate as an abstract port. Each product registers its projection-specific implementation.

2. **Projection-specific means projection-owned.** If the capability would be different for a different projection, it stays in the projection. If it would be identical, it moves to substrate.

3. **Cross-product communication flows through UMH.** Never peer-to-peer between projections. Signals go through the substrate pipeline. This is enforced by the architecture layer law (substrate/ never imports from projections/, projections/ never import from each other).

4. **Governance is always substrate-level.** Risk classification, approval flows, audit trails, and execution boundaries are UMH substrate concerns. No projection implements its own governance engine. If a projection's AI actions need governance (LyfeOS NOVA tool calls, CreatorOS automation triggers), they route through the substrate governance engine.

5. **Data isolation is physical.** Each projection has its own Neon PostgreSQL database. No cross-database queries. Cross-product data flows through UMH signal pipeline only. Sensitive data categories have hard exclusion boundaries.


## 7. Operator Review Questions

These questions require explicit operator decision before any implementation can proceed.

### 7A. Cross-Product Architecture

| # | Question | Impact | Entities Affected |
|---|----------|--------|-------------------|
| OQ-1 | Creator team management: CreatorOS feature or EOS requirement? | Determines whether CreatorOS builds role/permission system or requires EOS for teams. | CreatorOS, EOS |
| OQ-2 | Where does CreatorOS analytics end and EOS business intelligence begin? | Defines the depth boundary between creator analytics and business intelligence. | CreatorOS, EOS |
| OQ-3 | Separate automation engines or shared UMH automation substrate? | Determines whether to build two trigger/action DAG engines or one shared substrate with projection skins. | CreatorOS, EOS, UMH |
| OQ-4 | Where does "customer list" end and "CRM" begin? | Defines data ownership boundary for contacts/deals between the two products. | CreatorOS, EOS |
| OQ-5 | Separate repos or monorepo for EOS + CreatorOS SaaS layers? | Determines code organization, shared infrastructure strategy, CI/CD pipeline. | CreatorOS, EOS, UMH |
| OQ-6 | One unified account across all products or separate per-product accounts? | Determines SSO strategy, UMH platform identity model, data linking. | All |

### 7B. Data and Privacy

| # | Question | Impact | Entities Affected |
|---|----------|--------|-------------------|
| OQ-7 | What sensitive data filtering mechanism should signal emitters implement? | P0 gap. No filtering exists. LyfeOS health/therapy data could leak into UMH. | LyfeOS, UMH |
| OQ-8 | Should LyfeOS conversation history be accessible to UMH for cross-projection intelligence? | Determines whether NOVA conversations can inform EOS/CreatorOS agent intelligence. | LyfeOS, UMH |
| OQ-9 | Should dismissed knowledge preferences sync across projections? | Determines whether a LyfeOS knowledge dismissal affects CreatorOS/EOS AI behavior. | LyfeOS, UMH |
| OQ-10 | What data retention and right-to-deletion policy governs cross-product data? | Determines GDPR/privacy compliance framework. P1 gap. | All |

### 7C. Agent Governance

| # | Question | Impact | Entities Affected |
|---|----------|--------|-------------------|
| OQ-11 | Should LyfeOS NOVA tool actions (create goals, batch missions) require UMH governance approval? | Currently executes without any approval model. Risk: AI creates unwanted goals/missions. | LyfeOS, UMH |
| OQ-12 | When UMH integration activates, does NOVA's knowledge base move to UMH or stay in LyfeOS? | Determines whether the 16-domain knowledge base becomes substrate-level shared intelligence or stays projection-local. | LyfeOS, UMH |
| OQ-13 | Should CreatorOS visual automations route through UMH governance for risk classification? | Determines whether content/commerce triggers get the same governance treatment as EOS workflows. | CreatorOS, UMH |

### 7D. Execution Architecture

| # | Question | Impact | Entities Affected |
|---|----------|--------|-------------------|
| OQ-14 | Should the three execution paths (Gateway->CognitiveLoop, Substrate.execute()->Spine, Organism WorkPackets) be unified? | Determines execution architecture evolution. Options: keep separate per use case, merge governance/memory/tracing, or full unification. | UMH |
| OQ-15 | What is the activation sequence for cross-product signal routing? | Integration code exists in all projections but cross-product routing is not wired. Determines when to activate. | All |
| OQ-16 | Auth convergence priority: which product migrates to Clerk first? | CreatorOS auth is BROKEN (P0 security). EOS Beast branch already has Clerk. LyfeOS has working but legacy auth. | CreatorOS, EOS, LyfeOS |


## 8. Summary: Boundary Health Assessment

| Boundary | Health | Evidence |
|----------|--------|----------|
| UMH <-> Projections | HEALTHY | Architecture layer law enforced by pre-commit. Abstract ports defined. No substrate importing from projections. |
| EOS <-> CreatorOS | WELL-DEFINED | phase14_6b_creatoros_eos_boundary_canon.md documents 30+ capability assignments. 6 open questions remain. |
| EOS <-> LyfeOS | IMPLICIT | No formal boundary document exists. Assumed: EOS = business, LyfeOS = personal. No contested capabilities identified yet. |
| CreatorOS <-> LyfeOS | IMPLICIT | No formal boundary document exists. Assumed: CreatorOS = creator/audience, LyfeOS = personal life. Potential overlap: habit tracking for creators, life-work balance. |
| Cockpit <-> All | WELL-DEFINED | Cockpit is observation + control. Private. Operator-only. Never customer-facing. 276 endpoints serve all entities. |
| Data isolation | PARTIAL | Physical database separation exists. Signal-scoped access implemented. Sensitive data filtering NOT implemented (P0). |
| Agent boundaries | DEFINED BUT UNGOVERNED | EOS has full governance. CreatorOS and LyfeOS AI features have NO governance integration. Gap must close before UMH integration activates. |
| Auth convergence | CRITICAL GAP | Three products, three auth systems, one broken (CreatorOS). Target is Clerk for all. No migration has started. |
