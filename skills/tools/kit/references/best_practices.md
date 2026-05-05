# Kit — Creator-Level Best Practices
Source: https://developers.kit.com
API Version: V4
SDK Version: HTTP only (no first-party Python SDK)
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## Authentication

Kit V4 supports two authentication modes. Choose based on whether you are
automating your own account (API key) or building a multi-tenant integration
that other Kit users install (OAuth).

### API Key (personal automation)

API keys are issued from the Kit dashboard at:
`Account → Settings → Advanced → API`

Each account can hold multiple keys; rotate by issuing a new one and revoking
the old. Keys are bearer secrets — anyone with the key has full read/write on
the account. Store in `eos_ai/.env` as `KIT_API_KEY` and never commit.

Header on every request:

```
X-Kit-Api-Key: <key>
```

```bash
curl https://api.kit.com/v4/account \
  -H "X-Kit-Api-Key: $KIT_API_KEY"
```

Successful response:

```json
{
  "account": {
    "name": "Antony F Munoz",
    "plan_type": "creator",
    "primary_email_address": "afm@munoz.co",
    "created_at": "2025-08-14T19:03:11Z"
  }
}
```

API keys are personal-use only. Per Kit's policy you cannot publish a public
app on the integrations directory using an API key — that path requires OAuth.

### OAuth 2.0 (apps + integrations)

Three-legged OAuth with the standard authorization-code flow.

- Authorization endpoint: `https://app.kit.com/oauth/authorize`
- Token endpoint: `https://api.kit.com/oauth/token`
- Header on calls: `Authorization: Bearer <access_token>`

Step 1 — redirect the user to:

```
https://app.kit.com/oauth/authorize
  ?client_id=<your_client_id>
  &redirect_uri=<your_callback>
  &response_type=code
  &state=<csrf_token>
```

Step 2 — exchange the returned `code` for a token:

```bash
curl -X POST https://api.kit.com/oauth/token \
  -d 'grant_type=authorization_code' \
  -d 'client_id=<id>' \
  -d 'client_secret=<secret>' \
  -d 'code=<code>' \
  -d 'redirect_uri=<callback>'
```

Response:

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "expires_in": 7200,
  "created_at": 1712409600
}
```

Step 3 — refresh when expired:

```bash
curl -X POST https://api.kit.com/oauth/token \
  -d 'grant_type=refresh_token' \
  -d 'refresh_token=<refresh>' \
  -d 'client_id=<id>' \
  -d 'client_secret=<secret>'
```

Scopes are coarse in V4. There is effectively one public scope that grants
the app full access to the granting user's account. Kit has not yet shipped
the per-resource scope granularity that Stripe or Google offer.

EOS uses API key. Switch to OAuth only if Empyrean Studio packages a
Kit-integrated SaaS offering for clients.

## Core Operations with Exact Signatures

Base URL for every endpoint below: `https://api.kit.com/v4`.

All examples use API key auth (`X-Kit-Api-Key: $KIT_API_KEY`). For OAuth,
substitute `Authorization: Bearer $TOKEN`.

### Subscribers

**Create a subscriber**

```
POST /subscribers
```

```bash
curl -X POST https://api.kit.com/v4/subscribers \
  -H "Content-Type: application/json" \
  -H "X-Kit-Api-Key: $KIT_API_KEY" \
  -d '{
    "first_name": "Alice",
    "email_address": "alice@example.com",
    "state": "active",
    "fields": {
      "Last name": "Lamarr",
      "Birthday": "Feb 17"
    }
  }'
```

Response:

```json
{
  "subscriber": {
    "id": 1234567,
    "first_name": "Alice",
    "email_address": "alice@example.com",
    "state": "active",
    "created_at": "2026-04-06T12:00:00Z",
    "fields": {"Last name": "Lamarr", "Birthday": "Feb 17"}
  }
}
```

If the email already exists, Kit returns the existing subscriber rather than
creating a duplicate. This makes the call idempotent on email.

**Get a subscriber**

```
GET /subscribers/{id}
```

**List subscribers** (cursor-paginated, filterable)

```
GET /subscribers?per_page=500&status=active&created_after=2026-01-01T00:00:00Z
```

Optional filters: `email_address`, `status`, `created_after`, `created_before`,
`updated_after`, `updated_before`, `tagged_after`, `tagged_before`,
`per_page` (max 500), `after`, `before`.

**Update a subscriber**

```
PUT /subscribers/{id}
```

```bash
curl -X PUT https://api.kit.com/v4/subscribers/1234567 \
  -H "Content-Type: application/json" \
  -H "X-Kit-Api-Key: $KIT_API_KEY" \
  -d '{"first_name":"Alicia","fields":{"Funnel":"initiate-arena-qualified"}}'
```

**Unsubscribe**

```
POST /subscribers/{id}/unsubscribe
```

**Bulk create**

```
POST /bulk/subscribers
```

Body accepts `subscribers: [{...}, ...]` up to 1000 per call. Returns a
bulk action id you can poll.

### Tags

**Create**

```
POST /tags
{ "name": "initiate-arena-lead" }
```

**List**

```
GET /tags
```

