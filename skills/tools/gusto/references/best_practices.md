# Gusto — Creator-Level Best Practices
Source: https://docs.gusto.com/embedded-payroll/
API Version: 2024-04-01 (versioned via X-Gusto-API-Version header)
SDK Version: @gusto/embedded-api 0.x (TypeScript), gusto-embedded (Python)
Last Researched: 2026-04-06

This document is the authoritative reference for the Gusto Embedded Payroll
API as used inside EOS. It is structured as 19 mastery sections plus EOS
Usage Patterns and a compounding Gotchas log. Content covers the **Embedded
Payroll API** primarily, with Partner API differences called out where
relevant.

---

# Tier 1 — Technical Mastery

## Authentication

Gusto Embedded uses OAuth 2.0 authorization-code grant with rotating refresh
tokens. There is no static API key, no service account, no machine-to-machine
client credentials grant for the Embedded surface. Every integration must
walk a human (or simulated human in sandbox) through the consent screen at
least once to mint the first refresh token.

### Endpoints

- Authorize: `https://api.gusto.com/oauth/authorize`
- Token:     `https://api.gusto.com/oauth/token`
- Sandbox:   `https://api.gusto-demo.com` (same paths, different host)

### Authorization request

```
GET https://api.gusto-demo.com/oauth/authorize
  ?client_id={CLIENT_ID}
  &redirect_uri={REDIRECT_URI}
  &response_type=code
  &scope=public
  &state={CSRF_TOKEN}
```

The user authenticates, accepts the requested scope, and is redirected to
your `redirect_uri` with `?code=...&state=...`. The code is single-use and
expires in ~10 minutes.

### Token exchange (initial)

```
POST https://api.gusto-demo.com/oauth/token
Content-Type: application/json

{
  "client_id":     "{CLIENT_ID}",
  "client_secret": "{CLIENT_SECRET}",
  "code":          "{AUTH_CODE}",
  "grant_type":    "authorization_code",
  "redirect_uri":  "{REDIRECT_URI}"
}
```

Response:

```json
{
  "access_token":  "...",
  "refresh_token": "...",
  "expires_in":    7200,
  "token_type":    "bearer",
  "scope":         "public",
  "created_at":    1733600000
}
```

### Token refresh

```
POST https://api.gusto-demo.com/oauth/token
Content-Type: application/json

{
  "client_id":     "{CLIENT_ID}",
  "client_secret": "{CLIENT_SECRET}",
  "refresh_token": "{REFRESH_TOKEN}",
  "grant_type":    "refresh_token"
}
```

The response shape is identical and contains a NEW refresh_token. The OLD
refresh_token is invalidated immediately on use. This is the single most
common way to lock yourself out of a Gusto integration — see Gotchas.

### Required headers on every API call

```
Authorization:        Bearer {access_token}
X-Gusto-API-Version:  2024-04-01
Content-Type:         application/json
Accept:               application/json
```

### Scopes

Gusto Embedded today exposes a single broad `public` scope. There is no
fine-grained scoping like "payroll:read" — once a token is granted, it can
read and write everything the company allows. This is why EOS enforces
write protection at the application layer (authority engine), not at the
token layer.

## Core Operations with Exact Signatures

All paths are relative to `https://api.gusto-demo.com` (sandbox) or
`https://api.gusto.com` (production).

### Identity

- `GET /v1/me` — returns the authenticated user and the list of roles/companies
  the token can act on. First call after a refresh; cheapest health check.

### Company

- `POST /v1/partner_managed_companies` — create a new Embedded company
- `GET /v1/companies/{company_uuid}` — fetch company state and onboarding status
- `GET /v1/companies/{company_uuid}/onboarding_status` — granular onboarding
  step tracker (federal_tax_setup, state_setup, add_bank_info, etc.)
- `PUT /v1/companies/{company_uuid}/finish_onboarding` — finalize after all
  steps green
- `GET /v1/companies/{company_uuid}/locations` — work locations
- `POST /v1/companies/{company_uuid}/locations` — add a work location
- `GET /v1/companies/{company_uuid}/bank_accounts` — list company bank accounts
- `POST /v1/companies/{company_uuid}/bank_accounts` — add (triggers verification
  via micro-deposits or instant Plaid)

### Federal & State tax

- `GET  /v1/companies/{company_uuid}/federal_tax_details`
- `PUT  /v1/companies/{company_uuid}/federal_tax_details`
- `GET  /v1/companies/{company_uuid}/company_state_taxes/{state}`
- `PUT  /v1/companies/{company_uuid}/company_state_taxes/{state}`

### Employees

