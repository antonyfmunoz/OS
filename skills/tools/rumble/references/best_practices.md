# Rumble — Creator-Level Best Practices
Source: help.rumble.com/Rumble-Upload-API.html, help.rumble.com/Rumble-Platform-API.html, help.rumble.com/MRSS-&-OTT-Feeds.html, player.rumble.com/developers/, rumble.support/help/, rumble.com/help, en.wikipedia.org/wiki/Rumble_(company)
API Version: Simple Upload API (rumble.com/api/simple-upload.php) — gated, no version string published
SDK Version: HTTP multipart only (no first-party SDK in any language)
Last Researched: 2026-04-06

This document is intentionally honest about what does not exist on Rumble.
Where the analogous YouTube Data API v3 surface is missing, the section
explains the missing piece and points at the practical alternative
(OpenRSS, Playwright, scraping the public HTML page, or "do it manually
in the dashboard"). Do not assume YouTube parity — Rumble is a much
thinner developer surface and that thinness drives every pattern below.

---

# Tier 1 — Technical Mastery

## Authentication

Rumble has three independent auth surfaces, none of them OAuth.

**1. Simple Upload API token.** A single static `access_token` parameter
issued manually by Rumble's BD team. The token is a 40-character hex string
(e.g. `0123456789abcdef0123456789abcdef01234567`). To obtain one you email
`bd@rumble.com` from the address tied to your Rumble account, describe your
use case (typically: "I want to programmatically upload videos from my own
channel"), and wait for human review. There is no developer console, no
self-service signup, no sandbox / production split, and no rotation endpoint.

The token is bound to a user account, not a single channel. An account that
owns multiple channels can target any of them by passing `channel_id`.
Quoting the official docs, the token is to be "kept secret and treated
like a password." If the token leaks, the only revocation path is to email
Rumble again and ask for a new one — there is no "rotate" button.

EOS storage convention:
```
RUMBLE_ACCESS_TOKEN=0123456789abcdef0123456789abcdef01234567
RUMBLE_DEFAULT_CHANNEL_ID=12345
```
in `eos_ai/.env`, gitignored, never echoed in logs, never passed in a query
string (multipart body only).

**2. MRSS / OTT feed URLs.** No token. PRO-tier accounts generate per-channel
or whole-account feeds in the Rumble dashboard; the resulting URLs contain
an unguessable hash that acts as a bearer credential. Anyone with the URL
can read the feed. Treat the URL itself as a secret and store it the same
way you would a token.

**3. Web session (Playwright fallback).** Plain username + password against
`https://rumble.com/login.php`. Rumble issues a session cookie that is good
for several days; persist the cookie jar in `~/.rumble-session.json` between
runs to avoid hitting the login page on every upload. Two-factor auth, when
enabled, blocks fully-headless flows because Rumble does not support
app-password style provisioning. The pragmatic answer is a dedicated
"poster" account with 2FA off, separated from any account holding payout
information.

**Not auth, but adjacent:** Rumble Cloud (`docs.rumble.cloud`) uses an
OpenStack-style API token system. It is a different product and irrelevant
to video upload. Do not import Rumble Cloud client libraries when building
video automations.

## Core Operations with Exact Signatures

Rumble exposes exactly **one** documented HTTP endpoint for creators:

```
POST https://rumble.com/api/simple-upload.php
Content-Type: multipart/form-data
```

There is no `GET /videos`, no `GET /videos/{id}`, no `GET /channels/{id}`,
no `DELETE /videos/{id}`, no `PATCH` for editing metadata, no
`/comments`, no `/analytics`, no `/search`. If you need any of these, your
options are: (a) the public HTML page + an HTML parser, (b) the channel's
RSS/MRSS feed if you have one, or (c) a Playwright session driving the
dashboard.

### POST /api/simple-upload.php — fields

| Field | Type | Required | Notes |
|---|---|---|---|
| `access_token` | string | yes | 40 hex chars, issued by Rumble BD |
| `title` | string | yes | Plain text, ≤100 chars recommended |
| `description` | string | yes | Plain text, no HTML, line breaks allowed |
| `license_type` | int | yes | See license table below |
| `channel_id` | int | optional | Numeric channel ID; omit to upload to the account's default channel |
| `video` | file | yes | Multipart file part. MP4 / H.264 / AAC strongly recommended |
| `thumb` | file | optional | JPEG, 1280x720 ideal. If omitted, Rumble auto-generates |
| `cc_<lang>` | file | optional | One per language, e.g. `cc_en=@cc.srt`, `cc_fr=@fr.vtt`. SRT or VTT |

### `license_type` integer values

The full mapping is not published in the official docs. Known values
extracted from community uploads and the dashboard's licensing comparison
page:

| Value | Meaning | Cross-post implication |
|---|---|---|
| `0` | Personal Use / "not for sale" | Most permissive. Use this for cross-posts from YouTube. You retain all rights. |
| `6` | Rumble Only | Exclusive to Rumble. Required for some monetization bonuses. Do NOT use for cross-posts of content also on YouTube. |
| (other) | Exclusive Video Management, Video Management Excluding YouTube | Integer values not officially documented; set via dashboard, not API |

**The license is locked to the video on upload.** You cannot cleanly change
`license_type` after the fact via API; you have to delete and re-upload.
Default to `0` unless Antony has explicitly opted into a Rumble exclusive.

### Canonical curl

```bash
curl -X POST "https://rumble.com/api/simple-upload.php" \
  -F "access_token=${RUMBLE_ACCESS_TOKEN}" \
  -F "title=The Vigilante Architect — Episode 12" \
  -F "description=Long-form description, plain text." \
  -F "license_type=0" \
  -F "channel_id=${RUMBLE_CHANNEL_ID}" \
  -F "video=@/opt/OS/exports/ep12.mp4" \
  -F "thumb=@/opt/OS/exports/ep12_thumb.jpg" \
  -F "cc_en=@/opt/OS/exports/ep12.srt"
```

### Response shape

The endpoint returns JSON. On success:

```json
{
  "success": 1,
  "video": {
    "id": 12345678,
    "url": "https://rumble.com/v4abcd-title-slug.html",
    "embed_html": "<script src=\"https://rumble.com/embedJS/...\"></script>",
    "embed_url": "https://rumble.com/embed/v4abcd/"
  }
}
```

On failure:

```json
{
  "success": 0,
  "error": "Invalid access_token"
}
```

EOS parsing pattern: always check `success == 1` before reading `video`.
Persist `video.id` and `video.url` to the `content` table; persist the raw
JSON response to `content.platform_metadata` for forensics.

### Everything else

**There is no pagination of any kind**, because there is no list endpoint.
**There are no PATCH/PUT/DELETE verbs.** **There is no batch upload.** If
you need to upload N videos, you make N independent POSTs.

## Pagination Patterns

N/A — Rumble has no list/search endpoints, so there is no pagination to
discuss. Iteration over your own catalog is done by:

1. **Walking the channel page HTML** (`https://rumble.com/c/{slug}`),
   which paginates with `?page=N` and shows ~20 videos per page. Scrape
   with BeautifulSoup or Playwright. Stop when a page returns no new items.
2. **Reading the channel's RSS/MRSS feed** if PRO, or via OpenRSS otherwise.
   Feeds typically expose only the most recent ~20-50 items, so they are
   useless for full backfill — only for "what's new since last poll."
3. **Maintaining your own catalog table in Neon** keyed by `rumble_video_id`
   so you never need to re-walk the channel from scratch.

The third option is the only correct one for EOS. Treat the channel-page
walk as a one-time backfill, then never touch it again.

## Rate Limits

Rumble does not publish rate limits for the Simple Upload API. Empirical
behavior reported by community users:

- Sequential uploads of 1–5 videos in a session work without throttling.
- Bursts of >10 uploads in a few minutes can return generic 5xx errors that
  resolve on retry after a few minutes.
- The token is per-account, not per-IP, so distributing uploads across
  hosts does not help.
- Very large uploads (>5 GB) sometimes fail with connection resets;
  retry the whole POST.

Practical EOS guardrails:
- Max 1 concurrent upload per token. Serialize.
- Sleep 30 seconds between uploads inside a batch.
- Treat any 5xx as retryable up to 3 times with exponential backoff
  (60s, 120s, 240s).
- Treat any 4xx as non-retryable except `408` and `429` (which Rumble
  may or may not send — assume `429` is retryable).

For the public HTML / OpenRSS read paths there is no published limit but
the polite ceiling is roughly:
- OpenRSS: 1 request per channel per 5 minutes. They are doing you a favor.
- `rumble.com/c/{slug}` HTML: 1 request per channel per minute, max.
  Faster will get you Cloudflare-challenged from VPS IPs.

## Error Codes and Recovery

The Simple Upload API returns plain HTTP status codes plus a JSON body
with `success: 0` and an `error` string when something is wrong. Common
errors observed in the wild:

| HTTP | JSON `error` | Retryable? | Fix |
|---|---|---|---|
| 200 | `Invalid access_token` | no | Get a new token from BD |
| 200 | `Missing field: title` | no | Code bug, supply the field |
| 200 | `Channel not found` | no | Wrong `channel_id`, check dashboard |
| 200 | `License type required` | no | Pass `license_type=0` |
| 400 | (HTML) | no | Malformed multipart; check `Content-Type` |
| 413 | (HTML) | no | File too large; re-encode below 15/30 GB |
| 5xx | (HTML) | yes | Backoff + retry |
| Connection reset | — | yes | Backoff + retry the whole POST |

Retry policy:
```python
for attempt in range(3):
    try:
        r = requests.post(URL, files=files, data=fields, timeout=(10, 1800))
        body = r.json()
        if body.get("success") == 1:
            return body
        if body.get("error") in NON_RETRYABLE:
            raise PermanentUploadError(body["error"])
    except (requests.ConnectionError, requests.Timeout, ValueError):
        pass
    time.sleep(60 * (2 ** attempt))
raise UploadFailedAfterRetries()
```

Always log the full response body (with `access_token` redacted) on every
failure — Rumble's error messages are inconsistent and the only way to
build an error catalog is to capture every failure mode you encounter.

## SDK Idioms

N/A — there is no first-party SDK in any language. Anything calling itself
a "Rumble SDK" is a community project and almost certainly a thin wrapper
around `requests` or `axios`. The right idiom for EOS is plain
`requests.post` in Python:

```python
def upload_to_rumble(
    *,
    video_path: str,
    title: str,
    description: str,
    channel_id: int | None = None,
    license_type: int = 0,
    thumb_path: str | None = None,
    captions: dict[str, str] | None = None,
) -> dict:
    """Upload a video to Rumble via the Simple Upload API.

    Returns the parsed JSON response on success.
    Raises PermanentUploadError or UploadFailedAfterRetries on failure.
    """
    token = os.environ["RUMBLE_ACCESS_TOKEN"]
    files = {"video": open(video_path, "rb")}
    if thumb_path:
        files["thumb"] = open(thumb_path, "rb")
    for lang, srt_path in (captions or {}).items():
        files[f"cc_{lang}"] = open(srt_path, "rb")
    data = {
        "access_token": token,
        "title": title,
        "description": description,
        "license_type": str(license_type),
    }
    if channel_id is not None:
        data["channel_id"] = str(channel_id)
    return _post_with_retries(
        "https://rumble.com/api/simple-upload.php",
        data=data, files=files,
    )
```

This belongs in `eos_ai/connectors/rumble.py` (when Antony's token is
provisioned) alongside `youtube.py`. Same shape as every other thin
connector in EOS — no abstraction, no class hierarchy, just a function.

## Anti-Patterns

The patterns to avoid, written as "never" rules so they're unambiguous:

- **Never put `access_token` in a query string.** Some community wrappers
  pass it as `?access_token=...` which leaks it into proxy/CDN logs.
  Body multipart only.
- **Never run two simultaneous uploads against the same token.** Rumble
  has no transactional guarantees and ordering becomes unrecoverable.
- **Never retry a `4xx Invalid access_token` error** — it will never
  succeed. Fail loudly.
- **Never trust workflow defaults for `license_type`.** Validate the
  exact integer at the call site before every POST. The license is
  locked permanently after upload.
- **Never store Rumble video IDs without a `rumble_` prefix** in tables
  shared with other platforms. They collide with YouTube IDs.
- **Never block the YouTube publish workflow on a Rumble result.** Async
  queue, fail open, three retries max.
- **Never scrape the channel page faster than once per minute** from a
  VPS IP — Cloudflare will challenge.
- **Never use `embed_url` as the canonical link.** Use `video.url` (the
  `.html` permalink) for sharing, descriptions, and footers.
- **Never assume HTML scraper selectors are stable.** Wrap them in
  feature flags so a broken scraper can be disabled without taking
  down the pipeline.
- **Never fetch from third-party RSS proxies on the critical path of
  anything timing-sensitive.** OpenRSS is best-effort.

## Data Model

Rumble's creator-side object model, in order of containment:

- **Account** — top-level user. Owns access tokens, payout info, and 1+ channels.
- **Channel** — `https://rumble.com/c/{slug}`. An account can own multiple
  channels (e.g. a personal channel and a brand channel under the same login).
  `channel_id` in the API is the numeric ID, NOT the slug. You find it in the
  dashboard URL when editing channel settings.
- **Video** — owned by a channel. Has `id` (numeric, opaque, e.g. `12345678`),
  `url` (public permalink with slug), `embed_url`. Lifecycle: `uploaded` →
  `encoding` → `published` (or `under_review`, then `published`). The API
  does not surface state transitions; you only know it is live when the
  feed/page shows it.
- **License** — locked at upload time. See `license_type` table above.
- **Caption tracks** — one per language, attached at upload via `cc_<lang>`.
  Cannot be added or replaced post-upload via API.
- **Comments, likes, Rumbles (votes)** — exist on the public page, not
  exposed via API at all.
- **Categories and tags** — set via the dashboard; the Simple Upload API
  does not accept them as fields. This is a real gap: API-uploaded videos
  are uncategorized until you log in and tag them. Plan for that.

Encoding latency: small (sub-1 GB) videos publish within minutes; long 4K
masters can take 30+ minutes. There is no `status` endpoint. Polling the
public URL for HTTP 200 + a `<video>` tag is the practical signal.

## Webhooks and Events

N/A — Rumble has no public webhook surface as of 2026-04-06. There is no
"notify me when my video is published," no "notify me on new comment," no
"notify me on milestone view count." For new-upload monitoring use the
channel feed (RSS/MRSS) on a poll interval of 5–15 minutes. For comment
or engagement events, scrape the public video page on a much slower
cadence (hourly, daily) and diff against the previous snapshot in Neon.

The poll-and-diff pattern, in pseudocode shape:

```python
last_seen = neon.fetch_one(
    "SELECT last_video_guid FROM rumble_channel_state WHERE channel_id = %s",
    (cid,),
)
feed = feedparser.parse(f"https://openrss.org/rumble.com/c/{slug}")
new_items = []
for entry in feed.entries:
    if entry.guid == last_seen:
        break
    new_items.append(entry)
if new_items:
    emit_events(new_items)
    neon.execute(
        "UPDATE rumble_channel_state SET last_video_guid = %s WHERE channel_id = %s",
        (new_items[0].guid, cid),
    )
```

This is the canonical "Rumble as event source" pattern. It is intentionally
boring because the platform gives you nothing fancier.

## Limits

Hard and soft limits, as of 2026-04:

| Limit | Free | Premium / PRO |
|---|---|---|
| Max upload file size | 15 GB | 30 GB |
| Max on-demand stream file | 15 GB | 60 GB |
| Max video length | ~4 hours | ~4 hours |
| 4K playback eligibility | duration < 21 min | duration < 21 min |
| HD (1080p) eligibility | duration < 46 min | duration < 46 min |
| 720p eligibility | duration < 61 min (testing 240 min) | same |
| Concurrent live streams | 1 | 3 |
| MRSS/OTT feed access | no | yes |
| API token access | no relationship to tier — gated by BD email | same |
| Title length | ~100 chars recommended | same |
| Captions per video | one per language code | same |

Format limits:
- Container: MP4 strongly preferred. MOV / AVI / MKV may work but are
  not officially documented and have failure-rate stories.
- Video codec: H.264. H.265 is accepted in theory but inconsistent in practice.
- Audio codec: AAC or MP3.
- Resolution: up to 4K (3840×2160).
- Frame rate: 30 fps recommended; 60 fps accepted.
- Bitrate: 5–8 Mbps for 1080p, 3–5 Mbps for 720p.
- Aspect ratio: 16:9 standard.
- Thumbnail: 1280×720 JPEG, ideally <2 MB.
- Captions: SRT or VTT.

There is no published API call quota. See § Rate Limits for empirical
guidance.

## Cost Model

Rumble is free to upload and free to consume. Costs to be aware of:

- **Rumble Premium (viewer subscription):** $9.99/mo, ad-free viewing,
  supports creators. Not relevant to creator-side automation.
- **Rumble PRO (creator tier):** ~$25/mo as of 2026-04, unlocks MRSS/OTT
  feeds, higher upload limits (30 GB), 3 concurrent live streams,
  Rumble Premium streaming.
- **Creator monetization:** 60/40 ad rev split (60% to creator), with a
  Creator Partnership Program for top creators going up to 90/10. $50
  payout minimum. Revenue: $2-10 per 1000 views (vs YouTube $1-5),
  but on much lower view volume.
- **Rumble Studio streaming hour requirement** for some monetization
  tiers: was 30 hours, dropped to 1 hour as of December 2025.
- **Rumble Cloud (separate IaaS product):** has its own pricing page,
  irrelevant to video.

EOS cost framing: zero direct cost on the free tier for cross-posting.
The PRO tier ($25/mo) is justified only if (a) the MRSS feed is needed
for syndication or OTT, or (b) Antony hits the 15 GB file size limit
regularly. Until then, free tier + OpenRSS.

## Version Pinning

Rumble does not publish an API version. The `simple-upload.php` endpoint
has been stable in shape since at least 2020 — same fields, same response
shape — so the de facto version is "v1, immortal." You should still record
which version you tested against in your skill front matter
(`api_version`) and re-test on a quarterly cadence.

When (if) Rumble ever ships a v2 endpoint, treat it as a separate skill
revision; do not silently switch.

For Rumble's HTML surface (channel page, video page) there is no
versioning at all — they redesign whenever they want and your scrapers
will break. The mitigation is to keep scrapers thin and obvious so they
fail loudly, and to wrap them in feature flags so you can disable a
broken scraper without taking down the whole pipeline.

Quarterly re-test checklist:
1. POST a known-good test video through `simple-upload.php` from staging.
2. Diff the response shape against the parser.
3. Re-fetch the channel feed via OpenRSS and parse it.
4. Spot-check the video page HTML scraper selectors.
5. Update `last_researched` in skill frontmatter.
6. Fix any drift before the next production cross-post.

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

Rumble was founded in 2013 by Chris Pavlovski as a YouTube alternative,
spent the first half of its life as a low-profile viral-video clip site
("America's Funniest Home Videos for the web"), and pivoted hard in
2020-2021 toward a free-speech / censorship-resistant positioning,
courting creators who had been demonetized or removed from YouTube. By
2022 it was clearly the largest of the "alt-tech" video platforms, well
ahead of BitChute and Odysee in funding, revenue, traffic, and
mainstream-creator adoption. It went public via SPAC in 2022. As of 2026
it operates its own infrastructure (vs renting AWS / GCP) and has
launched Rumble Cloud as an IaaS spinoff.

The deliberate tradeoffs:

- **Creator-friendly economics over discovery sophistication.** Rumble
  pays a higher revenue share than YouTube (60/40 vs 55/45, with top
  creators going to 90/10), but invests far less in recommendation
  systems. The bet: creators will bring their own audience.
- **Permissive moderation over advertiser comfort.** Rumble accepts
  content that gets demonetized or removed from YouTube. The cost is
  brand-safety advertisers stay away, capping ad rates.
- **Owned infrastructure over rented.** Rumble runs its own data
  centers — slower to scale, but immune to cloud-provider deplatforming
  (a real risk for free-speech-positioned companies). Rumble Cloud
  monetizes the spare capacity.
- **Thin developer surface over rich ecosystem.** No public SDKs, no
  OAuth, gated upload API, no analytics API. Saves engineering effort
  and reduces attack surface; the cost is developers (like EOS) get
  almost nothing to work with.
- **Live streaming as the engagement engine.** Rumble Studio (live
  streaming product) is where the platform invests, not asynchronous
  video. Monetization tier eligibility is tied to streaming hours.

## Problem-Solution Map and Hidden Capabilities

| Problem | Rumble's answer | Hidden capability or workaround |
|---|---|---|
| YouTube might deplatform me | Cross-post to Rumble | OpenRSS gives you a feed even without PRO |
| I want to programmatically upload | Simple Upload API | Email `bd@rumble.com` to get a token |
| I need a feed of my channel | MRSS (PRO only) | OpenRSS proxy works on free accounts |
| I need analytics | Dashboard only | Scrape the public video page on a schedule |
| I need to schedule a publish | Not supported | Delay the upload itself in your queue |
| I need to add tags via API | Not supported | Playwright post-step against the dashboard |
| I need OTT distribution to Roku/Fire | PRO MRSS feed → "roku.json" | Rumble auto-generates the JSON; one-click |
| I need the highest possible payout | Creator Partnership Program (90/10) | Manual application, not API |
| I need 4K playback for long videos | Cap at 21 min | Split into multi-part series |
| I need to upload >15 GB on free tier | Not allowed | Upgrade to Premium ($25/mo) or re-encode |

Hidden capabilities most creators don't know about:
- The Simple Upload API supports closed captions for arbitrary languages
  via the `cc_<lang>` field naming convention. Most cross-posters don't
  ship captions and lose the SEO/accessibility win.
- Rumble auto-generates a thumbnail if you don't supply one, but the
  chosen frame is rarely good — always supply your own thumbnail.
- The `embed_html` field in the response is a script tag that includes
  the player; you can embed Rumble videos on a Substack/blog without
  the user ever leaving for rumble.com.
- Rumble PRO ($25/mo) is the cheapest path to OTT distribution
  (Roku, Amazon Fire) of any video platform. YouTube doesn't offer
  this at all without a custom CMS deal.
- Channel pages support `?page=N` for pagination, undocumented but
  stable.

## Operational Behavior and Edge Cases

Things that bite you in production:

- **Encoding can stall indefinitely.** A video can sit in
  `pending_encode` for hours with no error. There is no retry button
  for encoding; the only fix is to delete and re-upload.
- **Silent takedowns.** A video that violates Rumble's terms can be
  removed hours after publishing with no notification. The API call
  returned success; the public URL just starts returning 404. Build a
  watcher that confirms the video is still live a week after publish.
- **License change is destructive.** You cannot move a video from
  Personal Use to Rumble Only (or vice versa) without delete + re-upload.
- **`channel_id` confusion.** The dashboard shows channels by slug;
  the API needs the numeric ID. Dig it out of the edit URL.
- **HTML redesigns.** Rumble periodically updates the channel page and
  video page markup. Selector-based scrapers break. Plan to re-fix
  selectors quarterly.
- **Cloudflare challenges.** Login pages and high-traffic scraping
  endpoints occasionally challenge requests from VPS IPs. Same
  pattern as the Instagram monitor in EOS.
- **OpenRSS occasional outages.** It's a courtesy service, not an SLA.
  Cache the last good feed and fall back when it's down.
- **The free tier 15 GB limit catches you on long-form 4K.** A 90 min
  4K master at decent bitrate easily exceeds 15 GB. Re-encode to
  1080p/8 Mbps before upload.
- **Resolution duration gates feel arbitrary.** A 22-minute video gets
  HD instead of 4K because it's 60 seconds over the 21-min mark. Edit
  to 20:59 or accept HD.
- **Captions cannot be edited post-upload via API.** Get them right
  the first time.
- **Description rendering is plain text.** Markdown does not render.
  HTML tags are stripped or escaped depending on the version. Plain
  text + URLs only.

## Ecosystem Position and Composition

Rumble's position in the 2026 video platform ecosystem:

- **vs YouTube (Google).** YouTube is 50-100x larger by every metric
  (users, watch time, ad revenue, creator count). Rumble is the largest
  alternative but still 1-2 orders of magnitude smaller. They are not
  substitutes for most creators; they are insurance and overflow.
- **vs BitChute.** Rumble is "better-funded and more mainstream" per a
  Reuters analysis. BitChute is more fringe, less monetized, and runs
  a more hands-off moderation policy. Rumble has overtaken BitChute
  as the default alt-platform recommendation.
- **vs Odysee.** Odysee is blockchain-based (LBRY), tries to monetize
  via crypto, and has not achieved the creator pull that Rumble has.
  Useful as a tertiary mirror, not a primary alt-platform.
- **vs Locals.** Locals is owned by Rumble (acquired in 2021). Locals
  is the membership/community product, Rumble is the open video
  platform. Together they form a creator stack: open video on Rumble,
  paid community on Locals.
- **vs PeerTube.** PeerTube is federated open source (ActivityPub).
  Almost zero mainstream adoption. Interesting for ideologues, not
  for personal brand cross-posting.
- **vs Substack Video.** Substack is becoming an asynchronous video
  destination for the newsletter crowd. Different audience entirely,
  but the cross-post pipeline shape is similar.
- **vs X (Twitter) Video.** X has aggressively expanded video and is
  arguably a closer competitor to YouTube on news/politics than
  Rumble is. For Antony's personal brand, X is probably more important
  than Rumble for short-form clips.

Composition with EOS tools:
- **YouTube Data API v3** — upstream source of canonical artifacts.
- **Gemini / Claude** — description rewriting.
- **Playwright** — fallback upload path; tagging post-step.
- **feedparser** — RSS parsing.
- **BeautifulSoup / lxml** — HTML scraping.
- **Neon Postgres** — catalog source of truth.
- **Discord bot (`os-bot`)** — alerting and "now live" notifications.
- **Cron / systemd timers** — feed and encode-status watchers.
- **Apify residential proxy** — fallback when VPS IP gets challenged.

The composition story: Rumble is one node in a fan-out pattern from a
single canonical YouTube upload. Not a special case, just one more
destination plugged into the same content pipeline.

## Trajectory and Evolution

Where Rumble is heading as of 2026-04:

- **Live streaming is the strategic priority.** Rumble Studio gets
  feature investment; the asynchronous upload product is in maintenance
  mode. Expect more features for streamers, fewer for uploaders.
- **Creator Partnership Program is expanding.** Top creators getting
  90/10 splits is a recruitment tool aimed at YouTube refugees. The
  bar to qualify is opaque and probably gameable through relationships.
- **Rumble Cloud is the long game.** The IaaS spinoff is monetizing
  spare infrastructure capacity and giving Rumble revenue diversification
  beyond ad-supported video. If it succeeds it eventually subsidizes
  the video platform; if it fails it doesn't affect the video product.
- **Locals integration is deepening.** Expect tighter Rumble↔Locals
  flows: pay for a Locals membership, get ad-free Rumble; stream live
  on Rumble, paywall the replay on Locals.
- **API surface is unlikely to expand significantly.** Rumble has
  shown no signal of building a developer ecosystem. The Simple
  Upload API has been stable for years; expect that to continue.
  Don't wait for a v2.
- **Moderation policies are stable.** Rumble's positioning is the
  product. They will not tighten moderation to court advertisers
  (they tried this circa 2024 and it hurt creator trust; reversed).
- **Mainstream adoption is plateauing.** Per Pew (2022-2024 data), ~20%
  of US adults have heard of Rumble, ~2% regularly get news there.
  Growth has slowed since the 2020-2022 spike; the "deplatforming
  refugee" wave is mostly absorbed.
- **The audience is durable but politically narrow.** ~76% Republican
  / Republican-leaning. This is unlikely to broaden meaningfully.
  Plan for it as a feature (audience clarity) not a bug.

Implications for EOS:
- Don't bet on a richer API. Build for the API that exists.
- Treat Rumble as stable, secondary, and small. Don't over-invest.
- The Locals integration is a more interesting future expansion than
  any new Rumble API. If Antony eventually monetizes a community,
  Locals is a candidate.

## Conceptual Model and Solution Recipes

Mental model: **Rumble is a destination, not an audience graph.** Treat
it the way you would treat a Substack mirror or an RSS pingback target.
Your already-converted audience can find you there; cold discovery is
unlikely.

Recipe 1 — One-time channel backfill:
1. Use Playwright to walk `https://rumble.com/c/{slug}?page=1..N`.
2. Parse each video tile for `id`, `url`, `title`, `published_at`.
3. Insert into `content_destinations` with `rumble_status = live`.
4. Stop when a page has zero new items.
5. Done. Never run this again.

Recipe 2 — Cross-post one YouTube video:
1. Trigger on YouTube publish.
2. Pull source MP4 from export bucket.
3. Rewrite description via Gemini.
4. POST to `simple-upload.php` (or queue Playwright job if no token).
5. Parse response, write to `content_destinations`.
6. Watcher promotes `pending_encode` → `live`.

Recipe 3 — Monitor a channel for new uploads:
1. Cron job every 6 hours.
2. GET `https://openrss.org/rumble.com/c/{slug}`.
3. Diff against `rumble_channel_state.last_video_guid`.
4. Insert new entries into `content_destinations`.
5. Update `last_video_guid` to the newest GUID.

Recipe 4 — Track view counts over time:
1. Weekly cron job.
2. For each `live` row in `content_destinations`, GET the public URL.
3. Parse the view count out of the HTML.
4. Append snapshot to `rumble_view_history`.
5. Never overwrite, always append (so you have a time series).

Recipe 5 — Audience-link injection:
1. Pre-publish hook on YouTube upload workflow.
2. Look up the most recent `live` Rumble video for the same channel.
3. Append "Also on Rumble: <url>" to the YouTube description.
4. Publish.

## Industry Expert and Cutting-Edge Usage

What sophisticated Rumble creators are actually doing in 2026:

- **Live-first, upload-second.** Top creators stream live on Rumble
  Studio for 4-8 hours, then upload the recording as VOD plus extract
  3-5 short clips. Streaming hours qualify them for monetization tiers
  the upload-only path doesn't reach.
- **Locals + Rumble bundles.** Free content on Rumble, paid community
  on Locals, with cross-promotion between them. The Rumble video drives
  Locals signups; Locals members get early/exclusive Rumble content.
- **Multi-channel accounts.** Power creators run a main channel plus
  topical sub-channels (politics, tech, lifestyle) under one account,
  using `channel_id` to route uploads. Helps with audience segmentation.
- **MRSS-to-OTT distribution.** A few creators use Rumble PRO purely
  for the Roku/Fire feed generation, treating Rumble as a content
  management backend for OTT apps they control.
- **Original-on-Rumble exclusives.** Creators in the Partnership
  Program post some content as `license_type=6` (Rumble Only) for the
  90/10 share. This is the only case where Rumble-first publishing
  makes economic sense.
- **Manual cross-posting at scale.** Most creators (Steven Crowder,
  Russell Brand, Joe Rogan clip channels) cross-post manually because
  the API is gated and they only need it once per video. Antony's
  scale is similar — automation matters more for the consistency than
  the throughput.
- **Cross-platform clip distribution.** Top creators clip Rumble live
  streams into vertical short-form for X / TikTok / Instagram Reels /
  YouTube Shorts, fanning out clips to maximize discovery on each
  platform's native short-form surface.

For Antony specifically, the cutting-edge pattern that maps best is:
**publish on YouTube primary, automated cross-post to Rumble as
insurance, manual short-form clips to X for personal brand
amplification.** Rumble does not need to be sophisticated. It needs
to be reliable.

---

## EOS Usage Patterns

This section is the EOS-specific operational layer. Antony's situation:
solo founder, pre-revenue, building a personal brand as the marketing
vehicle for everything, primarily on YouTube. Rumble is secondary —
audience diversification + censorship hedge — and Antony posts manually
today. The goal is to make cross-posting cheap enough (in time) that
he never skips it, without making Rumble feel like a primary platform.

### Pattern: YouTube → Rumble cross-post pipeline

The canonical pipeline:

1. **Trigger.** YouTube publishes a new video on Antony's channel.
   Either a webhook from the YouTube Data API v3 PubSubHubbub feed,
   or a polling watcher on the channel uploads playlist (every 5
   minutes, cheap).
2. **Source pull.** The `content` table already has the YouTube row
   with `youtube_id`, `title`, `description`, `published_at`, and
   the source MP4 path (from the export bucket).
3. **Description rewrite.** Call `model_router.call_with_fallback`
   with the YouTube description and a prompt that strips
   YouTube-specific CTAs, neutralizes YouTube-only references ("see
   comments below" → inline link), and adds a single "originally on
   YouTube: <url>" line. Cache the rewritten description in
   `content_destinations.rumble_description`.
4. **Upload.** If `RUMBLE_ACCESS_TOKEN` is set, call
   `upload_to_rumble(...)` from `eos_ai/connectors/rumble.py`.
   Otherwise queue a Playwright job that drives the GUI upload form.
   `license_type=0` (Personal Use), `channel_id` from
   `RUMBLE_DEFAULT_CHANNEL_ID`, thumbnail from the YouTube thumbnail.
5. **Persist.** Write `rumble_video_id`, `rumble_url`, `rumble_status
   = pending_encode`, `rumble_uploaded_at = now()` to
   `content_destinations`.
6. **Watcher promotes pending → live.** A separate cron job polls
   each `pending_encode` row's `rumble_url` every 10 minutes for the
   first hour, then every hour. When the URL returns 200 with a
   `<video>` tag, flip to `live`, set `rumble_went_live_at`, and
   emit a Discord notification.
7. **Audience-link injection.** Once `live`, the next morning brief /
   email footer / link-in-bio update includes the Rumble URL.

This pipeline runs entirely in the background. Antony does nothing
except publish the YouTube video. If anything fails three times, it
logs to Discord and waits for manual retry from the dashboard.

### Pattern: Manual upload SOP (no API token yet)

Until Rumble issues an `access_token`, the workflow is manual. EOS
supports it by generating the artifacts Antony needs and dropping
them in a known location:

1. EOS detects new YouTube upload.
2. EOS generates the Rumble-tuned title, description, and tag list.
3. EOS exports the source MP4 (already exists from the YouTube
   workflow) and a 1280×720 thumbnail JPEG to
   `/opt/OS/exports/rumble/<youtube_id>/`.
4. EOS posts a Discord message to Antony with: file paths, generated
   title/description ready to copy-paste, license recommendation
   (Personal Use), suggested tags.
5. Antony opens the Rumble dashboard, drags the MP4, pastes metadata,
   publishes.
6. Antony pastes the resulting Rumble URL into a Discord reply.
7. EOS parses the URL, extracts the video ID, writes back to
   `content_destinations` exactly as if the API path had succeeded.

This is "EOS as upload assistant" — same end state, human in the loop
for the actual button press. The 80% time savings comes from not
manually rewriting the description, not from automating the click.

### Pattern: Channel feed monitoring

A daily cron job (cheap, low-cadence) reads Antony's channel feed via
OpenRSS:

```
GET https://openrss.org/rumble.com/c/{antony_slug}
```

Diffs against the last seen GUID in
`rumble_channel_state.last_video_guid`. New entries are inserted into
`content_destinations` if they don't already exist (catching the case
where Antony uploaded directly without going through EOS). This keeps
EOS's view of the catalog in sync with reality even when humans bypass
the pipeline.

Cadence: every 6 hours is plenty. Failure mode: OpenRSS down → log,
skip, try again next run. Never block on this.

### Pattern: Description rewriting prompt

The actual prompt template, kept short and deterministic:

```
Rewrite the following YouTube video description for cross-posting to Rumble.

Rules:
- Preserve the core message and any specific facts or links.
- Remove "subscribe", "like and subscribe", "hit the bell" and similar
  YouTube-specific CTAs.
- Replace "see pinned comment" or "see comments below" with the actual
  link inlined into the description.
- Remove YouTube channel membership / Super Thanks / Super Chat language.
- Keep the tone as the original (do not soften or harden).
- Keep length within 20% of the original.
- End with a single line: "Originally posted on YouTube: <YOUTUBE_URL>".

Source description:
<<<
{youtube_description}
>>>
```

Run this through Gemini Flash (cheap, fast, deterministic enough).
Cache the output by `youtube_id` so re-runs don't re-spend tokens.

### Pattern: Failure handling and Antony notification

Rumble cross-posts are secondary. The escalation rules:

- **First failure:** silent retry after 60 seconds.
- **Second failure:** silent retry after 5 minutes.
- **Third failure:** post a single Discord message to `#eos-alerts`:
  "Rumble cross-post failed for `<youtube_id>`, last error:
  `<error string>`. Manual upload SOP in
  `/opt/OS/exports/rumble/<youtube_id>/`."
- **No retries beyond three.** Move on. The morning brief shows the
  cross-post as `error`, not `live`, and Antony decides whether to
  manually retry or skip.

This explicitly accepts that some Rumble uploads will be skipped. That
is the right trade for a secondary platform.

### Pattern: Performance pulling (scraped views)

Once a week, walk every `live` Rumble video in `content_destinations`
and scrape the public video page for the view count and Rumble-Rank
position (if shown). Store as a snapshot in `rumble_view_history` keyed
by `(rumble_video_id, snapshot_at)`. Never overwrite — always append.

This gives Antony a time series of how each video is doing on Rumble vs
YouTube, which is the only signal that matters for "should we keep
investing in cross-posts." The expected answer is "yes, because the
marginal cost is zero," but having the data lets you confirm.

### Pattern: Audience-link injection into the next YouTube description

After a Rumble cross-post goes `live`, the next YouTube video Antony
publishes gets an extra line auto-injected near the bottom of its
description: "Also on Rumble: <link to the previous Rumble video>."
This is the cross-pollination mechanism — the YouTube audience becomes
aware that a Rumble mirror exists, and a sliver migrates over time.

Implement as a `pre_publish_hook` on the YouTube upload workflow.
Parameter: which previous Rumble video to link (most recent live one).

### Pattern: Quarterly re-test of the API contract

Every quarter, a manual checklist:

1. Re-run a known-good upload against `simple-upload.php` from staging.
2. Confirm response shape matches the parser (especially `video.id`,
   `video.url`, `video.embed_url`).
3. Re-fetch the channel feed via OpenRSS and confirm it parses.
4. Spot-check the video page HTML for the view-count selector working.
5. Update `last_researched` in the skill frontmatter.
6. If anything has broken, fix it before the next cross-post fires.

This is the operationalization of "Rumble can change anything at any
time and won't tell you." The quarterly checklist catches drift before
Antony does.

---

## Gotchas

The full failure catalog. Add to this list whenever a real failure
hits production.

- **`access_token` issuance is gated by a human at Rumble BD.** There
  is no signup form. Default state for any new EOS instance is "no
  token, use the Playwright fallback or manual SOP."
- **`license_type` is mandatory and the integer table is mostly
  undocumented.** Known: `0` = Personal Use, `6` = Rumble Only. Default
  to `0` for cross-posts. Never let workflow logic change this without
  an explicit Antony decision.
- **License cannot be cleanly changed post-upload.** A wrong
  `license_type` means delete + re-upload. There is no PATCH.
- **Categories and tags are NOT accepted by the Simple Upload API.**
  API-uploaded videos publish uncategorized. Either accept that or add
  a Playwright post-step that logs in and tags them.
- **No video metadata edit endpoint.** Once published, you cannot PATCH
  the title or description via API. Dashboard or delete + re-upload.
- **No delete endpoint.** Same reason. Dashboard only.
- **No `status` endpoint.** "Is my video done encoding?" is answered
  by polling the public URL.
- **The response JSON uses `success: 1` (integer), not `success: true`
  (boolean).** Type-strict parsers will mishandle it. Check with
  `== 1`, not `is True`.
- **`channel_id` is numeric, not the slug.** `rumble.com/c/foo` does
  not give you the channel ID — find it in the dashboard URL when
  editing channel settings.
- **File size cap is 15 GB free / 30 GB Premium.** A 4K master at full
  bitrate easily exceeds 15 GB at 30 minutes. Re-encode before
  uploading on a free account.
- **Resolution is duration-gated.** 4K only for <21 min, HD only for
  <46 min, 720p for <61 min (or <240 min if the experiment shipped).
  A 90-minute long-form interview will be capped low.
- **No public read API.** Don't search for `GET /videos/{id}`. It does
  not exist.
- **No webhooks, no event stream.** Poll the channel feed.
- **No analytics API.** Scrape the page or live without the data.
- **No comment API.** Same.
- **MRSS feeds are PRO-only.** Free accounts get nothing native.
  Workaround is OpenRSS, which is third-party.
- **OpenRSS is a courtesy service.** No SLA. Cache aggressively, fail
  gracefully, don't put it on critical paths.
- **Cloudflare challenges from VPS IPs.** Same pattern as the Instagram
  monitor. Login pages and high-traffic scraping endpoints occasionally
  challenge. Mitigate with residential proxy or back off.
- **Rumble redesigns the HTML occasionally and breaks scrapers.** Wrap
  scrapers in feature flags so a broken scraper can be disabled without
  taking down the whole pipeline.
- **`rumble.com/api/simple-upload.php` is the URL — note the `.php`
  extension.** Some community examples drop the extension and 404.
- **The token is per-account, not per-channel.** A leaked token can
  upload to ALL channels owned by the account, not just one.
- **2FA on the Rumble account blocks Playwright.** Use a dedicated
  poster account with 2FA off and no payout info.
- **Rumble Cloud (`docs.rumble.cloud`) is a different product.** When
  searching for "Rumble API," half the results are about the IaaS
  product. Filter aggressively.
- **`rumble-rss.xyz` and similar third-party feed generators** come
  and go. Don't depend on any single one. Prefer OpenRSS.
- **Connection resets on large uploads.** >5 GB POSTs occasionally
  reset mid-stream. Always retry the whole POST; there is no resume
  protocol.
- **Encoding can stall.** A video can sit in `pending_encode` for hours
  with no error and no progress signal. Set a timeout (24 hours) after
  which the watcher gives up, marks the row `error`, and notifies
  Antony to investigate manually.
- **Apify's Rumble scraper exists**
  (`azzouzana/rumble-all-inclusive-scraper`) but is third-party and
  costs Apify credits. Use only if scraping needs grow beyond what
  `requests` + `BeautifulSoup` can do.
- **The `embed_url` returned by the API is for the player iframe**,
  not the canonical video page. Persist `video.url` (the `.html`
  permalink) as the public link, not `embed_url`.
- **Rumble's terms of service still apply** even though moderation is
  permissive. A terms violation gets the video taken down silently;
  the API upload returns success and the takedown happens hours
  later. There is no notification — you find out by polling the URL
  and getting a 404.
- **Payouts are not API-accessible.** Earnings, view counts for payout
  calculation, and tier eligibility live entirely in the dashboard.
  There is no programmatic access.
- **The "Rumble Studio" name is overloaded.** It refers to the live
  streaming product, NOT a creator dashboard analogous to YouTube
  Studio. Don't confuse the two.
- **`description` is plain text, not HTML.** Line breaks render but
  HTML tags do not. Strip HTML before passing.
- **There's no way to schedule a publish via API.** The video goes live
  as soon as encoding completes. If you need delayed publish, delay
  the upload itself with a queue.
- **Captions cannot be added or replaced after upload via API.** They
  must be supplied at upload time as `cc_<lang>` files.
- **The `success` integer is the only reliable signal of success.** Do
  not infer success from HTTP 200 alone — the endpoint returns 200
  even on most error cases with `success: 0` in the body.
- **License type `6` (Rumble Only) blocks cross-posts.** If the same
  video is also on YouTube, choosing `6` is a terms violation. Default
  `0` is the safe choice.
- **Closed caption file extensions matter.** SRT and VTT are accepted.
  Other formats (TTML, DFXP) are not.
- **Thumbnail JPEG size:** keep under 2 MB. Larger thumbnails sometimes
  silently fail to attach with no error in the response.
