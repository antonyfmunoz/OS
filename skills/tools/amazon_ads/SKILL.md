<<<<<<< Updated upstream
---
name: amazon_ads
description: "Use when managing Amazon Advertising campaigns via the Ads API (Sponsored Products/Brands/Display, DSP), pulling performance reports, analyzing ACOS/TACOS for Lyfe Spectrum, building keyword/bid optimization loops, or planning Amazon ad strategy. For Seller Central inventory/orders use amazon_seller_central."
allowed-tools: "Read, Bash, Write, Edit, WebFetch"
version: 1.0
source_url: "https://advertising.amazon.com/API/docs"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "v3"
sdk_version: "python-amazon-ad-api 0.7.x (community); official Amazon Ads SDKs (Java/Node/Python) 2024+"
speed_category: stable
trigger: both
effort: low
context: fork
---

# Tool: Amazon Ads

## What This Tool Does

Amazon Advertising API v3 is the programmatic surface for the entire Amazon
ad ecosystem: Sponsored Products (keyword + product targeting on search and
detail pages), Sponsored Brands (banner + video on search), Sponsored Display
(remarketing, audiences, off-Amazon), Sponsored TV (CTV), Amazon DSP
(programmatic display, partial API), Amazon Attribution (off-Amazon traffic
measurement), and Amazon Marketing Cloud (AMC, clean-room SQL on event-level
data). It is a *campaign management + reporting* API, not a real-time bidding
API — the auction itself runs inside Amazon.

Core capabilities:

- **Profiles** — one per (account, marketplace, country). Every API call must
  carry an `Amazon-Advertising-API-Scope` header with the profile id.
- **Campaign management** — CRUD on campaigns, ad groups, keywords, product
  ads, product/audience targets, negative keywords, portfolios, budgets, bids.
- **Reports API (async)** — request a v3 report, poll status, download a
  gzipped JSON or CSV from a pre-signed S3 URL. There is no synchronous
  reporting at scale.
- **Recommendations** — keyword recs, bid recs, budget recs, negative keyword
  recs straight from Amazon's models.
- **Audiences** — first-party + Amazon-modeled audiences for SD and DSP.
- **Snapshots** — point-in-time entity exports (campaigns, ad groups, etc.).
- **Brand metrics, Stores analytics, DSP, AMC** — adjacent surfaces under the
  same LWA token, separate scopes.

Authentication is Login With Amazon (LWA) OAuth 2.0 — the *same identity* used
by Selling Partner API (SP-API), but a different scope (`advertising::campaign_management`)
and a different set of endpoints. The refresh token is long-lived; the access
token expires every 60 minutes.

## EOS Integration

Amazon Ads is the primary paid-traffic surface for **Lyfe Spectrum** (apparel)
once SKUs are live in Amazon's catalog. EOS uses it to:

- **Launch-phase campaign automation** — when a new SKU ships, an EOS skill
  spins up the canonical campaign tree (1 auto + 1 broad + 1 phrase + 1 exact
  research campaign + 1 product-targeting campaign) with seed bids derived from
  the bid recommendations endpoint.
- **ACOS-first bid loop** — nightly Reports API pull (search term report +
  keyword report + advertised product report) feeds the optimization agent.
  Keywords with ACOS > 1.5x target ACOS get bid-down or paused; keywords with
  ACOS < 0.5x target ACOS get bid-up. All decisions logged to Neon.
- **Negative keyword harvest** — search term report rows with > N clicks and
  zero attributed sales become campaign-negatives (exact) automatically.
  Ambiguous brand-adjacent terms become negative-phrase.
- **Budget pacing** — daily spend pull at 06:00, 12:00, 18:00. If a campaign
  is on pace to overspend its monthly budget, daily budget is throttled.
- **TACOS monitoring** — combined with the **amazon_seller_central** skill
  (SP-API orders + sales) the orchestrator computes Total ACOS (ad spend /
  total sales, not just ad-attributed sales) and surfaces it in the morning brief.
