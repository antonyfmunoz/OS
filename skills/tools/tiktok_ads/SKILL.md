<<<<<<< Updated upstream
---
name: tiktok_ads
description: "Use when creating/managing TikTok paid campaigns via the Marketing API, boosting organic posts as Spark Ads, sending server-side conversions through the Events API, managing pixels, custom/lookalike audiences, creatives, or pulling paid-media reporting for Initiate Arena or Lyfe Spectrum."
allowed-tools: "Read, Bash, Write, Edit, WebFetch"
version: 1.0
source_url: "https://business-api.tiktok.com/portal/docs"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "v1.3"
sdk_version: "tiktok-business-api-sdk (Python, official, generated from OpenAPI)"
speed_category: medium
trigger: both
effort: medium
context: fork
---

# Tool: TikTok Marketing API (Ads)

## What This Tool Does

The TikTok Marketing API (a.k.a. TikTok Business API, "Ads API") is the
authenticated REST surface that powers everything inside TikTok Ads Manager:
campaign creation, budgeting, targeting, creative upload, Spark Ads
authorization, pixel + Events API conversion ingestion, audience management,
reporting, and account/asset administration.

It is a separate API surface from the consumer/creator side (`tiktok` skill,
Content Posting API and Display API) — different host, different OAuth, different
scopes, different rate buckets. The Marketing API talks to ad accounts
(`advertiser_id`), not user accounts (`open_id`).

Core capabilities:

- **Campaign hierarchy CRUD** — `campaign → adgroup → ad`, with budget,
  bidding, schedule, targeting, optimization goal at the right level
- **Spark Ads** — boost an organic post by referencing its `tiktok_item_id` and
  a creator-issued authorization code, instead of uploading new creative
- **Events API (CAPI)** — server-to-server conversion ingestion, dedup-paired
  with the browser pixel via `event_id`
- **Pixels & web events** — create/manage pixels, web event rules, attribution
  windows
- **Audience management** — Custom Audiences (file upload, engagement, web,
  app, lead form, customer file) and Lookalikes
- **Creative management** — image/video upload, identity (BC + BC user)
  management, AIGC label, music library
- **Reporting** — synchronous and async report endpoints with metric/dimension
  query language, attribution windows, breakdowns
- **Business Center** — multi-advertiser org structure, asset sharing, member
  roles

## EOS Integration

Paid TikTok is the canonical paid surface for Initiate Arena founder content
and Lyfe Spectrum drops. The EOS pattern is **Spark Ads on top of organic
content** — content IS the advertising. We never produce ad-only creative; we
boost the founder posts that already work organically.

Primary EOS uses:

- **Spark Ads boosting** — pick a high-performing organic post (sourced via
  the `tiktok` skill metrics), request an authorization code from the creator
  identity, create an adgroup with `identity_type=AUTH_CODE` and
  `identity_authorized_bc_id`, attach the `tiktok_item_id`, set a small daily
  budget, ship to a `WEB_CONVERSIONS` or `LANDING_PAGE` objective
- **Events API** — server-side conversions from the Initiate Arena funnel
  (`Lead`, `CompletePayment`, `Subscribe`) flow through eos_ai → Events API
  with hashed `email`/`phone`/`external_id` and an `event_id` shared with the
  pixel for deduplication
- **Reporting cron** — nightly pull of cost, CPM, CPC, CTR, CPA, ROAS by ad
  for the prior 7 days, written to Neon for the morning brief
- **Custom audiences** — Initiate Arena CRM Tier-1 leads pushed as a hashed
  customer file audience for retargeting and lookalike seeding
- **Budget guardrails** — every spend-affecting call (`campaign/create`,
  `campaign/update`, `adgroup/create`, `adgroup/update`, `*/status/update`
  with `ENABLE`) is **CRITICAL** risk and routes through the
  authority_engine for human approval

Canonical EOS pattern:

- All calls go through `eos_ai/tiktok_ads_client.py` (single chokepoint)
- Long-lived access tokens cached in Neon (`integrations.tiktok_ads`)
- All write calls log to `audit.paid_media_changes` before execution
- Spend caps enforced client-side: `daily_budget` and `lifetime_budget`
  validated against the `budgets.tiktok` ceiling before any create/update
