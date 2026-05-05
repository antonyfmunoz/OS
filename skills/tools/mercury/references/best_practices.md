# Mercury — Creator-Level Best Practices
Source: docs.mercury.com/reference, docs.mercury.com/changelog, mercury.com/api, support.mercury.com
API Version: Mercury API v1 (REST/JSON over HTTPS)
SDK Version: No official SDK. Community: mercury-bank-api (PyPI, 0.x). Direct REST is canonical.
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## Authentication

Mercury uses HTTPS Basic Auth where the API token is the username and the
password is empty. Equivalently, `Authorization: Bearer <token>` works on
every endpoint. Tokens are minted from the Mercury dashboard at
Settings → API Tokens. There is no OAuth client-credentials flow for first-
party use; OAuth2 exists only for third-party integrations going through the
Mercury Public API onboarding program (separate review process documented at
portal.wearemercury.com).

Three scope tiers exist:

- **Read** — list and get only. Cannot create transactions, cannot create
  recipients. Safe to load into long-running ingest jobs and CI environments.
- **Read + Write** — can create transactions and manage recipients without
  admin approval. **Mandatory IP whitelist** at token creation time. Mercury
  refuses to mint a write token without at least one IP entry. Calls from a
  non-listed IP return 403.
- **Custom** — fine-grained scopes selected at creation. Useful for segmented
  automation where one process should read only one account, etc.

Token format is opaque (long random string, no embedded scope information).
Tokens do not expire on a schedule but can be revoked from the dashboard. A
revoked token returns 401 immediately. Mercury does not rotate tokens for you;
treat rotation as an operator-driven workflow.

EOS consequence: read tokens live in `eos_ai/.env` as
`MERCURY_TOKEN_<ENTITY_SLUG>`. Write tokens live ONLY on the operator host
(the static-IP machine that fires approved payments). They never appear in
the agent runtime environment, never in Docker images, never in git. Multi-
entity organizations get one token per org — there is no cross-org token.

```bash
# Auth header forms (equivalent)
curl -u "$TOKEN:" https://api.mercury.com/api/v1/accounts
curl -H "Authorization: Bearer $TOKEN" https://api.mercury.com/api/v1/accounts
```

## Core Operations with Exact Signatures

All paths are relative to:
- Production: `https://api.mercury.com/api/v1`
- Sandbox:    `https://api-sandbox.mercury.com/api/v1`

All responses are `application/json`. All POST bodies are `application/json`.
All timestamps are ISO 8601 UTC.

### Accounts

```
GET /accounts
  → { "accounts": [ {id, name, accountNumber, routingNumber, type,
                     status, balance, currentBalance, kind,
                     nickname, legalBusinessName, ...}, ... ] }

GET /account/{id}
  → single account object

GET /account/{id}/statements
  → list statements for an account (cursor-paginated)
```

### Transactions

```
GET /account/{id}/transactions
  Query: limit, offset, status, start, end, search, order
  → { "transactions": [ ... ], "total": N, "next": cursor|null }

GET /account/{id}/transaction/{txId}
  → single transaction (account-scoped form)

GET /transactions/{txId}
  → single transaction without account path
  (added in 2024 changelog; preferred for webhook handlers
  that only know the transaction id)
```

Common transaction fields: `id`, `amount`, `createdAt`, `postedAt`,
`status` (`pending`, `sent`, `cancelled`, `failed`, `posted`), `note`,
`bankDescription`, `counterpartyName`, `counterpartyId`, `kind`
(`internalTransfer`, `externalTransfer`, `incomingPayment`, `outgoingPayment`,
`fee`, `creditCardCredit`, `creditCardTransaction`, etc.), `feeId`,
`reasonForFailure`, `mercuryCategory`, `details` (rail-specific).

### Recipients

```
GET /recipients
  → { "recipients": [ {id, name, nickname, status, emails,
                       defaultPaymentMethod, electronicRoutingInfo,
                       address, ...}, ... ] }

POST /recipients
  Body: { name, emails, paymentMethod, electronicRoutingInfo,
          domesticWireRoutingInfo, address, ... }
  → created recipient object
```

`electronicRoutingInfo` carries ACH coordinates: `accountNumber`,
`routingNumber`, `bankName`, `electronicAccountType` (`businessChecking`,
`personalChecking`, etc.). `domesticWireRoutingInfo` carries wire-specific
fields. A recipient can hold multiple rail capabilities at once.

### Send money (create transaction)

```
POST /account/{id}/transactions
  Body: {
    "recipientId": "rec_...",
    "amount": 1234.56,
    "paymentMethod": "ach" | "wire" | "check",
    "note": "...",
    "externalMemo": "...",      # appears on counterparty's statement
    "idempotencyKey": "..."     # optional client reference;
                                # see Gotchas — not strictly enforced
  }
  → created transaction object, status starts as "pending"
```

The `paymentMethod` must match a rail the recipient was saved with.
Validation errors are 422 with a JSON body explaining the missing field. The
endpoint is documented at docs.mercury.com/reference/createtransaction.

### Treasury

```
GET /treasury
  → list treasury accounts the token can see

GET /treasury/{id}/transactions
  Query: limit, cursor   → cursor-paginated
  → treasury account transactions

GET /treasury/{id}/statements
  Query: limit, cursor, documentType
  → paginated treasury statements (PDF urls + metadata)
```

