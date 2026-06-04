---
phase: "14.6B-CreatorOS (revised 14.6F)"
status: "DRAFT"
operator_approved: false
allows_implementation: false
date: "2026-06-04"
provenance: "SYNTHESIZED_CANON"
description: "Definitive boundary document between CreatorOS and EntrepreneurOS — what each product owns, what crosses, what must not cross, and where UMH (Universal Meta Harness) substrate mediates"
sources:
  - "phase14_6b_creatoros_lossless_product_canon.md (CreatorOS master canon)"
  - "phase14_6b_eos_lossless_product_canon.md (EOS master canon)"
  - "phase14_6b_eos_umh_integration_architecture.md (EOS-UMH integration model)"
  - "phase14_6b_eos_agent_architecture_spec.json (EOS agent hierarchy)"
  - "phase14_6b_eos_data_ontology.json (EOS data model — 3 schema surfaces)"
  - "phase14_6b_creatoros_data_ontology.json (CreatorOS data model — 20 tables)"
  - "phase14_6b_creatoros_automation_ai_canon.json (CreatorOS AI and automation spec)"
  - "phase14_6b_eos_business_democratization_doctrine.json (EOS product identity)"
  - "CreatorOS_1NIZXMZR.json Tab 8 (platform kernel vision, layer architecture)"
  - "projections/eos/integration/ (EOS UMH integration code — signals, capabilities, outcomes)"
  - "projections/creatoros/integration/ (CreatorOS UMH integration code — 1,099 lines)"
  - "substrate/understanding/domains/creator.py (creator domain bridge — 516 lines)"
---


# CreatorOS / EOS Boundary Canon

This document defines the authoritative boundary between CreatorOS and EntrepreneurOS (EOS). Both are projections built on the Universal Meta Harness (UMH) — a reality-isomorphic intelligence harness whose core functional purpose is to build, maintain, and act through a reality-isomorphic approximation of reality (DEC-146C-001, DEC-146B-UMH-001, ratified 2026-06-04). Every boundary claim traces to a source artifact. Where boundaries are uncertain or contested, the document flags OPEN_QUESTION_OPERATOR_DECISION_REQUIRED rather than inventing a resolution.


## 1. Boundary Principle

```json
{
  "phase": "14.6B-CreatorOS",
  "status": "DRAFT",
  "operator_approved": false,
  "allows_implementation": false,
  "date": "2026-06-04",
  "provenance": "SYNTHESIZED_CANON",
  "description": "The foundational principle that separates CreatorOS from EOS — what each product IS and IS NOT"
}
```

**EOS is a business operations operating system.**
It structures, operates, optimizes, and scales economic activity. Its center of gravity is the operator running one or more businesses. EOS owns the org chart, the agent workforce, the workflow engine, the financial stack, the governance model, and the strategic command center. Its users are founders, operators, and teams managing businesses.

**CreatorOS is a creator product/distribution/community operating system.**
It is the command center for modern creators. Its center of gravity is a creator building an audience, distributing content, selling products, and managing communities. CreatorOS owns the content pipeline, the community platform, the course builder, the marketplace, the consumer feed, the UGC engine, the ads platform, and the automation builder. Its users are creators, consumers, UGC creators, and advertisers.

**The separation rule:** If a capability exists to help someone run a business (any business, any type), it belongs to EOS. If a capability exists to help a creator produce, distribute, monetize, or build community around content, it belongs to CreatorOS.

**The overlap acknowledgment:** Creators are entrepreneurs. Every CreatorOS user is, structurally, operating a business. The boundary is not about whether a creator "has a business" (they do) — it is about which product surface serves which concern. CreatorOS serves the creator's product and audience concerns. EOS serves the creator's operational and financial concerns. A creator who outgrows CreatorOS's built-in analytics and needs departmental workflows, agent delegation, and portfolio management graduates into EOS — or runs both.

**Source: phase14_6b_creatoros_lossless_product_canon.md Section 1 (center of gravity), phase14_6b_eos_lossless_product_canon.md Section 1 (center of gravity), CreatorOS_1NIZXMZR.json Tab 8 (layer architecture: EOS = Layer 2 Business Operations, CreatorOS = Layer 3 Distribution/Audience OS)**


