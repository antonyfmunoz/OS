---
phase: "14.6B-EOS (revised 14.6F)"
status: "DRAFT"
operator_approved: false
allows_implementation: false
date: "2026-06-04"
provenance: "CODE_RESOLVED_CURRENT_TRUTH"
description: "Side-by-side comparison of what exists in code vs what is specified in canon across all 19 desired-state modules and their sub-features, with discovered features, pure gaps, contradictions, and priority ordering for gap closure."
revision_provenance: "Revised in Phase 14.6F to align with 18 ratified P0 decisions (2026-06-04)."
---

# EOS Code vs Canon Gap Comparison

Side-by-side truth: what the canonical desired state specifies vs what actually
exists in code across three code surfaces (GitHub main, Beast feature/company-system,
UMH projection at projections/eos/).

Cross-references (not duplicated):
- `phase14_6b_eos_current_implementation_truth.json` -- code-level state
- `phase14_6b_eos_full_end_state_canon.json` -- complete desired state
- `phase14_6b_eos_professional_gap_register.md` -- 83 professional gaps
- `phase14_6b_eos_implementation_debt_register.md` -- tech debt inventory
- `phase14_6b_eos_source_detail_preservation_ledger.json` -- 120 preserved signals

---

## Gap Level Definitions

| Level | Meaning |
|-------|---------|
| COMPLETE | Code matches desired state in structure and behavior |
| PARTIAL | Some sub-features exist but significant gaps remain |
| STUB | Page/file/class exists but contains no real logic |
| MISSING | Zero code exists for this feature |
| CONTRADICTED | Code exists but implements something different from desired state |

---

## Module 1: Portfolio and Multi-Company Management

Desired state: Operator manages one or more Portfolios. Each Portfolio contains
Entities (businesses, investments, assets, holding structures). 8 entity types,
19 business types. Cross-entity metrics. Portfolio-level dashboard.

| Feature | Desired State | GitHub Main | Beast Branch | Projection Code | Gap Level |
|---------|--------------|-------------|--------------|-----------------|-----------|
| Portfolio CRUD | Create, read, update, delete portfolios with metadata | MISSING -- no portfolio concept | PARTIAL -- portfolio-list-page.tsx and portfolio-detail-page.tsx exist; company model present but portfolio-above-company layer absent | MISSING -- entity_model references departments/roles but no portfolio container | PARTIAL |
| Entity types (8) | operating_company, investment, asset, holding_company, trust, fund, real_estate, joint_venture | MISSING -- no entity type system | PARTIAL -- company model only; no investment/asset/trust/fund/real_estate/joint_venture types | PARTIAL -- entities.py defines departments, roles, dashboards, skill allocations but entity_type enum limited | PARTIAL |
| Business types (19) | SaaS, agency, e-commerce, consulting, coaching, content, services, retail, manufacturing, franchise, marketplace, fintech, healthtech, edtech, proptech, media, hospitality, logistics, non-profit | MISSING | MISSING -- company-setup-page.tsx has basic setup, no business type selection | MISSING | MISSING |
| Cross-entity metrics | Portfolio-level aggregated KPIs, entity comparison, capital allocation view | MISSING | MISSING | PARTIAL -- KPIView exists with revenue/leads/conversion but no cross-entity aggregation | MISSING |
| Portfolio dashboard | Consolidated view of all entities in a portfolio with health indicators | MISSING | STUB -- portfolio-detail-page.tsx exists, content unknown | MISSING | STUB |
| Company/entity switcher | Left Rail component to switch active entity context | MISSING | PARTIAL -- company guard component implies company switching | MISSING | PARTIAL |

---

## Module 2: Org Chart Engine

Desired state: AI-generated organizational structures based on business model and stage.
Visual org chart editor. Part of onboarding (steps 9-11). Department and role creation.

| Feature | Desired State | GitHub Main | Beast Branch | Projection Code | Gap Level |
|---------|--------------|-------------|--------------|-----------------|-----------|
| Org chart generation | AI generates org chart from business type + stage + team size | MISSING | MISSING -- org-chart-page.tsx exists but no generation logic | MISSING | STUB |
| Visual org chart editor | Interactive tree/graph editor for org structure | MISSING | STUB -- page exists, no editor component | MISSING | MISSING |
| Department CRUD | Create, edit, delete departments within an entity | MISSING | MISSING -- no department management in routes | PARTIAL -- entities.py defines 10 departments as Python data structures | PARTIAL |
| Role assignment | Assign humans and AI agents to roles within departments | MISSING | MISSING | PARTIAL -- DepartmentAgent base class has role concept, PermissionTier enum | PARTIAL |
| Stage-aware templates | Different org structures for startup/growth/scale/enterprise stages | MISSING | MISSING | MISSING | MISSING |

---

## Module 3: Role System

Desired state: First-class role objects supporting human and AI ownership.
Permission tiers (READ/DRAFT/EXECUTE/COMMIT). Entity-scoped. Approval authority.

| Feature | Desired State | GitHub Main | Beast Branch | Projection Code | Gap Level |
|---------|--------------|-------------|--------------|-----------------|-----------|
| Role CRUD | Create, edit, delete roles with permissions and scope | MISSING | MISSING -- no role management API | MISSING | MISSING |
| Permission tiers | READ, DRAFT, EXECUTE, COMMIT hierarchy | MISSING | MISSING | COMPLETE -- PermissionTier enum in substrate/types.py; DepartmentAgent enforces tier-gated skill execution | PARTIAL |
| Human + AI role assignment | Same role object can be owned by human user or AI agent | MISSING | MISSING | PARTIAL -- agents assigned department + tier; no shared role object model | PARTIAL |
| Entity-scoped permissions | Agent can only operate on assigned entities, not all in org | MISSING | MISSING | MISSING -- agents are org-wide, no entity scoping (GAP-AIA-003) | MISSING |
| Role UI | Role management screen with assignment, permissions, audit | MISSING | MISSING | N/A | MISSING |

