---
name: tiktok
description: "Use when posting/scheduling TikTok content via the Content Posting API, querying video/user data via Display or Research API, designing creator workflows for short-form video, analyzing FYP performance, or planning TikTok content strategy for personal brand or commerce."
allowed-tools: "Read, Bash, Write, Edit, WebFetch"
version: 1.0
source_url: "https://developers.tiktok.com/doc"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "v2"
sdk_version: "HTTP / no first-party Python SDK (community: TikTokApi, pyktok, traktok)"
speed_category: fast
---

# Tool: TikTok

## What This Tool Does

TikTok is a short-form vertical-video network with two surfaces that matter for
EOS:

1. **The creator app** — where humans actually film, edit, and post. The
   algorithm (FYP ranking) is the distribution engine. Watch time, completion
   rate, replays, shares, and saves are the dominant signals; follower count is
   explicitly *not* a direct ranking factor.
2. **The developer platform** (`open.tiktokapis.com/v2`) — a set of OAuth-gated
   HTTP APIs that let an app post on behalf of a user, list/query that user's
   own videos, read basic profile data, or (with separate approval) query
   public videos for research.

The developer surface is split into four products:

- **Login Kit** — OAuth 2.0 user authorization, token issuance, refresh.
- **Content Posting API** — Direct Post (`/v2/post/publish/video/init/`) and
  Upload-to-inbox (`/v2/post/publish/inbox/video/init/`) flows. Both support
  `FILE_UPLOAD` (chunked PUT to a TikTok-issued URL) and `PULL_FROM_URL`
  (TikTok pulls from a domain you've verified).
- **Display API** — `/v2/user/info/`, `/v2/video/list/`, `/v2/video/query/`
  for the authorized user's own data.
- **Research API** — `/v2/research/video/query/`, `/v2/research/user/info/`,
  `/v2/research/comment/list/`. Approval-gated, restricted to academic /
  non-profit researchers, ~2 week review.

There is no first-party Python or Node SDK. Everything is HTTP + Bearer token.

## EOS Integration

TikTok is one of the primary distribution channels for Antony's personal
brand content (the marketing vehicle for Initiate Arena, Empyrean Studio,
and Lyfe Spectrum). EOS uses TikTok in three modes:

- **Personal brand (primary)** — Antony films and posts manually. Agents
  draft hooks, scripts, captions, and hashtag sets; analyze performance after
  the fact via Display API; flag winning patterns back into the brand voice
  memory. Posting is never autonomous.
- **Initiate Arena** — coaching content snippets repurposed from longer
  founder talks (CapCut/Opus Clip pipeline). Agents propose clip
  candidates from transcripts and write the on-screen text + caption.
- **Lyfe Spectrum** — apparel product clips (worn by Antony in
  brand content; product placement-style, not pitch-style). Eventually
  routes to TikTok Shop affiliate when the entity is operational.

Canonical EOS pattern:

- Tokens stored in `eos_ai/.env` as `TIKTOK_CLIENT_KEY`,
  `TIKTOK_CLIENT_SECRET`, `TIKTOK_ACCESS_TOKEN`, `TIKTOK_REFRESH_TOKEN`,
  `TIKTOK_REFRESH_EXPIRES_AT`.
- All draft outputs land as Notion documents under the Content DB; nothing
  ships to `/v2/post/publish/` without Antony's explicit confirmation in
  Telegram or Discord.
- Performance analysis runs from `/v2/video/list/` on a nightly job and
  feeds the world_pulse engine.

## Authentication

OAuth 2.0 Authorization Code grant. PKCE supported for public clients.

1. Send the user to:
   `https://www.tiktok.com/v2/auth/authorize/?client_key=...&scope=user.info.basic,video.list,video.upload,video.publish&response_type=code&redirect_uri=...&state=...`
2. TikTok redirects back with `?code=...&state=...`.
3. Exchange the code:

```bash
curl -X POST 'https://open.tiktokapis.com/v2/oauth/token/' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -H 'Cache-Control: no-cache' \
  -d "client_key=$TIKTOK_CLIENT_KEY" \
  -d "client_secret=$TIKTOK_CLIENT_SECRET" \
  -d "code=$AUTH_CODE" \
  -d "grant_type=authorization_code" \
  -d "redirect_uri=$REDIRECT_URI"
```

Response: `access_token`, `expires_in` (~24h), `refresh_token`,
`refresh_expires_in` (~365d), `open_id`, `scope`, `token_type=Bearer`.

Refresh:

```bash
curl -X POST 'https://open.tiktokapis.com/v2/oauth/token/' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d "client_key=$TIKTOK_CLIENT_KEY" \
  -d "client_secret=$TIKTOK_CLIENT_SECRET" \
  -d "grant_type=refresh_token" \
  -d "refresh_token=$TIKTOK_REFRESH_TOKEN"
```

`user.info.basic` is granted by default for any Login Kit app. Every other
scope must be added in the developer portal *and* re-approved in audit, *and*
re-consented by the user.

## Quick Reference

Get authorized user profile:

```bash
curl -X GET 'https://open.tiktokapis.com/v2/user/info/?fields=open_id,union_id,avatar_url,display_name,bio_description,follower_count,following_count,likes_count,video_count' \
  -H "Authorization: Bearer $TIKTOK_ACCESS_TOKEN"
```

List the authorized user's videos:

```bash
curl -X POST 'https://open.tiktokapis.com/v2/video/list/?fields=id,title,video_description,duration,cover_image_url,share_url,view_count,like_count,comment_count,share_count,create_time' \
  -H "Authorization: Bearer $TIKTOK_ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"max_count": 20}'
```

Pagination: pass `cursor` from the previous response; stop when
`has_more=false`. Display API max `max_count` is 20; Research API is 100.

Direct Post — initialize an upload (`FILE_UPLOAD` mode):

```bash
curl -X POST 'https://open.tiktokapis.com/v2/post/publish/video/init/' \
  -H "Authorization: Bearer $TIKTOK_ACCESS_TOKEN" \
  -H 'Content-Type: application/json; charset=UTF-8' \
  -d '{
    "post_info": {
      "title": "Structure over discipline. #lifemaxing",
      "privacy_level": "PUBLIC_TO_EVERYONE",
      "disable_duet": false,
      "disable_comment": false,
      "disable_stitch": false,
      "video_cover_timestamp_ms": 1000
    },
    "source_info": {
      "source": "FILE_UPLOAD",
      "video_size": 12345678,
      "chunk_size": 10000000,
      "total_chunk_count": 2
    }
  }'
```

Response returns `publish_id` and an `upload_url`. PUT each chunk with
`Content-Range: bytes START-END/TOTAL` and `Content-Type: video/mp4`. The
`upload_url` is valid for 1 hour.

Poll status:

```bash
curl -X POST 'https://open.tiktokapis.com/v2/post/publish/status/fetch/' \
  -H "Authorization: Bearer $TIKTOK_ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{\"publish_id\":\"$PUBLISH_ID\"}"
```

Status enum: `PROCESSING_UPLOAD` → `PROCESSING_DOWNLOAD` (PULL_FROM_URL only)
→ `SEND_TO_USER_INBOX` or `PUBLISH_COMPLETE` → terminal `FAILED`.

## Conceptual Model

Two layers, almost disconnected:

- **The algorithm layer** is what determines outcomes. The FYP test set is
  200–500 viewers in the first 30–90 minutes. If completion rate clears the
  ~70% threshold and shares/saves are non-trivial, distribution expands in
  waves. Watch time is the dominant signal, completion rate second, replays
  third. Likes are weak. Follower count is not a ranking input.
- **The API layer** is a thin posting/reading shell. It cannot influence
  ranking, cannot read FYP impressions of *other* users' videos
  (Display API is "your own posts only"), cannot read non-public metadata,
  and cannot trigger sounds, effects, or stitches programmatically. The
  Content Posting API is fundamentally a *delivery pipe* — the creative
  decisions still happen in CapCut and the human's hands.

Think of EOS as living entirely on the *creative + analytic* side: scripts
in, posts out (manually), metrics back in nightly. Treat the API as a
minimal IO surface, not as a growth lever.

## Gotchas

- **Sandbox approval bottleneck.** Apps in development mode can only post
  to the developer's own private account
  (`unaudited_client_can_only_post_to_private_accounts`). To post publicly
  you must submit for audit and pass review per scope. Plan 1–3 weeks.
  Adding a *new* scope after approval triggers another audit.
- **Video upload protocol quirks.** Chunks must be 5–64 MB except the
  *final* chunk which can be up to 128 MB. Files under 5 MB ship as a
  single chunk equal to the file size. Max 1000 chunks. Upload sequentially.
  The `upload_url` expires 1 hour after init.
- **Rate limit shape.** 1-minute sliding window per (app, user). HTTP 429
  with `error.code=rate_limit_exceeded`. Honor `X-RateLimit-Remaining` /
  `X-RateLimit-Reset`. Research API caps daily at 1,000 requests / 100,000
  records.
- **Status polling, not webhooks (for posting).** `post.publish.complete`
  webhook exists but only fires reliably for the older Video Kit *inbox*
  flow, not always for Direct Post. Always poll
  `/v2/post/publish/status/fetch/` as the source of truth.
- **Scope additions require re-approval AND re-consent.** Adding
  `video.publish` after launching with only `video.upload` means existing
  users must re-authorize. Old refresh tokens remain valid only for the
  old scopes.
- **Research API gating.** Restricted to approved academic / non-profit
  researchers. Approval ~2 weeks. EOS does *not* qualify — do not design
  any flow that depends on it.
- **No third-party-account analytics.** You cannot pull `view_count` for
  competitors via the official API. For competitor intel use Apify scrapers
  (separate skill: `apify_competitor_intelligence`), not TikTok APIs.
- **Version drift.** Legacy `/v1/` Display endpoints are deprecated. Always
  use `/v2/`.

See references/best_practices.md for full Tier 1 (technical mastery) and
Tier 2 (creator intelligence) — endpoint reference, error codes, FYP
mechanics, hook formulas, batch filming pipeline, and EOS usage patterns.
