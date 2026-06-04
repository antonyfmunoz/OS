---
phase: "14.6B-CreatorOS (revised 14.6F)"
status: "DRAFT"
operator_approved: false
allows_implementation: false
date: "2026-06-04"
revised: "2026-06-04"
provenance: "OPEN_QUESTION_OPERATOR_DECISION_REQUIRED"
description: "Every operator decision needed for CreatorOS — 32 decisions across scope, security, architecture, commerce, design, infrastructure, features, legal, and UMH integration. 4 P0 decisions RESOLVED per operator ratification (2026-06-04). Revised in Phase 14.6F to align with 18 ratified P0 decisions (2026-06-04)."
sources:
  - "phase14_6b_creatoros_lossless_product_canon.md"
  - "phase14_6b_creatoros_versions_contradictions_matrix.json"
  - "phase14_6b_creatoros_professional_gap_register.md"
  - "phase14_6b_creatoros_auth_security_truth.json"
  - "phase14_6b_creatoros_product_types_commerce_canon.json"
  - "phase14_6b_creatoros_design_identity_canon.json"
  - "phase14_6b_creatoros_eos_boundary_canon.md"
  - "phase14_6b_creatoros_content_distribution_canon.json"
  - "phase14_6b_creatoros_community_messaging_canon.json"
  - "phase14_6b_creatoros_automation_ai_canon.json"
  - "phase14_6b_creatoros_ugc_ads_canon.json"
  - "phase14_6b_creatoros_analytics_dashboard_canon.json"
  - "phase14_6b_creatoros_data_ontology.json"
  - "phase14_6b_creatoros_current_implementation_truth.json"
  - "phase14_5a_operator_decision_ledger.json (carries forward DEC-145-002, DEC-145-004)"
---


# CreatorOS Operator Decision Queue

Every decision that requires explicit operator selection before implementation can proceed. Nothing here is resolved by default. System recommendations are informational, not authoritative. Only operator-selected options unlock implementation.

Decision count: 32 (4 P0 RESOLVED, 28 remaining open)

---

## Priority Legend

| Priority | Meaning |
|----------|---------|
| P0 | Blocks ALL implementation. Must resolve first. |
| P1 | Blocks major workstreams. Must resolve before feature build. |
| P2 | Blocks specific modules. Can work around temporarily. |
| P3 | Shapes long-term direction. Can defer past MVP. |

## Category Legend

| Category | Scope |
|----------|-------|
| SCOPE | What gets built and what does not |
| SECURITY | Auth, data protection, access control |
| ARCHITECTURE | Code structure, patterns, splitting strategy |
| COMMERCE | Payments, pricing, revenue model |
| DESIGN | Visual identity, component library, UX patterns |
| INFRASTRUCTURE | Deployment, CI/CD, hosting, monitoring |
| FEATURE | Specific module-level decisions |
| LEGAL | Privacy, compliance, terms |
| INTEGRATION | UMH, EOS, third-party boundaries |

---

## P0 — Blocks ALL Implementation (4 decisions — ALL RESOLVED)

### DEC-146B-COS-001: MVP Scope Definition — RESOLVED

| Field | Value |
|-------|-------|
| Priority | P0 |
| Category | SCOPE |
| Status | **RESOLVED** |
| Resolution | **Option B ratified: Content + Community + Courses + Sales (8-12 weeks)** |
| Decision ID | DEC-146B-COS-001 |
| Ratified | 2026-06-04, Phase 14.6C |
| Carried from | DEC-145-002 (now resolved) |
| Evidence | CONTRA-COS-002 (3 conflicting MVP definitions), Google Doc Tabs 6, 7, 3 |

**Question:** Which of the three conflicting MVP scope definitions is canonical?

**Ratified answer:** Option B — Content + Community + Courses + Sales (8-12 weeks). Operator approved.

**Options (historical):**

| Option | Scope | Source | Modules | Timeline estimate |
|--------|-------|--------|---------|-------------------|
| A | Content distribution + community only. Excludes courses, marketplace, payments, Stripe, analytics dashboard, native mobile, AI, stories. | Google Doc Tab 6 (original MVP) | 2 of 16 | 4-6 weeks |
| **B** | **Content + community + courses + basic product sales. Includes Stripe checkout for digital downloads and courses. Excludes UGC, ads, automation, editing studio, email.** | **System recommendation (synthesized)** | **4 of 16** | **8-12 weeks** |
| C | Content + community + courses + marketplace + payments (Stripe). Everything Tab 6 explicitly excludes. | Google Doc Tab 7 (expanded MVP) | 6 of 16 | 14-18 weeks |
| D | Full PRD scope. All 16 modules. | Google Doc Tab 3 + Tab 8 combined | 16 of 16 | 6-9 months |

**Previously blocked by this decision (now unblocked):**
- ALL feature build scope decisions
- Sprint planning and sequencing
- Resource allocation
- Database migration planning (which of 25 missing tables to build)
- Module priority ordering

---

### DEC-146B-COS-002: Auth Migration Strategy — RESOLVED

| Field | Value |
|-------|-------|
| Priority | P0 |
| Category | SECURITY |
| Status | **RESOLVED** |
| Resolution | **Clerk first, block ALL other implementation until auth complete (Option D)** |
| Decision ID | DEC-146B-COS-002 |
| Ratified | 2026-06-04, Phase 14.6C |
| Carried from | DEC-145-004 (now resolved) |
| Evidence | GAP-COS-001 (comparePasswords returns true for ALL), COS-AUTH-001 (critical vulnerability), CONTRA-COS-001 |

**Question:** How is the broken auth resolved and when?

**Ratified answer:** Option D — Clerk migration as first task, block ALL other implementation until auth is complete. Operator approved.

**Options (historical):**

| Option | Approach | Risk | Timeline |
|--------|----------|------|----------|
| A | Fix Passport.js comparePasswords immediately (bandaid), then migrate to Clerk later | Low immediate risk, double work | Fix: 1 day, Clerk: 2-3 weeks later |
| B | Skip Passport.js fix, migrate directly to Clerk as the first implementation task | Higher risk if timeline slips — app stays broken longer | 2-3 weeks |
| C | Fix Passport.js comparePasswords AND add rate limiting/CSRF as interim hardening, defer Clerk to post-MVP | Accumulates auth tech debt, but gets secure faster | Fix: 2-3 days, no Clerk timeline |
| **D** | **Clerk migration as first task, block ALL other implementation until auth is complete** | **Clean but sequential — nothing else progresses until Clerk is done** | **2-3 weeks, then other work begins** |

**Previously blocked by this decision (now unblocked):**
- ALL deployment (cannot deploy with broken auth)
- ALL feature build (features built on broken auth must be rebuilt)
- Session management architecture
- OAuth provider configuration
- MFA rollout

---

### DEC-146B-COS-003: Source Code Baseline — RESOLVED

| Field | Value |
|-------|-------|
| Priority | P0 |
| Category | ARCHITECTURE |
| Status | **RESOLVED** |
| Resolution | **Verify baseline, then GitHub as canonical (Option C)** |
| Decision ID | DEC-146B-COS-003 |
| Ratified | 2026-06-04, Phase 14.6C |
| Evidence | phase14_6b_creatoros_source_inventory.json (296 GitHub files, 271 Beast files, aligned) |

