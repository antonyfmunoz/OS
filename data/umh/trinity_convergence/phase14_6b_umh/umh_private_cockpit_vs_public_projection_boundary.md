# UMH Private Cockpit vs Public Projection Boundary

**Phase:** 14.6B-UMH (revised 14.6F)
**Status:** DRAFT -- awaiting operator ratification
**Provenance:** OPERATOR_CORRECTION + CODE_RESOLVED_CURRENT_TRUTH + DEC-146C-001/003 ratification
**Date:** 2026-06-03

Revised in Phase 14.6F to align with 18 ratified P0 decisions (2026-06-04).

---

## Purpose

This document codifies the hard boundary between the private operator Cockpit (the operator's reality-model interface) and the public projection products (EOS, CreatorOS, LyfeOS -- instance reality models for specific domains). The boundary exists because Cockpit and projections serve fundamentally different audiences, have different security models, and must never be conflated.

**Reality-model framing (DEC-146C-001/003):** Cockpit is the operator's interface into the full UMH reality model. Projections are domain-specific instance reality models. The boundary is not merely UI separation -- it is the boundary between universal reality-model access (Cockpit) and domain-scoped reality-model access (projections). Cockpit sees all 12 reality layers; projections see the subset relevant to their domain.

Related documents:
- `umh_substrate_cockpit_projection_boundary_matrix.md` -- 5-layer boundary matrix (substrate / cockpit / projection runtime / projection product / cross-projection)
- `umh_projection_ecosystem_doctrine.md` -- what projections are and are not
- `umh_projection_data_boundary_privacy_model.md` -- data category isolation rules
- `umh_cockpit_jarvis_doctrine.md` -- what Cockpit is and is not

---

## Boundary Matrix

| Dimension | Cockpit (Private) | Projections (Public) |
|-----------|-------------------|---------------------|
| **Owner** | Operator (Antony) | Projection-specific users/customers |
| **User type** | Single operator / founder | Multiple end-users, teams, organizations |
| **Public/Private** | PRIVATE -- operator-only access | PUBLIC -- customer-facing SaaS products |
| **Data ownership** | UMH substrate data, cross-product intelligence, audit logs, source truth, production truth | Projection-specific domain data (CRM contacts for EOS, posts for CreatorOS, quests for LyfeOS) |
| **Capability ownership** | Full universal capability pipeline -- ingestion, routing, governance, execution, memory, orchestration | Domain-specific capabilities declared via integration manifest |
| **Execution authority** | Full -- can approve/deny any action, override governance, trigger any workflow | Constrained -- governed by permission tiers, risk classes, and approval gates |
| **Auth model** | API key + operator token + dev bypass from private IPs | Per-projection auth (session tokens, magic links, OAuth) for end-users |
| **Permissions model** | PermissionTier (READ/DRAFT/EXECUTE/COMMIT) -- operator has COMMIT by default | Projection-specific RBAC per their user model |
| **UX ownership** | Private command center -- panels, HUD, voice, command palette | Public domain UX -- onboarding, dashboards, workflows, mobile/web |
| **Integration pathway** | Direct substrate API + organism bridge + WebSocket | Integration manifests + polled tables + signal/capability socket pattern |
| **Examples** | Inspect all agent state, launch cross-projection workflow, approve high-risk action, use browser agent, operate external tools | EOS user manages sales pipeline, CreatorOS creator schedules post, LyfeOS user logs daily reflection |
| **What must NOT happen** | Cockpit must not be exposed publicly. Cockpit must not replace projection UX for end-users. Cockpit must not bypass audit logging. | Projections must not access other projections' data without UMH governance. Projections must not bypass risk classification. Projections must not expose UMH substrate internals to end-users. |

---

## Key Boundaries

### 1. Cockpit is not a public product -- it is the reality-model interface

Cockpit is the operator's interface into UMH's full reality model (DEC-146C-001, DEC-146C-003). It renders all 12 reality layers for the operator and accepts commands that mutate reality-model state through governed execution. It is not a customer-facing product and must never be exposed to end-users of EOS, CreatorOS, or LyfeOS. The Cockpit domain (universalmetaharness.tech) is operator-only. No end-user should ever see a Cockpit URL, Cockpit panel, or Cockpit error message. Per DEC-146C-003, Cockpit without a reality model is only a dashboard -- both must be viable together.

**Current implementation:** Three-tier auth (API key + operator token + dev bypass) ensures no unauthenticated access. Dev bypass is restricted to private Tailscale IPs only.

### 2. Projections are not dumb frontends

Projections own real product logic -- their own data models, workflows, permissions, onboarding, analytics, and customer experience. They are not thin wrappers around Cockpit. Each projection is a standalone SaaS product that happens to use UMH as its intelligence substrate.

**Current implementation:**
- EOS: Full agent/view/workflow stack (10 department agents, 3 views, 3 workflows) + separate TypeScript/React SaaS codebase
- CreatorOS: Integration layer only (signals, capabilities, outcomes) + separate SaaS codebase (shared/schema.ts)
- LyfeOS: Deployed standalone at lyfeos.net (35 database tables, working app) with partial UMH integration stubs

### 3. Cockpit sees everything; projections see their domain

The operator (via Cockpit) can inspect and act across all projections simultaneously. Individual projections can only see and act within their own domain, unless UMH explicitly orchestrates cross-domain work through governed channels.

**Cockpit cross-projection visibility:**
- ProductConnectionManager provides unified status across all three projections
- 276 API endpoints across 12 route files cover every substrate subsystem
- 27 frontend panels provide full ecosystem observability

**Projection isolation:**
- Each projection declares what signals it emits and what capabilities it exposes via integration manifest
- Projection data enters UMH only through declared signal types
- UMH acts on projections only through declared capability types
- No projection can query another projection's data directly

### 4. UMH intelligence is shared; UX is separate

All projections share the same intelligence pipeline (ingestion, model routing, governance, execution, memory, trace, feedback) through UMH substrate. But each projection owns its own user experience design, onboarding flow, customer journey, and visual identity.

**Shared (substrate):** Signal routing, memory recall, trace recording, governance classification, execution spine, model routing, ingestion pipeline
**Separate (per projection):** UI components, onboarding, navigation, domain workflows, customer-facing dashboards, mobile/web apps

### 5. Data flows are governed

- Projection data enters UMH only through declared signal types (see `umh_projection_data_boundary_privacy_model.md` for the 7 data categories)
- UMH acts on projections only through declared capability types
- Cross-projection data sharing requires explicit governance policy
- Sensitive data (LyfeOS health/therapy data, EOS employee SSNs, CreatorOS payment details) has a HARD BOUNDARY -- must never enter UMH under any circumstances
- Signal emitters are responsible for filtering sensitive data before emission

### 6. Operator authority vs end-user authority

- The operator (Cockpit) has universal authority within governance constraints -- COMMIT tier by default
- End-users have projection-scoped authority within their projection's permission model
- High-risk actions (RiskClass.HIGH or CRITICAL) require operator approval regardless of who or what initiates them
- The operator can override governance decisions; end-users cannot

---

## Implementation Truth

### Current Cockpit Implementation

| Metric | Value |
|--------|-------|
| Backend API endpoints | 276 across 12 Python route files |
| Frontend panels | 27 |
| Frontend components | 26 |
| Frontend stores | 19 |
| Auth tiers | 3 (API key + operator token + dev bypass) |
| WebSocket | Live pulse at 2-second interval |
| Deployed domain | universalmetaharness.tech |
| Backend LOC | ~6,200 lines across cockpit route files |
| Frontend location | cockpit/src/ (Electron + React + TypeScript + Vite) |

### Current Projection Implementation

| Projection | UMH Integration Status | Standalone Status | Code Location |
|------------|----------------------|-------------------|---------------|
| EOS | Full: 10 agents, 3 views, 3 workflows, entity hierarchy, integration layer | Separate SaaS codebase (TypeScript/React) | projections/eos/ |
| CreatorOS | Integration-only: manifest, signal/capability/outcome handlers | Separate SaaS codebase (shared/schema.ts) | projections/creatoros/ |
| LyfeOS | Partial: integration stubs, manifest + signals only | Deployed at lyfeos.net (35 tables, working app) | projections/lyfeos/ |

### Boundary Violations in Current Code

1. **Instance context hardcoded in /profile endpoint.** Cockpit API /profile endpoint returns hardcoded founder name and company names. Should load from BIS at runtime. Violates Instance Context Law.

2. **EOS-specific endpoints in cockpit.py.** Endpoints `/api/umh/eos/*` (pipeline, KPIs, activity) are directly in cockpit.py rather than a projection-specific route file. This does not violate the boundary per se (Cockpit should be able to view projection data), but it conflates projection-specific API surface with core Cockpit routes. Architectural debt.

3. **ProductConnectionManager dependency direction.** `substrate/integrations/product_connections.py` may import from projections/ -- an upward dependency violation. RESOLVED per DEC-146B-UMH-005 (ratified 2026-06-04): abstract port pattern via `substrate/sockets/projection_port.py`. Implementation not yet started.

4. **Missing projection panels.** No CreatorOS or LyfeOS specific cockpit panels exist yet. Only EOS views are surfaced in the Cockpit frontend. Not a violation, but an incompleteness -- Cockpit should provide cross-projection visibility.

---

## Anti-Patterns This Boundary Prevents

### Anti-Pattern 1: Cockpit as public app
"Let's just give customers a login to the Cockpit."
**Why wrong:** Cockpit exposes substrate internals (agent state, governance decisions, execution traces, infrastructure details) that end-users must never see. Cockpit auth is single-operator, not multi-tenant.

### Anti-Pattern 2: Projection as Cockpit skin
"EOS doesn't need its own dashboard -- users can use the Cockpit panels."
**Why wrong:** Cockpit is designed for one operator managing the entire ecosystem. Projection UX is designed for domain-specific workflows by domain-specific users. The information density, navigation model, and permission model are completely different.

### Anti-Pattern 3: Substrate bypass
"Let the EOS frontend call substrate APIs directly."
**Why wrong:** Projections interact with UMH through declared integration manifests (signals, capabilities, outcomes). Direct substrate API calls bypass governance, risk classification, and data boundary enforcement.

### Anti-Pattern 4: Cross-projection data leakage
"Let EOS see CreatorOS audience data to improve sales targeting."
**Why wrong:** Cross-projection data sharing requires explicit governance policy. Each projection's data boundary is sovereign. The operator can see everything via Cockpit, but projections cannot see each other without governed channels.

### Anti-Pattern 5: Cockpit replacing projection logic
"Put the EOS CRM workflow in Cockpit since it's already there."
**Why wrong:** Cockpit observes and governs. Projections own domain logic. If CRM workflow lives in Cockpit, it cannot serve EOS end-users without exposing Cockpit.

---

## OPEN QUESTIONS -- Operator Decision Required

1. **Projection panel strategy.** Should each projection have its own Cockpit panel section (EOS Panel, CreatorOS Panel, LyfeOS Panel), or should projection visibility be unified into a single cross-projection view? Current state: only EOS-specific views exist.

2. **EOS endpoint extraction.** Should cockpit.py's EOS-specific endpoints (`/eos/pipeline`, `/eos/kpis`, `/eos/activity`) be extracted to a projection-specific route file (e.g., `cockpit_eos_routes.py`)? This would improve separation but adds another route file.

3. **Cockpit MVP scope.** What is the minimum Cockpit MVP -- which panels and capabilities must work before any implementation phase begins? Current 27 panels may be over-scoped for the pre-revenue phase where operator attention is the binding constraint.

4. **Projection auth delegation.** When projections need to trigger UMH capabilities (e.g., EOS needs model routing for an AI feature), should they use a per-projection service account, or should all projection requests route through a shared integration gateway?

5. **Cockpit mobile access.** Is iPhone/Termius SSH access sufficient for mobile Cockpit operations, or should there be a mobile-optimized Cockpit view for quick approvals and status checks?
