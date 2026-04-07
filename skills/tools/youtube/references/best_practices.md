# YouTube — Creator-Level Best Practices

Source: https://developers.google.com/youtube
API Version: Data API v3, Analytics API v2, Reporting API v1
SDK Version: google-api-python-client 2.122+, googleapis Node 144+
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## Authentication

YouTube uses Google's standard OAuth 2.0 + API key system. Three auth modes,
chosen by what the call needs to do:

**1. API Key (public reads only)**
- Created in Google Cloud Console under Credentials -> API Key
- Restrict by API ("YouTube Data API v3") and optionally by HTTP referrer / IP
- Pass as `?key=...` query param OR `X-goog-api-key` header
- Quota counts against the *project*, not the key
- Cannot read Analytics, cannot write anything, cannot read private data

**2. OAuth 2.0 (read/write owned channels)**
- Standard Google OAuth: client_id + client_secret + redirect_uri
- Request `access_type=offline` and `prompt=consent` on first auth to force
  a refresh_token (otherwise Google returns only an access_token after the
  first consent and you cannot get the refresh token without revoking)
- Access tokens last 1 hour; SDKs refresh transparently
- Refresh tokens are durable IF the OAuth consent screen is in "Production"
  publishing status. While in "Testing" mode, refresh tokens **expire after
  7 days** and your cron silently dies
- Personal-channel scopes do NOT require Google verification — push to
  "In production" without going through review

**3. Service Accounts**
- NOT supported for YouTube. Service accounts cannot own a channel and
  cannot impersonate a user even via domain-wide delegation. Use OAuth.

**Required scopes** (request the minimum that satisfies your calls):

| Scope | Grants |
| --- | --- |
| `youtube.readonly` | All read endpoints (Data API list/search) |
| `youtube` | Read + write content management (videos, playlists, etc.) |
| `youtube.upload` | `videos.insert` only |
| `youtube.force-ssl` | Equivalent to `youtube` for OAuth 2.0 calls |
| `yt-analytics.readonly` | Analytics API non-revenue metrics |
| `yt-analytics-monetary.readonly` | Analytics API revenue metrics (YPP only) |
| `youtubepartner` | Content owner / CMS calls (not for normal creators) |
| `youtubepartner-channel-audit` | Read-only audit data for MCN onboarding |

**Token endpoint**: `https://oauth2.googleapis.com/token`
**Auth endpoint**: `https://accounts.google.com/o/oauth2/v2/auth`
**Revoke**: `POST https://oauth2.googleapis.com/revoke?token=...`

**Refresh dance** (manual, when not using SDK):
```
POST https://oauth2.googleapis.com/token
grant_type=refresh_token
refresh_token=<token>
client_id=<id>
client_secret=<secret>
```
Returns `{access_token, expires_in, scope, token_type}`. No new refresh_token
unless you re-consent.

## Core Operations with Exact Signatures

All endpoints rooted at `https://www.googleapis.com/youtube/v3/` for Data API,
`https://youtubeanalytics.googleapis.com/v2/` for Analytics,
`https://youtubereporting.googleapis.com/v1/` for Reporting.

### videos

```
GET    /videos?part=snippet,statistics,contentDetails,status&id=ID1,ID2,...   [1 base + 1 per part]
GET    /videos?part=snippet&chart=mostPopular&regionCode=US&maxResults=50
POST   /videos?part=snippet,status&uploadType=resumable                       [1600 units]
PUT    /videos?part=snippet,status                                            [50 units]
DELETE /videos?id=ID                                                          [50 units]
POST   /videos/rate?id=ID&rating=like|dislike|none                            [50 units]
GET    /videos/getRating?id=ID                                                [1 unit]
POST   /videos/reportAbuse                                                    [50 units]
```

Python SDK:
```python
yt.videos().list(part="snippet,statistics,contentDetails", id=",".join(ids), maxResults=50).execute()
yt.videos().insert(part="snippet,status", body=body, media_body=MediaFileUpload(path, resumable=True))
yt.videos().update(part="snippet", body={"id": vid, "snippet": {...}}).execute()
yt.videos().delete(id=vid).execute()
```

`videos.insert` body shape:
```python
{
  "snippet": {
    "title": str,                  # max 100 chars
    "description": str,            # max 5000 chars
    "tags": [str, ...],            # total tag bytes <= 500
    "categoryId": str,             # see videoCategories.list
    "defaultLanguage": "en",
    "defaultAudioLanguage": "en",
  },
  "status": {
    "privacyStatus": "private|public|unlisted",
    "publishAt": "RFC3339",        # requires private
    "license": "youtube|creativeCommon",
    "embeddable": bool,
    "publicStatsViewable": bool,
    "selfDeclaredMadeForKids": bool,   # REQUIRED on every insert since 2020
  },
  "recordingDetails": {
    "recordingDate": "RFC3339",
  },
}
```

### channels

```
GET /channels?part=snippet,statistics,contentDetails,brandingSettings&mine=true
GET /channels?part=snippet&id=UC...
GET /channels?part=snippet&forHandle=@mrbeast
GET /channels?part=snippet&forUsername=legacy   [deprecated path]
PUT /channels?part=brandingSettings              [50 units]
```

The `contentDetails.relatedPlaylists.uploads` field is the magic playlist
ID for "all uploads in chronological order" — use this for `playlistItems.list`
to enumerate a channel's full upload history (instead of `search.list`,
which is 100 units per call).

