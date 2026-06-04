# UMH Substrate / Cockpit / Projection Boundary Matrix

**Phase:** 14.6B-UMH
**Status:** DRAFT -- awaiting operator ratification
**Provenance:** OPERATOR_CORRECTION + CODE_RESOLVED_CURRENT_TRUTH

This document explicitly distinguishes the 5 architectural boundaries per operator doctrine.

---

## 1. Universal Substrate

**What it is:** The reusable intelligence/control plane used by Cockpit and all projections.
**Owner:** UMH platform
**User type:** Internal -- consumed by Cockpit and projections, not directly by end-users
**Public/Private:** PRIVATE -- internal infrastructure
**Data ownership:** Substrate-level data (traces, memories, governance decisions, audit logs, type registry, component registry)
**Capability ownership:** Full capability pipeline (ingestion through feedback/learning)
**Execution authority:** Governed by risk classes and permission tiers
**Auth model:** Internal -- no external-facing auth on substrate itself
**Permissions model:** PermissionTier (READ/DRAFT/EXECUTE/COMMIT) with RiskClass (NEGLIGIBLE through CRITICAL)
**UX ownership:** None -- substrate has no UI, only API
**Integration pathway:** Python imports from substrate/ package
**Code location:** substrate/ (696 files, 206,602 lines)
**Examples:** Signal routing, memory recall, trace recording, governance classification, execution spine
**What must NOT happen:** Substrate must never import from transports/, services/, or projections/ (except via abstract ports in substrate/sockets/). Substrate must never contain projection-specific logic, instance-specific values, or UI code.

## 2. Cockpit / Private Jarvis Interface

**What it is:** The private operator control surface into the full UMH ecosystem.
**Owner:** Operator (Antony)
**User type:** Single operator / founder
**Public/Private:** PRIVATE -- operator-only
**Data ownership:** Operator commands, operator decisions, approval history, operator preferences
**Capability ownership:** Universal -- can invoke any substrate capability, inspect any projection, trigger any workflow
**Execution authority:** Full -- operator has COMMIT tier, can approve/deny any action
**Auth model:** API key + operator token + dev bypass (private IPs)
**Permissions model:** Operator has all permissions; rate limiting on certain actions
**UX ownership:** Private command center -- panels, HUD, voice command, command palette
**Integration pathway:** REST API (transports/api/cockpit*.py) + WebSocket + Electron/React frontend
**Code location:** transports/api/cockpit*.py (12 files, ~6,200 lines) + cockpit/src/ (98 files) + services/operator_api.py (740 lines)
**Examples:** Approve high-risk action, inspect agent state, launch cross-projection workflow, use voice command, monitor infrastructure
**What must NOT happen:** Cockpit must never be exposed publicly. Cockpit must not replace projection UX for end-users. Cockpit must not bypass audit logging. Cockpit must not hardcode instance context.

## 3. Projection Runtime Layer

**What it is:** The shared integration fabric through which public products use UMH safely.
**Owner:** UMH platform (shared infrastructure)
**User type:** Projection applications (programmatic consumers)
**Public/Private:** INTERNAL -- integration infrastructure
**Data ownership:** Integration state (connection status, watermarks, correlation maps)
**Capability ownership:** Declared capabilities per projection manifest
**Execution authority:** Constrained by projection manifests and governance
**Auth model:** Database URL per projection, env-var configured
**Permissions model:** Projection-scoped -- each projection declares what signals it emits and what capabilities it exposes
**UX ownership:** None -- this is the integration protocol layer
**Integration pathway:** ProductConnectionManager + integration manifests + polled tables + signal/capability socket pattern
**Code location:** substrate/integrations/product_connections.py + projections/*/integration/ + substrate/sockets/projection_port.py
**Examples:** EOS CRM poller emitting signals, CreatorOS creating a post via capability handler, LyfeOS logging a reflection
**What must NOT happen:** Projections must not directly access substrate internals. Projections must not share data across projections without governance. Integration layer must not bypass risk classification.

## 4. Public Projections / Products

**What it is:** Domain-specific SaaS products used by customers/users.
**Owner:** Product-specific teams/entities
**User type:** Multiple end-users, teams, organizations
**Public/Private:** PUBLIC -- customer-facing
**Data ownership:** Product-specific domain data (CRM contacts, posts, quests, daily logs, etc.)
**Capability ownership:** Domain-specific capabilities within their product scope
**Execution authority:** User-scoped -- governed by product-specific permissions
**Auth model:** Product-specific (session tokens, OAuth, magic links)
**Permissions model:** Product-specific RBAC
**UX ownership:** Full -- own their entire user experience (onboarding, dashboards, workflows, mobile/web)
**Integration pathway:** Integration manifests declaring signals and capabilities
**Code location:** projections/ (48 files) + separate SaaS codebases
**Examples:** EOS user manages sales pipeline; CreatorOS creator publishes content; LyfeOS user tracks daily stats
**What must NOT happen:** Projections must not expose UMH internals to end-users. Projections must not access other projections' data without UMH governance. Projections must not bypass approval gates. Projections must not be reduced to dumb frontends.

## 5. External Tool Layer

**What it is:** Software/services operated through agents, adapters, APIs, CLI, MCP, browser/computer use.
**Owner:** Third parties (Google, Discord, Notion, GitHub, etc.)
**User type:** UMH adapters acting on behalf of operator or projections
**Public/Private:** EXTERNAL -- third-party systems
**Data ownership:** Third-party data -- UMH accesses via APIs/adapters
**Capability ownership:** Third-party capabilities made available through UMH adapters
**Execution authority:** Governed -- external actions require appropriate risk classification and may require approval
**Auth model:** API keys, OAuth tokens, session credentials per service
**Permissions model:** External service permissions (Google OAuth scopes, Discord bot permissions, etc.)
**UX ownership:** Third-party UX -- UMH interacts via APIs, not UIs (except browser/computer-use agents)
**Integration pathway:** adapters/ (89 files, 18,723 lines), MCP servers, CLI tools, browser agents
**Code location:** adapters/ (google_workspace, calendar, notion, models, browser_exports, capabilities, tool_adapters, scrapling, higgsfield, notebooklm)
**Examples:** Google Calendar meeting scheduling, Notion document sync, Discord message posting, GitHub source ingestion, Higgsfield video generation
**What must NOT happen:** External actions must not bypass governance. Credentials must not be hardcoded. External services must not become single points of failure. Browser/computer-use agents must have explicit safety boundaries.

---

## Cross-Boundary Rules

1. **Dependency direction is one-way downward:** projections -> transports -> adapters -> substrate
2. **Substrate never reaches outward** -- use abstract ports in substrate/sockets/ instead
3. **Data flows are governed** -- projection data enters UMH only through declared signal types
4. **External actions require risk classification** -- EXTERNAL_COMMUNICATION and FINANCIAL are blocking by default
5. **Cross-projection data sharing requires explicit policy** -- no automatic data sharing between projections
6. **Cockpit sees everything; projections see their domain** -- operator has universal visibility
7. **End-users never see UMH internals** -- substrate implementation details stay behind the projection boundary