## 2. Ownership Matrix

```json
{
  "phase": "14.6B-CreatorOS",
  "status": "DRAFT",
  "operator_approved": false,
  "allows_implementation": false,
  "date": "2026-06-04",
  "provenance": "SYNTHESIZED_CANON",
  "description": "Capability-by-capability ownership assignment across EOS, CreatorOS, and shared UMH substrate"
}
```

### Content and Distribution

| Capability | EOS | CreatorOS | UMH Substrate |
|---|---|---|---|
| Content creation/editing | - | OWNS | - |
| Cross-platform distribution | - | OWNS | - |
| Content calendar and scheduling | - | OWNS | - |
| Social feed (consumer experience) | - | OWNS | - |
| Stories (24h ephemeral) | - | OWNS | - |
| In-app video editing studio | - | OWNS | - |
| Live multistreaming | - | OWNS | - |
| Email/newsletter broadcasts | - | OWNS | - |
| Content analytics (views, engagement, reach) | - | OWNS | - |

### Community and Social

| Capability | EOS | CreatorOS | UMH Substrate |
|---|---|---|---|
| Branded community spaces (Discord-like) | - | OWNS | - |
| Community channels (text/voice/video) | - | OWNS | - |
| Community membership tiers and gating | - | OWNS | - |
| DM messaging and conversations | - | OWNS | - |
| Follower/following relationships | - | OWNS | - |
| Notifications (content, social, commerce) | - | OWNS | - |
| Moderation and trust/safety | - | OWNS | - |
| User reputation (XP/level system) | - | OWNS | - |

### Commerce and Products

| Capability | EOS | CreatorOS | UMH Substrate |
|---|---|---|---|
| Product listing and marketplace | - | OWNS | - |
| Course builder and course player | - | OWNS | - |
| Digital download delivery | - | OWNS | - |
| Subscription/membership management | - | OWNS | - |
| Checkout and payment processing | - | OWNS | - |
| Order fulfillment | - | OWNS | - |
| UGC campaign management | - | OWNS | - |
| Ads platform (self-serve) | - | OWNS | - |
| Revenue tracking (creator-level) | - | OWNS | - |
| Pricing and billing tiers (platform SaaS) | - | OWNS | - |

### Business Operations

| Capability | EOS | CreatorOS | UMH Substrate |
|---|---|---|---|
| Org chart generation and management | OWNS | - | - |
| Department and role management | OWNS | - | - |
| Workflow/SOP engine | OWNS | - | - |
| Task board and assignment | OWNS | - | - |
| KPI tracking and anomaly detection | OWNS | - | - |
| Financial dashboard (P&L, cash flow, unit economics) | OWNS | - | - |
| CRM (contacts, deals, pipeline) | OWNS | - | - |
| Portfolio and multi-entity management | OWNS | - | - |
| Capital allocation intelligence | OWNS | - | - |
| Business template library (UBOS) | OWNS | - | - |
| Morning briefing and next-best-actions | OWNS | - | - |
| Compliance and governance policies | OWNS | - | - |

### Automation and AI

| Capability | EOS | CreatorOS | UMH Substrate |
|---|---|---|---|
| Visual automation builder (Manychat-style) | - | OWNS | - |
| Creator AI agents (custom system prompts) | - | OWNS | - |
| Department agents (CEO, Sales, Finance, etc.) | OWNS | - | - |
| EA Agent (operator interface, triage, routing) | OWNS | - | - |
| Agent skill system (versioned, trust-scored) | OWNS | - | - |
| Agent delegation chain and escalation | OWNS | - | - |

### Shared Infrastructure (Universal Meta Harness Substrate)

UMH (Universal Meta Harness) is the reality-isomorphic intelligence harness that both projections register with (DEC-146C-001, DEC-146B-UMH-001). Clerk is the ratified production auth provider for all projections (DEC-146B-EOS-003, DEC-146B-COS-002).

