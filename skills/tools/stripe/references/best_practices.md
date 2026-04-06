# Stripe — Best Practices

Creator-level reference. 19 sections: Tier 1 (1-12) technical mastery,
Tier 2 (13-19) creator intelligence. Last researched 2026-04-06.

SDK: `stripe-python` v11+ line (StripeClient pattern).
API version pinned: `2026-03-25.dahlia` (Dahlia line).
Source URLs inline.

---

## Authentication

**Key types (prefix → purpose):**
- `sk_live_…` / `sk_test_…` — secret keys; server-side; full power
- `pk_live_…` / `pk_test_…` — publishable keys; browser/mobile; tokenization only
- `rk_live_…` / `rk_test_…` — restricted keys (RAKs); scoped permissions
  per resource (None/Read/Write). **Prefer RAKs for single-purpose services**
- `whsec_…` — webhook signing secret, per endpoint

**Transport:** HTTPS only. Two accepted methods:
1. `Authorization: Bearer sk_live_xxx` (SDK default)
2. HTTP Basic auth with key as username + empty password

**Connect:** `Stripe-Account: acct_1ABCxyz` header on every request that
should act on behalf of a connected account. Base auth remains the
platform's `sk_live_…`. OAuth Connect uses
`https://connect.stripe.com/oauth/token`.

**Restricted key scopes:** Dashboard → Developers → API keys → Create
restricted key. Grant None/Read/Write per resource class (Customers,
Charges, PaymentIntents, Checkout, Billing, Connect, Issuing, Radar,
Reporting, Sigma, Terminal, Webhook Endpoints, Files, …). One RAK per
service. A leaked RAK costs you one capability, not the whole account.

**Test vs live:** no flag — the key prefix determines mode. `livemode_mismatch`
error if you cross the boundary. Dashboard toggle is display-only.

**EOS storage** — `/opt/OS/eos_ai/.env`:
```
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_PUBLISHABLE_KEY=pk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
STRIPE_API_VERSION=2026-03-25.dahlia
STRIPE_CONNECT_CLIENT_ID=ca_xxx   # optional
```
Never commit. Never log in full (mask to last 4).

Source: docs.stripe.com/keys, docs.stripe.com/api/authentication,
docs.stripe.com/connect/authentication.

---

## Core Operations

Legacy module form and StripeClient v8+ form coexist. Parameter names
are identical; all examples below use the legacy form for brevity.

### Customers
```python
stripe.Customer.create(
    email=None, name=None, phone=None, description=None,
    payment_method=None,            # pm_xxx — attach + set default
    invoice_settings=None,          # {"default_payment_method": "pm_xxx"}
    metadata=None,                  # 50 keys max
    address=None, shipping=None, tax_id_data=None,
)  # → Customer: id="cus_xxx"
stripe.Customer.retrieve("cus_xxx", expand=["default_source"])
stripe.Customer.modify("cus_xxx", email="new@y.com")
stripe.Customer.list(limit=100, email="x@y.com", created={"gte": 1700000000})
stripe.Customer.delete("cus_xxx")                     # soft delete
stripe.Customer.search(query="email:'x@y.com'", limit=100)
```

### PaymentIntent (modern, SCA-compliant primitive)
```python
stripe.PaymentIntent.create(
    amount,                         # int, smallest currency unit
    currency,                       # "usd", lowercase ISO 4217
    customer=None,                  # cus_xxx
    payment_method=None,            # pm_xxx
    payment_method_types=None,      # ["card"]
    automatic_payment_methods=None, # {"enabled": True}
    confirm=False,
    off_session=False,              # True for merchant-initiated
    capture_method="automatic",     # or "manual"
    setup_future_usage=None,        # "on_session" | "off_session"
    description=None,
    statement_descriptor=None,      # ≤22 chars
    receipt_email=None,
    metadata=None,
    application_fee_amount=None,    # Connect
    transfer_data=None,             # Connect
    on_behalf_of=None,              # Connect
)  # → id="pi_xxx", client_secret, status, charges
stripe.PaymentIntent.confirm("pi_xxx", payment_method="pm_xxx", return_url="...")
stripe.PaymentIntent.capture("pi_xxx", amount_to_capture=500)
stripe.PaymentIntent.cancel("pi_xxx", cancellation_reason="requested_by_customer")
stripe.PaymentIntent.retrieve("pi_xxx", expand=["latest_charge.balance_transaction"])
```
Statuses: `requires_payment_method` → `requires_confirmation` →
`requires_action` → `processing` → `succeeded` (or `requires_capture`,
`canceled`).

### Subscription
```python
stripe.Subscription.create(
    customer,                       # required
    items,                          # [{"price": "price_xxx", "quantity": 1}]
    default_payment_method=None,
    trial_period_days=None, trial_end=None,
    proration_behavior="create_prorations",
    collection_method="charge_automatically",
    cancel_at_period_end=False,
    metadata=None,
    payment_behavior="default_incomplete",   # SCA-safe
    expand=None,                    # e.g. ["latest_invoice.payment_intent"]
)  # → id="sub_xxx", status, latest_invoice
stripe.Subscription.modify("sub_xxx", cancel_at_period_end=True)
stripe.Subscription.cancel("sub_xxx", invoice_now=False, prorate=True)
```
Limit: **500 active or scheduled subscriptions per customer**.

