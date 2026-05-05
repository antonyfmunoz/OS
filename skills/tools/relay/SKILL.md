<<<<<<< Updated upstream
---
name: relay
description: "Use when reading Relay account balances, classifying Relay transactions, drafting transfer or bill-pay requests for human approval, reconciling multi-entity treasury between Mercury and Relay, configuring QuickBooks/Plaid/Gusto sync from Relay, or answering any question about Munoz Conglomerate funds held at Relay."
allowed-tools: "Read, Bash, Write, Edit, WebFetch"
version: 1.0
source_url: "https://relayfi.com/"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "N/A — no public REST API as of 2026-04-06"
sdk_version: "N/A — dashboard-only; data ingress via Plaid/QuickBooks/Yodlee bank feeds"
speed_category: human-in-the-loop
trigger: both
effort: medium
context: fork
---

# Tool: Relay (Relay Financial)

## What This Tool Does

Relay is a US business banking platform built for small businesses, multi-entity
operators, and Profit First practitioners. It is a fintech, not a chartered
bank — accounts are FDIC-insured through Thread Bank. The defining product
feature is **20 free checking accounts per business** with named buckets, which
makes Relay the natural home for envelope-style cash management across a
holding company with multiple operating entities.

Core capabilities:

- **Up to 20 individually-numbered checking accounts** per business entity
- **Multi-entity dashboard** — switch between entities without re-authenticating
- **Role-based user access** with approval workflows on payments
- **ACH, wire (domestic + international), check, and physical/virtual debit cards**
- **Bill Pay** with vendor management and approval rails
- **Bank feeds** into QuickBooks Online, Xero, and Gusto
- **Plaid + Yodlee compatibility** for downstream apps that need read access

What Relay does NOT have (verified 2026-04-06):

- **No public REST API.** There is no developer portal, no OAuth client
  registration, no API key issuance for third parties. The only "API" surface
  is the Xero/QuickBooks Bank Feeds protocol and Plaid/Yodlee aggregator
  read-only feeds. (`docs.relay.link` belongs to a different product — Relay
  Protocol, an NFT bridge — and is not related.)
- **No webhooks** for transaction events from Relay directly.
- **No SDK** in any language.

This skill therefore frames Relay as a **human-operator tool**: Antony performs
all writes (transfers, payments, card issuance) inside the Relay web/mobile
dashboard. EOS agents reach Relay data **read-only** by tailing the Plaid
aggregator feed or the QuickBooks Online sync that Relay populates.

## EOS Integration

Relay is the **secondary treasury substrate** for Munoz Conglomerate, sitting
alongside Mercury. The split is intentional:

- **Mercury** — primary operating accounts for Lyfe Institute and Empyrean
  Studio, where API access is required (Mercury has a real REST API).
- **Relay** — multi-bucket cash management for entities that need Profit First
  envelope structure: Lyfe Spectrum, LyfeOS, holding company sweep accounts,
  and personal-brand reserves.

Canonical EOS pattern:

1. **Read path** — `eos_ai/treasury_aggregator.py` pulls Relay balances via
   the existing Plaid item that the personal-finance ingestor already owns.
   Transactions land in Neon under `treasury.transactions` with
   `source='relay_via_plaid'`.
2. **Classification path** — the cognitive loop reads the transaction stream
   and tags each line by entity, P&L category, and Profit First bucket.
3. **Write path** — when an agent decides a transfer is needed (e.g. sweep
   profit bucket → owner pay), it produces a **Transfer Request artifact**
   in the inbox: amount, source bucket, destination bucket, justification,
   urgency. Antony executes inside Relay. The agent never touches money.
4. **Reconciliation** — nightly job diffs Relay's QuickBooks bank feed against
   Neon's mirror; any drift triggers a Notion alert.

Payments are **CRITICAL risk** under EOS authority classes. No agent, no skill,
no script ever submits a payment to Relay. Human-only. Always.

## Authentication

Relay login is **email + password + TOTP MFA** in a browser. There is no
API key, no service account, no OAuth app registration available to customers.

Indirect read access requires one of:

- **Plaid Link** — Antony completes the Plaid handshake once in a Plaid-using
  app. The resulting `access_token` is stored in `eos_ai/.env` as
  `PLAID_RELAY_ACCESS_TOKEN` and used for `/transactions/sync` and
  `/accounts/balance/get` calls.
