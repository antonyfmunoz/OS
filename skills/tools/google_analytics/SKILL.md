---
name: google_analytics
description: "Use when querying GA4 traffic, conversions, or funnels for any EOS-tracked site (Initiate Arena landing pages, Lyfe Spectrum store, Empyrean Studio, personal brand), pulling realtime active users, listing properties/dataStreams via the Admin API, sending server-side events via Measurement Protocol, or exporting raw events to BigQuery."
allowed-tools: "Read, Bash, Write, Edit"
version: 1.0
source_url: "https://developers.google.com/analytics/devguides/reporting/data/v1"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "Data API v1beta, Admin API v1beta, Measurement Protocol v2"
sdk_version: "google-analytics-data 0.18.x, google-analytics-admin 0.22.x"
speed_category: stable
trigger: both
effort: low
context: fork
---

# Tool: google_analytics

## What This Tool Does

Google Analytics 4 (GA4) is the event-based web/app analytics platform that
replaced Universal Analytics. It exposes three programmatic surfaces relevant
to EOS:

1. **Data API (v1beta)** — read-only reporting on aggregated GA4 properties.
   `runReport`, `batchRunReports`, `runPivotReport`, `runRealtimeReport`,
   `checkCompatibility`, plus metadata endpoints (`getMetadata`).
2. **Admin API (v1beta)** — manage accounts, properties, data streams,
   custom dimensions/metrics, conversion events, Measurement Protocol secrets.
   Read-only for our use; mutating endpoints exist but EOS does not call them.
3. **Measurement Protocol (v2)** — fire `POST` requests to
   `https://www.google-analytics.com/mp/collect` to record server-side events
   against a measurement_id + api_secret pair.

Optional fourth surface: **BigQuery Export** (`events_YYYYMMDD` daily tables
plus `events_intraday_YYYYMMDD` streaming tables) — bypasses API quotas
entirely by giving raw event-level access via SQL.

Core capabilities:

- Conversion funnels per landing page, per source/medium, per device
- Realtime active users (last 30 minutes) for launch monitoring
- Acquisition reports (sessionSource, sessionMedium, sessionCampaignName)
- Engagement reports (engagedSessions, engagementRate, averageSessionDuration)
- Event-based conversions (purchase, generate_lead, sign_up — fully custom)
- Audience exports for downstream activation
- Quota introspection via `returnPropertyQuota: true`

## EOS Integration

GA4 is the canonical web-analytics layer for every EOS-tracked surface.
Read-only; no risk class concerns. Primary uses:

- **Initiate Arena landing pages** — daily funnel from session → scroll →
  CTA click → checkout-start → purchase. Drop-off detection feeds the morning
  brief and the outreach prioritization loop.
- **Lyfe Spectrum store** — product list views, add-to-cart, checkout funnel.
- **Empyrean Studio site** — lead-form completion rate, content engagement.
- **Personal brand site** — top referring sources, content engagement,
  geographic split.
- **Morning brief enrichment** — `world_pulse.py` and `morning_prep.sh` call
  the Data API for yesterday's totals + 7-day trend, surface deltas to CEO
  agents.
- **Realtime check during launches** — `runRealtimeReport` polled every 60s
  during outreach pushes to detect spikes/drops while they're actionable.

Canonical EOS pattern:
- One service account JSON in `eos_ai/.env` referenced by
  `GOOGLE_APPLICATION_CREDENTIALS` (path) or `GA4_SA_JSON` (inline JSON)
- Property IDs in BIS, never hardcoded — `bis.get('ga4_property_ids')`
- All calls through a thin `eos_ai/ga4_client.py` wrapper that handles
  pagination, quota introspection, and exponential backoff
- Results written to Neon `analytics.ga4_daily` for trend tracking

## Authentication

Two valid auth modes. EOS uses **service account** exclusively.

### Service account (EOS standard)

1. Create a GCP project, enable **Google Analytics Data API** and
   **Google Analytics Admin API**
2. IAM → Create service account → download JSON key
3. In GA4 Admin → Property Access Management → add the service account email
   as **Viewer** (or **Analyst** if you need annotations). The API call will
   return `403 PERMISSION_DENIED` until this is done — adding the API to the
   project is necessary but not sufficient
4. Scope: `https://www.googleapis.com/auth/analytics.readonly`

```python
from google.oauth2 import service_account
from google.analytics.data_v1beta import BetaAnalyticsDataClient

creds = service_account.Credentials.from_service_account_file(
    "/opt/OS/eos_ai/.secrets/ga4-sa.json",
    scopes=["https://www.googleapis.com/auth/analytics.readonly"],
)
client = BetaAnalyticsDataClient(credentials=creds)
```

### OAuth 2.0 user (NOT used by EOS)

Three-legged flow with refresh tokens. Required only if you need to act as a
specific human (e.g. read a property the founder owns but cannot share to a
service account). Avoid — service accounts are simpler and don't expire.

### Measurement Protocol auth

Different model: per-data-stream `api_secret` created in
GA4 Admin → Data Streams → choose stream → Measurement Protocol API secrets.
Sent as `?api_secret=...&measurement_id=G-XXXXXXX` query string. Treat as
secret — anyone with the pair can write events to your property.

## Quick Reference

### Run a basic report

```python
from google.analytics.data_v1beta.types import (
    DateRange, Dimension, Metric, RunReportRequest,
)

req = RunReportRequest(
    property=f"properties/{PROPERTY_ID}",
    dimensions=[Dimension(name="sessionSource"), Dimension(name="pagePath")],
    metrics=[
        Metric(name="sessions"),
        Metric(name="conversions"),
        Metric(name="totalRevenue"),
    ],
    date_ranges=[DateRange(start_date="7daysAgo", end_date="yesterday")],
    limit=100000,
    return_property_quota=True,  # ALWAYS in EOS
)
resp = client.run_report(req)
for row in resp.rows:
    print([d.value for d in row.dimension_values],
          [m.value for m in row.metric_values])
print("Quota left:", resp.property_quota.tokens_per_hour.remaining)
```

