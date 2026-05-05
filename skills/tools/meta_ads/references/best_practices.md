# Meta Marketing API (meta_ads) — Creator-Level Best Practices
Source: developers.facebook.com/docs/marketing-api, github.com/facebook/facebook-python-business-sdk, Meta Marketing API changelogs v22-v25
API Version: v23.0 stable / v24.0 / v25.0 latest (quarterly cadence, ~24 month support window)
SDK Version: facebook-business 25.0.0 (Python, March 2026); facebook-nodejs-business-sdk 25.x
Last Researched: 2026-04-06

Cross-reference: `meta_graph_api` skill owns OAuth, version cadence, webhook
infrastructure, and the Graph URL surface common to all Meta products. This
document does not duplicate that material — it focuses on what is unique to
the paid-media slice.

---

# Tier 1 — Technical Mastery

## Authentication

The Marketing API rides on the same OAuth + access-token model as the rest of
Graph (see `meta_graph_api` for the token-exchange dance). The deltas that
matter for ads:

**Permission scopes (declared at app review):**

- `ads_management` — write access to ad accounts (create, update, delete
  campaigns/ad sets/ads/creatives/audiences, upload custom audiences)
- `ads_read` — read-only Insights and configuration
- `business_management` — assign assets, manage business users, create system
  users, register pixels to ad accounts
- `pages_show_list` + `pages_read_engagement` — required if your creatives
  reference page posts (almost all do)
- `instagram_basic` + `pages_show_list` — required if creatives publish to an
  Instagram business account
- `leads_retrieval` — required to download lead form submissions

**Access tiers (Marketing API specific):**

- **Development access** — auto-granted at app creation. Tiny rate quota
  (~60 score, decay 300s, block 300s on overrun). Limited to 5 ad accounts
  the developer admins. Useful for sandbox.
- **Standard access** — requires App Review submission against Marketing API.
  ~9000 score, decay 300s, 60s block on overrun, plus the BUC formula
  (100k base + 40 * active ads per hour). Required for any production system
  doing nightly Insights pulls or managing more than a handful of campaigns.

**Token types — only one is correct for production:**

| Token type            | Lifespan       | Production-suitable? |
|-----------------------|----------------|----------------------|
| Short-lived user      | ~1-2 hours     | NO                   |
| Long-lived user       | ~60 days       | NO (still expires)   |
| Page                  | matches user   | NO (wrong scope)     |
| **System user**       | **non-expiring** under Standard tier | **YES** |
| App access            | non-expiring   | NO (insufficient permissions for ads) |

**Generating a system user token:**

1. Business Settings → Users → System Users → Add → name + role
2. Add Assets → Apps → assign your app with full control
3. Add Assets → Ad Accounts → assign with Manage role
4. Add Assets → Pages → assign with Create Content role
5. Generate New Token → pick app → check `ads_management`, `ads_read`,
   `business_management`, `pages_manage_ads`, `leads_retrieval`
6. Choose token expiration: **Never** (only available at Standard tier)
7. Copy ONCE. Token is hashed server-side after the modal closes — there is
   no recovery if you lose it.

**App secret proof:**

Required on every server-side call when "Require App Secret" is enabled in
the app dashboard (you should always enable it).

```python
import hashlib, hmac
appsecret_proof = hmac.new(
    app_secret.encode('utf-8'),
    access_token.encode('utf-8'),
    hashlib.sha256,
).hexdigest()
# Pass as ?appsecret_proof=... or in form body
```

The Python SDK includes this automatically when `app_secret` is passed to
`FacebookAdsApi.init()`. The Node SDK does not — you must compute and append.

**Token health monitoring:**

```bash
curl "https://graph.facebook.com/v23.0/debug_token?input_token=${TOKEN}&access_token=${APP_ID}|${APP_SECRET}"
```

Returns `is_valid`, `expires_at` (0 = never), `scopes`, `data_access_expires_at`.
Check daily — system user tokens CAN be invalidated by Business admin password
reset, app secret rotation, app suspension, or 90 days of total inactivity.

## Core Operations with Exact Signatures

All endpoints under `https://graph.facebook.com/v23.0/`. Object IDs are
opaque numeric strings; ad account IDs are prefixed `act_<id>` in URLs and
SDK constructors but bare `<id>` in JSON request bodies for some legacy
fields.

### Ad Account

```
GET    /act_{ad-account-id}                            # read
GET    /act_{ad-account-id}/campaigns                  # list children
GET    /act_{ad-account-id}/adsets
GET    /act_{ad-account-id}/ads
GET    /act_{ad-account-id}/adcreatives
GET    /act_{ad-account-id}/customaudiences
GET    /act_{ad-account-id}/insights
POST   /act_{ad-account-id}/campaigns                  # create campaign
POST   /act_{ad-account-id}/adsets                     # create ad set
POST   /act_{ad-account-id}/ads                        # create ad
POST   /act_{ad-account-id}/adcreatives                # create creative
POST   /act_{ad-account-id}/customaudiences            # create audience
POST   /act_{ad-account-id}/customaudiences/{id}/users # upload users
```

### Campaign

```
POST /act_{ad-account-id}/campaigns
  name                    (str, required)
  objective               (enum, required) — OUTCOME_AWARENESS|OUTCOME_TRAFFIC|
                          OUTCOME_ENGAGEMENT|OUTCOME_LEADS|OUTCOME_APP_PROMOTION|
                          OUTCOME_SALES
  status                  (enum) — ACTIVE|PAUSED|DELETED|ARCHIVED
  special_ad_categories   (list, REQUIRED — pass [] if none)
  buying_type             (enum) — AUCTION (default) | RESERVED
  daily_budget            (int, cents) — campaign budget optimization
  lifetime_budget         (int, cents)
  bid_strategy            (enum) — LOWEST_COST_WITHOUT_CAP | LOWEST_COST_WITH_BID_CAP |
                          COST_CAP | LOWEST_COST_WITH_MIN_ROAS
  spend_cap               (int, cents) — hard ceiling
  start_time              (ISO8601)
  stop_time               (ISO8601)
  campaign_optimization_type (enum)
  is_skadnetwork_attribution (bool) — required for iOS app campaigns

GET    /{campaign-id}
POST   /{campaign-id}                                  # update
DELETE /{campaign-id}
```

### Ad Set (the most important object)

