# LyfeOS Code Source Inventory

**Phase:** 14.6B-LyfeOS
**Operator Approved:** false
**Allows Implementation:** false

---

## Repository Locations

| Location | Type | Status |
|----------|------|--------|
| `C:\dev\dev\LyfeOS` (Beast) | Full repository | 853 files, complete git history, latest commit ee1bb0f3 |
| GitHub (private repo) | Remote | Aligned with Beast, no branch divergence |
| `/opt/OS/data/repos/LYFEOS/` (VPS) | Partial snapshot | Schema, configs, tests, scripts only |
| `lyfeos.net` (Replit) | Deployed MVP | Production instance, functional |

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (snapshot files), INFERRED_PROFESSIONAL_GAP (files not in snapshot)

---

## Files Present in VPS Snapshot

### Shared Code (Data Layer)

| File | Lines | Description | Provenance |
|------|-------|-------------|------------|
| `shared/schema.ts` | 1449 | Complete Drizzle ORM schema. 35 pgTable declarations, all relations, all insert schemas, all TypeScript types. | CODE_RESOLVED_CURRENT_TRUTH |
| `shared/models/chat.ts` | 35 | Legacy/alternate chat model. Conversations + messages tables without userId. Superseded by schema.ts definitions. | CODE_RESOLVED_CURRENT_TRUTH |

### Tests

| File | Lines | Description | Provenance |
|------|-------|-------------|------------|
| `tests/api-auth.test.ts` | 128 | Integration tests for auth API (register, login, logout, session, password reset, health check). | CODE_RESOLVED_CURRENT_TRUTH |
| `tests/xp-calculations.test.ts` | 143 | Unit tests for XP/leveling math. 3-tier exponential curve verified. | CODE_RESOLVED_CURRENT_TRUTH |

### Scripts

| File | Lines | Description | Provenance |
|------|-------|-------------|------------|
| `scripts/seed-demo-user.ts` | ~50 | Demo user seeder (Alex Chen, ARCHITECT archetype). | CODE_RESOLVED_CURRENT_TRUTH |
| `scripts/capture-screenshots.ts` | unknown | Screenshot capture utility. | INFERRED_PROFESSIONAL_GAP |
| `scripts/kill-port.sh` | unknown | Port cleanup script. | INFERRED_PROFESSIONAL_GAP |

### Configuration Files

| File | Lines | Description | Provenance |
|------|-------|-------------|------------|
| `package.json` | 145 | 100+ production deps, 15 dev deps. Confirms full stack. | CODE_RESOLVED_CURRENT_TRUTH |
| `vite.config.ts` | 34 | Vite build config with React, Replit plugins, path aliases. | CODE_RESOLVED_CURRENT_TRUTH |
| `tsconfig.json` | 24 | TypeScript strict mode, ESNext, bundler resolution. | CODE_RESOLVED_CURRENT_TRUTH |
| `drizzle.config.ts` | 15 | Drizzle Kit config: schema from shared/schema.ts, postgresql dialect. | CODE_RESOLVED_CURRENT_TRUTH |
| `tailwind.config.ts` | 94 | Dark mode, CSS variable colors, glow-cyan shadow, typography plugin. | CODE_RESOLVED_CURRENT_TRUTH |
| `theme.json` | 7 | Replit shadcn theme: professional variant, cyan primary, dark, 0.5 radius. | CODE_RESOLVED_CURRENT_TRUTH |
| `vitest.config.ts` | 17 | Vitest config: node env, 15s timeout, tests/**/*.test.ts glob. | CODE_RESOLVED_CURRENT_TRUTH |
| `postcss.config.js` | 7 | PostCSS with tailwindcss + autoprefixer. | CODE_RESOLVED_CURRENT_TRUTH |
| `build.sh` | 4 | Build script: npm install && npm run build. | CODE_RESOLVED_CURRENT_TRUTH |

---

## Files NOT in Snapshot (Documented via replit.md and Beast Inventory)

### Client Directory (Frontend)

**Provenance:** INFERRED_PROFESSIONAL_GAP (documented in replit.md but files not directly inspected)

**Pages (~42 documented):**
- `client/src/pages/QuestsPage.tsx` — Missions page with Board/List/Calendar views
- `client/src/pages/DocumentVaultPage.tsx` — Data Vault (Google Drive-style organizer)
- Dashboard page (primary landing)
- AI chat page (NOVA companion interface)
- Chronilog page (daily logging)
- Profile page (character sheet / settings)
- Stat detail pages (Experience, Health, Wealth, Efficiency, Energy, Time, Attention)
- Settings pages
- Contacts page
- Kanban boards page
- Spreadsheets page
- Canvases page
- Graphs page
- Media gallery page
- Onboarding mission pages (0-7)
- Auth pages (login, register, forgot password, reset password)
- Tracker page (analytics / milestone progress)

**Custom Components (~30 documented):**
- `client/src/components/ui/rich-text-toolbar.tsx` — Inline image upload toolbar
- ObsidianMarkdown component — Markdown rendering across views
- HapticInit component — Initializes haptic/sound state on login
- Navigation components (bottom nav, sidebar)
- Quest/Mission components (board, list, calendar views)
- AI chat components (message list, input, tool display)
- Daily log components (energy, intention, data, research, reflection tabs)
- Vision goal components
- Profile/character sheet components

