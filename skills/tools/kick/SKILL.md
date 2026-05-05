<<<<<<< Updated upstream
---
name: kick
description: "Use when evaluating Kick as a streaming platform, cross-posting live content or clips from Twitch/YouTube, analyzing Kick audience dynamics, designing multi-platform streaming workflows, or monitoring Kick channels via any available API/webhook surface."
allowed-tools: "Read, Bash, Write, Edit, WebFetch"
version: 1.0
source_url: "https://docs.kick.com"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "Public API v1 (stable, growing) + legacy api/v2 (unofficial, undocumented)"
sdk_version: "HTTP / Pusher WebSocket / Playwright fallback"
speed_category: medium
trigger: both
effort: medium
context: fork
---

# Tool: Kick

## What This Tool Does

Kick is a live-streaming platform launched in 2022 as a direct Twitch
competitor. It is owned and bankrolled by the operators of Stake.com, which
shapes both its economics (the famous 95/5 creator revenue split) and its
content policy (much higher tolerance for gambling, mature, and political
content than Twitch).

For an automation/agent perspective, Kick exposes three surfaces:

- **Public Developer API** (`api.kick.com/public/v1`) — REST, OAuth 2.0 with
  PKCE, hosted at `id.kick.com`. Launched 2024, expanded through 2025. Smaller
  than Twitch Helix but covers users, channels, categories, livestream status,
  chat send, moderation, and event subscriptions.
- **Pusher WebSocket** — Kick's chat and live events ride on Pusher channels
  (e.g. `chatrooms.<id>`, `channel.<id>`). Same transport whether you arrive
  via the official SDK or a reverse-engineered client.
- **Webhooks (event subscriptions)** — POST to `/public/v1/events/subscriptions`
  to receive HTTP callbacks for chat messages, follows, subs, gifted subs,
  livestream metadata, and moderation bans. Kick retries 3x and auto-unsubscribes
  on persistent failure.

Where the API does not yet cover something (full analytics, schedule editing,
clip CMS), the fallback is Playwright web automation against `kick.com` —
Kick has minimal bot defenses compared to Twitch and Instagram.

## EOS Integration

Kick is **secondary / exploratory** for Antony's personal brand. The thesis:
audience diversification away from algorithm-locked-in platforms, combined with
materially better revenue economics if and when an audience forms there. Today
this skill exists so EOS agents can:

- **Evaluate the platform** before committing live time. Read category sizes,
  competitor activity, top-stream watch hours.
- **Cross-post clips** from Twitch/YouTube/Instagram to Kick automatically once
  a Kick channel exists. The 95/5 split only matters if there are clips on the
  channel for casual discovery.
- **Monitor the channel** once live: webhook on `livestream.status.updated` →
  EOS event bus → Discord ping → optional Reels/Shorts repurpose pipeline.
- **Plan stream schedules** in concert with the OBS skill (separate, this wave)
  and the Restream skill (when added) so a single OBS scene set goes to Kick +
  Twitch + YouTube without human intervention.
- **Honest gating:** EOS will NOT recommend going Kick-exclusive (95/5 + partner
  status) until there is a real audience. The exclusivity tradeoff is a
  business decision, not an automation decision.

## Authentication

OAuth 2.0 with **mandatory PKCE** for both flows. Authorization server:
`https://id.kick.com`. API base: `https://api.kick.com/public/v1`.

Two token types:

- **App Access Token** — `client_credentials` grant, server-to-server, used for
  public data only. Good for "is this channel live?" polling.
- **User Access Token** — `authorization_code` grant with PKCE. Required for
  any write (chat, moderation, event subscription on behalf of a user).

Scopes (as of 2026-04-06):

- `user:read` — read authenticated user profile
- `channel:read` — read channel metadata
- `channel:write` — update stream title, category
- `chat:write` — send chat messages
- `streamkey:read` — fetch stream key (sensitive — treat like a password)
- `events:subscribe` — create webhook subscriptions

Refresh tokens are issued and rotate. Store them encrypted in EOS memory and
re-rotate on every refresh — Kick may invalidate the previous one.

EOS storage convention: `.env` keys `KICK_CLIENT_ID`, `KICK_CLIENT_SECRET`,
plus per-user tokens in Neon `oauth_tokens` row keyed by `(provider='kick',
user_id, broadcaster_user_id)`. Never commit tokens; never log full bearer
strings.

