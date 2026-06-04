---
phase: "14.6B-CreatorOS"
status: "DRAFT"
operator_approved: false
allows_implementation: false
date: "2026-06-04"
provenance: "IMPLEMENTATION_DEBT"
description: "Complete technical debt register for CreatorOS codebase — 38 items across security, architecture, testing, infrastructure, data model, UX, DevOps, and platform integration"
sources:
  - "phase14_6b_creatoros_current_implementation_truth.json (code-verified current state)"
  - "phase14_6b_creatoros_auth_security_truth.json (broken auth deep analysis)"
  - "phase14_6b_creatoros_api_infrastructure_canon.json (89-route monolith, god files)"
  - "phase14_6b_creatoros_source_inventory.json (296 GitHub files, Replit origin, attached_assets)"
  - "phase14_6b_creatoros_data_ontology.json (20 tables, 25 missing, schema gaps)"
  - "phase14_6b_creatoros_design_identity_canon.json (X/Twitter identity, Stitch UI inventory needed)"
  - "phase14_6b_creatoros_versions_contradictions_matrix.json (conflicting PRD claims)"
  - "phase14_6b_creatoros_community_messaging_canon.json (communities no owner FK)"
  - "phase14_6b_creatoros_product_types_commerce_canon.json (no payment, no checkout)"
---


# CreatorOS Implementation Debt Register

All debt items traced to verified code state. No speculative entries. Severity uses CRITICAL / HIGH / MEDIUM / LOW. Priority uses P0 (must fix before any deploy) through P3 (long-term improvement). Effort uses T-shirt sizing: XS (<1 day), S (1-2 days), M (3-5 days), L (1-2 weeks), XL (2+ weeks).


## Security Debt

| ID | Category | Debt | Severity | Location | Remediation | Effort | Priority |
|----|----------|------|----------|----------|-------------|--------|----------|
| COS-SEC-001 | Auth | `comparePasswords()` returns `true` for ALL passwords — authentication is effectively disabled. Any password works for any user account. Full account takeover with only a username. | CRITICAL | `server/auth.ts` | Do NOT fix Passport.js. Migrate directly to Clerk. Fixing broken auth in a system scheduled for replacement is wasted work. | L | P0 |
| COS-SEC-002 | Session | Hardcoded fallback session secret: `'creatorOS-secret-key'`. If `SESSION_SECRET` env var missing, sessions become predictable and hijackable. | HIGH | `server/auth.ts` | Remove hardcoded fallback. Require `SESSION_SECRET` env var or fail fast at startup. Will be eliminated entirely by Clerk migration. | XS | P0 |
| COS-SEC-003 | Rate Limiting | Zero rate limiting on `/api/register`, `/api/login`, `/api/logout`, `/api/user`. Brute force, credential stuffing, and account enumeration attacks unblocked. | HIGH | `server/routes.ts`, `server/auth.ts` | Add `express-rate-limit` middleware. Auth endpoints: 5 req/min. General API: 60 req/min. | S | P0 |
| COS-SEC-004 | CSRF | No CSRF protection on any mutation endpoints. All 89 routes accept requests from any origin. | HIGH | `server/routes.ts` | Add `csurf` or `csrf-csrf` middleware for all state-changing endpoints. Clerk migration may partially address this with token-based auth. | S | P1 |
| COS-SEC-005 | Input Validation | No server-side input validation on route handlers. Route bodies parsed as raw JSON with no Zod/schema enforcement despite `drizzle-zod` being in dependencies. | HIGH | `server/routes.ts` | Wire `drizzle-zod` insert schemas as Express middleware validators. Every mutation route gets Zod `.parse()` on `req.body`. | M | P1 |
| COS-SEC-006 | Authorization | No ownership checks on mutation endpoints. Any authenticated user can update/delete any other user's posts, products, documents, stories. Only authentication check is `req.isAuthenticated()`. | HIGH | `server/routes.ts` | Add ownership middleware: compare `req.user.id` against resource `userId` FK for every mutation. | M | P1 |
| COS-SEC-007 | Session Store | MemoryStore for sessions — not persistent, data lost on restart, does not scale beyond single process, leaks memory under load. `connect-pg-simple` exists in deps but memorystore is the active fallback. | MEDIUM | `server/auth.ts` | Force `connect-pg-simple` (Postgres-backed sessions) as sole store. Remove memorystore fallback. Will be eliminated entirely by Clerk migration. | S | P1 |
| COS-SEC-008 | Cookie Config | Session cookie security attributes (secure, httpOnly, sameSite, maxAge) are unverified — may not be set or may be insecure defaults. | MEDIUM | `server/auth.ts` | Audit and explicitly set: `{ secure: true, httpOnly: true, sameSite: 'strict', maxAge: 86400000 }`. | XS | P1 |


