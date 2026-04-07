# Twitch — Creator-Level Best Practices
Source: dev.twitch.tv/docs, dev.twitch.tv/docs/api/reference, dev.twitch.tv/docs/eventsub, dev.twitch.tv/docs/irc, github.com/twurple/twurple, github.com/PythonistaGuild/TwitchIO, github.com/tmijs/tmi.js
API Version: Helix (Kraken removed)
SDK Version: twitchio 2.10 (Python) / twurple 7.2 (TypeScript) / tmi.js 1.8 (chat)
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## Authentication

Twitch implements OAuth 2.0 with three usable token shapes plus an
authentication-only validation endpoint. Picking the wrong one is the single
most common cause of `401 Unauthorized` against Helix.

### Token shapes

**App access token** — server-to-server credential issued via the
`client_credentials` grant. Used for any Helix call that does NOT need to act
on behalf of a specific user (GetStreams, GetUsers, GetGames, GetClips by
broadcaster, GetVideos, EventSub webhook subscription create/list/delete).
Lives ~60 days, no refresh token — re-request when expired. There is exactly
one valid app access token per `(client_id, client_secret)` pair at a time;
re-issuing invalidates the previous one.

```bash
curl -X POST https://id.twitch.tv/oauth2/token \
  -d "client_id=${TWITCH_CLIENT_ID}" \
  -d "client_secret=${TWITCH_CLIENT_SECRET}" \
  -d "grant_type=client_credentials"
# {"access_token":"...", "expires_in":5184000, "token_type":"bearer"}
```

**User access token** — issued by the Authorization Code flow after a user
clicks "Authorize" on a Twitch consent screen. Required for any endpoint that
acts as that user: ModifyChannelInformation, CreateClip, CreateStreamMarker,
ManageRedemptions, SendChatMessage, StartCommercial, ManagePoll/Prediction,
EventSub WebSocket transport, and reading any private data scoped to the user
(subscriptions, followers, bits leaderboard).

Lifetime is **~4 hours**. Refresh proactively via the included `refresh_token`
at ~75% of `expires_in`. Refresh tokens are single-use — the response gives
you a NEW refresh token; persist it or you lose access.

```
GET https://id.twitch.tv/oauth2/authorize
  ?client_id={client_id}
  &redirect_uri={https-or-localhost}
  &response_type=code
  &scope=channel:manage:broadcast+clips:edit+channel:read:subscriptions+moderator:read:followers
  &state={csrf_nonce}
  &force_verify=true            (optional, makes Twitch always re-prompt)
```

```bash
# Exchange authorization code
curl -X POST https://id.twitch.tv/oauth2/token \
  -d "client_id=${CLIENT_ID}" \
  -d "client_secret=${CLIENT_SECRET}" \
  -d "code=${CODE_FROM_REDIRECT}" \
  -d "grant_type=authorization_code" \
  -d "redirect_uri=${REDIRECT_URI}"

# Refresh
curl -X POST https://id.twitch.tv/oauth2/token \
  -d "client_id=${CLIENT_ID}" \
  -d "client_secret=${CLIENT_SECRET}" \
  -d "grant_type=refresh_token" \
  -d "refresh_token=${REFRESH_TOKEN}"
```

**Device code flow** — for input-constrained devices and CLIs (Stream Deck,
TVs). User opens `twitch.tv/activate`, enters a short code; your CLI polls
`/oauth2/token` until the user completes. No browser embedding needed.

**Implicit grant** — fragment-only browser flow with no refresh token. Twitch
still serves it but it is officially discouraged for new apps. Don't use.

### Validation

Every request lifecycle should start with `/oauth2/validate` on boot. It is a
free, fast, definitive answer about token health.

```bash
curl -H "Authorization: OAuth ${TOKEN}" \
  https://id.twitch.tv/oauth2/validate
# {"client_id":"...", "login":"antonyfmunoz", "user_id":"...", "scopes":[...], "expires_in":13412}
```

Note the `OAuth` prefix here vs the `Bearer` prefix everywhere else. This is
historic and not a typo.

### Header requirements

EVERY Helix request must include both:
```
Authorization: Bearer <access_token>
Client-Id: <client_id>
```
Missing `Client-Id` returns 401 even with a perfect token. Missing
`Authorization` returns 401 with `Invalid OAuth token`. The SDKs handle this;
direct curl scripts forget half the time.

### Scope catalog (the ones that matter for EOS)

| Scope | Purpose |
|---|---|
| `channel:manage:broadcast` | ModifyChannelInformation, stream markers |
| `channel:read:subscriptions` | Subscriber list / EventSub channel.subscribe |
| `channel:manage:redemptions` | Create/manage channel point rewards |
| `channel:read:redemptions` | EventSub redemption events |
| `clips:edit` | CreateClip |
| `moderator:read:followers` | EventSub channel.follow v2 |
| `moderator:manage:banned_users` | Ban/timeout |
| `moderator:manage:chat_messages` | Delete chat messages |
| `user:write:chat` | POST /helix/chat/messages |
| `user:read:chat` | EventSub channel.chat.message |
| `bits:read` | Bits leaderboard, EventSub cheer |
| `channel:read:ads` | EventSub ad break begin |
| `channel:edit:commercial` | StartCommercial |

**Adding ANY scope retroactively forces every user to re-authorize.** Plan
the full scope list up front.

## Core Operations with Exact Signatures

All Helix endpoints are under `https://api.twitch.tv/helix/`. JSON request
bodies; query parameters for filters; results wrapped in `{"data":[...],
"pagination":{"cursor":"..."}}`.

### Streams

```
GET /helix/streams
  ?user_id={id}        (repeatable, max 100)
  ?user_login={login}  (repeatable, max 100)
  ?game_id={id}
  ?type=live
  ?language=en
  ?first=20
  ?after={cursor}
# Auth: app or user token
# Returns: id, user_id, user_login, game_id, type, title,
#          viewer_count, started_at, language, thumbnail_url, tags
```

Polling for "is Antony live right now?" is the canonical use; for production,
prefer EventSub `stream.online` and treat polling as the fallback.

### Users

```
GET /helix/users
  ?id={id}        (repeatable, max 100)
  ?login={login}  (repeatable, max 100)
# Returns: id, login, display_name, type, broadcaster_type,
#          description, profile_image_url, offline_image_url,
#          view_count (deprecated, returns 0), email (with user:read:email),
#          created_at
```

Use this to resolve `login → broadcaster_id` exactly once at app boot, cache
it, and never query again.

### Channels

