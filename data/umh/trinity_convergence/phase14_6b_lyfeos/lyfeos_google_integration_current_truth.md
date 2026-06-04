# LyfeOS Google Integration Current Truth

**Phase:** 14.6B-LyfeOS
**Artifact:** 36
**Operator Approved:** false
**Allows Implementation:** false
**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (from replit.md, schema.ts, server/routes/google.ts documentation)

---

## Architecture Overview

Google integration in LyfeOS provides bidirectional Calendar sync and read-only Tasks import. Routes live in `server/routes/google.ts`. Tokens are stored in the `integrations` table.

---

## OAuth Flow

1. **Auth URL Generation** (`GET /api/google/auth-url`)
   - Server generates Google OAuth consent URL
   - Scopes requested for Calendar and Tasks access
   - Redirect URI points back to LyfeOS callback

2. **Callback Token Exchange** (`GET /api/google/callback`)
   - Receives authorization code from Google
   - Exchanges code for access_token + refresh_token
   - Stores tokens in `integrations` table
   - Sets `google_calendar_connected = true` in `user_integrations` table

3. **Token Refresh** (automatic)
   - When access_token expires, refresh_token is used to obtain new access_token
   - Token expiry tracked in `integrations.token_expiry`
   - Automatic renewal on API calls

---

## Calendar Sync — Bidirectional

### Pull from Google (`POST /api/google/sync`)
- Fetches events from Google Calendar API
- Smart deduplication strategy:
  1. **Primary match:** `externalId` — if a calendar_event or quest already has this Google event ID, skip or update
  2. **Fuzzy match:** title + date + time comparison against both `calendar_events` and `quests` tables to avoid duplicates when same event exists locally
- Stores synced events in `calendar_events` table with:
  - `external_id`: Google Calendar event ID
  - `external_source`: "google" identifier

### Push to Google
- Local calendar events can be pushed to Google Calendar
- Creates Google Calendar events from local data
- Maintains `external_id` link for future sync cycles

### Unified Calendar View
- Missions page Calendar view renders both:
  - Local calendar events (from `calendar_events` table)
  - Scheduled missions (from `quests` table with start_date/start_time)
- Grouped by day with Google Calendar-style UI (year/month/week/day zoom)

---

## Tasks Import — Read-Only

### Fetch Tasks (`GET /api/google/tasks`)
- Retrieves task lists from Google Tasks API
- Returns task data for user preview

### Import Tasks (`POST /api/google/import-tasks`)
- Converts Google Tasks into LyfeOS missions (quests)
- Sets XP rewards on imported missions
- Deduplication via `external_id`/`external_source` fields on `quests` table
- One-way only: changes in LyfeOS do not sync back to Google Tasks

---

## Disconnect Flow (`POST /api/google/disconnect`)
- Removes tokens from `integrations` table
- Sets `google_calendar_connected = false` in `user_integrations` table
- UI: Connect/disconnect toggle on Profile Settings page

---

## Status Check (`GET /api/google/status`)
- Returns current connection status
- Checks token validity
- Reports last sync time from `integrations.last_synced_at`

---

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `GOOGLE_OAUTH_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Google OAuth client secret |

---

## Database Tables Involved

| Table | Role |
|-------|------|
| `integrations` | OAuth token storage (access_token, refresh_token, token_expiry, scope, status, settings) |
| `user_integrations` | Boolean flag: `google_calendar_connected` |
| `calendar_events` | Local + synced event storage (external_id, external_source for tracking) |
| `quests` | Missions — receives imported Google Tasks (external_id, external_source) |

---

## Security Concerns

### Token Storage (INFERRED_PROFESSIONAL_GAP)
- `access_token` and `refresh_token` stored in `integrations` table
- Column type is `text` — schema comment says "Encrypted access token" / "Encrypted refresh token"
- Whether application code actually encrypts before storage is **unverified**
- If stored in plaintext, anyone with database access can impersonate the user's Google account
- **Risk level:** HIGH if tokens are plaintext, LOW if properly encrypted
- **Required action:** Verify encryption implementation in server code

### Scope Minimization (INFERRED_PROFESSIONAL_GAP)
- Which Google OAuth scopes are requested is defined in server code
- Whether minimal necessary scopes are used is unverified
- Over-scoped OAuth grants increase blast radius if tokens are compromised

### Revocation (INFERRED_PROFESSIONAL_GAP)
- Whether the disconnect flow revokes the token with Google (not just deletes locally) is unverified
- Best practice: call Google token revocation endpoint on disconnect

---

## UMH Integration Points

The UMH integration bridge at `projections/lyfeos/integration/` does NOT currently interact with the Google integration. Future integration could:
- Emit signals when Google Calendar events are synced
- Allow UMH to create calendar events via capability
- Cross-reference calendar data with quest/mission data for scheduling intelligence
