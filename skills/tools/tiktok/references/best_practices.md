# TikTok — Creator-Level Best Practices

Source: https://developers.tiktok.com/doc
API Version: v2 (`open.tiktokapis.com/v2`)
SDK Version: HTTP only — no first-party Python or Node SDK
  (community alternatives: `TikTokApi` (unofficial scraper),
  `pyktok`, `traktok` (R, Research API), `oauth2-tiktok` (PHP))
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## Authentication

TikTok uses OAuth 2.0 Authorization Code grant. Confidential clients
authenticate with `client_secret`; public clients (mobile, SPA) should use
PKCE (`code_challenge` / `code_verifier`).

### Authorization request

Browser redirect:

```
https://www.tiktok.com/v2/auth/authorize/
  ?client_key=YOUR_CLIENT_KEY
  &scope=user.info.basic,video.list,video.upload,video.publish
  &response_type=code
  &redirect_uri=https://your.app/oauth/tiktok/callback
  &state=RANDOM_CSRF_TOKEN
```

`state` is mandatory in any sane implementation; TikTok will echo it
back. `redirect_uri` must match exactly what's registered in the
developer portal.

### Token exchange

```bash
curl -X POST 'https://open.tiktokapis.com/v2/oauth/token/' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -H 'Cache-Control: no-cache' \
  --data-urlencode "client_key=$TIKTOK_CLIENT_KEY" \
  --data-urlencode "client_secret=$TIKTOK_CLIENT_SECRET" \
  --data-urlencode "code=$AUTH_CODE" \
  --data-urlencode "grant_type=authorization_code" \
  --data-urlencode "redirect_uri=$REDIRECT_URI"
```

Response (200):

```json
{
  "access_token": "act.example12345",
  "expires_in": 86400,
  "open_id": "_000abc...",
  "refresh_expires_in": 31536000,
  "refresh_token": "rft.example12345",
  "scope": "user.info.basic,video.list,video.upload,video.publish",
  "token_type": "Bearer"
}
```

### Refresh

```bash
curl -X POST 'https://open.tiktokapis.com/v2/oauth/token/' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode "client_key=$TIKTOK_CLIENT_KEY" \
  --data-urlencode "client_secret=$TIKTOK_CLIENT_SECRET" \
  --data-urlencode "grant_type=refresh_token" \
  --data-urlencode "refresh_token=$TIKTOK_REFRESH_TOKEN"
```

Each successful refresh issues a new `access_token` and may rotate the
`refresh_token`. The 365-day `refresh_expires_in` window is reset on
each refresh — so an active user effectively never re-consents.

### Revoke

```bash
curl -X POST 'https://open.tiktokapis.com/v2/oauth/revoke/' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode "client_key=$TIKTOK_CLIENT_KEY" \
  --data-urlencode "client_secret=$TIKTOK_CLIENT_SECRET" \
  --data-urlencode "token=$TIKTOK_ACCESS_TOKEN"
```

### Scope catalog

| Scope | Grants | Audit-gated |
|---|---|---|
| `user.info.basic` | `/v2/user/info/` minimal fields | No (default) |
| `user.info.profile` | full profile + bio | Yes |
| `user.info.stats` | follower/following/likes counts | Yes |
| `video.list` | `/v2/video/list/`, `/v2/video/query/` (own) | Yes |
| `video.upload` | upload to user inbox (drafts) | Yes |
| `video.publish` | direct publish without user tap-through | Yes |
| `research.adlib.basic` | Commercial Content Library | Yes |
| `research.data.basic` | Research API | Yes (2-week academic review) |

`open_id` is per-app (different across apps). `union_id` is stable
across apps owned by the same developer account — use it for joining
analytics across multiple TikTok apps you own.

## Core Operations with Exact Signatures

All endpoints are HTTPS, all responses are JSON, all auth is
`Authorization: Bearer <access_token>` unless noted.

### Display API — `/v2/user/info/`

```
GET https://open.tiktokapis.com/v2/user/info/?fields=open_id,union_id,avatar_url,avatar_url_100,avatar_large_url,display_name,bio_description,profile_deep_link,is_verified,follower_count,following_count,likes_count,video_count
```

Field selection is mandatory. Requesting `follower_count`,
`following_count`, `likes_count`, `video_count` requires the
`user.info.stats` scope; bio + display_name require `user.info.profile`.

Response:

```json
{
  "data": {
    "user": {
      "open_id": "_000abc",
      "union_id": "_000xyz",
      "display_name": "Antony Munoz",
      "follower_count": 12345,
      "video_count": 87
    }
  },
  "error": {"code": "ok", "message": "", "log_id": "..."}
}
```

### Display API — `/v2/video/list/`

```
POST https://open.tiktokapis.com/v2/video/list/
  ?fields=id,create_time,cover_image_url,share_url,video_description,duration,height,width,title,embed_html,embed_link,like_count,comment_count,share_count,view_count
```

Body:

```json
{"max_count": 20, "cursor": 1712345678000}
```

`max_count` ≤ 20. `cursor` is the unix-ms `create_time` of the oldest
post on the previous page; omit on first call. Response includes
`videos[]`, `cursor`, `has_more`.

### Display API — `/v2/video/query/`

```
POST https://open.tiktokapis.com/v2/video/query/?fields=id,title,view_count,like_count,comment_count,share_count
```

Body:

```json
{"filters": {"video_ids": ["7000000000000000001", "7000000000000000002"]}}
```

Up to 20 IDs per call. Used to fetch fresh stats on a known set of the
authorized user's posts (e.g., nightly performance refresh).

### Content Posting API — Direct Post init

