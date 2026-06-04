---
phase: "14.6B-EOS"
status: "DRAFT"
operator_approved: false
allows_implementation: false
date: "2026-06-04"
provenance: "OPEN_QUESTION_OPERATOR_DECISION_REQUIRED"
---

# EOS Phase 14.6B: Open Questions & Operator Decision Queue

**Phase:** 14.6B-EOS
**Status:** DRAFT
**Operator Approved:** false
**Allows Implementation:** false
**Date:** 2026-06-04
**Provenance:** OPEN_QUESTION_OPERATOR_DECISION_REQUIRED

---

## Purpose

This document captures every unresolved product, architecture, and business decision
surfaced during the Phase 14.6B EOS lossless canon reconstruction. Each decision
is blocking or partially blocking downstream implementation work. Nothing in this
queue may be assumed — the operator must explicitly approve or override each item
before the corresponding implementation proceeds.

## Decision Format

Each entry includes priority, category, the specific question, enumerated options
with tradeoffs, a default recommendation, and what is blocked pending resolution.

## Ownership Context

- **Product Owner:** OST (Operational Services & Technology entity under Munoz Conglomerate)
- **Hierarchy:** Operator → Portfolio → Entity → Business Operations → Teams/Agents → Workflows/Tasks → Capital/KPIs
- **Communication Model:** User → EA → Portfolio Advisor OR CEO → Department agents
- **Auth State:** Clerk on Beast branch, Passport.js on GitHub main (stale)
- **Codebase State:** GitHub main (202 files, stale since Feb 2026) vs Beast feature/company-system (603 files, active development)
- **MVP Plan:** 5 releases (R1 through R5), single founder single business

---

## P0 — Must Resolve Before Any Implementation

These decisions gate the entire build. No code should be written until P0 is resolved.

---

### DEC-146B-EOS-001: Beast Branch Promotion to Canonical
**Priority:** P0
**Category:** architecture
**Question:** Should the Beast feature/company-system branch (603 files) be promoted as the canonical EOS codebase, deprecating GitHub main (202 files)?
**Options:**
1. **Promote Beast as canonical.** The Beast branch has 401 more files, active Clerk auth integration, company-system architecture, and all recent development. GitHub main has been stale since February 2026. Tradeoff: requires a clean merge strategy for any main-only changes (likely none), and all CI/CD must retarget. Risk is low — the divergence is overwhelmingly additive on Beast.
2. **Merge Beast into main incrementally.** Cherry-pick Beast changes into main over time. Tradeoff: enormous effort for 401-file divergence, high risk of subtle integration bugs, delays all other work by weeks. No clear benefit over option 1.
3. **Start fresh from neither.** Use the canon reconstruction as the new source of truth and rebuild. Tradeoff: throws away working code on Beast, massively increases timeline. Only justified if both codebases are fundamentally flawed.
**Default Recommendation:** Option 1. Promote Beast as canonical. The divergence is too large for incremental merge, and GitHub main has no unique value.
**Blocked By This:** Every implementation task. Cannot write code without knowing which codebase is the starting point.
**Provenance:** OPEN_QUESTION_OPERATOR_DECISION_REQUIRED

---

### DEC-146B-EOS-002: MVP Scope Confirmation — 5-Release Plan (R1-R5)
**Priority:** P0
**Category:** product_scope
**Question:** Is the 5-release MVP plan (R1 through R5) confirmed as the implementation roadmap, with R1 targeting single-founder single-business?
**Options:**
1. **Confirm R1-R5 as defined.** R1: Auth + onboarding + single company dashboard. R2: EA + basic delegation. R3: Financial tracking + KPIs. R4: Workflow SOPs + templates. R5: Agent autonomy + polish. Tradeoff: well-scoped, predictable, ships value incrementally.
2. **Compress to R1-R3.** Merge R4/R5 content into R3 for a faster "complete" MVP. Tradeoff: higher per-release complexity, longer time-to-first-ship, but fewer total releases to manage.
3. **Expand to R1-R7.** Slice thinner for even faster first ship. Tradeoff: more releases to coordinate, but R1 could ship in days instead of weeks.
4. **Redefine scope entirely.** The PRD and canon may have surfaced scope that doesn't match current priorities. Tradeoff: delays everything while re-scoping.
**Default Recommendation:** Option 1. The R1-R5 plan is well-structured and already documented across multiple canon artifacts.
**Blocked By This:** Implementation sequencing, sprint planning, all milestone definitions.
**Provenance:** OPEN_QUESTION_OPERATOR_DECISION_REQUIRED

---

### DEC-146B-EOS-003: Auth Finalization — Clerk Confirmed as Production Auth?
**Priority:** P0
**Category:** auth_security
**Question:** Is Clerk confirmed as the production authentication provider for EOS, replacing the Passport.js implementation on GitHub main?
**Options:**
1. **Confirm Clerk.** Beast branch already has Clerk integration (publishableKey, middleware, ClerkProvider). Managed auth reduces security surface. Tradeoff: vendor dependency, monthly cost at scale ($25/mo at 1K MAU, scales up), less control over auth flow customization.
2. **Switch to Auth.js (NextAuth successor).** Open source, self-hosted, no vendor lock-in. Tradeoff: more implementation work, must handle session management, token refresh, MFA ourselves. Beast Clerk work is thrown away.
3. **Switch to Supabase Auth.** If Supabase is considered for any other function, bundling auth reduces vendor count. Tradeoff: ties auth to database provider, migration complexity if we ever leave Supabase.
4. **Keep Passport.js from main.** Use the existing implementation. Tradeoff: stale code, GitHub main is 4 months behind, Passport.js requires more manual session/token management.
**Default Recommendation:** Option 1. Clerk is already integrated on Beast, works well for MVP scale, and can be swapped later if cost becomes prohibitive.
**Blocked By This:** All user-facing features, RLS policy design, session management, middleware architecture.
**Provenance:** OPEN_QUESTION_OPERATOR_DECISION_REQUIRED

---

## P1 — Must Resolve Before R1 Ships