Treasury endpoints were added throughout 2023–2024 (see changelog entries
"Treasury API now supports statements" and "Get transactions for a Mercury
Treasury account"). They are NOT a substitution of `account` → `treasury` in
existing routes — the path shapes differ.

### Webhooks

```
POST /webhooks
  Body: { url, eventTypes: ["transaction.updated", ...] }
  → webhook object including secret (shown ONCE)

GET  /webhooks
DELETE /webhooks/{id}
```

Event types include lifecycle events for transactions, recipients, and
account changes. Event payloads share the same structure as the Events API.

### Worked example — multi-account ingest

```python
import os, requests
from requests.auth import HTTPBasicAuth

BASE = "https://api.mercury.com/api/v1"
auth = HTTPBasicAuth(os.environ["MERCURY_TOKEN_LYFE_INSTITUTE"], "")

accts = requests.get(f"{BASE}/accounts", auth=auth, timeout=30).json()
for a in accts["accounts"]:
    next_cursor = None
    while True:
        params = {"limit": 500}
        if next_cursor:
            params["start"] = next_cursor
        r = requests.get(f"{BASE}/account/{a['id']}/transactions",
                         auth=auth, params=params, timeout=30)
        r.raise_for_status()
        body = r.json()
        for tx in body["transactions"]:
            upsert_neon(entity="lyfe_institute",
                        account_id=a["id"], tx=tx)
        next_cursor = body.get("next")
        if not next_cursor:
            break
```

## Pagination Patterns

Mercury uses **cursor-based pagination** on list endpoints. The response
contains a cursor field (typically `next` or an integer cursor on Treasury
endpoints) that the client passes back as a query parameter on the next call.
When the cursor field is missing or null, the iteration is complete.

Common query parameters:

- `limit` — items per page; default is small (often 50). Pass it explicitly.
  The practical maximum is around 500 on transaction endpoints.
- `order` — `asc` or `desc` (where supported)
- `start` / `end` — date or cursor bounds
- `start_after` / `end_before` — cursor bounds on some endpoints
- `status` — filter transactions by lifecycle state

Treasury statements/transactions specifically return an integer cursor in the
response that you pass back as a query param (see changelog entry).

There is **no `page=` parameter**. Calling with `page=2` is silently ignored.

EOS rule: every list call goes through a generator that loops on cursor and
yields rows. Never trust a single page to be complete.

## Rate Limits

Mercury enforces rate limits but does not publish numeric quotas. Treat 429
as authoritative. There is no documented `RateLimit-*` header schema, though
Mercury may add `Retry-After` on 429 responses (verify before relying on it).

EOS-safe defaults:

- Cap concurrency at 4 in-flight requests per token
- Insert 100–250ms jitter between sequential ingest calls during catch-up
- On 429: exponential backoff starting at 2s, doubling, max 60s, with full
  jitter
- On payment-creating POSTs: **never blind-retry**. First call
  `GET /account/{id}/transactions` and search the most recent N for the EOS
  approval id in `note`. Only retry if absent.

Webhook delivery is rate-limited from Mercury's side too — your handler
should ack within seconds (return 200) and do work async, otherwise Mercury
treats it as failure and retries.

## Error Codes and Recovery

Standard HTTP semantics:

| Status | Cause | Recovery |
|---|---|---|
| 400 | Malformed JSON or missing required field | Validate body locally before send |
| 401 | Bad token, revoked token, or wrong environment (sandbox token on prod URL) | Re-mint token; verify env binding |
| 403 | Write call from non-whitelisted IP, or scope-insufficient token | Check token scope and IP whitelist in dashboard |
| 404 | Wrong account/transaction/recipient id, or token cannot see that org | Confirm id; confirm token org binding |
| 409 | Recipient or transaction conflict (e.g. duplicate recipient) | List and reuse existing resource |
| 422 | Validation error (e.g. payment method not supported by recipient) | Read JSON body; fix request shape |
| 429 | Rate limit | Backoff with jitter |
| 5xx | Mercury upstream | Retry with exponential backoff; alert on repeated failure |

Payment-specific failure modes are surfaced as transaction `status=failed`
with a `reasonForFailure` field. The original POST may return 200 with a
pending transaction that later transitions to failed — your reconciliation
loop must handle this asynchronously.

Recovery recipe for payment double-send risk:

```python
def safe_create_payment(account_id, recipient_id, amount, approval_id):
    note = f"eos-approval-id={approval_id}"
    # 1. Pre-check: has this approval already produced a transaction?
    recent = list_recent_transactions(account_id, limit=200)
    for tx in recent:
        if tx.get("note") == note:
            return tx  # already sent
    # 2. Create
    return requests.post(
        f"{BASE}/account/{account_id}/transactions",
        auth=auth,
        json={"recipientId": recipient_id, "amount": amount,
              "paymentMethod": "ach", "note": note},
        timeout=30,
    ).json()
```

## SDK Idioms

There is **no official Mercury SDK** in any language. The community publishes
`mercury-bank-api` on PyPI (0.x, single maintainer, lightly maintained). EOS
uses direct `requests` calls because:

- The endpoint surface is small enough to wrap in 50 lines of Python
- Community SDKs lag changelog updates by months
- Auth and pagination idioms are trivial
- A thin in-house client lets EOS bake in the EOS-specific safety wrapper
  around create-transaction

EOS canonical client shape:

```python
# eos_ai/mercury_client.py
import os, time, requests
from requests.auth import HTTPBasicAuth

class Mercury:
    def __init__(self, token: str, base: str = "https://api.mercury.com/api/v1"):
        self.base = base
        self.auth = HTTPBasicAuth(token, "")
        self.s = requests.Session()
        self.s.auth = self.auth

    def _get(self, path, **params):
        for attempt in range(5):
            r = self.s.get(f"{self.base}{path}", params=params, timeout=30)
            if r.status_code == 429:
                time.sleep(min(60, 2 ** attempt))
                continue
            r.raise_for_status()
            return r.json()
        r.raise_for_status()

    def accounts(self):
        return self._get("/accounts")["accounts"]

    def transactions(self, account_id, **q):
        cursor = None
        while True:
            params = {"limit": 500, **q}
            if cursor:
                params["start"] = cursor
            body = self._get(f"/account/{account_id}/transactions", **params)
            yield from body["transactions"]
            cursor = body.get("next")
            if not cursor:
                return

    def recipients(self):
        return self._get("/recipients")["recipients"]
```

Rules:

1. One client per Mercury organization. Don't share sessions across tokens.
2. All payment-creating calls go through `safe_create_payment`, never the
   raw POST. Authority class CRITICAL.
3. Read tokens are loaded at process start from env. Write tokens are loaded
   only inside the operator-host approval-execution script.

## Anti-Patterns

1. **Hardcoding the base URL.** Sandbox vs prod is a token-environment
   property. Derive at startup from `MERCURY_ENV=sandbox|prod`.
2. **One token across multiple Mercury orgs.** Impossible — tokens are org-
   scoped. Treating them as fungible silently routes calls to the wrong
   entity. Tag every row with the entity slug at ingest.
3. **Polling instead of webhooks for live events.** Wastes rate budget and
   adds latency. Use webhooks as the live edge, polling as the catch-up.
4. **Inline raw bank coordinates in payment calls.** Mercury's API forces
   recipient creation as a separate step for a reason — keeps PII out of
   transaction logs and lets recipients be reviewed once.
5. **Blind retry on payment POST.** Retries without pre-check can double-send.
   Always pre-check by note.
6. **Storing write tokens in agent runtime.** Agents must not be able to send
   money even if they want to. Write tokens live on a separate operator host.
7. **Skipping webhook signature verification.** Anyone with the URL can POST.
   Verify HMAC before trusting any field.
8. **Treating 200 as "money sent."** A 200 means "transaction created, status
   pending." Wait for `status=sent` or `posted` (or webhook event) before
   ack-ing the user.
9. **Page-based loops.** `page=N` is ignored. Use the cursor.
10. **Building business logic on `bankDescription`.** That field is human-
    facing and changes shape. Use `counterpartyId`, `counterpartyName`, and
    structured fields.
11. **Hardcoding payment limits.** Org limits change. Read them from the
    Mercury dashboard or catch the validation error and surface it.
12. **Unbounded statement downloads.** PDF statements are large. Cache by
    `(account_id, year, month)` and skip unchanged.

## Data Model

```
Mercury Organization (1 token = 1 org)
├── Accounts
│   ├── Transactions
│   │   ├── id, amount, status, kind
│   │   ├── counterpartyId / counterpartyName
│   │   ├── note, externalMemo, bankDescription
│   │   ├── createdAt, postedAt, estimatedDeliveryDate
│   │   └── details (rail-specific: ACH | wire | check | card)
│   └── Statements (monthly PDFs)
├── Recipients
│   ├── id, name, nickname, status
│   ├── electronicRoutingInfo (ACH)
│   ├── domesticWireRoutingInfo (wire)
│   ├── address, emails
│   └── defaultPaymentMethod
├── Treasury Accounts (parallel tree)
│   ├── Transactions (cursor-paginated)
│   └── Statements (cursor-paginated)
└── Webhooks
    ├── id, url, secret (shown once)
    └── eventTypes
```

Key invariants:

- **Account ids are stable.** Use them as primary keys in Neon.
- **Transaction ids are stable.** Always upsert by id, never insert-only.
- **Recipient ids are stable.** Reuse them; do not recreate per payment.
- **`status` is mutable** over the lifetime of a transaction. Refetch or
  rely on webhooks.
- **`amount` is signed**: positive for credit, negative for debit, in the
  account's currency (USD for US business accounts).

Multi-entity model (EOS layering):

```
Munoz Conglomerate
├── Lyfe Institute      → Mercury org A → token A
├── Empyrean Studio     → Mercury org B → token B
├── Lyfe Spectrum       → Mercury org C → token C
└── ...
```

Each entity ingests independently. Neon row-level security joins on
`entity_slug` so a CEO agent for Lyfe Institute can never see Empyrean
balances.

## Webhooks and Events

Mercury supports webhooks for real-time event notification, added in 2023
(see "Webhooks now available" changelog entry). Configuration:

1. Create the webhook in the dashboard or via `POST /webhooks` with a target
   URL and a list of event types.
2. Mercury returns a signing secret **once** at creation. Store it securely.
3. On every event, Mercury POSTs JSON to your URL with an HMAC-SHA256
   signature header derived from the secret and the raw body.
4. Your handler verifies the signature, returns 200 fast, and processes async.
5. Failed deliveries (non-2xx, timeouts) retry with exponential backoff for
   a documented retry window. After exhaustion, events are dropped — the
   polling safety net catches them.

Event types cover transaction lifecycle (created, updated, posted, failed),
and may include recipient and account changes. Verify the current set in the
changelog as it evolves.

EOS handler shape (`services/mercury_webhook.py`):

```python
import hmac, hashlib, os, json
from flask import Flask, request, abort

app = Flask(__name__)
SECRET = os.environ["MERCURY_WEBHOOK_SECRET"].encode()

@app.post("/mercury/webhook")
def mercury_webhook():
    raw = request.get_data()
    sig = request.headers.get("X-Mercury-Signature", "")
    expected = hmac.new(SECRET, raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        abort(401)
    event = json.loads(raw)
    enqueue_for_processing(event)   # async, idempotent on event id
    return "", 200
```

The handler MUST be idempotent on `event.id` because retries after a slow ack
will re-deliver the same event.

## Limits

- **Payment limits per org**: ACH, wire, and check each have separate daily
  limits set per Mercury account during onboarding. Higher limits require a
  support ticket (see support.mercury.com "Requesting higher payment limits").
- **Free programmatic ACH payments**: 100 per month included; beyond that,
  Mercury may meter or charge — confirm in current pricing.
- **Pagination ceilings**: practical `limit` max around 500 on transaction
  list endpoints; default is far smaller. Always pass explicitly.
- **Webhook payload size**: bounded but not officially documented; expect
  single-event JSON well under 64 KB.
- **Webhook delivery timeout**: handler must ack within seconds or Mercury
  treats it as failure.
- **Token quantity per org**: Mercury allows multiple tokens per org with
  independent scopes and IP whitelists. Use this to separate read from write.

## Cost Model

Mercury banking itself is free for the standard business account (no monthly
fee, no minimums). API access is included at no extra cost. The cost
dimensions to track:

- **Wire fees**: Mercury charges for outgoing wires (typical fee — verify
  current rate). Wires triggered by automation accumulate just like manual.
- **ACH overage**: 100 free programmatic ACH/month; beyond that, verify
  pricing in the current support article.
- **Treasury yield**: Treasury accounts earn yield (positive cost — track
  per-account).
- **Foreign wires**: Higher fees and FX spread; out of scope for most EOS
  flows but flag if multi-currency is added.
- **Failed payment fees**: Some failure modes (NSF, returned ACH) incur fees
  on the receiving side. Surface these in finance dashboards.

Budget rule: every payment-creating call should log the expected fee (looked
up from a small EOS table) before sending so the founder approval card shows
the all-in cost, not just the principal.

## Version Pinning

Mercury versions the API as a single `v1` and rolls forward additively.
Breaking changes are rare and announced in the changelog
(docs.mercury.com/changelog). There is no `Accept-Version` header to pin to.
Strategy:

- Subscribe to the changelog (RSS or check weekly) and re-research this skill
  whenever an entry mentions auth, pagination, or transaction shapes.
- Pin the community Python package (`mercury-bank-api==<exact>`) if you use
  it; better, don't use it and own a 50-line client.
- Treat new fields as additive: tolerate unknown JSON keys in your parsers
  (use `tx.get("field")`, never strict deserialization).

Notable changelog landmarks:

- 2023: webhooks shipped
- 2023–2024: Treasury API → transactions endpoint → statements endpoint
- 2024: `GET /transactions/{id}` (no account path) shipped
- 2024: send-money API extended to support checks and domestic wires
- ongoing: OAuth2 third-party integration program (separate path)

EOS rule: this skill's `last_researched` field is the authoritative re-check
trigger. If older than ~90 days when a new payment integration is touched,
re-research before deploying.

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

Mercury was founded in 2017 explicitly to be the bank that startups and
modern businesses would want to script against. The API is not a side
project — it's a first-class product surface, sold on
mercury.com/api with the line "Automate finance tasks with API access for
every account." This positioning matters: every API decision optimizes for
"the customer is a developer at a startup," which produces a very different
shape than legacy banks (who treat APIs as a partner-only afterthought) and
than fintechs like Stripe (who sell APIs themselves but aren't a bank).

Three non-negotiable design principles visible in the surface:

1. **Recipient-first money movement.** Mercury forces the two-step flow
   (create recipient, then create transaction) because it makes payment
   automation safer: the bank coordinates live in one auditable place,
   payment requests reference an opaque id, and a compromised payment
   script cannot exfiltrate routing numbers it never sees. This is exactly
   the property EOS needs to wire payments into an agent system.

2. **IP whitelist as a mandatory wall around write capability.** Mercury
   refuses to mint a write token without an IP whitelist. This is the bank
   admitting that a leaked token is a real risk and pushing operators
   toward defense-in-depth from the first minute. Read tokens are
   unrestricted; write tokens are gated.

3. **Cursor pagination and webhooks instead of polling.** Mercury chose
   patterns that scale and produce live data — both hallmarks of an API
   built by people who have run automation themselves.

Tradeoffs vs alternatives:

- **vs Plaid for read-only.** Plaid aggregates many institutions but adds a
  middleman, costs per-call, and breaks when institutions change their
  internal interfaces. Mercury direct gives you the bank's authoritative
  view with zero middleman, at the cost of being Mercury-specific. For an
  EOS that banks at Mercury, direct is strictly better.
- **vs Brex API.** Brex has a comparable API surface for its card+banking
  product. Different banking partner, different risk model, different
  feature set on Treasury and rewards. Choose based on which institution
  holds the money, not the API.
- **vs Stripe Treasury / Stripe Issuing.** Stripe is a payments processor
  that has bolted on banking-like features. Mercury is a bank with a
  payments API. Different mental model. If you need acceptance + treasury,
  Stripe; if you need banking + automation, Mercury.
- **vs legacy bank APIs (Chase, BofA).** No real comparison. Legacy banks
  expose APIs only to enterprise partners through gated programs, with
  weeks of onboarding and contracts. Mercury is self-serve in 60 seconds.

What Mercury is explicitly NOT: a payments processor (no card acceptance,
no checkout), an FX house, or an international remittance platform. It is a
US business bank with a great API.

## Problem-Solution Map and Hidden Capabilities

Things 95% of users never discover:

- **`GET /transactions/{id}` without an account path.** Newer than the
  account-scoped form. Essential for webhook handlers that receive a
  transaction id and don't already know which account it belongs to.
- **Treasury statements as JSON, not just PDF.** The `documentType` query
  parameter on `/treasury/{id}/statements` lets you ask for machine-readable
  data instead of (or alongside) the PDF. Skips the OCR step.
- **`note` as a poor-man's idempotency key.** Mercury doesn't enforce
  uniqueness on `note`, but you can. Write your EOS approval id into note
  on payment create, then before any retry list recent transactions and
  search for that note. This is the EOS-canonical safety pattern.
- **`externalMemo` vs `note`.** `note` is internal-facing (visible in the
  Mercury dashboard to your team). `externalMemo` is what appears on the
  counterparty's bank statement. Use externalMemo for "Invoice #1234" so
  your customer sees it; use note for the EOS approval id.
- **Custom-scope tokens to enforce per-process least privilege.** Instead of
  one read token everywhere, mint one custom token per long-running job
  with only the scopes that job needs. Limits blast radius on leak.
- **Multiple tokens per org with different IP whitelists.** Use this to
  separate "ingest from VPS" (read, no whitelist) from "send from operator
  host" (write, single IP) on the same Mercury org.
- **Webhooks scoped to event types.** You don't have to subscribe to every
  event. Subscribe only to `transaction.updated` if that's all you process,
  cutting handler load.
- **The dashboard exports CSV** for any view you can build with filters.
  Useful as a sanity check against API ingestion: pull the same window via
  CSV and diff against Neon to catch ingest bugs.
- **Mercury Treasury vaults vs checking accounts** are visible through
  different endpoints (`/treasury` vs `/accounts`). A complete cashflow
  picture requires both.
- **Recipient nicknames** are mutable and human-friendly. Use them in
  founder-facing approval cards instead of legal names so the founder
  recognizes "Stripe payout" instead of "Stripe Payments LLC."
- **The dashboard can show pending transactions before the API does** in
  some edge cases (Mercury's internal pipeline isn't strictly ordered).
  Don't alarm on a 30-second gap.

## Operational Behavior and Edge Cases

- **Pending → posted latency.** ACH transactions sit pending for 1–3
  business days before posting. Wires post same-day. Checks can take a
  week. Reconciliation logic must tolerate multi-day pending windows.
- **Transaction status transitions are not strictly monotonic.** A
  transaction can move from `pending` → `failed` (returned ACH), or
  `pending` → `cancelled` (manual cancel before sent). Reconciliation must
  handle every transition, not just success.
- **Counterparty fields populate over time.** A freshly-created transaction
  may have a sparse `counterpartyName` that fills in once Mercury enriches
  it. Re-fetch a few hours later for complete data.
- **Webhook ordering is not guaranteed.** A `transaction.updated` for
  `posted` may arrive before the `transaction.updated` for `pending` if the
  network reorders. Use the event timestamp, and let the latest-status-wins
  rule live in your DB upsert, not the handler.
- **Webhook duplicate delivery is normal.** Backoff retries can re-deliver.
  Idempotent handlers keyed on event id are mandatory.
- **Sandbox dummy data is fixed.** You cannot generate arbitrary historical
  transactions in sandbox. Test ingest with the canned dataset and test
  edge cases with mocks/fixtures.
- **Sandbox does not move money** (obviously) and does not produce real
  ACH/wire confirmations. Sandbox payment calls succeed but no value
  transfers — useful for shape validation only.
- **IP whitelist updates are not instant.** Allow ~minute for a newly-added
  IP to propagate before testing.
- **Token revocation is instant.** Useful for incident response: revoke from
  the dashboard, immediate 401 on next call.
- **Currency is implicit USD.** All amounts are USD-denominated for US
  business accounts. International wires have a separate FX path that adds
  fields to the response.
- **Statement availability is monthly, lagging.** Last month's PDF appears
  in the first week of the new month. Don't poll daily for last month's
  statement on the 31st.
- **Recipient soft-delete.** Removing a recipient from the dashboard sets
  status rather than hard-deleting; the id remains in historical
  transactions. Don't garbage-collect orphan recipients in your local
  cache.
- **Check payments take longer.** Checks include print-and-mail latency.
  Tracking moves through different states than ACH/wire.

## Ecosystem Position and Composition

Composes well with:

- **Neon Postgres / any SQL warehouse** — the natural sink for transaction
  ingest. EOS uses Neon with RLS to keep entities separate.
- **Webhook receivers (Flask/FastAPI/Express)** — small, single-purpose
  HTTP endpoints with HMAC verification and async processing.
- **Approval queues (Linear, Notion, Telegram, Discord)** — the human-in-
  the-loop layer. EOS uses Telegram cards.
- **Accounting tools (QuickBooks, Xero, Brex, Pilot)** — Mercury exports
  CSV for handoff; Pilot in particular has a direct Mercury integration.
  EOS plan: ingest into Neon as source of truth, reconcile against the
  bookkeeper's monthly close.
- **AI agents** — Mercury's API shape (recipient-first, IP-walled writes,
  webhooks) is unusually well-suited to wiring into an agent runtime
  because the dangerous capability is structurally separated from the
  read capability.
- **Tax tools (Carry, Cleer, Bench)** — same handoff pattern as
  bookkeeping.
- **mosh / SSH for the operator host** — the IP-whitelisted machine that
  fires payments needs persistent reachable shell access.

Composes badly with:

- **Anything that polls hard** — wastes rate budget and adds latency.
  Webhooks first, polling only for catch-up.
- **Multi-tenant SaaS that wants to bank-on-behalf-of customers** —
  Mercury is a single-org bank from your perspective. If you need to
  manage many customers' bank accounts via API, look at banking-as-a-
  service providers (Unit, Treasury Prime, Column).
- **Card acceptance flows** — Mercury isn't an acquirer. Pair with Stripe
  for acceptance, Mercury for the cash that lands.

## Trajectory and Evolution

Release cadence is steady, additive, and announced in the changelog at
docs.mercury.com/changelog. Notable arc:

- **2017–2020.** Founding, initial product, dashboard-first.
- **2020–2022.** API beta → GA, tokens, basic accounts/transactions/
  recipients/payments. Read+write split with IP whitelist.
- **2023.** Webhooks shipped. Treasury API beta. OAuth2 third-party
  integration program opens.
- **2023–2024.** Treasury endpoint coverage expands: transactions, then
  statements, both cursor-paginated.
- **2024.** `GET /transactions/{id}` (no account path) added — directly
  enabling clean webhook handlers. Send-money API extended beyond ACH to
  domestic wires and checks.
- **2025–2026 (current).** Continued additive feature work, tighter
  integration with the dashboard's payment-request UX, ongoing scope and
  custom-token improvements.

Maintenance status: Mercury is an active venture-backed company with the
API as a marketed product. The risk is not abandonment — it's policy
shifts (e.g. underlying banking partner changes, KYC tightening, fee
restructuring) that happen at the bank layer rather than the API layer.

5-year bet: Mercury remains the strongest API-first US business banking
option for solo founders and small teams. Watch for: competitor pressure
from Brex, Rho, Relay; banking-partner shifts; expansion into international
or treasury yield products. None of these threaten the core API surface.

## Conceptual Model and Solution Recipes

**Mental model.** A Mercury organization is a bag of accounts, recipients,
treasury accounts, and webhooks, all reachable through one API token. Money
movement is a two-step ritual: bind a counterparty into a recipient, then
fire a transaction referencing the recipient. Status is a process, not a
fact — every transaction has a lifecycle that resolves over hours or days,
and the API tells you about that lifecycle through both polling and
webhooks.

**One token per org. Read separated from write. Write gated by IP.** That's
the security model. Internalize it and the API stops feeling dangerous.

### Recipe A — Daily transaction ingest into Neon

```python
import os
from eos_ai.mercury_client import Mercury
from eos_ai.db import neon_connect

ENTITIES = {
    "lyfe_institute":  os.environ["MERCURY_TOKEN_LYFE_INSTITUTE"],
    "empyrean_studio": os.environ["MERCURY_TOKEN_EMPYREAN_STUDIO"],
}

def ingest():
    conn = neon_connect()
    for entity, token in ENTITIES.items():
        m = Mercury(token)
        for acct in m.accounts():
            for tx in m.transactions(acct["id"]):
                upsert(conn, entity, acct["id"], tx)
    conn.commit()

def upsert(conn, entity, account_id, tx):
    conn.execute("""
        INSERT INTO finance.transactions
            (entity, account_id, tx_id, amount, status, posted_at, raw)
        VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
        ON CONFLICT (tx_id) DO UPDATE
        SET status = EXCLUDED.status,
            posted_at = EXCLUDED.posted_at,
            raw = EXCLUDED.raw
    """, (entity, account_id, tx["id"], tx["amount"],
          tx["status"], tx.get("postedAt"), json.dumps(tx)))
```

### Recipe B — Webhook handler with HMAC verification

```python
from flask import Flask, request, abort
import hmac, hashlib, os, json

app = Flask(__name__)
SECRET = os.environ["MERCURY_WEBHOOK_SECRET"].encode()

@app.post("/mercury/webhook")
def mercury_webhook():
    raw = request.get_data()
    sig = request.headers.get("X-Mercury-Signature", "")
    if not hmac.compare_digest(
        sig, hmac.new(SECRET, raw, hashlib.sha256).hexdigest()
    ):
        abort(401)
    event = json.loads(raw)
    enqueue(event)            # async, idempotent on event["id"]
    return "", 200
```

### Recipe C — Drafting a payment request (agent-side, read scope only)

```python
def draft_payment_request(entity, account_id, recipient_id, amount,
                          payment_method, reason):
    """Agents call this. Writes to Neon, never to Mercury."""
    approval_id = neon_insert("finance.payment_requests", {
        "entity": entity,
        "account_id": account_id,
        "recipient_id": recipient_id,
        "amount": amount,
        "payment_method": payment_method,
        "reason": reason,
        "status": "awaiting_approval",
        "drafted_by": "agent",
    })
    notify_founder_telegram(approval_id)
    return approval_id
```

### Recipe D — Executing an approved payment (operator host, write scope)

```python
def execute_approved_payment(approval_id):
    pr = neon_fetch("finance.payment_requests", id=approval_id)
    if pr["status"] != "approved":
        raise RuntimeError("not approved")
    note = f"eos-approval-id={approval_id}"
    # Pre-check for double-send
    m = MercuryWrite(os.environ[f"MERCURY_WRITE_TOKEN_{pr['entity'].upper()}"])
    recent = m.list_recent_transactions(pr["account_id"], limit=200)
    for tx in recent:
        if tx.get("note") == note:
            neon_update(approval_id, status="sent", tx_id=tx["id"])
            return tx
    tx = m.create_transaction(
        account_id=pr["account_id"],
        recipient_id=pr["recipient_id"],
        amount=pr["amount"],
        payment_method=pr["payment_method"],
        note=note,
        external_memo=pr.get("external_memo", ""),
    )
    neon_update(approval_id, status="sent", tx_id=tx["id"])
    return tx
```

### Recipe E — Statement archival cron (monthly)

```python
def archive_statements():
    today = date.today()
    for entity, token in ENTITIES.items():
        m = Mercury(token)
        for acct in m.accounts():
            for stmt in m.account_statements(acct["id"]):
                path = f"/opt/OS/finance/statements/{entity}/{acct['id']}/{stmt['period']}.pdf"
                if os.path.exists(path):
                    continue
                download(stmt["url"], path)
```

### Recipe F — Reconciliation against bookkeeping

```python
def reconcile_month(entity, year, month):
    bank_txs = neon_query("""
        SELECT tx_id, amount, posted_at, counterparty_name
        FROM finance.transactions
        WHERE entity = %s
          AND date_trunc('month', posted_at) = %s
    """, (entity, date(year, month, 1)))
    book_txs = neon_query("""
        SELECT external_id, amount, posted_at, vendor
        FROM bookkeeping.entries
        WHERE entity = %s
          AND date_trunc('month', posted_at) = %s
    """, (entity, date(year, month, 1)))
    diff = symmetric_difference(bank_txs, book_txs)
    if diff:
        page_founder("Reconciliation drift in " + entity, diff)
```

## Industry Expert and Cutting-Edge Usage

- **Founder-as-operator pattern.** Solo founders run Mercury through a small
  Python script and a Telegram approval bot. The agent drafts, the founder
  taps approve from a phone, the script on a static-IP host fires the
  payment. This is the EOS shape.
- **Bank-as-source-of-truth.** Modern teams treat the bank's API as the
  authoritative ledger and reduce bookkeeping software to a derived view.
  QuickBooks/Xero get fed from the bank ingest, not the other way around.
  This inverts a 30-year accounting practice and only works because APIs
  like Mercury's are reliable enough to trust as a primary source.
- **Webhook-first cashflow alerts.** Wire arrived → Slack/Telegram ping
  with the EOS context (which invoice, which customer, which entity).
  Founder learns about money landing within seconds, not when they next
  open the dashboard.
- **Per-entity dashboards driven by Neon RLS.** Each Mercury org's data
  lands in Neon tagged with the entity slug. RLS policies scope reads so
  each CEO agent sees only its own entity. Cross-entity queries happen
  through an explicit founder-level view that joins all entities.
- **Approval-card-as-product.** The Telegram/Discord approval card is its
  own UX surface. EOS pattern: amount, recipient, reason, expected fee,
  remaining runway after, an "approve / reject" pair, and a one-line "what
  triggered this draft." The card IS the founder's payment UI.
- **Pre-flight runway check.** Before drafting a payment, agents check
  remaining runway against forecasted burn. Drafts that would cross the
  founder's guardrails get auto-rejected before the card is even sent.
- **Treasury sweep automation.** Excess checking balance gets swept into a
  Mercury Treasury account weekly via the API. Yield earned shows up in
  the cashflow dashboard.
- **Bank-feed-into-AI-context.** The most recent month of transactions is
  injected as context into agent prompts about cashflow questions. The
  agent can answer "how much did we spend on AI APIs last month" without
  any RAG layer because the data is small enough to fit in context.

## EOS Usage Patterns

Mercury is the **primary banking layer** for the Munoz Conglomerate. It is
not optional infrastructure — it's where the money lives.

Canonical EOS conventions:

- **One Mercury org per legal entity.** Lyfe Institute, Empyrean Studio,
  Lyfe Spectrum each have their own Mercury organization with their own
  tokens. No cross-pollination.
- **Read tokens in `eos_ai/.env`.** Named `MERCURY_TOKEN_<ENTITY_SLUG>`.
  Loaded at process start. Used for ingest, statements, balance reads.
- **Write tokens on operator host only.** Named `MERCURY_WRITE_TOKEN_<ENTITY>`.
  Stored in `/opt/operator/.env` on a static-IP machine that is in
  Mercury's IP whitelist for those tokens. Never copied to the VPS.
- **Authority class CRITICAL** for any payment-creating call in
  `authority_engine.py`. Agents draft (read scope), humans approve, the
  operator host sends. This separation is structural, not policy.
- **Daily ingest via cron.** A scheduled Python job calls
  `eos_ai/mercury_ingest.py` per entity, walks every account, upserts
  transactions into `finance.transactions` in Neon. Idempotent on tx id.
- **Webhook handler at `services/mercury_webhook.py`.** Verifies HMAC,
  enqueues to a small async worker that updates Neon. Handler is
  idempotent on event id.
- **Statement archival monthly.** PDFs land in
  `/opt/OS/finance/statements/{entity}/{account_id}/{YYYY-MM}.pdf`.
- **Approval cards via Telegram bot.** `services/telegram_control.py`
  formats payment requests with amount, recipient, reason, fee, post-pay
  runway, approve/reject buttons. Approval flips
  `finance.payment_requests.status` to `approved`.
- **Operator host watcher.** A cron on the operator host polls
  `finance.payment_requests` for `status='approved'` rows and executes
  them via the write-token client with the EOS approval id baked into
  `note`. Status flips to `sent` after success or `failed` after failure.
- **CEO agents read transactions, never write.** The CEO agent for an
  entity has read access to `finance.transactions` filtered by entity via
  RLS. It can answer cashflow questions, draft payment requests, but
  cannot send.
- **Sandbox for shape validation only.** EOS does not run a full sandbox
  parallel — too brittle. Sandbox is used by hand when changing payment
  shapes, then production tested with a $1 transfer to a known recipient.

Verification rule: after any Mercury-touching change, run

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.mercury_client import Mercury
import os
m = Mercury(os.environ['MERCURY_TOKEN_LYFE_INSTITUTE'])
print('accounts:', len(m.accounts()))
"
```

before declaring done. Never assume — hit the API.

## Gotchas

1. **Sandbox token on production URL (or vice versa).** Returns 401 with
   no useful message. Always derive base URL from a `MERCURY_ENV` env var,
   never hardcode.
2. **Write call from non-whitelisted IP.** Returns 403 silently. Whitelist
   is per-token in the dashboard. Allow ~1 minute after editing for
   propagation.
3. **No native idempotency header.** Mercury does not enforce uniqueness on
   any client-supplied key. Retries can double-send. EOS pattern: write
   the EOS approval id into `note`, pre-check by listing recent
   transactions and searching for that note before any retry.
4. **Page-based pagination doesn't exist.** `?page=2` is silently ignored.
   Always use the cursor.
5. **Default `limit` is small.** Pass `limit=500` explicitly on transaction
   list calls or you'll do hundreds of round trips for a year of history.
6. **Webhook signature must be verified.** Mercury HMAC-signs every
   delivery. Anyone with the URL can POST garbage. Verify before trusting
   any field in the body.
7. **Webhook duplicates are normal.** Backoff retries re-deliver. Handlers
   must be idempotent on event id.
8. **`200 OK` on payment create is "pending," not "sent."** Don't ack the
   user until the status transitions. Wait for `sent`/`posted` either via
   refetch or webhook.
9. **Transaction status can move backward** (`pending` → `failed` /
   `cancelled`). Always upsert by id, latest-status-wins.
10. **Counterparty fields fill in late.** A freshly-created transaction may
    have sparse `counterpartyName`. Re-fetch hours later for completeness.
11. **`bankDescription` is human-facing and unstable.** Never key business
    logic on it. Use `counterpartyId` and structured fields.
12. **`paymentMethod` must match recipient capability.** ACH-only recipient
    + wire request = 422. Check `defaultPaymentMethod` and supported rails
    on the recipient before drafting.
13. **Wires cost money.** Each outgoing wire incurs a fee. Surface the
    expected fee in the approval card so the founder sees the all-in cost.
14. **ACH overage may meter or charge.** 100 free programmatic ACH/month;
    beyond that, verify current pricing.
15. **Sandbox dummy data is fixed.** You cannot fabricate historical
    transactions in sandbox. Use mocks for edge cases.
16. **Sandbox payments don't actually move money or generate real
    confirmations.** Useful for shape validation only.
17. **One token per org, never shared.** Tokens are org-scoped. Reusing a
    token across entities silently routes calls to the wrong entity. Tag
    every Neon row with the entity slug at ingest.
18. **Statement availability lags.** Last month's PDF appears in the first
    week of the new month. Don't poll daily on the 31st.
19. **Treasury endpoints use a different path shape.** `/treasury/{id}/...`
    is parallel to `/account/{id}/...`, not a substitution. Don't blindly
    swap segments.
20. **Recipient soft-delete keeps the id.** Deleted recipients still appear
    in historical transactions. Don't garbage-collect from your local
    cache.
21. **Token revocation is instant; new IP whitelist propagation isn't.**
    Plan for ~1 minute lag on whitelist changes; revocations are immediate.
22. **`externalMemo` vs `note` confusion.** `note` is internal (Mercury
    dashboard for your team). `externalMemo` shows on the counterparty's
    statement. Don't put the EOS approval id in `externalMemo` unless you
    want the counterparty to see it.
23. **Webhook handler must ack within seconds.** Slow handlers get treated
    as failures and retried. Always return 200 fast and process async.
24. **Rate limits are not numerically documented.** Treat 429 as
    authoritative. Backoff with jitter. Don't pretend the budget is
    infinite just because Mercury didn't print the number.
25. **Authority class for any write call is CRITICAL.** Per the EOS rule,
    agents draft, humans approve, the operator host sends. Never wire a
    write token into agent runtime. This is the gotcha that ends careers.
