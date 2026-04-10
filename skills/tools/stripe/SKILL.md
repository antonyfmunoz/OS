---
name: stripe
description: "Use when creating, charging, refunding, or managing Stripe customers, payment intents, subscriptions, products, prices, checkout sessions, invoices, or webhooks — or when integrating payments for Initiate Arena, Empyrean Studio, or any Munoz Conglomerate venture. Also use when verifying webhook signatures, debugging 3DS/SCA flows, handling dunning, or composing Stripe with Sigma, Connect, Billing, or Treasury."
allowed-tools: "Read, Write, Edit, Bash, WebFetch, WebSearch"
version: 1.0
source_url: "https://stripe.com/docs/api"
last_researched: "2026-04-09"
instantiated_from: templates/tools/_template/
api_version: "2026-03-25.dahlia"
sdk_version: "stripe-python v11+"
speed_category: "medium"
trigger: both
effort: high
context: fork
---

# Tool: Stripe

Stripe is the payments primitive for Munoz Conglomerate. Revenue-critical
for Initiate Arena — this is how money actually lands in the business.

## What This Tool Does

Stripe provides money-movement infrastructure as an API:
- **Payments** — accept cards, ACH, Apple/Google Pay, local methods via
  PaymentIntents (SCA-ready state machine) or hosted Checkout.
- **Subscriptions & Billing** — recurring revenue, trials, proration,
  dunning, Smart Retries, hosted Customer Portal.
- **Connect** — marketplace payouts: direct / destination / separate+transfer.
- **Products & Prices** — the catalog primitives every other API references.
- **Radar** — fraud ML with custom rule DSL.
- **Sigma / Data Pipeline** — SQL + warehouse sync of your Stripe data.
- **Tax, Identity, Atlas, Issuing, Terminal, Treasury** — adjacent products
  built on the same primitives.

Design philosophy (Collison brothers, 2010): payments as a developer
primitive, not a banking problem. API-first, seven lines of code,
integer minor units (no floats), idempotency as a protocol-level contract,
PaymentIntents as state machines (to accommodate PSD2/SCA).

## EOS Integration

**Primary consumers:**
- Initiate Arena checkout (first $750 sale) — Payment Links or
  `checkout.Session` with `metadata={"venture": "initiate_arena"}`.
- Lyfe Spectrum membership (future) — Subscription with trial.
- Empyrean Studio AI offer (future) — one-off Checkout + usage-based
  metered Price.
- Webhook handler lives in `services/` (add when first sale is imminent).

**Revenue source-of-truth.** Stripe is canonical for "did this charge
settle?" — CRMs forecast, accounting reconciles, Stripe is reality.
Tag every charge with `metadata["venture"]` so Sigma can break down
revenue by venture without ETL.

**Webhook → queue → worker pattern.** Never do real work inside the
Stripe webhook request. Verify signature, enqueue, return 200 fast.
Stripe times out at ~30s and gives up after ~3 days.

## Authentication

**Key types:**
- `sk_live_…` / `sk_test_…` — full secret key (server-side only)
- `pk_live_…` / `pk_test_…` — publishable key (browser/mobile)
- `rk_live_…` / `rk_test_…` — restricted key (scoped; preferred for
  single-purpose services and webhook handlers)
- `whsec_…` — webhook signing secret (per endpoint)

**EOS storage** — `/opt/OS/eos_ai/.env`:
```
STRIPE_SECRET_KEY=sk_test_xxx        # sk_live_ in prod
STRIPE_PUBLISHABLE_KEY=pk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
STRIPE_API_VERSION=2026-03-25.dahlia
# Optional Connect:
STRIPE_CONNECT_CLIENT_ID=ca_xxx
```

Load with `load_dotenv('/opt/OS/eos_ai/.env')`. Never commit, never log
full keys (mask to last 4). Use restricted keys wherever possible.

**Test vs live** — the key prefix determines the mode. No flag. Objects
do not cross the boundary; `livemode_mismatch` if you try.

## Quick Reference