**Question:** Which codebase is the starting point for all CreatorOS development?

**Ratified answer:** Option C — Verify both are identical, then designate GitHub as canonical. Operator approved.

**Options (historical):**

| Option | Baseline | Rationale |
|--------|----------|-----------|
| A | GitHub main (antonyfmunoz/CreatorOS) as canonical starting point | Publicly hosted, CI/CD integration straightforward |
| B | Beast copy as canonical, push to GitHub as first step | Beast may have local-only changes not yet pushed |
| **C** | **Verify both are identical, then designate GitHub as canonical** | **Safest — confirms alignment before choosing** |

**Previously blocked by this decision (now unblocked):**
- All development work (which repo do PRs target?)
- CI/CD setup (which repo gets GitHub Actions?)
- Branch protection rules

---

### DEC-146B-COS-004: Module Build Sequence — RESOLVED

| Field | Value |
|-------|-------|
| Priority | P0 |
| Category | SCOPE |
| Status | **RESOLVED** |
| Resolution | **Auth -> Split -> Tests -> Content -> Community -> Courses -> Stripe -> Analytics (Option A)** |
| Decision ID | DEC-146B-COS-004 |
| Ratified | 2026-06-04, Phase 14.6C |
| Evidence | phase14_6b_creatoros_lossless_product_canon.md (16 modules, implementation status varies) |

**Question:** In what order are modules built after MVP scope is decided?

**Ratified answer:** Option A — Auth -> Split -> Tests -> Content -> Community -> Courses -> Stripe -> Analytics. Systematic, tests-first. Operator approved.

**Options (historical):**

| Option | Sequence | Tradeoff |
|--------|----------|----------|
| **A** | **Auth -> Split -> Tests -> Content -> Community -> Courses -> Stripe -> Analytics** | **Systematic, tests-first** |
| B | Auth -> Stripe -> Products -> Courses -> Content -> Community -> Analytics -> Tests | Revenue-first, riskier |
| C | Auth -> Content -> Community -> Tests -> Courses -> Stripe -> Analytics | User-value-first, revenue delayed |

**Previously blocked by this decision (now unblocked):**
- Sprint planning
- Resource allocation per phase
- Dependency ordering for database migrations

---

## P1 — Blocks Major Workstreams (10 decisions)

### DEC-146B-COS-005: Payment Processor Selection

| Field | Value |
|-------|-------|
| Priority | P1 |
| Category | COMMERCE |
| Provenance | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| Evidence | GAP-COS-012 (zero payment infrastructure), product_types_commerce_canon.json (10 product types need checkout) |

**Question:** Which payment processor for CreatorOS commerce?

**Options:**

| Option | Processor | Pros | Cons |
|--------|-----------|------|------|
| A | Stripe Connect (Standard) | Industry standard for marketplaces, handles payouts, KYC, 1099s. Well-documented. | 2.9% + 30c per transaction. Platform fee on top. Complex onboarding flow. |
| B | Stripe Connect (Express) | Simpler onboarding, Stripe-hosted dashboard for creators. | Less control over creator payout experience. Still 2.9% + 30c. |
| C | Stripe Connect (Custom) | Full control over UX. White-label payment experience. | Most complex integration. Requires handling compliance directly. |
| D | Lemonsqueezy | Merchant of record (handles tax, compliance). Simpler integration. | Higher fees. Less control. Newer, less ecosystem. |
| E | Paddle | Merchant of record. Handles global tax. | Limited marketplace features. Not designed for creator platforms. |

**Default if not decided:** B (Stripe Connect Express).

**System recommendation:** B — Express gives the best balance of simplicity and capability. Standard is too hands-off (creators manage their own Stripe dashboard). Custom is overengineering for pre-revenue. Paddle/Lemonsqueezy are single-seller tools, not marketplace-ready.

**Blocked by this decision:**
- All commerce implementation
- Product checkout flow
- Creator payout system
- Subscription billing
- Revenue analytics (needs transaction data source)

---

### DEC-146B-COS-006: Pricing Model Confirmation

| Field | Value |
|-------|-------|
| Priority | P1 |
| Category | COMMERCE |
| Provenance | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| Evidence | phase14_6b_creatoros_lossless_product_canon.md Section 5 (4-tier pricing from PRD) |

**Question:** Is the 4-tier pricing model from the PRD confirmed, or does it need revision?

**PRD pricing (from Google Doc):**

| Tier | Monthly | Transaction fee | Limits |
|------|---------|-----------------|--------|
| Free | $0 | 10% | 100 community members, 5 products, basic analytics |
| Pro | $29/mo | 5% | 10K members, unlimited products, advanced analytics |
| Business | $79/mo | 3% | 100K members, team features, custom domain, API access |
| Enterprise | $199+/mo | 1% | Unlimited, white-label, dedicated support, SLA |

**Options:**

| Option | Pricing | Rationale |
|--------|---------|-----------|
| A | Confirm PRD pricing as-is | Ship fast, iterate based on market feedback |
| B | Simplify to 2 tiers (Free + Pro $29/mo) for MVP, expand later | Reduces decision complexity, faster to implement |
| C | Match competitor pricing (Whop: Free + $0 platform fee, revenue from payment processing) | Different business model — zero subscription, revenue from transactions |
| D | Revise tiers and pricing based on updated competitive analysis | Delays implementation but may produce better pricing |

**Default if not decided:** A (confirm PRD pricing).

**System recommendation:** B for MVP — Free + Pro only. Business and Enterprise tiers require features (team management, white-label, API access, SLA) that do not exist and will not exist in MVP. Selling tiers you cannot deliver erodes trust.

**Blocked by this decision:**
- Subscription billing implementation
- Feature gating logic
- Onboarding flow (which tier does a new user see?)
- Landing page pricing section

---

### DEC-146B-COS-007: Design System Confirmation

| Field | Value |
|-------|-------|
| Priority | P1 |
| Category | DESIGN |
| Provenance | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| Evidence | phase14_6b_creatoros_design_identity_canon.json (X/Twitter minimalism, detailed color system, NOT glassmorphism) |

**Question:** Is the X/Twitter-inspired minimalism design system confirmed as the canonical visual identity?