### Product / Price
```python
stripe.Product.create(name, description=None, active=True, metadata=None,
                     default_price_data=None, images=None, url=None)
stripe.Price.create(
    currency, unit_amount=None, product=None,
    recurring=None,                 # {"interval": "month", "usage_type": "licensed"}
    billing_scheme="per_unit",      # or "tiered"
    tiers_mode=None, tiers=None,
    nickname=None, metadata=None,
)
```
Prices are mostly immutable — to change amounts, create a new Price and
swap references.

### Checkout.Session
```python
stripe.checkout.Session.create(
    mode,                           # "payment" | "subscription" | "setup"
    line_items,
    success_url,                    # required
    cancel_url=None,
    customer=None, customer_email=None,
    client_reference_id=None,       # your internal id, echoed in webhook
    payment_method_types=None,
    automatic_tax=None,             # {"enabled": True}
    allow_promotion_codes=None,
    subscription_data=None,
    payment_intent_data=None,
    metadata=None,
    expires_at=None,
    ui_mode="hosted",               # "hosted" | "embedded"
)  # → id="cs_xxx", url
```

### Invoice / Refund / SetupIntent / PaymentMethod / Webhook
```python
stripe.Invoice.create(customer, auto_advance=True, collection_method=...,
                     days_until_due=None, description=None, metadata=None)
stripe.Invoice.finalize_invoice("in_xxx")
stripe.Invoice.pay("in_xxx", payment_method="pm_xxx")
stripe.Invoice.void_invoice("in_xxx")

stripe.Refund.create(payment_intent="pi_xxx", amount=None,
                    reason="requested_by_customer", metadata=None)

stripe.SetupIntent.create(customer=None, payment_method_types=["card"],
                         usage="off_session")
stripe.PaymentMethod.attach("pm_xxx", customer="cus_xxx")
stripe.PaymentMethod.detach("pm_xxx")
stripe.PaymentMethod.list(customer="cus_xxx", type="card", limit=100)

event = stripe.Webhook.construct_event(
    payload,                        # RAW bytes
    sig_header,                     # request.headers["Stripe-Signature"]
    secret,                         # whsec_xxx
    tolerance=300,                  # replay-attack window (seconds)
)  # raises SignatureVerificationError on mismatch
```

Never call `PaymentMethod.create()` server-side with raw PANs — PCI scope.
Cards must come from Stripe.js / Elements / mobile SDK.

---

## Pagination

- `limit`: 1–100, default **10**
- Cursors: `starting_after=<id>` (forward) / `ending_before=<id>` (backward),
  mutually exclusive
- Response: `{data: [...], has_more: bool}`
- Auto-pagination:
  ```python
  for cust in stripe.Customer.list(limit=100).auto_paging_iter():
      ...
  ```
  Walks pages transparently via `starting_after`.
- Filter helpers: `created={"gte": ts, "lte": ts}` on most list endpoints.

Source: docs.stripe.com/api/pagination.

---

## Rate Limits

| Mode | Read req/s | Write req/s |
|---|---|---|
| **Live** | 100 | 100 |
| **Test (sandbox)** | 25 | 25 |

**Endpoint overrides:**
- Search API (`*.search`) — **20 req/s** live and test
- Files API — **20 read/s and 20 write/s**
- PaymentIntent updates — max **1000/hour per PaymentIntent**

**Algorithm:** token-bucket / leaky-bucket per account per endpoint class.
Short bursts above steady rate are tolerated then throttled.

**429 behavior:** HTTP 429, `error.type = "rate_limit_error"`,
`error.code = "rate_limit"`. `Retry-After` header is *not always*
included; implement your own exponential backoff with jitter regardless
(0.5s → 1s → 2s → 4s → 8s, max 5 attempts). The Python SDK does NOT
auto-retry 429s — `max_network_retries` covers connection errors only.

Sources: docs.stripe.com/rate-limits, stripe.com/blog/rate-limiters.

---

## Error Codes

**HTTP statuses:**
| Code | Meaning |
|---|---|
| 200 | OK |
| 400 | `invalid_request_error` |
| 401 | `authentication_error` — bad/missing/expired key |
| 402 | Request failed (card decline; `card_error`) |
| 403 | Forbidden — usually restricted-key scope violation |
| 404 | `resource_missing` |
| 409 | Conflict — idempotency replay with diff params, or state violation |
| 429 | `rate_limit_error` |
| 500 / 502 / 503 / 504 | Retryable Stripe/gateway errors |

**`error.type`:** `api_error`, `card_error`, `invalid_request_error`,
`idempotency_error`, `rate_limit_error`, `authentication_error`.

**Common `error.code`:**
- Card: `card_declined`, `expired_card`, `incorrect_cvc`, `incorrect_number`,
  `incorrect_zip`, `invalid_cvc`, `invalid_expiry_month`, `invalid_expiry_year`,
  `invalid_number`, `processing_error`
