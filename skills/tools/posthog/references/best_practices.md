# PostHog — Creator-Level Best Practices

Source: posthog.com/docs, posthog-python GitHub, PostHog pricing,
creator blog posts and YC W20 talks by James Hawkins and Tim Glaser.
API Version: REST v1
SDK Version: posthog-python 3.7.0
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## Authentication

PostHog uses two distinct key classes. Mixing them is the single most
common integration bug in the product.

### Project API Key
- Prefix: `phc_` (~47 chars)
- Scope: write-only — `POST /capture/`, `POST /batch/`, `POST /decide/`,
  `POST /e/`
- Cannot read events, insights, or manage anything
- Safe to ship in browser bundles, mobile apps, and public source
- One per PostHog project. Project Settings → Project API Key.
- Env: `POSTHOG_PROJECT_API_KEY` (or `POSTHOG_API_KEY`)

### Personal API Key
- Prefix: `phx_` (modern) or raw 40-char hex (legacy)
- Full read/write scope. Scopeable since 2024:
  `feature_flag:read`, `feature_flag:write`, `query:read`, `insight:read`,
  `insight:write`, `dashboard:read`, `organization:read`, `project:read`,
  `session_recording:read`, `export:read`, `annotation:write`, etc.
- Server-side only. Never ship to clients.
- Used for: HogQL queries, insight/dashboard/flag CRUD, exports,
  local flag evaluation (pulls definitions, evaluates in-process).
- Env: `POSTHOG_PERSONAL_API_KEY`

### Auth headers

Ingestion (project key in body):
```http
POST /capture/ HTTP/1.1
Content-Type: application/json

{"api_key":"phc_...","event":"$pageview","distinct_id":"u1","properties":{}}
```

REST (Bearer):
```http
GET /api/projects/123/insights/ HTTP/1.1
Authorization: Bearer phx_...
```

### Hosts
| Region | Ingestion (capture) | REST / App |
|---|---|---|
| US Cloud | `https://us.i.posthog.com` | `https://us.posthog.com` |
| EU Cloud | `https://eu.i.posthog.com` | `https://eu.posthog.com` |
| Self-host | your own | your own |

Mixing hosts silently drops events. Pick once per project, pin it.

## Core Operations

### Capture — `POST /capture/`
```json
{
  "api_key": "phc_...",
  "event": "user_signed_up",
  "distinct_id": "user_123",
  "timestamp": "2026-04-06T12:34:56Z",
  "properties": {"plan": "pro", "$lib": "posthog-python", "$lib_version": "3.7.0"}
}
```
Reserved properties start with `$`. `$set`/`$set_once` on the properties
update the person record.

### Batch — `POST /batch/`
```json
{"api_key":"phc_...","batch":[{"event":"e1","distinct_id":"u1","properties":{},"timestamp":"..."},{"event":"e2","distinct_id":"u1","properties":{},"timestamp":"..."}]}
```
Max 1000 events per batch. Max 20 MB compressed.

### Identify
`$identify` event with `$set`/`$set_once`. `$create_alias` merges an
anonymous distinct_id into a known user. Merges are irreversible.

### Groups
```json
{"event":"$groupidentify","distinct_id":"user_123","properties":{"$group_type":"company","$group_key":"acme_inc","$group_set":{"name":"Acme","arr":50000}}}
```
Max 5 group types per project. Hard limit.

### Feature flags — `POST /decide/?v=3`
```json
{"api_key":"phc_...","distinct_id":"u1","groups":{"company":"acme"},"person_properties":{"plan":"pro"},"group_properties":{"company":{"arr":50000}}}
```
Returns `{"featureFlags": {...}, "featureFlagPayloads": {...}}`.

### Session Replay
Captured only by JS and mobile SDKs — no server ingestion. Stored as
rrweb streams in S3. List via
`GET /api/projects/{id}/session_recordings/`.

