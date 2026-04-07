---
name: mercury
description: "Use when reading Mercury bank account balances, ingesting transactions for finance dashboards, listing recipients, drafting ACH/wire/check payments for human approval, retrieving statements, configuring webhooks for real-time transaction events, or working with Mercury Treasury accounts across multiple Munoz Conglomerate entities."
allowed-tools: "Read, Bash, Write, Edit, WebFetch"
version: 1.0
source_url: "https://docs.mercury.com/reference"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "Mercury API v1"
sdk_version: "REST (no official SDK; community: mercury-bank-api 0.x)"
speed_category: stable
---

# Tool: mercury

## What This Tool Does

Mercury is a US business banking platform whose REST API exposes account
balances, transaction history, recipients, statements, programmatic ACH/wire/
check payments, Treasury (cash management) accounts, and webhooks for real-time
transaction events. The API is the canonical way to wire Mercury into a finance
operating system: ingest postings, reconcile against ledgers, draft outbound
payments for human approval, and react to deposits the moment they post.

Core capabilities:

- **Account read** — list all accounts, fetch a single account by id, read
  routing/account numbers and current balances
- **Transaction history** — list transactions with cursor-paginated filters
  (date, status, amount), fetch a single transaction by id without an account
  path parameter
- **Recipients** — list and create payees once, then reuse them in payment
  requests so the API never holds raw bank routing details inline
- **Send money** — create ACH, domestic wire, and check transactions against
  an account; transactions may require admin approval depending on token
  scope and payment limits
- **Treasury** — list Mercury Treasury accounts, fetch their transactions,
  download statements (PDF/JSON) with cursor pagination
- **Statements** — paginated retrieval of monthly account statements
- **Webhooks** — real-time HTTPS POST notifications for transaction lifecycle
  events with HMAC signatures and exponential-backoff retry on failure

## EOS Integration

Mercury is the **primary banking layer** for the Munoz Conglomerate. Multiple
legal entities (Lyfe Institute, Empyrean Studio, Lyfe Spectrum, etc.) each
have their own Mercury organizations. EOS uses the API for:

- **Daily transaction ingest.** A scheduled task pulls new transactions from
  every account into Neon (`finance.transactions`) with entity, account id,
  posted amount, counterparty, and raw payload. CEO agents read this table to
  answer questions about cashflow, runway, and revenue per venture.
- **Finance dashboards for CEO agents.** Each entity's CEO agent sees its own
  accounts only — RLS in Neon enforces tenant scoping after ingestion.
- **Drafting payment requests for human approval.** Agents NEVER send money
  autonomously. The drafting flow writes a `payment_request` row, an EA agent
  composes a Telegram/Discord approval card, and only after explicit human
  approval does an operator-side script invoke the Mercury create-transaction
  endpoint with a separate IP-whitelisted token.
- **Webhook ingest.** A `services/mercury_webhook.py` handler receives POSTed
  events, verifies the signature, and writes the event into Neon's
  `finance.events` table for downstream agents.
- **Statement archival.** Monthly cron downloads PDF statements per entity
  per account into `/opt/OS/finance/statements/{entity}/{YYYY-MM}.pdf` for
  bookkeeping handoff.

Canonical EOS pattern:

- Multi-entity: one API token per Mercury organization, stored in
  `eos_ai/.env` as `MERCURY_TOKEN_<ENTITY_SLUG>`
- Read tokens for ingest jobs; **read+write tokens are stored on a separate
  IP-whitelisted host** and only used after human approval recorded in Neon
- All payment creates carry an EOS approval id in the transaction `note`
  field (Mercury has no native idempotency header)
- Authority class for any payment-creating call is **CRITICAL** in
  `authority_engine.py` — agent autonomy ends at "draft," never at "send"

## Authentication

HTTPS Basic Auth with the API token as the username and an empty password,
OR equivalently `Authorization: Bearer <token>`. Tokens are minted from the
Mercury web dashboard under Settings → API Tokens. Three scope tiers:

- **Read** — list/get only
- **Read + Write** — can create transactions and manage recipients without
  admin approval; **requires IP whitelist**
- **Custom** — restricted to selected scopes

Sandbox tokens are minted separately inside the sandbox dashboard and only
work against `https://api-sandbox.mercury.com/api/v1/`. Production tokens
only work against `https://api.mercury.com/api/v1/`. Tokens never expire on a
schedule but can be revoked from the dashboard.

