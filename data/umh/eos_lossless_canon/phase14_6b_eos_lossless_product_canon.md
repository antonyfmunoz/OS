---
phase: "14.6B-EOS (revised 14.6F)"
status: "DRAFT"
operator_approved: false
allows_implementation: false
date: "2026-06-04"
provenance: "SYNTHESIZED_CANON"
description: "Master EOS product canon — single coherent product truth document synthesizing all source inputs, operator corrections, code-resolved truth, and professional gap analysis into the definitive product reference."
revision_note: "Revised in Phase 14.6F to align with 18 ratified P0 decisions (2026-06-04)."
---

# EntrepreneurOS (EOS) — Master Product Canon

This document is the single source of product truth for EntrepreneurOS.
Every claim traces to a source. Every section carries a provenance label.
No implementation is authorized from this document — it is analysis only.

Existing artifacts referenced but NOT duplicated:

1. `phase14_6b_eos_preflight.json` — source inventory, success criteria, rules
2. `phase14_6b_eos_business_democratization_doctrine.json` — product identity, UMH mapping
3. `phase14_6b_eos_portfolio_entity_business_ontology.json` — hierarchy, entity types, business types
4. `phase14_6b_eos_communication_delegation_architecture.json` — routing chain, agent inventory, delegation protocol
5. `phase14_6b_eos_onboarding_first_boot_spec.json` — 25-step onboarding flow
6. `phase14_6b_eos_ui_ux_aesthetic_canon.json` — design direction, tokens, layout
7. `phase14_6b_eos_source_detail_preservation_ledger.json` — 120-signal lossless accounting

---

## 1. Product Identity

**Provenance: SOURCE_PRESERVED_TRUTH (operator corrections) + SYNTHESIZED_CANON**

| Field | Value |
|---|---|
| Product name | EntrepreneurOS (EOS) |
| Owner | OST (the technology/platform company) |
| NOT owned by | Lyfe Institute (which is a venture managed INSIDE EOS) |
| One-line | Business-in-a-box operating system that democratizes the ability to structure, operate, optimize, and scale economic activity |
| Product promise | The AI-assisted company command center — a cognitive operating system for business execution that lets operators run multiple businesses from anywhere in a few focused hours per day |
| Vision | To build the world's first truly AI-native operating system for entrepreneurs: a platform that structures companies, guides founders, deploys agentic labor, manages workflows, learns continuously, and helps humans operate at a world-class level regardless of prior experience |
| Center of gravity | Economic activity democratization — any operator, from solo founder to institutional holding company, gets enterprise-grade operational infrastructure |
| Relationship to UMH | EOS is a projection built on the Universal Meta Harness (UMH) substrate — a reality-isomorphic intelligence harness (DEC-146C-001). UMH provides universal mechanisms for modeling and acting through reality; EOS applies them to business operations. EOS registers with UMH at runtime via abstract ports. |
| Relationship to Trinity | EOS is one of three products (EOS, CreatorOS, LyfeOS) that share the UMH substrate and OS Platform Standard but each have distinct identity, aesthetic, and domain |
| Aesthetic metaphor | Executive command center / business cockpit / finance-grade clarity |
| Scale range | Solo operator to institutional holding company |

### Ownership clarification

Prior documentation (including some Phase 14.3A and 14.4 artifacts) incorrectly attributed EOS ownership to Lyfe Institute. This was corrected by the operator in the Phase 14.6B mission brief. The correct ownership chain:

- **OST** owns EntrepreneurOS as a product
- **Lyfe Institute** is a company/venture incubated through Empyrean Studios
- **Lyfe Institute** is managed inside EOS as one of many entities an operator can run on the platform
- Lyfe Institute is a customer of EOS, not its owner

**Source: SRC-OPERATOR-CORRECTIONS (Phase 14.6B mission brief)**

---

## 2. Target Users

**Provenance: SOURCE_PRESERVED_TRUTH (operator corrections) + SYNTHESIZED_CANON (14.4 desired state)**

### Primary users

| Segment | Description | Operational profile |
|---|---|---|
| Solo operators | Individual founders running one or more businesses without dedicated operations staff | Need AI agents to fill every operational role. Maximum automation. Minimum governance overhead. |
| Founders | Startup and SMB founders who need to structure and scale their companies | Need org chart, role generation, workflow engine, KPI tracking from day one. |
| Serial entrepreneurs | Operators managing multiple ventures across different industries | Need portfolio-level view, cross-entity analytics, capital allocation intelligence. |

### Secondary users

| Segment | Description | Operational profile |
|---|---|---|
| Small teams (2-20) | Teams that need enterprise-grade operational structure without enterprise overhead | Need role assignment, team coordination, governed delegation, department formation. |
| Investment operators | Active investors who operate their investments rather than passively hold them | Need position tracking, return metrics, due diligence workflows, portfolio analytics. |
| Holding companies | Operators managing multiple subsidiary entities under a parent structure | Need multi-entity governance, consolidated reporting, capital allocation across subsidiaries. |

### Future users

| Segment | Description | When |
|---|---|---|
| Family offices | Multi-generational wealth management with diversified portfolios | Post-MVP when multi-portfolio + governance is mature |
| Private equity operators | PE firms that acquire, optimize, and scale portfolio companies | Post-MVP when entity lifecycle management is complete |
| Institutional operators | Large-scale portfolio management with compliance and governance requirements | End-state when enterprise permissions, audit trails, and multi-region are complete |
| Enterprise teams | Department-scale deployment within larger organizations | End-state with enterprise SSO, admin controls, and seat management |

**Source: SRC-PHASE-14_4 (target_users), SRC-OPERATOR-CORRECTIONS (entity breadth correction), SRC-14.6B-BIZ (target_users array)**

---

## 3. Product Architecture — 19 Modules

**Provenance: SYNTHESIZED_CANON (14.4 desired state + operator corrections + code-resolved truth)**

Each module represents a functional domain of the product. Status reflects code reality as of 2026-06-04.

| # | Module | Description | Status | Dependencies |
|---|---|---|---|---|
| 1 | Portfolio and Multi-Company Management | Create portfolios, manage multiple entities, cross-entity metrics, capital allocation views, consolidated dashboards | PARTIALLY_IMPLEMENTED (Beast has company system, no portfolio layer above it) | Auth |
| 2 | Org Chart Engine | AI-generated organizational structures based on business model, stage, and complexity. Visual org chart editor. | NOT_IMPLEMENTED (onboarding steps 9-11 define generation) | Entity, Role System |
| 3 | Role System | First-class role objects with human and AI ownership, permission tiers (READ/DRAFT/EXECUTE/COMMIT), responsibility boundaries | PARTIALLY_IMPLEMENTED (UMH projection has PermissionTier enum and DepartmentAgent base) | Auth, Governance |
| 4 | Universal Dashboard Architecture | Shell layout: Header, Left Rail (portfolio/entity switcher + navigation), Main Workspace, Right Rail AI, Floating AI Control Panel | PARTIALLY_IMPLEMENTED (Beast has left-rail.tsx, right-rail.tsx, header.tsx, floating-ai-panel.tsx) | All modules feed data to dashboard |
| 5 | Workflow and SOP Engine | Multi-step workflow creation, execution, approval gates, retries, checkpoints, branching. SOP documentation tied to workflows. | NOT_IMPLEMENTED (onboarding steps 12-13 define generation; UMH substrate has execution pipeline) | Role System, Governance |
| 6 | Skill System | Reusable skill definitions with versioning and trust scoring. Agents invoke skills. Skills compose into workflows. | PARTIALLY_IMPLEMENTED (DepartmentAgent._add_skill() in projection; versioning/trust scoring not built) | Agent Runtime |
| 7 | Agent Runtime | Per-role agent with planner, skill router, tool executor. 10 department agents implemented, 6 more defined. | PARTIALLY_IMPLEMENTED (projections/eos/agents/ has 10 agents, 62 total skills) | Skill System, Intelligence Routing, Governance |
| 8 | AI Compute and Model Routing | Centralized intelligence gateway with cost-aware model selection, fallback chains, task-type routing | IMPLEMENTED (adapters/models/model_router.py — UMH substrate capability) | None (substrate layer) |
| 9 | Memory and Knowledge Architecture | Working memory, session memory, long-term memory. Agent memory per entity. Onboarding seeds initial memory. | PARTIALLY_IMPLEMENTED (UMH substrate has state/ layer; EOS-specific memory seeding not built) | State Management |
| 10 | Knowledge Graph | Semantic retrieval, relationship reasoning, business ontology as typed knowledge graph | NOT_IMPLEMENTED (UMH substrate/ontology/ exists; EOS business ontology projection not wired) | Memory Architecture |
| 11 | Human Intelligence Layer | Contact profiles with interaction history, relationship strength, communication preferences | NOT_IMPLEMENTED (explicitly excluded from MVP) | Knowledge Graph |
| 12 | Reality Intelligence Engine | External market data, competitor intelligence, trend detection pipeline | NOT_IMPLEMENTED (explicitly excluded from MVP) | Knowledge Graph, Integration Layer |
| 13 | Governance and Permissions | Hybrid RBAC+ABAC, autonomy levels, approval chains, risk gates, spending limits, compliance checks | PARTIALLY_IMPLEMENTED (UMH substrate governance.py has deterministic risk classification; full RBAC+ABAC not built) | Role System, Auth |
| 14 | Resilience and Failure Architecture | Retries, circuit breakers, saga compensation, failover, graceful degradation | MINIMAL (UMH substrate has basic retry; full resilience patterns are end-state) | All runtime modules |
| 15 | Cross-Platform Integration | Shared intelligence substrate with CreatorOS and LyfeOS. Cross-product data flow via UMH ports. | NOT_IMPLEMENTED (architecture defined in UMH sockets/; no runtime wiring) | UMH Substrate |
| 16 | Founder Command Center | Strategic command view with KPIs, next-best actions, morning briefing, decision queue | NOT_IMPLEMENTED (onboarding step 16 generates initial dashboard; CEO agent has morning_brief skill) | Dashboard, Agent Runtime, KPI Module |
| 17 | UBOS Template Engine | Franchise-like business templates. Pre-built operational templates for common business types. | NOT_IMPLEMENTED (onboarding generates type-aware structures; reusable template library not built) | All generation modules |
| 18 | Universal Business Primitives | 16 categories of business primitive types (customers, products, transactions, metrics, etc.) | PARTIALLY_IMPLEMENTED (UMH substrate/types.py has Pydantic models; EOS-specific business primitives not separated) | Type System |
| 19 | Self-Improvement Loop | Pattern detection across operations. Workflow refinement suggestions. Agent performance optimization. | NOT_IMPLEMENTED (UMH substrate has feedback.py quality scoring; EOS-specific loop not built) | Memory, Knowledge Graph, Feedback |