**Tag a subscriber by id**

```
POST /tags/{tag_id}/subscribers/{subscriber_id}
```

**Tag a subscriber by email**

```
POST /tags/{tag_id}/subscribers
{ "email_address": "alice@example.com" }
```

**Remove a tag**

```
DELETE /tags/{tag_id}/subscribers/{subscriber_id}
```

**List subscribers with a tag**

```
GET /tags/{tag_id}/subscribers?per_page=500&after=<cursor>
```

### Sequences

**List sequences**

```
GET /sequences
```

**Add subscriber to sequence by id**

```
POST /sequences/{sequence_id}/subscribers/{subscriber_id}
```

**Add subscriber to sequence by email**

```
POST /sequences/{sequence_id}/subscribers
{ "email_address": "alice@example.com" }
```

**List subscribers in a sequence**

```
GET /sequences/{sequence_id}/subscribers
```

### Broadcasts

**List broadcasts**

```
GET /broadcasts
```

**Create a broadcast**

```
POST /broadcasts
```

```bash
curl -X POST https://api.kit.com/v4/broadcasts \
  -H "Content-Type: application/json" \
  -H "X-Kit-Api-Key: $KIT_API_KEY" \
  -d '{
    "subject": "The structure no one teaches you",
    "preview_text": "Three rules for tactical luxury living",
    "content": "<p>Hey {{ subscriber.first_name }} ...</p>",
    "description": "Internal label - 2026-04-08 newsletter",
    "public": false,
    "published_at": null,
    "send_at": "2026-04-08T13:00:00Z",
    "email_template_id": null,
    "subscriber_filter": [
      { "all": [{ "type": "tag", "ids": [12345] }] }
    ]
  }'
```

Response includes the new broadcast id. To send immediately, set `send_at`
to the current time. To save as draft, omit `send_at`.

**Get broadcast stats**

```
GET /broadcasts/{id}/stats
```

Response includes `recipients`, `open_rate`, `click_rate`, `unsubscribes`,
`total_clicks`, `show_total_clicks`, `status`, `progress`.

**Update / delete**

```
PUT    /broadcasts/{id}
DELETE /broadcasts/{id}
```

Only allowed before send.

### Forms

**List**

```
GET /forms
```

**Subscribe by email**

```
POST /forms/{form_id}/subscribers
{ "email_address": "alice@example.com", "first_name": "Alice" }
```

If the form has double opt-in enabled, the subscriber lands in pending
state and only becomes active after clicking the confirmation email.

### Custom Fields

**Create**

```
POST /custom_fields
{ "label": "Funnel" }
```

**List**

```
GET /custom_fields
```

**Update**

```
PUT /custom_fields/{id}
{ "label": "Funnel Stage" }
```

WARNING: renaming a custom field invalidates every existing API payload that
referenced the old label. The values are not migrated automatically in
subscriber records — they remain under the old key inside the existing
subscriber JSON until you write a new value.

### Purchases

**Create a purchase** (e-commerce import for revenue attribution)

```
POST /purchases
```

```bash
curl -X POST https://api.kit.com/v4/purchases \
  -H "Content-Type: application/json" \
  -H "X-Kit-Api-Key: $KIT_API_KEY" \
  -d '{
    "purchase": {
      "transaction_id": "lyfe-spectrum-0042",
      "email_address": "alice@example.com",
      "first_name": "Alice",
      "currency": "USD",
      "transaction_time": "2026-04-06T15:30:00Z",
      "subtotal": 89.00,
      "tax": 7.12,
      "shipping": 8.00,
      "discount": 0.00,
      "total": 104.12,
      "status": "paid",
      "products": [
        {
          "name": "Lyfe Spectrum Tactical Tee",
          "sku": "LST-BLK-L",
          "pid": 4242,
          "lid": 1,
          "unit_price": 89.00,
          "quantity": 1
        }
      ]
    }
  }'
```

**List**

```
GET /purchases?per_page=500
```

### Webhooks

**Create**

```
POST /webhooks
{
  "target_url": "https://eos.afm.dev/kit/webhook",
  "event": { "name": "subscriber.subscriber_activate" }
}
```

**List / delete**

```
GET    /webhooks
DELETE /webhooks/{id}
```

### Account / Growth

```
GET /account
GET /account/growth_stats?starting=2026-01-01&ending=2026-04-06
```

## Pagination Patterns

V4 is **cursor-based only**. There is no `page=2`. Every list endpoint returns:

```json
{
  "subscribers": [ ... ],
  "pagination": {
    "has_previous_page": false,
    "has_next_page": true,
    "start_cursor": "MQ==",
    "end_cursor": "NTAw",
    "per_page": 500
  }
}
```

To walk forward, pass `?after=<end_cursor>` on the next call. To walk
backward, pass `?before=<start_cursor>`. Stop when `has_next_page` is false.

`per_page` defaults to 50; max is 500. Always use 500 for bulk reads.

Python helper:

```python
def paginate(path, key, params=None):
    params = dict(params or {})
    params.setdefault("per_page", 500)
    after = None
    while True:
        if after:
            params["after"] = after
        data = kit("GET", path, params=params)
        for item in data.get(key, []):
            yield item
        pg = data.get("pagination", {})
        if not pg.get("has_next_page"):
            return
        after = pg["end_cursor"]
```

