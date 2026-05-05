---
name: youtube
description: "Use when uploading/managing YouTube videos via Data API v3, querying channel analytics, scheduling premieres, designing thumbnails/titles, planning long-form or Shorts content strategy, or analyzing CTR/AVD/retention for the channel."
allowed-tools: "Read, Bash, Write, Edit, WebFetch"
version: 1.0
source_url: "https://developers.google.com/youtube"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "Data API v3 / Analytics API v2 / Reporting API v1"
sdk_version: "google-api-python-client 2.122+"
speed_category: stable
trigger: both
effort: low
context: fork
---

# Tool: YouTube

## What This Tool Does

YouTube exposes three distinct creator-facing APIs that share a single OAuth
surface but solve different problems:

- **Data API v3** — read/write channel content: videos, playlists, captions,
  thumbnails, comments, channel metadata, search. The verb layer.
- **Analytics API v2** — interactive `reports.query` against the cube
  (dimensions x metrics x filters). Sub-second responses for dashboards.
- **Reporting API v1** — bulk CSV jobs delivered daily, ~60 days retention,
  zero quota cost. The data-warehouse layer.

Together they let an agent fully operate a channel: upload, schedule, tag,
caption, thumbnail, then measure CTR / AVD / retention curves and iterate.

This skill is the **creator/data** surface. For *downloading* videos or
extracting subtitles from arbitrary URLs, use `yt_dlp` instead — it does not
require OAuth and is the right tool for ingestion pipelines. The two skills
are complementary: `yt_dlp` for read-only ingest, `youtube` for owning content.

## EOS Integration

Antony's personal brand uses YouTube as the long-form distribution channel
(interviews, breakdowns, BTS) plus a Shorts shelf repurposed from TikTok. The
agent layer touches YouTube in four loops:

- **Publish loop** — Empyrean Studio drafts title/description/chapters/tags,
  the agent uploads via `videos.insert` (resumable), sets thumbnail via
  `thumbnails.set`, schedules `publishAt`, posts to Community tab.
- **Shorts repurpose loop** — TikTok winners (>50k views, hook strong) get
  re-rendered vertical with captions burned in, uploaded as Shorts (<=180s,
  9:16, `#Shorts` in title). See `tiktok` skill for the source side.
- **Analytics ritual** — weekly `reports.query` pull of CTR, AVD, % viewed,
  traffic source breakdown, top retention dips. Written to Neon `yt_metrics`
  table for the morning brief.
- **Iteration loop** — A/B thumbnail test results (native YouTube test, polled
  via API once stable) feed the packaging library for Initiate Arena content.

Cross-reference: `yt_dlp` for downloading reference clips, `tiktok` and
`instagram` for cross-platform analytics, `notion` for the publishing board.

## Authentication

Two modes. Pick by use case.

- **API key (public reads only)** — `videos.list`, `search.list`,
  `channels.list` for public data. No OAuth dance. Cannot read Analytics,
  cannot write anything.
- **OAuth 2.0 (everything else)** — required for uploads, edits, Analytics,
  private data. Standard Google OAuth flow with offline access to get a
  refresh token. Refresh tokens for unverified apps **expire after 7 days** —
  push the app to "In production" in Google Cloud Console (no formal review
  needed for personal-channel scopes) before relying on long-lived tokens.

Scopes for the EOS use case:

```
https://www.googleapis.com/auth/youtube.upload          # videos.insert
https://www.googleapis.com/auth/youtube                 # full content management
https://www.googleapis.com/auth/youtube.readonly        # listing
https://www.googleapis.com/auth/yt-analytics.readonly   # Analytics API
https://www.googleapis.com/auth/yt-analytics-monetary.readonly  # revenue
```

Store refresh token in `eos_ai/.env` as `YOUTUBE_REFRESH_TOKEN`. Build the
service object once per process; the SDK auto-refreshes access tokens.

## Quick Reference

### Build the client (Python)

```python
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import os

creds = Credentials(
    token=None,
    refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
    client_id=os.environ["GOOGLE_CLIENT_ID"],
    client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
    token_uri="https://oauth2.googleapis.com/token",
)
yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
ya = build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False)
```

### Upload a video (resumable)