---

## Module 4: Universal Dashboard Architecture

Desired state: Executive command center. 7-component shell: Header, Left Rail
(role-dependent nav, portfolio/entity switcher), Main Workspace, Right Rail AI,
Floating AI Panel, Risk/Approval Notices, Activity Feed. Finance-grade clarity.

| Feature | Desired State | GitHub Main | Beast Branch | Projection Code | Gap Level |
|---------|--------------|-------------|--------------|-----------------|-----------|
| Three-panel shell | Left Rail + Workspace + Right Rail | MISSING -- no layout system | PARTIAL -- universal-layout.tsx, left-rail.tsx, right-rail.tsx, header.tsx components exist | N/A | PARTIAL |
| Left Rail navigation | Role-dependent nav, portfolio/entity switcher, collapsible | MISSING | PARTIAL -- left-rail.tsx exists; role-dependent nav unknown | N/A | PARTIAL |
| Right Rail AI assistant | Contextual AI assistant with EA routing | MISSING | STUB -- right-rail.tsx exists, agent-chat-stub.tsx is placeholder | N/A | STUB |
| Floating AI panel | Always-accessible AI control surface | MISSING | PARTIAL -- floating-ai-panel.tsx exists | N/A | PARTIAL |
| Risk/approval notices | Inline risk notices, approval queue badges | MISSING | MISSING | N/A | MISSING |
| Activity feed | Real-time event feed of business activity | MISSING | MISSING | PARTIAL -- ActivityView in projections/eos/views/activity.py (93 lines) | PARTIAL |
| Finance-grade KPI cards | Monospace financials, sparklines, trend indicators, period comparison | MISSING | MISSING -- dashboard exists but not finance-grade | PARTIAL -- KPIView produces KPICard list with revenue, leads, conversion, outreach, response rate | MISSING |
| Dark mode (primary) | Dark mode as default, light mode toggle | MISSING | MISSING -- design tokens exist but dark mode not applied | N/A | MISSING |
| Design token system | Consistent spacing, typography, color from tokens | MISSING | PARTIAL -- design-tokens.ts and theme.json exist | N/A | PARTIAL |

---

## Module 5: Workflow and SOP Engine

Desired state: Full workflow engine with approval gates, retries, checkpoints, branching.
8 built-in workflows. SOP management. AI-generated workflows from onboarding.
Template library. Workflow run view.

| Feature | Desired State | GitHub Main | Beast Branch | Projection Code | Gap Level |
|---------|--------------|-------------|--------------|-----------------|-----------|
| Workflow data model | Steps, branches, approval gates, retries, checkpoints | MISSING | STUB -- workflows-page.tsx and workflows route exist | PARTIAL -- 3 workflows implemented (Outreach, FollowUp, ContentCalendar) with step arrays and deterministic-first pattern | PARTIAL |
| Workflow builder UI | Visual workflow creation/editing | MISSING | STUB -- workflows-page.tsx exists, no builder | N/A | STUB |
| Workflow run view | Live execution tracking with step progress | MISSING | MISSING | N/A | MISSING |
| 8 built-in workflows | Onboarding, outreach, follow-up, content, hiring, financial close, client onboarding, product launch | MISSING | MISSING | PARTIAL -- 3 of 8 implemented (outreach, follow-up, content calendar) | PARTIAL |
| SOP management | Create, version, link SOPs to workflows | MISSING | MISSING | MISSING | MISSING |
| SOP generation | AI generates SOPs during onboarding (step 13) | MISSING | MISSING | MISSING | MISSING |
| Approval gates | Workflow steps that pause for operator approval | MISSING | MISSING | PARTIAL -- substrate has GovernanceDecision/GovernanceVerdict; not wired to workflow steps in SaaS | PARTIAL |
| Template library (UBOS) | Browse, use, share workflow templates | MISSING | MISSING | MISSING | MISSING |

---

## Module 6: Skill System

Desired state: Reusable skills with versioning, trust scoring. Skills as building
blocks for agent capabilities. Skill marketplace for sharing.

| Feature | Desired State | GitHub Main | Beast Branch | Projection Code | Gap Level |
|---------|--------------|-------------|--------------|-----------------|-----------|
| Skill registration | Skills registered per agent with metadata | MISSING | MISSING | COMPLETE -- DepartmentAgent._add_skill() with permission tier enforcement; 62 skills across 10 agents | PARTIAL |
| Skill execution | Agent executes skills within permission bounds | MISSING | MISSING | COMPLETE -- tier-gated execution in DepartmentAgent base class | PARTIAL |
| Skill versioning | Version-tracked skill definitions | MISSING | MISSING | MISSING | MISSING |
| Trust scoring | Per-skill trust scores based on execution history | MISSING | MISSING | MISSING | MISSING |
| Skill marketplace | Buy/sell/share skills across operators | MISSING | MISSING | MISSING | MISSING |
| Browser skills | Browser research and browser act on every agent | MISSING | MISSING | COMPLETE -- base.py registers browser_research and browser_act on all agents | PARTIAL |

---

## Module 7: Agent Runtime

Desired state: Multi-agent system with EA -> CEO/Portfolio Advisor -> Department
routing chain. 10 department agents. Planner, skill router, tool executor per role.
UMH substrate integration.

