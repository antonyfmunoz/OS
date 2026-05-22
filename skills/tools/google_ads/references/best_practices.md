# Google Ads API — Creator-Level Best Practices
Source: developers.google.com/google-ads/api, googleads/google-ads-python, ads-developers.googleblog.com
API Version: v23.1 (released February 25, 2026)
SDK Version: google-ads-python 26.x (proto-plus messages)
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## Authentication

Three credentials, all required, all separate concerns:

1. **Developer token** — application-level identity, issued once per
   manager (MCC) account by Google after a developer token application.
   Sent as the `developer-token` HTTP header on every request. The token
   has an *access level* (Test → Basic → Standard) that gates the daily
   operations quota and which production accounts you can hit. Tokens
   start in Test and must be promoted via a written application; until
   then they only work against test MCCs.

2. **OAuth2 user credentials** — `client_id` + `client_secret` (from a
   Google Cloud project with the Google Ads API enabled) plus a
   `refresh_token` issued for a user account that has access to the target
   Google Ads accounts. The SDK exchanges the refresh token for a
   short-lived access token on every request. Three OAuth flows are
   supported: Installed Application (CLI/desktop), Web Application
   (server-side OAuth callback), and Service Account (only for Google
   Workspace domain-wide delegation; rarely used because most Ads
   accounts are personal Gmail).

3. **login-customer-id** — a 10-digit MCC ID with no dashes, sent as the
   `login-customer-id` HTTP header. This declares "I am acting through
   this manager account" so the API knows which MCC to traverse to reach
   the target child account. Required whenever the authenticated user
   accesses a child account through a manager. If you forget it on an
   MCC-traversal call you get a `USER_PERMISSION_DENIED` with no useful
   detail.

The SDK stores all three together. The canonical loader is
`GoogleAdsClient.load_from_env(version="v23")` which reads:

```
GOOGLE_ADS_DEVELOPER_TOKEN
GOOGLE_ADS_CLIENT_ID
GOOGLE_ADS_CLIENT_SECRET
GOOGLE_ADS_REFRESH_TOKEN
GOOGLE_ADS_LOGIN_CUSTOMER_ID
GOOGLE_ADS_USE_PROTO_PLUS=True
```

Alternative loaders: `load_from_storage("/path/google-ads.yaml")`,
`load_from_dict({...})`, or `load_from_string(yaml_str)`. EOS rule: env
only. Never check a `google-ads.yaml` into the repo and never load it
from `~`.

Refresh tokens generated for "@gmail.com" Google accounts in apps still
in OAuth Testing mode expire after 7 days. Move the GCP project to
"Production" verification status before deploying or your refresh token
will silently die mid-week.

## Core Operations with Exact Signatures

All operations are gRPC RPCs on typed services. The Python SDK exposes
each service via `client.get_service("ServiceName")`. Method signatures
below are normalized to Python.

### GoogleAdsService — the universal entry point

```python
ga = client.get_service("GoogleAdsService")

# Paged search — 10,000 rows per page
response = ga.search(
    customer_id: str,
    query: str,                       # GAQL
    page_token: str = "",
    page_size: int = 10000,
    validate_only: bool = False,
    return_total_results_count: bool = False,
    summary_row_setting: enum = UNSPECIFIED,
    search_settings: SearchSettings = None,
)
# Returns SearchPagedResponse — iterate or use response.next_page_token

# Streamed search — single RPC, all rows
stream = ga.search_stream(
    customer_id: str,
    query: str,
    summary_row_setting: enum = UNSPECIFIED,
)
# Returns iterable of SearchGoogleAdsStreamResponse batches; each batch
# has .results, .field_mask, and .request_id

# Cross-resource bulk mutate
response = ga.mutate(
    customer_id: str,
    mutate_operations: list[MutateOperation],
    partial_failure: bool = False,
    validate_only: bool = False,
    response_content_type: enum = RESOURCE_NAME_ONLY,
)
```

### Per-resource mutate services

Every resource type has a dedicated mutate service with the same shape:

```python
campaign_service = client.get_service("CampaignService")
response = campaign_service.mutate_campaigns(
    customer_id: str,
    operations: list[CampaignOperation],
    partial_failure: bool = False,
    validate_only: bool = False,
    response_content_type: enum = RESOURCE_NAME_ONLY,
)
```

Equivalents exist for AdGroup, AdGroupAd, AdGroupCriterion, CampaignBudget,
ConversionAction, Asset, AssetGroup, AssetGroupAsset, CustomerNegativeCriterion,
SharedSet, BiddingStrategy, RecommendationService, and many more.

