---
name: meta_ads
description: "Use when creating, editing, pausing, or analyzing Meta paid ads (Facebook + Instagram + Messenger + Audience Network) — building campaign/ad set/ad/creative trees, uploading custom audiences, creating lookalikes, sending Conversions API events, pulling Insights with breakdowns, configuring Advantage+ campaigns, managing pixels, or scripting any Marketing API operation through facebook-business Python SDK or raw Graph calls. For organic Pages, Messenger, WhatsApp, Threads, IG publishing use the meta_graph_api / instagram skills instead."
allowed-tools: "Read, Bash, Write, Edit, WebFetch"
version: 1.0
source_url: "https://developers.facebook.com/docs/marketing-api"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "v23.0 stable / v24.0 / v25.0 latest (quarterly cadence, ~2yr support)"
sdk_version: "facebook-business 25.0.0 (Python, March 2026)"
speed_category: stable
---

# Tool: Meta Marketing API (meta_ads)

## What This Tool Does

The Meta Marketing API is the paid-media slice of the Graph API. It exposes
the four-level ad tree — **Ad Account → Campaign → Ad Set → Ad → Creative** —
plus everything that hangs off it: pixels, custom/lookalike audiences,
Conversions API event endpoints, Insights reporting, business assets, and
delivery estimates. Same HTTPS surface as Graph (`graph.facebook.com/v{N}.0/`),
same OAuth, but a separate Business Use Case bucket for rate limits
(`ads_management`, `ads_insights`) and its own permission set
(`ads_management`, `ads_read`, `business_management`).

What this skill covers:

- **Campaign tree CRUD** — Campaign objectives (ODAX 6: AWARENESS, TRAFFIC,
  ENGAGEMENT, LEADS, APP_PROMOTION, SALES), Ad Set targeting/budget/schedule,
  Ad creative association, status transitions
- **Creatives** — single image, video, carousel, collection, dynamic product
  ads, asset feed specs, Advantage+ creative enhancements, placement
  customization (asset_feed_spec, object_story_spec)
- **Audiences** — Custom Audiences (CUSTOMER_FILE, WEBSITE, APP, ENGAGEMENT,
  LOOKALIKE), SHA-256 hashing of PII, multi-key matching, replace vs append
  modes, sharing across business assets
- **Lookalikes** — `lookalike_spec` with seed audience, country, ratio (1-10%)
- **Conversions API (CAPI)** — `/{pixel-id}/events` server-side event upload,
  event_id deduplication with browser pixel, hashed user_data, custom_data,
  test_event_code workflow
- **Pixels** — create, fire test events, list events, share with ad accounts
- **Insights API** — sync and async reports, breakdowns, action_breakdowns,
  date_preset vs time_range, attribution_setting, level (account/campaign/
  adset/ad), pagination
- **Advantage+ campaigns** — Sales (ASC), App (AAC), audience/placement/
  budget/creative automation levers, the v24+ legacy ban
- **Targeting** — geo, demographic, interest, behavior, custom audience,
  detailed_targeting, flexible_spec, exclusions, Advantage+ audience
  defaults (v23+)
- **System user tokens** — long-lived production auth, never-expiring tokens,
  asset assignment, two-factor app secret proof

What this skill is NOT:

- Page posts, Messenger Send API, WhatsApp templates, Threads, IG organic →
  see `meta_graph_api` and `instagram` skills
- Auth/OAuth/webhook plumbing common to all Meta surfaces → see
  `meta_graph_api` (this skill assumes a working long-lived token exists)

## EOS Integration

Meta Ads is the **paid amplification layer** for Initiate Arena and Lyfe
Spectrum. It is not the primary discovery channel — that is organic content +
DM outreach — but it is the lever for turning a winning organic post into a
boosted lead-generation engine, and for retargeting site visitors who didn't
book a call.

EOS surfaces:

- **Initiate Arena lead ads** — Lead generation campaigns with instant forms,
  CAPI-fed CRM webhook, qualified lead routing into 03_CRM pipeline
- **Lyfe Spectrum traffic / sales** — Advantage+ Shopping Campaigns once SKUs
  are live, retargeting from product views and add-to-carts
- **Founder content boost** — Engagement / Traffic objective on top-performing
  organic Reels, scoped to lookalike of email subscribers
- **CAPI from Replit/Express SaaS** — server-side event upload for InitiateLead,
  Purchase, CompleteRegistration with deduplication keys matched to the
  client-side pixel
- **Performance reporting** — nightly Insights pull (campaign + ad set + ad
  level) into Neon for the World Pulse dashboard, ROAS/CPA/CTR/frequency
  trended weekly

Authority:

- All **budget changes** and **new campaign creation** are CRITICAL risk —
  human approval required (founder confirmation in Telegram before write)
- **Pause / status changes** on losing ads are HIGH risk — agent may propose,
  human one-click confirms
- **Read-only Insights pulls** are LOW risk — fully automated nightly
- **Audience uploads** are HIGH risk (privacy + compliance) — human-approved

## Authentication

Inherits the OAuth model documented in `meta_graph_api`. The ad-specific
deltas:

- Required permissions: `ads_management` (write), `ads_read` (read-only),
  `business_management` (asset assignment), plus `pages_show_list` and
  `pages_read_engagement` if creating page-post ads
- App must be in **Standard Access** tier of the Marketing API (not just Graph
  API standard) — Development tier caps you at ~60 score and a tiny rate quota
- **System User token** is the only sane production credential. Never use a
  user token. Never use a Page token. Generate inside Business Manager →
  System Users → Generate Token, scoped to the app and required permissions
- App secret proof (`appsecret_proof = HMAC-SHA256(access_token, app_secret)`)
  is REQUIRED on every server-side call when "Require App Secret" is enabled