### search

```
GET /search?part=snippet&q=query&type=video&maxResults=50&order=date|rating|relevance|title|videoCount|viewCount   [100 units per call]
```

Filters: `channelId`, `publishedAfter`, `publishedBefore`, `regionCode`,
`relevanceLanguage`, `videoDuration=any|long|medium|short`,
`videoDefinition=high|standard`, `eventType=completed|live|upcoming`.

**100 units is brutal** — avoid `search.list` for anything you can do via
`playlistItems.list` (1 unit) on the uploads playlist.

### playlists / playlistItems

```
GET    /playlists?part=snippet,contentDetails&mine=true&maxResults=50
POST   /playlists?part=snippet,status                                      [50 units]
PUT    /playlists?part=snippet                                             [50 units]
DELETE /playlists?id=PL...                                                 [50 units]
GET    /playlistItems?part=snippet,contentDetails&playlistId=PL...&maxResults=50
POST   /playlistItems?part=snippet                                         [50 units]
DELETE /playlistItems?id=...                                               [50 units]
```

### thumbnails / captions / commentThreads

```
POST /thumbnails/set?videoId=VID                          [50 units; multipart upload <= 2MB]
GET  /captions?part=snippet&videoId=VID                   [50 units]
POST /captions?part=snippet                               [400 units]
PUT  /captions?part=snippet                               [450 units]
GET  /captions/ID?tfmt=srt|vtt|sbv                        [200 units, downloads file]
GET  /commentThreads?part=snippet,replies&videoId=VID     [1 unit]
POST /commentThreads?part=snippet                         [50 units]
POST /comments?part=snippet                               [50 units]
POST /comments/setModerationStatus?id=...&moderationStatus=published|heldForReview|rejected   [50 units]
```

### Analytics API v2

Single big endpoint:
```
GET https://youtubeanalytics.googleapis.com/v2/reports?ids=channel==MINE
    &startDate=YYYY-MM-DD&endDate=YYYY-MM-DD
    &metrics=views,estimatedMinutesWatched,averageViewDuration,...
    &dimensions=day|video|country|insightTrafficSourceType|...
    &filters=video==VID;country==US
    &sort=-views
    &maxResults=200
    &startIndex=1
```

Common metrics: `views`, `estimatedMinutesWatched`, `averageViewDuration`,
`averageViewPercentage`, `subscribersGained`, `subscribersLost`, `likes`,
`dislikes`, `shares`, `comments`, `impressions`,
`impressionsClickThroughRate` (the canonical CTR), `cardClickRate`,
`endScreenElementClickRate`, `redViews`, `estimatedRedMinutesWatched`,
`estimatedRevenue`, `estimatedAdRevenue`, `cpm`, `playbackBasedCpm`,
`monetizedPlaybacks`, `adImpressions`.

Common dimensions: `day`, `month`, `video`, `country`, `deviceType`,
`operatingSystem`, `subscribedStatus`, `liveOrOnDemand`, `playbackLocationType`,
`insightTrafficSourceType` (`YT_SEARCH`, `RELATED_VIDEO`, `BROWSE`,
`YT_CHANNEL`, `EXT_URL`, `NO_LINK_OTHER`, `SUBSCRIBER`, `SHORTS`),
`insightPlaybackLocationType`, `ageGroup`, `gender`, `sharingService`.

Special "MINE" target: `ids=channel==MINE` for the OAuth user's channel,
`ids=contentOwner==OWNER_ID` for CMS calls.

### Reporting API v1

Bulk async CSV jobs.
```
GET  /reportTypes                                          [list available types]
POST /jobs   body={"reportTypeId":"channel_basic_a2","name":"basic"}
GET  /jobs                                                 [list registered jobs]
GET  /jobs/JOB_ID/reports?createdAfter=...                 [list daily reports]
GET  <report.downloadUrl>                                  [stream the gzipped CSV]
```

Daily delivery, ~60 day retention. Common reports: `channel_basic_a2`,
`channel_combined_a2`, `channel_traffic_source_a2`,
`channel_device_os_a2`, `playback_location_a2`, `content_owner_*` for CMS.

## Pagination Patterns

Data API uses `pageToken` / `nextPageToken`:

```python
items = []
req = yt.playlistItems().list(part="contentDetails", playlistId=pl, maxResults=50)
while req is not None:
    resp = req.execute()
    items.extend(resp["items"])
    req = yt.playlistItems().list_next(req, resp)
```

`maxResults` caps:
- Most list endpoints: 50
- `commentThreads.list`: 100
- `search.list`: 50 (and total addressable is hard-capped at ~500 results
  no matter how many pages you turn — `search.list` will not deliver page 11)

Analytics API uses `startIndex` (1-based) + `maxResults`:
```python
ya.reports().query(..., startIndex=1, maxResults=200).execute()
ya.reports().query(..., startIndex=201, maxResults=200).execute()
```
Hard cap is 200 rows per page. `totalResults` is in the response.

Reporting API uses `pageToken` for `jobs.reports.list`.

**Always sort before paginating** — the result set order is not stable across
pages without an explicit `order=` (Data API) or `sort=` (Analytics API).

## Rate Limits

Two independent quota systems. Both apply.

