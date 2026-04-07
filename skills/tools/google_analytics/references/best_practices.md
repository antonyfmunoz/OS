# google_analytics — Creator-Level Best Practices
Source: developers.google.com/analytics, googleapis.dev/python/analyticsdata, googleapis.dev/python/analyticsadmin, BigQuery export docs, Measurement Protocol v2 reference
API Version: Data API v1beta, Admin API v1beta (v1alpha still live), Measurement Protocol v2
SDK Version: google-analytics-data 0.18.x, google-analytics-admin 0.22.x (Python), gRPC default transport
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## Authentication

Three valid auth modes against the GA4 surface area. EOS uses one.

### 1. Service account (EOS standard)

Server-to-server. Long-lived JSON key file. The key holds an RSA private key
and a `client_email`. To call the Data or Admin API:

1. GCP Console → APIs & Services → enable **Google Analytics Data API** and
   **Google Analytics Admin API** on the project
2. IAM & Admin → Service Accounts → Create
3. Keys tab → Add Key → JSON → download
4. **GA4 property side** (the step everyone forgets): GA4 → Admin →
   Property Access Management → Add → paste the service account email
   (`name@project.iam.gserviceaccount.com`) → Viewer role minimum
5. Optional: also add to **Account Access Management** if you'll use Admin API
   to enumerate accounts

Code:

```python
from google.oauth2 import service_account
from google.analytics.data_v1beta import BetaAnalyticsDataClient

SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]

creds = service_account.Credentials.from_service_account_file(
    "/opt/OS/eos_ai/.secrets/ga4-sa.json", scopes=SCOPES,
)
client = BetaAnalyticsDataClient(credentials=creds)
```

Or via env var (`GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json`) and
zero-arg construction:

```python
client = BetaAnalyticsDataClient()  # ADC picks up the env var
```

EOS preference: explicit `from_service_account_file`. ADC is too magical for
multi-tenant code where we may need different credentials per call.

### 2. OAuth 2.0 user (NOT used by EOS)

Three-legged consent flow. Required only if your code must act as a specific
human user — e.g. reading a property the founder owns personally and refuses
to share to a service account. Returns a refresh token you store and trade
for short-lived access tokens. Avoid in EOS. Reasons:

- Refresh tokens silently expire after 6 months of inactivity
- Refresh tokens can be revoked by the user from myaccount.google.com
- The consent screen needs a verified GCP project (slow approval)

### 3. Application Default Credentials (ADC)

Reads, in order: `GOOGLE_APPLICATION_CREDENTIALS` env var → `gcloud auth
application-default login` cache → GCE/GKE metadata server. Works fine on
the VPS if you set the env var. Just be explicit about which mode you're in
or you'll debug "auth works locally fails on VPS" forever.

### 4. Measurement Protocol secret

Different model entirely. Per-data-stream HMAC-style secret. Created in
GA4 Admin → Data Streams → choose stream → Measurement Protocol API secrets
→ Create. Returns a 24-character secret. Sent as query string to
`https://www.google-analytics.com/mp/collect`. Treat exactly like an API
key — anyone with the (measurement_id, api_secret) pair can write events to
your property and pollute your data forever. EOS stores in `.env` as
`GA4_MP_SECRET_<PROPERTY_NICKNAME>`.

### Required scopes

| Surface | Scope |
|---|---|
| Data API (read) | `https://www.googleapis.com/auth/analytics.readonly` |
| Data API (full) | `https://www.googleapis.com/auth/analytics` |
| Admin API (read) | `https://www.googleapis.com/auth/analytics.readonly` |
| Admin API (manage users) | `https://www.googleapis.com/auth/analytics.manage.users` |
| Admin API (edit) | `https://www.googleapis.com/auth/analytics.edit` |

EOS uses `analytics.readonly` only.

## Core Operations with Exact Signatures

All operations live under `google.analytics.data_v1beta` (Data API) or
`google.analytics.admin_v1beta` (Admin API). The Python SDK is auto-generated
from protobuf and exposes both client objects and `*_pb2` request/response
types.

### Data API methods

```
client.run_report(request: RunReportRequest) -> RunReportResponse
client.batch_run_reports(request: BatchRunReportsRequest) -> BatchRunReportsResponse
client.run_pivot_report(request: RunPivotReportRequest) -> RunPivotReportResponse
client.batch_run_pivot_reports(request: BatchRunPivotReportsRequest) -> BatchRunPivotReportsResponse
client.run_realtime_report(request: RunRealtimeReportRequest) -> RunRealtimeReportResponse
client.get_metadata(name: str) -> Metadata
client.check_compatibility(request: CheckCompatibilityRequest) -> CheckCompatibilityResponse
client.create_audience_export(...)  # async LRO
client.query_audience_export(...)
client.list_audience_exports(...)
```

`RunReportRequest` fields (all optional unless noted):

```
property               str   "properties/123456789"  REQUIRED
dimensions             list[Dimension]
metrics                list[Metric]                  REQUIRED
date_ranges            list[DateRange]
dimension_filter       FilterExpression
metric_filter          FilterExpression
offset                 int   for pagination
limit                  int   max 250000 (default 10000)
metric_aggregations    list[MetricAggregation]  TOTAL/MAXIMUM/MINIMUM/COUNT
order_bys              list[OrderBy]
currency_code          str   ISO 4217, default property currency
cohort_spec            CohortSpec
keep_empty_rows        bool  default false
return_property_quota  bool  default false  ALWAYS TRUE IN EOS
comparisons            list[Comparison]
```

