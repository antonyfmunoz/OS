# Amazon Ads — Creator-Level Best Practices
Source: advertising.amazon.com/API/docs, github.com/amzn/ads-advanced-tools-docs, github.com/python-amazon-ad-api, Amazon Ads release notes
API Version: v3 (campaign management), v3 (Reporting), v2 (profiles, legacy SB/SD residual)
SDK Version: python-amazon-ad-api 0.7.x (community), Amazon Ads Java/Node SDK 2024+
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## Authentication

Amazon Advertising API uses **Login With Amazon (LWA)** OAuth 2.0 — the same
identity provider as the Selling Partner API (SP-API), but with a different
scope. The token surface is intentionally siloed: an LWA app authorized for
advertising cannot read SP-API resources, and vice versa, even though both
flow through `https://api.amazon.com/auth/o2/token`.

### One-time setup (per developer / account)

1. Register an LWA "Security Profile" at `developer.amazon.com/loginwithamazon/console/site/lwa/overview.html`.
   You get `LWA_CLIENT_ID` (`amzn1.application-oa2-client.<hash>`) and
   `LWA_CLIENT_SECRET`.
2. Apply for Amazon Ads API access at `advertising.amazon.com/API/docs/en-us/setting-up/overview`.
   This couples your LWA client to the Ads API and provisions the
   `advertising::campaign_management` scope. Approval is usually 1–3
   business days for sellers, longer for vendors / agencies.
3. Add a redirect URI under the LWA security profile (e.g.
   `https://localhost/callback` for one-shot dev use).

### Authorization-code flow (one-time, to mint a refresh token)

```
GET https://www.amazon.com/ap/oa
    ?client_id=<LWA_CLIENT_ID>
    &scope=advertising::campaign_management
    &response_type=code
    &redirect_uri=https://localhost/callback
    &state=<csrf-nonce>
```

The seller logs in, approves, and is bounced back to the redirect with
`?code=ANxxxxxxxx&scope=...&state=<csrf>`.

Exchange code for tokens:

```python
import requests
r = requests.post("https://api.amazon.com/auth/o2/token", data={
    "grant_type":   "authorization_code",
    "code":         code,
    "client_id":    LWA_CLIENT_ID,
    "client_secret":LWA_CLIENT_SECRET,
    "redirect_uri": "https://localhost/callback",
})
tok = r.json()
# {"access_token":"Atza|...", "refresh_token":"Atzr|...", "token_type":"bearer", "expires_in":3600}
```

Persist the **refresh_token** in `eos_ai/.env` as `AMAZON_ADS_REFRESH_TOKEN`.
That's the long-lived credential. Treat it like a password.

### Refresh-token flow (every 60 minutes)

```python
def get_access_token() -> str:
    r = requests.post("https://api.amazon.com/auth/o2/token", data={
        "grant_type":    "refresh_token",
        "refresh_token": os.environ["AMAZON_ADS_REFRESH_TOKEN"],
        "client_id":     os.environ["LWA_CLIENT_ID"],
        "client_secret": os.environ["LWA_CLIENT_SECRET"],
    }, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]
```

Cache the token in process memory (or Redis) for ~55 min. Don't hammer LWA on
every API call — LWA itself is rate-limited and will start returning `429`
on excessive token churn.

### Profile id discovery

After auth, hit `/v2/profiles` (region-specific endpoint) to enumerate every
ad profile attached to that LWA identity. Each profile is a (marketplace,
country, account-type) tuple. The same LWA token can drive a US Sponsored
Products profile, a CA profile, and a UK profile in parallel — each call just
swaps the `Amazon-Advertising-API-Scope` header.

```python
r = requests.get("https://advertising-api.amazon.com/v2/profiles", headers={
    "Authorization": f"Bearer {get_access_token()}",
    "Amazon-Advertising-API-ClientId": LWA_CLIENT_ID,
})
# Pick the seller US profile:
us = next(p for p in r.json()
          if p["countryCode"] == "US" and p["accountInfo"]["type"] == "seller")
PROFILE_ID = str(us["profileId"])
```

### EOS rule

Store `LWA_CLIENT_ID`, `LWA_CLIENT_SECRET`, `AMAZON_ADS_REFRESH_TOKEN`,
`AMAZON_ADS_PROFILE_ID`, `AMAZON_ADS_REGION` in `eos_ai/.env`. Never hardcode.
Never commit. The `model_router` does not handle ad credentials — they live
in their own loader (`eos_ai/integrations/amazon_ads.py` once built).

## Core Operations with Exact Signatures

All v3 endpoints expect a resource-specific media type. The pattern is:
`application/vnd.<resource>.v3+json` for both `Content-Type` and `Accept`.

### Profiles (v2 — only place v2 is still canonical)

```
GET  /v2/profiles                         → list all profiles for this LWA token
GET  /v2/profiles/{profileId}             → single profile
PUT  /v2/profiles                         → update daily budget cap, tz
GET  /v2/profiles/registerAssistant       → seller-assistant registration
```

### Sponsored Products (v3)

```
POST /sp/campaigns                        → create (batch up to 1000)
POST /sp/campaigns/list                   → list with filter
PUT  /sp/campaigns                        → update (batch)
POST /sp/campaigns/delete                 → soft-delete (state=ARCHIVED)

POST /sp/adGroups                         → create
POST /sp/adGroups/list
PUT  /sp/adGroups
POST /sp/adGroups/delete

POST /sp/productAds                       → create (one ASIN each)
POST /sp/productAds/list
PUT  /sp/productAds
POST /sp/productAds/delete

POST /sp/keywords                         → create (keyword text + matchType + bid)
POST /sp/keywords/list
PUT  /sp/keywords                         → update bid / state
POST /sp/keywords/delete

POST /sp/targets                          → product / category targets (auto + manual)
POST /sp/targets/list
PUT  /sp/targets
POST /sp/targets/delete

POST /sp/negativeKeywords                 → campaign-level negatives
POST /sp/negativeKeywords/list
POST /sp/negativeKeywords/delete

POST /sp/campaignNegativeKeywords         → distinct from ad-group negatives
POST /sp/negativeTargets                  → ASIN / category negatives
POST /sp/campaignNegativeTargets

GET  /sp/themes                           → AI-generated theme targeting
GET  /sp/budget/recommendations           → budget rec engine
POST /sp/targets/bid/recommendations      → bid rec for a target / keyword
POST /sp/targets/keywords/recommendations → keyword recs for an ASIN
```

