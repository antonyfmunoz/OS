---
phase: "14.6C"
status: "DRAFT"
operator_approved: false
allows_implementation: false
date: "2026-06-04"
provenance: "SYNTHESIZED_CANON"
sources:
  - "data/umh/trinity_convergence/phase14_6b_umh/ (57 artifacts)"
  - "data/umh/eos_lossless_canon/ (30 artifacts)"
  - "data/umh/creatoros_lossless_canon/ (28 artifacts)"
  - "data/umh/trinity_convergence/phase14_6b_lyfeos/ (51 artifacts)"
  - "Operator P0 clarification (verbatim, 2026-06-04)"
---

# Phase 14.6C: Implementation Blockers

Everything blocking implementation across all 4 products.

This document synthesizes every blocker surfaced during Phase 14.6B lossless canon reconstruction across UMH, EOS, CreatorOS, and LyfeOS. Blockers are drawn from decision queues (98 total decisions), implementation debt registers (145 total debt items), professional gap registers (218 total gaps), and the P0 operator clarification issued 2026-06-04. Nothing here is resolved. Nothing here authorizes implementation.

---

## Blocker Taxonomy

| Level | Meaning | Count |
|-------|---------|-------|
| P0 | Nothing can start until resolved | 8 |
| P1 | Blocks MVP / first release | 23 |
| P2 | Blocks growth / scaling | 14 |
| Cross-product | Shared infrastructure gap affecting all 4 products | 7 |

---

## P0 Blockers (Nothing Can Start)

### BLK-001: UMH Reality Model Correction

**Source:** Operator P0 clarification (verbatim, 2026-06-04)
**Affects:** UMH (17 artifacts), all downstream Cockpit and reality-engine phases
**Decision IDs:** DEC-146C-001, DEC-146C-002, DEC-146C-003

The operator has issued a binding correction to the foundational UMH product definition. The correction states:

1. UMH is not an operational tooling model or business/software model. It must model physical, digital, cognitive, biological, social, economic, symbolic, operational, software, memory, source-truth, and OS-level reality as corresponding layers of one isomorphic reality model.
2. The instance reality model carries the same isomorphic ambition from the perspective of a specific instantiated user, company, product, environment, or incarnation.
3. Stage 1 must not be split into separate sequential stages. Stage 1 is one indivisible minimum viable organism: Reality Model + Cockpit + Memory + Governed Execution Loop. The harness cannot function without the reality model. Cockpit without a reality model is only a dashboard.
4. Materialization Principle: if a human can imagine an outcome, UMH should attempt to simulate the path from imagination to materialization. Lack of resources creates acquisition loops, research loops, experiment loops, work packets, and time-bound execution paths.

**17 UMH artifacts requiring revision:**

| # | Artifact | Correction Needed |
|---|----------|-------------------|
| 1 | umh_lossless_product_canon.md | Core product definition must reframe UMH as isomorphic reality engine, not orchestration/harness |
| 2 | umh_projection_ecosystem_doctrine.md | Treats UMH as "orchestration kernel" — must reframe as reality substrate that projections observe |
| 3 | umh_full_end_state_canon.md | End state must reflect 12-layer isomorphic reality ambition (physical through OS-level) |
| 4 | umh_cockpit_jarvis_doctrine.md | Cockpit is part of indivisible Stage 1 organism, not a separate phase deliverable |
| 5 | umh_cockpit_buildable_readiness_detail.md | Readiness criteria assume sequential build (harness then cockpit) — must assume unified organism |
| 6 | umh_cockpit_readiness_buildable_criteria.md | Same sequential assumption as above |
| 7 | umh_cockpit_readiness_gap_matrix.md | Gaps framed around operational dashboard, not reality-model interface |
| 8 | umh_cockpit_screen_panel_inventory.json | Panels designed for operational display — must include reality-model layer panels |
| 9 | umh_private_cockpit_vs_public_projection_boundary.md | Boundary assumes cockpit is "just" private UI — must account for reality-model operator surface |
| 10 | umh_substrate_cockpit_projection_boundary_matrix.md | Boundary model incomplete without reality-model layer |
| 11 | umh_world_model_memory_architecture.md | Closest to reality-model intent but framed operationally, not ontologically |
| 12 | umh_execution_boundary_model.md | Execution model needs materialization principle integration |
| 13 | umh_governance_approval_lifecycle.md | Governance must cover reality-model mutation (what can change the model of reality) |
| 14 | umh_code_resolved_substrate_canon.md | Substrate canon treats UMH as code infrastructure, not reality engine |
| 15 | umh_workstation_jarvis_experience_canon.md | Jarvis experience must interface with reality model, not just operational commands |
| 16 | umh_signal_interpretation_decomposition_canon.md | Signal processing is the reality-model input layer — must be framed as such |
| 17 | umh_naming_canonicalization.md | Naming may need revision once "reality model" is the core concept |