```
POST /act_{ad-account-id}/adsets
  name                       (str, required)
  campaign_id                (str, required)
  status                     (enum)
  daily_budget | lifetime_budget (int, cents — required unless CBO at campaign)
  billing_event              (enum) — IMPRESSIONS | LINK_CLICKS | THRUPLAY |
                             APP_INSTALLS | PAGE_LIKES | POST_ENGAGEMENT
  optimization_goal          (enum) — REACH | IMPRESSIONS | LINK_CLICKS |
                             OFFSITE_CONVERSIONS | LEAD_GENERATION |
                             LANDING_PAGE_VIEWS | THRUPLAY | VALUE | etc.
  bid_amount                 (int, cents) — required for some bid strategies
  bid_strategy               (enum)
  targeting                  (object — see Data Model)
  promoted_object            (object) — page_id | pixel_id+custom_event_type |
                             application_id | product_set_id
  attribution_spec           (list) — [{event_type:CLICK_THROUGH,window_days:7}]
  start_time, end_time       (ISO8601)
  destination_type           (enum) — UNDEFINED | WEBSITE | APP | MESSENGER |
                             INSTAGRAM_DIRECT | WHATSAPP | ON_AD | ON_POST | ON_PAGE
  is_dynamic_creative        (bool)
  dynamic_creative_call_to_action_type
```

### Ad

```
POST /act_{ad-account-id}/ads
  name                  (str, required)
  adset_id              (str, required)
  creative              ({creative_id: <id>} or inline spec, required)
  status                (enum)
  tracking_specs        (list)
  conversion_specs      (list)
  adlabels              (list)
```

### Ad Creative

```
POST /act_{ad-account-id}/adcreatives
  name                  (str)
  object_story_spec     (object) — page_id + link_data | photo_data | video_data |
                        text_data | template_data
  asset_feed_spec       (object) — for dynamic creative / Advantage+ creative
  url_tags              (str)   — appended UTM tags
  degrees_of_freedom_spec (object) — Advantage+ creative enhancements opt-in
```

`object_story_spec.link_data` shape:

```json
{
  "page_id": "<page-id>",
  "link_data": {
    "message": "Body copy",
    "link": "https://initiatearena.com/?utm_campaign=ia_lead_2026_04",
    "name": "Headline",
    "description": "Description",
    "image_hash": "<from /act_{}/adimages>",
    "call_to_action": {"type": "BOOK_TRAVEL", "value": {"link": "..."}}
  }
}
```

### Custom Audience

```
POST /act_{ad-account-id}/customaudiences
  name                (str, required)
  subtype             (enum) — CUSTOM | WEBSITE | APP | LOOKALIKE | ENGAGEMENT |
                      DATA_SET | OFFLINE_CONVERSION
  description         (str)
  customer_file_source (enum) — USER_PROVIDED_ONLY | PARTNER_PROVIDED_ONLY |
                       BOTH_USER_AND_PARTNER_PROVIDED  (REQUIRED for CUSTOM)
  rule                (object — for WEBSITE / ENGAGEMENT)

POST /{audience-id}/users
  payload = {
    "schema": ["EMAIL","PHONE","FN","LN","COUNTRY"],
    "data":   [["<sha256>","<sha256>","<sha256>","<sha256>","us"], ...]
  }
```

### Lookalike

```
POST /act_{ad-account-id}/customaudiences
  name           (str)
  subtype        "LOOKALIKE"
  origin_audience_id  (str — seed audience, must have ≥100 matched people)
  lookalike_spec      (object) — {"type":"similarity"|"reach","ratio":0.01-0.10,
                                  "country":"US"} OR
                                 {"type":"custom_ratio","ratio":...,
                                  "starting_ratio":..,"country":..}
```

### Pixel

```
POST /act_{ad-account-id}/adspixels
  name (str)
GET  /{pixel-id}/stats
POST /{pixel-id}/shared_accounts
POST /{pixel-id}/events                                # CAPI ingestion
```

### Conversions API

```
POST /{pixel-id}/events                                # also /{dataset-id}/events
  data = [
    {
      event_name        (str, required) — Purchase, Lead, InitiateLead, etc.
      event_time        (int, unix, required, ≤7d old)
      event_id          (str — for dedup with pixel)
      event_source_url  (str)
      action_source     (enum, required since v12+) — website|app|email|chat|
                        physical_store|system_generated|business_messaging|other
      user_data         (object — hashed identifiers)
        em (list[sha256])  — email
        ph (list[sha256])  — phone (E.164, country code, no +)
        fn, ln, ct, st, zp, country, ge, db, external_id (all sha256, lowercased)
        client_ip_address (raw)
        client_user_agent (raw)
        fbc, fbp          (Facebook click ID + browser ID, raw)
      custom_data       (object) — value, currency, content_ids, contents,
                                   content_type, num_items, predicted_ltv
      opt_out           (bool)
    }
  ]
  test_event_code     (str, optional) — for Test Events tab
  partner_agent       (str)
```

Response includes `events_received`, `messages` (warnings), `fbtrace_id`.

### Insights (sync)

```
GET /act_{ad-account-id}/insights      # also /{campaign}/insights, /{adset}/insights, /{ad}/insights
  fields                  (csv) — campaign_name, impressions, reach, frequency,
                          spend, clicks, ctr, cpc, cpm, cpp, actions, action_values,
                          conversions, conversion_values, video_p25/50/75/100_watched_actions,
                          purchase_roas, website_purchase_roas, etc.
  level                   (enum) — account | campaign | adset | ad
  date_preset             (enum) — today | yesterday | last_3d | last_7d | last_14d |
                          last_28d | last_30d | last_90d | this_month | last_month |
                          this_quarter | maximum
  time_range              ({since:'YYYY-MM-DD',until:'YYYY-MM-DD'})
  time_increment          (int days | 'monthly' | 'all_days')
  breakdowns              (csv) — age, gender, country, region, dma, impression_device,
                          publisher_platform, platform_position, device_platform,
                          product_id, hourly_stats_aggregated_by_advertiser_time_zone
  action_breakdowns       (csv) — action_type, action_target_id, action_destination,
                          action_device, action_video_sound, action_carousel_card_id
  action_attribution_windows (csv) — 1d_view, 7d_view, 1d_click, 7d_click, 28d_click
  filtering               (json) — [{field:'spend',operator:'GREATER_THAN',value:100}]
  use_unified_attribution_setting (bool)
  limit                   (int)
```

### Insights (async — required for big jobs)

```
POST /act_{ad-account-id}/insights      # same params as GET, returns report_run_id
GET  /{report_run_id}                    # poll: async_status, async_percent_completion
GET  /{report_run_id}/insights           # fetch results when async_status == 'Job Completed'
```

`async_status` values: `Job Started`, `Job Running`, `Job Completed`,
`Job Failed`, `Job Skipped`.

