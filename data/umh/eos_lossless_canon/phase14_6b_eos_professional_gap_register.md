---
phase: "14.6B-EOS"
status: "DRAFT"
operator_approved: false
allows_implementation: false
date: "2026-06-04"
provenance: "INFERRED_PROFESSIONAL_GAP"
description: "Exhaustive register of every gap between current EOS code state and professional production standard. 83 gaps across 12 categories, each with severity, current state, target state, provenance, and blocker classification."
---

# EOS Professional Gap Register

Every gap between current code and professional production standard.

Provenance: INFERRED_PROFESSIONAL_GAP unless otherwise noted. These are gaps
identified from professional engineering standards, production SaaS best
practices, and security baselines that no source document explicitly stated
but that a production business-in-a-box operating system requires.

Cross-references:
- phase14_6b_eos_current_implementation_truth.json (code state)
- phase14_6b_eos_auth_security_truth.json (auth/security gaps)
- phase14_6b_eos_13_layer_mapping.json (13-layer gap analysis)
- phase14_6b_eos_agent_architecture_spec.json (agent gaps)
- phase14_6b_eos_data_ontology.json (schema gaps)
- phase14_6b_eos_governance_permissions_model.json (permission gaps)
- phase14_6b_eos_workflow_sop_engine_spec.json (workflow gaps)
- phase14_6b_eos_analytics_kpi_spec.json (analytics gaps)
- phase14_6b_eos_ui_ux_aesthetic_canon.json (design gaps)
- phase14_6b_eos_api_contract_map.json (API gaps)

Severity scale:
- CRITICAL: Blocks production deployment or creates unacceptable risk
- HIGH: Must be resolved before public release
- MEDIUM: Should be resolved before scaling beyond solo founder
- LOW: Professional standard gap, addressable post-launch

Blocker classifications:
- BLOCKS_DEPLOYMENT: Cannot deploy to production without resolution
- BLOCKS_MULTI_USER: Cannot onboard second user without resolution
- BLOCKS_SCALE: Cannot scale beyond early adopters without resolution
- NON_BLOCKING: Professional debt, not a gate

---

## Auth / Security

| ID | Category | Gap | Severity | Current State | Target State | Provenance | Blocker |
|----|----------|-----|----------|---------------|--------------|------------|---------|
| GAP-SEC-001 | Auth/Security | No real authentication on UMH platform API | CRITICAL | x-org-id header self-asserted identity. Any client that knows a valid org UUID can impersonate the owner. userId derived from org ownerId, not from an authenticated session. | Clerk JWT verification via @clerk/backend. userId extracted from verified token. orgId from Clerk Organization membership. Bearer token in Authorization header. | CODE_RESOLVED_CURRENT_TRUTH | BLOCKS_DEPLOYMENT |
| GAP-SEC-002 | Auth/Security | RLS bypass on DATABASE_APP_URL fallback | CRITICAL | DATABASE_APP_URL falls back to DATABASE_URL (neondb_owner with BYPASSRLS). If env var not set, all RLS policies silently disabled. Every query sees all tenant data. | DATABASE_APP_URL required. Startup fails if missing. No fallback to admin pool for application queries. | CODE_RESOLVED_CURRENT_TRUTH | BLOCKS_DEPLOYMENT |
| GAP-SEC-003 | Auth/Security | No rate limiting on any endpoint | HIGH | Zero rate limiting middleware. Every endpoint unbounded. AI-powered endpoints (chat/converse) trigger LLM calls with no throttle. Attacker can exhaust server resources or rack up API costs. | Hono rate-limiter middleware or Fly.io/Cloudflare proxy-level limits. Per-org and per-IP limits. Strict limits on AI endpoints. | CODE_RESOLVED_CURRENT_TRUTH | BLOCKS_DEPLOYMENT |
| GAP-SEC-004 | Auth/Security | users and portfolios tables have no RLS policies | HIGH | 14 of 16 tables have RLS enabled. users and portfolios excluded from TENANT_TABLES. In multi-tenant deployment, any org can query any user email/name and any portfolio data. | Add portfolios to TENANT_TABLES with org_id scoping. Users table: membership-based RLS policy (user visible to orgs they belong to). | CODE_RESOLVED_CURRENT_TRUTH | BLOCKS_MULTI_USER |
| GAP-SEC-005 | Auth/Security | Placeholder password for eos_app DB role | HIGH | migrate.ts creates eos_app role with password 'REPLACE_WITH_STRONG_PASSWORD'. If migration runs without manual intervention, DB role has known weak credential. | Read password from EOS_APP_ROLE_PASSWORD env var. Refuse to create role if env var missing. | CODE_RESOLVED_CURRENT_TRUTH | BLOCKS_DEPLOYMENT |
| GAP-SEC-006 | Auth/Security | No security headers configured | MEDIUM | No Content-Security-Policy, X-Frame-Options, X-Content-Type-Options, Strict-Transport-Security, Referrer-Policy, Permissions-Policy. No Hono secureHeaders() middleware. | Add Hono secureHeaders() middleware from hono/secure-headers. CSP configured for EOS frontend domain. HSTS enabled. | INFERRED_PROFESSIONAL_GAP | BLOCKS_DEPLOYMENT |
| GAP-SEC-007 | Auth/Security | Error handler leaks internal details | MEDIUM | Global onError handler returns err.message to client. Database errors, file paths, stack traces may be exposed in error responses. | Sanitize error messages in production. Return generic 'Internal Server Error' to client. Log full error server-side. NODE_ENV check controls verbosity. | CODE_RESOLVED_CURRENT_TRUTH | BLOCKS_DEPLOYMENT |
| GAP-SEC-008 | Auth/Security | No input validation middleware | MEDIUM | Most API routes cast req.json() to TypeScript types with 'as'. No runtime validation despite Zod being a dependency. Malformed or malicious payloads pass to business logic and DB. | Zod validation middleware on all POST/PUT/PATCH routes. withValidation() helper pattern. Zod schemas co-located with route handlers. | CODE_RESOLVED_CURRENT_TRUTH | BLOCKS_DEPLOYMENT |
| GAP-SEC-009 | Auth/Security | No CORS configuration | MEDIUM | No CORS middleware in server.ts. Hono defaults to no CORS headers. Browser cross-origin requests fail, but server-to-server requests unrestricted. | Explicit CORS config. Allowlist cockpit domain (universalmetaharness.tech), EOS production domain, localhost for dev. Deny all others. | CODE_RESOLVED_CURRENT_TRUTH | BLOCKS_DEPLOYMENT |
| GAP-SEC-010 | Auth/Security | No dependency vulnerability scanning | LOW | No npm audit in CI. No Dependabot/Renovate. 7 runtime dependencies have low surface area but no automated CVE check. | npm audit in CI pipeline. Dependabot or Renovate for automated security updates. Weekly audit report. | INFERRED_PROFESSIONAL_GAP | NON_BLOCKING |
| GAP-SEC-011 | Auth/Security | No API key authentication for programmatic access | LOW | Only header-based org identity (placeholder). No mechanism for third-party integrations, CI/CD pipelines, or API consumers to authenticate via API keys. | API key table with rotation mechanism, scope-limited permissions, per-key rate limits. Separate from Clerk session auth. | INFERRED_PROFESSIONAL_GAP | BLOCKS_SCALE |