`Dimension`:
```
name                   str   e.g. "sessionSource", "pagePath"
dimension_expression   DimensionExpression  for derived dims (concat/lower)
```

`Metric`:
```
name                   str   e.g. "sessions", "totalRevenue"
expression             str   inline math: "sessions/users"
invisible              bool  use in filter only, don't return
```

### Admin API methods (read-only subset EOS uses)

```
admin.list_account_summaries() -> pages of AccountSummary
admin.list_accounts() -> pages of Account
admin.get_property(name="properties/123") -> Property
admin.list_properties(filter="parent:accounts/456") -> pages
admin.list_data_streams(parent="properties/123") -> pages of DataStream
admin.list_conversion_events(parent="properties/123") -> pages
admin.list_custom_dimensions(parent="properties/123") -> pages
admin.list_custom_metrics(parent="properties/123") -> pages
admin.list_measurement_protocol_secrets(parent="properties/123/dataStreams/456") -> pages
```

### Measurement Protocol v2

POST to `https://www.google-analytics.com/mp/collect?api_secret=...&measurement_id=G-...`.
Validation endpoint: `https://www.google-analytics.com/debug/mp/collect`.

Body schema:
```
{
  "client_id":       "string",        REQUIRED for web measurement
  "user_id":         "string",
  "timestamp_micros": 0,
  "user_properties": {...},
  "consent":         {"ad_user_data": "GRANTED", "ad_personalization": "GRANTED"},
  "events": [
    {"name": "event_name", "params": {...}}    max 25 events per request
  ]
}
```

Per-event constraints: name max 40 chars, params max 25, param key max 40,
param value max 100, alphanumeric + underscore only in names.

## Pagination Patterns

GA4 Data API caps `limit` at 250,000 rows per call. For larger result sets
use `offset`:

```python
def paginate(client, base_req, page_size=100000):
    rows = []
    offset = 0
    while True:
        req = copy.deepcopy(base_req)
        req.limit = page_size
        req.offset = offset
        resp = client.run_report(req)
        rows.extend(resp.rows)
        if len(resp.rows) < page_size or offset + page_size >= resp.row_count:
            break
        offset += page_size
    return rows
```

`row_count` on the response gives total matching rows BEFORE the limit was
applied. Use it to decide whether to keep paging.

Admin API uses Google's standard `page_token` / `next_page_token` model and
the SDK exposes it as a Python iterator — just `for item in admin.list_x(...)`
and pagination is automatic.

BigQuery export has no pagination — it's SQL.

## Rate Limits

GA4 Data API uses a **token bucket** model with five separate buckets per
property. All five are checked on every request; exhausting any one returns
`429 RESOURCE_EXHAUSTED`.

Standard property quotas (as of 2026-04):

| Bucket | Limit | Refresh |
|---|---|---|
| Tokens per property per hour | 200,000 | hourly |
| Tokens per project per property per hour | 14,000 | hourly |
| Tokens per property per day | 200,000 | daily |
| Concurrent requests per property | 10 | instant |
| Server errors per project per property per hour | 50 | hourly |

GA360 properties get roughly 5x these limits.

Token cost per request varies by complexity (number of dimensions × cardinality
× date range × number of metrics). A simple 1-dim, 1-metric, 7-day report
costs ~10 tokens. A 5-dim, 5-metric, 90-day report can cost 1000+. Always
introspect actual cost via `return_property_quota=True`:

```python
resp = client.run_report(req)
q = resp.property_quota
print(f"Tokens/hour {q.tokens_per_hour.consumed}/{q.tokens_per_hour.remaining}")
print(f"Tokens/project/hour {q.tokens_per_project_per_hour.consumed}/{q.tokens_per_project_per_hour.remaining}")
print(f"Concurrent {q.concurrent_requests.consumed}/{q.concurrent_requests.remaining}")
```

Realtime reports have a separate quota: 10,000 tokens/hour, 10 concurrent.

Measurement Protocol: no documented hard quota but a soft cap around 1
request/second per (measurement_id, client_id). Batch up to 25 events per
request to amortize.

Admin API: 1,200 requests per minute per project. Generous, never the binding
constraint in EOS.

## Error Codes and Recovery

| Code | gRPC Status | Meaning | Recovery |
|---|---|---|---|
| 400 | INVALID_ARGUMENT | Bad dimension/metric name, incompatible combo, malformed filter | Fix request, do not retry |
| 401 | UNAUTHENTICATED | Token expired or invalid SA key | Refresh credentials |
| 403 | PERMISSION_DENIED | SA not added to GA4 property, or wrong scope | Add SA as Viewer in GA4 Admin, do not retry |
| 404 | NOT_FOUND | Property/account doesn't exist or you can't see it | Verify ID format `properties/N` |
| 429 | RESOURCE_EXHAUSTED | Quota bucket empty | Backoff with jitter; respect `Retry-After` if present |
| 500 | INTERNAL | Google-side transient | Exponential backoff up to 5 retries |
| 503 | UNAVAILABLE | gRPC channel issue | Retry with backoff; consider `transport="rest"` |
| 504 | DEADLINE_EXCEEDED | Query too expensive | Reduce date range or dimensions |

Recovery pattern (EOS canonical):