- PaymentIntent: `payment_intent_authentication_failure`,
  `payment_intent_payment_attempt_failed`, `payment_intent_unexpected_state`,
  `payment_intent_incompatible_payment_method`
- Account/keys: `account_invalid`, `api_key_expired`, `secret_key_required`,
  `livemode_mismatch`, `testmode_charges_only`
- Request: `parameter_missing`, `parameter_unknown`, `parameter_invalid_empty`,
  `parameter_invalid_integer`, `parameter_invalid_string_blank`,
  `invalid_charge_amount`
- Resource: `resource_missing`, `resource_already_exists`
- Locking: `lock_timeout`
- Forwarding: `forwarding_api_retryable_upstream_error`

**`decline_code`** (on `card_declined`): `insufficient_funds`, `lost_card`,
`stolen_card`, `do_not_honor`, `generic_decline`, `pickup_card`,
`try_again_later`, `card_velocity_exceeded`, `fraudulent`,
`currency_not_supported`, `card_not_supported`, `transaction_not_allowed`,
`processing_error`, `incorrect_pin`.

**Retryable vs non-retryable:**
- Retryable: 5xx, `lock_timeout`, `processing_error`, `rate_limit`,
  `forwarding_api_retryable_upstream_error` — retry with **same idempotency_key**.
- Non-retryable: most declines (except `try_again_later`), `expired_card`,
  `incorrect_*`, `parameter_*`, `authentication_error`, `resource_missing`,
  `idempotency_error`.

Source: docs.stripe.com/error-codes, docs.stripe.com/api/errors.

---

## SDK Idioms

- PyPI: `stripe` — `pip install --upgrade stripe`. Async extras:
  `pip install "stripe[async]"` (adds httpx).
- Python support: **3.9+**.
- Current major line: v11/v12/v13 (Acacia/Dahlia API versions).
- Module-level form (legacy, still supported):
  ```python
  import stripe, os
  stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
  stripe.api_version = "2026-03-25.dahlia"        # always pin
  stripe.max_network_retries = 2                  # connection-error retries only
  ```
- Preferred client form (v8+):
  ```python
  from stripe import StripeClient
  client = StripeClient(
      api_key=os.getenv("STRIPE_SECRET_KEY"),
      stripe_version="2026-03-25.dahlia",
  )
  client.v1.customers.list(params={"limit": 100})
  ```
- **Idempotency key — required on every mutating call.** 24h cache.
  Same key + same body → cached response. Same key + different body →
  `idempotency_error`. Use deterministic keys tied to domain actions:
  `f"order-{order_id}-charge-v1"`.
- **Expand** (max depth **4**):
  ```python
  pi = stripe.PaymentIntent.retrieve(
      "pi_xxx",
      expand=["customer", "latest_charge.balance_transaction",
              "invoice.subscription"],
  )
  ```
- **Version pinning precedence (high → low):**
  1. Per-request `Stripe-Version` header / `options={"stripe_version":...}`
  2. SDK global / constructor
  3. Account default (Dashboard)
  Always pin at layer 2. Never trust the account default.
- **Async twins:** `client.v1.customers.retrieve_async("cus_xxx")`.
- **Error handling:**
  ```python
  from stripe.error import (CardError, RateLimitError, InvalidRequestError,
      AuthenticationError, APIConnectionError, StripeError,
      SignatureVerificationError, IdempotencyError)
  try:
      pi = stripe.PaymentIntent.create(amount=1000, currency="usd",
                                       idempotency_key=key)
  except CardError as e:
      # e.user_message, e.code, e.decline_code, e.http_status
      ...
  except RateLimitError:
      backoff_and_retry_with_same_key()
  ```

Sources: github.com/stripe/stripe-python, v8 StripeClient migration guide.

---

## Anti-Patterns

1. **Dollars instead of cents.** All `amount` fields are integer minor units.
   `$19.99` → `1999`. JPY/KRW (zero-decimal) → still integer. Never float.
2. **Client-side amount trust.** Look up Price/Product server-side, compute
   `unit_amount` there. Publishable key provides zero protection.
3. **Retry without idempotency_key.** Network retries will double-charge.
   Rule: every mutating call carries a deterministic idempotency key.
4. **Polling instead of webhooks.** `PaymentIntent.retrieve` in a loop burns
   rate limit and is racy. Subscribe to `payment_intent.succeeded`.
5. **Storing raw PANs.** Out of PCI scope. Use `PaymentMethod` + `SetupIntent`
   and store only `pm_xxx` IDs.
6. **`Charge.create(source=...)` for new flows.** Legacy, SCA-incompatible.
   Use `PaymentIntent` with `setup_future_usage` → `off_session` later.
7. **Publishable key on the server** → `secret_key_required`.
8. **Unverified webhook payloads.** Anyone can POST to your URL —
   `Webhook.construct_event` is mandatory.
9. **`request.json` in webhook handlers.** You must hand the RAW body bytes
   to `construct_event` — Flask `request.get_data()`, not `.json`.
10. **Mixing test and live keys** → `livemode_mismatch`. Separate env files,
    separate services.
11. **Trusting the account default API version.** A Dashboard upgrade silently
    changes response shapes. Pin in code AND pin the webhook endpoint version.
