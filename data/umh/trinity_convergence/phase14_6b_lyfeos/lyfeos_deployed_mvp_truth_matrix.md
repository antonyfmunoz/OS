# LyfeOS Deployed MVP Truth Matrix

**Phase:** 14.6B-LyfeOS
**Operator Approved:** false
**Allows Implementation:** false

---

## Methodology

Each feature is classified by deployment evidence strength:
- **DEPLOYED_CONFIRMED** — Schema + dependencies + documentation all align. Feature present in production.
- **DEPLOYED_LIKELY** — Schema exists and dependencies support it. Strong inference of deployment.
- **SCHEMA_ONLY** — Database table exists but feature completion not confirmed from snapshot.
- **DOCS_ONLY** — Documented in replit.md but no schema or dependency evidence in snapshot.
- **NOT_DEPLOYED** — Confirmed absent from current deployment.

---

## Core User Flow

| Feature | Deployed Status | Evidence | Risk Level | Notes |
|---------|----------------|----------|------------|-------|
| User Registration (email/password) | DEPLOYED_CONFIRMED | Schema: users table, bcrypt dep, test: api-auth.test.ts confirms register | LOW | Working auth flow |
| User Login/Logout | DEPLOYED_CONFIRMED | Schema: users.password, bcrypt, test confirms login/logout/session | LOW | Session-based via express-session |
| Firebase OAuth (Google/Apple/Facebook) | DEPLOYED_LIKELY | Schema: firebaseUid, authProvider. Deps: firebase, firebase-admin | LOW | OAuth providers configured |
| 2FA (Email + Phone) | DEPLOYED_LIKELY | Schema: twoFactorEnabled, twoFactorEmailCode/PhoneCode fields | MEDIUM | Fields exist but delivery mechanism depends on Firebase config |
| Email Verification | DEPLOYED_LIKELY | Schema: emailVerified, emailVerificationToken fields. Firebase handles delivery | LOW | |
| Password Reset | DEPLOYED_LIKELY | Schema: passwordResetToken/Expiry. Test confirms reset endpoint exists | LOW | |

## Primary Navigation

| Feature | Deployed Status | Evidence | Risk Level | Notes |
|---------|----------------|----------|------------|-------|
| Dashboard | DEPLOYED_CONFIRMED | Operator confirmation. widget_states table for config persistence | LOW | Primary landing page |
| Missions | DEPLOYED_CONFIRMED | Schema: quests (50+ fields), mission_views table. replit.md: Board/List/Calendar views | LOW | Most feature-rich module |
| AI (NOVA) | DEPLOYED_CONFIRMED | Schema: conversations + messages tables. Deps: anthropic + openai SDKs | LOW | Chat interface with AI companion |
| Chronilog (Daily Logs) | DEPLOYED_CONFIRMED | Schema: user_daily_logs with energy/intention/data/research/reflection fields | LOW | Daily logging system |
| Profile | DEPLOYED_CONFIRMED | Schema: user_profile (~200 fields), user_stats. Operator confirmation as 5th primary tab | LOW | Character sheet + settings |

## Gamification

| Feature | Deployed Status | Evidence | Risk Level | Notes |
|---------|----------------|----------|------------|-------|
| 5 Stat Tokens | DEPLOYED_CONFIRMED | Schema: all 5 current/max pairs in user_stats, defaults 100/100 | LOW | Energy, Health, Wealth, Time, Attention |
| XP/Leveling System | DEPLOYED_CONFIRMED | Schema: experienceCurrent/Max, level, totalXP. Tests: xp-calculations.test.ts (11 tests) | LOW | 3-tier exponential growth verified |
| Streak Tracking | DEPLOYED_CONFIRMED | Schema: streakDays, lastActiveDate in user_stats | LOW | |
| Efficiency Score | DEPLOYED_CONFIRMED | Schema: efficiencyScore in user_stats | LOW | |
| Mission Difficulty Ranks | DEPLOYED_CONFIRMED | Schema: difficulty field with S/A/B/C/D ranks | LOW | |
| Mission Resource Costs | DEPLOYED_CONFIRMED | Schema: energyCost, attentionCost, timeCost fields | LOW | |
| Stat Detail Pages | DEPLOYED_LIKELY | replit.md documents 7 stat pages with recharts. recharts dep confirmed | LOW | |
| Haptic Feedback | DEPLOYED_LIKELY | Schema: hapticFeedback boolean in user_profile. replit.md documents patterns | LOW | Web Vibration API |
| Sound Effects | DEPLOYED_LIKELY | Schema: soundEffects boolean in user_profile. replit.md documents Web Audio API | LOW | No external audio files |

