---
name: posthog
description: "Use when capturing product events, identifying users, checking feature flags, running experiments, querying insights via HogQL, wiring LLM observability (`posthog.ai`), or building session-replay/surveys/CDP flows against PostHog Cloud (US/EU) or self-hosted. Covers posthog-python SDK, REST API, and `/decide/` behavior."
allowed-tools: "Read, Write, Edit, Bash, WebFetch, WebSearch"
version: 1.0
source_url: "https://posthog.com/docs/api"
last_researched: "2026-04-09"
instantiated_from: templates/tools/_template/
api_version: "REST v1"
sdk_version: "posthog-python>=3.7,<4"
speed_category: "fast"
trigger: both
effort: medium
context: fork
---

# Tool: PostHog

Open-source product OS: analytics, session replay, feature flags,
experiments, surveys, LLM observability, data warehouse, CDP. Everything
writes to one ClickHouse event store keyed by `distinct_id`.

## What This Tool Does

- **Product analytics** — `capture()` events, trends/funnels/retention
  insights via REST + HogQL.
- **Feature flags / experiments** — boolean + multivariate, with local
  evaluation to avoid `/decide/` on hot paths.
- **Session replay** — rrweb-based, JS/mobile SDKs only (no server
  ingestion).
- **LLM observability** — `posthog.ai.openai`/`anthropic` wrappers auto-
  emit `$ai_generation` events with token + cost + latency.
- **HogQL** — ClickHouse SQL dialect for escape-hatch queries against
  events, persons, groups, and warehouse sources.

## EOS Integration

**Primary consumers:**
- `eos_ai/cognitive_loop.py` — emit `$ai_generation` via the
  `posthog.ai.*` wrapper around `model_router.call_with_fallback()`
  so every agent call is traced with cost, tokens, trace_id, and the
  calling agent as a property.
- Initiate Arena outreach loop — `capture("outreach_sent",
  distinct_id=lead_id, properties={...})`, then HogQL funnel from
  `outreach_sent → reply_received → call_booked → sale_closed`.
- Feature flags for staged rollouts of new agents / skills — local
  eval in Python (personal_api_key + polling), never `/decide/` from
  inside the loop.

**Project key** (safe to ship): `POSTHOG_PROJECT_API_KEY=phc_...`
**Personal key** (server-only, scoped): `POSTHOG_PERSONAL_API_KEY=phx_...`
Both in `/opt/OS/eos_ai/.env`. Host is US cloud:
`POSTHOG_HOST=https://us.i.posthog.com`.

## Authentication

Two key classes — mixing them is the #1 bug:

| Key | Prefix | Scope | Where |
|---|---|---|---|
| Project API key | `phc_` | write-only (capture/batch/decide) | Safe in clients |
| Personal API key | `phx_` | full read/write, scopeable | Server only |

Capture endpoints take `api_key` in the JSON body. REST endpoints
(`/api/projects/...`) take `Authorization: Bearer phx_...`.

Personal keys support per-scope restrictions since 2024:
`feature_flag:read`, `query:read`, `insight:write`, etc. Always
least-privilege.

## Quick Reference

### Minimal capture (Python)
```python
import os, atexit, posthog

posthog.api_key = os.environ["POSTHOG_PROJECT_API_KEY"]
posthog.host    = "https://us.i.posthog.com"
atexit.register(posthog.shutdown)  # critical for short-lived scripts

posthog.capture(
    distinct_id="user_123",
    event="order_placed",
    properties={"plan": "pro", "amount": 49.0, "currency": "USD"},
    groups={"company": "acme_inc"},
)
```

Note: posthog-python 3.x reversed the arg order vs 2.x —
`distinct_id` is now first, `event` second. This bites every upgrader.

### Feature flag with local eval + fallback
```python
from posthog import Posthog

ph = Posthog(
    project_api_key=os.environ["POSTHOG_PROJECT_API_KEY"],
    personal_api_key=os.environ["POSTHOG_PERSONAL_API_KEY"],  # enables local eval
    host="https://us.i.posthog.com",
    feature_flags_polling_interval=30,
)

def is_enabled(flag, uid, default=False):
    try:
        v = ph.feature_enabled(
            flag, uid,
            person_properties={"plan": "pro"},
            groups={"company": "acme_inc"},
            only_evaluate_locally=True,  # never touch /decide/ on hot path
        )
        return bool(v) if v is not None else default
    except Exception:
        return default
```

### Group analytics
```python
ph.group_identify(
    group_type="company", group_key="acme_inc",
    properties={"name": "Acme Inc", "arr": 50000, "plan": "enterprise"},
)
ph.capture(
    distinct_id="user_123",
    event="report_exported",
    properties={"format": "pdf"},
    groups={"company": "acme_inc"},
)
```

### LLM observability wrapper
```python
from posthog.ai.openai import OpenAI
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
resp = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role":"user","content":"hi"}],
    posthog_distinct_id="user_123",
    posthog_trace_id="trace_abc",
    posthog_properties={"agent": "ceo", "feature": "morning_prep"},
    posthog_groups={"company": "lyfe_institute"},
)
```

