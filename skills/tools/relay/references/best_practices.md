# Relay (Relay Financial) — Creator-Level Best Practices
Source: relayfi.com, support.relayfi.com, NerdWallet 2026 review, Xero blog, Plaid coverage data
API Version: N/A — no public REST API exists as of 2026-04-06
SDK Version: N/A — no first-party SDK in any language
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## Authentication

N/A as a programmatic surface. Relay Financial does not offer API keys, OAuth
client registration, service accounts, or any form of machine credential to
its customers. Authentication exists only in two forms:

1. **Human dashboard login** — email + password + TOTP (Google Authenticator,
   1Password, Authy). New devices require an emailed verification code on
   first sign-in. There is no "remember device" override for wire approvals
   or for adding new payees; both re-prompt for MFA every time.
2. **Aggregator delegation** — Relay is a covered institution on Plaid and
   Yodlee. The customer completes a Plaid Link flow inside a third-party app,
   enters Relay credentials + MFA into Plaid's hosted form, and a `public_token`
   is exchanged for a long-lived `access_token` that the third-party app
   holds. The token authorizes **read-only** access to balances and
   transactions. It does NOT authorize transfers, payments, or any write.

EOS consequence: store one `PLAID_RELAY_ACCESS_TOKEN` per entity in
`eos_ai/.env`, never check it into git, rotate by re-running Plaid Link when
`consent_expiration_time` falls below 14 days. If Plaid ever marks the item
`ITEM_LOGIN_REQUIRED`, all reads stop until Antony re-consents in the link
flow.

There is no concept of "scopes" or "permissions" on the Plaid side beyond
the products requested at link time (`auth`, `transactions`, `identity`,
`balance`). Request the minimum: `transactions` + `balance`.

## Core Operations with Exact Signatures

Relay has no command surface of its own. The operations that matter are
either **dashboard actions performed by a human** or **Plaid endpoints used to
read Relay data**. Both are documented below as the closest thing to a
"signature" this tool has.

### Human dashboard operations

```text
LOGIN
  URL:    https://app.relayfi.com/
  Inputs: email, password, TOTP code
  Result: session cookie, valid until idle timeout (~30 min) or explicit logout

SWITCH ENTITY
  Path:   top-left dropdown → select business
  Inputs: none beyond the click
  Result: dashboard re-renders with that entity's accounts and permissions

CREATE ACCOUNT (a new "bucket")
  Path:   Accounts → + New Account
  Inputs: account name (e.g. "Profit"), account type (checking)
  Result: a new individually-numbered checking account with its own ACH
          routing/account number, owned by the current entity. Counts toward
          the 20-account-per-entity limit.

INTERNAL TRANSFER
  Path:   Move Money → Transfer Between Accounts
  Inputs: from account, to account, amount, optional memo
  Result: instant in-dashboard, no MFA prompt for internal moves
  Limit:  no per-transaction limit beyond the source balance

ACH PAYMENT
  Path:   Move Money → Send Payment → ACH
  Inputs: payee (must exist), amount, memo, send date
  Result: queued for next ACH window. Standard ACH is 1-3 business days.
          Same-day ACH available for an additional fee on Pro plan.
  Limits: per-payment + daily caps depend on plan tier

DOMESTIC WIRE
  Path:   Move Money → Send Payment → Wire
  Inputs: payee bank details, amount, memo
  Result: cutoff is typically 4pm ET; misses → next business day
  MFA:    re-prompt every time, no exceptions

INTERNATIONAL WIRE
  Path:   Move Money → Send Payment → International Wire
  Inputs: SWIFT/BIC, IBAN where applicable, currency, amount
  Result: settles in 1-5 business days depending on corridor
  MFA:    re-prompt every time

BILL PAY
  Path:   Bills → Add Bill (or upload from email forwarding address)
  Inputs: vendor, amount, due date, optional GL category
  Result: enters approval queue if approval rule applies; otherwise scheduled

ISSUE CARD
  Path:   Cards → Issue New Card
  Inputs: cardholder, virtual or physical, spending limit, account to draw on
  Result: virtual card available immediately; physical card mailed in 5-10 days

INVITE USER
  Path:   Settings → Team → Invite
  Inputs: email, role (Owner / Admin / Member / Bookkeeper)
  Result: invite emailed, recipient sets own credentials + MFA

SET APPROVAL RULE
  Path:   Settings → Approvals
  Inputs: threshold ($), approver(s), payment types covered
  Result: payments above threshold require named approver before sending
```

### Plaid endpoints used to read Relay data

```text
POST /link/token/create        → create a one-time link_token for the UI
POST /item/public_token/exchange → swap public_token for access_token
POST /accounts/balance/get     → real-time balance refresh (rate limited)
POST /transactions/sync        → cursor-based incremental transaction sync
POST /identity/get             → account holder names (for entity verification)
POST /item/get                 → check consent_expiration_time, error state
POST /item/remove              → revoke and delete the item
```

`/transactions/sync` is the canonical read path. It returns `added`,
`modified`, `removed`, and `next_cursor`. EOS persists `next_cursor` in
`treasury.plaid_cursors` keyed by `(institution, entity_id)`.