- Reporting reads run as the service account; writes run only after
  authority_engine approval

## Authentication

OAuth 2.0 (TikTok for Business / TikTok Ads Manager identity), distinct from
the consumer TikTok Login Kit.

Flow:

1. Register a developer app at <https://business-api.tiktok.com/portal>
2. Configure redirect URI and request scopes (e.g. `Ad Account Management`,
   `Ads Management`, `Audience Management`, `Reporting`, `Business Center
   Management`, `Pixel`, `Creative Management`, `Conversion Event`)
3. Redirect the human to the TikTok auth URL with `app_id`, `state`,
   `redirect_uri`
4. Receive `auth_code` on the redirect
5. Exchange for `access_token` via
   `POST /open_api/v1.3/oauth2/access_token/` with `app_id`, `secret`,
   `auth_code`
6. Response includes `access_token`, `advertiser_ids` (the list of ad accounts
   the granting user authorized), and a long expiry (effectively non-expiring
   for first-party app + own ad account, but you must still handle revocation)

Every authenticated request sets `Access-Token: <token>` as a header (NOT a
bearer token in `Authorization`). The `advertiser_id` is a request-level
parameter on almost every endpoint; one token can drive many advertisers if
authorized.

```bash
curl -H "Access-Token: $TIKTOK_ADS_TOKEN" \
  "https://business-api.tiktok.com/open_api/v1.3/advertiser/info/?advertiser_ids=%5B%22${ADV_ID}%22%5D"
```

For Spark Ads on creator content, you additionally need either:
- A **Spark Ads authorization code** the creator generates in-app (video → ⋯ →
  Ad settings → Ad authorization → Generate code), OR
- The creator's TikTok identity added to the Business Center as an authorized
  identity (no per-video code needed; covers all their posts)

## Quick Reference

### Hosts

- Production: `https://business-api.tiktok.com`
- Sandbox: `https://sandbox-ads.tiktok.com` (separate app, separate token,
  separate fake advertiser_id — does NOT spend money, perfect for EOS smoke
  tests)

### Create campaign → adgroup → ad

```bash
# 1. Campaign
curl -X POST "https://business-api.tiktok.com/open_api/v1.3/campaign/create/" \
  -H "Access-Token: $TIKTOK_ADS_TOKEN" -H "Content-Type: application/json" \
  -d '{
    "advertiser_id": "'"$ADV_ID"'",
    "campaign_name": "IA-FounderContent-2026-04",
    "objective_type": "WEB_CONVERSIONS",
    "budget_mode": "BUDGET_MODE_DAY",
    "budget": 20.00
  }'

# 2. Adgroup (Spark Ads identity, web conversions, pixel optimization)
curl -X POST "https://business-api.tiktok.com/open_api/v1.3/adgroup/create/" \
  -H "Access-Token: $TIKTOK_ADS_TOKEN" -H "Content-Type: application/json" \
  -d '{
    "advertiser_id": "'"$ADV_ID"'",
    "campaign_id": "'"$CAMPAIGN_ID"'",
    "adgroup_name": "IA-US-25-44-M",
    "placement_type": "PLACEMENT_TYPE_NORMAL",
    "placements": ["PLACEMENT_TIKTOK"],
    "promotion_type": "WEBSITE",
    "pixel_id": "'"$PIXEL_ID"'",
    "optimization_event": "COMPLETE_PAYMENT",
    "billing_event": "OCPM",
    "bid_type": "BID_TYPE_NO_BID",
    "budget_mode": "BUDGET_MODE_DAY",
    "budget": 20.00,
    "schedule_type": "SCHEDULE_FROM_NOW",
    "schedule_start_time": "2026-04-07 00:00:00",
    "location_ids": ["6252001"],
    "gender": "GENDER_MALE",
    "age_groups": ["AGE_25_34","AGE_35_44"],
    "operation_status": "DISABLE"
  }'

# 3. Ad — Spark Ad referencing organic post
curl -X POST "https://business-api.tiktok.com/open_api/v1.3/ad/create/" \
  -H "Access-Token: $TIKTOK_ADS_TOKEN" -H "Content-Type: application/json" \
  -d '{
    "advertiser_id": "'"$ADV_ID"'",
    "adgroup_id": "'"$ADGROUP_ID"'",
    "creatives": [{
      "ad_name": "IA-Spark-2026-04-07-A",
      "ad_format": "SINGLE_VIDEO",
      "identity_type": "AUTH_CODE",
      "identity_authorized_bc_id": "'"$BC_ID"'",
      "identity_id": "'"$IDENTITY_ID"'",
      "tiktok_item_id": "'"$VIDEO_ID"'",
      "call_to_action": "LEARN_MORE",
      "landing_page_url": "https://initiatearena.com/?utm_source=tiktok"
    }]
  }'
```