## Pagination Patterns

Graph paging applies (cursors). The Marketing API has three pagination flavors:

**Cursor pagination (default):** `paging.cursors.before/after`. Use SDK
iterators (`for x in account.get_campaigns()`) — they handle next-page fetching
automatically.

**Time-based pagination:** for `time_range` Insights, paginate by date window
yourself, not by API cursor. Splitting a 90-day window into 9x10-day requests
is faster and far less likely to hit error 17 than asking for 90 days at once.

**Async report pagination:** results are paginated with cursors after the
report job completes. Always set `limit=500` or higher; default 25 means
thousands of round-trips for an account-level pull.

```python
campaigns = account.get_campaigns(fields=['name','status'])
for c in campaigns:                         # SDK auto-pages
    print(c['name'])
```

```python
import time
job = account.get_insights_async(
    fields=['campaign_name','spend','actions'],
    params={'level':'campaign','time_range':{'since':'2026-01-01','until':'2026-03-31'}},
)
job.api_get()
while job[AdReportRun.Field.async_status] not in ('Job Completed','Job Failed','Job Skipped'):
    time.sleep(5)
    job.api_get()
for row in job.get_result(params={'limit': 500}):
    ...
```

## Rate Limits

Marketing API has its OWN bucket — separate from generic Graph API rate
limits. Two layers stack on top of each other:

**1. Business Use Case (BUC) limits — per ad account, per BUC bucket:**

| BUC                   | Standard Tier formula                          | Dev Tier |
|-----------------------|------------------------------------------------|----------|
| `ads_management`      | 100,000 + (40 × active ads) per hour           | 300 + (40 × active ads) |
| `ads_insights`        | 190,000 + (40 × active ads) per hour           | 600 + (40 × active ads) |
| `custom_audience`     | 700,000 + (40 × active ads) per day            | severely limited |

These are point pools; each call deducts a varying number of points by
endpoint complexity. Exposed in the response header:

```
X-Business-Use-Case-Usage:
{"<ad_account_id>":[{"type":"ads_management",
  "call_count":42,"total_cputime":18,"total_time":15,
  "estimated_time_to_regain_access":0}]}
```

When any of `call_count`, `total_cputime`, `total_time` reach 100, you are
throttled. `estimated_time_to_regain_access` is in minutes. Read this header
on every response and back off proactively at ≥75.

**2. Per-app score (the older limit, still enforced):**

- Standard tier: max score 9000, decay 300s, 60s block on overrun
- Dev tier: max score 60, decay 300s, 300s block on overrun

**3. Custom audience write quota:** ~10,000 update operations per hour per
account. Bulk uploads count as one op per request, not per row.

**4. CAPI quota:** 1000 events per request, 5000 requests per second per
pixel. Effectively unlimited for any small business — but always batch.

## Error Codes and Recovery

| Code   | Subcode | Meaning                                | Action                  |
|--------|---------|----------------------------------------|-------------------------|
| 1      | —       | Unknown / temporary server             | Retry with backoff      |
| 2      | —       | Service temporarily unavailable        | Retry with backoff      |
| 4      | —       | App-level rate limit                   | Backoff, slow down      |
| 17     | —       | User-level rate limit (Insights)       | Switch to async / batch |
| 100    | —       | Invalid parameter                      | Fix params, do not retry|
| 100    | 1487749 | Operating budget too low for objective | Raise budget            |
| 102    | —       | Session expired / token invalid        | Refresh, alert human    |
| 190    | —       | Access token error                     | Refresh, alert human    |
| 200    | —       | Permissions error                      | Re-review scopes        |
| 200    | 1349125 | Page not assigned to user              | Assign in BM            |
| 270    | —       | Permission required for resource       | Add scope               |
| 368    | —       | Action attempt limit exceeded          | 24h cooldown            |
| 80004  | —       | Too many calls — BUC throttled         | Backoff per header      |
| 1487007| —       | Invalid creative — image spec wrong    | Fix asset               |
| 1487390| —       | Custom audience too small              | Need ≥100 matched users |
| 1885041| —       | Pixel not assigned to ad account       | /{pixel}/shared_accounts|
| 2635   | —       | App in dev mode for prod resource      | Submit for review       |

**Retry policy that actually works:**

```python
import random, time
RETRYABLE = {1, 2, 4, 17, 80004, 368}
def call_with_retry(fn, max_attempts=5):
    for attempt in range(max_attempts):
        try:
            return fn()
        except FacebookRequestError as e:
            code = e.api_error_code()
            if code not in RETRYABLE or attempt == max_attempts - 1:
                raise
            sleep = (2 ** attempt) + random.random()
            time.sleep(sleep)
```

Honor the BUC header instead of blind exponential when available — wait
`estimated_time_to_regain_access` minutes.

## SDK Idioms

### facebook-business (Python) — the canonical idioms

```python
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.customaudience import CustomAudience
from facebook_business.adobjects.adreportrun import AdReportRun
from facebook_business.exceptions import FacebookRequestError
```

**Init once per process:**

```python
FacebookAdsApi.init(
    app_id=APP_ID, app_secret=APP_SECRET, access_token=TOKEN,
    api_version='v23.0', crash_log=False, proxies=None,
)
```

**Field constants instead of strings** (catches typos at import time):

```python
campaign = AdAccount(f'act_{ACT}').create_campaign(params={
    Campaign.Field.name: 'IA Lead Gen 2026-04',
    Campaign.Field.objective: Campaign.Objective.outcome_leads,
    Campaign.Field.special_ad_categories: [],
    Campaign.Field.status: Campaign.Status.paused,
})
```

**Lazy fetching** — accessing a field on a freshly-created object hits the
network unless you `fields=[...]` first:

```python
c = Campaign(campaign_id)
c.api_get(fields=[Campaign.Field.name, Campaign.Field.objective])
print(c[Campaign.Field.name])
```

**Batch requests** for shaving round trips (≤50 per batch):

```python
api = FacebookAdsApi.get_default_api()
batch = api.new_batch()
for ad_id in ad_ids:
    Ad(ad_id).api_get(fields=['effective_status'], batch=batch,
                      success=lambda resp: results.append(resp.json()))
batch.execute()
```

**Async insights** — use `AdReportRun` polling pattern shown above.

### Node SDK gotcha

`facebook-nodejs-business-sdk` does NOT auto-add `appsecret_proof`. You must
compute it and append to every request. This is the #1 production silent-fail
pattern when porting Python code to Node.

## Anti-Patterns

- **Manual user-token refresh in production.** System user tokens exist
  precisely so you never have to. If you're refreshing tokens nightly, you
  set up the wrong credential.