### Operation message structure

Every `*Operation` is a oneof with `create`, `update`, `remove`, plus an
`update_mask` field for partial updates. The proto-plus pattern:

```python
op = client.get_type("CampaignOperation")
campaign = op.create                  # populate fields directly
campaign.name = "IA - Search - Brand"
campaign.advertising_channel_type = client.enums.AdvertisingChannelTypeEnum.SEARCH
campaign.status = client.enums.CampaignStatusEnum.PAUSED
campaign.campaign_budget = budget_resource_name
campaign.manual_cpc.enhanced_cpc_enabled = False  # bidding strategy oneof

# For update, set resource_name and use update_mask
op2 = client.get_type("CampaignOperation")
op2.update.resource_name = "customers/123/campaigns/987"
op2.update.status = client.enums.CampaignStatusEnum.ENABLED
client.copy_from(op2.update_mask, protobuf_helpers.field_mask(None, op2.update._pb))
```

### ConversionUploadService

```python
upload_svc = client.get_service("ConversionUploadService")

upload_svc.upload_click_conversions(
    customer_id: str,
    conversions: list[ClickConversion],
    partial_failure: bool = True,
    validate_only: bool = False,
    debug_enabled: bool = False,
)

upload_svc.upload_call_conversions(
    customer_id: str,
    conversions: list[CallConversion],
    partial_failure: bool = True,
    validate_only: bool = False,
)
```

### BatchJobService

```python
bj = client.get_service("BatchJobService")

# 1. Create
create_resp = bj.mutate_batch_job(
    customer_id=cid,
    operation={"create": {}},
)
batch_job_resource = create_resp.result.resource_name

# 2. Add operations (paged add, up to 1M total per job)
add_resp = bj.add_batch_job_operations(
    resource_name=batch_job_resource,
    sequence_token=None,         # opaque, returned by previous add call
    mutate_operations=[...],
)

# 3. Run (returns LRO)
lro = bj.run_batch_job(resource_name=batch_job_resource)

# 4. List results
for row in bj.list_batch_job_results(resource_name=batch_job_resource):
    print(row.operation_index, row.status, row.mutate_operation_response)
```

## Pagination Patterns

Two methods, one query:

- **`search`** — fixed-size pages of up to 10,000 rows. The response
  contains `next_page_token`; pass it back as `page_token` for the next
  request. Each `search` call counts as one operation.
- **`search_stream`** — single RPC, server streams as many batches as
  needed until the result set ends. The Python SDK exposes it as an
  iterable of `SearchGoogleAdsStreamResponse` objects, each containing a
  `results` repeated field. **One stream = one operation** regardless of
  row count.

Rule of thumb: **always use `search_stream`** unless you genuinely need
random-access paging (UI showing page 5 of 17). For agent reporting you
read all rows into Pandas/Neon and `search_stream` is strictly faster
because it eliminates per-page round trips.

`OFFSET` is not supported in GAQL. `LIMIT N` is. There is no way to skip
N rows other than reading and discarding them.

`GoogleAdsService.search` supports `return_total_results_count=True` if
you need a row count without iterating; this adds quota but is cheaper
than fetching all rows just to count them.

## Rate Limits

Two independent ceilings: **operations per day** (per developer token)
and **QPS** (per developer token + customer ID combination, token-bucket).

### Operations per day, by access level

| Access Level | Daily Operations Cap |
|---|---|
| Test | only test MCC, no production calls |
| Explorer | 2,880 ops/day against production accounts |
| Basic | 15,000 ops/day |
| Standard | unlimited for `Search`/`SearchStream`; high cap for mutates |

"Operations" means both reads (each `search` page or `searchStream` call
= 1 op) and mutates (one operation per `*Operation` in a request). The
day is a sliding 24h window, not midnight-to-midnight.

### Per-CID QPS

The token-bucket rate limit on each (developer-token, customer-id) pair
is not published as a fixed number — it varies with overall server load.
When you blow it you get `RESOURCE_EXHAUSTED` with a `retryDelay` field
in `quotaErrorDetails`. Honor that delay; do not hardcode sleeps.

### Mutate request size cap

A single mutate request cannot contain more than **10,000 operations**.
Larger jobs must use `BatchJobService` (cap: 1M operations per batch
job, 100 active+pending jobs per account).

## Error Codes and Recovery

