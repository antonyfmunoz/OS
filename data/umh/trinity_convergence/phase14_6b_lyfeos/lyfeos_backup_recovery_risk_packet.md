# LyfeOS Backup and Recovery Risk Packet

**Phase:** 14.6B-LyfeOS
**Artifact:** 40
**Operator Approved:** false
**Allows Implementation:** false
**Provenance:** INFERRED_PROFESSIONAL_GAP

---

## Critical Finding

LyfeOS is the **ONLY deployed Trinity app with real user data**, and there is **NO verified backup or recovery strategy**.

**Risk Level:** P0 CRITICAL

---

## Current State

| Item | Status | Provenance |
|------|--------|------------|
| Backup scripts in codebase | NONE found | CODE_RESOLVED_CURRENT_TRUTH |
| Backup configuration files | NONE found | CODE_RESOLVED_CURRENT_TRUTH |
| Recovery procedures documented | NONE found | CODE_RESOLVED_CURRENT_TRUTH |
| Automated backup verification | NONE | CODE_RESOLVED_CURRENT_TRUTH |
| Backup restore test performed | NO evidence | INFERRED_PROFESSIONAL_GAP |
| Data export/portability | NOT implemented | INFERRED_PROFESSIONAL_GAP |

---

## Database Provider: Neon Postgres

Neon Postgres (serverless) provides built-in capabilities:

### What Neon Provides (Provider-Level)
- **Point-in-Time Recovery (PITR):** Neon supports PITR with branching
- **Branching:** Create database branches (copies) for testing/recovery
- **Autoscaling:** Compute scales to zero, storage is persistent
- **Backup retention:** Depends on Neon plan (Free: 7 days, Pro: 30 days, custom for higher tiers)

### What Is NOT Verified
1. Which Neon plan LyfeOS is on (Free vs Pro vs Scale)
2. Whether PITR is actually enabled for this project
3. Whether anyone has tested a restore from Neon PITR
4. Whether Neon's backup retention meets requirements
5. Whether the database has any data at all (could be empty if users haven't registered)

---

## Data at Risk

If the database is lost without recovery capability:

| Data Type | Tables | Recoverability |
|-----------|--------|---------------|
| User accounts | users | LOST — passwords, email, Firebase UIDs |
| Personal profiles | user_profile | LOST — 99 columns of deeply personal data |
| Missions/quests | quests | LOST — all task history |
| Vision goals | vision_goals | LOST — long-term goal tracking |
| Daily logs | user_daily_logs | LOST — daily reflection history |
| AI conversations | conversations, messages | LOST — all NOVA interaction history |
| Contacts | contacts | LOST — personal rolodex |
| Documents | documents, folders | LOST — all user documents |
| Calendar events | calendar_events | PARTIALLY RECOVERABLE — Google Calendar synced events can be re-imported |
| Media | media_items, media_albums | LOST — if stored as base64 in DB |
| Stats/XP | user_stats | LOST — gamification progress |
| Integration tokens | integrations | LOST — must re-authenticate Google |

---

## Required Actions Before Any Migration or Significant Change

### 1. Verify Neon PITR Capability (P0)
- Log into Neon console
- Confirm which plan is active
- Confirm PITR is enabled
- Identify backup retention period
- **Owner:** Operator
- **Classification:** INFERRED_PROFESSIONAL_GAP

### 2. Test Restore Procedure (P0)
- Create a Neon branch from PITR
- Verify branch contains expected data
- Verify application can connect to branch
- Document exact steps
- **Owner:** Operator
- **Classification:** INFERRED_PROFESSIONAL_GAP

### 3. Document Recovery Runbook (P1)
- Step-by-step recovery from Neon PITR
- Step-by-step recovery from manual dump (if implemented)
- Contact information for Neon support
- RTO (Recovery Time Objective) and RPO (Recovery Point Objective) targets
- **Owner:** Operator + Developer
- **Classification:** INFERRED_PROFESSIONAL_GAP

### 4. Implement Automated Backup Verification (P1)
- Scheduled pg_dump to external storage (S3, Cloudflare R2, etc.)
- Verification that dump is valid (pg_restore --dry-run)
- Alert if backup fails
- **Owner:** Developer
- **Classification:** IMPLEMENTATION_DEBT

### 5. Confirm Data Exists in Production (P0)
- Connect to production Neon database
- Verify users table has rows
- Verify user_profile has data
- Verify quests have entries
- If empty: lower urgency (no data to lose)
- If populated: backup verification becomes urgent
- **Owner:** Operator
- **Classification:** INFERRED_PROFESSIONAL_GAP

---

## Threat Scenarios

### Scenario 1: Accidental Schema Migration
A Drizzle migration drops or alters a table incorrectly. Without backup:
- User data is permanently lost
- No rollback possible
- **Mitigation:** Always take Neon branch before migrations

### Scenario 2: Neon Free Tier Expiry
If on free tier and Neon changes terms or the project is inactive too long:
- Database could be suspended or deleted
- **Mitigation:** Verify plan, set up external backup

### Scenario 3: Replit Deployment Failure
Replit platform has an outage or the project is deleted:
- Application is lost but database persists (Neon is separate)
- **Mitigation:** Code is in GitHub (recoverable). Database recovery depends on Neon.

### Scenario 4: Security Breach
Attacker gains database access:
- All user data exposed (no RLS)
- OAuth tokens potentially exposed (encryption unknown)
- **Mitigation:** RLS, token encryption, regular credential rotation

---

## Operator Decision Required

**DEC-146B-BACKUP-001:** Backup strategy priority

Options:
1. **Immediate (P0):** Verify Neon PITR and test restore NOW before any other work
2. **Bundled (P1):** Include in production hardening phase alongside RLS and error tracking
3. **Deferred:** Accept risk until platform migration to Fly.io

**Recommendation:** Option 1 — Immediate. This is the only deployed app with potential user data. Verifying that Neon PITR works takes 30 minutes and eliminates the highest-severity risk on the board.
