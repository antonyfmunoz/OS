# YouTube Ads — Creator-Level Best Practices
Source: developers.google.com/google-ads/api/docs/video-campaigns, support.google.com/google-ads, Google Ads API release notes, Think with Google, YouTube Advertising Policies, Reach Planner docs
API Version: Google Ads API v17 (with v16/v18 deltas noted)
SDK Version: google-ads-python 25.x
Last Researched: 2026-04-06

> Companion skill: `/opt/OS/skills/tools/google_ads/` covers all
> non-video Google Ads mechanics (auth, GAQL basics, batch jobs,
> change-events, mutate framing, retries, error taxonomy). This file
> only documents YouTube-ad-specific behavior. Where the base behavior
> is identical to search/display, sections say "see google_ads skill"
> rather than restate.

---

# Tier 1 — Technical Mastery

## Authentication

YouTube ads use the same Google Ads API auth as every other channel:

- OAuth 2.0 with offline refresh token (client_id, client_secret,
  refresh_token, developer_token)
- `developer-token` header on every gRPC/REST call
- `login-customer-id` header set to the manager (MCC) account when the
  target customer sits underneath an MCC
- Scope: `https://www.googleapis.com/auth/adwords`

YouTube-specific auth prerequisites:

1. **Channel link** — In the Google Ads UI, Tools → Linked Accounts →
   YouTube → Add channel. The channel owner approves from YouTube Studio.
   No API equivalent.
2. **Account access** — OAuth user must have STANDARD or ADMIN access on
   the Ads account. READ_ONLY can pull GAQL but cannot mutate.
3. **Asset access** — even after linking, only videos owned by the
   linked channel can be added as `YouTubeVideoAsset` for promotion in
   reservation/Brand Lift contexts. Auction campaigns can promote any
   public/unlisted video, regardless of ownership, but earned-actions
   measurement only flows for owned videos.
4. **Conversion tracking** — Google tag, Google Analytics 4 link, or
   `ConversionAction` defined via API. View-through conversion windows
   are configured at the conversion action level
   (`view_through_lookback_window_days`, default 1, max 30).

For full bootstrap, see the google_ads skill. Treat anything below
as additive on top of that bootstrap.

## Core Operations with Exact Signatures

All signatures are gRPC service methods on the Google Ads API. Python
binding shown; REST is identical with snake_case → camelCase.

### AssetService — upload a YouTube video as an asset

```python
asset_service.mutate_assets(
    customer_id: str,
    operations: list[AssetOperation],
    partial_failure: bool = False,
    validate_only: bool = False,
    response_content_type: ResponseContentTypeEnum = RESOURCE_NAME_ONLY,
) -> MutateAssetsResponse
```

`AssetOperation.create.youtube_video_asset`:
- `youtube_video_id: str` — 11-char YouTube video ID, NOT a URL
- `youtube_video_title: str` — display name in Ads UI

### CampaignService — create a video campaign

```python
campaign_service.mutate_campaigns(customer_id, operations, ...)
```

Required `Campaign` fields for video:

- `name: str` — unique within customer
- `advertising_channel_type: AdvertisingChannelTypeEnum.VIDEO`
  - or `DISCOVERY` for Demand Gen (Shorts feed + Discover + Gmail)
- `advertising_channel_sub_type:` one of
  - `VIDEO_ACTION` (drive-to-site, conversions)
  - `VIDEO_NON_SKIPPABLE_IN_STREAM` (15s mid-roll)
  - `VIDEO_EFFICIENT_REACH` (bumper + skippable mix)
  - `VIDEO_VIEW` (TrueView in-stream view objective)
  - `VIDEO_REACH_TARGET_FREQUENCY` (3+ views over period)
  - `VIDEO_RESPONSIVE` (multi-asset, served as in-feed/in-stream)
  - `VIDEO_SEQUENCE` (story-arc ordered)
- `status: CampaignStatusEnum.PAUSED` (server-enforced on create)
- `campaign_budget: resource_name`
- One bidding-strategy oneof, constrained by sub_type:
  - `VIDEO_ACTION` → `maximize_conversions`, `target_cpa`,
    `maximize_conversion_value`, `target_roas`
  - `VIDEO_VIEW` → `target_cpm` or legacy `cpv` (read-only on new)
  - `VIDEO_NON_SKIPPABLE_IN_STREAM` → `target_cpm`
  - `VIDEO_EFFICIENT_REACH` → `target_cpm`
  - `VIDEO_REACH_TARGET_FREQUENCY` → `target_frequency_goal`
- `start_date`, `end_date` — `YYYYMMDD` strings
- `network_settings.target_youtube` — must be true; other targets
  (search, content, partners) toggle additional inventory
- `video_campaign_settings` — frequency caps, video position bidding

### AdGroup — child of campaign

```python
ad_group.campaign = campaign_resource_name
ad_group.type_ = AdGroupTypeEnum.VIDEO_TRUE_VIEW_IN_STREAM
              | VIDEO_BUMPER
              | VIDEO_NON_SKIPPABLE_IN_STREAM
              | VIDEO_EFFICIENT_REACH
              | VIDEO_RESPONSIVE
              | VIDEO_TRUE_VIEW_IN_DISPLAY     # in-feed discovery
ad_group.status = AdGroupStatusEnum.ENABLED
ad_group.cpv_bid_micros / cpm_bid_micros / target_cpa_micros (per type)
```

