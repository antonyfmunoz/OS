# LyfeOS Integration Architecture

**Phase:** 14.6B-LyfeOS
**Artifact:** 35
**Operator Approved:** false
**Allows Implementation:** false

---

## Current Integrations (CODE_RESOLVED_CURRENT_TRUTH)

### 1. Google Calendar — ACTIVE
- **Status:** Working bidirectional sync
- **OAuth flow:** Server-side via `server/routes/google.ts`
- **Token storage:** `integrations` table (access_token, refresh_token, token_expiry)
- **Sync mechanism:** Pull from Google + push to Google
- **Deduplication:** Smart dedup — externalId first, then fuzzy title+date+time matching against both calendar_events and quests tables
- **Token refresh:** Automatic access token renewal using refresh_token
- **Calendar events:** Stored in `calendar_events` table with `external_id`/`external_source` fields
- **Unified view:** Missions page Calendar view shows both local events and synced Google Calendar events
- **Env vars:** `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`
- **Provenance:** CODE_RESOLVED_CURRENT_TRUTH

### 2. Google Tasks — ACTIVE (Read-Only)
- **Status:** Working read-only import
- **Mechanism:** Import Google Tasks as missions with XP rewards
- **Deduplication:** Via `external_id`/`external_source` fields on quests table
- **Direction:** One-way (Google -> LyfeOS only)
- **Provenance:** CODE_RESOLVED_CURRENT_TRUTH

### 3. Firebase Auth — ACTIVE
- **Status:** Working OAuth provider and verification service
- **Functions:** Google/Apple/Facebook OAuth, email verification, password reset, 2FA (email + phone)
- **Reverse proxy:** `/__/auth/*` route proxies to Firebase for same-origin OAuth (avoids 3rd-party cookie blocking in Safari/Chrome)
- **Admin SDK:** `server/firebaseAdmin.ts` for server-side token verification
- **Push notifications:** Firebase Cloud Messaging (FCM) for push notification delivery
- **Env vars:** `VITE_FIREBASE_API_KEY`, `VITE_FIREBASE_PROJECT_ID`, `VITE_FIREBASE_APP_ID`, `VITE_FIREBASE_ACTUAL_PROJECT_ID`, `FIREBASE_SERVICE_ACCOUNT_KEY`
- **Provenance:** CODE_RESOLVED_CURRENT_TRUTH

### 4. Apple Health — FLAG ONLY
- **Status:** `apple_health_connected` boolean in `user_integrations` table
- **Actual integration:** NONE. No HealthKit API calls, no data import, no device connection
- **Classification:** Flag exists in schema, no implementation behind it
- **Provenance:** CODE_RESOLVED_CURRENT_TRUTH

### 5. Notion — FLAG ONLY
- **Status:** `notion_connected` boolean in `user_integrations` table
- **Actual integration:** NONE. No Notion API calls, no sync
- **Classification:** Flag exists in schema, no implementation behind it
- **Provenance:** CODE_RESOLVED_CURRENT_TRUTH

### 6. Anthropic AI — ACTIVE
- **Status:** Working AI integration for NOVA
- **SDK:** `@anthropic-ai/sdk` v0.72.1
- **Models:** Haiku for simple tasks, Sonnet for complex reasoning (smart routing)
- **Streaming:** SSE streaming responses
- **Tools:** 5+ tool functions (createMission, updateEnergyLog, web search, vision goal creation, batch mission creation)
- **Knowledge base:** 16-domain knowledge base with automatic topic detection
- **Vision:** Image analysis capability (base64 vision content blocks)
- **Provenance:** CODE_RESOLVED_CURRENT_TRUTH

### 7. OpenAI — ACTIVE (Fallback)
- **Status:** `openai` v4.96.0 in dependencies
- **Usage:** GPT-4o integration with keyword-based fallback (per replit.md)
- **Provenance:** CODE_RESOLVED_CURRENT_TRUTH

---

## Future Integrations

### Apple Health — Real Data (SOURCE_PRESERVED_FUTURE_CANON)
- Would provide LIVE_VERIFIED_DEVICE_API data for Health Points
- Steps, heart rate, sleep, activity data
- Would change Health stat provenance from USER_SELF_REPORT to LIVE_VERIFIED_DEVICE_API
- **Blocked by:** No HealthKit implementation, no device bridge

### Notion Sync (SOURCE_PRESERVED_FUTURE_CANON)
- Bidirectional document sync
- Flag exists but no implementation
- Would complement existing Data Vault (documents/folders)
- **Blocked by:** No Notion API integration

### Stripe Billing (IMPLEMENTATION_DEBT)
- Stripe was previously integrated and then removed
- Stub endpoints remain in code
- `stripe_customer_id` and `stripe_subscription_id` remain in users table
- Subscription page UI is intact
- **Blocked by:** Operator decision on billing timing

### UMH Substrate Integration (UMH_INTEGRATION_DEPENDENT_GAP)
- NOVA AI would connect to UMH model_router/agent architecture
- LyfeOS quests/stats would emit signals to UMH substrate
- UMH outcomes would write back to LyfeOS tables
- **Existing bridge:** `projections/lyfeos/integration/` (Python, 6 files, 1184 lines)
  - Signal emitter, capability handler, outcome receiver, correlation map
  - Tables: quests, user_stats, user_daily_logs, vision_goals
  - Capabilities: noop, create_quest, complete_quest, log_daily_reflection
  - Poll interval: 30 seconds
  - Env: `LYFEOS_DATABASE_URL`, `LYFEOS_USER_IDS`, `LYFEOS_POLL_INTERVAL`
- **Blocked by:** UMH integration boundary definition, operator decision

### PRD Integration Harmonization Flow (SOURCE_PRESERVED_FUTURE_CANON)
- 6-stage flow: Capture -> Translate -> Align -> Seed -> Forecast -> Surface
- Cross-platform events: life.energy_low, business.launch_scheduled
- Shared kernel: Identity, AI Runtime, Workflow Engine, Event Bus, Memory Graph
- **Status:** Aspirational architecture, no implementation contracts
- **Provenance:** SOURCE_PRESERVED_TRUTH (PRD v2.0)

---

## Integration Table Architecture

Two tables handle integrations:

1. **user_integrations** (flags table) — Boolean flags per integration type. Simple presence tracking.
2. **integrations** (tokens table) — Full OAuth token storage with provider, access_token, refresh_token, token_expiry, scope, status, settings.

The flag table predates the tokens table. Both are used simultaneously. Flag table tracks "is connected" state. Tokens table stores actual credentials.

---

## Security Concerns

1. **Token encryption:** `access_token` and `refresh_token` stored in `integrations` table. Column comment says "Encrypted" but whether actual encryption is applied before storage is unverified. (INFERRED_PROFESSIONAL_GAP)
2. **Token rotation:** Refresh tokens are used for automatic access token renewal. Refresh token rotation policy is unknown.
3. **Scope limitation:** Google OAuth scope stored in `scope` field. Whether minimal scopes are requested is unverified.
4. **Disconnect cleanup:** Google disconnect endpoint removes tokens. Whether all associated data is cleaned up is unverified.
