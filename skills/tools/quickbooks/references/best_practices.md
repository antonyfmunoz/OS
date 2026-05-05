# QuickBooks Online — Creator-Level Best Practices

Source of truth: Intuit Developer Portal,
`developer.intuit.com/app/developer/qbo/docs`. Last researched 2026-04-06,
pinned to API v3 minor version 75. SDK references: `python-quickbooks 0.9.12`,
`intuit-oauth 1.2.6`. This document is the creator-level reference for the
EOS Developer Agent — it covers the things you only learn after operating
QBO integrations in production for years across multiple legal entities.

---

## Authentication

QuickBooks Online uses **OAuth 2.0 authorization code flow** against the
**Intuit Identity Platform** (a single sign-on surface shared with TurboTax,
Mint, and Intuit Developer). There is no API key alternative. There is no
service-account flow. Every connection is user-mediated and binds an access
token to exactly one `realmId` (the QuickBooks company you authorized against).

### The five secrets

| Name | Lifetime | Source | Storage |
|---|---|---|---|
| `client_id` | App lifetime | Intuit Developer dashboard | env |
| `client_secret` | App lifetime | Intuit Developer dashboard | env |
| `verifier_token` | App lifetime | Webhooks tab in dashboard | env |
| `access_token` | 60 minutes | Token endpoint | Neon (per realm) |
| `refresh_token` | 100 days from last use, **rolls** | Token endpoint | Neon (per realm) |

### Endpoints

- Authorization: `https://appcenter.intuit.com/connect/oauth2`
- Token / refresh: `https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer`
- Revoke: `https://developer.api.intuit.com/v2/oauth2/tokens/revoke`
- OIDC discovery: `https://developer.api.intuit.com/.well-known/openid_configuration`
- User info: `https://accounts.platform.intuit.com/v1/openid_connect/userinfo`

### Scopes

- `com.intuit.quickbooks.accounting` — the entire accounting API surface
- `com.intuit.quickbooks.payment` — Intuit Payments (separate product)
- `openid profile email phone address` — OIDC claims

Request the minimum you need. Adding scopes later forces a re-consent.

### Authorization request shape

```
https://appcenter.intuit.com/connect/oauth2
  ?client_id=...
  &response_type=code
  &scope=com.intuit.quickbooks.accounting
  &redirect_uri=https://eos.local/oauth/intuit/callback
  &state=<csrf-nonce>
```

The redirect comes back with `code`, `state`, and **`realmId`** as query
parameters. `realmId` is the QuickBooks company ID — store it; you will need
it on every subsequent API call.

### Token exchange

```python
data = {
    "grant_type": "authorization_code",
    "code": code,
    "redirect_uri": "https://eos.local/oauth/intuit/callback",
}
# Plus HTTP Basic auth: client_id:client_secret
```

### Token refresh — the most important rule

**Refresh tokens roll on every refresh.** The response gives you a new
`refresh_token` value. If you do not persist it before returning from the
function, the next refresh will fail with `invalid_grant` and the realm is
locked out until the user re-authorizes through the consent screen.

The correct pattern is one DB transaction:

```python
with conn:
    cur = conn.cursor()
    cur.execute("SELECT refresh_token FROM qbo_tokens WHERE realm_id=%s FOR UPDATE", (realm,))
    old = cur.fetchone()[0]
    new = intuit_refresh(old)
    cur.execute(
      "UPDATE qbo_tokens SET refresh_token=%s, access_token=%s, "
      "access_expires_at=NOW()+INTERVAL '55 minutes', refreshed_at=NOW() "
      "WHERE realm_id=%s",
      (new["refresh_token"], new["access_token"], realm),
    )
```

### Refresh token expiry

Refresh tokens live **100 days from last use**. Every successful refresh
resets the clock. If a realm goes 100 days without an API call, its refresh
token dies and re-consent is required. EOS schedules a weekly no-op
`/companyinfo` GET against every realm to keep tokens warm.

### Revoking access

POST to the revoke endpoint with either the access or refresh token in the
body. Revoking either invalidates both. Use this on tenant offboarding.

---

## Core Operations with Exact Signatures

The QBO API exposes about 35 entities. The ones EOS touches:

| Entity | What it is | Read | Create | Update | Delete |
|---|---|---|---|---|---|
| `CompanyInfo` | Realm metadata | yes | no | yes | no |
| `Account` | Chart of accounts node | yes | yes | yes | yes |
| `Customer` | Sales counterparty | yes | yes | yes | yes |
| `Vendor` | Purchase counterparty | yes | yes | yes | yes |
| `Employee` | Payroll counterparty | yes | yes | yes | no |
| `Item` | Sellable product/service | yes | yes | yes | yes |
| `Invoice` | A/R document | yes | yes | yes | yes |
| `Bill` | A/P document | yes | yes | yes | yes |
| `Payment` | Cash receipt against Invoice | yes | yes | yes | yes |
| `BillPayment` | Cash disbursement against Bill | yes | yes | yes | yes |
| `JournalEntry` | Direct ledger posting | yes | yes | yes | yes |
| `Transfer` | Bank-to-bank | yes | yes | yes | yes |
| `Deposit` | Multi-source bank deposit | yes | yes | yes | yes |
| `CreditMemo` | A/R credit | yes | yes | yes | yes |
| `Purchase` | Cash/credit purchase | yes | yes | yes | yes |
| `TaxAgency` | Tax authority | yes | yes | no | no |
| `Attachable` | File link | yes | yes | yes | yes |

### URL shapes

```
GET    /v3/company/{realmId}/{entity}/{id}?minorversion=75
POST   /v3/company/{realmId}/{entity}?minorversion=75              # create
POST   /v3/company/{realmId}/{entity}?operation=update             # update (full)
POST   /v3/company/{realmId}/{entity}?operation=update             # update (sparse, body has "sparse":true)
POST   /v3/company/{realmId}/{entity}?operation=delete             # delete
POST   /v3/company/{realmId}/{entity}?operation=void               # void (Invoice, Payment, BillPayment)
GET    /v3/company/{realmId}/query?query=...                       # SQL-like read
POST   /v3/company/{realmId}/batch                                 # multi-op
POST   /v3/company/{realmId}/upload                                # Attachable + binary
GET    /v3/company/{realmId}/reports/{reportName}                  # Reports API
```

Required headers on every call:
```
Authorization: Bearer {access_token}
Accept: application/json
Content-Type: application/json   # except multipart upload
```

### CompanyInfo (use as warmup probe)

```bash
GET /v3/company/{realmId}/companyinfo/{realmId}?minorversion=75
```

### Customer create

