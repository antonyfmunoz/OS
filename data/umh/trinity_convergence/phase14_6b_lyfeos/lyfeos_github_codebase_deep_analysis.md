# LyfeOS GitHub Codebase Deep Analysis

**Phase:** 14.6B-LyfeOS
**Operator Approved:** false
**Allows Implementation:** false

---

## 1. Repository Structure

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

Monorepo architecture with three primary directories:

```
LyfeOS/
  client/          — React 18 frontend (SPA)
    src/
      pages/       — Route-level page components
      components/  — Reusable UI components
      lib/         — Utility modules (haptics, sounds, etc.)
  server/          — Express backend (API + auth + AI)
    routes/        — RESTful API route files
    replit_integrations/ — AI integration layer
    firebaseAdmin.ts     — Firebase Admin SDK
  shared/          — Shared code (schema, models, types)
    schema.ts      — Drizzle ORM schema (1449 lines, 35 tables)
    models/        — Additional model definitions
  tests/           — Test files (vitest)
  scripts/         — Operational scripts
  migrations/      — Drizzle migration output
  attached_assets/ — Static assets
  dist/            — Build output
```

**Evidence:** tsconfig.json includes `client/src/**/*`, `shared/**/*`, `server/**/*`. Vite config sets root to `client/`, build output to `dist/public`.

---

## 2. Frontend Architecture

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (package.json, configs) + SOURCE_PRESERVED_TRUTH (replit.md)

- **Framework:** React 18.3.1 with TypeScript 5.6.3
- **Build:** Vite 5.4.21 with React plugin
- **Routing:** Wouter 3.3.5 (lightweight React router)
- **State Management:** TanStack React Query 5.60.5 + React Context API
- **UI Library:** shadcn/ui built on Radix UI primitives (25+ Radix packages in deps)
- **Styling:** Tailwind CSS 3.4.14, dark-only theme, CSS variable-based color system
- **Animation:** Framer Motion 11.13.1
- **Charts:** Recharts 2.13.0
- **Drag & Drop:** react-dnd 16.0.1 + react-beautiful-dnd 13.1.1 (both present)
- **Forms:** React Hook Form 7.53.1 + Zod validation
- **Markdown:** react-markdown 10.1.0 + remark-gfm + remark-math + rehype-katex
- **Icons:** Lucide React 0.453.0 + React Icons 5.4.0

**Theme:** Professional variant, primary cyan hsl(188, 100%, 50%), dark appearance, 0.5 border radius. "Solo Leveling" anime-inspired aesthetic per replit.md.

---

## 3. Backend Architecture

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (package.json) + SOURCE_PRESERVED_TRUTH (replit.md)

- **Runtime:** Node.js with Express 4.21.2
- **Language:** TypeScript, compiled via tsx (dev) and esbuild (production)
- **API Style:** RESTful JSON API
- **ORM:** Drizzle ORM 0.39.1 with Drizzle Zod 0.7.1 for schema validation
- **Database Driver:** @neondatabase/serverless 0.10.4
- **Sessions:** express-session 1.18.1 + connect-pg-simple 10.0.0 (Postgres session store)
- **Security:** Helmet 8.1.0 (security headers), compression 1.8.1
- **AI SDKs:** @anthropic-ai/sdk 0.72.1, openai 4.96.0
- **Web Scraping:** puppeteer-core 24.37.2, cheerio 1.2.0, turndown 7.2.2 (HTML to markdown)
- **File Processing:** adm-zip 0.5.16, multer 2.0.2
- **WebSocket:** ws 8.18.0
- **Build:** esbuild bundles server/index.ts to dist/index.js for production

---

## 4. Routing and Navigation

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (operator correction) + SOURCE_PRESERVED_TRUTH (replit.md)

**Primary Navigation (5 items):**
1. **Dashboard** — Main landing page, widget-based overview
2. **Missions** — Quest/task management with Board/List/Calendar views
3. **AI** — NOVA AI companion chat interface
4. **Chronilog** — Daily logging (energy, intention, data, research, reflection)
5. **Profile** — Character sheet, settings, integrations