12. **Statement descriptors with disallowed chars** (`< > ' " *`) or all
    digits — Stripe rejects.

---

## Data Model

Top-level resources and relationships that matter:

```
Account (acct_…)
 └─ Customer (cus_…)
     ├─ PaymentMethod (pm_…)
     ├─ Subscription (sub_…)
     │   └─ SubscriptionItem (si_…) → Price (price_…) → Product (prod_…)
     │   └─ latest_invoice → Invoice (in_…)
     ├─ Invoice (in_…) → InvoiceLineItem (il_…) → PaymentIntent (pi_…)
     └─ Charge (ch_…)  (legacy or via PI)

PaymentIntent (pi_…)
 ├─ latest_charge → Charge (ch_…) → BalanceTransaction (txn_…) → Payout (po_…)
 ├─ payment_method → PaymentMethod
 └─ customer → Customer

Product (prod_…) → Price (price_…) → Subscription | Checkout line_item
```

**Money flow:** PaymentIntent → Charge → BalanceTransaction
(records gross/fee/net) → Balance → Payout (`po_…`).

**Metadata constraints:** 50 keys max per object, key ≤40 chars,
value ≤500 chars, no `[` or `]` in keys. Strings only (numbers/bools
coerced). Use it as a poor-man's CRM: `metadata={"eos_venture_id": "ven_123",
"eos_lead_id": "lead_456"}`.

**Immutable fields:** Price `unit_amount`, `currency`, `recurring`. Product
type. Charge `amount`. Invoice line items frozen on finalize. To change
any immutable field → create a new resource and swap references.

**Soft delete:** `Customer.delete()` returns `{id, deleted: true}` — kept
for history, removed from default lists. Most resources cannot be
hard-deleted via API.

**Opaque IDs:** store as `VARCHAR(255)`. Stripe reserves the right to
change length/format. Never parse.

---

## Webhooks

**Setup:** Dashboard → Developers → Webhooks → Add endpoint → select events →
Stripe issues a per-endpoint `whsec_…`.

**Signature verification (Flask):**
```python
import stripe, os
sig     = request.headers["Stripe-Signature"]
payload = request.get_data()   # RAW bytes — NEVER request.json
try:
    event = stripe.Webhook.construct_event(
        payload, sig, os.getenv("STRIPE_WEBHOOK_SECRET"),
        tolerance=300,
    )
except stripe.error.SignatureVerificationError:
    return ("", 400)
```

**`Stripe-Signature` header format:**
`t=1700000000,v1=5257a869e7e…,v1=…,v0=…`
- `t=` unix timestamp at signing
- `v1=` HMAC-SHA256 over `f"{t}.{payload}"` using signing secret
- Multiple `v1=` entries appear during secret rotation
- `v0=` is legacy — ignore

**Retry policy (live mode):** up to **3 days**, exponential backoff —
immediate, ~5 min, 30 min, 2 h, 5 h, 10 h, then every 12 h. After 3 days
Stripe disables the endpoint and emails the owner. Sandbox retries only
~3 times over a few hours.

**At-least-once delivery.** Stripe resends if it doesn't get a 2xx fast
enough. Handlers MUST be idempotent — dedup on `event.id` in Redis SETNX
or a Postgres unique index. Ordering is NOT guaranteed.

**Response timing:** 2xx within ~30 seconds. Do work async.

**Common event types (most-used subset):**
- `payment_intent.{succeeded,payment_failed,requires_action,processing,canceled}`
- `charge.{succeeded,failed,refunded,dispute.created,dispute.closed}`
- `checkout.session.{completed,async_payment_succeeded,expired}`
- `customer.{created,updated,deleted}`
- `customer.subscription.{created,updated,deleted,trial_will_end,paused,resumed}`
- `invoice.{created,finalized,payment_succeeded,payment_failed,upcoming}`
- `payout.{created,paid,failed}`
- `setup_intent.{succeeded,setup_failed}`

Each event has `id` (`evt_xxx`), `type`, `created`, `livemode`,
`api_version`, `data.object`. **Pin the webhook endpoint api_version
to match your code.**

---

## Limits

| Limit | Value |
|---|---|
| Metadata keys per object | **50** |
| Metadata key length | **40 chars** |
| Metadata value length | **500 chars** |
| Disallowed metadata key chars | `[` `]` |
| Expand depth | **4 levels** |
| Statement descriptor | **22 chars**, no `< > ' " *`, at least one non-digit |
| Pagination `limit` | 1–100, default 10 |
| Active subscriptions per customer | **500** |
| PaymentIntent updates | 1000/hour per PI |
| Idempotency key cache | **24 hours** |
| Webhook 2xx timeout | ~30 s |
| Webhook retry window (live) | 3 days |
| File upload (`dispute_evidence`) | ~16 MB/file (verify per-purpose) |

**No native batch endpoint.** Parallelize requests (respect 100/s),
use Sigma SQL for analytical bulk reads, or Reporting API.

**Application fee:** capped at charge amount minus Stripe fees;
error `application_fee_amount_too_large` on overflow.

---

## Cost Model