---

## Testing

| ID | Category | Gap | Severity | Current State | Target State | Provenance | Blocker |
|----|----------|-----|----------|---------------|--------------|------------|---------|
| GAP-TST-001 | Testing | Near-zero test coverage on EOS SaaS application | CRITICAL | GitHub main: 0 tests. Beast branch: Vitest + Playwright configured but coverage unknown. UMH projection: 4 dedicated tests (import/register). No end-to-end tests. No integration tests for API routes. | Unit tests for all route handlers. Integration tests for DB operations. E2E tests for critical user flows (auth, onboarding, dashboard, workflows). Minimum 80% line coverage on business logic. | CODE_RESOLVED_CURRENT_TRUTH | BLOCKS_DEPLOYMENT |
| GAP-TST-002 | Testing | No component tests for React frontend | HIGH | Neither GitHub main nor Beast branch has component tests. 65+ React components untested. UI regressions undetectable. | Vitest + Testing Library for component tests. Snapshot tests for design-system compliance. Tests for layout system, portfolio switcher, approval notices. | CODE_RESOLVED_CURRENT_TRUTH | BLOCKS_DEPLOYMENT |
| GAP-TST-003 | Testing | No API contract tests | HIGH | No tests verify API request/response shapes. Routes can break silently on refactor. No OpenAPI spec. | API contract tests per route module. Zod schemas double as contract and validation. OpenAPI spec generated from Zod schemas. | INFERRED_PROFESSIONAL_GAP | BLOCKS_DEPLOYMENT |
| GAP-TST-004 | Testing | Integration tests from DESIGN.md may be unrelocatable | MEDIUM | DESIGN.md Phases 1-3 reference 97 integration tests at services/umh/tests/test_eos_*. Files migrated during convergence. Location uncertain. Tests may need rewriting if they reference old module paths. | Locate, verify, or rewrite all 97 integration tests. Ensure they pass against current module structure (projections/eos/integration/). | IMPLEMENTATION_DEBT | BLOCKS_DEPLOYMENT |
| GAP-TST-005 | Testing | No load/performance tests | MEDIUM | No load testing framework. No benchmarks for API response times, concurrent user capacity, or agent execution throughput. | k6 or Artillery load tests. Baseline benchmarks for key operations: auth (<100ms), dashboard load (<500ms), workflow execution (<2s), agent skill execution (<5s). | INFERRED_PROFESSIONAL_GAP | BLOCKS_SCALE |
| GAP-TST-006 | Testing | No accessibility testing | MEDIUM | No automated WCAG 2.1 AA testing. Neither branch has axe-core, pa11y, or similar. Target shared platform standard requires WCAG 2.1 AA. | axe-core integration in component tests. pa11y-ci in CI pipeline. Automated WCAG 2.1 AA compliance checking on every PR. | INFERRED_PROFESSIONAL_GAP | BLOCKS_SCALE |
| GAP-TST-007 | Testing | No visual regression testing | LOW | No screenshot-based or visual diff testing. Design drift undetectable across deploys. Critical for finance-grade aesthetic consistency. | Chromatic, Percy, or Playwright screenshots for visual regression. Golden screenshots for key screens (dashboard, portfolio, workflow). | INFERRED_PROFESSIONAL_GAP | NON_BLOCKING |

---

## Infrastructure