### LLM Observability (`posthog.ai`)
Wraps OpenAI, Anthropic, Gemini clients. Auto-emits `$ai_generation`
events with `$ai_provider`, `$ai_model`, `$ai_input`, `$ai_output_choices`,
`$ai_input_tokens`, `$ai_output_tokens`, `$ai_total_cost_usd`,
`$ai_latency`, `$ai_trace_id`, `$ai_span_id`, `$ai_parent_id`,
`$ai_is_error`, `$ai_error`. Rolls up into traces in the LLM
Observability dashboard.

### HogQL — `POST /api/projects/{id}/query/`
```json
{"query":{"kind":"HogQLQuery","query":"SELECT properties.plan, count() FROM events WHERE event='user_signed_up' AND timestamp > now() - interval 7 day GROUP BY properties.plan"}}
```
ClickHouse SQL dialect with PostHog functions: `person_property(...)`,
`groups[...]`, `$session_id`, etc.

### Endpoint cheat sheet
```
POST   {host_i}/capture/            single event
POST   {host_i}/batch/              batch events
POST   {host_i}/decide/?v=3         flag eval
GET    {host_i}/array/{key}/config  flag defs (local eval)

GET    {host}/api/projects/
GET    {host}/api/projects/{id}/events/
GET    {host}/api/projects/{id}/persons/
DELETE {host}/api/projects/{id}/persons/{uuid}/      GDPR delete
GET    {host}/api/projects/{id}/feature_flags/
POST   {host}/api/projects/{id}/feature_flags/
GET    {host}/api/projects/{id}/insights/
POST   {host}/api/projects/{id}/query/               HogQL
GET    {host}/api/projects/{id}/session_recordings/
GET    {host}/api/projects/{id}/experiments/
GET    {host}/api/projects/{id}/cohorts/
POST   {host}/api/projects/{id}/annotations/
```

## Pagination

REST list endpoints use DRF offset/limit with a `next` URL:
```json
{"next":"https://.../events/?limit=100&offset=100","previous":null,"results":[...]}
```
Default `limit=100`, max 1000 (10000 for `/events/`). Follow `next`
rather than incrementing offset. HogQL queries paginate inside the SQL
(`LIMIT n OFFSET m`) — the query API does not auto-paginate.

## Rate Limits

| Endpoint | Limit |
|---|---|
| `/capture/`, `/batch/`, `/e/` | Effectively unlimited (~10k rps/project soft cap) |
| `/decide/` | 100 rps sustained, 400 rps burst per project |
| REST `/api/...` (personal key) | 480 req/min per key |
| `/api/projects/{id}/query/` (HogQL) | 240 req/min, 120/hr free plan, 1200/hr paid |
| `/api/projects/{id}/persons/`, exports | 60 req/min per key |

429 responses include `X-RateLimit-Limit`, `X-RateLimit-Remaining`,
`X-RateLimit-Reset`, `Retry-After`. Capture endpoint rarely 429s —
if it does, batch.

## Error Codes

| Code | Meaning | Action |
|---|---|---|
| 200 | OK — capture returns `{"status":1}` | — |
| 400 | Malformed JSON, missing api_key/event/distinct_id | Fix payload |
| 401 | Invalid personal API key | Rotate |
| 402 | Billing quota exceeded | Events silently dropped downstream |
| 403 | Personal key lacks scope | Add scope in UI |
| 404 | Wrong project_id or host (US vs EU) | Verify host |
| 413 | Payload >20MB | Split batch |
| 422 | Validation error on CRUD | Fix payload |
| 429 | Rate limited | Honor `Retry-After` |
| 500 | Internal | Retry w/ backoff |
| 503 | Ingestion overloaded | Retry w/ backoff + jitter |

Capture is fire-and-forget — it returns 200 even if the event is later
dropped. Validate payloads locally before sending.

## SDK Idioms

### posthog-python 3.7.0

Requires Python ≥ 3.8. LLM observability needs ≥ 3.5.0.

Module singleton:
```python
import posthog
posthog.api_key = "phc_..."
posthog.host = "https://us.i.posthog.com"
posthog.personal_api_key = "phx_..."  # only for local flag eval
```