## Architecture Debt

| ID | Category | Debt | Severity | Location | Remediation | Effort | Priority |
|----|----------|------|----------|----------|-------------|--------|----------|
| COS-ARCH-001 | God File | `server/routes.ts` is 53,388 bytes — all 89 API routes in a single monolithic file. Blocks parallel development, impossible to navigate, no domain separation. | HIGH | `server/routes.ts` | Split into domain routers: `routes/auth.ts`, `routes/users.ts`, `routes/posts.ts`, `routes/products.ts`, `routes/communities.ts`, `routes/messages.ts`, `routes/ai.ts`, `routes/notifications.ts`, `routes/stories.ts`, `routes/documents.ts`, `routes/revenue.ts`, `routes/contacts.ts`. Mount via `app.use()`. | L | P1 |
| COS-ARCH-002 | God File | `server/storage.ts` is 104,725 bytes — all data access logic (queries, inserts, updates, deletes for all 20 tables) in a single file. Largest file in codebase by 2x. | HIGH | `server/storage.ts` | Split into domain repositories: `storage/users.ts`, `storage/posts.ts`, `storage/products.ts`, `storage/communities.ts`, `storage/messages.ts`, `storage/ai.ts`, etc. Single `storage/index.ts` re-exports. | L | P1 |
| COS-ARCH-003 | Layering | No architectural layering. Routes call storage functions directly with no service/business logic layer. Validation, authorization, business rules, and data access are interleaved in route handlers. | HIGH | `server/routes.ts`, `server/storage.ts` | Introduce service layer: `services/post-service.ts`, `services/product-service.ts`, etc. Routes call services; services call storage. Business logic lives in services only. | XL | P2 |
| COS-ARCH-004 | Error Handling | No centralized error handling. Each route handler has ad-hoc try/catch or none at all. No standard error response shape. No error classification. | MEDIUM | `server/routes.ts` | Add Express error-handling middleware. Define `AppError` class with status code + error code. All routes throw typed errors; middleware serializes them. | M | P1 |
| COS-ARCH-005 | Type Safety | Route handlers use untyped `req.body` with no TypeScript generics. Despite 40 exported Drizzle types (20 Select + 20 Insert), routes do not use them for request/response typing. | MEDIUM | `server/routes.ts` | Type all route handlers with `Request<Params, ResBody, ReqBody>` generics using Drizzle insert/select types. | M | P2 |
| COS-ARCH-006 | Config | No configuration management. Database URL, session secret, OpenAI key, and port are read from `process.env` at point of use with no validation, no defaults documentation, and no startup check. Replit-specific `REPL_ID` in env vars. | MEDIUM | `server/index.ts`, `server/auth.ts` | Create `config.ts` with typed config loader. Validate all required env vars at startup. Fail fast with clear error if missing. Remove `REPL_ID`. | S | P1 |
| COS-ARCH-007 | Replit Artifacts | `.replit`, `replit.nix`, `generated-icon.png` committed to repo. Replit run/deployment config has no relevance outside Replit. | MEDIUM | root directory | Remove `.replit`, `replit.nix`, `generated-icon.png`. Add to `.gitignore`. | XS | P2 |


## Testing Debt