## Pagination Patterns

Plaid's `/transactions/sync` is cursor-based. First call passes no cursor;
subsequent calls pass the `next_cursor` from the previous response. There is
no offset/limit. The cursor encodes the last-seen state on Plaid's side. EOS
must:

- Persist `next_cursor` durably (Neon, not memory)
- Loop until `has_more == false` on every poll
- Treat `removed` array as authoritative deletes (Plaid corrected itself)

`/transactions/get` (the older endpoint) supports `start_date`/`end_date` plus
`offset`/`count` (max 500 per page). Use only for historical backfill on first
link, never for ongoing sync.

The Relay dashboard itself paginates transaction lists at 50 per page with no
deep-link to a specific page. CSV export covers the selected date range in one
file.

## Rate Limits

Relay publishes no rate limits because there is no API to rate-limit. The
indirect surfaces have their own:

- **Plaid Production** — soft limits roughly 600 calls/min per `client_id`
  across all items. `/accounts/balance/get` is metered separately and billed
  per call; do not poll it more than every 4 hours per item or costs balloon.
- **Plaid `/transactions/sync`** — designed for frequent polling. Safe at
  every 1-5 minutes per item. EOS uses every 15 minutes.
- **QBO Bank Feed** — Relay pushes on its own schedule (typically every
  2-6 hours). EOS cannot accelerate this from outside.
- **Dashboard** — no documented rate limits on a logged-in human. Aggressive
  scraping will trigger account-protection MFA.

If a sync skill ever hits Plaid's `RATE_LIMIT_EXCEEDED` error, back off
exponentially starting at 30 seconds, max 5 retries, then alert.

## Error Codes and Recovery

Relay surfaces errors in three places: dashboard toasts (human-readable),
Plaid error envelopes (machine-readable), and bank-feed sync failures inside
QuickBooks/Xero. Plaid is the structured one EOS code touches.

| Error type | Cause | Recovery |
|---|---|---|
| `ITEM_LOGIN_REQUIRED` | Antony changed Relay password, Plaid lost session | Re-run Plaid Link, swap new public_token |
| `ITEM_LOCKED` | Too many failed MFA attempts via Plaid | Log into Relay dashboard, clear lockout, then re-link |
| `INSUFFICIENT_CREDENTIALS` | MFA changed (new TOTP) | Re-link with current TOTP |
| `INSTITUTION_DOWN` | Relay/Thread Bank maintenance | Wait, retry after 30 min |
| `RATE_LIMIT_EXCEEDED` | Too many balance polls | Back off, reduce polling cadence |
| `PRODUCT_NOT_READY` | First sync still warming up | Wait 30-60 sec on first link |
| `PENDING_EXPIRATION` | `consent_expiration_time` < 7 days | Schedule re-consent |
| `ACCESS_NOT_GRANTED` | Antony declined a permission in link flow | Re-link and grant |

Dashboard-side errors that cannot be fixed in code:

- "Insufficient funds" on a transfer → human moves money from another bucket first
- "Wire failed - invalid routing" → human re-enters payee
- "Bill Pay vendor address required" → human edits vendor record

EOS pattern: catch every `PlaidError`, write a row to `treasury.errors` with
`error_code`, `error_message`, `error_type`, `request_id`, then ping Telegram
if the error is one of the four bolded above.

## SDK Idioms

N/A — Relay has no SDK. The closest substitute is the **Plaid Python SDK**
(`plaid-python`), which EOS already uses. Idioms that apply when reading
Relay through Plaid:

- Always pass a `Configuration` with `host=plaid.Environment.Production`
- Use `PlaidApi(api_client)` and call methods like
  `transactions_sync(TransactionsSyncRequest(...))`
- Wrap in try/except for `plaid.ApiException`, parse `e.body` as JSON to get
  `error_code` and `error_type`
- Never hand-roll the JSON; the SDK keeps `client_id`/`secret` injection sane

For QuickBooks Online (the other read path), use the QuickBooks API skill at
`/opt/OS/skills/tools/quickbooks/` once it exists. Until then, treat QBO bank
feed as a downstream consumer only — EOS reads from QBO's transactions table
via the QBO read path, not from Relay directly.

## Anti-Patterns

- **Searching for `api.relayfi.com` and assuming it must exist somewhere.**
  It does not. Do not let an autocomplete in an LLM convince you otherwise.
- **Citing `docs.relay.link`.** That is Relay Protocol, an NFT cross-chain
  bridge. Different company, different product, different industry. The name
  collision is unfortunate.
- **Hardcoding Relay account numbers in code.** They are PII-adjacent and
  belong only in `.env` or Neon-encrypted columns.
- **Polling `/accounts/balance/get` in a tight loop.** Plaid bills per call.
  Use `/transactions/sync` and derive running balance, or accept the 4-hour
  staleness on the dashboard mirror.
- **Automating any Relay payment via headless browser.** This is the most
  tempting anti-pattern. It violates EOS authority class CRITICAL, it
  violates Relay TOS (no scraping), and it puts the entire treasury at risk
  if a selector breaks mid-wire. Do not build it. Do not let any sub-agent
  build it.