```python
import time, random
from google.api_core import exceptions as gax

def call_with_retry(fn, *args, max_retries=5):
    delay = 1.0
    for attempt in range(max_retries):
        try:
            return fn(*args)
        except gax.ResourceExhausted as e:
            if attempt == max_retries - 1:
                raise
            sleep = delay * (2 ** attempt) + random.random()
            time.sleep(sleep)
        except (gax.InternalServerError, gax.ServiceUnavailable):
            time.sleep(delay * (2 ** attempt))
        except (gax.InvalidArgument, gax.PermissionDenied, gax.NotFound):
            raise  # never retry these
```

`PERMISSION_DENIED` is the #1 GA4 error in production and is NEVER fixed by
retry. Surface it loudly to the operator with the exact SA email so they
know what to add to GA4.

## SDK Idioms

### Property ID always wrapped

```python
PROPERTY = f"properties/{numeric_id}"  # never bare integer
```

### Date ranges accept both relative and absolute

```python
DateRange(start_date="7daysAgo", end_date="yesterday")
DateRange(start_date="2026-04-01", end_date="2026-04-06")
DateRange(start_date="30daysAgo", end_date="today", name="last_30")
```

Multiple `date_ranges` produce side-by-side comparison columns.

### Filter expressions

```python
from google.analytics.data_v1beta.types import (
    Filter, FilterExpression, FilterExpressionList,
)

# Single condition: pagePath starts with /arena/
filt = FilterExpression(filter=Filter(
    field_name="pagePath",
    string_filter=Filter.StringFilter(
        match_type=Filter.StringFilter.MatchType.BEGINS_WITH,
        value="/arena/",
    ),
))

# AND of two: pagePath starts with /arena/ AND deviceCategory == mobile
filt = FilterExpression(and_group=FilterExpressionList(expressions=[
    FilterExpression(filter=Filter(
        field_name="pagePath",
        string_filter=Filter.StringFilter(
            match_type=Filter.StringFilter.MatchType.BEGINS_WITH,
            value="/arena/"))),
    FilterExpression(filter=Filter(
        field_name="deviceCategory",
        string_filter=Filter.StringFilter(value="mobile"))),
]))

req = RunReportRequest(..., dimension_filter=filt)
```

`metric_filter` uses the same shape but with `Filter.NumericFilter` /
`Filter.BetweenFilter`.

### Order by

```python
from google.analytics.data_v1beta.types import OrderBy
req.order_bys = [
    OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True),
]
```

### Inline metric expressions

```python
Metric(name="conv_rate", expression="conversions/sessions")
```

The expression metric appears in the response under the `name` you give it.

### Dimension expressions

```python
Dimension(name="lower_path",
          dimension_expression=DimensionExpression(
              lower_case=DimensionExpression.CaseExpression(
                  dimension_name="pagePath")))
```

Useful when GA4 stores the same path with different casing and you need
collapse before grouping.

### Async / parallel calls

The Python SDK is sync-by-default but ships async clients under
`google.analytics.data_v1beta.BetaAnalyticsDataAsyncClient`. EOS prefers a
`ThreadPoolExecutor(max_workers=5)` since the gRPC channel is thread-safe and
we want to respect the 10-concurrent limit.

## Anti-Patterns

- **Hardcoding property IDs in eos_ai/ modules** — they belong in BIS.
- **Looping single-day reports for a 30-day window** — request the whole
  range in one call. 30x quota waste otherwise.
- **Calling `runReport` for data you'll re-derive** — query Neon
  `analytics.ga4_daily` first, fall through to API only on miss.
- **Re-instantiating `BetaAnalyticsDataClient` per call** — the gRPC channel
  setup is ~200ms. Keep one client per process.
- **Calling Data API for raw event lookup** — use BigQuery export. The Data
  API is for aggregated dashboards, not transactional event retrieval.
- **Sending PII through Measurement Protocol** — GA4 will silently scrub or
  ban your property. Hash everything client-side.
- **Polling realtime every 5s during a launch** — 10k token/hour realtime
  bucket exhausts in 30 minutes. 60s polling is the floor.
- **Using `v1alpha` Admin API by accident** — newer SDK versions default to
  v1beta but the alpha module still exists. Always import the explicit
  version.
- **Treating `(other)` as a real source** — it's a high-cardinality bucket.
  Aggregations over it are meaningless.
- **Trusting `events_intraday` for revenue** — `traffic_source` and
  `user_ltv` aren't populated until the daily table writes.

## Data Model

GA4 is fully event-based. Every interaction is an event with up to 25 custom
parameters. Reserved/recommended events: `page_view`, `session_start`,
`first_visit`, `user_engagement`, `scroll`, `click`, `view_item`,
`add_to_cart`, `begin_checkout`, `purchase`, `generate_lead`, `sign_up`,
`login`. Custom events are anything else with a name you choose.

Hierarchy:

```
Account
  └── Property (the unit of API access)
        ├── Data Stream (web | iOS | Android)   one per platform
        │     └── Measurement Protocol Secrets
        ├── Custom Dimensions   (event-scoped, user-scoped, item-scoped)
        ├── Custom Metrics      (event-scoped only)
        ├── Conversion Events   (any event marked as conversion)
        ├── Audiences
        └── BigQuery Linked Project
```

**Scope matters**. Dimensions have scope (event, session, user) and metrics
have scope (event, user). Mixing scopes in one report can cause
`INVALID_ARGUMENT` or surprising aggregations. Use `checkCompatibility`
during development to validate combinations.