### Events API (server-side conversion)

```bash
curl -X POST "https://business-api.tiktok.com/open_api/v1.3/event/track/" \
  -H "Access-Token: $TIKTOK_ADS_TOKEN" -H "Content-Type: application/json" \
  -d '{
    "event_source": "web",
    "event_source_id": "'"$PIXEL_ID"'",
    "data": [{
      "event": "CompletePayment",
      "event_time": 1743984000,
      "event_id": "ia-order-90218",
      "user": {
        "email": "<sha256_lower_trim>",
        "phone": "<sha256_e164>",
        "external_id": "<sha256_user_id>",
        "ttclid": "E.C.P.xxxxx",
        "ttp": "<_ttp_cookie>",
        "ip": "203.0.113.4",
        "user_agent": "Mozilla/5.0 ..."
      },
      "properties": {
        "currency": "USD",
        "value": 750.00,
        "content_id": "ia-cohort-2026-04",
        "content_type": "product"
      },
      "page": { "url": "https://initiatearena.com/checkout/success" }
    }]
  }'
```

### Reporting (synchronous)

```bash
curl -G "https://business-api.tiktok.com/open_api/v1.3/report/integrated/get/" \
  -H "Access-Token: $TIKTOK_ADS_TOKEN" \
  --data-urlencode 'advertiser_id='"$ADV_ID" \
  --data-urlencode 'report_type=BASIC' \
  --data-urlencode 'data_level=AUCTION_AD' \
  --data-urlencode 'dimensions=["ad_id","stat_time_day"]' \
  --data-urlencode 'metrics=["spend","impressions","clicks","ctr","cpc","cpm","conversion","cost_per_conversion","conversion_rate"]' \
  --data-urlencode 'start_date=2026-03-30' \
  --data-urlencode 'end_date=2026-04-06' \
  --data-urlencode 'page=1' --data-urlencode 'page_size=200'
```

### Status toggles (the spend-critical calls)

```bash
# Enable a campaign — CRITICAL, requires authority_engine approval
curl -X POST "https://business-api.tiktok.com/open_api/v1.3/campaign/status/update/" \
  -H "Access-Token: $TIKTOK_ADS_TOKEN" -H "Content-Type: application/json" \
  -d '{"advertiser_id":"'"$ADV_ID"'","campaign_ids":["'"$CAMPAIGN_ID"'"],"operation_status":"ENABLE"}'
```

## Conceptual Model

**Advertiser is the wallet. Hierarchy is the lever. Identity is the face.
Pixel is the feedback loop.**

Every spend-affecting object is scoped to an `advertiser_id` — that is the
billing boundary, the access boundary, and the reporting boundary. Inside one
advertiser, the `campaign → adgroup → ad` hierarchy carves up *what to do*
(objective), *who to show it to* (targeting + budget + bid), and *what they
see* (creative + identity + landing). Each level owns a different decision —
putting budget on the wrong level, or targeting on the wrong level, is the
single biggest source of "why is my campaign not delivering" tickets.

**Identity** is the face the ad wears. For uploaded creative, you create a
"Custom Identity" with a name + avatar. For Spark Ads, the identity is a real
TikTok account (creator or brand) that has either been added to your Business
Center or has issued a per-video authorization code. The same ad object
references both the identity and the `tiktok_item_id` of the post being
boosted.

**Pixel + Events API** is the closed loop that lets the auction optimize. The
auction can only optimize toward events it sees. Web pixel events are
ad-blocker-fragile and Safari-fragile; Events API is server-side and durable.
Best practice is **send both** with a shared `event_id` so TikTok can
deduplicate. Without conversion signal back to TikTok, OCPM bidding has nothing
to learn from and degenerates to expensive impression buying.