**3 ratification decisions required:**

| Decision ID | Question |
|-------------|----------|
| DEC-146C-001 | Ratify the isomorphic reality model as the foundational UMH product definition (replacing the orchestration/harness framing) |
| DEC-146C-002 | Ratify Stage 1 as one indivisible organism (Reality Model + Cockpit + Memory + Governed Execution Loop) — no sequential phasing |
| DEC-146C-003 | Ratify the Materialization Principle as a core UMH design law |

**Blocks:** ALL Cockpit implementation phases. ALL UMH reality-engine phases. ALL projection integration that depends on UMH substrate framing. This is the single highest-priority blocker across the entire portfolio.

---

### BLK-002: EOS Beast Branch Promotion

**Source:** DEC-146B-EOS-001 (P0), DEBT-003, DEBT-014, DEBT-041, GAP-ARC-001
**Affects:** EOS (all implementation)

The EOS codebase exists in two divergent locations:
- **GitHub main** (antonyfmunoz/EntrepreneurOS): 202 files. Stale since 2026-02-20. Passport.js auth. No RLS. Monolithic routes.ts (2,362 lines). Zero tests.
- **Beast feature/company-system**: 603 files. Active development through 2026-04-16. Clerk auth integration. Portfolio/entity hierarchy. Company system. 14 split route modules. Vitest + Playwright configured.

401-file divergence. Beast is not on GitHub. Beast is not accessible from VPS. Beast has never been through CI. The 401 new files have never been reviewed.

**What must happen before any EOS code is written:**
1. Push Beast branch to GitHub (DEBT-014)
2. Run full audit: tsc --noEmit, ESLint, npm audit, dead code detection (DEBT-041)
3. Operator ratifies Beast as canonical (DEC-146B-EOS-001)
4. Promote Beast as new main. Archive old main.
5. Unify three schema surfaces (GitHub main, Beast, UMH platform) into one canonical schema (DEBT-015)

**Blocks:** Every EOS implementation task. Cannot write code without knowing which codebase is the starting point. 13 CRITICAL-severity debt items and 6 CRITICAL-severity gaps are downstream of this decision.

---

### BLK-003: CreatorOS Auth Bypass

**Source:** COS-SEC-001, GAP-COS-001, DEC-146B-COS-002
**Affects:** CreatorOS (all implementation, all deployment)

`comparePasswords()` in `server/auth.ts` unconditionally returns `true` for ALL passwords. Any password works for any user account. Full account takeover with only a username. This is not a partial vulnerability — authentication is completely disabled.

Additionally:
- Hardcoded session secret fallback: `'creatorOS-secret-key'` (COS-SEC-002, GAP-COS-002)
- Zero CSRF protection on all 89 mutation endpoints (GAP-COS-003)
- Zero rate limiting on auth endpoints (COS-SEC-003, GAP-COS-004)
- No input validation on any route (COS-SEC-005, GAP-COS-005)
- Parallel auth system in zustand store exposes full user list to client (GAP-COS-023)