```
GET /helix/channels?broadcaster_id={id}
PATCH /helix/channels?broadcaster_id={id}
  body: {
    "game_id": "1469308723",
    "broadcaster_language": "en",
    "title": "Live coaching Q&A",
    "delay": 0,
    "tags": ["coaching","entrepreneurship"],
    "content_classification_labels": [...],
    "is_branded_content": false
  }
# PATCH requires user token with channel:manage:broadcast,
# broadcaster_id MUST equal the authenticated user.
```

### Videos / VODs

```
GET /helix/videos
  ?id={id}                (repeatable, max 100)
  ?user_id={id}           (mutually exclusive with id and game_id)
  ?game_id={id}
  ?language=&period=&sort=&type=
  ?first=20&after={cursor}
# Returns: id, user_id, title, description, created_at, published_at,
#          url, thumbnail_url, viewable, view_count, language, type,
#          duration ("1h2m3s"), muted_segments
```

### Clips

```
GET /helix/clips
  ?broadcaster_id={id}    (one of)
  ?game_id={id}
  ?id={id}                (repeatable, max 100)
  ?started_at=&ended_at=
  ?first=20&after=&before=

POST /helix/clips
  ?broadcaster_id={id}
  ?has_delay=true|false   (true adds ~5s delay so a moderator can review)
# Auth: user token with clips:edit
# Returns immediately with {id, edit_url}; clip is processing for ~15s.
```

### Games / Categories

```
GET /helix/games
  ?id={id}    (repeatable, max 100)
  ?name={n}   (repeatable, max 100)
  ?igdb_id={id}
GET /helix/games/top?first=20
```

### Channel Editors

```
GET /helix/channels/editors?broadcaster_id={id}
# Auth: user token, channel:read:editors
```

### Channel Points / Custom Rewards

```
POST   /helix/channel_points/custom_rewards?broadcaster_id={id}
GET    /helix/channel_points/custom_rewards?broadcaster_id={id}&id={id}&only_manageable_rewards=true
PATCH  /helix/channel_points/custom_rewards?broadcaster_id={id}&id={reward_id}
DELETE /helix/channel_points/custom_rewards?broadcaster_id={id}&id={reward_id}

GET    /helix/channel_points/custom_rewards/redemptions
  ?broadcaster_id={id}&reward_id={id}&status=UNFULFILLED|FULFILLED|CANCELED
PATCH  /helix/channel_points/custom_rewards/redemptions
  ?id={id}&broadcaster_id={id}&reward_id={id}
  body: {"status": "FULFILLED"}
# Auth: user token, channel:manage:redemptions
# Only rewards created by YOUR client_id are manageable. Default Twitch rewards are read-only.
```

### Polls / Predictions

```
POST /helix/polls          body: {broadcaster_id, title, choices[], duration}
PATCH /helix/polls         body: {broadcaster_id, id, status: TERMINATED|ARCHIVED}
POST /helix/predictions    body: {broadcaster_id, title, outcomes[], prediction_window}
PATCH /helix/predictions   body: {broadcaster_id, id, status: RESOLVED|CANCELED|LOCKED, winning_outcome_id}
```

### Chat (Helix transport)

```
POST /helix/chat/messages
  body: {
    "broadcaster_id": "...",
    "sender_id": "...",
    "message": "hello",
    "reply_parent_message_id": "..."   (optional)
  }
# Auth: user token with user:write:chat (sender_id must be the auth user)
# Rate-capped per sender; for high-frequency send, use IRC.
```

### Schedule

```
GET   /helix/schedule?broadcaster_id={id}
POST  /helix/schedule/segment   body: {broadcaster_id, start_time, timezone, duration, is_recurring, category_id, title}
PATCH /helix/schedule/segment?broadcaster_id={id}&id={seg_id}
DELETE /helix/schedule/segment?broadcaster_id={id}&id={seg_id}
```

### Moderation

```
POST   /helix/moderation/bans      body: {data:{user_id, duration, reason}}
DELETE /helix/moderation/bans?broadcaster_id&moderator_id&user_id
GET    /helix/moderation/banned    ?broadcaster_id
GET    /helix/moderation/chatters  ?broadcaster_id&moderator_id
DELETE /helix/moderation/chat?broadcaster_id&moderator_id&message_id
```

### Ads

```
POST /helix/channels/commercial   body: {broadcaster_id, length: 30|60|90|120|150|180}
GET  /helix/channels/ads?broadcaster_id
```

## Pagination Patterns

Helix uses **cursor pagination** uniformly. Every list response includes
`pagination.cursor` (omitted on the last page). Pass it back as `after=`.

```python
def paginate(url, params, headers):
    while True:
        r = requests.get(url, params=params, headers=headers).json()
        for item in r["data"]:
            yield item
        cursor = r.get("pagination", {}).get("cursor")
        if not cursor:
            return
        params["after"] = cursor
```

`first` controls page size, max 100 for most endpoints (some are 20 or 50 —
GetClips is 100, GetVideos is 100, GetFollowedStreams is 100, GetTopGames is
100). Going over the max returns 400. There is no `total` field on most
endpoints — you cannot know the total count without paginating.

A handful of endpoints (GetClips, GetUsersFollows-deprecated) support
`before=` for backwards pagination. Most don't. EventSub subscription list
returns a cursor too.

## Rate Limits

Helix enforces a **token bucket per app access token** of 800 points per
minute. Most calls cost 1 point; bulk reads (GetStreams with multiple
user_logins) still cost 1. Some moderation calls cost 1 per item.

User access tokens have a **separate, smaller bucket** (~30 points/sec
sustained, varies by endpoint). Send Chat Messages has its own per-channel
limit (20 messages / 30s for non-mods, 100 / 30s for mods/broadcaster).

The bucket state is in response headers — these are authoritative, never
estimate:
```
Ratelimit-Limit: 800
Ratelimit-Remaining: 793
Ratelimit-Reset: 1712419200      (epoch seconds when bucket refills)
```

On 429, sleep until `Ratelimit-Reset`. The error body includes
`{"error":"Too Many Requests","status":429,"message":"..."}` with a hint.

EventSub subscription **count** is also limited: 3 webhook subscriptions per
broadcaster per app for events that don't require user auth, ~300 total per
app, and per-user EventSub WebSocket caps. The HTTP error on hitting these is
`409 Conflict` (duplicate subscription) or `429 Too Many Requests`.

IRC chat has its own connection-level limits: 20 JOINs per 10 seconds, 20
authentication attempts per 10 seconds, message rates as above.

## Error Codes and Recovery

Helix uses standard HTTP semantics with consistent JSON error envelopes:

```json
{"error":"Bad Request","status":400,"message":"Missing required parameter \"broadcaster_id\""}
```