These decisions affect R1 implementation directly. They can be resolved in parallel with initial setup work but must be answered before R1 feature development completes.

---

### DEC-146B-EOS-004: Embedding Dimension — 384 vs 1536
**Priority:** P1
**Category:** architecture
**Question:** What embedding dimension should EOS use for vector storage (knowledge base, semantic search, agent memory)?
**Options:**
1. **384-dimensional (e.g., all-MiniLM-L6-v2, Nomic Embed).** Faster, cheaper, smaller storage footprint. Good enough for most retrieval tasks. Tradeoff: lower semantic resolution for nuanced queries, may miss subtle distinctions in business documents.
2. **1536-dimensional (e.g., OpenAI text-embedding-3-small, Cohere embed-v3).** Industry standard, higher semantic fidelity. Tradeoff: 4x storage cost, slower similarity search at scale, API cost per embedding call.
3. **Adaptive — 384 for MVP, migrate to 1536 later.** Start cheap, upgrade when data volume justifies it. Tradeoff: migration requires re-embedding all stored vectors, which is a one-time batch job but non-trivial.
4. **Matryoshka embeddings (e.g., Nomic Embed with dimension truncation).** Store at 1536 but query at 384 for speed, full dimension for precision. Tradeoff: not all providers support this, adds complexity.
**Default Recommendation:** Option 3. Start with 384 for MVP cost efficiency. The canon should define the migration path so it's not a surprise later.
**Blocked By This:** Vector storage schema design, pgvector column definitions, embedding pipeline implementation.
**Provenance:** OPEN_QUESTION_OPERATOR_DECISION_REQUIRED

---

### DEC-146B-EOS-005: Pricing Model — No Pricing Defined in PRD
**Priority:** P1
**Category:** product_scope
**Question:** What is the EOS pricing model? The PRD and all source documents define features but contain zero pricing information.
**Options:**
1. **Flat monthly subscription.** e.g., $49/mo Starter, $99/mo Pro, $199/mo Business. Simple, predictable revenue. Tradeoff: doesn't capture value from heavy users, may be too expensive for solo founders starting out.
2. **Usage-based pricing.** Charge per AI agent action, per workflow execution, or per active business entity. Tradeoff: unpredictable costs scare away early users, complex billing infrastructure needed.
3. **Freemium + paid tiers.** Free tier with 1 business + limited agents, paid tiers unlock more. Tradeoff: free tier costs money to run, but lowers barrier to entry for the $10K/mo target market (solo founders).
4. **Founder-access pricing.** Single price point ($29-49/mo) during MVP, with the understanding that pricing will evolve. Tradeoff: leaves money on the table from power users, but maximizes early adoption.
5. **Defer pricing until post-R3.** Build the product first, price based on observed usage patterns. Tradeoff: delays revenue, but avoids pricing mistakes.
**Default Recommendation:** Option 4. Single founder-access price ($39/mo) for MVP. Revisit after 50 paying users. This aligns with the $10K/mo target — need ~256 users at $39/mo.
**Blocked By This:** Stripe integration scope, onboarding flow design, feature gating logic, landing page copy.
**Provenance:** OPEN_QUESTION_OPERATOR_DECISION_REQUIRED

---

### DEC-146B-EOS-006: UBOS Template Library — Community Contributed or Curated Only?
**Priority:** P1
**Category:** product_scope
**Question:** Should the Universal Business Operating System (UBOS) template library accept community-contributed templates, or only operator-curated templates?
**Options:**
1. **Curated only at MVP.** Operator (AFM) and AI create all templates. Quality is guaranteed. Tradeoff: limited template variety, all creation burden on operator.
2. **Community-contributed from R3+.** Allow users to submit templates after core library is proven. Tradeoff: requires review/approval workflow, quality control, potential for spam/low-quality submissions.
3. **Community-contributed from R1.** Open marketplace from day one. Tradeoff: high risk of low-quality templates polluting the library, significant moderation overhead, but maximizes content growth.
4. **AI-generated templates only.** Use the agent system to generate business-specific templates on demand. Tradeoff: quality varies by prompt, no reuse across users without curation layer.
**Default Recommendation:** Option 1 for MVP (R1-R3), transition to option 2 at R4+ with an approval workflow.
**Blocked By This:** Template data model (does it need author_id, approval_status, community_rating fields?), template CRUD API scope.
**Provenance:** OPEN_QUESTION_OPERATOR_DECISION_REQUIRED

---

### DEC-146B-EOS-007: Portfolio Multi-Company — Deferred to Post-MVP or MVP R1?
**Priority:** P1
**Category:** product_scope
**Question:** The hierarchy defines Portfolio → Entity → Business, implying multi-company support. Does R1 ship with single-company only, or does the schema support multi-company from day one?
**Options:**
1. **Single company in R1, multi-company post-MVP.** Simplifies onboarding, reduces schema complexity, focuses on proving value for one business first. Tradeoff: schema migration later when adding portfolio layer, potential data model rework.
2. **Schema supports multi-company from R1, UI is single-company.** Build the portfolio/entity/business hierarchy into the database from day one, but the UI only shows one company. Tradeoff: slightly more upfront schema work, but zero migration pain later. The hierarchy is already defined in the ontology.
3. **Full multi-company in R1.** Ship portfolio management from the start. Tradeoff: significantly more UI work, onboarding complexity, edge cases around cross-company data access.
**Default Recommendation:** Option 2. The ontology already defines the hierarchy — encoding it in the schema costs very little upfront and avoids a painful migration. UI stays single-company for R1.
**Blocked By This:** Database schema design, RLS policy scope, onboarding flow complexity.
**Provenance:** OPEN_QUESTION_OPERATOR_DECISION_REQUIRED

---