## Quick Reference

### OAuth — App Access Token (server-to-server)

```bash
curl -X POST https://id.kick.com/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=$KICK_CLIENT_ID" \
  -d "client_secret=$KICK_CLIENT_SECRET" \
  -d "scope=channel:read events:subscribe"
```

### OAuth — User Access Token (PKCE flow)

1. Generate `code_verifier` (43-128 chars) and
   `code_challenge = base64url(sha256(verifier))`.
2. Send the user to:
   `https://id.kick.com/oauth/authorize?response_type=code&client_id=$ID&redirect_uri=$URI&scope=user:read+chat:write&code_challenge=$CHAL&code_challenge_method=S256&state=$STATE`
3. Exchange `code` at `/oauth/token` with `grant_type=authorization_code` plus
   the `code_verifier`.
4. Refresh with `grant_type=refresh_token` — rotate stored token.

### Read channel info

```bash
curl https://api.kick.com/public/v1/channels?slug=antonyfmunoz \
  -H "Authorization: Bearer $TOKEN"
```

### Send chat (requires user token + chat:write)

```bash
curl -X POST https://api.kick.com/public/v1/chat \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"broadcaster_user_id": 12345, "content": "hello chat", "type": "user"}'
```

### Subscribe to a webhook event

```bash
curl -X POST https://api.kick.com/public/v1/events/subscriptions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "method": "webhook",
    "broadcaster_user_id": 12345,
    "events": [
      {"name": "chat.message.sent", "version": 1},
      {"name": "channel.followed", "version": 1},
      {"name": "livestream.status.updated", "version": 1}
    ]
  }'
```

Validate every incoming webhook against the `Kick-Event-Signature` header
(Ed25519). Reject any payload that fails verification before doing anything.

### Pusher chat WebSocket (read-only firehose)

Connect to the Kick Pusher cluster, subscribe to `chatrooms.<chatroom_id>.v2`,
listen for `App\Events\ChatMessageEvent`. The chatroom id is on the channel
metadata response. Use a maintained Python lib (`kickpython`, `kick.py`) rather
than rolling your own — Pusher protocol is stable but Kick's channel naming
shifts.

## Conceptual Model

Kick is best understood as **the inverse of Twitch's tradeoffs**.

Twitch optimizes for: scale, advertiser safety, exclusivity rents, partner-tier
gatekeeping, and a mature creator economy. Kick optimizes for: creator payout,
fewer content rules, faster partner ladder, and being the platform of last
resort when Twitch bans you. Neither is morally superior — they are different
points on the same curve.

The platform-wars calculus EOS uses for Antony:

1. **Where is your audience right now?** A 95/5 split of zero is zero. Until
   there is a baseline audience, presence matters more than rev share.
2. **Can you stream to both?** Yes — Kick does not require exclusivity at any
   tier. The catch is Kick's *multistreaming partner tier* takes the 95/5 down
   toward roughly half if you simulcast to another full live platform. Vertical
   short-form (TikTok, Shorts) is exempt — that simulcast still qualifies for
   95/5.
3. **What are the brand-adjacency risks?** Kick's front page is heavy on
   gambling and slots streams. For a tactical-luxury personal brand, being
   discovered next to a slots stream is a real cost. Mitigate by linking to
   the channel directly, not asking the algorithm to do discovery.
4. **What is the discovery surface?** Smaller and more responsive than Twitch.
   Watch time, chat engagement, retention, and schedule consistency dominate.
   Category choice is binary: too small = no traffic, too big = invisible.
5. **What is the exit cost?** Lower than Twitch. Kick has no Partner Plus
   exclusivity to lose. You can leave or come back without burning subs.

The conceptual takeaway: **treat Kick as an option, not a bet**. Hold the
infrastructure (account, OAuth app, OBS scene preset, cross-post pipeline)
ready to activate when there is a strategic reason, and otherwise keep
attention on the primary platform.

## Gotchas

- **The Public API is young (launched 2024).** Endpoints, scopes, and event
  names have shifted multiple times in 2025. Pin the date you researched
  (this skill: 2026-04-06), re-verify before any new build, and watch the
  `KickEngineering/KickDevDocs` GitHub issues for breaking changes.
- **`api/v2` is NOT the public API.** It is the website's internal API,
  unofficial and undocumented. Many community libraries still use it because
  the public API took years to ship. It works today, breaks tomorrow, and
  Cloudflare bot detection can lock you out. Prefer the public API for any
  EOS-critical path.