```json
{
  "DisplayName": "Initiate Arena - Cohort 7 - John Doe",
  "PrimaryEmailAddr": {"Address": "john@example.com"},
  "GivenName": "John",
  "FamilyName": "Doe",
  "CompanyName": "Doe Industries"
}
```

`DisplayName` must be globally unique across Customer, Vendor, and Employee
within the realm. Pre-check with a query before creating.

### Invoice create (most common EOS write)

```json
{
  "Line": [{
    "DetailType": "SalesItemLineDetail",
    "Amount": 750.00,
    "SalesItemLineDetail": {
      "ItemRef": {"value": "19"},
      "Qty": 1,
      "UnitPrice": 750.00,
      "TaxCodeRef": {"value": "NON"}
    },
    "Description": "Initiate Arena - Tier 1 enrollment"
  }],
  "CustomerRef": {"value": "31"},
  "TxnDate": "2026-04-06",
  "DueDate": "2026-04-20",
  "CurrencyRef": {"value": "USD"},
  "PrivateNote": "auto-generated by EOS sales agent run abc123"
}
```

### JournalEntry create — the high-risk one

```json
{
  "TxnDate": "2026-04-06",
  "DocNumber": "JE-2026-0042",
  "PrivateNote": "EOS draft — Q1 owner draw, founder approved 2026-04-06",
  "Line": [
    {
      "DetailType": "JournalEntryLineDetail",
      "Amount": 1500.00,
      "Description": "Owner draw",
      "JournalEntryLineDetail": {
        "PostingType": "Debit",
        "AccountRef": {"value": "42"}
      }
    },
    {
      "DetailType": "JournalEntryLineDetail",
      "Amount": 1500.00,
      "Description": "Owner draw",
      "JournalEntryLineDetail": {
        "PostingType": "Credit",
        "AccountRef": {"value": "85"}
      }
    }
  ]
}
```

The sum of `Amount` where `PostingType=Debit` must equal the sum where
`PostingType=Credit`, exactly, to the cent. Use `Decimal`, not `float`. QBO
will reject `1500.000000001` vs `1500.0`.

### Sparse update — the only safe update

```json
{
  "Id": "31",
  "SyncToken": "4",
  "sparse": true,
  "PrimaryEmailAddr": {"Address": "newemail@example.com"}
}
```

Without `"sparse": true`, the body **replaces the entity**. Forgetting this
on an Invoice obliterates every line. Always sparse, always with the latest
SyncToken from a fresh GET.

### Payment (apply cash to an Invoice)

```json
{
  "TotalAmt": 750.00,
  "CustomerRef": {"value": "31"},
  "Line": [{
    "Amount": 750.00,
    "LinkedTxn": [{"TxnId": "208", "TxnType": "Invoice"}]
  }]
}
```

---

## Pagination Patterns

QBO uses **offset pagination via the query language**, not cursor or
header-based pagination. There is no `next` link in responses.

```
SELECT * FROM Invoice
WHERE TxnDate >= '2026-01-01'
ORDER BY Id
STARTPOSITION 1
MAXRESULTS 1000
```

Rules:

- `MAXRESULTS` hard ceiling is **1000**, default is **100**
- `STARTPOSITION` is **1-indexed** (not 0)
- Loop until a page returns fewer than `MAXRESULTS` rows
- Always `ORDER BY Id` for deterministic pagination — without it, concurrent
  writes can cause rows to skip or repeat across pages
- `COUNT(*)` is supported: `SELECT COUNT(*) FROM Invoice WHERE ...`. Use it
  to size jobs before paging.

```python
def paginate(qb_get, entity, where=""):
    pos, page = 1, 1000
    while True:
        q = f"SELECT * FROM {entity} {where} ORDER BY Id STARTPOSITION {pos} MAXRESULTS {page}"
        rows = qb_get(q)
        yield from rows
        if len(rows) < page:
            return
        pos += page
```

The Reports API does not paginate. Each report response is the full result
for the date range you supplied. For very wide reports (GeneralLedger over a
year), shard by month.

---

## Rate Limits

QBO enforces multiple overlapping ceilings per realm per app:

| Limit | Value | Scope |
|---|---|---|
| Per-minute total | **500 req/min** | per realmId |
| Per-second concurrency | **10 concurrent** | per realmId per app |
| Batch endpoint | **40 batches/min** | per realmId per app |
| Heavy endpoints (Reports, GL queries) | **~200 req/min** | per realmId |
| Monthly cap (Builder tier) | **500,000 calls** | per app |

Hitting any limit returns **HTTP 429** with no machine-readable retry hint.
The recommended backoff is **60 seconds**, then resume.

EOS pattern:
- Per-realm semaphore (max 8 concurrent — leave headroom under 10)
- Per-realm token bucket sized at 480/min (95% of ceiling)
- Global circuit breaker on consecutive 429s — open for 90 seconds
- Reports API has its own bucket sized at 180/min

```python
import time, threading
class RealmLimiter:
    def __init__(self, rate=480, concurrency=8):
        self.tokens = rate
        self.rate = rate
        self.last = time.monotonic()
        self.sem = threading.Semaphore(concurrency)
        self.lock = threading.Lock()
    def acquire(self):
        self.sem.acquire()
        with self.lock:
            now = time.monotonic()
            self.tokens = min(self.rate, self.tokens + (now - self.last) * (self.rate / 60))
            self.last = now
            if self.tokens < 1:
                time.sleep((1 - self.tokens) * (60 / self.rate))
                self.tokens = 1
            self.tokens -= 1
    def release(self):
        self.sem.release()
```

---

## Error Codes and Recovery

QBO returns errors in a `Fault` envelope:

```json
{
  "Fault": {
    "Error": [{
      "Message": "Stale Object Error",
      "Detail": "Stale Object Error : You and ... ",
      "code": "5010",
      "element": ""
    }],
    "type": "ValidationFault"
  },
  "time": "2026-04-06T12:00:00.000-07:00"
}
```

### Common error codes

| Code | Type | Meaning | Recovery |
|---|---|---|---|
| `100` | AuthenticationFault | Token invalid/expired | refresh + retry once |
| `270` | AuthenticationFault | Realm not authorized | re-consent flow |
| `500` | SystemFault | Internal QBO error | retry with jitter |
| `610` | SystemFault | Object not found | propagate as 404 |
| `2010` | ValidationFault | Required param missing | fix payload, do not retry |
| `2020` | ValidationFault | Required field missing | fix payload |
| `2500` | ValidationFault | Invalid reference ID | refetch reference |
| `4001` | ValidationFault | Invalid query | fix query, do not retry |
| `5010` | ValidationFault | **Stale Object** (SyncToken mismatch) | refetch + retry |
| `6000` | ValidationFault | Business validation (e.g. unbalanced JE) | fix payload |
| `6240` | ValidationFault | Duplicate DocNumber | choose new number |
| `10000` | SystemFault | Unknown error | retry with backoff |

