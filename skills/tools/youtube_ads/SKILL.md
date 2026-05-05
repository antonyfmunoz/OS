---
name: youtube_ads
description: "Use when planning, building, launching, measuring, or optimizing paid YouTube video campaigns (in-stream, bumper, non-skippable, in-feed/discovery, Shorts, masthead) — including TrueView for Action, video reach, video views, audience targeting (affinity, in-market, custom intent, customer match), Brand Lift studies, view-through conversion analysis, or any Google Ads API call where advertising_channel_type=VIDEO."
allowed-tools: "Read, Bash, Write, Edit, WebFetch"
version: 1.0
source_url: "https://developers.google.com/google-ads/api/docs/video-campaigns/overview"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "Google Ads API v17"
sdk_version: "google-ads-python 25.x"
speed_category: stable
trigger: both
effort: low
context: fork
---

# Tool: youtube_ads

## What This Tool Does

YouTube advertising is delivered exclusively through the **Google Ads API** —
there is no separate "YouTube Ads API." YouTube ads are Google Ads campaigns
where `Campaign.advertising_channel_type = VIDEO` (or `DISCOVERY` for
Demand Gen surfaces that include in-feed and Shorts feed). Every video ad
is a Google Ads `Ad` resource of a `Video*Ad` type referencing a
`YouTubeVideoAsset` whose `youtube_video_id` is the public 11-character
YouTube video ID.

This skill is **scoped to the YouTube-specific surface** of Google Ads.
For OAuth refresh tokens, developer-token headers, GAQL basics,
`login_customer_id`, batch jobs, rate limits, retries, and the v17→v18
upgrade rhythm, see the companion skill at
`/opt/OS/skills/tools/google_ads/`. This file does not duplicate that.

Core capabilities specific to YouTube:

- **Video campaign sub-types** — `VIDEO_ACTION` (TrueView for Action /
  drive-to-site), `VIDEO_NON_SKIPPABLE_IN_STREAM`, `VIDEO_EFFICIENT_REACH`
  (bumper + skippable reach mix), `VIDEO_VIEW` (TrueView in-stream views),
  `VIDEO_REACH_TARGET_FREQUENCY`, `VIDEO_RESPONSIVE`, `VIDEO_SEQUENCE`
- **Ad formats** — In-stream skippable, In-stream non-skippable (15s),
  Bumper (6s, no skip), In-feed video discovery, Outstream (mobile web/app),
  YouTube Shorts vertical, Masthead (reservation only)
- **Targeting** — Affinity, In-Market, Life Events, Custom Audiences
  (custom intent / custom segments), Customer Match, Detailed Demographics,
  Topics, Placements (channel/video/playlist/website/app), contextual Keywords
- **Bidding** — `TARGET_CPM`, `TARGET_CPA`, `MAXIMIZE_CONVERSIONS`,
  `MAXIMIZE_CONVERSION_VALUE`, `TARGET_ROAS`, `CPV` (legacy),
  `TARGET_IMPRESSION_SHARE` (masthead reservation only)
- **Measurement** — View-through conversions (VTC), Brand Lift studies,
  Reach Planner forecasting, Audience Insights, earned actions
- **Asset model** — `YouTubeVideoAsset`, `ImageAsset` (companion banner),
  `CallToActionAsset`, `LeadFormAsset`, `SitelinkAsset` linked via
  `CampaignAsset` / `AdGroupAsset` / `CustomerAsset` with `field_type`

## EOS Integration

Paid amplification surface for the personal-brand engine
(CLAUDE.local.md Phase 1). Two distinct media plans:

- **Initiate Arena founder content** — Antony's long-form on the Lyfe
  Institute channel. Goal: qualified discovery calls. Campaign type
  `VIDEO_ACTION`, bidding `MAXIMIZE_CONVERSIONS` against the
  `arena_application_submitted` conversion action, with Customer Match
  remarketing lists from CRM exports plus a custom-segment audience built
  from competitor coach search terms.
- **Lyfe Spectrum drops** — product-launch bursts. Campaign type
  `VIDEO_REACH_TARGET_FREQUENCY` (3+ views over 14 days) for top-of-funnel
  awareness, then `VIDEO_ACTION` retargeting view-engagers and the Shopify
  customer list.

Agent responsibilities:

- Draft full campaign trees (Campaign → AdGroup → AdGroupAd → Targeting)
  as `MutateOperation` JSON for human approval before any `mutate` call
- Recommend audience layers given an offer description and business stage
- Pull weekly performance via GAQL — surface VTC vs. click conversions,
  unique reach, view rate by ad — and write the summary into `world_pulse`
- Flag policy-risk creative before upload (claims, before/after, sensitive
  categories, restricted verticals)

Live spend authority: capped per `eos_ai/authority_engine.py` risk class
HIGH. Anything over $50/day requires CEO confirmation.

## Authentication

Identical to base Google Ads — OAuth 2.0 refresh token flow with a
developer token in the `developer-token` header. See
`/opt/OS/skills/tools/google_ads/SKILL.md` for full setup. YouTube-ad
specific notes:

- The Google Ads account must be linked to the YouTube channel under
  **Linked accounts → YouTube** in the Ads UI before any video assets
  can be promoted. The API will not create the link.
- Linking grants the Ads account access to the channel's earned actions
  (likes, subscribes, shares) for measurement.
- The OAuth user must have at least `STANDARD` access on the Ads account.
- Brand Lift studies require additional invitation by a Google rep —
  there is no self-serve API for spinning up a study, only reading its
  results back via segmented metrics.

## Quick Reference

### Create a YouTube video asset