Anti-pattern: trying to compute total pages or random-access page N. Cursors
are opaque and you must walk sequentially.

## Rate Limits

- **API key:** 120 requests / rolling 60 seconds, per key.
- **OAuth access token:** 600 requests / rolling 60 seconds, per token.
- Applies to both V3 and V4 endpoints.
- 429 response with no body when exceeded.
- No `Retry-After` header — back off yourself.

Recommended backoff: exponential with jitter, capped at 60s, max 5 retries.

```python
import random, time
def backoff(attempt):
    time.sleep(min(60, (2 ** attempt) + random.random()))
```

If you need to import a list of 50K subscribers, use the bulk endpoint
(`POST /bulk/subscribers`) — one call up to 1000 records — rather than 50K
individual creates. Otherwise you will hit the rate limit and the import
will take ~7 hours minimum.

## Error Codes and Recovery

| Status | Meaning | Recovery |
|--------|---------|----------|
| 200 / 201 | Success | — |
| 400 | Bad request — malformed JSON or missing required field | Fix payload, do not retry |
| 401 | Auth failure — bad/missing/revoked key or expired OAuth token | Refresh token (OAuth) or rotate key |
| 402 | Payment required — account past due or plan downgraded below API access | Surface to user; the API key remains valid but writes are blocked |
| 403 | Forbidden — endpoint requires a higher plan or the resource is not yours | Do not retry |
| 404 | Resource not found | Verify id; do not retry |
| 422 | Validation error — Kit returns `errors` array with field-level detail | Fix payload, do not retry |
| 429 | Rate limited | Exponential backoff |
| 500 / 502 / 503 / 504 | Kit-side error | Retry with backoff up to 5 attempts |

422 response shape:

```json
{ "errors": ["Email address has already been taken"] }
```

Always log the request id from the `X-Request-Id` response header when
opening a Kit support ticket.

## SDK Idioms

There is **no first-party Python SDK**. Kit ships official guidance for
direct HTTP. Community libraries:

- `convertkit-python` (PyPI) — covers V3 well, partial V4
- `joncalhoun/convertkit` (Go) — V3 only, well-maintained
- `convertkit/convertkitapi` (PHP, Composer) — official-ish, V3 + partial V4

EOS rule: use `requests` directly. The wrapper is ~50 lines, you avoid
dependency drift, and the API is clean enough that an SDK adds little.

Canonical EOS client (`eos_ai/kit_client.py`):

```python
import os, time, random, requests
from typing import Iterator, Any

BASE = "https://api.kit.com/v4"

class KitClient:
    def __init__(self, api_key: str | None = None):
        self.key = api_key or os.environ["KIT_API_KEY"]
        self.session = requests.Session()
        self.session.headers.update({
            "X-Kit-Api-Key": self.key,
            "Content-Type": "application/json",
            "User-Agent": "EOS/1.0 (kit_client)",
        })

    def _call(self, method: str, path: str, **kw) -> dict:
        for attempt in range(5):
            r = self.session.request(method, f"{BASE}{path}", timeout=30, **kw)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(min(60, (2 ** attempt) + random.random()))
                continue
            if not r.ok:
                raise RuntimeError(f"Kit {method} {path} {r.status_code}: {r.text}")
            return r.json() if r.content else {}
        raise RuntimeError(f"Kit {method} {path} exhausted retries")

    def upsert_subscriber(self, email: str, first_name: str = "", **fields) -> dict:
        return self._call("POST", "/subscribers", json={
            "email_address": email.lower(),
            "first_name": first_name,
            "state": "active",
            "fields": fields,
        })["subscriber"]

    def tag(self, tag_id: int, email: str) -> None:
        self._call("POST", f"/tags/{tag_id}/subscribers",
                   json={"email_address": email.lower()})

    def add_to_sequence(self, sequence_id: int, email: str) -> None:
        self._call("POST", f"/sequences/{sequence_id}/subscribers",
                   json={"email_address": email.lower()})

    def paginate(self, path: str, key: str, **params) -> Iterator[Any]:
        params.setdefault("per_page", 500)
        after = None
        while True:
            if after:
                params["after"] = after
            data = self._call("GET", path, params=params)
            yield from data.get(key, [])
            pg = data.get("pagination", {})
            if not pg.get("has_next_page"):
                return
            after = pg["end_cursor"]
```

## Anti-Patterns

- **Polling instead of webhooks.** If you need to react to a tag add, do not
  poll `/tags/{id}/subscribers` every minute. Subscribe to
  `subscriber.tag_add` once and let Kit push.
- **One subscriber-create call per row in a CSV.** Use `POST /bulk/subscribers`.
- **Caching tag ids by name in code.** Tag ids are stable; cache them in a
  config table or env vars, not in source. When a tag is renamed in the UI
  the id stays — refer to it by id.
- **Treating sequences as the brain.** Sequences are linear. Use Visual
  Automations for any branching logic. Calling Kit "send to sequence A or B
  based on tag X" from Python is fragile — express it once as an automation.