### DEC-146B-EOS-008: Agent Autonomy Levels — What Ships at MVP vs End-State?
**Priority:** P1
**Category:** product_scope
**Question:** The agent architecture defines multiple autonomy levels (from fully manual to fully autonomous). What level ships at R1 vs R5 vs end-state?
**Options:**
1. **R1: Manual only (user triggers all actions).** Agents are suggestion engines — they recommend but never act. Tradeoff: safest, but feels like a fancy dashboard rather than an AI operating system.
2. **R1: Semi-autonomous (agents act with approval).** Agents queue actions, user approves/rejects. Tradeoff: requires approval queue UI, notification system, but delivers the core AI-assisted promise.
3. **R1: Tier-based (low-risk actions auto-execute, high-risk require approval).** Risk classification determines autonomy. Tradeoff: requires governance engine from day one, more complex but most aligned with UMH philosophy.
4. **R1: Full autonomy with kill switch.** Agents act freely, user can pause/stop. Tradeoff: highest risk, highest reward, but trust must be earned — dangerous for a new product.
**Default Recommendation:** Option 2 for R1-R2, transition to option 3 at R3 when governance engine is proven. Option 4 is end-state only.
**Blocked By This:** Agent execution pipeline design, governance UI requirements, notification system scope, risk classification implementation.
**Provenance:** OPEN_QUESTION_OPERATOR_DECISION_REQUIRED

---

### DEC-146B-EOS-009: RLS Strategy — org_id Scoped Neon RLS Approach?
**Priority:** P1
**Category:** auth_security
**Question:** Should EOS use Neon's Row-Level Security with org_id scoping as the primary data isolation mechanism?
**Options:**
1. **Full RLS on all tenant tables.** Every table with user/org data gets RLS policies scoped to org_id. Tradeoff: strongest isolation, but complex to maintain, can cause subtle query performance issues, every migration must update policies.
2. **Application-level isolation only.** All queries include WHERE org_id = ? at the application layer. Tradeoff: simpler to implement and debug, but a single missed WHERE clause is a data leak. No defense in depth.
3. **Hybrid — RLS on sensitive tables, application-level elsewhere.** Financial data, PII, and auth tables get RLS. Reference data and templates use application-level filtering. Tradeoff: pragmatic balance, but requires clear documentation of which tables are RLS-protected.
4. **Separate schemas per org.** Each org gets its own Postgres schema. Tradeoff: strongest isolation, simplest queries, but dramatically increases operational complexity for migrations, backups, and connection pooling.
**Default Recommendation:** Option 3. Full RLS on financial, PII, and auth tables. Application-level isolation on everything else. Document the boundary clearly.
**Blocked By This:** Every database migration, Drizzle schema design, query patterns, Neon branch strategy.
**Provenance:** OPEN_QUESTION_OPERATOR_DECISION_REQUIRED

---

### DEC-146B-EOS-010: Deployment Target — Fly.io Confirmed?
**Priority:** P1
**Category:** architecture
**Question:** Is Fly.io confirmed as the production deployment platform for EOS?
**Options:**
1. **Confirm Fly.io.** Already used for UMH cockpit (universalmetaharness.tech). Familiar platform, edge deployment, good DX. Tradeoff: can get expensive at scale, vendor-specific Dockerfile patterns, limited GPU access for AI workloads.
2. **Switch to Railway.** Simpler deployment model, generous free tier, good for early-stage. Tradeoff: less mature than Fly, fewer regions, less control over networking.
3. **Switch to Vercel (frontend) + separate API host.** Vercel for the React app, Fly/Railway for the Express API. Tradeoff: splits deployment across two platforms, but Vercel is best-in-class for frontend.
4. **Self-host on VPS.** Deploy directly to VPS via Docker Compose. Tradeoff: no auto-scaling, single point of failure, but zero vendor cost and full control.
5. **Defer — containerize cleanly, deploy anywhere.** Write clean Dockerfiles, deploy to Fly for now, switch later if needed. Tradeoff: no decision is a decision — but if Dockerfiles are clean, migration is cheap.
**Default Recommendation:** Option 5. Deploy to Fly.io now (familiar, working), but ensure Dockerfiles are portable. Revisit at scale.
**Blocked By This:** CI/CD pipeline design, environment variable management, database connection strategy, deployment scripts.
**Provenance:** OPEN_QUESTION_OPERATOR_DECISION_REQUIRED

---

## P2 — Should Resolve Before R3 Ships

These decisions affect mid-term architecture and product direction. They can be deferred during R1 but will cause rework if not resolved before R3.

---

### DEC-146B-EOS-011: Mobile Strategy — Responsive Web vs Native App
**Priority:** P2
**Category:** design_ux
**Question:** What is the mobile strategy for EOS? The PRD mentions mobile access but doesn't specify the approach.
**Options:**
1. **Responsive web only.** The React app adapts to mobile viewports. Tradeoff: lowest development cost, single codebase, but limited access to push notifications, offline mode, and device APIs.
2. **PWA (Progressive Web App).** Responsive web with service worker for offline, push notifications, and home screen install. Tradeoff: moderate additional effort, covers 80% of native app benefits, but iOS PWA support is still limited.
3. **React Native app (post-MVP).** Build a dedicated mobile app after web MVP is proven. Tradeoff: high development cost, separate codebase, but best mobile UX. Justifiable only after product-market fit.
4. **Capacitor/Ionic wrapper.** Wrap the web app in a native shell for app store distribution. Tradeoff: app store presence with minimal additional code, but performance and UX are noticeably worse than native.
**Default Recommendation:** Option 2. PWA gives mobile presence with minimal additional effort. Native app only after PMF and revenue justify it.
**Blocked By This:** UI component library choices (touch targets, mobile navigation patterns), notification architecture.
**Provenance:** OPEN_QUESTION_OPERATOR_DECISION_REQUIRED

---