| Code | Meaning | Recovery |
|---|---|---|
| 400 | Bad request — missing/malformed param | Fix request shape; do not retry |
| 401 | Token invalid, expired, or wrong type (app vs user) | Validate via `/oauth2/validate`; refresh if user token; re-issue if app token |
| 403 | Token valid but missing scope, or broadcaster_id ≠ authenticated user | Re-OAuth with the missing scope; check identity match |
| 404 | Resource doesn't exist or you can't see it | Don't retry |
| 409 | Conflict — usually a duplicate EventSub subscription | Look up existing subscription, reuse |
| 422 | Semantically valid but rejected (e.g. clip create when offline) | Don't retry; surface to user |
| 429 | Rate limited | Sleep until `Ratelimit-Reset` |
| 500/502/503/504 | Twitch-side | Exponential backoff: 1s, 2s, 4s, 8s, max 5 tries |

EventSub-specific failure modes:
- **`webhook_callback_verification_failed`** — your callback didn't echo the
  challenge in time. The subscription is killed; recreate.
- **`notification_failures_exceeded`** — Twitch tried to deliver and got
  non-2xx repeatedly. Subscription is disabled. Recreate.
- **`authorization_revoked`** — user revoked the OAuth grant. Subscription
  killed. Re-prompt the user.
- **`user_removed`** — broadcaster account deleted/banned. Don't retry.
- **`version_removed`** — you subscribed to a deprecated event version
  (e.g. `channel.follow` v1). Migrate to the new version.

IRC-specific failure modes:
- **NOTICE * :Login authentication failed** — bad oauth password (forgot
  `oauth:` prefix, or token expired/scope-stripped).
- **PING/PONG miss** — Twitch sends `PING :tmi.twitch.tv` every ~5 min; you
  must reply `PONG :tmi.twitch.tv`. Miss it and you get RECONNECT or silent
  disconnect.
- **NOTICE :Improperly formatted auth** — missing `PASS oauth:...` before
  `NICK`.

## SDK Idioms

### twitchio (Python, async)

`twitchio` (PythonistaGuild) is the canonical Python SDK. Built on `aiohttp`,
async-native, supports IRC bots, Helix calls, EventSub WebSocket.

```python
from twitchio.ext import commands
import twitchio

class EOSBot(commands.Bot):
    def __init__(self):
        super().__init__(
            token=os.environ["TWITCH_USER_ACCESS_TOKEN"],
            client_secret=os.environ["TWITCH_CLIENT_SECRET"],
            prefix="!",
            initial_channels=["antonyfmunoz"],
        )

    async def event_ready(self):
        print(f"Ready as {self.nick}")

    async def event_message(self, message):
        if message.echo:
            return  # ignore own messages
        await self.handle_commands(message)

    @commands.command()
    async def arena(self, ctx: commands.Context):
        await ctx.send("Initiate Arena: lyfeinstitute.com")

    @commands.command()
    async def uptime(self, ctx: commands.Context):
        stream = (await self.fetch_streams(user_logins=["antonyfmunoz"]))
        if not stream:
            await ctx.send("offline")
            return
        delta = datetime.utcnow() - stream[0].started_at.replace(tzinfo=None)
        await ctx.send(f"up {delta}")

EOSBot().run()
```

twitchio also exposes a Helix client (`bot.fetch_*` and `bot.create_clip`)
that handles auth headers, pagination, and rate-limit backoff.

### twurple (TypeScript)

`twurple` is the modern TypeScript stack and the most actively maintained
Twitch library overall. Modular packages: `@twurple/api`, `@twurple/auth`,
`@twurple/chat`, `@twurple/eventsub-http`, `@twurple/eventsub-ws`,
`@twurple/pubsub` (deprecated alias for EventSub).

```ts
import { ApiClient } from '@twurple/api';
import { RefreshingAuthProvider } from '@twurple/auth';

const auth = new RefreshingAuthProvider({ clientId, clientSecret });
auth.onRefresh(async (userId, newToken) => persist(userId, newToken));
await auth.addUserForToken(savedToken, ['chat']);
const api = new ApiClient({ authProvider: auth });

const stream = await api.streams.getStreamByUserName('antonyfmunoz');
console.log(stream?.title);
```

`RefreshingAuthProvider` is the killer feature — handles token refresh +
persistence callbacks automatically.

EventSub WebSocket:

```ts
import { EventSubWsListener } from '@twurple/eventsub-ws';
const listener = new EventSubWsListener({ apiClient: api });
listener.start();
listener.onChannelFollow(userId, userId, e =>
  console.log(`${e.userDisplayName} followed`));
```

### tmi.js (chat-only, Node)

`tmi.js` is the original Twitch IRC library — connection mgmt, reconnect,
event-based PRIVMSG handling. Use when you only need chat and don't want a
full SDK.

```js
const tmi = require('tmi.js');
const client = new tmi.Client({
  options: { debug: false },
  identity: { username: 'antonyfmunoz', password: `oauth:${process.env.TOKEN}` },
  channels: ['antonyfmunoz']
});
client.connect();
client.on('message', (channel, tags, message, self) => {
  if (self) return;
  if (message === '!arena') client.say(channel, 'lyfeinstitute.com');
});
client.on('cheer', (channel, userstate, message) => { /* bits */ });
client.on('subscription', (channel, username, method, message, userstate) => { /* T1 sub */ });
client.on('raided', (channel, username, viewers) => { /* incoming raid */ });
```

### Versioning of SDKs

- twitchio is on 2.x; the 3.0 alpha rewrite is incompatible — pin `twitchio>=2.10,<3`.
- twurple is on 7.x; major versions break monthly enough to pin minor.
- tmi.js is feature-frozen at 1.8 — fine for chat, but EventSub work should
  use twurple instead.

## Anti-Patterns

- **Polling `/helix/streams` every 30 seconds** when you could subscribe to
  `stream.online` once. The polling burns rate limit AND has up to 30s
  latency vs sub-second EventSub.
- **Storing tokens in source control or hardcoding them.** Always env vars.
- **Ignoring `Ratelimit-Remaining`** and only handling 429. By the time 429
  comes, you've already wasted retries; check headers proactively.
- **Verifying EventSub HMAC after JSON-decoding the body.** Decoder
  whitespace/escaping changes the bytes; HMAC must run on raw request body.
- **Treating `login` as a stable identifier.** Users can rename. Use
  `user_id` everywhere internally.
- **One subscription per redemption type per user instead of one per
  broadcaster.** Channel point reward redemptions come through ONE EventSub
  topic with `reward.id` in the payload — filter client-side, don't make
  N subscriptions.
- **Catching all errors and retrying.** 4xx errors (except 429) will never
  succeed on retry; you'll just burn quota. Retry only 5xx and 429.
- **Treating IRC as send-only.** IRC's value is sub-100ms inbound; if you
  drop received messages because you only care about commands, you lose
  USERNOTICE (subs/raids/bits) which only IRC delivers in real-time outside
  EventSub.