- **Treating QBO bank feed lag as a bug.** It is the contract. If you need
  near-real-time, use the Plaid path, not the QBO path.
- **Mixing entities in one Plaid item.** Each Munoz Conglomerate entity gets
  its own Plaid link, its own access token, its own row in
  `treasury.plaid_items`. Never collapse them.
- **Skipping the Notion approval artifact.** Even when the agent is "sure"
  about a transfer, the artifact is the audit trail. No artifact, no transfer.

# Tier 2 — Architectural Understanding

## Data Model

Relay's underlying model, inferred from the dashboard and the bank-feed shape:

```
Business (entity)
  ├── Users (Owner / Admin / Member / Bookkeeper)
  ├── Accounts (up to 20)
  │     ├── account_number (unique, ACH-routable)
  │     ├── routing_number (Thread Bank's)
  │     ├── name (human label, e.g. "Profit")
  │     ├── balance (current + available)
  │     └── Transactions
  │           ├── id, posted_at, amount, direction (debit/credit)
  │           ├── description, counterparty
  │           ├── category (Relay's coarse buckets)
  │           └── status (pending / posted / returned)
  ├── Cards
  │     ├── physical | virtual
  │     ├── cardholder (User)
  │     ├── source_account (Account)
  │     └── spending_limit
  ├── Payees
  │     ├── ACH payees (routing + account)
  │     ├── Wire payees (domestic / international)
  │     └── Check payees (mailing address)
  ├── Bills (Bill Pay)
  │     ├── vendor → Payee
  │     ├── amount, due_date
  │     └── approval_state
  └── Approval Rules
        ├── threshold ($)
        ├── covered payment types
        └── approver users
```

Plaid mirrors only the Business → Accounts → Transactions slice and a thin
identity layer. Cards, Payees, Bills, and Approval Rules are invisible to
Plaid. EOS cannot reason about a vendor's address or an approval rule from
the read path — it only sees money movement after the fact.

When designing `treasury.transactions`, mirror Plaid's shape (id, account_id,
amount, iso_currency_code, date, name, merchant_name, pending, category,
payment_channel) plus EOS-specific columns (entity_id, profit_first_bucket,
classified_at, classifier_version).

## Webhooks and Events

Relay does not emit webhooks to customer-controlled endpoints. There is no
"transaction.created" or "payment.completed" callback you can subscribe to.

Plaid does emit webhooks at the `webhook` URL passed to `/link/token/create`:

| Plaid webhook | Meaning | EOS handler |
|---|---|---|
| `SYNC_UPDATES_AVAILABLE` | New transactions ready | Trigger `/transactions/sync` poll |
| `DEFAULT_UPDATE` | Legacy update available | Same as above for older items |
| `ITEM_ERROR` | `error_code` set on item | Write to `treasury.errors`, alert |
| `PENDING_EXPIRATION` | < 7 days to consent expiry | Notion task: re-consent |
| `USER_PERMISSION_REVOKED` | Antony revoked at Plaid | Mark item dead, alert |
| `WEBHOOK_UPDATE_ACKNOWLEDGED` | URL change confirmed | No-op |

EOS pattern: a single webhook receiver at `/webhooks/plaid` validates the
`Plaid-Verification` header (JWT signed by Plaid), routes by
`webhook_type` + `webhook_code`, and enqueues work into the cognitive loop.
Never trust a webhook payload without verifying the JWT.

There is no Relay-side equivalent. If you need event-driven behavior on a
Relay action, the only mechanism is the Plaid sync webhook firing AFTER the
ledger settles, which is **eventually consistent** with the action.

## Limits

| Limit | Value | Notes |
|---|---|---|
| Accounts per entity | 20 | Hard cap, no upgrade path |
| Entities per login | unlimited | Switch via dropdown |
| Users per entity | varies by plan | Free: limited; Pro: more |
| Approval rules per entity | varies | UI does not document a hard cap |
| ACH per day | plan-dependent | Pro tier higher caps |
| Wire per day | plan-dependent | Pro tier higher caps |
| Cards per entity | 50 (typical) | Both physical and virtual count |
| FDIC insurance | $250K standard, up to $3M sweep | Sweep program is opt-in |
| File upload size (Bills) | ~10 MB | PDF, image |
| Statement history | 7 years | Manual download only |

EOS-relevant: the **20 accounts per entity** is the binding constraint on
Profit First implementation. Six accounts is the canonical Profit First
setup, leaving 14 free for future categories. Plenty of headroom for any one
entity, but it forces Munoz Conglomerate to create separate Relay
businesses for Lyfe Institute, Empyrean Studio, etc. — which is what the
corporate structure already requires anyway.

## Cost Model

Relay's pricing as of 2026-04-06:

- **Relay Standard** — free. Includes 20 accounts, 50 free outgoing ACH per
  month, free incoming ACH and wires, debit cards, QuickBooks/Xero/Gusto sync.
- **Relay Pro** — paid monthly per entity. Adds same-day ACH, higher wire
  limits, accounts payable workflows with approvals, auto-import of bills.