**No per-API-call fee.** API is free. You pay on processed payments and
value-add products.

**Standard US card processing:**
- **2.9% + $0.30** per successful card charge
- **+1.5%** for international cards (→ 4.4% + $0.30)
- **+1%** for currency conversion
- Example: US merchant, EU card, EUR charge → 2.9% + 1.5% + 1% =
  **5.4% + $0.30**

**ACH Direct Debit (US):** 0.8%, capped at $5.00.

**Radar:**
- Radar (basic) — **free** with standard processing
- Radar for Teams (custom rules, lists) — **+$0.05 per screened txn**

**Stripe Billing:** 0.5% on recurring invoices (Starter), 0.8% (Scale).
Free if you only use Subscriptions without Invoices/dunning automation.

**Stripe Connect:**
- Standard accounts — free
- Express / Custom — +0.25% + $2.00 per active account per month +
  payout fees
- Cross-border payouts — 0.25%–1%

**Issuing:** $0 platform fee, ~$3/card, + interchange share.
**Disputes:** $15.00 per dispute (refunded if you win).
**Instant Payouts:** 1.5%, $0.50 min.
**Test mode:** free.

Always cross-check the live pricing page for the venture's geography.

Sources: stripe.com/pricing.

---

## Version Pinning

**Format:** `YYYY-MM-DD.codename`, e.g. `2024-09-30.acacia`,
`2025-10-29.clover`, `2026-03-25.dahlia`. `.codename` marks a major line;
monthly releases within a line are backward compatible.

**Current pin:** `2026-03-25.dahlia`. Previous lines: Clover (2025),
Acacia (2024). Verify current latest at docs.stripe.com/api/versioning.

**Three places version is set (precedence high → low):**
1. Per-request `Stripe-Version` header / `options={"stripe_version":...}`
2. SDK global `stripe.api_version = "..."` or `StripeClient(stripe_version=...)`
3. Account default (Dashboard → Developers → API version)

**EOS rule:** always pin at layer 2. Keep webhook endpoint versions in
sync.

**Backward-compatibility guarantees within a major line:**
- Adding new resources
- Adding new optional request parameters
- Adding new response properties
- Reordering response properties
- Changing opaque ID length/format

**Can break across major lines (Acacia → Dahlia, etc.):**
- Removed/renamed fields
- Default value changes
- Required parameter additions
- Response shape restructuring

**Upgrade flow:**
1. Read every monthly changelog between your version and target
2. Bump `stripe.api_version` AND webhook endpoint version in staging
3. Run integration tests against test mode
4. Roll to production
5. Stripe keeps old versions accessible for years — never forced migration

Source: docs.stripe.com/api/versioning, docs.stripe.com/upgrades,
docs.stripe.com/changelog/acacia.

---

# Tier 2 — Creator Intelligence

---

## Design Intent

**Founding vision (Patrick & John Collison, 2010):**
Payments as a developer problem, not a banking problem. The literal
"seven lines of code" wedge: paste a snippet, accept money. PayPal's
legacy was hosted forms and merchant accounts; Stripe's bet was that
API-first would route around the incumbent stack. Mission:
"increase the GDP of the internet" — lower activation energy for any
internet business to exist.

**Why API-first (vs PayPal redirect):** PayPal broke conversion by
forcing a redirect off-site. Stripe's insight: keep the customer on
your domain, push card data straight from JS to Stripe (Stripe.js
tokenization), let the merchant own UX. The API IS the product.

**Money as integers in smallest currency unit:** Floats in financial
math are malpractice (`0.1 + 0.2 != 0.3`). Stripe enforces integer
minor units everywhere. Even zero-decimal currencies (JPY, KRW) are
integer. This forces correctness at the type boundary.

**Why PaymentIntents replaced Charges (2019):** `Charge.create()` was
synchronous — success or failure. Then PSD2/Strong Customer Authentication
landed in Europe (Sept 2019), requiring 3D Secure 2. SCA is async and
multi-step. Charges couldn't model that. PaymentIntents reframed payments
as state machines — the intent persists across redirects and the whole
lifecycle. Charges is retained only for legacy reads.

**Idempotency-as-a-primitive:** Stripe's "Designing robust and predictable
APIs with idempotency" post is canon. Networks fail, retries are inevitable,
so build the retry contract into the protocol. Brandur Leach (ex-Stripe)
wrote the definitive Postgres implementation.

**Positioning: "economic infrastructure for the internet":** Not a bank.
Not a merchant of record (until April 2025 Stripe Managed Payments beta).
Not an accountant. Plumbing. Merchant-of-record liability historically
lived with the seller — which is why Paddle, FastSpring, Lemon Squeezy
carved a niche. Stripe finally re-entered this space in 2025.

Sources: stripe.com/blog/idempotency, brandur.org/idempotency-keys,
news.ycombinator.com/item?id=14902696.

---

## Problem-Solution Map

Most developers know Checkout, Subscriptions, Webhooks. The depth chart:

- **Sigma** — SQL (and now natural-language) over your Stripe data inside
  the Dashboard. Custom reports without ETL. Fresh data within ~3 hours.
  Replaces "export CSV → spreadsheet."