### Recovery matrix

- **Stale Object (5010)** → GET the entity, copy SyncToken, reapply mutation,
  retry once. If it fails again, escalate to human — concurrent edit storm.
- **AuthenticationFault (100)** → trigger refresh, retry the original call
  exactly once. If refresh itself fails, mark realm as needing re-consent
  and STOP all writes for that realm.
- **429** → sleep 60s, retry. Open per-realm circuit breaker after 3 in a row.
- **5xx** → exponential backoff 1s, 2s, 4s, 8s, then alert.
- **ValidationFault** → never retry. The payload is wrong. Log, surface to
  the agent, and let it draft a corrected version.

---

## SDK Idioms

### `intuit-oauth` (Python)

```python
from intuitlib.client import AuthClient
from intuitlib.enums import Scopes

auth_client = AuthClient(
    client_id=os.environ["INTUIT_CLIENT_ID"],
    client_secret=os.environ["INTUIT_CLIENT_SECRET"],
    environment="production",  # or "sandbox"
    redirect_uri="https://eos.local/oauth/intuit/callback",
)
auth_url = auth_client.get_authorization_url([Scopes.ACCOUNTING])
# After redirect with ?code=&realmId=
auth_client.get_bearer_token(code, realm_id=realm_id)
# auth_client.access_token, auth_client.refresh_token now populated
```

### `python-quickbooks` (built on intuit-oauth)

```python
from quickbooks import QuickBooks
client = QuickBooks(
    auth_client=auth_client,
    refresh_token=auth_client.refresh_token,
    company_id=realm_id,
    minorversion=75,
)
```

The SDK auto-refreshes when it detects a 401, but **does not persist the
new refresh_token back to your DB**. You must subscribe to the refresh
callback or wrap every call:

```python
def call_with_persist(fn, *a, **kw):
    before = client.refresh_token
    result = fn(*a, **kw)
    if client.refresh_token != before:
        save_refresh_token(realm_id, client.refresh_token)
    return result
```

This is the #1 reason production QBO integrations break silently after a
month — the SDK refreshes in memory and the DB still holds the dead token.

### Always re-instantiate per realm

The `QuickBooks` client is bound to one realm at construction. Do not try to
swap realms on a single client. Build N clients, one per realm, and look
them up by `realm_id`.

---

## Anti-Patterns

- **Sharing one OAuth connection across realms.** There is no such thing.
  Tokens are per-realm.
- **Storing access tokens but not refresh tokens.** Refresh tokens are the
  only durable credential. Access tokens are 1-hour scratch.
- **Not persisting rolled refresh tokens.** Every refresh produces a new one.
  Save it before the function returns or the realm dies.
- **Polling instead of webhooks for change detection.** EventNotifications
  are free, instant, and don't burn rate limit.
- **Webhook handlers that 200 OK after parsing.** 200 OK should be the
  *first* thing the handler does, then process async. Intuit will retry on
  any non-200 with exponential backoff, and slow handlers cause storms.
- **`SELECT *` over Bill or Invoice without a date filter.** Realms with
  years of history will OOM the parser. Always bound by TxnDate.
- **Float arithmetic on amounts.** Always Decimal. Always. JE rejection on
  `1500.0000001` will cost you 30 minutes the first time.
- **Catching all exceptions and retrying.** ValidationFaults must NEVER be
  retried — they will fail forever and burn your rate limit ceiling.
- **Hardcoding entity IDs.** `AccountRef.value="42"` works in your realm and
  is meaningless in another. Look up by `Name` or `AcctNum` per realm.
- **Letting agents POST directly to mutating endpoints.** Drafts → queue →
  human approve → service POSTs. Always.
- **Treating sandbox tokens as production tokens.** Different base URL,
  different data, sometimes different client_id.
- **Not pinning `minorversion`.** Your parsers break the day Intuit ships
  minor 76 and adds a new field your strict schema rejects.

---

## Data Model

The QBO data model is a **double-entry general ledger** wrapped in a REST
veneer. Every transaction-like entity (Invoice, Bill, Payment, JournalEntry,
Deposit, Transfer) ultimately produces ledger postings — equal debits and
credits — against accounts in the chart of accounts. The "entity" you see in
the API is a *higher-level construct* that knows how to generate those
postings on save.

### Chart of accounts (`Account`)

Every account has:
- `AccountType` — Bank, Accounts Receivable, Other Current Asset, Fixed
  Asset, Other Asset, Accounts Payable, Credit Card, Other Current Liability,
  Long Term Liability, Equity, Income, Other Income, Cost of Goods Sold,
  Expense, Other Expense
- `AccountSubType` — finer classification (~80 values)
- `Classification` — Asset, Liability, Equity, Revenue, Expense (derived)
- `CurrentBalance` — point-in-time, only on balance sheet accounts

You cannot delete an account that has historical postings. You can only
make it inactive (`Active: false`).

### Counterparties

- `Customer` — A/R counterparty. Hierarchical: `ParentRef` enables sub-customers
  (jobs). Soft-deleted by setting `Active: false`.
- `Vendor` — A/P counterparty. Has `Vendor1099: true` flag for IRS reporting.
- `Employee` — Payroll counterparty. Cannot be hard deleted.
- `DisplayName` is unique across all three within a realm.

### Items

- `Type` — Inventory, NonInventory, Service, Group, Bundle, Category
- `IncomeAccountRef` — where sales of this item post (Revenue)
- `ExpenseAccountRef` — where purchases of this item post (COGS for inventory,
  Expense for non-inventory)
- `AssetAccountRef` — Inventory entities only

### Transaction entities

| Entity | A/R or A/P | Posts to |
|---|---|---|
| Invoice | A/R | Customer → Income (via Item) |
| SalesReceipt | A/R (cash) | Bank → Income (via Item) |
| CreditMemo | A/R | Income (via Item) → Customer |
| RefundReceipt | A/R | Income → Bank |
| Payment | A/R | Customer → Bank/Undeposited Funds |
| Bill | A/P | Expense (via Item or Account) → Vendor |
| BillPayment | A/P | Vendor → Bank |
| Purchase | direct | Bank/CreditCard → Expense |
| Deposit | direct | Undeposited Funds → Bank |
| Transfer | direct | Bank → Bank |
| JournalEntry | direct | any → any (must balance) |

### Linked transactions

Almost every transaction can have `LinkedTxn[]` pointing at other transactions
(Payment → Invoice, BillPayment → Bill, CreditMemo → Invoice). The link is
how QBO knows to apply the cash. Without it, you create unapplied cash.

---

## Webhooks and Events