### DEC-146B-EOS-012: Local/Private AI Runtime Scope
**Priority:** P2
**Category:** architecture
**Question:** The PRD mentions local/private AI capabilities. What is the scope of local AI processing in EOS?
**Options:**
1. **Cloud-only AI for MVP.** All LLM calls go through cloud APIs (Anthropic, OpenAI, Google). Tradeoff: simplest implementation, but users with privacy concerns may not adopt. Per-call API costs eat into margin.
2. **Optional local runtime via Ollama.** Users can self-host an Ollama instance and point EOS at it. Tradeoff: adds configuration complexity, model quality varies, but differentiates from competitors who are cloud-only.
3. **Hybrid — cloud for complex tasks, local for simple classification/extraction.** Use small local models for classification, entity extraction, and embedding. Cloud for generation and reasoning. Tradeoff: best cost/quality balance, but requires maintaining two inference paths.
4. **Defer entirely to post-MVP.** Ship cloud-only, add local runtime when demand materializes. Tradeoff: may lose privacy-conscious early adopters, but simplifies R1-R5 scope significantly.
**Default Recommendation:** Option 4 for MVP. Cloud-only is simpler and the target market (solo founders) is unlikely to self-host AI.
**Blocked By This:** Model routing architecture, agent runtime design, cost estimation, infrastructure requirements documentation.
**Provenance:** OPEN_QUESTION_OPERATOR_DECISION_REQUIRED

---

### DEC-146B-EOS-013: Multi-Region Deployment
**Priority:** P2
**Category:** architecture
**Question:** Does EOS need multi-region deployment before scaling beyond MVP?
**Options:**
1. **Single region (US) for MVP and early growth.** Deploy everything to one Fly.io region. Tradeoff: higher latency for non-US users, but simplifies database replication, caching, and debugging.
2. **Multi-region read replicas at R3.** Primary write region in US, read replicas in EU and APAC. Tradeoff: moderate complexity, covers latency for reads (dashboards, reports), writes still go to primary.
3. **Full multi-region at scale.** Deploy application servers and database in multiple regions with conflict resolution. Tradeoff: significant engineering complexity, only justified at thousands of active users across geographies.
4. **Edge-first with Fly.io.** Fly natively supports edge deployment — application runs close to users, database stays centralized. Tradeoff: easy to enable on Fly, minimal code changes, but database latency remains.
**Default Recommendation:** Option 1 for MVP through early growth. Option 4 is nearly free on Fly if we need it. Multi-region database only when user geography data demands it.
**Blocked By This:** Database connection pooling strategy, session affinity design, cache invalidation patterns.
**Provenance:** OPEN_QUESTION_OPERATOR_DECISION_REQUIRED

---

### DEC-146B-EOS-014: Skill Marketplace Economics
**Priority:** P2
**Category:** product_scope
**Question:** If/when EOS has a skill marketplace, what are the economics? Revenue share? Free-only? Paid skills?
**Options:**
1. **Free marketplace, curated.** All skills are free, operator curates for quality. Tradeoff: no marketplace revenue, but builds ecosystem and user value. Similar to VS Code extensions.
2. **Paid marketplace with revenue share (70/30 creator/platform).** Creators can charge for premium skills. Tradeoff: requires payment processing, dispute resolution, creator payouts. Significant infrastructure for a feature that may not drive meaningful revenue.
3. **Freemium marketplace.** Skills are free to publish, premium features (analytics, priority support, featured placement) are paid. Tradeoff: lower friction than paid skills, but revenue is from creators not users.
4. **Defer marketplace entirely.** Template library is operator-curated, no third-party marketplace until post-PMF. Tradeoff: simplest approach, but misses community flywheel opportunity.
**Default Recommendation:** Option 4 for MVP. Marketplace economics are a distraction before PMF. Revisit when there are 100+ active users generating templates worth sharing.
**Blocked By This:** Template data model (marketplace fields), API scope, creator onboarding flow.
**Provenance:** OPEN_QUESTION_OPERATOR_DECISION_REQUIRED

---

### DEC-146B-EOS-015: Competitive Positioning vs Monday.com / Notion / ClickUp
**Priority:** P2
**Category:** product_scope
**Question:** How does EOS position against established project/business management tools? This affects feature priority, marketing, and pricing.
**Options:**
1. **"AI-native business OS" — fundamentally different category.** Position as the first platform where AI agents are first-class team members, not just copilots. Tradeoff: requires strong AI differentiation from day one, which is hard with current LLM limitations.
2. **"Notion for business operations."** Position as a structured business operations tool with AI assistance. Tradeoff: easier to explain, but invites direct comparison with Notion (which has massive head start).
3. **"Fractional COO in a box."** Position as an AI-powered COO for solo founders who can't afford to hire. Tradeoff: narrow but compelling positioning, directly addresses the target market's pain point. The $10K/mo target market resonates with "I need help running my business."
4. **Avoid direct competition — focus on niche.** Target a specific vertical (e.g., service businesses, agencies, consultants) rather than competing broadly. Tradeoff: smaller TAM, but higher conversion and clearer messaging.
**Default Recommendation:** Option 3. "Fractional COO in a box" is the most compelling positioning for solo founders at the $10K/mo stage. It's specific, valuable, and hard for horizontal tools to match.
**Blocked By This:** Landing page copy, onboarding messaging, feature prioritization (COO-relevant features first), marketing strategy.
**Provenance:** OPEN_QUESTION_OPERATOR_DECISION_REQUIRED

---

### DEC-146B-EOS-016: Knowledge Graph Technology Choice
**Priority:** P2
**Category:** architecture
**Question:** The data ontology includes knowledge graph capabilities. What technology powers the knowledge graph?
**Options:**
1. **pgvector + Postgres full-text search.** Use Neon's pgvector extension for embeddings and Postgres FTS for keyword search. Tradeoff: no additional infrastructure, good enough for MVP, but not a true graph database — relationship traversal is SQL joins.
2. **Neo4j (managed or self-hosted).** Purpose-built graph database. Tradeoff: best for relationship-heavy queries (e.g., "which agents depend on which workflows"), but adds infrastructure complexity and cost.
3. **Apache AGE (Postgres graph extension).** Graph query support inside Postgres. Tradeoff: no additional infrastructure, Cypher-like queries, but AGE is less mature than Neo4j and may have edge cases.
4. **Hybrid — Postgres for structured data, lightweight in-memory graph for relationships.** Use a Python graph library (NetworkX) for relationship traversal, backed by Postgres tables. Tradeoff: no new infrastructure, works well for small graphs, breaks down at scale.
5. **Defer — relational only for MVP.** Standard Postgres tables with foreign keys for relationships. Add graph capabilities when query patterns demand it. Tradeoff: simplest approach, may require rework if graph queries become critical.
**Default Recommendation:** Option 1 for MVP (pgvector + FTS), with option to add Apache AGE if graph traversal queries become common. No new infrastructure until proven necessary.
**Blocked By This:** Knowledge base schema design, semantic search implementation, agent memory architecture.
**Provenance:** OPEN_QUESTION_OPERATOR_DECISION_REQUIRED