- **ROAS attribution loop** — Amazon Attribution API ingests off-Amazon
  traffic (Lyfe Spectrum content posts, Initiate Arena email blasts) to
  attribute upstream content to Amazon conversions.

Sibling skill cross-refs:
- **amazon_seller_central** — SP-API for inventory, orders, listings,
  conversion-side data. Shares LWA app, different scope.
- **amazon_associates** — affiliate PA-API. Different program, different keys.
- **google_ads / meta_ads / tiktok_ads / youtube_ads** — parallel paid skills.
  EOS routes to the right skill via channel router.

## Authentication

LWA OAuth 2.0 authorization-code flow, then long-lived refresh token.

```bash
# Required env (eos_ai/.env)
LWA_CLIENT_ID=amzn1.application-oa2-client.xxxx
LWA_CLIENT_SECRET=xxxx
AMAZON_ADS_REFRESH_TOKEN=Atzr|xxxx
AMAZON_ADS_PROFILE_ID=1234567890123456     # one per marketplace
AMAZON_ADS_REGION=NA                       # NA | EU | FE
```

Endpoint roots by region:
- NA: `https://advertising-api.amazon.com`
- EU: `https://advertising-api-eu.amazon.com`
- FE: `https://advertising-api-fe.amazon.com`

```python
import os, requests

def get_access_token() -> str:
    r = requests.post("https://api.amazon.com/auth/o2/token", data={
        "grant_type": "refresh_token",
        "refresh_token": os.environ["AMAZON_ADS_REFRESH_TOKEN"],
        "client_id":     os.environ["LWA_CLIENT_ID"],
        "client_secret": os.environ["LWA_CLIENT_SECRET"],
    }, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]   # 60 min TTL — cache it
```

Required headers on **every** Ads API call:

```
Authorization: Bearer <access_token>
Amazon-Advertising-API-ClientId: <LWA_CLIENT_ID>
Amazon-Advertising-API-Scope: <profile_id>
Content-Type: application/vnd.spCampaign.v3+json    # varies per resource
```

The `Content-Type` / `Accept` for v3 endpoints is *resource-specific*
(e.g. `application/vnd.spCampaign.v3+json`,
`application/vnd.spKeyword.v3+json`,
`application/vnd.createasyncreportrequest.v3+json`). Using a generic
`application/json` will return `415 Unsupported Media Type` on v3.

## Quick Reference

### List profiles (do this once per account to discover profile_ids)

```python
import requests
HEADERS_BASE = {
    "Authorization": f"Bearer {get_access_token()}",
    "Amazon-Advertising-API-ClientId": os.environ["LWA_CLIENT_ID"],
}
r = requests.get("https://advertising-api.amazon.com/v2/profiles", headers=HEADERS_BASE)
profiles = r.json()
# [{"profileId": 1234567890, "countryCode": "US", "currencyCode": "USD",
#   "accountInfo": {"marketplaceStringId": "ATVPDKIKX0DER", "type": "seller"}}, ...]
```

### List Sponsored Products campaigns (v3)

```python
url = "https://advertising-api.amazon.com/sp/campaigns/list"
headers = {
    **HEADERS_BASE,
    "Amazon-Advertising-API-Scope": str(os.environ["AMAZON_ADS_PROFILE_ID"]),
    "Content-Type": "application/vnd.spCampaign.v3+json",
    "Accept":       "application/vnd.spCampaign.v3+json",
}
body = {"maxResults": 100, "stateFilter": {"include": ["ENABLED", "PAUSED"]}}
r = requests.post(url, headers=headers, json=body)
data = r.json()  # {"campaigns": [...], "nextToken": "..."}
```

### Request a search term report (v3 Reporting)

