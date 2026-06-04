# LyfeOS Code-Resolved Product Canon

Revised in Phase 14.6F to align with 18 ratified P0 decisions (2026-06-04).

**Phase:** 14.6B-LyfeOS (revised 14.6F)
**Revised:** 2026-06-04
**Operator Approved:** false
**Allows Implementation:** false

This is the master canon document for LyfeOS. Every claim is grounded in code evidence. Where code evidence is unavailable, claims are labeled with their provenance.

---

## 1. Product Identity

**LyfeOS** is a gamified personal life operating system that treats human life as a stateful system with measurable inputs, outputs, and progression mechanics.

- **Domain:** lyfeos.net (deployed on Replit; ratified migration target: Fly.io per DEC-146B-LOS-003)
- **Repository:** Private GitHub + Beast at C:\dev\dev\LyfeOS
- **Stack:** React 18 + TypeScript + Vite + Express + Neon Postgres + Drizzle ORM
- **Aesthetic:** Dark-only, "Solo Leveling" anime-inspired, neon cyan accents, HUD-style interfaces
- **Theme:** Professional variant, primary hsl(188, 100%, 50%), radius 0.5

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH

---

## 2. Center of Gravity

LyfeOS is transformation infrastructure. The core value proposition:

1. **Measure** your life state (5 stat tokens, daily logs, archetype profiling)
2. **Plan** your evolution (vision goals across 5 time horizons, missions with resource costs)
3. **Execute** daily (mission completion, daily logging, streak tracking)
4. **Reflect** and compound (AI companion coaching, research logging, reflection prompts)
5. **Level up** visibly (XP, levels, efficiency scores, stat progression)

The gamification layer makes this feel like playing a game where you are the character.

---

## 3. Core Product Loop

```
Wake -> Daily Log (energy/intention) -> Execute Missions -> Earn XP/Resources
  -> AI Coaching (NOVA) -> Reflect (Chronilog) -> Level Up -> Vision Progress
  -> Sleep -> Repeat
```

**Schema Evidence:** user_daily_logs (wake/sleep/state), quests (energy/XP), user_stats (level/streak), vision_goals (milestone tracking), conversations (AI coaching), custom reflection prompts in user_profile.

---

## 4. Current Navigation Architecture

### Primary Navigation (5 tabs)

| Tab | Purpose | Key Tables |
|-----|---------|------------|
| **Dashboard** | Widget-based overview of all life systems | widget_states |
| **Missions** | Quest management with Board/List/Calendar views | quests, mission_views |
| **AI** | NOVA companion chat interface | conversations, messages |
| **Chronilog** | Daily logging across 5 dimensions | user_daily_logs |
| **Profile** | Character sheet, settings, integrations | user_profile, user_stats, user_integrations |

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (operator correction)

### Secondary Navigation

Document Vault, Tracker, Settings, Contacts, Kanban, Spreadsheets, Canvases, Graphs, Media.

---

## 5. Module Architecture

### 5a. Dashboard Module

- Widget-based layout with user-configurable state
- `widget_states` table: per-user JSONB state storage
- Entry point for daily initialization flow

### 5b. Missions Module

**Tables:** quests, mission_views, ritual_groups, user_categories

- **Quest Fields:** title, description, category, difficulty (S/A/B/C/D), resource costs (energy/attention/time), XP reward, scheduling (start/end dates, repeat patterns), ritual linkage, vision goal linkage, external sync (Google), soft delete
- **3 Default Views:** Board (vertical kanban: Today/Future/Completed/Inbox/Terminated), List (chronological by day), Calendar (year/month/week/day zoom)
- **Custom Views:** Notion-style user-created views with filters, columns, sorting (persisted in mission_views table)
- **Rituals:** Repeating missions grouped via ritual_groups with parent-child hierarchy
- **External Sync:** externalId/externalSource fields for Google Calendar/Tasks bidirectional sync with smart deduplication

### 5c. AI Companion Module (NOVA)

**Tables:** conversations, messages (+ legacy ai_messages)