| ID | Category | Debt | Severity | Location | Remediation | Effort | Priority |
|----|----------|------|----------|----------|-------------|--------|----------|
| COS-TEST-001 | Test Suite | Zero test files. No vitest, jest, playwright, or any test framework in `devDependencies`. Zero coverage. No CI gate. | HIGH | entire codebase | Add vitest + @testing-library/react. Target: unit tests for all storage functions, integration tests for all 89 routes, component tests for critical UI paths. | XL | P1 |
| COS-TEST-002 | E2E Tests | No end-to-end tests. No Playwright or Cypress. Critical flows (register, login, create post, create product, follow user, send message) have zero automated verification. | HIGH | entire codebase | Add Playwright. Write E2E for auth flow, post CRUD, product CRUD, messaging, community creation. Gate deploys on E2E pass. | L | P2 |
| COS-TEST-003 | Type Checking | `tsc` exists as `check` script but is not run in CI or pre-commit. Unknown number of type errors in codebase. TypeScript strict mode status unverified. | MEDIUM | `tsconfig.json` | Run `tsc --noEmit`, fix all errors. Enable `strict: true` if not already. Add to CI pipeline. | M | P1 |
| COS-TEST-004 | Linting | No ESLint or Biome configuration. No code style enforcement. Replit Agent code has unknown style consistency. | MEDIUM | root directory | Add ESLint (or Biome) with strict TypeScript rules. Fix all violations. Add to CI. | M | P2 |


## Data Model Debt

| ID | Category | Debt | Severity | Location | Remediation | Effort | Priority |
|----|----------|------|----------|----------|-------------|--------|----------|
| COS-DATA-001 | Missing Tables | 25 tables specified in data ontology have zero implementation. Missing: orders, entitlements, subscriptions, courses, course_progress, connected_accounts, automation_flows, email_campaigns, ad_campaigns, ugc_campaigns, and 15 more. Core commerce flow (order -> entitlement) does not exist. | HIGH | `shared/schema.ts` | Implement missing tables per data ontology. Prioritize commerce (orders, entitlements, subscriptions) and connected_accounts (core "post once, publish everywhere" promise). | XL | P1 |
| COS-DATA-002 | Community Ownership | `communities` table has no owner/creator FK. Communities exist in a vacuum with no ownership, no moderation authority, no creator attribution. | HIGH | `shared/schema.ts` (communities table) | Add `creatorId integer FK -> users.id` column. Migrate existing data (assign to first admin or seed user). | S | P1 |
| COS-DATA-003 | Price Type | `products.price` uses `doublePrecision` (floating point). Floating point arithmetic produces rounding errors in financial calculations. $19.99 + $29.99 may not equal $49.98. | MEDIUM | `shared/schema.ts` (products table) | Change to `integer` (cents) or `numeric(10,2)`. Update all price display to divide by 100 or format from decimal. | M | P1 |
| COS-DATA-004 | Revenue Type | `revenue.amount` also uses `doublePrecision`. Same floating point financial problem as products. | MEDIUM | `shared/schema.ts` (revenue table) | Change to `integer` (cents) or `numeric(10,2)`. Coordinate with products price type change. | S | P1 |
| COS-DATA-005 | Soft Deletes | No soft delete support on any table. All deletes are hard deletes. No audit trail. Cannot recover accidentally deleted posts, products, or communities. | MEDIUM | `shared/schema.ts` (all tables) | Add `deletedAt timestamp` to posts, products, communities, documents. Filter queries on `deletedAt IS NULL`. | M | P2 |
| COS-DATA-006 | Role Enum | `users.role` is a plain `text` field with default `'creator'`. No enum constraint. Any string accepted. Consumer role assumed from PRD but not enforced in schema. | LOW | `shared/schema.ts` (users table) | Add Postgres enum or check constraint: `role IN ('creator', 'consumer', 'admin')`. | XS | P2 |
| COS-DATA-007 | No Indexes | No custom indexes defined beyond primary keys and unique constraints. All list queries (posts feed, products marketplace, user search) do full table scans. | MEDIUM | `shared/schema.ts` | Add indexes: `posts(userId, createdAt)`, `products(category, createdAt)`, `followers(followerId)`, `followers(followedId)`, `notifications(userId, read)`, `channel_messages(channelId, createdAt)`. | S | P2 |


