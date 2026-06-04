# LyfeOS Navigation Shell Canon

**Phase:** 14.6B-LyfeOS
**Artifact:** 14 of 30
**operator_approved:** false
**allows_implementation:** false
**Date:** 2026-06-03

---

## Purpose

Canonical documentation of the LyfeOS navigation architecture, including primary tabs, secondary routes, mobile navigation, sidebar structure, root layout, and protected route enforcement.

---

## Primary Navigation (5 Tabs)

| Tab | Route | Component | Provenance |
|-----|-------|-----------|------------|
| Dashboard | `/` | `DashboardPage.tsx` | CODE_RESOLVED_CURRENT_TRUTH |
| Missions | `/missions` | `QuestsPage.tsx` | CODE_RESOLVED_CURRENT_TRUTH |
| AI | `/ai` | `AIPage.tsx` | CODE_RESOLVED_CURRENT_TRUTH |
| Chronilog | `/chronilog` | `ChronilogPage.tsx` | CODE_RESOLVED_CURRENT_TRUTH |
| Profile | `/profile` | `ProfilePage.tsx` | CODE_RESOLVED_CURRENT_TRUTH |

### Critical Correction: Systems is NOT a Primary Tab

**Provenance: SOURCE_PRESERVED_TRUTH (operator correction)**

"Systems" was listed as a primary navigation tab in early documentation and the Phase 14.5 convergence plan. The operator has corrected this: Systems is NOT a primary navigation tab. Systems-like functionality is distributed across secondary modules and routes. The primary navigation consists of exactly five tabs listed above.

---

## Secondary Routes

| Route | Component | Description | Provenance |
|-------|-----------|-------------|------------|
| `/document-vault` | `DocumentVaultPage.tsx` | Google Drive-style data organizer with folders, documents, templates, media | CODE_RESOLVED_CURRENT_TRUTH |
| `/tracker` | `TrackerPage.tsx` | Milestone analytics, vision goal progress tracking | CODE_RESOLVED_CURRENT_TRUTH |
| `/settings` | `SettingsPage.tsx` | Profile settings, integrations, display preferences | CODE_RESOLVED_CURRENT_TRUTH |
| `/contacts` | `ContactsPage.tsx` | CRM/rolodex — personal and professional contacts | CODE_RESOLVED_CURRENT_TRUTH |
| `/kanban` | `KanbanPage.tsx` | Project boards with columns and tasks | CODE_RESOLVED_CURRENT_TRUTH |
| `/spreadsheets` | `SpreadsheetsPage.tsx` | User spreadsheets with JSON content storage | CODE_RESOLVED_CURRENT_TRUTH |
| `/canvases` | `CanvasesPage.tsx` | Whiteboard/canvas drawing tool | CODE_RESOLVED_CURRENT_TRUTH |
| `/graphs` | `GraphsPage.tsx` | Node-link diagrams and visualizations | CODE_RESOLVED_CURRENT_TRUTH |
| `/media` | `MediaPage.tsx` | Photos/videos organized in albums | CODE_RESOLVED_CURRENT_TRUTH |

---

## Special Routes

| Route | Component | Description | Provenance |
|-------|-----------|-------------|------------|
| `/login` | `LoginPage.tsx` | Authentication entry — email/password + OAuth | CODE_RESOLVED_CURRENT_TRUTH |
| `/register` | `RegisterPage.tsx` | Account creation with terms acceptance | CODE_RESOLVED_CURRENT_TRUTH |
| `/onboarding` | `OnboardingPage.tsx` | 8-mission character creation wizard | CODE_RESOLVED_CURRENT_TRUTH |
| `/stat/:statType` | `StatDetailPage.tsx` | Per-stat detail view (Experience, Health, Wealth, Efficiency, Energy, Time, Attention) | CODE_RESOLVED_CURRENT_TRUTH |

---

## Mobile Navigation (MobileNav.tsx)

**Provenance: CODE_RESOLVED_CURRENT_TRUTH**

- Bottom navigation bar visible on mobile viewport
- Contains the 5 primary tabs: Dashboard, Missions, AI, Chronilog, Profile
- Icon-based with labels
- Highlights active route
- Fixed to bottom of screen
- Hides on scroll (implementation-dependent)

---

## Sidebar (Sidebar.tsx)

**Provenance: CODE_RESOLVED_CURRENT_TRUTH**

- Desktop-only left sidebar
- Contains primary navigation links (same 5 tabs)
- Secondary routes accessible from sidebar sub-menu or navigation drawer
- User avatar and level display at top
- Collapse/expand toggle
- Dark theme with neon accent highlights matching Solo Leveling aesthetic

---

## Root Layout (RootLayout.tsx)

**Provenance: CODE_RESOLVED_CURRENT_TRUTH**

- Wraps all authenticated pages
- Renders Sidebar (desktop) or MobileNav (mobile) based on viewport
- Contains main content area with responsive padding
- Manages global state providers (auth context, theme context, query client)
- Renders notification/toast overlay
- Does NOT render on `/login`, `/register` routes (those are standalone)

---

## Protected Routes

**Provenance: CODE_RESOLVED_CURRENT_TRUTH**

- All routes except `/login`, `/register`, and `/waitlist` require authentication
- Auth check: session-based via express-session on server, auth context on client
- Unauthenticated access redirects to `/login`
- Onboarding completion is checked: incomplete onboarding redirects to `/onboarding`
- Firebase OAuth tokens validated server-side via Firebase Admin SDK

### Route Protection Logic

```
1. User hits any route
2. Client checks auth context (loaded from /api/user session endpoint)
3. If not authenticated -> redirect to /login
4. If authenticated but onboarding not complete -> redirect to /onboarding
5. If authenticated and onboarding complete -> render requested route
```

---

## Navigation Architecture Diagram

```
RootLayout
  |
  +-- Sidebar (desktop) / MobileNav (mobile)
  |     |
  |     +-- Dashboard (/)
  |     +-- Missions (/missions)
  |     +-- AI (/ai)
  |     +-- Chronilog (/chronilog)
  |     +-- Profile (/profile)
  |
  +-- Main Content Area
        |
        +-- Primary pages (above)
        +-- Secondary pages (document-vault, tracker, settings, contacts, kanban, spreadsheets, canvases, graphs, media)
        +-- Special pages (stat/:statType)
```

---

## Open Questions

| ID | Question | Classification |
|----|----------|----------------|
| NAV-001 | Should secondary routes be accessible from sidebar or only from within primary pages? | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| NAV-002 | Is there a planned hamburger menu or navigation drawer for secondary routes on mobile? | OPEN_QUESTION_OPERATOR_DECISION_REQUIRED |
| NAV-003 | Should onboarding redirect be enforced client-side only or also server-side on API routes? | INFERRED_PROFESSIONAL_GAP |