The Google Ads API returns gRPC status codes plus a `GoogleAdsFailure`
proto in the error details with structured `errors[]`. Each error has an
`error_code` (oneof of dozens of error enums), a human `message`, a
`trigger` value, and a `location.field_path_elements` pointing at the
exact field that broke.

| gRPC code | Common cause | Recovery |
|---|---|---|
| `INVALID_ARGUMENT` | malformed GAQL, bad field, bad enum, missing required field | parse `field_path_elements`, fix the field |
| `PERMISSION_DENIED` / `USER_PERMISSION_DENIED` | wrong `login-customer-id`, refresh token has no access, dev token wrong access level | check headers; re-auth refresh token |
| `UNAUTHENTICATED` | refresh token expired or revoked | regenerate refresh token via OAuth flow |
| `RESOURCE_EXHAUSTED` | per-CID QPS or daily ops cap | exponential backoff honoring `retryDelay` |
| `FAILED_PRECONDITION` | account in unworkable state (suspended, billing failed) | surface to human, no retry |
| `INTERNAL` / `UNAVAILABLE` | transient Google-side | retry with backoff up to 5 attempts |
| `DEADLINE_EXCEEDED` | RPC slower than client timeout | increase timeout, narrow query |

EOS error handler pattern (always):

```python
from google.ads.googleads.errors import GoogleAdsException
try:
    response = service.mutate_campaigns(...)
except GoogleAdsException as ex:
    for err in ex.failure.errors:
        print(f"[{err.error_code}] {err.message}")
        if err.location:
            for el in err.location.field_path_elements:
                print(f"  at {el.field_name}[{el.index}]")
    print(f"request_id={ex.request_id}")
    raise
```

The `request_id` is the single most useful debugging artifact — include
it in every log line and in any escalation to Google support.

## SDK Idioms

The Python SDK is built on `proto-plus`, a Pythonic wrapper over
protobuf. Always run with `use_proto_plus=True`.

### Resource name builders

Every service exposes path helpers:

```python
campaign_service.campaign_path(customer_id, campaign_id)
ad_group_service.ad_group_path(customer_id, ad_group_id)
asset_service.asset_path(customer_id, asset_id)
```

Build resource names with these — never f-string them yourself.

### Enum access

```python
client.enums.CampaignStatusEnum.ENABLED
client.enums.AdvertisingChannelTypeEnum.PERFORMANCE_MAX
client.enums.KeywordMatchTypeEnum.EXACT
```

### `client.get_type("Foo")` vs `client.get_service("FooService")`

`get_type` instantiates a message (`CampaignOperation`, `ClickConversion`,
`UserIdentifier`). `get_service` returns an RPC stub. Confusing them is
the most common SDK newbie error.

### `client.copy_from`

For setting nested oneof or message fields, use:

```python
client.copy_from(parent.field, child)
```

Never assign nested messages with `=` — proto-plus will reject it.

### Update masks

For updates, set only the fields you intend to change *and* an
`update_mask` listing those field paths. The SDK provides a helper:

```python
from google.api_core import protobuf_helpers
op.update.status = client.enums.CampaignStatusEnum.PAUSED
client.copy_from(op.update_mask, protobuf_helpers.field_mask(None, op.update._pb))
```

The helper inspects `op.update._pb` and produces the mask automatically.

### Temporary resource IDs in bulk mutate

When creating multiple linked resources in one mutate, you cannot know
the real resource IDs yet. Use negative integers as placeholders:

```python
TEMP_BUDGET_ID = -1
TEMP_CAMPAIGN_ID = -2

budget_op.create.resource_name = f"customers/{cid}/campaignBudgets/{TEMP_BUDGET_ID}"
campaign_op.create.campaign_budget = budget_op.create.resource_name
campaign_op.create.resource_name = f"customers/{cid}/campaigns/{TEMP_CAMPAIGN_ID}"
```

The server resolves negative IDs to real ones in the same request.
Negative IDs only work within a single mutate call.

## Anti-Patterns

- **Polling status with `search` instead of `searchStream`** wastes ops.
- **Looping `search` 1 row at a time** ("get me one campaign") instead
  of batching by IDs in a `WHERE id IN (...)` clause.
- **Catching `GoogleAdsException` and printing `str(e)`** discards the
  structured `failure` proto. Always iterate `ex.failure.errors`.
- **Hardcoding spend in dollars instead of micros.** Setting
  `cpc_bid_micros = 5` is half a cent, not five dollars.
- **Using `validate_only=True` then immediately running again with it
  False without re-running the same draft.** State can drift between
  calls; the second call may now fail validation that the first passed.