If you internalize advertiser-as-wallet, hierarchy-as-lever, identity-as-face,
pixel-as-feedback, every confusing TikTok Ads behavior becomes obvious:

- "Budget changes aren't applying" → you set it on the wrong level (CBO vs ABO)
- "Spark Ad got rejected" → identity not authorized, or auth code expired
- "Reporting shows zero conversions" → pixel + events API not wired, or
  optimization_event mismatched
- "My API call returned 200 but nothing happened" → check the JSON body
  `code`/`message` — TikTok returns HTTP 200 with embedded error codes

## Gotchas

- **HTTP 200 != success.** TikTok wraps every response in
  `{"code":N,"message":"...","data":{}}`. Always check `code == 0`. Anything
  else is a failure even though the HTTP status was 200. The #1 integration
  bug.
- **`Access-Token` header, not `Authorization: Bearer`.** Wrong header = 40105
  auth error. Different from every other major API.
- **`advertiser_id` is a STRING in all params,** even though it looks numeric.
  JSON number → 40002 invalid params. Always quote it.
- **Array params in GET requests must be JSON-encoded then URL-encoded** —
  `advertiser_ids=["1234"]` not `advertiser_ids=1234`. The
  `--data-urlencode 'metrics=["spend"]'` pattern is mandatory.
- **`budget_mode=BUDGET_MODE_INFINITE` exists** and is the default if you omit
  budget on a CBO campaign — meaning unbounded spend. NEVER omit. Always set
  `BUDGET_MODE_DAY` or `BUDGET_MODE_TOTAL` with a hard number.
- **Minimum daily budget** is currency-dependent: USD ad-level $20,
  campaign-level $50. Below this returns `40002` with no useful explanation.
- **`operation_status: DISABLE` on create** is the safe default — create
  paused, then human-approve before enabling. EOS enforces this.
- **Spark Ads authorization codes expire** (7/30/60/365 days, creator's
  choice). After expiry the ad keeps running until you edit it; on edit it
  dies. Track expiries in Neon.
- **`tiktok_item_id` is the numeric video id, not the share URL.** Extract
  from `https://www.tiktok.com/@user/video/<ID>`.
- **Identity confusion:** `identity_type=AUTH_CODE` requires `identity_id` AND
  `identity_authorized_bc_id`. `identity_type=TT_USER` requires only
  `identity_id` if the user is in your BC. `identity_type=CUSTOMIZED_USER` for
  uploaded creative.
- **Events API hashing:** email/phone/external_id MUST be SHA-256 of
  lowercase-trimmed (email) or E.164 (phone) input. Sending raw PII = silent
  drop, no error. Verify in Events Manager → Test Events.
- **Pixel `event_source_id` IS the pixel code,** despite the field name. Same
  string you find in Ads Manager → Assets → Events.
- **Rate limit is per-app per-advertiser**, roughly 10 QPS for write
  endpoints, 20 QPS for reads, with daily caps. Burst beyond → 40100 / 50002.
  Backoff exponentially with jitter. Reporting endpoints have separate, lower
  buckets.
- **Reporting `data_level` must match `dimensions`.** `AUCTION_AD` data level
  with `campaign_id` dimension = empty result, no error.
- **`stat_time_day` dimension returns dates in advertiser timezone**, not UTC.
  Always read `advertiser/info/` and store the timezone.
- **Sandbox advertisers cannot serve real ads, cannot use real pixels, cannot
  authorize real creator content.** Use sandbox for schema validation and
  authority_engine dry-runs only.
- **Webhooks are limited.** TikTok Ads has *some* webhook support (lead form
  submissions, app event postbacks, Business Center membership) but no general
  "campaign state changed" webhook. For state, you poll.
- **No event deduplication unless `event_id` matches** between pixel and CAPI
  for the same event. Without `event_id` you'll double-count conversions and
  the auction will get bad signal.
- **`promotion_type=WEBSITE` requires a pixel; `APP` requires app_id;
  `LEAD_GEN` requires a lead form id.** Mismatching promotion_type and
  optimization_event is the most common adgroup-create rejection.