---

### DEC-146B-EOS-017: SSO / Magic Link Strategy
**Priority:** P2
**Category:** auth_security
**Question:** Beyond email/password (provided by Clerk), what additional auth methods should EOS support?
**Options:**
1. **Clerk defaults only (email/password + OAuth providers).** Google, GitHub, Apple sign-in via Clerk's built-in OAuth. Tradeoff: covers 90% of solo founders, zero additional implementation.
2. **Add magic link (passwordless email).** Users click a link in email to sign in, no password needed. Tradeoff: better UX for infrequent users, supported by Clerk out-of-box, but email deliverability issues can lock users out.
3. **Add SSO (SAML/OIDC) for enterprise.** Allow organizations to bring their own identity provider. Tradeoff: expensive Clerk tier ($50+ per SAML connection), only relevant for enterprise customers (not MVP target).
4. **Add passkey/WebAuthn support.** Biometric authentication. Tradeoff: cutting-edge UX, supported by Clerk, but adoption is still low and may confuse less technical users.
**Default Recommendation:** Option 2. Magic link is free in Clerk, improves UX, and requires zero code beyond Clerk configuration. SSO is post-PMF only.
**Blocked By This:** Clerk configuration, onboarding flow design, login page UI.
**Provenance:** OPEN_QUESTION_OPERATOR_DECISION_REQUIRED

---

### DEC-146B-EOS-018: Python-TypeScript Bridge Architecture
**Priority:** P2
**Category:** architecture
**Question:** EOS has a TypeScript frontend/API and Python AI backend (UMH). How do they communicate?
**Options:**
1. **HTTP REST API between TypeScript and Python.** Express backend calls Python services via HTTP. Tradeoff: well-understood, easy to debug, but adds latency per call and requires running Python as a separate service.
2. **stdin/stdout JSON protocol (current UMH pattern).** TypeScript spawns Python subprocess, communicates via JSON over stdio. Tradeoff: fast, no network overhead, already implemented in UMH (transports/api/ bridges), but subprocess lifecycle management is tricky.
3. **gRPC between TypeScript and Python.** Strong typing, streaming support, efficient binary protocol. Tradeoff: more setup than REST, requires proto file management, but better for high-frequency calls.
4. **Message queue (Redis/NATS).** Async communication via message broker. Tradeoff: best for fire-and-forget agent tasks, but adds infrastructure dependency and complexity for simple request/response patterns.
5. **Hybrid — REST for synchronous, message queue for async agent tasks.** Use REST for UI-driven requests, queue for long-running agent tasks. Tradeoff: two communication patterns to maintain, but each is optimal for its use case.
**Default Recommendation:** Option 2 for MVP (already built in UMH), transition to option 5 as agent task complexity grows. The stdio bridge works and ships faster than any alternative.
**Blocked By This:** Agent execution architecture, API route design, deployment topology (co-located vs separate services).
**Provenance:** OPEN_QUESTION_OPERATOR_DECISION_REQUIRED

---

### DEC-146B-EOS-019: CI/CD Platform Selection
**Priority:** P2
**Category:** implementation_sequencing
**Question:** What CI/CD platform runs EOS builds, tests, and deployments?
**Options:**
1. **GitHub Actions.** Already using GitHub for source control. Native integration, generous free tier, extensive marketplace. Tradeoff: YAML-heavy configuration, can be slow for complex pipelines.
2. **Fly.io built-in deploy (flyctl deploy).** If deploying to Fly, use their built-in deploy command triggered by GitHub webhook. Tradeoff: simplest possible pipeline, but limited to deployment — no test/lint/build stages.
3. **Self-hosted runner on VPS.** GitHub Actions runner on the VPS for faster builds and access to local resources. Tradeoff: free, fast, but single point of failure and maintenance burden.
4. **Defer — manual deploy for MVP.** SSH into VPS/Fly, run deploy script manually. Tradeoff: simplest, no setup, but error-prone and doesn't scale past one developer.
**Default Recommendation:** Option 1 with option 2 for the deploy step. GitHub Actions for lint/test/build, flyctl deploy for deployment. Standard, well-documented, free.
**Blocked By This:** Branch protection rules, deployment automation, test suite execution, environment secret management.
**Provenance:** OPEN_QUESTION_OPERATOR_DECISION_REQUIRED

---

### DEC-146B-EOS-020: Error Tracking / Monitoring Tool
**Priority:** P2
**Category:** architecture
**Question:** What tool captures and surfaces production errors and performance data for EOS?
**Options:**
1. **Sentry.** Industry standard error tracking. Free tier covers MVP. Tradeoff: excellent DX, source maps, issue grouping, but another vendor dependency.
2. **PostHog.** Already in the UMH ecosystem (PostHog plugin exists). Combines analytics + error tracking + session replay. Tradeoff: error tracking is newer/less mature than Sentry, but reduces vendor count.
3. **BetterStack (formerly Logtail).** Log-based monitoring with alerting. Tradeoff: good for log aggregation, but less structured than Sentry for error tracking.
4. **Console logging + health endpoint only.** Minimal monitoring — structured logs to stdout, a /health endpoint, and manual log review. Tradeoff: zero cost, but blind to errors users don't report. Only viable for very early MVP.
5. **Sentry (errors) + PostHog (analytics).** Best-of-breed for each function. Tradeoff: two vendors, but each excels at its job.
**Default Recommendation:** Option 5. Sentry free tier for errors, PostHog for analytics. Both have SDKs for React + Express. Switch to option 2 if PostHog error tracking matures.
**Blocked By This:** Error handling middleware, frontend error boundary design, alerting configuration, deployment verification.
**Provenance:** OPEN_QUESTION_OPERATOR_DECISION_REQUIRED