- **Creating campaigns with `objective='CONVERSIONS'`.** Banned since v21.0.
  Use `OUTCOME_SALES` with `optimization_goal=OFFSITE_CONVERSIONS` on the ad set.
- **Hashing PII on the wire (raw email in payload, hashed on server).**
  Privacy violation; fix by hashing client-side before the request leaves
  your process.
- **Polling Insights every 5 minutes for "real-time" dashboards.** Insights
  has 15-30 min delay regardless. Poll every 30 min, hourly is better, and
  use Conversions API + your own pixel events for true real-time.
- **One ad set per ad.** Defeats the optimizer, fragments learning phase,
  and pushes every set into "Learning Limited." Consolidate aggressively.
- **Daily budget changes >20%.** Resets the learning phase. Change <20% per
  day or batch into one larger move.
- **Pause/resume cycles for "tests."** Each resume = new learning phase. Use
  a separate test ad set or A/B Test feature instead.
- **Putting URLs in creative `message`/copy fields and forgetting `link`.**
  Facebook strips URLs from message; the actual click target must be `link`.
- **Targeting nested too narrow** (interest AND interest AND interest with
  age 25-26 in one zip code). Audience size <50k = high CPM, slow learning,
  often "Audience Too Small" delivery warning.
- **Ignoring `effective_status`** when iterating ads — `status` is what you
  set, `effective_status` is the live state (PENDING_REVIEW, DISAPPROVED,
  CAMPAIGN_PAUSED, ADSET_PAUSED, etc.). The two often disagree.
- **Building lookalikes from <1000 person seeds.** Match quality is too low.
  Real lookalikes need 1000-50,000 high-quality seeds.
- **Sending CAPI events without `action_source`.** Required field since v12;
  missing = silent drop with `messages` warning you have to log to see.

## Data Model

### The four-level tree

```
AdAccount (act_<id>)
├── Campaigns (objective, budget if CBO, special_ad_categories, buying_type)
│   ├── AdSets (targeting, budget, bid, optimization_goal, billing_event,
│   │           schedule, placements, promoted_object, attribution_spec)
│   │   └── Ads (creative + tracking_specs + conversion_specs)
│   │
└── AdCreatives (object_story_spec | asset_feed_spec, url_tags)
    └── (referenced by ads, reusable across ads/ad sets)

AdAccount also has, at the same level as Campaigns:
├── CustomAudiences   (CUSTOM, WEBSITE, ENGAGEMENT, LOOKALIKE, OFFLINE)
├── AdImages          (image_hash → reference in creatives)
├── AdVideos          (video_id → reference in creatives)
├── AdsPixels         (server-side events + browser pixel)
├── AdLabels          (free-form tags)
├── BusinessAssets    (assigned via Business Manager)
```

### Targeting object — the most important shape

```json
{
  "geo_locations": {
    "countries": ["US"],
    "regions": [{"key": "3847"}],
    "cities": [{"key":"2418779","radius":25,"distance_unit":"mile"}],
    "zips": [{"key":"US:97201"}],
    "location_types": ["home","recent"]
  },
  "age_min": 25,
  "age_max": 55,
  "genders": [1,2],
  "locales": [6,24],
  "publisher_platforms": ["facebook","instagram","messenger","audience_network"],
  "facebook_positions": ["feed","story","reels","marketplace","video_feeds"],
  "instagram_positions": ["stream","story","reels","explore","explore_home"],
  "device_platforms": ["mobile","desktop"],
  "user_os": ["iOS","Android"],
  "flexible_spec": [
    {
      "interests": [{"id":"6003107902432","name":"Personal development"}],
      "behaviors": [{"id":"6002714895372","name":"Engaged shoppers"}]
    },
    {
      "custom_audiences": [{"id":"<lookalike-id>"}]
    }
  ],
  "exclusions": {
    "custom_audiences": [{"id":"<existing-customers-id>"}]
  },
  "targeting_optimization": "expansion_all",
  "targeting_automation": {
    "advantage_audience": 1,
    "individual_setting": {
      "age": 1,
      "gender": 1
    }
  }
}
```

`flexible_spec` arrays are AND-of-ORs: each array element is OR'd internally,
the elements themselves are AND'd together. `exclusions` is always AND-NOT.

### CAPI user_data normalization (OFFICIAL rules)

| Field | Normalize before SHA256                                  |
|-------|----------------------------------------------------------|
| em    | trim, lowercase                                          |
| ph    | digits only, country code prefix, no `+`                 |
| fn,ln | trim, lowercase, strip punctuation, NO accents stripping |
| ct    | trim, lowercase, strip non-alpha                         |
| st    | 2-letter code, lowercase                                 |
| zp    | first 5 digits (US), trim+lowercase otherwise            |
| country | 2-letter ISO code, lowercase                           |
| ge    | `m` or `f`                                               |
| db    | YYYYMMDD                                                 |

Hash with SHA-256, lowercase hex output. NEVER pass raw PII to Meta.

## Webhooks and Events

The Marketing API exposes the standard Graph webhook subscription model
(see `meta_graph_api`) plus four ad-specific topics:

- **`ad_account`** — fires on changes to ad accounts you're subscribed to
  (status, spend, billing). Useful for "account just got disabled" alerts.
- **`leadgen`** — fires when a lead is submitted via a Lead Ad form. The
  webhook payload includes `leadgen_id`; you GET `/{leadgen-id}?fields=field_data`
  to fetch the actual lead. Requires `leads_retrieval` permission. **This is
  the canonical pattern for piping leads into a CRM.**
- **`ad_review_status`** — fires when a creative moves between review states
  (PENDING_REVIEW → APPROVED, → DISAPPROVED). Useful for paging a human on
  rejection.
- **`page` (with `feed` field)** — for boosted posts triggered by org content.

Webhook payload for leadgen:

```json
{
  "object": "page",
  "entry": [{
    "id": "<page-id>",
    "time": 1712345678,
    "changes": [{
      "field": "leadgen",
      "value": {
        "ad_id": "...",
        "form_id": "...",
        "leadgen_id": "...",
        "created_time": 1712345670,
        "page_id": "...",
        "adgroup_id": "..."
      }
    }]
  }]
}
```

Always re-fetch the lead body from `/{leadgen-id}?fields=field_data,created_time`
within ~30 days; lead content is GDPR-purgeable after that.

## Limits

**Tree shape:**

- 5,000 ad sets per ad account (hard cap)
- 5,000 ads per ad account (hard cap)
- 200 ad sets per campaign (recommended; soft enforcement at ~250)
- 50 ads per ad set (hard cap)
- 200 creatives per asset feed spec (Advantage+ creative)
- 50 simultaneous active campaigns recommended (no hard cap; learning suffers)

