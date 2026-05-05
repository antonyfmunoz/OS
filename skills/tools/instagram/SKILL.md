<<<<<<< Updated upstream
---
name: instagram
description: "Use when any agent needs Instagram DM monitoring, comment scraping, session management, or bot detection avoidance for lead generation."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://developers.facebook.com/docs/instagram-api/"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "Instagram Graph API v22.0 (Meta Graph API rolling — v24.0 available) / Playwright automation"
sdk_version: "Playwright 1.58.0 (sync API) + Apify actors"
speed_category: "slow"
trigger: both
effort: medium
context: fork
---

# Tool: Instagram

## What This Tool Does

Instagram access in EOS happens through three distinct paths, each serving a different purpose:

1. **Playwright browser automation** (`dm_monitor.py`) — reads DM inbox, detects replies, extracts messages
2. **Apify cloud scrapers** (`apify_scraper.py`) — scrapes comments from hashtags and competitor posts
3. **ManyChat** — DM automation for approved outreach campaigns (external, not coded in EOS)

The Meta Graph API exists but is not actively used for DM access — DM access requires approved Instagram Messaging permission which is not granted for EOS's use case. However, the Graph API IS the right path for Instagram **content publishing** (Reels, Stories, Feed posts), **insights/analytics**, **comment moderation**, and **Shopping product tagging** — all relevant to Lyfe Spectrum and Empyrean Studio content workflows. See the "Instagram Graph API — Publishing & Insights" section below.

**Cross-reference:** For Meta Graph API auth (long-lived tokens, system user tokens, app review, webhook subscriptions, the unified token zoo across Messenger/WhatsApp/Threads/Pages), see `/opt/OS/skills/tools/meta_graph_api/SKILL.md`. This skill focuses on Instagram-specific endpoints; meta_graph_api owns the auth/token/webhook mechanics shared across Meta surfaces.

## EOS Integration

### Path 1: DM Monitor — Playwright (`services/dm_monitor.py`)

**What it does:**
1. Launches headless Chromium inside Docker (os-monitor container)
2. Restores Instagram session from `storage_state` JSON
3. Navigates to DM inbox (`/direct/inbox/`)
4. Detects unread conversations via DOM selectors
5. Opens each unread thread, extracts messages
6. Feeds extracted messages to AI for sales conversation assistance
7. Takes diagnostic screenshots on failures

**Architecture:**
```
os-monitor container
  └── dm_monitor.py (90-second startup delay)
        └── sync_playwright()
              └── chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
                    └── browser.new_context(storage_state=..., user_agent=..., viewport=...)
                          └── context.new_page()
                                ├── page.goto("https://www.instagram.com/direct/inbox/")
                                ├── page.query_selector_all('a[href*="/direct/t/"]')
                                ├── Extract unread indicators
                                ├── Click thread → extract messages
                                └── context.storage_state(path=...) [save session]
```

**Key config:**
```yaml
# docker-compose.yml
os-monitor:
  shm_size: '2gb'  # Chromium needs this, default 64MB causes SIGBUS
  environment:
    - MONITOR_STARTUP_DELAY=90
    - INSTAGRAM_USE_PROXY=false
```

### Path 2: Comment Scraping — Apify (`services/apify_scraper.py`)

See `skills/tools/apify/SKILL.md` for full details.

**Flow:**
```
Cron → apify_scraper.py
  ├── Hashtag scraping (A/B rotation groups)
  │     → Instagram Hashtag Scraper actor → posts
  │     → Instagram Comment Scraper actor → comments
  │     → Bot/spam filter → priority classification
  │     → Save to 01_Inbox/raw_signals/
  └── Competitor scraping (5 accounts)
        → Instagram Profile Scraper actor → posts
        → Filter by ICP relevance (Whisper + Claude + keywords)
        → Comment scrape → filter → save
```

### Path 3: ManyChat (External)
ManyChat handles approved DM automation sequences.
Not coded in EOS — configured in ManyChat dashboard.
EOS receives booking notifications via Calendly webhooks when ManyChat DMs convert.

### Agents that use it
- DM Monitor (directly — Playwright)
- Scraper Service (directly — Apify)
- EA Agent (indirectly — reads DM Monitor reports)
- Outreach Agent (indirectly — uses signals from scraper)

## Authentication