| Feature | Desired State | GitHub Main | Beast Branch | Projection Code | Gap Level |
|---------|--------------|-------------|--------------|-----------------|-----------|
| EA Agent | Primary operator intake, triage, routing | MISSING | MISSING | MISSING -- architecturally required but not implemented (GAP-ARC-005) | MISSING |
| CEO Agent | Entity-level strategy, department delegation | MISSING | MISSING | PARTIAL -- CEOAgent exists with 6 skills; contains hardcoded instance context (GAP-AIA-002) | PARTIAL |
| 9 department agents | Sales, marketing, ops, finance, CS, HR, legal, product, engineering | MISSING | MISSING | COMPLETE -- all 10 (incl CEO) implemented with 62 total skills | PARTIAL |
| Portfolio Advisor | Cross-entity intelligence, capital allocation | MISSING | MISSING | MISSING | MISSING |
| Inter-agent routing | Message bus, delegation queue, routing logic | MISSING | MISSING | MISSING -- agents are standalone classes, no routing infra (GAP-AIA-001) | MISSING |
| Agent delegation chain | User -> EA -> CEO -> Department with escalation | MISSING | MISSING | MISSING -- direct invocation only, no chain | MISSING |
| Agent execution limits | Timeout, memory cap, output size limits | MISSING | MISSING | MISSING (GAP-AIA-004) | MISSING |
| Agent audit trail | Skill invocations logged with params, duration, cost | MISSING | MISSING | MISSING (GAP-AIA-005) | MISSING |
| 6 extended agents | Admin, research, content, automation, investment_analyst, asset_manager | MISSING | MISSING | MISSING | MISSING |

---

## Module 8: AI Compute and Model Routing

Desired state: Centralized gateway. Cost-aware model selection. Fallback chains.
Per-org budget limits. Agent cost tracking.

| Feature | Desired State | GitHub Main | Beast Branch | Projection Code | Gap Level |
|---------|--------------|-------------|--------------|-----------------|-----------|
| Centralized model routing | Single entry point for all LLM calls | PARTIAL -- 5 separate AI services (anthropic, openai, gemini, perplexity, xai) with no unified router | PARTIAL -- server/ai/gateway.ts exists as unified gateway | COMPLETE -- all agents route through adapters/models/model_router.py call_with_fallback() | PARTIAL |
| Fallback chain | Automatic fallback across providers on failure | MISSING | MISSING | COMPLETE -- cc_sdk -> Gemini 2.5 Flash -> Groq -> Ollama chain | PARTIAL |
| Cost tracking | Per-call, per-agent, per-org cost accounting | MISSING | MISSING | MISSING (GAP-AIA-006) | MISSING |
| Budget limits | Per-org monthly budget with alerting | MISSING | MISSING | MISSING | MISSING |
| Cost-aware selection | Route to cheaper models for simple tasks | MISSING | MISSING | PARTIAL -- TaskType.FAST_RESPONSE routes to Haiku; agent_type='ceo' forces best model | PARTIAL |

---

## Module 9: Memory and Knowledge Architecture

Desired state: Three-tier memory (working, session, long-term). Knowledge graph
with semantic retrieval. Business context persistence. Company-specific memory.

| Feature | Desired State | GitHub Main | Beast Branch | Projection Code | Gap Level |
|---------|--------------|-------------|--------------|-----------------|-----------|
| Three-tier memory | Working, session, long-term memory stores | MISSING | MISSING | PARTIAL -- UMH substrate has memory architecture in substrate/state/ | PARTIAL |
| Knowledge graph | Entity-relationship graph with semantic search | MISSING | MISSING | PARTIAL -- UMH has ontology system and embeddings table (vector(384)) | PARTIAL |
| Business context seeding | Onboarding seeds initial business memory | MISSING | MISSING | MISSING | MISSING |
| Company-specific memory | Per-entity isolated memory stores | MISSING | MISSING | MISSING | MISSING |
| Semantic retrieval | Vector similarity search across memory | MISSING | MISSING | PARTIAL -- embeddings table exists; dimension mismatch (384 vs 1536) unresolved (GAP-ARC-007) | PARTIAL |

---

## Module 10: Knowledge Graph

Desired state: Structured knowledge graph for business ontology. Entity relationships.
Semantic search. Graph-based intelligence.

| Feature | Desired State | GitHub Main | Beast Branch | Projection Code | Gap Level |
|---------|--------------|-------------|--------------|-----------------|-----------|
| Business ontology graph | Entities, relationships, attributes as graph nodes | MISSING | MISSING | PARTIAL -- substrate/ontology/ has laws, primitives, relationships | PARTIAL |
| Graph queries | Traverse business relationships, find dependencies | MISSING | MISSING | PARTIAL -- scripts/query_graph.py exists for codebase graph, not business graph | PARTIAL |
| Semantic search | Natural language queries against knowledge store | MISSING | MISSING | MISSING -- no EOS-specific semantic search | MISSING |

---

## Module 11: Human Intelligence Layer

Desired state: Rich contact profiles. Relationship intelligence. Interaction history.
Sentiment tracking. Contact-to-entity mapping.

| Feature | Desired State | GitHub Main | Beast Branch | Projection Code | Gap Level |
|---------|--------------|-------------|--------------|-----------------|-----------|
| Contact profiles | Rich contact records with metadata | PARTIAL -- CRM page with contact/deal management | MISSING -- crm route module exists but implementation unknown | MISSING | PARTIAL |
| Relationship intelligence | Automated relationship strength scoring | MISSING | MISSING | MISSING | MISSING |
| Interaction history | Timeline of all interactions per contact | MISSING | MISSING | MISSING | MISSING |
| Sentiment tracking | Positive/negative/neutral per interaction | MISSING | MISSING | MISSING | MISSING |

---

## Module 12: Reality Intelligence Engine

Desired state: Market research automation. Competitor monitoring. Trend detection.
External data pipeline for business intelligence.