- **Creating one campaign per request in a loop** instead of batching.
  Each call is one network round trip and one ops increment.
- **Setting `partial_failure=False`** on a bulk upload of conversions —
  one bad row aborts everything. Conversions should always be partial.
- **Forgetting `update_mask`** on an update — the API silently ignores
  the field changes if no mask is set, and you wonder why nothing happened.
- **Using `client_id` from the wrong GCP project** that doesn't have the
  Google Ads API enabled. Failure mode is `PERMISSION_DENIED` from auth,
  not from Ads.
- **Pinning to a deprecated API version** in CI. Pin `version="v23"`
  explicitly and add a calendar reminder to upgrade before sunset.
- **Treating `validate_only=True` as free** — it still consumes quota.
- **Using `search` instead of `searchStream` for reports** because
  "streams are scary." Streams are simpler in Python: just iterate.
- **Re-creating `GoogleAdsClient` per request** — TLS handshake on every
  call. Cache the client at module scope.

## Data Model

The Google Ads object graph, simplified:

```
Customer (account)
├── CampaignBudget (shared across campaigns)
├── BiddingStrategy (portfolio strategies)
├── ConversionAction
├── Asset (image, text, video, callout, sitelink, ...)
├── Campaign
│   ├── CampaignBudget (link)
│   ├── CampaignCriterion (location, language, audience targeting at campaign level)
│   ├── AdGroup
│   │   ├── AdGroupAd (the actual creative)
│   │   ├── AdGroupCriterion (keyword, audience, demographic)
│   │   └── AdGroupAdLabel
│   └── (Performance Max only) AssetGroup
│       └── AssetGroupAsset (links Asset → AssetGroup with FieldType)
└── CustomerNegativeCriterion (account-wide negatives)
```

Key invariants:

- A `Campaign` always has exactly one `CampaignBudget` (which may be
  shared with other campaigns).
- A Performance Max `Campaign` has one or more `AssetGroup`s, each with
  linked assets via `AssetGroupAsset`. Asset groups are not shareable
  across campaigns.
- `Asset`s are reusable. Linking is what assigns them to a context.
- Keywords (`AdGroupCriterion` of type `KEYWORD`) live at the ad group
  level. Negative keywords can live at the ad group, campaign, or shared
  set level.
- `ConversionAction` lives at the customer level, not the campaign level.
- `Resource_name` is the canonical identity — never use bare IDs across
  services without rebuilding the resource name.

GAQL `FROM` clauses are *resources*, not tables. Each resource has a
fixed set of joinable resources, fields, segments, and metrics. Reference:
the per-resource pages under `developers.google.com/google-ads/api/fields/v23/`.

## Webhooks and Events

**The Google Ads API has no webhook system.** It is a polling API.
There is no push notification when a campaign is paused, when a budget
runs out, or when a conversion fires. To detect changes you must:

1. **Poll GAQL on a schedule** — query `change_event` or `change_status`
   resources to find what changed since a checkpoint.
2. **Use `change_event`** — entries are kept for ~30 days and include
   the user, the change type, and old/new values for every field
   touched.
3. **Use `change_status`** — coarser, indicates which resources changed
   without per-field detail. Useful for incremental syncs.

Conversion notifications are similarly polled — `conversion_action_id`
metrics show up in metrics queries on whatever cadence Google decides
(usually within hours, sometimes 24h+).

EOS pattern: nightly cron at 3am pulls `change_event` since the last
checkpoint, writes to Neon, and the morning brief surfaces anything
that happened outside business hours.

## Limits

| Limit | Value |
|---|---|
| Mutate operations per request | 10,000 |
| BatchJob operations per job | 1,000,000 |
| Active+pending BatchJobs per account | 100 |
| GAQL search page size | 10,000 |
| GAQL query length | ~16 KB practical |
| Asset groups per Performance Max campaign | 100 |
| Ad groups per campaign | 20,000 |
| Keywords per ad group | 20,000 (target far less for quality) |
| Negative keywords per campaign | 10,000 |
| Active conversion actions per account | 50,000 |
| ClickConversions per upload request | 2,000 |
| Resource name length | 255 chars |
| Customer ID format | exactly 10 digits, no dashes when used in API |

## Cost Model

The Google Ads API itself is **free** to use — there is no per-request
charge. The cost is the spend you authorize on the underlying ads. The
two indirect costs:

1. **Engineering cost of getting it wrong** — a bad `mutate_campaigns`
   that flips a paused campaign to ENABLED with a 10x budget burns real
   money in minutes. The API has no "spending cap" safety net. Your
   safety net is `validate_only`, code review, and human approval on
   anything that changes spend.