| ID | Category | Gap | Severity | Current State | Target State | Provenance | Blocker |
|----|----------|-----|----------|---------------|--------------|------------|---------|
| GAP-INF-001 | Infrastructure | No production deployment exists | CRITICAL | EOS SaaS not deployed anywhere. No fly.toml. No EOS-specific Docker container. No CI/CD pipeline. GitHub main and Beast branch are local-only codebases. | Fly.io deployment (frontend + backend). fly.toml with health checks, auto-scaling, rolling deploys. Docker image for EOS SaaS. Neon Postgres in production region. | CODE_RESOLVED_CURRENT_TRUTH | BLOCKS_DEPLOYMENT |
| GAP-INF-002 | Infrastructure | No CI/CD pipeline | CRITICAL | No GitHub Actions, no automated builds, no automated tests, no automated deploys. Every change is manual. | GitHub Actions: lint, type-check, test, build, deploy. Branch protection on main. Required status checks. Deploy to Fly.io staging on PR merge, production on release tag. | INFERRED_PROFESSIONAL_GAP | BLOCKS_DEPLOYMENT |
| GAP-INF-003 | Infrastructure | Beast branch not on VPS | HIGH | Beast feature/company-system (603 files, Clerk auth, canonical candidate) lives only on Windows Beast at C:\dev\dev\EntrepreneurOS. Cannot be built, tested, or deployed from VPS. | Beast branch promoted to main. Cloned/accessible on VPS. Build pipeline runs from VPS or GitHub Actions. | CODE_RESOLVED_CURRENT_TRUTH | BLOCKS_DEPLOYMENT |
| GAP-INF-004 | Infrastructure | No staging environment | HIGH | No staging for either EOS SaaS or UMH platform. All development is against dev Neon database. No way to test deployments before production. | Staging environment on Fly.io. Separate Neon branch for staging data. Staging mirrors production config except for scale. | INFERRED_PROFESSIONAL_GAP | BLOCKS_DEPLOYMENT |
| GAP-INF-005 | Infrastructure | No health check endpoints on EOS SaaS | MEDIUM | UMH platform has /health endpoint. EOS SaaS has none. No readiness, liveness, or startup probes. | /health (overall status), /health/ready (dependency checks: DB, Clerk, Redis if applicable), /health/live (process alive). Fly.io health check configured against /health. | INFERRED_PROFESSIONAL_GAP | BLOCKS_DEPLOYMENT |
| GAP-INF-006 | Infrastructure | No caching layer | MEDIUM | No Redis, no in-memory cache, no CDN for static assets. Every request hits the database. Dashboard queries re-execute on every page load. | Redis or Upstash for session cache and computed KPI cache. CDN (Fly.io edge or Cloudflare) for static frontend assets. Cache invalidation on data mutation. | INFERRED_PROFESSIONAL_GAP | BLOCKS_SCALE |
| GAP-INF-007 | Infrastructure | No backup/disaster recovery plan | MEDIUM | Neon has point-in-time restore. No documented backup strategy. No runbook for data recovery. No tested restore procedure. | Documented backup strategy. Weekly backup verification. Tested restore runbook. RTO < 1 hour, RPO < 15 minutes. Neon branching for pre-migration snapshots. | INFERRED_PROFESSIONAL_GAP | BLOCKS_SCALE |
| GAP-INF-008 | Infrastructure | No secrets management beyond .env files | MEDIUM | API keys and credentials in .env files. No rotation policy. No encrypted secret store. | Fly.io secrets for deployment. GitHub Actions secrets for CI/CD. Secret rotation policy (90-day max). No plaintext secrets in any repository. | INFERRED_PROFESSIONAL_GAP | BLOCKS_DEPLOYMENT |

---

## Architecture

| ID | Category | Gap | Severity | Current State | Target State | Provenance | Blocker |
|----|----------|-----|----------|---------------|--------------|------------|---------|
| GAP-ARC-001 | Architecture | 401-file source divergence between codebases | CRITICAL | GitHub main: 202 files (Passport.js, stale Feb 2026). Beast: 603 files (Clerk, active Apr 2026). 401-file delta. No merge strategy validated. | Single unified codebase. Beast promoted as canonical per DEC-145-001. Merge validated: build passes, secret scan clean, operator reviewed, rollback plan documented. | CODE_RESOLVED_CURRENT_TRUTH | BLOCKS_DEPLOYMENT |
| GAP-ARC-002 | Architecture | God file risk on Beast merge | HIGH | Beast branch has server/generated/ directory with 21 storage modules. Generated code may contain duplicated logic, inconsistent patterns, or oversized files. No review of generated code quality. | Audit generated code before merge. Split files over 500 lines. Verify no logic duplication with hand-written modules. Remove generation scaffold if not needed post-merge. | INFERRED_PROFESSIONAL_GAP | BLOCKS_DEPLOYMENT |
| GAP-ARC-003 | Architecture | Python-TypeScript bridge undefined | HIGH | UMH is Python (substrate, projection). EOS SaaS is TypeScript (React, Express). No defined bridge mechanism for EOS frontend to invoke UMH substrate operations. transports/api/ has Python bridges (stdin/stdout JSON protocol) but no EOS-specific bridge. | HTTP API bridge: EOS Express backend calls UMH platform API (transports/api/http/) over internal network. Or: shared Neon database with event-driven coordination. Bridge must be documented with contract, error handling, and timeout policy. | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED | BLOCKS_DEPLOYMENT |
| GAP-ARC-004 | Architecture | Three separate schema surfaces need unification | HIGH | GitHub main schema.ts (15 tables), Beast schema.ts + generated (6+ tables), UMH platform schema.ts (8 tables). Three independently authored schemas with overlapping concerns (users, agents, tasks). | Single source-of-truth schema. EOS-specific tables in EOS schema. UMH platform tables in transports/api/http/db/schema.ts. Clear boundary: EOS tables reference UMH tables via foreign keys, never the reverse. | CODE_RESOLVED_CURRENT_TRUTH | BLOCKS_DEPLOYMENT |
| GAP-ARC-005 | Architecture | No EA Agent implemented | HIGH | Communication chain requires EA Agent as primary operator intake (User -> EA -> CEO/Portfolio Advisor -> Department). EA Agent is specified but not implemented anywhere in code. Without it, operator commands route directly to department agents, violating the corrected architecture. | EA Agent implemented in projections/eos/agents/ea.py. Registers with UMH substrate. Handles chat intake, triage, routing, clarification. READ permission tier. Routes to Portfolio Advisor or CEO based on scope. | CODE_RESOLVED_CURRENT_TRUTH | BLOCKS_DEPLOYMENT |
| GAP-ARC-006 | Architecture | No Portfolio Advisor Agent implemented | MEDIUM | Portfolio Advisor is required for multi-entity portfolio management. Handles capital allocation, cross-entity intelligence, portfolio-level strategy. Not implemented. | Portfolio Advisor Agent in projections/eos/agents/portfolio_advisor.py. DRAFT permission tier. Capabilities: portfolio analytics, capital allocation advice, entity comparison, cross-entity strategy. | INFERRED_PROFESSIONAL_GAP | BLOCKS_SCALE |
| GAP-ARC-007 | Architecture | Embedding dimension mismatch (384 vs 1536) | MEDIUM | embeddings table in UMH platform schema defines vector(384). OpenAI text-embedding-3-small produces 1536 dimensions. Mismatch prevents semantic search if different embedding models are used. | Decide on embedding model and dimension. If OpenAI: vector(1536). If local (sentence-transformers): vector(384). Document decision and migration path. | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED | BLOCKS_SCALE |
| GAP-ARC-008 | Architecture | No real-time event streaming to frontend | MEDIUM | No WebSocket, SSE, or polling mechanism for real-time updates. Dashboard data is static until page refresh. Agent execution progress invisible to user in real-time. | WebSocket (via Hono upgrade) or Server-Sent Events for real-time: agent execution progress, approval notifications, KPI updates, workflow step completions. | INFERRED_PROFESSIONAL_GAP | BLOCKS_SCALE |