```python
from googleapiclient.http import MediaFileUpload

body = {
  "snippet": {
    "title": "How I Built a $10K/mo Coaching Funnel",
    "description": "Chapters:\n00:00 Intro\n01:30 Offer\n...",
    "tags": ["coaching", "funnel", "Initiate Arena"],
    "categoryId": "27",  # Education
    "defaultLanguage": "en",
  },
  "status": {
    "privacyStatus": "private",     # required when using publishAt
    "publishAt": "2026-04-08T14:00:00Z",
    "selfDeclaredMadeForKids": False,
  },
}
media = MediaFileUpload("video.mp4", chunksize=8 * 1024 * 1024, resumable=True)
req = yt.videos().insert(part="snippet,status", body=body, media_body=media)

response = None
while response is None:
    status, response = req.next_chunk()
    if status: print(f"{int(status.progress() * 100)}%")
print("video_id:", response["id"])
```

### Set a thumbnail

```python
yt.thumbnails().set(videoId=video_id, media_body="thumb.jpg").execute()
```

### Analytics query (last 28 days CTR + AVD by video)

```python
resp = ya.reports().query(
    ids="channel==MINE",
    startDate="2026-03-09", endDate="2026-04-06",
    metrics="views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,impressions,cardClickRate",
    dimensions="video",
    sort="-estimatedMinutesWatched",
    maxResults=25,
).execute()
```

### Quota-cheap public search

```bash
curl "https://www.googleapis.com/youtube/v3/search?part=snippet&q=mrbeast&type=video&maxResults=10&key=$YT_API_KEY"
```

## Conceptual Model

**Three APIs, one OAuth, one mental model: verbs vs cube vs warehouse.**

- Data API v3 is the **verb layer** — every action is a REST verb on a
  resource (`videos.insert`, `playlists.update`). It costs quota *per call*,
  not per row, and writes are expensive (1600 units for `videos.insert`).
- Analytics API v2 is the **OLAP cube** — pick metrics x dimensions x filters,
  YouTube returns rows. Free of Data API quota; has its own per-minute caps.
- Reporting API v1 is the **warehouse** — register a job once, YouTube drops
  daily CSVs you download. Heaviest data, zero quota cost.

The algorithm itself is a **session-time maximizer**: it scores videos on
expected `(CTR x AVD x session contribution)`. Browse and Suggested are the
two big traffic engines; Search is third. Shorts is a separate feed with its
own ranker — vertical-only, sound-driven, loop-aware.

If you internalize "session time," every YouTube decision becomes obvious:
clickbait that under-delivers tanks AVD, the algorithm punishes. Long videos
with strong retention curves get boosted because you held the session.

## Gotchas

- **Quota explosion** — default project quota is 10,000 units/day. A single
  `videos.insert` is 1600. A `search.list` is 100. One enthusiastic search
  loop drains the day. Always batch via `id=...,...` (50 max) and request
  only the parts you need.
- **OAuth refresh token 7-day expiry** in "Testing" mode — your scheduled
  cron silently dies after a week. Push the OAuth consent screen to
  "In production" in Google Cloud Console.
- **Resumable upload session URL is single-use** — if `next_chunk()` raises
  hard, re-create the request from scratch with the same file; do not retry
  the raw URL with a new chunk.
- **`thumbnails.set` race condition** — if you call it within ~30s of
  `videos.insert`, YouTube can overwrite your custom thumbnail with the
  auto-generated one when processing finishes. Wait for `processingDetails`
  to show `processingStatus=succeeded`, then set the thumbnail.
- **Captions race condition** — `captions.insert` against a video still in
  `processingStatus=processing` returns 409. Poll first.
- **Shorts are inferred, not flagged** — there is no `isShort` field on
  `videos.insert`. YouTube classifies a video as a Short post-upload based on
  duration <=180s AND aspect ratio <=1:1. `#Shorts` in the title is a hint,
  not a switch.
- **Analytics API permissions trap** — `yt-analytics.readonly` does NOT cover
  revenue. You also need `yt-analytics-monetary.readonly`, and the channel
  must be in YPP, or revenue metrics return 403.
- **`publishAt` requires `privacyStatus=private`** at insert. Public +
  publishAt = 400. Insert as private with `publishAt`, YouTube flips it.
- **Data API v2 (`gdata.youtube.com`) is dead** since 2015. v3 only.
  Analytics is on v2 (different API, unrelated version number).
- **Daily quota reset is midnight Pacific Time**, not UTC.

See references/best_practices.md for the full 19-section creator-level
knowledge base (Tier 1 operational depth, Tier 2 packaging/algorithm
intuition, EOS-specific patterns).