### Playwright session (DM Monitor)
```python
# Session stored as Playwright storage_state JSON
# Contains both cookies AND localStorage (both required)
instagram_session.json = {
    "cookies": [...],
    "origins": [{
        "origin": "https://www.instagram.com",
        "localStorage": [...]
    }]
}

# Restore session
context = browser.new_context(storage_state="instagram_session.json")

# Save session after successful login
context.storage_state(path="instagram_session.json")
```

### Fresh login flow (when session expires)
```python
# 1. Navigate to root (NOT /accounts/login/ — returns blank from VPS)
page.goto("https://www.instagram.com/")

# 2. Fill credentials (use .type() with delay, NOT .fill() — React inputs)
page.locator('input[name="email"]').click()
page.locator('input[name="email"]').type(username, delay=80)
page.locator('input[name="pass"]').click()
page.locator('input[name="pass"]').type(password, delay=80)

# 3. Click login button
page.locator('button:has-text("Log in")').click()

# 4. Handle verification code (relayed via Telegram)
# 5. Dismiss "Save Info" and "Not Now" prompts
# 6. Save session
context.storage_state(path="instagram_session.json")
```

### Environment variables
| Variable | Purpose |
|----------|---------|
| `INSTAGRAM_USERNAME` | Login email/username |
| `INSTAGRAM_PASSWORD` | Login password |
| `INSTAGRAM_USE_PROXY` | `true` to route through Apify RESIDENTIAL proxy |
| `APIFY_PROXY_PASSWORD` | Proxy auth when proxy enabled |
| `MONITOR_STARTUP_DELAY` | Seconds to wait before first check (default 90) |

## Quick Reference

### Check DM inbox
```python
page.goto("https://www.instagram.com/direct/inbox/", wait_until="domcontentloaded")
page.wait_for_selector("div[role='main']", timeout=60000)
threads = page.query_selector_all('a[href*="/direct/t/"]')
```

### Detect unread conversations
```python
# Look for unread indicators (blue dot, bold text)
for thread in threads:
    unread_indicator = thread.query_selector('[data-testid="unread"]')
    # OR check for bold font-weight on thread preview text
```

### Extract messages from thread
```python
thread.click()
page.wait_for_load_state("domcontentloaded")
messages = page.query_selector_all('div[dir="auto"]')
for msg in messages:
    text = msg.inner_text()
```

### Bot detection avoidance
```python
# Human-like timing
import random
time.sleep(random.uniform(2, 5))

# Character-by-character typing (NOT fill())
page.locator('input').type("text", delay=80)

# Desktop Chrome UA (NOT mobile — causes blank page)
user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36...'

# Viewport matches real browser
viewport = {'width': 1280, 'height': 800}
```

## Gotchas

### Direct /accounts/login/ URL returns blank page (ACTIVE)
Instagram serves a blank page when `/accounts/login/` is accessed from VPS IPs.
**Fix:** Always navigate to root `https://www.instagram.com/` — login form renders correctly.

### Cookie-only session restore triggers bot detection (RESOLVED)
Using only `context.add_cookies()` left sessions incomplete — localStorage was missing.
**Fix:** Use `storage_state()` which saves both cookies AND localStorage.

### React inputs reject fill() (ACTIVE)
Instagram's React-controlled inputs reject synthetic `fill()` events.
**Fix:** Use `click()` + `type(text, delay=80)` for character-by-character input.

### Chromium SIGBUS in Docker (RESOLVED)
Default Docker `/dev/shm` is 64MB. Chromium exceeds this during rendering.
**Fix:** `shm_size: '2gb'` in docker-compose.yml.

### Startup OOM from rapid restart loops (RESOLVED)
Docker `restart: always` caused rapid Chromium restarts (~700MB each), exhausting RAM.
**Fix:** 90-second startup delay (`MONITOR_STARTUP_DELAY=90`) + stale session cleanup.

### Mobile User-Agent causes blank page (RESOLVED)
Mobile Safari UA causes Instagram to serve app-redirect blank page in headless Chromium.
**Fix:** Desktop Chrome UA confirmed to render login form correctly.

### Instagram selector changes break DM extraction (INTERMITTENT)
Instagram updates DOM structure without notice. Selectors for thread links, unread indicators, and message containers break.
**Detection:** DM Monitor reports 0 threads despite known unread messages.
**Fix:** Update selectors in `dm_monitor.py`, test with diagnostic screenshots.