---

## Data

| ID | Category | Gap | Severity | Current State | Target State | Provenance | Blocker |
|----|----------|-----|----------|---------------|--------------|------------|---------|
| GAP-DAT-001 | Data | No data classification scheme | HIGH | No field-level PII tagging. No sensitivity classification. Schema has no data_classification column or metadata. Agent conversations, user emails, financial data all treated identically. | Classify every field: PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED. PII fields (email, name, conversation content) marked CONFIDENTIAL minimum. Classification drives encryption, retention, export, deletion policies. | INFERRED_PROFESSIONAL_GAP | BLOCKS_SCALE |
| GAP-DAT-002 | Data | No data retention policy | HIGH | All data retained indefinitely. No TTL, no archival, no purge. interactions, embeddings, events, user_agent_sessions, umh_outcomes tables grow unbounded. | Defined retention periods per data type. Automated archival/purge. 90-day active, 1-year archive, then purge (except legal hold). Financial records: 7-year retention. | INFERRED_PROFESSIONAL_GAP | BLOCKS_SCALE |
| GAP-DAT-003 | Data | No database migration strategy documented | MEDIUM | Beast branch has migrations/ directory. GitHub main has no migrations. UMH platform has migrate.ts. No documented migration strategy for schema changes, rollback procedures, or data backfill. | Documented migration strategy: Drizzle migration files, reviewed before merge. Rollback procedure for every migration. Data backfill scripts when adding non-nullable columns. Pre-migration Neon branch snapshot. | INFERRED_PROFESSIONAL_GAP | BLOCKS_DEPLOYMENT |
| GAP-DAT-004 | Data | No field-level encryption for PII | MEDIUM | All data stored plaintext in Neon Postgres. Neon provides encryption at rest (AES-256) but no application-level field encryption. User emails, agent conversation content, financial data all plaintext in DB. | pgcrypto extension (already enabled in migrations) for pgp_sym_encrypt/decrypt on CONFIDENTIAL+ fields. Application-level encryption for API keys and integration credentials. | INFERRED_PROFESSIONAL_GAP | BLOCKS_SCALE |
| GAP-DAT-005 | Data | No data export capability | MEDIUM | No user data export endpoint. No bulk data extraction mechanism. Required for GDPR Article 20 (data portability) and for operator business continuity. | /api/v1/export endpoint. Export formats: JSON, CSV. Scoped by org_id. Includes all user-generated data: entities, workflows, tasks, documents, conversations, KPIs, transactions. Rate-limited to prevent abuse. | INFERRED_PROFESSIONAL_GAP | BLOCKS_SCALE |
| GAP-DAT-006 | Data | Correlation map does not survive restart | LOW | EOS integration correlation map (projections/eos/integration/correlation.py) uses in-memory dict. Thread-safe but lost on process restart. Pending outcomes may be orphaned. | Persist correlation map to Neon or Redis. Recover pending correlations on startup. TTL on stale correlations (e.g., 24h) to prevent unbounded growth. | CODE_RESOLVED_CURRENT_TRUTH | NON_BLOCKING |
| GAP-DAT-007 | Data | No database connection pooling strategy | LOW | UMH platform uses dual-pool (admin + app) via Neon serverless driver. EOS SaaS has no documented connection pooling. Beast branch uses Neon with Drizzle but pooling config unknown. | Documented connection pooling strategy. Neon serverless pooler with connection limits. Separate pools for read and write if needed at scale. Max connections aligned with Neon plan limits. | INFERRED_PROFESSIONAL_GAP | BLOCKS_SCALE |

---

## UI / UX

