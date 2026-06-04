# LyfeOS Open Questions and Operator Decision Queue

Revised in Phase 14.6F to align with 18 ratified P0 decisions (2026-06-04).

**Phase:** 14.6B-LyfeOS (revised 14.6F)
**Revised:** 2026-06-04
**Artifact:** 49
**Operator Approved:** false
**Allows Implementation:** false
**Provenance:** OPEN_QUESTION_OPERATOR_DECISION_REQUIRED

---

## What This Is

Every item in this document requires a human operator decision before implementation can proceed. These are not bugs to fix or debt to pay — they are strategic, architectural, or business choices that only the founder can make.

---

## Strategic Decisions

### 1. PRD v1.0 vs v2.0 Canonical Version
- **Decision ID:** DEC-146B-001 → **DEC-146B-LOS-001**
- **STATUS: RESOLVED** — Ratified 2026-06-04 (Phase 14.6E)
- **Ratified Answer:** PRD v2.0 is canonical direction; v1.0 is historical/shipped context. OPERATOR-APPROVED.
- **Question:** Which PRD version is canonical?
- **Context:** Both versions exist in documentation. They differ on tab count (4 vs 5), model count (3 vs 5), onboarding mission count (9 vs 8), and timeline.
- **Recommendation:** v2.0 as canonical direction, v1.0 as historical context.
- **Impact:** Determines feature scope for post-MVP work.
- **Blocks:** Feature expansion decisions.

### 2. Clerk Migration Timing and Approach
- **Decision ID:** DEC-146B-002 → **DEC-146B-LOS-002**
- **STATUS: RESOLVED** — Ratified 2026-06-04 (Phase 14.6E)
- **Ratified Answer:** Migrate LyfeOS from Passport.js+Firebase to Clerk AFTER CreatorOS proves the pattern. OPERATOR-APPROVED.
- **Question:** Should LyfeOS migrate from Passport.js+Firebase to Clerk? If so, when?
- **Context:** Current auth works. Firebase deeply integrated (auth, verification, 2FA, push notifications). CreatorOS should prove the pattern first.
- **Options:** (A) Migrate after CreatorOS, (B) Keep Firebase, (C) Defer indefinitely.
- **See:** Artifact 38

### 3. UMH Integration Boundary Definition
- **Decision ID:** DEC-146B-003
- **Question:** Where does LyfeOS end and UMH substrate begin?
- **Context:** UMH integration bridge exists (1184 lines). NOVA could route through UMH model_router. Quests/stats could emit UMH signals.
- **Options:** (A) Stay isolated, (B) Light integration (signals + capabilities), (C) Deep integration (NOVA as UMH agent, shared kernel).
- **Blocks:** All UMH integration work.

### 4. Infrastructure Migration (Replit to Fly.io or Other)
- **Decision ID:** DEC-146B-004 → **DEC-146B-LOS-003**
- **STATUS: RESOLVED** — Ratified 2026-06-04 (Phase 14.6E)
- **Ratified Answer:** Fly.io is the Trinity standard. Migrate from Replit to Fly.io. OPERATOR-APPROVED.
- **Question:** Should LyfeOS migrate from Replit?
- **Context:** Replit works but has vendor lock-in, no CI/CD, no staging, autoscale cold starts.
- **Options:** (A) Stay on Replit, (B) Fly.io (Trinity standard), (C) Vercel, (D) Defer.
- **See:** Artifact 44

### 5. Transformation Thread Ratification
- **Decision ID:** DEC-146B-005
- **Question:** Should the Transformation Thread be added to post-MVP scope?
- **Context:** PRD describes it as developmental engine. No schema or code exists. Distinguishing feature but significant complexity.
- **Options:** (A) Post-MVP roadmap, (B) End-state only, (C) Deprioritize.