### Apify RESIDENTIAL proxy 403 (ACTIVE)
Proxy credits are separate from compute units. 403 when depleted.
**Fix:** `INSTAGRAM_USE_PROXY=false` until credits refill.

See references/best_practices.md for full session management patterns, anti-detection strategies, and selector reference.

---

## Instagram Graph API — Publishing & Insights (2026-04-06 expansion)

This section covers the Instagram-specific Graph API endpoints. Auth, long-lived tokens, system user tokens, webhook subscription mechanics, and app review live in `skills/tools/meta_graph_api/` — do not duplicate here.

**Conceptual model:** All endpoints below assume an **Instagram Business account** linked to a Facebook Page, with a Page access token (or System User token) that has `instagram_basic`, `instagram_content_publish`, `instagram_manage_insights`, `instagram_manage_comments`, `pages_read_engagement`, and (for Shopping) `instagram_shopping_tag_products` scopes. The IG user ID (`{ig-user-id}`) is the IG Business Account ID, NOT the username. Resolve via `GET /{page-id}?fields=instagram_business_account`.

Creator accounts are NOT supported for content publishing API — Business only.

### Content Publishing — Two-step container flow

All publishing (Feed, Reels, Stories, Carousels) uses a two-step pattern:

```
1. POST /{ig-user-id}/media         → returns container_id
2. POST /{ig-user-id}/media_publish  → creation_id=container_id → returns published media id
```

Containers expire after 24 hours. For video/Reels containers, poll `GET /{container-id}?fields=status_code` until `FINISHED` before publishing (typical wait 30-90s). Status codes: `IN_PROGRESS`, `FINISHED`, `ERROR`, `EXPIRED`, `PUBLISHED`.

### Reels publishing

```http
POST /{ig-user-id}/media
  ?media_type=REELS
  &video_url=https://cdn.example.com/reel.mp4
  &caption=...
  &cover_url=https://cdn.example.com/cover.jpg
  &share_to_feed=true
  &collaborators=["partner_ig_username"]
  &thumb_offset=1000        # ms into video for thumbnail
  &audio_name=...
  &access_token=...
```

Then poll status_code → `FINISHED`, then:
```http
POST /{ig-user-id}/media_publish?creation_id={container_id}&access_token=...
```

**Reels constraints (current):**
- Aspect ratio 9:16 required for Reels tab eligibility
- Duration 5–90 seconds for Reels tab eligibility (API accepts up to 15 min but anything outside 5–90s publishes as regular video)
- Video host: video uploads use `rupload.facebook.com`, not `graph.facebook.com`
- Rate limit: 100 API-published posts per IG account per rolling 24h (counts Reels + feed + carousels + stories together)
- Container is `media_type=REELS` but `GET /{media-id}?fields=media_type` returns `VIDEO`. Use `media_product_type` field to confirm REELS designation.

### Stories publishing

```http
POST /{ig-user-id}/media
  ?media_type=STORIES
  &image_url=...                # OR video_url for video stories
  &access_token=...
```
Then `media_publish`. Stories support image and video. No caption parameter — stickers/text overlays are not supported via API (publish raw media only).

### Carousel publishing (children pattern)

```
1. Create child containers (one per item, no caption):
   POST /{ig-user-id}/media?media_type=IMAGE&image_url=...&is_carousel_item=true
2. Create parent carousel container:
   POST /{ig-user-id}/media?media_type=CAROUSEL&children=child_id_1,child_id_2,...&caption=...
3. Publish parent.
```

### Collaborators API

`collaborators` parameter on the Feed/Reel media container accepts an array of IG usernames. The collaborator receives an invitation in their app and must accept before the post appears on their grid. Only available for Reels and feed video/image posts (not Stories).

### Mentions & user tags

- **Photo tags (image posts):** `user_tags` parameter — array of `{username, x, y}` (x/y = 0.0–1.0 normalized).
- **Caption mentions:** `@username` in caption auto-resolves and sends notification.
- **Story mentions:** Not supported via Content Publishing API (Story sticker mentions are app-only).
- **Mention webhooks:** Subscribe to the `mentions` field on the Instagram webhook to receive notifications when your account is @-mentioned in captions/comments. Lookup payload via `GET /{ig-user-id}?fields=mentioned_media{caption,media_type,id}`.

### Insights API