| Capability | EOS | CreatorOS | UMH Substrate |
|---|---|---|---|
| Authentication provider (Clerk — ratified DEC-146B-EOS-003, DEC-146B-COS-002) | - | - | SHARED |
| Intelligence routing (model_router) | - | - | SHARED |
| Execution pipeline (8-stage spine) | - | - | SHARED |
| Governance engine (risk classification) | - | - | SHARED |
| Signal/capability/outcome protocol | - | - | SHARED |
| Memory and state management | - | - | SHARED |
| Ontology and knowledge graph | - | - | SHARED |
| Domain bridges | - | - | SHARED |
| Projection registration (sockets) | - | - | SHARED |
| Observability and trace recording | - | - | SHARED |
| Neon PostgreSQL hosting | - | - | SHARED |
| Deployment infrastructure (Docker, Fly) | - | - | SHARED |


## 3. Data Boundary

```json
{
  "phase": "14.6B-CreatorOS",
  "status": "DRAFT",
  "operator_approved": false,
  "allows_implementation": false,
  "date": "2026-06-04",
  "provenance": "CODE_RESOLVED_CURRENT_TRUTH",
  "description": "What data each product owns exclusively, and what is shared through the UMH substrate"
}
```

### CreatorOS-Owned Data (20 tables current, 30+ target)

CreatorOS owns all data that represents the creator's product, content, audience, and community experience. Currently implemented in shared/schema.ts via Drizzle ORM against Neon PostgreSQL.

| Data Domain | Current Tables | Target Tables (not yet implemented) |
|---|---|---|
| User identity | users | creator_accounts, businesses (creator business entity) |
| Content | posts, comments, tagged_users | scheduled_posts, content_calendar, content_templates |
| Social | followers, stories, saved_posts | bookmarks_v2 |
| Community | communities, channels, channel_messages | community_tiers, memberships, membership_gating |
| Messaging | conversations, conversation_participants, direct_messages | group_chats_v2 |
| Notifications | notifications | notification_preferences |
| Commerce | products, revenue, contacts | orders, entitlements, order_items, coupons, subscriptions |
| AI | ai_agents, ai_chats | (sufficient for current scope) |
| Documents | documents | (sufficient for current scope) |
| Automation | (none) | automation_flows, automation_runs, automation_run_steps |
| Courses | (none) | courses, modules, lessons, enrollments, progress |
| UGC | (none) | ugc_campaigns, ugc_applications, ugc_deliverables, ugc_payments |
| Ads | (none) | ad_campaigns, ad_groups, ad_creatives, ad_impressions |
| Email | (none) | email_lists, email_subscribers, email_campaigns, email_sends |
| Search | (none) | search_index (or external service) |

### EOS-Owned Data (Beast canonical codebase — DEC-146B-EOS-001)

EOS owns all data that represents the operator's business structure, operations, and intelligence. Beast branch is the canonical EOS codebase (DEC-146B-EOS-001, ratified 2026-06-04); GitHub main is stale/deprecated. Three schema surfaces exist (GitHub main [stale], Beast canonical, UMH platform layer).

| Data Domain | Current Tables | Notes |
|---|---|---|
| User identity | users (text PK, email, company fields) | Different schema from CreatorOS users |
| CRM | crm_contacts, crm_deals, crm_activities | Accessed by UMH via projections/eos/integration/ |
| Tasks | tasks | Workflow-generated task tracking |
| Agent actions | agent_actions | Agent execution audit trail |
| UMH outcomes | umh_outcomes | Audit table for pipeline outcome writeback |
| Financial | (Beast: revenue, expenses, cash_flow) | Not on GitHub main yet |
| Company/Entity | (Beast: companies, portfolios, departments) | Not on GitHub main yet |
| Roles | (Beast: roles, permissions, team_members) | Not on GitHub main yet |
| Workflows | (Beast: workflows, sops, workflow_runs) | Not on GitHub main yet |
| Onboarding | (Beast: onboarding_steps, onboarding_state) | Not on GitHub main yet |

### Shared Data (via UMH Substrate)

| Data | Owner | Access Pattern |
|---|---|---|
| UMH platform users | UMH (transports/api/http/db/schema.ts) | Both products authenticate against UMH user records |
| UMH platform orgs | UMH | Both products resolve org context |
| UMH platform portfolios | UMH | Both products can be portfolio members |
| Signal envelopes | UMH substrate | Both products emit signals into the pipeline |
| Execution traces | UMH substrate | Both products' signals produce traces |
| Governance decisions | UMH substrate | Both products' actions are risk-classified |
| Memory store | UMH substrate | Both products' agents share memory infrastructure |