**What must happen:**
Operator must select an auth migration strategy (DEC-146B-COS-002):
- Option A: Fix Passport.js immediately, migrate to Clerk later (double work)
- Option B: Skip fix, migrate directly to Clerk (app stays broken longer)
- Option C: Fix Passport.js + harden, defer Clerk (accumulates tech debt)
- Option D: Clerk migration first, block ALL other work until complete (recommended)

**Blocks:** ALL CreatorOS deployment. ALL feature work (features built on broken auth must be rebuilt). Session management. OAuth configuration. Cannot deploy to any public URL.

---

### BLK-004: CreatorOS MVP Scope Undefined

**Source:** DEC-146B-COS-001 (P0, carried from DEC-145-002)
**Affects:** CreatorOS (all implementation planning)

Three conflicting MVP scope definitions exist across source documents:

| Scope | Source | Modules | Timeline |
|-------|--------|---------|----------|
| A: Content + community only | Google Doc Tab 6 | 2 of 16 | 4-6 weeks |
| B: Content + community + courses + products | System synthesis | 4 of 16 | 8-12 weeks |
| C: Content + community + courses + marketplace + payments | Google Doc Tab 7 | 6 of 16 | 14-18 weeks |
| D: Full PRD (all 16 modules) | Google Doc Tab 3+8 | 16 of 16 | 6-9 months |

Cannot proceed without scope. Every downstream decision (build sequence, sprint planning, resource allocation, which of 25 missing tables to build) depends on this.

**Blocks:** ALL CreatorOS feature build scope. Sprint planning. Database migration planning. Module priority ordering. Pricing model implementation.

---

### BLK-005: CreatorOS Source Code Baseline

**Source:** DEC-146B-COS-003 (P0)
**Affects:** CreatorOS (all development)

Source inventory shows 296 GitHub files vs 271 Beast files (25-file difference unexplained). Which codebase is canonical? Where do PRs target? Where does CI run?

**Blocks:** All development work. CI/CD setup. Branch protection rules.

---

### BLK-006: CreatorOS Module Build Sequence

**Source:** DEC-146B-COS-004 (P0)
**Affects:** CreatorOS (all implementation sequencing)

Depends on BLK-004 (MVP scope) being resolved first. Even after scope is decided, the operator must ratify the build order: auth first or features first? Tests before god-file split or after? Revenue features early or late?

**Blocks:** Sprint planning. Resource allocation per phase. Dependency ordering for database migrations.

---

### BLK-007: EOS MVP Scope Confirmation

**Source:** DEC-146B-EOS-002 (P0)
**Affects:** EOS (implementation sequencing)

The 5-release plan (R1-R5) exists but is unratified:
- R1: Auth + onboarding + single company dashboard
- R2: EA + basic delegation
- R3: Financial tracking + KPIs
- R4: Workflow SOPs + templates
- R5: Agent autonomy + polish

Operator must confirm or modify this plan before sprint planning begins.

**Blocks:** Implementation sequencing. Sprint planning. All milestone definitions.

---

### BLK-008: EOS Auth Finalization

**Source:** DEC-146B-EOS-003 (P0)
**Affects:** EOS (all user-facing features)

Clerk exists on Beast branch but is unratified as production auth. Options: confirm Clerk, switch to Auth.js, switch to Supabase Auth, or keep Passport.js from stale main.

**Blocks:** All user-facing features. RLS policy design. Session management. Middleware architecture. Cannot implement onboarding, dashboard, or any authenticated feature without this.

---

## P1 Blockers (Block MVP / First Release)

### EOS P1 Blockers (10)