- **Forgetting `CAP REQ :twitch.tv/tags twitch.tv/commands twitch.tv/membership`**
  on IRC connect. Without it you don't get badges, bits, USERNOTICE, JOIN/PART.
- **Subscribing to EventSub from a localhost callback.** Webhook callbacks
  must be public HTTPS. For local dev, use the Twitch CLI's `event verify`
  and `event trigger` commands or a tunneling service.
- **Building your own OAuth flow when twurple's `RefreshingAuthProvider` or
  twitchio's built-in handle it.** Re-implementing token refresh is where
  every junior Twitch dev wastes a week.

## Data Model

The Twitch object graph centers on the **broadcaster** (a user who has at
least streamed once). Everything attaches to a broadcaster_id.

```
User (id, login, display_name, broadcaster_type)
 └── Channel (broadcaster_id, title, game_id, tags, language)
      ├── Stream (id, started_at, viewer_count, type=live)         (only when live)
      │    └── StreamMarker (id, position_seconds, description)
      ├── Video / VOD (id, duration, url, type=archive|highlight|upload)
      │    └── MutedSegment (duration, offset)
      ├── Clip (id, broadcaster_id, creator_id, video_id, vod_offset, duration)
      ├── CustomReward (id, title, cost, prompt, is_enabled)
      │    └── RewardRedemption (id, user_id, status, redeemed_at)
      ├── Poll / Prediction
      ├── Subscriber (user_id, tier, is_gift, gifter_id)
      ├── Follower (user_id, followed_at)
      ├── Schedule
      │    └── ScheduleSegment (start_time, duration, category_id, is_recurring)
      └── ModerationState
           ├── BannedUser, BlockedTerms, AutoMod settings
           └── Chatter (user_id)
```

`broadcaster_type` is `""`, `"affiliate"`, or `"partner"` — gates monetization
features. Affiliate unlocks subs/bits; Partner adds higher revenue split,
priority support, and (historically) transcoding guarantees.

A `Stream` only exists while live. The `id` of a stream is NOT the same as
the resulting VOD `id`. To map stream → VOD, use `GET /helix/videos?user_id=...&type=archive`
and match by `created_at` ≈ stream `started_at`.

A `Clip` references both `broadcaster_id` and `video_id` (the parent VOD)
plus `vod_offset` (seconds into the VOD where the clip begins). This is the
hook for the EOS post-stream clipping pipeline: walk new clips after a
stream, fetch their `vod_offset`, line them up against chat density.

## Webhooks and Events

EventSub is THE push mechanism. There is no other Twitch webhook system in
2026 — "Twitch Webhooks v1" was retired. EventSub has two transports for
identical event payloads:

### Webhook transport (HTTPS POST)

```
POST https://api.twitch.tv/helix/eventsub/subscriptions
{
  "type": "channel.subscribe",
  "version": "1",
  "condition": {"broadcaster_user_id": "12345"},
  "transport": {
    "method": "webhook",
    "callback": "https://your.example.com/twitch/eventsub",
    "secret": "32+ char string"
  }
}
```

Twitch sends an immediate **verification challenge**:
```
POST /twitch/eventsub
Twitch-Eventsub-Message-Type: webhook_callback_verification
Twitch-Eventsub-Subscription-Type: channel.subscribe
{"challenge":"abc123","subscription":{...}}
```

You MUST respond within 10 seconds with HTTP 200 and body `abc123` as
`text/plain` (or include challenge in JSON — plain text is safest). Miss
this and the subscription dies forever.

Subsequent events:
```
POST /twitch/eventsub
Twitch-Eventsub-Message-Id: ...
Twitch-Eventsub-Message-Timestamp: ...
Twitch-Eventsub-Message-Signature: sha256=...
Twitch-Eventsub-Message-Type: notification
Twitch-Eventsub-Subscription-Type: channel.subscribe
Twitch-Eventsub-Subscription-Version: 1
{"subscription":{...},"event":{...}}
```

**HMAC verification** (the most-failed step):
```python
import hmac, hashlib
def verify(headers, raw_body, secret):
    msg = (headers["Twitch-Eventsub-Message-Id"]
         + headers["Twitch-Eventsub-Message-Timestamp"]
         + raw_body.decode())
    expected = "sha256=" + hmac.new(
        secret.encode(), msg.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, headers["Twitch-Eventsub-Message-Signature"])
```

Reject and 403 if invalid. Also dedupe by `Message-Id` (Twitch may retry) and
reject events older than 10 minutes (replay protection).

### WebSocket transport

Open a connection to `wss://eventsub.wss.twitch.tv/ws`. First message is a
`session_welcome` containing `session.id`. Use that id when creating the
EventSub subscription:

```json
{
  "type": "channel.follow",
  "version": "2",
  "condition": {"broadcaster_user_id": "...", "moderator_user_id": "..."},
  "transport": {"method": "websocket", "session_id": "AQoQ..."}
}
```

Subsequent frames carry `session_keepalive` (every ~10s; if you miss two,
reconnect), `notification` (the actual events), `session_reconnect` (Twitch
asks you to switch to a new URL), and `revocation` (subscription killed).

### Topic catalog (most useful for EOS)

| Topic | Trigger | Required scope |
|---|---|---|
| `stream.online` | Broadcaster goes live | none (app token) |
| `stream.offline` | Broadcaster ends stream | none |
| `channel.update` | Title/category/language changed | none |
| `channel.follow` v2 | New follower | `moderator:read:followers` |
| `channel.subscribe` | New paid sub | `channel:read:subscriptions` |
| `channel.subscription.gift` | Gift subs purchased | `channel:read:subscriptions` |
| `channel.subscription.message` | Resub with chat msg | `channel:read:subscriptions` |
| `channel.cheer` | Bits cheered | `bits:read` |
| `channel.raid` | Incoming/outgoing raid | none |
| `channel.ban` / `channel.unban` | Moderation | `channel:moderate` |
| `channel.channel_points_custom_reward_redemption.add` | Reward redeemed | `channel:read:redemptions` |
| `channel.poll.begin/progress/end` | Poll lifecycle | `channel:read:polls` |
| `channel.prediction.begin/progress/lock/end` | Prediction lifecycle | `channel:read:predictions` |
| `channel.hype_train.begin/progress/end` | Hype train | `channel:read:hype_train` |
| `channel.ad_break.begin` | Ad starts | `channel:read:ads` |
| `channel.chat.message` | Every chat msg | `user:read:chat` |
| `channel.chat.notification` | USERNOTICE (sub/raid/etc) | `user:read:chat` |
| `channel.shoutout.create/receive` | Shoutout | `moderator:read:shoutouts` |
| `user.update` | User profile changed | none |