- **Storing subscriber state in a parallel database.** Kit is the source of
  truth for audience state. Mirror only what your cognitive loop needs to
  reason about (e.g. last_engaged_at), and refresh from Kit nightly.
- **Using V3 for new code.** Even though `api.convertkit.com/v3` still answers,
  it is on the deprecation path. Every new EOS module hits V4.
- **Sending broadcasts to the entire active list cold.** Warm up: start
  with engaged segments (`opened_in_last_30_days`), expand outward.
- **Treating custom field names as mutable.** They are schema. Pick the name
  once. Add a new field rather than rename.

## Data Model

```
Account
 ├─ Subscribers           (the global pool)
 │   ├─ state             (active|inactive|bounced|complained|cancelled)
 │   ├─ fields            (per-subscriber custom field key/value)
 │   ├─ tags              (many-to-many)
 │   ├─ subscriptions     (sequence enrollments + position)
 │   └─ purchases         (e-commerce events)
 ├─ Tags                  (flat namespace, no hierarchy)
 ├─ Custom Fields         (schema, account-wide)
 ├─ Forms / Landing Pages (subscribe surfaces)
 ├─ Sequences             (linear time-delayed drips)
 ├─ Visual Automations    (node graphs — not exposed via API)
 ├─ Broadcasts            (one-shot sends with tag-based filters)
 ├─ Email Templates       (reusable HTML shells)
 └─ Webhooks              (push notifications to your endpoint)
```

The critical insight: **Subscribers** is one global pool. There is no concept
of a "list" or "audience" that contains a subset. All segmentation is
expressed via tags + custom fields + state filters.

Visual Automations are first-class objects in the UI but **not directly
manipulable via the API** — you cannot create or edit an automation through
HTTP. You can only fire its triggers (by adding a tag, completing a sequence,
etc.) and observe its effects.

## Webhooks and Events

Create:

```bash
curl -X POST https://api.kit.com/v4/webhooks \
  -H "Content-Type: application/json" \
  -H "X-Kit-Api-Key: $KIT_API_KEY" \
  -d '{
    "target_url": "https://eos.afm.dev/kit/webhook",
    "event": { "name": "subscriber.subscriber_activate" }
  }'
```

Available events:

| Event name | Required parameter | Fires when |
|---|---|---|
| `subscriber.subscriber_activate` | — | Subscriber confirms / becomes active |
| `subscriber.subscriber_unsubscribe` | — | Subscriber unsubscribes |
| `subscriber.subscriber_bounce` | — | Hard bounce recorded |
| `subscriber.subscriber_complain` | — | Spam complaint received |
| `subscriber.form_subscribe` | `form_id` | Subscriber fills the named form |
| `subscriber.course_subscribe` | `sequence_id` | Subscriber added to sequence |
| `subscriber.course_complete` | `sequence_id` | Subscriber finishes sequence |
| `subscriber.link_click` | `initiator_value` (URL) | Subscriber clicks a tracked link |
| `subscriber.product_purchase` | `product_id` | Subscriber buys a Kit Commerce product |
| `subscriber.tag_add` | `tag_id` | Tag attached to subscriber |
| `subscriber.tag_remove` | `tag_id` | Tag removed from subscriber |
| `purchase.purchase_create` | — | Any purchase imported |

Delivery:

- Kit POSTs JSON to your `target_url`
- Retries on 5xx for a small bounded number of attempts (not indefinite)
- No HMAC signature in V4 yet — verify by IP allowlist or by including a
  shared secret in the URL (`?secret=...`)
- Receivers MUST be idempotent and respond <10s

Payload example for `subscriber.tag_add`:

```json
{
  "subscriber": {
    "id": 1234567,
    "email_address": "alice@example.com",
    "first_name": "Alice",
    "state": "active",
    "created_at": "2026-04-06T12:00:00Z",
    "tag": { "id": 12345, "name": "initiate-arena-lead" }
  }
}
```

## Limits

- **Subscribers per account:** no hard cap; the plan determines pricing
  brackets but the API will accept arbitrary growth.
- **Tags per account:** no hard cap; UI degrades past ~200.
- **Custom fields per account:** no hard published cap; practical limit ~50
  before subscriber payloads become unwieldy.
- **Bulk create batch:** 1000 subscribers per `POST /bulk/subscribers` call.
- **Per-page list size:** max 500.
- **Rate limit:** 120/min API key, 600/min OAuth.
- **Webhook receiver timeout:** ~10s before Kit considers the delivery failed.
- **Broadcast send rate:** Kit throttles broadcasts internally based on shared
  IP capacity; for large lists a send can take minutes to dispatch fully.
- **Free plan API access:** the Newsletter (free) plan can use the API but
  some endpoints (advanced reporting, certain commerce features) gate behind
  Creator / Creator Pro.

## Cost Model