**Account-level (`GET /{ig-user-id}/insights`):**
- Metrics: `reach`, `impressions` (deprecated April 2025 — use `views`), `profile_views`, `accounts_engaged`, `total_interactions`, `likes`, `comments`, `shares`, `saves`, `replies`, `follows_and_unfollows`, `profile_links_taps`, `website_clicks`, `email_contacts`, `phone_call_clicks`, `text_message_clicks`, `get_directions_clicks`.
- Required `metric_type=total` for v18.0+ on most metrics. Use `period=day` and `since`/`until` Unix timestamps.
- Demographic breakdowns: `follower_demographics`, `engaged_audience_demographics`, `reached_audience_demographics` with `breakdown=age,gender,city,country`.

**Media-level (`GET /{ig-media-id}/insights`):**
- Feed image/carousel: `reach`, `likes`, `comments`, `shares`, `saved`, `total_interactions`, `views`, `profile_visits`, `profile_activity`, `follows`.
- Reels: `reach`, `likes`, `comments`, `shares`, `saved`, `total_interactions`, `views` (replaces `plays` and `ig_reels_aggregated_all_plays_count` post-April-2025), `ig_reels_video_view_total_time` (ms), `ig_reels_avg_watch_time` (ms).
- Stories: `reach`, `views`, `replies`, `shares`, `total_interactions`, `profile_visits`, `follows`, `navigation` (with breakdown into `tap_back`, `tap_forward`, `tap_exit`, `swipe_forward`).

**April 2025 deprecation:** `impressions`, `plays`, `clips_replays_count`, `ig_reels_aggregated_all_plays_count` → unified into `views`. Update any code referencing those metric names.

### Comment moderation

- `GET /{ig-media-id}/comments` — list comments on a media object.
- `GET /{ig-comment-id}/replies` — list replies to a comment.
- `POST /{ig-media-id}/comments?message=...` — reply on the post.
- `POST /{ig-comment-id}/replies?message=...` — reply to a comment.
- `DELETE /{ig-comment-id}` — delete a comment.
- `POST /{ig-comment-id}?hide=true` — hide/unhide a comment.
- Webhook field `comments` delivers new-comment events; subscribe via meta_graph_api skill's webhook flow.

### Shopping — Product tagging (Lyfe Spectrum)

Requires an approved Instagram Shop linked to a Facebook Catalog plus `instagram_shopping_tag_products` permission.

- **Product search:** `GET /{ig-user-id}/available_catalogs` → catalog id; `GET /{ig-user-id}/catalog_product_search?q=...` → product ids eligible for tagging.
- **Image post with tags:** add `product_tags=[{"product_id":"...","x":0.5,"y":0.5}]` to the `media` container call.
- **Video/Reel post with tags:** `product_tags=[{"product_id":"..."}]` (no x/y — applied as collection).
- **Carousel:** product tags go on the child container at creation time, not the parent.
- **Storefront eligibility:** product must be `approved` status in the catalog. Check `GET /{product-id}?fields=review_status`.

### Quick reference — common Reels publish snippet

```python
import requests, time

IG = "<ig-user-id>"
TOKEN = "<page-access-token>"
BASE = "https://graph.facebook.com/v22.0"

# 1. Create container
r = requests.post(f"{BASE}/{IG}/media", data={
    "media_type": "REELS",
    "video_url": "https://cdn.example.com/reel.mp4",
    "caption": "Built different. #LifeMaxing",
    "share_to_feed": "true",
    "access_token": TOKEN,
}).json()
container_id = r["id"]

# 2. Poll until FINISHED
while True:
    s = requests.get(f"{BASE}/{container_id}",
        params={"fields": "status_code", "access_token": TOKEN}).json()
    if s["status_code"] == "FINISHED":
        break
    if s["status_code"] in ("ERROR", "EXPIRED"):
        raise RuntimeError(s)
    time.sleep(5)

# 3. Publish
pub = requests.post(f"{BASE}/{IG}/media_publish", data={
    "creation_id": container_id,
    "access_token": TOKEN,
}).json()
media_id = pub["id"]

# 4. Pull insights (after ~5 min for early numbers)
ins = requests.get(f"{BASE}/{media_id}/insights", params={
    "metric": "views,reach,likes,comments,shares,saved,total_interactions,ig_reels_video_view_total_time,ig_reels_avg_watch_time",
    "access_token": TOKEN,
}).json()
```