See references/best_practices.md for the full 19-section creator-level
knowledge base.
Cross-reference: skills/tools/tiktok/ for organic posting, Display API, and
the metric pull that feeds Spark Ads candidate selection.
=======
---
name: tiktok_ads
description: "Use when creating/managing TikTok paid campaigns via the Marketing API, boosting organic posts as Spark Ads, sending server-side conversions through the Events API, managing pixels, custom/lookalike audiences, creatives, or pulling paid-media reporting for Initiate Arena or Lyfe Spectrum."
allowed-tools: "Read, Bash, Write, Edit, WebFetch"
version: 1.0
source_url: "https://business-api.tiktok.com/portal/docs"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "v1.3"
sdk_version: "tiktok-business-api-sdk (Python, official, generated from OpenAPI)"
speed_category: fast
---

# Tool: TikTok Marketing API (Ads)

## What This Tool Does

The TikTok Marketing API (a.k.a. TikTok Business API, "Ads API") is the
authenticated REST surface that powers everything inside TikTok Ads Manager:
campaign creation, budgeting, targeting, creative upload, Spark Ads
authorization, pixel + Events API conversion ingestion, audience management,
reporting, and account/asset administration.

It is a separate API surface from the consumer/creator side (`tiktok` skill,
Content Posting API and Display API) — different host, different OAuth, different
scopes, different rate buckets. The Marketing API talks to ad accounts
(`advertiser_id`), not user accounts (`open_id`).

Core capabilities:

- **Campaign hierarchy CRUD** — `campaign → adgroup → ad`, with budget,
  bidding, schedule, targeting, optimization goal at the right level
- **Spark Ads** — boost an organic post by referencing its `tiktok_item_id` and
  a creator-issued authorization code, instead of uploading new creative
- **Events API (CAPI)** — server-to-server conversion ingestion, dedup-paired
  with the browser pixel via `event_id`
- **Pixels & web events** — create/manage pixels, web event rules, attribution
  windows
- **Audience management** — Custom Audiences (file upload, engagement, web,
  app, lead form, customer file) and Lookalikes
- **Creative management** — image/video upload, identity (BC + BC user)
  management, AIGC label, music library
- **Reporting** — synchronous and async report endpoints with metric/dimension
  query language, attribution windows, breakdowns
- **Business Center** — multi-advertiser org structure, asset sharing, member
  roles

## EOS Integration

Paid TikTok is the canonical paid surface for Initiate Arena founder content
and Lyfe Spectrum drops. The EOS pattern is **Spark Ads on top of organic
content** — content IS the advertising. We never produce ad-only creative; we
boost the founder posts that already work organically.

Primary EOS uses:

- **Spark Ads boosting** — pick a high-performing organic post (sourced via
  the `tiktok` skill metrics), request an authorization code from the creator
  identity, create an adgroup with `identity_type=AUTH_CODE` and
  `identity_authorized_bc_id`, attach the `tiktok_item_id`, set a small daily
  budget, ship to a `WEB_CONVERSIONS` or `LANDING_PAGE` objective
- **Events API** — server-side conversions from the Initiate Arena funnel
  (`Lead`, `CompletePayment`, `Subscribe`) flow through eos_ai → Events API
  with hashed `email`/`phone`/`external_id` and an `event_id` shared with the
  pixel for deduplication
- **Reporting cron** — nightly pull of cost, CPM, CPC, CTR, CPA, ROAS by ad
  for the prior 7 days, written to Neon for the morning brief
- **Custom audiences** — Initiate Arena CRM Tier-1 leads pushed as a hashed
  customer file audience for retargeting and lookalike seeding
- **Budget guardrails** — every spend-affecting call (`campaign/create`,
  `campaign/update`, `adgroup/create`, `adgroup/update`, `*/status/update`
  with `ENABLE`) is **CRITICAL** risk and routes through the
  authority_engine for human approval

Canonical EOS pattern:

- All calls go through `eos_ai/tiktok_ads_client.py` (single chokepoint)
- Long-lived access tokens cached in Neon (`integrations.tiktok_ads`)
- All write calls log to `audit.paid_media_changes` before execution
- Spend caps enforced client-side: `daily_budget` and `lifetime_budget`
  validated against the `budgets.tiktok` ceiling before any create/update
- Reporting reads run as the service account; writes run only after
  authority_engine approval

## Authentication