The `AdGroup.type_` MUST agree with the parent campaign's sub_type. The
server returns `INVALID_AD_GROUP_TYPE_FOR_CAMPAIGN_TYPE` otherwise.

### AdGroupAd — the actual creative slot

```python
ad_group_ad.ad_group = ad_group_resource_name
ad_group_ad.status = AdGroupAdStatusEnum.PAUSED
ad = ad_group_ad.ad
ad.name = "ia-vsl-15s"
ad.final_urls.append("https://lyfeinstitute.com/arena")
# pick ONE oneof:
ad.in_stream_video_ad.action_button_label = "Apply"
ad.in_stream_video_ad.action_headline    = "Initiate Arena"
ad.in_stream_video_ad.video.asset        = video_asset_resource
ad.in_stream_video_ad.companion_banner.asset = banner_asset_resource
# or:
ad.bumper_ad.video.asset = video_asset_resource
ad.in_feed_video_ad.headline = "..."
ad.in_feed_video_ad.description1 = "..."
ad.in_feed_video_ad.description2 = "..."
ad.in_feed_video_ad.thumbnail = ...
ad.video_responsive_ad.headlines.add(text="...")
ad.video_responsive_ad.long_headlines.add(text="...")
ad.video_responsive_ad.descriptions.add(text="...")
ad.video_responsive_ad.call_to_actions.add(text="Apply")
ad.video_responsive_ad.videos.add(asset=video_asset_resource)
```

### AdGroupCriterion — targeting

```python
crit.ad_group = ad_group_resource
# Audience:
crit.user_list.user_list = "customers/123/userLists/456"   # Customer Match
crit.user_interest.user_interest_category = "customers/123/userInterests/789"  # affinity
crit.custom_audience.custom_audience = "customers/123/customAudiences/101"
crit.gender.type_ = GenderTypeEnum.MALE
crit.age_range.type_ = AgeRangeTypeEnum.AGE_RANGE_25_34
crit.parental_status.type_ = ParentalStatusTypeEnum.NOT_A_PARENT
# Placement:
crit.youtube_channel.channel_id = "UCxxxxxxxxxxxxxxxxxxxxxx"
crit.youtube_video.video_id    = "dQw4w9WgXcQ"
crit.placement.url             = "example.com"
crit.mobile_app_category.mobile_app_category_constant = "..."
# Topic / keyword (contextual):
crit.topic.topic_constant = "topicConstants/123"
crit.keyword.text = "high ticket coaching"
crit.keyword.match_type = KeywordMatchTypeEnum.BROAD
```

Negative criteria use `negative=True` and live on the AdGroup or
Campaign (`CampaignCriterion`).

### CustomAudienceService — custom intent / segment

```python
custom_audience_service.mutate_custom_audiences(customer_id, operations)
```

Members:
- `KEYWORD` — search-intent terms
- `URL`     — URLs the segment has visited
- `PLACE_CATEGORY` / `APP` — physical/app interest signals

`type_`:
- `SEARCH`     — pure intent (replaces Custom Intent)
- `INTEREST`   — pure affinity (replaces Custom Affinity)
- `PURCHASE_INTENT` — combined
- `AUTO`       — let Google pick

### UserDataService — Customer Match upload

Upload hashed emails/phones to a `UserList` of type `CRM_BASED`. Hash
SHA-256 lowercase trimmed. Match rate < 30% triggers a warning email
but does not fail the upload.

### ReachPlanService — forecast video plans (separate service)

```python
reach_plan_service.generate_reach_forecast(
    customer_id, currency_code, campaign_duration, planned_products,
    targeting, cookie_frequency_cap, ...
) -> GenerateReachForecastResponse
```

Returns `on_target_reach`, `total_reach`, `views`, `impressions` per
forecast point. Uses Reach Planner inventory data, NOT auction data —
treat as planning, not guarantee.

### GoogleAdsService.search / search_stream — GAQL reporting

See google_ads skill. Video-specific resources/segments:

- `FROM video` — per-video creative report
- `FROM ad_group_ad` filtered by `ad_group_ad.ad.type IN ('IN_STREAM_VIDEO_AD', 'BUMPER_AD', 'IN_FEED_VIDEO_AD', 'VIDEO_RESPONSIVE_AD')`
- `segments.ad_network_type IN ('YOUTUBE_WATCH', 'YOUTUBE_SEARCH')`
- `metrics.video_views`, `video_view_rate`, `video_quartile_p25_rate`,
  `video_quartile_p50_rate`, `video_quartile_p75_rate`, `video_quartile_p100_rate`
- `metrics.engagements`, `engagement_rate`
- `metrics.average_cpv`, `average_cpm`
- `metrics.video_quartile_*` — funnel through the creative
- `metrics.view_through_conversions`

## Pagination Patterns