```
POST https://open.tiktokapis.com/v2/post/publish/video/init/
Content-Type: application/json; charset=UTF-8
```

Body — `FILE_UPLOAD`:

```json
{
  "post_info": {
    "title": "Caption text including #hashtags and @mentions",
    "privacy_level": "PUBLIC_TO_EVERYONE",
    "disable_duet": false,
    "disable_comment": false,
    "disable_stitch": false,
    "video_cover_timestamp_ms": 1000,
    "brand_content_toggle": false,
    "brand_organic_toggle": false
  },
  "source_info": {
    "source": "FILE_UPLOAD",
    "video_size": 12345678,
    "chunk_size": 10000000,
    "total_chunk_count": 2
  }
}
```

Body — `PULL_FROM_URL`:

```json
{
  "post_info": { "...": "..." },
  "source_info": {
    "source": "PULL_FROM_URL",
    "video_url": "https://verified.your-domain.com/video.mp4"
  }
}
```

`video_url` host must be added and verified in the developer portal
under "URL Properties" before this works.

`privacy_level` enum: `PUBLIC_TO_EVERYONE`, `MUTUAL_FOLLOW_FRIENDS`,
`FOLLOWER_OF_CREATOR`, `SELF_ONLY`. Unaudited apps are forced to
`SELF_ONLY`.

Response:

```json
{
  "data": {
    "publish_id": "v_pub_url~v2-1.7000000",
    "upload_url": "https://open-upload.tiktokapis.com/upload/?upload_id=...&upload_token=..."
  },
  "error": {"code": "ok", "message": "", "log_id": "..."}
}
```

### Content Posting API — chunk upload

```
PUT <upload_url>
Content-Type: video/mp4
Content-Length: <chunk_bytes>
Content-Range: bytes 0-9999999/12345678
```

Each chunk PUTs to the same `upload_url` with a different
`Content-Range`. After the last chunk, TikTok responds with HTTP 201.

### Content Posting API — Upload-to-inbox (draft) flow

```
POST https://open.tiktokapis.com/v2/post/publish/inbox/video/init/
```

Same body shape as Direct Post but minus `post_info` (the user fills
caption/privacy in the TikTok app). Uses `video.upload` scope, not
`video.publish`. Result lands in the user's TikTok inbox where they
finish posting manually. **This is the safer option for unaudited
apps and the EOS-recommended path** because it always keeps a human
in the loop.

### Content Posting API — status fetch

```
POST https://open.tiktokapis.com/v2/post/publish/status/fetch/
```

Body:

```json
{"publish_id": "v_pub_url~v2-1.7000000"}
```

Response:

```json
{
  "data": {
    "status": "PUBLISH_COMPLETE",
    "publicaly_available_post_id": ["7000000000000000099"],
    "uploaded_bytes": 12345678,
    "fail_reason": ""
  },
  "error": {"code": "ok", "message": "", "log_id": "..."}
}
```

Status enum:

| Status | Meaning |
|---|---|
| `PROCESSING_UPLOAD` | TikTok is receiving the file chunks |
| `PROCESSING_DOWNLOAD` | (PULL_FROM_URL) TikTok is fetching from your URL |
| `SEND_TO_USER_INBOX` | Inbox flow only — landed as draft |
| `PUBLISH_COMPLETE` | Direct post — live on the user's profile |
| `FAILED` | Inspect `fail_reason` |

### Creator Info query (Direct Post pre-flight)

```
POST https://open.tiktokapis.com/v2/post/publish/creator_info/query/
```

Returns the user's allowed `privacy_level_options`,
`comment_disabled`, `duet_disabled`, `stitch_disabled`,
`max_video_post_duration_sec`, and `creator_username`. **Call this
before** every Direct Post init — never hard-code privacy levels,
because some accounts (e.g., under-18) have restricted options and
the post will reject with a confusing error otherwise.

### Research API — `/v2/research/video/query/`

```
POST https://open.tiktokapis.com/v2/research/video/query/?fields=id,video_description,create_time,region_code,share_count,view_count,like_count,comment_count,music_id,hashtag_names,username,effect_ids,playlist_id,voice_to_text
```

Body:

```json
{
  "query": {
    "and": [
      {"operation": "IN", "field_name": "region_code", "field_values": ["US"]},
      {"operation": "EQ", "field_name": "hashtag_name", "field_values": ["lifemaxing"]}
    ]
  },
  "max_count": 100,
  "cursor": 0,
  "start_date": "20260301",
  "end_date": "20260406"
}
```

Date window cannot exceed 30 days per request. `max_count` ≤ 100.
Approval-gated, academic-only — EOS does not qualify.

## Pagination Patterns

- **Display `/v2/video/list/`** — `cursor` is unix-ms create_time;
  pass back the value returned in the previous response. Stop when
  `has_more=false`. Sorted desc.
- **Display `/v2/video/query/`** — no pagination; pass up to 20 IDs
  per call.
- **Research video/comment endpoints** — `cursor` is an integer; pass
  back the integer from the previous response. Stop on `has_more=false`
  or when you've hit the daily 1000-call cap.
- **Token endpoint** — N/A, not paginated.
- **Content Posting status fetch** — N/A, single-record polling.

Defensive idiom: cap pagination loops at a hard `max_pages` (e.g.
50) regardless of `has_more` to avoid infinite loops on a buggy API
day. Log every cursor advance.

## Rate Limits

TikTok publishes few hard numbers; what is documented:

- Sliding 1-minute window per (`app_id`, `open_id`) pair.
- HTTP 429, body `{"error":{"code":"rate_limit_exceeded","message":"..."}}`.
- Headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`,
  `X-RateLimit-Reset` (epoch seconds when the window resets).
- Research API: 1,000 requests/day, 100,000 records/day across all
  research endpoints combined.
- Content Posting: per-user posting cap exists (commonly cited as
  ~6 direct posts per 24h for new apps; raised after audit).
  Additional throttling on init→upload→status state machine to
  prevent thrashing.
- TikTok Shop API (separate product) has its own published limits
  via Partner Center — out of scope for this skill.

Recovery rules:

1. On 429, sleep until `X-RateLimit-Reset` then retry once.
2. Backoff base 2 seconds, exponential, max 5 retries.
3. Treat repeated 429s as a circuit-breaker signal — pause the
   batch job and alert.
4. Never parallelize Content Posting calls per user; always serial.

## Error Codes and Recovery

Top-level response shape:

```json
{
  "data": {...},
  "error": {
    "code": "...",
    "message": "...",
    "log_id": "20240406abc123",
    "intra_log_id": "..."
  }
}
```

`error.code` of `ok` (or empty) means success even though HTTP is 200.
Always inspect `error.code`, not just status.

| code | HTTP | Meaning | Recovery |
|---|---|---|---|
| `ok` | 200 | success | proceed |
| `access_token_invalid` | 401 | token rotated, expired, or scope removed | refresh, then retry once; if still failing trigger re-consent |
| `scope_not_authorized` | 403 | user never granted this scope | re-prompt OAuth with the missing scope |
| `unaudited_client_can_only_post_to_private_accounts` | 403 | sandbox app posting publicly | submit for audit; meanwhile force `privacy_level=SELF_ONLY` |
| `rate_limit_exceeded` | 429 | sliding window full | sleep until `X-RateLimit-Reset`, exponential backoff |
| `invalid_params` | 400 | bad request body / field combo | log full body, do not retry |
| `invalid_file_upload` | 400 | chunk size or format wrong | re-init upload, never patch in place |
| `spam_risk_too_many_posts` | 429 | per-user post cap | back off ≥1h, skip auto-retry |
| `spam_risk_user_banned_from_posting` | 403 | account moderation hold | escalate to human, do not retry |
| `internal_error` | 500 | TikTok-side | retry with backoff up to 3x |
| `server_unavailable` | 503 | TikTok-side | retry with backoff up to 3x |

OAuth-specific errors (returned by `/v2/oauth/token/`):

| `error` | Meaning |
|---|---|
| `invalid_request` | missing/duplicate parameter |
| `invalid_client` | bad `client_key`/`client_secret` |
| `invalid_grant` | code already used, expired, or redirect mismatch |
| `unauthorized_client` | grant type not enabled for this app |
| `unsupported_grant_type` | typo in `grant_type` |

## SDK Idioms

There is no first-party SDK. Build a thin Python client; the EOS
canonical pattern is a single class wrapping `requests.Session`:

```python
import os, time, requests
from typing import Any

class TikTokClient:
    BASE = "https://open.tiktokapis.com/v2"

    def __init__(self) -> None:
        self.s = requests.Session()
        self.s.headers["Authorization"] = f"Bearer {os.environ['TIKTOK_ACCESS_TOKEN']}"
        self.s.headers["Content-Type"] = "application/json"

    def _req(self, method: str, path: str, **kw: Any) -> dict:
        for attempt in range(5):
            r = self.s.request(method, f"{self.BASE}{path}", timeout=30, **kw)
            if r.status_code == 429:
                reset = int(r.headers.get("X-RateLimit-Reset", time.time() + 2 ** attempt))
                time.sleep(max(1, reset - int(time.time())))
                continue
            body = r.json()
            err = (body.get("error") or {}).get("code", "ok")
            if err in ("ok", "", None):
                return body["data"]
            if err == "access_token_invalid":
                self._refresh()
                continue
            raise RuntimeError(f"TikTok {err}: {body['error'].get('message')}")
        raise RuntimeError("TikTok: retries exhausted")

    def _refresh(self) -> None:
        ...  # POST /v2/oauth/token/ grant_type=refresh_token, mutate self.s headers
