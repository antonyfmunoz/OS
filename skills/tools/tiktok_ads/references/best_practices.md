# TikTok Marketing API — Creator-Level Best Practices
Source: business-api.tiktok.com/portal/docs, github.com/tiktok/tiktok-business-api-sdk, ads.tiktok.com/help
API Version: v1.3 (current as of 2026-04)
SDK Version: tiktok-business-api-sdk (Python, JS, Java, Go) — generated from OpenAPI
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## Authentication

OAuth 2.0, **TikTok for Business identity** (the same login that backs Ads
Manager and Business Center). This is a different identity provider from
TikTok Login Kit (consumer / Display API), and a different developer portal
(`business-api.tiktok.com/portal` vs `developers.tiktok.com`).

Identifiers your app holds:
- `app_id` — public, embedded in OAuth URLs
- `secret` — server-side only, used in `oauth2/access_token/` exchange
- `redirect_uri` — must match exactly what's registered, including trailing slash

Identifiers TikTok issues per granting user:
- `auth_code` — short-lived, single-use, comes back on the redirect
- `access_token` — long-lived (no documented expiry for first-party flow but
  can be revoked)
- `advertiser_ids[]` — the ad accounts the user authorized your app for

Flow:
```
GET https://business-api.tiktok.com/portal/auth
  ?app_id=APP_ID
  &state=STATE_NONCE
  &redirect_uri=https%3A%2F%2Fyourapp%2Fcb
  &rid=RANDOM
```
Browser comes back with `?auth_code=...&state=...`.

```
POST https://business-api.tiktok.com/open_api/v1.3/oauth2/access_token/
Content-Type: application/json
{
  "app_id": "APP_ID",
  "secret": "APP_SECRET",
  "auth_code": "AUTH_CODE"
}
```
Returns:
```json
{ "code": 0, "message": "OK",
  "data": {
    "access_token": "TOKEN",
    "advertiser_ids": ["1234567890"],
    "scope": [4,3,1,...]
  }
}
```

Header on every request thereafter:
```
Access-Token: <TOKEN>
```
NOT `Authorization: Bearer <TOKEN>`. The wrong header returns `40105` and
nothing else useful.

Scopes are integer codes; common ones:
- `1` Account Management
- `3` Ad Account Management
- `4` Ads Management
- `5` Audience Management
- `6` Reporting
- `7` Pixel
- `8` Creative Management
- `15` Conversion Event (Events API)
- `19` Business Center Management
Request only what you need; over-scoped consent screens lower conversion.

For Spark Ads, you additionally need an **identity authorization** path:
either (a) the creator generates a per-video Spark Code in-app (7/30/60/365
days), or (b) the creator's TikTok user is added to your Business Center as an
authorized identity, granting indefinite use of any of their posts. Path (b)
is the EOS default for the founder's own account.

## Core Operations with Exact Signatures

All v1.3. Base URL `https://business-api.tiktok.com`. Sandbox base
`https://sandbox-ads.tiktok.com`. All POST bodies are JSON with
`Content-Type: application/json`. All GET array params are JSON-then-URL
encoded.

### Account & Business Center

```
GET  /open_api/v1.3/advertiser/info/?advertiser_ids=["..."]&fields=["name","timezone","currency","status","balance"]
GET  /open_api/v1.3/oauth2/advertiser/get/?app_id=...&secret=...
GET  /open_api/v1.3/bc/get/                                  # list business centers
GET  /open_api/v1.3/bc/advertiser/get/?bc_id=...             # ad accounts in a BC
GET  /open_api/v1.3/bc/member/get/?bc_id=...
POST /open_api/v1.3/bc/asset/assign/
POST /open_api/v1.3/bc/asset/partner/add/
```

### Campaigns

```
POST /open_api/v1.3/campaign/create/
POST /open_api/v1.3/campaign/update/
POST /open_api/v1.3/campaign/status/update/         # ENABLE | DISABLE | DELETE
GET  /open_api/v1.3/campaign/get/?advertiser_id=...&filtering=...&page=1&page_size=100
```

Required campaign fields on create:
- `advertiser_id` (string)
- `campaign_name` (≤512 chars, unique within advertiser)
- `objective_type` — one of `REACH`, `TRAFFIC`, `VIDEO_VIEWS`, `LEAD_GENERATION`,
  `WEB_CONVERSIONS`, `APP_PROMOTION`, `PRODUCT_SALES`, `ENGAGEMENT`, `SHOP_PURCHASES`
- `budget_mode` — `BUDGET_MODE_DAY` | `BUDGET_MODE_TOTAL` | `BUDGET_MODE_INFINITE`
- `budget` (number) — required unless `BUDGET_MODE_INFINITE`

CBO (Campaign Budget Optimization): set budget at campaign level, omit at
adgroup level. ABO (Adgroup Budget Optimization): omit at campaign, set at
adgroup. Mixing them is a 40002 error.

### Adgroups

```
POST /open_api/v1.3/adgroup/create/
POST /open_api/v1.3/adgroup/update/
POST /open_api/v1.3/adgroup/status/update/
GET  /open_api/v1.3/adgroup/get/
POST /open_api/v1.3/adgroup/budget/update/         # incremental change
POST /open_api/v1.3/adgroup/schedule/update/
```

The adgroup is where 80% of decisions live. Required fields on create
(WEB_CONVERSIONS objective, OCPM bidding):
- `advertiser_id`, `campaign_id`, `adgroup_name`
- `placement_type` — `PLACEMENT_TYPE_AUTOMATIC` | `PLACEMENT_TYPE_NORMAL`
- `placements` — `["PLACEMENT_TIKTOK"]` (drop Pangle for brand-safe; add
  `PLACEMENT_PANGLE` for cheap reach)