OAuth 2.0 (TikTok for Business / TikTok Ads Manager identity), distinct from
the consumer TikTok Login Kit.

Flow:

1. Register a developer app at <https://business-api.tiktok.com/portal>
2. Configure redirect URI and request scopes (e.g. `Ad Account Management`,
   `Ads Management`, `Audience Management`, `Reporting`, `Business Center
   Management`, `Pixel`, `Creative Management`, `Conversion Event`)
3. Redirect the human to the TikTok auth URL with `app_id`, `state`,
   `redirect_uri`
4. Receive `auth_code` on the redirect
5. Exchange for `access_token` via
   `POST /open_api/v1.3/oauth2/access_token/` with `app_id`, `secret`,
   `auth_code`
6. Response includes `access_token`, `advertiser_ids` (the list of ad accounts
   the granting user authorized), and a long expiry (effectively non-expiring
   for first-party app + own ad account, but you must still handle revocation)

Every authenticated request sets `Access-Token: <token>` as a header (NOT a
bearer token in `Authorization`). The `advertiser_id` is a request-level
parameter on almost every endpoint; one token can drive many advertisers if
authorized.

```bash
curl -H "Access-Token: $TIKTOK_ADS_TOKEN" \
  "https://business-api.tiktok.com/open_api/v1.3/advertiser/info/?advertiser_ids=%5B%22${ADV_ID}%22%5D"
```

For Spark Ads on creator content, you additionally need either:
- A **Spark Ads authorization code** the creator generates in-app (video → ⋯ →
  Ad settings → Ad authorization → Generate code), OR
- The creator's TikTok identity added to the Business Center as an authorized
  identity (no per-video code needed; covers all their posts)

## Quick Reference

### Hosts

- Production: `https://business-api.tiktok.com`
- Sandbox: `https://sandbox-ads.tiktok.com` (separate app, separate token,
  separate fake advertiser_id — does NOT spend money, perfect for EOS smoke
  tests)

### Create campaign → adgroup → ad

```bash
# 1. Campaign
curl -X POST "https://business-api.tiktok.com/open_api/v1.3/campaign/create/" \
  -H "Access-Token: $TIKTOK_ADS_TOKEN" -H "Content-Type: application/json" \
  -d '{
    "advertiser_id": "'"$ADV_ID"'",
    "campaign_name": "IA-FounderContent-2026-04",
    "objective_type": "WEB_CONVERSIONS",
    "budget_mode": "BUDGET_MODE_DAY",
    "budget": 20.00
  }'

# 2. Adgroup (Spark Ads identity, web conversions, pixel optimization)
curl -X POST "https://business-api.tiktok.com/open_api/v1.3/adgroup/create/" \
  -H "Access-Token: $TIKTOK_ADS_TOKEN" -H "Content-Type: application/json" \
  -d '{
    "advertiser_id": "'"$ADV_ID"'",
    "campaign_id": "'"$CAMPAIGN_ID"'",
    "adgroup_name": "IA-US-25-44-M",
    "placement_type": "PLACEMENT_TYPE_NORMAL",
    "placements": ["PLACEMENT_TIKTOK"],
    "promotion_type": "WEBSITE",
    "pixel_id": "'"$PIXEL_ID"'",
    "optimization_event": "COMPLETE_PAYMENT",
    "billing_event": "OCPM",
    "bid_type": "BID_TYPE_NO_BID",
    "budget_mode": "BUDGET_MODE_DAY",
    "budget": 20.00,
    "schedule_type": "SCHEDULE_FROM_NOW",
    "schedule_start_time": "2026-04-07 00:00:00",
    "location_ids": ["6252001"],
    "gender": "GENDER_MALE",
    "age_groups": ["AGE_25_34","AGE_35_44"],
    "operation_status": "DISABLE"
  }'

# 3. Ad — Spark Ad referencing organic post
curl -X POST "https://business-api.tiktok.com/open_api/v1.3/ad/create/" \
  -H "Access-Token: $TIKTOK_ADS_TOKEN" -H "Content-Type: application/json" \
  -d '{
    "advertiser_id": "'"$ADV_ID"'",
    "adgroup_id": "'"$ADGROUP_ID"'",
    "creatives": [{
      "ad_name": "IA-Spark-2026-04-07-A",
      "ad_format": "SINGLE_VIDEO",
      "identity_type": "AUTH_CODE",
      "identity_authorized_bc_id": "'"$BC_ID"'",
      "identity_id": "'"$IDENTITY_ID"'",
      "tiktok_item_id": "'"$VIDEO_ID"'",
      "call_to_action": "LEARN_MORE",
      "landing_page_url": "https://initiatearena.com/?utm_source=tiktok"
    }]
  }'
```

