# LyfeOS Implementation Debt Register

Revised in Phase 14.6F to align with 18 ratified P0 decisions (2026-06-04).

**Phase:** 14.6B-LyfeOS (revised 14.6F)
**Artifact:** 47
**Revised:** 2026-06-04
**Operator Approved:** false
**Allows Implementation:** false
**Provenance:** SYNTHESIZED_CANON

**Ratified Decisions Affecting Debt Prioritization:**
- **DEC-146B-LOS-001** (PRD v2.0 canonical): Debt items should be prioritized against v2.0 scope, not v1.0.
- **DEC-146B-LOS-002** (Clerk migration after CreatorOS): Auth-related debt (Passport.js/Firebase) will be addressed during Clerk migration. Timing: after CreatorOS proves the pattern.
- **DEC-146B-LOS-003** (Fly.io infrastructure): Infrastructure debt related to Replit will be resolved during Fly.io migration.

---

## Classification

Each debt item is classified by:
- **Priority:** P0 (critical), P1 (important), P2 (should-have), P3 (nice-to-have)
- **Category:** SECURITY, RELIABILITY, QUALITY, OBSERVABILITY, INFRASTRUCTURE, DATA
- **Effort:** LOW (hours), MEDIUM (days), HIGH (weeks)

---

## P0 — Critical

### DEBT-001: No Backup Verification
- **Category:** RELIABILITY
- **Description:** No backup scripts, no verified restore procedure. Only deployed Trinity app with potential user data.
- **Risk:** Permanent data loss if Neon database fails or migration goes wrong.
- **Effort:** LOW (verify Neon PITR takes 30 minutes)
- **Provenance:** INFERRED_PROFESSIONAL_GAP

### DEBT-002: No Error Tracking
- **Category:** OBSERVABILITY
- **Description:** No Sentry or equivalent. Deployed production app with zero error visibility.
- **Risk:** Users could be experiencing errors right now with no awareness.
- **Effort:** LOW (Sentry SDK install is ~1 hour)
- **Provenance:** INFERRED_PROFESSIONAL_GAP

### DEBT-003: Session Secret Auto-Generation
- **Category:** SECURITY
- **Description:** If SESSION_SECRET env var is not set, application auto-generates a secret. Sessions invalidated on restart.
- **Risk:** Unreliable sessions in production. Potential for weak secret.
- **Effort:** LOW (verify env var is set)
- **Provenance:** INFERRED_PROFESSIONAL_GAP

---

## P1 — Important

### DEBT-004: No RLS
- **Category:** SECURITY
- **Description:** Zero Row-Level Security policies on 35 tables. All isolation is application-level.
- **Risk:** Single server bug could expose all user data across accounts.
- **Effort:** MEDIUM (RLS policies + session variable setup)
- **Provenance:** INFERRED_PROFESSIONAL_GAP

### DEBT-005: No Rate Limiting in Production
- **Category:** SECURITY
- **Description:** Auth endpoints and AI chat endpoint have no confirmed rate limits.
- **Risk:** Brute force attacks on auth. Cost amplification on AI endpoints.
- **Effort:** LOW (express-rate-limit middleware)
- **Provenance:** INFERRED_PROFESSIONAL_GAP

### DEBT-006: Thin Test Coverage
- **Category:** QUALITY
- **Description:** 2 test files, ~24 tests. Core features (quests, AI chat, profile, Google sync) untested.
- **Risk:** Any refactoring or migration has no safety net.
- **Effort:** HIGH (comprehensive test suite is weeks of work)
- **Provenance:** IMPLEMENTATION_DEBT

### DEBT-007: No CI/CD Pipeline
- **Category:** INFRASTRUCTURE
- **Description:** No GitHub Actions. No automated build, test, lint, or deploy.
- **Risk:** Manual deployment, no pre-merge checks, no regression detection.
- **Effort:** MEDIUM (basic pipeline is a day)
- **Provenance:** IMPLEMENTATION_DEBT

### DEBT-008: OAuth Token Encryption Unknown
- **Category:** SECURITY
- **Description:** access_token and refresh_token in integrations table — schema says "encrypted" but application-level encryption unverified.
- **Risk:** If plaintext, anyone with DB access can impersonate users' Google accounts.
- **Effort:** LOW (audit, then MEDIUM if encryption needs to be added)
- **Provenance:** INFERRED_PROFESSIONAL_GAP

### DEBT-009: No CORS Configuration
- **Category:** SECURITY
- **Description:** CORS setup not documented or confirmed for production domain.
- **Risk:** Cross-origin requests may be overly permissive or incorrectly blocked.
- **Effort:** LOW
- **Provenance:** INFERRED_PROFESSIONAL_GAP

### DEBT-010: No CSRF Protection
- **Category:** SECURITY
- **Description:** No CSRF middleware confirmed. Session-based auth is vulnerable to CSRF.
- **Risk:** Cross-site request forgery attacks.
- **Effort:** LOW (csurf or similar middleware)
- **Provenance:** INFERRED_PROFESSIONAL_GAP