## Limits

| Resource | Limit |
|---|---|
| Helix rate limit (app) | 800 points/min |
| Helix rate limit (user) | per-endpoint, ~30/s sustained |
| Send chat (user) | 20 msgs / 30s (mod: 100) |
| Send chat (broadcaster slow mode) | configurable per channel |
| EventSub webhook subs per broadcaster (no user auth) | 3 per app |
| EventSub total subs per app | ~10,000 (cost-weighted) |
| EventSub WebSocket subs per session | 300 |
| EventSub max sessions per user | 3 |
| EventSub callback URL response timeout | 10s |
| Clip duration | 5-60 seconds |
| Clip max age for creation | must be created during/just after live |
| VOD retention | 14 days for Affiliate, 60 days for Partner / Turbo / Prime |
| VOD highlights / uploads | indefinite |
| Stream marker description | 140 chars |
| Channel title | 140 chars |
| Tags per channel | 10 custom tags, 25 chars each |
| Custom rewards per channel | 50 |
| Poll choices | 2-5, max 25 chars each |
| Poll duration | 15-1800 seconds |
| Prediction outcomes | 2-10 |
| Prediction window | 30-1800 seconds |
| Raid limit | 1 outgoing raid per ~10 minutes |
| IRC JOIN rate | 20 channels / 10 seconds |
| EventSub event delivery retries | 5 attempts over ~6 hours |

## Cost Model

**Twitch APIs are free.** No per-call fees, no tier upgrades, no API keys
behind a paywall. The only billing surface is the developer console (free).

**Creator-side monetization** (where money flows):

- **Bits** — viewers buy bits in bulk; each bit cheered to a channel pays the
  broadcaster $0.01. Bits aren't free for viewers; they're a Twitch SKU.
- **Subscriptions** — T1 ($5.99), T2 ($9.99), T3 ($24.99). Standard split is
  50/50 with Twitch; Partners with traction negotiate up to 70/30. Prime subs
  count as T1 and pay slightly less.
- **Ads** — pre-roll, mid-roll, post-roll. Affiliate+ only. Revenue varies
  wildly by category and audience geography; the 2024 "Ads Incentive Program"
  pays a flat hourly rate to streamers who hit ad-minute quotas.
- **Hype Train** — community bits/subs in a window unlock channel-wide
  emote tiers. Pure marketing — no extra payout, but drives sub bursts.
- **Charity** — direct donation routing via Twitch Charity (no fees).
- **Bounty Board** — sponsored content marketplace (Partner only).

**Affiliate eligibility**: 50 followers + 500 broadcast minutes in last 30
days + 7 unique broadcast days + average 3 concurrent viewers.

**Partner eligibility**: ~75 hrs streamed in last 30 days + 12 unique
broadcast days + average 75 concurrent viewers, plus a manual review.

## Version Pinning

- **Helix** is the only supported API. Kraken (v5) is fully removed (404).
- **EventSub** topics are versioned per topic (`v1`, `v2`). Old versions are
  deprecated then removed; `channel.follow` v1 is gone, use v2.
- **EventSub transports** — webhook and websocket are both stable. The old
  PubSub WebSocket protocol (`pubsub-edge.twitch.tv`) is deprecated for
  redemption / bits / etc — migrate to EventSub WebSocket.
- **IRC** is frozen and not versioned; capability requests
  (`twitch.tv/tags twitch.tv/commands twitch.tv/membership`) are stable.
- **Authentication endpoints** at `id.twitch.tv/oauth2/*` are stable; no
  versioning planned.
- **SDK pinning**:
  - `twitchio>=2.10,<3` (3.x is an incompatible rewrite)
  - `@twurple/api@^7` (semver, but follow release notes for breaking minor)
  - `tmi.js@^1.8` (frozen, fine to pin)

`User-Agent` is not validated but a recognizable one (`eos-bot/1.0`) helps
Twitch ops contact you when something breaks. Twitch publishes deprecation
schedules at `dev.twitch.tv/docs/change-log` — subscribe.

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

Twitch was built around the assumption that **live, real-time community is
the product**. Every feature reinforces synchronous viewing: "currently live"
discovery, raids that yeet viewers between streams, hype trains that reward
mass simultaneous action, channel points that only earn while watching,
emote-based identity. The platform is hostile to async consumption because
async consumption is how YouTube wins.

The tradeoff: discovery is brutal for new streamers. Twitch's homepage and
category pages rank by current viewer count and recency, which means streams
with viewers get more viewers and streams with zero viewers stay at zero.
This is the opposite of TikTok's flat distribution. There is no algorithmic
"give a new creator a chance" boost — the only injection mechanisms are
follower notifications, raids from larger streamers, and external traffic.

Implication for Antony: **Twitch will not discover you. You must drive
traffic to Twitch from elsewhere (YouTube/TikTok/X) and use Twitch as the
high-trust live conversion layer**, not as a top-of-funnel acquisition
channel.

The other deliberate tradeoff: monetization is real (subs/bits/ads) but the
floor is high. Affiliate (~$50/mo for tiny streamers) is achievable; getting
to a meaningful income requires Partner-level audience or external
sponsorships. Twitch the product makes more money on bits than Twitch the
SaaS would on API fees, so the API stays free — they want you to build
overlays and bots that increase engagement.

## Problem-Solution Map and Hidden Capabilities

### Hidden capability: Stream markers

`POST /helix/streams/markers` (or `/marker` in chat) drops a timestamped
marker on the live stream. Every marker becomes a navigable point in the VOD
and is queryable post-stream via `GET /helix/streams/markers`. The clipping
pipeline should write a marker on every "good" moment: chat density spike,
laugh, demo success, audience question, hype train start.

### Hidden capability: Channel point rewards as button presses

A custom reward with cost=1 and "skip queue" enabled is just a $0 button on
the stream UI. EOS uses these for non-monetary interactions: "Ask Antony a
question" rewards that route into the post-stream Q&A digest.

### Hidden capability: Stream tags vs game tags

Tags went from free-form (pre-2022) to a curated list (post-2022) and back to
free-form (2023, 10 tags / 25 chars). They're searchable. Use the tag space
for keywords your audience actually searches: `coaching`, `bootstrapping`,
`solofounder`, not `IRL` `chatting`.

### Hidden capability: VOD muted segments

If Twitch detects copyrighted audio it auto-mutes 30-min chunks of the VOD
and exposes `muted_segments` on `GET /helix/videos`. Read this before clip
extraction so you don't ship a clip that starts in the middle of a mute.

### Hidden capability: Predictions as engagement loops

Channel point predictions ("will Antony close the deploy in <10 min?") drive
chat participation 5-10x for the prediction window. Cost zero, work great as
in-stream segments.