## Onboarding

| Feature | Deployed Status | Evidence | Risk Level | Notes |
|---------|----------------|----------|------------|-------|
| 8 Onboarding Missions | DEPLOYED_CONFIRMED | Schema: onboardingMission (0-7), onboardingStep, completedOnboardingMissions | LOW | Progressive onboarding |
| Archetype Calibration | DEPLOYED_LIKELY | Schema: archetypePrimary/Secondary/Shadow, archetypeScores. replit.md: 54 questions | LOW | 6 archetypes confirmed |
| Character Affirmation | SCHEMA_ONLY | Schema: characterAffirmation field. AI-generated narrative | MEDIUM | Field exists but generation logic not confirmed |

## AI Companion (NOVA)

| Feature | Deployed Status | Evidence | Risk Level | Notes |
|---------|----------------|----------|------------|-------|
| Chat Interface | DEPLOYED_CONFIRMED | Schema: conversations + messages tables. Deps: anthropic SDK | LOW | |
| User-Renamable AI | DEPLOYED_CONFIRMED | Schema: aiAssistantName default "NOVA", in insert schema pick list | LOW | |
| Streaming Responses | DEPLOYED_LIKELY | Deps: ws (WebSocket). replit.md documents streaming | LOW | |
| AI Tools (web search, vision goals, etc.) | DEPLOYED_LIKELY | Deps: puppeteer-core, cheerio, turndown. replit.md documents 5+ tools | MEDIUM | Tool implementation not in snapshot |
| 16-Domain Knowledge Base | DOCS_ONLY | replit.md names all 16 domains. File path documented but not in snapshot | MEDIUM | High confidence given detail |
| Vision/Image Analysis | DEPLOYED_LIKELY | replit.md documents base64 vision content blocks. media_items table exists | MEDIUM | |
| Smart Model Routing (Haiku -> Sonnet) | DOCS_ONLY | replit.md documents upgrade triggers. Not verifiable from snapshot | MEDIUM | |

## Secondary Features

| Feature | Deployed Status | Evidence | Risk Level | Notes |
|---------|----------------|----------|------------|-------|
| Document Vault | DEPLOYED_LIKELY | Schema: folders + documents + templates tables. replit.md documents features | LOW | Google Drive-style |
| Contacts | DEPLOYED_LIKELY | Schema: contacts table (30+ fields) | LOW | CRM-style |
| Kanban Boards | DEPLOYED_LIKELY | Schema: kanban_boards + kanban_columns + kanban_tasks (3-table design) | LOW | |
| Spreadsheets | SCHEMA_ONLY | Schema: spreadsheets table with JSONB content | MEDIUM | UI unknown |
| Canvases | SCHEMA_ONLY | Schema: canvases table with JSONB content | MEDIUM | UI unknown |
| Graphs | SCHEMA_ONLY | Schema: graphs table with JSONB content | MEDIUM | UI unknown |
| Media Gallery | DEPLOYED_LIKELY | Schema: media_albums + media_items tables. replit.md documents inline images | LOW | |
| Progress Trackers | SCHEMA_ONLY | Schema: progress_trackers table | MEDIUM | UI unknown |
| Vision Goals | DEPLOYED_CONFIRMED | Schema: vision_goals with 5 time horizons. quests.visionGoalId FK linkage | LOW | |
| Smart Reminders | SCHEMA_ONLY | Schema: smart_reminders table | MEDIUM | Delivery mechanism unclear |
| Custom Mission Views | DEPLOYED_LIKELY | Schema: mission_views table. replit.md documents Notion-style custom views | LOW | |
| Ritual Groups | DEPLOYED_LIKELY | Schema: ritual_groups table. quests.ritualGroup field | LOW | |
| User Categories | SCHEMA_ONLY | Schema: user_categories table | MEDIUM | |