```python
url = "https://advertising-api.amazon.com/reporting/reports"
headers = {
    **HEADERS_BASE,
    "Amazon-Advertising-API-Scope": str(os.environ["AMAZON_ADS_PROFILE_ID"]),
    "Content-Type": "application/vnd.createasyncreportrequest.v3+json",
}
body = {
    "name": "spSearchTerm-daily",
    "startDate": "2026-03-30",
    "endDate":   "2026-04-05",
    "configuration": {
        "adProduct": "SPONSORED_PRODUCTS",
        "groupBy": ["searchTerm"],
        "columns": [
            "date","campaignId","adGroupId","keywordId","keyword","matchType",
            "searchTerm","impressions","clicks","cost","purchases7d","sales7d",
            "acosClicks7d","roasClicks7d"
        ],
        "reportTypeId": "spSearchTerm",
        "timeUnit": "DAILY",
        "format": "GZIP_JSON",
    },
}
report_id = requests.post(url, headers=headers, json=body).json()["reportId"]
```

### Poll + download

```python
import time, gzip, json
status_url = f"https://advertising-api.amazon.com/reporting/reports/{report_id}"
while True:
    j = requests.get(status_url, headers=headers).json()
    if j["status"] == "COMPLETED":
        download_url = j["url"]    # short-lived pre-signed S3 URL
        break
    if j["status"] == "FAILED":
        raise RuntimeError(j.get("failureReason"))
    time.sleep(15)

gz = requests.get(download_url).content
rows = json.loads(gzip.decompress(gz))   # list of dicts
```

### Create a negative keyword (campaign-level)

```python
url = "https://advertising-api.amazon.com/sp/negativeKeywords"
headers = {**HEADERS_BASE,
           "Amazon-Advertising-API-Scope": str(os.environ["AMAZON_ADS_PROFILE_ID"]),
           "Content-Type": "application/vnd.spNegativeKeyword.v3+json"}
body = {"negativeKeywords": [{
    "campaignId": "123456789",
    "adGroupId":  "987654321",
    "keywordText":"cheap",
    "matchType":  "NEGATIVE_EXACT",
    "state":      "ENABLED",
}]}
r = requests.post(url, headers=headers, json=body)
```

## Conceptual Model

**Five-level hierarchy** (Sponsored Products):

```
profile (account × marketplace)
 └── portfolio          (optional spend grouping, monthly budget cap)
      └── campaign      (daily budget, targeting type, bidding strategy)
           └── ad group (default bid, one product set)
                ├── product ad         (one ASIN being advertised)
                ├── keyword | target   (the auction lever)
                └── negative keyword | negative target
```

Sponsored Brands and Sponsored Display use the same shape with different
auction inventory and creative assets.

**ACOS / TACOS calculus**

```
ACOS  = ad_spend / ad_attributed_sales       # ad efficiency in isolation
ROAS  = 1 / ACOS
TACOS = ad_spend / total_sales               # ad spend as % of all revenue
```

ACOS by itself is misleading: a 30% ACOS on a SKU with no organic sales is
worse than a 60% ACOS on a SKU with strong organic halo. TACOS is the EOS
north-star metric for Amazon ad health, computed by joining the Ads API
report (ad spend, ad sales) with SP-API orders (total sales) over the same
window.

**Reports API async lifecycle**

```
POST /reporting/reports         → reportId, status=PENDING
GET  /reporting/reports/{id}    → status=PROCESSING → COMPLETED → url (S3, ~30 min TTL)
GET  <s3 url>                   → gzipped JSON / CSV
```

There is no synchronous "give me yesterday's data now." Even for one day of
one campaign, you go through the async pipeline. Bake polling and exponential
backoff into every report skill — NEVER block the cognitive loop on a
synchronous poll.

**Negative keyword harvest loop** (the highest-leverage pattern)

```
1. Pull spSearchTerm report for last 14 days
2. For each (search_term, campaign_id, ad_group_id):
     if clicks > 10 and orders == 0:           → NEGATIVE_EXACT
     if clicks > 30 and orders/clicks < 0.5%:  → NEGATIVE_EXACT
     if matches a brand-adjacent regex:        → NEGATIVE_PHRASE
3. Dedupe vs existing negatives (list endpoint)
4. POST batch to /sp/negativeKeywords
5. Log everything to Neon for reversal
```

This single loop, run weekly, is the difference between a 60% ACOS account
and a 25% ACOS account.

## Gotchas