- `GET  /v1/companies/{company_uuid}/employees` — list employees
- `POST /v1/companies/{company_uuid}/employees` — create employee
- `GET  /v1/employees/{employee_uuid}` — fetch employee
- `PUT  /v1/employees/{employee_uuid}` — update employee
- `GET  /v1/employees/{employee_uuid}/jobs` — list jobs (a job is a
  position with title, location, and compensation history)
- `POST /v1/employees/{employee_uuid}/jobs` — create job
- `GET  /v1/jobs/{job_uuid}/compensations` — pay rates
- `POST /v1/jobs/{job_uuid}/compensations` — set pay rate
- `GET  /v1/employees/{employee_uuid}/forms` — W-4, I-9, etc.
- `POST /v1/employees/{employee_uuid}/terminations` — terminate

### Contractors

- `GET  /v1/companies/{company_uuid}/contractors`
- `POST /v1/companies/{company_uuid}/contractors`
- `GET  /v1/contractors/{contractor_uuid}`
- `PUT  /v1/contractors/{contractor_uuid}`
- `GET  /v1/companies/{company_uuid}/contractor_payments`
- `POST /v1/companies/{company_uuid}/contractor_payments`
- `GET  /v1/companies/{company_uuid}/contractor_payments/{payment_uuid}`
- `DELETE /v1/companies/{company_uuid}/contractor_payments/{payment_uuid}`
  (only valid before processing window closes)

### Pay Schedules

- `GET  /v1/companies/{company_uuid}/pay_schedules`
- `POST /v1/companies/{company_uuid}/pay_schedules`
- `GET  /v1/companies/{company_uuid}/pay_schedules/{pay_schedule_uuid}`
- `PUT  /v1/companies/{company_uuid}/pay_schedules/{pay_schedule_uuid}`
- `GET  /v1/companies/{company_uuid}/pay_schedules/{pay_schedule_uuid}/pay_periods`

### Payrolls

- `GET  /v1/companies/{company_uuid}/payrolls` — list (filterable by
  `processing_statuses`, `payroll_types`, `start_date`, `end_date`,
  `include=totals,taxes,benefits,deductions`)
- `GET  /v1/companies/{company_uuid}/payrolls/{payroll_uuid}` — single payroll
- `PUT  /v1/companies/{company_uuid}/payrolls/{payroll_uuid}` — update line
  items (hours, gross pay, etc.) while in `unprocessed`
- `PUT  /v1/companies/{company_uuid}/payrolls/{payroll_uuid}/calculate` —
  preview taxes and net pay without submitting
- `PUT  /v1/companies/{company_uuid}/payrolls/{payroll_uuid}/submit` —
  IRREVOCABLE after deadline. Agents NEVER call this.
- `PUT  /v1/companies/{company_uuid}/payrolls/{payroll_uuid}/cancel`

### Webhooks (Webhook Subscriptions)

- `GET    /v1/webhook_subscriptions`
- `POST   /v1/webhook_subscriptions`
- `GET    /v1/webhook_subscriptions/{subscription_uuid}`
- `PUT    /v1/webhook_subscriptions/{subscription_uuid}`
- `DELETE /v1/webhook_subscriptions/{subscription_uuid}`
- `PUT    /v1/webhook_subscriptions/{subscription_uuid}/verify`

## Pagination Patterns

Gusto Embedded uses **page-based pagination** via query parameters:

```
GET /v1/companies/{company_uuid}/payrolls?page=2&per=50
```

- `page` — 1-indexed page number
- `per` — items per page (default 25, max typically 100)

Pagination metadata is returned in HTTP headers, not the body:

```
X-Total-Count:   137
X-Total-Pages:   3
X-Per-Page:      50
X-Page:          2
```

There is no cursor-based pagination on Embedded. For very large
employee/payroll histories, page sequentially and respect rate limits.

The Python SDK exposes iterators that handle this transparently:

```python
for payroll in client.payrolls.list_iter(company_uuid=COMPANY_UUID):
    process(payroll)
```

When you build pagination by hand, always read the `X-Total-Pages` header
rather than looping until you get an empty page — Gusto will happily return
200 with an empty array if you walk past the end.

## Rate Limits

Gusto does not publish a precise per-endpoint RPS in its public docs. The
observed and SDK-recommended behavior:

- 429 Too Many Requests on burst above ~10–20 req/s per token
- `Retry-After` header on 429 with seconds to wait
- Long-term ceiling around several thousand requests per hour per OAuth
  application

Practical rule for EOS: cap concurrency at 4 in-flight requests per token
and add exponential backoff starting at 1s with jitter on any 429 or 503.
Gusto support has confirmed in community channels that they will throttle
abusive integrations rather than hard-block, so a well-behaved client almost
never sees 429s.

