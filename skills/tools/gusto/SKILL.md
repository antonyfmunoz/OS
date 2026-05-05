---
name: gusto
description: "Use when integrating with Gusto Embedded Payroll API or Partner API for company onboarding, employee/contractor management, pay schedules, running payrolls, fetching payroll history for finance dashboards, handling Gusto webhooks, OAuth 2.0 token management, or sandbox demo company workflows."
allowed-tools: "Read, Bash, Write, Edit, WebFetch"
version: 1.0
source_url: "https://docs.gusto.com/embedded-payroll/"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "Gusto Embedded API v1 (2024-04-01 versioned header)"
sdk_version: "@gusto/embedded-api 0.x (TS), gusto-embedded (Python)"
speed_category: stable
trigger: both
effort: low
context: fork
---

# Tool: gusto

## What This Tool Does

Gusto exposes two distinct API surfaces:

1. **Gusto Embedded Payroll API** — a white-label payroll engine that lets
   platforms run real W-2 and 1099 payroll on behalf of their own customers.
   You own the UI, Gusto owns tax filings, direct deposit rails, and
   compliance posture across all 50 US states.
2. **Gusto Partner API** — a thinner integration surface for accountants and
   bookkeeping platforms that read from existing Gusto company accounts the
   end customer set up themselves at gusto.com.

For Munoz Conglomerate the relevant surface is **Embedded** because it allows
programmatic company creation, employee onboarding, contractor payments, and
payroll execution from inside EOS.

Core capabilities:

- **Company lifecycle** — create company, accept ToS on behalf of signatory,
  collect federal/state tax info, bank account, sign payroll forms
- **Employee + contractor management** — onboard, collect W-4/I-9/W-9, manage
  compensation, jobs, garnishments, terminations
- **Pay schedules** — weekly, biweekly, semimonthly, monthly with frequency
  rules per state
- **Payroll runs** — gather, calculate, submit, cancel, fetch historical
- **Contractor payments** — off-cycle 1099 payments without a pay schedule
- **Tax filings** — Gusto files 941/940/W-2/1099/state withholding automatically
- **Webhooks** — async notifications for payroll status, employee changes,
  company state transitions, bank verification
- **Sandbox / demo company** — fully simulated end-to-end environment with
  fake bank, fake tax filings, instant onboarding

## EOS Integration

Gusto is the payroll substrate for any W-2 employee or 1099 contractor that
Munoz Conglomerate entities pay. EOS uses Gusto in two distinct lanes:

- **Read lane (autonomous)** — agents pull payroll history, employee rosters,
  contractor totals, upcoming pay dates into the finance dashboard and the
  weekly cashflow forecast. Read endpoints have ZERO blast radius and run
  unattended on the nightly consolidation cron.
- **Write lane (human-only)** — drafting a contractor payment, modifying a
  pay schedule, submitting a payroll, or onboarding an employee. These are
  CRITICAL risk under the EOS authority engine. Agents prepare a draft payload
  and surface it via Telegram approval; only the human founder hits submit.

Canonical EOS pattern:

- All Gusto calls go through `eos_ai/integrations/gusto_client.py` (single
  client, single token cache, single retry policy)
- Token refresh handled by `eos_ai/integrations/gusto_oauth.py` with atomic
  refresh-token persistence to Neon
- Read endpoints called from `services/finance_sync.py` on cron
- Write endpoints called only via `eos_ai/authority_engine.py` with
  `risk_class=CRITICAL` and `requires_human_approval=True`
- Sandbox base URL pinned in `.env` as `GUSTO_API_BASE` and switched to
  production only after the human founder explicitly flips
  `GUSTO_ENVIRONMENT=production`

## Authentication

Gusto Embedded uses **OAuth 2.0 authorization code flow** with refresh tokens.
There is no static API key — every access token is short-lived (~2 hours) and
must be refreshed using a long-lived refresh token (~60 days, rotates on use).

```
Authorization: Bearer {access_token}
X-Gusto-API-Version: 2024-04-01
Content-Type: application/json
```

Token endpoints:
- Authorize: `https://api.gusto.com/oauth/authorize`
- Token: `https://api.gusto.com/oauth/token`
- Sandbox host: `https://api.gusto-demo.com` (different host, same OAuth shape)

Refresh tokens **rotate on every use** — the old refresh token is invalidated
the moment you exchange it for a new pair. Persist the new refresh token
atomically before returning from your refresh function or you will lose access
permanently and have to redo the auth handshake from scratch.

## Quick Reference

### Refresh an access token

```bash
curl -X POST https://api.gusto-demo.com/oauth/token \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "'"$GUSTO_CLIENT_ID"'",
    "client_secret": "'"$GUSTO_CLIENT_SECRET"'",
    "grant_type": "refresh_token",
    "refresh_token": "'"$GUSTO_REFRESH_TOKEN"'"
  }'
```

### List companies the token has access to

