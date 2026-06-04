# LyfeOS MVP Current Canon

**Phase:** 14.6B-LyfeOS
**Operator Approved:** false
**Allows Implementation:** false

This document contains ONLY what is proven to exist in the current deployed MVP. Every item has CODE_RESOLVED_CURRENT_TRUTH provenance. If it cannot be verified from code, it is not listed here.

---

## Product

- **Name:** LyfeOS
- **URL:** lyfeos.net
- **Host:** Replit
- **Stack:** React 18.3.1 + TypeScript 5.6.3 + Vite 5.4.21 + Express 4.21.2 + Neon Postgres + Drizzle ORM 0.39.1
- **Theme:** Dark-only, cyan primary, professional variant

---

## Database: 35 Tables

All 35 tables confirmed via `grep -c 'pgTable(' schema.ts`:

users, user_stats, user_profile, user_daily_logs, user_integrations, quests, ai_messages, calendar_events, mission_pages, contacts, spreadsheets, push_subscriptions, canvases, graphs, folders, documents, templates, integrations, progress_trackers, kanban_boards, kanban_columns, kanban_tasks, media_albums, media_items, conversations, messages, dismissed_knowledge, vision_goals, user_categories, ritual_groups, widget_states, user_activity_events, smart_reminders, mission_views, waitlist_emails.

---

## Authentication

- **Local auth:** Passport.js + bcrypt (username/password registration and login)
- **OAuth:** Firebase (Google, Apple, Facebook providers via authProvider field)
- **Sessions:** express-session + connect-pg-simple (Postgres-backed)
- **2FA fields:** twoFactorEnabled, twoFactorEmailCode/Expiry, twoFactorPhoneCode/Expiry
- **Email verification fields:** emailVerified, emailVerificationToken/Expiry
- **Password reset fields:** passwordResetToken/Expiry
- **Security headers:** Helmet 8.1.0

**Test coverage:** 10 integration tests (register validation, login/logout, session management, password reset, health check).

---

## Primary Navigation

1. **Dashboard** — Widget-based overview (widget_states table)
2. **Missions** — Quest management (quests + mission_views tables)
3. **AI** — NOVA chat companion (conversations + messages tables)
4. **Chronilog** — Daily logging (user_daily_logs table)
5. **Profile** — Character sheet + settings (user_profile + user_stats tables)

---

## AI Companion

- **Default name:** "NOVA" (user_stats.aiAssistantName, default "NOVA")
- **User-renamable:** Yes (field is in insert schema pick list)
- **Chat storage:** conversations (threaded, with deletedAt) + messages (role: user/assistant)
- **Legacy storage:** ai_messages (flat, sender: ai/user)
- **AI SDK:** @anthropic-ai/sdk 0.72.1
- **OpenAI SDK:** openai 4.96.0 (also in dependencies)
- **WebSocket:** ws 8.18.0 (supports streaming)

---

## Gamification System

### Stat Tokens (5, all 0-100)
- Energy: energyPointsCurrent/Max (default 100/100)
- Health: healthPointsCurrent/Max (default 100/100)
- Wealth: wealthTokensCurrent/Max (default 100/100)
- Time: timeTokensCurrent/Max (default 100/100)
- Attention: attentionTokensCurrent/Max (default 100/100)

### XP and Leveling
- Level 1 base: 1000 XP
- Tier 1 (levels 1-10): 1.0372x exponential multiplier
- Tier 2 (levels 11-50): 1.0572x exponential multiplier
- Tier 3 (levels 51-100): 1.0872x exponential multiplier
- Level cap: 100
- **Test coverage:** 11 unit tests confirm the math

### Mission Difficulty
Ranks: S, A, B, C, D (D is default)

### Mission Resource Costs
energyCost (default 1), attentionCost (default 0), timeCost (default 0), experienceReward (default 10)

### Streaks
streakDays + lastActiveDate in user_stats

### Efficiency
efficiencyScore + previousDayEnergyUsed in user_stats

---

## Onboarding System

- 8 missions (0-7): onboardingMission integer, default 0
- Per-step tracking: onboardingStep integer, default 0
- Completion flag: onboardingCompleted boolean
- History: completedOnboardingMissions (integer array), completedTutorials (text array)