---

## P3 — Long-Term Architecture Decisions

These decisions affect scale and enterprise features. They should be documented now so architectural choices don't accidentally close doors, but implementation is post-MVP.

---

### DEC-146B-EOS-021: Enterprise Permissions Model Detail
**Priority:** P3
**Category:** auth_security
**Question:** What is the detailed permissions model for multi-user organizations? The current canon defines roles (Operator, Manager, Member) but not granular permissions.
**Options:**
1. **Role-based access control (RBAC) with fixed roles.** Operator (full access), Manager (team-level), Member (own data only). Tradeoff: simple to implement and understand, but inflexible for organizations with custom structures.
2. **RBAC with custom roles.** Allow organizations to define their own roles with granular permission toggles. Tradeoff: more flexible, but complex UI for role management, more testing surface.
3. **Attribute-based access control (ABAC).** Permissions based on user attributes, resource attributes, and context (time, location). Tradeoff: most flexible, but complex to implement, hard to reason about, and overkill for MVP target market.
4. **Clerk Organizations + custom layer.** Use Clerk's built-in organization/role system for auth-level permissions, add application-level permissions for business logic. Tradeoff: leverages existing Clerk investment, but creates two permission systems to maintain.
**Default Recommendation:** Option 1 for MVP (three fixed roles), transition to option 4 when enterprise customers arrive. The schema should include a permissions table from day one to avoid migration.
**Blocked By This:** Team management UI (post-MVP), enterprise sales readiness, compliance requirements.
**Provenance:** OPEN_QUESTION_OPERATOR_DECISION_REQUIRED

---

### DEC-146B-EOS-022: White-Label / Multi-Tenant Architecture
**Priority:** P3
**Category:** architecture
**Question:** Will EOS ever support white-labeling (resellers deploy their own branded version) or is it strictly multi-tenant SaaS?
**Options:**
1. **Multi-tenant SaaS only.** Single deployment, all users share infrastructure. Tradeoff: simplest operations, lowest cost, but no customization per organization beyond settings.
2. **Multi-tenant with theming.** Single deployment, organizations can customize colors/logos/domain. Tradeoff: moderate additional work (theme system, custom domain mapping), but significantly increases enterprise appeal.
3. **White-label ready.** Separate deployable instances per reseller with full branding. Tradeoff: complex deployment orchestration, per-instance costs, but opens reseller revenue channel.
4. **Defer entirely.** Build standard SaaS, evaluate white-label demand later. Tradeoff: architectural decisions now may make white-labeling harder later (e.g., hardcoded brand references).
**Default Recommendation:** Option 1 for MVP with awareness of option 2. Avoid hardcoding brand assets (use a theme config), so theming is easy to add later. White-label is post-PMF only.
**Blocked By This:** CSS architecture (theme variables vs hardcoded), asset loading patterns, domain configuration, deployment topology.
**Provenance:** OPEN_QUESTION_OPERATOR_DECISION_REQUIRED

---

### DEC-146B-EOS-023: API Versioning Strategy
**Priority:** P3
**Category:** architecture
**Question:** How will the EOS API handle versioning as the product evolves?
**Options:**
1. **URL path versioning (/api/v1/).** Explicit, visible, well-understood. Tradeoff: URL clutter, maintaining parallel route handlers for multiple versions.
2. **Header-based versioning (Accept-Version: v1).** Clean URLs, version in request header. Tradeoff: less visible, harder to test with browser, but cleaner API surface.
3. **No versioning for MVP, add at first breaking change.** Ship without version prefix, add /v2 when v1 needs breaking changes. Tradeoff: simplest start, but the first breaking change requires migrating all clients to /v1 retroactively.
4. **Date-based versioning (Stripe pattern).** API version is a date (2026-06-04). Tradeoff: very flexible, allows gradual deprecation, but complex to implement and maintain.
**Default Recommendation:** Option 1. URL path versioning (/api/v1/) from day one. Near-zero cost to implement, avoids the painful retrofit of option 3.
**Blocked By This:** Express router structure, API documentation, client SDK generation (if any).
**Provenance:** OPEN_QUESTION_OPERATOR_DECISION_REQUIRED

---

### DEC-146B-EOS-024: Internationalization / Localization
**Priority:** P3
**Category:** product_scope
**Question:** Will EOS support languages other than English?
**Options:**
1. **English only, indefinitely.** Target market is English-speaking solo founders. Tradeoff: limits TAM to English-speaking markets, but avoids significant i18n engineering overhead.
2. **English-first, i18n-ready architecture.** Use react-i18next or similar from day one, but only ship English translations. Tradeoff: small upfront cost (~2-4 hours to set up), makes future translation trivial, avoids the painful retrofit.
3. **Multi-language from R3.** Ship English, Spanish, Portuguese for initial Latin American market entry. Tradeoff: significant translation effort, ongoing maintenance of translation files, but opens large market.
4. **AI-translated on demand.** Use LLM to translate UI strings at runtime or build time. Tradeoff: innovative but unreliable for UI copy, would need human review, and adds latency.
**Default Recommendation:** Option 2. Set up react-i18next skeleton in R1, ship English only. The 2-hour investment now saves weeks of retrofit later.
**Blocked By This:** UI string handling patterns (hardcoded vs i18n keys), date/number formatting, right-to-left support consideration.
**Provenance:** OPEN_QUESTION_OPERATOR_DECISION_REQUIRED

---