- **PKCE is mandatory.** Kick rejects authorization-code flows without
  `code_challenge`. There is no plain client-secret-only user flow.
- **Refresh tokens rotate.** After every refresh, store the new refresh token;
  the old one is invalidated. Race conditions across two workers refreshing
  at the same time will brick the account — use a single-flight refresh.
- **Webhook signatures are Ed25519, not HMAC-SHA256.** Don't reuse Twitch's
  EventSub verification code blindly. Fetch Kick's public key from
  `/public/v1/public-key` and verify with `cryptography.hazmat`.
- **Webhook auto-unsubscribe.** Three failed deliveries (non-2xx, timeout,
  unreachable) and Kick drops the subscription silently. EOS must monitor
  subscription state and re-create on a schedule.
- **Multistream policy is a financial trap.** Going partner and then turning
  on multistream to Twitch/YouTube can quietly cut the rev share roughly in
  half. Verticals (TikTok/Shorts) are exempt but the documentation has
  shifted — re-check before activating partner.
- **Stream key has its own scope.** `streamkey:read` is sensitive enough that
  Kick treats it as a separate scope. Do not request it in the default OAuth
  bundle; only request when actively configuring OBS.
- **Category policy differs from Twitch.** Some categories that get you
  insta-banned on Twitch are first-class on Kick. Other categories Twitch
  allows are de-prioritized on Kick. Don't assume parity.
- **Exclusivity contracts exist for the top creator deals** even though the
  standard partner program does not require exclusivity. Read any partnership
  offer carefully — the headline 95/5 may not be the actual deal.
- **No public analytics API yet.** Stream analytics (avg viewers, retention,
  follow conversion) live in the Creator Dashboard only. EOS analytics
  pipelines need Playwright-against-dashboard until Kick ships endpoints.
- **Rate limits are documented poorly.** Expect 429s. Always implement
  exponential backoff and respect any `Retry-After` header. Build for
  surprise tightening.

See references/best_practices.md for the full 19-section creator-level
knowledge base, including pagination, error catalog, Pusher idioms, the
problem-solution map, EOS usage patterns, and the gotchas catalog.
=======
---
name: kick
description: "Use when evaluating Kick as a streaming platform, cross-posting live content or clips from Twitch/YouTube, analyzing Kick audience dynamics, designing multi-platform streaming workflows, or monitoring Kick channels via any available API/webhook surface."
allowed-tools: "Read, Bash, Write, Edit, WebFetch"
version: 1.0
source_url: "https://docs.kick.com"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "Public API v1 (stable, growing) + legacy api/v2 (unofficial, undocumented)"
sdk_version: "HTTP / Pusher WebSocket / Playwright fallback"
speed_category: fast
---

# Tool: Kick

## What This Tool Does

Kick is a live-streaming platform launched in 2022 as a direct Twitch
competitor. It is owned and bankrolled by the operators of Stake.com, which
shapes both its economics (the famous 95/5 creator revenue split) and its
content policy (much higher tolerance for gambling, mature, and political
content than Twitch).

For an automation/agent perspective, Kick exposes three surfaces:

- **Public Developer API** (`api.kick.com/public/v1`) — REST, OAuth 2.0 with
  PKCE, hosted at `id.kick.com`. Launched 2024, expanded through 2025. Smaller
  than Twitch Helix but covers users, channels, categories, livestream status,
  chat send, moderation, and event subscriptions.
- **Pusher WebSocket** — Kick's chat and live events ride on Pusher channels
  (e.g. `chatrooms.<id>`, `channel.<id>`). Same transport whether you arrive
  via the official SDK or a reverse-engineered client.
- **Webhooks (event subscriptions)** — POST to `/public/v1/events/subscriptions`
  to receive HTTP callbacks for chat messages, follows, subs, gifted subs,
  livestream metadata, and moderation bans. Kick retries 3x and auto-unsubscribes
  on persistent failure.

Where the API does not yet cover something (full analytics, schedule editing,
clip CMS), the fallback is Playwright web automation against `kick.com` —
Kick has minimal bot defenses compared to Twitch and Instagram.

## EOS Integration

Kick is **secondary / exploratory** for Antony's personal brand. The thesis:
audience diversification away from algorithm-locked-in platforms, combined with
materially better revenue economics if and when an audience forms there. Today
this skill exists so EOS agents can:

- **Evaluate the platform** before committing live time. Read category sizes,
  competitor activity, top-stream watch hours.
- **Cross-post clips** from Twitch/YouTube/Instagram to Kick automatically once
  a Kick channel exists. The 95/5 split only matters if there are clips on the
  channel for casual discovery.
- **Monitor the channel** once live: webhook on `livestream.status.updated` →
  EOS event bus → Discord ping → optional Reels/Shorts repurpose pipeline.
- **Plan stream schedules** in concert with the OBS skill (separate, this wave)
  and the Restream skill (when added) so a single OBS scene set goes to Kick +
  Twitch + YouTube without human intervention.
- **Honest gating:** EOS will NOT recommend going Kick-exclusive (95/5 + partner
  status) until there is a real audience. The exclusivity tradeoff is a
  business decision, not an automation decision.

## Authentication

OAuth 2.0 with **mandatory PKCE** for both flows. Authorization server:
`https://id.kick.com`. API base: `https://api.kick.com/public/v1`.

Two token types:

- **App Access Token** — `client_credentials` grant, server-to-server, used for
  public data only. Good for "is this channel live?" polling.
- **User Access Token** — `authorization_code` grant with PKCE. Required for
  any write (chat, moderation, event subscription on behalf of a user).

Scopes (as of 2026-04-06):

- `user:read` — read authenticated user profile
- `channel:read` — read channel metadata
- `channel:write` — update stream title, category
- `chat:write` — send chat messages
- `streamkey:read` — fetch stream key (sensitive — treat like a password)
- `events:subscribe` — create webhook subscriptions

Refresh tokens are issued and rotate. Store them encrypted in EOS memory and
re-rotate on every refresh — Kick may invalidate the previous one.

EOS storage convention: `.env` keys `KICK_CLIENT_ID`, `KICK_CLIENT_SECRET`,
plus per-user tokens in Neon `oauth_tokens` row keyed by `(provider='kick',
user_id, broadcaster_user_id)`. Never commit tokens; never log full bearer
strings.

## Quick Reference

### OAuth — App Access Token (server-to-server)

```bash
curl -X POST https://id.kick.com/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=$KICK_CLIENT_ID" \
  -d "client_secret=$KICK_CLIENT_SECRET" \
  -d "scope=channel:read events:subscribe"
```

### OAuth — User Access Token (PKCE flow)

1. Generate `code_verifier` (43-128 chars) and
   `code_challenge = base64url(sha256(verifier))`.
2. Send the user to:
   `https://id.kick.com/oauth/authorize?response_type=code&client_id=$ID&redirect_uri=$URI&scope=user:read+chat:write&code_challenge=$CHAL&code_challenge_method=S256&state=$STATE`
3. Exchange `code` at `/oauth/token` with `grant_type=authorization_code` plus
   the `code_verifier`.
4. Refresh with `grant_type=refresh_token` — rotate stored token.

### Read channel info

```bash
curl https://api.kick.com/public/v1/channels?slug=antonyfmunoz \
  -H "Authorization: Bearer $TOKEN"
```

### Send chat (requires user token + chat:write)

```bash
curl -X POST https://api.kick.com/public/v1/chat \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"broadcaster_user_id": 12345, "content": "hello chat", "type": "user"}'
```

### Subscribe to a webhook event

```bash
curl -X POST https://api.kick.com/public/v1/events/subscriptions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "method": "webhook",
    "broadcaster_user_id": 12345,
    "events": [
      {"name": "chat.message.sent", "version": 1},
      {"name": "channel.followed", "version": 1},
      {"name": "livestream.status.updated", "version": 1}
    ]
  }'
```

Validate every incoming webhook against the `Kick-Event-Signature` header
(Ed25519). Reject any payload that fails verification before doing anything.

### Pusher chat WebSocket (read-only firehose)

Connect to the Kick Pusher cluster, subscribe to `chatrooms.<chatroom_id>.v2`,
listen for `App\Events\ChatMessageEvent`. The chatroom id is on the channel
metadata response. Use a maintained Python lib (`kickpython`, `kick.py`) rather
than rolling your own — Pusher protocol is stable but Kick's channel naming
shifts.

## Conceptual Model

Kick is best understood as **the inverse of Twitch's tradeoffs**.