- **Default Name:** "NOVA" (stored in user_stats.aiAssistantName, user-renamable)
- **Models:** Anthropic (Haiku default, Sonnet for complex/tool tasks), OpenAI SDK also present
- **Chat:** Threaded conversations with soft delete. Roles: user, assistant
- **Tools:** Web search, web page reading, vision goal creation, batch mission creation, uncomplete missions, knowledge base lookup (SOURCE_PRESERVED_TRUTH)
- **Knowledge Base:** 16 domains with auto-topic injection (SOURCE_PRESERVED_TRUTH)
- **Vision:** Image upload/paste + auto-extraction from mission/goal/log descriptions (SOURCE_PRESERVED_TRUTH)
- **Streaming:** WebSocket-based response streaming (DEPLOYED_LIKELY)

### 5d. Chronilog Module (Daily Logging)

**Table:** user_daily_logs (unique per user+date)

5 logging dimensions:
1. **Energy Log:** wakeTime, sleepTime, mentalState (1-10), physicalState (1-10), emotionalState (1-10)
2. **Intention Log:** gratitude, tomorrowGoals, annualGoals, thoughts
3. **Data Log:** contentConsumed, research, todoIdeas (convertible to quests)
4. **Research Log:** sourceAuthor, sourceMaterial, researchNote, revisionNote, executionNote, archived entries array
5. **Reflection Log:** wentWell, couldBeBetter, learned (customizable prompts via user_profile)

**Meta:** yesterdayXp, todayPrimaryMission, optionalBoostsShown, boostsData

### 5e. Profile Module (Character Sheet)

**Tables:** user_profile (~200 fields), users, user_stats, user_integrations

Comprehensive personal data model organized into sections:
- Mission 0: Demographics (age, birthday, location, timezone)
- Mission 1: Archetype calibration (6 archetypes, scores, primary/secondary/shadow)
- Identity: Instincts, drivers, shadow distortions
- Personality: Beliefs (core/limiting/empowering), values, standards, habits, strengths, weaknesses
- Vision & Goals: 4 time horizons (90-day to 10-year), legacy metric, mortality insights
- Learning & Skills: Learning style, skill stacking pyramid, practice cadence
- Projects & Creations: Current projects, active phase, primary craft
- Body & Health: Physical metrics, fitness, nutrition, health vitality, injuries
- Wealth & Work: Career, ventures, financial position, weekly capacity, resources
- Performance: Collaboration style, role orientation, decision making, stress response
- Style & Expression: Aesthetic, signature expression, creative outlets
- History & Roots: Shadow patterns, upbringing, cultural context
- Systems & Rituals: Ideal day/week, morning/evening rituals, boundaries
- Emotions & Coping: Emotions to cultivate, coping practices, belief system, instincts

**Character Affirmation:** AI-generated third-person narrative stored in user_profile.characterAffirmation.

---

## 6. Data Model Overview

### Table Count: 35

### Table Categories:
- **Core Identity (3):** users, user_stats, user_profile
- **Daily Operations (2):** user_daily_logs, quests
- **AI (3):** conversations, messages, ai_messages (legacy)
- **Vision (1):** vision_goals
- **Calendar (2):** calendar_events, mission_pages
- **Organization (6):** folders, documents, templates, kanban_boards, kanban_columns, kanban_tasks
- **Creative (3):** canvases, graphs, spreadsheets
- **Media (2):** media_albums, media_items
- **Social (1):** contacts
- **Integrations (2):** user_integrations, integrations
- **Gamification (3):** user_categories, ritual_groups, progress_trackers
- **System (5):** widget_states, user_activity_events, smart_reminders, mission_views, push_subscriptions
- **Marketing (2):** waitlist_emails, dismissed_knowledge

### Key Design Patterns:
- Serial integer IDs (not UUIDs)
- userId FK on all user-scoped tables
- JSONB for flexible/complex data
- Soft deletes via deletedAt timestamps
- External sync via externalId/externalSource pairs
- Drizzle Zod insert schemas for validation

---

## 7. Gamification System

### Stat Tokens (5)
Energy, Health, Wealth, Time, Attention. All current/max pairs defaulting to 100/100.

### XP and Leveling
- Level 1 base: 1000 XP
- Tier 1 (levels 1-10): 1.0372x exponential multiplier
- Tier 2 (levels 11-50): 1.0572x exponential multiplier
- Tier 3 (levels 51-100): 1.0872x exponential multiplier
- Level cap: 100
- Verified by 11 test cases in xp-calculations.test.ts