- `promotion_type` — `WEBSITE` | `APP_ANDROID` | `APP_IOS` | `LEAD_GEN` | `SHOP`
- `pixel_id` (if WEBSITE)
- `optimization_event` — must match an active pixel event
  (`COMPLETE_PAYMENT`, `LEAD_GENERATION`, `SUBSCRIBE`, `ADD_TO_CART`, ...)
- `billing_event` — `OCPM` | `CPC` | `CPV` | `CPM`
- `bid_type` — `BID_TYPE_NO_BID` (lowest cost) | `BID_TYPE_CUSTOM`
- `bid_price` (if CUSTOM)
- `budget_mode`, `budget` (unless campaign CBO)
- `schedule_type`, `schedule_start_time` (`YYYY-MM-DD HH:MM:SS` advertiser TZ),
  `schedule_end_time` (if SCHEDULE_START_END)
- `location_ids[]` — Geoname IDs (`6252001` = US)
- `gender`, `age_groups[]`, `languages[]`, `interest_category_ids[]`,
  `behavior_category_ids[]`, `audience_ids[]`, `excluded_audience_ids[]`
- `operation_status` — **always `DISABLE` on EOS create**

### Ads

```
POST /open_api/v1.3/ad/create/
POST /open_api/v1.3/ad/update/
POST /open_api/v1.3/ad/status/update/
GET  /open_api/v1.3/ad/get/
POST /open_api/v1.3/ad/aco/create/                  # Automated Creative Optimization
GET  /open_api/v1.3/ad/review_info/                 # rejection reasons
```

Required fields per creative on create:
- `ad_name`, `ad_format` (`SINGLE_VIDEO` | `SINGLE_IMAGE` | `CAROUSEL_ADS`)
- For Spark: `identity_type=AUTH_CODE` (or `TT_USER`), `identity_id`,
  `identity_authorized_bc_id`, `tiktok_item_id`
- For Custom: `identity_type=CUSTOMIZED_USER`, `identity_id` (created via
  `identity/create/`), `video_id` (uploaded via `file/video/ad/upload/`),
  `image_ids[]` (cover)
- `call_to_action` (enum: `LEARN_MORE`, `SHOP_NOW`, `SIGN_UP`, ...)
- `landing_page_url`
- `display_name` (overrides identity name)

### Creative & Identity

```
POST /open_api/v1.3/file/video/ad/upload/         # multipart, video_signature MD5 required
POST /open_api/v1.3/file/image/ad/upload/
GET  /open_api/v1.3/file/video/ad/info/
POST /open_api/v1.3/identity/create/              # CUSTOMIZED_USER identity
GET  /open_api/v1.3/identity/get/
POST /open_api/v1.3/tt_video/list/                # list authorized creator videos
POST /open_api/v1.3/tt_video/auth_code/apply/     # request creator auth
```

### Pixels & Events API

```
POST /open_api/v1.3/pixel/create/
GET  /open_api/v1.3/pixel/list/
POST /open_api/v1.3/pixel/event/create/
POST /open_api/v1.3/pixel/event/update/
POST /open_api/v1.3/event/track/                  # Events API ingest (CAPI)
POST /open_api/v1.3/pixel/track/                  # legacy single-event
```

`event/track/` payload skeleton:
```json
{
  "event_source": "web",                  // web | app | offline | crm
  "event_source_id": "PIXEL_CODE",
  "data": [{
    "event": "CompletePayment",
    "event_time": 1743984000,             // unix seconds
    "event_id": "ia-order-90218",         // dedup key with browser pixel
    "user": {
      "email": "<sha256>",
      "phone": "<sha256>",
      "external_id": "<sha256>",
      "ttclid": "<click id from URL>",
      "ttp": "<_ttp cookie>",
      "ip": "...",
      "user_agent": "..."
    },
    "properties": {
      "currency": "USD",
      "value": 750.00,
      "content_id": "ia-cohort-2026-04",
      "content_type": "product",
      "contents": [{"content_id":"...","quantity":1,"price":750.0}]
    },
    "page": { "url": "https://...", "referrer": "..." },
    "limited_data_use": false
  }]
}
```

Standard event names: `ViewContent`, `ClickButton`, `Search`, `AddToWishlist`,
`AddToCart`, `InitiateCheckout`, `AddPaymentInfo`, `CompletePayment`,
`PlaceAnOrder`, `Subscribe`, `CompleteRegistration`, `Contact`, `Download`,
`SubmitForm`, `Lead`.

### Audiences

```
POST /open_api/v1.3/dmp/custom_audience/create/                # file_paths or rule
POST /open_api/v1.3/dmp/custom_audience/file/upload/           # CSV of hashed records
POST /open_api/v1.3/dmp/custom_audience/update/
GET  /open_api/v1.3/dmp/custom_audience/list/
POST /open_api/v1.3/dmp/custom_audience/delete/
POST /open_api/v1.3/dmp/custom_audience/share/
POST /open_api/v1.3/dmp/saved_audience/create/                 # targeting save
POST /open_api/v1.3/dmp/lookalike_audience/create/
```

Customer file format: CSV with header row, columns chosen from
`EMAIL_SHA256`, `PHONE_SHA256`, `IDFA_SHA256`, `GAID_SHA256`. Hash before
upload — TikTok does not hash for you. Rows below threshold (~1000 matched)
will not seed a lookalike.

### Reporting

```
GET  /open_api/v1.3/report/integrated/get/                     # synchronous
POST /open_api/v1.3/report/task/create/                        # async, large pulls
GET  /open_api/v1.3/report/task/check/?task_id=...
GET  /open_api/v1.3/report/task/download/?task_id=...
```