| ID | Category | Gap | Severity | Current State | Target State | Provenance | Blocker |
|----|----------|-----|----------|---------------|--------------|------------|---------|
| GAP-UIX-001 | UI/UX | No design system documentation | HIGH | Beast branch has design-tokens.ts and theme.json. No Storybook, no component catalog, no design system docs. 45+ UI components undocumented. Design decisions not recorded. | Storybook catalog with every component. Design tokens documented with usage guidelines. Component API docs. Anti-pattern gallery (what NOT to do per UI canon). | INFERRED_PROFESSIONAL_GAP | BLOCKS_SCALE |
| GAP-UIX-002 | UI/UX | Risk/Approval Notices UI not implemented | HIGH | Governance engine queues approvals. AuthorityEngine records decisions. No user-facing approval/governance flow. Operator cannot see, review, or approve pending actions in any UI. | Approval queue in Right Rail or dedicated screen. Notification badges for pending approvals. Inline risk notices on high-risk actions. Approval history log accessible. | CODE_RESOLVED_CURRENT_TRUTH | BLOCKS_DEPLOYMENT |
| GAP-UIX-003 | UI/UX | EA Chat interface not implemented | HIGH | Communication architecture specifies EA chat as primary input surface. No EA chat implementation on any branch. Beast has agent-chat-stub.tsx but it is a placeholder. | EA chat box in shell chrome (always accessible). Message routing through EA Agent. Streaming responses. Context-aware suggestions. Command palette (Cmd+K) for power users. | CODE_RESOLVED_CURRENT_TRUTH | BLOCKS_DEPLOYMENT |
| GAP-UIX-004 | UI/UX | No onboarding flow implemented | HIGH | 25-step onboarding flow specified in phase14_6b_eos_onboarding_first_boot_spec.json. Beast has company-setup-page.tsx (single page). No multi-step wizard, no AI-generation integration, no progressive disclosure. | Full 25-step onboarding wizard. Steps 1-7: configuration. Steps 8-19: AI generation with live preview. Steps 20-24: governance config. Step 25: approval and activation. Progress indicator, back/forward, save-and-resume. | CODE_RESOLVED_CURRENT_TRUTH | BLOCKS_DEPLOYMENT |
| GAP-UIX-005 | UI/UX | No responsive/mobile experience | MEDIUM | UI canon specifies responsive design as shared platform standard. Neither branch has responsive breakpoints implemented. No mobile testing. Desktop-only. | Responsive breakpoints: mobile (< 768px), tablet (768-1024px), desktop (> 1024px). Left Rail collapses on mobile. Right Rail becomes bottom sheet. Touch-friendly controls. Tested on iOS Safari and Chrome Android. | INFERRED_PROFESSIONAL_GAP | BLOCKS_SCALE |
| GAP-UIX-006 | UI/UX | No error/empty/loading states designed | MEDIUM | No systematic empty states, error states, or loading skeletons. User sees blank page or raw error on failure. No zero-data onboarding prompts. | Empty state designs for every screen (with CTA to create first item). Error boundary components with retry. Loading skeleton matching finance-grade layout. Optimistic UI updates for mutations. | INFERRED_PROFESSIONAL_GAP | BLOCKS_DEPLOYMENT |
| GAP-UIX-007 | UI/UX | No keyboard shortcuts or command palette | LOW | UI canon specifies Cmd+K command palette and keyboard shortcuts as power-user features. Neither codebase has any keyboard shortcut implementation. | cmdk or kbar library for command palette. Keyboard shortcuts for navigation (g+d = dashboard, g+w = workflows), actions (n = new, e = edit), and AI (/ = chat focus). Shortcut legend panel. | INFERRED_PROFESSIONAL_GAP | NON_BLOCKING |
| GAP-UIX-008 | UI/UX | No dark mode implementation | MEDIUM | UI canon specifies dark mode as PRIMARY. Neither branch has a working dark mode toggle or dark theme. Design tokens exist directionally but not applied. | Dark mode as default. Light mode available via toggle. Tailwind dark: variant applied to all components. Design tokens resolved to dark/light via CSS variables. Persistent user preference. | CODE_RESOLVED_CURRENT_TRUTH | BLOCKS_DEPLOYMENT |

---

## AI / Agents

| ID | Category | Gap | Severity | Current State | Target State | Provenance | Blocker |
|----|----------|-----|----------|---------------|--------------|------------|---------|
| GAP-AIA-001 | AI/Agents | No communication delegation chain implemented | HIGH | Operator correction mandates User -> EA -> Portfolio Advisor/CEO -> Department. Current code has 10 department agents that can be called directly. No routing through EA or CEO. No escalation protocol. | Full delegation chain: EA receives all operator input, classifies scope (portfolio vs entity), routes to Portfolio Advisor or CEO, CEO delegates to departments, results flow back up. 8 escalation triggers enforced. | CODE_RESOLVED_CURRENT_TRUTH | BLOCKS_DEPLOYMENT |
| GAP-AIA-002 | AI/Agents | Instance-specific hardcoded values in CEO Agent | MEDIUM | CEOAgent (projections/eos/agents/ceo.py) contains hardcoded references to specific ventures (e.g., "Initiate Arena"). Instance context law requires runtime lookup via BIS. | Replace all hardcoded venture/product/company references with BIS runtime lookup. get_ai_name() for AI identity. BIS venture registry for business context. | CODE_RESOLVED_CURRENT_TRUTH | BLOCKS_MULTI_USER |
| GAP-AIA-003 | AI/Agents | No per-entity agent scoping | MEDIUM | A sales agent with EXECUTE permission can operate on ANY entity in the org, not just assigned ones. No entity_scope in agent execution context. Permission tiers are org-wide, not entity-scoped. | Add entity_scope to agent execution context. Governance engine checks entity assignment before permitting action. Agent can only operate on entities it is registered to serve. | CODE_RESOLVED_CURRENT_TRUTH | BLOCKS_MULTI_USER |
| GAP-AIA-004 | AI/Agents | No agent execution resource limits | MEDIUM | No CPU, memory, or time limits on individual agent task execution. A runaway agent task can consume unbounded resources. No output size limits on agent responses. | Per-agent execution limits: 30s timeout for fast tasks, 300s for research tasks. Memory cap per execution context. Output size limit (64KB default, configurable per skill). Circuit breaker on repeated failures. | INFERRED_PROFESSIONAL_GAP | BLOCKS_SCALE |
| GAP-AIA-005 | AI/Agents | No agent execution audit trail | MEDIUM | GovernanceEngine logs governance decisions. AuthorityEngine records approvals. But no dedicated audit trail for agent skill invocations: what skill was called, with what parameters, what it returned, how long it took. | Agent execution audit table: agent_id, skill_name, parameters (hashed PII), result_summary, duration_ms, tokens_used, cost_estimate, timestamp, entity_id, workflow_run_id. Queryable for cost analysis and debugging. | INFERRED_PROFESSIONAL_GAP | BLOCKS_SCALE |
| GAP-AIA-006 | AI/Agents | No agent cost tracking/budgeting | MEDIUM | Agents call model_router.call_with_fallback() with no cost tracking. No per-agent, per-org, or per-entity budget limits. AI spend is invisible and unbounded. | Cost tracking per LLM call: model, tokens_in, tokens_out, estimated_cost. Per-org monthly budget with alerting. Per-entity budget allocation. Agent cost dashboard in analytics. | INFERRED_PROFESSIONAL_GAP | BLOCKS_SCALE |
| GAP-AIA-007 | AI/Agents | No network isolation for agent browser sessions | LOW | Browser research and browser act skills run in the same process/container. Agent browser sessions can access internal services, other agents, and admin endpoints. | Network policy: agent browser sessions isolated to external-only network. Internal service endpoints unreachable from agent browser context. Proxy-based isolation. | INFERRED_PROFESSIONAL_GAP | BLOCKS_SCALE |
| GAP-AIA-008 | AI/Agents | 6 planned specialist agents not implemented | LOW | Agent architecture specifies admin, research, content, automation, investment_analyst, asset_manager, property_manager as professional gaps. None implemented. | Implement as demand requires. Investment_analyst and asset_manager needed for non-business entity types (investment, asset). Others are quality-of-life additions. | INFERRED_PROFESSIONAL_GAP | NON_BLOCKING |