### Data Isolation Rule

CreatorOS and EOS each have their own Neon PostgreSQL databases. No direct cross-database queries. Cross-product data flow occurs exclusively through UMH substrate signals, capabilities, and outcomes. The UMH platform layer (transports/api/http/db/) provides shared identity (users, orgs, portfolios) that both projections reference.

**Source: phase14_6b_creatoros_data_ontology.json (schema_surfaces), phase14_6b_eos_data_ontology.json (schema_surfaces), phase14_6b_eos_umh_integration_architecture.md (Section 1: integration model)**


## 4. Agent Boundary

```json
{
  "phase": "14.6B-EOS",
  "status": "DRAFT",
  "operator_approved": false,
  "allows_implementation": false,
  "date": "2026-06-04",
  "provenance": "SYNTHESIZED_CANON",
  "description": "How agent intelligence is distributed between EOS (full agent hierarchy) and CreatorOS (AI utilities)"
}
```

### EOS: Full Multi-Agent Hierarchy

EOS has a three-tier agent architecture designed for business operations:

| Tier | Agents | Purpose |
|---|---|---|
| Strategic | EA Agent, Portfolio Advisor | Operator interface, triage, portfolio-level intelligence, routing |
| Planning | CEO Agent | Entity-level strategy, department coordination, delegation, approval |
| Execution | Sales, Marketing, Finance, Customer Success, HR, Legal, Operations, Product, Engineering | Domain-specific skill execution within permission tier bounds |

Total: 12 agents (10 implemented in code, 2 defined as professional gaps). 62 skills across agents. Permission tiers: READ, DRAFT, EXECUTE, COMMIT. Delegation chain: Operator -> EA -> CEO -> Department -> CEO -> EA -> Operator.

**Source: phase14_6b_eos_agent_architecture_spec.json (agent_hierarchy)**

### CreatorOS: AI Utilities (Not an Agent Hierarchy)

CreatorOS has AI features, but they are user-facing utilities, not an autonomous agent workforce:

| Feature | Description | Implementation Status |
|---|---|---|
| Custom AI agents | Creator-defined chatbots with custom system prompts, sold as products | IMPLEMENTED (ai_agents, ai_chats tables; AgentCard, ChatInterface components; OpenAI SDK) |
| AI content assistant | (Desired) AI-powered content generation, caption writing, hashtag suggestions | NOT IMPLEMENTED |
| AI community moderation | (Desired) Auto-moderation, spam detection, content classification | NOT IMPLEMENTED |
| AI analytics insights | (Desired) Intelligent analytics summaries and recommendations | NOT IMPLEMENTED |

CreatorOS AI agents are products that creators build and sell to consumers. They are NOT operational agents that run the creator's business. The distinction: EOS agents manage operations autonomously within governance bounds. CreatorOS agents are content products.

### Boundary Rule

EOS agents operate ON businesses. CreatorOS AI agents are products OF creators. EOS agents have permission tiers, delegation chains, and escalation protocols. CreatorOS agents have system prompts, chat histories, and consumer-facing interfaces.

If a creator wants AI-assisted business operations (financial planning, workflow automation with governance, agent delegation), that capability lives in EOS. If a creator wants AI-powered content tools (writing assistants, chatbots for their audience), that capability lives in CreatorOS.


## 5. User Boundary

```json
{
  "phase": "14.6B-CreatorOS",
  "status": "DRAFT",
  "operator_approved": false,
  "allows_implementation": false,
  "date": "2026-06-04",
  "provenance": "SYNTHESIZED_CANON",
  "description": "Who uses each product — user segments, roles, and the crossover path"
}
```

### EOS Users

| Segment | Role | What They Do in EOS |
|---|---|---|
| Solo operators | Founder/CEO | Run one or more businesses with AI agent workforce |
| Founders | Founder/CEO | Structure and scale companies with org charts, workflows, KPIs |
| Serial entrepreneurs | Portfolio operator | Manage multiple ventures, cross-entity analytics, capital allocation |
| Small teams (2-20) | Team members | Role assignment, coordinated execution, governed delegation |
| Investment operators | Portfolio operator | Position tracking, due diligence, return metrics |
| Holding companies | Parent operator | Multi-entity governance, consolidated reporting |