Synchronous params:
- `advertiser_id`
- `report_type` — `BASIC` | `AUDIENCE` | `PLAYABLE_MATERIAL` | `CATALOG` | `BC`
- `data_level` — `AUCTION_AD` | `AUCTION_ADGROUP` | `AUCTION_CAMPAIGN` | `AUCTION_ADVERTISER`
- `dimensions[]` — must include the level id (e.g. `ad_id`) plus optional time/breakdowns
- `metrics[]` — must be valid for that data_level (TikTok rejects unknown silently)
- `start_date`, `end_date` — `YYYY-MM-DD`, max 30 days range, max 1 year lookback
- `filtering[]`, `order_field`, `order_type`, `page`, `page_size` (max 1000)
- `query_lifetime` — boolean, ignores date range

Common metrics: `spend`, `impressions`, `clicks`, `ctr`, `cpc`, `cpm`,
`conversion`, `conversions_breakdown`, `cost_per_conversion`,
`conversion_rate`, `result`, `cost_per_result`, `video_play_actions`,
`video_watched_2s`, `video_watched_6s`, `video_views_p25`, `video_views_p50`,
`video_views_p75`, `video_views_p100`, `engaged_view`, `real_time_app_install`.

## Pagination Patterns

Most list endpoints (`/get/`, `/list/`) use page-based pagination with
`page` (1-indexed) and `page_size` (default 10, max varies: 1000 for
campaign/adgroup/ad, 200 for reporting, 50 for audiences). Response includes
`page_info`:
```json
"page_info": { "page": 1, "page_size": 100, "total_number": 437, "total_page": 5 }
```
Drive your loop off `page < total_page` rather than counting items, because
filtering server-side may shrink results unpredictably.

Async reporting (`report/task/`) uses task-based pagination — submit, poll
`task/check/` until `status=SUCCESS`, then `task/download/` returns a signed
URL to a CSV/JSON file with the entire result set, no paging. Use this for
anything more than ~10K rows.

There is no cursor-based pagination on Marketing API — pages can shift if
data mutates between calls. Sort by an immutable field (`create_time desc`)
when consistency matters.

## Rate Limits

Limits are per app + per advertiser_id, applied in two layers: QPS bucket and
daily quota. Approximate ceilings (TikTok does not publish exact numbers and
they change):

| Endpoint class             | QPS | Daily quota |
|----------------------------|-----|-------------|
| Read (campaign/get etc.)   | ~20 | ~100k       |
| Write (create/update/status)| ~10 | ~10k       |
| Reporting (sync)           | ~10 | ~10k        |
| Reporting (async task)     | ~5  | ~5k         |
| Events API (event/track/)  | ~25 batches/sec, 500 events per batch | very high |
| Audience file upload       | ~1  | ~50 |

Burst over the QPS bucket → `40100` ("rate limit exceeded") or `50002`
("server busy"). Exceed the daily quota → `40100` until UTC midnight.
Exponential backoff with jitter: 1s, 2s, 4s, 8s, 16s, give up at 32s and
escalate.

The Events API specifically tolerates much higher throughput because TikTok
wants the conversion signal — batch up to 500 events per call and you'll never
hit limits in normal use.

## Error Codes and Recovery

Every response is HTTP 200 with `{"code":N,"message":"...","data":{},"request_id":"..."}`.
Always check `code == 0`. Always log `request_id` — TikTok support cannot help
without it.

| code  | meaning                                  | recovery                                          |
|-------|------------------------------------------|---------------------------------------------------|
| 0     | success                                  | —                                                 |
| 40000 | invalid token / missing token            | re-auth, check `Access-Token` header              |
| 40001 | param missing                            | check `message` for the field name                |
| 40002 | param invalid                            | most common; budget/format/enum mismatch          |
| 40003 | resource not found                       | wrong advertiser_id or stale id                   |
| 40004 | permission denied                        | scope missing, or BC asset not assigned           |
| 40100 | rate limited                             | exponential backoff with jitter                   |
| 40105 | invalid access token                     | wrong header, expired, or revoked — re-auth       |
| 40300 | account frozen / banned                  | human intervention, no API recovery               |
| 50000 | system error                             | retry with backoff                                |
| 50002 | server busy                              | retry with backoff                                |
| 51001 | image/video processing failed            | re-upload, check format                           |
| 51005 | creative review rejected                 | call `ad/review_info/` for reasons                |

Recovery patterns:
- Always retry 5xx and 40100 with exponential backoff + jitter, max 5 attempts
- Never retry 4xx other than 40100 — they will not succeed
- For 40105 mid-job, refresh token from Neon and retry once; if still failing,
  escalate to human (token revoked)
- For 51005 (creative rejection), pull `ad/review_info/`, log the reason, and
  notify human — do NOT auto-resubmit

## SDK Idioms

The official SDK (`tiktok-business-api-sdk`) is generated from the OpenAPI
spec and is verbose but complete. Python install:
```bash
pip install business_api_client
```

Idiomatic call:
```python
import business_api_client
from business_api_client.rest import ApiException

cfg = business_api_client.Configuration()
cfg.access_token = os.environ["TIKTOK_ADS_TOKEN"]
client = business_api_client.ApiClient(cfg)

api = business_api_client.CampaignCreationApi(client)
try:
    res = api.campaign_create(
        access_token=cfg.access_token,
        body={
            "advertiser_id": ADV_ID,
            "campaign_name": "IA-FounderContent-2026-04",
            "objective_type": "WEB_CONVERSIONS",
            "budget_mode": "BUDGET_MODE_DAY",
            "budget": 20.00,
        },
    )
    if res.code != 0:
        raise RuntimeError(f"tiktok error {res.code} {res.message} {res.request_id}")
    campaign_id = res.data.campaign_id
except ApiException as e:
    log.error("HTTP failure: %s", e)
    raise
```