### Dimensions catalog (most-used in EOS)

| Name | Scope | Example |
|---|---|---|
| `date` | event | "20260406" |
| `pagePath` | event | "/arena/onboarding" |
| `pageTitle` | event | "Initiate Arena" |
| `deviceCategory` | session | "mobile" |
| `country` | session | "United States" |
| `sessionSource` | session | "google" |
| `sessionMedium` | session | "cpc" |
| `sessionCampaignName` | session | "arena_q2_launch" |
| `landingPage` | session | "/" |
| `eventName` | event | "purchase" |
| `firstUserSource` | user | "instagram" |
| `unifiedScreenName` | event | (realtime only) |

### Metrics catalog (most-used in EOS)

| Name | Scope | Notes |
|---|---|---|
| `sessions` | session | |
| `activeUsers` | user | the GA4 default "users" |
| `newUsers` | user | |
| `engagedSessions` | session | |
| `engagementRate` | session | engagedSessions / sessions |
| `averageSessionDuration` | session | |
| `screenPageViews` | event | |
| `eventCount` | event | |
| `conversions` | event | filter by `eventName` |
| `purchaseRevenue` | event | from purchase events only |
| `totalRevenue` | event | purchase + ad + subscription |
| `userEngagementDuration` | user | |

Full catalog at developers.google.com/analytics/devguides/reporting/data/v1/api-schema.

### Cardinality and `(other)`

Each dimension has a 50,000 unique-value cap per day per property. Past that,
GA4 collapses additional values into `(other)` to keep aggregated tables
fast. High-cardinality dimensions to watch:

- `pagePath` on sites with query strings or session IDs in URLs
- Any custom dimension that captures user IDs or transaction IDs
- `sessionCampaignName` on accounts that auto-tag heavily

Mitigation: pre-process URLs to strip query strings before they hit GA4
(via Tag Manager or gtag config), or accept the loss and query BigQuery for
the long tail.

## Webhooks and Events

**N/A — GA4 has no native webhook surface.** There is no callback URL you
register for "fire on every conversion". The closest equivalents:

1. **BigQuery streaming export + scheduled query** — events land in
   `events_intraday_YYYYMMDD` within seconds. A BigQuery scheduled query
   running every minute can pull new rows and write them to a Pub/Sub topic
   that EOS subscribes to.
2. **Polling `runRealtimeReport`** — every 60s, diff against the previous
   pull, trigger downstream actions on new conversions. Simpler but cruder.
3. **Tag Manager dual-fire** — configure GTM to fire both a GA4 tag AND a
   custom HTTP tag pointing at an EOS webhook. Bypasses GA4 entirely on the
   notification path; GA4 just gets the analytics copy. This is the EOS
   preferred pattern for true real-time conversion notifications.

EOS does not currently use any of the three. Planned: option 3 for the
Initiate Arena checkout completion event when first paid traffic starts.

## Limits

| Surface | Limit |
|---|---|
| Data API rows per response | 250,000 |
| Data API dimensions per request | 9 |
| Data API metrics per request | 10 |
| Data API date ranges per request | 4 |
| Data API batch reports per request | 5 |
| Data API max date range | 14 months (older data dropped on standard properties) |
| Admin API custom dimensions per property | 50 |
| Admin API custom metrics per property | 50 |
| Admin API conversion events per property | 30 |
| Measurement Protocol events per request | 25 |
| Measurement Protocol params per event | 25 |
| Measurement Protocol param value length | 100 chars |
| BigQuery daily export events/day (standard) | 1,000,000 |
| BigQuery streaming export | unlimited |
| Property data retention (standard) | 14 months |
| Property data retention (360) | 50 months |
| Cardinality cap per dimension per day | 50,000 unique values |
| Sampling threshold (Explore/raw) | 10M events for the date range |

## Cost Model

Data API and Admin API: **free**. No per-call charge. The constraint is
quota, not money.

Measurement Protocol: **free**.

BigQuery export: **free** for the export itself, **paid** for storage and
queries against the exported tables. Standard BQ pricing — ~$0.02/GB/month
storage, ~$5/TB scanned for on-demand queries. For Initiate Arena scale (sub
1M events/day) the monthly bill is < $5.

GA4 itself: **free** (standard). GA360: $150k+/year, irrelevant for EOS.

The real cost is ENGINEER TIME spent debugging quota errors and permission
issues. Build the wrapper right once and never touch it again.

## Version Pinning

Pin in `requirements.txt`:

```
google-analytics-data==0.18.18
google-analytics-admin==0.22.10
google-auth==2.39.0
```

The Admin SDK exposes both `admin_v1alpha` and `admin_v1beta` modules. Always
import the explicit version:

```python
from google.analytics.admin_v1beta import AnalyticsAdminServiceClient
# NOT: from google.analytics.admin import AnalyticsAdminServiceClient
```

The Data API only ships v1beta (v1alpha was retired in 2023). Import:

```python
from google.analytics.data_v1beta import BetaAnalyticsDataClient
```

The class is literally named `BetaAnalyticsDataClient` with the `Beta`
prefix even though v1beta is the current GA-stable surface. Confusing but
correct.

API versioning policy: `v1beta` is supported with the same SLA as a GA
release. Google has stated v1beta will not be deprecated until v1 ships and
a 12-month migration window passes. Safe to depend on.

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

GA4 was designed to replace Universal Analytics with a fully event-based
model that works equally well for web and mobile (via Firebase). Key design
choices and their tradeoffs:

**Event-based (not pageview-based)**. Everything is an event including
`page_view`. This unifies web/app analytics but breaks every UA report and
every mental model built around sessions and pageviews. The migration pain
is real and ongoing.

**No views/segments at the data layer**. UA had Views (filtered slices of
property data). GA4 deleted them. You filter at query time instead. Simpler
architecture, but you can't accidentally lock yourself into a broken View
forever.

**Aggregated tables for speed, raw tables for power**. The two-tier model
trades flexibility for performance. Most queries hit the aggregated tier and
are fast. Power-user queries fall through and get sampled. The Data API
hides this from you, which is friendly until you hit `(other)` and don't
know why.

**BigQuery export free for everyone**. UA gated raw event export behind
GA360 ($150k/year). GA4 ships it free. This is the single biggest GA4
improvement and the reason serious analytics teams tolerate the migration.

**Cardinality cap at 50k**. Trades data fidelity for query speed. Acceptable
on consumer sites, painful for B2B with long-tail account names.

**Quota in tokens not requests**. More accurate cost accounting (a 5-dim
report costs more than a 1-dim one) but harder to predict. The
`returnPropertyQuota` introspection is the only sane way to budget.

**Measurement Protocol returns 204 even on bad data**. Designed for
fire-and-forget reliability; you never want a tag manager hit to throw on
the user's browser. But it makes server-side debugging miserable.

## Problem-Solution Map and Hidden Capabilities

| Problem | Solution |
|---|---|
| "What's my conversion rate by source for the last 7 days?" | `runReport` with `sessionSource` dim, `conversions/sessions` expression metric |
| "Are people on the new landing page right now?" | `runRealtimeReport` with `unifiedScreenName` dim, `activeUsers` metric |
| "I need event-level data for ML training" | BigQuery export, query `events_*` |
| "Compare this week vs last week" | Two `DateRange`s on the same `RunReportRequest` |
| "Find pages where mobile bounces but desktop converts" | `runPivotReport` with deviceCategory pivot, pagePath rows |
| "Will these dimensions and metrics work together?" | `checkCompatibility` before running the actual report |
| "Show only US visitors who saw at least 3 pages" | `dimensionFilter` on country + `metricFilter` on screenPageViews >= 3 |
| "Server fired an event but it's not showing in GA" | Hit `/debug/mp/collect` with the same payload, read the validation messages |
| "I changed a custom dimension and old data looks wrong" | Custom dimensions are NOT retroactive. Reprocessing only happens forward. |

### Hidden capabilities most users miss

- **`checkCompatibility`** — pre-flight check that returns which
  dimensions/metrics are compatible with your current request. Saves a round
  trip and a confusing error.
- **`metricAggregations`** — set to `[TOTAL, MAXIMUM, MINIMUM]` to get
  summary rows in the same response. Avoids a second call.
- **Cohort reports** — `cohortSpec` gives you retention curves natively. No
  need to build them in BigQuery.
- **Comparisons** — `comparisons` field enables side-by-side filtered slices
  in a single report (the API equivalent of GA4 UI Comparisons).
- **`keep_empty_rows`** — return zero-value rows for completeness in
  time-series. Default false.
- **Audience exports** — async LRO that exports an entire audience definition
  to a queryable table. Takes minutes; useful for activation pipelines.
- **`debug_view` events** — hit Measurement Protocol with `?debug_mode=1`
  and the events appear in GA4 → Admin → DebugView in real time.

## Operational Behavior and Edge Cases

### Latency

- **Realtime API**: 30-60 second delay from event firing to availability
- **Standard reports**: 4-24 hours for complete data; partial data appears
  within 1-2 hours
- **Conversion attribution**: up to 48 hours for cross-channel attribution
  to settle (the conversion shows up immediately, but the attributed source
  may shift)
- **BigQuery daily export**: typically arrives 4-12 hours after midnight in
  the property's timezone
- **BigQuery streaming export**: events land within seconds

### Data revisions

GA4 reprocesses data for ~72 hours after collection. Numbers for "yesterday"
queried at 6am may differ from the same query at 6pm. EOS pattern: never
query yesterday before 6am local; cache the 6am result for the rest of the
day.

### Sampling

Standard reports never sample. Explore-style queries (multi-dim, custom
funnels, segments) sample at 10M events for the date range on standard
properties. The Data API picks the layer for you — when you fall through,
the response includes a `metadata.data_loss_from_other_row` flag.

### Bot filtering

GA4 auto-applies the IAB/ABC International Spiders & Bots List. Cannot be
disabled. Adds variability to small-traffic sites — a single misclassified
crawler can move "real users" by 10%.

### Consent mode

If your site uses Google Consent Mode v2 (required in EU), GA4 may receive
"cookieless pings" that are modeled rather than measured. The Data API
exposes these via the `googleSignalsAdsClicks` family of metrics. EOS
ignores this — Initiate Arena traffic is US-primary.

### Time zones

A property has ONE timezone set at creation. All `date` dimensions are in
that timezone. Cannot be changed without losing data continuity. Set it to
the founder's actual timezone (America/Los_Angeles for EOS) at property
creation and never touch it.

## Ecosystem Position and Composition

GA4 sits at the top of the web-measurement stack:

```
Browser
  └── gtag.js / Google Tag Manager
        └── GA4 collection endpoint
              └── GA4 property (aggregated tables)
                    ├── Data API ← EOS reads here
                    ├── Admin API ← EOS reads here
                    └── BigQuery Export ← EOS may add later
```