2. **Quota** — operations against your daily cap. At Standard access
   this is effectively unlimited for reads.

Performance Max and Smart Bidding require **conversion data** to work.
Uploading Enhanced Conversions for Leads is free to the API but
critical: without high-quality conversions the bidding algorithm has
nothing to learn from and your spend is wasted. The "cost" is the
engineering work to wire your CRM closed-won events to
`upload_click_conversions`.

## Version Pinning

Google releases a new major version roughly every 2-3 months and sunsets
versions after ~8 months. The version is in the URL: `v23`. Pin in code:

```python
client = GoogleAdsClient.load_from_env(version="v23")
```

As of April 2026:
- v17, v18 — **dead** (sunset)
- v19, v20, v21, v22 — older, still alive but soon to sunset
- **v23.1** — current (released Feb 25, 2026), recommended pin

Upgrade procedure:
1. Read the release notes for v23 → next-version diff.
2. Upgrade the SDK: `pip install -U google-ads`.
3. Change `version=` argument.
4. Run the smoke test (read-only `searchStream` against a known account).
5. Run a `validate_only=True` mutate against a known sandbox campaign.
6. Deploy.

Subscribe to `googleadsapi-announcements@googlegroups.com` for sunset
notifications. Calendar a v-bump six weeks before any scheduled sunset.

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

The Google Ads API exists because Google's advertising business runs at
a scale where the UI is insufficient for power users. Agencies managing
thousands of accounts, in-house teams running tens of thousands of ad
groups, and bid management platforms (Marin, Kenshoo, Skai) all need
machine access. The API design reflects three priorities, in order:

1. **Safety of Google's revenue** — quotas, access levels, validate-only,
   developer token review, OAuth scopes. Google would rather make the
   API hard than let a buggy script accidentally bid $1M on a typo.
2. **Schema parity with the UI** — every concept in the Ads UI has a
   resource. New features land in the API at the same time as the UI
   (or shortly after). This creates surface-area bloat (hundreds of
   resources) but means anything humans can do, agents can do.
3. **Versioned forward motion** — Google ships features fast and is
   willing to break the API to do it. The 8-month sunset cycle is the
   tradeoff: Google buys the right to evolve, you pay the cost of
   periodic upgrades.

The migration from AdWords API (SOAP, version-by-name) to Google Ads
API (gRPC, version-by-number, GAQL) was a hard reset around 2018. The
old SOAP API is dead. Anything written before 2019 is a museum piece.

The choice of **gRPC + proto-plus** instead of REST+JSON is deliberate:
the schema is too large and too tightly typed for hand-written JSON
clients. The REST mirror exists for languages without good gRPC
support, but the SDKs are gRPC-native.

## Problem-Solution Map and Hidden Capabilities

| Problem | API Solution |
|---|---|
| Pull all spend for last week across 50 child accounts | `searchStream` against each child CID with login_customer_id set to the MCC |
| Find wasteful keywords | GAQL on `search_term_view` with `metrics.cost_micros > X AND metrics.conversions = 0` |
| Bulk pause underperformers | `validate_only` first, then `mutate_campaigns` with `partial_failure=True` |
| Sync CRM closed-won to ad platform | `ConversionUploadService.upload_click_conversions` with hashed user identifiers |
| Detect "what changed last night" | `change_event` resource since checkpoint |
| Stage millions of ops without timeout | `BatchJobService` |
| Test a campaign without paying | Test MCC + test customer (not Test access against prod) |
| Mirror a campaign across accounts | Read with `searchStream`, write with bulk mutate using temp negative IDs |
| Get Recommendations and apply selectively | `RecommendationService.list_recommendations` then `apply_recommendation` |
| Find which assets are "Best/Good/Low" in PMax | GAQL on `asset_group_asset` joined to `asset_group_top_combination_view` |

Hidden capabilities most users miss:

- **`change_event`** — full audit log accessible via GAQL.
- **`search_term_view` resource** — actual search queries that triggered
  your ads, not just your keywords.
- **`shared_set`** + `campaign_shared_set` — manage negative keyword
  lists once, attach to many campaigns.
- **`label`** — apply labels via the API, then filter reports by them.
- **`customizer_attribute`** — dynamic ad customization without managing
  per-ad copy.
- **`recommendation`** resource — every "Optimization Score" suggestion
  in the UI is queryable and apply-able.