### Module status summary

| Status | Count | Modules |
|---|---|---|
| IMPLEMENTED | 1 | AI Compute and Model Routing |
| PARTIALLY_IMPLEMENTED | 7 | Portfolio Mgmt, Role System, Dashboard, Skill System, Agent Runtime, Governance, Business Primitives |
| MINIMAL | 1 | Resilience |
| NOT_IMPLEMENTED | 10 | Org Chart, Workflow Engine, Knowledge Graph, Human Intelligence, Reality Intelligence, Cross-Platform, Command Center, UBOS Templates, Self-Improvement, Memory (EOS-specific) |

**Source: SRC-PHASE-14_4 (modules array), SRC-UMH-PROJECTION (code truth), SRC-BEAST-FEATURE (Beast codebase documentation), SRC-14.6B-COM (agent inventory)**

---

## 4. Screen Inventory

**Provenance: SYNTHESIZED_CANON (14.4 desired state) + CODE_RESOLVED_CURRENT_TRUTH (Beast branch)**

### 11 canonical screens from desired state

| # | Screen | Purpose | Key components | Data requirements | Current status |
|---|---|---|---|---|---|
| 1 | Auth / Entry | Sign in, create or access workspace | Clerk auth flow, sign-in form, SSO buttons | User table, session | IMPLEMENTED (Beast: Clerk auth pages) |
| 2 | Company/Entity Setup | Define entity name, type, stage, offer, goals | Multi-step form, AI-assisted fields, entity type grid | Entity record, stage, goals, type classification | PARTIALLY_IMPLEMENTED (Beast: company creation, no portfolio-first flow) |
| 3 | Home Dashboard | Entity summary, KPI strip, today panel, AI copilot panel, operating memory | KPI cards, sparklines, next-best-action list, activity feed, EA chat | KPIs, tasks, workflows, agent actions, memory | PARTIALLY_IMPLEMENTED (Beast: dashboard layout exists, no KPI engine) |
| 4 | Company/Entity Settings | Entity configuration, preferences, billing, team settings | Settings form, section tabs, integration toggles | Entity config record, team data, integration state | PARTIALLY_IMPLEMENTED (Beast: settings pages exist) |
| 5 | Department/Role Management | Create departments, roles, responsibilities. Visual org chart. | Org chart visualization, role cards, drag-and-drop hierarchy editor | Departments, roles, permissions, team members | NOT_IMPLEMENTED |
| 6 | Workflow Library | Browse, create, manage workflows and SOPs | Workflow cards, search/filter, category tabs, AI generation button | Workflow records, SOP records, run history | NOT_IMPLEMENTED |
| 7 | Workflow Run View | Execute a workflow step-by-step with AI assistance | Step-by-step view, progress indicator, AI assistance panel, notes, output capture | Workflow run record, step state, agent outputs | NOT_IMPLEMENTED |
| 8 | Task Board/List | Create tasks, assign to roles, link to workflows, track status | Kanban board or list view, filters, priority indicators, assignment selector | Task records, role assignments, workflow links | NOT_IMPLEMENTED (Beast: basic task management may exist) |
| 9 | AI Copilot Workspace | Ask business questions, get summaries, draft documents, receive recommendations | Chat interface, document preview, action buttons, context panel | Conversation history, entity context, memory, agent capabilities | NOT_IMPLEMENTED |
| 10 | Docs/Notes Workspace | SOP notes, operating notes, strategy notes, role documentation | Rich text editor, document tree, version history, sharing controls | Document records, version history, permissions | NOT_IMPLEMENTED |
| 11 | Settings (Global) | User preferences, notification settings, theme, account management | Settings form, toggle switches, account management | User preferences record | PARTIALLY_IMPLEMENTED (Beast: user settings exist) |

### Additional screens from Beast branch (not in 14.4 desired state)

Beast feature/company-system has 32 pages. The following screens extend beyond the 11 canonical screens:

| Screen | Purpose | Beast path | Provenance |
|---|---|---|---|
| Portfolio Dashboard | Cross-entity portfolio view | client/src/pages/portfolio/ | CODE_RESOLVED_CURRENT_TRUTH |
| Team Management | Team member invitation, role assignment | client/src/pages/team/ | CODE_RESOLVED_CURRENT_TRUTH |
| Client/Customer Management | CRM-style client tracking | client/src/pages/clients/ | CODE_RESOLVED_CURRENT_TRUTH |
| Financial Dashboard | Revenue, expenses, cash flow, unit economics | client/src/pages/finance/ | CODE_RESOLVED_CURRENT_TRUTH |
| Analytics | Business analytics and reporting | client/src/pages/analytics/ | CODE_RESOLVED_CURRENT_TRUTH |
| Onboarding Wizard | Multi-step company setup flow | client/src/pages/onboarding/ | CODE_RESOLVED_CURRENT_TRUTH |

**Source: SRC-PHASE-14_4 (screens array), SRC-BEAST-FEATURE (32 pages documented in Phase 14.5)**

---

## 5. Workflow Inventory

**Provenance: SYNTHESIZED_CANON (14.4 desired state + onboarding spec)**

### 8 canonical workflows from desired state

| # | Workflow | Trigger | Steps (summary) | Agents involved |
|---|---|---|---|---|
| 1 | Set up business operating system | Operator completes onboarding | Create workspace, define entity, generate org structure, generate workflows, configure agents, activate | EA Agent, CEO Agent |
| 2 | See what matters today | Daily (scheduled) or on-demand | Aggregate KPIs, surface alerts, compile next-best actions, generate morning briefing | CEO Agent (morning_brief skill) |
| 3 | Define org structure | Operator triggers from Dept/Role screen | Select complexity, generate departments, generate roles, assign human/AI, configure permissions | CEO Agent (delegation skill) |
| 4 | Store and run workflows/SOPs | Operator creates or AI generates | Define steps, set approval gates, assign owners, execute step-by-step with AI assistance | Operations Agent (workflow_audit), any department agent for step execution |
| 5 | Use AI to plan and draft work | Operator request via EA or copilot | Clarify intent, select domain, draft content (plans, docs, role defs, workflow drafts, summaries), review, refine | EA Agent routes to appropriate department agent |
| 6 | Track tasks and priorities | Task creation (manual or workflow-generated) | Create task, assign to role, link to workflow/SOP, set priority/deadline, track status, report completion | Any department agent, CEO Agent (pipeline_review) |
| 7 | Keep business context persistent | Continuous (background) | Capture decisions, store preferences, record workflow outcomes, update entity context, maintain agent memory | All agents (memory_item event type) |
| 8 | Review key metrics and next-best actions | Periodic or on-demand | Pull KPI data, compare targets, detect anomalies, rank opportunities, generate recommendations | CEO Agent, Finance Agent (revenue_report, budget_forecast), Operations Agent (bottleneck_detection) |