| ID | Blocker | Decision/Debt ID | What It Blocks |
|----|---------|-------------------|----------------|
| BLK-EOS-P1-01 | No production deployment exists | GAP-INF-001, DEBT-019 | Cannot ship anything to users |
| BLK-EOS-P1-02 | No CI/CD pipeline | GAP-INF-002, DEBT-019 | No automated testing, no safe deploys |
| BLK-EOS-P1-03 | No real authentication on UMH platform API | GAP-SEC-001, DEBT-028 | Any client with an org UUID can impersonate owner |
| BLK-EOS-P1-04 | RLS bypass fallback (DATABASE_APP_URL) | GAP-SEC-002 | Env var missing silently disables all RLS |
| BLK-EOS-P1-05 | No test coverage | GAP-TST-001, DEBT-017 | Zero tests on GitHub main, Beast coverage unknown |
| BLK-EOS-P1-06 | Three schema surfaces not unified | DEBT-015, GAP-ARC-004 | GitHub main, Beast, UMH platform have overlapping schemas |
| BLK-EOS-P1-07 | No EA Agent implemented | DEBT-030, GAP-ARC-005 | Core communication chain broken at step 1 (User -> EA) |
| BLK-EOS-P1-08 | No pricing model defined | DEC-146B-EOS-005, GAP-BIZ-001 | Cannot implement Stripe, onboarding, or landing page |
| BLK-EOS-P1-09 | No Terms of Service or privacy policy | GAP-CMP-003, GAP-CMP-004 | Legal blocker for any public deployment |
| BLK-EOS-P1-10 | Notification system architecture undecided | DEC-146B-EOS-027 | Affects real-time infrastructure, approval queue, agent notifications |

### CreatorOS P1 Blockers (7)

| ID | Blocker | Decision/Debt ID | What It Blocks |
|----|---------|-------------------|----------------|
| BLK-COS-P1-01 | No production deployment | COS-INFRA-001, GAP-COS-009 | App has never been deployed anywhere |
| BLK-COS-P1-02 | God files (routes.ts 53KB, storage.ts 104KB) | COS-ARCH-001, COS-ARCH-002 | Parallel development, code review, module testing |
| BLK-COS-P1-03 | Zero test files | COS-TEST-001, GAP-COS-008 | No regression safety net for any refactoring |
| BLK-COS-P1-04 | Payment processor undecided | DEC-146B-COS-005 | Blocks all commerce: checkout, payouts, subscriptions |
| BLK-COS-P1-05 | Design system unconfirmed | DEC-146B-COS-007 | Blocks component library, dark mode, all new UI |
| BLK-COS-P1-06 | No payment integration (zero Stripe) | COS-INT-002, GAP-COS-012 | Cannot monetize. Core business model requires payments. |
| BLK-COS-P1-07 | 25 missing database tables | COS-DATA-001, GAP-COS-013 | 9 of 16 modules have zero schema support |

### LyfeOS P1 Blockers (3)

| ID | Blocker | Decision/Debt ID | What It Blocks |
|----|---------|-------------------|----------------|
| BLK-LOS-P1-01 | No backup verification | DEBT-001, GAP-REL-001 | Only deployed Trinity app — data loss risk |
| BLK-LOS-P1-02 | No error tracking | DEBT-002, GAP-REL-002 | Production app with zero error visibility |
| BLK-LOS-P1-03 | No RLS on 35 tables | DEBT-004, GAP-SEC-004 | Single app bug could expose cross-user data |

### UMH P1 Blockers (3)

| ID | Blocker | Decision/Debt ID | What It Blocks |
|----|---------|-------------------|----------------|
| BLK-UMH-P1-01 | Execution control endpoints are stubs | C1, Cockpit Gap #9 | 7 endpoints return static ok:false. No verified execution control loop. |
| BLK-UMH-P1-02 | Three parallel execution paths not unified | A1, Gap 2.1 | Gateway/Spine/WorkPacket each have different governance, memory, tracing |
| BLK-UMH-P1-03 | Substrate connects as neondb_owner (BYPASSRLS) | S1, Gap 6.1 | All RLS policies bypassed for Python substrate code |

