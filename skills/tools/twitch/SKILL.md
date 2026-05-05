<<<<<<< Updated upstream
---
name: twitch
description: "Use when querying Twitch Helix API for streams/users/clips, building EventSub webhook integrations for live events, managing chat via IRC/EventSub, designing stream layouts, planning live content strategy for personal brand, or analyzing stream performance."
allowed-tools: "Read, Bash, Write, Edit, WebFetch"
version: 1.0
source_url: "https://dev.twitch.tv/docs"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "Helix"
sdk_version: "twitchio 2.10 (Python) / twurple 7.2 (TypeScript) / tmi.js 1.8 (chat)"
speed_category: stable
trigger: both
effort: low
context: fork
---

# Tool: Twitch

## What This Tool Does

Twitch is a live-streaming platform with a creator economy and a fully
documented developer API surface. For developers it exposes three protocols
that look separate but compose into one product:

- **Helix REST API** (`api.twitch.tv/helix/*`) — the modern HTTP control plane.
  Read/write streams, users, channels, clips, videos, schedules, polls,
  predictions, channel points, moderation, ads, charity, raids. Rate-limited
  per app/user via a token-bucket header (`Ratelimit-Remaining`).
- **EventSub** — push notifications for live events (`stream.online`,
  `channel.subscribe`, `channel.cheer`, `channel.follow`,
  `channel.channel_points_custom_reward_redemption.add`, `channel.raid`,
  `channel.ad_break.begin`, `channel.chat.message`, ~80 topics). Two
  transports: **webhook** (HMAC-signed POST to your HTTPS endpoint) and
  **WebSocket** (persistent client connection, no public URL needed —
  preferred for desktop apps and overlays).
- **IRC chat** (`irc.chat.twitch.tv:6697`) — the legacy but still-canonical
  chat protocol. PRIVMSG, USERNOTICE, CLEARCHAT, PING/PONG, with
  Twitch-specific tags (`badges`, `bits`, `emotes`, `tmi-sent-ts`).
  EventSub `channel.chat.message` is the modern alternative but IRC remains
  the lowest-latency path and the one every chat bot uses.

For creators it is a discovery + monetization product: categories, raids,
follows, channel points, bits, subscriptions (T1/T2/T3), ads, hype trains,
predictions, polls, clips, schedule, mobile push.

The duality matters: Helix is the read/write API, EventSub is the push API,
IRC is the chat firehose. A real Twitch integration almost always uses two
of the three.

## EOS Integration