**1. Data API project quota**
- Default 10,000 units / day per Google Cloud project
- Resets midnight Pacific Time, not UTC
- Per-call cost varies — see Cost Model below
- Can request increase via the "Compliance Audit" form; must demonstrate
  policy compliance and use case. Approvals take 2-4 weeks
- Returns HTTP 403 with `reason=quotaExceeded` or `dailyLimitExceeded`

**2. Analytics API per-minute limits**
- Default 720 queries per minute per project
- 60 queries per minute per user
- Returns HTTP 429 with retry-after header

**Per-user write limits** (not formally documented but enforced):
- Approximately 50 video uploads per day per user via API
- Approximately 6 thumbnail changes per video per day
- Comment posting throttled aggressively for new accounts

**Reporting API** has no per-call quota — the jobs run server-side daily.

## Error Codes and Recovery

| Code | Reason | Recovery |
| --- | --- | --- |
| 400 | `invalidArgument` | Bad params; do not retry |
| 400 | `badRequest` + invalid filter | Fix filter; do not retry |
| 401 | `authError` | Refresh token; if still 401 the refresh token is dead, re-consent |
| 403 | `quotaExceeded` | Wait until midnight PT; do not retry until then |
| 403 | `dailyLimitExceeded` | Same as above |
| 403 | `rateLimitExceeded` | Backoff exponentially; per-minute, recover fast |
| 403 | `forbidden` + `insufficientPermissions` | Add scope and re-consent |
| 403 | `accountClosed` / `accountSuspended` | Permanent — surface to human |
| 403 | `commentsDisabled` | Per-video; do not retry |
| 404 | `videoNotFound` / `playlistNotFound` | Stale ID; remove from queue |
| 409 | `conflict` | ETag mismatch on update OR captions/thumbnails race; refetch + retry |
| 429 | (Analytics only) | Honor `Retry-After`, exponential backoff |
| 500 | `backendError` | Idempotent retry with backoff |
| 503 | `backendError` | Same |

Resumable upload special errors:
- 308 Resume Incomplete — normal mid-upload, contains `Range` header showing
  bytes received so far
- 404 on the upload session URL — session expired (12hr), restart upload
- 410 Gone — session URL invalidated, restart upload

Recommended backoff: `min(2**n + jitter, 64)` seconds, max 5 retries on 5xx
and `rateLimitExceeded`. Never retry `quotaExceeded` without sleeping until
the next reset.

## SDK Idioms

**Python (`google-api-python-client`)**:
- `build("youtube", "v3", credentials=creds, cache_discovery=False)` — always
  pass `cache_discovery=False` in production; the default writes a cache file
  to a system path that may not exist (warning in containerized envs)
- `.execute()` is synchronous, returns the parsed dict
- `.list_next(prev_request, prev_response)` for pagination
- `MediaFileUpload(path, chunksize=8*1024*1024, resumable=True)` for uploads
  — chunk sizes must be multiples of 256 KiB; -1 means upload-in-one-shot
- `MediaIoBaseUpload` for in-memory streams
- `HttpError.resp.status` and `HttpError.error_details` for structured errors
- Batch requests via `yt.new_batch_http_request(callback=cb)` — batches up to
  50 sub-requests in one HTTP call but **each sub-request still costs full
  quota** (the batching saves wall-time, not quota)

**Node (`googleapis`)**:
```javascript
const {google} = require('googleapis');
const yt = google.youtube({version: 'v3', auth: oauth2Client});
const res = await yt.videos.list({part: ['snippet'], id: ['VIDEO_ID']});
```
- Returns standard Promise; `res.data` for the body
- Uploads via `media: {body: fs.createReadStream(path)}`

**Idiomatic patterns**:
- Always pass `part=` as comma-separated string (Python) or array (Node), not
  as a list parameter
- For "give me N latest videos from a channel": resolve channel -> get
  `uploads` playlist ID -> `playlistItems.list` (1 unit), do NOT use
  `search.list` (100 units)
- For batch metadata reads: chunk video IDs into 50s, single `videos.list`
  call per chunk
- Always specify `fields=` parameter to limit response payload (does not
  reduce quota cost but reduces bandwidth and parse time)

## Anti-Patterns

- **Polling `search.list` for new uploads** — 100 units per call, has a hard
  ~500 result ceiling, and is heavily cached so it lags real-time. Use
  PubSubHubbub push notifications instead, or `playlistItems.list` against
  the uploads playlist (1 unit).
- **Calling `videos.list` per video in a loop** — batch IDs, 50 per call.
- **Using `videos.update` without `If-Match`** — race conditions silently
  overwrite concurrent edits.
- **Hardcoding API key in client-side JS** — exposes the key, drains your
  project quota when scraped. Restrict by HTTP referrer at minimum.
- **Storing access_token in DB** — store the refresh_token; access tokens
  expire in 1 hour and are cheap to regenerate.
- **Setting custom thumbnail immediately after upload** — race with auto-gen.
  Wait for processing.
- **Using ChromeDriver to "click upload" instead of API** — fragile, breaks
  on every UI redesign, and triggers bot-detection.
- **Treating "view count" from `videos.list` as real-time** — it's cached
  ~30 minutes for popular videos and updated less often for long-tail.
- **Querying Analytics API for today's data before ~48hr** — partial and
  unstable; "yesterday" only stabilizes by ~36 hours after midnight PT.
- **Polling `commentThreads.list` for moderation** — use `commentThreads.list`
  with `moderationStatus=heldForReview` and a low cadence; the moderation
  queue is typically small.