### Onboarding-generated workflows (per entity type)

The 25-step onboarding flow (step 12) generates initial workflows tailored to entity type and stage. Examples:

| Entity type | Generated workflows (examples) |
|---|---|
| SaaS | Lead qualification, feature release, customer onboarding, monthly MRR review, churn analysis |
| Agency | Client intake, project kickoff, deliverable review, invoice generation, client check-in |
| E-Commerce | Order fulfillment, inventory reorder, product launch, customer support escalation, returns processing |
| Real Estate | Property acquisition evaluation, tenant screening, lease renewal, maintenance request routing, rent collection |
| Investment | Deal sourcing, due diligence checklist, position entry, portfolio rebalancing, exit evaluation |
| Coaching/Info-Product | Student onboarding, content creation cadence, community engagement, cohort launch, testimonial collection |

**Source: SRC-PHASE-14_4 (workflows array), SRC-14.6B-ONB (steps 12-14), SRC-14.6B-ONT (business_types with example KPIs)**

---

## 6. Feature Inventory

**Provenance: SYNTHESIZED_CANON (14.4 feature_list + operator corrections + code truth)**

### Features grouped by module (24 features from desired state + operator additions)

#### Portfolio and Entity Management
| # | Feature | MVP | End-state | Provenance |
|---|---|---|---|---|
| F-01 | Portfolio creation and management with cross-entity metrics | No (MVP = single entity) | Yes | SOURCE_PRESERVED_TRUTH |
| F-02 | Multi-entity workspace with entity switcher in Left Rail | No (MVP = one entity) | Yes | OPERATOR_CORRECTION |
| F-03 | Entity type taxonomy (LLC, C-Corp, SPV, Holding Co, etc.) | Yes (data model) | Yes (full lifecycle) | OPERATOR_CORRECTION |
| F-04 | Capital allocation views across portfolio entities | No | Yes | SYNTHESIZED_CANON |

#### Organizational Structure
| # | Feature | MVP | End-state | Provenance |
|---|---|---|---|---|
| F-05 | AI-generated org charts based on business model and stage | Yes (basic generation) | Yes (full editor) | SOURCE_PRESERVED_TRUTH |
| F-06 | First-class role objects with human/AI ownership | Yes | Yes | SOURCE_PRESERVED_TRUTH |
| F-07 | Department creation with linked workflows/tasks/docs | Yes (manual) | Yes (AI-generated) | SYNTHESIZED_CANON |

#### Dashboard and Intelligence
| # | Feature | MVP | End-state | Provenance |
|---|---|---|---|---|
| F-08 | Universal dashboard with Header, AI Control, Left Rail, Workspace, Right Rail | Yes | Yes | SOURCE_PRESERVED_TRUTH |
| F-09 | KPI strip with hero metrics, sparklines, trend indicators | Yes (basic) | Yes (full) | SYNTHESIZED_CANON |
| F-10 | Next-best-action recommendations | Yes (basic via CEO agent) | Yes (ML-powered) | SOURCE_PRESERVED_TRUTH |
| F-11 | Morning briefing from CEO agent | Yes | Yes | CODE_RESOLVED_CURRENT_TRUTH |

#### Workflow Engine
| # | Feature | MVP | End-state | Provenance |
|---|---|---|---|---|
| F-12 | Workflow creation with approval gates, checkpoints, branching | Yes (basic linear) | Yes (full DAG) | SOURCE_PRESERVED_TRUTH |
| F-13 | Workflow run view with step-by-step AI assistance | Yes | Yes | SOURCE_PRESERVED_TRUTH |
| F-14 | SOP documentation tied to workflows | Yes (basic) | Yes (versioned) | SYNTHESIZED_CANON |
| F-15 | UBOS template library (pre-built business templates) | No | Yes | SOURCE_PRESERVED_TRUTH |

#### AI and Agent System
| # | Feature | MVP | End-state | Provenance |
|---|---|---|---|---|
| F-16 | Reusable skill system with versioning and trust scoring | Yes (basic skills) | Yes (marketplace) | SOURCE_PRESERVED_TRUTH |
| F-17 | Role-specific agent runtime with planner, skill router, tool executor | Yes (10 department agents) | Yes (full agent hierarchy) | SOURCE_PRESERVED_TRUTH |
| F-18 | Centralized AI Gateway with cost-aware model selection | Yes (inherited from UMH) | Yes | CODE_RESOLVED_CURRENT_TRUTH |
| F-19 | EA Agent as primary operator interface | Yes | Yes | OPERATOR_CORRECTION |
| F-20 | Portfolio Advisor for cross-entity intelligence | No | Yes | OPERATOR_CORRECTION |

#### Knowledge and Memory
| # | Feature | MVP | End-state | Provenance |
|---|---|---|---|---|
| F-21 | Working/session/long-term memory per entity | Yes (basic) | Yes (full knowledge graph) | SOURCE_PRESERVED_TRUTH |
| F-22 | Semantic retrieval and relationship reasoning | No | Yes | SOURCE_PRESERVED_TRUTH |

#### Governance
| # | Feature | MVP | End-state | Provenance |
|---|---|---|---|---|
| F-23 | Hybrid RBAC+ABAC governance with autonomy levels | Yes (basic RBAC) | Yes (full RBAC+ABAC) | SOURCE_PRESERVED_TRUTH |
| F-24 | Approval chains with risk gates and spending limits | Yes (basic) | Yes (configurable per entity) | SYNTHESIZED_CANON |

#### Integration and Platform
| # | Feature | MVP | End-state | Provenance |
|---|---|---|---|---|
| F-25 | Cross-platform integration with CreatorOS and LyfeOS | No | Yes | SOURCE_PRESERVED_TRUTH |
| F-26 | Self-improvement loop (pattern detection, workflow refinement) | No | Yes | SOURCE_PRESERVED_TRUTH |
| F-27 | External market/competitor intelligence pipeline | No | Yes | SOURCE_PRESERVED_TRUTH |
| F-28 | Human intelligence profiles for contacts | No | Yes | SOURCE_PRESERVED_TRUTH |

**Source: SRC-PHASE-14_4 (feature_list), SRC-OPERATOR-CORRECTIONS (F-02, F-03, F-19, F-20), SRC-UMH-PROJECTION (F-11, F-17, F-18)**

---

## 7. Data Concepts — Entities, Relationships, Cardinality

**Provenance: SYNTHESIZED_CANON (14.4 data_concepts + operator ontology correction + code truth)**

### Core data model

```
Operator/User (1)
  |
  +-- Portfolio (1:N)
  |     |
  |     +-- Entity (1:N)
  |           |
  |           +-- Business/Venture/Organization (1:N per entity)
  |           +-- Investment (1:N per entity)
  |           +-- Asset (1:N per entity)
  |           |
  |           +-- Department (1:N)
  |           |     +-- Role (1:N per department)
  |           |           +-- Team Member — human or AI agent (1:N per role)
  |           |
  |           +-- Workflow (1:N)
  |           |     +-- WorkflowStep (1:N per workflow, ordered)
  |           |     +-- WorkflowRun (1:N per workflow)
  |           |           +-- StepExecution (1:N per run)
  |           |
  |           +-- SOP (1:N, linked to workflows)
  |           +-- Task (1:N, linked to roles and workflows)
  |           +-- Document (1:N)
  |           +-- KPI (1:N)
  |           +-- Transaction (1:N)
  |           +-- AgentConfig (1:N, one per agent role)
  |           +-- MemoryObject (1:N)
  |           +-- AIThread (1:N)
  |                 +-- AIMessage (1:N per thread)
```

### Data concept definitions (17 from 14.4 + operator additions)