---

## P2 Blockers (Block Growth / Scaling)

| ID | Product | Blocker | Reference |
|----|---------|---------|-----------|
| BLK-P2-01 | EOS | No staging environment | GAP-INF-004, DEBT-034 |
| BLK-P2-02 | EOS | No error tracking/monitoring | DEBT-020, GAP-MON-001 |
| BLK-P2-03 | EOS | Embedding dimension mismatch (384 vs 1536) undecided | DEC-146B-EOS-004, GAP-ARC-007 |
| BLK-P2-04 | EOS | No onboarding flow implemented | GAP-UIX-004 |
| BLK-P2-05 | CreatorOS | No content moderation | GAP-COS-024 (required by payment processor ToS) |
| BLK-P2-06 | CreatorOS | No search functionality | GAP-COS-035 |
| BLK-P2-07 | CreatorOS | No cross-posting integrations | GAP-COS-026 (core product promise "post once, publish everywhere") |
| BLK-P2-08 | LyfeOS | ~5% test coverage (24 tests) | DEBT-006, GAP-QA-002 |
| BLK-P2-09 | LyfeOS | No CI/CD pipeline | DEBT-007, GAP-QA-001 |
| BLK-P2-10 | LyfeOS | Clerk migration timing undecided | DEC-146B-002 |
| BLK-P2-11 | UMH | No request/access logging on cockpit API | O1, Gap 9.1 |
| BLK-P2-12 | UMH | 26,671 lines dead code in workstation/ | A3, Gap 2.3 |
| BLK-P2-13 | UMH | Projection manifests outdated vs 14.6B canons | P3 |
| BLK-P2-14 | UMH | No sensitive data exclusion mechanism for LyfeOS signals | Gap 5.1 |

---

## Cross-Product Blockers

These affect all 4 products and cannot be solved product-by-product.

### XBLK-001: No Unified Auth Strategy

No ratified auth provider decision spans the portfolio.
- **EOS:** Clerk on Beast (unratified). Passport.js on stale main.
- **CreatorOS:** Broken Passport.js. Clerk migration recommended but undecided.
- **LyfeOS:** Passport.js + Firebase (working). Clerk migration deferred.
- **UMH Cockpit:** API key + operator token + dev bypass. No Clerk. No JWT.

Each product making independent auth decisions creates four divergent auth systems. If Clerk is the portfolio standard, it should be ratified as such. If not, the cross-product auth integration protocol must account for different providers.

**Unresolved decisions:** DEC-146B-EOS-003, DEC-146B-COS-002, DEC-146B-002 (LyfeOS)

---

### XBLK-002: No Deployment Infrastructure Provisioned

| Product | Deployment Status |
|---------|-------------------|
| UMH Cockpit | Deployed (universalmetaharness.tech on Fly.io) |
| LyfeOS | Deployed (lyfeos.net on Replit) |
| EOS | Not deployed anywhere. No fly.toml. No Dockerfile. No domain. |
| CreatorOS | Not deployed anywhere. No Dockerfile. No fly.toml. No domain. |

Two of four products have zero deployment infrastructure. Hosting platform decisions are unresolved for both (DEC-146B-EOS-010, DEC-146B-COS-010).

---

### XBLK-003: No CI/CD for Any Product

| Product | CI/CD Status |
|---------|--------------|
| UMH | No CI. 4 pre-commit hooks exist locally only. |
| EOS | No CI. No GitHub Actions. No automated testing. |
| CreatorOS | No CI. No GitHub Actions. No automated testing. |
| LyfeOS | No CI. No GitHub Actions. No automated testing. |

Zero automated quality gates across the entire portfolio. Every merge to main in every repo is unverified.

---

### XBLK-004: No Production Monitoring for Any Product