### CreatorOS Users

| Segment | Role | What They Do in CreatorOS |
|---|---|---|
| Emerging creators (1K-50K) | Creator | Cross-posting, basic analytics, community start |
| Established creators (50K-500K) | Creator | Multi-platform distribution, courses, product sales, automation |
| Creator businesses (500K+) | Creator/team | White-label, API access, enterprise analytics, team permissions |
| Consumers (superfans) | Consumer | Unified feed, bookmarks, notifications, following |
| Consumers (learners) | Consumer | Course player, progress tracking, certificates |
| Consumers (community members) | Consumer | Community spaces, DMs, channels |
| UGC creators | UGC creator | Apply to campaigns, submit deliverables, receive payment |
| Advertisers | Advertiser | Create campaigns, set targeting and budgets, view metrics |

### Crossover Path

A creator who uses CreatorOS to build an audience and sell products may also use EOS to manage the operational side of their creator business. The two products serve different concerns for the same person:

- **In CreatorOS:** The creator posts content, manages their community, sells courses, runs UGC campaigns
- **In EOS:** The same person (as an operator) manages their creator business entity, tracks financials via the finance agent, delegates operational tasks, reviews KPIs, runs workflows

The shared UMH identity (via platform users/orgs) enables a single login across both products. The shared UMH substrate enables cross-product signals (e.g., a CreatorOS product sale triggers an EOS revenue event).


## 6. Integration Points (Where They Connect via UMH)

```json
{
  "phase": "14.6B-CreatorOS",
  "status": "DRAFT",
  "operator_approved": false,
  "allows_implementation": false,
  "date": "2026-06-04",
  "provenance": "CODE_RESOLVED_CURRENT_TRUTH",
  "description": "The specific UMH substrate mechanisms that allow EOS and CreatorOS to exchange data and trigger cross-product actions"
}
```

### Projection Registration

Both products register with UMH as projections via `substrate/sockets/projection_port.py`:

| Projection | Integration ID | Registration File |
|---|---|---|
| EOS | `"eos"` | projections/eos/integration/manifest.py |
| CreatorOS | `"creatoros"` | projections/creatoros/integration/manifest.py |

### Signal Exchange

Each product emits signals into the UMH execution pipeline. Signals from one product can be visible to the other through the substrate's signal routing.

| Signal Source | Signal Types | Risk Class | Pipeline Path |
|---|---|---|---|
| EOS | eos_contact_created, eos_deal_created, eos_activity_logged | READ_ONLY | EOS DB -> EOSPoller -> SignalEnvelope -> spine |
| CreatorOS | creatoros_product_created, creatoros_revenue_recorded, creatoros_user_registered | READ_ONLY (inferred) | CreatorOS DB -> CreatorOSPoller -> SignalEnvelope -> spine |

### Capability Exchange

Each product declares capabilities that the UMH execution pipeline can invoke:

| Product | Capabilities | Risk Class |
|---|---|---|
| EOS | noop, create_contact, create_deal, update_deal_stage, log_activity | READ_ONLY to EXTERNAL_COMMUNICATION |
| CreatorOS | (declared in manifest — product, revenue, user operations) | Per-capability |

### Outcome Writeback

Both products receive outcome notifications from the UMH pipeline:

| Product | Writeback Model | Persistence |
|---|---|---|
| EOS | Dual: source row update (umh_status) + audit table insert (umh_outcomes) | Correlation map in memory |
| CreatorOS | (same pattern as EOS — per projections/creatoros/integration/outcomes.py) | Correlation map in memory |

### Domain Bridge

The UMH substrate has domain bridges that translate raw signals into domain-typed observations:

| Domain Bridge | File | Lines | Purpose |
|---|---|---|---|
| Creator domain | substrate/understanding/domains/creator.py | 516 | Bridges CreatorOS signals into creator-domain ontology observations |
| Business domain | substrate/understanding/domains/business.py | (exists) | Bridges EOS signals into business-domain ontology observations |

### Cross-Product Flow Example