Wire fees: domestic outgoing ~$5, international outgoing varies by corridor,
incoming wires free. Check mailing has a per-check fee.

EOS operating cost from Relay itself is **$0** on Standard tier for the
multi-bucket use case. The cost we pay is on the Plaid side: Plaid Production
charges per transaction sync call and per balance call. Conservative estimate
for one Munoz Conglomerate entity polled every 15 minutes is well under
$5/month.

There is no API call billing because there is no API.

## Version Pinning

Relay does not version its dashboard. The platform updates continuously and
Antony sees whatever the current UI is. There is no "API v1 vs v2" decision
to make.

Version concerns that DO apply:

- **Plaid API version** — pinned via `Plaid-Version` header. EOS uses
  `2020-09-14` (current stable). Newer versions add fields; do not break
  reads.
- **Plaid SDK version** — `plaid-python>=11.0.0`. Pin in `requirements.txt`.
- **QuickBooks Bank Feed protocol** — Intuit-controlled, transparent to Relay
  customers. If QBO sync ever breaks, the fix is in the QBO integration
  panel inside Relay (re-authorize), not in any code EOS owns.
- **Yodlee API version** — only relevant if a downstream app uses Yodlee;
  EOS does not.

# Tier 3 — Strategic Wisdom

## Design Intent and Tradeoffs

Relay's design intent is clear: make Profit First mechanically trivial for a
small business owner. Every product decision flows from that thesis.

- **20 free accounts** because Profit First needs at least five and most
  banks charge per account. Relay removes the cost objection.
- **No public API** because the target customer is a non-technical owner,
  not a fintech developer. Relay's competitive moat is the dashboard UX and
  the bookkeeping integrations, not a developer ecosystem. Building an API
  would dilute focus and create support burden.
- **QuickBooks/Xero/Gusto integrations first-class** because that is where
  the bookkeeper actually lives. Meeting the bookkeeper in their tool is
  worth more to Relay than meeting a developer in Postman.
- **Approval workflows built in** because the moment a business has two
  people touching money, the #1 anxiety is "did someone send a wire I didn't
  approve." Relay puts approvals in the core flow, not as a paid add-on.
- **Thread Bank as charter partner** because building a bank charter is
  multi-year and capital-intensive. Partnering lets Relay ship product
  features, not regulatory infrastructure.

The tradeoff Relay accepts in exchange:

- **No developer ecosystem** — the explicit cost. Power users who want
  programmatic control either use Mercury (which has an API) or build a
  Plaid-mediated read layer like EOS does.
- **Reliance on Thread Bank's processor** for ACH/wire mechanics. When Thread
  has an outage, Relay has an outage.
- **Slower feature velocity on edge cases** — international wire corridors,
  exotic currencies, treasury sweep variations — because the company
  optimizes for the median Profit First user, not the long tail.

For Munoz Conglomerate, this tradeoff is exactly right. The buckets matter;
the API doesn't (because Mercury exists for that). Relay is the right tool
for the multi-entity Profit First job.

## Problem-Solution Map and Hidden Capabilities

| Problem | Relay solution | Hidden detail |
|---|---|---|
| Profit First needs 5+ accounts, banks charge per account | 20 free accounts | Each gets its own ACH routing/account number — usable as direct deposit destinations for split-deposit payroll |
| Bookkeeper needs clean transaction data | Direct QBO/Xero bank feeds | Faster and cleaner than Plaid path; payee names map directly |
| Vendor payments scattered across email | Bill Pay with email forwarding address | Forward invoice PDF to a Relay address; it parses vendor + amount automatically (Pro tier) |
| Multi-entity owner re-authenticates constantly | Single login, entity switcher | Approval rules and users are per-entity; do not forget |
| Need to sweep profit weekly without thinking | Auto-transfer rules | Can be percentage-based on incoming deposits, not just fixed amounts |
| Card spending visibility | Per-card virtual issuance | Issue one virtual card per vendor for clean reconciliation |
| Payroll integration | Gusto direct connection | Gusto pulls from a designated Relay account, posts back transaction reference |
| Reconciliation drift between bank and books | QBO bank feed with categorization rules | Set rules inside Relay, not inside QBO, so they apply at sync time |

Hidden capabilities most users miss:

- **Receiving wires from international clients** is free at Relay (the sender
  pays sender's bank; Relay charges $0 inbound). This makes Relay good for
  collecting EU/UK contractor invoices.
- **Each account's ACH routing/account pair is splittable for direct
  deposit**, so payroll can land in Profit/Owner Pay/Tax/OpEx in one paycheck
  with no manual transfer.
- **Auto-transfer rules** can fire on a percentage of inbound, which is the
  exact mechanic Profit First prescribes ("on the 10th and 25th, move 5% of
  what came in").
- **Bookkeeper role** has read + categorization rights without payment
  authority — give the bookkeeper this role, never Admin.

## Operational Behavior and Edge Cases

- **Pending vs posted transactions** show separately in the dashboard but
  Plaid emits both with `pending: true|false`. A pending transaction can
  change `amount` (e.g. tip on a card swipe) before posting. EOS must
  treat the same `transaction_id` across pending → posted as the same row
  (Plaid guarantees ID stability across the transition; do not insert twice).
- **ACH returns** appear as new transactions with negative amount referencing
  the original. They can land 2-5 business days after the original. Never
  consider an ACH "settled" until at least 5 business days have passed.
- **Wire reversals** are extremely rare and require a recall request through
  Thread Bank's operations team. Plan for them as "essentially impossible to
  unwind" once sent.
- **Card pre-auths** (gas station holds, hotels) appear as a pending charge
  for the hold amount, then post for the actual amount. The hold can persist
  for days after the actual charge posted. Reconcile against `posted` only.
- **Daylight Saving transitions** affect ACH cutoff times because Relay's
  cutoffs are quoted in ET. Document accordingly in any scheduling logic.
- **MFA via SMS is not offered** — TOTP only. If Antony loses his phone,
  recovery requires identity verification with Relay support, which can take
  48-72 hours. Backup TOTP seeds in 1Password.
- **Account closure** is irreversible and requires balance to be zero.
  Always sweep to another bucket first.
- **Sub-user lockouts** after 5 failed MFA attempts require Owner-level
  unlock from inside the dashboard.
- **The mobile app and web dashboard share state**, but the mobile app caches
  aggressively. After a transfer on web, mobile may show stale balances for
  a few minutes.

## Ecosystem Position and Composition

Relay sits in a specific niche:

- **vs Mercury** — Mercury wins on developer experience (real REST API,
  webhooks, treasury management features for venture-backed startups).
  Relay wins on bucket-based cash management, multi-entity dashboard, and
  bookkeeping integrations. The two are complementary, not competitive, for
  an operator who needs both.
- **vs Bluevine** — Bluevine bundles a higher APY but caps free accounts at
  5. Relay wins on multi-bucket and on integrations.
- **vs Novo / Lili** — those target solopreneurs and freelancers. Relay
  targets multi-employee small businesses with bookkeepers.
- **vs Brex / Ramp** — those are expense management platforms with banking
  bolted on. Relay is banking with light expense management bolted on.
  Different center of gravity.
- **vs traditional regional banks** — Relay's UX is a generation ahead, but
  it lacks branches, cash deposit, and merchant services. Operators who
  need cash deposit keep a regional bank as a third leg.

Composition with EOS:

- **Plaid** is the read substrate
- **QuickBooks Online** is the secondary read substrate and the system of
  record for accounting
- **Notion** is the action substrate (transfer requests, approval queue)
- **Telegram** is the alert substrate (drift, errors, expirations)
- **Mercury skill** (when built) is the API-first sibling
- **Thread Bank** is invisible but is the regulatory backstop

## Trajectory and Evolution

Relay's public roadmap signals (as of April 2026):

- Continued investment in **Open Banking integrations** — possibly hinting
  at a future Relay-hosted API for partner accounting tools, but no public
  developer portal has been announced.
- **Advanced fraud detection** rolling out throughout 2026.
- **Dashboard personalization** mid-2026, hinting at saved views and custom
  reports.
- Continued bookkeeper-tooling investment (bookkeeper-specific UX, batch
  categorization, year-end packets).

What is unlikely to happen:

- A general-purpose customer-facing REST API. Relay has consistently pointed
  customers who want one toward Mercury or Plaid-mediated reads. The
  business model does not reward building a developer ecosystem.
- Native crypto support, custody, or DeFi integrations. Relay's regulatory
  posture (Thread Bank charter) makes this path expensive.
- International accounts (non-USD denominated). Relay is US-only and US
  business entity-only.

EOS strategic posture: build the human-operator skill now (this skill),
keep the read path on Plaid + QBO, and **revisit annually** by re-checking
relayfi.com for an API announcement. If Relay ever ships an API, this skill
gets a major version bump and the Plaid path becomes the fallback.

## Conceptual Model and Solution Recipes

The right mental model is **"Relay is a specialized spreadsheet a human
maintains, and EOS reads it through a window."** Every recipe below assumes
Antony is the only actuator.

### Recipe: Weekly Profit First sweep

1. EOS reads inbound deposits to Operating bucket from Plaid sync
2. Calculates 5% (or whatever the configured percentage is)
3. Drafts a transfer request artifact in Notion
4. Telegram pings Antony every Friday morning
5. Antony logs in, executes the internal transfer
6. Next Plaid sync confirms the transfer landed
7. EOS reconciles: artifact closed, transaction tagged with `request_id`

### Recipe: Vendor bill pay with approval

1. Vendor sends invoice PDF
2. Antony forwards to Relay's bill pay email address (Pro tier feature)
3. Relay parses, creates a Bill record awaiting approval
4. Relay approval rule fires (e.g. "above $500 needs second approver")
5. Antony approves in dashboard
6. Bill Pay schedules ACH for next window
7. EOS sees the outbound ACH on next Plaid sync, classifies as vendor expense

### Recipe: Multi-entity treasury snapshot

1. Nightly cron triggers `treasury_aggregator.snapshot_all()`
2. For each entity in BIS: pull Plaid balances for the linked Relay item
3. Pull Mercury balances via Mercury API
4. Write a single row to `treasury.snapshots` with entity, institution,
   account, balance, timestamp
5. Morning brief reads the latest snapshot row and publishes to Notion

### Recipe: Detecting an unexpected outflow

1. Plaid webhook fires `SYNC_UPDATES_AVAILABLE`
2. EOS pulls deltas via `/transactions/sync`
3. For each new outbound transaction above $X (configurable per entity), tag
   as "needs human review"
4. Telegram pings with amount, payee, account
5. Antony confirms (legitimate) or escalates (fraud → call Relay support)

### Recipe: Re-consent before Plaid expiry

1. Daily job calls `/item/get` for every Relay item
2. If `consent_expiration_time` is within 14 days, create a Notion task
3. Task contains the exact link Antony clicks to start the link flow
4. After re-link, delete the task and overwrite the access_token in `.env`

## Industry Expert and Cutting-Edge Usage

How a treasury-savvy operator squeezes maximum value out of Relay:

- **Six-bucket Profit First with auto-transfer rules**: Income, OpEx,
  Owner Pay, Profit, Tax, Vault. All sweeps automated as percentage rules.
  Human only intervenes on quarterly distribution from Vault.
- **One virtual card per SaaS subscription**, named after the vendor. When
  it's time to cancel, freeze the card and the next charge bounces — no
  more "I forgot to cancel before renewal."
- **Direct-deposit split** for owner pay landing into Owner Pay bucket
  directly, bypassing Operating entirely.
- **Per-entity bookkeeper users** with bookkeeper role only — no payment
  authority — for clean separation of duties.
- **Vault account isolated from Bill Pay vendor list** so a misconfigured
  payment cannot accidentally drain it.
- **Inbound international wire optimization** — share the Relay
  routing/account/SWIFT details with international clients who would
  otherwise pay PayPal/Wise fees. Free inbound makes Relay competitive with
  Wise for receiving.
- **Year-end statement bundle** downloaded in January for the prior year and
  archived to GDrive in YYYY-MM-DD format per universal rules.
- **Approval rule rotation** — quarterly, change the approver email used for
  email-based approval notifications, and verify the alert path still works.
  Treat as a fire drill.

For Munoz Conglomerate specifically, the cutting-edge play is **using Relay
buckets as the runway forecasting source of truth**: each entity's "OpEx"
bucket is sized to N months of expenses, and the dashboard shows runway
visually as the bucket drains. EOS reads bucket balance + burn rate from
Plaid and publishes runway in days to the morning brief.

## EOS Usage Patterns

Concrete patterns this skill enables inside EOS:

1. **`/treasury` command** in the Telegram bot: returns balance per entity
   per bucket as of the latest Plaid sync
2. **Morning brief treasury section**: top of brief shows yesterday's net
   movement across all Relay entities, plus runway days
3. **Profit First Friday** scheduled job: drafts the weekly sweep transfer
   request artifact every Friday at 7am ET
4. **Outflow alerts** for any transaction above $500 from a Relay account,
   pinged to Telegram within 15 minutes
5. **Plaid health monitor**: daily check of `consent_expiration_time` and
   `error.error_code` for every Relay item; alert at 14 days remaining
6. **QBO drift detector**: nightly diff of Relay's QBO bank feed against the
   Plaid mirror; alert on any account where the two diverge by more than
   $0.01 for more than 24 hours
7. **Year-end statement scraper**: scheduled human task each January to pull
   PDFs and archive them with `YYYY-MM-DD` filenames per universal rules
8. **Authority-class enforcement**: `eos_ai/authority_engine.py` should
   refuse any plan step that contains the substring `relayfi.com` in a
   write context. Hard guardrail.

## Gotchas

- **There is no API.** This is not a temporary state. It is the product
  decision. Stop looking.
- **`docs.relay.link` is not Relay Financial.** Different company.
- **`api.relayfi.com` is not a public surface.** Even if a tool autocompletes
  it, do not use it.
- **Plaid item expires every 90 days** silently. Monitor it.
- **Pending balance != available balance != ledger balance.** Three
  different numbers in three different places. Use `available` for "can I
  spend right now" and `current` for "what's actually in the account."
- **ACH returns can land days later** as a negative-amount transaction. Do
  not consider an ACH final until 5 business days have passed.
- **Wires are practically irreversible.** Treat every wire as a one-way door.
- **Bookkeeper role still sees all transactions** — do not put truly secret
  data in transaction memos.
- **Email-based approval notifications can be spoofed** in theory; always
  verify any approval request by logging into the dashboard, never by
  clicking a link in an email.
- **20-account cap is per entity, not per login.** Plan corporate structure
  accordingly.
- **QBO bank feed lag is real and is the contract.** Do not reconcile
  against "now."
- **Same-day ACH costs extra and is Pro-only.** Do not assume a payment will
  arrive same day unless explicitly configured.
- **The mobile app caches stale balances** after dashboard actions for a
  few minutes.
- **TOTP only — no SMS fallback.** Backup the seed in 1Password.
- **Cash deposits are not supported.** Relay is not a branch bank.
- **No merchant services** — Relay does not process card payments for
  customers; pair with Stripe.
- **CRITICAL: never automate a payment.** Human-only. Always.

---

# Appendix A — Plaid Integration Deep Dive (Read Path)

The Plaid path is the only programmatic way EOS touches Relay. Treat this
appendix as the operating manual for that bridge.

## Link flow walk-through

1. EOS server calls `link/token/create` with `client_user_id` (entity slug),
   `country_codes=['US']`, `language='en'`, `products=['transactions']`,
   `webhook='https://eos.munoz.co/webhooks/plaid'`. It receives a `link_token`.
2. The link_token is rendered into a Plaid Link UI (web or mobile). Antony
   selects Relay Financial from the institution picker, enters his Relay
   email + password, completes TOTP MFA inside Plaid's hosted form.
3. Plaid returns a `public_token` to the front-end. The front-end POSTs it
   to EOS at `/plaid/exchange`.
4. EOS calls `item/public_token/exchange` and receives `access_token` +
   `item_id`. Both are persisted in `treasury.plaid_items` keyed by entity.
5. EOS immediately calls `accounts/get` to enumerate the bucket accounts and
   write them to `treasury.accounts`.
6. EOS issues an initial `transactions/sync` with no cursor to backfill.
   This may return `PRODUCT_NOT_READY` for up to 60 seconds; retry with
   exponential backoff.

## Sync loop pseudocode

```python
def sync_relay_entity(entity_id: str) -> SyncResult:
    item = fetch_plaid_item(entity_id, institution='relay')
    cursor = item.next_cursor
    added, modified, removed = [], [], []
    has_more = True
    while has_more:
        resp = plaid.transactions_sync(TransactionsSyncRequest(
            access_token=item.access_token,
            cursor=cursor,
            count=500,
        ))
        added.extend(resp.added)
        modified.extend(resp.modified)
        removed.extend(resp.removed)
        cursor = resp.next_cursor
        has_more = resp.has_more
    persist_transactions(added, modified, removed, entity_id)
    update_cursor(entity_id, cursor)
    return SyncResult(len(added), len(modified), len(removed))
```

## Webhook signature verification

Plaid signs webhooks with a JWT in the `Plaid-Verification` header. The
verification key rotates; fetch it via `webhook_verification_key/get` and
cache for the `key_id` claimed in the JWT header. Reject any webhook whose
signature does not verify or whose body hash does not match the JWT's
`request_body_sha256` claim.

## Cost minimization

- Use `transactions/sync` exclusively for ongoing reads. It is the lowest
  per-call cost.
- Avoid `accounts/balance/get` except for explicit "is there enough to send"
  checks. Use the cached `current` balance from the last sync otherwise.
- Disable `identity` product unless EOS needs it. Identity refresh costs
  per call.
- Run sync on the webhook trigger, not on a fixed timer. The webhook fires
  when there is actually new data; polling on a timer wastes calls.

---

# Appendix B — QuickBooks Online Bank Feed (Secondary Read Path)

When the Plaid path is broken or rate-limited, EOS falls back to reading
Relay data from QuickBooks Online, which Relay populates via its first-party
bank feed integration. This appendix covers the contract.

## Setup

Inside Relay dashboard: Integrations → QuickBooks Online → Connect. Antony
authorizes Relay to push transactions into a specific QBO company. Relay
maps each Relay account to a QBO bank account. Mapping is editable.

## Sync cadence

Relay pushes transactions to QBO on its own schedule. Observed cadence:

- Card swipes appear in QBO within 1-2 hours
- ACH posts within 6-12 hours of settlement
- Wires within 1-4 hours of settlement
- Internal transfers within 1-2 hours

EOS treats QBO as eventually consistent with a 24-hour worst-case lag.

## Drift detection

The drift detector compares per-account daily totals between Plaid mirror
and QBO mirror. Acceptable drift is $0.00. Any non-zero drift after 24 hours
is an alert because it usually means one of:

1. Plaid lost a transaction (rare, requires re-link)
2. QBO bank feed dropped a transaction (more common, requires "Update Now"
   in QBO bank feed UI)
3. A duplicate was created in QBO by a categorization rule firing twice

Resolution is always a human action — neither EOS nor Relay can fix QBO
drift programmatically.

## Categorization rules

Set categorization rules **inside Relay's QBO integration panel**, not inside
QBO's bank feed UI. Rules set in Relay apply at push time, so transactions
arrive in QBO already categorized. Rules set in QBO apply at acceptance
time, which is human-gated. Earlier is better.

---

# Appendix C — Multi-Entity Treasury Topology for Munoz Conglomerate

The recommended topology, mapped to the corporate structure document at
`/opt/OS/docs/corporate-structure.md`:

```
Munoz Conglomerate (holding)
  ├── Relay Business: Munoz Conglomerate Holdings
  │     ├── Account: Holding Operating
  │     ├── Account: Inter-entity Sweep
  │     ├── Account: Tax Reserve (consolidated)
  │     └── Account: Vault (long-term reserve)
  │
  ├── Relay Business: Lyfe Institute
  │     ├── Account: Income (deposit landing)
  │     ├── Account: Operating Expenses
  │     ├── Account: Owner Pay
  │     ├── Account: Profit
  │     ├── Account: Tax
  │     └── Account: Initiate Arena Reserve
  │
  ├── Relay Business: Empyrean Studio
  │     ├── Account: Income
  │     ├── Account: Operating Expenses
  │     ├── Account: Owner Pay
  │     ├── Account: Profit
  │     └── Account: Tax
  │
  ├── Relay Business: Lyfe Spectrum
  │     └── (similar 5-bucket layout)
  │
  └── Relay Business: LyfeOS / CreatorOS
        └── (similar 5-bucket layout)
```

Each Relay Business has its own Plaid item, its own access_token, its own
row in `treasury.plaid_items`. The holding entity is the only one allowed
to receive inter-entity sweeps.

## Inter-entity transfer protocol

1. Origin entity sends ACH from its Operating account to the destination
   entity's Income account, using the destination's external ACH
   routing/account number (each Relay account has one).
2. Antony executes the ACH manually inside the origin entity's dashboard.
3. EOS sees the outbound on origin entity's Plaid sync, classifies as
   "inter-entity transfer (outbound)."
4. EOS sees the inbound on destination entity's Plaid sync 1-3 business days
   later, classifies as "inter-entity transfer (inbound)."
5. Reconciliation pairs the two halves by amount + window.

Never use a wire for inter-entity sweeps unless time-critical — ACH is free,
wires cost $5 each, and the amounts are usually small.

---

# Appendix D — Disaster Recovery and Continuity

If Relay goes down, this is the playbook.

## Scenario: Plaid item broken

- Symptom: Plaid sync returns `ITEM_LOGIN_REQUIRED` or `ITEM_LOCKED`
- Impact: EOS read path stale, no new transactions land in Neon
- Recovery: Antony re-runs Plaid Link, EOS overwrites `access_token`,
  resume sync. Backfill any missed transactions via initial sync (no cursor).

## Scenario: Relay dashboard down

- Symptom: app.relayfi.com returns 5xx or hangs
- Impact: Antony cannot move money or approve bills
- Recovery: Use Mercury for any urgent payments. Check status.relayfi.com.
  Plaid read path may continue working if Plaid's connection to Relay is
  separate. Wait for Relay to recover; do not panic.

## Scenario: Thread Bank outage

- Symptom: ACH and wires not settling, dashboard shows pending forever
- Impact: All money movement frozen at Relay
- Recovery: No customer action possible. Use Mercury. Wait. Federal Reserve
  outages affect all banks; Thread-specific outages affect only Relay.

## Scenario: Relay account compromised

- Symptom: unrecognized transactions, login from unknown device
- Impact: CRITICAL — funds at risk
- Recovery: Immediately call Relay support (number in 1Password), freeze
  all cards from dashboard, change password, rotate TOTP, review last 30
  days of transactions, file fraud report. Notify Plaid to disable item.
  Notify QBO to disconnect bank feed. EOS read paths must NOT be re-enabled
  until Relay confirms account is secure.

## Scenario: Antony's TOTP device lost

- Symptom: cannot log in to Relay
- Impact: HIGH — read path keeps working briefly via Plaid, write path
  unavailable
- Recovery: Restore TOTP from 1Password backup seed. If 1Password also
  lost, contact Relay support with identity verification (48-72 hours).
  Mercury is the bypass.

## Backups

- TOTP seeds in 1Password vault `Treasury`
- Plaid access_tokens in `eos_ai/.env`, replicated to encrypted Neon row,
  rotated on every re-link
- Monthly statement PDFs in GDrive, filenames `YYYY-MM-DD-relay-<entity>-
  statement.pdf`
- Year-end packets in GDrive under `taxes/YYYY/`
- Corporate structure source of truth in `/opt/OS/docs/corporate-structure.md`

---

# Appendix E — Compliance and Audit

Relay is a US fintech with FDIC insurance via Thread Bank. Compliance
considerations EOS must respect:

- **KYC** — Relay verified each Munoz Conglomerate entity at signup. Any
  change to entity ownership requires re-verification.
- **Beneficial ownership** — Antony is listed as beneficial owner on all
  entities. Any addition of co-owners requires Relay support.
- **Transaction reporting** — Relay handles BSA/AML reporting; EOS does not
  need to. But avoid patterns that look like structuring (e.g. multiple
  transfers just under $10K to evade reporting). Such patterns are flagged
  automatically and can trigger account review.
- **1099-INT** — issued by Thread Bank if interest exceeds $10/year.
- **Audit trail** — every EOS action that touches Relay (read or
  request-draft) writes a row to `treasury.audit_log` with `entity_id`,
  `action`, `actor` (always 'agent' for read, 'human' for execution),
  `timestamp`, `request_id`, `outcome`.
- **Data retention** — Neon `treasury.transactions` is the canonical EOS
  copy and is retained indefinitely. Plaid retains 24 months by default.
  QBO retains as long as the QBO subscription is active.
- **Right to delete** — if Antony ever closes Relay, the access_token must
  be revoked via `/item/remove`, the QBO bank feed must be disconnected,
  and `treasury.plaid_items` row marked deleted (not hard-deleted, for
  audit trail).