**UI Library Components (~58 shadcn/ui):**
- Full Radix UI primitive set (accordion, alert-dialog, avatar, checkbox, collapsible, context-menu, dialog, dropdown-menu, hover-card, label, menubar, navigation-menu, popover, progress, radio-group, scroll-area, select, separator, slider, slot, switch, tabs, toast, toggle, toggle-group, tooltip)
- All confirmed by @radix-ui/* dependencies in package.json

**Utility Modules:**
- `client/src/lib/haptics.ts` — Web Vibration API patterns (light, medium, heavy, success, level-up)
- `client/src/lib/sounds.ts` — Web Audio API synthesized sound effects

### Server Directory (Backend)

**Provenance:** INFERRED_PROFESSIONAL_GAP (documented in replit.md but files not directly inspected)

- `server/index.ts` — Express server entrypoint
- `server/routes/quests.ts` — Mission/quest CRUD + views
- `server/routes/documents.ts` — Document vault API
- `server/routes/google.ts` — Google Calendar/Tasks OAuth and sync
- `server/firebaseAdmin.ts` — Firebase Admin SDK setup
- `server/replit_integrations/chat/knowledge-base.ts` — NOVA 16-domain knowledge base
- Auth middleware (Passport.js + bcrypt + Firebase)
- Session management (express-session + connect-pg-simple)
- AI integration endpoints (Anthropic SDK)

### Other Root Files

- `generated-icon.png` — App icon
- `package-lock.json` — Dependency lockfile
- `.replit` — Replit runtime config (presumed)
- `attached_assets/` — Static assets directory (referenced in vite alias)
- `migrations/` — Drizzle migration output directory

---

## Database Schema: 35 Tables

All tables confirmed in `shared/schema.ts` (CODE_RESOLVED_CURRENT_TRUTH):

| # | Table | Purpose | Key Fields |
|---|-------|---------|------------|
| 1 | `users` | Core accounts | id, username, password, email, authProvider, firebaseUid, stripeCustomerId |
| 2 | `user_stats` | Player stats + settings | 5 stat tokens (energy/health/wealth/time/attention), XP, level, streak, aiAssistantName |
| 3 | `user_profile` | Full character sheet (~200 fields) | Archetype, identity, personality, vision, learning, health, wealth, missions 0-7 tracking |
| 4 | `user_daily_logs` | Daily reflections | Energy/intention/data/research/reflection logs, unique per user+date |
| 5 | `user_integrations` | Connected apps flags | appleHealth, googleCalendar, notion booleans |
| 6 | `quests` | Missions/tasks | Title, description, category, difficulty (S/A/B/C/D), energy/attention/time cost, XP reward, repeat, ritual, vision goal linkage |
| 7 | `ai_messages` | Legacy AI messages | sender (ai/user), content, timestamp |
| 8 | `calendar_events` | Calendar entries | title, start/end time, category, external sync fields |
| 9 | `mission_pages` | Rich mission content | slug, content, XP value, tags, event linkage |
| 10 | `contacts` | CRM-style contacts | 30+ fields including social links, trust level, relationship type |
| 11 | `spreadsheets` | JSON spreadsheet data | title, content (JSONB), category |
| 12 | `push_subscriptions` | FCM push tokens | fcmToken per user |
| 13 | `canvases` | Visual canvas boards | content (JSONB for shapes/connections) |
| 14 | `graphs` | Graph visualizations | content (JSONB for nodes/edges) |
| 15 | `folders` | Document folder tree | parentId for nesting, external sync fields |
| 16 | `documents` | Document storage | content, format, folder linkage, external sync, file attachments |
| 17 | `templates` | Document templates | content, format, category, tags |
| 18 | `integrations` | OAuth provider tokens | provider, access/refresh tokens, token expiry, scope, status |
| 19 | `progress_trackers` | Progress tracking | current/target value, unit, date range, color |
| 20 | `kanban_boards` | Kanban boards | title, description, isDefault |
| 21 | `kanban_columns` | Kanban columns | boardId, title, status, order |
| 22 | `kanban_tasks` | Kanban tasks | boardId, title, status, priority, tags |
| 23 | `media_albums` | Photo/video albums | title, coverImage, smart album rules |
| 24 | `media_items` | Photos/videos | fileName, fileType, mimeType, fileUrl/fileData, thumbnailUrl, metadata |
| 25 | `conversations` | AI chat conversations | title, userId, deletedAt (soft delete) |
| 26 | `messages` | AI chat messages | conversationId, role (user/assistant), content |
| 27 | `dismissed_knowledge` | Dismissed research items | author, sourceMaterial |
| 28 | `vision_goals` | Vision milestones | category (legacy/10year/5year/18month/90day), title, bonusXp, completed |
| 29 | `user_categories` | Custom categories | value, label, description |
| 30 | `ritual_groups` | Ritual groupings | value, label, parentGroupValue |
| 31 | `widget_states` | Dashboard widget config | states (JSONB) |
| 32 | `user_activity_events` | Activity tracking | eventType, occurredAt, metadata |
| 33 | `smart_reminders` | Reminder config | reminderType, preferredHour, preferredDays, cooldownHours |
| 34 | `mission_views` | Custom Notion-style views | viewType, filters, columns, sorting |
| 35 | `waitlist_emails` | Waitlist signups | email, referralSource |

---

## Latest Commit

- **Hash:** ee1bb0f3
- **Date:** 2026-05-20
- **Message:** "merge Development branch into main"
- **Status:** GitHub and Beast aligned, no branch divergence