## Infrastructure / DevOps Debt

| ID | Category | Debt | Severity | Location | Remediation | Effort | Priority |
|----|----------|------|----------|----------|-------------|--------|----------|
| COS-INFRA-001 | No Deployment | No production deployment exists. No Dockerfile, no fly.toml, no Vercel config, no deployment script. App runs only via `tsx server/index.ts` in development mode. | HIGH | root directory | Create Dockerfile, deployment config (Fly.io or similar), and deploy pipeline. Must resolve COS-SEC-001 (broken auth) before any public deployment. | L | P0 |
| COS-INFRA-002 | No CI/CD | No GitHub Actions, no CI pipeline, no automated checks on PR or push. Code merges to main with zero gates. | HIGH | `.github/` (missing) | Create `.github/workflows/ci.yml`: type check, lint, test, build. Gate merges on CI pass. | M | P1 |
| COS-INFRA-003 | No Logging | No structured logging. Server uses implicit console output. No request IDs, no log levels, no correlation between requests and errors. | MEDIUM | `server/index.ts`, all route handlers | Add `pino` (or `winston`) with structured JSON logging. Request ID middleware. Log all route entries, exits, errors. | M | P1 |
| COS-INFRA-004 | No Health Check | No `/health` or `/ready` endpoint. No way for load balancers, orchestrators, or monitoring to verify app is alive and connected to database. | MEDIUM | `server/routes.ts` | Add `GET /health` (returns 200 if app running) and `GET /ready` (returns 200 if DB connected). | XS | P1 |
| COS-INFRA-005 | No Monitoring | No APM, no error tracking (Sentry/Datadog), no uptime monitoring. Errors in production would be invisible. | MEDIUM | entire codebase | Add Sentry (or equivalent) error tracking. Add basic uptime monitor. | S | P2 |
| COS-INFRA-006 | Repo Bloat | `attached_assets/` has 90 files (~84MB of images and text pastes) committed to git. `uploads/` has 28 user-uploaded media files in git history. | MEDIUM | `attached_assets/`, `uploads/` | Remove from git tracking. Add to `.gitignore`. Use `git filter-branch` or BFG to clean history (optional — reduces clone size). Move assets to S3/R2/external storage. | M | P2 |
| COS-INFRA-007 | Stale Files | Backup files committed: `MessagePanel.tsx.bak`, `MessagePanel.tsx.new`. Dead artifacts from Replit Agent editing. | LOW | `client/src/components/` | Delete `.bak` and `.new` files. Add `*.bak` and `*.new` to `.gitignore`. | XS | P3 |


## UX / Frontend Debt

| ID | Category | Debt | Severity | Location | Remediation | Effort | Priority |
|----|----------|------|----------|----------|-------------|--------|----------|
| COS-UX-001 | Mobile Responsiveness | X/Twitter-inspired design targets mobile-first but responsiveness is unaudited. Replit Agent code may have hardcoded widths, non-responsive layouts. | MEDIUM | `client/src/` | Audit all pages for mobile breakpoints. Fix any hardcoded widths. Verify Tailwind responsive classes. | M | P2 |
| COS-UX-002 | Loading States | No standardized loading pattern. Unknown whether skeleton screens, spinners, or blank states are consistent across pages. | MEDIUM | `client/src/pages/`, `client/src/components/` | Audit all React Query usages. Add consistent loading skeletons. Add error boundaries. | M | P2 |
| COS-UX-003 | Accessibility | No accessibility audit. ARIA labels, keyboard navigation, focus management, screen reader support all unknown. | MEDIUM | `client/src/` | Run Lighthouse accessibility audit. Fix critical a11y violations (missing alt text, focus traps, ARIA). shadcn/ui provides some baseline. | M | P2 |
| COS-UX-004 | Design System Inventory | 90 design reference files exist in `attached_assets/` but no Stitch UI inventory maps them to implemented components. 48 shadcn/ui components installed but usage coverage unknown. | LOW | `attached_assets/`, `client/src/components/ui/` | Create Stitch UI inventory mapping design references to implemented components. Identify gaps between design intent and code. | M | P3 |