| Feature | Desired State | GitHub Main | Beast Branch | Projection Code | Gap Level |
|---------|--------------|-------------|--------------|-----------------|-----------|
| Market research | Automated market sizing, opportunity identification | MISSING | MISSING | MISSING | MISSING |
| Competitor monitoring | Track competitor actions, pricing, features | MISSING | MISSING | MISSING | MISSING |
| Trend detection | Industry trend identification and alerting | MISSING | MISSING | MISSING | MISSING |
| External data pipeline | Ingest from public APIs, web scraping, RSS | MISSING | MISSING | MISSING | MISSING |

---

## Module 13: Governance and Permissions

Desired state: Hybrid RBAC+ABAC. 5 human permission tiers. Agent authority boundaries.
Approval gates. Audit trail. Configurable governance policies.

| Feature | Desired State | GitHub Main | Beast Branch | Projection Code | Gap Level |
|---------|--------------|-------------|--------------|-----------------|-----------|
| RBAC model | Role-based access with hierarchical roles | MISSING | MISSING | PARTIAL -- PermissionTier enum (READ/DRAFT/EXECUTE/COMMIT); agents assigned tiers | PARTIAL |
| ABAC model | Attribute-based policies (entity scope, time, risk) | MISSING | MISSING | MISSING | MISSING |
| Deterministic risk classification | Risk scoring for agent actions | MISSING | MISSING | COMPLETE -- substrate/control_plane/governance.py has deterministic risk classification | PARTIAL |
| Approval queue UI | Operator reviews and approves pending actions | MISSING | MISSING | MISSING (GAP-UIX-002) | MISSING |
| Governance audit trail | Every decision recorded with provenance | MISSING | MISSING | PARTIAL -- GovernanceEngine logs decisions; AuthorityEngine records approvals; no UI surface | PARTIAL |
| Configurable policies | Operator can adjust governance thresholds | MISSING | MISSING | MISSING | MISSING |

---

## Module 14: Resilience and Failure Architecture

Desired state: Circuit breakers. Saga compensation. Retry with backoff.
Graceful degradation. Error recovery.

| Feature | Desired State | GitHub Main | Beast Branch | Projection Code | Gap Level |
|---------|--------------|-------------|--------------|-----------------|-----------|
| Circuit breakers | Automatic failure detection and fallback | MISSING | MISSING | PARTIAL -- model_router has retry logic; no circuit breaker pattern | PARTIAL |
| Saga compensation | Multi-step rollback on failure | MISSING | MISSING | MISSING | MISSING |
| Retry with backoff | Exponential backoff on transient failures | MISSING | MISSING | PARTIAL -- call_with_fallback retries across providers | PARTIAL |
| Graceful degradation | System works with reduced capability when components fail | MISSING | MISSING | PARTIAL -- deterministic-first principle ensures AI-independent fallback | PARTIAL |

---

## Module 15: Cross-Platform Integration (CreatorOS + LyfeOS)

Desired state: Shared intelligence across EOS, CreatorOS, LyfeOS via UMH
abstract ports. Energy state from LyfeOS influences EOS scheduling.

| Feature | Desired State | GitHub Main | Beast Branch | Projection Code | Gap Level |
|---------|--------------|-------------|--------------|-----------------|-----------|
| UMH abstract port integration | EOS registers as projection on UMH | MISSING | MISSING | COMPLETE -- projections/eos/__init__.py registers via Substrate API | PARTIAL |
| CreatorOS bridge | Content creation intelligence shared | MISSING | MISSING | MISSING | MISSING |
| LyfeOS bridge | Personal energy/focus state feeds scheduling | MISSING | MISSING | MISSING | MISSING |
| Shared substrate capabilities | 15 UMH capabilities projected to business domain | MISSING | MISSING | PARTIAL -- uses substrate.execute, substrate.register, substrate.types | PARTIAL |

---

## Module 16: Founder Command Center

Desired state: Single view showing business health, AI activity, pending approvals,
next-best actions, active workflows, critical alerts. The "home screen" of EOS.

| Feature | Desired State | GitHub Main | Beast Branch | Projection Code | Gap Level |
|---------|--------------|-------------|--------------|-----------------|-----------|
| Command center page | Unified executive overview | MISSING | STUB -- command-center-page.tsx exists | MISSING | STUB |
| Business health indicators | Revenue, growth, burn, runway at a glance | MISSING | MISSING | PARTIAL -- KPIView produces revenue, leads, conversion metrics | PARTIAL |
| AI activity feed | Real-time agent actions and status | MISSING | MISSING | MISSING | MISSING |
| Pending approvals | Count and list of items awaiting operator decision | MISSING | MISSING | MISSING | MISSING |
| Next-best actions | AI-recommended priorities | MISSING | MISSING | MISSING | MISSING |
| Active workflow monitor | Currently running workflows with progress | MISSING | MISSING | MISSING | MISSING |

---

## Module 17: UBOS Template Engine

Desired state: Franchise-like business templates. Entity-type-aware.
Pre-configured org charts, workflows, KPIs, SOPs per business type.
Community and curated contributions.

| Feature | Desired State | GitHub Main | Beast Branch | Projection Code | Gap Level |
|---------|--------------|-------------|--------------|-----------------|-----------|
| Template library | Browse and apply business templates | MISSING | MISSING | MISSING | MISSING |
| Entity-type templates | Templates tailored to each of 19 business types | MISSING | MISSING | MISSING | MISSING |
| Template application | Apply template to generate org chart + workflows + KPIs + SOPs | MISSING | MISSING | MISSING | MISSING |
| Community contributions | Operators publish templates for others | MISSING | MISSING | MISSING | MISSING |
| Template quality gate | Review before listing | MISSING | MISSING | MISSING | MISSING |