The Embedded sandbox has tighter limits than production — burst tests in
sandbox are not representative of production headroom.

## Error Codes and Recovery

Standard HTTP semantics with one Gusto-specific quirk: 422 is the workhorse
error for everything domain-related (validation, missing onboarding step,
illegal state transition).

| Code | Meaning                          | EOS recovery                                                  |
|------|----------------------------------|---------------------------------------------------------------|
| 400  | Malformed request                | Log and surface; never retry blindly                          |
| 401  | Invalid/expired access token     | Refresh token, retry once                                     |
| 402  | Payment required (rare)          | Surface to human                                              |
| 403  | Forbidden (scope/role)           | Surface to human; do not retry                                |
| 404  | Not found                        | Treat as definitive; do not retry                             |
| 409  | Conflict (concurrent edit)       | Refetch, merge, retry once                                    |
| 422  | Unprocessable entity (domain)    | Inspect `errors` array, surface specific field problems       |
| 429  | Rate limited                     | Honor Retry-After, exponential backoff                        |
| 500  | Internal server error            | Retry with backoff up to 3 times                              |
| 502  | Bad gateway                      | Retry with backoff                                            |
| 503  | Service unavailable              | Retry with backoff, longer ceiling                            |
| 504  | Gateway timeout                  | Retry with backoff; payroll submit is NOT idempotent — see below |

### 422 error body shape

```json
{
  "errors": {
    "employee": [
      { "error_key": "first_name", "category": "invalid_attribute_value",
        "message": "First name can't be blank" }
    ]
  }
}
```

Always log `error_key` and `category`. The `message` is human-readable but
not stable across versions; categories are stable enough to branch on.

### 504 on `submit` is the dangerous case

If a payroll submit times out with 504, the submission MAY have been
processed server-side. **Do not retry blindly.** Refetch the payroll, check
`payroll_status_meta.processed`, and only retry if it is still `unprocessed`.
This is one reason EOS routes all payroll submits through human approval.

## SDK Idioms

Gusto ships first-party SDKs generated by Speakeasy:

- TypeScript: `@gusto/embedded-api`
- Python:     `gusto-embedded`

Both follow the same conventions:

- Resource-namespaced clients: `client.companies`, `client.employees`,
  `client.payrolls`, `client.contractor_payments`
- Strongly typed request/response models
- Built-in retry middleware for 5xx with exponential backoff
- Built-in pagination iterators
- Versioned via constructor argument; do not rely on the default

### Python idiom

```python
from gusto_embedded import Gusto

client = Gusto(
    server_url="https://api.gusto-demo.com",
    security={"company_access_token": access_token},
    api_version="2024-04-01",
)

me = client.introspection.get_info()
companies = client.companies.list()
payrolls = client.payrolls.get_payrolls(
    company_uuid=COMPANY_UUID,
    processing_statuses=["processed"],
    start_date="2026-01-01",
    end_date="2026-04-06",
)
```

### TypeScript idiom

```ts
import { Gusto } from "@gusto/embedded-api";

const client = new Gusto({
  serverURL: "https://api.gusto-demo.com",
  security: { companyAccessToken: accessToken },
  apiVersion: "2024-04-01",
});

const payrolls = await client.payrolls.getPayrolls({
  companyUuid: COMPANY_UUID,
  processingStatuses: ["processed"],
});
```

EOS pins the version in the client constructor, never relies on the default.

## Anti-Patterns

- **Treating Gusto like a DB you write to from anywhere.** Funnel all calls
  through one client module. Diffuse access = diffuse risk.
- **Catching 422 generically and retrying.** 422 means "your input is wrong";
  retrying without changing the input will loop forever.
- **Submitting a payroll from automation without human approval.** Payroll
  submission moves real money and triggers real tax filings. Banned in EOS.
- **Polling `/payrolls` every minute to detect status changes.** Use
  webhooks. Polling burns rate limit and produces stale data.
- **Storing the access token only and re-authing when it expires.** You will
  bounce humans out of the consent flow constantly. Store and rotate the
  refresh token.
- **Hardcoding `https://api.gusto.com`.** Always read the host from env so
  sandbox and production are a config flip, not a code change.
- **Concatenating the company_uuid into the URL via f-string without
  validation.** UUID typos cause 404s that look like missing data.
- **Trusting webhook payloads without HMAC verification.** Anyone who guesses
  your endpoint can post fake events.
- **Bumping `X-Gusto-API-Version` casually.** A version bump is a schema
  migration. Test in sandbox first.
- **Using the Partner API expecting Embedded semantics.** Partner is
  read-mostly and authenticated against existing customer accounts. They are
  not interchangeable.

## Data Model

The core hierarchy:

```
Application (your OAuth client)
  └── Company  (legal payroll entity, one EIN)
        ├── Locations           (mailing/work addresses, drives state taxes)
        ├── BankAccounts        (verified via Plaid or micro-deposits)
        ├── FederalTaxDetails   (filing status, deposit schedule)
        ├── CompanyStateTaxes   (per-state registration + rates)
        ├── PaySchedules        (frequency + anchor dates)
        │     └── PayPeriods    (concrete instances of a schedule)
        ├── Employees
        │     ├── HomeAddress
        │     ├── WorkAddresses
        │     ├── Jobs          (title + location + history of compensations)
        │     │     └── Compensations  (rate, payment_unit)
        │     ├── Forms         (W-4, I-9, state withholding)
        │     ├── Garnishments
        │     └── Terminations
        ├── Contractors
        │     ├── ContractorPayments
        │     └── Forms         (W-9)
        └── Payrolls
              ├── EmployeeCompensations  (line items per employee)
              │     ├── HourlyCompensations
              │     ├── FixedCompensations
              │     └── PaidTimeOff
              ├── Taxes                  (employer + employee, per jurisdiction)
              ├── Benefits
              └── Deductions
```

### IDs

Every resource has a UUID v4. Gusto also exposes `id` (integer) on legacy
resources but the API is moving to UUIDs everywhere — always prefer the
`uuid` field. EOS stores Gusto IDs as `gusto_uuid` columns to make grep easy.

### Money

- Newer endpoints (Embedded): decimal dollars in JSON (`"wage": 2500.00`)
- Older fields surfaced from legacy: integer cents
- Always check the schema. Never assume.

### Dates

ISO 8601 dates (`YYYY-MM-DD`) for pay dates, check dates, hire dates.
Timestamps are ISO 8601 with timezone. Pay periods are date ranges, inclusive
on both ends.

## Webhooks and Events

Gusto Webhook Subscriptions deliver real-time events for company, employee,
contractor, payroll, and bank verification state changes. Events are JSON
posted to your endpoint with an HMAC-SHA256 signature.

### Subscription lifecycle

1. `POST /v1/webhook_subscriptions` with `url`, `subscription_types`
2. Gusto immediately POSTs a verification token to your URL
3. You echo it back via `PUT /v1/webhook_subscriptions/{uuid}/verify`
4. Subscription becomes `verified` and starts delivering events

### Common event types

- `Company` — company state change, onboarding step complete
- `Employee` — created, updated, terminated
- `Contractor` — created, updated
- `Payroll` — calculated, submitted, processed, cancelled
- `ContractorPayment` — created, processed, cancelled
- `Form` — signed, expired
- `CompanyBankAccount` — verification status changes

### Payload shape

```json
{
  "event_type": "Payroll",
  "event_uuid": "f0e8d9...",
  "resource_uuid": "abc123...",
  "resource_type": "Payroll",
  "timestamp": "2026-04-06T18:30:00Z",
  "entity_type": "Company",
  "entity_uuid": "company-uuid"
}
```

The payload only contains identifiers, not the full resource. You must
follow up with a GET to fetch the actual state. This is intentional: it
prevents stale or out-of-order state from leaking through webhooks.

### Delivery guarantees

- **At-least-once.** Dedupe on `event_uuid`.
- Retries on non-2xx for ~24 hours with exponential backoff.
- 200 OK within 5 seconds is required; long-running handlers must enqueue
  and ack immediately.

### Signature verification

Header: `X-Gusto-Signature` containing the hex HMAC-SHA256 of the raw body
keyed by the subscription secret. Always verify before trusting any field.

## Limits

- Companies per OAuth application: no published hard cap; thousands in
  practice
- Employees per company: no published cap; thousands in practice
- Pay schedules per company: practical cap ~25; one per group of employees
  (e.g., hourly weekly + salaried biweekly)
- Payroll history retention: indefinite for processed payrolls
- Webhook subscriptions per app: ~100
- Webhook payload retry window: ~24 hours
- Sandbox demo companies per developer account: unlimited
- File uploads (forms): 5 MB per file typically; PDF preferred
- Pagination max `per`: 100 on most list endpoints

## Cost Model

- Sandbox: free
- Production Embedded pricing is per-employee-per-month (PEPM) negotiated
  through Gusto's Embedded sales team. Contract minimums apply.
- There is no per-API-call cost; you are paying for the payroll
  infrastructure, not the bandwidth.
- Tax filing fees are bundled into PEPM for Embedded.

For EOS pre-revenue: stay in sandbox. Move to production only when there is
an actual W-2 or contractor to pay through a Munoz entity.

## Version Pinning