### Events API (server-side conversion)

```bash
curl -X POST "https://business-api.tiktok.com/open_api/v1.3/event/track/" \
  -H "Access-Token: $TIKTOK_ADS_TOKEN" -H "Content-Type: application/json" \
  -d '{
    "event_source": "web",
    "event_source_id": "'"$PIXEL_ID"'",
    "data": [{
      "event": "CompletePayment",
      "event_time": 1743984000,
      "event_id": "ia-order-90218",
      "user": {
        "email": "<sha256_lower_trim>",
        "phone": "<sha256_e164>",
        "external_id": "<sha256_user_id>",
        "ttclid": "E.C.P.xxxxx",
        "ttp": "<_ttp_cookie>",
        "ip": "203.0.113.4",
        "user_agent": "Mozilla/5.0 ..."
      },
      "properties": {
        "currency": "USD",
        "value": 750.00,
        "content_id": "ia-cohort-2026-04",
        "content_type": "product"
      },
      "page": { "url": "https://initiatearena.com/checkout/success" }
    }]
  }'
```

### Reporting (synchronous)

```bash
curl -G "https://business-api.tiktok.com/open_api/v1.3/report/integrated/get/" \
  -H "Access-Token: $TIKTOK_ADS_TOKEN" \
  --data-urlencode 'advertiser_id='"$ADV_ID" \
  --data-urlencode 'report_type=BASIC' \
  --data-urlencode 'data_level=AUCTION_AD' \
  --data-urlencode 'dimensions=["ad_id","stat_time_day"]' \
  --data-urlencode 'metrics=["spend","impressions","clicks","ctr","cpc","cpm","conversion","cost_per_conversion","conversion_rate"]' \
  --data-urlencode 'start_date=2026-03-30' \
  --data-urlencode 'end_date=2026-04-06' \
  --data-urlencode 'page=1' --data-urlencode 'page_size=200'
```

### Status toggles (the spend-critical calls)

```bash
# Enable a campaign — CRITICAL, requires authority_engine approval
curl -X POST "https://business-api.tiktok.com/open_api/v1.3/campaign/status/update/" \
  -H "Access-Token: $TIKTOK_ADS_TOKEN" -H "Content-Type: application/json" \
  -d '{"advertiser_id":"'"$ADV_ID"'","campaign_ids":["'"$CAMPAIGN_ID"'"],"operation_status":"ENABLE"}'
```

## Conceptual Model

**Advertiser is the wallet. Hierarchy is the lever. Identity is the face.
Pixel is the feedback loop.**

Every spend-affecting object is scoped to an `advertiser_id` — that is the
billing boundary, the access boundary, and the reporting boundary. Inside one
advertiser, the `campaign → adgroup → ad` hierarchy carves up *what to do*
(objective), *who to show it to* (targeting + budget + bid), and *what they
see* (creative + identity + landing). Each level owns a different decision —
putting budget on the wrong level, or targeting on the wrong level, is the
single biggest source of "why is my campaign not delivering" tickets.

**Identity** is the face the ad wears. For uploaded creative, you create a
"Custom Identity" with a name + avatar. For Spark Ads, the identity is a real
TikTok account (creator or brand) that has either been added to your Business
Center or has issued a per-video authorization code. The same ad object
references both the identity and the `tiktok_item_id` of the post being
boosted.

**Pixel + Events API** is the closed loop that lets the auction optimize. The
auction can only optimize toward events it sees. Web pixel events are
ad-blocker-fragile and Safari-fragile; Events API is server-side and durable.
Best practice is **send both** with a shared `event_id` so TikTok can
deduplicate. Without conversion signal back to TikTok, OCPM bidding has nothing
to learn from and degenerates to expensive impression buying.