QBO **EventNotifications** are the only sane way to detect entity changes.
They are HTTP POST callbacks, sent per-realm, batched, signed with HMAC-SHA256,
and delivered with at-least-once semantics within a few seconds of the
underlying mutation.

### Configuration

Configured in the Intuit Developer dashboard under your app's **Webhooks**
tab. You specify:
- **Endpoint URL** — must be HTTPS, publicly reachable, validated by Intuit
- **Verifier token** — Intuit generates this; copy it into your env
- **Subscribed events** — entity types and operations (Create, Update,
  Delete, Merge, Void). You can subscribe to just the entities you care
  about (Invoice, JournalEntry, Customer, etc.)

The same endpoint receives notifications for every realm authorized to your
app. Use the `realmId` in each notification to route.

### Payload shape

```json
{
  "eventNotifications": [{
    "realmId": "1234567890",
    "dataChangeEvent": {
      "entities": [
        {"name": "Invoice",     "id": "208", "operation": "Create", "lastUpdated": "2026-04-06T12:00:00.000Z"},
        {"name": "Customer",    "id": "31",  "operation": "Update", "lastUpdated": "2026-04-06T12:00:01.000Z"},
        {"name": "JournalEntry","id": "147", "operation": "Delete", "lastUpdated": "2026-04-06T12:00:02.000Z"}
      ]
    }
  }]
}
```

A single POST may contain multiple realms × multiple entities. Iterate the
full structure.

### Signature verification — DO THIS FIRST

The `intuit-signature` header is the **base64-encoded** HMAC-SHA256 of the
**raw request body** using your **verifier token** as the key.

```python
import hmac, hashlib, base64, os
from flask import request, abort

VERIFIER = os.environ["INTUIT_WEBHOOK_VERIFIER_TOKEN"].encode()

@app.post("/qbo/webhook")
def qbo_webhook():
    sig_header = request.headers.get("intuit-signature", "")
    raw = request.get_data()  # MUST be raw bytes, not request.json
    digest = hmac.new(VERIFIER, raw, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode()
    if not hmac.compare_digest(expected, sig_header):
        abort(401)
    # 200 IMMEDIATELY, then process async
    enqueue_for_processing(raw)
    return "", 200
```

### Critical webhook rules

1. **Verify the signature against the raw body bytes**, not the parsed JSON.
   JSON parsing reorders keys and changes whitespace, breaking the HMAC.
2. **Return 200 OK immediately** — within a few hundred ms. Process the
   payload asynchronously (enqueue to a worker queue, then return).
3. **Webhooks are at-least-once** — design handlers to be idempotent. The
   `id + operation + lastUpdated` triple is a good dedup key.
4. **Webhooks contain IDs only, not entity bodies.** You must call the API
   to fetch the actual entity. Do this in your worker, not the webhook
   handler.
5. **Subscribe narrowly.** If you only care about Invoice and JournalEntry,
   don't subscribe to Customer — fewer events, less work.
6. **Intuit retries failed deliveries** with exponential backoff over ~36
   hours. A bad endpoint will get hammered. Either fix it or unsubscribe.
7. **Order is not guaranteed.** A Create and a Delete for the same entity
   may arrive in either order. Use `lastUpdated` for ordering inside your
   worker, not delivery sequence.
8. **No payload on Merge events** beyond IDs — you must query both old and
   new entities to understand what merged.

### Local development with webhooks

Intuit cannot reach `localhost`. Use `ngrok http 5000` and configure the
ngrok URL in the dashboard. Sandbox webhooks fire from sandbox-specific
domains; check the dashboard's allowlist if your firewall is paranoid.

---

## Limits

Beyond rate limits, QBO has structural limits worth knowing:

| Thing | Limit |
|---|---|
| Query result page | 1000 rows max |
| Batch sub-requests | 30 per batch |
| JournalEntry lines | 500 lines per JE |
| Invoice lines | 750 lines per Invoice |
| Description fields | 4000 chars |
| Memo / PrivateNote | 4000 chars |
| Custom fields per entity | 3 (QBO Plus/Advanced) |
| Attachment file size | 100 MB per file |
| Attachable types | PDF, JPG, PNG, GIF, DOC, DOCX, XLS, XLSX, TIF, TIFF, CSV, TXT |
| Account hierarchy depth | 5 levels |
| Customer hierarchy depth | 5 levels |
| Active accounts (Plus) | 250 |
| Active accounts (Advanced) | unlimited |
| Inventory items (Plus) | unlimited |
| Currency switching | one-way (cannot revert multi-currency) |
| Closing date | 1 per realm, password-protected |

---

## Cost Model

QBO API itself is **free** for production apps after publishing through the
Intuit App Store. Pre-publish (development phase), apps are limited to **5
authorized realms** maximum and the **Builder tier** monthly cap of 500,000
calls. After publishing, the cap lifts and you can connect unlimited realms.

The **revenue model** for Intuit is the underlying QBO subscription, not the
API. Each realm requires a paying QBO subscription (Simple Start, Essentials,
Plus, or Advanced). Some entities and reports are gated:

- `Class` and `Location` tracking → Plus or Advanced
- Inventory items → Plus or Advanced
- Multi-currency → Essentials or higher (and one-way)
- Custom fields → Advanced for full power
- Reports API for some advanced reports → Plus or Advanced

API calls do not bill the user. They count against your app's monthly cap
during dev and your rate limits in production.

---

## Version Pinning

The QBO API has two version axes:

1. **Major version** — `v3` in the URL path. Has been v3 since 2014. No v4
   announced. Treat as stable.
2. **Minor version** — `?minorversion=N` query parameter. Increments roughly
   quarterly. Each minor version **strictly adds** fields and capabilities;
   it does not remove. Pinning protects you from new fields appearing in
   responses and breaking strict schema parsers.

### How to pin