| Concept | Description | Cardinality | Provenance |
|---|---|---|---|
| User | Authenticated operator. Ultimate authority. One per account in MVP. | Top-level | CODE_RESOLVED_CURRENT_TRUTH |
| Portfolio | Strategic container grouping entities under unified governance. | 1:N per user | OPERATOR_CORRECTION |
| Entity | Legal/operational vehicle (LLC, C-Corp, SPV, etc.). Owns bank accounts, signs contracts. | 1:N per portfolio | OPERATOR_CORRECTION |
| Company/Venture | Operating activity within an entity. Revenue generation, product delivery. | 1:N per entity | SYNTHESIZED_CANON |
| Investment | Capital deployment with return expectation. Active or passive. | 1:N per entity | OPERATOR_CORRECTION |
| Asset | Economic resource owned by entity. Tangible or intangible. | 1:N per entity | SYNTHESIZED_CANON |
| Department | Functional grouping within an entity (Sales, Engineering, Finance, etc.). | 1:N per entity | SOURCE_PRESERVED_TRUTH |
| Role | Named permission/responsibility set assignable to human or AI. | 1:N per department | SOURCE_PRESERVED_TRUTH |
| Workflow | Multi-step process with trigger, steps, gates, and outcome. | 1:N per entity | SOURCE_PRESERVED_TRUTH |
| WorkflowStep | Single step within a workflow. Has owner, action type, and completion criteria. | 1:N per workflow (ordered) | SOURCE_PRESERVED_TRUTH |
| WorkflowRun | Execution instance of a workflow. | 1:N per workflow | SOURCE_PRESERVED_TRUTH |
| Task | Assignable work item. May be standalone or workflow-generated. | 1:N per entity | SOURCE_PRESERVED_TRUTH |
| SOP | Standard Operating Procedure document tied to workflows. | 1:N per entity | SYNTHESIZED_CANON |
| Document | Persistent document (notes, plans, specs, operating docs). | 1:N per entity | SOURCE_PRESERVED_TRUTH |
| KPI | Key Performance Indicator with target, current value, and trend. | 1:N per entity | SYNTHESIZED_CANON |
| Transaction | Financial event (payment, invoice, expense, revenue). | 1:N per entity | SYNTHESIZED_CANON |
| MemoryObject | Persisted knowledge item (fact, preference, decision, pattern). | 1:N per entity | SOURCE_PRESERVED_TRUTH |
| AIThread | Conversation thread between operator and agent(s). | 1:N per entity | SOURCE_PRESERVED_TRUTH |
| AIMessage | Single message within a thread. | 1:N per thread | SOURCE_PRESERVED_TRUTH |
| Skill | Reusable capability registered on an agent. | 1:N per agent config | CODE_RESOLVED_CURRENT_TRUTH |
| AgentConfig | Configuration for an AI agent role within an entity. | 1:N per entity | SYNTHESIZED_CANON |
| Tool | External system/API registered as a capability. | 1:N globally | SYNTHESIZED_CANON |
| UniversalBusinessPrimitive | One of 16 typed business primitive categories. | N/A (type system) | SOURCE_PRESERVED_TRUTH |

### Database truth (current code)

| Source | Tables | ORM | Auth | RLS |
|---|---|---|---|---|
| GitHub main | 15 tables | Drizzle ORM | Passport.js + Firebase | Partial (org_id scoping) |
| Beast feature/company-system | Expanded schema (company, portfolio additions) | Drizzle ORM | Clerk | Yes (org_id scoping) |
| Target | Full schema matching data concepts above | Drizzle ORM | Clerk | Full RLS with entity-level isolation |

**Embedding dimension mismatch**: 384 vs 1536 is unresolved across the codebase. This requires an operator decision before implementation.

**Source: SRC-PHASE-14_4 (data_concepts), SRC-14.6B-ONT (hierarchy definitions), SRC-GITHUB-MAIN (15 tables), SRC-BEAST-FEATURE (expanded schema)**

---

## 8. AI/Agent Architecture

**Provenance: OPERATOR_CORRECTION (routing chain) + CODE_RESOLVED_CURRENT_TRUTH (implemented agents) + INFERRED_PROFESSIONAL_GAP (missing agents)**

### Communication and delegation chain

```
Operator
  |
  v
EA Agent (primary intake, triage, routing)
  |
  +--[portfolio-scope]--> Portfolio Advisor Agent (cross-entity strategy)
  |
  +--[entity-scope]----> CEO Agent (entity strategy, department coordination)
                            |
                            +---> Sales Agent
                            +---> Marketing Agent
                            +---> Operations Agent
                            +---> Finance Agent
                            +---> Legal/Compliance Agent
                            +---> Customer Success Agent
                            +---> Product Agent
                            +---> HR/Recruiting Agent
                            +---> Engineering Agent
                            +---> Admin/EA Department Agent *
                            +---> Research Agent *
                            +---> Content Agent *
                            +---> Automation Agent *
                            +---> Investment Analyst Agent *
                            +---> Asset Manager Agent *
                            +---> Property Manager Agent *

(* = NOT_IMPLEMENTED, marked INFERRED_PROFESSIONAL_GAP)
```

### Critical routing constraint

**EA Agent does NOT route directly to department/specialist agents.** This is a hard boundary corrected by the operator. All department-level work flows through the CEO Agent. EA routes to Portfolio Advisor (for portfolio-scope concerns) or CEO Agent (for entity-scope execution).

### Agent inventory

| Agent | Department | Permission tier | Skills | Code status | Location |
|---|---|---|---|---|---|
| EA Agent | N/A (routing layer) | READ | Chat intake, triage, routing, scheduling, status aggregation | NOT_IMPLEMENTED | -- |
| Portfolio Advisor | N/A (portfolio layer) | DRAFT | Portfolio strategy, capital allocation, cross-entity comparison, risk detection | NOT_IMPLEMENTED | -- |
| CEO Agent | executive | COMMIT | Strategic analysis, decision briefs, delegation, pipeline review, morning brief, action approval | IMPLEMENTED | projections/eos/agents/ceo.py |
| Sales Agent | sales | EXECUTE | Lead scoring, outreach drafting, pipeline reporting, follow-up, outreach sending, call booking | IMPLEMENTED | projections/eos/agents/sales.py |
| Marketing Agent | marketing | EXECUTE | Content calendar, content ideation, audience analysis, brand audit, content posting, campaign reporting | IMPLEMENTED | projections/eos/agents/marketing.py |
| Operations Agent | operations | EXECUTE | System health, workflow audit, process automation, resource allocation, bottleneck detection, ops reporting | IMPLEMENTED | projections/eos/agents/operations.py |
| Finance Agent | finance | COMMIT | Revenue reporting, expense tracking, budget forecasting, unit economics, cashflow analysis, payment processing, invoicing | IMPLEMENTED | projections/eos/agents/finance.py |
| Legal Agent | legal | COMMIT | Contract review, compliance check, entity status, terms drafting, IP audit, contract execution | IMPLEMENTED | projections/eos/agents/legal.py |
| Customer Success Agent | customer_success | EXECUTE | Ticket routing, satisfaction reporting, churn detection, onboarding guides, feedback analysis, response drafting, response sending | IMPLEMENTED | projections/eos/agents/customer_success.py |
| Product Agent | product | DRAFT | Roadmap status, feature prioritization, user feedback summary, competitor analysis, release planning, spec drafting | IMPLEMENTED | projections/eos/agents/product.py |
| HR Agent | hr | EXECUTE | Candidate screening, hiring pipeline, onboarding plans, performance review, contractor search, candidate outreach | IMPLEMENTED | projections/eos/agents/hr.py |
| Engineering Agent | engineering | EXECUTE | Code review, architecture analysis, deployment status, tech debt reporting, incident response, deployment | IMPLEMENTED | projections/eos/agents/engineering.py |
| Admin/EA Dept Agent | admin | EXECUTE | Meeting scheduling, document management, expense processing, travel, workspace management | NOT_IMPLEMENTED | -- |
| Research Agent | research | READ | Market research, competitor intelligence, technology scouting, trend analysis, data gathering | NOT_IMPLEMENTED | -- |
| Content Agent | content | EXECUTE | Content writing, editing, media production, repurposing, distribution queue, content analytics | NOT_IMPLEMENTED | -- |
| Automation Agent | automation | EXECUTE | Workflow automation design, integration management, trigger/action config, monitoring, optimization | NOT_IMPLEMENTED | -- |
| Investment Analyst | investment_analysis | DRAFT | Due diligence, valuation modeling, risk assessment, investment thesis, market analysis, position sizing | NOT_IMPLEMENTED | -- |
| Asset Manager | asset_management | EXECUTE | Asset inventory, depreciation tracking, maintenance scheduling, license management, valuation, lifecycle reporting | NOT_IMPLEMENTED | -- |
| Property Manager | property_management | EXECUTE | Tenant management, lease tracking, maintenance routing, rent collection, property inspection, vendor coordination | NOT_IMPLEMENTED | -- |