Twitch is a **secondary** live channel for the personal brand. Priority sits
below YouTube and TikTok (where Antony's evergreen + viral content lives) but
above passive platforms because **going live is the highest-trust signal a
founder can produce.** Used selectively, not constantly.

Concrete EOS uses:

- **Live coaching Q&A streams** — weekly or biweekly, ~60-90 min, "ask the
  Vigilante Architect anything" style. Builds Initiate Arena top-of-funnel
  through real-time proof.
- **Building-in-public sessions** — code on EOS, run agents, walk through
  deploys. Highest-trust marketing for the future Empyrean Studio AI offer.
  Behind-the-scenes is the content.
- **Post-stream clip extraction pipeline** — every VOD goes through an agent
  that pulls chat density spikes (`channel.chat.message` count per 30s window),
  cross-references with stream markers, and proposes 30-90 second clip ranges
  via `POST /helix/clips`. Output is repurposed to TikTok / YouTube Shorts /
  Reels — making one live hour into ~10 short-form posts.
- **Chat moderation prompts** — agents draft AutoMod tier rules and `/timeout`
  policies; Antony approves. Bot uses EventSub `channel.chat.message` +
  `channel.moderate` scopes.
- **Alert design** — channel point reward redemptions
  (`channel:manage:redemptions`) drive on-screen overlays via OBS browser
  source talking to a local WebSocket relay.
- **Schedule planning** — `PATCH /helix/schedule/segment` to publish the
  weekly stream slot to the channel page so followers get push notifications.

Antony streams himself. Agents draft, ingest, and react — they never speak
on stream as Antony.

Composition with adjacent skills in this wave:
- **OBS** — encoder, scenes, sources (separate skill)
- **Streamlabs / StreamElements** — alerts and tip jars
- **Restream** — multi-platform simulcast to YouTube Live + Kick
- **Stream Deck** — physical control surface for scene switches

## Authentication

Twitch uses **OAuth 2.0** with three token shapes. Knowing which one to use
is the single most common point of failure.

| Token type | How obtained | Used for | Lifetime |
|---|---|---|---|
| **App access token** | `client_credentials` grant: POST `id.twitch.tv/oauth2/token` with `client_id`+`client_secret`+`grant_type=client_credentials` | Read-only public Helix endpoints (GetStreams, GetUsers, GetGames, GetClips, GetVideos), EventSub webhook subscriptions | ~60 days, refresh by re-requesting |
| **User access token** | Authorization code or device code flow — user grants scopes, you exchange `code` for `access_token` + `refresh_token` | Anything that acts as a user (ModifyChannelInformation, CreateClip, manage rewards, send chat, EventSub WebSocket) | ~4 hours, refresh with `refresh_token` |
| **Implicit grant** | URL fragment after `/oauth2/authorize?response_type=token` | Browser-only apps | Same ~4h, NO refresh token — deprecated for new apps |

**Scopes are additive and force re-auth.** Adding a scope to your app means
every existing user token must be re-issued. EOS holds one user token for the
Antony account in `/opt/OS/eos_ai/.env` as `TWITCH_USER_ACCESS_TOKEN` +
`TWITCH_REFRESH_TOKEN`, plus an app token for unauthenticated reads.

Validate any token with `GET id.twitch.tv/oauth2/validate` (returns `client_id`,
`login`, `scopes`, `expires_in`). Do this on app boot — a 401 mid-request is
the worst place to discover expiry.

```bash
# App access token (server-to-server)
curl -X POST https://id.twitch.tv/oauth2/token \
  -d "client_id=${TWITCH_CLIENT_ID}" \
  -d "client_secret=${TWITCH_CLIENT_SECRET}" \
  -d "grant_type=client_credentials"

# Refresh user token
curl -X POST https://id.twitch.tv/oauth2/token \
  -d "client_id=${TWITCH_CLIENT_ID}" \
  -d "client_secret=${TWITCH_CLIENT_SECRET}" \
  -d "grant_type=refresh_token" \
  -d "refresh_token=${TWITCH_REFRESH_TOKEN}"
```

Every Helix request needs BOTH headers — missing `Client-Id` returns 401 even
with a valid `Authorization`:

```
Authorization: Bearer <token>
Client-Id: <client_id>
```

## Quick Reference

### Get currently live channel

```bash
curl -H "Authorization: Bearer $APP_TOKEN" -H "Client-Id: $CLIENT_ID" \
  "https://api.twitch.tv/helix/streams?user_login=antonyfmunoz"
```

### Update channel title and category before going live

```bash
# Look up category id
curl -H "Authorization: Bearer $APP_TOKEN" -H "Client-Id: $CLIENT_ID" \
  "https://api.twitch.tv/helix/games?name=Software%20and%20Game%20Development"

# Patch channel
curl -X PATCH \
  -H "Authorization: Bearer $USER_TOKEN" -H "Client-Id: $CLIENT_ID" \
  -H "Content-Type: application/json" \
  "https://api.twitch.tv/helix/channels?broadcaster_id=$BCID" \
  -d '{"title":"Live coaching Q&A — Initiate Arena","game_id":"1469308723"}'
```

### Create a clip from the live stream

```bash
curl -X POST \
  -H "Authorization: Bearer $USER_TOKEN" -H "Client-Id: $CLIENT_ID" \
  "https://api.twitch.tv/helix/clips?broadcaster_id=$BCID&has_delay=true"
# Returns clip id; clip is processing for ~15s, then GET /helix/clips?id=...
```

### Subscribe to stream.online via EventSub webhook

```bash
curl -X POST \
  -H "Authorization: Bearer $APP_TOKEN" -H "Client-Id: $CLIENT_ID" \
  -H "Content-Type: application/json" \
  https://api.twitch.tv/helix/eventsub/subscriptions \
  -d '{
    "type":"stream.online",
    "version":"1",
    "condition":{"broadcaster_user_id":"'$BCID'"},
    "transport":{
      "method":"webhook",
      "callback":"https://eos.example.com/twitch/eventsub",
      "secret":"'$EVENTSUB_SECRET'"
    }
  }'
```

### Send chat via IRC (Python, no SDK)

```python
import socket, ssl
s = ssl.wrap_socket(socket.socket())
s.connect(("irc.chat.twitch.tv", 6697))
s.send(f"PASS oauth:{USER_TOKEN}\r\n".encode())
s.send(f"NICK antonyfmunoz\r\n".encode())
s.send(b"CAP REQ :twitch.tv/tags twitch.tv/commands\r\n")
s.send(b"JOIN #antonyfmunoz\r\n")
s.send(b"PRIVMSG #antonyfmunoz :hello from EOS\r\n")
```

### twitchio (Python) — minimal bot

```python
from twitchio.ext import commands
class Bot(commands.Bot):
    def __init__(self):
        super().__init__(token=USER_TOKEN, prefix="!", initial_channels=["antonyfmunoz"])
    @commands.command()
    async def arena(self, ctx):
        await ctx.send("Initiate Arena: lyfeinstitute.com")
Bot().run()
```

## Conceptual Model

**Helix is current. Kraken is dead.** The v5 "Kraken" API was deprecated and
removed; ANY tutorial using `api.twitch.tv/kraken/*` is wrong. New work is
Helix (`api.twitch.tv/helix/*`) only. Webhooks v1 was also replaced — the
current push system is EventSub, not "Twitch Webhooks."

**EventSub topology.** A subscription has three parts: a `type` (e.g.
`channel.subscribe`), a `condition` (which broadcaster), and a `transport`
(webhook URL or WebSocket session id). Webhook transport is for servers with
public HTTPS; WebSocket transport is for desktop/local apps and is what every
modern Twitch overlay uses. Both deliver identical event payloads — only the
delivery mechanism differs.

**Scope explosion.** Twitch scopes are extremely fine-grained (~90 of them):
`channel:read:subscriptions`, `channel:manage:redemptions`,
`moderator:read:chatters`, `user:write:chat`, `bits:read`, `clips:edit`. There
is no "give me everything" scope. Plan the full scope list before first OAuth
or you'll re-prompt the user every feature.

**Identity is broadcaster_user_id everywhere.** The numeric `user_id` from
`GET /helix/users` is the canonical key. The login name (`antonyfmunoz`) is a
mutable display string. Never key your DB on login.

**Chat is two protocols pretending to be one.** IRC is the read/write firehose
with sub-100ms latency. EventSub `channel.chat.message` (added 2024) is the
same data over webhooks/WebSocket with structured JSON instead of IRC tags.
Bots that need to *send* messages use IRC or `POST /helix/chat/messages`
(rate-capped). Bots that only *read* should prefer EventSub.

## Gotchas

- **Token expiry surprise** — user tokens expire in ~4 hours and the SDK
  doesn't auto-refresh unless you wire it. Always validate on boot via
  `/oauth2/validate` and refresh proactively at ~75% of `expires_in`.
- **EventSub HMAC signature** — every webhook delivery includes
  `Twitch-Eventsub-Message-Signature: sha256=<hex>` over
  `message_id + timestamp + raw_body` keyed by your subscription secret.
  If you parse the body before computing the HMAC you'll get a wrong digest
  half the time (whitespace/encoding). Verify on the **raw** bytes.
- **EventSub webhook callback verification challenge** — the first POST after
  subscribing has `Twitch-Eventsub-Message-Type: webhook_callback_verification`
  and you must echo `challenge` in the body within 10 seconds with HTTP 200.
  Miss it and the subscription is killed permanently.
- **IRC vs Helix duality** — sending chat via IRC needs an `oauth:` prefix on
  the password; sending via `POST /helix/chat/messages` needs the bare token.
  Mixing them up is the most common chatbot bug.
- **Rate limit shape** — the helix bucket is per-app (~800 points/min) AND
  per-user (varies). The `Ratelimit-Remaining` header is authoritative; do not
  estimate. On 429, honor `Ratelimit-Reset` (epoch seconds).
- **Clip creation latency** — `POST /helix/clips` returns a clip id immediately
  but the clip is not playable for ~15s. `GET /helix/clips?id=...` returns
  empty array until processing finishes. Poll, don't assume.
- **Scope additions force re-auth** — adding a single scope to your app means
  every existing user token is now under-scoped and must be reissued through
  the auth flow. Plan all scopes up front.
- **`broadcaster_id` must be the authenticated user** for all `manage:*`
  endpoints. You can't moderate someone else's channel without their explicit
  moderator scope grant.
- **EventSub `channel.follow` v2** requires `moderator:read:followers` and a
  `moderator_user_id` in the condition — v1 is deprecated and stops returning
  data silently.
- **Ad break notifications** (`channel.ad_break.begin`) only fire if your app
  has the broadcaster's permission AND ads are actually enabled (Affiliate+).

See references/best_practices.md for the full 19-section creator-level knowledge base.
=======
---
name: twitch
description: "Use when querying Twitch Helix API for streams/users/clips, building EventSub webhook integrations for live events, managing chat via IRC/EventSub, designing stream layouts, planning live content strategy for personal brand, or analyzing stream performance."
allowed-tools: "Read, Bash, Write, Edit, WebFetch"
version: 1.0
source_url: "https://dev.twitch.tv/docs"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "Helix"
sdk_version: "twitchio 2.10 (Python) / twurple 7.2 (TypeScript) / tmi.js 1.8 (chat)"
speed_category: stable
---

# Tool: Twitch

## What This Tool Does

Twitch is a live-streaming platform with a creator economy and a fully
documented developer API surface. For developers it exposes three protocols
that look separate but compose into one product:

- **Helix REST API** (`api.twitch.tv/helix/*`) — the modern HTTP control plane.
  Read/write streams, users, channels, clips, videos, schedules, polls,
  predictions, channel points, moderation, ads, charity, raids. Rate-limited
  per app/user via a token-bucket header (`Ratelimit-Remaining`).
- **EventSub** — push notifications for live events (`stream.online`,
  `channel.subscribe`, `channel.cheer`, `channel.follow`,
  `channel.channel_points_custom_reward_redemption.add`, `channel.raid`,
  `channel.ad_break.begin`, `channel.chat.message`, ~80 topics). Two
  transports: **webhook** (HMAC-signed POST to your HTTPS endpoint) and
  **WebSocket** (persistent client connection, no public URL needed —
  preferred for desktop apps and overlays).
- **IRC chat** (`irc.chat.twitch.tv:6697`) — the legacy but still-canonical
  chat protocol. PRIVMSG, USERNOTICE, CLEARCHAT, PING/PONG, with
  Twitch-specific tags (`badges`, `bits`, `emotes`, `tmi-sent-ts`).
  EventSub `channel.chat.message` is the modern alternative but IRC remains
  the lowest-latency path and the one every chat bot uses.

For creators it is a discovery + monetization product: categories, raids,
follows, channel points, bits, subscriptions (T1/T2/T3), ads, hype trains,
predictions, polls, clips, schedule, mobile push.

The duality matters: Helix is the read/write API, EventSub is the push API,
IRC is the chat firehose. A real Twitch integration almost always uses two
of the three.

## EOS Integration

Twitch is a **secondary** live channel for the personal brand. Priority sits
below YouTube and TikTok (where Antony's evergreen + viral content lives) but
above passive platforms because **going live is the highest-trust signal a
founder can produce.** Used selectively, not constantly.

Concrete EOS uses:

- **Live coaching Q&A streams** — weekly or biweekly, ~60-90 min, "ask the
  Vigilante Architect anything" style. Builds Initiate Arena top-of-funnel
  through real-time proof.
- **Building-in-public sessions** — code on EOS, run agents, walk through
  deploys. Highest-trust marketing for the future Empyrean Studio AI offer.
  Behind-the-scenes is the content.
- **Post-stream clip extraction pipeline** — every VOD goes through an agent
  that pulls chat density spikes (`channel.chat.message` count per 30s window),
  cross-references with stream markers, and proposes 30-90 second clip ranges
  via `POST /helix/clips`. Output is repurposed to TikTok / YouTube Shorts /
  Reels — making one live hour into ~10 short-form posts.
- **Chat moderation prompts** — agents draft AutoMod tier rules and `/timeout`
  policies; Antony approves. Bot uses EventSub `channel.chat.message` +
  `channel.moderate` scopes.
- **Alert design** — channel point reward redemptions
  (`channel:manage:redemptions`) drive on-screen overlays via OBS browser
  source talking to a local WebSocket relay.
- **Schedule planning** — `PATCH /helix/schedule/segment` to publish the
  weekly stream slot to the channel page so followers get push notifications.

Antony streams himself. Agents draft, ingest, and react — they never speak
on stream as Antony.

Composition with adjacent skills in this wave:
- **OBS** — encoder, scenes, sources (separate skill)
- **Streamlabs / StreamElements** — alerts and tip jars
- **Restream** — multi-platform simulcast to YouTube Live + Kick
- **Stream Deck** — physical control surface for scene switches

## Authentication

Twitch uses **OAuth 2.0** with three token shapes. Knowing which one to use
is the single most common point of failure.

| Token type | How obtained | Used for | Lifetime |
|---|---|---|---|
| **App access token** | `client_credentials` grant: POST `id.twitch.tv/oauth2/token` with `client_id`+`client_secret`+`grant_type=client_credentials` | Read-only public Helix endpoints (GetStreams, GetUsers, GetGames, GetClips, GetVideos), EventSub webhook subscriptions | ~60 days, refresh by re-requesting |
| **User access token** | Authorization code or device code flow — user grants scopes, you exchange `code` for `access_token` + `refresh_token` | Anything that acts as a user (ModifyChannelInformation, CreateClip, manage rewards, send chat, EventSub WebSocket) | ~4 hours, refresh with `refresh_token` |
| **Implicit grant** | URL fragment after `/oauth2/authorize?response_type=token` | Browser-only apps | Same ~4h, NO refresh token — deprecated for new apps |

**Scopes are additive and force re-auth.** Adding a scope to your app means
every existing user token must be re-issued. EOS holds one user token for the
Antony account in `/opt/OS/eos_ai/.env` as `TWITCH_USER_ACCESS_TOKEN` +
`TWITCH_REFRESH_TOKEN`, plus an app token for unauthenticated reads.

Validate any token with `GET id.twitch.tv/oauth2/validate` (returns `client_id`,
`login`, `scopes`, `expires_in`). Do this on app boot — a 401 mid-request is
the worst place to discover expiry.

```bash
# App access token (server-to-server)
curl -X POST https://id.twitch.tv/oauth2/token \
  -d "client_id=${TWITCH_CLIENT_ID}" \
  -d "client_secret=${TWITCH_CLIENT_SECRET}" \
  -d "grant_type=client_credentials"

# Refresh user token
curl -X POST https://id.twitch.tv/oauth2/token \
  -d "client_id=${TWITCH_CLIENT_ID}" \
  -d "client_secret=${TWITCH_CLIENT_SECRET}" \
  -d "grant_type=refresh_token" \
  -d "refresh_token=${TWITCH_REFRESH_TOKEN}"
```

Every Helix request needs BOTH headers — missing `Client-Id` returns 401 even
with a valid `Authorization`:

```
Authorization: Bearer <token>
Client-Id: <client_id>
```

## Quick Reference

### Get currently live channel

```bash
curl -H "Authorization: Bearer $APP_TOKEN" -H "Client-Id: $CLIENT_ID" \
  "https://api.twitch.tv/helix/streams?user_login=antonyfmunoz"
```

### Update channel title and category before going live

```bash
# Look up category id
curl -H "Authorization: Bearer $APP_TOKEN" -H "Client-Id: $CLIENT_ID" \
  "https://api.twitch.tv/helix/games?name=Software%20and%20Game%20Development"

# Patch channel
curl -X PATCH \
  -H "Authorization: Bearer $USER_TOKEN" -H "Client-Id: $CLIENT_ID" \
  -H "Content-Type: application/json" \
  "https://api.twitch.tv/helix/channels?broadcaster_id=$BCID" \
  -d '{"title":"Live coaching Q&A — Initiate Arena","game_id":"1469308723"}'
```

### Create a clip from the live stream

```bash
curl -X POST \
  -H "Authorization: Bearer $USER_TOKEN" -H "Client-Id: $CLIENT_ID" \
  "https://api.twitch.tv/helix/clips?broadcaster_id=$BCID&has_delay=true"
# Returns clip id; clip is processing for ~15s, then GET /helix/clips?id=...
```

### Subscribe to stream.online via EventSub webhook

```bash
curl -X POST \
  -H "Authorization: Bearer $APP_TOKEN" -H "Client-Id: $CLIENT_ID" \
  -H "Content-Type: application/json" \
  https://api.twitch.tv/helix/eventsub/subscriptions \
  -d '{
    "type":"stream.online",
    "version":"1",
    "condition":{"broadcaster_user_id":"'$BCID'"},
    "transport":{
      "method":"webhook",
      "callback":"https://eos.example.com/twitch/eventsub",
      "secret":"'$EVENTSUB_SECRET'"
    }
  }'
```

### Send chat via IRC (Python, no SDK)

```python
import socket, ssl
s = ssl.wrap_socket(socket.socket())
s.connect(("irc.chat.twitch.tv", 6697))
s.send(f"PASS oauth:{USER_TOKEN}\r\n".encode())
s.send(f"NICK antonyfmunoz\r\n".encode())
s.send(b"CAP REQ :twitch.tv/tags twitch.tv/commands\r\n")
s.send(b"JOIN #antonyfmunoz\r\n")
s.send(b"PRIVMSG #antonyfmunoz :hello from EOS\r\n")
```

### twitchio (Python) — minimal bot

```python
from twitchio.ext import commands
class Bot(commands.Bot):
    def __init__(self):
        super().__init__(token=USER_TOKEN, prefix="!", initial_channels=["antonyfmunoz"])
    @commands.command()
    async def arena(self, ctx):
        await ctx.send("Initiate Arena: lyfeinstitute.com")
Bot().run()
```

## Conceptual Model

**Helix is current. Kraken is dead.** The v5 "Kraken" API was deprecated and
removed; ANY tutorial using `api.twitch.tv/kraken/*` is wrong. New work is
Helix (`api.twitch.tv/helix/*`) only. Webhooks v1 was also replaced — the
current push system is EventSub, not "Twitch Webhooks."

**EventSub topology.** A subscription has three parts: a `type` (e.g.
`channel.subscribe`), a `condition` (which broadcaster), and a `transport`
(webhook URL or WebSocket session id). Webhook transport is for servers with
public HTTPS; WebSocket transport is for desktop/local apps and is what every
modern Twitch overlay uses. Both deliver identical event payloads — only the
delivery mechanism differs.

**Scope explosion.** Twitch scopes are extremely fine-grained (~90 of them):
`channel:read:subscriptions`, `channel:manage:redemptions`,
`moderator:read:chatters`, `user:write:chat`, `bits:read`, `clips:edit`. There
is no "give me everything" scope. Plan the full scope list before first OAuth
or you'll re-prompt the user every feature.

**Identity is broadcaster_user_id everywhere.** The numeric `user_id` from
`GET /helix/users` is the canonical key. The login name (`antonyfmunoz`) is a
mutable display string. Never key your DB on login.

**Chat is two protocols pretending to be one.** IRC is the read/write firehose
with sub-100ms latency. EventSub `channel.chat.message` (added 2024) is the
same data over webhooks/WebSocket with structured JSON instead of IRC tags.
Bots that need to *send* messages use IRC or `POST /helix/chat/messages`
(rate-capped). Bots that only *read* should prefer EventSub.

## Gotchas

- **Token expiry surprise** — user tokens expire in ~4 hours and the SDK
  doesn't auto-refresh unless you wire it. Always validate on boot via
  `/oauth2/validate` and refresh proactively at ~75% of `expires_in`.
- **EventSub HMAC signature** — every webhook delivery includes
  `Twitch-Eventsub-Message-Signature: sha256=<hex>` over
  `message_id + timestamp + raw_body` keyed by your subscription secret.
  If you parse the body before computing the HMAC you'll get a wrong digest
  half the time (whitespace/encoding). Verify on the **raw** bytes.
- **EventSub webhook callback verification challenge** — the first POST after
  subscribing has `Twitch-Eventsub-Message-Type: webhook_callback_verification`
  and you must echo `challenge` in the body within 10 seconds with HTTP 200.
  Miss it and the subscription is killed permanently.
- **IRC vs Helix duality** — sending chat via IRC needs an `oauth:` prefix on
  the password; sending via `POST /helix/chat/messages` needs the bare token.
  Mixing them up is the most common chatbot bug.
- **Rate limit shape** — the helix bucket is per-app (~800 points/min) AND
  per-user (varies). The `Ratelimit-Remaining` header is authoritative; do not
  estimate. On 429, honor `Ratelimit-Reset` (epoch seconds).
- **Clip creation latency** — `POST /helix/clips` returns a clip id immediately
  but the clip is not playable for ~15s. `GET /helix/clips?id=...` returns
  empty array until processing finishes. Poll, don't assume.
- **Scope additions force re-auth** — adding a single scope to your app means
  every existing user token is now under-scoped and must be reissued through
  the auth flow. Plan all scopes up front.
- **`broadcaster_id` must be the authenticated user** for all `manage:*`
  endpoints. You can't moderate someone else's channel without their explicit
  moderator scope grant.
- **EventSub `channel.follow` v2** requires `moderator:read:followers` and a
  `moderator_user_id` in the condition — v1 is deprecated and stops returning
  data silently.
- **Ad break notifications** (`channel.ad_break.begin`) only fire if your app
  has the broadcaster's permission AND ads are actually enabled (Affiliate+).

See references/best_practices.md for the full 19-section creator-level knowledge base.
>>>>>>> Stashed changes