- **Data Pipeline** — Native sync of Stripe data to Snowflake, Redshift,
  Databricks, S3, GCS, Azure Blob. Use this instead of Fivetran/Airbyte
  when Stripe is your only source needing warehousing.
- **Stripe Apps** — UI extensions that render inside the Stripe Dashboard.
  Build internal ops tooling where your team already lives.
- **Financial Connections** — Stripe's Plaid alternative. Link bank
  accounts for balances, transactions, ownership. Gateway for ACH,
  payouts, underwriting.
- **Atlas** — Delaware C-corp incorporation as a service. Entity + EIN +
  bank account + stock issuance in days.
- **Tax** — Automatic calculation, collection, and (in GA markets) filing.
- **Identity** — KYC (document + selfie). Marketplaces onboarding sellers;
  SaaS gating sensitive features.
- **Terminal** — In-person card readers. Same API as online.
- **Issuing** — Issue your OWN virtual/physical cards. Substrate behind
  Brex, Ramp corporate-card startups. Define auth rules in real time via
  `/v1/issuing/authorizations` webhooks.
- **Treasury** — Embedded banking-as-a-service. Powers Shopify Balance,
  Lyft Direct.
- **Radar** — Fraud ML with custom rule DSL. Velocity rules, device
  fingerprinting, Lists, and a 2024+ Radar Assistant that converts
  natural language to rules.
- **Payment Links** — No-code hosted checkout URL. Fastest path from
  "I have a product" to "I can take money." Perfect for Initiate Arena's
  first $750 sale before custom UI exists.
- **Pricing Tables** — Embeddable hosted pricing UI.
- **Customer Portal** — Hosted subscription management. Skip building
  billing UI entirely.
- **Metadata as poor-man's CRM** — Searchable via Search API
  (`metadata['venture']:'initiate_arena'`).
- **Restricted Keys** — Scoped API keys. A leak costs one capability,
  not the whole account.
- **Webhook endpoints as published event bus** — treat Stripe events
  as a message broker.

**Connect charge type decision (load-bearing for marketplaces):**
- *Direct charges* — payment on connected account; connected account pays
  fees. Use when customers transact directly with a seller (Shopify
  storefronts, Thinkific creators).
- *Destination charges* — payment on platform; funds (and optionally fees)
  transfer to connected account in one call. Platform pays fees. Use when
  customers transact with YOUR brand (Lyft, Airbnb, DoorDash).
- *Separate charges + transfers* — charge platform first, transfer to N
  connected accounts later. Use when recipient unknown at charge time or
  splitting across multiple sellers (food delivery: restaurant + driver).

Sources: stripe.com/sigma, stripe.com/data-pipeline, docs.stripe.com/connect/charges.

---

## Operational Behavior

- **Webhook ordering is NOT guaranteed.** `customer.subscription.updated`
  can arrive before `.created`. `invoice.paid` before `invoice.created`.
  Laravel Cashier has years of issue tracker proof. Mitigation: on
  receipt of a child event, fetch the parent object from the API rather
  than trusting prior state.
- **Duplicate delivery happens.** "Occasionally" at Stripe scale means
  hourly. Dedup on `event.id` with Redis SETNX or a Postgres unique index.
- **Failure detection is slow.** Stripe eventually emails you that your
  endpoint is failing — days later. Build your own monitoring: track
  `event.created` lag in your own DB.
- **`balance_transactions` eventual consistency.** A successful charge
  will not immediately have an associated balance_transaction — seconds
  to minutes of lag. Don't reconcile balances synchronously in the charge
  flow.
