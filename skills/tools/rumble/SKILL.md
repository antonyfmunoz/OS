---
name: rumble
description: "Use when cross-posting content to Rumble for audience diversification, monitoring Rumble channels via RSS, designing the YouTube → Rumble pipeline, planning Rumble-specific content strategy, or evaluating Rumble for personal brand alt-platform presence."
allowed-tools: "Read, Bash, Write, Edit, WebFetch"
version: 1.0
source_url: "https://help.rumble.com/Rumble-Upload-API.html"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "Simple Upload API (rumble.com/api/simple-upload.php) — gated, manual approval"
sdk_version: "HTTP multipart / Playwright fallback / OpenRSS proxy"
speed_category: stable
trigger: both
effort: low
context: fork
---

# Tool: Rumble

## What This Tool Does

Rumble is a US-based video hosting and live streaming platform positioned as a
free-speech / censorship-resistant alternative to YouTube. For creators it is
mainly a destination, not a developer surface — its public APIs are sparse,
gated, and largely undocumented compared to YouTube Data API v3.

What actually exists for developers in 2026:

- **Simple Upload API** (`https://rumble.com/api/simple-upload.php`) — a single
  multipart endpoint for posting a video file with title, description, channel,
  license, thumbnail, and closed captions. Access is gated: you must email
  `bd@rumble.com` to be issued a 40-character `access_token`. There is no
  self-service signup, no OAuth, no sandbox.
- **MRSS / JSON / OTT feeds** — Rumble Premium / PRO accounts can generate
  per-channel or whole-account feeds (MRSS, JSON, Roku JSON, Amazon Fire) from
  the dashboard for syndication. Free accounts cannot.
- **No public read API** for video metadata, stats, comments, or search. No
  webhooks. No event stream. No watch-history endpoint. No analytics API.
- **Channel pages and embeds** — `https://rumble.com/c/{channel}` and
  `https://rumble.com/embed/{video_id}/` are stable public surfaces and can be
  scraped or embedded.
- **Third-party RSS proxies** — `openrss.org/rumble.com/c/{channel}` and
  community projects like `rumble-rss` / `rumblerss` provide RSS feeds for any
  public channel without a PRO subscription. They scrape, so they break when
  Rumble's HTML changes.
- **Rumble Studio** — the live streaming product (separate from
  `studio.youtube.com` paradigm). Earnings tier eligibility is tied to streaming
  hours through Studio.
- **Rumble Cloud** — a completely separate IaaS product (VMs, object storage,
  Kubernetes). Not the video platform. Has its own OpenStack-based API. Out of
  scope for this skill.

The honest summary: if you want to programmatically interact with Rumble at
creator scale, you have one gated upload endpoint, an RSS-shaped read surface,
and the browser. Everything else is web automation.

## EOS Integration

Rumble is a **secondary** distribution channel for Antony's personal brand — an
audience-diversification and censorship-hedge play, not a primary acquisition
surface. Volume and engagement are an order of magnitude below YouTube; the
ROI per upload comes from low marginal cost, not high marginal return.

Concrete EOS use cases:

- **Cross-post pipeline (YouTube → Rumble)** — when a YouTube video is
  finalized, an EOS workflow re-uploads the same MP4 to Rumble with a
  Rumble-tuned title/description (no YouTube-specific CTAs, no "subscribe"
  language that doesn't map). Either via the Simple Upload API if Antony's
  `access_token` is provisioned, or via Playwright against the manual upload
  page if not.
- **Description rewriting** — Gemini-powered rewrite of the YouTube description
  to (a) strip YouTube-specific language, (b) add Rumble-native phrasing, (c)
  swap any "see comments" for inline links, (d) tag with Rumble-friendly hashes.
- **Channel monitoring** — pull Antony's own channel feed via OpenRSS (or
  Playwright if blocked) once per day to confirm uploads went live, capture the
  permalink, and write `rumble_url` back to the content row in Neon.
- **Performance pulling** — view counts and Rumble-Rank position are scraped
  from the public video page (no API). Stored alongside YouTube stats for
  cross-platform reporting.