EOS prefers a thin `httpx` client over the SDK because:
- The SDK pins old urllib3, conflicts with our Neon/psycopg stack
- Generated method names mutate on every regeneration
- Error handling is uniform across endpoints — one wrapper does it all
- We need request/response logging to `audit.paid_media_changes`

EOS wrapper sketch (`eos_ai/tiktok_ads_client.py`):
```python
class TikTokAdsClient:
    BASE = "https://business-api.tiktok.com/open_api/v1.3"
    def __init__(self, token: str, advertiser_id: str):
        self.token = token
        self.adv = advertiser_id
        self.http = httpx.Client(timeout=30, headers={"Access-Token": token})

    def call(self, method: str, path: str, *, json=None, params=None) -> dict:
        url = f"{self.BASE}{path}"
        r = self.http.request(method, url, json=json, params=params)
        r.raise_for_status()
        body = r.json()
        if body.get("code") != 0:
            raise TikTokAPIError(body["code"], body["message"], body.get("request_id"))
        return body["data"]
```

## Anti-Patterns

- **Trusting HTTP 200.** Every code path must check `body["code"] == 0`. The
  number of TikTok integrations broken by this in the wild is enormous.
- **Hardcoding `advertiser_id` as int.** It's a string everywhere — JSON
  field, URL param, log key. Coercing loses leading zeros and breaks signed
  comparisons.
- **Setting budget on both campaign and adgroup.** Pick CBO or ABO. Both
  → `40002`.
- **Optimizing for an event the pixel never fires.** OCPM with
  `optimization_event=COMPLETE_PAYMENT` on a pixel that only sees
  `ViewContent` will spend without learning. Verify event volume in Events
  Manager before launching.
- **Uploading raw email/phone to Custom Audiences.** TikTok expects SHA-256
  pre-hashed; raw data is dropped silently with a "0 matched" result.
- **Using the consumer Display API token for Marketing API calls** (or vice
  versa). Different identity provider, different token shape, different host.
- **Building Spark Ads with one-off auth codes that expire mid-campaign.** Use
  Business Center identity authorization for any account you control.
- **Scraping reporting via repeated `report/integrated/get/` instead of
  `report/task/create/`.** You will hit the daily quota by lunchtime.
- **Not setting `event_id`** on Events API events. No `event_id` = no
  deduplication = double-counted conversions = corrupted optimization.
- **Polling `campaign/get/` every minute to detect changes.** Use the
  Business Center webhook for membership changes; for spend changes, poll
  reporting on a cron, not a tight loop.

## Data Model

```
Advertiser (advertiser_id)
├── Campaign (campaign_id)        — objective + (CBO) budget
│   └── Adgroup (adgroup_id)      — targeting + bidding + schedule + (ABO) budget
│       └── Ad (ad_id)            — creative + identity + landing
├── Pixel (pixel_id / pixel_code)
│   ├── Event Rule (event)        — Standard or Custom event definition
│   └── Web Event                 — actual fires (browser pixel + Events API)
├── Identity (identity_id)
│   ├── CUSTOMIZED_USER           — uploaded display name + avatar
│   ├── TT_USER                   — real TikTok account in your BC
│   └── AUTH_CODE                 — per-video creator authorization
├── Custom Audience (custom_audience_id)
│   ├── FILE                      — uploaded customer list (hashed)
│   ├── ENGAGEMENT                — ad/post engagers
│   ├── WEBSITE                   — pixel-based
│   ├── APP                       — SDK-based
│   ├── LEAD_GEN                  — lead form submitters
│   └── CUSTOMER_FILE             — synonym for FILE
├── Lookalike Audience (lookalike_audience_id)  — derived from a seed
├── Saved Audience (saved_audience_id)          — saved targeting bundle
├── Lead Form (lead_form_id)                    — instant form, lives in BC
├── Catalog (catalog_id)                        — product feed for DPA
└── Image / Video (image_id / video_id)         — uploaded creative

Business Center (bc_id)
├── Members (user_id)             — humans with BC roles
├── Asset assignments             — advertiser ↔ user, advertiser ↔ partner BC
├── Identities                    — authorized TT_USER list (Spark Ads)
└── Reports                       — cross-advertiser rollups
```

Object lifecycle: `DRAFT → REVIEWING → APPROVED → DELIVERING → COMPLETED`
(or `REJECTED` from REVIEWING, `DISABLE` at any time, `DELETE` is soft-delete
keeping ID for reporting). Status fields you'll see in responses:
`primary_status`, `secondary_status`, `operation_status`. Manage with
`operation_status`; the others are read-only TikTok-side state.

## Webhooks and Events

TikTok Marketing API has **partial** webhook support. As of v1.3 (2026-04):

Supported webhooks:
- **Lead form submissions** — `LEAD` event, configured per-app, posts to
  registered URL when an instant lead form is submitted. Includes lead_id,
  form_id, advertiser_id, page_id, form payload. EOS uses this to push leads
  straight to the Initiate Arena CRM.
- **App event postbacks (MMP)** — for app installs/events from approved
  Mobile Measurement Partners (Adjust, AppsFlyer, Branch, Singular).
- **Business Center membership** — partner BC additions, asset assignments.
- **Catalog item updates** (DPA) — feed processing complete.

NOT supported (poll instead):
- Campaign/adgroup/ad status changes
- Spend threshold reached
- Creative approval / rejection (poll `ad/review_info/`)
- Custom audience size updates
- Pixel fire counts

Webhook security: TikTok signs webhook payloads with HMAC-SHA256 of
`(timestamp + body)` using your app secret, sent in `X-TT-Signature` header.
Verify on every request, reject if older than 5 minutes (replay protection).

EOS pattern: register the lead form webhook to a Cloudflare Worker that
validates signature, drops the lead into `inbound.tiktok_leads`, and signals
the orchestrator. Everything else is polled by `scripts/scheduled/tiktok_ads_pull.py`.

