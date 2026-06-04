# LyfeOS RLS and Tenant Isolation Matrix

**Phase:** 14.6B-LyfeOS
**Artifact:** 39
**Operator Approved:** false
**Allows Implementation:** false
**Provenance:** INFERRED_PROFESSIONAL_GAP

---

## Current State: NO RLS

After complete inspection of `shared/schema.ts` (1449 lines, 35 tables), **zero Row-Level Security policies** are defined. All data isolation relies on application-level middleware checks.

---

## Application-Level Isolation

All authenticated routes check `req.user.id` to scope queries:

```
WHERE user_id = $1  -- where $1 is req.user.id from session
```

This provides basic data isolation but has inherent risks:
- Any server-side bug that omits the WHERE clause exposes all user data
- Any SQL injection that bypasses Drizzle ORM could access all rows
- Direct database access (admin, migration scripts, backups) has no isolation
- NOVA AI has full access to the authenticated user's data

---

## Table Isolation Classification

### User-Scoped Tables (require RLS)

| Table | Scope Column | Cascade Delete | Risk if Leaked |
|-------|-------------|----------------|----------------|
| users | id (self) | N/A | CRITICAL — account credentials |
| user_stats | user_id | No | MEDIUM — gamification data |
| user_profile | user_id | No | CRITICAL — deeply personal data |
| user_daily_logs | user_id | No | HIGH — daily mental/emotional state |
| user_integrations | user_id | CASCADE | MEDIUM — integration flags |
| quests | user_id | No | MEDIUM — tasks and missions |
| vision_goals | user_id | No | MEDIUM — personal goals |
| ai_messages | user_id | No | HIGH — AI conversation history |
| calendar_events | user_id | No | MEDIUM — schedule data |
| mission_pages | user_id | No | LOW — content pages |
| contacts | user_id | CASCADE | HIGH — personal contact info |
| spreadsheets | user_id | CASCADE | LOW — user data |
| canvases | user_id | No | LOW — visual content |
| graphs | user_id | No | LOW — knowledge graphs |
| folders | user_id | No | LOW — folder structure |
| documents | user_id | No | MEDIUM — personal documents |
| templates | user_id | CASCADE | LOW — document templates |
| integrations | user_id | CASCADE | CRITICAL — OAuth tokens |
| progress_trackers | user_id | CASCADE | LOW — progress data |
| kanban_boards | user_id | CASCADE | LOW — board structure |
| media_albums | user_id | CASCADE | MEDIUM — photo organization |
| media_items | user_id | CASCADE | HIGH — personal photos/videos |
| conversations | user_id | CASCADE | HIGH — AI chat history |
| dismissed_knowledge | user_id | No | LOW — preference data |
| user_categories | user_id | No | LOW — category preferences |
| ritual_groups | user_id | No | LOW — ritual organization |
| widget_states | user_id | No | LOW — UI state |
| user_activity_events | user_id | No | MEDIUM — behavioral data |
| smart_reminders | user_id | No | LOW — notification preferences |
| mission_views | user_id | CASCADE | LOW — view configuration |
| push_subscriptions | user_id | No | MEDIUM — push tokens |

### Non-User-Scoped Tables

| Table | Scope | Risk if Leaked |
|-------|-------|----------------|
| kanban_columns | board_id -> kanban_boards.user_id | LOW |
| kanban_tasks | board_id -> kanban_boards.user_id | LOW |
| messages | conversation_id -> conversations.user_id | HIGH |
| waitlist_emails | N/A (public) | LOW |

---

## Risk Assessment

### Overall Risk Level: MEDIUM-HIGH

**Why MEDIUM-HIGH and not CRITICAL:**
- LyfeOS is currently single-user / low-traffic
- Drizzle ORM uses parameterized queries (SQL injection is unlikely)
- Application-level auth middleware provides baseline protection
- No known auth bypass vulnerability (unlike CreatorOS)

**Why not LOW:**
- user_profile contains deeply sensitive personal data (shadow patterns, beliefs, financial data, trauma patterns)
- integrations table stores OAuth tokens (potentially unencrypted)
- No defense-in-depth: one application bug exposes everything
- As user base grows, attack surface increases
- NOVA AI has full access to all user data — no AI permission tiers

---

## Required RLS Policies

For each user-scoped table, the following policy pattern is needed:

```sql
ALTER TABLE <table> ENABLE ROW LEVEL SECURITY;
CREATE POLICY <table>_user_isolation ON <table>
  USING (user_id = current_setting('app.current_user_id')::integer);
```

For indirectly scoped tables (kanban_columns, kanban_tasks, messages):

```sql
CREATE POLICY kanban_columns_user_isolation ON kanban_columns
  USING (board_id IN (SELECT id FROM kanban_boards WHERE user_id = current_setting('app.current_user_id')::integer));
```

### Application Changes Required
1. Set `app.current_user_id` session variable on each request
2. Use a database role with RLS enforced (not superuser)
3. Admin/migration operations use a separate superuser connection

---

## Operator Decision Required

**DEC-146B-RLS-001:** RLS implementation priority

Options:
1. **P0 — Before any user growth** — implement RLS before marketing/growth efforts
2. **P1 — With production hardening** — bundle with backup verification and error tracking
3. **P2 — After platform migration** — implement when moving from Replit to Fly.io
4. **Defer** — accept application-level isolation risk for now

**Recommendation:** P1 — implement alongside other production hardening. The current single-user state reduces immediate risk, but RLS should be in place before any user acquisition push.