**Total agents**: 19 defined (10 implemented + 9 not implemented)
**Total skills across implemented agents**: 62

### Permission tier model

| Tier | Authority | Can do |
|---|---|---|
| READ | Observe only | View data, generate reports, analyze |
| DRAFT | Create artifacts | Draft documents, plans, proposals — no execution |
| EXECUTE | Act within scope | Send messages, post content, create tasks, run workflows |
| COMMIT | Full authority | Approve actions, execute payments, sign contracts, make binding decisions |

### Intelligence routing (inherited from UMH)

EOS inherits UMH's intelligence routing through `adapters/models/model_router.py`:

- **Strategic/CEO tasks**: Best available model (Opus 4.6 via subscription)
- **Routine department tasks**: Fast/cheap models (Gemini 2.5 Flash, Groq)
- **Fallback chain**: cc_sdk (Opus 4.6) -> Gemini 2.5 Flash -> Groq -> Ollama
- **Cost optimization**: Task type determines model selection, not blanket high-quality

### Instance-specific concern

CEO agent's `strategic_analysis` skill contains hardcoded references to "Initiate Arena" and specific business context. This must be generalized for multi-entity support via BIS runtime lookup.

**Source: SRC-14.6B-COM (full routing chain, 19 agents, delegation protocol, escalation protocol), SRC-UMH-PROJECTION (10 implemented agents), SRC-OPERATOR-CORRECTIONS (EA routing constraint)**

---

## 9. Business Model

**Provenance: OPEN_QUESTION_OPERATOR_DECISION_REQUIRED**

No pricing tiers, revenue model, or monetization strategy has been defined in any source document. This is the most significant product decision gap.

### What is known

- EOS is a SaaS product (TypeScript/React frontend, Express backend, Neon Postgres)
- The product serves operators from solo founders to institutional holding companies
- Multiple tiers are implied by the scale range but not specified
- No free tier vs. paid tier decision has been made
- No pricing anchors exist in any source document

### What must be decided (operator decision required)

| Decision | Options (inferred) | Impact |
|---|---|---|
| Free tier existence | Free tier with limits vs. paid-only vs. freemium | Acquisition funnel, conversion metrics, infrastructure cost |
| Pricing model | Per-seat, per-entity, per-portfolio, flat-rate, usage-based, hybrid | Revenue predictability, expansion revenue, churn dynamics |
| Tier structure | Solo/Team/Business/Enterprise or similar | Feature gating, upsell paths, competitive positioning |
| AI usage billing | Included in tier, usage-metered, hybrid | Cost management, value perception, margin |
| Entity limits | Unlimited entities per tier or tiered entity counts | Expansion revenue from multi-entity operators |
| Agent limits | All agents included or tiered agent access | Value differentiation between tiers |

### Competitive pricing context (inferred, not from any source)

| Competitor | Pricing range | Model |
|---|---|---|
| Monday.com | $9-19/seat/month | Per-seat, tiered features |
| Notion | $8-15/seat/month | Per-seat, AI add-on |
| ClickUp | $7-12/seat/month | Per-seat, tiered features |
| Linear | $8/seat/month | Per-seat, flat |
| Carta | $2,000-10,000+/year | Per-entity/cap-table size |

EOS competes at a higher value proposition than project management tools and closer to Carta/AngelList for portfolio operators, but pricing must be validated.

**Source: SRC-PHASE-14_4 (open_questions: "Pricing tiers not defined"), inference from competitive landscape**

---

## 10. Competitive Position

**Provenance: INFERRED_PROFESSIONAL_GAP**

No competitive analysis exists in any EOS source document. The following is inferred from professional standards for product positioning.

### What EOS is NOT competing with directly

| Category | Tools | Why not direct competition |
|---|---|---|
| Project management | Monday.com, Asana, ClickUp, Linear | EOS is an operating system for entire businesses, not a task board. Projects are one layer within EOS. |
| Note-taking / wikis | Notion, Confluence, Obsidian | EOS has docs/notes but they are operational artifacts within a governed business structure. |
| Accounting | QuickBooks, Xero, FreshBooks | EOS tracks capital flow and KPIs but integrates with accounting tools rather than replacing them. |
| CRM | HubSpot, Salesforce, Pipedrive | EOS has client lifecycle management but CRM is one module within the full operating system. |

### Where EOS occupies unique territory

| Dimension | EOS | Nearest competitors |
|---|---|---|
| Full business operating system | Yes — portfolio to workflow to KPI | No single competitor covers this range |
| AI-native agent hierarchy | Yes — 19 agents with governed delegation | Notion AI, ClickUp Brain are copilots, not org-chart-integrated agents |
| Multi-entity portfolio management | Yes — portfolio -> entity -> operations | Carta (cap table only), AngelList (investment tracking only) |
| Entity type breadth | 8 entity types, 19 business types | Most tools serve one business type |
| Onboarding-as-generation | 25-step flow generates complete operating system | Competitors require manual setup |
| Governed AI autonomy | Permission tiers, approval chains, risk gates | No competitor has governed AI agent hierarchies |

### Competitive risks

| Risk | Description | Mitigation |
|---|---|---|
| Breadth vs depth | Covering 19 modules means each may be shallow vs. point solutions | MVP focuses on 5 releases of core functionality; depth over breadth initially |
| "All-in-one" stigma | Market skepticism toward platforms that claim to do everything | Position as operating system (infrastructure), not suite (collection of tools) |
| Enterprise incumbents | Salesforce, Microsoft 365 ecosystem | EOS targets founders and operators, not enterprise IT departments |
| AI commoditization | AI copilot features becoming table stakes | EOS differentiates on governed agent hierarchy, not just chat AI |

**Source: Inferred from professional product positioning standards. No competitive analysis exists in any EOS source document (SRC-PHASE-14_4 open_questions confirms this gap).**

---

## 11. What EOS Is NOT

**Provenance: SOURCE_PRESERVED_TRUTH (operator corrections) + SYNTHESIZED_CANON**

These exclusions are canonical. They define the product boundary and prevent scope drift.

| EOS is NOT | Explanation | Sibling that IS this |
|---|---|---|
| A CRM | EOS is not a customer relationship management tool. Client lifecycle is one module, not the product identity. EOS can integrate with CRMs. | -- |
| A simple dashboard | EOS is not a read-only reporting layer. It is an active operating substrate — it executes, not just displays. | -- |
| A workflow tool | EOS is not just task automation. Workflows are one layer of a complete operating system. | -- |
| A generic AI copilot | EOS agents have defined roles, authority, and governance. They are not chat assistants. They are autonomous operators with bounded authority. | -- |
| A portfolio tracker | EOS does not just display portfolio data. It actively operates the entities within portfolios. | -- |
| A business admin panel | EOS is not a settings page. It is the business runtime itself. | -- |
| A project management tool | EOS is not Asana/Monday/Notion. Projects exist within a larger operational structure. | -- |
| An accounting system | EOS tracks capital flow and KPIs but does not replace QuickBooks/Xero. Integration, not replacement. | -- |
| A creator platform | EOS aesthetic is executive command center. No social feeds, no follower counts, no content engagement as primary UI. | CreatorOS |
| A gamified self-improvement platform | No XP bars, leveling systems, achievement badges, quest metaphors, RPG character sheets. | LyfeOS |
| A marketplace | EOS operates businesses. It does not connect buyers and sellers as its primary function. | -- |
| A landing page builder | The operating interface is a cockpit, not a marketing site. No hero sections or gradient CTAs inside the app. | -- |

### Visual anti-patterns (from UI/UX canon)

| Never | Reason |
|---|---|
| Playful/gamified elements | LyfeOS territory |
| Creator-social aesthetic | CreatorOS territory |
| RPG/character sheet metaphors | LyfeOS territory |
| Glassmorphic/frosted glass | Reduces finance-grade clarity |
| Neon/cyberpunk colors | Not institutional |
| Casual/rounded/bouncy | Not operational |
| Marketing-site patterns inside the app | This is an OS, not a landing page |

**Source: SRC-14.6B-BIZ (what_eos_is_not), SRC-14.6B-UI (what_eos_is_not_visually), SRC-OPERATOR-CORRECTIONS (aesthetic correction)**

---

## 12. Source Provenance

**Every claim in this document traces to one of 13 source inputs. This section maps the provenance chain.**

### Source inventory

