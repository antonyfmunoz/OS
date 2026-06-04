# UMH Projection Ecosystem Doctrine

- **Phase:** 14.6B-UMH (revised 14.6F)
- **Status:** RATIFIED -- all 18 P0 decisions operator-approved (2026-06-04)
- **Provenance:** OPERATOR_CORRECTION + CODE_RESOLVED_CURRENT_TRUTH + DEC-146C-001/002/003 ratification
- **Revision note:** Revised in Phase 14.6F to align with 18 ratified P0 decisions (2026-06-04).

---

## Core Doctrine

Universal Meta Harness (UMH) is the integrated AI-native system whose core functional purpose is to build, maintain, and act through a reality-isomorphic approximation of reality (DEC-146C-001, RATIFIED 2026-06-04). Product name: "Universal Meta Harness" (DEC-146B-UMH-001, RATIFIED 2026-06-04). Functional identity: reality-isomorphic intelligence harness. UMH attempts to model reality across physical, digital, cognitive, biological, social, economic, symbolic, operational, software, memory, source-truth, and OS-level layers. All subsystems -- orchestration, governance, execution, memory, adapters, agents, Cockpit, and projections -- are capabilities and organs serving this reality model. The reality model is the central organizing model through which UMH understands intent, state, constraints, resources, possible actions, consequences, and feedback.

UMH is NOT:
- A Cockpit UI only
- A chatbot
- A SaaS app
- An EOS/business app
- A public social platform
- A public ads platform
- A CRM, dashboard, or tool wrapper
- A collection of unrelated agents or modules
- A public mega-app
- Merely an orchestration kernel or operational tooling model

UMH IS:
- The private reality-isomorphic intelligence harness that powers all projections
- A reality-modeling system that governs execution through its understanding of reality state
- The operator/Jarvis system whose interface (Cockpit) renders the reality model for human use
- The shared capability pipeline owner -- all capabilities serve reality-model construction and actuation
- The cross-system coordination brain whose coordination authority derives from its reality model

## Projection Definition

Projections are domain-specific views of the UMH reality model, manifested as public SaaS products. Each projection is an instance reality model -- it carries the same isomorphic ambition as UMH but from the perspective/context of a specific domain, user base, and use case.

Projections:
- Package UMH reality-model capabilities into safe, purpose-built user experiences
- Own their own domain UX, workflows, permissions, customer experience, and data models
- Are NOT dumb frontends -- they have real product logic
- Are NOT the limit of UMH -- UMH can privately orchestrate beyond any single projection
- Can function independently (degraded) if UMH is unavailable
- Feed observations back into the UMH reality model, enriching the system's understanding of reality

## Current Projections

### EntrepreneurOS (EOS)
- Domain: Business/company/operations management
- Status: Most mature projection in /opt/OS codebase
- Code location: projections/eos/
- Components: 10 department agents, 3 views, 3 workflows, entity hierarchy, full integration
- Separate SaaS codebase exists (TypeScript/React, Drizzle ORM)
- **Canonical SaaS codebase:** Beast branch (DEC-146B-EOS-001, RATIFIED 2026-06-04). GitHub main is stale/deprecated.
- **Auth:** Clerk confirmed as production auth provider (DEC-146B-EOS-003, RATIFIED 2026-06-04)
- **MVP scope:** R1-R5 confirmed (DEC-146B-EOS-002, RATIFIED 2026-06-04)

### CreatorOS
- Domain: Creator/content/community/commerce platform
- Status: Integration-only in /opt/OS codebase
- Code location: projections/creatoros/
- Components: Integration manifest, signal/capability/outcome handlers, no agents/views/workflows
- Separate SaaS codebase exists (shared/schema.ts referenced)
- **MVP scope:** Content + Community + Courses + Sales, 8-12 weeks (DEC-146B-COS-001, RATIFIED 2026-06-04)
- **Auth:** Clerk first, blocks all other implementation (DEC-146B-COS-002, RATIFIED 2026-06-04)
- **Build sequence:** Auth -> Split -> Tests -> Content -> Community -> Courses -> Stripe -> Analytics (DEC-146B-COS-004, RATIFIED 2026-06-04)
- **Source code:** Verify baseline, then GitHub as canonical (DEC-146B-COS-003, RATIFIED 2026-06-04)

### LyfeOS
- Domain: Personal life/transformation/wellness
- Status: Integration-only in /opt/OS (most mature as standalone SaaS)
- Code location: projections/lyfeos/ (integration stubs)
- Deployed: lyfeos.net on Replit (35 database tables, working app)
- Phase 14.6B-LyfeOS produced 52 detailed artifacts
- **PRD:** v2.0 is canonical direction; v1.0 is historical context only (DEC-146B-LOS-001, RATIFIED 2026-06-04)
- **Auth:** Clerk migration after CreatorOS proves the pattern (DEC-146B-LOS-002, RATIFIED 2026-06-04)
- **Infrastructure:** Fly.io is the Trinity standard, migrating from Replit (DEC-146B-LOS-003, RATIFIED 2026-06-04)

## UMH / Projection Relationship

### What UMH Owns (Reality Model + Capability Pipeline)