Auto-emits `$ai_generation` with provider, model, input/output tokens,
USD cost, latency, trace/span IDs. `posthog_privacy_mode=True` to redact.

### HogQL query via REST
```python
import requests, os
r = requests.post(
    "https://us.posthog.com/api/projects/12345/query/",
    headers={"Authorization": f"Bearer {os.environ['POSTHOG_PERSONAL_API_KEY']}"},
    json={"query": {"kind": "HogQLQuery", "query":
        "SELECT properties.plan, count() FROM events "
        "WHERE event='user_signed_up' AND timestamp > now() - interval 7 day "
        "GROUP BY properties.plan"}},
    timeout=30,
)
print(r.json()["results"])
```

### Shutdown discipline
```python
import atexit, signal, posthog
def _shutdown(*_): posthog.shutdown()
atexit.register(_shutdown)
signal.signal(signal.SIGTERM, _shutdown)
signal.signal(signal.SIGINT,  _shutdown)
```

## Conceptual Model

**Events → Persons → Groups → Cohorts → Insights.**
Events are immutable ClickHouse rows keyed by `distinct_id`. `$identify`
merges distinct_ids into one Person (irreversible). Groups are higher-
order entities (company, project) — max 5 types per project. Cohorts
are saved queries of persons (static or dynamic). Insights are saved
HogQL queries.

Everything ties to `distinct_id`. Always count distinct *persons*,
never raw `distinct_id`, because identify-merges rewrite the graph.

## Gotchas

- **`phc_` vs `phx_` are not interchangeable.** `phc_` → write-only
  client-safe. `phx_` → full read/write, server-only. Leaking `phx_`
  is full account compromise.
- **Capture endpoint always returns 200** — events can still be dropped
  downstream by quota, bad types, or filters. Do not trust HTTP status.
- **US vs EU host mismatch silently drops events.** Capture must go to
  `us.i.posthog.com` OR `eu.i.posthog.com`. Wrong choice = empty dashboard.
- **posthog-python 3.x reversed `capture()` arg order** — `distinct_id`
  first now. Migrating from 2.x will silently attribute every event to
  the event name.
- **Background flush thread is daemonic** — short scripts lose events on
  exit. ALWAYS `atexit.register(posthog.shutdown)` or use
  `sync_mode=True` in serverless.
- **`/decide/` is the rate-limited endpoint, not `/capture/`.** 100 rps
  sustained, 400 burst per project. Local eval avoids it entirely.
- **Flag checks in hot paths without local eval add 60-300ms p50.**
  Always pass `personal_api_key` + required person/group properties at
  call site + `only_evaluate_locally=True`.
- **`$feature_flag_called` autocapture explodes event volume.** Every
  flag check emits one event (JS dedupes per-page, Python does not).
  Cache per request or pass `send_feature_flag_events=False`.
- **Session replay is the #1 cost line.** Default records 100% of
  sessions. Sample to 10%, set `minimum_duration_milliseconds=5000`,
  gate on a feature flag or target cohort.
- **Session replay PII masking only covers `<input>` elements** by
  default. Emails/SSNs in `<div>` are captured verbatim to S3. Add
  `ph-no-capture` class or `maskTextSelector`.
- **Forgetting `posthog.reset()` on logout** merges two users onto the
  same anonymous distinct_id permanently. One of the most common
  instrumentation bugs.
- **High-cardinality event *names*** (not properties) tank query
  perf — stores assume low cardinality. Put the dynamic part in
  `properties`, never in `event`.
- **Ingestion is eventually consistent** — 30s to 2 min healthy, up to
  15 min during incidents. Never build read-after-write product flows.
- **Group types are hard-capped at 5 per project.** Plan before you hit
  the ceiling.
- **Insights are cached 3-15 min.** Dashboards do not reflect events
  you just fired; force-refresh if testing.
- **HogQL query API has per-hour rate limits** (120/hr free, 1200/hr
  paid). Use the async query endpoint for heavy batch work.
- **Self-hosted is a full-time SRE job** — PostHog officially
  discourages new self-hosts unless data residency forces it.
- **Spending limits drop ingestion silently when hit** — capture keeps
  returning 200. Alert on the `/api/billing/` endpoint externally.
- **`google.generativeai` (old) is deprecated** — posthog.ai Gemini
  wrapper uses `google-genai` (new SDK) ≥ 0.3.0.

## Verification

```bash
python3 -c "
toolname='posthog'
c=open(f'/opt/OS/skills/tools/{toolname}/SKILL.md').read()
b=open(f'/opt/OS/skills/tools/{toolname}/references/best_practices.md').read()
assert len(c)>500 and '## Authentication' in c and '## Gotchas' in c
assert len(b)>2000
for s in ['Authentication','Core Operations','Pagination','Rate Limits',
          'Error Codes','SDK Idioms','Anti-Patterns','Data Model','Webhooks',
          'Limits','Cost Model','Version Pinning','Design Intent',
          'Problem-Solution Map','Operational Behavior','Ecosystem Position',
          'Trajectory','Conceptual Model','Industry Expert']:
    assert f'## {s}' in b, f'Missing {s}'
print('PASS')
"
```

See `references/best_practices.md` for the full 19-section reference.