**Targeting:**

- Custom audience minimum size for delivery: 1,000 people
- Lookalike seed minimum: 100 matched people (1,000+ recommended)
- Lookalike ratio: 1-10% of country population (0.01-0.10)
- Detailed targeting flex specs: max 5 inclusion + 5 exclusion groups
- Locations: 200 max per ad set (cities/zips combined)

**Custom audience uploads:**

- 10,000 users per HTTPS request payload
- 700,000 update operations per day per account (Standard tier)
- Audiences become "Ready" within 30 minutes for ≤100k users; up to 24h for
  multi-million

**Creative:**

- Image: max 30MB, recommended 1080×1080 / 1080×1350 / 1080×1920
- Video: max 4GB, max 241 minutes, MP4/MOV/GIF, H.264 codec
- Headline: 27 char recommended (40 hard cap on most placements)
- Primary text: 125 char recommended (no hard cap, gets truncated)
- Description: 27 char recommended
- Carousel: 2-10 cards

**Insights:**

- Sync request: ~50,000 rows hard cap, often errors at ~10k
- Async report: ~37 months historical max, 100k rows per result page
- Report retention: 60 days from completion before deletion
- max 100 reports per day per account

## Cost Model

The API itself is free. You pay for ad delivery. There is no per-call charge,
no Conversions API charge, no Insights charge.

What costs money inside the surface:

- **Ad spend** — billed via the ad account's payment method. `spend_cap` on
  the campaign or account is the only hard ceiling. Always set both.
- **Custom audience matching** — free, but matched audiences <100 people
  refuse to deliver (no cost incurred, just no impressions).
- **CAPI** — free. There is no event quota cost.

What can SURPRISE-cost you:

- **CBO with no `spend_cap`** — Meta will spend your daily budget across all
  ad sets. Without a cap, a runaway script that creates 50 ad sets each at
  $50/day = $2500/day even if you only intended one.
- **Lifetime budgets without an `end_time`** — runs indefinitely. Always set
  both.
- **Test campaigns left ACTIVE in production accounts** — agents that forget
  to set `status=PAUSED` on creation are how every single first-time API user
  gets surprise-billed. Default to PAUSED at write, require explicit activate.

## Version Pinning

- Pin every call: `https://graph.facebook.com/v23.0/...` — never use
  `/latest/` or unversioned paths.
- Set the SDK version explicitly: `FacebookAdsApi.init(api_version='v23.0')`.
- Meta releases a new version each quarter. Each version is supported for
  ~24 months. v23.0 is the current stable choice for new code as of
  2026-04-06; v24.0 and v25.0 are available but each contains breaking
  changes (the v24.0 ASC/AAC ban being the most disruptive recent one).
- Track the official changelog at
  `developers.facebook.com/docs/marketing-api/marketing-api-changelog/`.
- When upgrading, run a parallel pin test: read the same data through both
  versions, diff the result, fix breakages BEFORE swapping.
- Hard breaking changes that have happened recently:
  - v21.0: legacy objectives banned for new creation
  - v22.0: action_attribution_window default changes
  - v23.0: Advantage+ Audience opt-in by default; `instagram_destination_id`
    semantic flip; `targeting_automation.individual_setting` for age/gender
  - v24.0: ASC/AAC creation banned via legacy APIs
  - v25.0: deprecation of additional non-ODAX legacy fields

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

The Marketing API was designed around a few opinionated assumptions:

**1. Auction efficiency first, advertiser control second.** Every product
direction since 2020 has moved decisions OUT of the advertiser's hands and
INTO Meta's optimizer (Advantage+ everything, ODAX consolidating 11
objectives into 6, learning phase enforcement, 50-event-per-week minimum).
Building tools that fight this — narrow targeting, tiny budgets, manual
bidding — increasingly underperforms vs tools that lean in.

**2. iOS ATT broke pixel attribution; CAPI is the band-aid.** Apple's App
Tracking Transparency (2021) collapsed Meta's ability to attribute web
conversions on iOS Safari. CAPI exists to recover what the pixel can no
longer see. The API has been redesigned around the assumption that you will
ship server-side events; advertisers who don't are penalized in CPA and
delivery quality.

**3. Business Manager is the unit of trust, not the user.** Permissions,
asset assignment, audit, billing — all flow through Business Manager. The
"system user" concept exists because users come and go but businesses stay.
Long-running automation should never depend on a human user account.

**4. The four-level tree is intentionally inflexible.** You cannot put
targeting on a campaign or budget on a creative. This forces consolidation —
Meta wants 5 ad sets with 5 ads each, not 50 ad sets with 1 ad each, because
the former is what the optimizer is good at.

The tradeoff: simple use cases (boost a post, run one ad) are weirdly hard;
complex use cases (multi-campaign, multi-creative, multi-audience portfolios
on autopilot) are weirdly easy.

## Problem-Solution Map and Hidden Capabilities

| Problem                                  | The right Meta tool                                        |
|------------------------------------------|-----------------------------------------------------------|
| iOS conversion gap                       | CAPI with `action_source=website` + matching `event_id`   |
| Same creative across many countries      | Asset Customization Rules on the ad creative              |
| Lead form into CRM in real time          | `leadgen` webhook + `/{leadgen-id}?fields=field_data`     |
| Test 10 headlines + 5 images automatically | Dynamic Creative on the ad set + asset_feed_spec        |
| Stop optimizer wasting on losing ads     | Rules API (`/{ad-account}/adrules_library`) — auto-pause  |
| Dedupe a customer list before upload     | Use `external_id` + `email` + `phone` together; multi-key |
| One creative across Page + IG + Reels    | `placement_asset_customization_rules` in asset_feed_spec  |
| Find when a campaign last had budget edit | `/{campaign}/adactivities` — full audit log              |
| Bulk update many ad sets at once         | `/{adaccount}/adsets?ids=a,b,c` POST batch                |
| Predict result before launching          | `/{adaccount}/delivery_estimate` — reach & impressions estimate |
| A/B test cleanly                         | `/{adaccount}/ab_test_runs` — managed split test          |

**Hidden capabilities most teams don't use:**

- **`adrules_library`** — full automation rules (pause when CPA > $X, scale
  when ROAS > Y) created via API, not just the UI
- **`/delivery_estimate`** — pre-flight reach/impression forecast before
  spending money
- **`copy_campaign` / `copy_adset`** — server-side duplication without
  re-uploading creatives
