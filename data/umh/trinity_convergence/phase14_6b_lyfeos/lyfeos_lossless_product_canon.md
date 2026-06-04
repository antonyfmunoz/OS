# LyfeOS Lossless Product Canon

**Phase:** 14.6B-LyfeOS
**Operator Approved:** false
**Allows Implementation:** false

This document preserves EVERYTHING from ALL sources — current implementation, future intent, historical context, operator corrections, design concepts, and open questions. Every section is labeled with its provenance. Nothing is lost.

---

## PART 1: PRODUCT IDENTITY

### 1.1 Current Identity [CODE_RESOLVED_CURRENT_TRUTH]

- **Name:** LyfeOS
- **Tagline:** Gamified Life Operating System
- **Domain:** lyfeos.net
- **Deployment:** Replit
- **Repository:** Private GitHub, Beast at C:\dev\dev\LyfeOS (853 files)
- **Latest Commit:** ee1bb0f3 (2026-05-20) "merge Development branch into main"
- **Package Name:** rest-express (package.json)

### 1.2 Design Language [CODE_RESOLVED_CURRENT_TRUTH]

- **Aesthetic:** "Solo Leveling" anime-inspired, dark-only, neon cyan accents, HUD-style
- **Theme:** Professional variant, primary hsl(188, 100%, 50%), dark appearance, 0.5 radius
- **Color System:** CSS variable-based via shadcn theme.json + Tailwind
- **Custom Effects:** glow-cyan box shadow, accordion animations
- **Typography Plugin:** @tailwindcss/typography
- **Animation:** Framer Motion

### 1.3 Product Philosophy [SOURCE_PRESERVED_TRUTH]

From replit.md: "LYFEOS is a gamified personal productivity and life management web application that transforms daily tasks, habits, and goals into a game-like experience."

Treats human life as a stateful system with:
- Measurable attributes (stat tokens)
- Progressive advancement (XP, levels, tiers)
- Strategic planning (vision goals across time horizons)
- Daily discipline (missions, rituals, daily logs)
- AI-augmented coaching (NOVA companion)

### 1.4 Future Identity Aspirations [SYNTHESIZED_CANON]

From phase 14.5: "Personal Life Operating System treating human life as a stateful system." Most mature MVP in the Trinity (LyfeOS, CreatorOS, EOS). Eventual UMH projection.

---

## PART 2: TECHNOLOGY STACK

### 2.1 Frontend [CODE_RESOLVED_CURRENT_TRUTH]