Pricing as of 2026 (subject to change — confirm at https://kit.com/pricing):

| Plan | Monthly | Subscribers | API access | Notable features |
|---|---|---|---|---|
| Newsletter (free) | $0 | up to 10,000 | Yes | Unlimited landing pages, forms, broadcasts; tagging; sell digital products; no automations; no Creator Network |
| Creator | from $39/mo (1K) | tiered | Yes | Visual Automations, Sequences, Creator Network, integrations, 1 team member, live chat |
| Creator Pro | from $79/mo (1K) | tiered | Yes | Subscriber scoring, advanced reporting, newsletter referral system, Facebook custom audiences, deliverability reporting, unlimited team |

Annual billing ≈ 16% off (2 months free). 14-day free trial of paid plans.
30-day money-back guarantee.

EOS-relevant tier choice: **Creator** is the minimum for Initiate Arena
nurture because Visual Automations are essential. Stay on Creator until the
list crosses 5K active or until subscriber scoring becomes load-bearing for
qualifying Arena leads — then upgrade to Creator Pro.

## Version Pinning

- **V3** (`api.convertkit.com/v3/...`) — legacy. Auth via `api_secret` query
  parameter. Offset-based pagination. Still answers requests but is on the
  deprecation path. Do not start new code on V3.
- **V4** (`api.kit.com/v4/...`) — current GA. Auth via `X-Kit-Api-Key` header
  or OAuth bearer. Cursor-based pagination. New endpoints (custom fields,
  improved purchases, webhooks v2) only exist on V4.

EOS rule: every new module pins `BASE = "https://api.kit.com/v4"`. If you
encounter V3 code, migrate it during the next touch.

The hostname matters — `api.convertkit.com` is V3-only and `api.kit.com` is
V4-only. They are not the same gateway with a version prefix; they are
different services.

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

Kit was built by Nathan Barry in 2013 specifically because Mailchimp was
list-centric and creators needed tag-centric. Barry's thesis: the unit of
the creator economy is **the audience relationship**, not "the list this
person is on." Every product decision flows from this.

Tradeoffs Kit accepts as a result:

- **No native lists.** Newcomers find this disorienting. Kit has consistently
  refused to add lists despite years of feature requests because lists would
  fragment the audience and break the single-pool model that makes tags work.
- **Templates are deliberately spartan.** Kit's email templates default to
  plain-text-styled HTML. Barry has written publicly that this is intentional:
  plain emails feel personal, ship faster, deliver better, and let the words
  carry the message. Mailchimp's visual builder is the explicit anti-pattern.
- **Visual Automations over conditionals in code.** The branching logic lives
  in a node graph the creator can see. The API deliberately does not let you
  create or edit automations programmatically — Kit wants the creator to
  reason about their funnel visually.
- **Creator Network as a moat.** No other email platform has a built-in
  cross-recommendation graph. This is the network effect Kit is betting the
  rebrand on.
- **Commerce baked in.** Kit Commerce + Tip Jar mean a creator can sell
  digital products and accept tips without ever touching Stripe, Gumroad,
  or Shopify. Margin is lower than DIY but the integration is zero-friction.

The cost of these choices: Kit is opinionated. If your mental model is
"campaigns sent to lists," you will fight Kit at every step. If your mental
model is "tags express state and automations express logic," Kit feels
frictionless.

## Problem-Solution Map and Hidden Capabilities

| Problem | Kit's solution | Hidden depth |
|---|---|---|
| Lead capture | Forms + landing pages | Forms can be embedded, modal, slide-in, sticky bar — all configured per-form |
| Lead delivery (PDF, video) | Form's "incentive email" auto-fires the asset | Asset URL can be a magic link Kit signs |
| Welcome sequence | Sequences | Email-by-email A/B testing of subject lines |
| Branching nurture | Visual Automations | Wait-until-condition nodes, RSS triggers, link-click branches |
| Cross-promotion | Creator Network recommendations | After-subscribe modal with reciprocal recommendations from creators in the network — drives organic growth without paid ads |
| Newsletter referrals | Sparkloop-style referral program (Creator Pro) | Built into broadcasts as a Creator Pro feature |
| Commerce | Kit Commerce | Sell PDFs, templates, courses, paid newsletters; recurring subscriptions; coupon codes |
| Tip Jar | Standalone tip page per creator | Zero setup; revenue lands in Kit-managed Stripe account |
| Sponsor matching | Sponsor Network | Brands can place sponsorships in qualifying creator newsletters; Kit takes a cut |
| Subscriber scoring | Creator Pro | Heuristic score based on opens/clicks/recency; queryable via tag-like filter |
| Deliverability dashboard | Creator Pro | IP reputation, spam-trap hits, ISP-level inbox placement |
| Multiple authors / team | Creator (1 seat), Pro (unlimited) | Per-seat permissioning |

The capabilities most creators do not realize they already have:

- **Subscriber engagement scoring** — Creator Pro auto-computes a 0-10 score
  per subscriber. Use it to define a "warm" segment for Initiate Arena
  outreach prioritization.
- **Link triggers** — any tracked link in any email can fire a tag add
  automatically. This is the cleanest way to capture interest signals.
- **Sequence-level A/B testing** — for evergreen welcome flows, test subject
  lines on each sequence step independently.
- **RSS-to-email** — Kit can poll an RSS feed and broadcast on new items.
  Useful for syncing the personal-brand blog to the newsletter automatically.
- **Snippet library** — reusable text blocks that can be edited once and
  updated everywhere they appear.

## Operational Behavior and Edge Cases

- **Deliverability.** Kit uses shared IP pools managed for the platform. New
  accounts inherit the pool reputation, which is generally strong. A single
  account sending spammy content can degrade the pool for neighbors, so Kit
  is aggressive about complaint thresholds — accounts past 0.3% complaint
  rate get throttled. Stay under by warming up cold lists and never importing
  unconfirmed emails in bulk.
- **Double opt-in.** Forms default to double opt-in. API-created subscribers
  bypass this and land in `active` state immediately. The deliverability
  protection of confirmation is a real thing — only API-create when you trust
  the source (e.g. paid customer, manually verified outreach reply).
- **GDPR.** Kit is GDPR-compliant. Subscribers have a data-export right and
  a right-to-erasure. The API exposes hard-delete, not just unsubscribe.
  EU-origin subscribers should always go through double opt-in to satisfy
  the consent record.
- **Bounce handling.** Hard bounces auto-flip the subscriber to `bounced`
  state. Soft bounces are retried by Kit; after several consecutive soft
  bounces over a window, Kit flips to `bounced`.
- **Complaint handling.** Spam complaints flip to `complained` state and
  the subscriber is excluded from all future sends. There is no resurrection
  path — if the user re-subscribes via a form, Kit creates a new record.
- **IP warmup for migration.** If you're migrating from another platform with
  >5K subscribers, contact Kit support — they will guide a multi-day warmup
  to avoid reputation damage.
- **Time zones.** All API timestamps are ISO 8601 UTC. Broadcast `send_at`
  is interpreted in UTC; the dashboard shows it in account time zone.
- **Timestamp drift.** Webhook payload timestamps can lag the actual event
  by a few seconds. Don't use them as causal ordering.

## Ecosystem Position and Composition

| Platform | Best for | Where it loses to Kit |
|---|---|---|
| **Mailchimp** | Small business, e-commerce, list-based marketing | List-centric model fights creator workflows; visual builder seduces toward bloated emails; pricing scales worse |
| **Beehiiv** | Newsletter-first creators chasing growth | No native automations; segmentation weaker; Creator Network does not exist; younger product, fewer integrations |
| **Substack** | Pure publishing + paid newsletters | No tags, no automations, no API, no segmentation; you do not own the data layer; Substack takes 10% |
| **MailerLite** | Budget-conscious small senders | Cheaper at low volume; thinner automations; no Creator Network; smaller integration surface |
| **Customer.io** | Product-led companies needing event-driven messaging | More powerful event model; vastly more expensive; built for engineering teams not creators; requires writing Liquid |
| **ActiveCampaign** | Sales-led B2B with CRM needs | More CRM features; clunkier UI; learning curve; not creator-aligned |
| **HubSpot** | Enterprise inbound marketing | Real CRM, much heavier, much more expensive, total overkill for a creator |

Where Kit composes well in EOS:

- **Calendly** — opt-in tags trigger Calendly booking link delivery via
  sequence; replies to outreach feed both
- **Stripe** — Kit Commerce handles digital products natively; for physical
  goods (Lyfe Spectrum) use Shopify and import purchases via the Kit API
- **Notion** — campaign briefs in Notion, executed in Kit, results pulled
  back via broadcast stats endpoint into the EOS memory
- **Apify** — outreach replies scraped → emails passed to Kit → tagged → nurtured
- **Discord** — `subscriber.tag_add` webhook posts to Discord so Antony sees
  every new lead in real time

## Trajectory and Evolution

Kit's strategic direction since the 2024 rebrand:

- **From email tool to creator OS.** The rebrand was explicit: drop "email"
  from the name, position as the operating layer for a creator business.
- **Creator Network as the moat.** Kit is investing heavily in the
  recommendation graph because it's the one feature competitors cannot
  trivially copy — it requires a network of creators already on the platform.
- **Commerce push.** Kit Commerce + Tip Jar + paid recommendations are
  building toward a future where Kit takes a small percentage of creator
  revenue across multiple monetization surfaces, not just the SaaS fee.
- **Sponsor Network.** Brand sponsorships matched to qualifying creators —
  Kit becomes a media-buying surface as well as a sending platform.
- **API maturation.** V4 was a clean break to enable better third-party
  integrations. Webhooks v2, custom fields, and improved cursor pagination
  are all V4-only. Expect more V4-only endpoints (automation triggers, deeper
  reporting) over the next 12–18 months.
- **AI features.** Kit has begun shipping subject-line generation, send-time
  optimization, and audience-summary AI features. None are exposed via API yet.

What this means for EOS: build against V4, lean on Creator Network as a
free distribution channel for the personal brand, and treat Kit as the
canonical audience store rather than mirroring it locally.

## Conceptual Model and Solution Recipes

### Recipe: Lead magnet → tag → nurture sequence

1. Create a Form in Kit with the incentive email pointed at the lead magnet PDF
2. Create a Tag `lm-{slug}` (e.g. `lm-tactical-luxury-guide`)
3. In Visual Automations, create a flow:
   - Trigger: subscribes to form
   - Action: add tag `lm-tactical-luxury-guide`
   - Action: subscribe to Sequence "Tactical Luxury Welcome (5 emails)"
   - Filter (after sequence completes): if `link_click` on the Initiate Arena
     CTA → add tag `initiate-arena-warm`
   - Action: subscribe to Sequence "Initiate Arena Soft Pitch (3 emails)"
4. Embed the form on the personal-brand site
5. From EOS, monitor `subscriber.tag_add` webhook for `initiate-arena-warm`
   to surface qualified leads in Discord

### Recipe: Outreach reply → opt-in → Initiate Arena nurture

1. Outreach replies parsed by EOS gateway
2. If reply contains explicit consent ("yes send me more"), call
   `POST /subscribers` with `state: "active"` and `fields: {"Source": "outreach"}`
3. Call `POST /tags/{initiate-arena-lead}/subscribers` with the email
4. Visual Automation triggered by tag → Sequence "Initiate Arena Welcome"
5. Final sequence email contains Calendly booking link
6. `subscriber.link_click` webhook on the Calendly URL → adds tag
   `booked-call-intent` → Discord alert to Antony

### Recipe: Personal brand newsletter weekly send

1. Draft in Notion, paste into Kit broadcast
2. Filter: `subscriber_filter: [{ "all": [{ "type": "tag", "ids": [<active-newsletter>] }] }]`
3. Schedule for Tuesday 9am PT
4. After 24h, fetch `/broadcasts/{id}/stats`, log to EOS memory
5. Subscribers who clicked the primary CTA get auto-tagged via link trigger

### Recipe: Lyfe Spectrum drop announcement

1. Create broadcast filtered to `spectrum-interest` tag
2. Include single CTA linking to Shopify product
3. Shopify webhook → EOS receives purchase → calls Kit `POST /purchases` to
   record the conversion against the subscriber
4. Visual Automation: on `purchase.purchase_create` → add tag `spectrum-buyer`,
   remove `spectrum-interest`
5. Future Spectrum drops segmented to past buyers vs. interested-but-not-yet

### Recipe: Segmentation by funnel stage

Use a single custom field `Funnel Stage` with controlled values:
`cold | warm | engaged | qualified | booked | customer | churned`. Update
via API on every state transition. Broadcast filters can target any value.
Cleaner than a `funnel-cold` / `funnel-warm` / ... tag explosion.

### Recipe: A/B subject line

In the Kit broadcast UI, enable "Test subject lines." Provide two subjects.
Kit sends each to 15% of the segment, picks the winner by open rate after
4 hours, sends the winner to the remaining 70%. No API access to the test
config — it must be set in the UI.

## Industry Expert and Cutting-Edge Usage

- **Nathan Barry (founder).** Famously uses Kit to run his own creator
  business. His public playbook: small number of well-named tags, heavy use
  of Visual Automations, plain-text emails, weekly newsletter on a fixed
  schedule, lead magnets behind every blog post, all sequences end with a
  soft CTA to a paid offer.
- **James Clear (Atomic Habits, ~3M subscribers).** Single weekly newsletter
  ("3-2-1 Thursday") on Kit. Minimal automation, minimal segmentation —
  proves that for a publishing-led creator the simplest model wins. The
  list is the product.
- **Pat Flynn (Smart Passive Income).** Heavy automation user. Multiple lead
  magnets, each tagged, each entering a tailored sequence. Uses subscriber
  scoring (Creator Pro) to identify high-engagement subscribers for course
  launch announcements. Webhooks to a custom analytics layer.
- **Tim Ferriss.** Plain-text broadcasts only. Moved from Mailchimp to Kit
  for the deliverability and the simplicity. No automations — the brand is
  the product.
- **Justin Welsh.** Newsletter-first solopreneur ($5M+/year). Uses Kit's
  Creator Network as a primary growth channel — recommends ~5 newsletters
  in his after-subscribe modal and accepts reciprocal recommendations.
  Public attribution: Creator Network drives ~30% of new subscribers.

The cutting-edge pattern in 2026: **AI-personalized broadcasts.** Use Kit's
`{{ subscriber.first_name }}` and custom field merge tags, plus Liquid-style
conditionals, plus a pre-send pass through an LLM to rewrite paragraphs
based on the subscriber's `Funnel Stage` field. The personalization happens
outside Kit (in EOS) before the broadcast HTML is uploaded via API.

---

## EOS Usage Patterns

The following patterns are the canonical EOS workflows for Kit. Each maps
to a real Initiate Arena / personal brand / Lyfe Spectrum need.

### Pattern: Initiate Arena lead nurture sequence

The flagship Kit workflow. Every Initiate Arena lead, regardless of source
(outreach reply, lead magnet, podcast guest), enters this funnel.

Tags involved:
- `source-outreach` / `source-leadmagnet-{slug}` / `source-podcast`
- `funnel-cold` / `funnel-warm` / `funnel-engaged` / `funnel-qualified`
- `initiate-arena-lead` (umbrella)
- `booked-call-intent` (clicked Calendly link)
- `customer` (closed)

Sequence "IA Welcome" (5 emails over 7 days):
1. Day 0: Welcome + framing
2. Day 1: Story + identity
3. Day 3: Proof + social validation
4. Day 5: Soft offer + Calendly link
5. Day 7: Final nudge

Visual Automation:
- Trigger: tag `initiate-arena-lead` added
- Action: subscribe to "IA Welcome" sequence
- Wait: until sequence complete OR `booked-call-intent` tag added
- If `booked-call-intent`: add `funnel-qualified`, exit
- Else: add `funnel-cold-archive`, exit

### Pattern: Lead magnet → tag → automation

For each lead magnet (`tactical-luxury-guide`, `solo-founder-os`, etc.):

1. Form in Kit with the asset as incentive email
2. Tag `lm-{slug}` auto-applied
3. Visual Automation: `lm-{slug}` → custom welcome sequence → join
   `initiate-arena-lead` umbrella → enter the IA nurture flow above

### Pattern: Personal brand newsletter cadence

Weekly Tuesday 9am PT broadcast. Drafted in Notion. EOS automation:

1. EOS pulls the latest draft from the Notion newsletter database
2. Renders to HTML via the EOS template
3. `POST /broadcasts` with `send_at` set to Tuesday 9am PT in UTC
4. After 24h, `GET /broadcasts/{id}/stats` and write open/click rates to
   EOS memory
5. Subscribers who clicked the primary CTA get tagged via Kit link trigger
   (not via API — configured once in the broadcast)

### Pattern: Segmentation by funnel stage

Use the `Funnel Stage` custom field, not a tag explosion. Update via API
on every state transition. Tags are reserved for source attribution and
discrete intent signals (clicked X, downloaded Y). Custom field is the
single-valued state machine.

### Pattern: Calendly handoff

When the Initiate Arena nurture sequence emits the Calendly link, that link
is a Kit-tracked URL. Configure a link trigger in the email: clicking it
adds the `booked-call-intent` tag. The `subscriber.tag_add` webhook fires
to EOS, which posts to Discord so Antony sees a hot lead within seconds.

After the call, Antony manually tags `customer` or `nurture-not-now`. EOS
periodically syncs the `customer` tag list against the Stripe customer list
to detect drift.

### Pattern: Lyfe Spectrum drop announcement

Broadcast to `spectrum-interest` tag. Shopify webhook on purchase →
`POST /purchases` to Kit → tag `spectrum-buyer` → remove `spectrum-interest`.
Future drops segment past buyers separately (more aggressive copy) from
warm interest (softer intro).

## Gotchas

- **V3 hostname is a different service.** `api.convertkit.com` (V3) and
  `api.kit.com` (V4) are not the same gateway. Mixing them produces
  confusing 401/404 errors.
- **No Retry-After on 429.** Implement your own backoff. Cap at 5 retries.
- **Rate limits are per-key.** Two parallel scripts using the same key share
  the 120/min budget. Either spawn separate keys or serialize.
- **Bulk endpoint accepts up to 1000 per call.** Going above silently truncates.
- **`POST /subscribers` is idempotent on email.** It will not return an error
  if the email exists; it returns the existing record. Do not write code
  that assumes 2xx means "newly created."
- **Renaming a custom field breaks old API payloads.** Treat custom field
  names as immutable. To change semantics, create a new field.
- **Visual Automations are not API-manipulable.** You can fire their triggers
  but not create or edit the graphs. Plan logic in the Kit UI, then drive
  it from EOS via tags + sequence enrollments.
- **Broadcasts cannot be edited after send.** Cancel before `send_at` or live
  with the typo. There is no recall.
- **Webhook payloads have no HMAC signature in V4.** Use a shared secret in
  the URL or an IP allowlist. Make handlers idempotent.
- **Receiver timeout ~10 seconds.** Do not run synchronous LLM calls inside
  a Kit webhook handler — enqueue and respond immediately.
- **Free plan gates some features behind paid tiers.** Visual Automations
  require Creator. Subscriber scoring requires Creator Pro. Test on the
  same plan you will run on.
- **Email casing.** Kit stores email as entered. Always `.lower()` before
  comparison or dedupe in your own code.
- **`subscriber_id` vs `email_address`.** Cache the id on first create. Most
  endpoints accept either, but bulk and some delete operations only accept id.
- **API keys grant full account access.** No scope restriction. Treat them
  like database root credentials. Rotate on team-member offboarding (in EOS:
  on every service redeploy that touches the Kit module).
- **Cold lists tank deliverability.** Warm up segments before broadcasting.
  Engaged subscribers first, expand outward over days.
- **Double opt-in is bypassed by API creates.** This is a feature when you
  trust the source and a footgun when you don't. Never bulk-import an
  unverified list via the API.
- **Sequence "courses" terminology is legacy.** The webhook event names still
  say `course_subscribe` / `course_complete` even though the UI calls them
  Sequences. Don't be confused — they refer to the same thing.
- **Plain-text emails outperform.** Kit's design intent. Resist the urge to
  build heavy HTML templates. The wins are in the words.
- **No first-party Python SDK.** Use `requests`. Don't add a community
  dependency for a 50-line wrapper.