- **`audience_insights_service`** — programmatic audience research.
- **`reach_plan_service`** — forecast reach/frequency before launching
  YouTube/Display/Video campaigns.
- **`keyword_plan_service`** — programmatic Keyword Planner access (the
  same tool as the UI, with the same data).

## Operational Behavior and Edge Cases

- **Eventually consistent reporting.** Metrics in `metrics.*` lag behind
  reality by 3-24 hours. Don't expect "spend in the last 5 minutes" to
  be accurate. For real-time monitoring use the budget pacing fields,
  not metrics.
- **Smart Bidding learning period** — newly created or significantly
  changed bid strategies enter a 1-2 week learning phase during which
  performance is volatile. Resist the urge to "fix" things mid-learning.
- **Auction-time signals** — many performance variables (device, time,
  audience) are decided at auction. The API exposes them via `segments`
  in GAQL. Segmenting by `segments.device` triples your row count.
- **`metrics.cost_micros`** is in the *account currency* — for multi-
  currency MCCs you must read `customer.currency_code` per CID and
  convert to a base currency yourself. The API will not do it.
- **Time zones** — every account has a fixed time zone
  (`customer.time_zone`). All `segments.date` filtering is in *that*
  zone, not UTC. Cross-account date ranges need per-account fixups.
- **Removed resources stay queryable** — `WHERE status != 'REMOVED'` is
  almost always what you want; otherwise you'll get historical orphans.
- **Resource removal is soft.** Removed entities remain accessible via
  GAQL forever (so historical reporting works). They just can't be
  re-enabled — you must create new ones.
- **API responses are paged at the field level too** — long lists of
  ad group criteria return in chunks even within a single page.
- **gRPC deadlines default to 1 hour** in the SDK. Long-running batch
  job polling is fine but a single search_stream that takes more than
  an hour will time out.

## Ecosystem Position and Composition

The Google Ads API is one member of a family:

- **Google Ads API** — the live ad platform (what this skill covers)
- **Google Analytics Data API (GA4)** — site/app analytics, not ads
- **Search Ads 360 Reporting API** — enterprise SA360
- **Display & Video 360 API** — DV360 (programmatic display)
- **Campaign Manager 360 API** — ad serving / measurement
- **Merchant Center API** — product feeds for Shopping/PMax retail
- **Tag Manager API** — GTM container management

Composition with other systems EOS already uses:

- **Neon Postgres** — every nightly GAQL pull writes a snapshot to a
  versioned table. Diffs power the morning brief.
- **CRM (HubSpot/Notion)** — closed-won events trigger Enhanced
  Conversion uploads via the `ConversionUploadService`.
- **Gemini / Claude** — agents interpret report deltas, draft
  recommendations, write GAQL queries for ad-hoc investigations.
- **Discord / Telegram** — alerts when budget pacing or RESOURCE_EXHAUSTED.
- **Apify** — scrape competitor SERPs for keyword discovery; feed
  candidates into draft mutates.

The API is not a substitute for the Ads UI for human work. Humans should
still review changes, look at the optimization score, and approve spend
changes in the UI. The API is for automation and reporting.

## Trajectory and Evolution

Where the API has been heading:

- **Performance Max** — Google's preferred campaign type. Almost every
  release adds PMax capability. Search and Shopping are being slowly
  subsumed.
- **Privacy and consent** — `consent` field on conversions is now
  required for traffic from EEA/UK. Enhanced Conversions push hashed
  first-party data into bidding (replacing third-party cookies).
- **AI-driven everything** — Smart Bidding is non-optional for PMax. The
  recommendation system increasingly drives auto-applied optimizations.
- **Asset-first creative** — the Ad object is being deprioritized in
  favor of Asset + AssetGroup. PMax has no traditional "ads."
- **Generative copy** — recent versions added LLM-generated headlines/
  descriptions hooks via the `customizer_attribute` and asset
  generation workflows.
- **Sunset cadence** — Google has held to 8-month version lifespans for
  three years. Plan for it.

What this means for EOS: build everything around Performance Max,
treat conversions as the bidding fuel, and plan for v-bumps every 6-8
months as a normal maintenance task.

## Conceptual Model and Solution Recipes

The deepest mental model: **the API is a thin RPC layer over a giant
relational database.** Resources are tables. GAQL is SQL. Mutate is
INSERT/UPDATE/DELETE. The schema is fixed by Google and versioned. Every
weird behavior makes sense if you remember that you are querying a
database that powers a multi-billion-dollar ad auction in real time —
of course it's eventually consistent, of course it has quotas, of course
some fields are read-only after creation.