```

Community packages exist but each has serious caveats:

- **`TikTokApi`** (Python, davidteather) — unofficial scraper using
  Playwright + browser fingerprints. Not for production.
  Bans, captchas, ToS exposure. Useful for one-off research only.
- **`pyktok`** — academic scraper, also ToS-grey.
- **`traktok`** (R) — wraps Research API; only useful if you have
  research credentials.
- **`oauth2-tiktok`** (PHP, bastiaandewaele) — League OAuth2 provider.
  Useful as a reference for the OAuth dance.

EOS recommendation: own your HTTP client. The API is small enough.

## Anti-Patterns

- **Polling status every second.** Backoff 2s → 5s → 15s → 60s. The
  state machine is slow on TikTok's side and over-polling will earn
  a 429 before your video is even ingested.
- **Treating Display API as analytics.** It returns lifetime totals
  only, not time-series. For trend analysis, snapshot nightly into
  Neon and compute deltas yourself.
- **Hardcoding privacy_level.** Always read `creator_info/query`
  first; under-18 accounts disallow `PUBLIC_TO_EVERYONE`.
- **Catching all exceptions silently.** TikTok 401s usually mean a
  user revoked consent. Surface, don't swallow.
- **Storing one access token shared across users.** Tokens are
  per-(`app_id`, `open_id`). Multi-user EOS instances must keep a
  token table keyed by `open_id`.
- **Auto-posting "for the user."** Even when audited, EOS policy is
  human-in-the-loop publish. Use the inbox flow.
- **Parallelizing chunk uploads.** Sequential only — TikTok will
  reject out-of-order chunks.
- **Trusting webhook delivery as the only signal.** Always reconcile
  via status polling; webhooks miss a non-trivial fraction.
- **Embedding `client_secret` in mobile or browser code.** Use PKCE
  + a server-side token exchange.
- **Using the legacy `/v1/` Display endpoints.** Deprecated; rewrite.
- **Pulling competitor stats via the official API.** Impossible —
  the Display API is "your own posts only." Use Apify scrapers.

## Data Model

Three first-class entities:

- **User** — keyed by `open_id` (per-app) and `union_id` (per-developer).
  Carries display_name, avatar, bio, follower_count, following_count,
  likes_count, video_count, is_verified.
- **Video** — keyed by 19-digit `id`. Carries title (often empty;
  the *real* caption is `video_description`), duration (seconds),
  cover_image_url (CDN-hosted, expires), share_url, embed_html,
  view_count, like_count, comment_count, share_count, create_time
  (unix seconds). Music, hashtags, and effects are not exposed via
  Display API — only via Research.
- **Publish job** — ephemeral, keyed by `publish_id`. Carries status,
  uploaded_bytes, fail_reason, and on success the resulting
  `publicaly_available_post_id` (note the spelling — it really is
  misspelled in the API response).

Relationships:

- A user has many videos. The Display API returns the authorized
  user's own videos only.
- A publish job either resolves into a video (Direct Post) or into
  a draft in the user's inbox (Upload flow).
- Hashtags, sounds, and effects are first-class on the FYP side but
  second-class in the Display API — Research API exposes them as
  separate fields.

CDN URL gotcha: `cover_image_url`, `share_url`, and `embed_link` are
**signed and time-limited**. Treat them as cache references, not
permalinks. The stable identifier is the video `id`.

## Webhooks and Events

Configured per-app in the developer portal under "Webhooks." Payloads
POST as JSON over HTTPS. Must respond 200 within a few seconds.

Event types:

| Event | Fires when |
|---|---|
| `post.publish.complete` (modern) / `video.publish.complete` (legacy) | Inbox-flow upload becomes a published post |
| `video.upload.failed` | Inbox-flow upload failed processing |
| `authorization.removed` | User revoked your app in TikTok settings |
| `app.removed` | User uninstalled / removed connection |

Payload shape:

```json
{
  "client_key": "aw...",
  "event": "post.publish.complete",
  "create_time": 1712345678,
  "user_openid": "_000abc",
  "content": "{\"publish_id\":\"v_pub_url~v2-1...\",\"post_id\":\"7000...\"}"
}
```

`content` is a stringified JSON sub-object — parse twice. Field name
migrated from `share_id` (legacy) to `publish_id` (modern).

Verification: TikTok signs deliveries with an HMAC-SHA256 of the
raw body using your app's `client_secret`, sent in
`TikTok-Signature: t=<timestamp>,s=<sig>`. Compute
`HMAC_SHA256(client_secret, f"{t}.{raw_body}")` and compare in
constant time. Reject anything older than 5 minutes.

Default subscription is "all events" once a callback URL is set;
there is no per-event toggle in the portal.

## Limits

| Limit | Value |
|---|---|
| Max video file size (Direct Post) | 4 GB (practical), 128 MB final chunk |
| Max video duration | 10 minutes (most accounts), 60 minutes (eligible accounts) |
| Min video duration | 3 seconds |
| Min chunk size | 5 MB |
| Max chunk size | 64 MB (final chunk up to 128 MB) |
| Max chunks per upload | 1000 |
| Min chunks per upload | 1 |
| `upload_url` lifetime | 1 hour |
| Caption (`title`) max length | 2,200 characters (incl. hashtags) |
| Hashtags per post | unlimited in API; ~5 effective for ranking |
| Display `/v2/video/list/` `max_count` | 20 |
| Display `/v2/video/query/` IDs per call | 20 |
| Research `max_count` | 100 |
| Research date window | 30 days per query |
| Research daily quota | 1,000 calls / 100,000 records |
| Access token lifetime | ~24h (`expires_in=86400`) |
| Refresh token lifetime | ~365d (`refresh_expires_in=31536000`) |
| Webhook ack timeout | ~5 seconds |
| Webhook signature freshness | 5 minutes |
| Direct posts per user (unaudited) | ~6 / 24h (raised after audit) |

## Cost Model

All four APIs (Login Kit, Display, Content Posting, Research) are
**free** to use. There is no per-call billing. The "cost" is in
compliance:

- **Audit time.** First public-posting audit ≈ 1–3 weeks. Each new
  scope re-triggers audit.
- **Research approval.** ~2 weeks, requires non-profit/academic
  affiliation.
- **TikTok Shop API.** Separate product, separate Partner Center
  approval, separate rate limits, separate revenue share (not
  per-call cost). Out of scope for this skill.
- **Indirect cost.** Storage of refresh tokens and per-user state in
  Neon; CDN egress if you use `PULL_FROM_URL`; verified domain SSL.

Account economics (creator side, for context, not API cost):

- **Creativity Program Beta** payouts ~$0.40–$1.00 per 1,000
  qualified views (5s+ watch). Eligibility: 10K followers, 100K
  views/30 days, 18+, non-business account, US/UK/DE/FR/BR/JP/KR.
  Min video length: 1 minute.
- **TikTok Shop affiliate** commissions: 5–15% physical, 20–30%
  digital, negotiable up to 50%.

## Version Pinning

- API base: `https://open.tiktokapis.com/v2/` — pin `/v2/` in code.
- Legacy `/v1/` Display endpoints are deprecated; do not use.
- The legacy "Share Video API" (`tiktokapis.com/share/video/upload/`)
  is deprecated in favor of the Content Posting API. Migration was
  enforced in 2023.