## Platform Integration Debt

| ID | Category | Debt | Severity | Location | Remediation | Effort | Priority |
|----|----------|------|----------|----------|-------------|--------|----------|
| COS-INT-001 | UMH Projection | CreatorOS UMH projection code exists (1,099 lines across 6 files) but is unverified at runtime. Signal emitters, capability handlers, and outcome receivers have never been tested against live UMH substrate. | MEDIUM | `projections/creatoros/integration/` | Write integration tests against substrate mock. Verify signal emission, capability dispatch, outcome writeback. Deploy and test with live substrate. | L | P2 |
| COS-INT-002 | No Payment Integration | No Stripe, no PayPal, no payment processing of any kind. Products exist in marketplace with prices but zero checkout flow. The entire commerce primitive (User -> Product -> Order -> Entitlement) is broken at Order. | HIGH | `server/routes.ts`, `shared/schema.ts` | Implement Stripe Connect integration. Add orders table, checkout flow, webhook handler, entitlement granting. | XL | P1 |
| COS-INT-003 | OpenAI Hardcoded | AI agents use `openai 4.91.1` SDK directly. No model routing, no fallback chain, no abstraction layer. Tied to single provider. | MEDIUM | `server/routes.ts` (AI routes) | Abstract AI calls behind a provider interface. Consider routing through UMH model_router or at minimum an adapter that supports multiple providers. | M | P2 |
| COS-INT-004 | No WebSocket Auth | WebSocket server (`ws 8.18.0`) exists for real-time features but WebSocket connection authentication is unverified. May accept unauthenticated connections. | MEDIUM | `server/` (WebSocket setup) | Verify WebSocket upgrade handler validates session cookie or auth token. Reject unauthenticated connections. | S | P1 |


## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 1 |
| HIGH | 14 |
| MEDIUM | 19 |
| LOW | 4 |
| **Total** | **38** |

| Priority | Count |
|----------|-------|
| P0 | 4 |
| P1 | 18 |
| P2 | 13 |
| P3 | 3 |
| **Total** | **38** |

| Category | Count |
|----------|-------|
| Security | 8 |
| Architecture | 7 |
| Testing | 4 |
| Data Model | 7 |
| Infrastructure / DevOps | 7 |
| UX / Frontend | 4 |
| Platform Integration | 4 |


## Critical Path

The following debt items block production deployment and must be resolved in order:

1. **COS-SEC-001** (CRITICAL) — Broken auth. Nothing else matters until auth works. Target: Clerk migration.
2. **COS-SEC-002** (HIGH) — Hardcoded session secret. Eliminated by Clerk migration.
3. **COS-SEC-003** (HIGH) — Rate limiting. Must exist before public traffic.
4. **COS-INFRA-001** (HIGH) — No deployment infrastructure. Cannot ship without it.
5. **COS-ARCH-001 + COS-ARCH-002** (HIGH) — God file decomposition. Must happen before any serious feature work or parallel development.
6. **COS-TEST-001** (HIGH) — Test suite. Must exist before shipping features.
7. **COS-INT-002** (HIGH) — Payment integration. Core monetization primitive.
8. **COS-DATA-001** (HIGH) — Missing 25 tables. Core product features depend on them.


## Notes

- All severity/priority assessments assume CreatorOS is pre-production (no live users, no real data). If deployment timeline accelerates, all P1 security items become P0.
- The Clerk migration (COS-SEC-001) eliminates COS-SEC-002, COS-SEC-007, and COS-SEC-008 as side effects. It should be done as a single coordinated effort, not piecemeal Passport.js fixes.
- God file decomposition (COS-ARCH-001 + COS-ARCH-002) is prerequisite for nearly all other work. The 53KB routes.ts and 104KB storage.ts make every other change harder. Split first, then build.
- The Replit Agent origin (COS-ARCH-003) is pervasive debt — it means every file in the codebase has unknown quality. The test suite (COS-TEST-001) is the antidote: as tests are written, Replit Agent code quality gets verified or corrected.