### DEBT-011: No CSP Headers
- **Category:** SECURITY
- **Description:** Content Security Policy not confirmed beyond Helmet defaults.
- **Risk:** XSS mitigation incomplete.
- **Effort:** LOW (Helmet CSP configuration)
- **Provenance:** INFERRED_PROFESSIONAL_GAP

---

## P2 — Should-Have

### DEBT-012: Memory Store Fallback
- **Category:** RELIABILITY
- **Description:** memorystore as fallback session store. Sessions lost on restart if PG store fails.
- **Risk:** Session loss in edge cases. Acceptable as fallback, but should alert.
- **Effort:** LOW (add alerting when fallback activates)
- **Provenance:** IMPLEMENTATION_DEBT

### DEBT-013: Stripe Stubs in Users Table
- **Category:** DATA
- **Description:** stripe_customer_id and stripe_subscription_id columns remain after Stripe removal.
- **Risk:** Schema confusion. Legacy fields accumulate.
- **Effort:** LOW (migration to drop columns, or document as reserved)
- **Provenance:** IMPLEMENTATION_DEBT

### DEBT-014: Legacy Auth Fields
- **Category:** DATA
- **Description:** email_verification_token, password_reset_token columns exist but Firebase handles these flows natively.
- **Risk:** Confusion about which auth mechanism is active.
- **Effort:** LOW (audit and document or migrate)
- **Provenance:** IMPLEMENTATION_DEBT

### DEBT-015: No Data Export/Portability
- **Category:** DATA
- **Description:** Users cannot export their data. No GDPR data portability compliance.
- **Risk:** Regulatory non-compliance if serving EU users. User lock-in perception.
- **Effort:** MEDIUM (JSON/CSV export API)
- **Provenance:** INFERRED_PROFESSIONAL_GAP

### DEBT-016: No AI Action Audit Trail
- **Category:** OBSERVABILITY
- **Description:** NOVA tool calls (createMission, updateEnergyLog, etc.) not logged in structured format.
- **Risk:** No accountability for AI actions. Cannot audit what AI did.
- **Effort:** MEDIUM (structured logging + audit table)
- **Provenance:** INFERRED_PROFESSIONAL_GAP

### DEBT-017: Legacy Profile Fields
- **Category:** DATA
- **Description:** start_stage, target_archetype, flow_style, core_motivation, setup_mission_status, primary_theme_color, future_self_summary, ai_personality_profile — marked as legacy in schema comments.
- **Risk:** Schema bloat. Confusion about which fields are active.
- **Effort:** LOW (document, then migrate in future)
- **Provenance:** IMPLEMENTATION_DEBT

### DEBT-018: No Structured Logging
- **Category:** OBSERVABILITY
- **Description:** No Winston, Pino, or similar. Console.log assumed.
- **Risk:** Cannot search, filter, or aggregate logs.
- **Effort:** MEDIUM (logging library + refactor)
- **Provenance:** INFERRED_PROFESSIONAL_GAP

### DEBT-019: No Privacy Policy / Terms of Service
- **Category:** DATA
- **Description:** Deployed app collecting personal data with no legal documents.
- **Risk:** Legal liability. User trust.
- **Effort:** MEDIUM (legal document creation)
- **Provenance:** INFERRED_PROFESSIONAL_GAP

---

## P3 — Nice-to-Have

### DEBT-020: No Uptime Monitoring
- **Category:** OBSERVABILITY
- **Description:** No external uptime checks on lyfeos.net.
- **Effort:** LOW (UptimeRobot free tier)
- **Provenance:** INFERRED_PROFESSIONAL_GAP

### DEBT-021: Replit-Specific Dependencies
- **Category:** INFRASTRUCTURE
- **Description:** @replit/vite-plugin-shadcn-theme-json, .replit config, Replit AI Integrations — platform lock-in. Will be resolved during Fly.io migration (DEC-146B-LOS-003, OPERATOR-APPROVED 2026-06-04; Fly.io is the ratified Trinity standard).
- **Effort:** MEDIUM (remove during Fly.io migration)
- **Provenance:** IMPLEMENTATION_DEBT

### DEBT-022: Base64 Image Storage
- **Category:** DATA
- **Description:** Images stored as base64 in file_data columns (mediaItems, documents). Increases DB size, slower queries.
- **Risk:** Database bloat as users upload media.
- **Effort:** HIGH (migrate to S3/R2 object storage)
- **Provenance:** IMPLEMENTATION_DEBT

---

## Summary

| Priority | Count | Categories |
|----------|-------|-----------|
| P0 | 3 | RELIABILITY, OBSERVABILITY, SECURITY |
| P1 | 8 | SECURITY (5), QUALITY (1), INFRASTRUCTURE (1), SECURITY (1) |
| P2 | 8 | DATA (4), OBSERVABILITY (2), RELIABILITY (1), DATA (1) |
| P3 | 3 | OBSERVABILITY (1), INFRASTRUCTURE (1), DATA (1) |
| **Total** | **22** | |