**Secondary Navigation:**
- Document Vault (`/document-vault`) — Google Drive-style file manager
- Tracker — Progress tracking and milestone analytics
- Settings — System preferences
- Contacts — CRM-style contact management
- Kanban — Board-based project management
- Spreadsheets — JSON-based spreadsheet tool
- Canvases — Visual diagramming
- Graphs — Node/edge visualization
- Media — Photo/video gallery with albums

**Operator Correction:** Prior artifacts listed "Systems" as a primary nav item. Current code truth confirms Profile is the 5th primary tab, not Systems.

---

## 5. Database Architecture

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

- **Provider:** Neon PostgreSQL (serverless)
- **ORM:** Drizzle ORM with drizzle-zod for insert schema validation
- **Schema File:** `shared/schema.ts` (1449 lines)
- **Table Count:** 35 tables (exact, verified by grep)
- **Migration Tool:** Drizzle Kit (`drizzle-kit push`)
- **Connection:** DATABASE_URL environment variable

**Key Architectural Decisions:**
- All IDs are serial integers (not UUIDs)
- All user-scoped tables have `userId` foreign key to `users.id`
- JSONB used extensively for flexible data (archetype scores, linked items, widget states, smart album rules, etc.)
- Soft deletes via `deletedAt` timestamps on conversations, quests, folders, documents
- External sync tracking via `externalId`/`externalSource` fields on quests, calendar events, folders, documents
- Unique constraints: user+date on daily logs, user on user_stats/user_profile/widget_states

---

## 6. Authentication Architecture

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (package.json, schema.ts) + SOURCE_PRESERVED_TRUTH (replit.md)

**Dual Auth System:**
1. **Local Auth:** Passport.js 0.7.0 + passport-local 1.0.0 + bcrypt 6.0.0
   - Username/password registration and login
   - bcrypt password hashing (10 rounds per seed script)
   - Session-based (express-session + Postgres session store)
2. **Firebase Auth:** firebase 11.6.1 + firebase-admin 13.6.1
   - Google/Apple/Facebook OAuth
   - Email verification (Firebase Auth native)
   - Password reset (Firebase Auth native)
   - 2FA via email (Firebase email verification) and phone (Firebase Phone Auth)
   - Server creates Firebase Auth users alongside database users
   - Reverse proxy (`/__/auth/*` -> Firebase) to avoid third-party cookie blocking

**Schema Evidence:**
- `users.authProvider` — default "email", options: "email", "google", "apple", "facebook"
- `users.firebaseUid` — Firebase UID for OAuth users
- `users.password` — bcrypt hash for local auth
- `users.twoFactorEnabled`, `users.twoFactorEmailCode/Expiry`, `users.twoFactorPhoneCode/Expiry`
- `users.emailVerified`, `users.emailVerificationToken/Expiry`
- `users.passwordResetToken/Expiry`