---

## Documentation

| ID | Category | Gap | Severity | Current State | Target State | Provenance | Blocker |
|----|----------|-----|----------|---------------|--------------|------------|---------|
| GAP-DOC-001 | Documentation | No API documentation | HIGH | No OpenAPI spec. No API reference docs. No endpoint documentation beyond code comments. Developers and integrators have no reference for how to use the API. | OpenAPI 3.1 spec generated from Zod schemas. Interactive API explorer (Swagger UI or Scalar). Versioned API docs deployed alongside the application. | INFERRED_PROFESSIONAL_GAP | BLOCKS_SCALE |
| GAP-DOC-002 | Documentation | No deployment runbook | HIGH | No documented procedure for deploying EOS. No runbook for common operations (restart, rollback, scale, debug). No incident response procedure. | Deployment runbook: pre-deploy checklist, deploy command, post-deploy verification, rollback procedure. Incident response: who to alert, how to diagnose, how to recover. | INFERRED_PROFESSIONAL_GAP | BLOCKS_DEPLOYMENT |
| GAP-DOC-003 | Documentation | No architecture decision records | MEDIUM | Key decisions (Clerk over Passport.js, Beast as canonical, portfolio-first hierarchy, dark mode primary) exist in analysis artifacts but not in a standard ADR format. Future developers cannot trace why decisions were made. | ADR directory (docs/adr/). One ADR per significant decision. Format: context, decision, consequences, status. Linked from relevant code comments. | INFERRED_PROFESSIONAL_GAP | BLOCKS_SCALE |
| GAP-DOC-004 | Documentation | No user-facing help/docs | MEDIUM | No in-app help. No knowledge base. No tooltips on complex features. No onboarding tooltips. | In-app contextual help (tooltips, info popovers). Knowledge base (Notion, GitBook, or custom). EA agent can answer "how do I..." questions from knowledge base. | INFERRED_PROFESSIONAL_GAP | BLOCKS_SCALE |
| GAP-DOC-005 | Documentation | No changelog/release notes system | LOW | No CHANGELOG.md. No release notes mechanism. Users have no way to know what changed between versions. | CHANGELOG.md maintained with every release. In-app "What's New" notification for significant changes. Semantic versioning applied. | INFERRED_PROFESSIONAL_GAP | NON_BLOCKING |

---

## Compliance

| ID | Category | Gap | Severity | Current State | Target State | Provenance | Blocker |
|----|----------|-----|----------|---------------|--------------|------------|---------|
| GAP-CMP-001 | Compliance | No GDPR compliance | HIGH | No right to erasure (Article 17). No data portability (Article 20). No consent management. No data processing agreement. No privacy policy in application. No cookie consent. | Full GDPR compliance: data deletion endpoint, data export endpoint, consent tracking, DPA template, privacy policy page, cookie consent banner (for PostHog/Clerk cookies). | INFERRED_PROFESSIONAL_GAP | BLOCKS_SCALE |
| GAP-CMP-002 | Compliance | No CCPA compliance | MEDIUM | No right to know, right to delete, right to opt-out of sale. No California Consumer Privacy Act implementation. Applies if serving CA residents. | CCPA compliance: do-not-sell mechanism, deletion request handling, annual privacy notice update, data inventory mapped to CCPA categories. | INFERRED_PROFESSIONAL_GAP | BLOCKS_SCALE |
| GAP-CMP-003 | Compliance | No Terms of Service | HIGH | No ToS in application. No legal agreement governing use. No liability limitation. No dispute resolution. | ToS page in application. Accepted during onboarding (step 1). Versioned ToS with change notification. Reviewed by legal. | INFERRED_PROFESSIONAL_GAP | BLOCKS_DEPLOYMENT |
| GAP-CMP-004 | Compliance | No privacy policy | HIGH | No privacy policy. No documentation of what data is collected, how it is used, who it is shared with, or how to request deletion. | Privacy policy page. Covers data collection (Clerk auth data, business data, analytics), usage (product operation, AI training opt-out), sharing (no selling, processor list), rights (deletion, portability). | INFERRED_PROFESSIONAL_GAP | BLOCKS_DEPLOYMENT |
| GAP-CMP-005 | Compliance | No financial data handling compliance | MEDIUM | EOS handles financial data (transactions, revenue, expenses, burn rate). No SOC 2 compliance. No financial data handling procedures. No audit trail for financial mutations. | SOC 2 Type II target for post-revenue phase. Immediate: immutable audit trail for all financial data mutations. Segregation of duties for financial operations. Agent actions on financial data require COMMIT tier approval. | INFERRED_PROFESSIONAL_GAP | BLOCKS_SCALE |
| GAP-CMP-006 | Compliance | No AI governance disclosure | LOW | AI agents make decisions affecting business operations. No disclosure to end users about AI involvement. No explainability for AI-generated recommendations. | AI disclosure in ToS and product UI. "AI-generated" labels on AI outputs. Explainability: governance decisions include reasoning. Agent actions logged with provenance. Opt-out for fully autonomous execution. | INFERRED_PROFESSIONAL_GAP | BLOCKS_SCALE |

---

## Performance