See google_ads skill for `search` page-token semantics and
`search_stream` chunked streaming. YouTube reports are unremarkable —
the only nuance is that `FROM video` joins the publishing-side video
table and can return tens of thousands of rows for large channels;
prefer `search_stream` and segment by date to keep memory bounded.

## Rate Limits

Identical to base Google Ads — Basic access tier defaults to 15,000
operations/day; Standard access lifts to 1M ops/day after the dev token
is approved. Brand-Lift-related fields and reach-planner forecasts have
no separate quotas. The practical YouTube-specific bottlenecks:

- **Creative review queue** — 1-3 business days; not a quota but a wall
  clock that blocks ENABLED → SERVING transition
- **Customer Match warm-up** — 24-72h before audience size populates
- **Reach Planner forecast** — 1 forecast per customer per minute soft
  limit (not documented but observed)

## Error Codes and Recovery

| Error enum | Cause | Recovery |
|---|---|---|
| `YOUTUBE_CHANNEL_NOT_LINKED` | Tried to use earned-actions metric or upload owned video without linking the channel under Linked Accounts | Link in UI; cannot fix via API |
| `INVALID_YOUTUBE_VIDEO_ID` | Passed full URL or wrong-length string to `youtube_video_id` | Extract 11-char ID |
| `YOUTUBE_VIDEO_NOT_FOUND` | Video private, deleted, or geo-blocked from the Google Ads server's region | Make unlisted or public |
| `INVALID_AD_GROUP_TYPE_FOR_CAMPAIGN_TYPE` | AdGroup.type_ doesn't match campaign sub_type | Match the table in this doc |
| `BIDDING_STRATEGY_NOT_SUPPORTED_WITH_AD_GROUP_TYPE` | e.g. CPV on a VIDEO_ACTION campaign | Use the legal pair |
| `CAMPAIGN_MUST_BE_PAUSED_FOR_NEW_VIDEO_CAMPAIGN` | Tried to create with status ENABLED | Create paused, mutate to ENABLED |
| `CUSTOMER_NOT_ENABLED_FOR_VIDEO_ADVERTISING` | New account, billing not finished | Set up billing in UI |
| `INVALID_LANDING_PAGE_FOR_VIDEO_AD` | Final URL fails policy or domain not verified | Verify domain |
| `VIDEO_NOT_ALLOWED_DUE_TO_AGE_RESTRICTION` | Video flagged 18+ on YouTube | Different creative |
| `BUMPER_AD_DURATION_EXCEEDED` | > 6.0s | Re-cut to ≤6s exact |
| `NON_SKIPPABLE_AD_DURATION_EXCEEDED` | > 15s (or 20s in eligible markets) | Re-cut |
| `CUSTOMER_MATCH_USER_LIST_TOO_SMALL` | < 1000 matched users | Wait for warm-up; expand source list |

Recovery pattern: always wrap mutates with `partial_failure=True` during
agent autonomous runs so a single bad ad doesn't reject the whole batch;
parse `partial_failure_error.details` for `GoogleAdsFailure` per index.

## SDK Idioms

`google-ads-python` v25 specifics for video work:

- Always load via `GoogleAdsClient.load_from_storage("...yaml")` —
  never instantiate manually; the YAML carries developer token + login
  customer ID.
- Use `client.get_type("AssetOperation")` rather than direct imports —
  works across version bumps.
- Use enum accessor `client.enums.AdvertisingChannelTypeEnum.VIDEO`
  rather than int literals; intellisense and version-safe.
- For multi-step builds (campaign → ad group → ads → criteria) use
  `GoogleAdsService.mutate` with a list of `MutateOperation` and
  temporary resource names (`-1`, `-2`, ...) so the whole tree commits
  atomically. This is the only way to avoid orphan campaigns when one
  step in a multi-call sequence fails.
- For GAQL, prefer `search_stream` over `search` for any reporting
  query — pagination is automatic and memory is bounded.

## Anti-Patterns

- **Building campaigns one mutate at a time** — partial trees orphan on
  failure. Use a single `GoogleAdsService.mutate` with a temp-resource
  graph.
- **Using `cpv` on new VIDEO_ACTION campaigns** — CPV is legacy; new
  best practice is conversion-based bidding (`MAXIMIZE_CONVERSIONS` /
  `TARGET_CPA`).
- **Hardcoding `target_cpa_micros` from past performance without
  smart-bidding warmup window** — TCPA needs ~50 conversions in 30d
  before it stabilizes; tighter targets just throttle delivery.
- **Layering 4+ audiences on one ad group** — Google's optimizer needs
  signal volume; multiple narrow stacks beat one over-targeted stack.
- **Treating `metrics.video_views` as "watched"** — it counts at 30s or
  completion. Bumpers always show zero.
- **Ignoring `view_through_conversions`** — for top-of-funnel video,
  VTC is often >50% of total contribution; reporting only `conversions`
  badly understates ROAS.
- **Using public YouTube URL in `youtube_video_id`** — strip to 11-char.
- **Forgetting to set `network_settings.target_youtube=true`** — the
  default for VIDEO sub_type is true, but anyone copy-pasting from a
  search example will set it false and create a serving-zero campaign.