## Limits

Hard product limits (not rate limits):

| Resource                              | Limit                              |
|---------------------------------------|------------------------------------|
| Campaigns per advertiser              | 999 active                         |
| Adgroups per campaign                 | ~999 (soft, performance-based)     |
| Ads per adgroup                       | 20 active                          |
| Custom audiences per advertiser       | 400                                |
| Lookalikes per seed audience          | 10                                 |
| Pixel events per pixel                | 30 standard + custom               |
| Locations targeted per adgroup        | 1000                               |
| Interests / behaviors per adgroup     | 100                                |
| Excluded audiences per adgroup        | 30                                 |
| Video file size                       | 500 MB                             |
| Video duration                        | 5–60s recommended, up to 10 min    |
| Video aspect ratios                   | 9:16 (mandatory native), 1:1, 16:9 |
| Image file size                       | 500 KB                             |
| Customer file size                    | 1 GB / 100M rows                   |
| Lead form fields                      | 13                                 |
| Min daily budget                      | $20 ad / $50 campaign (USD)        |
| Reporting date range                  | 30 days per call                   |
| Reporting lookback                    | 365 days                           |
| Async report rows                     | 1M                                 |

## Cost Model

The API itself is free. The cost is the ad spend it triggers. EOS treats
**every spend-affecting call as CRITICAL risk** and routes through
authority_engine. Reads are free and unrestricted.

Auction model: second-price auction with quality multiplier. You bid via
`bid_type`/`bid_price`. `BID_TYPE_NO_BID` (lowest cost) is the EOS default —
TikTok finds the cheapest impressions for your optimization event within
budget. `BID_TYPE_CUSTOM` (cost cap) lets you set a target CPA but reduces
delivery if the cap is too low.

Budget pacing: TikTok paces evenly across the day by default. `pacing` field
on adgroup: `PACING_MODE_SMOOTH` (default) | `PACING_MODE_FAST` (front-load).
Day-budget caps are hard ceilings — TikTok will not overspend within a 24-hour
window, but can come within 25% over briefly and self-correct.

## Version Pinning

Current stable: **v1.3** (in URL path, `/open_api/v1.3/...`).
Prior: v1.2 (deprecated 2024 — many tutorials still show v1.2 URLs, **do not
copy them**, the auth_token endpoint shape changed).

Versioning is in the URL path, not a header. TikTok announces version
sunsets in the developer changelog with 6+ months notice. There is no
"stable" alias — pin the exact version in code and bump deliberately.

EOS pinning rules:
- `eos_ai/tiktok_ads_client.py` has a `API_VERSION = "v1.3"` constant
- Skill `last_researched` field tracks when we verified
- On 4xx error code containing "deprecated", page the human

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

The Marketing API is built around the Ads Manager UI surface — every screen
in Ads Manager has a corresponding endpoint, and the data shapes match the UI
fields one-to-one. This is why the JSON looks tedious (it preserves UI enum
strings like `BUDGET_MODE_DAY` instead of cleaner alternatives) but also why
it never surprises you: anything you can do in Ads Manager you can do via API,
and vice versa.

Tradeoffs TikTok chose:
- **HTTP 200 + body code** instead of HTTP status codes — enables consistent
  client-side parsing across SDK languages but trips integrators who use
  generic HTTP libraries.
- **Long-lived tokens** instead of refresh-token rotation — easier first-party
  integration, harder to handle revocation.
- **Per-advertiser auth scoping** — allows agencies to act on many clients
  with one app, at the cost of forcing `advertiser_id` into every request.
- **Numeric scope codes** — compact but unreadable; documentation is the only
  way to decode.
- **Synchronous + async reporting split** — sync is simple but capped, async
  is unlimited but takes minutes; integrators must pick.
- **Spark Ads as first-class** — TikTok deliberately privileges boosting
  organic content over polished ad creative because their data shows it
  outperforms 2-3x. The API rewards this with cleaner Spark endpoints than
  Custom creative endpoints.

## Problem-Solution Map and Hidden Capabilities

| Problem                                                     | Solution                                                              |
|-------------------------------------------------------------|-----------------------------------------------------------------------|
| Want to A/B test creative without fragmenting budget        | ACO (Automated Creative Optimization) — `ad/aco/create/`              |
| Want to test 5 hooks fast on one budget                     | One adgroup, 5 ad objects, OCPM, let auction pick                     |
| Boost a creator's post but creator won't add you to BC      | Per-video Spark Code, 365-day duration                                |
| Conversion tracking destroyed by Safari ITP                 | Events API + dedup `event_id` with browser pixel                      |
| Reporting too slow for dashboard                            | Async `report/task/create/`, cache CSV, refresh hourly                |
| Need cross-advertiser rollup                                | BC reporting endpoints (`bc/report/`), not per-advertiser loops       |
| Lead routing latency                                        | Lead form webhook → CF Worker → CRM, sub-second                       |
| Custom event optimization                                   | `pixel/event/create/` with custom name + Events API ingest            |
| Pause everything fast (kill switch)                         | `campaign/status/update/` with `operation_status=DISABLE` + all ids   |
| Find which ad caused a conversion                           | `attribution/conversion/get/` with `ttclid` filter                    |
| Automate creative refresh                                   | `tt_video/list/` for new authorized posts → `ad/create/` for boost    |
| Build a 1% lookalike of paying customers                    | Customer file Custom Audience → `lookalike_audience/create/`          |
| Geographic targeting beyond country                         | `tool/region/get/` for sub-region geoname IDs                         |
| Save hours building targeting bundles                       | `dmp/saved_audience/create/` then reference by id                     |

Hidden capabilities most users don't know:
- **`pixel/track/test/`** — fires a test event you can verify in Events
  Manager without affecting reporting.