| ID | Source | Type | Status | Weight |
|---|---|---|---|---|
| SRC-GDOC-001 | Google Doc: EntrepreneurOS (doc_id: 1kKBGCS9kewN...) | Product vision document | SOURCE_PRESERVED_TRUTH | Highest for product intent |
| SRC-PHASE-14_3A | Phase 14.3A: Product Requirements Gap Report | Analysis artifact | SYNTHESIZED_CANON | Claim extraction layer |
| SRC-PHASE-14_3A-CLAIMS | Phase 14.3A: Full Content Extracted Claims | Analysis artifact | SYNTHESIZED_CANON | Exhaustive claim set |
| SRC-PHASE-14_3A-DESIGN | Phase 14.3A: End State Design Map | Analysis artifact | SYNTHESIZED_CANON | Design convergence |
| SRC-PHASE-14_4 | Phase 14.4: EOS Desired State Canon | Desired state artifact | SYNTHESIZED_CANON | 19 modules, 11 screens, 8 workflows, MVP definition |
| SRC-PHASE-14_5 | Phase 14.5: EOS Convergence Plan | Convergence plan | SYNTHESIZED_CANON | Divergence analysis, auth state, work packets |
| SRC-PHASE-14_5A | Phase 14.5A: EOS 13-Layer Production Stack | Production stack design | SYNTHESIZED_CANON | Layer-by-layer current vs desired state |
| SRC-GITHUB-MAIN | GitHub main branch (entrepreneuros repo) | Codebase | CODE_RESOLVED_CURRENT_TRUTH | 202 files, stale (2026-02-20), Passport.js |
| SRC-BEAST-FEATURE | Beast feature/company-system branch | Codebase | CODE_RESOLVED_CURRENT_TRUTH | 603 files, Clerk, active, **canonical codebase** (DEC-146B-EOS-001) |
| SRC-UMH-PROJECTION | UMH EOS Projection (projections/eos/) | Projection code | CODE_RESOLVED_CURRENT_TRUTH | 10 agents, 62 skills, 5699 lines |
| SRC-OPERATOR-CORRECTIONS | Operator corrections (Phase 14.6B mission brief) | Operator directive | SOURCE_PRESERVED_TRUTH | Highest authority — overrides all |
| SRC-14.6B-* | Phase 14.6B corrective artifacts (7 total) | Corrective canon | SYNTHESIZED_CANON | This phase's output |

### Provenance label definitions

| Label | Meaning | Authority |
|---|---|---|
| SOURCE_PRESERVED_TRUTH | Directly from operator-authored documents. No interpretation. | Highest |
| CODE_RESOLVED_CURRENT_TRUTH | Derived from reading actual source code. Code wins over docs when they conflict. | High (for current state) |
| SYNTHESIZED_CANON | Synthesized from multiple sources with explicit provenance chain. Analyst judgment applied. | Medium |
| INFERRED_PROFESSIONAL_GAP | Gap identified from professional standards not stated in any source document. | Advisory |
| OPEN_QUESTION_OPERATOR_DECISION_REQUIRED | Ambiguity or conflict that only the operator can resolve. Must not be auto-resolved. | Blocking until resolved |
| IMPLEMENTATION_DEBT | Known gap between desired state and current implementation. | Informational |

### Conflict resolution hierarchy

When sources disagree:

1. **Operator corrections** override everything (SOURCE_PRESERVED_TRUTH from 14.6B mission brief)
2. **Code** resolves ambiguity between docs (CODE_RESOLVED_CURRENT_TRUTH)
3. **Later phases** supersede earlier phases (14.6B > 14.5A > 14.5 > 14.4 > 14.3A)
4. **Professional inference** is advisory only, never overrides source truth

### Known contradictions resolved in this canon

| Contradiction | Resolution | Source |
|---|---|---|
| EOS ownership: Lyfe Institute vs OST | OST owns EOS. Lyfe Institute is a venture managed inside EOS. | SRC-OPERATOR-CORRECTIONS |
| Auth: Passport.js (main) vs Clerk (Beast) | Clerk is the confirmed production auth provider (DEC-146B-EOS-003, ratified 2026-06-04). Passport.js is stale. | SRC-BEAST-FEATURE (canonical codebase per DEC-146B-EOS-001) |
| Class names: EOSGateway vs Gateway, EOSContext vs SubstrateContext | Generic names are canonical (Gateway, SubstrateContext). EOS-prefixed names were renamed during substrate cleanup. | SRC-UMH-PROJECTION (code truth) |
| Module paths: eos_ai/ vs substrate/+adapters/+transports/ | Post-convergence paths (substrate/, adapters/, transports/) are canonical. eos_ai/ is historical. | SRC-UMH-PROJECTION (code truth) |
| North star: $100K vs $10K/month | $10K/month net profit is the current north star. $100K appears in aspirational context. | SRC-OPERATOR-CORRECTIONS |
| EA routing: direct to specialists vs through CEO | EA routes through Portfolio Advisor or CEO. Never directly to specialists. | SRC-OPERATOR-CORRECTIONS |
| UI aesthetic: RPG/gamified vs executive command center | Executive command center. RPG/gamified is LyfeOS territory. | SRC-OPERATOR-CORRECTIONS |

---

## Appendix A: MVP Definition

**Provenance: SYNTHESIZED_CANON (14.4 mvp_definition + operator corrections)**
**Decision: MVP scope R1-R5 confirmed as defined (DEC-146B-EOS-002, ratified 2026-06-04).**

### Scope

AI-assisted company command center for one founder and one business.

### 5 releases (ratified)

| Release | Name | Core deliverable |
|---|---|---|
| R1 | Core Shell | Auth (Clerk), entity creation, settings, shell layout (Left Rail, Header, Workspace) |
| R2 | Org + Tasks | Departments, roles, task board, basic org chart |
| R3 | Workflows | Workflow library, workflow runner, AI-assisted SOP drafting |
| R4 | AI Copilot | EA Agent chat, CEO agent integration, memory, recommendations |
| R5 | Docs + Memory | Notes workspace, operating docs, persistent context, knowledge seeding |

### MVP explicit exclusions

These features are NOT in MVP. They are end-state.

- Portfolio multi-company orchestration
- Full autonomous agents (agents operate with approval in MVP)
- Multi-agent collaboration (agents are standalone in MVP)
- Advanced market intelligence (Reality Intelligence Engine)
- Human intelligence graph
- Local/offline AI
- Multi-region production deployment
- Full CreatorOS/LyfeOS shared runtime
- Enterprise permissions
- Skill marketplace
- UBOS template library (full)
- Cross-platform integration

**Source: SRC-PHASE-14_4 (mvp_definition)**

---

## Appendix B: Current Code State

**Provenance: CODE_RESOLVED_CURRENT_TRUTH**

### Two codebases, one canonical codebase (ratified)

| Dimension | GitHub main | Beast feature/company-system |
|---|---|---|
| Files | 202 | 603 |
| Last active | 2026-02-20 (stale) | Active development |
| Author | Replit Agent | Developer (human + AI) |
| Auth | Passport.js + Firebase | Clerk |
| Schema | 15 tables (basic) | Expanded (company, portfolio, team) |
| Pages | ~11 | 32 |
| Route modules | Basic | 14 |
| Status | Stale (deprecated) | **Canonical codebase** (DEC-146B-EOS-001, ratified 2026-06-04) |
| Location | GitHub repository | Beast Windows machine (C:\dev\dev\entrepreneuros) |

### Source divergence

401-file divergence between branches. Beast has 401 files that main does not.
Beast has been ratified as the canonical EOS codebase (DEC-146B-EOS-001, ratified 2026-06-04). GitHub main is stale/deprecated. Promotion execution still requires:

- Build validation (clean compile on target)
- Secret scan (no hardcoded credentials)
- Rollback plan

### UMH projection (third codebase)

| Dimension | Value |
|---|---|
| Path | projections/eos/ |
| Lines | 5699 |
| Agents | 10 department agents |
| Views | 3 |
| Workflows | 3 |
| Integration | Registers with UMH substrate via abstract ports |

**Source: SRC-GITHUB-MAIN, SRC-BEAST-FEATURE, SRC-UMH-PROJECTION, SRC-PHASE-14_5 (divergence analysis)**

---

## Appendix C: Technology Stack

**Provenance: CODE_RESOLVED_CURRENT_TRUTH + SYNTHESIZED_CANON**

### Frontend

