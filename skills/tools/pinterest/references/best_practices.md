# Pinterest — Creator-Level Best Practices
Source: developers.pinterest.com/docs/api/v5, business.pinterest.com, Pinterest Newsroom, Pinterest Predicts 2026, help.pinterest.com
API Version: v5 (current stable as of 2026-04)
SDK Version: Pinterest publishes an OpenAPI spec; community SDKs include `pinterest-python-generated` (1.x) and `@pinterest/sdk` (Node, generated). EOS uses direct REST via `httpx`.
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## Authentication

Pinterest API v5 uses **OAuth 2.0 Authorization Code grant**, with optional
PKCE for public clients. There is no API key, no app token, no service
account — every API call is made on behalf of a user (almost always your own
business account in EOS's case).

### Account requirement

Personal Pinterest accounts CANNOT use the API. Calls return `403` with a
generic permission error. Convert at business.pinterest.com (free, no review,
no spend required). The conversion preserves boards, pins, followers — it
just unlocks Analytics, the API, and Ads Manager.

### App registration

1. Go to developers.pinterest.com → "My apps" → "Connect app".
2. Provide app name, description, redirect URIs (one per environment), and
   the contact email.
3. Pinterest issues an **App ID** (public, OK in client code) and an
   **App Secret** (server-only, store in `eos_ai/.env`).
4. The app starts in **Trial mode**. Trial mode allows full API surface but
   caps reach: pins created via API may not be distributed to non-following
   users until the app passes Pinterest review.
5. Submit for review when ready for production. Review typically takes 5-10
   business days. Required: privacy policy URL, terms URL, demo video showing
   the integration, and a written description of every requested scope.

### Scopes

Request only what you actually need — Pinterest review rejects over-scoped
apps. Common scopes:

| Scope                | What it grants                                              |
|----------------------|-------------------------------------------------------------|
| `user_accounts:read` | Read your business profile, account stats                   |
| `boards:read`        | List boards, sections, board pins                           |
| `boards:write`       | Create, update, delete boards and sections                  |
| `pins:read`          | Read pins (own and public)                                  |
| `pins:write`         | Create, update, delete pins (own boards only)               |
| `catalogs:read`      | Read product catalogs and items                             |
| `catalogs:write`     | Create catalog feeds, manage products                       |
| `ads:read`           | Read ad campaign data and ad-level analytics                |
| `ads:write`          | Manage campaigns, ad groups, ads (NOT used in EOS organic)  |

EOS organic stack: `user_accounts:read,boards:read,boards:write,pins:read,pins:write,catalogs:read,catalogs:write`.

### Authorization code flow

```
GET https://www.pinterest.com/oauth/
  ?client_id={APP_ID}
  &redirect_uri={URLENCODED_REDIRECT}
  &response_type=code
  &scope=boards:read,boards:write,pins:read,pins:write,user_accounts:read
  &state={CSRF_NONCE}
```

User approves → Pinterest redirects to your redirect URI with `?code=...&state=...`.

```bash
curl -s -u "${APP_ID}:${APP_SECRET}" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "code=${CODE}" \
  --data-urlencode "redirect_uri=${REDIRECT_URI}" \
  https://api.pinterest.com/v5/oauth/token
```

Response:

```json
{
  "access_token": "pina_...",
  "refresh_token": "pinr_...",
  "token_type": "bearer",
  "expires_in": 2592000,
  "refresh_token_expires_in": 31536000,
  "scope": "boards:read,..."
}
```

Access token TTL is 30 days. Refresh tokens have historically been 60 days but
recent updates extended to ~1 year for new apps — verify the
`refresh_token_expires_in` field on every refresh and persist accordingly.

### Refresh

```bash
curl -s -u "${APP_ID}:${APP_SECRET}" \
  -d "grant_type=refresh_token" \
  -d "refresh_token=${REFRESH_TOKEN}" \
  https://api.pinterest.com/v5/oauth/token
```

**Refresh tokens rotate.** Each refresh response contains a new
`refresh_token`. You MUST persist it or lose auth. EOS pattern: write to a
Neon `pinterest_tokens` row with `(access_token, refresh_token, expires_at,
refreshed_at)` after every refresh.

### EOS auth bootstrap

```python
# scripts/pinterest_auth_bootstrap.py — run once interactively to seed Neon
import os, secrets, urllib.parse, webbrowser, httpx
from dotenv import load_dotenv
load_dotenv("/opt/OS/eos_ai/.env")

APP_ID = os.environ["PINTEREST_APP_ID"]
APP_SECRET = os.environ["PINTEREST_APP_SECRET"]
REDIRECT = "http://localhost:8765/cb"
SCOPES = "user_accounts:read,boards:read,boards:write,pins:read,pins:write,catalogs:read,catalogs:write"
state = secrets.token_urlsafe(16)
url = (
    "https://www.pinterest.com/oauth/?"
    + urllib.parse.urlencode({
        "client_id": APP_ID, "redirect_uri": REDIRECT,
        "response_type": "code", "scope": SCOPES, "state": state,
    })
)
print(url)
# After user pastes code:
code = input("paste code: ").strip()
r = httpx.post(
    "https://api.pinterest.com/v5/oauth/token",
    auth=(APP_ID, APP_SECRET),
    data={"grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT},
    timeout=30,
)
r.raise_for_status()
tokens = r.json()
# Persist to Neon: pinterest_tokens(account, access_token, refresh_token, expires_at)
print(tokens)
```

## Core Operations with Exact Signatures

All endpoints are rooted at `https://api.pinterest.com/v5`. All request bodies
are JSON. All responses are JSON. Auth header: `Authorization: Bearer
{access_token}`.

### User accounts

```
GET    /user_account
GET    /user_account/analytics?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
         &from_claimed_content=BOTH&pin_format=ALL
         &app_types=ALL&metric_types=IMPRESSION,SAVE,PIN_CLICK,OUTBOUND_CLICK
         &split_field=NO_SPLIT
GET    /user_account/analytics/top_pins
GET    /user_account/analytics/top_video_pins
GET    /user_account/websites
POST   /user_account/websites          # claim a domain
DELETE /user_account/websites/{website}
```

### Boards

```
GET    /boards?page_size=25&bookmark={cursor}&privacy=ALL
POST   /boards
       body: {"name": "...", "description": "...", "privacy": "PUBLIC"|"PROTECTED"|"SECRET"}
GET    /boards/{board_id}
PATCH  /boards/{board_id}
DELETE /boards/{board_id}
GET    /boards/{board_id}/pins?page_size=25&bookmark={cursor}
GET    /boards/{board_id}/sections
POST   /boards/{board_id}/sections     body: {"name": "..."}
PATCH  /boards/{board_id}/sections/{section_id}
DELETE /boards/{board_id}/sections/{section_id}
GET    /boards/{board_id}/sections/{section_id}/pins
```

### Pins

```
GET    /pins?page_size=25&bookmark={cursor}&pin_filter=...&include_protected_pins=false
POST   /pins
       body shape (image_url):
       {
         "board_id": "string",
         "board_section_id": "string",          # optional
         "title": "string (max 100)",
         "description": "string (max 800)",
         "alt_text": "string (max 500)",
         "link": "https://...",                 # outbound destination
         "dominant_color": "#RRGGBB",           # optional, helps load
         "media_source": {
           "source_type": "image_url",          # or image_base64, image_url_video_cover, video_id, multiple_image_urls, multiple_image_base64, pin_id
           "url": "https://..."
         },
         "parent_pin_id": "string",             # for repins
         "note": "internal note (max 500)"
       }
GET    /pins/{pin_id}
PATCH  /pins/{pin_id}
DELETE /pins/{pin_id}
GET    /pins/{pin_id}/analytics?start_date=...&end_date=...
         &metric_types=IMPRESSION,SAVE,PIN_CLICK,OUTBOUND_CLICK,VIDEO_MRC_VIEW,...
         &app_types=ALL&split_field=NO_SPLIT
POST   /pins/{pin_id}/save              body: {"board_id": "...", "board_section_id": "..."}
```

### Media (for video and large image upload)

```
POST   /media                # register an upload, returns media_id + presigned upload params
       body: {"media_type": "video"}
       response: {
         "media_id": "...",
         "media_type": "video",
         "upload_url": "https://...",
         "upload_parameters": {
           "x-amz-...": "...",
           "key": "..."
         }
       }
# Then POST multipart/form-data to upload_url with all upload_parameters as
# fields plus the file as "file".
GET    /media/{media_id}     # poll status until status == "succeeded"
GET    /media?page_size=25&bookmark=...
```

Then create the pin referencing the `media_id`:

```json
{
  "board_id": "...",
  "title": "...",
  "media_source": {
    "source_type": "video_id",
    "cover_image_url": "https://...",
    "media_id": "..."
  }
}
```

### Catalogs (Shopping)

```
GET    /catalogs                                   # list catalogs
POST   /catalogs                                   # create a RETAIL catalog
GET    /catalogs/feeds?catalog_id=...
POST   /catalogs/feeds                             # create a feed
       body: {
         "name": "lyfe_spectrum_main",
         "format": "XML"|"TSV"|"CSV",
         "catalog_type": "RETAIL"|"HOTEL"|"CREATIVE_ASSETS",
         "location": "https://lyfespectrum.com/feeds/pinterest.xml",
         "default_country": "US",
         "default_locale": "en-US",
         "default_currency": "USD",
         "credentials": {"username":"...","password":"..."},   # optional basic auth
         "preferred_processing_schedule": {"time": "06:00", "timezone": "America/Los_Angeles"}
       }
PATCH  /catalogs/feeds/{feed_id}
DELETE /catalogs/feeds/{feed_id}
GET    /catalogs/feeds/{feed_id}/processing_results
GET    /catalogs/items?catalog_id=...&item_ids=...&country=US&language=EN
GET    /catalogs/product_groups?catalog_id=...
POST   /catalogs/product_groups
PATCH  /catalogs/product_groups/{product_group_id}
DELETE /catalogs/product_groups/{product_group_id}
GET    /catalogs/product_groups/{product_group_id}/products
```

### Search (limited; primarily for own content)

```
GET    /search/boards?query=...&bookmark=...           # search YOUR boards
GET    /search/pins?query=...&bookmark=...             # search YOUR pins
GET    /search/partner/pins/about?term=...             # partner-only ad signals
```

There is no public "search all of Pinterest" endpoint via the v5 API. Visual
search and full catalog search are reserved for Ads partners.

### Analytics quick reference

Metric type enums (case-sensitive):
`IMPRESSION`, `SAVE`, `PIN_CLICK`, `OUTBOUND_CLICK`, `VIDEO_MRC_VIEW`,
`VIDEO_AVG_WATCH_TIME`, `VIDEO_V50_WATCH_TIME`, `QUARTILE_95_PERCENT_VIEW`,
`VIDEO_10S_VIEW`, `ENGAGEMENT`, `ENGAGEMENT_RATE`, `PIN_CLICK_RATE`,
`OUTBOUND_CLICK_RATE`, `SAVE_RATE`.

Split fields: `NO_SPLIT`, `APP_TYPE`, `OWNED_CONTENT`, `PIN_FORMAT`,
`PRODUCT_CATEGORY`, `PLACEMENT`.

## Pagination Patterns

Pinterest uses **bookmark-based cursor pagination**. Every list endpoint
returns:

```json
{
  "items": [...],
  "bookmark": "Y2JveD0xJmJvb2..."     // null/absent on last page
}
```

Iterate with the bookmark, never with offsets:

```python
def iter_all(client, path, params=None):
    params = dict(params or {})
    while True:
        r = client.get(path, params=params)
        r.raise_for_status()
        body = r.json()
        for it in body.get("items", []):
            yield it
        bm = body.get("bookmark")
        if not bm:
            return
        params["bookmark"] = bm
```

`page_size` defaults to 25, max 100 for most endpoints. Use 100 to minimize
round-trips. Bookmarks are opaque — never parse them.

## Rate Limits

As of 2026-04 (verify in dev portal — Pinterest does not always publish exact
numbers):

- **Default user-token quota:** ~1000 requests / hour per access token, per
  app. This is the most common limit you'll hit.
- **App-level burst:** ~10 requests / second per app. Pinterest enforces with
  short 429 windows.
- **Trial apps:** lower per-account caps (sometimes ~100/hr) until reviewed.
- **Catalog feed processing:** 1 active processing run per feed at a time;
  feeds rate-limited to 4 manual triggers per day.
- **Media upload:** no documented hard cap, but uploads count against the
  user-token quota AND the upload S3 endpoint enforces its own rate.
- **Analytics endpoints:** date ranges capped at 90 days per call. Larger
  windows must be chunked.

Rate-limit responses:

```
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1712393100
Retry-After: 47
```

EOS pattern: respect `Retry-After`, exponential backoff with jitter on 429,
hard-fail on 5+ consecutive 429s and emit a Discord alert.

```python
import time, random, httpx
def call_with_backoff(client, method, path, **kw):
    for attempt in range(5):
        r = client.request(method, path, **kw)
        if r.status_code == 429:
            sleep = int(r.headers.get("Retry-After", "30"))
            time.sleep(sleep + random.uniform(0, 5))
            continue
        return r
    raise RuntimeError(f"Pinterest 429 wall on {method} {path}")
```

## Error Codes and Recovery

| HTTP | `code` field   | Meaning                                  | Recovery                                 |
|------|----------------|------------------------------------------|------------------------------------------|
| 400  | 1, 2           | Validation error (bad field, missing)    | Read `message`; do NOT retry             |
| 401  | 3              | Invalid or expired access token          | Refresh token, retry once                |
| 401  | 4              | Refresh token invalid/expired            | Re-run interactive auth flow             |
| 403  | 7              | Insufficient scope                       | Re-auth with extra scope                 |
| 403  | 8              | Personal account (not business)          | Convert to business; do NOT retry        |
| 403  | 12             | Trial mode reach cap                     | Submit app for review                    |
| 404  | 11             | Pin/board not found OR not yours         | Check IDs; do NOT retry                  |
| 409  | 21             | Duplicate (e.g. board name conflict)     | Read existing or rename                  |
| 415  | -              | Unsupported media type                   | Check Content-Type and image format      |
| 422  | 18             | Image URL unreachable                    | Verify URL public + HTTPS + valid image  |
| 422  | 19             | Video failed processing                  | Re-encode to spec, retry once            |
| 429  | -              | Rate limited                             | Honor `Retry-After`, exponential backoff |
| 500  | -              | Pinterest internal                       | Retry with backoff up to 3 attempts      |
| 503  | -              | Service unavailable                      | Retry after 30-60s                       |

Standard error envelope:

```json
{
  "code": 7,
  "message": "Authentication failed."
}
```

EOS pattern: any 4xx that isn't 401/429 should be logged with the full request
body and never retried — the request itself is wrong.

## SDK Idioms

Pinterest publishes an OpenAPI spec but **does not maintain official
hand-written SDKs**. Generated clients exist:

- `pinterest-python-generated` (PyPI) — auto-generated, ~OK but verbose
- `@pinterest-sdk/pinterest-rest-client` (npm) — generated TS

EOS uses **direct REST via `httpx`** because:

1. The API surface is small enough that a thin wrapper costs less than
   learning a generated client's quirks.
2. Generated clients break on every spec rev.
3. Direct REST gives full control over rate-limit handling.

Canonical EOS client:

```python
# eos_ai/pinterest_client.py
import os, time, random, json, httpx
from typing import Iterator
from dotenv import load_dotenv

load_dotenv("/opt/OS/eos_ai/.env")

class PinterestClient:
    BASE = "https://api.pinterest.com/v5"

    def __init__(self, access_token: str | None = None):
        self.token = access_token or os.environ["PINTEREST_ACCESS_TOKEN"]
        self.http = httpx.Client(
            base_url=self.BASE,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "User-Agent": "EOS/1.0 (+https://antonyfmunoz.com)",
            },
            timeout=30,
        )

    def request(self, method: str, path: str, **kw) -> dict:
        for attempt in range(5):
            r = self.http.request(method, path, **kw)
            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After", "30"))
                time.sleep(wait + random.uniform(0, 3))
                continue
            if r.status_code >= 500 and attempt < 3:
                time.sleep(2 ** attempt)
                continue
            if r.status_code >= 400:
                raise RuntimeError(f"Pinterest {r.status_code}: {r.text}")
            return r.json() if r.content else {}
        raise RuntimeError(f"Pinterest exhausted retries on {method} {path}")

    def list_boards(self) -> Iterator[dict]:
        params = {"page_size": 100}
        while True:
            body = self.request("GET", "/boards", params=params)
            for b in body.get("items", []):
                yield b
            bm = body.get("bookmark")
            if not bm:
                return
            params["bookmark"] = bm

    def create_pin(self, board_id: str, title: str, description: str,
                   image_url: str, link: str, alt_text: str | None = None,
                   board_section_id: str | None = None) -> dict:
        body = {
            "board_id": board_id,
            "title": title[:100],
            "description": description[:800],
            "link": link,
            "media_source": {"source_type": "image_url", "url": image_url},
        }
        if alt_text:
            body["alt_text"] = alt_text[:500]
        if board_section_id:
            body["board_section_id"] = board_section_id
        return self.request("POST", "/pins", json=body)

    def pin_analytics(self, pin_id: str, start: str, end: str) -> dict:
        return self.request(
            "GET", f"/pins/{pin_id}/analytics",
            params={
                "start_date": start, "end_date": end,
                "metric_types": "IMPRESSION,SAVE,PIN_CLICK,OUTBOUND_CLICK",
            },
        )
```

## Anti-Patterns

- **Posting the same image to many boards in a short window.** Pinterest used
  to reward this; in 2026 it's a spam signal. One pin per board, per concept,
  per ~7 days max.
- **Hashtag stuffing the description.** Hashtags are ignored for ranking and
  hashtag-heavy descriptions look spammy. Use natural-language keyword
  sentences instead.
- **Generic board names** ("Outfits," "Inspo," "Stuff"). The board name is a
  ranking signal — be specific and keyword-driven.
- **Ignoring `alt_text`.** Alt text is read by Pinterest's accessibility layer
  AND its visual model. Skipping it leaves ranking on the table.
- **Treating Pinterest like Instagram** — caption-first, follower-driven, daily
  cadence. Pinterest is a search engine; "going viral" happens months later
  through SEO, not on day one.
- **Using `link` to redirect through trackers Pinterest can't follow.**
  Pinterest crawls the destination URL. If your link is a tracking redirect
  that returns 302→302→200, the crawler may give up and the pin loses
  Rich Pin treatment.
- **Catalog-only strategy.** Auto-generated Product Pins are necessary but
  insufficient. They have lower engagement than handcrafted lifestyle pins
  because they look like ads. Mix handcrafted lookbook pins on top.
- **Not persisting refresh tokens after rotation.** Most common dev outage.
- **Polling analytics for new pins on day 1.** Data is 24-48hr lagged; you'll
  see zeros and falsely conclude failure.

## Data Model

```
User (business account)
 └─ Boards
     ├─ Board Sections (1 level deep, optional)
     │   └─ Pins
     └─ Pins (directly on board if no section)

Catalog (separate top-level entity)
 └─ Feeds (one per file source, scheduled or manual)
     └─ Catalog Items (products from feed)
         └─ Product Groups (rule-based bundles for ads/distribution)
```

**IDs:** all IDs are opaque numeric strings. Never assume length or
arithmetic. A pin ID looks like `"998765432109876543"` and is stable for the
life of the pin.

**Pin entity (response):**

```json
{
  "id": "998765432109876543",
  "created_at": "2026-04-06T10:00:00Z",
  "link": "https://lyfespectrum.com/...",
  "title": "...",
  "description": "...",
  "alt_text": "...",
  "board_id": "...",
  "board_section_id": null,
  "board_owner": {"username": "lyfespectrum"},
  "media": {
    "media_type": "image",
    "images": {
      "150x150": {"url": "...", "width": 150, "height": 150},
      "400x300": {"url": "...", "width": 400, "height": 300},
      "600x":    {"url": "...", "width": 600, "height": 900},
      "1200x":   {"url": "...", "width": 1200, "height": 1800}
    }
  },
  "parent_pin_id": null,
  "is_owner": true,
  "pin_metrics": null,
  "dominant_color": "#1a1a1a"
}
```

**Board entity:**

```json
{
  "id": "...",
  "name": "All Black Tactical Outfits for Men",
  "description": "...",
  "privacy": "PUBLIC",
  "follower_count": 0,
  "pin_count": 47,
  "media": {"image_cover_url": "...", "pin_thumbnail_urls": [...]},
  "owner": {"username": "lyfespectrum"},
  "created_at": "2026-01-15T10:00:00Z",
  "board_pins_modified_at": "2026-04-06T09:00:00Z"
}
```

**Catalog item:**

```json
{
  "item_id": "BLACK-BOMBER-M",
  "pin_id": "...",
  "metadata": {
    "title": "Tactical Black Bomber Jacket",
    "description": "...",
    "link": "https://lyfespectrum.com/products/black-bomber",
    "image_link": "https://cdn.../black-bomber.jpg",
    "availability": "in stock",
    "price": "189.00 USD",
    "brand": "Lyfe Spectrum",
    "google_product_category": "Apparel & Accessories > Clothing > Outerwear > Coats & Jackets"
  }
}
```

## Webhooks and Events

**Pinterest does not currently expose general-purpose webhooks** for organic
content events (new save, new follow, pin click). What it DOES expose:

- **Catalog feed processing notifications** — set `notifications_emails` on a
  feed to receive parse-completion mail. Programmatic equivalent: poll
  `/catalogs/feeds/{feed_id}/processing_results`.
- **Conversions API webhook (Ads only)** — server-side event ingestion for
  ad attribution; out of scope for organic EOS.
- **OAuth disconnect callback** — when a user revokes your app, Pinterest
  posts to your registered redirect URI. Handle gracefully (mark token dead
  in Neon).

EOS workaround for "did anything change?" — schedule an analytics pull cron
that diffs metric snapshots in Neon. Cheap, reliable, no webhooks needed.

## Limits

| Resource                    | Limit                                                |
|-----------------------------|------------------------------------------------------|
| Pin title                   | 100 characters                                       |
| Pin description             | 800 characters                                       |
| Pin alt text                | 500 characters                                       |
| Pin board note              | 500 characters                                       |
| Boards per account          | 2,000 (soft limit; rarely hit)                       |
| Pins per board              | 200,000                                              |
| Pins per account            | 200,000 lifetime                                     |
| Sections per board          | 500                                                  |
| Image min dimensions        | 600 x 900 (effectively); 200 x 300 hard floor       |
| Image recommended           | 1000 x 1500 (2:3) — Pinterest's documented sweet spot|
| Image max file size         | 32 MB (PNG/JPG)                                      |
| Image aspect ratio range    | 2:3 ideal; 1:2.1 min, longer gets cropped in feed    |
| Video min duration          | 4 seconds                                            |
| Video max duration          | 15 minutes                                           |
| Video max file size         | 2 GB (via /media upload)                             |
| Video min resolution        | 240p (1080p strongly recommended)                    |
| Video aspect ratio          | 9:16 (vertical) or 1:1; 16:9 allowed but suppressed  |
| Idea Pin pages              | 1 to 20 pages                                        |
| Catalog items per feed      | ~20M (hard cap rarely a concern)                     |
| Catalog feed file size      | 8 GB                                                 |
| API rate limit (default)    | ~1000 requests / hour per user token per app         |

## Cost Model

**The API itself is free.** No per-call fees, no quotas you must pay for, no
seat licenses. The Pinterest cost surface is:

- **Ads spend** — paid promotion via Ads Manager. Out of scope for EOS organic
  strategy except for retargeting top organic performers.
- **Catalog ingestion is free** — feeds host on your own server, Pinterest
  pulls them.
- **Trial mode opportunity cost** — until your app is reviewed, organic reach
  on API-created pins is capped, which can effectively cost you traffic.
- **Domain verification is free** but takes time and is required for Rich
  Pin treatment.
- **Conversions API (CAPI)** is free but requires engineering time to
  instrument server-side events.

EOS cost: **$0/month** for the organic stack. Time cost: ~2 hours initial
setup (auth, app review submission, domain verification) + ~30 min/week
maintenance (token refresh monitoring, weekly analytics pulls).

## Version Pinning

API version is part of the URL: `/v5/...`. There is no `Accept-Version`
header dance. EOS pins to `v5` explicitly via the `BASE` constant in
`PinterestClient`. When Pinterest releases v6 (no announcement as of
2026-04), pin both clients side-by-side and migrate per-endpoint.

Pinterest deprecates aggressively:

- v3 was deprecated in 2021
- v4 was deprecated in 2022
- v5 launched Q4 2022, current stable

When a `v5` endpoint is deprecated, Pinterest emits a `Deprecation` and `Sunset`
HTTP header on responses. Log these centrally:

```python
def warn_deprecation(r):
    if "Sunset" in r.headers:
        print(f"DEPRECATED: {r.request.url} sunsets {r.headers['Sunset']}")
```

OpenAPI spec: https://developers.pinterest.com/docs/api/v5/ — download the
JSON to pin a known-good version of the schema. Re-fetch quarterly.

EOS convention: every Pinterest-touching module imports from
`eos_ai.pinterest_client`, which is the only file that knows the base URL
and version. To migrate: change one constant, run import smoke test, run
integration smoke test, deploy.

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

Pinterest is a **discovery engine for future intent**. The product team
designs explicitly against the dopamine-loop / outrage-engagement model that
defines Instagram, TikTok, and X. The thesis: people come to Pinterest to
PLAN — a wedding, a kitchen renovation, a wardrobe, a meal — and the platform
that helps them plan best wins long-term retention even if it loses
session-time-per-day.

**Tradeoffs this design forces:**

1. **No real-time feed.** There is no chronological "what's happening now."
   Every surface is curated by relevance to long-tail intent. Cost: zero
   newsjacking value. Benefit: pins compound for years.
2. **No comments-as-engagement-driver.** Comments exist but are de-emphasized.
   Saves are the dominant engagement signal because saves correlate with
   intent to act, not intent to argue.
3. **Aggressive de-platforming of low-quality clickbait.** Pinterest's spam
   team is more aggressive than Instagram's. The penalty for "Buzzfeed
   listicle with 17 ads" pins is severe and sometimes account-level.
4. **No verified-creator caste system.** Verification exists for merchants
   (domain claim) but there is no blue check that boosts your reach. Reach is
   earned per-pin, not per-account.
5. **Creators paid to build the catalog, not to keep posting.** Pinterest's
   creator monetization story is weak compared to YouTube or TikTok — there's
   no Creator Fund that pays per-impression. Pinterest's bet is that creators
   come for the traffic to their own businesses, not for direct platform
   payouts.

**What this means for EOS:**

- Don't optimize for cadence. Optimize for SEO-grade quality on every pin.
- Don't expect overnight virality. Build a 6-month accumulation curve.
- Don't try to "engage with the audience" in comments. Focus on clicks and
  saves — they're what the algorithm cares about.
- Use Pinterest as a top-of-funnel for owned channels (Lyfe Spectrum store,
  antonyfmunoz.com). Don't try to monetize natively.

## Problem-Solution Map and Hidden Capabilities

| Problem                                              | Pinterest capability                                  |
|------------------------------------------------------|-------------------------------------------------------|
| "I need free traffic to my Shopify store"            | Catalog feed → Product Pins → Rich Pin treatment      |
| "I have a long blog post; how do I distribute it?"   | 5-10 pin variants on niche-keyworded boards           |
| "I need to validate which of 3 product photos sells" | A/B by posting variants and reading `OUTBOUND_CLICK_RATE` after 14d |
| "I want to find out what Pinterest users are searching for" | Pinterest Trends (trends.pinterest.com) — not in API for organic, but free in browser |
| "I need to repackage video for distribution"         | Idea Pin upload OR direct video pin with cover image  |
| "I want to know what colors / styles are trending"   | Pinterest Predicts annual report + Trends tool        |
| "I need to find out who saved my pin"                | Pin analytics show aggregate audience demographics, NOT individual savers |
| "I need to schedule pins"                            | Native Pinterest scheduler (web UI) OR API + cron     |
| "I need to bulk-upload 500 pins"                     | API loop with rate-limit backoff; or Tailwind         |

**Hidden capabilities most marketers miss:**

- **Rich Pins are automatic when og: tags are present** on the destination
  page. You don't have to do anything in the API — just verify your domain
  and put `<meta property="og:price:amount">`, `<meta property="product:availability">`, etc.
  on product pages. Pinterest's crawler picks them up and decorates the pin
  with live data.
- **The `note` field** on a pin is internal-only — invisible to users but
  searchable in your own dashboard. Use it to tag pins with internal
  campaign IDs.
- **`dominant_color`** in pin creation lets Pinterest skip a CPU step and
  often improves first-impression speed.
- **`board_pins_modified_at`** on boards is a freshness signal — adding a new
  pin to an old board reactivates the whole board's distribution.
- **Idea Pins can have a single product tag** linking to a catalog item (in
  supported regions) — under-used by most marketers because the UI is buried.
- **`/user_account/analytics/top_pins`** returns YOUR top-performing pins by
  metric — much faster than iterating every pin.
- **Catalog Product Groups** let you create rule-based bundles ("all in-stock
  jackets under $200") that auto-update as inventory changes — useful for
  ad creative even if you're organic-first.
- **The `parent_pin_id` field** records which pin you re-pinned from. If you
  re-pin your own old high-performer to a fresh board, you inherit some of
  its ranking signal.

## Operational Behavior and Edge Cases

- **Pin distribution is gradual.** Pinterest doesn't blast a new pin to
  everyone instantly. It tests it with a small audience (followers + a slice
  of relevant home-feed users), measures save rate, then expands distribution
  if signals are strong. This is why patience matters.
- **Save rate >> impressions.** A pin with 100 impressions and 10 saves
  outperforms a pin with 10,000 impressions and 50 saves. Optimize for save
  rate, not impression count.
- **Outbound clicks are the most weighted signal for shopping queries.**
  For Lyfe Spectrum, the metric to watch is `OUTBOUND_CLICK_RATE`, not
  `SAVE_RATE`.
- **Boards with high pin density rank better than sparse boards.** A board
  with 100 tightly themed pins beats a board with 5 pins on the same theme.
- **Repinning your own old content to new boards reignites it.** Pinterest
  treats it as a fresh distribution test.
- **Edits don't reset ranking.** You can update title/description/alt text on
  a live pin without losing the engagement signal. Use this to refine
  keywords on pins that almost broke through.
- **Deleting and reposting kills ranking.** If you delete a pin and recreate
  the same image, you start from zero — the engagement history is gone.
- **Pinterest's image CDN aggressively re-encodes uploads.** Always upload at
  max quality; Pinterest will down-sample for delivery.
- **Video processing can fail silently.** Always poll `/media/{id}` until
  status is `succeeded` before referencing the media_id in a pin.
- **Catalog feed processing failures are reported only in
  `/processing_results`** — they don't bubble up via email by default unless
  you set notification emails.
- **API calls from a fresh IP can trigger anti-abuse holds** even with valid
  auth. EOS pattern: warm up new VPS IPs by starting with a few reads before
  any writes.
- **Domain re-verification** is required if you change DNS providers or move
  hosting — don't be surprised when Rich Pins go dark after a Cloudflare
  switch.

## Ecosystem Position and Composition

**Where Pinterest sits in the funnel:**

```
Awareness → Discovery → Planning → Purchase → Loyalty
                ▲            ▲
                │            │
            Pinterest plays heavily here
```

Pinterest is upstream of Google Shopping (users start broad on Pinterest,
narrow on Google) and parallel to Etsy (visual product discovery). It is
NOT a substitute for Instagram (community + culture) or TikTok (entertainment
+ short-form virality).

**Composition with the EOS stack:**

| Tool          | Composition pattern with Pinterest                                  |
|---------------|--------------------------------------------------------------------|
| **Shopify**   | Source of catalog feed; deep-link destination for Product Pins. Set up Pinterest sales channel in Shopify Admin to auto-generate the feed. |
| **Canva**     | Pin design factory. Vertical 1000x1500 templates with brand fonts, generated in batch from blog post titles. |
| **Notion**    | Pin pipeline tracking. One Notion DB row per pin idea, status: drafted → designed → posted → tracked. |
| **Tailwind**  | Third-party Pinterest scheduler. Powerful but $15/mo and the API path is now mature enough that EOS can replicate it for $0. Mention but don't recommend. |
| **antonyfmunoz.com (Astro/Next)** | Destination for personal-brand pins. Must have og: tags + fast LCP (<2.5s) for ranking. |
| **Substrate** | EOS-internal — pins enter as durable jobs, drained by a Pinterest poster operator. Lets us batch and rate-limit cleanly. |
| **Discord**   | Notification surface for catalog feed errors, rate-limit wall hits, and weekly top-pin reports. |
| **Gemini / Claude** | Pin description drafter. Prompt: "Given this product page, write a Pinterest pin title (max 90 chars, keyword-loaded) and description (max 500 chars, natural-language SEO)." |
| **Apify**     | Competitor pin scraping for trend research (organic Pinterest scraping is gray-zone — be careful with TOS). |

## Trajectory and Evolution

**What Pinterest is investing in (2025-2026):**

1. **Shopping is the entire strategy.** Every product update over the past
   3 years has been a Shopping update: Catalog improvements, Product Tagging
   on Idea Pins, AR Try-On expansion (eyewear, beauty, furniture, soon
   apparel), Shopping API deepening, merchant onboarding flows.
2. **Video is a forced bet.** Pinterest is suppressing static pins relative
   to video pins in some categories to push creators toward video. Idea Pins
   are the strategic bet against TikTok / Reels.
3. **AI-powered visual search.** Pinterest Lens is being rebuilt on top of
   their internal multimodal model; expect "find products that match this
   vibe" to get dramatically better in 2026.
4. **Direct checkout in some markets.** Pinterest is testing in-app checkout
   with select merchants — historically Pinterest sent you to the merchant
   site, but Shop tab is becoming a marketplace.
5. **Generative AI for pin creation.** Pinterest released "Pinterest AI"
   features that let merchants generate lifestyle backdrops for product
   photos. API exposure is limited but expanding.
6. **Conversions API hardening** to compete with Meta CAPI on attribution.
7. **Pinterest Predicts** — an annual trend report that has become
   surprisingly accurate. Use it for content planning Q1 every year.

**What Pinterest is de-emphasizing:**

- Story Pins (rebranded as Idea Pins, then de-emphasized in favor of regular
  video pins in 2024)
- Group boards (still exist, no longer a growth lever)
- Following feed (replaced by personalized discovery as primary surface)

**EOS implication:** invest in Shopping + video pins. Don't build long-term
tooling around Idea Pins — they may be deprecated again. Watch the
Conversions API space for when Lyfe Spectrum's revenue justifies attribution.

## Conceptual Model and Solution Recipes

**The five mental models that unlock Pinterest mastery:**

### 1. The pin is a forever search result

Every pin you create is a row in Pinterest's search index. Optimize like an
SEO. The fields that get indexed:

- Title (highest weight)
- Description (high weight, especially first 100 chars)
- Board name (high weight — pin inherits board's keyword authority)
- Alt text (medium)
- Image content (visual model — medium-high)
- Destination URL + page content (medium)
- `note` field — NOT indexed publicly

### 2. The board is a category page

Boards rank in Pinterest search and Google search. Treat them as SEO landing
pages:

- Specific name with primary keyword
- Description with secondary keywords (max 500 chars)
- Cover pin that visually represents the category
- 20+ pins minimum to be considered "complete"
- Keep on-topic — one board, one tightly-defined category

### 3. Save rate is the funnel start

Save rate is the only metric Pinterest's algorithm cares about during the
distribution-test phase. If save rate > 1.5%, distribution expands. If <0.5%,
the pin is shelved.

### 4. Outbound click rate is the funnel end

For shopping intent, outbound click rate is what determines whether
Pinterest keeps surfacing the pin to high-intent users vs. demoting it to
the casual-scroll audience.

### 5. The destination URL is part of the pin

Pinterest's crawler reads the destination page on first save and again
periodically. If the destination is slow, broken, or off-topic, the pin
silently loses ranking. Conversely, a high-quality landing page (fast,
relevant, og:-tagged) lifts every pin pointing to it.

### Solution recipes

**Recipe: Bootstrap a new board from a blog post.**

```
1. Pick the blog post's primary keyword
2. Create board: name = keyword phrase, description = 2-3 sentences with secondaries
3. Generate 10 pin variants in Canva (different hooks, same destination)
4. Post 3 pins on day 0, 3 on day 3, 4 on day 7
5. After 14 days, pull pin analytics
6. Kill the bottom 3, repin top 3 to a related secondary board
```

**Recipe: Sync Lyfe Spectrum Shopify catalog.**

```
1. In Shopify Admin: install Pinterest sales channel
2. Pinterest sales channel auto-generates feed at /feeds/pinterest.xml
3. Verify domain at developers.pinterest.com
4. POST /catalogs/feeds with location pointing to the Shopify URL
5. Wait 24h for first ingestion
6. GET /catalogs/feeds/{id}/processing_results to verify
7. Auto-generated Product Pins now live; nothing more to do
8. Layer handcrafted lifestyle pins on top for engagement
```

**Recipe: Find your top-performing pin pattern.**

```
1. GET /user_account/analytics/top_pins for last 90 days, sorted by SAVE
2. For each top pin, GET /pins/{id} and extract title, description, image dimensions, board_id
3. Cluster by board, by image aspect ratio, by description length
4. Identify 2-3 patterns that repeat across top performers
5. Brief Antony with the patterns; replicate 5 new pins per pattern
```

**Recipe: Weekly performance loop.**

```
Monday morning cron:
  - Pull /user_account/analytics for last 7 days
  - Pull top pins by IMPRESSION, SAVE, OUTBOUND_CLICK
  - Diff against last week's snapshot in Neon
  - Generate Discord report: top 5 risers, top 5 fallers, total OUTBOUND_CLICK delta
  - Alert if total OUTBOUND_CLICK fell >30% week-over-week
```

## Industry Expert and Cutting-Edge Usage

**What top Pinterest operators do that beginners don't:**

- **Anna Bennett, Vanessa Kynes, Kate Ahl** (top Pinterest strategists in
  the marketing world) all preach the same thing: keyword research first,
  pin creation second. They use Pinterest's own search bar as a keyword tool —
  type a seed term and read the autosuggest dropdown.
- **Tailwind Communities** (formerly Tribes) was the power-user growth hack
  for years. Pinterest's algorithm has since penalized obvious community
  re-pin spikes, so this is a softer lever now.
- **The "fresh pin" hack:** top operators create new pins for the same
  destination URL every 2-4 weeks rather than re-pinning the same image.
  Pinterest's algorithm prefers visual novelty, even pointing to the same
  link.
- **Pin design conventions** that consistently outperform:
  - Vertical 1000x1500 (2:3) — non-negotiable
  - Text overlay with high contrast (white text, dark gradient behind it)
  - Brand color block in the top-left or bottom-left corner
  - Face in the image (lifestyle pins with a face beat product-only pins)
  - Title text repeats the pin title (Pinterest can read text in images)
- **Top ecommerce operators** publish blog content on the merchant domain
  primarily to feed Pinterest. Every product gets a "How to style the X"
  blog post, which becomes the pin destination instead of the bare product
  page — better dwell time, better Rich Pin behavior.
- **Top creators use Pinterest's Trends tool** (trends.pinterest.com) to
  validate keywords before investing in pin creation. It shows search volume
  trends back 12 months and seasonal patterns.
- **Pinterest Predicts** (the annual trend report) is treated as gospel by
  serious operators. They publish in November for the upcoming year, and the
  predictions are usually right because Pinterest has unique visibility into
  early-stage planning behavior.
- **The "clean board" practice:** quarterly, top operators audit boards for
  low-performers and either delete them, archive them, or merge them. A
  bloated account with 80 dead boards drags down distribution.
- **Catalog + lifestyle layering:** the combination of auto-Product-Pins
  (volume) + handcrafted lifestyle pins (engagement) outperforms either
  alone by 3-5x in EOS-scale ecommerce benchmarks.

**Cutting-edge as of 2026:**

- **AI-generated lifestyle backdrops** (DreamBooth + ControlNet on flat
  product photos) are how lean ecommerce brands now produce 50 lifestyle
  variants from one studio shot. Pinterest's own AI tools are catching up.
- **Pinterest video pins generated from blog posts** via script-to-video
  pipelines (Runway, Pika, plus voiceover) are an emerging top-of-funnel
  play that Pinterest's algorithm currently rewards heavily.
- **Conversions API for organic-driven sales attribution** is starting to
  matter even for organic-first brands because it lets Pinterest's algorithm
  learn which pins drive actual revenue (vs. clicks).

## EOS Usage Patterns

### Pattern 1: Lyfe Spectrum daily product pin loop

```python
# scripts/scheduled/pinterest_lyfe_spectrum_daily.py
# Cron: 0 9 * * *
"""
Pulls today's recommended product to feature from Shopify, generates a pin
description via Gemini, posts it to the appropriate lookbook board.
"""
import os, sys
sys.path.insert(0, "/opt/OS")
from eos_ai.pinterest_client import PinterestClient
from eos_ai.shopify_client import ShopifyClient
from eos_ai.model_router import call_with_fallback

shop = ShopifyClient()
pin = PinterestClient()

# 1. Pick today's hero product (highest inventory + recent low traffic)
product = shop.pick_pinterest_hero()

# 2. Generate pin copy
prompt = f"""
Product: {product.title}
URL: {product.url}
Image: {product.hero_image}
Vibe: tactical luxury, all-black, Lyfe Spectrum

Write:
1. Pinterest pin title (max 90 chars, keyword-loaded, no hashtags)
2. Pinterest pin description (max 500 chars, natural language, primary keyword in first sentence)
3. Alt text (max 300 chars, describe the visual literally)

Output as JSON: {{"title":..,"description":..,"alt_text":..}}
"""
copy = call_with_fallback(prompt, agent_type="content").json()

# 3. Pick board by category
board_id = shop.pinterest_board_for(product.category)  # mapped in Neon

# 4. Post
result = pin.create_pin(
    board_id=board_id,
    title=copy["title"],
    description=copy["description"],
    image_url=product.hero_image,
    link=f"{product.url}?utm_source=pinterest&utm_campaign=daily_hero",
    alt_text=copy["alt_text"],
)
print(f"Pin created: {result['id']}")
```

### Pattern 2: Personal brand blog → pin variant generator

For each new long-form post on antonyfmunoz.com, agent generates 8 pin
variants and queues them in Notion for Antony to review. On approval, EOS
posts them to staggered boards over 14 days.

```python
def generate_pin_variants_for_post(post):
    variants = []
    hooks = call_with_fallback(
        f"Write 8 distinct hook-style Pinterest titles for this essay: {post.title}\n{post.summary}",
        agent_type="content",
    )
    for hook in hooks.split("\n"):
        variants.append({
            "title": hook[:90],
            "description": post.meta_description[:500],
            "image_url": post.pinterest_image_for(hook),
            "link": f"{post.url}?utm_source=pinterest&utm_content={slug(hook)}",
            "alt_text": post.alt_text,
            "scheduled_at": stagger_over_days(14),
        })
    return variants
```

### Pattern 3: Weekly performance pull

```python
# scripts/scheduled/pinterest_weekly_report.py
# Cron: 0 8 * * MON
from datetime import date, timedelta
end = date.today() - timedelta(days=2)   # 48hr lag tolerance
start = end - timedelta(days=7)
top = pin.request("GET", "/user_account/analytics/top_pins",
                  params={"start_date": start.isoformat(),
                          "end_date": end.isoformat(),
                          "metric_types": "SAVE,OUTBOUND_CLICK",
                          "sort_by": "OUTBOUND_CLICK"})
post_to_discord("#lyfe-spectrum-metrics", format_top_pins(top))
```

### Pattern 4: Catalog feed health monitor

```python
# Runs hourly; alerts if last successful processing > 36h ago
results = pin.request("GET", f"/catalogs/feeds/{FEED_ID}/processing_results",
                       params={"page_size": 5})
last = results["items"][0]
if last["status"] != "COMPLETED":
    alert(f"Pinterest catalog feed failed: {last['ingestion_details']}")
```

### Pattern 5: Pin SEO refresh on underperformers

```python
# Monthly: find pins with <0.5% save rate after 30 days, regenerate copy
underperformers = neon.query("""
  SELECT pin_id FROM pinterest_pin_metrics
  WHERE created_at < NOW() - INTERVAL '30 days'
    AND save_rate < 0.005
""")
for pid in underperformers:
    new_copy = regenerate_copy_via_gemini(pid)
    pin.request("PATCH", f"/pins/{pid}", json=new_copy)
```

### Pattern 6: Substrate operator integration

Every pin post is enqueued as a substrate job:

```
{
  "type": "pinterest.create_pin",
  "payload": {"board_id":"...","title":"...","description":"...","image_url":"...","link":"..."},
  "scheduled_at": "2026-04-07T15:00:00Z",
  "max_attempts": 3
}
```

The `pinterest_drainer` operator pulls jobs, calls `PinterestClient.create_pin`,
respects rate limits across the whole queue, and writes results back to Neon.
This is how EOS gets clean rate-limit + retry semantics for free.

## Gotchas

- **Personal account 403:** convert to business account at business.pinterest.com.
- **Trial mode reach cap:** submit app for review the moment you have a real
  use case. Don't wait until you're in production.
- **Refresh token rotation:** persist EVERY refresh response, not just the
  initial token grant. Lose this and you lose auth in 60 days with no
  warning.
- **Scope additions need re-auth:** plan scopes upfront. Adding `catalogs:write`
  six months later requires a full reauth flow.
- **Idea Pin endpoints are different:** `/pins` won't accept multi-page
  payloads. Read the Idea Pin docs separately if you're going that route.
- **Image URL must be public HTTPS:** Pinterest's crawler must be able to
  fetch the image without auth. S3 presigned URLs work but expire — host
  permanently.
- **Pin title is 100 chars max, not 100 chars recommended:** truncating at 90
  is safer because Pinterest sometimes appends emoji indicators.
- **Description first 100 chars matter most:** Pinterest's preview shows
  ~100 chars before "more" — front-load keywords.
- **Alt text is mandatory for ranking parity:** skipping it costs ~15-20%
  distribution.
- **Outbound link must be reachable:** Pinterest's crawler validates the URL.
  302 redirects are OK, broken links kill the pin.
- **Domain verification is per-domain, not per-subdomain:** verify
  `lyfespectrum.com` and `www.lyfespectrum.com` separately if you serve from
  both.
- **Rich Pins require og: tags:** add `og:type=product`, `og:price:amount`,
  `og:price:currency`, `product:availability`. Pinterest crawls and
  decorates automatically.
- **Catalog feed format gotcha:** XML feed must use Pinterest's schema, not
  Google Shopping schema. The two are similar but NOT identical (different
  field names for variants and `availability` enum casing).
- **Catalog ingestion is async, not idempotent on partial failures:** if
  10% of items fail validation, the rest still ingest. Always read
  processing_results.
- **Day-1 analytics are zero:** wait 48-72h before drawing conclusions on
  any pin's performance.
- **Save rate is what matters early; outbound click rate is what matters
  later:** don't optimize the wrong metric for the wrong phase.
- **Repinning identical images to many boards in one day** triggers spam
  detection. Spread over weeks.
- **Editing a pin doesn't reset its ranking; deleting and reposting does:**
  prefer PATCH over delete-recreate.
- **Pinterest video pins need polled status:** `/media/{id}` must show
  `succeeded` before referencing the media_id, or pin creation 422s.
- **Catalog feed location must be HTTPS and reachable from Pinterest's
  crawler IPs:** if you geo-block or rate-limit by IP, whitelist Pinterest.
- **Pinterest deprecates aggressively:** v3 → v4 → v5 over 4 years. Don't
  build long-lived integrations against undocumented endpoints — they
  vanish.
- **No webhooks for organic events:** if you need to know "did anything
  happen," you must poll. Build a snapshot diff in Neon.
- **API keys / app secrets in client-side code:** never. Pinterest tokens
  give full posting authority on the account.
- **Rate limit 429s are bursty:** the per-hour quota is the wall; the
  per-second burst is the speed bump. Backoff handles both.
- **Trial app reach cap is silent:** API returns 200 OK on pin creation,
  but the pin gets ~zero distribution. Symptom: pins post fine but get
  zero impressions for weeks. Fix: get the app reviewed.
- **Pinterest Trends tool is not in the v5 API for organic accounts:**
  scrape the web UI manually or pull annually from Pinterest Predicts.
- **`utm_source=pinterest` matters:** use it on every outbound link so GA4
  / your analytics can attribute traffic correctly. Pinterest does NOT
  inject UTMs for you.