**Clerk Status:** No @clerk/* dependency in package.json. Clerk is a FUTURE migration target, not current implementation.

---

## 7. AI Companion Architecture (NOVA)

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (package.json, schema.ts) + SOURCE_PRESERVED_TRUTH (replit.md)

**Identity:**
- Default name: "NOVA" (stored in `userStats.aiAssistantName`, default "NOVA")
- User-renamable (field is editable, not a system constant)
- Roles: Advisor, Coach, Executive Assistant

**AI Models:**
- Anthropic SDK: @anthropic-ai/sdk 0.72.1 (Haiku for simple, Sonnet for complex)
- OpenAI SDK: openai 4.96.0 (presence in deps, usage scope unclear)
- Smart routing: upgrades from Haiku to Sonnet for tool use, complex queries, or images

**Data Ingestion (Salience Engine):**
NOVA has full read access to: user profile, stats, missions, daily logs, vision milestones, calendar, conversation history.

**AI Tools:**
1. Web search
2. Web page reading (puppeteer-core + cheerio + turndown)
3. Vision goal creation
4. Batch mission creation
5. Uncomplete missions (mark incomplete)
6. `lookup_knowledge_base` — active knowledge retrieval

**Knowledge Base:**
16 domains: philosophy, sleep, exercise, nutrition, psychology, relationships, finance, learning, productivity, crisis management, modern challenges, breathwork, advanced nutrition, functional fitness, biomarkers, supplementation. Auto-topic detection injects relevant knowledge into system prompt.

**Vision/Image Analysis:**
Users attach images in chat. NOVA also auto-extracts inline images from mission/goal/daily log descriptions. Images sent as base64 vision content blocks (max 5 most recent).

**Chat Data Model:**
- `conversations` table: userId, title, deletedAt (soft delete)
- `messages` table: conversationId, role (user/assistant), content
- Legacy `ai_messages` table also exists (sender: ai/user)

---

## 8. Gamification System

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (schema.ts, xp-calculations.test.ts) + SOURCE_PRESERVED_TRUTH (replit.md)

### 8a. Five Stat Tokens (0-100 scale)

| Token | Current Field | Max Field | Default |
|-------|---------------|-----------|---------|
| Energy | `energyPointsCurrent` | `energyPointsMax` | 100/100 |
| Health | `healthPointsCurrent` | `healthPointsMax` | 100/100 |
| Wealth | `wealthTokensCurrent` | `wealthTokensMax` | 100/100 |
| Time | `timeTokensCurrent` | `timeTokensMax` | 100/100 |
| Attention | `attentionTokensCurrent` | `attentionTokensMax` | 100/100 |

### 8b. XP and Leveling

- **Base:** 1000 XP for level 1
- **Tier 1 (levels 1-10):** `1000 * 1.0372^(level-1)` multiplier
- **Tier 2 (levels 11-50):** `tier1_cap * 1.0572^(level-10)` multiplier
- **Tier 3 (levels 51-100):** `tier2_cap * 1.0872^(level-50)` multiplier
- **Level cap:** 100
- **Total XP tracking:** `userProfile.totalXP` field
- **Per-level tracking:** `userStats.experienceCurrent` / `userStats.experienceMax`
- **Streaks:** `userStats.streakDays` + `userStats.lastActiveDate`
- **Efficiency:** `userStats.efficiencyScore`

### 8c. Mission Difficulty Ranks

S, A, B, C, D (S highest, D default)

### 8d. Mission Resource Costs

Each quest has: `energyCost` (default 1), `attentionCost` (default 0), `timeCost` (default 0)

### 8e. Mission XP Rewards

`experienceReward` per quest (default 10 XP)

### 8f. Stat Detail Pages

Dedicated pages for: Experience, Health, Wealth, Efficiency, Energy, Time, Attention. Real-time data, recharts visualizations, time range selectors, AI-powered insights.

---

## 9. Onboarding System

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (schema.ts) + SOURCE_PRESERVED_TRUTH (replit.md)

- **Tracking:** `userProfile.onboardingMission` (integer, default 0, range 0-7)
- **Step tracking:** `userProfile.onboardingStep` (integer, default 0)
- **Completion:** `userProfile.onboardingCompleted` (boolean, default false)
- **Completed missions:** `userProfile.completedOnboardingMissions` (integer array)
- **Completed tutorials:** `userProfile.completedTutorials` (text array)

**8 Onboarding Missions:**
- Mission 0: Access & Quickstart (age, birthday, location, timezone)
- Mission 1: Archetype Calibration (54-question assessment per replit.md, 6 archetypes)
- Missions 2-7: Progressive onboarding through identity, personality, vision, learning, health, wealth sections

---

## 10. Archetype System

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (schema.ts)

- **6 Archetypes:** Warrior, Architect, Creator, Monarch, Oracle, Alchemist
- **Fields:** `archetypePrimary`, `archetypeSecondary`, `archetypeShadow`
- **Scores:** `archetypeScores` (JSONB: `{ warrior: X, architect: X, creator: X, monarch: X, oracle: X, alchemist: X }`)
- **54-question calibration assessment** (documented in replit.md)

---

## 11. Profile/Character Sheet

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (schema.ts)

The `user_profile` table is the most extensive single table with ~200 fields organized into sections:

1. **Mission 0:** age_range, birthday, location, timezone
2. **Mission 1:** Archetype calibration results
3. **Identity:** Primary instincts, key drivers, shadow distortions
4. **Personality:** Beliefs, values, standards, patterns, habits, strengths, weaknesses
5. **Vision & Goals:** Life stage, 90-day/18-month/5-year/10-year visions, legacy metric, mortality insights
6. **Learning & Skills:** Learning style, deep dives, skill stacking pyramid, practice cadence
7. **Projects & Creations:** Current projects, active phase, primary craft
8. **Body & Health:** Physical metrics, fitness, nutrition, health vitality, injuries
9. **Wealth & Work:** Career, ventures, financial position, weekly capacity, resources
10. **Performance & Contribution:** Collaboration style, role orientation, decision making, stress response
11. **Style & Expression:** Aesthetic, signature expression, creative outlets
12. **History & Roots:** Shadow patterns, upbringing, cultural context, key experiences
13. **Systems & Rituals:** Ideal day/week, morning/evening rituals, boundaries
14. **Emotions & Coping:** Emotions to cultivate, coping practices, belief system, instincts
15. **Character Affirmation:** AI-generated third-person narrative
16. **Display Settings:** Blue light filter, haptic feedback, sound effects
17. **Legacy Fields:** startStage, targetArchetype, setupMissionStatus, etc.

---

## 12. Daily Logging (Chronilog)

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (schema.ts)

`user_daily_logs` table with unique constraint on user+date:

- **Energy Log:** wakeTime, sleepTime, mentalState (1-10), physicalState (1-10), emotionalState (1-10)
- **Intention Log:** gratitude, tomorrowGoals, annualGoals, thoughts
- **Data Log:** contentConsumed, research (legacy), todoIdeas, todosConverted
- **Research Log:** sourceAuthor, sourceMaterial, researchNote, revisionNote, executionNote, researchEntries (JSONB array)
- **Reflection Log:** wentWell, couldBeBetter, learned (customizable prompts)
- **Meta:** yesterdayXp, todayPrimaryMission, optionalBoostsShown, boostsData

---

## 13. Mission/Quest System

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (schema.ts) + SOURCE_PRESERVED_TRUTH (replit.md)

`quests` table with rich fields:

- **Core:** title, description, category, completed, completedAt
- **Gamification:** energyCost, attentionCost, timeCost, experienceReward, difficulty (S/A/B/C/D)
- **Scheduling:** startDate/Time, endDate/Time, dueDate, allDay, timezone
- **Repeat:** repeatFrequency (hourly/daily/weekly/monthly/yearly), repeatInterval, repeatDays, repeatEndDate, parentRitualId
- **Ritual:** isRitualized, ritualGroup
- **Vision:** visionGoalId (FK to vision_goals)
- **External:** externalId, externalSource (Google sync)
- **Organization:** sortOrder, linkedItems (JSONB), location, url, attendees (JSONB)
- **Views:** viewId, viewColumn (for custom board views), missionStatus
- **Soft Delete:** deletedAt

**Mission Views (Notion-style):**
- `mission_views` table: viewType, filters (JSONB), columns (JSONB), sortBy, sortDirection
- 3 default view modes: Board (vertical kanban), List (chronological), Calendar (Google-style)
- Users can create custom views with filters and column configs

---

## 14. Vision Goals System

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (schema.ts)

`vision_goals` table:
- **Categories:** legacy, 10year, 5year, 18month, 90day (hierarchical time horizons)
- **Fields:** title, description, rewardText, bonusXp, completed, completedAt
- **Linkage:** Quests link to vision goals via `visionGoalId` FK
- **Organization:** displayOrder, disconnectedMissionIds

---

## 15. Google Integration

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (package.json, schema.ts) + SOURCE_PRESERVED_TRUTH (replit.md)

- **SDK:** googleapis 171.4.0
- **Calendar:** Read/write sync with deduplication (externalId matching + fuzzy title+date+time)
- **Tasks:** Read-only import as missions with dedup
- **OAuth Flow:** Server-side token exchange and storage in `integrations` table
- **Token Storage:** access_token, refresh_token, tokenExpiry in `integrations` table
- **Status Tracking:** `userIntegrations.googleCalendarConnected` boolean
- **Required Secrets:** GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET

---

## 16. Document Vault

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (schema.ts) + SOURCE_PRESERVED_TRUTH (replit.md)

- **Tables:** `folders` (nested via parentId) + `documents` + `templates`
- **Features:** Markdown editing, file upload (images, videos, PDFs), folder nesting
- **Sync:** Bidirectional Google Drive/Docs, Obsidian import/export (.md/.zip), Evernote import/export (.enex)
- **Source Tracking:** source field (local/google/obsidian/evernote), externalId, externalUrl, lastSyncedAt
- **Views:** List and Grid/Gallery modes
- **Quick Filters:** All, Documents, Images, Videos, PDFs

---

## 17. Contacts System

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (schema.ts)

`contacts` table with 30+ fields: name, alias, email, phone, company, jobTitle, department, industry, category, relationshipType, notes, favorite, lastContacted, birthday, address, city, country, timezone, linkedin, twitter, instagram, website, howMet, trustLevel, strengths, contactFrequency.

CRM-like functionality for personal relationship management.

---

## 18. Kanban System

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (schema.ts)

3-table normalized design:
- `kanban_boards`: userId, title, description, isDefault
- `kanban_columns`: boardId, title, status, order
- `kanban_tasks`: boardId, title, description, status, priority (low/medium/high), dates, tags

---

## 19. Media System

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (schema.ts) + SOURCE_PRESERVED_TRUTH (replit.md)

- `media_albums`: title, coverImageId, smart album rules (JSONB)
- `media_items`: fileName, fileType (image/video), mimeType, fileUrl/fileData/filePath, thumbnailUrl, metadata, location (JSONB), dateTaken, size
- **Inline Images:** RichTextToolbar component for inline image upload across all text fields
- **Storage:** base64 in mediaItems table (no S3/external storage confirmed)

---

## 20. Spreadsheet System

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (schema.ts)

`spreadsheets` table: userId, title, description, content (JSONB), favorite, category. JSON-based spreadsheet storage.

---

## 21. Canvas System

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (schema.ts)

`canvases` table: userId, title, description, content (JSONB for shapes, connections, text), favorite, category.

---

## 22. Graph System

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (schema.ts)

`graphs` table: userId, title, description, content (JSONB for nodes, edges, styling), favorite, category.

---

## 23. Progress Tracker

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (schema.ts)

`progress_trackers` table: userId, title, description, category, currentValue, targetValue, unit, startDate, endDate, color, favorite.

---

## 24. Smart Reminders

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (schema.ts)

`smart_reminders` table: userId, reminderType, enabled, source, preferredHour, preferredDays (array), cooldownHours, lastSentAt. Unique per user+reminderType.

---

## 25. User Activity Events

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (schema.ts)

`user_activity_events` table: userId, eventType, occurredAt, metadata (JSONB). Generic event tracking for analytics.

---

## 26. Widget States

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (schema.ts)

`widget_states` table: userId (unique), states (JSONB). Dashboard widget configuration persistence.

---

## 27. Waitlist

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (schema.ts)

`waitlist_emails` table: email (unique), referralSource. Pre-launch email collection.

---

## 28. PWA and Notifications

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (schema.ts) + SOURCE_PRESERVED_TRUTH (replit.md)

- `push_subscriptions` table: userId, fcmToken
- Firebase Cloud Messaging for push notifications
- PWA: manifest, service worker for offline caching, install prompt
- Haptic feedback: Web Vibration API with patterns (light, medium, heavy, success, level-up, notification)
- Sound effects: Web Audio API synthesized sounds (no external audio files)

---

## 29. Deployment Architecture

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (build.sh, package.json) + SOURCE_PRESERVED_TRUTH (replit.md)

- **Current Host:** Replit (deployed at lyfeos.net)
- **Build:** `npm install && npm run build` (Vite frontend + esbuild backend)
- **Start:** `NODE_ENV=production node dist/index.js`
- **Health Check:** `/api/health` endpoint (confirmed by test)
- **Database:** Neon PostgreSQL (serverless, requires DATABASE_URL)
- **Sessions:** Postgres-backed via connect-pg-simple (or memorystore 1.6.7 fallback)

---

## 30. Payment Architecture

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (schema.ts) + SOURCE_PRESERVED_TRUTH (replit.md)

- `users.stripeCustomerId` and `users.stripeSubscriptionId` fields exist
- Stripe integration REMOVED (stubbed endpoints preserved per replit.md)
- Subscription page UI kept intact
- No active payment processing

---

## 31. Test Architecture

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

- **Framework:** Vitest 4.0.18
- **Config:** Node environment, globals enabled, 15s timeout
- **Test Files:** 2 total
  - `tests/api-auth.test.ts` (128 lines, 10 test cases)
  - `tests/xp-calculations.test.ts` (143 lines, 11 test cases)
- **Total Test Cases:** 21
- **Coverage:** Auth API and XP math only. No frontend tests, no integration tests beyond auth.
- **Gap:** Major test coverage gap for a 35-table, multi-feature application.

---

## 32. Security Architecture

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (package.json) + SOURCE_PRESERVED_TRUTH (replit.md) + INFERRED_PROFESSIONAL_GAP

- **Confirmed:** Helmet 8.1.0 (security headers), bcrypt 6.0.0 (password hashing), Zod input validation, Drizzle parameterized queries
- **NOT Confirmed:** RLS (no evidence in schema.ts), CSRF protection, CSP configuration, rate limiting implementation
- **Documented but unverified in snapshot:** Rate limiting mentioned in replit.md

---

## 33. Error Tracking and Observability

**Provenance:** INFERRED_PROFESSIONAL_GAP

- **No error tracking service** (no Sentry, no PostHog error tracking in deps)
- **No structured logging library** (no Winston, no Pino in deps)
- **No analytics** (no PostHog, no Mixpanel in deps)
- **Replit runtime error overlay** exists for development only

---

## 34. Backup and Recovery

**Provenance:** INFERRED_PROFESSIONAL_GAP

- **No backup scripts** found in snapshot
- **No recovery runbook** found
- **Neon may provide automatic backups** (Neon's default behavior), but this is NOT confirmed for this specific project
- **Risk:** Deployed MVP with user data and no confirmed recovery strategy

---

## 35. UMH Integration Layer

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (projections/lyfeos/integration/)

Exists in UMH codebase at `/opt/OS/projections/lyfeos/integration/` (1184 lines, 7 Python files):

- **manifest.py:** 3 signal types, 4 capabilities, 3 polled tables, 30s poll interval
- **tables.py:** Typed row dataclasses (QuestRow, UserStatsRow, DailyLogRow, VisionGoalRow), read/write SQL helpers, outcome writeback helpers
- **signals.py:** SignalEmitter protocol implementation, builds SignalEnvelopes from polled rows
- **handlers.py:** CapabilityHandler protocol implementation (noop, create_quest, complete_quest, log_daily_reflection)
- **correlation.py:** Thread-safe correlation map for outcome writeback targeting
- **outcomes.py:** OutcomeReceiver protocol implementation, dual writeback (source row + audit table)

**Integration Method:** Direct Postgres polling (LYFEOS_DATABASE_URL env var). No HTTP API integration. UMH reads/writes directly to LyfeOS database.

**NOT in LyfeOS code:** The UMH integration layer exists only in the UMH codebase. LyfeOS has no knowledge of UMH.