Execution flows through a single unified path: Substrate -> SignalRouter -> Spine (DEC-146B-UMH-003, RATIFIED 2026-06-04).

1. Ingestion
2. Signal interpretation
3. Decomposition
4. Primitive extraction
5. Context assembly
6. Memory
7. Model routing (10 providers, dual fast/heavy path)
8. Capability routing
9. Tool routing
10. Agent orchestration
11. Workflow orchestration
12. Governed execution (simulation, deliberation council, approval gates)
13. Audit trails
14. Source truth / production truth management
15. Cross-system coordination
16. Projection registration
17. Adapter contracts
18. Data boundary enforcement
19. Observability / error recording
20. Feedback / learning loop

### What Projections Own
1. Domain UX design
2. Domain onboarding flows
3. Domain data models (their own database tables)
4. Domain workflows specific to their product
5. Domain permissions for their users
6. Product-specific analytics
7. Public/customer-facing experience
8. Monetization / business model
9. Integration points with UMH (they declare what they need)

### Correct UMH <-> Projection Relationship

"UMH owns the universal reality model; projections are domain-specific lenses onto that reality model. UMH has universal reality-modeling and orchestration reach, but not universal public product-interface ownership."

Example -- Running ads:
- UMH is NOT a public ads product
- But UMH CAN orchestrate: CreatorOS data + EOS data + external ad platforms + browser/computer-use agents + campaign workflows + approval gates + analytics + optimization loops
- CreatorOS may own the public creator-facing ads/marketplace UX
- EOS may own the business operations/budget management

Example -- Social/content:
- UMH is NOT the public social platform
- CreatorOS IS the public social/content/community/commerce platform
- But a CreatorOS embedded AI can use UMH's pipeline to: ingest analytics, decompose signals, reason over performance, generate recommendations, trigger approved workflows

Example -- Life OS:
- UMH is NOT the user-facing life companion
- LyfeOS IS the user-facing life OS
- But UMH can power: ingestion, decomposition, memory, signal extraction, profile seeding, context synthesis, integration governance

Example -- Business operations:
- UMH is NOT the business management app
- EOS IS the business/company operating experience
- But UMH can power: decomposition, role/workflow generation, agent execution, approvals, source truth, production truth, cross-system governance

## How Projections Access UMH

Current implementation (ProductConnectionManager -- DEC-146B-UMH-005 ratified abstract port pattern via substrate/sockets/projection_port.py):
- Integration manifests define signals and capabilities per projection
- Polled tables provide signal sources (EOS: CRM tables, CreatorOS: posts/products/revenue, LyfeOS: quests/daily_logs/stats)
- Signal emitters convert table rows to SignalEnvelopes
- Capability handlers execute UMH-initiated actions back into projection databases
- Outcome receivers handle writeback with dual audit
- **Ratified direction (DEC-146B-UMH-005):** ProductConnectionManager dependency violation resolved via abstract port pattern in substrate/sockets/projection_port.py

Future access methods may include:
- Internal API
- Public/private API
- MCP servers
- CLI
- Event streams / webhooks
- Database connectors
- Browser/computer-use agents
- Adapter SDK
- Scheduled polling
- Push events
- Embedded AI assistants
- User-scoped AI companions

## Cockpit's Role

Cockpit is the private operator/Jarvis interface into UMH's reality model (DEC-146C-003, RATIFIED 2026-06-04). It is part of the indivisible Stage 1 organism -- Cockpit without a reality model is only a dashboard; a reality model without Cockpit is inaccessible to the operator.

Cockpit MAY:
- Inspect projection state
- Ask cross-domain questions
- Launch workflows
- Coordinate agents across projections
- Review approvals
- Inspect source truth and production truth
- Use browser/computer-use agents
- Use coding agents
- Use APIs/MCP/CLI
- Operate external tools
- Orchestrate EOS/CreatorOS/LyfeOS workflows

Cockpit is NOT the public customer-facing product surface. Cockpit is NOT merely a dashboard -- it is the reality-model interface through which the operator observes, commands, and governs the entire UMH ecosystem.

## One Coherent Ecosystem

Do not interpret EOS, CreatorOS, LyfeOS, and UMH as unrelated systems.
They are one coherent ecosystem organized around a shared reality model:
- One universal private reality-isomorphic intelligence harness (UMH)
- Multiple public/domain-specific product surfaces (projections as instance reality models)
- Shared reality model and intelligence pipeline
- Separate product UX
- Explicit data boundaries
- Governed cross-system orchestration

**Materialization Principle (DEC-146C-002, RATIFIED 2026-06-04):** If a human can imagine an outcome, UMH should attempt to simulate the path from imagination to materialization. Lack of current knowledge, resources, tools, capital, information, skill, access, or time does not invalidate the intent -- it creates typed gaps and acquisition paths. UMH does not treat missing capability as terminal failure. It classifies the gap, identifies what must be acquired or learned, generates the highest-leverage path, and governs execution. If an outcome violates physical reality, law, safety, ethics, or non-negotiable constraints, UMH states the boundary clearly and proposes the nearest lawful/safe/materializable alternative.
