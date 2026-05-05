---
name: quickbooks
description: "Use when integrating QuickBooks Online — drafting journal entries, generating invoices, ingesting P&L data, syncing customers/vendors/items, handling Intuit OAuth 2.0 token refresh, processing EventNotifications webhooks, or coordinating multi-realm bookkeeping across Munoz Conglomerate entities."
allowed-tools: "Read, Bash, Write, Edit"
version: 1.0
source_url: "https://developer.intuit.com/app/developer/qbo/docs/api/accounting/all-entities"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "v3 minor 75"
sdk_version: "python-quickbooks 0.9.12 + intuit-oauth 1.2.6"
speed_category: stable
trigger: both
effort: low
context: fork
---

# Tool: quickbooks

## What This Tool Does

QuickBooks Online (QBO) is Intuit's cloud accounting platform. The QBO REST API
v3 exposes the entire double-entry general ledger — Customers, Vendors, Items,
Accounts, Invoices, Bills, Payments, JournalEntries, plus Reports (P&L, Balance
Sheet, Trial Balance, Cash Flow) — through a single per-company endpoint
namespaced by `realmId` (the QuickBooks company identifier).

Core capabilities:

- **Per-realm REST surface** at `https://quickbooks.api.intuit.com/v3/company/{realmId}/...`
  with sandbox at `https://sandbox-quickbooks.api.intuit.com/...`
- **OAuth 2.0 (Intuit Identity Platform)** — authorization code flow, 1-hour
  access tokens, 100-day rolling refresh tokens, scopes `com.intuit.quickbooks.accounting`
  (and optionally `payment`, `openid`, `profile`)
- **Intuit SQL query language** — `SELECT * FROM Invoice WHERE TxnDate > '2026-01-01' STARTPOSITION 1 MAXRESULTS 1000`
- **Batch endpoint** — up to 30 sub-requests per call, mixed CRUD + query, with per-item bId
- **Reports API** — P&L, BalanceSheet, CashFlow, TrialBalance, GeneralLedger as
  structured JSON (rows + columns + summary), parameterized by date/period
- **Attachable API** — upload PDFs, receipts, images and link them to any txn
- **EventNotifications webhooks** — HMAC-SHA256 signed POST callbacks per realm
  on entity create/update/delete (asynchronous, batched, near-real-time)
- **Minor versions** — opt-in field additions via `?minorversion=75` query param;
  pin per request to keep payload shape stable across Intuit rollouts

## EOS Integration

QuickBooks is the canonical source of truth for every Munoz Conglomerate entity's
books. Each legal entity (Lyfe Institute, Empyrean Studio, Lyfe Spectrum, etc.)
is a separate QBO company with its own `realmId`, OAuth refresh token, and chart
of accounts. EOS treats QBO as a HIGH-risk write surface — agents draft, the
founder approves, only then does anything post.

Primary EOS uses:

- **Journal entry drafting** — strategic agents draft `JournalEntry` payloads
  (e.g. accruals, owner draws, intercompany transfers) into a Neon
  `qbo_pending_writes` queue. Founder approves via Telegram or Discord, the
  approver service POSTs to QBO.
- **Initiate Arena invoice generation** — when a CRM lead closes, the sales
  agent assembles an `Invoice` for the customer's realm and posts it directly
  (LOW risk: one-shot, idempotent, customer-visible audit trail)
- **CEO P&L dashboards** — nightly orchestrator pulls Reports API
  `ProfitAndLoss` for each realm, normalizes into Neon `financial_snapshots`,
  feeds CEO agent for "how is each company performing this month"
- **Multi-entity ledger view** — board/portfolio advisor agent fans out queries
  across all realms in parallel, aggregates revenue/expense/cash for the
  conglomerate-wide view
- **Receipt ingestion** — Apify scraper or Gmail attachment hook uploads vendor
  receipts via the Attachable API, links them to drafted Bill entries

Canonical EOS pattern:
- Token store: Neon `qbo_tokens` table keyed by `realmId`, refreshed via
  background job ~50 minutes after issue (access token TTL is 60 min)
- Refresh token TTL: 100 days from last use — touch every realm weekly minimum
- Drafts go to `qbo_pending_writes`; only the approver service holds POST authority
- Every read pins `?minorversion=75` to lock payload shape
- Every webhook handler verifies `intuit-signature` before parsing the body