## Data Model

```
Customer
└── Campaign (advertising_channel_type=VIDEO, sub_type=VIDEO_*)
    ├── CampaignBudget (1:1)
    ├── BiddingStrategy (oneof embedded)
    ├── CampaignCriterion (location, language, negative placements, etc.)
    ├── CampaignAsset (sitelink, leadform, etc. via field_type)
    └── AdGroup (type matches campaign sub_type)
        ├── AdGroupAd
        │   └── Ad
        │       ├── in_stream_video_ad   ─┐
        │       ├── bumper_ad             │ oneof
        │       ├── in_feed_video_ad      │
        │       ├── non_skippable_video_ad│
        │       └── video_responsive_ad  ─┘
        │           └── references YouTubeVideoAsset(s),
        │              ImageAsset (companion banner),
        │              CallToActionAsset
        └── AdGroupCriterion (audiences, demos, placements, topics, keywords)

Asset (type_=YOUTUBE_VIDEO)
└── YouTubeVideoAsset(youtube_video_id, youtube_video_title)

CustomAudience (type=SEARCH|INTEREST|PURCHASE_INTENT|AUTO)
└── members[] (KEYWORD|URL|PLACE_CATEGORY|APP)

UserList (type=CRM_BASED|RULE_BASED|...)
└── used as AdGroupCriterion.user_list

ConversionAction
└── view_through_lookback_window_days (1..30)
```

Key invariants:
- Asset is shared across customers via asset linking; one upload, many ads
- A video asset cannot be deleted while referenced by any active ad
- Audience attaches at AdGroup, not Ad — you cannot vary audience per
  creative within an ad group
- Frequency caps live at the Campaign level for video, not AdGroup

## Webhooks and Events

N/A — Google Ads API has no webhook surface. The closest mechanism is
the `change_event` and `change_status` resources, which let you poll
for mutations made via UI or other API clients in the last 30 days.
For YouTube ads use `change_event` filtered by
`change_event.client_type` and `resource_change_operation` to detect
out-of-band edits to your campaigns. For real-time spend alerts, use
the Reporting API (search_stream) on a cron, not a webhook.

## Limits

Per Google Ads account:

- 10,000 active campaigns
- 20,000 ad groups per campaign
- 50 ads per ad group
- 5,000 keywords per ad group (contextual targeting on video)
- 20,000 user lists per account
- 5,000 audience targeting items per ad group
- Video asset library: effectively unlimited (governed by upload quota
  on YouTube itself, not Ads)
- Customer Match list: max 5M users per list
- 4 frequency caps per campaign (per impression / view event combos)
- Bumper ad: ≤ 6 seconds
- Non-skippable in-stream: ≤ 15s (US/most), ≤ 20s in eligible markets
- Skippable in-stream: 12s minimum to qualify for skip; no upper bound
  but completion rate falls off a cliff after 30s
- Video sequence: max 5 steps
- Final URL: must resolve to verified domain or be policy-flagged
- Conversion view-through window: 1-30 days

## Cost Model

- Bidding units:
  - CPM (cost per 1000 impressions) — bumpers, non-skip, reach
  - CPV (cost per view, view = 30s or completion or click) — legacy view
  - tCPA / Maximize Conversions — VIDEO_ACTION only
  - tROAS / Maximize Conversion Value — VIDEO_ACTION with value tracking