### Hidden capability: Transcoding tiers

Twitch decides whether to give your stream multiple bitrate options (the
"Source/720p/480p/360p/Mobile" menu) based on viewer count and broadcaster
type. Partners always get transcoding; Affiliates get it most of the time;
non-Affiliates get it inconsistently. If you have a slow viewer base, this is
the difference between losing them and not. Affiliate first.

### Problem: Discoverability dead-zone for solo founders

Solution: stream consistently in a niche category (Software & Game
Development → Just Chatting hybrid by switching mid-stream) and rely on
**raid networks** — coordinate with other small creators to raid each other
at end of stream. Twitch raids transfer your live viewers to another channel
with a chat takeover; reciprocal raids are the closest thing Twitch has to a
growth algorithm.

### Problem: Going live with empty chat

Solution: schedule streams (`POST /helix/schedule/segment`) so followers get
push notifications. Pre-announce on YouTube/TikTok 24h prior. Drive 5-10
viewers in the first 10 minutes from external channels — this is enough to
get a tiny exposure boost in category browse.

### Problem: VOD content is wasted for short-form repurposing

Solution: the EOS clipping pipeline. Combine `GET /helix/clips` (clips made
by viewers, which is signal for "this moment was worth saving"), stream
markers (your own signal), and chat density (`channel.chat.message` event
counts in 30s windows from EventSub). Every cluster becomes a candidate
30-90s vertical clip for TikTok/Shorts/Reels.

## Operational Behavior and Edge Cases

- **Going live ≠ stream.online instantly.** Twitch buffers ~10-15 seconds
  before a stream is "officially" live and EventSub fires. If you trigger
  external announcements off `stream.online`, expect the actual viewable
  stream to be ~10s ahead.
- **Raid lands BEFORE the EventSub event** in some cases — viewers appear in
  chat seconds before `channel.raid` notification. Don't gate raid greetings
  on the event alone; also watch IRC USERNOTICE.
- **Clip creation while offline** returns 422. You must create clips while
  the stream is live (or within ~30s of it ending). To clip an old VOD,
  there's no API — only the Twitch web UI clip editor.
- **Chat messages during stream startup** can arrive on IRC before
  `stream.online` fires. The clean ordering you'd expect (online → chatters
  → messages) does not hold.
- **Mod actions are eventually consistent.** A `/timeout` issued via Helix
  takes ~1-2s to propagate to chat clients. A second timeout in that window
  returns success but is a no-op.
- **`channel.update` fires for every PATCH** including no-op patches. Dedupe
  on the client side or you'll spam your own log.
- **EventSub WebSocket disconnects silently** if you skip keepalives. Heartbeat
  every 10s; if you miss two, reconnect.
- **Subscription gifts come as N+1 events**: one
  `channel.subscription.gift` (the gifter) plus N `channel.subscribe` events
  (the recipients). Don't double-count.
- **Anonymous gift subs** have `is_anonymous=true` and `user_id=null`. Your
  schema must allow that.
- **Bits cheermotes** (`Cheer100`, `Cheer1000`) appear inline in chat
  messages — parse them out before sentiment analysis.
- **VOD goes private before going public** — the `viewable` field is `private`
  for ~90s after stream end while Twitch processes. Poll until `public`
  before linking it externally.
- **Mobile broadcasts** (Twitch app) cannot run external EventSub overlay
  alerts because there's no OBS in the loop. Use bot-only alerts (chat
  messages from the bot account) for mobile streams.

## Ecosystem Position and Composition

Twitch is the **incumbent** for Western live streaming with ~70% market share
of the live-streaming category, but trajectory is flat-to-declining as
YouTube Live grows and Kick (separate skill) buys top streamers with
non-exclusive deals.

| Platform | Strength | Weakness | EOS use |
|---|---|---|---|
| **Twitch** | Dense live community, monetization tools, raid network | Discoverability brutal, mobile weak, ad rev declining | Primary live home for Q&A streams |
| **YouTube Live** | Huge async tail, recommendation engine surfaces VOD | Live community thinner, fewer creator-economy features | Simulcast + permanent VOD library |
| **Kick** | 95/5 split, lax content rules, big talent deals | Smaller audience, still building API | Optional simulcast for reach |
| **Rumble Live** | Conservative creator base, no demonetization | Niche audience | Skip for Antony's brand |
| **X Live Spaces / X Live** | Built into X feed | Discovery only via X follower graph | Only if simulcasting via Restream |

**Composition stack** for an EOS live stream:
```
OBS Studio (encoder, scenes, sources)
  ├── Browser source → local overlay (channel points, alerts, recent followers)
  ├── Audio source → microphone, system, optional Suno music bed
  ├── Scene source → camera + screen + browser overlay
  └── Output → Twitch RTMP ingest (one of)
                 OR Restream → fan-out to Twitch + YouTube + Kick + X
Stream Deck (XL or +)
  └── HTTP requests to local OBS WebSocket → scene/source toggles, mute, replays
Streamlabs / StreamElements
  └── Browser source overlay for tip alerts, goal bars, chat box
EOS bot (twitchio)
  ├── Listens IRC + EventSub channel.chat.message
  ├── Posts !arena, !uptime, !so commands
  └── Drops stream markers on agent-detected highlights
EOS post-stream pipeline (cron)
  ├── Pulls VOD from /helix/videos
  ├── Pulls clips from /helix/clips
  ├── Pulls chat log from EventSub archive
  └── Outputs candidate short-form clip ranges to /opt/OS/content_inbox/
```

## Trajectory and Evolution

- **EventSub WebSocket** (announced 2023, GA 2024) is becoming the canonical
  push transport, replacing webhook for 90% of use cases. Webhook stays for
  server-to-server.
- **`channel.chat.message` EventSub** (added 2024) means new bots can skip
  IRC entirely. IRC is still supported but stopped getting new tag
  capabilities; treat as legacy maintenance mode for new builds.
- **Mobile push** through the Twitch app continues to be the highest-conversion
  notification path. Schedule entries trigger pushes to followers.
- **Ads model** went through the 2024 Ads Incentive Program (AIP) which pays
  a flat hourly rate per ad-minute, encouraging mid-roll programming. Ads
  revenue split shifted from 50/50 to 55/45 favoring streamers (Aug 2023)
  for Plus members and is being squeezed back as Twitch margin is under
  pressure.
- **Content Classification Labels** (CCLs) replaced the old "Mature" toggle;
  every channel now picks specific labels (Drugs, Politics, Gambling, Mature
  Themes, Sexual Themes, Violent Content). PATCH `/helix/channels` accepts
  `content_classification_labels`.