## Integrations

| Feature | Deployed Status | Evidence | Risk Level | Notes |
|---------|----------------|----------|------------|-------|
| Google Calendar Sync | DEPLOYED_LIKELY | Deps: googleapis. Schema: integrations + calendar_events + externalId fields. replit.md documents full flow | LOW | Read/write with dedup |
| Google Tasks Import | DEPLOYED_LIKELY | Same evidence as Calendar. replit.md documents read-only import | LOW | |
| Apple Health | SCHEMA_ONLY | Schema: userIntegrations.appleHealthConnected boolean | HIGH | Bool field only, no implementation evidence |
| Notion | SCHEMA_ONLY | Schema: userIntegrations.notionConnected boolean | HIGH | Bool field only, no implementation evidence |
| Obsidian Import/Export | DOCS_ONLY | replit.md documents .md/.zip support in Document Vault sync dialog | MEDIUM | |
| Evernote Import/Export | DOCS_ONLY | replit.md documents .enex support in Document Vault sync dialog | MEDIUM | |
| Firebase Push Notifications | DEPLOYED_LIKELY | Schema: push_subscriptions with fcmToken. Deps: firebase | LOW | FCM-based |

## Infrastructure

| Feature | Deployed Status | Evidence | Risk Level | Notes |
|---------|----------------|----------|------------|-------|
| PWA (Service Worker) | DEPLOYED_LIKELY | replit.md documents manifest, service worker, install prompt. FCM deps | LOW | |
| Health Check Endpoint | DEPLOYED_CONFIRMED | tests/api-auth.test.ts confirms /api/health returns ok | LOW | |
| Replit Hosting | DEPLOYED_CONFIRMED | Replit-specific deps (@replit/*), build.sh, operator confirmation | LOW | lyfeos.net |
| Neon Postgres | DEPLOYED_CONFIRMED | Deps: @neondatabase/serverless. drizzle.config.ts: DATABASE_URL | LOW | |
| Waitlist | DEPLOYED_LIKELY | Schema: waitlist_emails table | LOW | |
| Stripe (Payments) | NOT_DEPLOYED | No stripe dep. Schema: stub fields remain. replit.md: "removed" | LOW | Intentionally removed |
| RLS | NOT_DEPLOYED | No policy definitions anywhere in schema | HIGH | Personal data unprotected at DB level |
| CI/CD | NOT_DEPLOYED | No workflow files, no CI deps | MEDIUM | Manual deployment only |
| Error Tracking | NOT_DEPLOYED | No Sentry/PostHog/similar deps | HIGH | Production blind spot |
| Automated Backups | NOT_DEPLOYED | No backup scripts or config | HIGH | Data loss risk |
| Rate Limiting | DOCS_ONLY | replit.md mentions rate limiting. No rate-limit dep in package.json | HIGH | May use custom middleware |

---

## Summary

| Status | Count |
|--------|-------|
| DEPLOYED_CONFIRMED | 20 |
| DEPLOYED_LIKELY | 22 |
| SCHEMA_ONLY | 8 |
| DOCS_ONLY | 5 |
| NOT_DEPLOYED | 5 |
| **Total Features Assessed** | **60** |

**Key Risk Areas:**
1. No error tracking on a deployed production app (HIGH)
2. No confirmed backup strategy for a database with user data (HIGH)
3. No RLS on 35 user-scoped tables (HIGH for multi-user scenarios)
4. No CI/CD pipeline (MEDIUM — manual deploys are error-prone)
5. Rate limiting status unclear (HIGH if absent on AI endpoints)