- Webhook event names migrated from `video.publish.complete` to
  `post.publish.complete`; field renamed `share_id` → `publish_id`.
  Subscribe to both names during transition windows.
- Audit-state matters more than API version: an unaudited app on
  `/v2/` behaves differently than an audited one on the same code.
  Track audit state in your config alongside the API version.
- Document `last_researched: 2026-04-06` in this skill; re-research
  if any of: (a) audit submission rejected, (b) `invalid_params` on
  a previously-working call, (c) >6 months since last research,
  (d) TikTok announces a v3 base.

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

TikTok was built around one bet: **"the algorithm beats the
follow graph."** Where Instagram and YouTube ranked content by who
you follow first and what you watch second, TikTok inverted that.
Every video is treated as a fresh test. The For You Page (FYP) is
not a feed of subscriptions — it's a ranked stream from a global
candidate pool, scored by predicted engagement on you specifically.

This produces a few core tradeoffs the platform consciously made:

- **Discoverability over loyalty.** A new account can outperform a
  million-follower account on any given day. This is great for
  creators starting from zero. It is brutal for creators relying on
  audience compounding — every post starts cold.
- **Watch time over taps.** Likes, follows, and comments are
  *outputs* of watch time, not inputs. The algorithm deliberately
  weights passive completion over active engagement because passive
  is harder to fake.
- **Sound-first.** Audio is a first-class signal. A trending sound
  is a distribution multiplier; using it lifts your video's ceiling
  even if your content is mediocre. This was a deliberate import
  from musical.ly's heritage.
- **Vertical-only, full-screen, no breaks.** The UI commits to
  immersion. There are no preview thumbnails on the FYP — you cannot
  decide to skip a video before it starts playing.
- **Native editor as a moat.** CapCut (also ByteDance) is integrated
  at the OS level. Templates published in CapCut surface as remixable
  formats inside TikTok. Other platforms have no equivalent.

What TikTok deliberately did *not* build:

- Chronological feed (you can opt into one but it's buried).
- Strong creator-to-follower notification graph.
- A "share to story" surface comparable to Instagram.
- Programmatic posting at scale (the Content Posting API is
  intentionally throttled and audit-gated to keep the FYP clean).

## Problem-Solution Map and Hidden Capabilities

Things you can do on TikTok that aren't obvious from the API surface:

- **Stitch** — clip 1–5 seconds of someone else's video as a lead-in
  to your own. Used heavily for reaction/response chains. Disabled
  per-post via `disable_stitch=true`.
- **Duet** — record alongside another video in a split-screen frame.
  Vertical, horizontal, or PIP layout. Disabled via `disable_duet`.
- **Series** — paywalled multi-episode collections (creators with
  10K+ followers). Each episode 1–20 minutes. Sold inside the app.
  Not exposed in the API.
- **Live** — real-time streaming + gifts (creator monetization).
  1K follower minimum, age 18+. Separate from posted video.
- **Live Shopping** — products pinned during a Live broadcast,
  one-tap checkout. Dominant in beauty/fashion categories.
- **TikTok Shop** — full e-commerce (catalog, checkout, fulfillment,
  affiliate creators). Now ~$23B US GMV in 2025, growing fast.
- **Sounds** — every video creates a sound asset that can be
  remixed. A video that goes viral via its sound is the #1 organic
  growth pattern on the platform.
- **Templates** — short, slot-based formats (e.g., "trends" page)
  where you fill in clips against a beat-matched edit.
- **Effects (TikTok Effect Studio)** — AR effects creators publish.
  An effect that catches on becomes a discovery surface in itself.
- **Photo carousels** — multi-image posts with audio. Converted from
  "TikTok Now" experiments. Algorithmically push as a separate
  format and often get high reach with low effort.
- **Q&A** — pinned question prompts on your profile that fans answer
  with videos. Great for community-driven content pipelines.
- **Auto-captions** — automatic on-screen subtitles, native to the
  app. Required for accessibility ranking signal.
- **Voice effects** — pitch shifters, robot voices, Jessie. Often
  the difference between a video reading as native vs. as
  out-of-place ad content.
- **Green screen** — built-in chroma key with image, video, or
  webcam backgrounds. The default "talking-head over a screenshot"
  format relies on this.

The API surfaces *none* of this directly. All of it lives in the
human's hands inside the app.

## Operational Behavior and Edge Cases

How the FYP actually behaves, observed in practice:

- **Initial test pool.** Every new post is shown to ~200–500
  viewers within 30–90 minutes. The algorithm measures watch
  time, completion rate, replays, shares, comments, and
  "not interested" signals on this cohort.
- **Threshold gating.** If completion rate clears ~70% on the
  test pool, the post is promoted to a wider tier (5K–50K
  impressions). If it clears again, another tier. There are
  multiple gates on the way up.
- **Stall depth.** A post that stalls under 500 views is almost
  always a hook problem (first 3 seconds). A post that stalls at
  ~1K views is almost always a mid-video drop-off problem.
- **Resurrection windows.** TikTok periodically re-tests
  underperforming posts weeks or months later. A post can go viral
  long after it was published. Do not delete underperforming
  videos.
- **Shadow ban behavior.** Posts that contain flagged content
  (political, "controversial topics," external links in caption)
  silently get capped at low view counts. There's no notification.
  Symptom: a normally-1K-view account suddenly hitting 80–200 on
  every post.
- **First-3-seconds steepest drop.** Across the platform, average
  drop-off in seconds 1–3 is the largest single retention loss.
  Optimize the first 1.5–3 seconds with disproportionate care.
- **Follower count is not a ranking input.** Officially confirmed
  by TikTok. A video from a 100-follower account and a video from
  a 1M-follower account get the same starting test pool.
- **3-second qualified view rule (Creativity Program).** Only views
  ≥5 seconds count toward Creativity Program payout. This means
  a 6-second viral hook video earns nothing even at 10M views.
  Minimum 1-minute video length to be eligible.
- **Saves and shares > likes.** Save = "I want this again later."
  Share = "Someone else needs this." Both weight far higher than
  a tap-like.
- **Comment replies as a content surface.** Replying to a comment
  with a video creates a new post that inherits some thread
  context. Strong distribution lift on these.
- **Sound trends decay fast.** A trending sound has a 7–14 day
  half-life. Catching one on day 2–4 is the sweet spot; day 1 is
  too early (no one has it yet) and day 10 is too late.

## Ecosystem Position and Composition

TikTok sits at the center of the short-form video market and
defines the format. Adjacent surfaces are reactive:

| Platform | Position | EOS notes |
|---|---|---|
| **Instagram Reels** | Largest follower-graph network; Reels are bolted on. Discovery weaker, monetization (broad-licence music + ad share) stronger. | Always cross-post — same vertical, captions adapted. |
| **YouTube Shorts** | Largest watch-time engine; Shorts are an attention gateway to long-form. Best monetization at scale via Shorts ad share. | Cross-post and link to long-form on the same channel. |
| **Snapchat Spotlight** | Niche, paid creator program. Diminishing share. | Not a priority for EOS. |
| **LinkedIn video** | B2B-aligned, weak short-form behavior. | Adapt for personal-brand B2B narrative posts only. |
| **X video** | Long-form bias since 2024 changes. Short-form competes weakly. | Cross-post selectively. |

Composability — what TikTok plugs into:

- **CapCut** — same parent company. Native template integration,
  one-tap "Share to TikTok" with metadata preserved.
- **Opus Clip** — long-form to short-form repurposer. Drop a
  YouTube/podcast video, get 5–10 ranked short clips with captions
  pre-cut and reframed vertical.
- **Submagic** — fast caption styling for finished clips. Best
  output for "talking-head with bold animated captions" format.
- **Descript** — text-based podcast/video editing; good for the
  long-form upstream of Opus Clip.
- **Metricool / Later / Buffer** — cross-platform schedulers
  using the Content Posting API or inbox flow.
- **Notion + Airtable** — content calendars and idea libraries.
- **TikTok Creative Center** — first-party trends explorer (sounds,
  hashtags, creators). The most underused free resource on the
  platform.

## Trajectory and Evolution

State of TikTok as of 2026-04-06:

- **US legal status.** PAFACA (signed April 2024) required ByteDance
  to divest TikTok's US operations. Supreme Court upheld the law
  Jan 2025. Ban was technically in force Jan 19 2025 → Jan 22 2026
  but never enforced. As of December 18, 2025 a divestiture
  agreement was signed forming **TikTok USDS Joint Venture LLC**
  (Oracle, Silver Lake, MGX, others). Transaction reported complete
  Jan 22, 2026. **Net effect for EOS today: TikTok is operating
  normally in the US, on US-controlled infrastructure. Continue
  treating it as a primary distribution channel; do not assume
  long-term stability — diversify to Reels and Shorts in parallel.**
- **TikTok Shop expansion.** ~$23.4B US GMV in 2025, projected to
  exceed $30B by 2028. Tarte Cosmetics generated $40M+ on TikTok
  Shop, 88% via affiliate creators. Conversion ~4.7% (versus
  2–4% in conventional ecommerce). EOS-relevant when Lyfe Spectrum
  launches: the affiliate model is the path of least resistance.
- **Creativity Program.** Replaced the original Creator Fund;
  pays 25× more per 1,000 views (~$0.50–$1.00 vs ~$0.02–$0.04).
  74% of former Creator Fund creators report 312% higher monthly
  earnings. EOS is not yet eligible (need 10K followers).
- **AI-generated content.** TikTok aggressively flags AI faces and
  voices. Faceless AI-narrated channels still work but are
  declining; the FYP is rebalancing toward authentic human content.
  Implication for EOS: keep Antony's face on camera, do not lean
  on AI avatars.
- **Longer videos.** Push toward 1–3 minute and 3–10 minute
  content has been steady since 2023. Creativity Program *requires*
  ≥1 minute. The "15-second clip" era is over for monetization;
  it survives only for top-of-funnel virality.
- **Photo carousels** continue to over-index in reach for low effort.

## Conceptual Model and Solution Recipes

### The hook–edit–CTA structure

Every high-performing TikTok decomposes into three blocks:

1. **Hook (0–3 seconds).** A single visual + auditory + textual
   beat that stops the scroll. Layered hooks (visual interrupt
   + sound + on-screen text) outperform single-element hooks ~3×
   on 3-second hold. Optimal hook length: 1.5–3 seconds.
2. **Edit (3 seconds → end).** Sustained tension. Cut every 1–3
   seconds; never let a single shot breathe. On-screen text
   reinforces audio. The goal is to get the viewer past the 70%
   completion threshold.
3. **CTA (final 1–2 seconds).** Either an explicit ask ("follow
   for part 2", "save this") or an implicit loop (the last frame
   feeds the first frame so the video replays — replays are a
   ranking signal).

### Hook formulas that work in 2026

- **Pattern interrupt** — a visual that doesn't belong (sudden
  zoom, prop reveal, jump cut to a different location).