- **Hype Chat** was launched and quietly killed — sunset 2024. Don't reference.
- **Twitch Plus** (subscription tier for viewers, 2024+) gives ad-free
  viewing per channel; revenue impact on streamers is small.
- **PubSub deprecation** — old `pubsub-edge.twitch.tv` is being shut down.
  Migrate to EventSub WebSocket.
- **API change-log** at `dev.twitch.tv/docs/change-log` is the single source
  of truth for what's deprecated. Subscribe.

## Conceptual Model and Solution Recipes

### Recipe: "Notify EOS the moment Antony goes live"

```python
# eos_ai/twitch_listener.py — EventSub WebSocket transport
import asyncio, json, websockets, requests, os

WSS = "wss://eventsub.wss.twitch.tv/ws"
HELIX = "https://api.twitch.tv/helix"
HEADERS = {
    "Authorization": f"Bearer {os.environ['TWITCH_USER_ACCESS_TOKEN']}",
    "Client-Id": os.environ["TWITCH_CLIENT_ID"],
    "Content-Type": "application/json",
}

async def run():
    async with websockets.connect(WSS) as ws:
        welcome = json.loads(await ws.recv())
        session_id = welcome["payload"]["session"]["id"]
        # Subscribe
        requests.post(
            f"{HELIX}/eventsub/subscriptions",
            headers=HEADERS,
            json={
                "type": "stream.online",
                "version": "1",
                "condition": {"broadcaster_user_id": os.environ["TWITCH_BCID"]},
                "transport": {"method": "websocket", "session_id": session_id},
            },
        ).raise_for_status()
        async for raw in ws:
            msg = json.loads(raw)
            mtype = msg["metadata"]["message_type"]
            if mtype == "session_keepalive":
                continue
            if mtype == "notification":
                event = msg["payload"]["event"]
                # Write to EOS memory, fire announcements, etc.
                print("LIVE:", event)

asyncio.run(run())
```

### Recipe: Post-stream clip extraction

```python
# scripts/twitch_post_stream_clipper.py
# Run from cron 30 min after stream ends.
import requests, os
from datetime import datetime, timedelta

H = {"Authorization": f"Bearer {os.environ['TWITCH_APP_TOKEN']}",
     "Client-Id": os.environ["TWITCH_CLIENT_ID"]}
BCID = os.environ["TWITCH_BCID"]

# 1. Find the most recent VOD
videos = requests.get(
    f"https://api.twitch.tv/helix/videos?user_id={BCID}&type=archive&first=1",
    headers=H,
).json()["data"]
vod = videos[0]

# 2. Pull viewer-created clips from the last 24h
since = (datetime.utcnow() - timedelta(hours=24)).isoformat() + "Z"
clips = requests.get(
    f"https://api.twitch.tv/helix/clips?broadcaster_id={BCID}&started_at={since}&first=100",
    headers=H,
).json()["data"]

# 3. Sort by view_count, take top 10
clips.sort(key=lambda c: c["view_count"], reverse=True)
candidates = clips[:10]

# 4. Write each candidate to inbox for short-form repurposing
import json
with open(f"/opt/OS/content_inbox/twitch_clips_{datetime.utcnow().date()}.json", "w") as f:
    json.dump(
        [{"id": c["id"], "url": c["url"], "title": c["title"],
          "views": c["view_count"], "vod_offset": c.get("vod_offset"),
          "duration": c["duration"]} for c in candidates],
        f, indent=2)
print(f"wrote {len(candidates)} candidates")
```

### Recipe: Pre-stream channel update

```bash
#!/usr/bin/env bash
# scripts/twitch_go_live.sh — call before opening OBS
TITLE="$1"
GAME_ID="${2:-509670}"  # Software and Game Development
curl -X PATCH \
  -H "Authorization: Bearer ${TWITCH_USER_ACCESS_TOKEN}" \
  -H "Client-Id: ${TWITCH_CLIENT_ID}" \
  -H "Content-Type: application/json" \
  "https://api.twitch.tv/helix/channels?broadcaster_id=${TWITCH_BCID}" \
  -d "{\"title\":\"${TITLE}\",\"game_id\":\"${GAME_ID}\",\"tags\":[\"coaching\",\"solofounder\",\"buildinginpublic\"]}"
```

## Industry Expert and Cutting-Edge Usage

The streamers winning Twitch in 2026 share a small set of patterns. Worth
copying.

- **xQc, Asmongold, Kai Cenat** — extreme consistency (8-12 hrs/day, 6-7
  days/week). For solo founders this is impossible; the relevant lesson is
  not duration but **same-time-every-week**. Pick one slot and never miss it.
- **Northernlion, DougDoug** — multi-platform native. Stream on Twitch live,
  upload edited highlights to YouTube same-day, clips to TikTok within 24h.
  This is the pattern EOS implements via the post-stream clipper.
- **DistortionGS / Sodapoppin** — raid networks. Every stream ends with a
  raid to a friend; reciprocal raids are scheduled. Build your network with
  5-10 founder-creators in the same niche and raid round-robin.
- **Dr Disrespect** (now on Kick) demonstrated the production-value ceiling
  — overlays, transitions, music, character. For Antony's brand, lean into
  tactical-luxury aesthetic via OBS scenes (clean black overlay, single
  brand color, Inter font, no Streamlabs default cheese).
- **Building-in-public streamers** (Pieter Levels, Theo, ThePrimeagen) —
  proof that dev-focused streams convert to paid product. Theo's pattern:
  start streaming code, end up selling courses + SaaS to the audience that
  watched him build it. Direct precedent for EOS → Empyrean Studio AI offer.

Cutting-edge tools the top tier uses:
- **OBS WebSocket v5** + Stream Deck for hands-free scene control
- **Crowd Control** (gamified channel point redemptions affecting gameplay)
- **NightBot / StreamElements / Wizebot** for chat moderation and timed messages
- **Sammi.app / Aitum** as visual EventSub middleware (drag-drop "when X happens, do Y")
- **OBS Move plugin** for animated transitions
- **Restream** for multi-streaming + chat aggregation
- **Twitch CLI** (`twitch-cli`) for local EventSub testing — simulates events
  against your callback so you can develop offline:
  ```bash
  twitch event trigger stream.online -F http://localhost:8000/twitch/eventsub -s YOUR_SECRET
  twitch event verify-subscription stream.online -F http://localhost:8000/twitch/eventsub -s YOUR_SECRET
  ```

---

## EOS Usage Patterns

### Pattern 1: Live coaching Q&A workflow

**Frequency**: weekly, ~60-90 min, same slot every week (Thursday 5pm PT
suggested — captures EU evening and US afternoon).