### 6. Data Provenance Model Approval
- **Decision ID:** DEC-146B-007
- **Question:** Approve the 6-category provenance classification model?
- **Context:** Categories: MANUAL_INPUT, USER_SELF_REPORT, COMPUTED_FROM_APP_BEHAVIOR, IMPORTED_FROM_INTEGRATIONS, LIVE_VERIFIED_DEVICE_API, UMH_INFERRED_SYNTHESIZED.
- **See:** Artifact 33

### 7. AI Permission Tiers Approval
- **Decision ID:** DEC-146B-008
- **Question:** Should NOVA have tiered permissions for data access?
- **Context:** Currently unrestricted read access to all user data including shadow patterns, beliefs, financial data.
- **Options:** (A) Keep unrestricted, (B) Read-only tiers, (C) Read/write tiers with user control.

### 8. Privacy Classification for Sensitive Fields
- **Decision ID:** DEC-146B-009
- **Question:** Should sensitive profile fields have enhanced access controls?
- **Context:** user_profile contains therapy-level data stored alongside display preferences.
- **Options:** (A) Classify + field-level controls, (B) Uniform access, (C) Separate sensitive table.

### 9. Backup/Recovery Priority and Approach
- **Decision ID:** DEC-146B-010
- **Question:** How urgently should backup be verified?
- **Context:** Only deployed Trinity app. Unknown if database has user data.
- **Recommendation:** Verify NOW (30 minutes).
- **See:** Artifact 40

### 10. RLS Implementation Priority
- **Decision ID:** DEC-146B-011
- **Question:** When should RLS policies be added?
- **Options:** (A) Before growth (P0), (B) With hardening (P1), (C) After migration (P2).
- **See:** Artifact 39

### 11. Error Tracking Service Selection
- **Decision ID:** DEC-146B-012
- **Question:** Which error tracking service?
- **Options:** (A) Sentry (free tier), (B) PostHog, (C) Bugsnag, (D) Defer.
- **Recommendation:** Sentry.

### 12. NOVA Naming Correction Approval
- **Decision ID:** DEC-146B-013
- **Question:** Is "NOVA" (Neural Operating Virtual Assistant) the finalized AI companion name?
- **Context:** ai_assistant_name defaults to "NOVA" in user_stats (configurable per user).

### 13. Integration Onboarding Mission Scope
- **Decision ID:** DEC-146B-014
- **Question:** Should onboarding include a mission for connecting integrations?
- **Options:** (A) Add integration mission, (B) Keep separate, (C) Optional post-onboarding.

### 14. Which Secondary Modules Become Primary Nav
- **Decision ID:** DEC-146B-015
- **Question:** Which Systems page modules should be promoted to primary navigation?
- **Context:** Calendar and Documents used more than Spreadsheets/Canvases/Graphs.
- **Options:** (A) Keep all under Systems, (B) Promote Calendar + Documents, (C) Data-driven.

### 15. Stripe Re-integration Timing
- **Decision ID:** DEC-146B-016
- **Question:** When to re-integrate Stripe billing?
- **Context:** Stripe removed, stubs remain. Subscription page UI intact.
- **Options:** (A) Before first paying user, (B) After hardening, (C) After migration, (D) Different provider.

### 16. Whether LyfeOS Keeps Own DB or Becomes UMH Projection
- **Decision ID:** DEC-146B-006
- **Question:** Should LyfeOS data stay in its own Neon instance or move to UMH substrate DB?
- **Context:** 35 tables in separate Neon instance. UMH integration polls externally. Full projection would merge DBs.
- **Options:** (A) Separate DB with polling, (B) Shared UMH DB, (C) Hybrid.
- **Blocks:** Data architecture decisions.

---

## Summary

| Category | Count | Resolved | Open |
|----------|-------|----------|------|
| Strategic / architectural | 6 | 1 (DEC-146B-LOS-001) | 5 |
| Data / privacy | 4 | 0 | 4 |
| Technical / infrastructure | 6 | 2 (DEC-146B-LOS-002, DEC-146B-LOS-003) | 4 |
| **Total** | **16** | **3** | **13** |

3 items resolved via operator ratification (Phase 14.6E, 2026-06-04). 13 items remain OPEN and require operator decision.