| Technology | Purpose | Source |
|---|---|---|
| TypeScript | Language (strict mode) | Both branches |
| React 18 | UI framework | Both branches |
| Vite | Build tool | Both branches |
| Tailwind CSS | Styling (utility-first) | Both branches |
| shadcn/ui + Radix UI | Component library | Both branches |
| TanStack Query (React Query) | Server state management | Beast branch |
| wouter or React Router | Client-side routing | Beast branch |
| Drizzle ORM + Drizzle-Zod | Type-safe ORM + runtime validation | Both branches |
| Recharts or Tremor | Data visualization (direction, not confirmed) | SYNTHESIZED_CANON |
| Inter | Typography (direction, not confirmed) | SYNTHESIZED_CANON |

### Backend

| Technology | Purpose | Source |
|---|---|---|
| Express | HTTP server | Both branches |
| TypeScript | Language | Both branches |
| Drizzle ORM | Database access | Both branches |
| Zod | Request/response validation | Both branches |
| Clerk SDK | Authentication | Beast branch |

### Infrastructure

| Technology | Purpose | Source |
|---|---|---|
| Neon Postgres | Database (with RLS) | Both branches |
| Clerk | Authentication provider | Beast branch (canonical) |
| Fly.io | Deployment target (planned) | SYNTHESIZED_CANON |

### UMH Substrate (Python layer)

| Technology | Purpose | Source |
|---|---|---|
| Python 3.11 | Runtime | UMH projection |
| Pydantic | Type system | UMH projection |
| adapters/models/model_router.py | Intelligence routing | UMH substrate |
| cc_sdk | Claude Code CLI integration (Opus 4.6) | UMH substrate |

**Source: SRC-GITHUB-MAIN, SRC-BEAST-FEATURE, SRC-UMH-PROJECTION**

---

## Appendix D: Onboarding Summary

**Provenance: OPERATOR_CORRECTION + SYNTHESIZED_CANON**

Full specification in `phase14_6b_eos_onboarding_first_boot_spec.json`.

### 25-step flow (summary)

| Step | Name | Category |
|---|---|---|
| 1 | Create Account / Sign In with Clerk | authentication |
| 2 | Create Primary Portfolio | portfolio_setup |
| 3 | Choose Onboarding Path (4 paths) | path_selection |
| 4 | Select Entity Type | entity_definition |
| 5 | Choose Stage (8 stages) | stage_selection |
| 6 | Define Goals and Constraints | strategic_context |
| 7 | Define Complexity (5 levels) | complexity_selection |
| 8 | Generate Company/Entity Workspace | generation |
| 9 | Generate Org Chart | generation |
| 10 | Generate Departments | generation |
| 11 | Generate Roles | generation |
| 12 | Generate Workflows | generation |
| 13 | Generate SOPs | generation |
| 14 | Generate Recurring Tasks | generation |
| 15 | Generate Tool Stack | generation |
| 16 | Generate KPIs / Dashboard | generation |
| 17 | Generate Client/Customer Lifecycle | generation |
| 18 | Generate Offer/Product/Service Model | generation |
| 19 | Generate Investment/Asset Tracking Model | generation |
| 20 | Configure Team or Solo-Founder Mode | configuration |
| 21 | Configure EA / Portfolio Advisor / CEO Agent Behavior | configuration |
| 22 | Configure Approval Settings | governance |
| 23 | Configure Integrations / Tools | configuration |
| 24 | Review Generated Operating System | review |
| 25 | Approve / Edit / Enter Active Mode | activation |

### Four onboarding paths

1. **Start New Business** — new entity from scratch, launch-oriented generation
2. **Model Existing Business** — capture current state, map existing operations
3. **Create Investment / Entity** — non-operating entity: investments, holdings, assets
4. **Import Existing Operation** — import from spreadsheets, exports, external tools

### Eight business stages

Idea -> Validation -> Launch -> Early Revenue -> Growth -> Scale -> Enterprise -> Portfolio/Institutional

### Five complexity levels

Solo Operator -> Lean Team -> Growing Team -> Multi-Department -> Multi-Entity

---

## Appendix E: UI Shell Architecture

**Provenance: OPERATOR_CORRECTION + CODE_RESOLVED_CURRENT_TRUTH**

Full specification in `phase14_6b_eos_ui_ux_aesthetic_canon.json`.

### Shell components

| Component | Size | Position | Content |
|---|---|---|---|
| Left Rail | 240-280px (collapsible to ~60px) | Fixed left | Portfolio/entity switcher, role-dependent navigation, settings/profile |
| Header | 48-56px | Fixed top | Global search, notification bell, user avatar, entity breadcrumb, quick actions |
| Main Workspace | Flexible (fills remaining) | Center | Context-dependent: dashboards, tables, forms, boards, workflow views |
| Right Rail AI | 320-400px (collapsible) | Fixed right | Contextual AI (EA or context-appropriate agent), recommendations, chat input |
| Floating AI Control | FAB pattern | Bottom-right overlay | Quick command input, agent status, expand to command palette |
| Risk/Approval Notices | Inline or banner | Below header when active | Pending approvals, risk warnings, compliance alerts |
| Activity/Event Feed | Tab in Right Rail | Within Right Rail | Real-time stream of human actions, agent actions, system events |

### Design direction

- **Dark mode primary** (Bloomberg/terminal inspired)
- **Compact density** by default (not generous SaaS whitespace)
- **Finance-grade typography** (Inter, monospace for numbers, tabular numerals)
- **Sharp borders** (4-6px radius, visible 1px borders, not borderless floating)
- **Minimal animation** (fast state changes, no bounce, 150ms fade max)
- **Data-first** (tables are first-class citizens, KPI cards with sparklines)

---

## Appendix F: Open Questions Requiring Operator Decision

**Provenance: OPEN_QUESTION_OPERATOR_DECISION_REQUIRED**

These are collected from all source artifacts. No auto-resolution permitted.

### Product / Business

| ID | Question | Source |
|---|---|---|
| OQ-BIZ-001 | What are the pricing tiers and revenue model? | SRC-PHASE-14_4 |
| OQ-BIZ-002 | Free tier vs. paid-only vs. freemium? | Inferred |
| OQ-BIZ-003 | Mobile strategy: web-responsive only vs. native app? | SRC-PHASE-14_4 |
| OQ-BIZ-004 | Skill marketplace economics (if/when built)? | SRC-PHASE-14_4 |
| OQ-BIZ-005 | Whether UBOS template library will be community-contributed or curated only? | SRC-PHASE-14_4 |

### Architecture / Technical

| ID | Question | Source |
|---|---|---|
| OQ-TECH-001 | Embedding dimension: 384 vs 1536? | SRC-PHASE-14_4 |
| OQ-TECH-002 | How to bridge Python substrate and TypeScript SaaS frontend? | SRC-PHASE-14_4 |
| OQ-TECH-003 | Multi-region deployment strategy? | SRC-PHASE-14_4 |
| OQ-TECH-004 | Local/private AI runtime scope? | SRC-PHASE-14_4 |

### Agent Architecture

| ID | Question | Source |
|---|---|---|
| OQ-AGENT-001 | Should EA Agent be a DepartmentAgent subclass or distinct type? | SRC-14.6B-COM |
| OQ-AGENT-002 | Can operators bypass EA and communicate directly with CEO/department agents in power-user mode? | SRC-14.6B-COM |
| OQ-AGENT-003 | How does routing handle multi-portfolio operators? | SRC-14.6B-COM |
| OQ-AGENT-004 | Per-entity agent instances vs. shared instances with entity context? | SRC-14.6B-COM |

### UI/UX

| ID | Question | Source |
|---|---|---|
| OQ-UI-001 | Dark mode only for initial launch, or ship both dark and light? | SRC-14.6B-UI |
| OQ-UI-002 | Preserve Beast design-tokens.ts values or replace with finance-grade direction? | SRC-14.6B-UI |
| OQ-UI-003 | Specific commercial font (Inter recommended) or system fonts? | SRC-14.6B-UI |
| OQ-UI-004 | Default dashboard density: Bloomberg-level vs Stripe-level? | SRC-14.6B-UI |
| OQ-UI-005 | Activity/Event Feed: tab in Right Rail or separate panel? | SRC-14.6B-UI |

### Onboarding

| ID | Question | Source |
|---|---|---|
| OQ-ONB-001 | Multiple entities in single onboarding flow or one at a time? | SRC-14.6B-ONB |
| OQ-ONB-002 | Minimum viable onboarding: can operator skip all generation and enter bare? | SRC-14.6B-ONB |
| OQ-ONB-003 | Persist onboarding state for resume later? | SRC-14.6B-ONB |
| OQ-ONB-004 | Import formats for v1: CSV/JSON only or more? | SRC-14.6B-ONB |
| OQ-ONB-005 | Generation display: sequential (real-time) or batch (loading screen)? | SRC-14.6B-ONB |