### DEC-146B-EOS-025: Data Retention / Compliance Policy
**Priority:** P3
**Category:** data_privacy
**Question:** What data retention and compliance policies does EOS follow? This affects schema design, backup strategy, and legal requirements.
**Options:**
1. **Retain everything, delete on request.** Store all user data indefinitely, honor deletion requests manually (GDPR Article 17). Tradeoff: simplest implementation, but accumulates data and may violate GDPR's data minimization principle.
2. **Tiered retention policy.** Active data retained indefinitely, inactive account data archived after 12 months, deleted after 24 months. Tradeoff: requires archive/deletion jobs, user notification before deletion, but clean data hygiene.
3. **User-controlled retention.** Let users set their own retention periods per data type. Tradeoff: most flexible, good for enterprise, but complex UI and implementation.
4. **GDPR + CCPA compliant from day one.** Implement right to deletion, data export, consent management, privacy policy. Tradeoff: significant upfront legal and engineering work, but required before selling to EU customers.
5. **Minimal compliance, enhance on demand.** Privacy policy + ToS + deletion endpoint. Add formal compliance as regulatory or customer requirements demand it. Tradeoff: legal risk if EU customers sign up before compliance is in place.
**Default Recommendation:** Option 5 for MVP. Privacy policy, ToS, and a soft-delete endpoint. GDPR compliance before any EU marketing. The schema should use soft deletes (deleted_at column) from day one.
**Blocked By This:** Database schema patterns (soft delete columns), backup strategy, legal document creation, data export endpoint.
**Provenance:** OPEN_QUESTION_OPERATOR_DECISION_REQUIRED

---

### DEC-146B-EOS-026: Voice/Audio Integration Scope
**Priority:** P2
**Category:** product_scope
**Question:** The UMH substrate has voice session capabilities. Does EOS expose voice interaction to users?
**Options:**
1. **No voice in MVP.** Text-only interaction with agents. Tradeoff: simpler UX, no audio infrastructure needed, but misses the "talk to your AI COO" differentiator.
2. **Voice input only (speech-to-text).** Users can speak commands/queries, transcribed to text, processed as normal. Tradeoff: moderate UX improvement, Web Speech API is free in-browser, but one-directional.
3. **Full voice conversation (STT + TTS).** Users can have spoken conversations with agents via Kokoro TTS (already on Beast) and Whisper/Deepgram for STT. Tradeoff: significant infrastructure (audio streaming, TTS service, STT service), but dramatically differentiates from competitors.
4. **Voice as premium feature (R4+).** Build text-first, add voice as a premium/paid feature later. Tradeoff: defers complexity, creates upsell opportunity, but delays a key differentiator.
**Default Recommendation:** Option 4. Voice is a strong differentiator but complex to ship. Text-first for R1-R3, voice as premium feature in R4.
**Blocked By This:** Audio infrastructure requirements, TTS/STT service selection, real-time communication architecture, bandwidth requirements.
**Provenance:** OPEN_QUESTION_OPERATOR_DECISION_REQUIRED

---

### DEC-146B-EOS-027: Notification System Architecture
**Priority:** P1
**Category:** architecture
**Question:** How does EOS notify users of agent actions, approvals needed, and system events?
**Options:**
1. **In-app notifications only.** Bell icon with notification dropdown, similar to GitHub. Tradeoff: only visible when user is in the app, no way to reach them otherwise.
2. **In-app + email notifications.** Real-time in-app via WebSocket, async via email for important events. Tradeoff: covers online and offline users, email infrastructure needed (SendGrid/Resend), user preferences UI required.
3. **In-app + email + push (PWA).** Add browser push notifications via Web Push API. Tradeoff: best reach, but push notification permission UX is often annoying, and iOS PWA push support is limited.
4. **In-app + email + SMS.** SMS for critical alerts (agent failures, financial anomalies). Tradeoff: most reliable for urgent notifications, but SMS costs money per message (Twilio) and requires phone number collection.
5. **In-app + email + webhook (extensible).** Users can configure webhooks to forward notifications to Slack, Discord, Zapier, etc. Tradeoff: most extensible, appeals to technical users, but requires webhook management UI.
**Default Recommendation:** Option 2 for R1-R2 (in-app + email covers 95% of use cases), add option 5 at R3+ for power users.
**Blocked By This:** Real-time infrastructure (WebSocket/SSE), email service selection, notification preferences schema, agent approval queue design.
**Provenance:** OPEN_QUESTION_OPERATOR_DECISION_REQUIRED

---

### DEC-146B-EOS-028: Financial Data Source Integration
**Priority:** P2
**Category:** product_scope
**Question:** How does EOS ingest financial data? Manual entry, bank integration, or accounting software sync?
**Options:**
1. **Manual entry only for MVP.** Users input revenue, expenses, and KPIs manually. Tradeoff: zero integration complexity, but high friction — users will stop entering data.
2. **Plaid integration for bank accounts.** Auto-import transactions from bank accounts via Plaid. Tradeoff: powerful but expensive ($500+/mo at scale), requires PCI-adjacent security practices, complex onboarding.
3. **Accounting software sync (QuickBooks, Xero, Wave).** Import from the tools solo founders already use. Tradeoff: covers the target market well, but each integration is a separate build. QuickBooks alone is a significant OAuth + API integration.
4. **CSV/spreadsheet import.** Users upload bank statements or accounting exports. Tradeoff: low-tech but flexible, covers users who don't use accounting software, requires parsing logic for multiple formats.
5. **Manual entry + CSV import for MVP, Plaid/accounting sync post-MVP.** Start simple, add integrations when user demand is clear. Tradeoff: high friction initially, but ships faster.
**Default Recommendation:** Option 5. Manual entry + CSV import for R1-R3. Survey users at R3 to determine which integration (Plaid vs QuickBooks vs Xero) to build first.
**Blocked By This:** Financial tracking schema design (does it need transaction_source field?), import pipeline architecture, data validation rules.
**Provenance:** OPEN_QUESTION_OPERATOR_DECISION_REQUIRED

---