A concrete example of how the two products interact through UMH:

1. Creator sells a course in CreatorOS -> `creatoros_revenue_recorded` signal emitted
2. UMH pipeline processes the signal through the creator domain bridge
3. If the creator also runs an EOS entity, the revenue event can trigger an EOS capability (log_activity or update a financial record)
4. EOS Finance Agent sees the new revenue data in its morning briefing
5. Outcome written back to both CreatorOS (revenue confirmed) and EOS (activity logged)

This flow is architecturally possible but NOT currently wired end-to-end. The integration code exists in both projections, but the cross-product routing logic in the substrate has not been activated.

**Source: phase14_6b_eos_umh_integration_architecture.md (Sections 1-4), projections/creatoros/integration/ (1,099 lines), substrate/understanding/domains/creator.py (516 lines)**


## 7. What MUST NOT Cross

```json
{
  "phase": "14.6B-CreatorOS",
  "status": "DRAFT",
  "operator_approved": false,
  "allows_implementation": false,
  "date": "2026-06-04",
  "provenance": "SYNTHESIZED_CANON",
  "description": "Hard boundary violations — things that belong to one product and must never leak into the other"
}
```

### EOS Logic Must NOT Appear in CreatorOS

| Violation | Why It Is Wrong | Where It Belongs |
|---|---|---|
| Org chart generation in CreatorOS | CreatorOS does not structure businesses into departments | EOS Org Chart Engine (Module 2) |
| Department agents in CreatorOS | CreatorOS AI agents are products, not operational workers | EOS Agent Runtime (projections/eos/agents/) |
| Workflow/SOP engine in CreatorOS | CreatorOS has visual automations, not governed business workflows | EOS Workflow Engine (Module 5) |
| KPI anomaly detection in CreatorOS | CreatorOS has content analytics, not business metric intelligence | EOS KPI Module (Module 16) |
| Permission tiers (READ/DRAFT/EXECUTE/COMMIT) in CreatorOS | CreatorOS uses role-based access (creator/consumer), not tiered governance | EOS Governance Module (Module 13) |
| CRM deal pipeline in CreatorOS | CreatorOS has contacts (for creators), not sales pipeline management | EOS CRM (crm_contacts, crm_deals) |
| Portfolio/multi-entity management in CreatorOS | CreatorOS manages one creator business at a time, not portfolios | EOS Portfolio Module (Module 1) |
| Capital allocation in CreatorOS | CreatorOS tracks revenue; it does not allocate capital across entities | EOS Finance Module |

### CreatorOS Logic Must NOT Appear in EOS

| Violation | Why It Is Wrong | Where It Belongs |
|---|---|---|
| Content creation/posting in EOS | EOS operators publish through workflows, not social content editors | CreatorOS Content Distribution Hub (Module 1) |
| Social feed experience in EOS | EOS does not have a consumer content feed | CreatorOS Consumer Feed (Module 5) |
| Community hosting (Discord-like) in EOS | EOS team coordination is internal; community hosting is a creator product | CreatorOS Community Hub (Module 2) |
| Course builder in EOS | Courses are creator products, not business operations | CreatorOS Course Platform (Module 3) |
| Marketplace/product listing in EOS | EOS has entities and services, not a consumer marketplace | CreatorOS Marketplace (Module 4) |
| Stories (ephemeral content) in EOS | Ephemeral content is a creator/consumer feature | CreatorOS Stories System (Module 13) |
| UGC campaign management in EOS | UGC campaigns are creator-economy workflows, not business operations | CreatorOS UGC Campaigns (Module 8) |
| Ads platform in EOS | Self-serve advertising is a creator/advertiser feature | CreatorOS Ads Platform (Module 9) |
| Consumer follower/following in EOS | EOS users are operators, not social followers | CreatorOS social system |
| XP/level gamification in EOS | Gamification is a consumer engagement mechanism | CreatorOS user reputation system |

### The Litmus Test

Before adding any feature to either product, ask:

1. **"Does this serve the creator's product/audience/community?"** -> CreatorOS
2. **"Does this serve the operator's business structure/operations/intelligence?"** -> EOS
3. **"Does this serve both equally and is infrastructure-level?"** -> UMH substrate
4. **"Am I unsure?"** -> Flag as OPEN_QUESTION_OPERATOR_DECISION_REQUIRED