Adjacent / competing tools:

- **Plausible / Fathom / Simple Analytics** — privacy-first lightweight
  alternatives. No event API, no BigQuery export, no funnels. Wrong tool for
  EOS.
- **Mixpanel / Amplitude** — product analytics, deeper event modeling, no
  free tier worth using at our volume. Better for in-app behavior tracking.
- **PostHog** — open-source Mixpanel alternative. Already in EOS for product
  analytics on the SaaS side. PostHog and GA4 coexist: PostHog for product,
  GA4 for marketing/SEO.
- **Looker Studio** — Google's BI layer on top of GA4. Free dashboarding.
  EOS does not use it because we want agent-driven brief generation, not
  human dashboards.

EOS composition pattern:

```
GA4 Data API ──┐
                ├── eos_ai/ga4_client.py ──┐
PostHog API ───┘                             ├── world_pulse.py ──┐
                                             │                       │
Apify scrapers ──── eos_ai/scraper.py ───────┘                       │
                                                                       │
                                              morning_prep.sh ←───────┘
                                                    ↓
                                              CEO agent brief
```

## Trajectory and Evolution

GA4 launched October 2020, became default July 2023 when UA was retired.
v1beta of the Data API stabilized in 2022. Recent and pending changes:

- **Tokens-per-property-per-hour quota raised from 1,250 → 14,000** in late
  2023 after the Looker Studio quota apocalypse
- **`v1beta` Admin API** stabilized in 2024; `v1alpha` still ships with
  experimental endpoints
- **Subproperties** (account-level slicing) GA in late 2024
- **Roll-up properties** for multi-brand consolidation, GA in 2025
- **Consent Mode v2** mandatory in EU since March 2024
- **AI insights API** in private preview as of late 2025 — natural-language
  query against your GA4 data, would be a strong fit for EOS agents but not
  yet GA
- **Universal Analytics fully sunset** July 2024 — historic UA data only
  accessible via BigQuery export from before the sunset

Pending (rumored, unconfirmed):
- Server-side conversion APIs (deeper than Measurement Protocol)
- Native webhook delivery for conversion events
- Predictive metrics in the Data API beyond `purchaseProbability`

EOS posture: depend on v1beta. Don't build on v1alpha endpoints. Watch the
AI insights API release notes — when it goes GA, route morning brief
queries through it.

## Conceptual Model and Solution Recipes

### Core mental model

**A GA4 property is a write-once event log with two read views.** The log
is the BigQuery export. The read views are the aggregated tables (fast,
limited) and the raw tables (slow, complete). The Data API is a query
language over the read views; BigQuery is SQL over the log.

If you want speed → API. If you want fidelity → BigQuery. If you want both
→ build a Neon cache layer that pulls from the API daily and falls back to
BigQuery on cache miss. EOS does the first two and may add the third.

### Recipe: Daily funnel for a landing page

```python
def landing_page_funnel(property_id: str, page_path: str, days: int = 7):
    base = {
        "property": f"properties/{property_id}",
        "date_ranges": [DateRange(start_date=f"{days}daysAgo", end_date="yesterday")],
        "dimension_filter": FilterExpression(filter=Filter(
            field_name="landingPage",
            string_filter=Filter.StringFilter(value=page_path),
        )),
        "return_property_quota": True,
    }
    funnel_events = [
        ("page_view", "Visited"),
        ("scroll", "Scrolled"),
        ("click", "Clicked CTA"),
        ("begin_checkout", "Started checkout"),
        ("purchase", "Purchased"),
    ]
    results = {}
    for event_name, label in funnel_events:
        req = RunReportRequest(
            **base,
            metrics=[Metric(name="eventCount")],
            dimension_filter=FilterExpression(and_group=FilterExpressionList(expressions=[
                base["dimension_filter"],
                FilterExpression(filter=Filter(
                    field_name="eventName",
                    string_filter=Filter.StringFilter(value=event_name))),
            ])),
        )
        resp = client.run_report(req)
        results[label] = int(resp.rows[0].metric_values[0].value) if resp.rows else 0
    return results
```

### Recipe: Realtime pulse for launch day

```python
def realtime_pulse(property_id: str):
    req = RunRealtimeReportRequest(
        property=f"properties/{property_id}",
        dimensions=[Dimension(name="country"), Dimension(name="unifiedScreenName")],
        metrics=[Metric(name="activeUsers")],
        return_property_quota=True,
    )
    return client.run_realtime_report(req)
```

Poll every 60s, write to Neon `realtime_pulse` table, alert when
`activeUsers` drops to zero for two consecutive polls during a launch
window.

### Recipe: Quota-safe daily morning brief query

```python
def morning_brief_metrics(property_id: str):
    metrics = [
        Metric(name="sessions"),
        Metric(name="activeUsers"),
        Metric(name="conversions"),
        Metric(name="totalRevenue"),
        Metric(name="engagementRate"),
    ]
    req = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[Dimension(name="date")],
        metrics=metrics,
        date_ranges=[DateRange(start_date="8daysAgo", end_date="yesterday")],
        return_property_quota=True,
    )
    return client.run_report(req)
```

One call per property per day → ~50 tokens × 4 properties × 1 call = 200
tokens/day. Negligible against the 14k/hour budget.

## Industry Expert and Cutting-Edge Usage

What sophisticated GA4 teams do that hobbyists don't:

- **Pre-process URLs in Tag Manager** to strip query strings, lowercase,
  and collapse paginated paths. Prevents cardinality blowups before they
  hit the property.
- **Always enable BigQuery export from day 1** even if you don't use it.
  Storage is cheap; you cannot retroactively get raw events for a period
  before export was enabled.
- **Build a Neon (or equivalent) cache layer** between the Data API and
  agent code. API for cache misses, cache for everything else. Cuts quota
  burn 100x.
- **Use `checkCompatibility` in CI** for any new report definition. Catches
  scope mismatches at PR time, not in production.
- **Tag conversions with `currency` even if you only sell in one currency**.
  Future-proofs international expansion and unlocks `purchaseRevenue` math.
- **Set property timezone to match the founder's calendar**, not UTC. Every
  date dimension reads in property time; UTC adds mental overhead forever.
- **Send a `client_id` derived from a stable hash for Measurement Protocol
  events**. Random per-call client_ids fragment your user model and inflate
  user counts.
- **Run `runReport` with `returnPropertyQuota=True` and log the consumed
  cost** to a metrics table. After a week you have empirical token costs
  per query type and can budget intelligently.
- **Use batch reports aggressively**. Five reports in one HTTP call is
  cheaper than five sequential calls and respects concurrent-request limits.
- **For high-stakes launches, dual-track**: GA4 for the funnel + Plausible
  for a sanity check. GA4's bot filtering and modeling can swing numbers
  10%; Plausible gives a clean second opinion.

## EOS Usage Patterns

Concrete EOS-specific patterns. These are the load-bearing recipes for the
current build phase.

### Pattern 1: ga4_client.py wrapper

A single module under `eos_ai/` that holds the client, the retry logic, the
quota budget, and the property catalog (loaded from BIS). Every other
module imports from this wrapper, never directly from `google.analytics`.

```python
# eos_ai/ga4_client.py
import os, time, random
from functools import lru_cache
from google.oauth2 import service_account
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest, RunRealtimeReportRequest,
    Dimension, Metric, DateRange,
)
from google.api_core import exceptions as gax

SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]

@lru_cache(maxsize=1)
def _client():
    creds = service_account.Credentials.from_service_account_file(
        os.environ["GA4_SA_KEY_PATH"], scopes=SCOPES,
    )
    return BetaAnalyticsDataClient(credentials=creds)

def run_report(property_id: str, dimensions, metrics,
               start="7daysAgo", end="yesterday", **kw):
    req = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[Dimension(name=d) for d in dimensions],
        metrics=[Metric(name=m) for m in metrics],
        date_ranges=[DateRange(start_date=start, end_date=end)],
        return_property_quota=True,
        **kw,
    )
    return _retry(lambda: _client().run_report(req))

def _retry(fn, max_retries=5):
    delay = 1.0
    for attempt in range(max_retries):
        try:
            return fn()
        except gax.ResourceExhausted:
            if attempt == max_retries - 1: raise
            time.sleep(delay * 2**attempt + random.random())
        except (gax.InternalServerError, gax.ServiceUnavailable):
            time.sleep(delay * 2**attempt)
        except (gax.InvalidArgument, gax.PermissionDenied, gax.NotFound):
            raise
```

### Pattern 2: Daily snapshot to Neon

`scripts/scheduled/morning_prep.sh` calls a Python entry that pulls
yesterday's totals for every BIS-registered property and writes to
`analytics.ga4_daily`. Subsequent agent calls hit Neon, not the API.

```python
# scripts/ga4_snapshot.py
from eos_ai.business_instance import bis
from eos_ai.ga4_client import run_report
from eos_ai.db import write_row

for nickname, prop_id in bis.get("ga4_property_ids").items():
    resp = run_report(
        prop_id,
        dimensions=["date", "sessionSource"],
        metrics=["sessions", "activeUsers", "conversions", "totalRevenue"],
        start="yesterday", end="yesterday",
    )
    for row in resp.rows:
        write_row("analytics.ga4_daily", {
            "property": nickname,
            "date": row.dimension_values[0].value,
            "source": row.dimension_values[1].value,
            "sessions": int(row.metric_values[0].value),
            "active_users": int(row.metric_values[1].value),
            "conversions": float(row.metric_values[2].value),
            "revenue": float(row.metric_values[3].value),
        })
    print(f"{nickname}: quota left {resp.property_quota.tokens_per_hour.remaining}")
```

### Pattern 3: CEO agent funnel question

When a CEO agent asks "where are people dropping off on the Initiate Arena
landing page", `world_pulse.py` calls the funnel recipe above and returns a
structured drop-off report with absolute numbers and percentages. The agent
formats it into the morning brief.

### Pattern 4: Realtime watch during outreach pushes

During a manual outreach blast, `scripts/realtime_watch.py` polls
`runRealtimeReport` every 60s and pings the Discord ops channel if
activeUsers exceeds 50 (real spike) or drops to 0 for two consecutive polls
(infra failure). Started/stopped manually.

### Pattern 5: Property registration in BIS

`bis.set("ga4_property_ids", {...})` is the only place GA4 property IDs live.
Format:

```json
{
  "ga4_property_ids": {
    "initiate_arena": "123456789",
    "lyfe_spectrum":  "234567890",
    "empyrean_studio": "345678901",
    "afm_personal":   "456789012"
  }
}
```