- **`Amazon-Advertising-API-Scope` is mandatory on every call.** Forgetting it
  returns `401 Unauthorized` even with a valid token. Profile id is not baked
  into the token — it's a header.
- **Reports are async — no exceptions.** Even tiny reports go through the
  PENDING → PROCESSING → COMPLETED pipeline. Plan for 1–10 min latency.
- **Region isolation.** A profile in NA cannot be queried from the EU
  endpoint and vice versa. Pick the endpoint by `countryCode` of the profile.
- **v3 `Content-Type` is resource-specific.** `application/json` returns
  `415`. Always use the `vnd.<resource>.v3+json` form.
- **Report `url` is a short-lived pre-signed S3 link** (~30 min). Download
  immediately on COMPLETED — don't store the URL for "later."
- **Bid minimums vary by marketplace.** US Sponsored Products minimum is
  $0.02; some marketplaces are higher. Always validate against the
  recommendations endpoint before creating bids — `400 INVALID_BID` is
  silent-killer common.
- **Campaign state transitions are not free.** Pausing → enabling can take
  up to ~30 min to fully propagate to the auction. Don't design loops that
  pause+enable in seconds.
- **Rate limits are per-profile and per-resource**, not per-account. Hitting
  the limit on a `POST /sp/keywords` does not slow your `GET /sp/campaigns/list`.
  Track 429s per (profile, endpoint) tuple.
- **LWA refresh tokens revoke on password change** for the seller. Build a
  re-auth path; do not assume the refresh token is forever.
- **Sponsored Brands video has hard creative requirements** — 6–45 seconds,
  16:9 or 1:1, ≤500 MB, no audio-only. The asset upload happens via the
  `/sb/v4/creatives` endpoints, NOT in the campaign create call.
- **Auto campaigns generate the best keyword research data** — never delete
  them, even when ACOS is high. Treat them as a research surface and let
  exact-match campaigns capture converted terms.
- **AMC and DSP are gated.** AMC requires an Amazon Ads account manager to
  enable. DSP requires either self-service onboarding or a managed contract.
  The Ads API token alone is not enough.

See references/best_practices.md for the full 19-section creator-level knowledge base.
=======
---
name: amazon_ads
description: "Use when managing Amazon Advertising campaigns via the Ads API (Sponsored Products/Brands/Display, DSP), pulling performance reports, analyzing ACOS/TACOS for Lyfe Spectrum, building keyword/bid optimization loops, or planning Amazon ad strategy. For Seller Central inventory/orders use amazon_seller_central."
allowed-tools: "Read, Bash, Write, Edit, WebFetch"
version: 1.0
source_url: "https://advertising.amazon.com/API/docs"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "v3"
sdk_version: "python-amazon-ad-api 0.7.x (community); official Amazon Ads SDKs (Java/Node/Python) 2024+"
speed_category: stable
---

# Tool: Amazon Ads

## What This Tool Does

Amazon Advertising API v3 is the programmatic surface for the entire Amazon
ad ecosystem: Sponsored Products (keyword + product targeting on search and
detail pages), Sponsored Brands (banner + video on search), Sponsored Display
(remarketing, audiences, off-Amazon), Sponsored TV (CTV), Amazon DSP
(programmatic display, partial API), Amazon Attribution (off-Amazon traffic
measurement), and Amazon Marketing Cloud (AMC, clean-room SQL on event-level
data). It is a *campaign management + reporting* API, not a real-time bidding
API — the auction itself runs inside Amazon.

Core capabilities:

- **Profiles** — one per (account, marketplace, country). Every API call must
  carry an `Amazon-Advertising-API-Scope` header with the profile id.
- **Campaign management** — CRUD on campaigns, ad groups, keywords, product
  ads, product/audience targets, negative keywords, portfolios, budgets, bids.
- **Reports API (async)** — request a v3 report, poll status, download a
  gzipped JSON or CSV from a pre-signed S3 URL. There is no synchronous
  reporting at scale.
- **Recommendations** — keyword recs, bid recs, budget recs, negative keyword
  recs straight from Amazon's models.