- **Idempotency gotchas:** 24h scope, then expires. Same key + different
  body → error ("keys for idempotent requests can only be used with the
  same parameters they were first used with"). Keys are scoped per API
  key, not globally.
- **3DS silently changes UX.** `requires_action` means the user must
  complete a bank challenge (modal/redirect). If your frontend doesn't
  handle `intent.next_action`, the payment hangs forever. SCA regions:
  EU, UK, India.
- **Subscription proration edges:** default `create_prorations` generates
  credit/debit on the NEXT invoice, not immediately. Trial → active fires
  `updated`, not `created`. Monthly → annual mid-cycle creates surprising
  prorations — preview with `/v1/invoices/upcoming`.
- **Payouts:** US T+2 default. UK T+7 → T+3. India T+3-7. New accounts
  have 7-14 day holds before first payout.
- **Currency conversion timing:** Charging USD on an EU card → bank
  converts. Charging EUR via presentment currency → Stripe locks FX at
  charge time, you receive USD minus ~1% spread.
- **Refunds blocked once a dispute fires.** Win or lose the funds.
- **Test clocks are mandatory.** Create sandbox time, attach customers/
  subscriptions, advance time forward (`+30 days`) to fire renewal/trial-
  end/payment-fail events deterministically. Limit: 3 customers / 3
  subscriptions / 10 quotes per clock.

Sources: docs.stripe.com/webhooks, stigg.io Stripe webhook best practices,
docs.stripe.com/billing/testing/test-clocks.

---

## Ecosystem Position

- **Stripe as revenue source-of-truth.** CRMs forecast, accounting
  reconciles, Stripe is reality — it's the only system that knows whether
  a charge actually settled.
- **Stripe + warehouse + BI.** Pattern: Data Pipeline → Snowflake/BigQuery
  → dbt → Looker/Metabase. Sigma for ad-hoc; warehouse when joining with
  product analytics, marketing spend, support tickets.
- **Stripe + Segment.** Mirror Stripe events into your warehouse and
  downstream destinations.
- **Stripe Billing vs Chargebee/Recurly:** Stripe Billing falls short on
  complex ASC 606 revenue recognition, quote-to-cash workflows with
  approvals, and multi-entity consolidation. Use Stripe for
  "monthly/annual + maybe usage" — layer Chargebee/Maxio once CFO-level
  requirements kick in.
- **Stripe vs Paddle (MoR):** Paddle 5% + $0.50, handles global VAT/sales
  tax filing, chargebacks, MoR liability. Stripe 2.9% + $0.30 base, tax
  compliance is YOUR problem (Stripe Tax calculates, not files in most
  jurisdictions). For solo founders selling globally, Paddle's all-in
  often wins once you add Stripe Tax + accountant + chargeback time.
  April 2025: Stripe launched Managed Payments beta — implicit concession.
- **Stripe + accounting:** QuickBooks/Xero native connectors sync charges
  as line items.
- **Checkout vs Elements vs Embedded:**
  - *Checkout (hosted)* — Stripe-hosted page, redirect. Fastest ship.
    SCA + tax + methods all handled. Limited brand UX.
  - *Embedded Checkout* — same Checkout in an iframe on your domain (2023+).
  - *Elements* — composable React/JS for full custom UX. You handle SCA
    flow, 3DS modal, error states.
  - *Payment Element* — single multi-method input (card, Apple Pay, iDEAL,
    …) that auto-detects.
- **Webhooks → queue → worker.** Stripe retries on backoff but eventually
  gives up (~3 days). Production pattern: Stripe → endpoint → enqueue
  (SQS/Cloud Tasks/Inngest) → return 200 → async worker processes
  idempotently. Stripe publishes a DLQ guide for AWS.

Sources: paddle.com/compare/stripe, stripe.dev/blog/building-resilient-webhook-handlers.

---

## Trajectory

**API generation history:**
- Charges (2011) → Sources (2017, multi-method abstraction) → PaymentMethods
  + PaymentIntents (2019, SCA-ready) → Payment Element (2021, unified UI).
- Sources deprecated. Orders API deprecated.
- All new code: PaymentIntents + PaymentMethods + (Checkout Session OR
  Payment Element).

**Recent GA / launches:**
- Stripe Tax, Identity, Treasury, Issuing all GA.
- Sigma + natural-language SQL.
- Radar Assistant (NL → rules).

**Sessions 2025 (April 29-30) headline announcements:**
- **Stripe for Agents** — agentic commerce primitives. Agents can earn,
  hold, spend. New Order Intents API.
- **Stripe Workflows** — visual conditional logic across products without
  code.
- **Stripe Profiles** — public business identity for B2B invoicing.
- **Stripe Verified** — accreditation credential.
- **Stripe Managed Payments (beta)** — MoR. Finally competing with Paddle.
- **Optimized Checkout Suite AI** — 100+ signals personalize checkout in
  real time; 125+ payment methods including stablecoins, Pix, UPI.

**Crypto:** Killed Bitcoin in 2018. Re-entered 2024 with USDC on L2s
(Polygon, Base, Solana). 2025 doubled down with stablecoins as first-class
payment method.

**AI-native direction:** LLM-friendly docs (`/llms.txt`), agentic toolkit
(`@stripe/agent-toolkit` for OpenAI/Anthropic function calling), Radar
Assistant NL rules, Sigma NL SQL. Stripe is positioning to be the
financial primitive for AI agents the same way it positioned for human
developers in 2010.

Sources: stripe.com/blog/top-product-updates-sessions-2025, stripe.com/sessions/2025.

---

## Conceptual Model

**Core primitives:**
```
Customer ──owns──> PaymentMethod
   │
   ├──pays──> PaymentIntent ──creates──> Charge
   │                                       └──> BalanceTransaction ──> Payout
   ├──subscribes──> Subscription ──invoices──> Invoice ──pays──> PaymentIntent
   │                     └──contains──> Price ──belongs──> Product
   └──tagged with──> metadata{}
```

**The PaymentIntent state machine (memorize):**
```
requires_payment_method
       │ (attach pm)
       ▼
requires_confirmation
       │ (confirm)
       ▼
requires_action  ◄── 3DS challenge (SCA regions)
       │ (user completes)
       ▼
processing
       │
       ▼
succeeded  OR  requires_payment_method (failed → retry)  OR  canceled
```

Every other Stripe API is a wrapper around this state machine.

**Recipe 1 — One-time $750 sale (Initiate Arena):**
```python
session = stripe.checkout.Session.create(
    mode="payment",
    line_items=[{
        "price_data": {
            "currency": "usd",
            "product_data": {"name": "Initiate Arena — Cohort 01"},
            "unit_amount": 75000,   # $750.00
        },
        "quantity": 1,
    }],
    success_url="https://lyfeinstitute.com/welcome?session_id={CHECKOUT_SESSION_ID}",
    cancel_url="https://lyfeinstitute.com/initiate-arena",
    metadata={"venture": "initiate_arena", "cohort": "01"},
    customer_creation="always",
)
# Redirect to session.url
# Webhook: listen for checkout.session.completed → fulfill
```

**Recipe 2 — Subscription with trial:**
```python
product = stripe.Product.create(name="Lyfe Spectrum Membership")
price   = stripe.Price.create(product=product.id, currency="usd",
                              unit_amount=4900, recurring={"interval": "month"})
sub = stripe.Subscription.create(
    customer=customer.id,
    items=[{"price": price.id}],
    trial_period_days=14,
    payment_behavior="default_incomplete",  # SCA compliance
    expand=["latest_invoice.payment_intent"],
)
```

**Recipe 3 — Usage-based billing:**
- Metered Price (`recurring.usage_type='metered'`)
- Report usage: `stripe.SubscriptionItem.create_usage_record(item_id,
  quantity=N, timestamp=now, action='increment')`
- Stripe aggregates and invoices at period end.

**Recipe 4 — Marketplace payout (destination charge):**
```python
stripe.PaymentIntent.create(
    amount=10000, currency="usd",
    payment_method_types=["card"],
    application_fee_amount=300,    # platform takes $3
    transfer_data={"destination": connected_account_id},
)
```

**Recipe 5 — Failed payment dunning:**
- Enable Smart Retries in Dashboard (Stripe ML picks retry timing)
- Listen for `invoice.payment_failed` → email customer with `hosted_invoice_url`
- Listen for `customer.subscription.updated` → `status='past_due'` →
  soft-disable feature
- Listen for `customer.subscription.deleted` → hard-disable + win-back

---

## Industry Expert

**Patrick McKenzie (patio11):** Joined Stripe 2016 for Atlas. Writing at
Kalzumeus and Bits About Money is canonical for SaaS pricing, invoicing,
and how money actually moves. Heuristics he's pushed:
- Charge more. Low-touch SaaS should start at `$X9/mo`, not `$9/mo`.
- Invoices are human-readable artifacts, not receipts — a sales surface.
- "Anything better than what you'd offer a $500/mo account gets a line
  item that costs $10K."
- B2B enterprise expects annual invoices, NET-30, PDF — meet them there.

**Shopify on Stripe Connect:** Shopify Payments is white-labeled Stripe.
Connect embeds payments inside merchant stores while Shopify owns the
merchant relationship. Co-built Shopify Balance on Treasury.

**Lyft on Stripe Connect (destination charges):** ~700K drivers,
~1M rides/day, all through Stripe on AWS. Express Pay (instant driver
cashout) reached >40% of payouts in 6 months — Treasury+Connect
composition is now table stakes for gig platforms.

**LLM-driven checkout (Stripe for Agents 2025):** `@stripe/agent-toolkit`
exposes Stripe primitives as tools for OpenAI/Anthropic function calling.
Agents can create customers, payment links, invoices, refunds. Order
Intents API lets an agent commit to a purchase that materializes as a
PaymentIntent on confirmation. Frontier pattern: chat → agent → Order
Intent → human confirms via Payment Link → fulfillment.

**Advanced Radar rule composition:**
```
Block if :card_velocity_24h: > 3
  AND :email_domain: in ['mailinator.com', 'tempmail.io']
  AND :ip_country: != :card_country:
```
Composite velocity + device fingerprint + email reputation rules cut
card-testing attacks dramatically. Use "Review" action (not block) for
marginal scores so humans adjudicate.

**Metadata-driven analytics in Sigma:**
```sql
SELECT metadata['venture'] AS venture,
       SUM(amount) / 100.0 AS gross_usd,
       COUNT(*) AS txn_count
FROM charges
WHERE created >= date_trunc('month', current_date)
  AND status = 'succeeded'
GROUP BY 1
ORDER BY gross_usd DESC;
```
Tag every charge with `venture/campaign/cohort` metadata and Sigma
becomes free revenue BI.

**Webhook dedup with `event.id`:** Use `event.id` (not `idempotency_key`)
as the unique key in your processed-events table. SETNX in Redis with
7-day TTL, or unique-indexed Postgres row. Reject the second delivery
silently and return 200.

**Test clocks in CI:** Wire test-clock creation/advance into integration
tests. Validate that a 14-day trial converts to paid, that payment failure
triggers dunning, that annual renewal fires the right webhooks — all in
seconds, not days.

**Clerk/Auth0 + Stripe SaaS spine:** JWT holds `org_id`; Stripe Customer
holds `metadata['org_id']`; per-seat metered Price; webhook on
`customer.subscription.updated` mirrors `status` and `quantity` to the
auth provider's org claims; middleware reads JWT to gate features. This
is the modern multi-tenant SaaS backbone.

Sources: kalzumeus.com, bitsaboutmoney.com/patio11, stripe.com/customers/lyft,
stripe.com/customers/shopify, docs.stripe.com/radar/rules/supported-attributes.