=======
---
name: instagram
description: "Use when any agent needs Instagram DM monitoring, comment scraping, session management, or bot detection avoidance for lead generation."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://developers.facebook.com/docs/instagram-api/"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "Instagram Graph API v22.0 (Meta Graph API rolling — v24.0 available) / Playwright automation"
sdk_version: "Playwright 1.58.0 (sync API) + Apify actors"
speed_category: "slow"
---

# Tool: Instagram

## What This Tool Does

Instagram access in EOS happens through three distinct paths, each serving a different purpose:

1. **Playwright browser automation** (`dm_monitor.py`) — reads DM inbox, detects replies, extracts messages
2. **Apify cloud scrapers** (`apify_scraper.py`) — scrapes comments from hashtags and competitor posts
3. **ManyChat** — DM automation for approved outreach campaigns (external, not coded in EOS)

The Meta Graph API exists but is not actively used for DM access — DM access requires approved Instagram Messaging permission which is not granted for EOS's use case. However, the Graph API IS the right path for Instagram **content publishing** (Reels, Stories, Feed posts), **insights/analytics**, **comment moderation**, and **Shopping product tagging** — all relevant to Lyfe Spectrum and Empyrean Studio content workflows. See the "Instagram Graph API — Publishing & Insights" section below.

**Cross-reference:** For Meta Graph API auth (long-lived tokens, system user tokens, app review, webhook subscriptions, the unified token zoo across Messenger/WhatsApp/Threads/Pages), see `/opt/OS/skills/tools/meta_graph_api/SKILL.md`. This skill focuses on Instagram-specific endpoints; meta_graph_api owns the auth/token/webhook mechanics shared across Meta surfaces.

## EOS Integration

### Path 1: DM Monitor — Playwright (`services/dm_monitor.py`)

**What it does:**
1. Launches headless Chromium inside Docker (os-monitor container)
2. Restores Instagram session from `storage_state` JSON
3. Navigates to DM inbox (`/direct/inbox/`)
4. Detects unread conversations via DOM selectors
5. Opens each unread thread, extracts messages
6. Feeds extracted messages to AI for sales conversation assistance
7. Takes diagnostic screenshots on failures

**Architecture:**
```
os-monitor container
  └── dm_monitor.py (90-second startup delay)
        └── sync_playwright()
              └── chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
                    └── browser.new_context(storage_state=..., user_agent=..., viewport=...)
                          └── context.new_page()
                                ├── page.goto("https://www.instagram.com/direct/inbox/")
                                ├── page.query_selector_all('a[href*="/direct/t/"]')
                                ├── Extract unread indicators
                                ├── Click thread → extract messages
                                └── context.storage_state(path=...) [save session]
```

**Key config:**
```yaml
# docker-compose.yml
os-monitor:
  shm_size: '2gb'  # Chromium needs this, default 64MB causes SIGBUS
  environment:
    - MONITOR_STARTUP_DELAY=90
    - INSTAGRAM_USE_PROXY=false
```

### Path 2: Comment Scraping — Apify (`services/apify_scraper.py`)

See `skills/tools/apify/SKILL.md` for full details.

**Flow:**
```
Cron → apify_scraper.py
  ├── Hashtag scraping (A/B rotation groups)
  │     → Instagram Hashtag Scraper actor → posts
  │     → Instagram Comment Scraper actor → comments
  │     → Bot/spam filter → priority classification
  │     → Save to 01_Inbox/raw_signals/
  └── Competitor scraping (5 accounts)
        → Instagram Profile Scraper actor → posts
        → Filter by ICP relevance (Whisper + Claude + keywords)
        → Comment scrape → filter → save
```

### Path 3: ManyChat (External)
ManyChat handles approved DM automation sequences.
Not coded in EOS — configured in ManyChat dashboard.
EOS receives booking notifications via Calendly webhooks when ManyChat DMs convert.

### Agents that use it
- DM Monitor (directly — Playwright)
- Scraper Service (directly — Apify)
- EA Agent (indirectly — reads DM Monitor reports)
- Outreach Agent (indirectly — uses signals from scraper)

## Authentication