- **Audiences** — first-party + Amazon-modeled audiences for SD and DSP.
- **Snapshots** — point-in-time entity exports (campaigns, ad groups, etc.).
- **Brand metrics, Stores analytics, DSP, AMC** — adjacent surfaces under the
  same LWA token, separate scopes.

Authentication is Login With Amazon (LWA) OAuth 2.0 — the *same identity* used
by Selling Partner API (SP-API), but a different scope (`advertising::campaign_management`)
and a different set of endpoints. The refresh token is long-lived; the access
token expires every 60 minutes.

## EOS Integration

Amazon Ads is the primary paid-traffic surface for **Lyfe Spectrum** (apparel)
once SKUs are live in Amazon's catalog. EOS uses it to:

- **Launch-phase campaign automation** — when a new SKU ships, an EOS skill
  spins up the canonical campaign tree (1 auto + 1 broad + 1 phrase + 1 exact
  research campaign + 1 product-targeting campaign) with seed bids derived from
  the bid recommendations endpoint.
- **ACOS-first bid loop** — nightly Reports API pull (search term report +
  keyword report + advertised product report) feeds the optimization agent.
  Keywords with ACOS > 1.5x target ACOS get bid-down or paused; keywords with
  ACOS < 0.5x target ACOS get bid-up. All decisions logged to Neon.
- **Negative keyword harvest** — search term report rows with > N clicks and
  zero attributed sales become campaign-negatives (exact) automatically.
  Ambiguous brand-adjacent terms become negative-phrase.
- **Budget pacing** — daily spend pull at 06:00, 12:00, 18:00. If a campaign
  is on pace to overspend its monthly budget, daily budget is throttled.
- **TACOS monitoring** — combined with the **amazon_seller_central** skill
  (SP-API orders + sales) the orchestrator computes Total ACOS (ad spend /
  total sales, not just ad-attributed sales) and surfaces it in the morning brief.
- **ROAS attribution loop** — Amazon Attribution API ingests off-Amazon
  traffic (Lyfe Spectrum content posts, Initiate Arena email blasts) to
  attribute upstream content to Amazon conversions.

Sibling skill cross-refs:
- **amazon_seller_central** — SP-API for inventory, orders, listings,
  conversion-side data. Shares LWA app, different scope.
- **amazon_associates** — affiliate PA-API. Different program, different keys.
- **google_ads / meta_ads / tiktok_ads / youtube_ads** — parallel paid skills.
  EOS routes to the right skill via channel router.

## Authentication

LWA OAuth 2.0 authorization-code flow, then long-lived refresh token.

```bash
# Required env (eos_ai/.env)
LWA_CLIENT_ID=amzn1.application-oa2-client.xxxx
LWA_CLIENT_SECRET=xxxx
AMAZON_ADS_REFRESH_TOKEN=Atzr|xxxx
AMAZON_ADS_PROFILE_ID=1234567890123456     # one per marketplace
AMAZON_ADS_REGION=NA                       # NA | EU | FE
```

Endpoint roots by region:
- NA: `https://advertising-api.amazon.com`
- EU: `https://advertising-api-eu.amazon.com`
- FE: `https://advertising-api-fe.amazon.com`

```python
import os, requests

def get_access_token() -> str:
    r = requests.post("https://api.amazon.com/auth/o2/token", data={
        "grant_type": "refresh_token",
        "refresh_token": os.environ["AMAZON_ADS_REFRESH_TOKEN"],
        "client_id":     os.environ["LWA_CLIENT_ID"],
        "client_secret": os.environ["LWA_CLIENT_SECRET"],
    }, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]   # 60 min TTL — cache it
```

Required headers on **every** Ads API call:

```
Authorization: Bearer <access_token>
Amazon-Advertising-API-ClientId: <LWA_CLIENT_ID>
Amazon-Advertising-API-Scope: <profile_id>
Content-Type: application/vnd.spCampaign.v3+json    # varies per resource
```

The `Content-Type` / `Accept` for v3 endpoints is *resource-specific*
(e.g. `application/vnd.spCampaign.v3+json`,
`application/vnd.spKeyword.v3+json`,
`application/vnd.createasyncreportrequest.v3+json`). Using a generic
`application/json` will return `415 Unsupported Media Type` on v3.