---

## Module 18: Universal Business Primitives (16 categories)

Desired state: Reusable primitives across all entity types: revenue, expense,
customer, product, campaign, workflow, task, SOP, KPI, document, role, agent,
skill, integration, event, decision.

| Feature | Desired State | GitHub Main | Beast Branch | Projection Code | Gap Level |
|---------|--------------|-------------|--------------|-----------------|-----------|
| Primitive type system | 16 business primitive categories defined | MISSING | MISSING | PARTIAL -- substrate has PrimitiveType enum (10 types: state/change/constraint/resource/signal/action/outcome/feedback/goal/time) but these are ontology primitives, not business primitives | CONTRADICTED |
| Business-specific primitives | Revenue, expense, customer, product, campaign | MISSING | MISSING | MISSING -- ontology primitives are domain-agnostic | MISSING |
| Primitive CRUD | Create, query, relate primitives | MISSING | MISSING | PARTIAL -- substrate ingestion pipeline handles ontology observations | PARTIAL |

---

## Module 19: Self-Improvement Loop

Desired state: Pattern detection across business operations. Workflow refinement
suggestions. Optimization recommendations. Learning from outcomes.

| Feature | Desired State | GitHub Main | Beast Branch | Projection Code | Gap Level |
|---------|--------------|-------------|--------------|-----------------|-----------|
| Pattern detection | Identify recurring business patterns | MISSING | MISSING | PARTIAL -- substrate/execution/feedback.py has quality scoring and learning loop | PARTIAL |
| Workflow optimization | Suggest workflow improvements from execution data | MISSING | MISSING | MISSING | MISSING |
| Outcome learning | Track outcomes and feed back to agent behavior | MISSING | MISSING | PARTIAL -- substrate feedback loop architecture exists | PARTIAL |
| Optimization dashboard | Surface suggestions to operator | MISSING | MISSING | MISSING | MISSING |

---

## Additional Screens (from desired state: 11 screens)

| Screen | Desired State | GitHub Main | Beast Branch | Projection Code | Gap Level |
|--------|--------------|-------------|--------------|-----------------|-----------|
| Auth / Entry | Clerk auth, SSO, login/signup | CONTRADICTED -- Passport.js + Firebase | PARTIAL -- Clerk auth, login-page.tsx, signup-page.tsx, forgot-password-page.tsx | N/A | CONTRADICTED |
| Company Setup | Multi-step onboarding wizard (25 steps) | MISSING | STUB -- company-setup-page.tsx (single page, not 25-step wizard) | N/A | STUB |
| Home Dashboard | Executive KPI dashboard, finance-grade | PARTIAL -- agent-os-dashboard.tsx exists | PARTIAL -- dashboard-page.tsx + dashboard.tsx exist | N/A | PARTIAL |
| Company Settings/Profile | Entity configuration, metadata, integrations | MISSING | PARTIAL -- settings-page.tsx exists | N/A | PARTIAL |
| Department/Role Management | Org chart editor, role assignment | MISSING | STUB -- org-chart-page.tsx exists | N/A | STUB |
| Workflow Library | Browse, create, edit workflows | MISSING | STUB -- workflows-page.tsx exists | N/A | STUB |
| Workflow Run View | Live execution tracking | MISSING | MISSING | N/A | MISSING |
| Task Board/List | Kanban/list with assignment and workflow links | PARTIAL -- task-board-page.tsx with drag-and-drop | PARTIAL -- task-board-page.tsx + task-board-page-new.tsx | N/A | PARTIAL |
| AI Copilot Workspace | EA chat + context-aware AI assistance | PARTIAL -- agent-chat.tsx, gpt4o-chat-page.tsx | PARTIAL -- agent-chat-page.tsx + agent-chat-stub.tsx | N/A | PARTIAL |
| Docs/Notes Workspace | Document editor, SOP viewer, strategy notes | PARTIAL -- documents-page.tsx | PARTIAL -- documents-page.tsx | N/A | PARTIAL |
| Settings | API keys, preferences, integrations config | PARTIAL -- settings-page.tsx | PARTIAL -- settings-page.tsx | N/A | PARTIAL |

---

## Additional Workflows (from desired state: 8 workflows)

| Workflow | Desired State | GitHub Main | Beast Branch | Projection Code | Gap Level |
|----------|--------------|-------------|--------------|-----------------|-----------|
| Business setup | Create workspace, define company, AI-generate org | MISSING | STUB -- company-setup-page.tsx | MISSING | STUB |
| Daily dashboard | KPIs, alerts, next-best actions, active workflows | MISSING | MISSING | PARTIAL -- KPIView, PipelineView produce dashboard data | PARTIAL |
| Define org structure | Departments, roles, responsibilities | MISSING | STUB -- org-chart-page.tsx | PARTIAL -- entities.py defines 10 departments with roles | PARTIAL |
| Workflow/SOP management | Create, AI-generate, step through with AI | MISSING | STUB -- workflows-page.tsx | PARTIAL -- 3 workflows implemented with step arrays | PARTIAL |
| AI planning and drafting | Plans, documents, role defs, workflow drafts | MISSING | MISSING | PARTIAL -- agents have planning/drafting skills | PARTIAL |
| Task tracking | Create, assign, link to workflows, status dashboard | PARTIAL -- task-board-page.tsx | PARTIAL -- task-board-page.tsx | MISSING | PARTIAL |
| Business context persistence | Memory stores company context, preferences | MISSING | MISSING | PARTIAL -- UMH substrate memory architecture | PARTIAL |
| Metrics and next-best actions | KPI cards, AI recommendations, portfolio views | MISSING | MISSING | PARTIAL -- KPIView produces metrics; no AI recommendations | PARTIAL |