`bis.set("ga4_measurement_ids", {...})` for the `G-XXXXXXX` form used by
Measurement Protocol. Service account JSON path in `eos_ai/.env` as
`GA4_SA_KEY_PATH`.

## Gotchas

The full failure catalog. Hard-won.

- **`PERMISSION_DENIED` after correct GCP setup** — service account is on
  the project but not on the GA4 property. Fix: GA4 Admin → Property Access
  Management → add SA email as Viewer. The error message does NOT tell you
  this; it just says "User does not have sufficient permissions for this
  property."
- **`returnPropertyQuota` is false by default** — you'll burn the budget
  blind. Always set true in EOS code. Cost is ~0.
- **Quota refresh is hourly, not rolling** — being at 95% at 10:55 means
  you have 5 minutes of pain then a full reset at 11:00. Don't panic-pause
  your job; check if you're 60 seconds from a refresh.
- **Quota counts even for empty/error responses** — a 400 INVALID_ARGUMENT
  still consumes tokens. Validate requests with `checkCompatibility` first
  for novel queries.
- **`(other)` row appears at 50k unique values per dimension per day** —
  not configurable. Strip query strings from URLs before they hit GA4.
- **Sampling on Explore-style queries kicks in at 10M events** for the date
  range on standard properties. Standard reports do not sample. The Data
  API picks the layer; you can't force it.
- **Custom dimensions are NOT retroactive** — values populate forward from
  creation time. Old data stays empty forever for that dimension.
- **Property timezone is set at creation and locked** — cannot change
  without creating a new property and losing history.
- **GA4 has a 14-month retention default** on standard properties. Older
  data is purged from the aggregated tables. BigQuery export keeps it
  forever (subject to BQ storage costs).
- **`events_intraday_YYYYMMDD` BigQuery table is missing `traffic_source`,
  `user_ltv`, `is_active_user`** — these populate only when the daily table
  writes. Joining intraday → revenue attribution silently produces wrong
  numbers.
- **Daily BigQuery export caps at 1M events/day on standard properties**.
  Streaming has no cap. Enable both for redundancy or your high-traffic
  days lose data.
- **Measurement Protocol returns 204 on bad payloads** — silent failure.
  Use `/debug/mp/collect` while developing. There is no production
  validation feedback.
- **Measurement Protocol `client_id` matters** — random per-call client_ids
  fragment your user model and inflate user counts. Use a stable hash
  derived from a real identifier.
- **Measurement Protocol events tagged as `debug_mode: 1` appear in
  DebugView and are NOT counted in normal reports** — easy to think your
  pipeline is broken when you forgot to remove the debug flag.
- **Measurement Protocol `consent` block is required in EU** for events to
  be processed. Missing → silent drop.
- **`totalRevenue`, `purchaseRevenue`, `eventValue`** are three different
  metrics with different scopes. Picking the wrong one means your CEO
  agent reports the wrong number to the founder. Read the metadata catalog.
- **Date format in Data API is `YYYY-MM-DD`, in BigQuery export is
  `YYYYMMDD`**. Easy to mix. Lose hours.
- **Property ID is numeric (`123456789`), measurement ID is `G-XXXXXXX`**.
  Data API wants `properties/{numeric}`. Measurement Protocol wants
  `G-XXXXXXX`. Mixing gives unhelpful errors.
- **Quota is per-project AND per-property-per-project**. Two services in
  the same GCP project querying the same property double-burn the project
  bucket. Use separate projects for separate workloads if quota matters.
- **`v1beta` Admin API is current; `v1alpha` still ships in the SDK** with
  extra mutating endpoints. Importing the wrong version compiles fine and
  fails at runtime in obscure ways. Always pin the version in imports.
- **gRPC default transport blocked by some corporate proxies** — instantiate
  with `transport="rest"` if connections hang.
- **`from_service_account_file` reads the file lazily on first call**, not
  at construction time. Bad path errors surface mid-execution. Validate the
  path at startup.
- **The `BetaAnalyticsDataClient` class name still has `Beta` even though
  v1beta is GA-stable**. Don't try to "find the GA client" — `Beta` is the
  GA client.
- **`checkCompatibility` is a separate method, not a flag on `runReport`** —
  call it explicitly during development for novel reports.
- **Audience exports are async LROs** that take minutes. Don't poll in a
  tight loop; use the SDK's `result()` with a timeout.
- **The Python SDK's auto-pagination on Admin API list calls hides the
  `page_token`** — for-loop is convenient but you can't resume mid-iteration.
  For huge lists, drop to manual pagination.
- **`ga4_client._client()` is `lru_cache(maxsize=1)`** so the gRPC channel
  is reused. If you fork after first call, the child gets a broken channel.
  Re-instantiate after fork.
- **GA4 bot filtering is mandatory** and uses the IAB list. A misclassified
  crawler can swing small-traffic numbers 10%. Don't trust day-over-day
  deltas under 100 sessions.
- **Conversion attribution can shift for 48 hours after the conversion
  fires** — yesterday's "direct" conversion may become today's "google /
  cpc" conversion. Re-snapshot after 48h for finalized numbers.
- **Property timezone applies to all `date` dimensions** — querying
  "yesterday" at 6am UTC for an LA-timezone property gets you LA-yesterday,
  which is still in progress. Wait until 6am LA time (14:00 UTC) for clean
  yesterday data.
- **Custom dimensions count toward the 50/property cap** including ones
  you created and forgot. List with Admin API periodically and prune.