### Recipe: nightly performance pull

```python
# 1. Build query from a template
query = f"""
  SELECT
    campaign.id, campaign.name,
    metrics.cost_micros, metrics.conversions,
    metrics.conversions_value, metrics.clicks, metrics.impressions
  FROM campaign
  WHERE segments.date BETWEEN '{start}' AND '{end}'
"""
# 2. Stream
for batch in ga.search_stream(customer_id=cid, query=query):
    for row in batch.results:
        upsert_to_neon(row)
# 3. Write checkpoint
write_checkpoint(cid, end)
```

### Recipe: safe campaign update

```python
# 1. Read current state
current = ga.search(customer_id=cid, query=f"SELECT campaign.status, campaign.name FROM campaign WHERE campaign.id = {cid}")
log(current)

# 2. Build operation
op = client.get_type("CampaignOperation")
op.update.resource_name = campaign_service.campaign_path(cid, campaign_id)
op.update.status = client.enums.CampaignStatusEnum.PAUSED
client.copy_from(op.update_mask, protobuf_helpers.field_mask(None, op.update._pb))

# 3. Validate
campaign_service.mutate_campaigns(customer_id=cid, operations=[op], validate_only=True)

# 4. HUMAN APPROVAL (in EOS, send to Discord, wait for thumbs-up)
if not approved: return

# 5. Commit
campaign_service.mutate_campaigns(customer_id=cid, operations=[op], validate_only=False)
```

### Recipe: Enhanced Conversion upload from CRM

```python
def hash_email(e): return hashlib.sha256(e.strip().lower().encode()).hexdigest()
def hash_phone(p):
    digits = "+" + re.sub(r"\D", "", p).lstrip("+")
    return hashlib.sha256(digits.encode()).hexdigest()

for lead in closed_won_since(checkpoint):
    click = client.get_type("ClickConversion")
    click.conversion_action = ca_path
    click.conversion_date_time = lead.closed_at.strftime("%Y-%m-%d %H:%M:%S+00:00")
    click.conversion_value = float(lead.contract_value)
    click.currency_code = "USD"
    if lead.gclid:
        click.gclid = lead.gclid
    if lead.email:
        uid = client.get_type("UserIdentifier")
        uid.hashed_email = hash_email(lead.email)
        click.user_identifiers.append(uid)
    if lead.phone:
        uid = client.get_type("UserIdentifier")
        uid.hashed_phone_number = hash_phone(lead.phone)
        click.user_identifiers.append(uid)
    conversions.append(click)

upload_svc.upload_click_conversions(
    customer_id=cid,
    conversions=conversions,
    partial_failure=True,
)
```

## Industry Expert and Cutting-Edge Usage

Patterns the top 1% of Google Ads API users employ:

- **Server-side GTM + Enhanced Conversions** — pipe every form fill
  through a server container that hashes PII before it ever touches
  Google Ads, then upload via API for the conversions GTM missed.
- **Incrementality testing via `experiment`** — programmatically run
  A/B tests on bid strategies, isolate causal lift.
- **Custom bidding columns** — since direct bid control on PMax is gone,
  the lever is *conversion value* — push your own ROAS estimates back
  via Enhanced Conversions to teach Smart Bidding what you actually
  care about. This is the highest-leverage move.
- **Negative keyword harvesting via search-term GAQL pulls** on a 6-hour
  loop, auto-staging negatives in shared sets for human approval.
- **Asset rotation by performance** — query
  `asset_group_top_combination_view`, demote LOW-rated assets, generate
  replacements with an LLM, validate-mutate to stage, human approves.
- **Pacing-aware budget reallocation** — query
  `campaign_budget.recommended_budget_amount_micros` and reallocate
  daily across a portfolio.
- **`change_event` as audit feed** — pipe into Neon for an immutable
  history of every change anyone (human or agent) made. Use for blame
  attribution and rollback.
- **Recommendation auto-apply with whitelist** — apply only specific
  `recommendation_type`s automatically (negative keywords, ad strength
  fixes); leave bid/budget recommendations to humans.
- **Multi-MCC traversal** — for agencies, set `login-customer-id` once
  per CID, not once per session, to keep the gRPC channel hot.

---

## EOS Usage Patterns

### Agent: Paid Acquisition Analyst (Initiate Arena)

Runs nightly. Pulls 7-day campaign performance via `searchStream`,
diffs against the previous night's snapshot in Neon, writes a Discord
summary highlighting:

- Campaigns where CPL climbed >25%
- Search terms with cost > $50 and 0 conversions (negative keyword
  candidates)