---

## Section 1: Discovered Features (Exist in Code, NOT in Desired State)

Features that exist in one or more code surfaces but were not specified in the
19-module desired state canon. These represent either organic development that
outpaced specification, or features from the Replit Agent era that were never
formally canonized.

| Feature | Code Location | Description | Disposition |
|---------|--------------|-------------|-------------|
| CRM page | GitHub main: crm-page.tsx | Contact and deal management with pipeline view | ADOPT -- aligns with Human Intelligence Layer (Module 11) but was built before module was specified |
| Agent programming interface | GitHub main: agent-programming.tsx | UI for programming agent behavior | EVALUATE -- may conflict with skill system approach |
| 5 separate AI services | GitHub main: server/ai/ (anthropic, openai, gemini, perplexity, xai) | Individual provider wrappers with no unified router | SUPERSEDED -- model_router.py in UMH projection replaces this pattern |
| Gmail integration | GitHub main: server/integrations/gmail.ts | OAuth Gmail connector | ADOPT -- first integration for Integration Marketplace (Module 15 end-state) |
| Firebase auth with MFA | GitHub main | Google OAuth + multi-factor authentication | SUPERSEDED -- Clerk auth replaces Firebase (ratified DEC-146B-EOS-003, 2026-06-04) |
| Tutorials page | GitHub main + Beast: tutorials-page.tsx | User tutorials/guides | EVALUATE -- not in desired state; may serve onboarding needs |
| Support page | GitHub main + Beast: support-page.tsx | Support/help interface | ADOPT -- standard SaaS requirement, not formally specified |
| Notifications page | GitHub main + Beast: notifications-page.tsx | Notification center | ADOPT -- aligns with Activity Feed in shell architecture |
| Admin dashboard | Beast: admin-dashboard-page.tsx | Admin-specific dashboard | EVALUATE -- may conflict with single Founder Command Center model |
| Generated code layer | Beast: server/generated/ (21 storage modules) | Auto-generated backend modules | AUDIT -- 21 storage modules may contain duplicated logic (GAP-ARC-002) |
| PostHog analytics | Beast: integrated in frontend | Product analytics tracking | ADOPT -- complements KPI Framework (Module 8 end-state); different concern (product analytics vs business analytics) |
| Company guard component | Beast: company-guard | Prevents access without active company | ADOPT -- aligns with entity context requirement |
| Actions route module | Beast: server/routes/actions.ts | Actions API endpoint | EVALUATE -- not mapped to any desired state module |
| Conversations route module | Beast: server/routes/conversations.ts | Conversations API | ADOPT -- needed for EA chat and agent communication |
| PipelineView | projections/eos/views/pipeline.py | 6-stage CRM pipeline with qualification | ADOPT -- aligns with sales agent capabilities and CRM needs |
| ContentCalendarWorkflow | projections/eos/workflows/content.py | Multi-channel content planning | ADOPT -- one of 8 built-in workflows, already specified |
| FollowUpWorkflow | projections/eos/workflows/followup.py | Automated follow-up sequences | ADOPT -- one of 8 built-in workflows, already specified |
| EOS integration layer | projections/eos/integration/ | manifest.py, correlation.py, registration for UMH | ADOPT -- critical wiring for UMH substrate integration |

---

## Section 2: Pure Gaps (Desired State with NO Code)

Features fully specified in canon with zero implementation across all three
code surfaces. These represent the largest implementation effort.

| Module | Feature | Desired State Artifact | Impact |
|--------|---------|----------------------|--------|
| 1 | Business types (19 types) | portfolio_entity_business_ontology.json | CRITICAL -- entity-type-aware generation depends on this |
| 1 | Cross-entity metrics | analytics_kpi_spec.json | HIGH -- portfolio value proposition |
| 2 | Org chart AI generation | onboarding_first_boot_spec.json (steps 9-11) | HIGH -- onboarding dependency |
| 2 | Visual org chart editor | onboarding_first_boot_spec.json | HIGH -- ongoing entity management |
| 2 | Stage-aware templates | portfolio_entity_business_ontology.json | MEDIUM -- improves generation quality |
| 3 | Role CRUD | governance_permissions_model.json | HIGH -- permission system foundation |
| 3 | Role management UI | governance_permissions_model.json | HIGH -- operator needs to manage roles |
| 5 | SOP management (full) | workflow_sop_engine_spec.json | HIGH -- operational backbone |
| 5 | SOP AI generation | onboarding_first_boot_spec.json (step 13) | HIGH -- onboarding dependency |
| 5 | Workflow run view | workflow_sop_engine_spec.json | HIGH -- operator visibility into execution |
| 5 | UBOS template library | workflow_sop_engine_spec.json | MEDIUM -- growth-phase |
| 7 | EA Agent | communication_delegation_architecture.json | CRITICAL -- corrected routing chain requires this |
| 7 | Inter-agent routing | communication_delegation_architecture.json | CRITICAL -- agents cannot delegate without this |
| 7 | Agent delegation chain | communication_delegation_architecture.json | CRITICAL -- operator-mandated architecture |
| 7 | Portfolio Advisor Agent | communication_delegation_architecture.json | MEDIUM -- multi-portfolio management |
| 8 | Cost tracking + budgets | analytics_kpi_spec.json | HIGH -- unbounded AI spend risk |
| 12 | Reality Intelligence Engine (full) | full_end_state_canon.json | LOW -- explicitly excluded from MVP |
| 13 | ABAC model | governance_permissions_model.json | MEDIUM -- needed for multi-entity scoping |
| 13 | Approval queue UI | governance_permissions_model.json | HIGH -- governance without UI is invisible |
| 16 | Command center (full) | full_end_state_canon.json | HIGH -- primary operator screen |
| 17 | UBOS Template Engine (full) | full_end_state_canon.json | MEDIUM -- growth-phase |
| 18 | Business-specific primitives | full_end_state_canon.json | MEDIUM -- 16 categories vs 10 ontology types |
| 19 | Workflow optimization suggestions | full_end_state_canon.json | LOW -- growth-phase |