Pass `minorversion=75` on **every** request, including the OAuth refresh
endpoint (it ignores it but it's free) and webhook re-fetches. Do NOT rely
on a global default — Intuit can change the default minor version on you.

```python
session.params = {"minorversion": "75"}  # requests.Session default
```

### Upgrading minor versions

1. Read the release notes for every version between yours and the target.
2. Diff the entity schemas — Intuit publishes a JSON diff per version.
3. Test in sandbox against the target version for at least one full sync
   cycle (24h minimum).
4. Bump the constant in one place. Never inline.
5. Roll forward, never backward — once you depend on a new field, you
   cannot un-depend on it without code changes.

### Available minor versions (2026-04)

Minor versions 75 and 76 are current. Minor versions 1–74 were retired in
the January 2025 sweep — Intuit auto-migrated all callers to 75. Pin to 75
unless you specifically need a 76 field.

### Major version transitions

There has not been one in over a decade. If Intuit ever announces v4, expect
a 12-month dual-support window. Plan for it but don't preemptively abstract
for it.

---

## Design Intent and Tradeoffs

The QBO API is designed by accountants for accountants, then wrapped in
REST. This produces several non-obvious design choices.

### Choice 1: Per-realm endpoints, no cross-tenant queries

You cannot query "all invoices across all my customers' QBO companies." Every
URL has a `realmId`. The intent is **strict tenant isolation** — Intuit
guarantees that no app can ever leak data across companies, even by accident.
The tradeoff is that multi-entity portfolio views must fan out N requests
and aggregate client-side.

### Choice 2: Optimistic concurrency via SyncToken

Every entity has a `SyncToken` that increments on every save. Updates must
include the current SyncToken. Stale tokens fail with 5010. The intent is
to make concurrent edits **detectable** rather than merging silently. The
tradeoff is that every update is two round trips: GET to read SyncToken,
POST to update. The Reports API has no equivalent because it's read-only.

### Choice 3: SQL-like query, not GraphQL or complex filters

The Intuit query language looks like SQL but is dramatically reduced — no
JOINs, no OR across fields, no nested aggregates, limited to one entity per
query. The intent is to make it cheap to evaluate against the underlying
ledger storage without running general-purpose SQL across denormalized data.
The tradeoff is that some logical questions (e.g. "all customers with no
invoices in the last 90 days") require client-side joining.

### Choice 4: Sparse update opt-in, not opt-out

Updates default to full replacement, requiring `"sparse": true` to do a
patch. The intent is to make the destructive case explicit and the safe
case opt-in. The tradeoff is that forgetting `sparse` is the most common
cause of catastrophic data loss in QBO integrations. EOS treats sparse-by-
default as a wrapper rule.

### Choice 5: Batch endpoint with per-item bId

Up to 30 sub-requests in one POST, each with a `bId` (batch ID), and
responses come back keyed by bId. The intent is **atomic-ish bulk operations**
that don't burn 30 rate-limit slots. The tradeoff is that batches are NOT
transactions — sub-requests can succeed or fail independently. You get a
mixed-status response and must reconcile.

### Choice 6: Webhooks instead of long-polling or pull cursors

Push-only change notification, no `?since=` query parameter on entities. The
intent is to nudge integrators toward event-driven architectures. The tradeoff
is that bootstrapping a new realm requires a full sync via paginated query,
and webhooks alone cannot reconstruct historical state.

### Choice 7: Reports API as a separate, structured surface

Reports are not queryable via SQL — they have their own URL pattern and
return a tree of rows/columns/summaries, not entity arrays. The intent is
to give accountants the same views they'd see in QBO's UI, including
running totals and group subtotals. The tradeoff is that you cannot easily
parameterize reports the way you can queries.

---

## Problem-Solution Map and Hidden Capabilities

### "I need to know when an invoice gets paid"
→ Subscribe to webhook events for `Invoice` (Update) and `Payment` (Create).
On Payment Create, fetch the Payment, look at `LinkedTxn[]` for Invoices,
and update your local state.

### "I need a real-time bank feed"
→ Use the BankAccount + Transaction endpoints. Bank feeds themselves are a
separate Intuit product (`bankfeeds.api.intuit.com`) requiring a partner
agreement. Most apps integrate with Plaid or Yodlee instead and write
results into QBO via JournalEntry or Deposit.

### "I need to back-date a transaction into a closed period"
→ Set the closing-date password header (`Intuit-Tid`) and supply the
password as a header value on the request. Agents must NEVER do this
without explicit per-write founder approval.

### "I need to attach a receipt to a Bill"
→ POST multipart to `/v3/company/{realmId}/upload`. The metadata part
references the Bill via `AttachableRef[].EntityRef.value`. Returns an
`Attachable` object linked to the Bill.

### "I need to map a chart of accounts across realms"
→ There is no shared COA. Each realm has its own. Build a translation
layer keyed on `AccountSubType` + `Name` if you need cross-realm
consolidation.

### "I need to detect a deleted entity"
→ Webhook with `operation: Delete`, OR query
`SELECT * FROM CDCEntity WHERE timestamp > '...'`. The CDC (change data
capture) endpoint is a hidden capability — `GET /v3/company/{realmId}/cdc?entities=Invoice,Customer&changedSince=2026-04-01T00:00:00`.

### "I need to find a transaction by external reference"
→ Most entities have `PrivateNote` (free text) and a few have `DocNumber`.
Stamp your external ID into PrivateNote at create time, then query
`WHERE PrivateNote LIKE '%external-id-...%'`.

### "I need to delete a Customer that has Invoices"
→ You can't. Soft-delete via `Active: false` on a sparse update. Customers
with txns can be deactivated but never hard-removed.

### "I need to convert a Bill to a Vendor Credit"
→ Different entity (`VendorCredit`). Create it fresh and use `LinkedTxn`
to apply against the Bill.

### "I need to test multiple realms in development"
→ Sandbox supports multiple companies under one developer account. Create
each via the dashboard. Each has its own `realmId`.

### Hidden: `query` over `Class` and `Location`
→ Plus/Advanced tracking dimensions. Most integrations forget these exist.
Querying `SELECT * FROM Class` returns the realm's class hierarchy — useful
for departmentalized P&L.

### Hidden: `Preferences` entity
→ `GET /v3/company/{realmId}/preferences` returns the realm's full settings
tree — currency, tax mode, class tracking enabled, custom field config.
Read this once at realm onboarding and cache.

---

## Operational Behavior and Edge Cases

### Eventual consistency

A POST that returns 200 with a new entity ID does not guarantee that the
entity is immediately queryable. There is a small window (usually <2s,
occasionally up to 30s) where a `SELECT * FROM Invoice WHERE Id='...'`
returns nothing. Your code must be ready to retry GETs after creates.

### Time zones

`TxnDate` is a date, not a datetime — it has no time component and is
interpreted in the realm's configured time zone. `MetaData.CreateTime` and
`MetaData.LastUpdatedTime` are datetimes in the realm's time zone, NOT UTC.
Convert at the boundary, store UTC internally.

### Currency

Multi-currency realms have a `CurrencyRef` on every transaction. The home
currency is set at realm creation and **cannot be changed**. Foreign-
currency transactions also carry `ExchangeRate` — capture it; QBO does not
recompute historical rates.

### Soft delete vs hard delete

Some entities (Customer, Vendor, Item, Account, Employee) support only
soft-delete via `Active: false`. Transaction entities (Invoice, Bill,
JournalEntry, etc.) hard-delete via `?operation=delete`. Voiding (Invoice,
Payment, BillPayment) is different from deleting — it keeps the record but
zeros the amount and stamps "VOID" in the description.

### Duplicate prevention

QBO does not enforce idempotency keys. Two identical Invoice POSTs will
create two Invoices. Use `DocNumber` (must be unique per entity type per
realm if `PreferencesPaymentInfo.DocNumberPattern` is enforced) or
`PrivateNote` markers + dedup queries before creating.

### Attaching files

The upload endpoint accepts multipart/form-data with two parts: a JSON
metadata part naming the Attachable, and a binary file part. Maximum 100MB
per file. Returns the Attachable ID and a download URL valid for 15 minutes.

### Transactions and atomicity

The batch endpoint is NOT a database transaction. Sub-requests succeed and
fail independently. There is no rollback. If you need atomicity (e.g. an
Invoice + Payment that must both succeed), you must implement compensating
deletes on partial failure.

### Account closures

A realm whose subscription lapses returns 403 on every request after a
grace period. Detect this and route to a different alert path than auth
failures — the user needs to pay Intuit, not re-consent.

---

## Ecosystem Position and Composition

QBO is the **canonical accounting layer** in the SMB SaaS ecosystem in the
US, alongside Xero (international) and FreshBooks/Wave (lower end). For
most US-based businesses, QBO is the system of record for the books, even
if other systems hold the operational data.

### Common compositions

- **Stripe + QBO** — Stripe is the payment processor, QBO is the ledger.
  Stripe charges flow into QBO via the Stripe Connector or via custom
  Payment + Deposit creation.
- **Bill.com + QBO** — Bill.com handles A/P workflow, syncs Bills and
  BillPayments into QBO.
- **Gusto + QBO** — Gusto runs payroll, posts a single JournalEntry per
  pay period summarizing wages, taxes, and net pay.
- **Plaid + QBO** — Plaid pulls bank transactions, code maps them to
  Accounts, posts as Purchase or Deposit.
- **Shopify + QBO** — Shopify orders flow as SalesReceipt or Invoice; the
  QBO Connector for Shopify is the canonical bridge.
- **Apify + QBO (EOS)** — receipt scraping into Attachable + drafted Bill.
- **EOS itself** — drafts JournalEntries for human approval, generates
  Invoices for Initiate Arena sales, ingests Reports for CEO dashboards.

### Where QBO fits in EOS architecture

- **Above:** CEO agent, portfolio advisor, financial dashboards
- **Beside:** Stripe (collection), CRM (lead → invoice), Apify (receipts)
- **Below:** Neon (snapshots, queue, token store), webhook listener service

EOS does NOT use QBO for operational workflows — leads, deals, and
fulfillment live in the CRM and Neon. QBO is purely the accounting
post-hoc record.

---

## Trajectory and Evolution

### Where QBO has been

- **2014:** v3 REST API launched, replacing v2 SOAP
- **2016:** OAuth 2.0 mandatory, OAuth 1.0a deprecated
- **2018:** EventNotifications webhooks GA
- **2020:** Reports API expanded with structured rows/columns
- **2022:** Minor version 65, improved batch limits
- **2024:** Minor versions 1–74 retired in mass migration
- **2025 Jan:** Minor version 75 becomes baseline
- **2025 Q3:** Minor version 76 ships with enhanced multi-currency fields
- **2026:** Stable on minor 75/76, no v4 announced

### Where it's going

- Intuit is investing heavily in **AI assistants** inside the QBO product
  itself ("Intuit Assist"), which means more LLM-friendly endpoints are
  likely coming — possibly a natural-language query interface.
- **Ledger-as-a-platform** rumors — Intuit has hinted at an embedded
  accounting offering for non-Intuit apps. If real, this would be a new
  authentication and entity model layered on top of v3.
- **More webhooks coverage** — currently EventNotifications cover only
  data changes, not workflow events (e.g., "report run", "user logged in").
  Expect expansion.
- **OAuth scope granularity** — Intuit has hinted at finer-grained scopes
  beyond the current `accounting` mega-scope.

### What to bet on

- v3 will be stable for years. Build against it.
- Webhooks will stay HMAC-SHA256 signed. The verifier-token model is good.
- Minor version pinning will remain the compatibility lever.
- Per-realm tenancy is foundational and will not change.

### What NOT to bet on

- Reports API getting SQL queryability — unlikely in current architecture
- Cross-realm queries — never going to happen, by design
- Cursor-based pagination — they would have shipped it by now if they
  cared

---

## Conceptual Model and Solution Recipes

### Mental model: realm-as-world, ledger-underneath-CRUD

Hold these two ideas simultaneously:

1. **A realm is its own universe.** Every query, every mutation, every
   webhook is scoped to one realm. There is no global QuickBooks. Your
   integration is a fleet of single-realm clients, not one multi-tenant
   client.

2. **CRUD verbs are ledger sugar.** When you POST an Invoice, you are
   really posting Debit: Accounts Receivable / Credit: Income (split by
   line items). When you POST a Payment, you are posting Debit: Bank /
   Credit: Accounts Receivable, with a `LinkedTxn` link that tells the
   ledger which receivable to clear. Every mutation that violates double-
   entry math will be rejected.

Once you hold these together, every QBO error message reads as ledger
physics: "you cannot delete an account with postings" → because that would
strand the postings. "you cannot edit a closed-period transaction" → because
the closed period has been reported to the IRS and is immutable. "your
JournalEntry is unbalanced" → because debits ≠ credits, not allowed by
double-entry.

### Recipe: full initial sync of a new realm

1. Refresh the access token (always start fresh)
2. GET `/companyinfo/{realmId}` — store realm metadata, currency, time zone
3. GET `/preferences` — store feature flags (multi-currency, class tracking)
4. Paginate `SELECT * FROM Account` — store full chart of accounts
5. Paginate `SELECT * FROM Item` — store product/service catalog
6. Paginate `SELECT * FROM Customer ORDER BY Id`
7. Paginate `SELECT * FROM Vendor ORDER BY Id`
8. Paginate `SELECT * FROM Invoice WHERE TxnDate >= '2024-01-01' ORDER BY Id`
   (windowed by year if older history exists)
9. Paginate Bills, Payments, BillPayments, JournalEntries the same way
10. Subscribe to webhooks for ongoing changes
11. Stamp `last_full_sync_at` on the realm record

### Recipe: incremental sync via CDC

```
GET /v3/company/{realmId}/cdc
  ?entities=Invoice,Bill,Payment,Customer,JournalEntry
  &changedSince=2026-04-05T00:00:00-08:00
```

Returns a single response with each entity's changed rows. Use this as a
fallback when webhook delivery is lagging or as a nightly safety net.

### Recipe: drafting a JournalEntry for human approval

```python
def draft_je(realm_id, lines, narrative, agent_id):
    payload = build_je_payload(lines, narrative)
    validate_balanced(payload)  # Decimal math, raise if unbalanced
    cur.execute(
        "INSERT INTO qbo_pending_writes "
        "(realm_id, kind, payload, narrative, drafted_by, status) "
        "VALUES (%s, 'JournalEntry', %s, %s, %s, 'pending_approval') "
        "RETURNING id",
        (realm_id, json.dumps(payload), narrative, agent_id),
    )
    pending_id = cur.fetchone()[0]
    notify_founder_telegram(pending_id, narrative)
    return pending_id
```

The approver service watches `qbo_pending_writes WHERE status='approved'`
and POSTs them, updating status to `posted` with the new entity ID.

### Recipe: P&L ingestion for CEO dashboards

```python
def ingest_pnl(realm_id, start, end):
    access = ensure_fresh_token(realm_id)
    r = requests.get(
        f"{base_url(realm_id)}/reports/ProfitAndLoss",
        params={"start_date": start, "end_date": end, "minorversion": "75"},
        headers={"Authorization": f"Bearer {access}", "Accept": "application/json"},
        timeout=60,
    )
    r.raise_for_status()
    rows = flatten_report_rows(r.json())  # walks the row/column tree
    for line in rows:
        cur.execute(
            "INSERT INTO financial_snapshots "
            "(realm_id, period_start, period_end, account_path, amount, snapshot_at) "
            "VALUES (%s, %s, %s, %s, %s, NOW()) "
            "ON CONFLICT (realm_id, period_start, period_end, account_path) "
            "DO UPDATE SET amount=EXCLUDED.amount, snapshot_at=NOW()",
            (realm_id, start, end, line.path, line.amount),
        )
```

### Recipe: multi-realm fan-out

```python
def conglomerate_revenue(month):
    realms = list_active_realms()
    with ThreadPoolExecutor(max_workers=len(realms)) as ex:
        futures = {ex.submit(get_pnl, r, month): r for r in realms}
        results = {futures[f]: f.result() for f in as_completed(futures)}
    return sum(r["Income"] for r in results.values())
```

Per-realm rate limit isolation makes parallel fan-out safe up to ~8 realms
without backoff coordination.

---

## Industry Expert and Cutting-Edge Usage

### What the top 1% of QBO integrators do differently

- **Zero-touch token rotation.** Refresh tokens are persisted in a
  transactional DB write that wraps the refresh call. No manual key
  management, no sandbox-to-prod copy-paste.
- **Idempotency markers in PrivateNote.** Every machine-created entity has
  a stable external ID stamped in PrivateNote. Re-runs check before insert.
- **Per-realm circuit breakers.** Not global. A single rogue realm can't
  take down the integration for everyone.
- **Eventually-consistent reconciliation.** Webhooks are the fast path; a
  nightly CDC sweep is the safety net. Both write to the same store.
- **Reports API memoization.** Period-based reports for closed periods are
  immutable. Cache them forever; only re-fetch open periods.
- **Schema diffing on minor version bumps.** Before bumping, run sandbox
  with the new version for a week and diff every entity payload against the
  old version. Catch surprises before prod.
- **Drafts table with full audit trail.** Every machine-generated mutation
  exists as a draft with the agent's reasoning before it ever touches QBO.
- **Realm-aware monitoring.** Alerts are tagged with realm_id so you can
  silence one noisy company without losing visibility on the others.
- **Webhook handler that does nothing but enqueue.** All work happens in
  workers. The handler is 10 lines and 100% test coverage.
- **Currency-safe Decimal math everywhere.** No floats touch any amount,
  ever. Linter rule enforces it.

### Frontier patterns

- **LLM-drafted JournalEntries with structured-output validation.** The
  agent emits a JSON schema-validated payload, the validator checks
  balance and account validity, only then does it become a draft.
- **CDC + webhook hybrid sync.** Webhooks for latency, CDC for completeness,
  reconciliation diffs surfaced as anomalies.
- **Cross-realm consolidation engine.** Map each realm's COA to a canonical
  conglomerate COA via AccountSubType + name fuzzy match. Roll up with
  intercompany elimination entries.
- **Receipt OCR → drafted Bill.** Vision model reads receipt, agent maps
  vendor + accounts, drafts a Bill with the receipt as Attachable.

---

## EOS Usage Patterns

### Pattern 1: Per-realm token store

Neon table:

```sql
CREATE TABLE qbo_tokens (
    realm_id          TEXT PRIMARY KEY,
    entity_name       TEXT NOT NULL,
    refresh_token     TEXT NOT NULL,
    access_token      TEXT,
    access_expires_at TIMESTAMPTZ,
    refreshed_at      TIMESTAMPTZ,
    last_used_at      TIMESTAMPTZ,
    minorversion      INT NOT NULL DEFAULT 75,
    status            TEXT NOT NULL DEFAULT 'active',
    notes             TEXT
);
```

A weekly cron job warms every realm with a `/companyinfo` GET to keep
refresh tokens from expiring.

### Pattern 2: Drafts queue for HIGH-risk writes

```sql
CREATE TABLE qbo_pending_writes (
    id               BIGSERIAL PRIMARY KEY,
    realm_id         TEXT NOT NULL REFERENCES qbo_tokens(realm_id),
    kind             TEXT NOT NULL,
    payload          JSONB NOT NULL,
    narrative        TEXT NOT NULL,
    drafted_by_agent TEXT NOT NULL,
    drafted_at       TIMESTAMPTZ DEFAULT NOW(),
    status           TEXT NOT NULL DEFAULT 'pending_approval',
    approved_by      TEXT,
    approved_at      TIMESTAMPTZ,
    posted_entity_id TEXT,
    posted_at        TIMESTAMPTZ,
    error_text       TEXT
);
CREATE INDEX qbo_pw_status ON qbo_pending_writes(status);
```

Status flow:
`pending_approval → approved → posting → posted` (or → `failed`)

Only the approver service writes to QBO. Agents only INSERT drafts.
The founder approves via Telegram or Discord with a one-tap confirm.

### Pattern 3: Financial snapshots for CEO dashboards

```sql
CREATE TABLE financial_snapshots (
    realm_id     TEXT NOT NULL,
    period_start DATE NOT NULL,
    period_end   DATE NOT NULL,
    report_kind  TEXT NOT NULL,
    account_path TEXT NOT NULL,
    amount       NUMERIC(18,2) NOT NULL,
    snapshot_at  TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (realm_id, period_start, period_end, report_kind, account_path)
);
```

Nightly orchestrator pulls P&L, BalanceSheet, and CashFlow for each realm
for MTD, QTD, YTD, and the prior period for comparison.

### Pattern 4: Webhook handler service

`services/qbo_webhook.py` runs as its own systemd unit with a single Flask
endpoint. It does three things in order:

1. Verify the `intuit-signature` HMAC against the raw body
2. Parse the `eventNotifications[]` and INSERT each entity event into
   `qbo_webhook_events` (for audit + replay)
3. Return 200 OK

A separate worker (`services/qbo_webhook_worker.py`) consumes the events
table, fetches the actual entities from QBO, and updates downstream caches.

### Pattern 5: Multi-entity portfolio view

The portfolio advisor agent receives a question like "what was Q1 revenue
across all entities" and the data layer fans out:

```python
def portfolio_revenue(quarter_start, quarter_end):
    realms = neon_query("SELECT realm_id, entity_name FROM qbo_tokens WHERE status='active'")
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {
            ex.submit(get_pnl_total, r["realm_id"], quarter_start, quarter_end, "Income"): r
            for r in realms
        }
        return [
            {"entity": futures[f]["entity_name"], "revenue": f.result()}
            for f in as_completed(futures)
        ]
```

### Pattern 6: Minor version constant

```python
# eos_ai/qbo_constants.py
QBO_MINOR_VERSION = 75
```

Imported everywhere. Bumping is a one-line change with a deliberate test
cycle in sandbox first.

### Pattern 7: Decimal-only money

```python
from decimal import Decimal, ROUND_HALF_UP

def to_money(x) -> Decimal:
    return Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def assert_balanced(lines):
    debits  = sum((to_money(l["Amount"]) for l in lines if l["...PostingType"]=="Debit"),  Decimal("0"))
    credits = sum((to_money(l["Amount"]) for l in lines if l["...PostingType"]=="Credit"), Decimal("0"))
    if debits != credits:
        raise ValueError(f"unbalanced JE: debits={debits} credits={credits}")
```

---

## Gotchas

This section is the running list of QBO-specific failures that have cost
real time. Append new ones as they're discovered.

- **Refresh token NOT persisted.** Most catastrophic and most common. Wrap
  every refresh in a DB transaction that writes the new token before
  returning.
- **Refresh token 100-day TTL.** Quiet realms die. Cron a weekly warm-up
  call (`/companyinfo`) on every realm.
- **Forgetting `?minorversion=N`.** Intuit changes the default and your
  parsers break with no code change on your side. Always pin.
- **Forgetting `"sparse": true` on updates.** Replaces the entity. Wipes
  Invoice line items. Use a wrapper that defaults to sparse.
- **`SyncToken` mismatch (5010).** GET fresh, retry once. If it fails
  again, escalate as a concurrent edit conflict.
- **Floats in amounts.** `1500.0000001 != 1500.0` in QBO's eyes. Use
  Decimal everywhere.
- **JE not balanced to the cent.** Same root cause. Validate before POST.
- **`DisplayName` collision across Customer/Vendor/Employee.** They share
  a namespace per realm. Pre-check before create.
- **Hardcoding entity IDs across realms.** AccountRef.value="42" works in
  one realm and is meaningless in another. Look up by Name + Type per realm.
- **Webhook handler returning 200 after processing.** Process async, return
  200 first. Slow handlers cause Intuit retry storms.
- **Verifying webhook signature against parsed JSON.** Verify against the
  raw body bytes. JSON parsing changes the bytes.
- **Webhook signature header is base64, not hex.** Compare with
  `hmac.compare_digest` after base64 encoding the digest.
- **Webhooks contain only IDs.** Refetch the entity in a worker.
- **Webhooks are at-least-once.** Dedupe on `(id, operation, lastUpdated)`.
- **Reports API doesn't paginate.** Shard by date range yourself.
- **Reports API isn't SQL queryable.** Different endpoint, different shape.
- **`STARTPOSITION` is 1-indexed.** Off-by-one bugs galore.
- **`MAXRESULTS` cap of 1000.** Don't ask for 5000.
- **No JOIN, no OR-across-fields, no LIKE.** Use STARTSWITH, query
  multiple times, join client-side.
- **Batch endpoint is not transactional.** Sub-requests succeed/fail
  independently. Reconcile in code.
- **Closed-period writes need closing-date password header.** Agents must
  NEVER attempt these without explicit per-write founder approval.
- **Sandbox data resets after ~120 days idle.** Don't build long-running
  state on sandbox.
- **Multi-currency is one-way.** Cannot revert a realm from multi-currency.
- **Currency exchange rate must be supplied** on foreign-currency txns;
  QBO does not auto-fetch historical rates.
- **TxnDate is a date, not a datetime.** No time component.
- **MetaData times are realm-local, not UTC.** Convert at the boundary.
- **`Active: false` for soft delete on Customer/Vendor/Item/Account.** Hard
  delete is forbidden once postings exist.
- **Voiding != deleting.** Void zeros the amount, keeps the record.
- **Eventual consistency on creates.** GET-after-POST may return empty for
  a few seconds. Retry GETs.
- **`?operation=delete` POST**, not HTTP DELETE. REST verbs don't map.
- **Sandbox base URL** is different from production. Don't mix.
- **Sandbox and production sometimes share OAuth client_id, sometimes
  don't.** Read the dashboard.
- **Per-realm rate limit isolation.** Parallel fan-out is safe; per-realm
  serialization is required for the same realm.
- **429 with no retry-after header.** Sleep 60 seconds, then retry.
- **Account hierarchy depth 5.** Deeper structures get rejected at create.
- **`Class` and `Location` are Plus/Advanced only.** Realms on Essentials
  return errors when you try to use them.
- **Custom fields are limited to 3 per entity** on Plus. Don't design
  around more.
- **Attachable upload is multipart with TWO parts.** Metadata + file.
  Single-part uploads silently fail.
- **`PrivateNote` is your only safe machine-readable marker.** Use it for
  external IDs. Most other fields are user-visible and editable.
- **Subscription lapsed → 403, not 401.** Different recovery path than
  auth failure. Tell the user to pay Intuit.
- **App publishing required to exceed 5 realms.** Unpublished apps cap at
  5 connections. Plan the App Store submission early if multi-tenant.
- **Intuit Identity Platform consent screen times out at 10 minutes.** If
  the user takes too long on the OAuth screen, the `code` is invalid.
- **`state` parameter is mandatory** for CSRF protection. Generate per
  authorization request, validate on callback.
- **`redirect_uri` is exact-match.** No wildcards, no path prefixes. Whole
  string must match the registered URI exactly, including query.
- **Webhook endpoint URL changes require dashboard reconfiguration.**
  There is no API to update it programmatically.
- **CDC endpoint requires explicit entity list.** No "all entities" option.
- **`changedSince` on CDC is 30 days max.** Older windows are rejected.