- Token storage: `META_ADS_SYSTEM_USER_TOKEN`, `META_APP_ID`, `META_APP_SECRET`,
  `META_AD_ACCOUNT_ID` in `eos_ai/.env`. Never commit. Rotate annually.

## Quick Reference

### Install + initialize SDK

```bash
pip install facebook-business==25.0.0
```

```python
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
import os

FacebookAdsApi.init(
    app_id=os.environ['META_APP_ID'],
    app_secret=os.environ['META_APP_SECRET'],
    access_token=os.environ['META_ADS_SYSTEM_USER_TOKEN'],
    api_version='v23.0',
    crash_log=False,
)
account = AdAccount(f"act_{os.environ['META_AD_ACCOUNT_ID']}")
```

### Create a LEADS campaign (paused)

```python
from facebook_business.adobjects.campaign import Campaign

campaign = account.create_campaign(params={
    Campaign.Field.name: 'IA Lead Gen 2026-04 [test]',
    Campaign.Field.objective: Campaign.Objective.outcome_leads,  # ODAX
    Campaign.Field.status: Campaign.Status.paused,
    Campaign.Field.special_ad_categories: [],
    Campaign.Field.buying_type: 'AUCTION',
})
print(campaign['id'])
```

### Insights pull (sync)

```python
fields = ['campaign_name','impressions','clicks','spend','ctr','cpc','actions']
params = {
    'level': 'campaign',
    'date_preset': 'last_7d',
    'breakdowns': ['publisher_platform'],
    'action_attribution_windows': ['7d_click','1d_view'],
}
for row in account.get_insights(fields=fields, params=params):
    print(dict(row))
```

### CAPI event (raw HTTPS)

```bash
curl -X POST "https://graph.facebook.com/v23.0/${PIXEL_ID}/events" \
  -d "access_token=${TOKEN}" \
  -d 'data=[{
    "event_name":"InitiateLead",
    "event_time":1712345678,
    "event_id":"ia_lead_42a7",
    "action_source":"website",
    "user_data":{"em":["<sha256-email>"],"client_ip_address":"1.2.3.4","client_user_agent":"..."},
    "custom_data":{"value":750.0,"currency":"USD"}
  }]' \
  -d "test_event_code=TEST12345"
```

## Conceptual Model

**Tree, not flat.** Every paid asset hangs off the four-level tree
`AdAccount → Campaign → AdSet → Ad → Creative`. Objectives live on the
campaign. Targeting, budget, schedule, optimization goal, billing event,
bid strategy live on the **ad set** — this is where most decisions actually
happen. Creatives are reusable across ads. The ad is just a binding of
(ad set, creative, status).

**ODAX is the only objective system now.** Six objectives: AWARENESS,
TRAFFIC, ENGAGEMENT, LEADS, APP_PROMOTION, SALES. Old objectives
(LINK_CLICKS, CONVERSIONS, etc.) cannot be created since v21.0 — existing
ones still run.

**Advantage+ is a state, not a campaign type.** A campaign becomes Advantage+
when you set the three automation levers (campaign budget + audience +
placements). Since v24.0 the legacy `ASC` / `AAC` shortcuts are banned for
new creation.

**CAPI and Pixel coexist via event_id.** Same `event_id` + `event_name` from
both browser and server → Meta dedupes and keeps the richer record. Without
matching IDs you double-count.

**Rate limits are per-ad-account, not per-token,** and shared across the
`ads_management` Business Use Case bucket.

## Gotchas

- **Mixing `account_id` (raw int) and `act_{id}` (prefixed)** — SDK constructors
  want `act_<id>`, raw Graph URLs want either. Wrong form returns "not found"
  not "bad format."
- **Forgetting `special_ad_categories`** when creating campaigns — required
  field even if empty list. Wrong category for a regulated vertical = ad
  rejection + account flag.
- **Custom audience PII not SHA-256 hashed and lowercased/trimmed** → match
  rate near zero. Hash AFTER normalization, not before.
- **CAPI `event_time` more than 7 days old** → silently dropped. Always send
  near-real-time.
- **`event_id` mismatch between pixel and CAPI** → conversion double-counted,
  CPA looks artificially low, optimization corrupted. Pin the same UUID in
  both client and server.
- **Insights `breakdowns` and `action_breakdowns` cannot mix freely** — many
  combinations return error 100. Test combinations before scheduling.
- **Synchronous Insights for >10k rows or wide date ranges → timeout / error
  17.** Switch to **async** (`POST .../insights` returns a `report_run_id`,
  poll until status `Job Completed`, then GET `/insights`).
- **Date ranges in Insights are inclusive on both ends** and use the ad
  account's timezone, not UTC. DST shifts hourly.
- **Custom audience upload `schema` order must match `data` row order** —
  silently 0% match otherwise.
- **Lookalike creation requires seed ≥100 people**, valid country, ratio 0.01-0.10.
- **Advantage+ Audience opt-in is the v23+ default** — old "exclude existing
  customers" logic may be ignored unless re-specified.
- **System user token can be invalidated by admin password reset** — monitor
  `/me?access_token=` health daily.
- **`ads_management_standard_access` review required** — without it, rate
  quota is too small for any nightly job.
- **`appsecret_proof` is REQUIRED in production** — without it, a leaked token
  works from anywhere.
- **Don't poll paused campaigns for live data** — empty rows, not zeros.
  Filter `effective_status` first.
- **`facebook-business` SDK has 0 retries by default** — wrap in your own
  jittered exponential backoff for errors 1, 2, 4, 17, 80004.

See references/best_practices.md for the full 19-section creator-level knowledge base.