---

## Section 3: Features with Contradictory Implementations

Features where code exists but contradicts the desired state specification.

| Feature | Desired State | Actual Implementation | Contradiction | Resolution |
|---------|--------------|----------------------|---------------|------------|
| Authentication | Clerk auth (Beast canonical) | GitHub main has Passport.js + Firebase; Beast has Clerk | Two incompatible auth systems. GitHub main is stale but represents prior investment. | Beast is the canonical codebase (DEC-146B-EOS-001). Clerk is ratified auth (DEC-146B-EOS-003). Passport.js + Firebase are deprecated. |
| AI model routing | Single centralized gateway (model_router.py) | GitHub main has 5 separate provider services (no router); Beast has server/ai/gateway.ts; Projection uses model_router.py | Three different routing architectures across code surfaces. | model_router.py (UMH substrate) is canonical. Beast gateway.ts needs to call UMH, not implement its own. GitHub main services are obsolete. |
| Business primitives | 16 business-specific categories (revenue, expense, customer, etc.) | Substrate has 10 ontology primitives (state, change, constraint, resource, signal, action, outcome, feedback, goal, time) | Ontology primitives are domain-agnostic; business primitives are domain-specific. These are different layers, not alternatives. | Both are needed. Ontology primitives live in substrate. Business primitives should be an EOS projection of ontology primitives (domain bridge pattern). |
| Entity model | 8 entity types with 19 business sub-types | Beast has single "company" model; GitHub main has no entity concept | Company model is a subset of entity model. "Company" conflates operating_company with all entity types. | Rename "company" to "entity" or "operating_company". Add entity_type discriminator. Schema migration required. |
| Agent invocation | EA -> CEO -> Department delegation chain | All 10 agents callable directly, no routing | Direct invocation bypasses governance, triage, and escalation. | Implement EA Agent as mandatory entry point. Lock direct department agent invocation to internal-only (from CEO/EA). |
| Org chart | AI-generated from business type + stage | Beast has org-chart-page.tsx (empty page); Projection has static department definitions | Static departments hardcoded in entities.py (10 departments) vs dynamic AI-generated structure per business type | Projection departments are defaults/templates. Generation engine should produce customized structures. Static list is seed data, not final architecture. |
| Dashboard | Finance-grade executive command center | GitHub main has basic agent-os-dashboard.tsx; Beast has dashboard-page.tsx; Projection has KPIView | None achieve finance-grade aesthetic or executive command center density specified in UI/UX canon | All three are starting points. Must converge on single dashboard implementing design token system from ui_ux_aesthetic_canon.json. |

---

## Section 4: Priority Ordering for Gap Closure

Ordered by deployment dependency and business impact.

### P0: Deployment Blockers (Must resolve before ANY production deployment)

| Priority | Gap | Module | Rationale |
|----------|-----|--------|-----------|
| P0.1 | Beast branch merge to main (canonical codebase per DEC-146B-EOS-001) | Architecture | 401-file divergence blocks everything. Single codebase required. RESOLVED: Beast is canonical. |
| P0.2 | Auth -- Clerk integration validated (ratified per DEC-146B-EOS-003) | Auth | Cannot deploy without working authentication. RESOLVED: Clerk is production auth. |
| P0.3 | RLS bypass fix (DATABASE_APP_URL) | Security | Multi-tenant data leak if env var missing. |
| P0.4 | Schema unification | Data | Three schema surfaces must converge to one. |
| P0.5 | Rate limiting | Security | AI endpoints without limits = unbounded cost exposure. |
| P0.6 | CI/CD pipeline | Infrastructure | Cannot deploy without automated build/test/deploy. |
| P0.7 | Health check endpoints | Infrastructure | Fly.io requires health probes for deployment. |

### P1: MVP Core (R1 -- Core Shell + Auth + Entity + Dashboard)

| Priority | Gap | Module | Rationale |
|----------|-----|--------|-----------|
| P1.1 | Entity type system (8 types, 19 business types) | Module 1 | Foundation for entity-type-aware everything. |
| P1.2 | Portfolio CRUD | Module 1 | Container for entities. Hierarchy root. |
| P1.3 | Three-panel shell with dark mode | Module 4 | Every screen lives inside the shell. |
| P1.4 | Finance-grade dashboard | Module 16 | First thing operator sees after login. |
| P1.5 | Entity switcher in Left Rail | Module 1 | Context switching is core UX pattern. |
| P1.6 | Design token application | Module 4 | Consistent aesthetic across all screens. |

### P2: MVP Core (R2 -- Tasks + Roles)

| Priority | Gap | Module | Rationale |
|----------|-----|--------|-----------|
| P2.1 | Role CRUD + permission tiers | Module 3 | Agent governance depends on roles. |
| P2.2 | Entity-scoped permissions | Module 3 | Multi-entity requires scoping. |
| P2.3 | Task management (board + list) | Module 5 | Operational backbone for daily work. |
| P2.4 | Department management UI | Module 2 | Operators need to configure their org. |

### P3: MVP Core (R3 -- Workflows + SOPs + Governance)