### Additional Progression
- Streak days tracked with lastActiveDate
- Efficiency score computed from daily performance
- previousDayEnergyUsed tracking
- Per-mission XP rewards (default 10)
- Vision goal bonus XP

---

## 8. Auth Architecture

**Dual Auth System:**

1. **Local:** Passport.js + bcrypt (username/password)
2. **Firebase:** Google/Apple/Facebook OAuth, email verification, password reset, 2FA (email + phone)
3. **Sessions:** express-session + connect-pg-simple (Postgres session store)

**Schema Support:** authProvider field (email/google/apple/facebook), firebaseUid, password (bcrypt hash), twoFactorEnabled, email verification tokens, password reset tokens.

**Test Coverage:** 10 integration tests covering register, login, logout, session management, password reset validation, health check.

---

## 9. Integration Architecture

### Active Integrations
- **Google Calendar:** Read/write sync, OAuth token management, smart deduplication
- **Google Tasks:** Read-only import as missions with dedup
- **Firebase Push Notifications:** FCM token-based subscription

### Schema-Only (Placeholder)
- Apple Health (boolean flag only)
- Notion (boolean flag only)

### Documented but Unverified
- Obsidian import/export (.md/.zip)
- Evernote import/export (.enex)

---

## 10. Deployment Architecture

| Component | Current State |
|-----------|--------------|
| **Hosting** | Replit (lyfeos.net) |
| **Database** | Neon PostgreSQL (serverless) |
| **Auth** | Passport.js + Firebase |
| **Build** | Vite (frontend) + esbuild (backend) |
| **Start** | `NODE_ENV=production node dist/index.js` |
| **CI/CD** | None |
| **Error Tracking** | None |
| **Backups** | Unverified (Neon defaults may apply) |
| **RLS** | None |
| **Security Headers** | Helmet 8.1.0 |
| **Session Store** | Postgres (connect-pg-simple) or memorystore fallback |

---

## 11. UMH Connection

UMH (Universal Meta Harness, DEC-146B-UMH-001) is the reality-isomorphic intelligence harness (DEC-146C-001) that LyfeOS connects to as a projection.

3 LyfeOS strategic decisions are now ratified (Phase 14.6E, 2026-06-04): PRD v2.0 is canonical (DEC-146B-LOS-001), Clerk migration after CreatorOS proves pattern (DEC-146B-LOS-002), Fly.io is Trinity standard (DEC-146B-LOS-003).

**Provenance:** SYNTHESIZED_CANON / UMH_INTEGRATION_DEPENDENT_GAP

### Current State

An integration layer exists at `projections/lyfeos/integration/` containing:

| Component | Purpose | Status |
|-----------|---------|--------|
| `signals.py` | Emits SignalEnvelope from LyfeOS DB changes (quests, daily logs, stats) | Implemented, not wired |
| `handlers.py` | Handles capability requests (create/complete quests, log reflections) | Implemented, testable |
| `outcomes.py` | Receives UMH outcomes and writes back to LyfeOS DB | Implemented, not receiving |
| `correlation.py` | Thread-safe correlation ID to writeback target mapping | Implemented |
| `tables.py` | Typed row dataclasses and CRUD helpers for integration use cases | Implemented |
| `manifest.py` | Integration contract (3 signal types, 4 capabilities, poll config) | Implemented |

**Classification:** Architecturally complete, operationally dormant. All building blocks exist; none are wired to production runtime.

### Integration Principle

**Adapter-first, not rewrite-first.** LyfeOS connects to UMH through boundary adapters. LyfeOS internals are not rewritten. The user never needs to know UMH exists. All non-AI features work without UMH (deterministic spine preserved). When UMH is unavailable, AI features degrade gracefully.

### What LyfeOS Owns vs. What UMH Owns

- **LyfeOS:** UX, modules, user data, gamification, daily logging, mission management, profile, integrations UI
- **UMH:** Agent runtime, model routing, governance, audit, memory/salience, execution boundaries, quality gates

### Blocking Questions (Operator Decision Required)

12 blocking questions documented in `lyfeos_umh_connection_architecture.md`, covering: AI routing model, identity mapping, knowledge base ownership, data sensitivity, conversation storage, consent boundaries, cross-projection data sharing, latency budget, AI name scope, onboarding data feed, preference sync, and degradation UX.