Method signature for the most common call (`POST /sp/keywords`):

```
POST /sp/keywords HTTP/1.1
Host: advertising-api.amazon.com
Authorization: Bearer <access_token>
Amazon-Advertising-API-ClientId: <LWA_CLIENT_ID>
Amazon-Advertising-API-Scope: <profileId>
Content-Type: application/vnd.spKeyword.v3+json
Accept:       application/vnd.spKeyword.v3+json
Prefer: return=representation

{
  "keywords": [
    {
      "campaignId": "123456789012345",
      "adGroupId":  "987654321098765",
      "keywordText":"merino wool t shirt",
      "matchType":  "EXACT",
      "state":      "ENABLED",
      "bid":        0.85
    }
  ]
}
```

Response (`207 Multi-Status` on partial success — always parse this):

```
{
  "keywords": {
    "success": [{"index":0,"keywordId":"112233445566"}],
    "error":   []
  }
}
```

### Sponsored Brands (v4)

```
POST /sb/v4/campaigns
POST /sb/v4/campaigns/list
PUT  /sb/v4/campaigns
POST /sb/v4/campaigns/delete

POST /sb/v4/adGroups
POST /sb/v4/ads                         → SB ad (creative + asset references)
POST /sb/v4/creatives                   → upload creatives (logo, custom image, video)
POST /sb/v4/keywords
POST /sb/v4/targets
POST /sb/v4/negativeKeywords
POST /sb/v4/negativeTargets

POST /sb/v4/recommendations/keyword
POST /sb/v4/recommendations/bid
```

### Sponsored Display (v3)

```
POST /sd/campaigns                      → create (tactic = T00020 remarketing, T00030 contextual, etc.)
POST /sd/campaigns/list
POST /sd/adGroups
POST /sd/productAds
POST /sd/targets                        → audiences, views-remarketing, purchases-remarketing
POST /sd/negativeTargets

GET  /sd/recommendations/products
GET  /sd/audiences/list                 → Amazon audiences (in-market, lifestyle, demographic)
```

### Sponsored TV / Streaming TV ads

```
POST /st/campaigns                      → Sponsored TV (creative is a video asset)
POST /st/adGroups
POST /st/ads
POST /st/targets                        → reach + audience selection
```

### Reporting (v3)

```
POST /reporting/reports                 → create async report
GET  /reporting/reports/{reportId}      → status + url when COMPLETED
GET  /reporting/reports/list            → recent reports for this profile
DELETE /reporting/reports/{reportId}    → cancel a PENDING / PROCESSING report
```

The v3 reporting body:

```json
{
  "name": "spKeyword-daily-2026-04-05",
  "startDate": "2026-04-05",
  "endDate":   "2026-04-05",
  "configuration": {
    "adProduct": "SPONSORED_PRODUCTS",
    "groupBy": ["campaign","adGroup","keyword"],
    "columns": ["date","campaignId","adGroupId","keywordId","keyword","matchType",
                "impressions","clicks","cost","purchases7d","sales7d",
                "acosClicks7d","roasClicks7d","attributedConversions7d"],
    "reportTypeId": "spKeyword",
    "timeUnit": "DAILY",
    "format": "GZIP_JSON"
  }
}
```

`reportTypeId` values you will use most:

| reportTypeId         | groupBy options                          | description                       |
|----------------------|------------------------------------------|-----------------------------------|
| `spCampaigns`        | campaign[, placement]                    | campaign performance              |
| `spTargeting`        | targeting                                | keyword + product target perf     |
| `spSearchTerm`       | searchTerm                               | search term report (harvest src)  |
| `spAdvertisedProduct`| advertisedProduct                        | per-ASIN advertised perf          |
| `spPurchasedProduct` | asin                                     | halo purchases (different ASIN)   |
| `sbCampaigns`        | campaign                                 | SB campaign perf                  |
| `sbSearchTerm`       | searchTerm                               | SB search term                    |
| `sbAds`              | ads                                      | SB creative perf                  |
| `sdCampaigns`        | campaign[, matchedTarget]                | SD campaign perf                  |
| `sdAdvertisedProduct`| advertisedProduct                        | SD advertised perf                |
| `sdPurchasedProduct` | asin                                     | SD halo                           |

### Snapshots (legacy v2 — still works for bulk entity export)

```
POST /v2/sp/{recordType}/snapshot       → recordType in {campaigns, adGroups, productAds, keywords, negativeKeywords, campaignNegativeKeywords}
GET  /v2/sp/snapshots/{snapshotId}      → status + location
GET  <download-url>                     → gzipped JSON list
```

### Recommendations (high-leverage)

```
POST /sp/targets/keywords/recommendations    → input ASINs → seed keywords w/ rank
POST /sp/targets/bid/recommendations         → input keyword/match → suggested bid (low/med/high)
GET  /sp/budget/recommendations              → daily-budget-too-low flags
GET  /sp/campaigns/{id}/budget/usage         → in-day spend pacing
POST /sp/negativeKeywords/recommendations    → suggested negatives based on perf
```

## Pagination Patterns

Two patterns coexist depending on resource age:

**v3 (current) — `nextToken` cursors**

```python
body = {"maxResults": 1000, "stateFilter": {"include": ["ENABLED","PAUSED"]}}
all_rows = []
while True:
    r = requests.post(".../sp/campaigns/list", headers=headers, json=body)
    j = r.json()
    all_rows.extend(j["campaigns"])
    if "nextToken" not in j: break
    body["nextToken"] = j["nextToken"]
```

`nextToken` is opaque. Don't try to parse it. It encodes the filter — if you
change the filter mid-paging you'll get inconsistent results.

**v2 (legacy SB pieces, profiles) — `startIndex` + `count`**

```python
params = {"startIndex": 0, "count": 100}
while True:
    j = requests.get("...", headers=headers, params=params).json()
    if not j: break
    all_rows.extend(j)
    if len(j) < 100: break
    params["startIndex"] += 100
```

**Reports** are not paginated — they return one big gzip blob. If your report
exceeds ~1 GB, narrow the date range or split by campaign.

## Rate Limits

Amazon Ads does not publish exact RPS numbers. Limits are dynamic per
(profile, endpoint, account-history) and adjusted by Amazon. Empirically:

- **Campaign management endpoints**: ~10 req/sec sustained per profile, with
  small bursts to ~30. Batch endpoints (1000 entities per call) are the
  intended scaling path — never loop singletons.