## Quick Reference

### List profiles (do this once per account to discover profile_ids)

```python
import requests
HEADERS_BASE = {
    "Authorization": f"Bearer {get_access_token()}",
    "Amazon-Advertising-API-ClientId": os.environ["LWA_CLIENT_ID"],
}
r = requests.get("https://advertising-api.amazon.com/v2/profiles", headers=HEADERS_BASE)
profiles = r.json()
# [{"profileId": 1234567890, "countryCode": "US", "currencyCode": "USD",
#   "accountInfo": {"marketplaceStringId": "ATVPDKIKX0DER", "type": "seller"}}, ...]
```

### List Sponsored Products campaigns (v3)

```python
url = "https://advertising-api.amazon.com/sp/campaigns/list"
headers = {
    **HEADERS_BASE,
    "Amazon-Advertising-API-Scope": str(os.environ["AMAZON_ADS_PROFILE_ID"]),
    "Content-Type": "application/vnd.spCampaign.v3+json",
    "Accept":       "application/vnd.spCampaign.v3+json",
}
body = {"maxResults": 100, "stateFilter": {"include": ["ENABLED", "PAUSED"]}}
r = requests.post(url, headers=headers, json=body)
data = r.json()  # {"campaigns": [...], "nextToken": "..."}
```

### Request a search term report (v3 Reporting)

```python
url = "https://advertising-api.amazon.com/reporting/reports"
headers = {
    **HEADERS_BASE,
    "Amazon-Advertising-API-Scope": str(os.environ["AMAZON_ADS_PROFILE_ID"]),
    "Content-Type": "application/vnd.createasyncreportrequest.v3+json",
}
body = {
    "name": "spSearchTerm-daily",
    "startDate": "2026-03-30",
    "endDate":   "2026-04-05",
    "configuration": {
        "adProduct": "SPONSORED_PRODUCTS",
        "groupBy": ["searchTerm"],
        "columns": [
            "date","campaignId","adGroupId","keywordId","keyword","matchType",
            "searchTerm","impressions","clicks","cost","purchases7d","sales7d",
            "acosClicks7d","roasClicks7d"
        ],
        "reportTypeId": "spSearchTerm",
        "timeUnit": "DAILY",
        "format": "GZIP_JSON",
    },
}
report_id = requests.post(url, headers=headers, json=body).json()["reportId"]
```

### Poll + download

```python
import time, gzip, json
status_url = f"https://advertising-api.amazon.com/reporting/reports/{report_id}"
while True:
    j = requests.get(status_url, headers=headers).json()
    if j["status"] == "COMPLETED":
        download_url = j["url"]    # short-lived pre-signed S3 URL
        break
    if j["status"] == "FAILED":
        raise RuntimeError(j.get("failureReason"))
    time.sleep(15)

gz = requests.get(download_url).content
rows = json.loads(gzip.decompress(gz))   # list of dicts
```

### Create a negative keyword (campaign-level)

```python
url = "https://advertising-api.amazon.com/sp/negativeKeywords"
headers = {**HEADERS_BASE,
           "Amazon-Advertising-API-Scope": str(os.environ["AMAZON_ADS_PROFILE_ID"]),
           "Content-Type": "application/vnd.spNegativeKeyword.v3+json"}
body = {"negativeKeywords": [{
    "campaignId": "123456789",
    "adGroupId":  "987654321",
    "keywordText":"cheap",
    "matchType":  "NEGATIVE_EXACT",
    "state":      "ENABLED",
}]}
r = requests.post(url, headers=headers, json=body)
```

## Conceptual Model

**Five-level hierarchy** (Sponsored Products):

```
profile (account × marketplace)
 └── portfolio          (optional spend grouping, monthly budget cap)
      └── campaign      (daily budget, targeting type, bidding strategy)
           └── ad group (default bid, one product set)
                ├── product ad         (one ASIN being advertised)
                ├── keyword | target   (the auction lever)
                └── negative keyword | negative target
```