- Auction is second-price-ish (Google's quality-adjusted) — your bid is
  the ceiling, you pay the minimum needed to beat the next bidder
- Quality Score equivalent for video is the **Video Ad Quality Signal**,
  not exposed in the API; manifests as auction wins/losses
- No platform fee from Google; budget = total spend
- Reach Planner forecasts are free (no impressions consumed)
- Brand Lift studies require committed spend ($5k+ in most markets) to
  qualify but don't add a separate line item
- Conversion tracking via Google tag is free; Enhanced Conversions
  requires hashing PII server-side, also free

EOS implication: model spend as `(daily_budget * days)` for each
campaign; Reach Planner output for awareness campaigns; `tCPA *
target_conversions_per_day` for action campaigns.

## Version Pinning

- Pin `google-ads-python==25.x` matching the Google Ads API version
  you target. v17 maps to library 25.x; v18 maps to 26.x.
- Google Ads API versions sunset 14 months after release. v17 sunset
  is approximately Q3 2026; build the v18 upgrade into the runway.
- The `version` is set in google-ads.yaml as
  `use_proto_plus: true` and the library auto-targets the latest known
  version. Pin explicitly with `client.get_service("AssetService",
  version="v17")` to avoid surprise upgrades when the library bumps.
- New video sub_types (e.g. PMax/Demand Gen) appear without API
  version bumps as new enum values — handle unknown enums defensively.
- When v18 lands, run `validate_only=True` mutates against a sandbox
  customer to surface enum / field-name deltas before flipping prod.

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

Google's design choice with the Google Ads API is **one API surface per
customer, many channels per campaign type**. Video is not special;
it's a sub_type discriminator on Campaign + a payload oneof on Ad.
This is the same pattern Search and Shopping use, and it's why the
mental cost of learning "the YouTube ads API" is mostly the cost of
learning Google Ads — once you've mutated a Search campaign, the only
delta for video is which fields are legal in which oneof.

The intentional tradeoffs:

- **Atomicity vs. simplicity** — `GoogleAdsService.mutate` with
  temp-resource-name graphs is the only safe way to build a campaign
  tree, but it's brutally verbose. Google chose atomicity over ergonomic
  builders. Net: agents need a builder layer in EOS.
- **Smart bidding vs. control** — VIDEO_ACTION campaigns essentially
  force you into Google's smart bidder. You can set TCPA, but Google
  decides per-impression bid. You give up control to get conversions
  the manual bidder cannot reach. For pre-revenue brands with weak
  conversion signal, this is a real problem — TCPA needs volume to learn.
- **Platform measurement vs. third-party** — Brand Lift, view-through
  conversions, and Audience Insights all live inside Google's measurement
  stack. Third-party verification (DoubleVerify, IAS) is supported but
  paid and adds latency.
- **Reach Planner accuracy vs. transparency** — Reach Planner uses
  proprietary inventory data not exposed elsewhere. Forecasts are
  trustworthy at portfolio level, lossy at narrow-audience level.

## Problem-Solution Map and Hidden Capabilities

| Problem | Solution |
|---|---|
| Need to test 5 creative variants without 5 ad groups | `VIDEO_RESPONSIVE` ad type — Google rotates and reports per asset |
| Story-based sequenced messaging | `VIDEO_SEQUENCE` campaign — set a sequence of 2-5 ads, viewers see them in order over time |
| Drive frequency without overspending on heavy viewers | `VIDEO_REACH_TARGET_FREQUENCY` with frequency cap = target |
| Want bumper + skippable mix optimized together | `VIDEO_EFFICIENT_REACH` sub_type does this automatically |
| Retarget viewers who watched 25/50/75/100% of a video | `UserList` of type `RULE_BASED` with `user_visited_site_rule_user_list` keyed off YouTube engagement events (set up via Audience Manager) |
| Negative-list a brand-unsafe channel | `CampaignCriterion` with `negative=True` and `youtube_channel.channel_id` |
| Block your ads from kids' content | Set `network_settings` and content exclusions for `EMBEDDED_YOUTUBE`, plus `made_for_kids_excluded` content label |
| Get audience size before launch | `AudienceInsightsService.generate_audience_composition_insights` |
| Forecast spend before launch | `ReachPlanService.generate_reach_forecast` |
| See which actual videos served your ad | `FROM detail_placement_view` with `segments.ad_network_type='YOUTUBE_WATCH'` |
| Pause ads on individual placements | Negative `youtube_video` criterion at campaign level |
| Limit to a curated set of channels | Campaign type with `placement` targeting + bid modifier 0% on auto-placements (placements-only mode) |

Hidden capabilities most teams don't use:

- **Earned actions reporting** — `metrics.video_quartile_p100_rate` plus
  earned subscribers/likes/shares are pulled automatically when the
  channel is linked. Unique view-through-conversion attribution
  including organic lifts.
- **Affinity in-market overlap targeting** — using two `user_interest`
  criteria with `combination_rule` reduces audience but raises
  precision; useful for narrow founder offers.
- **Custom segment with URL members** — feed a list of competitor URLs;
  Google builds a lookalike search-intent segment.
- **Final URL suffix at customer level** — global UTM injection so you
  never forget tagging.

## Operational Behavior and Edge Cases

- Newly-created video campaigns enter a learning period (~7 days, ~50
  conversions) before TCPA stabilizes. Don't judge ROI inside the
  learning window.
- Pausing and resuming a campaign resets the learning period. Editing
  bid strategy or tCPA target by >20% also resets it. Treat the
  learning window as expensive — change one thing at a time.
- Disapproved ads still accrue impressions during review under
  `APPROVED_LIMITED` status (limited inventory, no kids/sensitive)
  while full review pends.
- Bumper-only campaigns receive zero `video_views`; this is correct,
  not a bug.
- Ads served on `YOUTUBE_SEARCH` (in-feed) have very different VTR than
  `YOUTUBE_WATCH` (in-stream). Always segment by `ad_network_type`.
- Customer Match audience refresh propagates within 24h after upload.
  Removing a user does NOT immediately stop targeting; expect ~24h tail.
- View-through conversions can appear with timestamps before any
  `metrics.video_views` because VTC is counted at impression-with-view
  threshold (>=2 seconds visible) on Skippable In-Stream.
- Geo targeting at country level always works; sub-country radius
  targeting on YouTube is approximate (city-level signal density).
- Frequency caps measured per cookie/device, not per logged-in user;
  expect drift on shared devices.
- Brand Lift survey impressions are randomly sampled from your impression
  pool — they don't add cost, but they consume inventory.

## Ecosystem Position and Composition

YouTube ads sit inside the Google Ads ecosystem alongside Search,
Shopping, Display, App, Performance Max, and Demand Gen. The
compositions worth knowing:

- **Performance Max** — auto-allocates budget across YouTube + Search +
  Display + Discover + Gmail + Maps. Replaces standalone YouTube for
  pure-conversion goals when you don't need channel control. EOS picks
  PMax for Lyfe Spectrum products with strong conversion data; sticks
  with VIDEO_ACTION for Initiate Arena until conversion volume justifies
  PMax learning.
- **Demand Gen** — successor to Discovery campaigns, includes Shorts
  feed, Discover, Gmail; visual-first creative testing. Use for brand
  awareness with image+video assets when you don't want full reach
  campaign overhead.
- **Search** — direct response counterpart. Often runs parallel with
  VIDEO_ACTION to capture in-market searchers that video creates.
- **GA4 + Google Tag** — required for view-through conversion fidelity
  and Enhanced Conversions for Web.
- **YouTube Studio** — channel owner UI for video upload, audience tab,
  engagement metrics. Earned actions flow from Studio into Ads.
- **DV360 (Display & Video 360)** — Google's enterprise DSP, alternative
  surface for buying YouTube inventory at scale with frequency
  management across publishers. Overkill for EOS but worth knowing.
- **Third-party DSPs** — most cannot buy YouTube directly; Google
  reserves YouTube inventory for Google Ads + DV360.

EOS composition pattern: video for top-of-funnel + retargeting on
Lyfe Spectrum, Search for bottom-of-funnel intent capture, paid
Instagram via Apify-driven outreach for direct-response on Initiate
Arena until volume justifies a YouTube test.

## Trajectory and Evolution

- **Performance Max + Demand Gen are pulling budget** — Google is
  steadily de-emphasizing standalone Display and Video Discovery
  campaigns in favor of multi-channel auto-allocators. Standalone video
  remains for cases where channel control matters (brand safety,
  reach planning, sequence ads).
- **CPV bidding is in slow sunset** — new VIDEO campaigns increasingly
  default to CPM/CPA. Treat CPV as legacy.
- **Shorts inventory is growing fast** — vertical 9:16 creative
  required to compete. Most VIDEO_ACTION inventory now flows through
  Shorts feed automatically.
- **Confidential matching for Customer Match** — coming v18, allows
  zero-party match without exposing hashes to Google, reducing legal
  friction for EU advertisers.
- **GA4 data-driven attribution becoming default** — last-click is
  being deprecated. View-through credit will increase under DDA.
- **Brand Lift -> Lift studies** — Google is consolidating brand,
  search, and conversion lift into unified "lift studies" — same API
  read patterns, new resource names by v19.

## Conceptual Model and Solution Recipes

The best mental model: **Campaign = strategy, AdGroup = audience,
Ad = creative**. Pin those three roles and every API question maps to
exactly one resource:

- "Where does the bid live?" → Campaign (smart) or AdGroup (manual)
- "Where does the audience live?" → AdGroupCriterion
- "Where does the creative live?" → AdGroupAd → Ad → Asset
- "Where does the budget live?" → CampaignBudget linked to Campaign
- "Where do conversions count?" → ConversionAction (account-level),
  optionally restricted via Campaign.selective_optimization

### Recipe: launch a TrueView for Action campaign for a founder VSL

1. Upload video as Asset (`YOUTUBE_VIDEO`)
2. Create CampaignBudget (`delivery_method=STANDARD`, `amount_micros`)
3. Create Campaign (`VIDEO`, `VIDEO_ACTION`, paused, MaximizeConversions
   with `target_cpa_micros`), reference budget
4. Create AdGroup (`VIDEO_RESPONSIVE` or `VIDEO_TRUE_VIEW_IN_STREAM`)
5. Create AdGroupAd with `in_stream_video_ad` (or
   `video_responsive_ad`) referencing the asset; set `final_urls` and
   `companion_banner` asset
6. Add AdGroupCriterion: customer-match user list + custom segment +
   demographic guardrails
7. Add CampaignCriterion: geo (country), language (en), negative
   placements (kids content exclusion)
8. `validate_only=True` mutate the whole tree
9. Mutate without validate_only
10. Wait for policy approval; flip Campaign + AdGroupAd to ENABLED
11. GAQL daily for `view_through_conversions` + `conversions`

### Recipe: 2-step VIDEO_SEQUENCE for warm audience

1. Build two video assets (hook + offer)
2. Campaign sub_type `VIDEO_SEQUENCE`, set
   `video_campaign_settings.video_sequence_step_settings`
3. Two AdGroups in order, each with one AdGroupAd
4. Audience: retargeting list of viewers who watched the awareness
   campaign past 25%

### Recipe: weekly performance pull for the EOS world_pulse loop

```sql
SELECT
  campaign.name,
  segments.date,
  metrics.cost_micros,
  metrics.impressions,
  metrics.video_views,
  metrics.video_view_rate,
  metrics.conversions,
  metrics.view_through_conversions,
  metrics.average_cpv,
  metrics.average_cpm
FROM campaign
WHERE campaign.advertising_channel_type = 'VIDEO'
  AND segments.date DURING LAST_7_DAYS
```

Aggregate `(conversions + view_through_conversions) / cost` for true
contribution rate; write into Neon `marketing_performance` table.

## Industry Expert and Cutting-Edge Usage

- **Demand Gen for Shorts-first creators** — pros are running Demand
  Gen as primary for vertical creative because it auto-allocates
  across Shorts feed + Discover and uses visual signals more
  effectively than VIDEO_ACTION on a Shorts asset alone.
- **Hook-test on YouTube before paid social** — using cheap reach
  campaigns to test hook variants on YouTube (more honest CPM than
  Meta's algorithm-flattered impressions) before scaling winners on
  Meta/TikTok.
- **Customer Match from CRM as the default starting audience** — even
  for cold campaigns, seeded with a 1% lookalike via similar audiences
  (Note: similar audiences for non-search were sunset in 2023; current
  practice is Customer Match + smart bidding allowed to expand).
- **Earned actions as a free brand-lift proxy** — measuring earned
  subs/shares per $ as a leading indicator of organic lift before
  running a paid Brand Lift study.
- **Server-side conversion uploads** via `ConversionUploadService` for
  first-party CRM events (calls booked, applications submitted) — more
  reliable than tag-based VTC for conversion-light businesses.
- **Negative placement curation** — top brand-safety teams maintain a
  ~5,000-channel negative list per account, refreshed monthly via
  Apify scrapes of trending content categories.
- **Reach Planner as creative brief input** — pulling demographic
  composition for a target audience before scripting, so the script
  matches who will actually see it.

---

## EOS Usage Patterns

### Initiate Arena founder content amplification

- Lyfe Institute Google Ads account (manager link to MCC)
- One `VIDEO_ACTION` campaign per long-form VSL drop, lifecycle ~30 days
- AdGroup audience layers:
  1. Customer Match: existing CRM contacts not yet customers
  2. Custom Segment (SEARCH): competitor coach search terms
  3. In-Market: Business & Industrial > Career Resources
- Conversion action: `arena_application_submitted` (Google Tag on form
  thank-you, primary, count once)
- Bidding: MaximizeConversions with TCPA = current customer LTV * 0.10
- Daily budget: $30 in test, $100 in scale (HIGH risk class — CEO
  approval required above $50)
- Reporting cadence: daily GAQL pull into `marketing_performance` Neon
  table; weekly summary to world_pulse

### Lyfe Spectrum product drops

- Empyrean Studio Google Ads account
- Two-stage media plan:
  1. **Awareness** — `VIDEO_REACH_TARGET_FREQUENCY` campaign 14 days
     pre-launch, target frequency 3 over 14d, broad demographic +
     affinity (Lifestyles & Hobbies > Fashionistas, etc.)
  2. **Conversion** — `VIDEO_ACTION` retargeting view-engagers (75%
     watched) and Shopify customer list, Maximize Conversion Value
     against Shopify revenue conversion
- Creative: 6s bumper hook + 15s product story + 30s lookbook
- Vertical 9:16 master plus 16:9 derivative for in-stream

### Agent workflow

- `model_router.call_with_fallback(agent_type='strategist', ...)` to
  draft campaign trees as JSON; human approves; deterministic Python
  builder converts JSON to `MutateOperation` graph
- `validate_only=True` always before live mutate
- Post-mutate: persist resource names to Neon `campaigns_youtube`
- `world_pulse` weekly report: best/worst ad by VTC contribution,
  recommend pause/scale

### Verification commands

```bash
# Import smoke
python3 -c "import sys; sys.path.insert(0,'/opt/OS'); from eos_ai.youtube_ads_client import YouTubeAdsClient; print('ok')"

# Validate-only dry run
python3 -m eos_ai.youtube_ads_client validate --campaign-spec /tmp/spec.json

# Pull last 7 days
python3 -m eos_ai.youtube_ads_client report --days 7 --customer-id 1234567890
```

## Gotchas

(Compounds over time; mirrors and extends the SKILL.md gotchas list.)

- **YouTube channel link is UI-only.** No API endpoint creates the
  Linked Accounts → YouTube link. Provisioning a new account is a
  manual step.
- **Video ID must be the bare 11-char ID.** Pasting a URL returns
  `INVALID_YOUTUBE_VIDEO_ID`. EOS spec parser must strip URLs.
- **Private videos rejected; unlisted accepted.** Standard pre-launch
  pattern: upload video to YouTube as unlisted, run paid first, then
  flip to public after first view milestone.
- **Status PAUSED on create is server-enforced.** Two-step pattern:
  create paused, then mutate to ENABLED after QA.
- **Bumper duration is exact 6.000s.** 6.04s rejected. Encode at exact
  duration, not "about six seconds."
- **Non-skippable cap is region-dependent.** 15s most markets, 20s in
  some EMEA markets. Targeting multi-region = lowest cap binds.
- **`view_through_conversions` are NOT in `conversions`.** Sum both
  for true contribution. EOS dashboards must do this explicitly or
  understate ROAS by ~50% for awareness campaigns.
- **`metrics.video_views` only fires at 30s OR completion.** Bumpers
  always show zero. Use impressions + CPM for bumper performance.
- **Custom Audiences replaced Custom Intent and Custom Affinity in
  late 2022.** Old `CustomIntent` resource is read-only.
- **Customer Match list warms up in 24-72h.** Don't bind a campaign
  until `size_for_display > 1000` or YouTube won't deliver.
- **Brand Lift requires committed spend ($5k+) and a Google rep
  invitation.** No self-serve API.
- **Policy review is 1-3 business days for video** vs. minutes for
  search. Schedule Initiate Arena drops accordingly.
- **`ENABLED` ≠ serving.** Always join
  `ad_group_ad.policy_summary.approval_status` in launch verification.
- **Bidding strategy is constrained by sub_type.** `BIDDING_STRATEGY_
  NOT_SUPPORTED_WITH_AD_GROUP_TYPE` if you mismatch. Memorize the table.
- **AdGroup type must match Campaign sub_type.** Same enforcement
  layer; same family of errors.
- **Smart bidder needs ~50 conversions in 30d to stabilize.** Setting
  TCPA in pre-revenue phase silently throttles delivery.
- **Editing TCPA by >20% resets the learning period.** Don't tinker.
- **Pausing/resuming resets the learning period.** Same.
- **Bumper-only campaign with zero video_views is correct, not a bug.**
- **`segments.ad_network_type` matters.** YOUTUBE_WATCH and
  YOUTUBE_SEARCH have radically different VTR; segment in every report.
- **Customer Match removal has ~24h tail.** Removed users keep getting
  served briefly.
- **Frequency caps are device-cookie-scoped, not user-scoped.** Drift
  expected on shared devices.
- **Reach Planner forecasts use a separate inventory model.** Don't
  reconcile to auction data; use as planning, not truth.
- **Multi-step builds must use `GoogleAdsService.mutate` with temp
  resource names** — otherwise partial failures orphan campaigns.
- **`partial_failure=True` on agent runs.** A bad single ad shouldn't
  fail the whole batch; parse `partial_failure_error.details` per index.
- **Gemini 429 + Anthropic 401 means agents currently can't draft and
  validate live.** When credits restore, the campaign-builder agent
  should be wired with `agent_type='strategist'` for Opus reasoning.
- **`google-ads-python` library version must match API version.** v17
  → 25.x; v18 → 26.x. Pin in requirements.txt.
- **API version sunsets every 14 months.** v17 sunsets ~Q3 2026; bake
  v18 upgrade work into the runway.
- **`final_urls` must be on the Ad, not the AdGroup.** Search ads
  allow ad-group-level final URLs; video ads do not. Setting it on
  AdGroup silently no-ops.
- **Companion banner is required for desktop in-stream ads** of certain
  formats — Google auto-generates one from the channel avatar if not
  supplied, but the auto-generated version is brand-off. Always supply
  an `ImageAsset` companion (300x60).
- **`call_to_action.text` is restricted to a closed enum** (Apply,
  Sign Up, Learn More, Shop Now, Subscribe, Download, Book Now, Get
  Quote, Watch, Visit Site, Get Offer, Contact Us, Order Now, Get
  Started). Custom CTA text rejected.
- **`headline` and `description` character limits**: in-feed video ad
  headline 100 chars; description 35 chars per line × 2 lines.
  Responsive video ad: 5 short headlines (15 chars) + 5 long headlines
  (90 chars) + 5 descriptions (90 chars).
- **`final_urls` domain must match the verified domain on the Ads
  account** — verification is one-time per domain in Ads UI; first
  campaign on a new domain blocks here.
- **Conversion lookback window changes propagate retroactively.** A
  60-day window applied today recounts the last 60 days of impressions
  for VTC. Useful for backfill, dangerous if you forget.
- **Cross-account conversion tracking** requires the conversion action
  to live on the manager (MCC), not the child. Common foot-gun for
  accounts new to MCC structure.
- **Audience expansion (Optimized Targeting) is on by default for
  VIDEO_ACTION** as of mid-2024. It will spend outside your declared
  audiences. Disable explicitly if you need strict audience control:
  `targeting_setting.target_restrictions[].targeting_dimension=AUDIENCE,
  bid_only=True` doesn't apply here — use the new
  `optimized_targeting_enabled=False` field.
- **Geographic targeting at sub-country level reduces YouTube
  inventory dramatically** because YouTube IP-to-geo is coarser than
  search. Country-level is the safe default unless EOS is running a
  hyperlocal Lyfe Spectrum drop.
- **`change_event` polling has a 30-day window.** Anything older is
  invisible. Run the change-event sweep at least weekly to catch
  out-of-band edits.
- **Mutate response `RESOURCE_NAME_ONLY` is the default** — use
  `MUTABLE_RESOURCE` if you need the post-mutate state without an
  extra GAQL roundtrip. Costs nothing extra.
- **`validate_only=True` does not catch policy violations.** It
  validates schema and most business rules, but actual creative
  policy review only happens post-mutate. Build a separate
  pre-flight policy-risk classifier in agent layer for sensitive
  verticals (coaching, supplements, fitness — all relevant to EOS).
- **Smart bidding ignores manual bid adjustments** like
  device/age/gender bid modifiers. Setting them on a TCPA campaign
  is a no-op. Reporting still segments correctly, but the bidder
  doesn't honor them.
