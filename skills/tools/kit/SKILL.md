---
name: kit
description: "Use when capturing email subscribers, sending broadcasts, building visual automations, managing tags/segments/sequences, importing purchases, configuring webhooks, or querying audience data via the Kit (formerly ConvertKit) V4 API for Initiate Arena lead nurture, personal brand newsletter, or Lyfe Spectrum announcements."
allowed-tools: "Read, Bash, Write, Edit, WebFetch"
version: 1.0
source_url: "https://developers.kit.com"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "V4"
sdk_version: "HTTP only (no first-party Python SDK; community libs: convertkit-python, joncalhoun/convertkit Go)"
speed_category: stable
trigger: both
effort: low
context: fork
---

# Tool: Kit (formerly ConvertKit)

## What This Tool Does

Kit is the email marketing and audience platform built by Nathan Barry for the
creator economy. Rebranded from ConvertKit in 2024, it positions itself less as
"email software" and more as the operating system for a creator business —
subscribers, tags, sequences, visual automations, broadcasts, landing pages,
forms, digital commerce, tip jar, and a built-in cross-newsletter recommendation
graph (Creator Network).

The V4 REST API (`api.kit.com/v4`) is the programmatic surface that lets EOS
treat Kit as the canonical audience store: every lead capture, every nurture
step, every broadcast, every tag-driven branch can be driven from Python.

Core capabilities exposed by the API:

- **Subscribers** — create, fetch, update, list, bulk-import, change state
  (`active`, `inactive`, `bounced`, `complained`, `cancelled`)
- **Tags** — create, list, attach to subscribers by id or email, remove
- **Sequences** (formerly "courses") — list, add subscribers by id or email
- **Broadcasts** — draft, schedule, send, fetch stats (opens, clicks, recipients)
- **Forms & Landing Pages** — list, subscribe by email
- **Custom Fields** — create, list, write per-subscriber
- **Purchases** — import e-commerce events for revenue attribution
- **Webhooks** — subscribe to subscriber/purchase/tag/link/form events
- **Account, Growth Stats, Email Templates** — read-only metadata

## EOS Integration

Kit is the audience layer for the entire EOS go-to-market motion. Antony is
solo, pre-revenue, and the binding constraint is leads-to-first-sale for
Initiate Arena. Kit is where every lead lands and every nurture happens.

Primary EOS uses:

- **Initiate Arena lead nurture** — outreach replies that opt in get tagged
  `initiate-arena-lead`, dropped into a 7-email warmup sequence, branched by
  reply behavior. Tag transitions drive Calendly booking handoff.
- **Personal brand newsletter** — Antony's main marketing vehicle. Weekly
  broadcast to the full active list, segmented by interest tags
  (`tactical-luxury`, `lyfe-maxing`, `solo-founder`).
- **Lyfe Spectrum drops** — apparel announcements as broadcasts to the
  `spectrum-interest` tag, with purchase imports flowing back via webhook.
- **Lead magnet → automation** — opt-in form delivers PDF, fires `lm-{slug}`
  tag, enters a Visual Automation that nurtures and qualifies for the Arena.
- **Reply mining** — `subscriber.link_click` webhooks pipe into EOS memory so
  the cognitive loop knows which leads engaged with which CTAs.

Canonical EOS pattern:

- API key in `eos_ai/.env` as `KIT_API_KEY` (personal automation, not OAuth app)
- Base URL pinned: `https://api.kit.com/v4`
- All calls go through a `kit_client.py` wrapper that injects the
  `X-Kit-Api-Key` header, handles 429 backoff, and unwraps cursor pagination
- Every subscriber action writes a memory event so cognitive_loop can correlate
  outreach activity with audience movement

## Authentication

Kit V4 supports two auth modes:

**API Key (personal use — what EOS uses):**

```bash
curl https://api.kit.com/v4/account \
  -H "X-Kit-Api-Key: $KIT_API_KEY"
```

- Issued from Account → Advanced → API
- 120 requests / 60s rolling window per key
- No scopes — full read/write on the owning account
- Cannot be used to publish a public app on the Kit integrations directory

**OAuth 2.0 (apps for the integrations directory):**

```
Authorization endpoint: https://app.kit.com/oauth/authorize
Token endpoint:         https://api.kit.com/oauth/token
Header on calls:        Authorization: Bearer <access_token>
```