```python
from google.ads.googleads.client import GoogleAdsClient

client = GoogleAdsClient.load_from_storage("/opt/OS/eos_ai/google-ads.yaml")
asset_service = client.get_service("AssetService")

op = client.get_type("AssetOperation")
asset = op.create
asset.name = "ia-founder-vsl-2026q2"
asset.type_ = client.enums.AssetTypeEnum.YOUTUBE_VIDEO
asset.youtube_video_asset.youtube_video_id = "dQw4w9WgXcQ"   # 11-char ID
asset.youtube_video_asset.youtube_video_title = "Initiate Arena — VSL"

resp = asset_service.mutate_assets(
    customer_id="1234567890", operations=[op]
)
print(resp.results[0].resource_name)
```

### Create a VIDEO_ACTION campaign (paused)

```python
camp_op = client.get_type("CampaignOperation")
c = camp_op.create
c.name = "IA-Action-Founder-2026Q2"
c.advertising_channel_type = client.enums.AdvertisingChannelTypeEnum.VIDEO
c.advertising_channel_sub_type = (
    client.enums.AdvertisingChannelSubTypeEnum.VIDEO_ACTION
)
c.status = client.enums.CampaignStatusEnum.PAUSED   # always paused on create
c.campaign_budget = "customers/1234567890/campaignBudgets/987"
c.maximize_conversions.target_cpa_micros = 75_000_000   # $75 tCPA
c.start_date = "20260407"
c.end_date   = "20260507"
```

### GAQL — view-through conversions for last 7 days

```sql
SELECT
  campaign.name,
  ad_group.name,
  metrics.impressions,
  metrics.video_views,
  metrics.video_view_rate,
  metrics.average_cpv,
  metrics.conversions,
  metrics.view_through_conversions,
  metrics.cost_micros
FROM ad_group
WHERE campaign.advertising_channel_type = 'VIDEO'
  AND segments.date DURING LAST_7_DAYS
ORDER BY metrics.cost_micros DESC
```

### Add a custom segment (custom intent) audience

```python
seg_op = client.get_type("CustomAudienceOperation")
s = seg_op.create
s.name = "ia-competitor-coaches-search"
s.type_ = client.enums.CustomAudienceTypeEnum.SEARCH
m = s.members.add()
m.member_type = client.enums.CustomAudienceMemberTypeEnum.KEYWORD
m.keyword     = "high ticket coaching mentor"
```

Then attach via `AdGroupCriterion.custom_audience.custom_audience = "..."`.

## Conceptual Model

**Everything is a Google Ads resource. YouTube is a delivery channel,
not a separate API.** A video ad is a row in the `Ad` table whose payload
is one of the `Video*Ad` oneofs and whose creative is a `YouTubeVideoAsset`.
A "TrueView for Action campaign" is just a `Campaign` row with
`advertising_channel_type=VIDEO` and
`advertising_channel_sub_type=VIDEO_ACTION`.

Once that lands, every confusing thing falls out:

- "Why can't I edit the video file?" → assets are immutable; replace, don't update
- "Why does my campaign type lock my bid strategy?" → sub_type constrains
  the legal `BiddingStrategyType` set, enforced server-side
- "Where do I see Shorts?" → Shorts inventory is delivered automatically
  by VIDEO_ACTION/VIDEO_VIEW with vertical creative; there is no
  Shorts-only sub_type in v17 (Demand Gen handles it explicitly)

## Gotchas

- **No billing setup via API** — UI only. API returns `ACCOUNT_NOT_ACTIVE`
  until billing is configured manually.
- **Channel must be linked first** — `YOUTUBE_CHANNEL_NOT_LINKED` blocks
  asset upload. Link is UI-only under Linked Accounts.
- **Video ID, not URL** — `youtube_video_id` takes the 11-char ID. Pasting
  a full `https://...` returns `INVALID_YOUTUBE_VIDEO_ID`.
- **Unlisted videos work, private don't** — private videos are rejected.
  Use unlisted for pre-launch creative.
- **Status must be PAUSED on create** — Google Ads enforces paused-on-create
  for video campaigns to prevent accidental spend; flip to ENABLED in a
  separate mutate after QA.
- **Bumper ads must be ≤ 6 seconds** — exact, not "about." 6.01s rejected.
- **Non-skippable in-stream length is region-dependent** — 15s in US,
  20s in some EMEA markets.
- **`view_through_conversions` are NOT included in `conversions`** — they
  are a separate column. EOS dashboards must sum both for true contribution.
- **`metrics.video_views` only fires at 30s or completion** — bumpers
  therefore have zero `video_views` by definition; use `impressions` and
  `cost_micros / impressions` for CPM.
- **Custom Audiences replaced Custom Intent + Custom Affinity** since
  late 2022. The old `CustomIntent` resource is read-only; create via
  `CustomAudience` with `type=SEARCH` for intent semantics.
- **Customer Match list warm-up is 24-72h** — size-of-zero immediately
  after upload is normal. Don't bind a campaign until
  `size_for_display > 1000` or YouTube will not deliver.
- **Brand Lift requires $5k+ committed spend** in most markets and is
  set up by a Google rep. The API only reads results.
- **Policy review on video ads takes 1-3 business days**, not minutes.
  Schedule launches accordingly.
- **`ENABLED` ≠ serving** — `ad_group_ad.policy_summary.approval_status`
  must be `APPROVED` (or `APPROVED_LIMITED`). Always join the policy
  table in launch verification queries.
- **Reach Planner is a separate service** (`ReachPlanService`) using
  different units (target audience size, frequency cap) from mutate
  operations. Forecasts are aspirational, not guarantees.

See references/best_practices.md for the full 19-section creator-level
knowledge base, EOS Usage Patterns, and the extended Gotchas catalog.