- **Reporting**: ~200 reports per profile per day soft cap. Reports are async
  so wall-clock is dominated by Amazon's queue, not your RPS.
- **`/v2/profiles`**: very low — call once per session and cache.
- **LWA token endpoint**: ~5 req/sec. Cache the access token.

Headers to read on every response:

```
x-amzn-RateLimit-Limit: <number>      # current limit (sometimes set)
x-amzn-RequestId: <uuid>              # ALWAYS log this for support tickets
```

Backoff strategy on `429`:

```python
import time, random
def backoff_post(url, **kw):
    for attempt in range(6):
        r = requests.post(url, **kw)
        if r.status_code != 429: return r
        sleep = (2 ** attempt) + random.random()
        time.sleep(sleep)
    r.raise_for_status()
```

EOS rule: log every `x-amzn-RequestId` to Neon when the response is non-2xx —
Amazon support cannot help without it.

## Error Codes and Recovery

| Code | Meaning                                  | Recovery                                                       |
|------|------------------------------------------|----------------------------------------------------------------|
| 400  | Bad request / validation                 | Inspect `message` + `details`. Fix payload, do not retry.      |
| 401  | Auth — token invalid / scope wrong       | Re-mint access token. If still 401, refresh_token revoked.    |
| 403  | Profile not authorized for resource      | Check the profile has the product (e.g. SB requires brand reg) |
| 404  | Entity not found / wrong region          | Verify campaignId, verify region endpoint matches profile      |
| 406  | `Accept` header missing / wrong vendor   | Set `Accept: application/vnd.<resource>.v3+json`               |
| 415  | `Content-Type` wrong (using app/json)    | Set the resource-specific vnd type                             |
| 422  | Business rule violation (bid floor, etc) | Read `details[].message`. Fix and resubmit.                    |
| 429  | Throttle                                 | Exponential backoff with jitter, max ~6 retries                |
| 500  | Server error                             | Retry once after 5s. If persistent, file ticket w/ RequestId   |
| 502/503/504 | Edge / gateway hiccup            | Retry with backoff up to 3x                                    |

v3 batch responses ALWAYS return `207 Multi-Status` shape — even on full
success. Always parse `success[]` and `error[]` arrays per item:

```python
resp = r.json()
created = resp["keywords"]["success"]   # [{"index":0,"keywordId":"112"}, ...]
failed  = resp["keywords"]["error"]     # [{"index":3,"code":"INVALID_BID","message":"..."}, ...]
```

The `index` matches the position in your input array — that's how you map
errors back to the source row.

## SDK Idioms

### Official Amazon Ads SDKs

Amazon ships first-party SDKs for Java, Node, Python (under
`github.com/amzn/ads-advanced-tools-docs`). They are *generated from OpenAPI*
and tend to lag the API by a few weeks. They handle:

- LWA token refresh
- Region routing
- Pagination (`nextToken`) helpers
- Retry / backoff

### Community: `python-amazon-ad-api`

```python
from ad_api.api import sponsored_products
from ad_api.base import Marketplaces

credentials = dict(
    refresh_token=os.environ["AMAZON_ADS_REFRESH_TOKEN"],
    client_id=os.environ["LWA_CLIENT_ID"],
    client_secret=os.environ["LWA_CLIENT_SECRET"],
    profile_id=os.environ["AMAZON_ADS_PROFILE_ID"],
)

sp = sponsored_products.Campaigns(
    credentials=credentials,
    marketplace=Marketplaces.US,
)
res = sp.list_campaigns(body={"maxResults": 100})
print(res.payload["campaigns"])
```

The community SDK is the path of least resistance for EOS — it shadows
SP-API's `python-amazon-sp-api` patterns and handles token caching out of the box.

### Raw `requests` (canonical for EOS)

EOS prefers raw `requests` calls in `eos_ai/integrations/amazon_ads.py` so
the dependency surface stays small and the failure modes are visible.
Wrap them in a `_call(method, path, body, vendor)` helper that injects
headers, handles 429 backoff, parses 207s, and logs RequestId.

## Anti-Patterns

- **Single-item POSTs in a loop.** Every campaign management endpoint accepts
  up to 1000 entities per call. Looping singletons burns rate limit and
  multiplies request latency by N. Always batch.
- **Polling reports every second.** Amazon's queue is not real-time. Poll
  every 10–30 seconds. Faster polling does not make the report finish sooner
  and will get you 429d off the reporting endpoint.
- **Storing a report `url` and downloading later.** It's a pre-signed S3
  link that expires in ~30 min. Download immediately on COMPLETED.
- **One profile, one process — no concurrency cap.** Two parallel workers
  hammering the same (profile, endpoint) will collide on rate limits. Use a
  per-(profile,endpoint) semaphore.
- **Treating ACOS in isolation.** Optimizing only for ACOS kills total
  revenue (TACOS goes up). Always optimize against TACOS using SP-API
  ground truth.
- **Pausing campaigns instead of bid-down.** A paused campaign loses its
  search-rank history. Bid-down to $0.02 keeps the campaign active and
  recoverable.
- **Forgetting `stateFilter`.** Every list endpoint defaults to `ENABLED`
  only. If you're hunting for missing entities, expand to `ENABLED,PAUSED,ARCHIVED`.
- **Reusing keyword text across match types in one ad group.** Auto matches
  it twice and your reports get noisy. Single-keyword ad groups (SKAGs)
  prevent this.
- **Uploading SB video creative inline.** SB v4 creatives are uploaded via a
  separate `/sb/v4/creatives` call and *referenced* by id from the ad — not
  embedded in the ad payload.

## Data Model

```
LWA App (client_id)
 └── Refresh Token (per seller authorization)
      └── Profile (per marketplace, per account-type)
           ├── Portfolio (optional spend grouping)
           │    └── Campaign
           │         ├── Bidding Strategy (legacy_for_sales | auto_for_sales | manual)
           │         ├── Placement Bid Modifiers (top_of_search, product_pages, rest_of_search)
           │         ├── Daily Budget
           │         ├── Targeting Type (auto | manual)
           │         └── Ad Group
           │              ├── Default Bid
           │              ├── Product Ad (1 per ASIN)
           │              ├── Keyword (text, matchType in EXACT|PHRASE|BROAD, bid)
           │              ├── Target (ASIN target, category target, audience for SD)
           │              ├── Negative Keyword (NEGATIVE_EXACT | NEGATIVE_PHRASE)
           │              └── Negative Target (ASIN / category)
           ├── Audiences (SD, DSP)
           ├── Brand (for SB / SB video)
           ├── Stores (Amazon Stores analytics)
           └── Attribution Tags (Amazon Attribution)
```