Instance form:
```python
from posthog import Posthog
ph = Posthog(
    project_api_key="phc_...",
    host="https://us.i.posthog.com",
    personal_api_key="phx_...",
    sync_mode=False,        # default: bg queue + flush thread
    flush_at=20,            # flush at N events
    flush_interval=10,      # or every N seconds
    max_queue_size=10000,
    timeout=15,
    feature_flags_request_timeout_seconds=3,
    enable_exception_autocapture=False,
)
```

`capture()` signature (3.x):
```python
posthog.capture(
    distinct_id, event, properties=None, context=None, timestamp=None,
    uuid=None, groups=None, send_feature_flags=False, disable_geoip=True,
)
```
**Arg order reversed vs 2.x** — `distinct_id` is first now.

Flag evaluation:
```python
posthog.feature_enabled(flag, uid, person_properties={}, groups={},
                        group_properties={}, only_evaluate_locally=False,
                        send_feature_flags=False)
posthog.get_feature_flag(flag, uid)           # variant string
posthog.get_feature_flag_payload(flag, uid)   # JSON payload
```

Groups:
```python
posthog.group_identify(group_type, group_key, properties={})
```

LLM observability:
```python
from posthog.ai.openai import OpenAI
from posthog.ai.anthropic import Anthropic
client = OpenAI(api_key="sk-...")
client.chat.completions.create(
    model="gpt-4o", messages=[...],
    posthog_distinct_id="u1", posthog_trace_id="t1",
    posthog_properties={"feature":"x"}, posthog_groups={"company":"acme"},
)
```

Shutdown:
```python
import atexit
atexit.register(posthog.shutdown)
# or explicit
posthog.flush()       # blocks until queue drained
posthog.shutdown()    # flush + stop bg threads
```
Background thread is daemonic — short scripts MUST flush before exit,
or use `sync_mode=True` in the constructor for serverless.