### DEC-146B-EOS-029: Onboarding Wizard Depth
**Priority:** P1
**Category:** design_ux
**Question:** How deep is the R1 onboarding wizard? What data does it collect and what does it produce?
**Options:**
1. **Minimal — name, email, company name.** Get users into the app fast, let them discover features. Tradeoff: lowest friction, but users land in an empty dashboard with no guidance.
2. **Moderate — name, email, company name, industry, stage, primary goal.** Enough to customize the dashboard and recommend initial templates. Tradeoff: 2-3 minute onboarding, meaningfully personalized first experience.
3. **Deep — full business profile.** Company details, team size, revenue range, tools used, biggest pain points. Tradeoff: 5-8 minute onboarding, excellent personalization, but high drop-off risk at each step.
4. **Progressive — minimal upfront, deep over first week.** Collect basics at signup, then prompt for additional info contextually as users explore features. Tradeoff: low initial friction AND deep personalization, but requires careful UX design for progressive disclosure.
**Default Recommendation:** Option 4. Minimal signup (30 seconds), then progressive profiling over the first week. This matches the "fractional COO" positioning — the COO learns about your business over time.
**Blocked By This:** Onboarding UI design, user profile schema, template recommendation engine, dashboard personalization logic.
**Provenance:** OPEN_QUESTION_OPERATOR_DECISION_REQUIRED

---

### DEC-146B-EOS-030: UMH Substrate Coupling Depth
**Priority:** P1
**Category:** umh_integration
**Question:** How tightly does EOS couple to the UMH substrate? Is it a thin client that calls UMH APIs, or does it embed substrate functionality?
**Options:**
1. **Thin client — EOS calls UMH HTTP API.** EOS is a standard SaaS app that happens to call UMH for AI features. Tradeoff: cleanest separation, EOS can be developed/deployed independently, but adds HTTP latency to every AI call and requires UMH to be running as a service.
2. **Embedded — EOS imports UMH Python modules directly.** EOS backend includes UMH substrate as a Python dependency. Tradeoff: tightest integration, lowest latency, but couples EOS deployment to UMH version, and mixing TypeScript (EOS) with Python (UMH) requires the bridge architecture.
3. **Sidecar — UMH runs as a sidecar container alongside EOS.** Same deployment, separate process, communicates via localhost. Tradeoff: clean process boundary, easy to version independently, minimal latency, but more complex deployment.
4. **SDK pattern — UMH publishes a Python SDK that EOS consumes.** UMH is packaged as a pip-installable library. Tradeoff: cleanest dependency management, versioned, testable, but requires maintaining the SDK as a separate artifact.
**Default Recommendation:** Option 2 for MVP (already the pattern — TypeScript calls Python via stdio bridge), transition to option 4 post-MVP when UMH is mature enough to package as an SDK.
**Blocked By This:** Deployment architecture, development workflow, testing strategy, UMH version management.
**Provenance:** OPEN_QUESTION_OPERATOR_DECISION_REQUIRED

---

## Summary

| ID | Title | Priority | Category | Default |
|----|-------|----------|----------|---------|
| DEC-146B-EOS-001 | Beast Branch Promotion | P0 | architecture | Promote Beast |
| DEC-146B-EOS-002 | MVP Scope Confirmation | P0 | product_scope | Confirm R1-R5 |
| DEC-146B-EOS-003 | Auth Finalization | P0 | auth_security | Confirm Clerk |
| DEC-146B-EOS-004 | Embedding Dimension | P1 | architecture | 384 for MVP |
| DEC-146B-EOS-005 | Pricing Model | P1 | product_scope | $39/mo founder access |
| DEC-146B-EOS-006 | UBOS Template Library | P1 | product_scope | Curated only for MVP |
| DEC-146B-EOS-007 | Portfolio Multi-Company | P1 | product_scope | Schema multi, UI single |
| DEC-146B-EOS-008 | Agent Autonomy Levels | P1 | product_scope | Semi-autonomous R1 |
| DEC-146B-EOS-009 | RLS Strategy | P1 | auth_security | Hybrid RLS |
| DEC-146B-EOS-010 | Deployment Target | P1 | architecture | Fly.io, portable |
| DEC-146B-EOS-011 | Mobile Strategy | P2 | design_ux | PWA |
| DEC-146B-EOS-012 | Local AI Runtime | P2 | architecture | Cloud-only MVP |
| DEC-146B-EOS-013 | Multi-Region | P2 | architecture | Single region MVP |
| DEC-146B-EOS-014 | Skill Marketplace | P2 | product_scope | Defer to post-PMF |
| DEC-146B-EOS-015 | Competitive Positioning | P2 | product_scope | Fractional COO |
| DEC-146B-EOS-016 | Knowledge Graph | P2 | architecture | pgvector + FTS |
| DEC-146B-EOS-017 | SSO / Magic Link | P2 | auth_security | Magic link via Clerk |
| DEC-146B-EOS-018 | Python-TS Bridge | P2 | architecture | stdio bridge MVP |
| DEC-146B-EOS-019 | CI/CD Platform | P2 | implementation_sequencing | GitHub Actions + Fly |
| DEC-146B-EOS-020 | Error Tracking | P2 | architecture | Sentry + PostHog |
| DEC-146B-EOS-021 | Enterprise Permissions | P3 | auth_security | Fixed RBAC MVP |
| DEC-146B-EOS-022 | White-Label | P3 | architecture | Multi-tenant only |
| DEC-146B-EOS-023 | API Versioning | P3 | architecture | URL path /api/v1/ |
| DEC-146B-EOS-024 | Internationalization | P3 | product_scope | i18n-ready, English only |
| DEC-146B-EOS-025 | Data Retention | P3 | data_privacy | Minimal + soft delete |
| DEC-146B-EOS-026 | Voice Integration | P2 | product_scope | Text-first, voice R4+ |
| DEC-146B-EOS-027 | Notification System | P1 | architecture | In-app + email |
| DEC-146B-EOS-028 | Financial Data Source | P2 | product_scope | Manual + CSV MVP |
| DEC-146B-EOS-029 | Onboarding Wizard Depth | P1 | design_ux | Progressive profiling |
| DEC-146B-EOS-030 | UMH Coupling Depth | P1 | umh_integration | Embedded, SDK later |

---

## Resolution Protocol

1. Operator reviews each decision and selects an option (or provides a custom answer).
2. Selected option is recorded with date and rationale.
3. `operator_approved` is set to `true` for resolved decisions.
4. Blocked work may proceed once its blocking decisions are resolved.
5. This document is updated in-place — decisions are never removed, only resolved.

---

**End of decision queue. 30 decisions total. 3 P0, 10 P1, 12 P2, 5 P3.**