The single source of API version truth is the `X-Gusto-API-Version` HTTP
header. Gusto publishes a new version date whenever there is a breaking
change. Old versions remain supported for a long deprecation window
(typically 12+ months) but new fields and endpoints only appear on newer
versions.

Best practice:

1. Pin the version in one constant: `GUSTO_API_VERSION = "2024-04-01"`
2. Pass it on every request via the SDK constructor or HTTP middleware
3. When Gusto announces a new version, read the changelog, update sandbox
   first, run integration tests, then bump production
4. Never read "latest" — Gusto does not actually expose a "latest" alias
   and omitting the header gives an unspecified default

EOS pins the version in `eos_ai/integrations/gusto_client.py` as a module
constant. Bumping it requires a code change and a deploy.

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

Gusto Embedded was designed around three constraints that shape every API
decision:

1. **Compliance is non-negotiable.** Payroll touches federal tax law, state
   tax law, wage and hour law, garnishment law, and bank ACH rules. Every
   API surface is shaped to make it hard for an integrator to skip a
   compliance step. This is why onboarding is a strict step machine, why
   pay schedules can't be casually deleted, and why submitted payrolls have
   a hard cancellation deadline.
2. **The integrator owns the UI, Gusto owns the engine.** Embedded is not
   an iframe product. You build your own onboarding wizard, your own
   employee table, your own payroll review screen — Gusto provides the
   data model and the execution. This means the API is unusually rich:
   it has to expose every field a competent payroll product would need,
   without leaking internal Gusto state.
3. **Async is the default for anything that touches money.** Submitting
   payroll is irreversible after a deadline. Bank verification is async.
   Tax filings are async. The API uses webhooks + status fields to model
   this honestly rather than pretending writes are synchronous.

The tradeoff: the API has more endpoints, more required fields, and more
state machines than a typical SaaS API. The payoff: when an Embedded
integration runs payroll successfully, the result is legally compliant
W-2s, real direct deposits, and real tax filings. There is no "and now you
file with the IRS yourself" hidden step.

## Problem-Solution Map and Hidden Capabilities

| Problem                                              | Gusto solution                                            |
|------------------------------------------------------|-----------------------------------------------------------|
| Need to pay a 1099 contractor without a pay schedule | `/contractor_payments` (off-cycle, no schedule needed)    |
| Need to preview taxes before submitting payroll      | `/payrolls/{uuid}/calculate` returns full breakdown       |
| Need to model multi-state employees                  | `Employee.work_addresses[]` + per-state withholding forms |
| Need to handle terminations mid-pay-period           | `/employees/{uuid}/terminations` with `effective_date`    |
| Need to issue an off-cycle bonus payroll             | Create payroll with `payroll_type=off_cycle`              |
| Need to refund a deduction                           | Negative line item on next regular payroll                |
| Need to test without burning real money              | `api.gusto-demo.com` with auto-created demo companies     |
| Need to know when payroll actually clears the bank   | Subscribe to `Payroll` webhook events                     |
| Need to onboard an employee they fill out themselves | Self-onboarding flow toggle on Employee creation          |
| Need to handle garnishments correctly                | `/employees/{uuid}/garnishments` with court order details |
| Need to back-fill historical payrolls during migration | `payroll_type=external` for prior-payroll data           |

### Hidden capabilities most integrators miss

- **`include` query parameter** on list endpoints. `include=jobs,compensations`
  on `/employees` collapses what would be N+1 round trips into one call.
- **Demo company auto-onboarding** in sandbox: a single API call can create
  a company that's already past every onboarding step, with employees and
  pay schedules pre-populated. Use this for fast integration tests.
- **Calculate without submit.** `/payrolls/{uuid}/calculate` lets you show
  the user a tax preview without locking in anything. EOS uses this for
  the cashflow forecast.
- **Off-cycle and external payroll types.** `off_cycle` for bonuses,
  `external` for migration backfill, `correction` for fixing historical
  errors. Most integrators only know about `regular`.
- **Webhook verification token endpoint.** You can re-verify a subscription
  after a URL change without recreating it.

## Operational Behavior and Edge Cases

- **Bank verification can take 1–3 business days** via micro-deposits, or
  be instant via Plaid. Until verification completes, payrolls can be
  drafted but not submitted.
- **State registration can take weeks** in some states. Companies stuck in
  `state_setup` for a new state are common; the integration cannot fix
  this from the API — it requires the company to register with the state
  agency.
- **First payroll after onboarding** triggers a tax-filing setup pass that
  is not visible in the API but can delay processing by a day. Plan for it.
- **Year-end (W-2/1099 generation)** runs automatically in late January.
  Forms become available via `/forms` endpoints when ready.
- **Multi-state employees** require state withholding forms for each state
  worked. Missing forms block payroll submission with a 422.