```bash
curl https://api.gusto-demo.com/v1/me \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Gusto-API-Version: 2024-04-01"
```

### Get a company

```bash
curl https://api.gusto-demo.com/v1/companies/$COMPANY_UUID \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Gusto-API-Version: 2024-04-01"
```

### List employees with embedded jobs and compensations

```bash
curl "https://api.gusto-demo.com/v1/companies/$COMPANY_UUID/employees?include=jobs,compensations,home_address" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Gusto-API-Version: 2024-04-01"
```

### List pay schedules

```bash
curl https://api.gusto-demo.com/v1/companies/$COMPANY_UUID/pay_schedules \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Gusto-API-Version: 2024-04-01"
```

### List historical payrolls

```bash
curl "https://api.gusto-demo.com/v1/companies/$COMPANY_UUID/payrolls?processing_statuses=processed&start_date=2026-01-01&end_date=2026-04-06" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Gusto-API-Version: 2024-04-01"
```

### Draft a contractor payment (NEVER auto-submitted by an agent)

```bash
curl -X POST https://api.gusto-demo.com/v1/companies/$COMPANY_UUID/contractor_payments \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Gusto-API-Version: 2024-04-01" \
  -H "Content-Type: application/json" \
  -d '{
    "contractor_uuid": "'"$CONTRACTOR_UUID"'",
    "date": "2026-04-15",
    "wage": 2500.00,
    "hours": 0,
    "bonus": 0
  }'
```

### Webhook signature verification

Gusto signs webhook payloads with HMAC-SHA256 over the raw request body using
the per-subscription secret. Verify before trusting any payload:

```python
import hmac, hashlib

def verify_gusto_webhook(raw_body: bytes, sig_header: str, secret: str) -> bool:
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig_header)
```

## Conceptual Model

**Two trees, one root.** Every Gusto Embedded integration has a tree shaped
like: `application → companies → (employees, contractors, pay_schedules,
payrolls) → (jobs, compensations, contractor_payments)`. The application is
your OAuth client. Each company is an independent legal payroll entity with
its own EIN, bank, and tax registrations.

**Async by default.** Almost every "write" in Gusto is async. Submitting a
payroll returns immediately with `payroll_status_meta.expected_check_date` —
the actual debit, calculation finalization, and tax deposit happen later.
Webhooks are how you find out the real outcome. Polling works but is wasteful.

**Versioned by header.** Gusto pins schema to a single date header
(`X-Gusto-API-Version`). Bumping the header is a deliberate action, not a
side effect of upgrading the SDK. Pin the date in your client and never
read "latest."

**Sandbox is real.** The demo environment runs the same code paths as
production with simulated bank and tax filings. A bug that doesn't appear in
sandbox almost certainly won't appear in production.

## Gotchas

- **Refresh token rotation** — old refresh token dies the instant you call
  `/oauth/token`. Persist the new pair atomically (transaction or write-then-fsync)
  before returning. Lose this and you redo the entire handshake.
- **Token expiry is ~2 hours, not 24** — clients that cache "until tomorrow"
  silently break mid-day. Cache with `expires_in - 60s` safety margin.
- **`X-Gusto-API-Version` header is required** — omitting it gives you an
  unspecified default that can shift. Always pin.
- **Sandbox host is `api.gusto-demo.com`, not `sandbox.gusto.com`** — the
  latter does not exist and produces DNS errors that look like network failures.
- **Company onboarding has a strict step order** — federal tax info → state
  tax info → bank account → signatory → forms. Skipping a step returns 422
  with no clear hint about which step you're missing.
- **Pay schedules cannot be deleted once a payroll has run on them** — only
  marked inactive. Test schedules pollute sandbox forever.
- **Contractor payments are NOT payrolls** — different endpoint, different
  approval flow, different webhook events. Don't try to push contractors
  through `/payrolls`.
- **Submitting a payroll is irrevocable after the calculation deadline**
  (typically 4pm PT 2 banking days before check date). After that, cancellation
  requires Gusto support intervention. **EOS rule: agents never submit.**
- **Sandbox payrolls auto-process** on a fake schedule — don't assume sandbox
  payrolls stay in `unprocessed` forever for your tests.
- **Webhook events are at-least-once** — dedupe on `event_uuid`.
- **Rate limits are quiet** — Gusto returns 429 with `Retry-After` but does
  not document an exact RPS in their public docs. Stay under ~10 req/s per
  token and back off on 429.
- **`include` parameter is allowlisted per endpoint** — `include=jobs` works
  on `/employees` but not `/contractors`. Read the per-endpoint docs.
- **Decimal vs cents inconsistency** — newer endpoints use decimal dollars,
  some legacy fields use cents. Always check the schema for the field type.

See references/best_practices.md for the full 19-section creator-level
knowledge base including data model, error matrix, webhooks, anti-patterns,
EOS usage patterns, and operational gotchas.