### Playwright session (DM Monitor)
```python
# Session stored as Playwright storage_state JSON
# Contains both cookies AND localStorage (both required)
instagram_session.json = {
    "cookies": [...],
    "origins": [{
        "origin": "https://www.instagram.com",
        "localStorage": [...]
    }]
}

# Restore session
context = browser.new_context(storage_state="instagram_session.json")

# Save session after successful login
context.storage_state(path="instagram_session.json")
```

### Fresh login flow (when session expires)
```python
# 1. Navigate to root (NOT /accounts/login/ — returns blank from VPS)
page.goto("https://www.instagram.com/")

# 2. Fill credentials (use .type() with delay, NOT .fill() — React inputs)
page.locator('input[name="email"]').click()
page.locator('input[name="email"]').type(username, delay=80)
page.locator('input[name="pass"]').click()
page.locator('input[name="pass"]').type(password, delay=80)

# 3. Click login button
page.locator('button:has-text("Log in")').click()

# 4. Handle verification code (relayed via Telegram)
# 5. Dismiss "Save Info" and "Not Now" prompts
# 6. Save session
context.storage_state(path="instagram_session.json")
```

### Environment variables
| Variable | Purpose |
|----------|---------|
| `INSTAGRAM_USERNAME` | Login email/username |
| `INSTAGRAM_PASSWORD` | Login password |
| `INSTAGRAM_USE_PROXY` | `true` to route through Apify RESIDENTIAL proxy |
| `APIFY_PROXY_PASSWORD` | Proxy auth when proxy enabled |
| `MONITOR_STARTUP_DELAY` | Seconds to wait before first check (default 90) |

## Quick Reference

### Check DM inbox
```python
page.goto("https://www.instagram.com/direct/inbox/", wait_until="domcontentloaded")
page.wait_for_selector("div[role='main']", timeout=60000)
threads = page.query_selector_all('a[href*="/direct/t/"]')
```

### Detect unread conversations
```python
# Look for unread indicators (blue dot, bold text)
for thread in threads:
    unread_indicator = thread.query_selector('[data-testid="unread"]')
    # OR check for bold font-weight on thread preview text
```

### Extract messages from thread
```python
thread.click()
page.wait_for_load_state("domcontentloaded")
messages = page.query_selector_all('div[dir="auto"]')
for msg in messages:
    text = msg.inner_text()
```

### Bot detection avoidance
```python
# Human-like timing
import random
time.sleep(random.uniform(2, 5))

# Character-by-character typing (NOT fill())
page.locator('input').type("text", delay=80)

# Desktop Chrome UA (NOT mobile — causes blank page)
user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36...'

# Viewport matches real browser
viewport = {'width': 1280, 'height': 800}
```

## Gotchas

### Direct /accounts/login/ URL returns blank page (ACTIVE)
Instagram serves a blank page when `/accounts/login/` is accessed from VPS IPs.
**Fix:** Always navigate to root `https://www.instagram.com/` — login form renders correctly.

### Cookie-only session restore triggers bot detection (RESOLVED)
Using only `context.add_cookies()` left sessions incomplete — localStorage was missing.
**Fix:** Use `storage_state()` which saves both cookies AND localStorage.

### React inputs reject fill() (ACTIVE)
Instagram's React-controlled inputs reject synthetic `fill()` events.
**Fix:** Use `click()` + `type(text, delay=80)` for character-by-character input.

### Chromium SIGBUS in Docker (RESOLVED)
Default Docker `/dev/shm` is 64MB. Chromium exceeds this during rendering.
**Fix:** `shm_size: '2gb'` in docker-compose.yml.

### Startup OOM from rapid restart loops (RESOLVED)
Docker `restart: always` caused rapid Chromium restarts (~700MB each), exhausting RAM.
**Fix:** 90-second startup delay (`MONITOR_STARTUP_DELAY=90`) + stale session cleanup.

### Mobile User-Agent causes blank page (RESOLVED)
Mobile Safari UA causes Instagram to serve app-redirect blank page in headless Chromium.
**Fix:** Desktop Chrome UA confirmed to render login form correctly.

### Instagram selector changes break DM extraction (INTERMITTENT)
Instagram updates DOM structure without notice. Selectors for thread links, unread indicators, and message containers break.
**Detection:** DM Monitor reports 0 threads despite known unread messages.
**Fix:** Update selectors in `dm_monitor.py`, test with diagnostic screenshots.