### Realtime (last 30 minutes)

```python
from google.analytics.data_v1beta.types import RunRealtimeReportRequest

rt = client.run_realtime_report(RunRealtimeReportRequest(
    property=f"properties/{PROPERTY_ID}",
    dimensions=[Dimension(name="unifiedScreenName")],
    metrics=[Metric(name="activeUsers")],
))
```

### Batch up to 5 reports in one call

```python
from google.analytics.data_v1beta.types import BatchRunReportsRequest
batch = client.batch_run_reports(BatchRunReportsRequest(
    property=f"properties/{PROPERTY_ID}",
    requests=[req_a, req_b, req_c],  # up to 5
))
```

### Admin API — list properties and data streams

```python
from google.analytics.admin_v1beta import AnalyticsAdminServiceClient

admin = AnalyticsAdminServiceClient(credentials=creds)
for acct in admin.list_account_summaries():
    for prop in acct.property_summaries:
        print(prop.property, prop.display_name)
        for stream in admin.list_data_streams(parent=prop.property):
            print("  ", stream.name, stream.web_stream_data.measurement_id)
```

### Measurement Protocol — server-side event

```bash
curl -X POST \
  "https://www.google-analytics.com/mp/collect?measurement_id=G-XXXXXXX&api_secret=$MP_SECRET" \
  -H 'Content-Type: application/json' \
  -d '{
    "client_id": "eos.server.1234",
    "events": [{
      "name": "lead_qualified",
      "params": {"source": "outreach_loop", "value": 750, "currency": "USD"}
    }]
  }'
```

Response is `204 No Content` on success — and on most failures too. Use
`/debug/mp/collect` while developing for validation messages.

## Conceptual Model

**Property → DataStream → Event → Parameter → User**. A GA4 property is the
top container. Each property holds 1+ data streams (web, iOS, Android). Every
hit is an event with up to 25 custom parameters plus reserved ones (page_view,
session_start, first_visit, purchase, etc.). Events roll up to sessions and
users via cookies (web) or app instance IDs (mobile).

**Two storage layers behind the API**:
1. **Aggregated tables** (powering Standard reports + most Data API queries)
   — pre-computed, fast, no sampling
2. **Raw event tables** (powering Explorations + the BigQuery export) —
   sampled at 10M events for the date range on standard properties

The Data API picks the layer per query based on dimensions/metrics requested.
Add a high-cardinality dimension or an unusual metric combination → you fall
through to the raw layer → sampling kicks in → row count caps and
high-cardinality groups collapse into `(other)`.

If you internalize this two-layer model, every confusing GA4 behavior becomes
obvious: "why does my dashboard show a different number than yesterday" →
late-arriving events into the aggregated table. "Why is `(other)` in my
report" → cardinality > 50k. "Why is this slow" → fell through to raw layer.

## Gotchas

- **Service account added to GCP but not to GA4 property** → `403
  PERMISSION_DENIED`. The two are independent. ALWAYS add the SA email as a
  property Viewer in GA4 Admin → Property Access Management.
- **`returnPropertyQuota` defaults to false** → you have no idea you're
  burning the 14k/hour budget until you hit it. Set it on every call in EOS.
- **`(other)` row appears** when cardinality > 50k for a dimension. Mitigate
  by narrowing the date range or removing the high-cardinality dimension.
- **Sampling kicks in at 10M events for the date range** on standard
  properties (Explore-style queries). Standard reports do not sample.
- **Measurement Protocol returns 204 on bad payloads silently**. Use
  `/debug/mp/collect` during development. Production blind spot otherwise.
- **`events_intraday_YYYYMMDD` BigQuery streaming tables** are missing
  `traffic_source`, `user_ltv`, and `is_active_user` — never join those
  fields off intraday data, wait for the daily `events_YYYYMMDD` table.
- **Daily BigQuery export caps at 1M events/day** on standard properties.
  Streaming export has no cap. Enable both for redundancy.
- **`totalRevenue` vs `purchaseRevenue` vs `eventValue`** — three different
  metrics with three different scopes. Read the metadata catalog before
  picking one or your CEO agent will report the wrong number.
- **Date strings**: GA4 accepts `today`, `yesterday`, `NdaysAgo`, or
  `YYYY-MM-DD`. NOT `YYYYMMDD`. The BigQuery export uses `YYYYMMDD`.
  Easy to swap and lose hours.
- **Property ID is numeric** (e.g. `123456789`), measurement ID is
  `G-XXXXXXX`. Data API wants `properties/{numeric}`, Measurement Protocol
  wants the `G-` form. Mixing them gives unhelpful errors.
- **Quota is per-project AND per-property-per-project**. Two services in the
  same GCP project querying the same property double-burn the project bucket.
- **Webhooks: N/A** — GA4 has no native push/webhook surface. Closest
  equivalents are BigQuery streaming export + a scheduled query, or a polling
  loop on `runRealtimeReport`. Both documented in best_practices.md.
- **Admin API is `v1beta`** as of 2026-04. `v1alpha` still exists with
  extra mutating endpoints (subproperties, audiences) — pin the version
  explicitly in imports to avoid accidental upgrades breaking things.
- **gRPC vs REST**: the Python SDK uses gRPC by default. Behind corporate
  proxies that block gRPC, instantiate with `transport="rest"`.

See references/best_practices.md for the full 19-section creator-level
knowledge base, EOS usage patterns, and the failure catalog.
