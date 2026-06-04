# LyfeOS Auth Migration Candidate Plan

Revised in Phase 14.6F to align with 18 ratified P0 decisions (2026-06-04).

**Phase:** 14.6B-LyfeOS (revised 14.6F)
**Revised:** 2026-06-04
**Artifact:** 38
**Operator Approved:** false
**Allows Implementation:** false
**Provenance:** OPEN_QUESTION_OPERATOR_DECISION_REQUIRED

---

## Ratified Decision

**DEC-146B-LOS-002 — Clerk Migration Timing** (OPERATOR-APPROVED, 2026-06-04)

Migrate LyfeOS from Passport.js+Firebase to Clerk AFTER CreatorOS proves the pattern. This is the ratified direction. The current Passport.js+Firebase system remains the active implementation and is documented below as current-state truth. Firebase documentation is preserved as historical/current-state reference.

---

## Current State

LyfeOS uses Passport.js + Firebase for authentication. This is **working and functional**. There is no security vulnerability requiring immediate migration (unlike CreatorOS which had an auth bypass).

| Component | Current | Status |
|-----------|---------|--------|
| Local auth | Passport.js + bcrypt | Working |
| OAuth | Firebase (Google/Apple/Facebook) | Working |
| Email verification | Firebase native | Working |
| Password reset | Firebase native | Working |
| 2FA | Firebase (email + phone) | Working |
| Session management | express-session + connect-pg-simple | Working |

**Classification:** CODE_RESOLVED_CURRENT_TRUTH

---

## Candidate Target: Clerk — RATIFIED DIRECTION (DEC-146B-LOS-002)

Clerk migration is the **ratified direction** for LyfeOS auth standardization (DEC-146B-LOS-002, operator-approved 2026-06-04). Migration timing: AFTER CreatorOS proves the Clerk pattern successfully.

Current implementation status:

- Clerk is **NOT** currently installed in LyfeOS (no `@clerk/` packages in dependencies)
- No Clerk migration code exists
- No Clerk configuration exists
- Clerk is the ratified target, not a current implementation truth

---

## Migration Sequencing (from Phase 14.5)

Per Phase 14.5 convergence planning:

1. **CreatorOS migrates first** — has auth bypass vulnerability, needs Clerk urgently
2. **LyfeOS migrates second** — functional auth, migration is standardization not security fix
3. **EOS migrates last** — least mature, auth is part of initial build

**Rationale:** LyfeOS auth works. Migrating to Clerk is a standardization effort to align with the Trinity platform standard. It is not a security emergency.

---

## Migration Risks

### User Data Migration
- Existing users have bcrypt-hashed passwords in PostgreSQL
- Users have Firebase UIDs linking to Firebase Auth accounts
- Migration must preserve or bridge both credential sets
- **Risk:** User lockout during migration window

### Firebase UID Mapping
- `firebase_uid` column links local users to Firebase Auth
- OAuth users authenticated entirely via Firebase
- Clerk would need to import or map these identities
- **Risk:** Orphaned OAuth users if Firebase UIDs are not properly migrated

### Session Migration
- Current sessions stored in PostgreSQL via connect-pg-simple
- Clerk uses its own session management
- All active sessions would be invalidated on cutover
- **Risk:** User confusion when forced to re-login

### 2FA Migration
- Firebase Phone Auth handles phone 2FA
- Clerk has its own 2FA implementation
- Phone numbers and 2FA state must transfer
- **Risk:** Users lose 2FA protection during migration

### Data Dependencies
- `users.auth_provider` tracks current auth method per user
- `users.email_verified` / `users.phone_verified` status must transfer
- Terms acceptance state must persist

---

## Prerequisites Before Migration

1. **CreatorOS proves the pattern** — Clerk migration on CreatorOS validates the approach
2. **UMH identity mapping defined** — how Clerk identities map to UMH user identities
3. **Backup verified** — full database backup with tested restore before any migration
4. **Rollback plan** — ability to revert to Passport.js + Firebase if Clerk migration fails
5. **User notification** — existing users informed about auth change and any required actions

---

## Alternative Consideration

Keep Passport.js + Firebase. It works. Firebase provides:
- Robust OAuth with multiple providers
- Email verification
- Password reset
- Phone 2FA
- Push notifications (FCM)

The cost of migration may exceed the benefit, especially since Firebase is already deeply integrated for notifications, verification, and 2FA beyond just auth.

---

## Operator Decision — RESOLVED

**DEC-146B-LOS-002** (formerly DEC-146B-AUTH-001): Should LyfeOS migrate from Passport.js+Firebase to Clerk?

**STATUS: RESOLVED** — Ratified 2026-06-04 (Phase 14.6E). OPERATOR-APPROVED.

**Ratified Answer:** Option 1 — Migrate after CreatorOS proves the Clerk pattern.

Original options presented:
1. **Migrate after CreatorOS proves pattern** — align with platform standard ← **SELECTED**
2. **Keep Passport.js + Firebase** — working system, Firebase deeply integrated
3. **Defer indefinitely** — revisit when there is a concrete business reason

Factors considered:
- Firebase provides more than just auth (notifications, verification, 2FA)
- Clerk migration requires Firebase features to be replaced or run in parallel
- Current auth has no known vulnerabilities
- Standardization benefit must be weighed against migration cost and risk
- CreatorOS migration validates the approach before LyfeOS commits