### Apify RESIDENTIAL proxy 403 (ACTIVE)
Proxy credits are separate from compute units. 403 when depleted.
**Fix:** `INSTAGRAM_USE_PROXY=false` until credits refill.

See references/best_practices.md for full session management patterns, anti-detection strategies, and selector reference.

---

## Instagram Graph API — Publishing & Insights (2026-04-06 expansion)

This section covers the Instagram-specific Graph API endpoints. Auth, long-lived tokens, system user tokens, webhook subscription mechanics, and app review live in `skills/tools/meta_graph_api/` — do not duplicate here.

**Conceptual model:** All endpoints below assume an **Instagram Business account** linked to a Facebook Page, with a Page access token (or System User token) that has `instagram_basic`, `instagram_content_publish`, `instagram_manage_insights`, `instagram_manage_comments`, `pages_read_engagement`, and (for Shopping) `instagram_shopping_tag_products` scopes. The IG user ID (`{ig-user-id}`) is the IG Business Account ID, NOT the username. Resolve via `GET /{page-id}?fields=instagram_business_account`.

Creator accounts are NOT supported for content publishing API — Business only.

### Content Publishing — Two-step container flow

All publishing (Feed, Reels, Stories, Carousels) uses a two-step pattern:

```
1. POST /{ig-user-id}/media         → returns container_id
2. POST /{ig-user-id}/media_publish  → creation_id=container_id → returns published media id
```

Containers expire after 24 hours. For video/Reels containers, poll `GET /{container-id}?fields=status_code` until `FINISHED` before publishing (typical wait 30-90s). Status codes: `IN_PROGRESS`, `FINISHED`, `ERROR`, `EXPIRED`, `PUBLISHED`.

### Reels publishing

```http
POST /{ig-user-id}/media
  ?media_type=REELS
  &video_url=https://cdn.example.com/reel.mp4
  &caption=...
  &cover_url=https://cdn.example.com/cover.jpg
  &share_to_feed=true
  &collaborators=["partner_ig_username"]
  &thumb_offset=1000        # ms into video for thumbnail
  &audio_name=...
  &access_token=...
```

Then poll status_code → `FINISHED`, then:
```http
POST /{ig-user-id}/media_publish?creation_id={container_id}&access_token=...
```

**Reels constraints (current):**
- Aspect ratio 9:16 required for Reels tab eligibility
- Duration 5–90 seconds for Reels tab eligibility (API accepts up to 15 min but anything outside 5–90s publishes as regular video)
- Video host: video uploads use `rupload.facebook.com`, not `graph.facebook.com`
- Rate limit: 100 API-published posts per IG account per rolling 24h (counts Reels + feed + carousels + stories together)
- Container is `media_type=REELS` but `GET /{media-id}?fields=media_type` returns `VIDEO`. Use `media_product_type` field to confirm REELS designation.

### Stories publishing

```http
POST /{ig-user-id}/media
  ?media_type=STORIES
  &image_url=...                # OR video_url for video stories
  &access_token=...
```
Then `media_publish`. Stories support image and video. No caption parameter — stickers/text overlays are not supported via API (publish raw media only).

### Carousel publishing (children pattern)

```
1. Create child containers (one per item, no caption):
   POST /{ig-user-id}/media?media_type=IMAGE&image_url=...&is_carousel_item=true
2. Create parent carousel container:
   POST /{ig-user-id}/media?media_type=CAROUSEL&children=child_id_1,child_id_2,...&caption=...
3. Publish parent.
```

### Collaborators API

`collaborators` parameter on the Feed/Reel media container accepts an array of IG usernames. The collaborator receives an invitation in their app and must accept before the post appears on their grid. Only available for Reels and feed video/image posts (not Stories).

### Mentions & user tags

- **Photo tags (image posts):** `user_tags` parameter — array of `{username, x, y}` (x/y = 0.0–1.0 normalized).
- **Caption mentions:** `@username` in caption auto-resolves and sends notification.
- **Story mentions:** Not supported via Content Publishing API (Story sticker mentions are app-only).
- **Mention webhooks:** Subscribe to the `mentions` field on the Instagram webhook to receive notifications when your account is @-mentioned in captions/comments. Lookup payload via `GET /{ig-user-id}?fields=mentioned_media{caption,media_type,id}`.

### Insights API