## 8. Shared Infrastructure

```json
{
  "phase": "14.6B-CreatorOS",
  "status": "DRAFT",
  "operator_approved": false,
  "allows_implementation": false,
  "date": "2026-06-04",
  "provenance": "CODE_RESOLVED_CURRENT_TRUTH",
  "description": "Infrastructure that both products share — the UMH substrate layer and deployment platform"
}
```

### Authentication

| Component | Current State | Target State |
|---|---|---|
| EOS auth | Passport.js + Firebase (GitHub main [stale]), Clerk (Beast canonical) | Clerk (ratified DEC-146B-EOS-003) |
| CreatorOS auth | Passport.js (BROKEN — comparePasswords returns true for ALL) | Clerk (ratified DEC-146B-COS-002) |
| UMH platform auth | JWT middleware in transports/api/http/ | Clerk SSO for all projections |

**P0 security note:** CreatorOS auth is fundamentally broken. The comparePasswords function in server/auth.ts returns true for every password combination. This is a critical vulnerability that must be fixed before any deployment. Clerk is ratified as the production auth provider for both products (DEC-146B-EOS-003, DEC-146B-COS-002). CreatorOS Clerk migration is CRITICAL and blocks ALL other implementation (DEC-146B-COS-002). Migration order: Clerk first, block all other work until auth complete (DEC-146B-COS-004, ratified 2026-06-04).

### Database

| Layer | Provider | Instance |
|---|---|---|
| EOS application | Neon PostgreSQL | EOS-specific project/database |
| CreatorOS application | Neon PostgreSQL | CreatorOS-specific project/database |
| UMH platform | Neon PostgreSQL | UMH platform database (users, orgs, portfolios) |

Both application databases are separate Neon instances. The UMH platform database is shared infrastructure that both projections reference for identity and organization context.

### Intelligence Routing

Both products use `adapters/models/model_router.py` for all AI calls. The routing chain (cc_sdk -> Gemini 2.5 Flash -> Groq -> Ollama) is shared. Strategic agents (EOS CEO, EA) use `agent_type='ceo'` for best-available model. CreatorOS AI agents use the standard routing chain.

### Execution Pipeline

Both products submit signals to the same `substrate/execution/spine.py` 8-stage pipeline. Both products' signals go through the same governance engine for risk classification. Both products receive outcomes through the same outcome notification mechanism.

### Deployment

| Product | Current Deployment | Target Deployment |
|---|---|---|
| EOS SaaS layer | Not deployed (Beast canonical branch, local only) | Fly.io (saas/ TypeScript app) — Fly.io is the Trinity standard (DEC-146B-LOS-003) |
| CreatorOS | Not deployed (GitHub main, local dev only) | Fly.io — Trinity standard (DEC-146B-LOS-003) |
| UMH substrate | Docker on VPS (os-discord, os-operator, os-webhook, os-scraper) | Docker on VPS (orchestration brain) |
| UMH cockpit | Fly.io (universalmetaharness.tech) | Fly.io |

### Code Organization

| Product | Code Location | Language |
|---|---|---|
| EOS projection | projections/eos/ (agents, integration, entities) | Python |
| EOS SaaS | saas/ (routes, schema, seed data, UI) | TypeScript/React |
| CreatorOS projection | projections/creatoros/integration/ | Python |
| CreatorOS app | antonyfmunoz/CreatorOS repo (296 files) | TypeScript/React |
| UMH substrate | substrate/ | Python |
| UMH adapters | adapters/ | Python |
| UMH transports | transports/ | Python + TypeScript |

### Design System Independence

Both products have independent design systems. They do NOT share UI components:

| Product | Design System | Aesthetic |
|---|---|---|
| EOS | Executive command center, finance-grade clarity, dark theme | Corporate precision |
| CreatorOS | X/Twitter-inspired minimalism, professional variant, light theme default | Clean, fast, functional |
| UMH Cockpit | WorldView system (wv-* classes), 240px LeftRail, visible borders | Operational dashboard |


## 9. Open Questions