| Component | Package | Version |
|-----------|---------|---------|
| Framework | react | 18.3.1 |
| Language | typescript | 5.6.3 |
| Build Tool | vite | 5.4.21 |
| Router | wouter | 3.3.5 |
| State/Data | @tanstack/react-query | 5.60.5 |
| UI Library | shadcn/ui (25+ @radix-ui/* packages) | various |
| Styling | tailwindcss | 3.4.14 |
| Animation | framer-motion | 11.13.1 |
| Charts | recharts | 2.13.0 |
| Forms | react-hook-form | 7.53.1 |
| Validation | zod | 3.25.76 |
| Markdown | react-markdown + remark-gfm + remark-math + rehype-katex | various |
| Icons | lucide-react + react-icons | various |
| Drag & Drop | react-dnd + react-beautiful-dnd | both present |
| Date | date-fns | 3.6.0 |
| Panels | react-resizable-panels | 2.1.4 |
| Carousel | embla-carousel-react | 8.3.0 |
| Command | cmdk | 1.0.0 |
| Drawer | vaul | 1.1.0 |
| OTP Input | input-otp | 1.2.4 |
| Confetti | canvas-confetti | 1.9.3 |

### 2.2 Backend [CODE_RESOLVED_CURRENT_TRUTH]

| Component | Package | Version |
|-----------|---------|---------|
| Server | express | 4.21.2 |
| Dev Server | tsx | 4.19.1 |
| Production Build | esbuild | 0.25.12 |
| ORM | drizzle-orm | 0.39.1 |
| Schema Validation | drizzle-zod | 0.7.1 |
| DB Driver | @neondatabase/serverless | 0.10.4 |
| Auth (Local) | passport + passport-local | 0.7.0, 1.0.0 |
| Password Hashing | bcrypt | 6.0.0 |
| Auth (OAuth) | firebase + firebase-admin | 11.6.1, 13.6.1 |
| Sessions | express-session | 1.18.1 |
| Session Store | connect-pg-simple | 10.0.0 |
| Fallback Sessions | memorystore | 1.6.7 |
| Security Headers | helmet | 8.1.0 |
| Compression | compression | 1.8.1 |
| File Upload | multer | 2.0.2 |
| WebSocket | ws | 8.18.0 |
| AI (Anthropic) | @anthropic-ai/sdk | 0.72.1 |
| AI (OpenAI) | openai | 4.96.0 |
| Google APIs | googleapis | 171.4.0 |
| Browser | puppeteer-core | 24.37.2 |
| HTML Parser | cheerio | 1.2.0 |
| HTML to MD | turndown | 7.2.2 |
| ZIP | adm-zip | 0.5.16 |
| XML Parser | xml2js | 0.6.2 |
| UUID | uuid | 11.1.0 |
| Rate Control | p-limit + p-retry | 7.2.0, 7.1.1 |
| Env | dotenv | 17.3.1 |
| Glob | glob | 11.1.0 |

### 2.3 Testing [CODE_RESOLVED_CURRENT_TRUTH]

| Component | Package | Version |
|-----------|---------|---------|
| Framework | vitest | 4.0.18 |
| HTTP Testing | supertest | 7.2.2 |
| Config | vitest.config.ts | node env, 15s timeout |

---

## PART 3: DATABASE (35 TABLES)

### 3.1 Complete Table Inventory [CODE_RESOLVED_CURRENT_TRUTH]

Every table from schema.ts with field counts and purpose:

1. **users** (18 fields) — Core account: username, password, email, authProvider, firebaseUid, termsAccepted, emailVerified, twoFactorEnabled, stripeCustomerId
2. **user_stats** (22 fields) — Player stats: 5 stat token pairs, XP, level, streak, aiAssistantName, system settings (notifications, theme, sync, AI, color)
3. **user_profile** (~90 fields, 180 lines) — Full character sheet across 16 sections
4. **user_daily_logs** (23 fields) — Daily logs: energy, intention, data, research, reflection dimensions
5. **user_integrations** (7 fields) — Integration flags: appleHealth, googleCalendar, notion
6. **quests** (33 fields) — Missions: title, description, category, difficulty, costs, rewards, scheduling, repeat, ritual, vision, external, views
7. **ai_messages** (5 fields) — Legacy AI chat: sender, content, timestamp
8. **calendar_events** (12 fields) — Calendar: title, description, start/end, category, date, external sync
9. **mission_pages** (9 fields) — Rich mission content: slug, content, XP, tags, event linkage
10. **contacts** (28 fields) — CRM: name, alias, email, phone, company, social links, trust level, contact frequency
11. **spreadsheets** (7 fields) — JSON spreadsheets: content JSONB, category
12. **push_subscriptions** (4 fields) — FCM tokens
13. **canvases** (8 fields) — Visual boards: content JSONB (shapes, connections, text)
14. **graphs** (8 fields) — Graph viz: content JSONB (nodes, edges, styling)
15. **folders** (11 fields) — Document folders: nested via parentId, external sync
16. **documents** (16 fields) — Documents: content, format, folder, external sync, file attachments
17. **templates** (9 fields) — Document templates: content, format, category, tags
18. **integrations** (10 fields) — OAuth records: provider, tokens, expiry, scope, status, settings
19. **progress_trackers** (11 fields) — Progress: current/target value, unit, dates, color
20. **kanban_boards** (6 fields) — Boards: title, description, isDefault
21. **kanban_columns** (6 fields) — Columns: boardId, title, status, order
22. **kanban_tasks** (10 fields) — Tasks: boardId, title, status, priority, dates, tags
23. **media_albums** (7 fields) — Photo albums: title, coverImage, smart rules
24. **media_items** (16 fields) — Media files: type, mime, url/data/path, thumbnail, metadata, location
25. **conversations** (5 fields) — AI chat threads: userId, title, deletedAt
26. **messages** (5 fields) — Chat messages: conversationId, role, content
27. **dismissed_knowledge** (5 fields) — Dismissed research: author, sourceMaterial
28. **vision_goals** (10 fields) — Vision milestones: category (5 horizons), title, bonusXp, completed
29. **user_categories** (5 fields) — Custom categories: value, label, description
30. **ritual_groups** (6 fields) — Ritual hierarchy: value, label, parentGroupValue
31. **widget_states** (3 fields) — Dashboard config: states JSONB
32. **user_activity_events** (5 fields) — Activity tracking: eventType, occurredAt, metadata
33. **smart_reminders** (9 fields) — Reminder config: type, hour, days, cooldown, lastSent
34. **mission_views** (8 fields) — Custom views: viewType, filters, columns, sorting
35. **waitlist_emails** (4 fields) — Waitlist: email, referralSource

---

## PART 4: NAVIGATION

### 4.1 Primary Navigation (5 tabs) [CODE_RESOLVED_CURRENT_TRUTH]

1. Dashboard
2. Missions
3. AI
4. Chronilog
5. Profile

### 4.2 Secondary Navigation [SOURCE_PRESERVED_TRUTH]

- Document Vault (/document-vault)
- Tracker (analytics, renamed from "Analytics")
- Settings
- Contacts
- Kanban
- Spreadsheets
- Canvases
- Graphs
- Media

### 4.3 Historical: PRD v1.0 Navigation [SOURCE_PRESERVED_TRUTH]

4-tab layout: Dashboard, Missions, AI, Systems. No Chronilog or Profile as primary. Superseded.

### 4.4 Historical: Phase 14.5 Navigation Claim [SOURCE_PRESERVED_TRUTH]

Listed 6 items including both Systems and Profile. Incorrect per operator correction.

---

## PART 5: AI COMPANION

### 5.1 Current Implementation [CODE_RESOLVED_CURRENT_TRUTH]

- **Default Name:** NOVA (user_stats.aiAssistantName, default "NOVA")
- **Renamable:** Yes (field in insert schema pick list)
- **Chat Model:** conversations + messages tables (threaded)
- **Legacy Model:** ai_messages table (flat)
- **AI SDKs:** Anthropic (@anthropic-ai/sdk 0.72.1), OpenAI (openai 4.96.0)

### 5.2 AI Capabilities [SOURCE_PRESERVED_TRUTH, from replit.md]

- **Roles:** Advisor, Coach, Executive Assistant
- **Model Routing:** Haiku (simple) -> Sonnet (complex/tools/images)
- **Data Ingestion (Salience Engine):** Full access to user profile, stats, missions, logs, vision milestones, calendar, conversation history
- **Streaming:** WebSocket-based (ws dep confirms)

### 5.3 AI Tools [SOURCE_PRESERVED_TRUTH, from replit.md]

1. Web search
2. Web page reading (puppeteer-core + cheerio + turndown)
3. Vision goal creation
4. Batch mission creation
5. Uncomplete missions (mark missions incomplete)
6. lookup_knowledge_base (active knowledge retrieval)
- Deep tool chaining supported

### 5.4 Knowledge Base [SOURCE_PRESERVED_TRUTH, from replit.md]

16 domains in server/replit_integrations/chat/knowledge-base.ts:
1. Philosophy
2. Sleep
3. Exercise
4. Nutrition
5. Psychology
6. Relationships
7. Finance
8. Learning
9. Productivity
10. Crisis Management
11. Modern Challenges
12. Breathwork
13. Advanced Nutrition
14. Functional Fitness
15. Biomarkers
16. Supplementation

Auto-topic detection injects relevant domains into system prompt.

### 5.5 Vision/Image Capability [SOURCE_PRESERVED_TRUTH, from replit.md]

- Direct image upload/paste in chat
- Auto-extraction from mission/goal/log descriptions (keyword-triggered)
- Base64 vision content blocks to Anthropic API (max 5 most recent)

---

## PART 6: GAMIFICATION

### 6.1 Stat Tokens [CODE_RESOLVED_CURRENT_TRUTH]

| Token | Fields | Default |
|-------|--------|---------|
| Energy | energyPointsCurrent/Max | 100/100 |
| Health | healthPointsCurrent/Max | 100/100 |
| Wealth | wealthTokensCurrent/Max | 100/100 |
| Time | timeTokensCurrent/Max | 100/100 |
| Attention | attentionTokensCurrent/Max | 100/100 |

### 6.2 XP System [CODE_RESOLVED_CURRENT_TRUTH]

- Base: 1000 XP for level 1
- Tier 1 (1-10): `1000 * 1.0372^(level-1)`
- Tier 2 (11-50): `tier1_cap * 1.0572^(level-10)`
- Tier 3 (51-100): `tier2_cap * 1.0872^(level-50)`
- Level cap: 100
- Fields: experienceCurrent, experienceMax, level (user_stats); totalXP (user_profile)

### 6.3 Mission Difficulty [CODE_RESOLVED_CURRENT_TRUTH]

Ranks: S (highest), A, B, C, D (default)

### 6.4 Mission Resource Costs [CODE_RESOLVED_CURRENT_TRUTH]

energyCost (default 1), attentionCost (default 0), timeCost (default 0)

### 6.5 Streaks [CODE_RESOLVED_CURRENT_TRUTH]

streakDays + lastActiveDate in user_stats. previousDayEnergyUsed for daily tracking.

### 6.6 Efficiency Score [CODE_RESOLVED_CURRENT_TRUTH]

efficiencyScore in user_stats. Computation logic in server code (not in snapshot).

### 6.7 Stat Detail Pages [SOURCE_PRESERVED_TRUTH]

7 dedicated pages: Experience, Health, Wealth, Efficiency, Energy, Time, Attention. Recharts visualizations, time range selectors, AI-powered insights.

### 6.8 Haptic Feedback [CODE_RESOLVED_CURRENT_TRUTH]

hapticFeedback boolean in user_profile (default true). Web Vibration API patterns: light tap, medium, heavy, success, level-up, notification.

### 6.9 Sound Effects [CODE_RESOLVED_CURRENT_TRUTH]

soundEffects boolean in user_profile (default true). Web Audio API synthesized sounds. No external audio files.

### 6.10 Confetti [CODE_RESOLVED_CURRENT_TRUTH]

canvas-confetti 1.9.3 in deps. Used for celebrations (level-ups, completions).

---

## PART 7: ONBOARDING

### 7.1 Mission Structure [CODE_RESOLVED_CURRENT_TRUTH]

- 8 missions (0-7): onboardingMission field, range 0-7
- Per-step tracking: onboardingStep field
- Completion: onboardingCompleted boolean
- History: completedOnboardingMissions (integer array), completedTutorials (text array)

### 7.2 Mission Content [CODE_RESOLVED_CURRENT_TRUTH + SOURCE_PRESERVED_TRUTH]

- **Mission 0 (Access & Quickstart):** ageRange, birthday, location, timezone
- **Mission 1 (Archetype Calibration):** 54-question assessment (replit.md), 6 archetypes
- **Missions 2-7:** Progressive onboarding through identity, personality, vision, learning, health, wealth sections (inferred from user_profile section organization)

### 7.3 Setup Mission Status [CODE_RESOLVED_CURRENT_TRUTH]

Legacy tracking: setupMissionStatus JSONB with keys: archetype, integrations, future_self, rituals, pillars (all default "incomplete").

---

## PART 8: AUTHENTICATION

### 8.1 Current Auth [CODE_RESOLVED_CURRENT_TRUTH]

- **Local:** Passport.js 0.7.0 + passport-local 1.0.0 + bcrypt 6.0.0
- **OAuth:** Firebase 11.6.1 (Google, Apple, Facebook)
- **Sessions:** express-session 1.18.1 + connect-pg-simple 10.0.0
- **2FA:** Firebase email + phone verification
- **Email:** Firebase Auth native (not Resend)
- **SMS:** Firebase Phone Auth (not Twilio)
- **Reverse Proxy:** `/__/auth/*` -> Firebase to avoid third-party cookie blocking

### 8.2 Future Auth [SYNTHESIZED_CANON]

- **Target:** Clerk authentication
- **Priority:** Lower than CreatorOS migration
- **Status:** Zero implementation. Future standardization effort.

---

## PART 9: INTEGRATIONS

### 9.1 Active [CODE_RESOLVED_CURRENT_TRUTH + SOURCE_PRESERVED_TRUTH]

- **Google Calendar:** Read/write sync, OAuth, deduplication, token refresh
- **Google Tasks:** Read-only import as missions
- **Firebase FCM:** Push notifications via token subscription

### 9.2 Schema Placeholders [CODE_RESOLVED_CURRENT_TRUTH]

- Apple Health (boolean flag, no SDK)
- Notion (boolean flag, no SDK)

### 9.3 Documented [SOURCE_PRESERVED_TRUTH]

- Obsidian import/export (.md, .zip)
- Evernote import/export (.enex)

### 9.4 Removed [CODE_RESOLVED_CURRENT_TRUTH]

- Stripe (removed, stub fields + endpoints preserved)
- Twilio (replaced by Firebase Phone Auth)
- Resend (replaced by Firebase Auth email)

---

## PART 10: SECONDARY FEATURES

### 10.1 Document Vault [CODE_RESOLVED_CURRENT_TRUTH + SOURCE_PRESERVED_TRUTH]

Tables: folders, documents, templates. Nested folders, markdown editing, media upload, bidirectional sync (Google Drive, Obsidian, Evernote), source badges, quick-filter chips.

### 10.2 Contacts [CODE_RESOLVED_CURRENT_TRUTH]

Table: contacts (30+ fields). CRM-style personal relationship management.

### 10.3 Kanban [CODE_RESOLVED_CURRENT_TRUTH]

Tables: kanban_boards, kanban_columns, kanban_tasks. 3-table normalized design.

### 10.4 Spreadsheets [CODE_RESOLVED_CURRENT_TRUTH]

Table: spreadsheets. JSONB content storage.

### 10.5 Canvases [CODE_RESOLVED_CURRENT_TRUTH]

Table: canvases. JSONB content (shapes, connections, text).

### 10.6 Graphs [CODE_RESOLVED_CURRENT_TRUTH]

Table: graphs. JSONB content (nodes, edges, styling).

### 10.7 Media Gallery [CODE_RESOLVED_CURRENT_TRUTH + SOURCE_PRESERVED_TRUTH]

Tables: media_albums, media_items. Albums with smart rules, inline images via RichTextToolbar, base64 storage.

### 10.8 Progress Trackers [CODE_RESOLVED_CURRENT_TRUTH]

Table: progress_trackers. Value/target with unit, dates, color.

### 10.9 Tracker Page [SOURCE_PRESERVED_TRUTH]

Renamed from "Analytics". Milestone analytics widget for vision goal progress and recent completions.

### 10.10 Smart Reminders [CODE_RESOLVED_CURRENT_TRUTH]

Table: smart_reminders. Per-type with preferred hour, days, cooldown.

### 10.11 Dismissed Knowledge [CODE_RESOLVED_CURRENT_TRUTH]

Table: dismissed_knowledge. Tracks dismissed research suggestions (author + source).

### 10.12 User Activity Events [CODE_RESOLVED_CURRENT_TRUTH]

Table: user_activity_events. Generic event tracking with eventType, metadata JSONB.

### 10.13 Waitlist [CODE_RESOLVED_CURRENT_TRUTH]

Table: waitlist_emails. Pre-launch email collection with referral source.

---

## PART 11: DEPLOYMENT AND INFRASTRUCTURE

### 11.1 Current [CODE_RESOLVED_CURRENT_TRUTH]

- **Host:** Replit
- **Domain:** lyfeos.net
- **Database:** Neon PostgreSQL (serverless)
- **Build:** Vite (frontend) + esbuild (backend)
- **Start:** `NODE_ENV=production node dist/index.js`
- **Health:** /api/health endpoint confirmed
- **PWA:** Manifest, service worker, install prompt, FCM push (SOURCE_PRESERVED_TRUTH)

### 11.2 Missing [INFERRED_PROFESSIONAL_GAP]

- No CI/CD pipeline
- No error tracking service
- No structured logging
- No analytics
- No confirmed backup strategy
- No RLS on 35 user-scoped tables
- No rate limiting library (may have custom middleware)
- No uptime monitoring

### 11.3 Future Target [SYNTHESIZED_CANON]

- Fly.io deployment
- PostHog analytics
- Clerk authentication
- Neon backup verification
- RLS implementation
- GitHub Actions CI/CD

---

## PART 12: UMH INTEGRATION LAYER

### 12.1 Current State [CODE_RESOLVED_CURRENT_TRUTH]

Exists at `/opt/OS/projections/lyfeos/integration/` (1184 lines, 7 files):
- manifest.py: 3 signals, 4 capabilities, 3 polled tables
- tables.py: Typed SQL helpers for quests, stats, daily_logs, vision_goals
- signals.py: SignalEmitter — builds SignalEnvelopes from polled rows
- handlers.py: CapabilityHandler — noop, create_quest, complete_quest, log_daily_reflection
- correlation.py: Thread-safe UUID -> writeback target mapping
- outcomes.py: OutcomeReceiver — dual writeback (source row + audit table)

### 12.2 Integration Method [CODE_RESOLVED_CURRENT_TRUTH]

Direct Postgres polling via LYFEOS_DATABASE_URL. UMH connects to LyfeOS database directly. LyfeOS application is unaware of UMH.

### 12.3 Future Integration [UMH_INTEGRATION_DEPENDENT_GAP]

LyfeOS registers as UMH projection. NOVA connects to UMH agent runtime. Auth, profile, memory, governance flow through UMH.

### 12.4 Complete End-State AI Companion (UMH Substrate) [UMH_INTEGRATION_DEPENDENT_GAP]

When fully connected to UMH, the AI companion becomes a governed, memory-persistent, cross-session intelligence:

- **AI routing:** NOVA's requests route through UMH model_router with full fallback chain (Opus/Sonnet/Haiku/Gemini/Ollama)
- **Capability-aware execution:** Every tool call (create mission, create vision goal, batch operations) is risk-classified and governed by UMH approval gates
- **Cross-session memory:** UMH memory subsystem persists important context, preferences, and patterns across conversations and sessions
- **User model evolution:** UMH salience engine builds and refines a user model from all LyfeOS data (profile, missions, logs, stats, conversations)
- **Quality scoring:** Every AI response is quality-scored with feedback loop for continuous improvement
- **Execution traces:** Full audit trail of every AI action — input, output, model used, latency, outcome, governance decision
- **Permission model (graduated trust):**
  - Auto-approved: knowledge base lookup, web search, reading user context
  - Confirmation required: creating missions, creating vision goals, batch operations
  - Operator-gated: deleting data, modifying profile fields, financial actions
  - Never automated: account deletion, auth changes, integration disconnection
- **Deterministic fallback:** When UMH is unavailable, NOVA falls back to local Anthropic SDK (current behavior) — AI features degrade gracefully, never break

---

## PART 13: DESIGN CONCEPTS NOT YET IMPLEMENTED

### 13.1 Transformation Thread [SOURCE_PRESERVED_TRUTH]

Referenced in prior phase artifacts. No code implementation. Concept: a thread that tracks the user's transformation journey over time. Preserved as future candidate.

### 13.2 Advanced AI Autonomy [SOURCE_PRESERVED_TRUTH]

From replit.md: "autonomous agent capabilities with deep tool chaining." Current implementation scope unclear from snapshot. Future direction toward more autonomous AI actions.

### 13.3 Blue Light Filter [CODE_RESOLVED_CURRENT_TRUTH]

Schema field exists (user_profile.blueLightFilter, default false). Implementation unknown — may be CSS filter or system-level.

---

## PART 14: OPEN QUESTIONS

### 13.4 Privacy and Compliance Vision [INFERRED_PROFESSIONAL_GAP]

LyfeOS stores deeply personal data (financial position, health metrics, psychological profile, relationship details, beliefs, shadow patterns). A privacy and compliance framework is not yet implemented but is essential for production maturity:

- **Data export:** Full user data export per GDPR Article 20 (data portability) — all 35 tables for a given userId
- **Account deletion:** Cascade deletion across all 35 tables with FK cascade already in schema
- **Sensitive data classification:** Financial (wealth section), health (body section), identity (personal details), psychological (beliefs, shadow, coping) — each needs a sensitivity tier
- **AI consent framework:** userStats.aiAssistantEnabled toggle exists; granular per-category permissions for what data AI can access are needed
- **Data retention policies:** No explicit retention limits currently; user-configurable retention for conversations and daily logs
- **GDPR compliance:** Required before EU user acquisition (right to be forgotten, data portability, consent tracking)
- **CCPA compliance:** Required before California user acquisition (opt-out of data sale, deletion on request)
- **Cookie consent:** Required for EU users if analytics/tracking is added
- **Privacy policy and terms of service:** Must exist before scaling beyond personal use
- **UMH data boundary:** When UMH is connected, strict redaction rules for sensitive fields before signal emission (financial amounts, health conditions, relationship details)

---

## PART 14: OPEN QUESTIONS

### 14.1 Operator Decisions Needed [OPEN_QUESTION_OPERATOR_DECISION_REQUIRED]

1. Rate limiting: Does custom middleware exist? What are the limits on AI endpoints?
2. Neon backups: Which plan? Are automatic backups confirmed active?
3. Session store: Is connect-pg-simple active in production, or memorystore?
4. NOVA knowledge base: Is the 16-domain knowledge base deployed and active?
5. Apple Health / Notion: Are these planned features or abandoned placeholders?
6. Obsidian/Evernote sync: Implemented or documented aspirations?
7. Smart reminders delivery mechanism: Push notification? In-app only?
8. Spreadsheets/Canvases/Graphs UI: How feature-complete are these?