```python
import os, stripe
from dotenv import load_dotenv
load_dotenv('/opt/OS/eos_ai/.env')

stripe.api_key     = os.getenv("STRIPE_SECRET_KEY")
stripe.api_version = os.getenv("STRIPE_API_VERSION", "2026-03-25.dahlia")
stripe.max_network_retries = 2

# --- One-time Checkout Session: Initiate Arena $750 sale ---
session = stripe.checkout.Session.create(
    mode="payment",
    line_items=[{
        "price_data": {
            "currency": "usd",
            "product_data": {"name": "Initiate Arena — Cohort 01"},
            "unit_amount": 75000,   # $750.00 — integer cents, always
        },
        "quantity": 1,
    }],
    success_url="https://lyfeinstitute.com/welcome?session_id={CHECKOUT_SESSION_ID}",
    cancel_url="https://lyfeinstitute.com/initiate-arena",
    customer_creation="always",
    metadata={"venture": "initiate_arena", "cohort": "01"},
    idempotency_key=f"ia-cohort01-{lead_id}",
)
# redirect the user to session.url

# --- Subscription with trial ---
sub = stripe.Subscription.create(
    customer=customer.id,
    items=[{"price": price_id}],
    trial_period_days=14,
    payment_behavior="default_incomplete",   # SCA-safe
    expand=["latest_invoice.payment_intent"],
    idempotency_key=f"sub-{customer.id}-v1",
)

# --- Refund ---
stripe.Refund.create(
    payment_intent="pi_xxx",
    reason="requested_by_customer",
    idempotency_key=f"refund-{order_id}-v1",
)

# --- Webhook signature verify (Flask) ---
@app.post("/stripe/webhook")
def stripe_webhook():
    payload  = request.get_data()                  # RAW bytes, not .json
    sig      = request.headers["Stripe-Signature"]
    try:
        event = stripe.Webhook.construct_event(
            payload, sig, os.getenv("STRIPE_WEBHOOK_SECRET"),
            tolerance=300,
        )
    except stripe.error.SignatureVerificationError:
        return ("", 400)

    # Dedup on event.id (at-least-once delivery)
    if already_processed(event["id"]):
        return ("", 200)

    enqueue_for_worker(event)                       # ack fast, work async
    return ("", 200)
```

### The PaymentIntent state machine (memorize)

```
requires_payment_method → requires_confirmation → requires_action (3DS)
                                                         │
                                                         ▼
                                                    processing → succeeded
                                                         │
                                                         ├─→ requires_payment_method (retry)
                                                         └─→ canceled
```

Every modern Stripe payment flow is a wrapper around this state machine.

### Most useful webhook events

- `checkout.session.completed` — fulfillment trigger
- `payment_intent.succeeded` / `.payment_failed`
- `invoice.payment_succeeded` / `.payment_failed` — dunning hook
- `customer.subscription.created` / `.updated` / `.deleted` / `.trial_will_end`
- `charge.refunded`, `charge.dispute.created`

## Conceptual Model

Stripe is a hierarchy of state machines over money primitives:

```
Customer ──owns──> PaymentMethod
   │
   ├──pays──> PaymentIntent ──creates──> Charge ──> BalanceTransaction ──> Payout
   │
   └──subscribes──> Subscription ──invoices──> Invoice ──pays──> PaymentIntent
                         │
                         └──contains──> Price ──belongs──> Product
```

Every object has a `metadata` dict (50 keys, 40-char keys, 500-char
values). Use it as a poor-man's CRM — tag `venture`, `campaign`,
`lead_source` and query via Sigma SQL later.

Idempotency is a protocol primitive, not a retry hack. Every mutating
call (POST) MUST carry an `idempotency_key`. Stripe caches the response
body + status code for 24h. Replay with same key + same body → cached
response. Replay with same key + different body → `idempotency_error`.

## Gotchas

- **Amounts are integer cents, never floats.** $19.99 = `1999`. ¥100 = `100`.
  Floats in financial math are malpractice — Stripe enforces it at the type
  boundary.
- **Webhook payload must be RAW bytes**, not parsed JSON. Flask:
  `request.get_data()`, not `request.json`. Signature verify fails silently
  otherwise.
- **Webhook ordering is NOT guaranteed.** `customer.subscription.updated`
  can arrive before `.created`. On receipt, always fetch the parent object
  from the API rather than trusting prior state.
- **Webhooks are at-least-once** — dedup on `event.id` with Redis SETNX or
  a Postgres unique index. Don't use `idempotency_key`.
- **Idempotency key scope is 24h, per API key.** Replay after 24h creates
  a new object. Same key + different body = `idempotency_error` (this bites
  when you change request shape mid-deploy with deterministic keys).
- **Never trust client-side amounts.** Always look up the Price/Product
  server-side and compute `unit_amount` there.
- **Never pass publishable key server-side** → `secret_key_required`.
- **Pin `api_version` in code** — the Dashboard "Upgrade API version"
  button silently changes response shapes in production.
- **Pin the webhook endpoint API version to match code.** Otherwise
  an account upgrade breaks handlers.
- **Test clocks are mandatory for billing CI.** Wire them into integration
  tests to advance time +30 days and fire renewal/trial/failure events
  deterministically. Limit: 3 customers / 3 subscriptions per clock.
- **Refunds blocked once a dispute fires.** Win the dispute or lose the funds.
- **Don't poll PaymentIntents** — use webhooks. Polling burns rate limit
  and is racy.
- **stripe-python `max_network_retries`** only retries connection errors,
  not 429s. Wrap your own backoff for rate limits (0.5 → 1 → 2 → 4 → 8s
  with jitter, max 5 attempts, always reusing the same idempotency_key).
- **WebFetch is blocked on docs.stripe.com** from some environments —
  use WebSearch snippets or `curl` from the VPS when re-researching.

## Verification

After changes to this skill run:
```bash
python3 -c "
toolname='stripe'
skill=f'/opt/OS/skills/tools/{toolname}/SKILL.md'
bp=f'/opt/OS/skills/tools/{toolname}/references/best_practices.md'
c=open(skill).read(); b=open(bp).read()
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

See `references/best_practices.md` for exact signatures, rate limits,
error codes, and creator-level intelligence.