```json
{
  "phase": "14.6B-CreatorOS",
  "status": "DRAFT",
  "operator_approved": false,
  "allows_implementation": false,
  "date": "2026-06-04",
  "provenance": "OPEN_QUESTION_OPERATOR_DECISION_REQUIRED",
  "description": "Boundary decisions that require operator input — no synthesized answer is authoritative"
}
```

### OQ-1: Creator Team Management — EOS or CreatorOS?

**Question:** Creator businesses (500K+ tier) need team management — roles, permissions, multi-user access. Does this belong in CreatorOS (as a creator platform feature) or does it require EOS (because team management is business operations)?

**Arguments for CreatorOS:** Creator businesses expect team features in their creator tool. Whop, Kajabi, and Teachable all have team management. Forcing creators into a separate product for basic team features creates friction.

**Arguments for EOS:** Team management with governance, permissions, and role hierarchy is exactly what EOS does. Duplicating this in CreatorOS violates the boundary principle.

**Current state:** CreatorOS has a single `role` field (creator/consumer). No team management exists. EOS has the full Role System (Module 3) with permission tiers.

### OQ-2: Creator Analytics Depth — Where Does CreatorOS End and EOS Begin?

**Question:** CreatorOS needs analytics (content performance, revenue tracking, audience growth). At what depth does analytics become "business intelligence" that belongs in EOS?

**Proposed boundary (needs operator approval):** CreatorOS owns surface-level creator analytics (views, engagement, revenue, follower growth, content performance). EOS owns deep business intelligence (P&L analysis, unit economics, cash flow forecasting, KPI anomaly detection, cross-entity comparison).

**Current state:** CreatorOS has a single revenue chart (pages/revenue.tsx). EOS has a desired Analytics/KPI module with anomaly detection (Module 16, NOT IMPLEMENTED).

### OQ-3: Automation Builder — CreatorOS-Only or Shared Engine?

**Question:** CreatorOS has a visual automation builder (Manychat-style). EOS has a workflow/SOP engine. Are these genuinely different systems, or should there be one shared automation substrate that both products skin differently?

**Arguments for separate:** Different scopes. CreatorOS automations are content/commerce triggers (new follower -> send DM, product purchase -> grant access). EOS workflows are business processes (new lead -> qualify -> proposal -> close, monthly -> generate P&L).

**Arguments for shared substrate:** Both are trigger/action DAGs. Building two separate engines is wasteful. A shared UMH automation substrate with projection-specific trigger/action registries would be more efficient.

**Current state:** Neither is implemented. No code exists for either system.

### OQ-4: CRM vs. Contacts — Boundary Line

**Question:** CreatorOS has a contacts table (contactName, contactImage, purchaseInfo). EOS has full CRM (crm_contacts, crm_deals, crm_activities with pipeline management). Where exactly does "creator's customer list" end and "CRM" begin?

**Proposed boundary (needs operator approval):** CreatorOS owns the customer list (who bought what, basic contact info, purchase history). EOS owns the sales pipeline (deals, stages, probability, activities, forecasting).

### OQ-5: Single Codebase or Separate Repos Long-Term?

**Question:** Both products are TypeScript/React + Neon PostgreSQL. Currently they live in separate GitHub repos (antonyfmunoz/CreatorOS, antonyfmunoz/entrepreneur-os). Should they converge into one monorepo with shared infrastructure, or stay separate?

**Current state:** Separate repos, no shared code, no shared components, no shared types. Both use Drizzle ORM. Both target Neon PostgreSQL. Both will target Clerk for auth. The UMH substrate (Python, /opt/OS) is a third repo that both connect to.

### OQ-6: Consumer Account Unification

**Question:** If a person is a consumer on CreatorOS (buying courses, following creators) and also an operator on EOS (running a business), do they have one account or two?

**Implied answer from UMH platform layer:** One account. The UMH platform database (transports/api/http/db/schema.ts) provides shared user identity. Both products authenticate against the same user record. But the actual SSO implementation does not exist yet.

**Source: All prior canon documents listed in sources header. Open questions derived from ambiguities identified during synthesis — no answer in existing source material resolves them definitively.**

---

*Revised in Phase 14.6F to align with 18 ratified P0 decisions (2026-06-04).*