- **Cross-platform link injection** — once a Rumble URL exists, future YouTube
  descriptions and email footers can include "also on Rumble: <link>" so the
  audiences cross-pollinate.

What EOS does NOT do with Rumble:

- No live streaming integration (Antony is not streaming on Rumble Studio).
- No monetization automation (creator program eligibility is manual,
  per-account, and paid out via check/PayPal, not API).
- No ad buy integration (Rumble Ads is a separate product, not in scope).

## Authentication

**Simple Upload API:** a single static `access_token` parameter, 40 hex chars,
issued manually by Rumble after you email `bd@rumble.com` with a use case.
There is no rotation endpoint, no OAuth flow, no scoped tokens. Treat the
token like a root credential: store it in `eos_ai/.env` as `RUMBLE_ACCESS_TOKEN`,
never commit, never echo it in logs, never put it in a query string. The token
is bound to a Rumble user account and uploads attribute to whatever channels
that account owns.

**MRSS / OTT feeds:** no token. The feed URLs themselves are unguessable
secrets generated in the dashboard for PRO accounts. Treat the URL as the
credential.

**Web automation fallback:** username + password against `https://rumble.com/login.php`.
Rumble does not currently force CAPTCHA on every login but does issue a
session cookie. Persist the cookie jar between Playwright runs to avoid
repeated logins. 2FA, if enabled on the account, blocks fully-headless flows —
disable 2FA on the dedicated upload account or run headed.

**Rumble Cloud (separate product):** OpenStack-style API tokens, irrelevant
to the video platform. Do not conflate.

## Quick Reference

### Simple Upload API (gated)

```bash
curl -X POST "https://rumble.com/api/simple-upload.php" \
  -F "access_token=${RUMBLE_ACCESS_TOKEN}" \
  -F "title=The Vigilante Architect — Episode 12" \
  -F "description=Long-form description, plain text, no YouTube-isms." \
  -F "license_type=0" \
  -F "channel_id=${RUMBLE_CHANNEL_ID}" \
  -F "video=@/opt/OS/exports/ep12.mp4" \
  -F "thumb=@/opt/OS/exports/ep12_thumb.jpg" \
  -F "cc_en=@/opt/OS/exports/ep12.srt"
```

Response is JSON: success flag, video ID, monetized URL, embed HTML/JS, or
error object. See `references/best_practices.md` § Endpoint Surface for the
field-by-field breakdown and the known `license_type` values.

### Channel feed via OpenRSS (free, no token)

```bash
# Antony's hypothetical channel slug = "antonyfmunoz"
curl -s "https://openrss.org/rumble.com/c/antonyfmunoz" | head -100
```

Returns standard RSS 2.0 with `<item>` per video, `<pubDate>`, `<link>`,
`<description>`. Parse with `feedparser` in Python. Cache aggressively —
OpenRSS is a courtesy, not an SLA.

### Manual upload checklist (when Simple Upload is unavailable)

1. Source MP4: H.264, 1080p, 30fps, AAC audio, 16:9, ≤15 GB (free) or ≤30 GB (Premium).
2. Duration plan: keep under 21 min for full 4K playback eligibility.
3. Title ≤100 chars, descriptive, no clickbait that violates community guidelines.
4. Description: rewrite from YouTube version, strip YouTube-only CTAs.
5. Thumbnail: 1280x720 JPEG.
6. License: choose Personal Use (most permissive for cross-posting) unless you
   want Rumble exclusivity bonuses.
7. Categories + tags from the upload form.
8. After publish, capture the permalink and write back to the content row.

### Cross-post one YouTube video

```bash
python3 -m eos_ai.workflows.rumble_cross_post \
  --youtube-id dQw4w9WgXcQ \
  --license-type 0 \
  --channel personal_brand
```

The workflow pulls the source MP4 from the YouTube export bucket, calls Gemini
to rewrite the description, posts via Simple Upload API, parses the response
JSON, and writes `rumble_url` + `rumble_video_id` back to the `content` table.

## Conceptual Model

**Rumble is a destination, not a platform.** Treat it the way you would treat
a Substack mirror or an RSS pingback target: a place your content also lives,
not a place where you build a primary audience. The math:

- Audience overlap with YouTube is partial — Rumble skews US, conservative,
  news-and-politics-heavy. Personal brand content that lands on YouTube under
  business / philosophy / entrepreneurship will get a fraction of the reach
  on Rumble, but a non-zero fraction, and the marginal cost of cross-posting
  is near zero once the pipeline exists.
- The censorship hedge is the real value: if a YouTube channel is struck or
  demonetized, having an active Rumble mirror with the same back catalog and
  the same audience link in every email footer means the audience can find
  you again in 24 hours instead of 3 months.
- Monetization is real but small at sub-1M-view scale. Rumble pays $2-10 per
  1000 views vs YouTube's $1-5, but the views are 5-50x lower. Net out: a
  rounding error on personal brand revenue. Don't optimize for it.

**API thinness is a feature, not a bug, for the cross-post use case.** You
need exactly one verb (upload) and one noun (channel feed). Anything more is
out of scope and probably means you're treating Rumble as primary, which
contradicts the strategy.

**OpenRSS is the read API.** Until Rumble ships a public read endpoint —
which it has not in 5+ years — assume the read surface is RSS-shaped and
build accordingly. The watcher pattern (poll feed → diff against last seen
GUIDs → emit events) is the right shape.

## Gotchas

- **No public API for reads.** There is no "GET /videos/{id}" endpoint. Don't
  search for one. Use OpenRSS or scrape the HTML page.
- **Simple Upload API access is gated by email.** You email `bd@rumble.com`,
  wait for a human, and get a token if approved. There is no instant signup.
  Plan for "we don't have a token yet" as the default state and have a
  Playwright fallback that drives the GUI upload form.
- **`access_token` is a static 40-char string** — treat it as a password, not
  a JWT. No rotation API. If it leaks, you have to email Rumble to revoke.
- **`license_type` is required and the integer mapping is mostly undocumented.**
  Known values: `0` = "not for sale" / Personal Use, `6` = "Rumble Only".
  Other values exist (Exclusive Video Management, Video Management Excluding
  YouTube) but Rumble has not published the integer table. If you set the
  wrong one you cannot easily change it post-upload — the license is locked
  to the video.
- **Audience mismatch from YouTube.** Rumble's userbase is ~56% US,
  ~76% Republican-leaning per Pew. Personal brand content that performs well
  with a centrist or apolitical YouTube audience may underperform or get
  miscategorized on Rumble. Don't tune content for Rumble — let it be the
  mirror.
- **No webhooks, no event stream.** "Notify me when my video finishes
  encoding" does not exist. Poll the feed or scrape the video page.
- **MRSS feeds are PRO-only.** Free accounts have no native feed. The
  workaround is OpenRSS, which is third-party and can break.
- **Resolution is duration-gated.** 4K only for videos under 21 minutes, HD
  under 46 minutes, 720p under 61 minutes (with experimental 720p up to
  240 min). A 90-minute long-form interview will be capped below 720p
  unless that limit has been raised.
- **File size cap.** 15 GB free, 30 GB Premium, 60 GB Premium for on-demand
  live streams. Long 4K source masters need to be re-encoded down before
  upload.
- **Monetization eligibility is tied to Rumble Studio streaming hours**, not
  upload count. As of late 2025 the threshold dropped from 30 hours to 1 hour,
  but that has nothing to do with the upload API and isn't programmable.
- **Rumble Cloud is not the video platform.** `docs.rumble.cloud` is the IaaS
  product. If a search result mentions tokens, regions, or OpenStack, it's
  the wrong product. Use `help.rumble.com` and `player.rumble.com/developers/`
  for video API docs.
- **Third-party scrapers (Apify, rss-app, rumble-rss.xyz)** all break
  periodically when Rumble's HTML changes. Don't put them on the critical
  path of anything that has to fire on time. Treat them as best-effort.
- **Playwright against `rumble.com/login.php`** works but the login flow
  occasionally serves a Cloudflare challenge from VPS IPs. Same pattern as
  the Instagram monitor — run from a residential proxy if it starts failing.

See references/best_practices.md for the full 19-section creator-level knowledge base.