Sponsored Brands and Sponsored Display use the same shape with different
auction inventory and creative assets.

**ACOS / TACOS calculus**

```
ACOS  = ad_spend / ad_attributed_sales       # ad efficiency in isolation
ROAS  = 1 / ACOS
TACOS = ad_spend / total_sales               # ad spend as % of all revenue
```

ACOS by itself is misleading: a 30% ACOS on a SKU with no organic sales is
worse than a 60% ACOS on a SKU with strong organic halo. TACOS is the EOS
north-star metric for Amazon ad health, computed by joining the Ads API
report (ad spend, ad sales) with SP-API orders (total sales) over the same
window.

**Reports API async lifecycle**

```
POST /reporting/reports         → reportId, status=PENDING
GET  /reporting/reports/{id}    → status=PROCESSING → COMPLETED → url (S3, ~30 min TTL)
GET  <s3 url>                   → gzipped JSON / CSV
```

There is no synchronous "give me yesterday's data now." Even for one day of
one campaign, you go through the async pipeline. Bake polling and exponential
backoff into every report skill — NEVER block the cognitive loop on a
synchronous poll.

**Negative keyword harvest loop** (the highest-leverage pattern)

```
1. Pull spSearchTerm report for last 14 days
2. For each (search_term, campaign_id, ad_group_id):
     if clicks > 10 and orders == 0:           → NEGATIVE_EXACT
     if clicks > 30 and orders/clicks < 0.5%:  → NEGATIVE_EXACT
     if matches a brand-adjacent regex:        → NEGATIVE_PHRASE
3. Dedupe vs existing negatives (list endpoint)
4. POST batch to /sp/negativeKeywords
5. Log everything to Neon for reversal
```

This single loop, run weekly, is the difference between a 60% ACOS account
and a 25% ACOS account.

## Gotchas

- **`Amazon-Advertising-API-Scope` is mandatory on every call.** Forgetting it
  returns `401 Unauthorized` even with a valid token. Profile id is not baked
  into the token — it's a header.
- **Reports are async — no exceptions.** Even tiny reports go through the
  PENDING → PROCESSING → COMPLETED pipeline. Plan for 1–10 min latency.
- **Region isolation.** A profile in NA cannot be queried from the EU
  endpoint and vice versa. Pick the endpoint by `countryCode` of the profile.
- **v3 `Content-Type` is resource-specific.** `application/json` returns
  `415`. Always use the `vnd.<resource>.v3+json` form.
- **Report `url` is a short-lived pre-signed S3 link** (~30 min). Download
  immediately on COMPLETED — don't store the URL for "later."
- **Bid minimums vary by marketplace.** US Sponsored Products minimum is
  $0.02; some marketplaces are higher. Always validate against the
  recommendations endpoint before creating bids — `400 INVALID_BID` is
  silent-killer common.
- **Campaign state transitions are not free.** Pausing → enabling can take
  up to ~30 min to fully propagate to the auction. Don't design loops that
  pause+enable in seconds.
- **Rate limits are per-profile and per-resource**, not per-account. Hitting
  the limit on a `POST /sp/keywords` does not slow your `GET /sp/campaigns/list`.
  Track 429s per (profile, endpoint) tuple.
- **LWA refresh tokens revoke on password change** for the seller. Build a
  re-auth path; do not assume the refresh token is forever.
- **Sponsored Brands video has hard creative requirements** — 6–45 seconds,
  16:9 or 1:1, ≤500 MB, no audio-only. The asset upload happens via the
  `/sb/v4/creatives` endpoints, NOT in the campaign create call.
- **Auto campaigns generate the best keyword research data** — never delete
  them, even when ACOS is high. Treat them as a research surface and let
  exact-match campaigns capture converted terms.
- **AMC and DSP are gated.** AMC requires an Amazon Ads account manager to
  enable. DSP requires either self-service onboarding or a managed contract.
  The Ads API token alone is not enough.

See references/best_practices.md for the full 19-section creator-level knowledge base.
>>>>>>> Stashed changes