---

## Archetype System

- 6 archetypes: Warrior, Architect, Creator, Monarch, Oracle, Alchemist
- Fields: archetypePrimary, archetypeSecondary, archetypeShadow
- Scores: archetypeScores JSONB

---

## Character Sheet (user_profile)

~90 named fields organized into 16+ sections:
- Demographics, Archetype, Identity, Personality, Vision & Goals, Learning & Skills, Projects, Body & Health, Wealth & Work, Performance, Style & Expression, History & Roots, Systems & Rituals, Emotions & Coping, Display Settings, Legacy Fields

Custom reflection prompts: wentWell, couldBeBetter, learned (user-editable defaults).

---

## Daily Logging (user_daily_logs)

Unique per user+date. 5 dimensions:
1. Energy: wakeTime, sleepTime, mentalState (1-10), physicalState (1-10), emotionalState (1-10)
2. Intention: gratitude, tomorrowGoals, annualGoals, thoughts
3. Data: contentConsumed, research, todoIdeas (convertible to quests)
4. Research: sourceAuthor, sourceMaterial, researchNote, revisionNote, executionNote, researchEntries
5. Reflection: wentWell, couldBeBetter, learned

Meta: yesterdayXp, todayPrimaryMission, boostsData.

---

## Mission System (quests)

33 fields including:
- Core: title, description, category, completed, completedAt
- Gamification: energyCost, attentionCost, timeCost, experienceReward, difficulty
- Scheduling: startDate/Time, endDate/Time, dueDate, allDay, timezone
- Repeat: repeatFrequency, repeatInterval, repeatDays, repeatEndDate, parentRitualId
- Ritual: isRitualized, ritualGroup
- Vision: visionGoalId FK
- External: externalId, externalSource
- Views: viewId, viewColumn, missionStatus, sortOrder
- Soft delete: deletedAt

Custom views: mission_views table (viewType, filters, columns, sorting).

---

## Vision Goals (vision_goals)

5 time horizons: legacy, 10year, 5year, 18month, 90day
Fields: title, description, rewardText, bonusXp, completed, completedAt, displayOrder
Linkage: quests.visionGoalId FK, disconnectedMissionIds array

---

## Google Integration

- SDK: googleapis 171.4.0
- OAuth storage: integrations table (provider, accessToken, refreshToken, tokenExpiry, scope, status)
- Calendar: calendar_events table with externalId/externalSource
- Tasks: quests table with externalId/externalSource
- Status flag: userIntegrations.googleCalendarConnected

---

## Secondary Features (schema-confirmed)

| Feature | Tables | Evidence Level |
|---------|--------|----------------|
| Document Vault | folders, documents, templates | Full schema |
| Contacts | contacts (30+ fields) | Full schema |
| Kanban | kanban_boards, kanban_columns, kanban_tasks | Full schema |
| Spreadsheets | spreadsheets | Full schema |
| Canvases | canvases | Full schema |
| Graphs | graphs | Full schema |
| Media Gallery | media_albums, media_items | Full schema |
| Progress Trackers | progress_trackers | Full schema |
| Smart Reminders | smart_reminders | Full schema |
| User Activity Events | user_activity_events | Full schema |
| Widget States | widget_states | Full schema |
| User Categories | user_categories | Full schema |
| Ritual Groups | ritual_groups | Full schema |
| Dismissed Knowledge | dismissed_knowledge | Full schema |
| Waitlist | waitlist_emails | Full schema |

---

## What Does NOT Exist

- No Clerk auth (zero dependencies)
- No RLS policies
- No CI/CD pipeline
- No error tracking service
- No analytics service
- No confirmed backup scripts
- No Stripe payment processing (removed, stubs only)
- No UMH awareness in LyfeOS code
- No Transformation Thread implementation
- No Apple Health integration (boolean flag only)
- No Notion integration (boolean flag only)

---

## Test Coverage

- 2 test files, 21 test cases total
- api-auth.test.ts: 10 tests (auth API integration)
- xp-calculations.test.ts: 11 tests (gamification math)
- Framework: Vitest 4.0.18

---

## Health Check

`/api/health` returns `{ status: "ok", timestamp: "..." }` — confirmed by test.