## Authentication

OAuth 2.0 authorization code flow against Intuit Identity Platform. Three
durable secrets per app + one durable per realm:

| Secret | Scope | Where stored |
|---|---|---|
| `INTUIT_CLIENT_ID` | App-wide | `eos_ai/.env` |
| `INTUIT_CLIENT_SECRET` | App-wide | `eos_ai/.env` |
| `INTUIT_WEBHOOK_VERIFIER_TOKEN` | App-wide | `eos_ai/.env` |
| `refresh_token` | Per realm | Neon `qbo_tokens.refresh_token` |
| `realmId` | Per realm | Neon `qbo_tokens.realm_id` |

Token endpoints:
- Authorize: `https://appcenter.intuit.com/connect/oauth2`
- Token / refresh: `https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer`
- Revoke: `https://developer.api.intuit.com/v2/oauth2/tokens/revoke`
- Discovery: `https://developer.api.intuit.com/.well-known/openid_configuration`

Access tokens live 60 minutes. Refresh tokens live 100 days from last use and
**roll on every refresh** — you must persist the new refresh_token immediately
or the realm is locked out.

## Quick Reference

### Refresh access token (Python, no SDK)

```python
import os, base64, requests
auth = base64.b64encode(
    f"{os.environ['INTUIT_CLIENT_ID']}:{os.environ['INTUIT_CLIENT_SECRET']}".encode()
).decode()
r = requests.post(
    "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer",
    headers={"Authorization": f"Basic {auth}",
             "Accept": "application/json",
             "Content-Type": "application/x-www-form-urlencoded"},
    data={"grant_type": "refresh_token", "refresh_token": current_refresh},
    timeout=30,
)
r.raise_for_status()
tok = r.json()  # {access_token, refresh_token, expires_in, x_refresh_token_expires_in}
# PERSIST tok['refresh_token'] BEFORE returning — it has rolled
```

### Query (SQL-like)

```bash
curl -H "Authorization: Bearer $ACCESS" -H "Accept: application/json" \
  "https://quickbooks.api.intuit.com/v3/company/$REALM/query?minorversion=75&query=$(python3 -c "import urllib.parse;print(urllib.parse.quote('SELECT * FROM Invoice WHERE TxnDate >= \\'2026-01-01\\' STARTPOSITION 1 MAXRESULTS 1000'))")"
```

### Create JournalEntry (Python SDK)

```python
from quickbooks import QuickBooks
from quickbooks.objects.journalentry import JournalEntry, JournalEntryLine, JournalEntryLineDetail
from quickbooks.objects.detailline import AccountRef

je = JournalEntry()
for amt, posting, acct_id in [(1500.00, "Debit", "42"), (1500.00, "Credit", "85")]:
    line = JournalEntryLine()
    line.Amount = amt
    line.Description = "Q1 owner draw — Lyfe Institute"
    detail = JournalEntryLineDetail()
    detail.PostingType = posting
    detail.AccountRef = AccountRef()
    detail.AccountRef.value = acct_id
    line.JournalEntryLineDetail = detail
    je.Line.append(line)
je.save(qb=client)  # client is a QuickBooks(...) instance bound to a realm
```

### Create Invoice

```python
from quickbooks.objects.invoice import Invoice
from quickbooks.objects.detailline import SalesItemLine, SalesItemLineDetail
from quickbooks.objects.base import Ref

inv = Invoice()
inv.CustomerRef = Ref(); inv.CustomerRef.value = "31"
line = SalesItemLine(); line.Amount = 750.00
detail = SalesItemLineDetail(); detail.ItemRef = Ref(); detail.ItemRef.value = "19"
line.SalesItemLineDetail = detail
inv.Line.append(line)
inv.save(qb=client)
```

### Pull Profit & Loss report

```bash
curl -H "Authorization: Bearer $ACCESS" -H "Accept: application/json" \
  "https://quickbooks.api.intuit.com/v3/company/$REALM/reports/ProfitAndLoss?start_date=2026-01-01&end_date=2026-03-31&minorversion=75"
```

### Verify webhook signature (Python)

