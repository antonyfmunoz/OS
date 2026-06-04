# LyfeOS Test Coverage Inventory

**Phase:** 14.6B-LyfeOS
**Artifact:** 43
**Operator Approved:** false
**Allows Implementation:** false
**Provenance:** IMPLEMENTATION_DEBT

---

## Current State Summary

LyfeOS has 2 test files with approximately 24 tests total. Coverage is limited to auth endpoint validation and XP calculation logic. The vast majority of application functionality has zero automated test coverage.

---

## Test Framework

| Component | Version | Purpose |
|-----------|---------|---------|
| Vitest | 4.0.18 | Test runner and assertion library |
| Supertest | 7.2.2 | HTTP endpoint testing |

---

## Existing Test Files

### tests/api-auth.test.ts (9 tests)

Tests the authentication API endpoints via Supertest:
- Registration endpoint (valid input, duplicate email, missing fields)
- Login endpoint (valid credentials, wrong password, nonexistent user)
- Session validation (authenticated access, unauthenticated rejection)
- Logout endpoint

**Classification:** Integration tests (hit real Express routes, mock or test DB)

### tests/xp-calculations.test.ts (~15 tests)

Tests the XP and gamification calculation logic:
- Base XP award for quest completion
- Streak bonus calculations
- Level-up threshold logic
- Token distribution across categories (health/wealth/social/knowledge/creative/spiritual)
- Edge cases (zero XP, max level, streak reset)

**Classification:** Unit tests (pure function testing, no DB or HTTP)

---

## Coverage Gap Analysis

### NOT Covered — Core Features

| Module | Routes/Functions | Risk if Untested |
|--------|-----------------|------------------|
| Quest CRUD | create, read, update, delete, complete, uncomplete | HIGH — primary user feature |
| Quest recurrence | recurrence pattern parsing, next occurrence calculation | HIGH — complex logic, silent failures |
| Profile management | read, update (99 columns), onboarding state | MEDIUM — data integrity |
| Daily logs | create, read, update, date-based retrieval | MEDIUM — user reflection data |
| AI chat (NOVA) | message handling, tool dispatch, context assembly | HIGH — core differentiator |
| Vision goals | CRUD, progress tracking, milestone management | MEDIUM |
| Calendar events | CRUD, Google Calendar sync, recurrence | HIGH — integration complexity |
| Google integration | OAuth flow, token refresh, sync scheduling | HIGH — external dependency |

### NOT Covered — Secondary Features

| Module | Routes/Functions | Risk if Untested |
|--------|-----------------|------------------|
| Documents | CRUD, folder management, tagging, search | MEDIUM |
| Contacts | CRUD, relationship metadata, import/export | MEDIUM |
| Kanban boards | board/column/task CRUD, ordering, drag-drop state | LOW |
| Media management | upload, album CRUD, metadata extraction | MEDIUM |
| Spreadsheets | CRUD, cell data management | LOW |
| Canvases | CRUD, canvas data management | LOW |
| Graphs | CRUD, node/edge data | LOW |
| Templates | CRUD, system vs user templates | LOW |
| Progress trackers | CRUD, value updates | LOW |

### NOT Covered — Infrastructure

| Area | What Needs Testing | Risk if Untested |
|------|-------------------|------------------|
| Error handling | API error responses, validation errors, DB errors | HIGH |
| Auth middleware | Session validation, token expiry, role checks | HIGH |
| Firebase integration | OAuth callback, UID mapping, 2FA flow | HIGH |
| Push notifications | FCM token management, subscription, delivery | MEDIUM |
| Smart reminders | Trigger logic, recurrence, delivery scheduling | MEDIUM |
| Onboarding flow | Multi-step state machine, data persistence | MEDIUM |
| Data validation | Input sanitization, type coercion, constraints | HIGH |

### NOT Covered — Test Types

| Type | Status |
|------|--------|
| Unit tests | Partial (XP calculations only) |
| Integration tests | Partial (auth endpoints only) |
| End-to-end tests | NONE |
| Performance tests | NONE |
| Load tests | NONE |
| Security tests (injection, XSS) | NONE |
| Accessibility tests | NONE |

---

## Coverage Metrics

| Metric | Value |
|--------|-------|
| Test files | 2 |
| Total tests | ~24 |
| Estimated route coverage | ~8% (auth only out of ~50+ route groups) |
| Estimated logic coverage | ~5% (XP calc only out of dozens of business logic modules) |
| E2E coverage | 0% |
| Security test coverage | 0% |

---

## Recommended Test Expansion Priority

### P0 — Quest system and AI chat

These are the two features users interact with most. Quest CRUD has the highest data mutation surface. NOVA tool dispatch has the highest complexity and risk (AI writes user data).

### P1 — Auth hardening + Google integration

Auth tests exist but do not cover Firebase OAuth, 2FA, or token refresh. Google integration is the primary external dependency and has no test coverage.

### P2 — Full CRUD coverage

Expand to cover all remaining CRUD endpoints: documents, contacts, calendar, kanban, media, templates, progress trackers.

### P3 — E2E and security

Browser-driven E2E tests for critical flows (onboarding, quest completion, AI chat). Security-focused tests for injection, XSS, and authorization bypass.

---

## Operator Decision Required

**DEC-146B-TEST-001:** Test expansion priority

Options:
1. **Targeted P0** — quest system + NOVA tool dispatch tests before any feature additions
2. **Broad P1** — systematic CRUD test generation for all route groups
3. **Deferred** — accept current 24-test coverage until after platform migration

**Recommendation:** Option 1. The quest system is the primary user feature and NOVA tool dispatch is the highest-risk mutation path. Both can be tested with the existing Vitest + Supertest setup. Estimated effort: 2-3 sessions.