| Product | Monitoring Status |
|---------|-------------------|
| UMH | error_recorder.py centralized recording. No Sentry. No APM. No alerting. |
| EOS | PostHog analytics SDK on Beast (not deployed). No error tracking. |
| CreatorOS | Zero monitoring infrastructure. |
| LyfeOS | Zero monitoring infrastructure. Deployed production app with no error visibility. |

LyfeOS is the most urgent case — it is the only deployed Trinity app with real potential user data and zero error tracking.

---

### XBLK-005: UMH Integration Protocol Not Activated for Any Projection

| Projection | Integration Code | Runtime Status |
|------------|-----------------|----------------|
| EOS | 30 files, 5,699 lines | DORMANT — never invoked at runtime (DEBT-021) |
| CreatorOS | 6 files, 1,099 lines | DORMANT — never tested against live substrate (COS-INT-001) |
| LyfeOS | 2 files (manifest + signals) | DORMANT — partial integration only (Gap 4.1) |

All three projections have integration code that compiles but has never been activated. The UMH substrate governs nothing in practice.

---

### XBLK-006: No Cross-Product Data Boundary Policy

No ratified policy governs:
- What LyfeOS data (therapy, health, financial) UMH may ingest (UMH Q10)
- Whether cross-projection data sharing is opt-in or global (UMH Q11)
- How revenue attribution works across EOS and CreatorOS (DEC-146B-COS-029)
- Privacy classification for sensitive fields in LyfeOS (DEC-146B-009)

Without this, any UMH integration that touches LyfeOS data is a privacy risk.

---

### XBLK-007: No Backup/Recovery Verified for Any Product

| Product | Backup Status |
|---------|--------------|
| UMH | Neon PITR exists. No tested restore. No runbook. (Gap 12.1) |
| EOS | Neon PITR exists. No tested restore. No runbook. (DEBT-033) |
| CreatorOS | Neon PITR exists. No tested restore. No runbook. (GAP-COS-050) |
| LyfeOS | Neon PITR exists. No tested restore. No runbook. (DEBT-001) |

All four products rely on Neon's built-in PITR. None have a verified restore procedure. None have a documented recovery runbook. LyfeOS is most urgent as the only deployed app.

---

## Blocker Dependency Chain

Blockers are not independent. This graph shows which must be resolved before others become actionable.

```
BLK-001 (UMH Reality Model Correction)
  |
  +-> Blocks ALL UMH Cockpit implementation
  +-> Blocks ALL UMH reality-engine phases
  +-> Blocks UMH P1 blockers (BLK-UMH-P1-01 through P1-03 are downstream)
  +-> Does NOT block EOS, CreatorOS, or LyfeOS standalone work
  |
BLK-002 (EOS Beast Branch Promotion)
  |
  +-> BLK-008 (EOS Auth Finalization) — cannot finalize auth without knowing which codebase
  +-> BLK-007 (EOS MVP Scope) — can be decided in parallel
  +-> BLK-EOS-P1-01 through P1-10 — all downstream of promotion
  |
BLK-003 (CreatorOS Auth Bypass)
  |
  +-> BLK-COS-P1-01 (no deployment) — cannot deploy until auth works
  +-> BLK-COS-P1-02 (god files) — splitting strategy depends on whether Clerk is done first
  +-> BLK-COS-P1-06 (no Stripe) — payment integration requires auth
  |
BLK-004 (CreatorOS MVP Scope) + BLK-005 (Source Baseline)
  |
  +-> BLK-006 (Build Sequence) — cannot sequence what is not scoped
  +-> BLK-COS-P1-04 (payment processor) — scope determines if payments are MVP
  +-> BLK-COS-P1-07 (missing tables) — scope determines which tables to build
  |
BLK-007 (EOS MVP Scope) — independent of Beast promotion
  |
  +-> BLK-EOS-P1-08 (pricing) — pricing depends on feature scope
  |
BLK-008 (EOS Auth) — depends on BLK-002
  |
  +-> BLK-EOS-P1-03 (platform API auth) — must bridge Clerk to UMH API
  +-> BLK-EOS-P1-06 (schema unification) — PK types depend on auth provider
```