- Required for any multi-tenant or marketplace listing
- 600 requests / 60s rolling window per access token
- Scopes are coarse — current public scope is effectively `public` (full
  account read/write within the granting user's account)
- Refresh tokens supported; access tokens expire and must be refreshed

EOS rule: solo-founder context → API key. If/when Empyrean Studio packages an
EOS-as-SaaS offering that integrates a client's Kit account, switch to OAuth.

## Quick Reference

All examples assume `export KIT_API_KEY=...` and `BASE=https://api.kit.com/v4`.

**Create a subscriber (with custom fields):**

```bash
curl -X POST $BASE/subscribers \
  -H "Content-Type: application/json" \
  -H "X-Kit-Api-Key: $KIT_API_KEY" \
  -d '{
    "first_name": "Alice",
    "email_address": "alice@example.com",
    "state": "active",
    "fields": {"Source": "outreach-batch-2026-04", "Funnel": "initiate-arena"}
  }'
```

**Tag a subscriber by email:**

```bash
curl -X POST $BASE/tags/$TAG_ID/subscribers \
  -H "Content-Type: application/json" \
  -H "X-Kit-Api-Key: $KIT_API_KEY" \
  -d '{"email_address": "alice@example.com"}'
```

**Add to a sequence by email:**

```bash
curl -X POST $BASE/sequences/$SEQUENCE_ID/subscribers \
  -H "Content-Type: application/json" \
  -H "X-Kit-Api-Key: $KIT_API_KEY" \
  -d '{"email_address": "alice@example.com"}'
```

**Create + schedule a broadcast:**

```bash
curl -X POST $BASE/broadcasts \
  -H "Content-Type: application/json" \
  -H "X-Kit-Api-Key: $KIT_API_KEY" \
  -d '{
    "subject": "The structure no one teaches you",
    "content": "<p>Hey {{ subscriber.first_name }} ...</p>",
    "public": false,
    "send_at": "2026-04-08T13:00:00Z"
  }'
```

**Python pattern (drop-in for `eos_ai/kit_client.py`):**

```python
import os, time, requests
BASE = "https://api.kit.com/v4"
H = {"X-Kit-Api-Key": os.environ["KIT_API_KEY"],
     "Content-Type": "application/json"}

def kit(method: str, path: str, **kw):
    for attempt in range(5):
        r = requests.request(method, f"{BASE}{path}", headers=H, timeout=30, **kw)
        if r.status_code == 429:
            time.sleep(2 ** attempt)
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"Kit {method} {path} exhausted retries")

def paginate(path: str, key: str):
    after = None
    while True:
        params = {"after": after} if after else {}
        data = kit("GET", path, params=params)
        for item in data.get(key, []):
            yield item
        pg = data.get("pagination", {})
        if not pg.get("has_next_page"):
            return
        after = pg.get("end_cursor")
```

## Conceptual Model

Kit's data model is opinionated and very different from list-based platforms
like Mailchimp. Internalize this or you will fight it forever:

- **One audience, many tags.** There are no "lists." Every subscriber lives in
  one global pool. Segmentation is achieved entirely through **tags** and
  **custom fields**. A subscriber on "the Initiate Arena list" is really a
  subscriber with the `initiate-arena` tag.
- **Subscribers have a `state`.** `active` (billable + receives email),
  `inactive` (unsubscribed but record retained), `bounced`, `complained`,
  `cancelled`. You only pay for active subscribers.
- **Sequences are time-based drips.** Each step has a delay; subscribers move
  through linearly. Use for evergreen welcome / lead-magnet delivery.
- **Visual Automations are the brain.** A node graph with triggers (tag added,
  form filled, sequence completed, link clicked, purchase made), filters,
  actions (add tag, subscribe to sequence, send broadcast, wait, branch).
  Sequences are dumb pipes; Automations are where logic lives.
- **Broadcasts are one-shots.** Sent to a filter (tag intersection). Can be
  scheduled, A/B tested on subject, resent to non-openers.
- **Forms are subscribe surfaces** that own a default sequence and default tag.
  Landing pages are just hosted forms.
- **Custom fields are per-subscriber key/value.** Use sparingly — they bloat
  the subscriber payload and are not indexed for fast filtering.

The mental flip from Mailchimp/Beehiiv: stop thinking "what list is this
person on?" Start thinking "what tags do they have, and what automation are
they in?" Tags are cheap. Use them liberally for state, sparingly for content
preference, and never for things a custom field would express better.

## Gotchas

- **V3 → V4 migration.** `api.convertkit.com/v3` still answers but is in
  hard-deprecation. V3 used `api_secret` query param + offset pagination; V4
  uses `X-Kit-Api-Key` header + cursor pagination. They are not drop-in
  compatible. Pin `BASE = https://api.kit.com/v4` everywhere.
- **Cursor pagination only.** No `page=2`. Use `after=<end_cursor>` from the
  previous response's `pagination` object. Iterate until `has_next_page=false`.
- **Rate limits are per-key, not per-IP.** 120 req/min for API keys, 600/min
  for OAuth tokens. 429 returns no `Retry-After` — implement exponential
  backoff yourself.
- **Tag explosion.** Kit has no hard cap on tag count, but the UI degrades past
  ~200 tags and Visual Automation pickers become unusable. Adopt a strict
  taxonomy: `source-*`, `funnel-*`, `interest-*`, `state-*`, `lm-*`. Audit
  monthly.
- **Double opt-in defaults.** Forms default to double opt-in. Subscribers
  created via API land in `active` state immediately and skip confirmation —
  this is intentional but means you bypass the deliverability protection of
  confirmation. Only API-create subscribers you trust the source of.
- **Email field is case-insensitive but stored as entered.** Don't dedupe in
  your code on raw string equality; lowercase before compare.
- **`subscriber_id` is not the same as `email_address`.** Most endpoints
  accept either, but bulk operations only accept ids. Cache the id on first
  create.
- **Broadcasts cannot be edited after sending.** Schedule, then if you need
  to fix, cancel via UI before `send_at`. There is no "unsend."
- **Deliverability is not magic.** Kit has good shared IPs but a cold list
  blasted with a 10K broadcast on day one will tank your reputation. Warm up:
  start with engaged segments, scale daily volume gradually.
- **Custom field names are the key.** If you rename a custom field in the UI,
  every API payload referencing the old name silently drops the value. Treat
  custom field names as immutable schema.
- **Webhook deliveries do not retry indefinitely.** A few retries on 5xx then
  drop. Make your receiver idempotent and fast (<10s).
- **No first-party Python SDK.** Community libraries exist but lag the API.
  Use `requests` directly — it's a clean REST API and the wrapper is ~50 lines.

---

See references/best_practices.md for the full 19-section creator-level knowledge base.