- **Curiosity gap** — open a loop the viewer must close ("Here's
  what nobody tells you about ___").
- **Bold claim** — a contrarian thesis stated as fact in the first
  syllable ("Discipline is a lie. Use this instead.").
- **Numbered list promise** — "5 things I do every morning that
  put me ahead of 99% of founders."
- **Question to camera** — direct address that mirrors the viewer's
  internal state ("Ever notice how nothing you build sticks?").
- **Result first** — show the outcome before the process ("This is
  how I went from $0 to $10K MRR in 90 days. Here's the playbook.").

### Batch filming workflow (EOS canonical)

Used by every high-output personal-brand creator:

1. **Idea capture (continuous)** — an Apple Notes / Notion inbox
   for hooks and topics throughout the week. Agent-fed.
2. **Script batch (one session, ~1h)** — convert 10–15 ideas into
   60-second scripts with hook + 3 beats + CTA. Voice-and-tone
   matched to brand voice memory.
3. **Wardrobe + setup (15m)** — single outfit, single light, single
   framing. Lyfe Spectrum apparel stack. Lock the camera once.
4. **Filming batch (one session, ~2h)** — record all 10–15 in a
   row. Two takes max per video. Do not edit while filming.
5. **CapCut import + rough cut (one session)** — apply a saved
   project template (font, color, caption position, transitions).
6. **Caption pass (Submagic)** — auto-captions, manual cleanup of
   brand terms.
7. **Hashtag + caption text (agent-drafted)** — generated against
   the script + brand voice memory. Antony approves in Notion.
8. **Schedule across the week** — manual posts, 1/day, optimal
   time per audience (typically 6–9 AM and 6–9 PM PT for
   US founder audience).
9. **Nightly performance pull** — Display API into Neon, deltas
   computed, world_pulse summary at morning brief.

### Repurposing pipeline (long-form → short-form)

1. Founder talk recorded (YouTube long-form, podcast, or live).
2. Transcript via Whisper / Descript.
3. Opus Clip ranks ~10 candidate clips with scores.
4. Top 5 imported into CapCut for re-cut (tighter hook, branded
   captions).
5. Cross-posted manually to TikTok, Reels, Shorts.
6. Long-form linked in bio / pinned comment.

## Industry Expert and Cutting-Edge Usage

How the top tier actually operates:

- **Top creators batch heavily.** Alex Hormozi, Codie Sanchez, and
  similar founder-creators film 15–30 videos in a single 2-hour
  session, post 1/day across platforms. Their "always-on" aesthetic
  is engineered, not organic.
- **Hook libraries.** Pro creators maintain a Notion / Airtable of
  150+ proven hook templates, scored by past performance, and
  refresh from competitor analysis weekly.
- **Sound surfing.** Use TikTok Creative Center daily to spot
  rising sounds (5,000–50,000 uses). The sweet spot to adopt is
  day 2–4 of a sound's curve.
- **Reply-to-comment flywheel.** Every viral video generates 5–20
  reply videos that compound on the same topic. The reply video
  inherits topic relevance and outperforms a fresh post.
- **Series formats.** "Day 1 of building a $10K/mo SaaS in
  public" — counted-day series outperform standalone videos
  because the fan base self-organizes around catching up.
- **Faceless infill.** Even face-on creators run 2–3 faceless
  formats (B-roll over voice-over) to test riskier topics
  without burning brand equity.
- **Distribution stack.** Creator → CapCut → TikTok primary →
  Reels mirror → Shorts mirror → newsletter digest of weekly
  best → podcast cross-cut. Five surfaces, one pipeline.
- **Cohort-based posting.** Some founders post in coordinated
  swarms with their team / mastermind to seed early engagement.
  TikTok does not officially permit coordinated inauthentic
  behavior, but engagement from your own organic team is fine.
- **A/B captions.** Same video, two caption variants posted to
  separate accounts (main + secondary). Whichever wins, the
  losing version gets deleted within 24h.
- **30-day kill rule.** If a format hasn't produced a hit in 30
  days, kill the format. Top creators rotate format families
  every 30–60 days.

## EOS Usage Patterns

### Script generation prompts for Antony

Agent task: "Generate 5 TikTok hook variants for the following
script idea. Each hook is 1–2 sentences, designed for the first
1.5–3 seconds, and must use one of: pattern interrupt, curiosity
gap, bold claim, numbered promise, or direct question. Voice =
brand voice memory (tactical luxury, structure over discipline,
direct, no hedging). Return as a numbered list with the hook
formula label after each. Topic: ___."

### Hook libraries for personal brand

- Stored in Notion under `Content / Hook Library`.
- Schema: `hook_text`, `formula`, `topic_tags`, `posted_on`,
  `result_views`, `result_completion_rate`, `winner_flag`.
- Refreshed weekly: nightly Display API job updates `result_*`
  fields. Wins (top quartile) are flagged and become templates.
- Loaded into agent context for every new script generation.

### Content batch planning

- Weekly job (Sunday night): agent reviews last week's wins,
  proposes next week's 7 video concepts (one per day),
  outputs to Notion `Content / Calendar`.
- Antony reviews Monday morning, films Tuesday, posts daily.
- Each row: `concept`, `hook`, `script`, `caption`, `hashtags`,
  `target_post_date`, `format` (talking-head | b-roll | photo
  carousel | reaction).

### Performance analysis pulls

- Nightly cron: pull `/v2/video/list/` with `view_count,
  like_count, comment_count, share_count, create_time` for the
  last 50 videos.
- Compute deltas vs. yesterday's snapshot in Neon
  (`tiktok_video_stats` table).
- Surface in morning brief: top 3 movers, any video that crossed
  a threshold (10K, 100K, 1M views), any video with anomalous
  share-to-view ratio (a viral signal).
- Feed wins back into the hook library.

### Repurposing to Reels and Shorts

- After Antony posts to TikTok, agent generates Reels and Shorts
  variants of the caption (Reels = same caption + 3 hashtags;
  Shorts = title-first format, 100 char title + description).
- Output to Notion task list with the original TikTok URL.
- Antony manually cross-posts (Meta and YouTube auth flows are
  separate skills: `meta_graph`, `youtube_data`).

### TikTok Shop affiliate (future, Lyfe Spectrum)

- Not active until Lyfe Spectrum has SKUs and a merchant account.
- Once live: agent maintains a "currently-promoted SKU" record;
  every script that wears Lyfe Spectrum gets the affiliate link
  generator skill called against the active SKU; link goes in
  caption as the official TikTok Shop affiliate format.

### Telegram / Discord approval loop

- Every agent-drafted post is posted as a preview message in
  the dedicated content review channel.
- Antony reacts with a thumbs-up to approve, thumbs-down to
  reject. Approved drafts are saved to Notion for filming day.
- Nothing autonomously hits `/v2/post/publish/`.

## Gotchas

Real failures and edge cases — add to this list when EOS hits one.

- **`unaudited_client_can_only_post_to_private_accounts`** —
  the most common first-error. Means your app is in dev mode.
  Submit for audit. While waiting, force `privacy_level=SELF_ONLY`
  in every Direct Post call.
- **`upload_url` expired mid-upload.** Re-init the publish job;
  cannot resume. EOS uploads >100MB should pre-stage chunks and
  PUT them within ~30 minutes of init to be safe.
- **Chunks under 5 MB except final.** A 6 MB file split into 3 MB
  chunks will reject. Either ship as 1 chunk or recompute chunk
  count to satisfy the 5 MB minimum.
- **`creator_info/query` not called.** Hard-coded
  `privacy_level=PUBLIC_TO_EVERYONE` posts will reject for under-18
  accounts and some flagged accounts. Always pre-flight.
- **Cover image timestamp out of range.** `video_cover_timestamp_ms`
  must be ≤ video duration. Off-by-one error is silent — the cover
  defaults to frame 0.
- **Title field vs caption.** `post_info.title` is the *caption* —
  hashtags and mentions live here, not in a separate field.
- **`view_count` lifetime, not 24h.** Display API metrics are
  cumulative. Time-series requires snapshotting yourself.
- **Webhook misses.** `post.publish.complete` does not always fire
  for Direct Post. Status polling is the source of truth.
- **`access_token_invalid` after long idle.** Refresh tokens
  rotate on use; if you don't refresh for ~365 days the user has
  to re-consent. Refresh proactively on a weekly cron.
- **Refresh response sometimes omits new `refresh_token`.** When
  it does omit, keep using the old one. Don't null it out.
- **HTTP 200 with `error.code != ok`.** Always inspect `error.code`,
  not just status.
- **CDN URL expiry.** `cover_image_url` and `share_url` are signed
  and expire. Re-fetch from `video/list/` when displaying;
  do not cache long-term. The stable identifier is `id`.
- **"Spam risk" lockouts.** A user account can hit a posting cap
  even via the API; backoff ≥1 hour and surface to the human.
- **Audit submission rejected for trivial reasons.** Demo video
  must show the *exact* user flow you described in the audit form.
  Any drift = rejection. Plan to submit twice.
- **`region_code` filter in Research API.** Region is the *uploader's*
  region, not the *viewer's* region. Don't conflate.
- **`open_id` is per-app.** A user with two of your apps installed
  has two `open_id`s. Use `union_id` to dedupe across your portfolio.
- **`publicaly_available_post_id` is misspelled in the response.**
  Yes, in production. Don't "fix" it on the parsing side.
- **Display API "your own" only.** Cannot read competitors. Apify
  scrapers fill this gap; do not try to bypass via the official API.
- **Cross-account auto-post.** Posting "as" multiple users from a
  single token is impossible — every user has their own tokens.
  EOS multi-tenant designs must store one (`open_id`,
  `access_token`, `refresh_token`) tuple per connected user.
- **AI-generated content flagging.** TikTok's AI-content classifier
  is aggressive and silent. Heavily AI-edited videos get throttled.
  Keep edits human-finished where possible.
- **`title` over 2,200 chars.** Hard reject. Strip silently before
  posting; log the truncation.
- **Hashtag count.** Unlimited in API but ranking saturates around
  3–5 relevant hashtags. More than 8 starts to look spammy.
- **Unicode emoji in caption.** Allowed but consume character
  budget at 2–4 chars each. Watch the 2,200 limit.
- **Sandbox does not show real reach.** Test posts go to
  `SELF_ONLY`; you cannot validate FYP behavior in sandbox at all.
  Validate hooks on Antony's real account.
- **Music licensing.** Trending sounds licensed only for organic
  use. The moment you mark `brand_content_toggle=true` (branded
  content), the trending sound library shrinks to a "commercial
  music library" subset. Plan accordingly.
- **`brand_content_toggle` legal requirement.** US FTC requires
  disclosure for paid promotions; TikTok enforces this via the
  toggle. Always set `true` for sponsored Lyfe Spectrum or
  Initiate Arena promo posts even if unpaid affiliate.