---

## Unresolved Operator Decisions Summary

Total decisions across all products: **98**

| Product | P0 | P1 | P2 | P3 | Total |
|---------|----|----|----|----|-------|
| UMH | 3 (new 14.6C) + 6 (existing) = 9 | 4 | 2 | 0 | 15 |
| EOS | 3 | 10 | 12 | 5 | 30 |
| CreatorOS | 4 | 10 | 12 | 6 | 32 |
| LyfeOS | 2 | 6 | 4 | 4 | 16 |
| **Cross-product** | 3 | 2 | 0 | 0 | **5** |
| **Total** | **21** | **32** | **30** | **15** | **98** |

The 21 P0 decisions must be resolved before any implementation begins anywhere.

---

## Recommended Unblocking Sequence

This is the mechanically optimal order. Each step unblocks the maximum downstream work.

### Step 1: Ratify UMH Reality Model Correction (DEC-146C-001, 002, 003)
- **Time:** Operator review only (no code)
- **Unblocks:** All UMH Cockpit implementation. All UMH reality-engine work. Corrects the foundational product definition for everything else.
- **Parallel with:** Steps 2-5 (UMH correction does not gate EOS/CreatorOS/LyfeOS standalone work)

### Step 2: Ratify EOS Beast Branch Promotion (DEC-146B-EOS-001)
- **Time:** Operator decision (minutes). Push + audit (days).
- **Unblocks:** ALL EOS implementation. Resolves the 401-file divergence. Enables schema unification. Enables auth finalization.
- **Then:** Push Beast to GitHub. Run full audit. Promote as main.

### Step 3: Ratify EOS Auth (DEC-146B-EOS-003) + MVP Scope (DEC-146B-EOS-002)
- **Time:** Operator decisions (minutes each)
- **Depends on:** Step 2 (Beast must be canonical before auth is finalized)
- **Unblocks:** All user-facing EOS features. Sprint planning. Pricing model. Schema unification.

### Step 4: Ratify CreatorOS Auth Strategy (DEC-146B-COS-002)
- **Time:** Operator decision (minutes). Clerk migration (2-3 weeks).
- **Unblocks:** ALL CreatorOS deployment. ALL feature work. Session management.
- **Recommendation:** If Clerk is confirmed for EOS in Step 3, confirm it here too (shared pattern, single Clerk app or coordinated apps).

### Step 5: Ratify CreatorOS MVP Scope (DEC-146B-COS-001) + Source Baseline (DEC-146B-COS-003) + Build Sequence (DEC-146B-COS-004)
- **Time:** Operator decisions (3 decisions, can be batched)
- **Unblocks:** CreatorOS sprint planning. Module prioritization. Database migration scope.

### Step 6: Resolve Cross-Product Auth Strategy
- **Time:** Emerges from Steps 3-4. Ratify portfolio-wide if Clerk is chosen for both.
- **Unblocks:** XBLK-001. Cross-product session management. UMH API auth bridging.

### Step 7: LyfeOS Immediate Hardening (no operator decision required)
- **Time:** Hours
- **Actions:** Verify Neon backup (30 min). Install Sentry (1 hour). Verify session secret env var (5 min).
- **Unblocks:** BLK-LOS-P1-01, BLK-LOS-P1-02. Reduces risk on the only deployed product.

### Step 8: Resolve Remaining P1 Decisions
- **Time:** Operator review session (batch all P1 decisions per product)
- **EOS:** 10 P1 decisions (embedding dimension, pricing, template library, portfolio scope, autonomy levels, RLS strategy, deployment target, notification system, onboarding depth, UMH coupling)
- **CreatorOS:** 10 P1 decisions (payment processor, pricing model, design system, god file strategy, migration strategy, hosting, domain, Replit artifacts, money type, PK strategy)
- **LyfeOS:** 6 P1 decisions (PRD version, Clerk timing, UMH boundary, infrastructure migration, transformation thread, DB location)