Entity ids are stringified longs (`"123456789012345"`). Always treat as string
in Python — JSON precision-loss bites you on `int` round-trips.

State enum: `ENABLED | PAUSED | ARCHIVED`. ARCHIVED is soft-delete — you can
still report on archived entities but cannot un-archive (you must recreate).

Match types:
- `EXACT` — exact phrase, no extra words
- `PHRASE` — phrase contained in search, with leading/trailing words allowed
- `BROAD` — any order, plurals, synonyms (Amazon's matching is fuzzy here)
- `NEGATIVE_EXACT`, `NEGATIVE_PHRASE` — same logic, exclusion side
- Auto campaigns add: `loose-match`, `close-match`, `complements`, `substitutes`

Targeting expressions (v3 SD targets):

```json
{"type": "asinSameAs", "value": "B0XXXXXXXX"}
{"type": "asinCategorySameAs", "value": "1234567"}
{"type": "lookback", "value": "30"}                  // remarketing window
{"type": "audience", "value": "amzn1.audience...."}  // Amazon audience
```

## Webhooks and Events

Amazon Ads has **no real webhooks** in the traditional sense. There is no
"campaign.updated" push delivered to your endpoint. The closest things:

- **Stream API** (Amazon Marketing Stream) — near-real-time event stream
  (campaigns, ad groups, traffic, conversions) delivered to an AWS account
  the customer owns via SQS / Firehose. Requires AWS account linkage and is
  the *only* sub-hour data path. Use this for live ACOS dashboards.
- **Notification API** (some markets) — push alerts on budget exhaustion,
  campaign expiration, policy violations. Limited rollout.
- **Reports** — pull only, async.
- **Snapshots** — pull only, async.

EOS rule: don't design an event-driven Amazon Ads automation unless you have
Marketing Stream onboarded. Until then, run polling cron at 06:00 / 12:00 /
18:00 / 22:00 and treat the data as eventually-consistent.

## Limits

| Resource                              | Limit                                          |
|---------------------------------------|------------------------------------------------|
| Ad groups per campaign                | 1,000                                          |
| Keywords per ad group                 | 1,000                                          |
| Product ads per ad group              | 1,000                                          |
| Targets per ad group                  | 1,000                                          |
| Negative keywords per ad group        | 1,000                                          |
| Campaign negative keywords / campaign | 1,000                                          |
| Campaigns per profile                 | ~10,000 sponsored products (soft, raisable)    |
| Portfolios per profile                | 100                                            |
| Items per batch (POST)                | 1,000                                          |
| Reports per profile per day           | ~200 (soft)                                    |
| Report date range                     | up to 95 days per request                      |
| Report data retention                 | 95 days for SP, 60 days for SB/SD              |
| Bid minimum (US)                      | $0.02 (varies by marketplace; JP = ¥2)         |
| Daily budget minimum (US)             | $1.00                                          |
| Lifetime budget minimum (SB)          | $100                                           |
| Keyword text length                   | up to 80 characters, max 10 words              |
| Campaign name length                  | up to 128 characters, must be unique per profile |
| SB video duration                     | 6–45 seconds                                   |
| SB video aspect ratios                | 16:9 or 1:1                                    |
| SB video file size                    | ≤500 MB                                        |
| SB custom image                       | 1200×628, ≤5 MB                                |

Hitting a limit returns `422 Unprocessable Entity` with a `LIMIT_EXCEEDED`
detail code. Most limits are *soft* and can be raised by an account manager.

## Cost Model

- **Amazon Ads API itself is free.** No per-call charges, no monthly fee.
- **You pay for ad spend** — auction-driven CPC for SP/SD/SB, CPM for SB
  video / Sponsored TV / DSP. There is no API surcharge.
- **Marketing Stream** — free, but you pay AWS for the SQS / Firehose +
  storage.
- **Amazon Marketing Cloud (AMC)** — free for self-service queries, paid for
  the "AMC Audiences" and "AMC Insights" tiers.
- **Amazon DSP** — managed-service contracts have ~15% media markups +
  minimum spends ($35–50K/mo historically, lower for self-service in some
  markets). Self-service DSP is free of seat fees but the API is gated.
- **Sponsored TV** — auction-based, no platform fee, but minimum daily
  budgets ($10/day in 2024–2026 onboarding).

EOS pre-revenue rule: nothing on the Lyfe Spectrum Amazon Ads side until
ASINs are live. When live, start with $10–20/day per SKU, never more, until
ACOS data justifies scaling. Scale by *raising bids on winners*, not by
raising daily budgets — daily budget caps are the safety net.

## Version Pinning

- **API version**: v3 is the current and only forward-supported campaign
  management surface. v2 is deprecated for SP/SB/SD as of 2023–2024 except
  for `/v2/profiles` and a few snapshot endpoints. Migrate any v2 SP/SB code
  immediately.
- **Reporting**: v3 only. The v2 reporting endpoints (`/v2/sp/keywords/report`)
  were sunset in 2023. If you find example code calling them, it's stale.
- **SB**: v4 is current. v3 SB is sunset.
- **SDKs**: pin `python-amazon-ad-api` to a specific minor version
  (`==0.7.5`) — the maintainer follows Amazon's API changes but breaking
  releases happen every few months.
- **OpenAPI specs**: Amazon publishes per-resource OpenAPI 3.0 docs at
  `advertising.amazon.com/API/docs/en-us/reference`. Re-fetch and re-research
  this skill on any 4xx that mentions "deprecated."

EOS rule: stamp every Amazon Ads call with `last_validated_against_v3`
in the call log so future agents know when the contract was last verified.

---

# Tier 2 — Marketer Intelligence

## Design Intent and Tradeoffs

Amazon Ads exists for one reason: **sellers buy traffic on their own product
pages**. Unlike Google Ads or Meta Ads, the conversion event happens *inside
Amazon's walled garden*, on a SKU Amazon already owns the listing for. Amazon
knows exactly which click led to which purchase, to which order, to which
return — the attribution problem that plagues every other ad platform is
trivially solved here. That's the API's superpower and its cage.

Tradeoffs the design imposes:

- **No real-time auction control.** You set a bid, you set a budget, Amazon
  runs the auction. There is no QPS RTB endpoint. This kills entire categories
  of optimization (real-time dayparting at the impression level) but makes the
  surface tractable for solo founders.
- **Async-everywhere reporting.** Amazon's data pipeline batches in 1–24 hour
  windows. The Reports API surfaces "yesterday" reliably and "today" with
  partial coverage. Marketing Stream is the only escape valve.
- **Profile-as-tenant.** Every dimension (account, marketplace, account type)
  is collapsed into one opaque profile id. This makes multi-marketplace
  agencies awkward — you cannot query "all my US sellers" in one call.
- **Conversion data is privileged.** You only see ad-attributed conversions.
  Total order data lives in SP-API. The two APIs were designed by different
  teams and the join is left to you.
- **Creative is lightweight.** SP has no creative — Amazon uses your listing.
  SB/SD/STV have creative but it's heavily templated. This is by design:
  Amazon doesn't want sellers building brands off-Amazon-style. The brand
  surfaces (Stores, Posts, Brand Story) are gated behind Brand Registry.
- **Recommendations bake in Amazon's interests.** Bid recommendations from
  the API will, on average, recommend higher bids than profit-optimal, because
  Amazon's revenue is the auction. Treat them as inputs, not gospel.

## Problem-Solution Map and Hidden Capabilities

| Problem                                              | API surface                                   |
|------------------------------------------------------|-----------------------------------------------|
| New SKU has no traffic                               | Auto campaign + low bid + 14-day harvest     |
| Don't know what people search for to find this ASIN  | spSearchTerm report on auto campaign         |
| Bids feel like guesses                               | `/sp/targets/bid/recommendations`            |
| Wasting spend on irrelevant searches                 | Negative keyword harvest loop                |
| Cannibalizing organic                                | TACOS analysis (Ads + SP-API join)           |
| Competitors stealing branded search                  | SB defensive bid on brand terms              |
| Need to retarget detail-page viewers                 | Sponsored Display T00020 (views remarketing) |
| Need to retarget purchasers (cross-sell)             | SD T00030 (purchases remarketing)            |
| Off-Amazon traffic conversion measurement            | Amazon Attribution                           |
| Need event-level data for clean-room analysis        | Amazon Marketing Cloud (AMC)                 |
| Need video on search                                 | Sponsored Brands video                       |
| Need CTV / streaming TV                              | Sponsored TV                                 |
| Need full programmatic display                       | Amazon DSP                                   |
| Need budget pacing across many campaigns             | Portfolios (monthly cap)                     |
| Need to test bid strategies                          | `bidding.strategy` field on campaign create  |
| Need to find kw rank without external tools          | `/sp/themes` + theme-based targeting         |

Hidden capabilities most sellers never use:

- **Themes targeting** (`/sp/themes`) — Amazon-curated keyword themes you can
  target without picking individual keywords. Works well for new SKUs.
- **Top-of-search bid modifier** — multiplies your bid 1–900% specifically for
  the top-of-search placement. The single most ROI-positive lever in SP.
- **Bidding strategies** — `legacyForSales` (Amazon-bid-up to 100%),
  `autoForSales` (down + up), `manual` (no auto-adjust). Switching from
  manual to dynamic-up-and-down on a winning campaign typically lifts
  attributed sales 15–30%.
- **Sponsored Brands video** — much higher CTR than static SB at similar CPC.
- **SD audiences** — Amazon's in-market and lifestyle audiences are
  surprisingly accurate and only available via the API.
- **Amazon Attribution tags** — UTM-equivalent for off-Amazon traffic. Free.
  Lets you measure if your Instagram post drove Amazon sales.
- **Stores analytics API** — pageview / dwell / source breakdown of your
  Amazon Store. Free, requires Brand Registry.
- **Brand Metrics** — top-of-funnel "consideration" and "awareness" indices
  for your brand vs the category, calculated from Amazon's behavior data.

## Operational Behavior and Edge Cases

- **Eventual consistency.** A POST to create a keyword returns a keywordId
  immediately, but the keyword may take 1–15 minutes to enter the auction.
  Don't write tests that POST then immediately GET and expect to find perf data.
- **Time zones.** Reports are emitted in the **profile's time zone**, not UTC.
  A "2026-04-05" report for a US profile covers America/Los_Angeles 00:00–23:59.
  Joining cross-marketplace requires tz normalization.
- **Currency.** All monetary fields are in the profile's `currencyCode`
  (USD for US, GBP for UK, etc.). No conversion. EOS converts to USD at
  ingestion using the day's spot rate from a separate FX source.
- **Halo sales.** SP reports include `purchases1d/7d/14d/30d` and matching
  `sales1d/7d/14d/30d`. The 7d window is the "official" ACOS attribution
  window. Halo (a click on ASIN A drove a purchase of ASIN B) is in
  `spPurchasedProduct` with a separate `purchasedAsin` column.
- **Auto campaigns expand the targeting list themselves.** You'll see new
  keyword-like targets appear under your auto ad groups over time. Don't
  delete them — they're how Amazon tells you what worked.
- **Bidding strategy changes are instant** for pacing but the auction effect
  lags ~30 min.
- **Daily budget exhaustion** pauses the campaign for the day. The next day
  it resumes. There's no "spend twice tomorrow" make-up.
- **Campaigns can be in `state=ENABLED` but `servingStatus=ADVERTISER_PAYMENT_FAILURE`
  or `BILLING_ERROR`** — always check `extendedData.servingStatus` not just
  `state`.
- **Region routing for the same seller.** A US seller selling in Canada has
  a US profile and a CA profile, both under the same LWA token, but the CA
  profile is queried via the NA endpoint (NA = US + CA + MX). EU = UK, DE,
  FR, IT, ES, NL, SE, PL, BE, AE, SA, EG, TR. FE = JP, AU, SG.
- **Search term reports include impressions where you didn't get a click.**
  `clicks=0, impressions>0` rows are valid and useful for impression-share
  analysis.

## Ecosystem Position and Composition

Amazon Ads is the **only** programmatic surface for Amazon's first-party
ad inventory. There is no aggregator, no proxy, no third-party API that
gives you the same data — every Amazon-ads tool (Helium 10 Adtomic, Perpetua,
Pacvue, Teikametrics, Sellozo, M19, Ad Badger, Sellics) is a UI on top of
this same v3 API. This is unusual: in Google or Meta land you have multiple
ad networks competing; in Amazon land, the API is the moat *and* the
commodity.

How EOS composes Amazon Ads with other skills:

- **amazon_seller_central (SP-API)** — joined on (ASIN, day) for TACOS.
  Inventory data from SP-API gates the bid loop: don't bid up an out-of-stock
  ASIN; auto-pause when `quantity_available < N`.
- **google_ads / meta_ads / tiktok_ads** — parallel ad surfaces. EOS routes
  budget to whichever platform has the best blended ROAS for the target
  audience.
- **amazon_attribution** — measures off-Amazon traffic from social / email /
  content into Amazon conversions. Amazon Attribution uses the same LWA token.
- **AMC** — clean-room SQL on event-level (ad impression, click, view, ASIN
  detail page view, purchase) data. Use for sophisticated incrementality tests.
- **Marketing Stream** — for sub-hour dashboards.
- **Helium 10 / Jungle Scout** — keyword research signal *outside* the API
  (organic search volume estimates from Amazon's autocomplete + reverse-ASIN
  scraping). EOS combines these with Amazon's own search-term reports.
- **Notion / Slack / Discord** — alerting layer for ACOS drift, budget
  exhaustion, new negative keywords created.

Composition pattern: Amazon Ads is a **data source + control surface**, not
an intelligence layer. The intelligence is in EOS — the bid logic, the
harvest logic, the budget pacing, the cross-channel decision — and the API
is the actuator.

## Trajectory and Evolution

- **2018–2020** — v1 / v2 era. Limited surface, mostly read-only reporting,
  no SD, no SB video.
- **2021** — Sponsored Display launches, bid recommendations API.
- **2022** — v3 campaign management beta. Reports v2 sunset announced.
- **2023** — Amazon Marketing Stream GA (event streaming), AMC opens to
  self-service, v3 fully out of beta. Sponsored TV beta.
- **2024** — Sponsored TV GA. SB v4. AI-generated creative for SB. Themes
  targeting GA.
- **2025** — Generative AI listing optimization in Seller Central, AI bid
  strategies expand, AMC Audiences API.
- **2026 (current)** — Sponsored TV is the growth push. AMC democratization
  continues. AI-driven bidding (`autoForSales` + `multipleAdGroups`) is the
  default-on recommendation. Amazon DSP self-service rollout expanding.
  Live shopping (Amazon Live) ads creeping into the API.

Forward bets to make in EOS now:

- **Treat Sponsored TV as in-scope** even pre-revenue — the daily budgets are
  small enough ($10/day) for Lyfe Spectrum launch testing.
- **Build for AMC** — when EOS can write SQL against event-level data, the
  optimization quality jumps an order of magnitude.
- **Build for Marketing Stream** — once EOS has an AWS footprint, hook up
  Stream for live ACOS dashboards. Until then, the polling cron is fine.
- **Don't build creative-generation tooling for SP** — there's no SP creative
  to generate. Spend creative AI cycles on SB video assets instead.

## Conceptual Model and Solution Recipes

### Recipe — Lyfe Spectrum SKU launch (the canonical EOS pattern)

Day 0: SKU is live, 5+ reviews, A+ content done.

```python
# 1. Create the launch campaign tree
auto    = create_campaign("LS-{sku}-AUTO",      targeting="auto",   daily_budget=15)
broad   = create_campaign("LS-{sku}-BROAD",     targeting="manual", daily_budget=10)
phrase  = create_campaign("LS-{sku}-PHRASE",    targeting="manual", daily_budget=10)
exact   = create_campaign("LS-{sku}-EXACT",     targeting="manual", daily_budget=15)
product = create_campaign("LS-{sku}-PRODUCT",   targeting="manual", daily_budget=10)

# 2. One ad group per campaign, one ad each
for c in [auto, broad, phrase, exact, product]:
    ag = create_ad_group(c, default_bid=0.75)
    create_product_ad(ag, asin=sku.asin)

# 3. Seed manual campaigns from competitor research + Amazon recommendations
seed_kws = recommend_keywords(asin=sku.asin)[:30]
for kw in seed_kws:
    create_keyword(broad,  kw, "BROAD",  bid=0.65)
    create_keyword(phrase, kw, "PHRASE", bid=0.75)
    create_keyword(exact,  kw, "EXACT",  bid=0.85)

# 4. Seed product campaign from competitor ASINs
for asin in competitor_asins(sku):
    create_target(product, asin_target=asin, bid=0.70)

# 5. Set top-of-search bid modifier on EXACT (where you have intent)
update_campaign(exact, placement_bidding={"top_of_search": 50})  # +50%

# 6. Schedule the harvest loop to run weekly
```

Day 14: search-term harvest moves converted terms from auto/broad → exact at
higher bid, and unconverted high-click terms become negatives in auto/broad/phrase.

Day 30: First TACOS review. If ACOS < target on EXACT, scale exact daily
budget. If ACOS > target, bid down on losing keywords (don't pause).

Day 60: Add Sponsored Brands video defensive campaign on the ASIN's branded
search terms.

Day 90: Add Sponsored Display remarketing (T00020) on detail page viewers.

### Recipe — Weekly ACOS review

```python
# Pull last 7d spKeyword report
report = pull_report("spKeyword", days=7, group_by=["keyword"])

target_acos = 0.30
for row in report:
    if row["clicks"] < 10: continue                # not enough data
    acos = row["sales7d"] and row["cost"] / row["sales7d"] or float("inf")
    if acos > target_acos * 1.5:
        update_keyword_bid(row["keywordId"], row["bid"] * 0.85)
    elif acos < target_acos * 0.5:
        update_keyword_bid(row["keywordId"], row["bid"] * 1.15)
    log_decision_to_neon(row, acos, action)
```

Always log to Neon. Always cap a single bid adjustment at ±15% so the loop
doesn't oscillate.

### Recipe — Negative keyword harvest

```python
report = pull_report("spSearchTerm", days=14, group_by=["searchTerm"])
existing_negs = list_existing_negatives(profile_id)

new_negs = []
for r in report:
    key = (r["searchTerm"], r["adGroupId"])
    if key in existing_negs: continue
    if r["clicks"] >= 10 and r["purchases7d"] == 0:
        new_negs.append(make_negative(r, "NEGATIVE_EXACT"))
    elif r["clicks"] >= 30 and (r["purchases7d"] / r["clicks"]) < 0.005:
        new_negs.append(make_negative(r, "NEGATIVE_EXACT"))

for batch in chunked(new_negs, 1000):
    post("/sp/negativeKeywords", {"negativeKeywords": batch})
```

### Recipe — Budget pacing

```python
# Run at 06:00, 12:00, 18:00
for c in list_campaigns():
    spent_today = pull_in_day_spend(c.campaign_id)
    pct_of_day  = (now_local() - midnight_local()).total_seconds() / 86400
    pace        = spent_today / c.daily_budget
    if pace > pct_of_day * 1.3 and pct_of_day < 0.5:
        # On track to overspend by noon — throttle
        update_campaign(c.campaign_id, daily_budget=c.daily_budget * 0.85)
```

## Industry Expert and Cutting-Edge Usage

What top sellers and top agencies (Pacvue, Perpetua, Helium 10 Adtomic team)
actually do that the average seller doesn't:

- **SKAGs (Single Keyword Ad Groups)** — one keyword per ad group, one ASIN.
  Lets you set keyword-specific bids without bid-strategy collisions.
  Generates clean reports. Higher operational overhead → automate with the API.
- **Theme + Match-type matrix** — same keyword in EXACT (high bid),
  PHRASE (medium), BROAD (low), each in its own campaign, so the auction
  routes traffic to the most-precise match that converts. Negative-exact the
  exact match in the broad/phrase campaigns to prevent self-cannibalization.
- **Portfolio-level monthly budgets** for spend governance — let Amazon
  pace inside the portfolio cap rather than micromanaging campaign budgets.
- **Bid recommendations as a *floor*, not a target.** Top sellers bid below
  the recommended low end on long-tail terms and let impression share grow
  naturally.
- **Day-parting with Marketing Stream + cron** — pause campaigns 1–6am if
  the conversion data shows zero ROAS in those hours. The API has no native
  day-part — you simulate it.
- **Sponsored Brands defensive on brand terms** is non-negotiable once you
  have brand search volume — competitors will bid on your brand otherwise.
- **Sponsored Display retargeting** with custom audiences from AMC for
  cart-abandoners. This is the bleeding edge as of 2026.
- **AMC instructional queries** — Amazon publishes a library of canned SQL
  for AMC (`amazon-marketing-cloud-instructional-queries`). Top agencies
  modify these for their use cases.
- **Test → roll out** — every new campaign type runs as a 2-week test
  campaign first. Kill criteria are written before launch.

Tools the experts compose with the API:

- **Helium 10 Adtomic** — automation layer with pre-built rules. Useful as
  a benchmark for what your in-house EOS skill should do.
- **Perpetua** — bid automation w/ goal-based targeting (raise me to $X
  ACOS). Heavy ML on top.
- **Pacvue** — enterprise-grade, multi-marketplace, AMC-native. Their
  blog is a goldmine of API patterns.
- **Teikametrics** — Flywheel platform; pioneered TACOS as a north star.
- **Sellozo, Sellics, M19, Ad Badger** — second-tier but each has a
  distinctive optimization angle worth studying.

EOS composition: don't build a Helium 10 clone. Build a *minimum-viable-Pacvue*
that runs the harvest loop, the bid loop, and the budget pacer for one
seller (Lyfe Spectrum) with TACOS as the primary metric. Productize later.

---

## EOS Usage Patterns

### Pattern 1 — `eos_ai/integrations/amazon_ads.py` (the canonical client)

```python
import os, time, gzip, json, random, requests
from typing import Any
from datetime import date

LWA_TOKEN_URL = "https://api.amazon.com/auth/o2/token"
ENDPOINTS = {
    "NA": "https://advertising-api.amazon.com",
    "EU": "https://advertising-api-eu.amazon.com",
    "FE": "https://advertising-api-fe.amazon.com",
}

class AmazonAds:
    def __init__(self):
        self.client_id     = os.environ["LWA_CLIENT_ID"]
        self.client_secret = os.environ["LWA_CLIENT_SECRET"]
        self.refresh_token = os.environ["AMAZON_ADS_REFRESH_TOKEN"]
        self.profile_id    = os.environ["AMAZON_ADS_PROFILE_ID"]
        self.region        = os.environ.get("AMAZON_ADS_REGION", "NA")
        self.base          = ENDPOINTS[self.region]
        self._token        = None
        self._token_exp    = 0

    def _access_token(self) -> str:
        if self._token and time.time() < self._token_exp - 60:
            return self._token
        r = requests.post(LWA_TOKEN_URL, data={
            "grant_type":    "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id":     self.client_id,
            "client_secret": self.client_secret,
        }, timeout=30)
        r.raise_for_status()
        j = r.json()
        self._token     = j["access_token"]
        self._token_exp = time.time() + j["expires_in"]
        return self._token

    def _headers(self, vendor: str) -> dict:
        return {
            "Authorization": f"Bearer {self._access_token()}",
            "Amazon-Advertising-API-ClientId": self.client_id,
            "Amazon-Advertising-API-Scope":    self.profile_id,
            "Content-Type": f"application/vnd.{vendor}.v3+json",
            "Accept":       f"application/vnd.{vendor}.v3+json",
        }

    def call(self, method: str, path: str, vendor: str, body: Any = None) -> dict:
        url = f"{self.base}{path}"
        for attempt in range(6):
            r = requests.request(method, url, headers=self._headers(vendor),
                                 json=body, timeout=60)
            if r.status_code == 429:
                time.sleep((2 ** attempt) + random.random())
                continue
            req_id = r.headers.get("x-amzn-RequestId", "?")
            if not r.ok:
                # Log to Neon: (req_id, status, body, path)
                raise RuntimeError(f"{r.status_code} {path} req={req_id} {r.text[:500]}")
            return r.json()
        raise RuntimeError(f"throttled after 6 retries: {path}")

    def request_report(self, report_type_id: str, group_by: list[str],
                       columns: list[str], start: date, end: date) -> str:
        body = {
            "name": f"{report_type_id}-{start}-{end}",
            "startDate": start.isoformat(),
            "endDate":   end.isoformat(),
            "configuration": {
                "adProduct": "SPONSORED_PRODUCTS",
                "groupBy": group_by,
                "columns": columns,
                "reportTypeId": report_type_id,
                "timeUnit": "DAILY",
                "format":   "GZIP_JSON",
            },
        }
        return self.call("POST", "/reporting/reports",
                         "createasyncreportrequest", body)["reportId"]

    def wait_report(self, report_id: str, poll: int = 15, timeout: int = 1800) -> list[dict]:
        deadline = time.time() + timeout
        while True:
            j = self.call("GET", f"/reporting/reports/{report_id}",
                          "createasyncreportrequest")
            if j["status"] == "COMPLETED":
                gz = requests.get(j["url"], timeout=120).content
                return json.loads(gzip.decompress(gz))
            if j["status"] == "FAILED":
                raise RuntimeError(j.get("failureReason", "report failed"))
            if time.time() > deadline:
                raise TimeoutError(f"report {report_id} not ready in {timeout}s")
            time.sleep(poll)
```

### Pattern 2 — Lyfe Spectrum launch skill

`skills/business/lyfe_spectrum/launch_amazon_ads/SKILL.md` runs the canonical
SKU launch tree (auto + broad + phrase + exact + product) when a new SKU is
ingested. The skill calls `AmazonAds.call("POST", "/sp/campaigns", "spCampaign", body=...)`
five times in batch and writes the resulting campaign ids back to the SKU
record in Neon.

Verification step in the skill:
```bash
python3 -c "
from eos_ai.integrations.amazon_ads import AmazonAds
client = AmazonAds()
print(client.call('POST', '/sp/campaigns/list', 'spCampaign',
                  {'maxResults': 5}))
"
```

### Pattern 3 — Nightly bid loop

`scripts/scheduled/amazon_ads_bid_loop.sh` runs at 03:00 PT (Lyfe Spectrum
profile is US). It:

1. Requests `spKeyword` and `spSearchTerm` reports for last 7d.
2. Polls until COMPLETED.
3. Writes raw rows to Neon (`amazon_ads_keyword_perf`, `amazon_ads_search_term_perf`).
4. Computes ACOS per keyword vs target_acos from BIS (per-SKU).
5. Generates bid adjustments capped at ±15%.
6. Runs the bid adjustments via `PUT /sp/keywords` in 1000-item batches.
7. Generates negative keyword harvest candidates and posts them.
8. Logs every decision to `amazon_ads_decisions` table for reversal.
9. Posts a summary to Discord via os-bot.

### Pattern 4 — TACOS in the morning brief

`scripts/call_prep.py` joins `amazon_ads_campaign_perf` (yesterday's ad
spend + ad sales) with `sp_api_orders` (yesterday's total sales) for each
Lyfe Spectrum SKU and surfaces:

```
SKU XYZ — spend $42, ad sales $138 (ACOS 30%), total sales $410 (TACOS 10.2%)
SKU ABC — spend $18, ad sales $22  (ACOS 82%), total sales $35  (TACOS 51%)  ⚠
```

The ⚠ TACOS alert escalates to the CEO agent (via `agent_type='ceo'`) for a
strategic decision: kill the SKU, fix the listing, or restructure the campaign.

### Pattern 5 — Gotchas captured

Every Amazon Ads error EOS encounters in production gets a row in
`/opt/OS/skills/tools/amazon_ads/SKILL.md`'s Gotchas section. The
operationalization principle: never debug the same error twice.

---

## Gotchas

- **`Amazon-Advertising-API-Scope` header missing → 401.** Profile id is per-call.
- **`application/json` Content-Type → 415.** Use `application/vnd.<resource>.v3+json`.
- **Reports are async — no synchronous endpoint exists.** Plan for 1–10 min latency.
- **Report download URL expires in ~30 min.** Download immediately on COMPLETED.
- **`url` is pre-signed S3 — do not add Authorization header.** It will 403.
- **Region endpoint must match profile.** US profile from EU endpoint = 404.
- **`stateFilter` defaults to ENABLED only on list calls.** Pass `["ENABLED","PAUSED","ARCHIVED"]` if you're hunting.
- **`servingStatus` ≠ `state`.** A campaign can be `state=ENABLED` but not serving due to `BILLING_ERROR`, `AD_GROUPS_PAUSED`, `OUT_OF_BUDGET`.
- **Batch responses are 207 Multi-Status — parse `success[]` and `error[]` per item.**
- **`index` in error rows maps to your input array position.** That's the only way to attribute errors.
- **Bid minimums vary by marketplace.** US SP = $0.02. JP = ¥2. Validate before POST.
- **Daily budget minimum US = $1.00.** Below that → `400 INVALID_BUDGET`.
- **Keyword text > 80 chars or > 10 words → 422.** Pre-validate.
- **LWA refresh token revokes on seller password change.** Build a re-auth path.
- **LWA token endpoint is rate-limited (~5 rps).** Cache the access token for ~55 min.
- **Auto-campaign expansions are not visible until first impressions.** New auto campaign → wait 24h.
- **Pausing → enabling propagation lag ~30 min.** Don't loop pause/enable in seconds.
- **Bid recommendations are skewed toward Amazon's revenue.** Treat as upper bound.
- **`spSearchTerm` reports include 0-click rows.** Filter `clicks > 0` for harvest.
- **Sponsored Brands video creative → uploaded via `/sb/v4/creatives`, referenced by id.** Not inline.
- **SB video specs: 6–45s, 16:9 or 1:1, ≤500MB, no audio-only.**
- **`/v2/profiles` is the only v2 endpoint still canonical.** Everything else → v3.
- **Time zones are profile-local, not UTC.** A "2026-04-05" report for a US profile is PT, not UTC.
- **Currency is profile-local.** Convert to USD at ingestion if you join across marketplaces.
- **Halo sales are in `spPurchasedProduct`, not `spAdvertisedProduct`.** Two different reports.
- **Marketing Stream is the ONLY sub-hour data path.** Reports API minimum granularity is daily.
- **AMC and DSP are gated** — Ads API token alone is not enough.
- **Portfolio budgets are monthly only**, not daily. Use them for spend governance, not pacing.
- **Top-of-search bid modifier is the highest-leverage lever in SP** — most sellers leave it at 0%.
- **Don't pause losing campaigns — bid them down to $0.02.** Paused campaigns lose history.
- **`rate-limit` 429s are per (profile, endpoint) tuple**, not per account.
- **`x-amzn-RequestId` is mandatory in support tickets.** Log every non-2xx with it.
- **JSON entity ids are 15+ digit longs — keep them as strings.** Python int conversion can lose precision in some serializers.
- **Snapshot endpoints (legacy v2) are still the fastest way to bulk-export entities.** Use for nightly state mirrors.
- **When the Reports API says `FAILED` with no reason**, the most common cause is asking for a column the `groupBy` doesn't support. Re-validate the column matrix at `advertising.amazon.com/API/docs/en-us/reference/reporting-api-v3`.
- **Never POST keywords one at a time.** Batch up to 1000. The API was designed for it.
- **Never optimize ACOS in isolation.** Always pair with TACOS from SP-API.
- **Never delete auto campaigns.** They're your free keyword research engine.