- **Mixing API key auth with OAuth on the same request** — passing both `key`
  and `Authorization` is allowed but the OAuth identity wins; the API key
  is wasted.
- **Calling `videos.insert` with `notifySubscribers=true` AND scheduled
  publish** — subscribers get notified at insert time, not at publish time,
  spoiling the schedule.

## Data Model

```
Channel (UC...)
  +- Branding (banner, watermark, default language)
  +- Statistics (subscribers, views, video count)
  +- ContentDetails
  |    +- relatedPlaylists.uploads (PL...) -> all uploads in date order
  |    +- relatedPlaylists.likes
  +- Sections (channel sections layout)
  +- Playlists
  |    +- Playlist (PL...)
  |         +- PlaylistItems (PLi...) -> reference to videoId
  +- Videos
  |    +- Video (11-char ID, base64url)
  |         +- Snippet (title, desc, tags, thumbnails, categoryId)
  |         +- ContentDetails (duration ISO 8601, definition, caption flag)
  |         +- Statistics (views, likes, comments)
  |         +- Status (privacyStatus, uploadStatus, madeForKids, license)
  |         +- ProcessingDetails (processingStatus, partsTotal/processed)
  |         +- TopicDetails (Freebase IDs, deprecated but still returned)
  |         +- LiveStreamingDetails (if live)
  |         +- Captions (CC IDs, language, trackKind)
  |         +- Comments
  |              +- CommentThread (top-level + replies)
  |                   +- Comment (textOriginal, textDisplay, authorChannelId)
  +- Subscriptions (out-bound only via API)
```

ID conventions:
- Channel IDs always begin with `UC` and are 24 chars
- Video IDs are exactly 11 base64url chars
- Playlist IDs begin with `PL`, `UU` (uploads), `LL` (liked), `WL` (watch later)
- Comment IDs are opaque base64
- Caption track IDs are opaque

ISO 8601 durations on `contentDetails.duration`: `PT1H2M3S`, `PT45S`, `P0D`
for live streams.

Thumbnail sizes returned in snippet:
- `default` 120x90, `medium` 320x180, `high` 480x360
- `standard` 640x480 (only on videos uploaded after ~2014)
- `maxres` 1280x720 (only if a 720p+ source was uploaded)

## Webhooks and Events

YouTube uses **PubSubHubbub (PuSH)** for push notifications. There is no
modern REST webhook system.

**Hub URL**: `https://pubsubhubbub.appspot.com/subscribe`
**Topic URL pattern**: `https://www.youtube.com/xml/feeds/videos.xml?channel_id=UC...`

Subscribe (form-encoded POST to hub):
```
hub.callback=https://your.server/webhook
hub.topic=https://www.youtube.com/xml/feeds/videos.xml?channel_id=UC...
hub.verify=async
hub.mode=subscribe
hub.lease_seconds=864000   # 10 days, max
```

The hub will GET your callback with `hub.challenge=` to verify. Echo it back
verbatim with HTTP 200.

When a new video uploads OR an existing video's metadata changes, the hub
POSTs an Atom feed to your callback containing:
- `<yt:videoId>`
- `<yt:channelId>`
- `<title>`, `<published>`, `<updated>`

There is **no payload for video deletes** and no event for stat changes.
You must re-subscribe before `lease_seconds` expires or the subscription
silently dies — most production setups re-subscribe daily via cron.

PubSubHubbub fires within seconds of the upload becoming visible, but for
private/scheduled videos it does NOT fire until publish time.

For comment / reply events: no webhook exists. You must poll
`commentThreads.list` with `order=time`.

For live stream state changes: poll `liveBroadcasts.list` with
`broadcastStatus=active|upcoming|completed`.

## Limits

| Resource | Limit |
| --- | --- |
| Video file size | 256 GB OR 12 hours, whichever first |
| Video upload formats | MOV, MPEG-1/2/4, MP4, AVI, WMV, MPEGPS, FLV, 3GPP, WebM, DNxHR, ProRes, CineForm, HEVC (h265) |
| Title length | 100 characters |
| Description length | 5,000 characters |
| Tag total length | 500 characters across all tags combined |
| Thumbnail file size | 2 MB |
| Thumbnail dimensions | 1280x720 recommended, min 640x360, 16:9 |
| Thumbnail formats | JPG, GIF, PNG |
| Caption file size | No documented cap; practical limit ~1 MB |
| Playlist item count | 5,000 videos per playlist |
| Playlists per channel | 10,000 |
| Daily upload count via API | ~50 (soft) |
| Live stream max length | 12 hours per stream |
| Shorts duration | <=180 seconds (3 minutes) since Oct 2024 |
| Shorts aspect ratio | <=1:1 (vertical or square classified as Short) |
| Comment length | 10,000 characters |
| Search result hard cap | ~500 results regardless of pagination |
| Resumable upload session lifetime | 12 hours from creation |
| Default project quota | 10,000 units/day |
| OAuth refresh token (test mode) | 7 days |
| OAuth refresh token (production) | Indefinite (until revoked or 6 months unused) |

## Cost Model

YouTube APIs are **free in dollars** but constrained by **quota units**.
Quota is per Google Cloud project per day, default 10,000 units, resets at
midnight US Pacific.

**Data API v3 unit costs** (per call):