**Pre-stream (T-15 min)**:
1. `scripts/twitch_go_live.sh "Live coaching Q&A — Initiate Arena"`
2. Drop tweet + LinkedIn post: "Going live in 15 min, link in bio."
3. Open OBS, scene = "Coaching Q&A" (camera + chat overlay + brand lower-third).
4. Verify EventSub WebSocket listener is connected (check `eos-twitch.service`).

**During stream**:
- twitchio bot listens for `!q` chat commands and queues questions to a
  `questions_today` table.
- Channel point reward "Ask Antony a question" (cost 500) auto-fulfills and
  pushes higher-priority items to the top of the queue.
- Bot drops `/marker "Q from {user}: {first 50 chars}"` for each question
  answered.

**Post-stream (T+30 min, cron)**:
1. `scripts/twitch_post_stream_clipper.py` runs.
2. Markers + viewer clips merged → short-form candidate list.
3. Top 5 candidates sent to `content_inbox/` for human review.
4. Approved clips pushed to TikTok / YouTube Shorts / Reels via existing
   pipeline.

### Pattern 2: Building-in-public session

**Frequency**: ad-hoc, when there's something visual to build (UI work,
agent demo, deploy walkthrough).

**Difference from coaching Q&A**: scene flips to "Code + Cam," chat is
secondary, focus is the screen. Bot still listens but doesn't announce.
Channel category set to "Software and Game Development" for the ~5% of viewers
who browse that category.

**Hook**: lead with a specific unfinished problem. "I need to make the
post-stream clipper deduplicate candidates within a 30s window. Watch me
debug it." This sells the stream as proof-of-work, not infomercial.

### Pattern 3: Post-stream clip extraction for repurposing

The asset that justifies streaming. Every live hour produces ~10 candidate
clips. Even at 50% reject rate, that's 5 short-form posts per stream — at
weekly cadence, 20 short-form posts/month from one live commitment.

Pipeline: VOD → clips API → chat density windows → marker correlation →
ranked candidates → human approval → vertical re-encode → TikTok/Shorts/Reels.

### Pattern 4: Agent-drafted alerts and chat commands

Agents own the *content* of alerts, the *copy* of chat commands, the
*priority* of channel point rewards. Antony approves before deploying. Never
let an agent autonomously respond *as Antony* in chat — chat is human voice
or labeled "[bot]".

### Composition with OBS and Stream Deck

OBS is the encoder; Twitch is the destination. Stream Deck talks to OBS
directly (WebSocket v5) for scene/source control AND can hit Helix endpoints
via custom HTTP plugin actions for things like "create clip now" — use this
during streams to manually mark moments the chat density heuristic would
miss.

---

## Gotchas

- **`Client-Id` header omitted** — silent 401 even when token is perfect. The
  most common Helix bug. SDK users never see this; curl scripters always do.
- **Wrong token type** for the endpoint — using app token on a `manage:*`
  endpoint returns 401 with a misleading "Invalid OAuth token" message. The
  token isn't invalid; it's the wrong type. Check the docs for "App access
  token OR User access token" labels.
- **`oauth:` prefix** required for IRC PASS, forbidden for Helix Authorization
  header. Mix them up and IRC says "Login authentication failed" while Helix
  says "Invalid OAuth token" — same root cause.
- **Implicit grant tokens have no refresh** — if you build with implicit grant
  thinking it's simpler, you'll re-prompt the user every 4 hours. Use
  authorization code flow.
- **Refresh token rotation** — every refresh response includes a NEW
  refresh_token. Persist it. The old one is invalidated.
- **EventSub HMAC over decoded JSON** — the most common EventSub bug. Verify
  on raw bytes BEFORE parsing.
- **EventSub challenge response Content-Type** — return `text/plain` with
  the raw challenge string, not `application/json`. Some servers wrap in
  JSON; this works but is fragile across reverse proxies that strip JSON
  whitespace.
- **EventSub `version` field** must be a string, not a number. `"1"` not `1`.
- **Subscribing twice to the same `(type, condition)`** returns 409 Conflict.
  Always GET existing subscriptions first or catch 409 and reuse.
- **`channel.follow` v1 returns nothing** — silently. Migrate to v2 with the
  `moderator_user_id` condition.
- **`is_anonymous=true` gift subs** have `user_id=null` — your DB schema
  must allow null FK or you'll crash on every anonymous gifter.
- **Polling `/helix/streams` with 100 user_logins** still costs 1 point but
  rate-limits faster than expected if the response is empty (no broadcasters
  live) because of an internal cache miss penalty. Use EventSub.
- **`broadcaster_id` must equal authenticated user** for all `manage:*` and
  `edit:*` endpoints. You can't manage someone else's channel even if they
  added you as moderator — moderation has its own `moderator:manage:*` scopes
  and uses `moderator_id` separately.
- **Clips with `has_delay=true`** wait ~15s after capture before becoming
  visible — this is the default and what most streamers want (mod review),
  but if you're driving an instant-clip workflow, set `has_delay=false`.
- **Deleted VODs cascade to clips silently** — clips referencing a deleted
  VOD return `vod_offset=null` and the embed plays in standalone mode. Don't
  rely on `vod_offset` being non-null.
- **EventSub WebSocket `session_reconnect`** — Twitch periodically asks you
  to migrate to a new URL. Open the new URL, wait for `session_welcome` on
  the new connection, THEN close the old. Reverse order drops events.
- **Rate limit headers are missing on cached responses** — if the SDK uses an
  HTTP cache, you won't see `Ratelimit-Remaining`. Disable HTTP caching for
  Helix or trust the headers only on cache misses.
- **Twitch CLI `event trigger`** generates synthetic events that look real
  but use fake broadcaster_user_id `12826`. Filter test data out of your
  production handler or build a separate dev handler.
- **OAuth `redirect_uri`** must be EXACT match including trailing slash.
  `https://app/callback` and `https://app/callback/` are two different
  registered URIs.
- **Stream marker via chat (`/marker`)** requires editor or broadcaster
  permission. Bots that aren't editors silently fail to drop markers.
- **Tags input validation** — tag list is total replace, not merge. Sending
  `["coaching"]` removes every other tag. Always send the full desired set.
- **`game_id="0"`** sets category to "(no category)" which excludes you from
  every category browse page. Always set a real category before going live.
- **Custom rewards `is_paused`** doesn't refund — paused rewards just stop
  accepting new redemptions. To refund, PATCH each redemption to `CANCELED`.
- **Predictions can't be created while another is live** — 409. Resolve or
  cancel the previous one first.
- **`POST /helix/clips` while raid in progress** returns 422. Wait until raid
  countdown completes.
- **Helix `description` field** on PATCH /channels does NOT exist — channel
  description is set in user settings, not channel settings. The channel
  PATCH endpoint controls title, game, language, tags, delay, content
  classification, branded content. That's it.