EOS rule: never store a write-scope token in the same `.env` as read tokens,
never bake either into a Docker image, never commit to git. Read tokens live
in `eos_ai/.env`; write tokens live on the operator host only.

## Quick Reference

```bash
# Base URLs
PROD=https://api.mercury.com/api/v1
SANDBOX=https://api-sandbox.mercury.com/api/v1
TOKEN="$MERCURY_TOKEN_LYFE_INSTITUTE"

# List all accounts
curl -u "$TOKEN:" "$PROD/accounts"

# Get one account
curl -u "$TOKEN:" "$PROD/account/$ACCOUNT_ID"

# List transactions for an account (cursor pagination)
curl -u "$TOKEN:" "$PROD/account/$ACCOUNT_ID/transactions?limit=500&order=desc"

# Single transaction by id (no account path needed)
curl -u "$TOKEN:" "$PROD/transactions/$TRANSACTION_ID"

# List recipients
curl -u "$TOKEN:" "$PROD/recipients"

# Create an ACH payment (write scope, IP whitelist required)
curl -u "$TOKEN:" -X POST "$PROD/account/$ACCOUNT_ID/transactions" \
  -H 'Content-Type: application/json' \
  -d '{
    "recipientId": "rec_xxx",
    "amount": 1234.56,
    "paymentMethod": "ach",
    "note": "eos-approval-id=42"
  }'

# Treasury statements (cursor)
curl -u "$TOKEN:" "$PROD/treasury/$TREASURY_ID/statements?limit=50"
```

Python idiom (EOS canonical):

```python
import os, requests
from requests.auth import HTTPBasicAuth

BASE = "https://api.mercury.com/api/v1"
auth = HTTPBasicAuth(os.environ["MERCURY_TOKEN_LYFE_INSTITUTE"], "")

def list_transactions(account_id: str, limit: int = 500):
    out, cursor = [], None
    while True:
        params = {"limit": limit}
        if cursor:
            params["start"] = cursor
        r = requests.get(f"{BASE}/account/{account_id}/transactions",
                         auth=auth, params=params, timeout=30)
        r.raise_for_status()
        body = r.json()
        out.extend(body.get("transactions", []))
        cursor = body.get("next")
        if not cursor:
            break
    return out
```

## Conceptual Model

**Mercury organization → accounts → transactions, plus recipients and
webhooks as siblings.** A token is bound to exactly one organization. Every
account and every transaction the token can see is reachable through that one
org. Treasury accounts are a parallel tree with their own statements endpoint.

Money movement is a **two-step model**: first create or reuse a `recipient`
(name, routing, account, address), then create a `transaction` referencing
the recipient and a payment method. This is the layer that makes Mercury safe
to script — raw bank coordinates never appear in payment calls, only opaque
recipient ids. Payments may post immediately, sit in pending, or require
admin approval depending on token scope, amount, and the org's configured
limits.

Webhooks invert the polling loop: instead of re-listing transactions every
minute, register a webhook URL once and Mercury POSTs you the event. EOS
treats webhooks as the live edge and the polling loop as the safety net.

## Gotchas

- **Wrong base URL.** Sandbox tokens against production (or vice versa) fail
  silently with 401. Always derive base URL from the token's environment.
- **IP whitelist for write tokens.** A write token from a non-whitelisted IP
  returns 403 with no explanation. The whitelist is per-token, set in the
  dashboard. EOS write calls only fire from one operator host.
- **No native idempotency key header.** Mercury does not document an
  `Idempotency-Key` header (unlike Stripe). Retries can double-send. Mitigate
  by writing the EOS approval id into the `note` field, then before retry
  list the most recent N transactions and search for that note.
- **Cursor pagination, not offset.** Loop until the response cursor field is
  null/missing. Do not pass `page=` — there is no page parameter.
- **Webhook signature verification.** Mercury signs each webhook payload with
  HMAC. Verify before trusting any field. Failed deliveries retry with
  exponential backoff, so duplicates are normal — make handlers idempotent
  on event id.
- **Multi-entity mixups.** One token per Mercury org. Never reuse a token
  across entities. Tag every Neon row with the entity slug at ingest time.
- **Authority class for any write call is CRITICAL.** EOS rule: agents draft,
  humans approve, the operator host sends. Never wire a write token into an
  agent's runtime environment.

See references/best_practices.md for the full 19-section creator-level knowledge base.