### Async
posthog-python is sync HTTP under the hood. "async" = bg queue + worker
thread. No `await posthog.capture(...)`. For asyncio, run in a
threadpool or accept the enqueue cost (network doesn't block).

## Anti-Patterns

1. **PII in event properties without redaction** — ends up in
   ClickHouse forever. Use `$set` on the person so GDPR delete works.
2. **Not flushing on exit** — short scripts lose every event.
3. **Personal key in frontend / mobile bundle** — full account
   compromise. Rotate immediately if leaked.
4. **High-cardinality event NAMES** — `event="page_/users/12345"`.
   Tanks query perf. Put dynamic parts in properties.
5. **High-cardinality property keys** — `{f"item_{i}": ...}`.
   Use arrays.
6. **`send_feature_flags=True` on every capture** — hammers `/decide/`
   and you 429 yourself.
7. **Polling `/decide/` from N workers** without local eval — instant
   429. Set `personal_api_key` so each process evaluates locally.
8. **US ↔ EU host mismatch** — events vanish silently.
9. **`$identify` without `alias` on previously anonymous user** —
   forks the person graph, losing pre-signup events. Use `alias()`.
10. **Capturing in tests** — set `posthog.disabled = True`.
11. **Booleans as strings** — `"true"`/`"false"` breaks HogQL filters.
12. **Missing `$lib`/`$lib_version`** on raw POSTs — nobody can debug.
13. **Flag checks in hot loops** — every check emits a
    `$feature_flag_called` event unless you set
    `send_feature_flag_events=False` or dedupe per request.
14. **Forgetting `posthog.reset()` on logout** — merges two users onto
    one anonymous distinct_id permanently.

## Data Model

| Object | Identified by | Notes |
|---|---|---|
| Event | `uuid`, `event`, `distinct_id`, `timestamp`, `properties`, `team_id`, `person_id` | Immutable, ClickHouse row |
| Person | `uuid`, `distinct_ids[]`, `properties` | Upserted via persons table |
| Group | `group_type`, `group_key`, `group_properties` | Max 5 types/project |
| Cohort | static or dynamic | Dynamic = re-eval on schedule |
| Insight | Trends, Funnels, Retention, Paths, Lifecycle, Stickiness, HogQL | Cached 3-15 min |
| Dashboard | collection of insights | — |
| Feature flag | `key`, `filters`, `rollout_percentage`, `payloads` | Boolean or multivariate |
| Experiment | flag + metric + stats | Primary metric = insight |
| Action | event-matching rule | For filters + automation |
| Session recording | `session_id`, rrweb stream | JS/mobile only |
| Annotation | timestamped dashboard note | — |

Events are the atomic unit. Everything else is derived from events.

## Webhooks

### CDP Destinations (realtime)
Configured in Data Pipeline → Destinations. The HTTP destination
POSTs each matching event to your URL:
```json
{"event":"user_signed_up","distinct_id":"u1","properties":{},"person":{},"timestamp":"..."}
```
Custom headers. Retries with exponential backoff on 5xx. Dead-letter
after 24h.

### Action-triggered webhooks (legacy)
Per-action, Slack or generic JSON. Being deprecated in favor of CDP
destinations.

### Subscriptions
Insight and dashboard subscriptions email or Slack on a schedule —
NOT webhooks, scheduled push only.

### Inbound
PostHog has no inbound webhook receiver. Proxy through your server and
call `capture()`.

## Limits

| Limit | Value |
|---|---|
| Max event payload | 1 MB per event |
| Max batch payload | 20 MB compressed |
| Max events per batch | 1000 |
| Max property key length | 200 chars |
| Max property value size | 8 KB (truncated) |
| Max properties per event | 1000 (soft) |
| Max distinct event names per project | ~10,000 (soft) |
| Max group types per project | 5 (hard) |
| Max feature flags per project | unlimited (soft — decide perf >500) |
| Session recording max duration | 24 hours |
| Session recording inactivity timeout | 30 min default |
| HogQL query timeout | 60s default, 600s max paid |
| HogQL query memory | 8 GB per query |

## Cost Model

Event-based, per product, with separate meters.

**Product Analytics**: 1M events/mo free, then $0.00005 → $0.0000220
per event on a volume tier curve.

**Session Replay**: 5k recordings/mo free, then $0.0035 → $0.005 per
recording. **This is the line item that explodes first.**

**Feature Flags/Experiments**: 1M requests/mo free, then $0.0001 →
$0.000025 per request. Local eval counts as requests but is cheap.

**LLM Observability**: one `$ai_generation` = one product-analytics
event. No separate meter.

**Data Warehouse/CDP**: 1M rows/events free, then per-unit pricing.

**Plans**: Free (all free tiers, 1yr retention, community support) →
Pay-as-you-go (7yr retention, email support) → Teams add-on $450/mo
(SSO, RBAC, audit logs) → Enterprise (SAML, SLA, MSA).

Spending limits per product drop ingestion silently when exceeded.
Alert externally.

## Version Pinning

```
# requirements.txt
posthog==3.7.0
# for LLM observability
posthog[ai]==3.7.0
```

Compat matrix for 3.7.0:
- `openai >= 1.30.0, < 2.0.0`
- `anthropic >= 0.25.0, < 1.0.0`
- `google-genai >= 0.3.0` (NOT `google-generativeai`)

Python: 3.8 – 3.13. Drop 3.7 is final in 3.x.

---

# Tier 2 — Creator Intelligence

## Design Intent

Founded **Feb 2020** by **James Hawkins** (CEO, sales/founder) and
**Tim Glaser** (CTO, data eng). **YC W20**. Launched on HN, hit #1,
bootstrapped from there. Series A from GV and YC Continuity within
months.

The founding thesis: product teams were paying Mixpanel/Amplitude
six figures for what was architecturally a Postgres event store with
a chart builder. Sending behavioral data to a third-party SaaS was a
GDPR liability. The bet:

1. Engineers prefer **self-host** if it's good enough.
2. Analytics market wide open for an **open-source default** (GitLab
   vs GitHub, Mattermost vs Slack).
3. Cloud analytics unit economics were fat enough that an open-core
   model could undercut incumbents by 10× and still print money on
   PostHog Cloud.

Structural weaknesses attacked:
- **Data residency** — EU PII in Mixpanel-US is a legal minefield.
- **Vendor lock-in on event schema** — MTU/event pricing creates
  perverse incentive to instrument less. PostHog's pitch: instrument
  everything, autocapture by default, storage is cheap.
- **Closed black-box SQL** — Mixpanel doesn't let you run arbitrary
  SQL. PostHog exposed ClickHouse via HogQL.

**The "all-in-one" thesis** (the strategic bet that distinguishes
PostHog): product teams don't want eight tools, they want one. If
analytics, replay, flags, experiments, surveys, CDP, LLM obs, and
warehouse all share the same `distinct_id` and the same ClickHouse
backend, the integrated product is qualitatively better than any
best-of-breed combo — cohorts flow into flags without plumbing.

## Problem-Solution Map

| Surface | Problem | Replaces |
|---|---|---|
| Product analytics | Funnels, retention, drop-off | Mixpanel, Amplitude, Heap |
| Session replay | "Why did they drop?" rrweb + network + console | FullStory, Hotjar, LogRocket |
| Feature flags | Ship dark, staged rollout, kill switch | LaunchDarkly, Split |
| Experiments | A/B significance on flags + events | Optimizely, Statsig, VWO |
| Surveys | In-app prompts, NPS, paywall surveys | Hotjar, Sprig |
| LLM observability | Trace/span/token/cost per LLM call | Langfuse, Helicone, Arize |
| Data warehouse | Stripe/HubSpot/SF → ClickHouse-queryable | Fivetran (light) |
| CDP destinations | Forward events to Slack/BQ/Webhooks | Segment, RudderStack |
| Web analytics | Simple pageviews | GA4, Plausible |
| Error tracking (beta) | Frontend exceptions tied to person graph | Sentry (light) |

The unifying claim: every surface writes to / reads from the same
ClickHouse event table keyed by `distinct_id`. That's the moat.

## Operational Behavior

### ClickHouse backend
Migrated off Postgres in 2021. Single most important architectural
fact. Events live in `sharded_events` partitioned by month, ordered by
`(team_id, toDate(timestamp), event, cityHash64(distinct_id),
timestamp)`. Columnar, append-only. Mutations are async and expensive.
PostHog leans on this — events are immutable, person properties are
upserted in a separate table.

### Ingestion pipeline
1. SDK → `POST /e/` or `/capture/`.
2. Capture service → Kafka.
3. plugin-server consumes Kafka, runs ingestion plugins, person
   processing, writes to ClickHouse.
4. ClickHouse merges parts asynchronously.
5. Query layer reads merged parts.

End-to-end lag: **30s to 2 min healthy**, spikes to 5-15 min during
incidents. Self-hosted with undersized plugin-server: hours. Person
processing is the slowest stage.

### Insights caching
Insights cached 3-15 min. Dashboards do not reflect just-fired events.
Never build read-after-write product flows on PostHog state.

### Session replay
Recorded client-side via rrweb, chunked, uploaded to S3. Metadata in
`session_replay_events`. Typical replay: 50KB-2MB. At 100K+ MAU this
dwarfs event storage. Sample aggressively, use minimum-duration
filters, trigger-based recording, or conditional recording via flags.

### Feature flag eval — the leverage point
- **Remote** (default): every flag check → HTTP to `/decide/`. 60-300ms
  per call from a server. Adds that to request p99.
- **Local**: server SDK pulls flag definitions (not resolved values) on
  a 30s poll. Evaluates in-process. Zero network on hot path.

Local eval constraints:
- Must pass **all** relevant person/group properties at call site —
  no person lookup locally.
- Cohort-based flags require **static** cohorts or fall back to remote.
- Client SDKs can't do local eval (user only knows themselves).

### `/decide/` endpoint
Single hot endpoint client SDKs hit on page load. Returns flags,
replay config, autocapture config, surveys, toolbar state. Billions
of req/day on Cloud. ~50-150ms p50. Cached values in localStorage
when down. SDK only calls once per page load unless properties change
or `reloadFeatureFlags()` is called.

## Ecosystem Position

**vs Mixpanel**: PostHog wins on open source, self-host, bundled
product, HogQL, price at scale. Mixpanel wins on insight polish,
mobile-first UX, non-engineer ergonomics.

**vs Amplitude**: PostHog wins on price, open source, engineering DX,
raw SQL. Amplitude wins on behavioral cohorting, predictive, North
Star framework, data governance.

**vs Heap**: PostHog wins on open source, broader product. Heap wins
on autocapture quality — Heap's retroactive event definition is still
best in class.

**vs Segment**: PostHog wins on being the destination (no extra hop),
price at scale. Segment wins on 400+ destinations, Protocols for
schema governance, Personas for audience sync.

**vs LaunchDarkly**: PostHog wins on bundling + price + open source.
LaunchDarkly wins on enterprise flag governance, approvals, scheduled
rollouts, multi-env workflows, edge delivery CDN.

**vs Statsig**: PostHog wins on bundle + open source + surface.
Statsig wins on experimentation depth — sequential testing, CUPED,
holdouts, stats engine.

**vs Datadog RUM**: PostHog wins on product-first framing + bundle +
price. Datadog wins when you already live in Datadog and need RUM
tied to backend APM traces.

**Where PostHog loses in general**: mature enterprise data teams still
prefer Snowflake/BigQuery + dbt + Looker for the analytics layer and
use PostHog only for replay and flags. Mobile-first companies find
mobile SDKs less polished. Marketing attribution is not PostHog's
strength.

## Trajectory

- **LLM Observability GA (2024)** — trace/span/token/cost for OpenAI,
  Anthropic, Gemini, LangChain. Langfuse competitor that comes free
  with the rest of PostHog.
- **Data Warehouse GA (2024)** — managed Stripe/HubSpot/SF/Postgres/
  BQ/Snowflake/S3 connectors. HogQL JOINs warehouse tables to events.
- **Max AI (2024-2025)** — natural-language insight builder. "What's
  my conversion by country last week?" → HogQL + chart.
- **"Product OS" pivot** — messaging shifted from "analytics tool" to
  "everything you need to build a product." Notebooks shipped, error
  tracking in beta, CDP becoming first-class via Hog.
- **Hog + HogQL** — Hog is PostHog's scripting language for
  transformations; HogQL is their SQL dialect. Both central to
  platform bets.

**2026 direction**: deeper warehouse + reverse-ETL (Hightouch light),
more Max AI surface (agent that builds dashboards/experiments from
prompts), error tracking out of beta as Sentry alternative for small
teams, BI/Looker territory via HogQL notebooks. IPO drumbeat — expect
open-core data infra bets, not analytics SaaS bets.

## Conceptual Model

**Events → Persons → Groups → Cohorts → Insights.**

- **Events**: immutable ClickHouse rows. Atomic unit. Everything
  derives from events.
- **Persons**: resolve `distinct_id` aliases. Properties set via
  `$set`/`$set_once`. Upserted in the `persons` table by
  plugin-server during ingestion.
- **Groups**: higher-order entities (company, project, team). Max 5
  types. Required for serious B2B analytics.
- **Cohorts**: saved filters resolving to sets of persons. Static
  (snapshotted) or dynamic (re-evaluated). Dynamic cohorts back
  behavioral flag rules.
- **Insights**: saved queries. Trends/Funnels/Retention/Paths/
  Lifecycle/Stickiness/HogQL. Each type compiles to a different
  ClickHouse query shape.

**Everything ties to `distinct_id`.** Every event, replay, flag eval,
survey response, LLM trace is keyed by it. `$identify` merges
anonymous UUID into user ID; merge is irreversible.

**Identify is not retroactive on rows** — events keep their original
`distinct_id`, queries resolve through persons. Never count unique
users by raw distinct_id; count distinct persons.

### Local vs server flag eval mental model
- Client SDK = always remote (per-user)
- Server SDK = local if you pass properties, remote fallback otherwise
- Edge runtimes (Cloudflare Workers, Vercel Edge) = use edge-compat
  SDK with local eval; never `/decide/` on edge hot path

## Industry Expert

Non-obvious things a senior engineer learns by losing a week:

### `$feature_flag_called` autocapture explodes volume
Every flag check emits a `$feature_flag_called` event so the
experimentation engine can attribute exposure. JS SDK dedupes per
page per flag; Python/Node do NOT dedupe. Flag check in a hot loop
= 1000 events per request. Wrap behind per-request cache or set
`send_feature_flag_events=False` if you don't need experiment
attribution.

### Session replay cost surprise
Replay is the #1 cost line on every PostHog bill because:
- Default records 100% of sessions
- Long SPA sessions produce huge rrweb payloads
- Default retention is generous
- Replays count toward storage quota on top of events

Mitigations:
- `session_recording.sample_rate: 0.1`
- `minimum_duration_milliseconds: 5000`
- Gate on feature flag or target cohort (paid users only)
- Trigger recording on specific event (e.g. checkout)

### Flags in hot paths without local eval
A `/decide/` call adds 60-300ms p50 to a request. From an edge function
in another region it's worse. Symptom: request latency suddenly
doubles after "a small flag rollout." Always set `personal_api_key`,
pass `person_properties` + `group_properties` at call site, and
verify the SDK is actually evaluating locally (debug mode logs this
per-check).

### PII masking footgun
Default replay masks `<input>` elements ONLY. Emails/SSNs/card numbers
in `<div>` or `<span>` are captured verbatim and stored on S3 forever.
HIPAA/PCI/GDPR violation. Fixes: `ph-no-capture` class,
`data-ph-no-capture` attribute, `maskAllText: true`, `maskTextSelector`,
Stripe Elements for payment forms. Audit replays manually after rollout.

### Cohort evaluation
- **Static** = frozen person ID list. Fast, stale. Used by locally-eval'd
  flags.
- **Dynamic** = re-evaluated on a schedule (hourly default). Behavioral
  cohorts ("users who did X in last 7 days") are always dynamic.
  CANNOT be used in locally-eval'd flags.
- Hundreds of dynamic cohorts = ingestion pressure + stale memberships.

### Autocapture vs manual events
- **Autocapture** (JS SDK only) captures every click/submit/pageview
  as `$autocapture` with CSS-selector properties. Good for exploration.
  Fragile — selectors break when a designer changes a class.
- **Manual events** (`posthog.capture('order_completed')`) are stable
  and semantic. Use for anything business-critical.
- Best practice: autocapture on for dev, manual events for every
  critical funnel step, a taxonomy doc the team agrees on.

### `$identify` ordering bugs
Events before `$identify` get the anonymous distinct_id. `$identify`
merges them to the user. But if you `$identify` the SAME anonymous ID
to TWO different users (shared device, two logins), the merge is
permanent and you've polluted both profiles forever. Use
`posthog.reset()` on logout to rotate the anonymous ID. Forgetting
reset is one of the most common instrumentation bugs in the wild.

### HogQL escape hatch
When the visual insight builder can't express what you need, HogQL
gets you there. It's ClickHouse SQL + PostHog functions like
`person_property('email')`, `groups['organization']`. Senior engineers
should learn it early — removes 80% of "PostHog can't do this"
complaints.

### Property type inference
PostHog infers property types from the first handful of values and
**caches** the inference. First 100 events send `revenue: "10"`
(string), you switch to `revenue: 10` (number) — property stays typed
as string, numeric aggregations break. Fix via property definitions
UI or be disciplined from day one.

### Ingestion plugins / Hog transformations
Run on the hot ingestion path during plugin-server consumption. A slow
plugin backs up Kafka. Test under load before enabling in prod.

### `process_person_profile=false`
Recent PostHog lets you disable person processing per-event. Right
call for high-volume backend telemetry where you don't need per-user
attribution — skips the slowest ingestion stage and dramatically
reduces plugin-server load.

### Self-hosted is a full-time SRE job
Operating ClickHouse + Kafka + plugin-server + Postgres + Redis + MinIO
in production is real work. PostHog officially discourages new
self-hosted deployments unless there's a hard data residency
requirement. Use Cloud.

### EU vs US Cloud are separate deployments
Projects don't sync. API hosts differ. Sending EU events to US is a
GDPR violation and a config bug that often doesn't error loudly.

### The Toolbar
In-page PostHog Toolbar lets PMs click around the live site to create
autocapture events from the UI. Loaded via `/decide/` response, only
renders for authenticated PostHog users. Occasional source of "why is
this script tag in production" tickets from security review.

---

## EOS Usage Patterns

- `eos_ai/cognitive_loop.py` — instrument every agent LLM call via
  `posthog.ai.openai.OpenAI` / `posthog.ai.anthropic.Anthropic`
  wrapping `model_router.call_with_fallback()`. Pass
  `posthog_distinct_id=user_id_from_bis`, `posthog_trace_id=run_id`,
  `posthog_properties={"agent": agent_name, "stage": stage}`,
  `posthog_groups={"company": venture_slug}`.
- Initiate Arena outreach funnel — capture
  `outreach_sent → reply_received → call_booked → sale_closed`,
  HogQL for conversion rates and cost-per-lead against the $750 sale
  target.
- Feature flags for staged rollouts of new skills / agents.
  `personal_api_key` in env enables local eval. Pass the venture as
  a group and the founder's tier as `person_properties`.
- LLM observability dashboard as the canonical view of agent cost.
  Replaces ad-hoc logging of tokens/cost.
- Session replay OFF on server-rendered dashboards (no JS SDK), ON
  at 10% sample for the SaaS frontend once launched.

## Gotchas (Compounds Over Time)

- **Arg order reversed** in posthog-python 3.x `capture()` —
  `distinct_id` first, `event` second. 2.x was the reverse.
- **Background flush thread is daemonic** — cron jobs, one-shot
  scripts lose events on exit without `atexit.register(posthog.shutdown)`
  or `sync_mode=True`.
- **Capture endpoint returns 200 even on silent drop** — quota
  exceeded, bad property types, spend limit. HTTP status is
  meaningless for reliability.
- **US vs EU host mismatch** drops events without error.
- **`phc_` vs `phx_` mix-up** — `phc_` in a server script that tries
  to query insights fails with a confusing 401; `phx_` in a frontend
  bundle is full account compromise.
- **High-cardinality event NAMES** tank query performance. Put dynamic
  parts in properties.
- **`$feature_flag_called` per-check event** explodes volume when
  flags are called in loops. Dedupe per request.
- **Session replay PII leaks** via non-input DOM elements.
  `ph-no-capture` or `maskTextSelector`.
- **Missing `posthog.reset()` on logout** permanently merges users on
  shared devices.
- **Dynamic behavioral cohorts cannot be used in locally-eval'd flags**
  — silently falls back to remote.
- **Spending limits drop ingestion silently** — alert externally.
- **Insights are cached 3-15 min** — don't assume a freshly-captured
  event is immediately visible on a dashboard.
- **Group types capped at 5** — hard limit.
- **`google.generativeai` (old SDK)** is deprecated. posthog.ai Gemini
  wrapper uses `google-genai` (new SDK) ≥ 0.3.0.
- **HogQL query API rate limit**: 120/hr on free, 1200/hr paid —
  batch scripts need throttling.
- **posthog-python is not truly async** — it's a bg worker thread. In
  asyncio apps, `capture()` is fast but not awaitable.