| ID | Category | Gap | Severity | Current State | Target State | Provenance | Blocker |
|----|----------|-----|----------|---------------|--------------|------------|---------|
| GAP-PRF-001 | Performance | No performance benchmarks | MEDIUM | No baseline performance measurements. No SLOs. No performance budget. Response times, throughput, and latency unknown for any endpoint or user flow. | Defined SLOs: P95 API response < 200ms (CRUD), < 2s (AI-enhanced), < 500ms (dashboard). Performance budget: LCP < 2.5s, FID < 100ms, CLS < 0.1. k6 benchmarks in CI. | INFERRED_PROFESSIONAL_GAP | BLOCKS_SCALE |
| GAP-PRF-002 | Performance | No query optimization | MEDIUM | No database query analysis. No EXPLAIN plans. No indexes beyond primary keys (inferred). Dashboard queries may full-scan tables as data grows. KPI calculations not materialized. | Index audit on all query paths. Materialized views for dashboard KPIs. EXPLAIN ANALYZE on critical queries. Query monitoring in production (pg_stat_statements). | INFERRED_PROFESSIONAL_GAP | BLOCKS_SCALE |
| GAP-PRF-003 | Performance | No frontend bundle optimization | LOW | Vite provides basic bundling. No code splitting strategy documented. No lazy loading for routes. No tree-shaking verification. Bundle size unknown. | Route-based code splitting via React.lazy. Dynamic imports for heavy components (charts, editors). Bundle analysis (vite-bundle-visualizer). Budget: initial bundle < 200KB gzipped. | INFERRED_PROFESSIONAL_GAP | NON_BLOCKING |
| GAP-PRF-004 | Performance | No CDN for static assets | LOW | Frontend served from application server. No CDN. No edge caching for static assets (JS, CSS, images). Global users experience full round-trip latency. | Fly.io edge caching or Cloudflare CDN for static assets. Cache-busted filenames for immutable caching. 1-year max-age on hashed assets. | INFERRED_PROFESSIONAL_GAP | BLOCKS_SCALE |

---

## Monitoring

| ID | Category | Gap | Severity | Current State | Target State | Provenance | Blocker |
|----|----------|-----|----------|---------------|--------------|------------|---------|
| GAP-MON-001 | Monitoring | No error tracking service | HIGH | No Sentry, no Bugsnag, no error tracking. Errors visible only in container logs. No alerting on error spikes. No error grouping or triage workflow. | Sentry (or Highlight.io) for error tracking. Source maps uploaded for frontend. Python SDK for substrate errors. Alerting on new error types. Error budget monitoring. | INFERRED_PROFESSIONAL_GAP | BLOCKS_DEPLOYMENT |
| GAP-MON-002 | Monitoring | No application monitoring/observability | HIGH | No APM. No distributed tracing. No request latency monitoring. No dependency health checks. UMH substrate has observability/error_recorder.py but no production APM. | OpenTelemetry instrumentation. Traces for request lifecycle (auth -> handler -> DB -> response). Grafana or Highlight.io dashboards. Alerting on P95 latency degradation. | INFERRED_PROFESSIONAL_GAP | BLOCKS_DEPLOYMENT |
| GAP-MON-003 | Monitoring | No uptime monitoring | MEDIUM | No external uptime monitoring. No status page. No SLA tracking. Downtime invisible until user reports it. | Uptime monitoring (Better Stack, Checkly, or UptimeRobot). Public status page. SLA tracking (99.9% target). Incident notification via PagerDuty or Discord webhook. | INFERRED_PROFESSIONAL_GAP | BLOCKS_DEPLOYMENT |
| GAP-MON-004 | Monitoring | No log aggregation | MEDIUM | Logs in Docker container stdout only (docker logs os-*). No aggregation, no search, no retention beyond container lifecycle. UMH substrate logs to console. | Centralized log aggregation (Fly.io logs, Loki, or Axiom). Structured JSON logging. Log retention: 30 days searchable, 1 year archived. Correlation IDs across services. | INFERRED_PROFESSIONAL_GAP | BLOCKS_SCALE |
| GAP-MON-005 | Monitoring | No product analytics | MEDIUM | PostHog configured in Beast branch but not deployed. No product analytics in production. User behavior, feature usage, and conversion funnels unmeasured. | PostHog deployed with EOS SaaS. Event tracking: page views, feature usage, onboarding completion, workflow executions, agent interactions. Funnels, retention, and cohort analysis. | CODE_RESOLVED_CURRENT_TRUTH | BLOCKS_SCALE |

---

## Business / Strategy

| ID | Category | Gap | Severity | Current State | Target State | Provenance | Blocker |
|----|----------|-----|----------|---------------|--------------|------------|---------|
| GAP-BIZ-001 | Business | No pricing model defined | HIGH | No free/paid tiers. No pricing page. No Stripe integration. No subscription management. Revenue model entirely undefined. | Pricing tiers defined (e.g., Solo / Team / Enterprise). Stripe integration for subscription billing. Trial period. Usage-based pricing for AI compute. Plan limits enforced in code. | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED | BLOCKS_DEPLOYMENT |
| GAP-BIZ-002 | Business | No competitive analysis | MEDIUM | No formal competitive analysis vs Monday.com, Notion AI, ClickUp Brain, Rippling, Gusto, or other business OS products. Positioning not validated against market. | Competitive matrix: features, pricing, target market, AI capabilities. Positioning statement validated against top 5 competitors. Differentiation points documented. | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED | BLOCKS_SCALE |
| GAP-BIZ-003 | Business | No mobile strategy defined | LOW | No mobile app. No progressive web app (PWA). No responsive design implementation. Desktop-only experience. Mobile strategy undecided (web-responsive vs native). | Decision: web-responsive MVP (PWA with service worker for offline). Native apps deferred until product-market fit validated. Responsive breakpoints implemented. | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED | BLOCKS_SCALE |
| GAP-BIZ-004 | Business | No customer support infrastructure | MEDIUM | No support channel. No ticketing system. No FAQ. No chatbot. Users have no way to get help beyond the EA agent (which is also not implemented). | Support email/channel. In-app help widget. FAQ/knowledge base. EA agent as first-line support (after implementation). Escalation to human support for billing and account issues. | INFERRED_PROFESSIONAL_GAP | BLOCKS_SCALE |
| GAP-BIZ-005 | Business | No user feedback mechanism | LOW | No in-app feedback widget. No feature request system. No NPS survey. No way to collect structured user feedback. | In-app feedback widget (Canny, ProductBoard, or custom). NPS survey at day 7 and day 30. Feature request voting board. Feedback piped to PostHog for correlation with product data. | INFERRED_PROFESSIONAL_GAP | NON_BLOCKING |
| GAP-BIZ-006 | Business | No billing/subscription management | HIGH | No Stripe integration. No subscription lifecycle (create, upgrade, downgrade, cancel). No invoice generation. No payment failure handling. No dunning. | Stripe integration: subscription creation, plan changes, cancellation, invoicing. Webhook handlers for payment events. Dunning emails for failed payments. Subscription status enforced in middleware. | INFERRED_PROFESSIONAL_GAP | BLOCKS_DEPLOYMENT |