| Priority | Gap | Module | Rationale |
|----------|-----|--------|-----------|
| P3.1 | Workflow builder UI | Module 5 | Operators create custom workflows. |
| P3.2 | Workflow run view | Module 5 | Operators see execution progress. |
| P3.3 | SOP management | Module 5 | SOPs link to workflow steps. |
| P3.4 | Remaining 5 built-in workflows | Module 5 | Complete the 8-workflow set. |
| P3.5 | Approval queue UI | Module 13 | Governance needs a user surface. |

### P4: MVP Core (R4 -- AI Agents + Routing)

| Priority | Gap | Module | Rationale |
|----------|-----|--------|-----------|
| P4.1 | EA Agent implementation | Module 7 | Mandatory operator intake point. |
| P4.2 | Inter-agent routing infrastructure | Module 7 | EA -> CEO -> Department chain. |
| P4.3 | Agent delegation chain | Module 7 | Enforces corrected communication architecture. |
| P4.4 | CEO Agent instance context cleanup | Module 7 | Remove hardcoded values. |
| P4.5 | Right Rail AI with EA integration | Module 4 | Conversational surface for agent system. |
| P4.6 | Agent cost tracking | Module 8 | Visibility into AI spend. |

### P5: MVP Core (R5 -- Docs + Memory + Onboarding)

| Priority | Gap | Module | Rationale |
|----------|-----|--------|-----------|
| P5.1 | Documents workspace | Module 4 | SOPs, strategy notes need a surface. |
| P5.2 | Business context seeding | Module 9 | Onboarding writes to memory. |
| P5.3 | 25-step onboarding flow | Module 2 | Generate-first UX is core differentiator. |
| P5.4 | Org chart AI generation | Module 2 | Onboarding step 9. |
| P5.5 | SOP AI generation | Module 5 | Onboarding step 13. |

### P6: Growth Phase (Post-MVP)

| Priority | Gap | Module | Rationale |
|----------|-----|--------|-----------|
| P6.1 | Portfolio Advisor Agent | Module 7 | Multi-portfolio intelligence. |
| P6.2 | 6 extended department agents | Module 7 | Investment, asset, property management. |
| P6.3 | UBOS Template Library | Module 17 | Franchise-like scaling. |
| P6.4 | Skill marketplace | Module 6 | Network effects. |
| P6.5 | Integration marketplace | Module 15 | External tool connections. |
| P6.6 | Human Intelligence Layer | Module 11 | Rich contact profiles. |
| P6.7 | Reality Intelligence Engine | Module 12 | Market research automation. |
| P6.8 | Self-improvement loop | Module 19 | Optimization suggestions. |
| P6.9 | Command palette / keyboard shortcuts | Module 4 | Power user UX. |
| P6.10 | Autonomous agent execution | Module 7 | Agents act within bounds without per-action approval. |

### P7: Enterprise + Platform (Long-term)

| Priority | Gap | Module | Rationale |
|----------|-----|--------|-----------|
| P7.1 | Multi-tenant architecture | Enterprise | Tenant isolation at scale. |
| P7.2 | Enterprise SSO (SAML/OIDC) | Enterprise | Enterprise sales requirement. |
| P7.3 | Compliance suite | Enterprise | SOC 2, GDPR, HIPAA-readiness. |
| P7.4 | Public API | Platform | Third-party ecosystem. |
| P7.5 | White-label program | Platform | Agency/consultant channel. |
| P7.6 | Cross-platform bridges (CreatorOS/LyfeOS) | Module 15 | Trinity integration. |
| P7.7 | Mobile app | Platform | Mobile operator access. |

---

## Summary Statistics

| Metric | Count |
|--------|-------|
| Total desired-state modules | 19 |
| Modules with COMPLETE gap level on any feature | 0 |
| Modules with at least PARTIAL implementation | 14 |
| Modules with MISSING across all code surfaces | 5 (Reality Intelligence, UBOS Templates, Business Primitives domain layer, Self-Improvement dashboard, Cross-Platform bridges) |
| Total sub-features assessed | 124 |
| Sub-features at COMPLETE | 6 (all in UMH projection: skill registration, skill execution, browser skills, deterministic risk classification, model routing, UMH port registration) |
| Sub-features at PARTIAL | 49 |
| Sub-features at STUB | 10 |
| Sub-features at MISSING | 56 |
| Sub-features at CONTRADICTED | 3 |
| Discovered features (in code, not in canon) | 18 |
| Features with contradictory implementations | 7 |
| Total professional gaps (from gap register) | 83 |
| Deployment-blocking gaps | 16 |
| P0 blockers before any deployment | 7 |
| MVP releases to feature-complete | 5 (R1-R5) |

---

## Open Questions Requiring Operator Decision

These gaps cannot be resolved by engineering alone.

| ID | Question | Impact |
|----|----------|--------|
| OQ-GAP-001 | ~~Should Beast branch be promoted as-is, or should specific files be cherry-picked?~~ | RESOLVED: Beast is the canonical codebase per DEC-146B-EOS-001 (ratified 2026-06-04, Phase 14.6C). Promote as-is. |
| OQ-GAP-002 | Python-TypeScript bridge architecture: HTTP API, shared DB, or event-driven? | Determines how EOS SaaS calls UMH substrate |
| OQ-GAP-003 | Embedding dimension: 384 (local models) or 1536 (OpenAI)? | Affects semantic search quality and cost |
| OQ-GAP-004 | Should department agents be per-entity or shared with entity context? | Memory isolation vs resource efficiency |
| OQ-GAP-005 | What is the single production domain for EOS SaaS? | DNS, SSL, CORS, Clerk redirect configuration |
| OQ-GAP-006 | Should generated code (server/generated/) from Beast be kept or replaced? | 21 storage modules need audit vs rebuild decision |
| OQ-GAP-007 | Mobile: responsive web only, or native app roadmap? | Development cost vs user expectations |