If you internalize advertiser-as-wallet, hierarchy-as-lever, identity-as-face,
pixel-as-feedback, every confusing TikTok Ads behavior becomes obvious:

- "Budget changes aren't applying" → you set it on the wrong level (CBO vs ABO)
- "Spark Ad got rejected" → identity not authorized, or auth code expired
- "Reporting shows zero conversions" → pixel + events API not wired, or
  optimization_event mismatched
- "My API call returned 200 but nothing happened" → check the JSON body
  `code`/`message` — TikTok returns HTTP 200 with embedded error codes

## Gotchas

- **HTTP 200 != success.** TikTok wraps every response in
  `{"code":N,"message":"...","data":{}}`. Always check `code == 0`. Anything
  else is a failure even though the HTTP status was 200. The #1 integration
  bug.
- **`Access-Token` header, not `Authorization: Bearer`.** Wrong header = 40105
  auth error. Different from every other major API.
- **`advertiser_id` is a STRING in all params,** even though it looks numeric.
  JSON number → 40002 invalid params. Always quote it.
- **Array params in GET requests must be JSON-encoded then URL-encoded** —
  `advertiser_ids=["1234"]` not `advertiser_ids=1234`. The
  `--data-urlencode 'metrics=["spend"]'` pattern is mandatory.
- **`budget_mode=BUDGET_MODE_INFINITE` exists** and is the default if you omit
  budget on a CBO campaign — meaning unbounded spend. NEVER omit. Always set
  `BUDGET_MODE_DAY` or `BUDGET_MODE_TOTAL` with a hard number.
- **Minimum daily budget** is currency-dependent: USD ad-level $20,
  campaign-level $50. Below this returns `40002` with no useful explanation.
- **`operation_status: DISABLE` on create** is the safe default — create
  paused, then human-approve before enabling. EOS enforces this.
- **Spark Ads authorization codes expire** (7/30/60/365 days, creator's
  choice). After expiry the ad keeps running until you edit it; on edit it
  dies. Track expiries in Neon.
- **`tiktok_item_id` is the numeric video id, not the share URL.** Extract
  from `https://www.tiktok.com/@user/video/<ID>`.
- **Identity confusion:** `identity_type=AUTH_CODE` requires `identity_id` AND
  `identity_authorized_bc_id`. `identity_type=TT_USER` requires only
  `identity_id` if the user is in your BC. `identity_type=CUSTOMIZED_USER` for
  uploaded creative.
- **Events API hashing:** email/phone/external_id MUST be SHA-256 of
  lowercase-trimmed (email) or E.164 (phone) input. Sending raw PII = silent
  drop, no error. Verify in Events Manager → Test Events.
- **Pixel `event_source_id` IS the pixel code,** despite the field name. Same
  string you find in Ads Manager → Assets → Events.
- **Rate limit is per-app per-advertiser**, roughly 10 QPS for write
  endpoints, 20 QPS for reads, with daily caps. Burst beyond → 40100 / 50002.
  Backoff exponentially with jitter. Reporting endpoints have separate, lower
  buckets.
- **Reporting `data_level` must match `dimensions`.** `AUCTION_AD` data level
  with `campaign_id` dimension = empty result, no error.
- **`stat_time_day` dimension returns dates in advertiser timezone**, not UTC.
  Always read `advertiser/info/` and store the timezone.
- **Sandbox advertisers cannot serve real ads, cannot use real pixels, cannot
  authorize real creator content.** Use sandbox for schema validation and
  authority_engine dry-runs only.
- **Webhooks are limited.** TikTok Ads has *some* webhook support (lead form
  submissions, app event postbacks, Business Center membership) but no general
  "campaign state changed" webhook. For state, you poll.
- **No event deduplication unless `event_id` matches** between pixel and CAPI
  for the same event. Without `event_id` you'll double-count conversions and
  the auction will get bad signal.
- **`promotion_type=WEBSITE` requires a pixel; `APP` requires app_id;
  `LEAD_GEN` requires a lead form id.** Mismatching promotion_type and
  optimization_event is the most common adgroup-create rejection.

See references/best_practices.md for the full 19-section creator-level
knowledge base.
Cross-reference: skills/tools/tiktok/ for organic posting, Display API, and
the metric pull that feeds Spark Ads candidate selection.
>>>>>>> Stashed changes