**Total open questions: 19**

---

## Appendix G: Implementation Debt Register (Summary)

**Provenance: IMPLEMENTATION_DEBT**

Full details in individual artifact files. This is the consolidated summary.

### Critical debt (blocking)

| ID | Description | Artifact |
|---|---|---|
| DEBT-ARCH-001 | EA Agent does not exist — entire routing chain depends on it | SRC-14.6B-COM |
| DEBT-ARCH-002 | Portfolio Advisor Agent does not exist — no portfolio-level intelligence | SRC-14.6B-COM |
| DEBT-ARCH-003 | No inter-agent routing infrastructure — agents are standalone classes with no message passing | SRC-14.6B-COM |
| DEBT-ONB-001 | Beast has company creation but no portfolio-first flow — portfolio layer missing above company | SRC-14.6B-ONB |
| DEBT-ONB-002 | AI generation engine for onboarding steps 8-19 does not exist | SRC-14.6B-ONB |

### High debt

| ID | Description | Artifact |
|---|---|---|
| DEBT-UI-004 | No accessibility audit on either branch | SRC-14.6B-UI |
| DEBT-CODE-001 | 401-file divergence between GitHub main and Beast — promotion not yet executed | SRC-PHASE-14_5 |
| DEBT-CODE-002 | CEO agent hardcoded to Initiate Arena context — needs BIS generalization | SRC-14.6B-COM |
| DEBT-AUTH-001 | GitHub main still uses Passport.js — stale auth system | SRC-PHASE-14_5 |

### Medium debt

| ID | Description | Artifact |
|---|---|---|
| DEBT-UI-001 | No documented design system or Storybook for Beast components | SRC-14.6B-UI |
| DEBT-UI-002 | No component documentation | SRC-14.6B-UI |
| DEBT-UI-003 | Dark mode implementation unverified in Beast | SRC-14.6B-UI |
| DEBT-ONB-003 | Agent configuration UI requires behavior contracts not yet defined in SaaS layer | SRC-14.6B-ONB |
| DEBT-ONB-004 | Integration marketplace requires OAuth connector infrastructure not yet built | SRC-14.6B-ONB |
| DEBT-AGENT-001 | 6 department agents defined as professional gaps (admin, research, content, automation, investment_analyst, asset_manager, property_manager) | SRC-14.6B-COM |

### Low debt

| ID | Description | Artifact |
|---|---|---|
| DEBT-UI-005 | No keyboard shortcuts or command palette in Beast | SRC-14.6B-UI |

---

## Appendix H: UMH-EOS Integration Architecture

**Provenance: CODE_RESOLVED_CURRENT_TRUTH + SYNTHESIZED_CANON**

### How EOS connects to UMH

EOS is a **projection** built on the UMH substrate. The relationship is:

```
UMH Substrate (universal mechanisms)
  |
  +-- substrate/sockets/  (abstract ports)
  |     +-- notification.py
  |     +-- channel_port.py
  |     +-- projection_port.py (planned)
  |
  +-- projections/eos/  (EOS-specific code)
        +-- agents/     (10 department agents + base.py)
        +-- views/      (3 views)
        +-- workflows/  (3 workflows)
        +-- entities.py (entity definitions)
```

### 15 UMH capabilities and their EOS projections

Every generalized UMH substrate capability has a corresponding business-specific EOS projection:

| UMH capability | UMH location | EOS projection |
|---|---|---|
| Signal Processing | substrate/control_plane/router.py | Business event processing (customer inquiries, market signals, operational alerts) |
| Execution Pipeline | substrate/execution/spine.py | Business task execution (SOPs, workflows, approval chains) |
| Governance Engine | substrate/control_plane/governance.py | Business governance (role-based authority, spending limits, compliance) |
| Intelligence Routing | adapters/models/model_router.py | Business intelligence routing (strategic = Opus, routine = fast models) |
| Agent Coordination | substrate/organism/ | Team and agent coordination (CEO + departments + humans) |
| State Management | substrate/state/ | Business state (entity status, financial position, KPI snapshots) |
| Type System | substrate/types.py | Business domain types (Portfolio, Entity, Transaction, KPI as Pydantic models) |
| Context Management | substrate/state/context/ | Business context (which portfolio, entity, user, role is active) |
| Observability | substrate/observability/ | Business observability (dashboards, financial monitors, agent tracking) |
| Feedback Loop | substrate/execution/feedback.py | Business feedback (KPI correlation, strategy effectiveness) |
| Trace Recording | substrate/execution/trace.py | Business audit trail (every decision, transaction, approval traced) |
| Capability Router | substrate/execution/runtime/capability_router.py | Business capability matching (tasks to right agent/team/tool) |
| Notification Port | substrate/sockets/notification.py | Business notifications (email, Slack, Discord, SMS, in-app) |
| Session Management | substrate/execution/bridge/ | Business sessions (entity context, role switching, workspace state) |
| Ontology System | substrate/ontology/ | Business ontology (entities, ventures, markets, customers as knowledge graph) |

### Dependency direction

```
projections/eos/ (EOS projection)
    |  can import from
    v
transports/ (Discord, API/HTTP)
    |  can import from
    v
adapters/ (models, calendar, browser)
    |  can import from
    v
substrate/ (types, control_plane, execution, governance, state)
```

substrate/ NEVER imports from transports/, services/, or projections/.
If substrate needs transport functionality, it uses abstract ports in substrate/sockets/.

**Source: SRC-14.6B-BIZ (umh_business_projection), SRC-UMH-PROJECTION (projections/eos/ structure), CLAUDE.md (architecture layer law)**

---

## Document Verification

This canon synthesizes content from all 7 existing Phase 14.6B artifacts plus Phase 14.4 desired state canon. Coverage:

| Section | Primary sources |
|---|---|
| 1. Product Identity | SRC-14.6B-BIZ, SRC-14.6B-PRE, SRC-OPERATOR-CORRECTIONS |
| 2. Target Users | SRC-14.6B-BIZ, SRC-PHASE-14_4 |
| 3. Product Architecture (19 modules) | SRC-PHASE-14_4, SRC-UMH-PROJECTION, SRC-14.6B-COM |
| 4. Screen Inventory (11+ screens) | SRC-PHASE-14_4, SRC-BEAST-FEATURE |
| 5. Workflow Inventory (8+ workflows) | SRC-PHASE-14_4, SRC-14.6B-ONB |
| 6. Feature Inventory (28 features) | SRC-PHASE-14_4, SRC-OPERATOR-CORRECTIONS, SRC-UMH-PROJECTION |
| 7. Data Concepts (23 entities) | SRC-PHASE-14_4, SRC-14.6B-ONT, SRC-GITHUB-MAIN, SRC-BEAST-FEATURE |
| 8. AI/Agent Architecture (19 agents) | SRC-14.6B-COM, SRC-UMH-PROJECTION, SRC-OPERATOR-CORRECTIONS |
| 9. Business Model | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| 10. Competitive Position | INFERRED_PROFESSIONAL_GAP |
| 11. What EOS Is NOT (12 exclusions) | SRC-14.6B-BIZ, SRC-14.6B-UI, SRC-OPERATOR-CORRECTIONS |
| 12. Source Provenance (13 sources) | All sources |
| Appendix A: MVP | SRC-PHASE-14_4 |
| Appendix B: Code State | SRC-GITHUB-MAIN, SRC-BEAST-FEATURE, SRC-UMH-PROJECTION |
| Appendix C: Tech Stack | SRC-GITHUB-MAIN, SRC-BEAST-FEATURE, SRC-UMH-PROJECTION |
| Appendix D: Onboarding | SRC-14.6B-ONB |
| Appendix E: UI Shell | SRC-14.6B-UI, SRC-OPERATOR-CORRECTIONS |
| Appendix F: Open Questions (19) | All artifacts |
| Appendix G: Implementation Debt (16) | All artifacts |
| Appendix H: UMH Integration (15 projections) | SRC-14.6B-BIZ, SRC-UMH-PROJECTION |

**Signal accounting**: 120 signals tracked in source detail preservation ledger. All signals are referenced or covered by the sections above.

---

*This document is DRAFT. operator_approved = false. allows_implementation = false.*
*No code changes, no infrastructure mutations, no deployments are authorized from this document.*
*Revised in Phase 14.6F to align with 18 ratified P0 decisions (2026-06-04).*