| Operation | Cost |
| --- | --- |
| Read (`list`, `getRating`) base | 1 unit + 0 per part for most resources |
| `videos.list` | 1 unit base + extra per part on some parts |
| `search.list` | **100 units** |
| `videos.insert` | **1,600 units** |
| `videos.update` | 50 units |
| `videos.delete` | 50 units |
| `videos.rate` | 50 units |
| `videos.reportAbuse` | 50 units |
| `playlists.insert/update/delete` | 50 units each |
| `playlistItems.insert/update/delete` | 50 units each |
| `playlistItems.list` | 1 unit |
| `thumbnails.set` | 50 units |
| `captions.list` | 50 units |
| `captions.insert` | **400 units** |
| `captions.update` | 450 units |
| `captions.download` | 200 units |
| `commentThreads.insert` | 50 units |
| `comments.setModerationStatus` | 50 units |
| `subscriptions.insert/delete` | 50 units |

Practical implications at 10K/day default:
- ~6 video uploads max
- ~100 search queries max
- ~10,000 playlistItems list calls
- ~25 caption inserts

**Analytics API**: free, no unit cost, but 720 qpm project / 60 qpm user.

**Reporting API**: free, no unit cost.

**YouTube Premium revenue and ad revenue**: requires YPP membership, accessed
via Analytics API with `yt-analytics-monetary.readonly`. The data itself is
free; partner program participation has its own threshold (1000 subs +
4000 watch hours OR 1000 subs + 10M Shorts views in 90 days).

**Quota increase**: free, but requires the YouTube API Services Compliance
Audit form. Typical approvals raise to 1M units/day. Approvals can take
2-4 weeks and require demonstrating policy compliance.

## Version Pinning

| API | Version | Status | Sunset |
| --- | --- | --- | --- |
| YouTube Data API v3 | v3 | Stable | None announced |
| YouTube Data API v2 | v2 | **Dead** | Shut down 2015 |
| YouTube Analytics API v2 | v2 | Stable | None announced |
| YouTube Analytics API v1 | v1 | **Dead** | Shut down 2018 |
| YouTube Reporting API v1 | v1 | Stable | None announced |
| YouTube Live Streaming API | (folded into Data API v3) | Stable | n/a |

Pin SDK versions in production:
```
google-api-python-client==2.122.0
google-auth==2.29.0
google-auth-oauthlib==1.2.0
google-auth-httplib2==0.2.0
```

Discovery documents are versioned by API version, not SDK — the same SDK
version can talk to whatever Google publishes server-side. SDK upgrades
matter only for transport-level improvements (chunking, retry behavior).