- **Direct deposit cutoff** is typically 4pm PT 2 banking days before check
  date. After cutoff, payrolls can still be submitted but checks will be
  paper or delayed.
- **Bank holidays** shift cutoffs. Gusto's API exposes the calculated
  `expected_check_date` so you don't have to model holidays yourself.
- **Sandbox time is real time.** Demo companies process payrolls on real
  calendar days, not accelerated. Schedule sandbox tests accordingly or
  use the demo company time-travel endpoints.
- **Deleting a contractor with payments in history** is not allowed —
  contractors with payment history can only be marked inactive.
- **Renaming a company** doesn't change its UUID, but does propagate to
  W-2s and 1099s. Rename only between tax years.

## Ecosystem Position and Composition

Gusto Embedded competes in the same space as:

- **Check (checkhq.com)** — a more API-native, developer-first competitor.
  Lighter UI surface, similar PEPM model, narrower state coverage.
- **Finch** — an aggregator over many payroll providers including Gusto
  itself. Different shape: read-mostly, write through "Finch Pay" overlay.
- **Rippling**, **Justworks**, **ADP** — full-stack HR + payroll, not
  primarily Embedded plays.

Gusto's edge is breadth (50-state coverage, full tax filings, deep benefit
admin) and brand trust with US small business. The cost is integration
complexity: there is more API surface to learn than Check, and the model
is more opinionated about workflow.

Composition partners commonly used with Gusto in the wild:

- **Plaid** for instant bank verification (Gusto integrates this internally;
  you don't usually call Plaid yourself for bank-account-add)
- **Stripe Issuing / Modern Treasury** for adjacent money movement that is
  not payroll
- **QuickBooks / Xero** for GL sync — Gusto exposes journal entries via API
- **Slack / Teams / Telegram** for notifications driven off webhooks

In EOS, Gusto sits next to:
- Mercury (operating bank), for cross-validating ACH debits
- QuickBooks-equivalent ledger inside Neon, for cashflow forecasts
- The authority engine, which gates every write

## Trajectory and Evolution

Gusto Embedded has been moving in a clear direction over the past two years:

- **More versioned endpoints, fewer breaking changes.** The
  `X-Gusto-API-Version` header pattern was rolled out specifically to
  support long-lived integrations.
- **First-party Speakeasy SDKs** in TS and Python (and increasingly other
  languages) replacing community wrappers.
- **More embedded UI components** (Gusto's React component library) for
  integrators who don't want to build every screen.
- **Expanded contractor and international payments.** Contractor payments
  are getting feature parity with W-2 payroll; international contractor
  payments are in beta.
- **Better webhooks.** The webhook product was overhauled in 2023–2024 with
  the current verification flow and HMAC signing.

What is not changing: the core data model, the OAuth flow, or the
"integrator owns UI" stance. Gusto is unlikely to ship an iframe product
that competes with their own Embedded customers.

## Conceptual Model and Solution Recipes

### The mental model that makes Gusto easy

Think of Gusto Embedded as **three layers stacked**:

1. **Configuration layer** — companies, employees, contractors, pay
   schedules, tax registrations, bank accounts. Mostly synchronous CRUD.
   Mistakes here are recoverable.
2. **Execution layer** — payrolls and contractor payments. Async, deadline-
   driven, money-moving. Mistakes here are expensive.
3. **Reporting layer** — historical payrolls, forms (W-2/1099), tax filings.
   Read-only after execution. Mistakes here are legal.

The API surface mirrors this. Most of your code lives in layer 1. Layer 2
should be tiny, audited, and human-gated. Layer 3 is where dashboards live
and where automation can run free.

### Recipe — onboard a new W-2 employee to an existing company

1. `POST /v1/companies/{c}/employees` with name, SSN, DOB, email
2. `POST /v1/employees/{e}/jobs` with title, location, hire date
3. `POST /v1/jobs/{j}/compensations` with rate and payment_unit
4. `PUT  /v1/employees/{e}/forms/{w4_form_uuid}` to sign W-4 (or use
   self-onboarding flow and let the employee sign themselves)
5. `PUT  /v1/employees/{e}/onboarding_status` to mark complete
6. Verify by `GET /v1/employees/{e}` and check `onboarded` is true

### Recipe — fetch full payroll history for finance dashboard

1. Page through `/v1/companies/{c}/payrolls?processing_statuses=processed`
2. For each, GET with `include=totals,taxes,benefits,deductions`
3. Persist into Neon under (company_uuid, payroll_uuid) primary key
4. Subscribe to `Payroll` webhook to keep current going forward

### Recipe — draft a contractor payment for human approval

1. Look up contractor by name → uuid
2. Build payload: contractor_uuid, date, wage, hours, bonus
3. **Do not POST.** Render the payload into a Telegram approval card with
   the dollar amount and check date prominent.
4. Human taps approve → EOS POSTs the payment via the authority engine
5. Subscribe to `ContractorPayment` webhook to confirm processing

### Recipe — handle a 504 on submit

1. Wait 5 seconds
2. `GET /v1/companies/{c}/payrolls/{p}` and inspect `processed`,
   `payroll_status_meta`
3. If `processed=true`, the submit succeeded — treat as success
4. If `processed=false` and status is still `unprocessed`, retry submit ONCE
5. If still failing, escalate to human; do not loop

### Recipe — verify a webhook end to end

1. Read `X-Gusto-Signature` and the raw body bytes
2. HMAC-SHA256 the raw body with the subscription secret
3. `hmac.compare_digest` against the header
4. Reject with 401 if mismatch (do not 200 to silence retries)
5. Parse JSON, dedupe on `event_uuid`, enqueue, return 200 within 1 second

## Industry Expert and Cutting-Edge Usage

The integrators getting the most leverage out of Gusto Embedded today share
a few patterns:

- **Hybrid web + API onboarding.** Use Gusto's Embedded React component
  library for the gnarly screens (tax setup, signatory, bank) and the API
  for everything else. This avoids rebuilding UI for compliance edge cases
  while keeping your product feel intact.
- **Webhook-first state.** Treat your local DB as a cache that webhooks
  invalidate. Don't poll. Don't trust your cache for money decisions —
  always re-fetch the live resource at submit time.
- **Per-company token isolation.** One refresh token per company, not one
  giant token for all companies. Easier to revoke, easier to debug, easier
  to audit.
- **Calculate-then-submit pattern with diffing.** Run `/calculate`, hash
  the result, render to user, if user approves and the hash still matches
  on a re-calculate, submit. If it doesn't match (rates changed, hours
  edited), abort and re-render.
- **Background reconciliation jobs** that re-fetch the last 90 days of
  payrolls nightly and diff against the local cache. Catches missed
  webhooks and silent corrections.
- **Sandbox CI.** Every PR runs against a fresh demo company in CI, not
  against a shared sandbox. Gusto sandbox demo companies are cheap to
  create and isolate test pollution.

The frontier today is **agentic payroll prep** — AI that drafts payrolls
based on time tracking, expense data, and contractor invoices, then hands
the drafted payroll to a human for one-click approval. EOS is built around
exactly this pattern. The key insight is that agents are great at
preparation and terrible at irreversible execution; the API surface should
reflect that split, and Gusto's calculate/submit separation makes it easy.

---

## EOS Usage Patterns

EOS uses Gusto in a strict read/write split enforced by the authority engine.

### Module layout

```
eos_ai/integrations/
  gusto_client.py     # single source of all Gusto HTTP calls
  gusto_oauth.py      # token refresh + atomic refresh-token persistence
  gusto_webhooks.py   # signature verification + event dispatch
  gusto_models.py     # typed wrappers around Gusto resources for Neon ORM
services/
  finance_sync.py     # nightly cron, read-only
  gusto_webhook_handler.py  # FastAPI webhook receiver
```

### Configuration

Environment variables (in `eos_ai/.env`):

```
GUSTO_ENVIRONMENT=sandbox        # or production
GUSTO_API_BASE=https://api.gusto-demo.com
GUSTO_API_VERSION=2024-04-01
GUSTO_CLIENT_ID=...
GUSTO_CLIENT_SECRET=...
GUSTO_REFRESH_TOKEN=...           # initial only; rotated and persisted to Neon
GUSTO_WEBHOOK_SECRET=...
```

The `GUSTO_ENVIRONMENT=production` flip is a deliberate, founder-only
operation. EOS code must refuse to start if `GUSTO_ENVIRONMENT=production`
and `GUSTO_HUMAN_APPROVAL_REQUIRED` is not set to `true`.

### Token persistence

Refresh tokens are stored in a Neon table `gusto_credentials` with columns
`(client_id, refresh_token, access_token, expires_at, updated_at)`. The
refresh function:

1. Reads the current refresh_token from Neon inside a transaction
2. POSTs to `/oauth/token`
3. Writes the new pair back inside the same transaction
4. Commits

If the commit fails, the OLD refresh token is gone and EOS surfaces a
critical alert to the founder via Telegram. There is no recovery short of
re-running the OAuth handshake.

### Read lane (autonomous, runs on cron)

`services/finance_sync.py` runs nightly and:

- Pulls `/v1/me` to confirm token health
- Pulls all companies the token can access
- For each company, pulls employees, contractors, pay schedules
- For each company, pulls payrolls in the last 90 days with all `include`s
- Diffs against `gusto_payrolls` and `gusto_employees` Neon tables
- Writes diffs to memory for the morning brief

This lane never touches POST/PUT/DELETE. It is safe to run every night
unattended.

### Write lane (CRITICAL risk, human-gated)

Any agent that wants to draft a payroll, contractor payment, or onboarding
action calls `authority_engine.request_action()` with:

```python
authority_engine.request_action(
    action="gusto.create_contractor_payment",
    payload={...},
    risk_class=RiskClass.CRITICAL,
    requires_human_approval=True,
    human_summary="Pay Contractor X $2,500 on 2026-04-15",
)
```

The authority engine queues the action, surfaces it to the founder via
Telegram with a clear summary, and only executes after human approval.
Execution then calls `gusto_client.create_contractor_payment(...)`. There
is no other path to a Gusto write inside EOS.

### Webhook handling

`services/gusto_webhook_handler.py` runs as a FastAPI route:

1. Read raw body
2. HMAC-verify against `GUSTO_WEBHOOK_SECRET`
3. Dedupe on `event_uuid` against `gusto_webhook_events` Neon table
4. Enqueue a follow-up GET via `gusto_client` to fetch the resource
5. Return 200 within 1 second

The follow-up GET runs in a worker, not the request handler, to keep
webhook ack times fast.

### Sandbox-first development

All EOS Gusto development happens against `api.gusto-demo.com`. The
production switch is a one-line `.env` change plus a service restart, and
must be paired with a real refresh token from a production company.

---

## Gotchas

This section compounds with every real failure encountered. Initial entries
are derived from documented behavior and community-reported issues.

- **Refresh token rotation kills you.** The old refresh token dies the
  instant you call `/oauth/token`. If your write-back to storage fails after
  the HTTP call succeeds, the integration is locked out permanently. Always
  persist atomically and prefer transactions. EOS uses a Neon transaction
  around the refresh.

- **2-hour access token expiry is shorter than people expect.** Cron jobs
  that authenticate in the morning and run all day will silently start
  401-ing. Refresh on every cold start and on every 401.

- **`X-Gusto-API-Version` is not optional in practice.** Omitting it works
  today but binds you to whatever default Gusto picks, which can shift.
  Always pin.

- **Sandbox host is `api.gusto-demo.com`.** Not `sandbox.gusto.com`, not
  `demo.gusto.com`, not `api-sandbox.gusto.com`. The wrong host produces
  DNS errors that look like network failures.

- **Onboarding step order is strict.** Federal tax → state tax → bank →
  signatory → forms → finish. Skipping a step returns 422 with a vague
  error. Check `/onboarding_status` first if you're confused.

- **Pay schedules are immortal.** Once a payroll has run on a pay schedule,
  the schedule cannot be deleted, only deactivated. Test schedules in
  sandbox accumulate forever.

- **Contractor payments are not payrolls.** Different endpoint, different
  approval flow, different webhook events, different cancellation rules.

- **Submit is irrevocable after the calculation deadline.** Typically 4pm
  PT 2 banking days before check date. After that, only Gusto support can
  cancel. EOS rule: agents never call submit.

- **504 on submit is ambiguous.** The submit may have succeeded server-side
  even though the client saw a timeout. Always re-GET before retrying.

- **Sandbox payrolls auto-process.** The fake clock advances. Don't assume
  test payrolls stay `unprocessed` between test runs.

- **Webhook events are at-least-once.** Always dedupe on `event_uuid`.

- **Webhook payloads are identifiers, not state.** You must follow up with
  a GET. This is intentional and protects against out-of-order delivery.

- **Rate limits are quiet but real.** ~10–20 RPS sustainable. 429 with
  Retry-After. Always honor the header.

- **`include` is allowlisted per endpoint.** Don't assume `include=jobs`
  works on `/contractors` because it works on `/employees`.

- **Money type inconsistency.** Newer endpoints decimal dollars, some
  legacy fields cents. Always check the schema.

- **Multi-state employees require per-state forms.** Missing a state form
  blocks payroll submission with a 422 that names the state.

- **Bank verification timing.** Plaid is instant, micro-deposits are 1–3
  business days. First payroll cannot be submitted until verification
  completes.

- **Renaming a company mid-tax-year leaks into W-2s.** Only rename between
  tax years.

- **`processing_statuses` filter takes an array.** A single value still
  needs to be wrapped: `processing_statuses=["processed"]`.

- **Polling burns rate limit.** Use webhooks for status changes.

- **Sandbox demo companies share rate limit budget with each other.** Don't
  hammer twenty test companies in parallel from the same OAuth client.