- **`adactivities`** — time-stamped audit log of every change to a tree node
- **`saved_audiences`** — reusable targeting templates separate from
  custom audiences
- **`reach_estimate`** — given a targeting spec, returns expected daily reach
- **`generatepreviews`** — render an ad preview HTML/iframe BEFORE launching
- **`/insights?export_format=CSV`** — direct CSV download of report results
- **`adset.recommendations`** — Meta's own optimizer suggestions, surfaced
  through the API for agent ingestion
- **Lead Ad CRM integration** — CRM-to-CRMs adapter via `crm_setup` form

## Operational Behavior and Edge Cases

**Learning phase** — Every ad set entering optimization or any "significant
edit" enters Learning Phase, lasting until 50 optimization events occur in
~7 days. During learning, performance is inconsistent and CPA is unreliable.
Significant edits include: bid changes, budget changes >20%, optimization
goal changes, audience changes, creative additions/removals.

**Effective vs configured status** — `status` is what you set; `effective_status`
is what the system actually shows. Six common effective states:

- `IN_PROCESS` — being created
- `WITH_ISSUES` — disapproval, rejected creative, etc.
- `PENDING_REVIEW` — waiting on Meta's automated review
- `CAMPAIGN_PAUSED`, `ADSET_PAUSED` — paused at a higher level
- `DISAPPROVED` — creative violates policy
- `ARCHIVED` — soft-deleted

Always read `effective_status`, never trust `status` alone.

**Currency and money** — All monetary fields are in account currency MINOR
units (cents for USD, yen for JPY which has no minor unit). Do not divide
by 100 universally — check the account's currency.

**Insights freshness** — Live Insights data lags by 15-30 minutes for the
current day. Final attributed numbers can shift up to 28 days after a
conversion (28-day click attribution window). For the past 24h, refresh
multiple times. For >7d old data, treat as immutable.

**Async report cleanup** — Meta deletes report results 60 days after
completion. If you need history, mirror to your own warehouse.

**Pixel events in test mode** show in the Test Events tab in 5-30 seconds,
NOT in production reports. `test_event_code` flag both routes to test view
AND excludes from production attribution. Never leave test_event_code in
production code.

**Billing thresholds** — Ad accounts have a billing threshold (e.g. $25,
$50, $250). When unpaid spend hits the threshold, your card is charged.
Failed charge → ad account disabled within hours, all ads stop. Monitor
with `/act_<id>?fields=balance,amount_spent,account_status`.

**Disable cascade** — App suspended → all tokens invalid → all automation
breaks → ads keep running but you can't read or change them. Always have
a manual fallback access path through the UI.

## Ecosystem Position and Composition

**vs Google Ads API** — Google Ads is keyword-first, Meta is audience-first.
The API shapes reflect this: Google has Keywords as a core entity, Meta has
Audiences. The API surfaces are not interchangeable — abstraction layers
that try to unify them (Skai, Smartly, Marin) leak details constantly.

**vs TikTok Marketing API** — TikTok Ads API shamelessly cloned the Meta
shape (Campaign → Ad Group → Ad). Migration is mechanical for the schema
but creative requirements differ wildly (vertical, sound-on, native).

**vs LinkedIn Marketing API** — Different shape entirely (Campaign Group →
Campaign → Creative). Much smaller scale, slower delivery, more expensive.
Used for B2B, never primary for B2C.

**Composition partners that matter:**

- **Conversions API Gateway** — Meta's hosted CAPI proxy (free), turns server
  events into Meta calls without you writing CAPI client code. Use when you
  control the GTM container but not the backend.
- **Stape / GTM server-side** — third-party CAPI proxies; same idea, more
  flexible, costs money.
- **Triple Whale / Northbeam / Hyros** — third-party attribution layers that
  consume the same Insights API and add cross-channel models.
- **Zapier / Make leadgen integrations** — wrap the leadgen webhook for
  no-code use. Fine for prototypes, fragile at scale.

**EOS composition:**

- This skill produces requests. `meta_graph_api` provides token plumbing.
- `instagram` skill provides the IG account identifier used as
  `instagram_actor_id` in creatives.
- The CRM in `/opt/OS/03_CRM/` consumes leadgen webhook output.
- `eos_ai/world_pulse.py` ingests nightly Insights pulls.
- `eos_ai/skill_improvement.py` reads `adrules_library` to learn what
  pacing/scaling rules actually worked.

## Trajectory and Evolution

Where the API is heading (publicly stated by Meta):

- **All-Advantage future.** Every campaign type will eventually be
  Advantage+. Manual targeting and manual placements will become legacy.
  Already mandatory for ASC/AAC creation since v24.0.
- **AI creative generation.** Asset Customization + degrees_of_freedom_spec
  will expand to include Meta-generated headline, body, and image variants.
  Already in beta in some accounts.
- **CAPI-first attribution.** The browser pixel will become a hint, not the
  source of truth. Server events will be the canonical conversion record.
- **Lead Ads → CRM direct integrations** — the leadgen webhook pattern will
  be replaced with first-class CRM connectors. The webhook will keep working
  but be downplayed.
- **Stricter data minimization.** Each version since v20 has tightened what
  PII can be passed and how it must be hashed. Expect this to continue.
- **Quarterly version bumps with breaking changes.** Plan for an annual
  upgrade cycle minimum. Pin and parallel-test always.

What is being deprecated:

- Non-ODAX objectives (banned for new creation)
- Legacy ASC/AAC campaign creation paths (banned in v24.0)
- The 28-day-click attribution default (now 7-day click)
- `instagram_actor_id` field (replaced by `ig_user_id` semantics in v23.0)
- Standalone pixel-only conversion tracking without CAPI (deprioritized in
  optimization quality scoring)

## Conceptual Model and Solution Recipes

### Recipe 1 — Lead generation campaign with CAPI dedup