- Campaigns approaching daily budget cap before 4pm
- Disapproved ads or assets

Authority: read-only. All recommendations go to the founder for approval.

### Agent: Conversion Sync (CRM → Google Ads)

Runs hourly. Reads new closed-won deals from the CRM, hashes PII,
calls `ConversionUploadService.upload_click_conversions` with
`partial_failure=True`. Logs failures to Neon for inspection.

Authority: autonomous (uploads only, no campaign changes). Founder
gets a daily digest of upload counts.

### Agent: Campaign Drafter

On request, drafts a new search campaign structure (campaign + ad
groups + keywords + ads + budget) as a single bulk mutate using
negative temp IDs. Runs `validate_only=True` and dumps the diff to
Notion. Human reviews, approves, agent re-runs without
`validate_only`.

Authority: drafts only. Going live is always human-confirmed.

### Service module: `eos_ai/google_ads_client.py`

Single shared client factory:

```python
import os, sys, time
sys.path.insert(0, '/opt/OS')
from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

load_dotenv('/opt/OS/eos_ai/.env')

_CLIENT = None
def get_client():
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = GoogleAdsClient.load_from_env(version="v23")
    return _CLIENT

def safe_call(fn, *args, max_retries=5, **kwargs):
    delay = 1.0
    for attempt in range(max_retries):
        try:
            return fn(*args, **kwargs)
        except GoogleAdsException as ex:
            for err in ex.failure.errors:
                code = err.error_code
                if hasattr(code, 'quota_error'):
                    time.sleep(delay)
                    delay = min(delay * 2, 60)
                    break
            else:
                raise
    raise RuntimeError("max retries exceeded")
```

All EOS Google Ads code goes through this. No direct
`GoogleAdsClient(...)` calls anywhere else.

### Wiki entries

- `knowledge/integrations/google_ads_setup.md` — one-time OAuth and
  developer token bootstrapping
- `knowledge/runbooks/google_ads_v_bump.md` — version upgrade procedure
- `knowledge/runbooks/enhanced_conversions_for_leads.md` — CRM sync setup

## Gotchas

(Compounds over time as EOS encounters real failures. Seed entries
from research.)

- **`USER_PERMISSION_DENIED` with no detail** → 95% of the time you
  forgot `login-customer-id`. Set it from env on every call.
- **Customer IDs with dashes** are invalid in API calls but accepted
  in URLs and the UI. Strip them: `cid.replace("-", "")`.
- **Refresh token expired after 7 days** → your GCP OAuth consent
  screen is in Testing mode. Move it to Production verification.
- **`use_proto_plus=False`** changes message types. Every EOS code
  example assumes `True`. Set it explicitly in env.
- **Cost in micros** — multiplying by $1 instead of dividing by
  1,000,000 misreports spend by a factor of 10^12.
- **`metrics.conversions` is a float** that includes fractional
  attribution. Don't `int()` it.
- **`segments.date DURING LAST_7_DAYS`** is account-local time, not
  UTC. Cross-account aggregates require per-account TZ correction.
- **`partial_failure_error.details[0].value` is bytes** — must
  `ParseFromString` into `GoogleAdsFailure`.
- **Performance Max minimum asset requirements** must be met *in the
  same bulk mutate* as the AssetGroup. Splitting fails with a vague
  asset count error.
- **Enhanced Conversions silent 0% match** → unhashed input, or
  hashing the unnormalized string. Always lowercase + trim + strip
  formatting before SHA-256.
- **`RESOURCE_EXHAUSTED` doesn't mean you're at the daily cap** — it's
  more often the per-CID QPS bucket. Check `quotaErrorDetails.retryDelay`
  and back off; do not assume you're banned for the day.
- **`validate_only=True` consumes quota.** Drafts are not free.
- **Test access dev tokens cannot hit production accounts** — even
  read-only. The error is misleading ("authentication failed").
- **`mutate_campaigns` with no `update_mask`** silently ignores
  updates. Always set the mask for updates.
- **gRPC channel state breaks across `os.fork()`** — initialize the
  client *after* forking, never before.
- **Deprecated v17/v18 still have SDK constants** — pin
  `version="v23"` explicitly or you may pick up an old default.
- **`search_term_view`** is a separate resource from `keyword_view`.
  Confusing them returns surprising counts.
- **CRITICAL: spend mutates require human approval.** No agent goes to
  ENABLED, no agent raises a budget, no agent changes a tROAS without
  the founder confirming. Codify this in the authority engine.
