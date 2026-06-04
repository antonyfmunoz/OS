# UMH Projection Ecosystem Doctrine

- **Phase:** 14.6B-UMH
- **Status:** DRAFT -- awaiting operator ratification
- **Provenance:** OPERATOR_CORRECTION + CODE_RESOLVED_CURRENT_TRUTH

---

## Core Doctrine

UMH (Universal Meta Harness) is the private universal intelligence substrate, orchestration kernel, governed execution control plane, and operator/Jarvis system that powers, integrates with, and coordinates the Trinity ecosystem.

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

UMH IS:
- The private universal substrate that powers all projections
- The governed execution control plane
- The operator/Jarvis system
- The shared capability pipeline owner
- The cross-system coordination brain

## Projection Definition

Projections are public/domain-specific SaaS products that:
- Package UMH capabilities into safe, purpose-built user experiences
- Own their own domain UX, workflows, permissions, customer experience, and data models
- Are NOT dumb frontends -- they have real product logic
- Are NOT the limit of UMH -- UMH can privately orchestrate beyond any single projection
- Can function independently (degraded) if UMH is unavailable

## Current Projections

### EntrepreneurOS (EOS)
- Domain: Business/company/operations management
- Status: Most mature projection in /opt/OS codebase
- Code location: projections/eos/
- Components: 10 department agents, 3 views, 3 workflows, entity hierarchy, full integration
- Separate SaaS codebase exists (TypeScript/React, Drizzle ORM)

### CreatorOS
- Domain: Creator/content/community/commerce platform
- Status: Integration-only in /opt/OS codebase
- Code location: projections/creatoros/
- Components: Integration manifest, signal/capability/outcome handlers, no agents/views/workflows
- Separate SaaS codebase exists (shared/schema.ts referenced)

### LyfeOS
- Domain: Personal life/transformation/wellness
- Status: Integration-only in /opt/OS (most mature as standalone SaaS)
- Code location: projections/lyfeos/ (integration stubs)
- Deployed: lyfeos.net on Replit (35 database tables, working app)
- Phase 14.6B-LyfeOS produced 52 detailed artifacts

## UMH / Projection Relationship

### What UMH Owns (Shared Capability Pipeline)
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

"UMH has universal orchestration reach, but not universal public product-interface ownership."

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

Current implementation (ProductConnectionManager):
- Integration manifests define signals and capabilities per projection
- Polled tables provide signal sources (EOS: CRM tables, CreatorOS: posts/products/revenue, LyfeOS: quests/daily_logs/stats)
- Signal emitters convert table rows to SignalEnvelopes
- Capability handlers execute UMH-initiated actions back into projection databases
- Outcome receivers handle writeback with dual audit

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

Cockpit is the private operator/Jarvis interface into the FULL UMH ecosystem.

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

Cockpit is NOT the public customer-facing product surface.

## One Coherent Ecosystem

Do not interpret EOS, CreatorOS, LyfeOS, and UMH as unrelated systems.
They are one coherent ecosystem:
- One universal private substrate
- Multiple public/domain-specific product surfaces
- Shared intelligence pipeline
- Separate product UX
- Explicit data boundaries
- Governed cross-system orchestration