```python
# 1. Campaign
campaign = account.create_campaign(params={
    Campaign.Field.name: 'IA Lead Gen 2026-04',
    Campaign.Field.objective: Campaign.Objective.outcome_leads,
    Campaign.Field.special_ad_categories: [],
    Campaign.Field.status: Campaign.Status.paused,
})

# 2. Ad set with lead form destination
adset = account.create_ad_set(params={
    AdSet.Field.name: 'IA Leads | US 25-55 | LAL 1%',
    AdSet.Field.campaign_id: campaign['id'],
    AdSet.Field.daily_budget: 5000,                  # $50
    AdSet.Field.billing_event: 'IMPRESSIONS',
    AdSet.Field.optimization_goal: 'LEAD_GENERATION',
    AdSet.Field.bid_strategy: 'LOWEST_COST_WITHOUT_CAP',
    AdSet.Field.destination_type: 'ON_AD',           # instant form
    AdSet.Field.targeting: {
        'geo_locations': {'countries': ['US']},
        'age_min': 25, 'age_max': 55,
        'flexible_spec': [{'custom_audiences': [{'id': LAL_ID}]}],
        'targeting_automation': {'advantage_audience': 1},
    },
    AdSet.Field.status: AdSet.Status.paused,
})

# 3. Creative — page-post with instant form
creative = account.create_ad_creative(params={
    AdCreative.Field.name: 'IA LeadCreative 2026-04 v1',
    AdCreative.Field.object_story_spec: {
        'page_id': PAGE_ID,
        'instagram_actor_id': IG_USER_ID,
        'link_data': {
            'message': 'Become an Initiate.',
            'link': f'https://fb.me/leadgen/{LEADGEN_FORM_ID}',
            'name': 'The Arena',
            'call_to_action': {'type': 'SIGN_UP'},
        },
    },
    AdCreative.Field.url_tags: 'utm_source=meta&utm_campaign=ia_lead_2026_04',
})

# 4. Ad
ad = account.create_ad(params={
    Ad.Field.name: 'IA Lead Ad 2026-04 v1',
    Ad.Field.adset_id: adset['id'],
    Ad.Field.creative: {'creative_id': creative['id']},
    Ad.Field.status: Ad.Status.paused,
})
```

CAPI side, when the lead form fires:

```python
import hashlib, time, requests
def sha(s): return hashlib.sha256(s.strip().lower().encode()).hexdigest()

event_id = f"ia_lead_{leadgen_id}"   # SAME id browser pixel will use
requests.post(
    f"https://graph.facebook.com/v23.0/{PIXEL_ID}/events",
    data={
        'access_token': TOKEN,
        'data': json.dumps([{
            'event_name': 'Lead',
            'event_time': int(time.time()),
            'event_id': event_id,
            'action_source': 'system_generated',
            'user_data': {
                'em': [sha(email)],
                'ph': [sha(phone_e164_no_plus)],
            },
            'custom_data': {'value': 750.0, 'currency': 'USD'},
        }]),
    },
)
```

### Recipe 2 — Nightly Insights pull (async)

```python
job = account.get_insights_async(
    fields=['campaign_name','adset_name','ad_name','impressions','clicks',
            'spend','ctr','cpc','actions','action_values','frequency','reach'],
    params={
        'level':'ad',
        'time_range':{'since': yesterday_iso, 'until': yesterday_iso},
        'breakdowns':['publisher_platform'],
        'action_attribution_windows':['7d_click','1d_view'],
        'limit': 500,
    },
)
job.api_get()
while job[AdReportRun.Field.async_status] not in ('Job Completed','Job Failed','Job Skipped'):
    time.sleep(10)
    job.api_get()
if job[AdReportRun.Field.async_status] != 'Job Completed':
    raise RuntimeError(f"insights job failed: {job}")
rows = list(job.get_result(params={'limit': 500}))
write_to_neon(rows)
```

### Recipe 3 — Custom audience upload (hashed customer list)

```python
import hashlib
def sha(s): return hashlib.sha256(s.strip().lower().encode()).hexdigest()

audience = account.create_custom_audience(params={
    CustomAudience.Field.name: 'IA Customers 2026-04',
    CustomAudience.Field.subtype: 'CUSTOM',
    CustomAudience.Field.customer_file_source: 'USER_PROVIDED_ONLY',
    CustomAudience.Field.description: 'Initiate Arena paid customers',
})

CHUNK = 10_000
for i in range(0, len(rows), CHUNK):
    batch = rows[i:i+CHUNK]
    audience.create_user(params={
        'payload': {
            'schema': ['EMAIL','PHONE','FN','LN','COUNTRY'],
            'data':   [[sha(r.email), sha(r.phone_digits),
                        sha(r.first), sha(r.last), 'us'] for r in batch],
        }
    })
```

Then build a 1% lookalike from it:

```python
account.create_custom_audience(params={
    CustomAudience.Field.name: 'LAL 1% IA Customers US',
    CustomAudience.Field.subtype: 'LOOKALIKE',
    CustomAudience.Field.origin_audience_id: audience['id'],
    CustomAudience.Field.lookalike_spec: {
        'type': 'similarity', 'ratio': 0.01, 'country': 'US',
    },
})
```

### Recipe 4 — Auto-pause losing ads via Rules API

```python
account.create_ad_rules_library(params={
    'name': 'Auto-pause CPA > $100 after 7d',
    'evaluation_spec': {
        'evaluation_type': 'SCHEDULE',
        'filters': [
            {'field':'entity_type','value':'AD','operator':'EQUAL'},
            {'field':'time_preset','value':'LAST_7D','operator':'EQUAL'},
            {'field':'spent','value':10000,'operator':'GREATER_THAN'},
            {'field':'cost_per_result','value':10000,'operator':'GREATER_THAN'},
        ],
    },
    'execution_spec': {'execution_type': 'PAUSE'},
    'schedule_spec': {'schedule_type':'DAILY'},
    'status': 'ENABLED',
})
```

## Industry Expert and Cutting-Edge Usage

What sophisticated teams (Pattern, AKKO, Warby Parker, Ridge, Common Thread)
do that small teams don't:

- **Server-only attribution.** Pixel becomes optional. CAPI is the source of
  truth, with `event_id` minted on the server, browser sends a hint with
  the same id. Match rates 90%+ vs 60-70% for pixel-only.
- **Creative carousels of 50+ assets** per ad set with `asset_feed_spec` and
  let the optimizer A/B/C/D... test. Stop manually testing one variant at
  a time.
- **Daily creative refresh pipelines** — n8n / Make / custom Python that
  uploads new creatives every morning, archives losers via Rules API. Ads
  with frequency >2.5 = stale.
- **Pixel + CAPI + offline conversions stack.** Offline events from Stripe
  webhooks, Shopify orders, and Calendly bookings flow into
  `/offline_conversion_data_set/{id}/events` for full-funnel attribution.
- **Programmatic A/B test runs** via `/ab_test_runs` instead of duplicating
  ad sets and eyeballing the diff.
- **Lookalike laddering** — 1%, 2%, 5%, 10% all in one campaign with budget
  weighted higher to the smallest %.
- **Reading `adset.recommendations`** as agent input — Meta literally tells
  you "audience is too narrow," "creative is fatigued," "budget is below
  optimal" via the API. Most teams ignore it; agents should not.