- **QuickBooks Bank Feed** — set up inside Relay dashboard once; QBO becomes
  the system of record and EOS reads from QBO via the QuickBooks API skill.
- **Yodlee** — only relevant if a downstream app uses Yodlee instead of Plaid.

Re-auth cadence: Plaid items for Relay typically need re-consent every
**90 days** (Plaid's `consent_expiration_time` default). Set a calendar
reminder; an expired item silently stops syncing.

## Quick Reference

### Human operator actions (Antony, in dashboard)

```text
Login:         https://app.relayfi.com/  (email + password + TOTP)
Switch entity: top-left entity dropdown
New transfer:  Move Money → Transfer Between Accounts
Send ACH:      Move Money → Send Payment → ACH
Send wire:     Move Money → Send Payment → Wire / International Wire
Bill Pay:      Bills → Add Bill → review → Approve
Issue card:    Cards → Issue New → choose user + spending limit
Add user:      Settings → Team → Invite (set role)
Approval:      Settings → Approvals → set threshold and approvers
```

### Agent actions (read-only via Plaid)

```bash
# List Relay balances via the existing Plaid item
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.treasury_aggregator import TreasuryAggregator
ta = TreasuryAggregator()
for acct in ta.list_accounts(institution='relay'):
    print(f\"{acct.name:30s}  \${acct.balance:>12,.2f}\")
"

# Sync recent Relay transactions into Neon
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.treasury_aggregator import TreasuryAggregator
TreasuryAggregator().sync_transactions(institution='relay', days=7)
"
```

### Drafting a transfer request artifact (agent → human)

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.treasury_requests import draft_transfer_request
draft_transfer_request(
    from_bucket='Lyfe Institute - Operating',
    to_bucket='Lyfe Institute - Profit',
    amount_usd=500.00,
    reason='Weekly Profit First sweep — 5% of revenue',
    urgency='this_week',
)
"
# Writes a Notion card + Telegram ping. Antony approves and executes manually.
```

## Conceptual Model

**Relay is a dashboard, not an API.** Treat it the same way you treat a paper
filing cabinet that you happen to be able to read through a window. EOS agents
see what is inside (via Plaid/QBO mirrors), reason about it, and write
**instructions for a human** when something needs to change. The human is the
only actuator.

Three layers:

1. **Truth layer** — Relay's own ledger. Mutable only by humans inside the
   Relay dashboard or by Relay's own Bill Pay scheduler.
2. **Mirror layer** — Plaid's `/transactions/sync` cursor + QBO bank feed.
   Read-only, eventually consistent (typical lag: 2-24 hours for ACH, near
   real-time for card swipes).
3. **Action layer** — Notion/Telegram requests authored by EOS, executed by
   Antony. Every action is logged in Neon with a `request_id` for audit.

If you internalize "Relay = filing cabinet, Plaid = window, human = hands,"
every confusing situation becomes obvious.

## Gotchas

- **No API exists.** If you ever find yourself reaching for `requests.post(
  'https://api.relayfi.com/...')`, stop. It does not exist. The hostname
  `api.relayfi.com` is not a public surface as of 2026-04-06.
- **`docs.relay.link` is a different product.** That domain belongs to Relay
  Protocol (NFT/crypto bridge) and has zero relationship to Relay Financial.
  Do not cite it. Do not link to it.
- **Plaid item expiry at 90 days** silently breaks the read path. Add a
  monthly health check that calls `/item/get` and alerts if
  `consent_expiration_time` is within 14 days.
- **Bank feed lag** — QBO bank feed populates on Relay's schedule, not yours.
  Pending ACH may not appear for hours. Never reconcile against "right now."
- **20-account limit per entity.** Multi-entity operators must split across
  entities, not stuff everything into one. Mirror Munoz Conglomerate's
  corporate structure 1:1.
- **Wires require manual MFA every time.** No "remember device" for wire
  approvals. Antony must be physically present.
- **Approval workflows are per-entity, not global.** Setting an approval rule
  on Lyfe Institute does NOT propagate to Empyrean Studio.
- **Thread Bank is the chartered partner, not Relay.** ACH return codes and
  wire trace numbers come back from Thread Bank's processor, not Relay.
  Support tickets that involve federal-reserve-level details may be slow.
- **No statement download API.** PDF statements must be pulled manually from
  the dashboard each month. Schedule this as a recurring human task.
- **CRITICAL — payments are human-only.** Any attempt to automate a Relay
  payment violates EOS authority class CRITICAL. Block in code review.

See references/best_practices.md for the full 19-section creator-level knowledge base.
=======
---
name: relay
description: "Use when reading Relay account balances, classifying Relay transactions, drafting transfer or bill-pay requests for human approval, reconciling multi-entity treasury between Mercury and Relay, configuring QuickBooks/Plaid/Gusto sync from Relay, or answering any question about Munoz Conglomerate funds held at Relay."
allowed-tools: "Read, Bash, Write, Edit, WebFetch"
version: 1.0
source_url: "https://relayfi.com/"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "N/A — no public REST API as of 2026-04-06"
sdk_version: "N/A — dashboard-only; data ingress via Plaid/QuickBooks/Yodlee bank feeds"
speed_category: human-in-the-loop
---

# Tool: Relay (Relay Financial)

## What This Tool Does

Relay is a US business banking platform built for small businesses, multi-entity
operators, and Profit First practitioners. It is a fintech, not a chartered
bank — accounts are FDIC-insured through Thread Bank. The defining product
feature is **20 free checking accounts per business** with named buckets, which
makes Relay the natural home for envelope-style cash management across a
holding company with multiple operating entities.

Core capabilities:

- **Up to 20 individually-numbered checking accounts** per business entity
- **Multi-entity dashboard** — switch between entities without re-authenticating
- **Role-based user access** with approval workflows on payments
- **ACH, wire (domestic + international), check, and physical/virtual debit cards**
- **Bill Pay** with vendor management and approval rails
- **Bank feeds** into QuickBooks Online, Xero, and Gusto
- **Plaid + Yodlee compatibility** for downstream apps that need read access

What Relay does NOT have (verified 2026-04-06):

- **No public REST API.** There is no developer portal, no OAuth client
  registration, no API key issuance for third parties. The only "API" surface
  is the Xero/QuickBooks Bank Feeds protocol and Plaid/Yodlee aggregator
  read-only feeds. (`docs.relay.link` belongs to a different product — Relay
  Protocol, an NFT bridge — and is not related.)
- **No webhooks** for transaction events from Relay directly.
- **No SDK** in any language.

This skill therefore frames Relay as a **human-operator tool**: Antony performs
all writes (transfers, payments, card issuance) inside the Relay web/mobile
dashboard. EOS agents reach Relay data **read-only** by tailing the Plaid
aggregator feed or the QuickBooks Online sync that Relay populates.

## EOS Integration

Relay is the **secondary treasury substrate** for Munoz Conglomerate, sitting
alongside Mercury. The split is intentional:

- **Mercury** — primary operating accounts for Lyfe Institute and Empyrean
  Studio, where API access is required (Mercury has a real REST API).
- **Relay** — multi-bucket cash management for entities that need Profit First
  envelope structure: Lyfe Spectrum, LyfeOS, holding company sweep accounts,
  and personal-brand reserves.

Canonical EOS pattern:

1. **Read path** — `eos_ai/treasury_aggregator.py` pulls Relay balances via
   the existing Plaid item that the personal-finance ingestor already owns.
   Transactions land in Neon under `treasury.transactions` with
   `source='relay_via_plaid'`.
2. **Classification path** — the cognitive loop reads the transaction stream
   and tags each line by entity, P&L category, and Profit First bucket.
3. **Write path** — when an agent decides a transfer is needed (e.g. sweep
   profit bucket → owner pay), it produces a **Transfer Request artifact**
   in the inbox: amount, source bucket, destination bucket, justification,
   urgency. Antony executes inside Relay. The agent never touches money.
4. **Reconciliation** — nightly job diffs Relay's QuickBooks bank feed against
   Neon's mirror; any drift triggers a Notion alert.

Payments are **CRITICAL risk** under EOS authority classes. No agent, no skill,
no script ever submits a payment to Relay. Human-only. Always.

## Authentication

Relay login is **email + password + TOTP MFA** in a browser. There is no
API key, no service account, no OAuth app registration available to customers.

Indirect read access requires one of:

- **Plaid Link** — Antony completes the Plaid handshake once in a Plaid-using
  app. The resulting `access_token` is stored in `eos_ai/.env` as
  `PLAID_RELAY_ACCESS_TOKEN` and used for `/transactions/sync` and
  `/accounts/balance/get` calls.
- **QuickBooks Bank Feed** — set up inside Relay dashboard once; QBO becomes
  the system of record and EOS reads from QBO via the QuickBooks API skill.
- **Yodlee** — only relevant if a downstream app uses Yodlee instead of Plaid.

Re-auth cadence: Plaid items for Relay typically need re-consent every
**90 days** (Plaid's `consent_expiration_time` default). Set a calendar
reminder; an expired item silently stops syncing.

## Quick Reference

### Human operator actions (Antony, in dashboard)

```text
Login:         https://app.relayfi.com/  (email + password + TOTP)
Switch entity: top-left entity dropdown
New transfer:  Move Money → Transfer Between Accounts
Send ACH:      Move Money → Send Payment → ACH
Send wire:     Move Money → Send Payment → Wire / International Wire
Bill Pay:      Bills → Add Bill → review → Approve
Issue card:    Cards → Issue New → choose user + spending limit
Add user:      Settings → Team → Invite (set role)
Approval:      Settings → Approvals → set threshold and approvers
```

### Agent actions (read-only via Plaid)

```bash
# List Relay balances via the existing Plaid item
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.treasury_aggregator import TreasuryAggregator
ta = TreasuryAggregator()
for acct in ta.list_accounts(institution='relay'):
    print(f\"{acct.name:30s}  \${acct.balance:>12,.2f}\")
"

# Sync recent Relay transactions into Neon
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.treasury_aggregator import TreasuryAggregator
TreasuryAggregator().sync_transactions(institution='relay', days=7)
"
```

### Drafting a transfer request artifact (agent → human)

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.treasury_requests import draft_transfer_request
draft_transfer_request(
    from_bucket='Lyfe Institute - Operating',
    to_bucket='Lyfe Institute - Profit',
    amount_usd=500.00,
    reason='Weekly Profit First sweep — 5% of revenue',
    urgency='this_week',
)
"
# Writes a Notion card + Telegram ping. Antony approves and executes manually.
```

## Conceptual Model

**Relay is a dashboard, not an API.** Treat it the same way you treat a paper
filing cabinet that you happen to be able to read through a window. EOS agents
see what is inside (via Plaid/QBO mirrors), reason about it, and write
**instructions for a human** when something needs to change. The human is the
only actuator.

Three layers:

1. **Truth layer** — Relay's own ledger. Mutable only by humans inside the
   Relay dashboard or by Relay's own Bill Pay scheduler.
2. **Mirror layer** — Plaid's `/transactions/sync` cursor + QBO bank feed.
   Read-only, eventually consistent (typical lag: 2-24 hours for ACH, near
   real-time for card swipes).
3. **Action layer** — Notion/Telegram requests authored by EOS, executed by
   Antony. Every action is logged in Neon with a `request_id` for audit.

If you internalize "Relay = filing cabinet, Plaid = window, human = hands,"
every confusing situation becomes obvious.

## Gotchas

- **No API exists.** If you ever find yourself reaching for `requests.post(
  'https://api.relayfi.com/...')`, stop. It does not exist. The hostname
  `api.relayfi.com` is not a public surface as of 2026-04-06.
- **`docs.relay.link` is a different product.** That domain belongs to Relay
  Protocol (NFT/crypto bridge) and has zero relationship to Relay Financial.
  Do not cite it. Do not link to it.
- **Plaid item expiry at 90 days** silently breaks the read path. Add a
  monthly health check that calls `/item/get` and alerts if
  `consent_expiration_time` is within 14 days.
- **Bank feed lag** — QBO bank feed populates on Relay's schedule, not yours.
  Pending ACH may not appear for hours. Never reconcile against "right now."
- **20-account limit per entity.** Multi-entity operators must split across
  entities, not stuff everything into one. Mirror Munoz Conglomerate's
  corporate structure 1:1.
- **Wires require manual MFA every time.** No "remember device" for wire
  approvals. Antony must be physically present.
- **Approval workflows are per-entity, not global.** Setting an approval rule
  on Lyfe Institute does NOT propagate to Empyrean Studio.
- **Thread Bank is the chartered partner, not Relay.** ACH return codes and
  wire trace numbers come back from Thread Bank's processor, not Relay.
  Support tickets that involve federal-reserve-level details may be slow.
- **No statement download API.** PDF statements must be pulled manually from
  the dashboard each month. Schedule this as a recurring human task.
- **CRITICAL — payments are human-only.** Any attempt to automate a Relay
  payment violates EOS authority class CRITICAL. Block in code review.

See references/best_practices.md for the full 19-section creator-level knowledge base.
>>>>>>> Stashed changes
