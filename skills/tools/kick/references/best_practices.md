# Kick — Creator-Level Best Practices
Source: docs.kick.com, github.com/KickEngineering/KickDevDocs, dev.kick.com, help.kick.com, streamer.kick.com/partner, community SDKs (kicksdk-go, KickLib, kickpython, kick.py)
API Version: Public API v1 (api.kick.com/public/v1) — launched 2024, expanded throughout 2025
SDK Version: No first-party SDK. Community: kickpython (Python), kick.py (Python async), KickLib (C#), kicksdk (Go), @nekiro/kick-api (Node)
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## Authentication

Kick uses **OAuth 2.0 with mandatory PKCE** for all flows. The authorization
server runs at `https://id.kick.com` and the resource server at
`https://api.kick.com/public/v1`. There is no API-key shortcut and no legacy
"client secret only" user flow — every authorization-code grant must carry
a `code_challenge` derived from a `code_verifier` per RFC 7636. Kick rejects
the request otherwise.

### Two token types

**App Access Token** — `grant_type=client_credentials`. Server-to-server.
Useful for any "read public data without acting on behalf of a user" call:
fetch a channel by slug, check whether a category exists, poll livestream
status. These tokens carry no user context and cannot post chat, take
moderator actions, or subscribe to events on a user's behalf.

**User Access Token** — `grant_type=authorization_code` plus PKCE. Required
the moment you need to act *as* a user. EOS uses this for: writing chat,
updating stream title, subscribing to events for a broadcaster, fetching the
authenticated user's profile, and reading stream key.

Both tokens are bearer tokens. Send as `Authorization: Bearer <token>`.

### PKCE flow, exact

1. `verifier = base64url(os.urandom(64))` — must be 43-128 unreserved chars.
2. `challenge = base64url(sha256(verifier.encode()).digest())`.
3. Redirect user to:
   ```
   https://id.kick.com/oauth/authorize
     ?response_type=code
     &client_id=<CLIENT_ID>
     &redirect_uri=<URL-encoded redirect>
     &scope=user:read+chat:write+events:subscribe
     &code_challenge=<challenge>
     &code_challenge_method=S256
     &state=<CSRF nonce, store in session>
   ```
4. User logs in, approves, Kick redirects to your `redirect_uri` with
   `?code=...&state=...`. Validate the state matches.
5. Exchange:
   ```
   POST https://id.kick.com/oauth/token
   Content-Type: application/x-www-form-urlencoded
   grant_type=authorization_code
   code=<code>
   client_id=<CLIENT_ID>
   client_secret=<CLIENT_SECRET>
   redirect_uri=<same redirect_uri>
   code_verifier=<original verifier>
   ```
6. Response: `{access_token, refresh_token, expires_in, token_type, scope}`.

Refresh:
```
POST https://id.kick.com/oauth/token
grant_type=refresh_token
refresh_token=<current>
client_id=<CLIENT_ID>
client_secret=<CLIENT_SECRET>
```
The refresh token rotates — store the new one immediately. Lose the
race between two workers refreshing simultaneously and the account is dead
until re-authorized.

### Scopes as of 2026-04-06

| Scope             | Allows                                       |
| ----------------- | -------------------------------------------- |
| `user:read`       | Read authenticated user profile              |
| `channel:read`    | Read channel metadata, chatroom id, status   |
| `channel:write`   | Update title, category, tags                 |
| `chat:write`      | POST chat messages                           |
| `streamkey:read`  | Read RTMP stream key (sensitive)             |
| `events:subscribe`| Create/list/delete webhook subscriptions     |

Request only the scopes you need per session. Asking for `streamkey:read`
unnecessarily turns the consent screen into a red flag and may scare users.

### EOS storage convention

`.env` (gitignored) holds app-level credentials:
```
KICK_CLIENT_ID=...
KICK_CLIENT_SECRET=...
KICK_REDIRECT_URI=https://...
```
Per-user tokens go in Neon `oauth_tokens`:
```sql
CREATE TABLE IF NOT EXISTS oauth_tokens (
  provider TEXT NOT NULL,
  user_id TEXT NOT NULL,
  broadcaster_user_id TEXT,
  access_token TEXT NOT NULL,
  refresh_token TEXT NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  scope TEXT NOT NULL,
  PRIMARY KEY (provider, user_id)
);
```
Encrypt at rest with the same Fernet key the rest of EOS uses for OAuth
tokens. Never log the full bearer string — log the last 6 chars only.

## Core Operations with Exact Signatures

All endpoints below are under base `https://api.kick.com/public/v1`. Methods,
path templates, and required scopes are stated. Field names are taken from
the public docs as of 2026-04-06; treat any field-level claim as
verify-before-build.

### Categories

```
GET /categories?q=<query>          # search by name
GET /categories/{category_id}      # fetch one
```
No auth scope beyond a valid app or user token.

### Users

```
GET /users                         # auth user (user:read)
GET /users?id=<id1>&id=<id2>       # batch by id
```

### Channels

```
GET /channels?slug=<slug>          # by slug, e.g. ?slug=antonyfmunoz
GET /channels?broadcaster_user_id=<id>
PATCH /channels                    # update — channel:write
  body: { "stream_title": "...", "category_id": 12345 }
```
The channel response carries the `chatroom_id` that the Pusher WebSocket
needs.

### Chat

```
POST /chat                         # chat:write
  body: {
    "broadcaster_user_id": <id>,
    "content": "<text>",
    "type": "user" | "bot"
  }
```
`type=bot` posts as the authenticated app rather than the user, when the
authenticated user is the broadcaster and has bot mode enabled.

### Livestreams

```
GET /livestreams?broadcaster_user_id=<id>
GET /livestreams?category_id=<id>&limit=<n>&sort=<field>
```
Returns currently-live streams matching the filter. There is no historical
archive endpoint — past streams must be fetched from the Creator Dashboard
via web automation.

### Public key

```
GET /public-key
```
Returns Kick's Ed25519 public key, used to verify webhook signatures.
Cache for ~24h, refetch on signature failure.

### Event subscriptions (webhooks)

```
GET    /events/subscriptions          # list current subs
POST   /events/subscriptions          # create
DELETE /events/subscriptions?id=<id>  # delete
```
Create body:
```json
{
  "method": "webhook",
  "broadcaster_user_id": 12345,
  "events": [
    {"name": "chat.message.sent",          "version": 1},
    {"name": "channel.followed",           "version": 1},
    {"name": "channel.subscription.new",   "version": 1},
    {"name": "channel.subscription.gifts", "version": 1},
    {"name": "channel.subscription.renewal","version": 1},
    {"name": "livestream.status.updated",  "version": 1},
    {"name": "livestream.metadata.updated","version": 1},
    {"name": "moderation.banned",          "version": 1},
    {"name": "kicks.gifted",               "version": 1}
  ]
}
```
Subscriptions belong to your app + that broadcaster. Re-creating the same
event for the same broadcaster returns the existing subscription id.

### Moderation

```
POST /moderation/bans       # channel:write or moderator
  body: { "broadcaster_user_id": ..., "user_id": ..., "duration": <secs|null>, "reason": "..." }
DELETE /moderation/bans     # unban
```

### Stream key

```
GET /streamkey              # streamkey:read
```
Returns the RTMP URL and key for the authenticated user's channel. Treat
the response like a password — never log, never commit, never display in
logs that might end up in Discord.

## Pagination Patterns

Kick's public API uses cursor pagination on list endpoints, not offset
pagination. The pattern across endpoints that return collections:

```json
{
  "data": [ ... ],
  "pagination": {
    "next_cursor": "abc123",
    "prev_cursor": null
  }
}
```

To page forward, pass `?cursor=<next_cursor>` on the next request. When
`next_cursor` is null, you have reached the end. Do not assume a fixed page
size — Kick returns what it returns, somewhere between 20 and 100 items
depending on endpoint.

Idiom for full-history pull (use sparingly — most workflows want a recent
window, not the whole archive):

```python
def paginate(url, headers, params):
    while True:
        r = requests.get(url, headers=headers, params=params, timeout=30)
        r.raise_for_status()
        body = r.json()
        for item in body.get("data", []):
            yield item
        cursor = body.get("pagination", {}).get("next_cursor")
        if not cursor:
            return
        params = {**params, "cursor": cursor}
```

The unofficial `api/v2` uses page-number pagination (`?page=N`) and is the
opposite shape. Do not mix the two in the same code path — pick a side.

## Rate Limits

Kick's public API rate limits are not exhaustively documented. Empirically
and from community libraries:

- Most read endpoints: in the low-hundreds per minute per app or per user.
- Chat write: tighter, on the order of ~10/sec sustained, with burst
  allowance. Mirrors Twitch IRC's old 20/30s for verified bots.
- 429 responses include a `Retry-After` header in seconds. Honor it.
- Auth endpoints (`/oauth/token`) are rate-limited separately — do not
  busy-loop refreshes.

EOS rules:

1. Single-flight token refresh — one process at a time per `(provider,
   user_id)`, gated on a Postgres advisory lock.
2. Exponential backoff on 429 with full jitter, max 60s, max 5 attempts.
3. Treat any 5xx as transient, retry up to 3 times with backoff.
4. Cap concurrent in-flight requests per app at 8 by default until you have
   measured the actual ceiling.
5. Build for the documentation tightening — assume the limit you saw last
   week may be lower this week.

## Error Codes and Recovery

Kick follows standard HTTP semantics with a JSON error body:

```json
{ "error": { "code": "invalid_token", "message": "Token expired", "status": 401 } }
```

| Status | Meaning                                  | Recovery                                       |
| ------ | ---------------------------------------- | ---------------------------------------------- |
| 400    | Bad request — bad body, bad params       | Fix the request. Do not retry.                 |
| 401    | Missing/expired/invalid token            | Refresh, then retry once. If refresh fails, re-auth. |
| 403    | Forbidden — insufficient scope or perms  | Do not retry. Check scopes on the token.        |
| 404    | Resource missing or not visible to you   | Cache the negative result. Do not loop.         |
| 409    | Conflict — duplicate sub, dup ban, etc.  | Treat as success in idempotent flows.           |
| 422    | Validation error                          | Fix the body. Do not retry.                     |
| 429    | Rate limited                              | Backoff per `Retry-After`.                      |
| 500    | Server error                              | Retry with backoff up to 3x.                    |
| 502/503/504 | Edge / upstream                      | Retry with backoff up to 3x.                    |

Specific error codes seen in the wild include `invalid_grant` (refresh token
rotated out), `invalid_scope` (asked for a scope not approved on your app),
`subscription_already_exists` (re-create on existing event), and
`broadcaster_not_found` (channel deleted or banned).

The single non-obvious recovery: on `invalid_grant` for a refresh, the token
is gone. Mark the user as "needs reauth" in Neon, surface in the operator
console, and stop retrying. Looping on `invalid_grant` will not recover.

## SDK Idioms

There is no first-party SDK. The community options sort into three buckets:

**Public API wrappers** (recommended for EOS):
- `kicksdk` (Go) — clean, typed, follows official endpoints. Good
  reference for what the API actually exposes.
- `KickLib` (C#) — most actively maintained, supports both official and
  unofficial endpoints.
- `kickpython` (Python) — thinnest layer, easy to read source, fine for
  scripts.

**Unofficial / `api/v2` wrappers** (avoid for production):
- `kick.py` (Python async) — covers a lot of surface but rides on the
  internal API. Will break.
- `@nekiro/kick-api` (Node) — same caveat.
- `fb-sean/kick-website-endpoints` (reference list, not a library) —
  useful purely as documentation of what endpoints exist on the site.

**Pusher chat wrappers**:
- `kickchatwrapper` (Go) — minimal, just enough to subscribe and stream.
- Any generic Pusher client (`pysher` for Python, `pusher-js` for Node)
  works as long as you know the channel naming convention.

EOS idiom: write a thin internal client (~200 lines) against the public API
in `eos_ai/connectors/kick.py`. It owns token refresh, signing-key cache,
backoff, and a single `request()` method. Higher-level "post a clip" or
"subscribe to channel events" methods sit on top. Do not pull a community
SDK into the dependency tree — the API is small enough that a wrapper is
not worth the supply-chain risk.

## Anti-Patterns

- **Using `api/v2` for anything you depend on.** It is the website's
  internal API. Cloudflare can lock it out, fields can change, the only
  contract is "what the website rendered today."
- **Skipping PKCE because you're a confidential client.** Kick still
  requires it. There is no opt-out.
- **Storing the refresh token in plain text in `.env`.** Refresh tokens
  are long-lived. Encrypt them, scope them per user, audit access.
- **Polling `/livestreams` every 30 seconds** instead of subscribing to
  `livestream.status.updated`. Burns rate limit and lags reality.
- **HMAC-SHA256 webhook verification copied from Twitch.** Kick uses
  Ed25519. Wrong primitive, every signature fails.
- **One global app token shared by all users.** App tokens grant zero user
  context — and any rate limit on that token is now shared across the
  whole fleet. Use per-user tokens whenever the operation is per-user.
- **Reaching for `streamkey:read` early.** Only request when wiring OBS;
  never as part of the default OAuth bundle.
- **Trusting category IDs across environments.** A category id from a
  community wiki may be stale. Always look up via `/categories?q=...`
  before posting.
- **Treating Kick clip URLs as permanent.** Clips can be made private, the
  channel can be banned, the URL can rot. Mirror the media to your own
  storage if it matters.
- **Pulling more than you need from the Pusher firehose.** Subscribing to
  every event on a high-traffic channel will exhaust your event handler.
  Filter at subscribe time, not at process time.

## Data Model

The core nouns:

- **User** — an account on Kick. Has `id`, `username`, `slug`, `email` (only
  visible to itself with `user:read`).
- **Channel** — every user has exactly one channel. The channel carries the
  `slug` (URL identifier), `stream_title`, current `category`, and a
  `chatroom_id`.
- **Chatroom** — a room owned by a channel. Has its own `id`, distinct from
  the channel id. Pusher subscriptions are by chatroom id.
- **Category** — a content tag. Hierarchical: there is a parent category
  (e.g. "Just Chatting", "Slots", a specific game) and sometimes a sub-tag.
- **Livestream** — a session of a channel going live. Has `started_at`,
  `viewer_count`, `is_mature`, and references the channel.
- **Clip** — a short user-created excerpt of a livestream. Has its own id,
  thumbnail, duration, and creator.
- **Subscription (paid)** — a viewer paying for the channel monthly.
  Distinct from the dev API "event subscription" — context-disambiguate.
- **Event subscription (webhook)** — an entry in your app saying "send me
  callbacks for these events on this broadcaster."
- **Ban** — moderator action on a user in a chatroom. Can be timed or
  permanent.
- **Kick (gift)** — Kick's native virtual currency / gift mechanism, like
  Twitch bits. Tracked via the `kicks.gifted` event.

Relationships in one diagram:
```
User 1—1 Channel 1—1 Chatroom 1—* Message
                  1—* Livestream 1—* Clip
                  1—* PaidSubscription
App  1—* EventSubscription —* targeting Broadcaster (User)
```

## Webhooks and Events

Kick's webhook system is the closest analog to Twitch EventSub. The flow:

1. Your app authenticates (app token or user token with `events:subscribe`).
2. POST `/events/subscriptions` with `method=webhook`,
   `broadcaster_user_id`, and a list of `(name, version)` events.
3. Kick stores the subscription and starts POSTing event payloads to the
   webhook URL configured on your app in the developer console.
4. Kick retries up to **3 times** until it gets a 2xx. After 3 failures
   (non-2xx, timeout, unreachable) Kick **silently unsubscribes**. EOS must
   poll `GET /events/subscriptions` periodically and re-create missing ones.
5. Each callback carries headers including `Kick-Event-Type`,
   `Kick-Event-Version`, `Kick-Event-Message-Id`, `Kick-Event-Message-Timestamp`,
   and `Kick-Event-Signature` (Ed25519).

### Verifying signatures (Ed25519)

```python
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature
import base64

def verify(public_key_pem: bytes, message_id: str, timestamp: str,
           body: bytes, signature_b64: str) -> bool:
    pub = Ed25519PublicKey.from_public_bytes(_load_pem_raw(public_key_pem))
    payload = f"{message_id}.{timestamp}.".encode() + body
    try:
        pub.verify(base64.b64decode(signature_b64), payload)
        return True
    except InvalidSignature:
        return False
```

Reject anything older than 5 minutes (replay protection) and dedupe on
`Kick-Event-Message-Id` for 24h.

### Events known as of 2026-04-06

- `chat.message.sent` — every chat message in the broadcaster's room
- `channel.followed` — new follow
- `channel.subscription.new` — new paid subscription
- `channel.subscription.renewal` — subscription auto-renewed
- `channel.subscription.gifts` — gifted subs
- `livestream.status.updated` — went live / went offline
- `livestream.metadata.updated` — title or category changed
- `moderation.banned` — moderator action
- `kicks.gifted` — viewer gifted Kicks (the virtual currency)

New events ship roughly quarterly. Re-check the GitHub issues on
`KickEngineering/KickDevDocs` before you assume an event does not exist.

## Limits

- **Max active webhook subscriptions per app**: not formally documented,
  treat as "low hundreds." Periodically prune unused subs.
- **Max events per subscription POST**: a few dozen — don't try to register
  the entire catalog in one call, batch by domain.
- **Chat message length**: 500 characters. Anything longer is rejected with
  422.
- **Chat send rate per user**: ~10/sec, with burst. Verified bot tier may
  be higher; not formally announced.
- **OAuth `state` and `code_verifier`**: 43-128 ASCII unreserved chars.
- **Token TTLs**: access tokens around 1 hour. Refresh tokens long-lived but
  rotate on every refresh.
- **Page sizes**: implicit, vary by endpoint. Always cursor-paginate, never
  assume a count.

## Cost Model

The Kick public API is **free**. There is no metered tier, no API key
purchase, no minimum spend. Cost realities for EOS:

- **Compute** to run a long-lived Pusher WebSocket subscriber and a webhook
  receiver. Sub-dollar/month at EOS scale on the existing VPS.
- **Storage** for clip mirrors and chat archives — ~100 MB per active
  channel-month if you store all chat and a representative clip set.
- **Indirect platform cost**: going Kick partner can cost up to ~50% of
  rev-share if you also multistream to Twitch/YouTube. This is the only
  cost line that actually matters and it is a business decision, not an
  infrastructure one.
- **Risk cost**: time spent rebuilding when an undocumented endpoint
  changes shape. The single largest mitigation is to stay on the public API.

## Version Pinning

There is no semver on the public API today. Versioning is per-event
(`version: 1`, `version: 2`) on event subscriptions, and per-route URL prefix
(`/public/v1`). To pin EOS to a known surface:

1. Pin to `/public/v1` in the connector base URL constant.
2. Pin event versions explicitly in every subscription POST.
3. Record `last_researched: 2026-04-06` in this file. Re-research at the
   start of any non-trivial Kick build.
4. Watch the `KickEngineering/KickDevDocs` GitHub repo issues + commits as
   the canonical changelog. There is no "release notes" page.
5. Community SDK versions: pin `kicksdk` (Go), `KickLib` (C#) by exact
   version in any prototyping. Do not let dependabot float them.

When the API ever introduces `/public/v2`, EOS will run both in parallel
behind a feature flag for one cycle, then cut over.

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

Kick exists because Twitch shipped two things its biggest creators hated:
the 50/50 sub split (with 70% reserved for top partners) and aggressive
content moderation. Kick is funded by Stake.com, an offshore crypto casino,
and the founding wedge was straightforward: pay creators more, ban less.
The 95/5 split is the headline; the policy tolerance for slots, gambling,
and political content is the second wedge.

The design tradeoffs follow from that origin:

- **Generous payout but volatile platform.** A platform underwritten by a
  casino can change overnight if regulators change overnight.
- **Fewer rules but uglier neighbors.** Slots streams dominate the front
  page on bad days. Brand-adjacency risk is real.
- **Faster partner ladder but smaller TAM.** Easier to get partner status,
  but the total addressable audience is a fraction of Twitch's.
- **Modern tech stack but immature surface.** The public API is younger
  and cleaner than Twitch Helix in some ways, but missing entire
  categories (no analytics endpoints, no scheduled stream API, no clips
  CMS).
- **No exclusivity at the standard tier**, but exclusivity exists in
  bespoke top-creator deals (Adin Ross-tier).

The platform is simultaneously a credible alternative and a strategic
hedge. EOS treats it as the latter until proven otherwise.

## Problem-Solution Map and Hidden Capabilities

- **Problem**: Discord ping when Antony goes live anywhere.
  **Solution**: webhook on `livestream.status.updated` → existing EOS
  webhook receiver → Discord channel post. Same pattern as Twitch EventSub.
- **Problem**: Auto-cross-post Twitch clips to Kick.
  **Solution**: poll Twitch for new clips, download via the standard
  Helix flow, upload to Kick via Playwright (no clip-upload public API yet).
- **Problem**: Continuous chat archive for retro analysis.
  **Solution**: Pusher subscriber in a tmux pane, stream to JSON Lines,
  rotate daily, ship to S3 weekly.
- **Problem**: "Is the audience converting?" without a public analytics API.
  **Solution**: nightly Playwright login to the Creator Dashboard, scrape
  the analytics tab, normalize into the EOS analytics schema. Treat as
  a separate skill once activated.
- **Problem**: Brand-safe category placement.
  **Solution**: category whitelist in EOS config. Reject any auto-update
  to a category not on the list. Default to "Just Chatting" or topical
  brand-safe categories.
- **Hidden capability**: `livestream.metadata.updated` fires on title and
  category changes. EOS can use this as a signal that the stream pivoted,
  and trigger a fresh clip-marker for repurposing.
- **Hidden capability**: `chat.message.sent` is the cleanest real-time
  social signal Kick exposes. Sentiment-tag in real time, surface chat
  highlights to the operator console.
- **Hidden capability**: the chatroom id is stable across livestreams, so
  a persistent Pusher connection can bridge multiple sessions without
  re-subscribing.

## Operational Behavior and Edge Cases

- **Cold-start OAuth**: the first time a user authorizes, the token has the
  scopes you requested at that moment. To add a scope later, you must
  re-run the consent flow. Plan scope sets in advance.
- **Chatroom id vs broadcaster id**: do not confuse them. The webhook API
  takes `broadcaster_user_id`. The Pusher API takes `chatroom_id`. They
  are different numbers on the same channel.
- **Banned users**: when a broadcaster is banned by Kick, every webhook
  subscription targeting them returns 404 on next refresh. Detect, log,
  notify operator. Don't auto-recreate against a banned id.
- **Stream went offline mid-poll**: livestream endpoints can return 404 the
  instant a stream ends. Treat 404 on a previously-200 stream as "ended,"
  not as "error."
- **Clock skew**: webhook signature verification is timestamp-sensitive.
  NTP-sync the EOS VPS or Ed25519 verification will reject everything.
- **Cloudflare challenge on `api/v2`**: if you fall back to the unofficial
  API and it stops returning JSON, the response is probably an HTML
  Cloudflare challenge. Detect by content type, fail loud.
- **Multiple processes refreshing the same token**: classic race. Always
  refresh under a Postgres advisory lock keyed on
  `(provider='kick', user_id)`.
- **Pusher reconnect**: Pusher connections drop. The client must
  auto-reconnect with backoff and re-subscribe to prior channels. Don't
  assume the connection is permanent.
- **Time of day**: Kick traffic peaks late evening US/EU time. API
  responses can be slower then. Set generous timeouts (15-30s) on read,
  short on write (5s).
- **Region variance**: viewer IP geography influences which categories
  appear "trending." Don't assume your operator's view is the same as
  every viewer's.

## Ecosystem Position and Composition

Kick sits in a four-platform live-streaming ecosystem with Twitch, YouTube
Live, and TikTok Live. Each has a different shape:

- **Twitch** — the incumbent. Largest audience, strictest content rules,
  lowest creator payout. Mature API, mature tooling, mature creator economy.
- **YouTube Live** — owned by Google. Best discovery via the YouTube
  recommendation engine. Excellent VOD lifecycle. Live is a feature, not
  the product.
- **TikTok Live** — vertical-first, mobile-first. Discovery is algorithmic.
  Monetization through gifts. Very different content shape (short, vertical,
  reactive).
- **Kick** — the challenger. Best payout, weakest discovery. Audience skews
  toward viewers who left or got banned from Twitch.

Compositional patterns:

- **OBS** is the universal source. One scene set, multiple destinations
  via stream key. (See the OBS skill, separate.)
- **Restream / Streamlabs Multistream** can fan out one OBS RTMP feed to
  multiple platforms simultaneously. Watch the Kick partner multistream
  rev-share clause.
- **Cross-post pipeline**: Twitch clip → mirror to S3 → upload to Kick
  (Playwright) → upload short to YouTube Shorts and TikTok (verticals are
  always exempt from Kick's multistream penalty).
- **Chat unification**: Pusher → Kick chat events; Twitch IRC → Twitch
  chat events; YouTube live chat polling → YouTube events. EOS can
  surface a unified chat timeline in the operator console.
- **Discord** as the persistent home base — every platform event lands
  in a Discord channel. Discord is where Antony actually reads them.

## Trajectory and Evolution

What changed in 2025 (from the GitHub commit history and changelog):

- May 2025: livestream metadata events shipped, moderation banned events
  shipped. The "events that matter for monitoring" set roughly tripled.
- October 2025: `kicks.gifted` shipped — first-class tracking of the
  native gift currency.
- 2025: Partner program lowered requirements. More creators eligible for
  the 95/5 split.
- 2025: Multistream feature shipped, with the rev-share-haircut clause
  immediately controversial. Vertical exception was the compromise.
- Late 2025: more endpoints added to the public API as community pressure
  on the unofficial `api/v2` got loud.

What is plausible for 2026:

- Public clip CMS endpoints (currently web-only).
- Public scheduled-stream endpoints.
- Public analytics endpoints — the obvious gap.
- Tighter rate limit enforcement as the API becomes load-bearing for more
  third parties.
- A `/public/v2` namespace if any breaking changes ship.

What is unlikely:

- Kick weakening the 95/5 headline. The whole brand depends on it.
- Kick dropping PKCE — security posture is going up, not down.
- Kick aligning content policy with Twitch — that would erase the wedge.

## Conceptual Model and Solution Recipes

Mental model: **Kick is a generously-paid frontier with thin guard rails.**
Treat every Kick automation as if the API surface might shift next month
and the platform might be regulator-shaped next quarter. Don't build deep,
build composable.

Recipes:

### Recipe 1 — Live event ping

1. App access token at startup, refresh on 401.
2. Subscribe `livestream.status.updated` for the broadcaster.
3. Webhook receiver verifies Ed25519 signature.
4. On `is_live=true`, post to Discord channel `#live-alerts`.
5. On `is_live=false`, archive the session metadata to Neon.

### Recipe 2 — Chat archive

1. Fetch channel by slug, extract `chatroom_id`.
2. Open Pusher connection, subscribe `chatrooms.<id>.v2`.
3. Stream `App\\Events\\ChatMessageEvent` to a JSON Lines file in
   `/var/lib/eos/kick-chat/<broadcaster>-YYYY-MM-DD.jsonl`.
4. Daily rotate, weekly upload to S3, monthly summary into Neon.
5. Reconnect on disconnect with exponential backoff.

### Recipe 3 — Cross-post clip from Twitch

1. Twitch EventSub fires `clip.created` for Antony's channel.
2. Download the MP4 via the Twitch clip download URL.
3. Run through ffmpeg to normalize: 1080p, h264, 30fps, AAC.
4. Upload to Kick via Playwright (web automation against the clip
   upload page) — no public clip upload API yet.
5. Generate a 15s vertical cut, upload to YouTube Shorts and TikTok
   in parallel (verticals exempt from any multistream penalty).
6. Log all five destinations in the EOS content registry.

### Recipe 4 — Subscription health check

1. Hourly cron: `GET /events/subscriptions`.
2. Diff against the EOS desired-state list.
3. Re-create any missing subscriptions.
4. Alert on three consecutive auto-unsubscribes (means the webhook
   endpoint is down or the signing is broken).

### Recipe 5 — Brand-safe stream title update

1. Operator sends "set kick title to X" to EOS.
2. EOS verifies category id against the brand whitelist.
3. PATCH `/channels` with `stream_title` and `category_id`.
4. Confirm via a follow-up GET. If the change didn't take, rollback to
   the previous title and alert the operator.

## Industry Expert and Cutting-Edge Usage

What top Kick creators and tooling builders are doing in 2026:

- **Multi-camera / 4k pipelines**: high-end streamers run NVENC encoding
  with high-bitrate ingest. Kick's ingest is permissive on bitrate compared
  to Twitch (which throttles to ~6 Mbps for non-Partners).
- **AI moderator assistants**: real-time chat sentiment + topic
  classification, with the model auto-flagging messages for human review.
  EOS can build this in a weekend on top of the Pusher chat stream.
- **Clip auto-curation**: a watcher process tags moments where chat
  velocity, emote density, or specific keywords spike, then auto-creates
  clips at those timestamps. Kick's chat firehose is the cleanest signal
  for this kind of system.
- **Cross-platform unified bots**: a single bot that serves Twitch IRC,
  Kick Pusher, YouTube live chat, and Discord with a shared command set.
  Operationally hard, but every serious multi-platform creator is moving
  this direction.
- **Vertical-first repurposing**: top creators publish Kick VODs and
  Shorts/Reels/TikToks in the same workflow. Kick's vertical-exempt
  multistream clause makes this strategically free.
- **Sponsorship attribution**: creators are logging webhook events into
  their own CRM and tying gifts/subs to specific stream segments — proving
  ROI to sponsors with cleaner data than Twitch makes available.
- **Bot detection arms race**: Kick is gradually tightening Cloudflare
  rules on `api/v2` and on the website. The cutting edge is moving toward
  the public API + Playwright with realistic browser fingerprints, not
  raw HTTP scrapes.

---

## EOS Usage Patterns

EOS uses Kick today exclusively as **infrastructure-on-standby** for
Antony's personal brand. The audience does not exist there yet, so the
goal is to be ready, not to be active.

### Pattern 1 — Platform evaluation cron

A weekly job:

1. Pull category sizes for "Just Chatting" and Antony's brand-adjacent
   categories.
2. Pull top-10 streams in those categories — viewer count, average watch
   time, chat velocity.
3. Score the platform on a 0-100 "is this worth showing up for" rubric
   and write to the EOS strategic dashboard.
4. If the score crosses a threshold, queue a reminder to the CEO in the
   morning brief: "Kick category opportunity flagged."

Goal: never miss a window where the platform is undervalued.

### Pattern 2 — Cross-post pipeline (dormant, ready)

The full clip cross-post pipeline (Recipe 3 above) is wired and unit-tested,
but disabled by a feature flag (`KICK_CROSSPOST_ENABLED=false`). Activation
is one env var change once Antony has a Kick channel and a clip backlog.
This is the canonical EOS pattern: build the infrastructure under a flag,
verify it cold, ship the flag flip when strategy says so.

### Pattern 3 — Personal brand unified live alerts

Once Kick is active, `livestream.status.updated` subscribes for Antony's
broadcaster id alongside Twitch EventSub and YouTube Live polling. The
existing `services/discord_bot.py` live-alert path takes a unified
`LiveEvent` shape — adding Kick is one source plug-in, no schema change.

### Pattern 4 — Multistream decision support

When and only when partner status is on the table, EOS produces a
written decision memo:

- Estimated Kick rev under exclusive 95/5 (audience × ARPU)
- Estimated Kick rev under multistream tier (haircut applied)
- Lost Twitch/YouTube rev if Kick-exclusive
- Brand-adjacency cost of Kick discovery placements
- Recommendation with an explicit confidence score

This memo is not generated automatically. It runs on `/decision-memo kick`
when Antony asks. Never hide a decision this load-bearing inside an
automated cron.

### Pattern 5 — Restream composition

Once activated, OBS pushes one feed to Restream, Restream fans out to Kick +
Twitch + YouTube simultaneously. EOS owns:

- The OBS scene preset (separate skill)
- The Restream destination config (separate skill, when added)
- The per-platform title sync (Kick `channel:write`, Twitch Helix, YouTube
  Live API)

EOS does not own the encoder. Antony is the encoder.

### Pattern 6 — Chat as a real-time social signal

When Antony streams on Kick, the Pusher chat subscriber runs in a tmux
pane and feeds the EOS event bus. Operator console highlights:
- Top 5 emotes in the last 60 seconds
- Sentiment trendline
- Any message containing brand keywords or the word "buy"
- Velocity spikes that suggest a clip-worthy moment

This is read-only intelligence. EOS does not auto-respond in chat without
explicit operator approval — chat is the audience's space.

## Gotchas

This section compounds over time. Add real failures as they happen.

- **The Public API is young (launched 2024).** Endpoints, scopes, and
  event names have shifted multiple times in 2025. Pin
  `last_researched: 2026-04-06` and re-verify before any non-trivial
  build. Watch `KickEngineering/KickDevDocs` GitHub issues for the
  changelog Kick refuses to publish elsewhere.
- **`api/v2` is NOT the public API.** It is the website's internal
  surface. Many community libraries use it. Cloudflare can lock you out.
  Fields can change without notice. Use it only for Playwright-style
  fallback paths where there is no public alternative.
- **PKCE is mandatory** even for confidential clients. No exceptions.
- **Refresh tokens rotate.** Save the new one or you brick the account.
  Use a single-flight lock to prevent two workers refreshing at once.
- **Webhook signatures are Ed25519, not HMAC-SHA256.** Don't reuse a
  Twitch verification function. Wrong primitive every time.
- **Three failed deliveries → silent unsubscribe.** Periodically reconcile
  desired vs actual subscription state. There is no auto-resubscribe.
- **Multistream policy is a financial trap.** Kick partner status with
  multistream to Twitch/YouTube can cut the rev share roughly in half.
  Vertical short-form is exempt — but the rules have shifted, re-verify
  before activating.
- **Stream key has its own scope.** Don't request `streamkey:read` in the
  default OAuth bundle.
- **Category policy is not Twitch policy.** Slots, gambling, and certain
  political categories that get you banned on Twitch are first-class on
  Kick. The reverse is also true — some Twitch-friendly categories are
  shadow-suppressed on Kick.
- **Top-creator exclusivity contracts exist** (Adin Ross-tier) even though
  the standard partner program does not require exclusivity. Read any
  partnership offer carefully.
- **No public analytics API.** Use Creator Dashboard scraping under a
  separate skill until Kick ships endpoints.
- **Rate limits documented poorly.** Implement exponential backoff with
  jitter, honor `Retry-After`, never busy-loop.
- **Cloudflare challenges look like JSON failures.** When `api/v2`
  suddenly returns HTML, that is a Cloudflare challenge. Detect by
  content-type and fail loud.
- **Pusher channel naming has changed.** `chatrooms.<id>` vs
  `chatrooms.<id>.v2` differ over time. Use a maintained client and pin
  the version.
- **NTP skew breaks Ed25519 verification.** Webhook timestamp validation
  rejects anything outside its window. Keep the VPS clock honest.
- **Token storage in Neon must be encrypted.** Refresh tokens are
  long-lived; treat them like passwords.
- **Brand-adjacency on the front page is a real cost.** Don't auto-update
  to whatever category the algorithm rewards — enforce a brand whitelist.
- **There is no public clip upload API.** Use Playwright. Expect the
  upload page DOM to drift.
- **The unofficial `kick.py` library uses different field names** than
  the public API. Don't mix them in the same model layer.
- **Going Kick-exclusive is a one-way door for content** — viewers who
  followed you on Twitch will not all migrate. The platform decision
  precedes the technical decision; don't let the technical decision
  hide the platform decision.