- **Account-level throttling.** Track BUC headers across every call and
  back off proactively at 75% of quota, not after the 80004 error.
- **Diff-based deployment.** Treat the campaign tree like Terraform — diff
  desired vs current state, only POST what changed. Avoids learning-phase
  resets from no-op writes.
- **Test event tagging in dev** — every dev environment fires CAPI with
  `test_event_code`, every prod environment without. Hard wall in env vars.

## EOS Usage Patterns

How meta_ads composes inside EOS specifically:

**1. Initiate Arena lead engine (primary use case).**

- Campaign objective: `OUTCOME_LEADS`
- Lead form hosted natively on Facebook (instant forms beat landing pages
  for mobile lead cost in IA's verticals)
- Webhook subscription: `leadgen` field on the IA Page
- Webhook receiver: `services/discord_bot.py` route → CRM insert in
  `03_CRM/leads.py` → Telegram alert to founder
- CAPI fires on lead receipt with `event_name=Lead`, `event_id=ia_lead_{id}`,
  matching the pixel `Lead` event from any landing page visit
- Nightly performance pull into Neon via `eos_ai/world_pulse.py`
- Weekly review by EA agent flags: ads with `effective_status=DISAPPROVED`,
  ads with frequency >2.5, ad sets with CPA above target, ad sets in
  Learning Limited

**2. Lyfe Spectrum traffic + sales (post-launch).**

- Campaign objective: `OUTCOME_TRAFFIC` for cold prospecting
- Campaign objective: `OUTCOME_SALES` Advantage+ Shopping for retargeting
- Pixel + CAPI on shop.lyfespectrum.com firing PageView, ViewContent,
  AddToCart, InitiateCheckout, Purchase with deduplicated event_ids
- Catalog via Commerce Manager + dynamic product ads from `product_set_id`

**3. Founder content boost (organic-to-paid bridge).**

- Daily check: query `/{page-id}/posts?fields=insights.metric(post_impressions_unique)`
  for top 10% organic posts
- For each, create a `OUTCOME_ENGAGEMENT` Boost-style ad set targeting
  lookalike of email subscribers + interest expansion
- Always paused at creation, founder approves via Telegram one-click

**4. Authority-aware writes.**

```python
def write_with_authority(action, params, risk='HIGH'):
    if risk == 'CRITICAL':
        if not founder_telegram_confirm(action, params):
            return
    if risk == 'HIGH':
        propose_to_founder(action, params)
        return
    return execute(action, params)
```

All campaign creation, budget changes, and audience uploads route through
this. Read-only Insights bypass it.

**5. Token health daemon.**

`eos_ai/provider_health.py` checks `/me?access_token=...&fields=id` daily
for the system user token. Token failure → page founder via Discord
service immediately, don't wait for the next cron.

**6. Always-paused-at-creation pattern.**

Every `create_*` call in EOS sets `status=PAUSED`. Activation is a separate,
human-approved step. This single rule has saved more spend than any other
automation. Bake it in at the SDK wrapper layer, not at each call site.

## Gotchas

This list is the EOS-specific addendum to the SKILL.md Gotchas — patterns
discovered the hard way that should never bite again.

- **Wrong API version pinned across files.** Multiple modules each call
  `FacebookAdsApi.init` with different `api_version` strings → silent
  semantic differences (instagram_destination_id meaning, default attribution
  windows). Fix: one init module, imported everywhere.
- **Forgetting `customer_file_source` on CUSTOM audience create.** Returns
  a non-obvious "param missing" error 100. Always pass `USER_PROVIDED_ONLY`
  for first-party data.
- **Hashing CAPI client_ip_address or client_user_agent.** Those are NOT
  hashed — they're matched raw. Hashing them = zero match rate.
- **Phone number with `+` prefix** — Meta strips silently, then complains
  about format mismatch. Always strip to digits before hashing.
- **Time zone confusion in Insights.** All `time_range` is in the ad
  account's configured timezone. EOS runs in UTC, ad account is America/
  Los_Angeles → 7-8 hour shift. Convert in Python before sending.
- **Default `limit=25` on cursor pagination.** Iterating 5000 ads via SDK
  defaults = 200 round trips. Set `limit=500` always.
- **`ad_account` webhook fires for billing changes** — make sure your
  handler doesn't loop or alert noisy on every nightly auto-charge.
- **Pixel ID vs Dataset ID confusion.** Newer accounts have "Datasets"
  instead of "Pixels" in the UI but the API still calls them `adspixels`
  and the IDs interoperate. Either ID works in the `/events` URL path.
- **`special_ad_categories` cannot be changed after launch.** Wrong value
  on creation = delete and recreate the entire campaign.
- **System user token cached in old container.** When you rotate the token
  in `.env`, restart with `docker restart os-bot` — Python modules cache
  the env at import time.
- **Lead form field order changes break parsers.** Always look up by `name`
  in `field_data`, never by index.
- **`create_user` on a custom audience that's still building** — silently
  drops users. Wait for the audience to reach `Ready` state before appending.
- **`promoted_object` mismatch with optimization_goal.** `LEAD_GENERATION`
  needs `page_id`; `OFFSITE_CONVERSIONS` needs `pixel_id`+`custom_event_type`;
  `APP_INSTALLS` needs `application_id`+`object_store_url`. Wrong combination
  = error 100, no clear message.
- **Mixing Advantage+ Audience defaults with manual exclusions.** Since
  v23.0, `targeting_automation.advantage_audience: 1` is the default; your
  manual `exclusions.custom_audiences` may be ignored. Pin `advantage_audience: 0`
  if exclusions are critical (e.g. excluding existing customers in a cold
  prospecting set).
- **CAPI test events left enabled in prod.** `test_event_code` excludes
  events from production attribution. Search the codebase before every
  release: `grep -n test_event_code` should only match dev configs.
- **Tracking `actions` field assuming a fixed shape.** `actions` is a list
  of `{action_type, value}` dicts where `action_type` strings vary by
  objective (`offsite_conversion.fb_pixel_lead`, `onsite_conversion.lead_grouped`,
  `lead`, etc.). Sum across types you actually want, not blindly.
- **Forgetting `ad_label` taxonomy.** EOS convention: every ad gets a label
  for `{venture}`, `{funnel_stage}`, `{creative_concept}`. Without these,
  Insights breakdowns by label are useless.
- **Running outreach scripts from a non-system-user token "just for now"**
  — the user logs out next week, the token dies, the cron silently fails,
  the founder discovers it 14 days later. Never. System user from day one.

---

End of best_practices.md — meta_ads. See SKILL.md for the conceptual summary.