Twitch optimizes for: scale, advertiser safety, exclusivity rents, partner-tier
gatekeeping, and a mature creator economy. Kick optimizes for: creator payout,
fewer content rules, faster partner ladder, and being the platform of last
resort when Twitch bans you. Neither is morally superior — they are different
points on the same curve.

The platform-wars calculus EOS uses for Antony:

1. **Where is your audience right now?** A 95/5 split of zero is zero. Until
   there is a baseline audience, presence matters more than rev share.
2. **Can you stream to both?** Yes — Kick does not require exclusivity at any
   tier. The catch is Kick's *multistreaming partner tier* takes the 95/5 down
   toward roughly half if you simulcast to another full live platform. Vertical
   short-form (TikTok, Shorts) is exempt — that simulcast still qualifies for
   95/5.
3. **What are the brand-adjacency risks?** Kick's front page is heavy on
   gambling and slots streams. For a tactical-luxury personal brand, being
   discovered next to a slots stream is a real cost. Mitigate by linking to
   the channel directly, not asking the algorithm to do discovery.
4. **What is the discovery surface?** Smaller and more responsive than Twitch.
   Watch time, chat engagement, retention, and schedule consistency dominate.
   Category choice is binary: too small = no traffic, too big = invisible.
5. **What is the exit cost?** Lower than Twitch. Kick has no Partner Plus
   exclusivity to lose. You can leave or come back without burning subs.

The conceptual takeaway: **treat Kick as an option, not a bet**. Hold the
infrastructure (account, OAuth app, OBS scene preset, cross-post pipeline)
ready to activate when there is a strategic reason, and otherwise keep
attention on the primary platform.

## Gotchas

- **The Public API is young (launched 2024).** Endpoints, scopes, and event
  names have shifted multiple times in 2025. Pin the date you researched
  (this skill: 2026-04-06), re-verify before any new build, and watch the
  `KickEngineering/KickDevDocs` GitHub issues for breaking changes.
- **`api/v2` is NOT the public API.** It is the website's internal API,
  unofficial and undocumented. Many community libraries still use it because
  the public API took years to ship. It works today, breaks tomorrow, and
  Cloudflare bot detection can lock you out. Prefer the public API for any
  EOS-critical path.
- **PKCE is mandatory.** Kick rejects authorization-code flows without
  `code_challenge`. There is no plain client-secret-only user flow.
- **Refresh tokens rotate.** After every refresh, store the new refresh token;
  the old one is invalidated. Race conditions across two workers refreshing
  at the same time will brick the account — use a single-flight refresh.
- **Webhook signatures are Ed25519, not HMAC-SHA256.** Don't reuse Twitch's
  EventSub verification code blindly. Fetch Kick's public key from
  `/public/v1/public-key` and verify with `cryptography.hazmat`.
- **Webhook auto-unsubscribe.** Three failed deliveries (non-2xx, timeout,
  unreachable) and Kick drops the subscription silently. EOS must monitor
  subscription state and re-create on a schedule.
- **Multistream policy is a financial trap.** Going partner and then turning
  on multistream to Twitch/YouTube can quietly cut the rev share roughly in
  half. Verticals (TikTok/Shorts) are exempt but the documentation has
  shifted — re-check before activating partner.
- **Stream key has its own scope.** `streamkey:read` is sensitive enough that
  Kick treats it as a separate scope. Do not request it in the default OAuth
  bundle; only request when actively configuring OBS.
- **Category policy differs from Twitch.** Some categories that get you
  insta-banned on Twitch are first-class on Kick. Other categories Twitch
  allows are de-prioritized on Kick. Don't assume parity.
- **Exclusivity contracts exist for the top creator deals** even though the
  standard partner program does not require exclusivity. Read any partnership
  offer carefully — the headline 95/5 may not be the actual deal.
- **No public analytics API yet.** Stream analytics (avg viewers, retention,
  follow conversion) live in the Creator Dashboard only. EOS analytics
  pipelines need Playwright-against-dashboard until Kick ships endpoints.
- **Rate limits are documented poorly.** Expect 429s. Always implement
  exponential backoff and respect any `Retry-After` header. Build for
  surprise tightening.

See references/best_practices.md for the full 19-section creator-level
knowledge base, including pagination, error catalog, Pusher idioms, the
problem-solution map, EOS usage patterns, and the gotchas catalog.
>>>>>>> Stashed changes