**Account-level (`GET /{ig-user-id}/insights`):**
- Metrics: `reach`, `impressions` (deprecated April 2025 — use `views`), `profile_views`, `accounts_engaged`, `total_interactions`, `likes`, `comments`, `shares`, `saves`, `replies`, `follows_and_unfollows`, `profile_links_taps`, `website_clicks`, `email_contacts`, `phone_call_clicks`, `text_message_clicks`, `get_directions_clicks`.
- Required `metric_type=total` for v18.0+ on most metrics. Use `period=day` and `since`/`until` Unix timestamps.
- Demographic breakdowns: `follower_demographics`, `engaged_audience_demographics`, `reached_audience_demographics` with `breakdown=age,gender,city,country`.

**Media-level (`GET /{ig-media-id}/insights`):**
- Feed image/carousel: `reach`, `likes`, `comments`, `shares`, `saved`, `total_interactions`, `views`, `profile_visits`, `profile_activity`, `follows`.
- Reels: `reach`, `likes`, `comments`, `shares`, `saved`, `total_interactions`, `views` (replaces `plays` and `ig_reels_aggregated_all_plays_count` post-April-2025), `ig_reels_video_view_total_time` (ms), `ig_reels_avg_watch_time` (ms).
- Stories: `reach`, `views`, `replies`, `shares`, `total_interactions`, `profile_visits`, `follows`, `navigation` (with breakdown into `tap_back`, `tap_forward`, `tap_exit`, `swipe_forward`).

**April 2025 deprecation:** `impressions`, `plays`, `clips_replays_count`, `ig_reels_aggregated_all_plays_count` → unified into `views`. Update any code referencing those metric names.

### Comment moderation

- `GET /{ig-media-id}/comments` — list comments on a media object.
- `GET /{ig-comment-id}/replies` — list replies to a comment.
- `POST /{ig-media-id}/comments?message=...` — reply on the post.
- `POST /{ig-comment-id}/replies?message=...` — reply to a comment.
- `DELETE /{ig-comment-id}` — delete a comment.
- `POST /{ig-comment-id}?hide=true` — hide/unhide a comment.
- Webhook field `comments` delivers new-comment events; subscribe via meta_graph_api skill's webhook flow.

### Shopping — Product tagging (Lyfe Spectrum)

Requires an approved Instagram Shop linked to a Facebook Catalog plus `instagram_shopping_tag_products` permission.

- **Product search:** `GET /{ig-user-id}/available_catalogs` → catalog id; `GET /{ig-user-id}/catalog_product_search?q=...` → product ids eligible for tagging.
- **Image post with tags:** add `product_tags=[{"product_id":"...","x":0.5,"y":0.5}]` to the `media` container call.
- **Video/Reel post with tags:** `product_tags=[{"product_id":"..."}]` (no x/y — applied as collection).
- **Carousel:** product tags go on the child container at creation time, not the parent.
- **Storefront eligibility:** product must be `approved` status in the catalog. Check `GET /{product-id}?fields=review_status`.

### Quick reference — common Reels publish snippet

```python
import requests, time

IG = "<ig-user-id>"
TOKEN = "<page-access-token>"
BASE = "https://graph.facebook.com/v22.0"

# 1. Create container
r = requests.post(f"{BASE}/{IG}/media", data={
    "media_type": "REELS",
    "video_url": "https://cdn.example.com/reel.mp4",
    "caption": "Built different. #LifeMaxing",
    "share_to_feed": "true",
    "access_token": TOKEN,
}).json()
container_id = r["id"]

# 2. Poll until FINISHED
while True:
    s = requests.get(f"{BASE}/{container_id}",
        params={"fields": "status_code", "access_token": TOKEN}).json()
    if s["status_code"] == "FINISHED":
        break
    if s["status_code"] in ("ERROR", "EXPIRED"):
        raise RuntimeError(s)
    time.sleep(5)

# 3. Publish
pub = requests.post(f"{BASE}/{IG}/media_publish", data={
    "creation_id": container_id,
    "access_token": TOKEN,
}).json()
media_id = pub["id"]

# 4. Pull insights (after ~5 min for early numbers)
ins = requests.get(f"{BASE}/{media_id}/insights", params={
    "metric": "views,reach,likes,comments,shares,saved,total_interactions,ig_reels_video_view_total_time,ig_reels_avg_watch_time",
    "access_token": TOKEN,
}).json()
```

>>>>>>> Stashed changes