### Step 9: Parallel Implementation Streams
- **After:** Steps 1-8 complete
- **Stream A:** UMH Cockpit + Reality Model (corrected per Step 1)
- **Stream B:** EOS R1 (auth + onboarding + dashboard on promoted Beast)
- **Stream C:** CreatorOS Phase 1 (Clerk + god file split + tests)
- **Stream D:** LyfeOS hardening (RLS + CI/CD + error tracking)

---

## Decision Count by Product and Priority

### UMH (15 decisions)

| ID | Priority | Category | Decision |
|----|----------|----------|----------|
| DEC-146C-001 | P0 | product_definition | Ratify isomorphic reality model as foundational UMH definition |
| DEC-146C-002 | P0 | architecture | Ratify Stage 1 as indivisible organism (Reality Model + Cockpit + Memory + Execution) |
| DEC-146C-003 | P0 | design_law | Ratify Materialization Principle |
| Q1 | P0 | naming | Confirm "Universal Meta Harness" as canonical name |
| Q2 | P0 | naming | PHILOSOPHY.md rewrite scope |
| Q3 | P0 | architecture | Three parallel execution paths — target unification |
| Q4 | P0 | architecture | workstation/ 26,671 lines dead code disposition |
| Q6 | P0 | cockpit | Minimum Cockpit MVP panel/capability definition |
| Q8 | P0 | security | Dev bypass removal timeline |
| Q5 | P1 | architecture | ProductConnectionManager upward dependency resolution |
| Q7 | P1 | cockpit | Per-projection cockpit panels vs unified view |
| Q9 | P1 | security | Substrate DB role restriction timeline |
| Q10 | P1 | data_boundary | LyfeOS data exclusion from UMH ingestion |
| Q12 | P2 | execution | Maximum overnight autonomy level |
| Q13 | P2 | execution | Simulation/deliberation council configurability |

### EOS (30 decisions)

3 P0 (Beast promotion, MVP scope, auth). 10 P1. 12 P2. 5 P3. Full list in phase14_6b_eos_open_questions_operator_decision_queue.md.

### CreatorOS (32 decisions)

4 P0 (MVP scope, auth migration, source baseline, build sequence). 10 P1. 12 P2. 6 P3. Full list in phase14_6b_creatoros_open_questions_operator_decision_queue.md.

### LyfeOS (16 decisions)

2 P0 (PRD canonical version, DB location). 6 P1. 4 P2. 4 P3. Full list in lyfeos_open_questions_operator_decision_queue.md.

---

## Debt and Gap Totals by Product

| Product | Debt Items | Professional Gaps | Total Deficiencies |
|---------|-----------|-------------------|-------------------|
| UMH | 41 | 47 (10 P0, 25 P1, 12 P2) | 88 |
| EOS | 44 | 83 (6 CRITICAL, 27 HIGH, 36 MEDIUM, 14 LOW) | 127 |
| CreatorOS | 38 | 67 (5 CRITICAL, 18 HIGH, 28 MEDIUM, 16 LOW) | 105 |
| LyfeOS | 22 | 21 | 43 |
| **Total** | **145** | **218** | **363** |

---

## Status of This Document

This document is DRAFT. It is not operator-approved. It does not authorize implementation. It synthesizes blockers across all 4 products from the Phase 14.6B lossless canon reconstruction.

The operator P0 clarification (BLK-001) is included verbatim per the operator's instruction. It is classified as an OPERATOR CLARIFICATION, not silently approved canon.

No blocker in this document is resolved. Resolution requires explicit operator selection recorded in the decision ledger.