- **`tool/language/get/`, `tool/region/get/`, `tool/interest_category/get/`** —
  the lookup tables for every targeting enum, documented poorly but essential.
- **`ad/review_info/`** — returns specific rejection reasons (e.g. "music
  copyright", "prohibited claim", "missing disclosure"). Critical for
  automation.
- **`comment/list/` + `comment/hide/`** — moderate ad comments via API.
- **`ad/draft/create/`** — save an ad as a draft for human review without
  going live.
- **`creative_asset/portfolio/`** — central asset library, reuse across
  advertisers in same BC.

## Operational Behavior and Edge Cases

- **Time zones are an iceberg.** The advertiser has a timezone set at account
  creation that cannot be changed. All `schedule_*`, `start_date`, `end_date`,
  and `stat_time_day` values are in *that* timezone. Always read
  `advertiser/info/` once and store. EOS stores it in `integrations.tiktok_ads.timezone`.
- **Spend reporting lags.** Real-time numbers are estimates; final billing
  reconciles in T+72 hours. For ROAS calculation always use T-3 days as the
  most recent reliable day.
- **Currency is per-advertiser** and cannot be changed. EOS keeps currency in
  the same row as timezone.
- **Creative review takes minutes-to-hours** depending on category. Beauty,
  finance, supplements get manual review. Adgroup will sit in `REVIEWING` until
  approved.
- **Dynamic Product Ads (DPA) require a Catalog** uploaded via
  `catalog/product/upload/` or feed URL. Catalog must be approved before any
  DPA campaign can launch.
- **Identity changes invalidate ads.** If you change an `identity_id` on an
  existing ad, TikTok re-reviews from scratch and reset learning.
- **Editing an ad in `DELIVERING` status resets the learning phase** — cost
  spikes for 50 conversions before stabilizing. Avoid mid-flight edits unless
  necessary; instead, duplicate-and-launch.
- **Custom audience size is fuzzed** to prevent reverse-engineering. A
  reported "≤1000" really means "below the privacy threshold," not literal.
  Lookalike seeds need ≥1000 *matched* records, not uploaded records.
- **Pangle placement is brand-unsafe** by default. EOS hard-codes
  `placements: ["PLACEMENT_TIKTOK"]` and never opts into Pangle without
  explicit human approval.

## Ecosystem Position and Composition

TikTok Marketing API sits alongside Meta Marketing API, Google Ads API, and
Reddit Ads API as the major paid social/search APIs. Vs the others:

- **Meta Marketing API**: more mature, more complex object graph
  (AdAccount/Campaign/AdSet/Ad/Creative), better webhooks, much better
  Audience Network. TikTok has cleaner Spark Ads, Meta has nothing equivalent
  to creator content boosting.
- **Google Ads API**: gRPC + protobufs, much steeper learning curve, far more
  granular bidding. TikTok is REST/JSON, much simpler, less powerful bidding.
- **Reddit Ads API**: smaller, less feature-rich, similar shape.

EOS composition:
- `tiktok` skill (organic) → identifies high-performing posts → fed to
  `tiktok_ads` skill → boosted as Spark Ads
- `tiktok_ads` reporting → Neon → morning brief
- Initiate Arena CRM → hashed customer file → `tiktok_ads` Custom Audience →
  Lookalike → adgroup targeting
- Initiate Arena checkout → eos_ai Events API client → `tiktok_ads`
  conversion signal → optimization
- `meta_ads` skill (when built) shares the same client pattern; the wrapper
  abstraction in `eos_ai/paid_media/` will normalize across both

Authority boundary: every paid media write goes through `authority_engine`
with risk class CRITICAL. Reads are LOW risk and ungated.

## Trajectory and Evolution

TikTok Marketing API moves fast. Historical pace:
- v1.0 (2020) — initial release, very limited
- v1.1 (2021) — Spark Ads added
- v1.2 (2022) — Events API, Lead Generation, BC overhaul
- v1.3 (2023, current) — Shop ads, Smart+ campaigns, GMV Max, AIGC label,
  multi-advertiser BC reports
- v1.4 (rumored 2026) — broader webhook support, real-time event stream,
  unified Smart+ object model

Direction signals:
- TikTok is consolidating campaign types under "Smart+" (similar to Meta
  Advantage+) — fewer manual knobs, more ML auto-pilot. Manual targeting
  exists but increasingly nudged toward broad + good signal.
- Events API + Conversion Lift studies are getting heavier promotion as
  signal-loss mitigation (post-iOS 14 / Safari ITP / GDPR).
- Spark Ads is now the recommended default in Ads Manager UI. The API
  already reflects this — `tt_video/auth_code/apply/` is the cleanest auth
  flow they've shipped.
- TikTok Shop API surface is rapidly expanding; Shop ads will likely become
  a peer surface to Marketing API for ecommerce-first integrations.

For EOS this means: bet on Spark Ads + Events API + broad targeting + good
creative signal, not on manual interest stacking. Anything we automate around
manual targeting will erode in value.

## Conceptual Model and Solution Recipes

### Recipe 1: Boost the founder's best organic post

```python
# 1. Pull last 14 days of organic TT metrics (from `tiktok` skill, Display API)
top = pick_top_post_by_engagement_rate(days=14)
# top = { "video_id": "7349...", "engagement_rate": 0.087, ... }

# 2. Resolve the BC identity for the founder's TT account
identity_id = get_bc_identity("@antonyfmunoz")

# 3. authority_engine approval gate
budget_request = {"daily_budget": 20.00, "duration_days": 7,
                  "objective": "WEB_CONVERSIONS", "post_id": top["video_id"]}
approval = authority_engine.request("paid_media.spark_ads", budget_request, risk="CRITICAL")
if not approval.granted:
    return

# 4. Create campaign DISABLED
campaign = client.call("POST", "/campaign/create/", json={
    "advertiser_id": ADV_ID,
    "campaign_name": f"IA-Spark-{top['video_id']}-{today}",
    "objective_type": "WEB_CONVERSIONS",
    "budget_mode": "BUDGET_MODE_DAY",
    "budget": 20.00,
})

# 5. Adgroup DISABLED, OCPM, optimization=COMPLETE_PAYMENT
adgroup = client.call("POST", "/adgroup/create/", json={
    "advertiser_id": ADV_ID, "campaign_id": campaign["campaign_id"],
    "adgroup_name": f"IA-US-25-44-{today}",
    "placement_type": "PLACEMENT_TYPE_NORMAL",
    "placements": ["PLACEMENT_TIKTOK"],
    "promotion_type": "WEBSITE", "pixel_id": PIXEL_ID,
    "optimization_event": "COMPLETE_PAYMENT",
    "billing_event": "OCPM", "bid_type": "BID_TYPE_NO_BID",
    "budget_mode": "BUDGET_MODE_DAY", "budget": 20.00,
    "schedule_type": "SCHEDULE_FROM_NOW",
    "schedule_start_time": now_advertiser_tz(),
    "location_ids": ["6252001"],
    "age_groups": ["AGE_25_34","AGE_35_44"],
    "operation_status": "DISABLE",
})

# 6. Spark Ad referencing organic post
ad = client.call("POST", "/ad/create/", json={
    "advertiser_id": ADV_ID, "adgroup_id": adgroup["adgroup_ids"][0],
    "creatives": [{
        "ad_name": f"IA-Spark-{top['video_id']}",
        "ad_format": "SINGLE_VIDEO",
        "identity_type": "TT_USER",
        "identity_id": identity_id,
        "tiktok_item_id": top["video_id"],
        "call_to_action": "LEARN_MORE",
        "landing_page_url": "https://initiatearena.com/?utm_source=tiktok&utm_campaign=spark",
    }],
})

# 7. Final human ENABLE — separate authority gate
audit.log("paid_media.spark_ads.created", {"campaign_id": campaign["campaign_id"], ...})
notify_human_to_enable(campaign["campaign_id"])
```

### Recipe 2: Send a CompletePayment from Initiate Arena checkout

```python
def send_purchase_to_tiktok(order):
    payload = {
        "event_source": "web",
        "event_source_id": PIXEL_CODE,
        "data": [{
            "event": "CompletePayment",
            "event_time": int(order.created_at.timestamp()),
            "event_id": f"ia-order-{order.id}",   # MUST match browser pixel
            "user": {
                "email": sha256(order.email.strip().lower()),
                "phone": sha256(to_e164(order.phone)),
                "external_id": sha256(str(order.user_id)),
                "ttclid": order.ttclid_cookie,
                "ttp": order.ttp_cookie,
                "ip": order.ip,
                "user_agent": order.user_agent,
            },
            "properties": {
                "currency": "USD",
                "value": float(order.total),
                "content_id": order.product_sku,
                "content_type": "product",
            },
            "page": {"url": order.success_url, "referrer": order.referrer},
        }],
    }
    client.call("POST", "/event/track/", json=payload)
```

### Recipe 3: Nightly reporting pull

```python
def pull_yesterday():
    yday = (date.today() - timedelta(days=1)).isoformat()
    res = client.call("GET", "/report/integrated/get/", params={
        "advertiser_id": ADV_ID,
        "report_type": "BASIC",
        "data_level": "AUCTION_AD",
        "dimensions": json.dumps(["ad_id","stat_time_day"]),
        "metrics": json.dumps(["spend","impressions","clicks","ctr","cpc","cpm",
                               "conversion","cost_per_conversion","conversion_rate"]),
        "start_date": yday, "end_date": yday,
        "page": 1, "page_size": 1000,
    })
    upsert_neon("paid_media.tiktok_daily", res["list"])
```

## Industry Expert and Cutting-Edge Usage

How sophisticated TikTok advertisers use the API in 2026:

- **Creative velocity over targeting precision.** Top accounts ship 20-50 new
  creatives per week and let the auction sort. The API enables this via
  `ad/create/` automation against a creative pipeline. Targeting stays broad
  (country + age band, nothing else).
- **Spark Ads everything.** No uploaded creative for top performers. Every
  ad references an organic post that's already proven engagement. Identity
  authorization is BC-level, not per-video.
- **Events API as primary, pixel as backup.** Server-side first, browser
  second, dedup'd via `event_id`. iOS 14.5 and Safari ITP made this mandatory.
- **Smart+ campaigns** (TikTok's Advantage+ equivalent) for ecommerce —
  delegates targeting + bidding + creative selection to TikTok. The API path
  is `campaign/create/` with `objective_type=PRODUCT_SALES` and minimal
  manual overrides.
- **GMV Max** for TikTok Shop — fully automated shop campaign type. API
  surface still maturing.
- **Conversion Lift Studies** (`measurement/lift/`) as the source of truth
  for incrementality, not last-click attribution.
- **Interest expansion + lookalikes from CRM segments** rather than manual
  interest stacking.
- **Hourly creative rotation cron** that pauses underperformers
  (CTR < 0.5% and spend > $50) and promotes new variants from the queue.
- **Cross-platform Conversions API hub** — single eos_ai service that fans
  out events to TikTok Events API, Meta CAPI, Google Enhanced Conversions in
  parallel. EOS will build this as `eos_ai/conversions_hub.py`.

## EOS Usage Patterns

Concrete patterns mapped to EOS modules and current binding constraints.

**Pattern 1: Spark Ads boost loop (the canonical pattern)**
- Trigger: `scripts/scheduled/spark_ads_boost.py` runs daily at 09:00 PT
- Reads: `tiktok` skill metrics for posts created 2-14 days ago
- Filter: engagement rate > top quintile, no existing boost
- Approval: authority_engine asks human in Discord with the post embedded,
  proposed budget, projected CPA based on prior spark performance
- On approve: creates campaign + adgroup + ad in DISABLED state, posts
  Discord confirmation with `/enable [campaign_id]` button
- On enable: flips to ENABLE via `campaign/status/update/`, logs to
  `audit.paid_media_changes`
- Daily: pull spend + conversions, write to Neon, surface in morning brief

**Pattern 2: Events API conversion fan-out**
- Module: `eos_ai/conversions_hub.py` (planned)
- Initiate Arena checkout success → POST to internal `/conversion` endpoint
  → fans out to TikTok Events API + (later) Meta CAPI + Google Enhanced
  Conversions in parallel
- All hashed identifiers, all with shared `event_id`
- Failure mode: never block checkout response on conversion fan-out; queue
  on failure, retry from scheduled worker

**Pattern 3: Custom audience refresh**
- Trigger: weekly, Sunday 03:00 PT
- Reads: Initiate Arena CRM, segments tagged `paid_traffic_eligible`
- Action: hash + upload customer file via
  `dmp/custom_audience/file/upload/`, then create/update Custom Audience
- Follow-up: refresh dependent Lookalike audiences

**Pattern 4: Kill switch**
- Trigger: anomaly detection on spend (cron every 15 min) — if hourly burn
  > 3x trailing 7-day average, fire kill switch
- Action: `campaign/status/update/` with `operation_status=DISABLE` for
  every active campaign in scope
- Notify: page human, log incident

**Pattern 5: Reporting → morning brief**
- Trigger: 05:30 PT cron
- Pull: 1-day, 7-day, 28-day rollups by ad
- Compute: ROAS, CPA trend, top + bottom performers
- Write: Neon `paid_media.tiktok_summary`
- Surface: morning brief Discord post with the 3 highest and 3 lowest
  performers, paused-recommendation flags

**Pattern 6: Sandbox first**
- All new code paths run against `sandbox-ads.tiktok.com` with the EOS
  sandbox token before touching prod
- Sandbox app + advertiser_id stored in `eos_ai/.env` as
  `TIKTOK_ADS_SANDBOX_*`

## Gotchas

- **HTTP 200 != success.** `body["code"] == 0` is the only truth test. Never
  trust `r.status_code`.
- **Wrong auth header.** `Access-Token: <token>`, not
  `Authorization: Bearer <token>`. Returns 40105.
- **`advertiser_id` must be a string.** Quoting matters in JSON bodies.
- **Array params in GET** must be JSON-then-URL-encoded:
  `metrics=%5B%22spend%22%5D`.
- **`BUDGET_MODE_INFINITE` is real.** Omit `budget_mode` and you can ship
  unbounded spend. Always set explicitly to `DAY` or `TOTAL`.
- **Min daily budget** is currency-specific (USD: $20 ad / $50 campaign).
  Below = 40002 with vague message.
- **Create with `operation_status=DISABLE`.** Never auto-enable from code.
  Human approval gate is non-negotiable.
- **Spark auth codes expire.** Track expiries. Prefer BC identity
  authorization for accounts you control.
- **`tiktok_item_id` is the numeric video id**, not the share URL. Extract
  from `/video/<ID>`.
- **Identity field combinations are picky.** `AUTH_CODE` needs `identity_id`
  + `identity_authorized_bc_id`. `TT_USER` needs only `identity_id` from
  your BC. `CUSTOMIZED_USER` for uploaded creative.
- **Events API silently drops unhashed PII.** Hash email lowercased trimmed,
  phone in E.164, then SHA-256. Verify in Events Manager → Test Events.
- **`event_source_id` IS the pixel code.** Confusing field name, same value
  shown in Ads Manager → Assets → Events.
- **Rate limits are per-app per-advertiser.** Burst → 40100. Backoff
  exponential with jitter.
- **`data_level` must match `dimensions`.** Mismatch = empty result, no
  error.
- **Reporting is in advertiser timezone**, not UTC. Read once, store.
- **Spend reporting lags** ~72h to final reconciliation. Use T-3 for ROAS
  calcs.
- **Sandbox can't serve real ads** or use real pixels — schema validation
  only.
- **Webhooks are limited** — only lead forms, MMP, BC membership, catalog.
  Poll everything else.
- **`event_id` mismatch** between pixel and CAPI = double-counted
  conversions = bad optimization.
- **`promotion_type` must match `optimization_event`.** WEBSITE needs
  pixel events; APP needs MMP events; LEAD_GEN needs form id.
- **Ubuntu cron jobs need explicit env.** `TIKTOK_ADS_TOKEN` and
  `ADVERTISER_ID` must be exported in the cron line, not assumed from shell.
- **`pacing` defaults to smooth** but `BID_TYPE_NO_BID` can still front-load
  early in the day. Watch first 4 hours of any new adgroup.
- **Editing in DELIVERING resets learning.** Avoid mid-flight edits;
  duplicate-and-launch instead.
- **Creative review can take hours** for regulated verticals. Schedule new
  campaigns with a 4-hour buffer.
- **Lookalike seeds need ≥1000 matched records**, not uploaded records.
  Upload 5K-10K to seed reliably.
- **Pangle placement is brand-unsafe** for premium positioning. Hard-code
  `["PLACEMENT_TIKTOK"]` only.
- **`request_id` is essential for support.** Log it on every error.
- **TikTok Login Kit token != Marketing API token.** Different identity
  provider, different host, different shape. Never confuse them.
- **v1.2 documentation is still indexed and wrong.** Always confirm v1.3
  before copying any tutorial code.