**Current design canon states:**
- Inspiration: X/Twitter — information-dense, speed-optimized creator interfaces
- Principles: minimalism, speed, function-first, content-density, progressive-disclosure
- Color: Ink (#0F1419 light / #E7E9EA dark), monochrome base, strategic accent
- NOT: glassmorphism, heavy gradients, gamification chrome, RPG aesthetic, neon/cyberpunk

**Options:**

| Option | Direction | Impact |
|--------|-----------|--------|
| A | Confirm X/Twitter minimalism as documented in design canon | Ship with existing design direction, iterate post-launch |
| B | Confirm X/Twitter minimalism but commission Figma design system first | Delays build but produces pixel-perfect reference for all components |
| C | Pivot to different design direction | Requires new design canon, invalidates 90 reference files |
| D | Confirm direction but audit 90 design reference files first to extract component inventory | Ensures design canon matches actual design intent in reference images |

**Default if not decided:** A (confirm as documented).

**System recommendation:** A with D as a parallel workstream — confirm the direction so build can start, but schedule the design reference audit (GAP-COS-064: 90 unaudited files, 84 MB) as a non-blocking task. The 90 reference files may contain design decisions not yet captured in the design canon JSON.

**Blocked by this decision:**
- Component library build (shadcn/ui theme configuration)
- Dark mode implementation
- All new UI screens and components
- Landing page design

---

### DEC-146B-COS-008: God File Splitting Strategy

| Field | Value |
|-------|-------|
| Priority | P1 |
| Category | ARCHITECTURE |
| Provenance | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| Evidence | GAP-COS-006 (routes.ts 53KB), GAP-COS-007 (storage.ts 104KB), CONTRA-COS-003 |

**Question:** How are the two god files split, and when relative to other work?

**Options:**

| Option | Strategy | Risk |
|--------|----------|------|
| A | Split both BEFORE any feature work. Write tests first, then split with test coverage as safety net. | Safest. Slow start. 1-2 weeks of refactoring before any features. |
| B | Split both AFTER Clerk migration but BEFORE feature build. Auth change first reduces surface area of god files. | Auth migration may touch routes.ts heavily, making split easier after. |
| C | Split incrementally — extract one domain at a time as each domain is touched for feature work. | Faster feature velocity initially. God files shrink gradually. Risk of partial state persisting. |
| D | Split routes.ts first (smaller), then storage.ts. Tests written per-module after split. | Routes is more manageable first target. Storage.ts (104KB) is the harder problem. |

**Default if not decided:** A (split before features, tests first).

**System recommendation:** B — Clerk migration will rewrite all auth routes and session handling in routes.ts. Splitting before Clerk means re-splitting after Clerk touches the same file. Sequence: Clerk migration (changes routes.ts auth section) -> write tests against post-Clerk routes.ts -> split routes.ts by domain -> split storage.ts by domain.

**Blocked by this decision:**
- Parallel development (cannot have multiple devs in a single 53KB/104KB file)
- Module-level testing
- Code review efficiency
- Feature build confidence

---

### DEC-146B-COS-009: Database Migration Strategy

| Field | Value |
|-------|-------|
| Priority | P1 |
| Category | ARCHITECTURE |
| Provenance | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| Evidence | GAP-COS-020 (no migrations system), GAP-COS-013 (25 missing tables), data_ontology.json |

**Question:** How are database schema changes managed going forward?

**Options:**

| Option | Approach | Tradeoff |
|--------|----------|----------|
| A | drizzle-kit generate for versioned SQL migrations. Never use `push` again. Rollback scripts for every migration. | Disciplined. Slower per-change. Full audit trail. |
| B | Continue with drizzle-kit push for development, switch to generate for production only | Faster dev iteration. Risk of dev/prod schema drift. |
| C | Move to a different migration tool (Prisma Migrate, raw SQL, dbmate) | Non-standard for existing Drizzle codebase. Migration cost. |

**Default if not decided:** A (versioned migrations only).

**System recommendation:** A — `push` is destructive in production (no rollback, no history, no review). The codebase already uses Drizzle ORM; `drizzle-kit generate` is the native migration path. No reason to switch tools.

**Blocked by this decision:**
- All schema changes (25 missing tables need migration files)
- CI pipeline (migration verification step)
- Production deployment (migration strategy must be defined first)

---

### DEC-146B-COS-010: Hosting Platform

| Field | Value |
|-------|-------|
| Priority | P1 |
| Category | INFRASTRUCTURE |
| Provenance | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| Evidence | GAP-COS-009 (no production deployment), phase14_6b_creatoros_api_infrastructure_canon.json |

**Question:** Where is CreatorOS deployed?

**Options:**

| Option | Platform | Cost | Pros | Cons |
|--------|----------|------|------|------|
| A | Fly.io | ~$5-15/mo starter | Already used for UMH cockpit. Dockerfile-based. Global edge. | Another Fly app to manage. |
| B | Vercel (frontend) + Fly.io (backend) | ~$20/mo combined | Vercel optimized for React. Fly for Express API. | Split deployment. Two platforms to manage. |
| C | Railway | ~$5-10/mo | Simple monorepo deploy. Good DX. | Less mature than Fly. Fewer edge regions. |
| D | Self-hosted on VPS | $0 incremental | Already have VPS. Full control. | VPS is the coordination brain, not an app host (node role discipline). |
| E | Cloudflare Pages (frontend) + Fly.io (backend) | ~$5/mo | Free frontend hosting. Fast CDN. | Cloudflare Pages has build limitations. |

**Default if not decided:** A (Fly.io, consistent with UMH cockpit).

**System recommendation:** A — Fly.io is already in the stack for UMH cockpit. Same deployment patterns, same CLI, same monitoring approach. Keeping the platform consistent reduces operational overhead. VPS is explicitly the coordination brain per node role discipline — do not add app hosting to it.

**Blocked by this decision:**
- Dockerfile creation
- CI/CD pipeline target
- Environment variable management
- Domain/DNS configuration
- SSL/TLS setup

---

### DEC-146B-COS-011: Domain Name

| Field | Value |
|-------|-------|
| Priority | P1 |
| Category | INFRASTRUCTURE |
| Provenance | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| Evidence | No domain currently assigned to CreatorOS |

**Question:** What domain does CreatorOS deploy to?

**Options:**

| Option | Domain | Notes |
|--------|--------|-------|
| A | creatoros.app | Clean, memorable, .app TLD enforces HTTPS |
| B | creatoros.com | Premium TLD. May be taken/expensive. |
| C | creatoros.io | Tech-friendly TLD. Commonly available. |
| D | app.creatoros.com (subdomain of purchased domain) | Separates marketing site from app |
| E | creatoros.empyreanstudio.com (subdomain of parent entity) | Free. Signals corporate ownership. Less clean for users. |
| F | Defer — use Fly.io default domain until launch-ready | No cost. No commitment. |

**Default if not decided:** F (defer).

**System recommendation:** F for now, purchase domain when approaching public launch. No point paying for a domain while auth is broken and the app has no deployment.

**Blocked by this decision:**
- DNS configuration
- SSL certificate setup
- OAuth redirect URLs (Clerk needs a domain)
- Email sending domain (SPF/DKIM)

---

### DEC-146B-COS-012: Replit Artifact Handling

| Field | Value |
|-------|-------|
| Priority | P1 |
| Category | ARCHITECTURE |
| Provenance | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| Evidence | GAP-COS-018 (Replit coupling artifacts: .replit, replit.nix, REPL_ID, Vite plugins) |

**Question:** How are Replit artifacts handled?

**Options:**

| Option | Approach | Risk |
|--------|----------|------|
| A | Remove all Replit artifacts immediately (before any other work) | Clean slate. Low risk — artifacts are dead weight. |
| B | Remove as part of Clerk migration (auth rewrite touches same files) | Efficient — bundled with another breaking change. |
| C | Leave in place, ignore | Clutters builds, confuses new developers, Vite plugin conflicts possible. |

**Default if not decided:** A (remove immediately).

**System recommendation:** A — Replit files serve no purpose. `.replit` and `replit.nix` are platform-specific. REPL_ID is meaningless outside Replit. Vite plugin references may actively interfere with standard builds. Remove before any other work to prevent false build errors.

**Blocked by this decision:**
- Clean Docker builds
- Standard Vite configuration
- Developer onboarding clarity

---

### DEC-146B-COS-013: Money Data Type Migration

| Field | Value |
|-------|-------|
| Priority | P1 |
| Category | ARCHITECTURE |
| Provenance | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| Evidence | GAP-COS-022 (doublePrecision for money — floating-point rounding errors) |

**Question:** When and how is the price field migrated from doublePrecision to integer cents?

**Options:**

| Option | Timing | Approach |
|--------|--------|----------|
| A | Migrate as part of first schema migration batch (before any Stripe integration) | Clean foundation for all commerce. |
| B | Migrate when Stripe is integrated (Stripe uses integer cents natively) | Aligns with Stripe integration work. |
| C | Add price_cents as new column, deprecate price over time | Non-breaking migration. Dual columns temporarily. |

**Default if not decided:** A (migrate before Stripe).

**System recommendation:** A — floating-point money is a defect. Every line of commerce code written against doublePrecision is a bug waiting to surface. Fix the foundation before building on it. Since no production data exists, the migration is a schema change with zero data conversion risk.

**Blocked by this decision:**
- Checkout implementation
- Revenue analytics accuracy
- Stripe price sync
- Order/transaction table design

---

### DEC-146B-COS-014: Primary Key Strategy

| Field | Value |
|-------|-------|
| Priority | P1 |
| Category | ARCHITECTURE |
| Provenance | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| Evidence | GAP-COS-061 (serial integer PKs on all tables except notifications which uses UUID) |

**Question:** Do existing tables migrate from serial integers to UUIDs, or only new tables use UUIDs?

**Options:**

| Option | Approach | Risk |
|--------|----------|------|
| A | All new tables use UUID v7. Existing tables stay serial. Accept inconsistency. | No migration risk. Mixed PK types in codebase forever. |
| B | Migrate all tables to UUID v7 now (no production data, low risk). | Consistent. Touches all 20 existing tables. Schema-only change since no real data. |
| C | Keep serial integers everywhere. Accept the security tradeoff. | Simplest. ID enumeration remains possible. |

**Default if not decided:** B (migrate all to UUID now).

**System recommendation:** B — there is no production data, no users, no deployed app. The migration cost is zero. Doing it later when tables have millions of rows is expensive. UUIDs prevent enumeration attacks, enable distributed ID generation, and are the professional standard for user-facing SaaS.

**Blocked by this decision:**
- All new table designs (FK types must match PK types)
- API response format (integer IDs vs UUID strings in URLs/JSON)
- Client-side routing patterns

---

## P2 — Blocks Specific Modules (12 decisions)

### DEC-146B-COS-015: Content Moderation Approach

| Field | Value |
|-------|-------|
| Priority | P2 |
| Category | FEATURE |
| Provenance | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| Evidence | GAP-COS-024 (zero moderation code), Module 15 entirely unbuilt |

**Question:** What moderation model does CreatorOS use?

**Options:**

| Option | Model | Scope |
|--------|-------|-------|
| A | Creator-managed only — each creator moderates their own community/content | Simplest. Platform has no liability shield. |
| B | Platform-level automated moderation (AI text/image scanning) + creator-managed community moderation | Platform catches illegal/harmful content. Creators handle community standards. |
| C | Full moderation stack — automated scanning, user reporting, platform review queue, appeals process, creator-level tools | Comprehensive. Significant build cost. Required by payment processors and app stores at scale. |
| D | Defer moderation entirely — ship without it, add when needed | Fastest to market. Legal and payment processor risk. |

**Default if not decided:** D for MVP, B for post-MVP.

**System recommendation:** D for MVP with a clear post-MVP plan for B. Content moderation is critical at scale but a pre-revenue app with zero users does not need a moderation queue. Payment processor ToS (Stripe) requires a content policy and report mechanism before processing real money — so B must be in place before commerce goes live.

**Blocked by this decision:**
- Module 15 build scope
- Trust & safety policy
- Payment processor compliance
- App store submission readiness

---

### DEC-146B-COS-016: Community vs Courses Priority

| Field | Value |
|-------|-------|
| Priority | P2 |
| Category | SCOPE |
| Provenance | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| Evidence | Community is PARTIAL (6 tables, basic CRUD). Courses are NOT_IMPLEMENTED (zero tables, zero code). |

**Question:** If forced to choose one for MVP+1, which ships first — enhanced community or courses?

**Options:**

| Option | First | Rationale |
|--------|-------|-----------|
| A | Community enhancement (membership tiers, owner FK, role-based access, paid communities) | Foundation exists. Enhancement is faster than greenfield. Communities drive retention. |
| B | Courses (builder, video hosting, progress tracking, enrollment, completion) | Courses are a proven revenue driver. Higher ARPU than community subscriptions. |
| C | Build both in parallel (different developers/workstreams) | Fastest overall. Requires parallel development capacity. |

**Default if not decided:** A (community first).

**System recommendation:** A — community schema exists (6 tables). Enhancement requires adding owner FK, community_members table, and role-based access to existing structure. Courses are entirely greenfield (5 new tables, new UI, video hosting infrastructure). Community-first gets a monetizable feature live faster.

**Blocked by this decision:**
- Sprint allocation after core MVP
- Database migration sequencing
- Stripe integration scope (community subscriptions vs course purchases)

---

### DEC-146B-COS-017: UGC/Ads Timeline

| Field | Value |
|-------|-------|
| Priority | P2 |
| Category | SCOPE |
| Provenance | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| Evidence | Modules 8 (UGC) and 9 (Ads) are entirely NOT_IMPLEMENTED. Both require marketplace-level infrastructure. |

**Question:** When do UGC campaigns and the ads platform enter the build plan?

**Options:**

| Option | Timeline | Rationale |
|--------|----------|-----------|
| A | Post-MVP Phase 2 (after content + community + courses + commerce are live) | Revenue and user base needed before UGC/ads make sense |
| B | Post-MVP Phase 3 (after analytics, automation, email are also live) | UGC/ads need audience data and automation infrastructure |
| C | Defer indefinitely — not part of near-term roadmap | Focus on core creator tools. UGC/ads are marketplace features. |
| D | Build UGC as MVP+1 (differentiator vs competitors — no one else has this integrated) | UGC is a unique value prop. But requires payment infrastructure first. |

**Default if not decided:** B (Phase 3).

**System recommendation:** B — UGC campaigns require: Stripe Connect (for creator payouts), content submission flow, brand review interface, campaign analytics, and rights management. Ads require: audience data, targeting infrastructure, bidding system, and ad serving. Both modules depend on infrastructure that does not exist yet. Building them before the foundation is premature.

**Blocked by this decision:**
- Long-term roadmap planning
- Database table creation scope (6 UGC/ads tables)
- Brand/advertiser persona development

---

### DEC-146B-COS-018: Email Infrastructure Provider

| Field | Value |
|-------|-------|
| Priority | P2 |
| Category | INFRASTRUCTURE |
| Provenance | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| Evidence | GAP-COS-028 (Module 12 entirely unbuilt), SendGrid SDK listed as dependency but unused |

**Question:** Which email service for transactional email and newsletter/broadcast?

**Options:**

| Option | Provider | Cost | Pros | Cons |
|--------|----------|------|------|------|
| A | SendGrid (already in dependencies) | Free tier: 100 emails/day | Already a dependency. Proven at scale. | Reputation management complex. |
| B | Resend | Free tier: 100 emails/day, then $20/mo | Modern DX. React Email templates. Great API. | Newer, less battle-tested at scale. |
| C | Postmark | $15/mo for 10K emails | Best deliverability reputation. | No free tier. Higher cost at scale. |
| D | AWS SES | ~$0.10 per 1K emails | Cheapest at scale. | Worst DX. Complex setup. Cold start reputation. |
| E | Dual: Resend for transactional + SendGrid for bulk/newsletters | Varies | Best-of-breed per use case. | Two services to manage. |

**Default if not decided:** A (SendGrid, already in dependencies).

**System recommendation:** B (Resend) — modern API, React Email support (matches the React/TypeScript stack), excellent developer experience. SendGrid is in package.json but unused; there is no sunk cost. Resend's free tier covers development and early users.

**Blocked by this decision:**
- Transactional email (welcome, password reset, order confirmation)
- Newsletter/broadcast system (Module 12)
- Email verification flow (Clerk may handle auth emails, but commerce emails need a provider)

---

### DEC-146B-COS-019: Cross-Posting Platform Priority

| Field | Value |
|-------|-------|
| Priority | P2 |
| Category | FEATURE |
| Provenance | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| Evidence | GAP-COS-026 (Module 10 NOT_IMPLEMENTED), content_distribution_canon.json |

**Question:** Which platforms get cross-posting integration first?

**Options:**

| Option | Platforms | Rationale |
|--------|-----------|-----------|
| A | Twitter/X + Instagram + YouTube | Highest creator usage. Covers text, image, and video. |
| B | Twitter/X + LinkedIn + TikTok | Professional + short-form. Different audience segments. |
| C | Twitter/X only (single platform first, validate pattern, then expand) | Simplest. Twitter API is well-documented. Prove the pattern works. |
| D | Defer cross-posting entirely — focus on CreatorOS-native content first | Core product promise ("post once, publish everywhere") is unfulfilled but not an MVP requirement. |

**Default if not decided:** D (defer, focus on native content).

**System recommendation:** C for MVP+1 — the "post once, publish everywhere" promise IS the product identity. But cross-posting requires OAuth integrations, per-platform format adaptation, rate limiting, error handling, and platform API compliance. Start with Twitter/X (simplest API, text-first content maps directly) to validate the pattern. Add platforms incrementally.

**Blocked by this decision:**
- Connected accounts management UI
- OAuth integration scope (which provider SDKs to install)
- Content format adaptation logic
- Platform API compliance work

---

### DEC-146B-COS-020: AI Feature Scope

| Field | Value |
|-------|-------|
| Priority | P2 |
| Category | FEATURE |
| Provenance | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| Evidence | CONTRA-COS-004 (AI as utility vs AI as ecosystem runtime), automation_ai_canon.json |

**Question:** What level of AI capability ships in CreatorOS?

**Options:**

| Option | Scope | AI Provider |
|--------|-------|-------------|
| A | Utility-level only: AI writing assistant for posts, AI content suggestions, AI hashtag/caption generation | OpenAI (already in deps) |
| B | Utility + Custom AI agents (existing schema: ai_agents, ai_chats tables). Creators build and sell AI chatbots. | OpenAI + UMH model_router |
| C | Full AI ecosystem per Tab 8: AI runtime, autonomous agents, AI-powered analytics, AI moderation, AI content generation, AI automation triggers | UMH substrate integration |
| D | No AI features in MVP — remove OpenAI dependency, defer all AI to post-MVP | Simplify. Focus on core product. |

**Default if not decided:** A (utility-level only).

**System recommendation:** B — AI agents already have schema tables and UI components (AgentCard, ChatInterface). Enhancing partial implementation is cheaper than building from scratch later. Keep utility-level AI (writing assistant, suggestions) and upgrade the existing AI agent experience to be monetizable (add pricing, token tracking). Full ecosystem (Option C) requires UMH integration that does not exist in production.

**Blocked by this decision:**
- AI model provider selection and cost planning
- AI agent pricing model
- OpenAI API key management
- UMH integration timeline

---

### DEC-146B-COS-021: Real-Time Infrastructure

| Field | Value |
|-------|-------|
| Priority | P2 |
| Category | INFRASTRUCTURE |
| Provenance | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| Evidence | GAP-COS-038 (no WebSocket auth), community_messaging_canon.json (real-time messaging needs) |

**Question:** What real-time infrastructure for messaging and live features?

**Options:**

| Option | Technology | Scope |
|--------|-----------|-------|
| A | Existing ws (WebSocket) library with auth added | Minimal change. Already in deps. Low-level. |
| B | Socket.io (replaces raw ws) | Room support, reconnection, fallback transport, larger ecosystem. |
| C | Pusher/Ably (managed service) | Zero infrastructure. Handles auth, presence, scale. Cost per connection. |
| D | Supabase Realtime (if using Supabase for anything) | Built-in with Postgres changes. Less flexibility. |
| E | Server-Sent Events (SSE) for notifications + WebSocket for chat only | Simpler for one-way updates. WebSocket only where bidirectional is needed. |

**Default if not decided:** B (Socket.io).

**System recommendation:** B — Socket.io adds room support (needed for community channels), automatic reconnection (needed for mobile), and namespace isolation (separate messaging from notifications). Raw ws requires building all of this. Managed services add cost. Socket.io is the standard for this scale of application.

**Blocked by this decision:**
- Community real-time messaging
- Notification delivery
- Live presence indicators
- Typing indicators

---

### DEC-146B-COS-022: File Storage Provider

| Field | Value |
|-------|-------|
| Priority | P2 |
| Category | INFRASTRUCTURE |
| Provenance | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| Evidence | GAP-COS-021 (no file upload validation), GAP-COS-043 (no media optimization), content_distribution_canon.json |

**Question:** Where are user-uploaded files (images, video, audio, documents) stored?

**Options:**

| Option | Provider | Cost | Pros | Cons |
|--------|----------|------|------|------|
| A | Cloudflare R2 | Free egress, $0.015/GB storage | Zero egress fees. S3-compatible API. Built-in CDN. | Newer service. Less tooling ecosystem. |
| B | AWS S3 + CloudFront | $0.023/GB storage + egress fees | Industry standard. Massive tooling ecosystem. | Egress costs add up fast with media-heavy app. |
| C | Uploadthing | Free tier: 2GB | Purpose-built for Next.js/React. Great DX. | Less control. Vendor lock-in. Not S3-compatible. |
| D | Supabase Storage | Free tier: 1GB | Simple. Postgres-integrated. | Limited media processing. Smaller scale ceiling. |

**Default if not decided:** A (Cloudflare R2).

**System recommendation:** A — zero egress fees are critical for a media-heavy creator platform. Creators upload images, video, and audio. Consumers view/download them repeatedly. With S3, every view costs money. With R2, storage is cheap and delivery is free. S3-compatible API means no vendor lock-in.

**Blocked by this decision:**
- Media upload implementation
- Image optimization pipeline
- Video hosting (courses, content)
- Digital download delivery
- CDN configuration

---

### DEC-146B-COS-023: Error Tracking Service

| Field | Value |
|-------|-------|
| Priority | P2 |
| Category | INFRASTRUCTURE |
| Provenance | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| Evidence | GAP-COS-015 (no monitoring or observability), carried from DEC-145A-003 |

**Question:** Which error tracking service for CreatorOS production?

**Options:**

| Option | Service | Cost |
|--------|---------|------|
| A | Sentry | Free tier: 5K errors/mo. Source map support. Good React integration. |
| B | PostHog (analytics + error tracking combined) | Free tier: 1M events/mo. Already planned for UMH. |
| C | Highlight.io | Free tier: 500 sessions/mo. Session replay + error tracking. |
| D | BetterStack (Logtail) | Free tier: 1GB/mo. Log-based error tracking. |

**Default if not decided:** A (Sentry).

**System recommendation:** A — Sentry is the industry standard for application error tracking. Source map support is critical for a compiled TypeScript app. React Error Boundary integration is native. Free tier covers early usage. PostHog is better for product analytics; Sentry is better for engineering observability.

**Blocked by this decision:**
- Error monitoring setup
- Source map upload in CI/CD
- Error alerting configuration

---

### DEC-146B-COS-024: Notification Strategy

| Field | Value |
|-------|-------|
| Priority | P2 |
| Category | FEATURE |
| Provenance | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| Evidence | GAP-COS-040 (no notification preferences), notifications table exists but is minimal |

**Question:** What notification channels does CreatorOS support?

**Options:**

| Option | Channels | Scope |
|--------|----------|-------|
| A | In-app only (already partially built) | Simplest. No external dependencies. |
| B | In-app + email (transactional emails for critical events: purchase, follow, mention) | Adds email provider dependency. Covers offline users. |
| C | In-app + email + push (web push notifications via service worker) | Full coverage. Push requires PWA setup. |
| D | In-app + email + push + SMS (for critical security events like MFA, suspicious login) | Most complete. SMS adds cost and provider. |

**Default if not decided:** B (in-app + email).

**System recommendation:** B for MVP — in-app notifications exist, email covers the offline case. Push requires PWA infrastructure and user permission UX. SMS is expensive and only needed for security events (which Clerk handles natively for auth-related notifications).

**Blocked by this decision:**
- Notification preference UI design
- Email template design (order confirmation, welcome, follow notification)
- Push notification infrastructure (if selected)

---

### DEC-146B-COS-025: Search Implementation

| Field | Value |
|-------|-------|
| Priority | P2 |
| Category | FEATURE |
| Provenance | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| Evidence | GAP-COS-035 (no search functionality anywhere) |

**Question:** What search technology for CreatorOS?

**Options:**

| Option | Technology | Cost | Pros | Cons |
|--------|-----------|------|------|------|
| A | PostgreSQL full-text search (tsvector/tsquery) | Free (built into Neon) | No additional service. GIN indexes. Adequate for <100K records. | Limited relevance tuning. No fuzzy matching without extensions. |
| B | Meilisearch (self-hosted or cloud) | Cloud: free tier 10K docs | Fast, typo-tolerant, faceted search, great DX | Another service to manage |
| C | Typesense | Cloud: free tier 28K records/mo | Similar to Meilisearch. Slightly more mature. | Smaller community. |
| D | Algolia | Free tier: 10K records | Industry standard. Excellent relevance. | Expensive at scale. Vendor lock-in. |
| E | Defer search — no search in MVP | No cost | Simplest. Focus on core features. | Content discovery limited to feed scrolling. |

**Default if not decided:** E for MVP, A for post-MVP.

**System recommendation:** E for MVP, then A — PostgreSQL full-text search is free, already in the stack (Neon), and sufficient for early scale. No additional service to manage. Upgrade to Meilisearch or Typesense only when PostgreSQL search becomes a bottleneck (likely >100K searchable records).

**Blocked by this decision:**
- Search UI design
- Search index creation
- Content indexing pipeline

---

### DEC-146B-COS-026: Soft Delete Policy

| Field | Value |
|-------|-------|
| Priority | P2 |
| Category | ARCHITECTURE |
| Provenance | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| Evidence | GAP-COS-041 (no soft delete — hard deletes everywhere) |

**Question:** Which tables get soft delete (deleted_at column) and which keep hard delete?

**Options:**

| Option | Scope | Tables affected |
|--------|-------|-----------------|
| A | Soft delete on ALL content tables (posts, products, communities, channels, messages, comments, orders) | All user-facing content. Recovery possible. Audit trail. |
| B | Soft delete on revenue-critical tables only (products, orders, transactions) | Financial audit trail. Other content is expendable. |
| C | No soft delete — keep hard delete everywhere | Simplest. Permanent deletions. No recovery. |
| D | Soft delete on ALL tables including system tables | Most comprehensive. Overhead on every query (WHERE deleted_at IS NULL). |

**Default if not decided:** A (content tables only).

**System recommendation:** A — soft delete on user-facing content. Hard delete on system/config tables. Every content query adds `WHERE deleted_at IS NULL` but this is a standard pattern with negligible performance impact. Required for moderation audit trails and accidental deletion recovery.

**Blocked by this decision:**
- Schema migration design (adding deleted_at columns)
- Query patterns (all SELECTs must filter deleted records)
- Admin restore functionality

---

## P3 — Long-Term Direction (6 decisions)

### DEC-146B-COS-027: Mobile Strategy

| Field | Value |
|-------|-------|
| Priority | P3 |
| Category | INFRASTRUCTURE |
| Provenance | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| Evidence | GAP-COS-052 (no mobile app or PWA strategy) |

**Question:** What is the mobile access strategy for CreatorOS?

**Options:**

| Option | Approach | Timeline |
|--------|----------|----------|
| A | PWA (manifest.json, service worker, installability) — mobile-first responsive web | Near-term, low cost |
| B | React Native app sharing code with web (via shared types/logic packages) | Medium-term, moderate cost |
| C | Native iOS + Android apps (Swift/Kotlin) | Long-term, high cost |
| D | Capacitor/Ionic wrapper around the web app | Near-term, native distribution via app stores |
| E | Responsive web only — no PWA, no native | Simplest. No app store. |

**Default if not decided:** A (PWA).

**System recommendation:** A — PWA gives installability, offline caching, and push notifications without native app development cost. The existing codebase is already mobile-first responsive (BottomNav, use-mobile hook). Adding manifest.json and service worker is a 1-day task. Native apps are a Phase 3+ decision when the product has proven market fit.

**Blocked by this decision:**
- Push notification implementation
- App store submission timeline
- Offline capability scope
- Platform-specific UX decisions

---

### DEC-146B-COS-028: UMH Integration Depth

| Field | Value |
|-------|-------|
| Priority | P3 |
| Category | INTEGRATION |
| Provenance | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| Evidence | GAP-COS-066 (dormant projection integration — 1,099 lines in projections/creatoros/integration/) |

**Question:** When and how deeply does CreatorOS integrate with UMH substrate?

**Options:**

| Option | Depth | When |
|--------|-------|------|
| A | Activate dormant projection integration (signals, capabilities, outcomes) as-is | Post-MVP — code exists, needs wiring |
| B | Minimal integration — governance and source truth only (audit trail, not intelligence) | Post-MVP Phase 2 |
| C | Full integration — intelligence routing, cross-platform analytics, agent delegation from EOS to CreatorOS | Post-MVP Phase 3+ |
| D | No integration — CreatorOS operates independently | Indefinitely |

**Default if not decided:** A (activate dormant code post-MVP).

**System recommendation:** A — 1,099 lines of integration code already exist (signals, handlers, outcomes, correlation, manifest, tables). Activating it requires wiring signal emitters to post/product/revenue events and registering the projection at substrate startup. This is a 2-3 day task, not a build. Defer to post-MVP so it does not delay core product.

**Blocked by this decision:**
- UMH signal emission from CreatorOS events
- Cross-platform analytics (creator performance across EOS + CreatorOS)
- Agent delegation from EOS to CreatorOS contexts

---

### DEC-146B-COS-029: EOS Revenue Sharing Model

| Field | Value |
|-------|-------|
| Priority | P3 |
| Category | INTEGRATION |
| Provenance | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| Evidence | phase14_6b_creatoros_eos_boundary_canon.md (revenue attribution spans both via UMH substrate) |

**Question:** How does revenue attribution work when a creator uses both EOS and CreatorOS?

**Options:**

| Option | Model | Complexity |
|--------|-------|------------|
| A | Completely separate — CreatorOS revenue and EOS revenue are independent systems | Simplest. No cross-product attribution. |
| B | Unified revenue view via UMH — both products report to UMH, unified dashboard in EOS | Medium. UMH aggregates. Each product reports independently. |
| C | CreatorOS revenue feeds into EOS financial stack — EOS is the single source of financial truth | Complex. Dependency direction may violate architecture layers. |
| D | Defer — no cross-product revenue integration until both products are live and generating revenue | Lowest cost now. Technical debt later. |

**Default if not decided:** D (defer).

**System recommendation:** D — both products are pre-revenue. Cross-product revenue integration is premature optimization. Build independent revenue tracking in each product. When both are live, implement Option B (UMH as aggregation layer) — this preserves separation of concerns while giving the operator a unified view.

**Blocked by this decision:**
- Revenue analytics architecture
- UMH financial signal design
- Cross-product dashboard

---

### DEC-146B-COS-030: White-Label / Multi-Tenant Strategy

| Field | Value |
|-------|-------|
| Priority | P3 |
| Category | SCOPE |
| Provenance | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| Evidence | PRD Enterprise tier mentions white-label; no implementation exists |

**Question:** Is white-label (custom domain, custom branding per creator) part of the long-term product?

**Options:**

| Option | Scope | Impact |
|--------|-------|--------|
| A | Yes — white-label at Enterprise tier. Custom domain, custom logo, remove CreatorOS branding. | Major architecture impact: multi-tenant routing, per-tenant theming, custom domain SSL. |
| B | Yes but limited — custom domain only. CreatorOS branding remains. | Moderate: Fly.io custom domain certificates per creator. |
| C | No — all creators operate under CreatorOS branding | Simplest. Consistent brand. |
| D | Defer decision until Enterprise tier has paying customers requesting it | No build cost now. Architectural awareness maintained. |

**Default if not decided:** D (defer).

**System recommendation:** D — white-label is an Enterprise feature with zero demand (zero Enterprise customers). Making architectural decisions for white-label now constrains MVP flexibility. Defer, but document the architectural requirements so the system is not built in a way that makes white-label impossible later (e.g., avoid hardcoding CreatorOS branding in places that would need per-tenant override).

**Blocked by this decision:**
- Multi-tenant architecture design
- Custom domain infrastructure
- Theming system scope

---

### DEC-146B-COS-031: Internationalization Timeline

| Field | Value |
|-------|-------|
| Priority | P3 |
| Category | FEATURE |
| Provenance | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| Evidence | GAP-COS-059 (all strings hardcoded in English, no i18n library) |

**Question:** When does internationalization enter the build plan?

**Options:**

| Option | Timing | Approach |
|--------|--------|----------|
| A | Now — set up react-intl/next-intl from the start, externalize all strings | Cheapest long-term. Most expensive now. Every new component must use i18n. |
| B | Post-MVP — retrofit i18n after English-only launch proves market fit | Touch every component once to externalize strings. Moderate cost. |
| C | Never — English-only product | Limits TAM to English-speaking creators. Simplest. |
| D | Set up i18n infrastructure now (library, extraction tooling) but only translate when demand appears | Low cost now (just the plumbing). Strings externalized as written. No translations until needed. |

**Default if not decided:** D (infrastructure now, translations later).

**System recommendation:** D — installing react-intl and wrapping strings in `intl.formatMessage()` from day one is negligible overhead per component. Retrofitting i18n onto 100+ components after launch is a multi-week project. Set up the plumbing now, ship English-only, translate when a non-English market opportunity appears.

**Blocked by this decision:**
- Component authoring pattern (hardcoded strings vs i18n keys)
- Date/number formatting patterns
- RTL support planning

---

### DEC-146B-COS-032: Open-Source Strategy

| Field | Value |
|-------|-------|
| Priority | P3 |
| Category | SCOPE |
| Provenance | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| Evidence | Repository is currently public on GitHub (antonyfmunoz/CreatorOS) |

**Question:** Is CreatorOS open-source, source-available, or proprietary?

**Options:**

| Option | License | Implications |
|--------|---------|--------------|
| A | Open-source (MIT or Apache 2.0) — fully open, anyone can fork and self-host | Maximum community contribution. Competitors can fork. Whop-competitor strategy. |
| B | Source-available (BSL or SSPL) — code visible but commercial use restricted | Transparency without enabling direct competitors. cal.com/PostHog model. |
| C | Proprietary — make repository private, code is trade secret | Full control. No community contribution. Standard SaaS model. |
| D | Defer — keep public repo but add no license (default copyright, no permissions granted) | Current state. Technically no one can legally use the code. |

**Default if not decided:** D (current state — public, no license).

**System recommendation:** C for now — make the repository private. A public repo with broken auth (comparePasswords returns true for ALL) is a liability, not a feature. Revisit open-source vs source-available after the product is secure and generating revenue. Open-sourcing can be a deliberate marketing event, not an accident.

**Blocked by this decision:**
- Repository visibility (public/private)
- License file
- Contribution guidelines
- Community management

---

## Summary Matrix

| ID | Priority | Category | Decision | Default | Recommendation |
|----|----------|----------|----------|---------|----------------|
| DEC-146B-COS-001 | P0 | SCOPE | MVP scope definition | **RESOLVED** | **B ratified** (Content + Community + Courses + Sales) |
| DEC-146B-COS-002 | P0 | SECURITY | Auth migration strategy | **RESOLVED** | **D ratified** (Clerk first, block everything) |
| DEC-146B-COS-003 | P0 | ARCHITECTURE | Source code baseline | **RESOLVED** | **C ratified** (Verify then designate GitHub) |
| DEC-146B-COS-004 | P0 | SCOPE | Module build sequence | **RESOLVED** | **A ratified** (Auth > Split > Tests > Content > Community > Courses > Stripe > Analytics) |
| DEC-146B-COS-005 | P1 | COMMERCE | Payment processor | B | B (Stripe Connect Express) |
| DEC-146B-COS-006 | P1 | COMMERCE | Pricing model confirmation | A | B (Free + Pro only for MVP) |
| DEC-146B-COS-007 | P1 | DESIGN | Design system confirmation | A | A + D parallel (confirm direction, audit references) |
| DEC-146B-COS-008 | P1 | ARCHITECTURE | God file splitting strategy | A | B (Split after Clerk, not before) |
| DEC-146B-COS-009 | P1 | ARCHITECTURE | Database migration strategy | A | A (Versioned migrations, never push) |
| DEC-146B-COS-010 | P1 | INFRASTRUCTURE | Hosting platform | A | A (Fly.io) |
| DEC-146B-COS-011 | P1 | INFRASTRUCTURE | Domain name | F | F (Defer, Fly.io default for now) |
| DEC-146B-COS-012 | P1 | ARCHITECTURE | Replit artifact handling | A | A (Remove immediately) |
| DEC-146B-COS-013 | P1 | ARCHITECTURE | Money data type migration | A | A (Migrate before Stripe) |
| DEC-146B-COS-014 | P1 | ARCHITECTURE | Primary key strategy | B | B (Migrate all to UUID now, zero data risk) |
| DEC-146B-COS-015 | P2 | FEATURE | Content moderation approach | D | D for MVP, B post-MVP |
| DEC-146B-COS-016 | P2 | SCOPE | Community vs courses priority | A | A (Community first, existing schema) |
| DEC-146B-COS-017 | P2 | SCOPE | UGC/Ads timeline | B | B (Phase 3, after core infra) |
| DEC-146B-COS-018 | P2 | INFRASTRUCTURE | Email infrastructure | A | B (Resend) |
| DEC-146B-COS-019 | P2 | FEATURE | Cross-posting platform priority | D | C (Twitter/X first to validate pattern) |
| DEC-146B-COS-020 | P2 | FEATURE | AI feature scope | A | B (Utility + existing AI agents) |
| DEC-146B-COS-021 | P2 | INFRASTRUCTURE | Real-time infrastructure | B | B (Socket.io) |
| DEC-146B-COS-022 | P2 | INFRASTRUCTURE | File storage provider | A | A (Cloudflare R2) |
| DEC-146B-COS-023 | P2 | INFRASTRUCTURE | Error tracking service | A | A (Sentry) |
| DEC-146B-COS-024 | P2 | FEATURE | Notification strategy | B | B (In-app + email) |
| DEC-146B-COS-025 | P2 | FEATURE | Search implementation | E | E for MVP, A post-MVP |
| DEC-146B-COS-026 | P2 | ARCHITECTURE | Soft delete policy | A | A (Content tables only) |
| DEC-146B-COS-027 | P3 | INFRASTRUCTURE | Mobile strategy | A | A (PWA) |
| DEC-146B-COS-028 | P3 | INTEGRATION | UMH integration depth | A | A (Activate dormant code post-MVP) |
| DEC-146B-COS-029 | P3 | INTEGRATION | EOS revenue sharing model | D | D (Defer, both pre-revenue) |
| DEC-146B-COS-030 | P3 | SCOPE | White-label / multi-tenant | D | D (Defer until demand) |
| DEC-146B-COS-031 | P3 | FEATURE | Internationalization timeline | D | D (Plumbing now, translations later) |
| DEC-146B-COS-032 | P3 | SCOPE | Open-source strategy | D | C (Make private, open-source later if desired) |

---

## Decision Dependencies

Decisions are not independent. This graph shows which decisions must be resolved before others can be meaningfully answered.

```
DEC-146B-COS-001 (MVP Scope) — RESOLVED: Option B (Content + Community + Courses + Sales)
  ├── DEC-146B-COS-004 (Build Sequence) — RESOLVED: Option A (Auth > Split > Tests > Content > Community > Courses > Stripe > Analytics)
  ├── DEC-146B-COS-006 (Pricing) — UNBLOCKED: tiers depend on which features exist (now known)
  ├── DEC-146B-COS-016 (Community vs Courses) — UNBLOCKED: both are in scope per Option B
  ├── DEC-146B-COS-017 (UGC/Ads Timeline) — UNBLOCKED: excluded from MVP per Option B
  ├── DEC-146B-COS-019 (Cross-Posting) — UNBLOCKED: deferred to post-MVP per Option B
  └── DEC-146B-COS-020 (AI Scope) — UNBLOCKED: AI chat agents in scope per Option B

DEC-146B-COS-002 (Auth Migration) — RESOLVED: Option D (Clerk first, block everything)
  ├── DEC-146B-COS-008 (God File Split) — UNBLOCKED: sequenced after Clerk per DEC-146B-COS-004
  └── DEC-146B-COS-011 (Domain) — Clerk OAuth needs redirect URLs

DEC-146B-COS-003 (Source Code Baseline) — RESOLVED: Option C (Verify then GitHub canonical)

DEC-146B-COS-005 (Payment Processor)
  ├── DEC-146B-COS-013 (Money Type) — Stripe uses integer cents natively
  └── DEC-146B-COS-015 (Moderation) — payment processor ToS requires content policy

DEC-146B-COS-010 (Hosting)
  ├── DEC-146B-COS-023 (Error Tracking) — deployment target affects source map upload
  └── DEC-146B-COS-011 (Domain) — hosting platform determines DNS target

DEC-146B-COS-022 (File Storage)
  └── DEC-146B-COS-021 (Real-Time) — media delivery may flow through real-time layer
```

---

## Operator Action Required

4 of 32 decisions are resolved (all P0). The 4 P0 decisions (DEC-146B-COS-001 through DEC-146B-COS-004) were ratified by operator on 2026-06-04. 28 decisions remain open. P1 decisions (005-014) should be resolved before feature build begins. P2 and P3 can be resolved incrementally as those workstreams approach.

To resolve a decision, the operator selects an option (A/B/C/D/E/F) for each decision ID. Selected options are recorded in the decision ledger and unlock the corresponding implementation work.

Revised in Phase 14.6F to align with 18 ratified P0 decisions (2026-06-04).