Watch the [release notes](https://developers.google.com/youtube/v3/revision_history)
— breaking deprecations are announced ~6 months ahead. Recent removals:
`fileDetails`, `processingDetails.processingProgress.partsProcessed` (still
present but unstable), `topicDetails.topicIds` (replaced by `topicCategories`).

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

YouTube was architected around **session time** as the primary objective.
Every surface (Home, Watch Next, Search, Shorts) is a recommender competing
for the same user-attention budget. Ranking is ultimately:

```
score(video, user, context) ~ P(click) * E[watch_time_in_session | click] * session_value
```

This is why a 6-minute video with 80% retention often out-distributes a
30-minute video with 20% retention even if absolute watch time is identical:
the algorithm credits the session contribution and the satisfaction signal.

Tradeoffs YouTube has explicitly chosen:
- **Browse > Search**: Home/Suggested account for ~70% of typical channel
  views vs Search ~15%. The platform weights *what we recommend* over
  *what users ask for* because passive sessions are longer.
- **Per-impression CTR vs absolute views**: A 10% CTR on a video with 100K
  impressions is treated as a *positive feedback loop* signal — the
  algorithm pushes more impressions until CTR or AVD breaks.
- **Satisfaction over engagement**: Likes/comments matter less than survey
  satisfaction (the periodic "How would you rate this video?" prompts) and
  "not interested" / "don't recommend channel" hits.
- **Shorts is a separate ranker**: Shorts performance does NOT cleanly
  translate to long-form Browse score; the two feeds are siloed at the
  recommendation layer even though they share the same channel.
- **Session vs subscription**: Subscription bell traffic exists but is a
  small fraction. The home feed often shows non-subscribed channels first
  if predicted session value is higher.

## Problem-Solution Map and Hidden Capabilities

| Problem | Built-in Solution |
| --- | --- |
| Schedule a publish | `videos.insert` with `status.publishAt` + private |
| Drop a video to multiple time-zones simultaneously | YouTube auto-translates `publishAt` to local time per viewer; just pick a UTC time |
| A/B test thumbnails | Native "Test & Compare" feature (3 thumbnails, ~2-week test) — 2024 GA, no API yet but results show in Studio |
| Premiere a pre-recorded video as live | `liveBroadcasts.insert` with `contentDetails.enableEmbed=true`, set `snippet.scheduledStartTime` |
| Members-only content | Set `status.privacyStatus=public` then mark via `videoSegmentMembership` (Studio UI) |
| Chapters | Auto-generated from description timestamps starting with `00:00` and increasing |
| End screens | `videos.update` does NOT support — use Studio UI or YouTube end-screen template inheritance |
| Cards | Same — Studio only |
| Pinned comment | `comments.markAsSpam` is the only moderation API; pinning is Studio only |
| Auto-translate captions | Upload English captions; YouTube auto-generates community translations if enabled |
| Heatmap (most replayed) | `Most Replayed` graph appears in Studio after ~2 weeks; not exposed in API |
| Live chat replay | `liveChatMessages.list` with `liveChatId` from completed broadcast |
| Community tab posts | NOT in the public API — must use third-party scrapers or browser automation |
| Playlists ordering | Position field on `playlistItems` |

Hidden capabilities most creators don't know exist:
- **`uploads` playlist** — every channel has a magic playlist of all uploads
  in date order, listed in `channels.list -> contentDetails.relatedPlaylists.uploads`
- **`videoCategories.list` is region-specific** — IDs vary by `regionCode`
- **`i18nLanguages` and `i18nRegions`** for localized title/description
- **`videos.insert` `recordingDetails.location`** for geo-tagged content
- **`localizations` part** on `videos.update` for multi-language titles +
  descriptions visible to viewers in matching locales — massive untapped lever
- **`chart=mostPopular`** with `regionCode` for the public trending list
- **`activities.list`** — channel activity feed (uploads, likes, social)

## Operational Behavior and Edge Cases

- Newly uploaded videos are `processingStatus=processing` for ~minutes to
  hours depending on length. Most write operations queue cleanly during
  processing, but thumbnails and captions race.
- "Made for Kids" is **irreversible per video** in some account states;
  changing requires support ticket.
- Hashtags in description are clickable and appear above the title (top 3).
  Hashtags in title work but YouTube de-emphasizes them.
- The first 125 characters of the description appear above the fold ("Show
  more") on mobile — the algorithm and viewers use this prime real estate.
- Tags have minimal SEO weight since 2018; titles, descriptions, and on-screen
  text matter far more. Tags are still useful for misspelling capture.
- Closed captions improve retention measurably (~10% lift in some studies)
  because viewers in silent contexts can engage.
- Premiere countdowns generate a chat that converts to comments after the
  premiere ends — useful "fake live" engagement signal.
- Ending a video with "subscribe + watch next" reduces session time IF the
  next video is on YouTube's recommended panel (the platform handles that).
  Better to end with a strong recap and let YouTube route the next click.
- Re-uploading a video deletes view history and resets the ranking; never
  re-upload to "fix" something — use `videos.update` instead.
- Changing the title or thumbnail of an existing video resets the
  algorithm's CTR baseline and can revive a video that was buried.
- **Shadow throttling exists** for re-used content — the Content ID system
  flags duplicates and reduces distribution silently.
- **Shorts loops count as views** every loop after the first ~30s; this is
  why Shorts view counts inflate so fast and why "loop friendliness" matters.

## Ecosystem Position and Composition

YouTube sits at the center of long-form video distribution and is now
encroaching on short-form (vs TikTok/Reels), live (vs Twitch), and podcasts
(vs Spotify/Apple).

**Vs TikTok**: TikTok has stronger algorithm-to-creator amplification for
new accounts but worse monetization. YouTube Shorts pays via the Shorts
Fund -> now Partner Program revenue share, with much higher RPM ceilings.
Best practice: post originals on TikTok, repurpose top performers as Shorts.

**Vs Instagram Reels**: Reels has the worst monetization of the three but
best in-feed integration with photos/Stories. Use Reels for personal
brand/aesthetic, YouTube Shorts for monetizable repurposing.

**Vs Twitch**: Twitch dominates live gaming; YouTube dominates VOD. Stream
on Twitch, restream/archive on YouTube via tools like Restream.

**Vs Vimeo**: Vimeo is dead for distribution but useful for client-deliverable
private hosting with white-label players.

**Vs Podcasts (Spotify/Apple)**: YouTube quietly became the #1 podcast
discovery surface in 2024. Cross-post audio podcasts as videos (static image
OR remote-recorded multi-cam) and tag with `categoryId=22` (People & Blogs)
or `27` (Education).

**Composition stack** (typical creator):
- **Capture**: Sony A7IV / iPhone Pro / Riverside
- **Edit**: Premiere / DaVinci Resolve / Descript
- **Repurposing**: Opus Clip / Klap / Submagic for AI clip extraction
- **Thumbnails**: Photoshop / Figma / Canva / Thumbsup AI
- **Title testing**: TubeBuddy / VidIQ / Spotter Studio
- **Analytics dashboards**: Modash / Notion + custom Reporting API pulls
- **Publishing**: Native Studio OR Buffer/Hootsuite for cross-platform
- **SEO**: vidIQ keyword scores + Google Trends

Where the API fits in this stack: any component above that says "do it in
Studio" can be programmatized via Data API v3 for batch operations and
scheduled workflows.

## Trajectory and Evolution

Direction the platform is moving (2024-2026):

- **Shorts monetization at parity with long-form**: Partner Program now
  shares ad revenue from Shorts feed (started 2023). RPMs have risen but
  still lag long-form by ~5x. Platform is investing heavily because TikTok
  is the existential threat.
- **Podcast push**: YouTube Music adopted podcast hosting in 2024,
  dethroning Google Podcasts. Expect tighter integration with audio-only
  RSS-style ingestion.
- **AI-generated content disclosure**: New `selfDeclaredAltered` field
  required when synthetic media is used; failure to disclose risks
  Community Guidelines strikes.
- **Removable AI training opt-in/out**: Channel-level controls for whether
  third-parties can train on your videos. Default is opt-out for most.
- **Native A/B thumbnail testing GA** in 2024 — expect API exposure soon.
- **"Hype" feature** (2024) — viewers can boost small channels' videos,
  another Browse signal.
- **Communities replacing Community Tab** in 2025 rollout — creator-led
  forums per channel, no public API yet.
- **Short -> Long-form Bridge**: New "Continue watching on long-form"
  prompts in Shorts feed pushing creators to use Shorts as funnels.
- **Shorts duration extension to 3 minutes** (Oct 2024) closed the last gap
  with TikTok. Repurposing pipelines should target ~90s sweet spot still.
- **AI-generated dubbing**: Multi-language audio tracks now supported on a
  single video (`audioTrack` resource), removing the need for re-uploading.

What is being deprecated or de-emphasized:
- Stories (deprecated 2023 — gone)
- Community Posts (replaced by Communities in 2025)
- The `topicDetails` Freebase IDs (deprecated, returns nulls)
- Manual `categoryId` selection signals are being replaced by content
  understanding ML (categoryId still required, but algorithmic weight is low)

## Conceptual Model and Solution Recipes

**Mental model: every video is a pitch for the next click.**

The algorithm scores videos by predicted *contribution to the viewer's
session*. So every metric you optimize is downstream of two questions:
"Will they click?" (CTR) and "Will the click feel worth it?" (AVD +
satisfaction). All operational decisions trace back to those.

**Recipe: Launch a video the algorithm respects**
1. Title <60 chars, front-load the hook keyword
2. Custom thumbnail at 1280x720, contrast > color, max 4 visual elements
3. Description: hook in first 125 chars + 5 tag-worthy terms naturally + chapters
4. Upload to private with `publishAt` scheduled at high-traffic time
   (Tue-Thu 14:00-17:00 for the channel's primary timezone)
5. Set thumbnail AFTER `processingStatus=succeeded`
6. Add to relevant playlist immediately (playlist context boosts Suggested)
7. Pin a comment with a question to seed engagement
8. Do NOT mass-share to social media in the first 30 minutes — the algorithm
   prefers organic Browse traffic in the first hour for "external bias"
   reasons (tracked by traffic source mix)

**Recipe: Diagnose a flop**
1. `Analytics.reports.query` with `dimensions=insightTrafficSourceType`
2. If `BROWSE` is <30% of views: packaging failed (CTR too low for Browse
   to push) — test new thumbnail
3. If Browse is high but `averageViewPercentage` <35%: hook failed — re-cut
   the first 30 seconds
4. If Browse + AVD are both fine but `subscribersGained` is flat: video is
   not a "channel-defining" piece — your audience didn't bond
5. Re-test packaging 14 days later — algorithm gives second chances on title
   and thumbnail changes

**Recipe: Repurpose a TikTok winner as a Short**
1. Pull source via `tiktok` skill or yt_dlp
2. Re-render at 1080x1920, burn captions in (Submagic / Opus Clip)
3. Strip TikTok watermark (or YouTube down-ranks it)
4. Upload via `videos.insert` with `#Shorts` in title and description
5. Use a different (shorter) hook — TikTok hooks assume sound on, YouTube
   Shorts assumes mixed
6. Wait 48 hours, pull `dimensions=sharingService` to see if Shorts surfaced
   it; if not, the dup-detection caught the watermark

## Industry Expert and Cutting-Edge Usage

- **MrBeast (Jimmy Donaldson)**: Famously runs >20 thumbnail iterations per
  video, manually A/B tests via swap-and-watch in Studio, optimizes purely
  for CTR ceiling. His packaging operation is a 6-person team.
- **Veritasium (Derek Muller)**: Optimized for AVD over CTR — long
  educational videos with strong narrative arcs, low CTR but extreme
  retention. Algorithm rewards this with massive Suggested feed presence.
- **Ali Abdaal**: Productivity-stack creator who publicly documents the
  "stack of stacks" — Notion publishing pipeline + ConvertKit + Riverside +
  Descript + Skillshare. His channel is the canonical case study for
  service-business YouTube as marketing.
- **Colin and Samir**: Industry analysts who interview creators about
  metrics — primary source for understanding how the algorithm evolves.
- **Paddy Galloway**: YouTube growth strategist; coined "packaging" as the
  industry term. Heavy emphasis on first-hour CTR.
- **Spotter / Jellysmack**: Acquire creator catalogs and optimize them via
  systematic title/thumbnail/repackaging at scale using their own tools.
- **TubeBuddy / VidIQ**: Creator ops tools that wrap the API to surface
  CTR/keyword data Studio doesn't expose well.
- **Modash / Spotter Studio**: Advanced analytics dashboards aggregating
  Reporting API CSVs into channel-comparison dashboards.
- **Opus Clip / Klap / Vizard**: AI clip-extraction tools that ingest a
  long-form video, identify highlight moments (transcript + visual saliency),
  and auto-cut vertical Shorts. Output via API.
- **Descript Underlord**: AI-driven podcast/video editor with native YouTube
  publishing.

Cutting-edge patterns (2025-2026):
- **Multi-language audio tracks** to globally distribute one upload —
  MrBeast's channel led adoption, lifting global reach 30%+
- **AI-generated B-roll** via Sora / Veo / Runway, disclosed via the
  altered-content flag
- **Dynamic thumbnails** based on viewer cohort (Studio test feature, no
  API yet) — different viewers see different thumbnails for the same video
- **Hype boost coordination**: small-channel growth tactic where audiences
  use the Hype button to artificially inflate Browse signals
- **Shorts -> long-form funnels**: Use Shorts as top-of-funnel (cheap
  attention), pin a comment driving to a long-form deep-dive, measure
  conversion via traffic source `SHORTS` -> `RELATED_VIDEO`

---

## EOS Usage Patterns

**Channel growth strategy** (Antony's personal brand):
1. Long-form anchor video weekly: interview / breakdown, 15-25 min, optimized
   for AVD over CTR (positions as authority)
2. 3-5 Shorts per week repurposed from TikTok winners
3. Community tab posts manually 2x/week (can't be automated yet)
4. Weekly analytics ritual: every Sunday 09:00, agent pulls 7-day metrics
   via Analytics API, writes to Neon `yt_metrics` table, drafts a report in
   the morning brief identifying biggest CTR/AVD opportunity

**Publish loop** (`scripts/publish_youtube.py`):
1. Empyrean Studio writes draft (title 5 variants, description, chapters,
   tags, thumbnail brief)
2. Antony approves variant + finished thumbnail
3. Script calls `videos.insert` resumable + `thumbnails.set` after
   processingStatus poll loop
4. Schedules `publishAt` to next Tuesday 14:00 PT
5. Inserts to relevant playlist
6. Stores `video_id` in Neon `yt_publishing_queue` for tracking

**Shorts repurpose loop** (`scripts/shorts_repurpose.py`):
1. Pulls TikTok top 10 of last 7 days (via `tiktok` skill)
2. Filters by view threshold (>50K) and length (<3 min)
3. Re-renders 9:16 with caption burn-in (Submagic API or local FFmpeg)
4. Removes watermark, prepends 0.5s clean intro
5. Uploads as Shorts with new title (no TikTok-style hooks)
6. Logs to Neon `shorts_pipeline`

**Weekly analytics ritual**:
```python
# Sunday 09:00 PT cron
metrics = ya.reports().query(
    ids="channel==MINE",
    startDate=last_sunday, endDate=yesterday,
    metrics="views,impressions,impressionsClickThroughRate,averageViewPercentage,subscribersGained",
    dimensions="video",
    sort="-views",
    maxResults=25,
).execute()
# Diff against last week's snapshot in Neon
# Alert on CTR < 4% or AVP < 30% on any video > 1k views
```

**Quota budget** (10K units/day default):
- Daily list of recent uploads: ~10 units
- Analytics queries: 0 units (separate quota)
- Weekly publish (1 video): 1,650 units
- Weekly Shorts (5 videos): 8,000 units — risks ceiling
- One thumbnail set per video: 50 units
- Headroom for ad-hoc: <500 units

Hits the ceiling on Shorts week. Mitigation: spread Shorts uploads across
days, not one batch, OR file for quota increase to 100K/day.

**Notion publishing board** mirrors `yt_publishing_queue` for human oversight.
The agent drafts in Notion first, then pulls approved rows for upload.

## Gotchas

(Real failures encountered. Compounds over time.)

- **2026-04-06**: Initial OAuth setup hit the 7-day refresh token expiry.
  Cron was working all week, then died Sunday. Fix: pushed app to
  "In production" in Cloud Console, re-consented, new refresh token
  durable. Add to monthly review: verify token still valid first of every
  month.
- **2026-04-06**: First `thumbnails.set` after upload was overwritten by
  YouTube auto-thumbnail ~45 seconds later. Fix: poll
  `videos.list?part=processingDetails` until `processingStatus=succeeded`
  before thumbnail set.
- **Shorts duration boundary**: a 181-second video does NOT count as a
  Short, even with `#Shorts` tag and 9:16 aspect ratio. Strict <=180s.
- **`search.list` cost shocker**: a single test loop polling for "new
  uploads from competitor channels" burned 8,000 units in 15 minutes.
  Replaced with PubSubHubbub for real channels and `playlistItems.list`
  on uploads playlist for everything else.
- **Resumable upload retry**: when network drops mid-chunk, the SDK's
  default `next_chunk()` retry sometimes leaves the session in a bad
  state. Wrap the entire upload loop in a try/except that re-creates the
  request from scratch on persistent failure.
- **Analytics API "yesterday" returns partial data** until ~36 hours after
  midnight PT. The Sunday pull uses `endDate=Friday` to avoid this.
- **`publishAt` rejected with privacyStatus=public** error message is
  cryptic ("invalidPublishAt") — must be private at insert.
- **`#Shorts` in title vs description**: the algorithm reads both, but
  putting it in the title burns chars in the most valuable real estate.
  Description hashtag is sufficient.
- **Multipart upload via `MediaFileUpload(resumable=False)` on a 400MB
  video** silently OOM'd a 1GB container. Always use `resumable=True` for
  videos >50MB.
- **`fields=` parameter syntax**: dotted path with parens for nested
  selections, e.g. `items(id,snippet(title,thumbnails/high))`. Wrong
  syntax returns 400 invalidFieldSelection.
- **Captions track upload requires `sync=true`** as a query parameter for
  YouTube to auto-time the caption against the audio. Without it, the
  caption uploads but never displays.
- **OAuth scope additions require re-consent** — adding
  `yt-analytics-monetary.readonly` after the initial auth means the old
  refresh token is missing the scope and Analytics monetary calls return
  403 forever until re-consented from scratch.