---

## Summary Statistics

| Category | Count | Critical | High | Medium | Low |
|----------|-------|----------|------|--------|-----|
| Auth/Security | 11 | 2 | 3 | 4 | 2 |
| Testing | 7 | 1 | 2 | 3 | 1 |
| Infrastructure | 8 | 2 | 2 | 4 | 0 |
| Architecture | 8 | 1 | 4 | 3 | 0 |
| Data | 7 | 0 | 2 | 3 | 2 |
| UI/UX | 8 | 0 | 4 | 3 | 1 |
| AI/Agents | 8 | 0 | 1 | 5 | 2 |
| Documentation | 5 | 0 | 2 | 2 | 1 |
| Compliance | 6 | 0 | 3 | 2 | 1 |
| Performance | 4 | 0 | 0 | 2 | 2 |
| Monitoring | 5 | 0 | 2 | 3 | 0 |
| Business/Strategy | 6 | 0 | 2 | 2 | 2 |
| **TOTAL** | **83** | **6** | **27** | **36** | **14** |

### Blocker Distribution

| Blocker | Count |
|---------|-------|
| BLOCKS_DEPLOYMENT | 38 |
| BLOCKS_MULTI_USER | 3 |
| BLOCKS_SCALE | 34 |
| NON_BLOCKING | 8 |

### Provenance Distribution

| Provenance | Count |
|------------|-------|
| INFERRED_PROFESSIONAL_GAP | 53 |
| CODE_RESOLVED_CURRENT_TRUTH | 24 |
| OPEN_QUESTION_OPERATOR_DECISION_REQUIRED | 5 |
| IMPLEMENTATION_DEBT | 1 |

---

## Priority Execution Order

### P0 — Must resolve before ANY deployment (6 gaps)

1. GAP-SEC-001 — Real authentication (Clerk JWT)
2. GAP-SEC-002 — RLS bypass fix (require DATABASE_APP_URL)
3. GAP-ARC-001 — Source divergence resolution (Beast merge)
4. GAP-INF-001 — Production deployment exists
5. GAP-INF-002 — CI/CD pipeline exists
6. GAP-TST-001 — Minimum test coverage

### P1 — Must resolve before public launch (20 gaps)

7. GAP-SEC-003 — Rate limiting
8. GAP-SEC-005 — DB role credential fix
9. GAP-SEC-006 — Security headers
10. GAP-SEC-007 — Error sanitization
11. GAP-SEC-008 — Input validation middleware
12. GAP-SEC-009 — CORS configuration
13. GAP-INF-003 — Beast branch on VPS
14. GAP-INF-004 — Staging environment
15. GAP-ARC-003 — Python-TypeScript bridge
16. GAP-ARC-004 — Schema unification
17. GAP-ARC-005 — EA Agent implementation
18. GAP-UIX-002 — Approval notices UI
19. GAP-UIX-003 — EA Chat interface
20. GAP-UIX-004 — Onboarding flow
21. GAP-UIX-008 — Dark mode
22. GAP-AIA-001 — Communication delegation chain
23. GAP-CMP-003 — Terms of Service
24. GAP-CMP-004 — Privacy policy
25. GAP-MON-001 — Error tracking
26. GAP-MON-002 — Application monitoring
27. GAP-BIZ-001 — Pricing model
28. GAP-BIZ-006 — Billing/subscription

### P2 — Must resolve before scaling (28 gaps)

GAP-SEC-004, GAP-TST-002, GAP-TST-003, GAP-TST-004, GAP-INF-005,
GAP-INF-008, GAP-ARC-002, GAP-DAT-001, GAP-DAT-002, GAP-DAT-003,
GAP-UIX-001, GAP-UIX-006, GAP-AIA-002, GAP-AIA-003, GAP-DOC-001,
GAP-DOC-002, GAP-CMP-001, GAP-MON-003, GAP-MON-004, GAP-MON-005,
GAP-BIZ-004, GAP-ARC-006, GAP-ARC-007, GAP-ARC-008, GAP-AIA-004,
GAP-AIA-005, GAP-AIA-006, GAP-UIX-005

### P3 — Professional debt, post-launch (27 gaps)

All remaining LOW-severity and non-blocking MEDIUM gaps:
GAP-SEC-010, GAP-SEC-011, GAP-TST-005, GAP-TST-006, GAP-TST-007,
GAP-INF-006, GAP-INF-007, GAP-DAT-004, GAP-DAT-005, GAP-DAT-006,
GAP-DAT-007, GAP-UIX-005, GAP-UIX-007, GAP-AIA-007, GAP-AIA-008,
GAP-DOC-003, GAP-DOC-004, GAP-DOC-005, GAP-CMP-002, GAP-CMP-005,
GAP-CMP-006, GAP-PRF-001, GAP-PRF-002, GAP-PRF-003, GAP-PRF-004,
GAP-BIZ-002, GAP-BIZ-003, GAP-BIZ-005