```python
import hmac, hashlib, base64, os
def verify(body_bytes: bytes, intuit_signature_header: str) -> bool:
    digest = hmac.new(
        os.environ["INTUIT_WEBHOOK_VERIFIER_TOKEN"].encode(),
        body_bytes,
        hashlib.sha256,
    ).digest()
    expected = base64.b64encode(digest).decode()
    return hmac.compare_digest(expected, intuit_signature_header)
```

## Conceptual Model

**Realm is the world. Everything else is a row inside one realm.** A QBO API
client has no global state — every URL is `.../company/{realmId}/...` and every
access token is bound to exactly one realm at issue time. Multi-entity systems
do not share connections; they fan out N parallel single-realm clients.

The data model is a **double-entry ledger wearing CRUD clothing**. Customer,
Invoice, Bill, Payment look like REST resources, but underneath every mutation
posts symmetric debits and credits to the ledger via `JournalEntryLineDetail`.
This is why QuickBooks rejects "logical" mutations that would unbalance books:
you cannot delete an Invoice that has a Payment applied, you cannot edit an
Account that has historical postings, you cannot change a TxnDate into a closed
period without the closing-date password.

The **minor version** is the API's compatibility lever. Each minor version
strictly adds fields — never removes — so pinning protects you from Intuit
rollouts adding noise to your parsers. The major version (v3) has been stable
since 2014.

If you internalize realm-as-world + ledger-underneath-CRUD, every confusing QBO
behavior becomes obvious:
- "Why can't I just PATCH this Invoice?" → because the ledger lines must stay
  balanced; QBO requires sparse updates with `sparse: true` and `SyncToken`
- "Why does the same customer not appear across companies?" → different realms,
  different worlds
- "Why did my refresh fail after I just used it?" → refresh tokens roll, you
  saved the old one

## Gotchas

- **Refresh tokens roll** → if you don't persist the new `refresh_token` from
  every refresh response, the realm is dead and the user must re-authorize.
  Wrap refresh in a transaction with the DB write.
- **Refresh token 100-day TTL from last use** → cron a weekly touch on every
  realm or quiet entities expire silently. Re-auth requires a human in the loop.
- **Sandbox and production use different base URLs** but the same OAuth client
  in most app configurations. Read your app dashboard before assuming.
- **`SyncToken` is mandatory on every update** → fetch the entity, send back
  with the returned token. Skipping it returns `ValidationFault: Stale Object`.
- **`sparse: true` is opt-in** → without it, an update REPLACES the entity.
  Forgetting it on an Invoice update wipes all line items.
- **JournalEntry must balance to the penny** → sum of Debits must equal sum of
  Credits exactly. Floats will bite you. Use `Decimal`.
- **500 req/min per realm + 10 concurrent + 40 batch/min** → 429 means back off
  60 seconds. EOS queues should serialize per realm, not globally.
- **Reports API is NOT SQL-queryable** — different endpoint shape, returns
  rows/columns/summary trees, not entity arrays. Don't try `SELECT * FROM ProfitAndLoss`.
- **Query language quirks** — no `JOIN`, no `OR` across different fields, no
  `LIKE` (use `STARTSWITH`), `MAXRESULTS` cap is 1000, paginate with
  `STARTPOSITION` (1-indexed, not 0).
- **Webhook signature header is `intuit-signature`, base64-encoded** — not hex.
  Compare bytes via `hmac.compare_digest`.
- **Webhooks fire near-real-time but batched** — a single POST may contain
  multiple events for multiple entities. Iterate `EventNotifications[]`.
- **Webhook payload contains IDs only, no entity bodies** → you must re-fetch
  the entity from the API to see what changed.
- **Closed-period writes** require the closing-date password header — agents
  must NEVER attempt these without explicit founder approval per write.
- **Sandbox data resets if untouched** for ~120 days. Don't build long-running
  state on sandbox realms.
- **Minor version drift** — new fields appear when Intuit ships a minor version
  bump. Pin `?minorversion=75` on every request.
- **`DisplayName` collisions** — Customer, Vendor, and Employee share a global
  name namespace per realm. "Acme Inc" as a Customer blocks it as a Vendor.
- **Deleting is `?operation=delete` POST**, not HTTP DELETE → the REST verbs
  don't map to ledger semantics.

See references/best_practices.md for the full 19-section creator-level knowledge base.
