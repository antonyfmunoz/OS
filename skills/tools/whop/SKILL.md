---
name: whop
description: "Use when evaluating or building against Whop for Initiate Arena coaching checkout/community, designing creator commerce on Whop, integrating Discord roles with paid memberships, building Whop Apps, or analyzing Whop vs Gumroad/Circle/Skool for EOS commerce decisions."
allowed-tools: "Read, Bash, Write, Edit, WebFetch"
version: 1.0
source_url: "https://dev.whop.com"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "v5"
sdk_version: "@whop/sdk 0.0.25 (Node/TS), whopsdk-python (Python)"
speed_category: stable
---

# Tool: Whop

## What This Tool Does

Whop is a creator commerce platform that bundles checkout, memberships,
community, courses, Discord role gating, license keys, affiliates, and an
in-house app marketplace into a single account. A creator creates a "whop"
(a hub), attaches one or more **access passes** (the SKU — what users buy),
and exposes one or more **experiences** (the thing users get — a Discord role,
a course, a chat, a custom iframe app). Whop runs the storefront, the
checkout, payment processing, dunning, refunds, and Discover (their internal
marketplace) on top of every whop.

Core capabilities:

- **Hosted checkout + payment processing** — Stripe-grade flow with Apple Pay,
  Google Pay, cards, crypto; one-time and recurring billing; trials; coupons
- **Memberships** — recurring or lifetime, with auto role-sync to Discord on
  `membership.went_valid` / `membership.went_invalid`
- **Experiences** — courses (with drip schedules), chat, forums, file vault,
  livestream, calendar bookings, custom iframe apps (~15 first-party apps)
- **Affiliates** — built-in affiliate program per access pass with custom
  commission, attribution windows, automatic payout
- **License keys + software gating** — sell SaaS access, validate via API
- **Whop Apps SDK** — build a Next.js/React iframe app, publish to the App
  Store, instantly distributed across every whop
- **Public REST API (`api.whop.com/api/v5`)** — payments, memberships,
  access passes, users, webhooks; OAuth 2.1 + PKCE for user-context calls,
  bearer API key for app-context calls
- **Discover marketplace** — organic distribution channel competitors lack

## EOS Integration

Whop is evaluated as a **commerce substrate** for several EOS products. It
trades flexibility for speed: the moment a Whop is live, checkout, dunning,
Discord gating, affiliates, and a marketplace listing exist for free. The
trade is a 3% platform fee on top of payment processing.

Primary use cases under evaluation:

- **Initiate Arena (Lyfe Institute)** — replace the bespoke
  Stripe Checkout + custom Discord bot stack with a Whop access pass priced
  at the $750 entry point. One pass = one Discord role = one course experience
  with a drip schedule mapped to the Initiate curriculum. Removes weeks of
  webhook plumbing the EOS team would otherwise own.
- **Lyfe Spectrum exclusive drops** — gated merch drops where buying a Whop
  pass unlocks the drop link and a private Discord channel. The pass is the
  presale receipt; the affiliate program seeds the launch.
- **Future digital products** — prompt packs, templates, the EntrepreneurOS
  SaaS waitlist, Game of Lyfe pre-orders. Whop becomes the default checkout
  for anything sub-$500 that doesn't justify a custom funnel.

What Whop is NOT used for inside EOS:

- **Not** the system of record. The EOS Postgres remains canonical. Whop
  webhooks ingest into the EOS event bus and create/update Neon rows.
- **Not** the agent runtime. Whop is a commerce surface; cognition happens
  in `eos_ai/`. The Whop App SDK is used only when an experience needs
  embedded EOS UI.
- **Not** for any product where the take rate matters more than the
  go-to-market speed. At $50K/mo a 3% Whop cut is $1.5K/mo — a Whop App that
  embeds direct Stripe at scale becomes the right call.

Canonical EOS pattern:

1. Create access pass on Whop (manual, one-time) → record `pass_xxx` in
   `eos_ai/business_instance.py`
2. Subscribe to `payment.succeeded` and `membership.went_valid` /
   `membership.went_invalid` webhooks at `/webhooks/whop` on the EOS gateway
3. Verify webhook signature, persist event to `events` table, route into
   the cognitive loop as a `purchase_event` primitive
4. Cognitive loop triggers onboarding agent (welcome DM, calendar link,
   first-week drip)
5. Discord role-sync handled by Whop natively — EOS does not own that wire

## Authentication

Two distinct auth modes — choose by who is calling.

**App-context (server-to-server, you are acting as your own company):**

```bash
# Bearer API key in the Authorization header
curl https://api.whop.com/api/v5/payments \
  -H "Authorization: Bearer $WHOP_API_KEY" \
  -G --data-urlencode "company_id=biz_xxxxxxxxxxxxxx"
```

API key obtained from the developer settings page on dash.whop.com. Scoped to
a single company (`biz_*`). Store in `eos_ai/.env` as `WHOP_API_KEY`. Never
commit. Never hardcode.

**User-context (your app acting on behalf of a Whop user):**

OAuth 2.1 + PKCE flow. Get `client_id` and `client_secret` from developer
settings, redirect user to Whop's authorize endpoint, exchange code for an
access token, then call the API with that token instead of the bearer key.
Tokens are scoped to whatever the user can access. Use this only when
building a Whop App that other creators install.

**Permissions for webhooks:** request `webhook_receive:*` permissions on the
app and select the events you want before Whop will deliver them.

## Quick Reference

### TypeScript SDK (preferred)

```bash
npm i @whop/sdk
```

```ts
import Whop from "@whop/sdk";

const whop = new Whop({ apiKey: process.env.WHOP_API_KEY! });

// List recent payments for the company
const payments = await whop.payments.list({
  company_id: "biz_xxxxxxxxxxxxxx",
});

// Check if a user holds a specific access pass
const access = await whop.me.hasAccess({ id: "pass_xxxxxxxxxxxxxx" });

// List members of an access pass (auto-paginating)
for await (const m of whop.memberships.list({ access_pass_id: "pass_xxx" })) {
  console.log(m.id, m.status, m.user.username);
}
```

### Python SDK

```bash
pip install whop
```

```python
import os
from whop import Whop

client = Whop(api_key=os.environ["WHOP_API_KEY"])
page = client.payments.list(company_id="biz_xxxxxxxxxxxxxx")
for payment in page.auto_paging_iter():
    print(payment.id, payment.final_amount, payment.user_id)
```

### Raw REST (for EOS Python where the SDK is overkill)

```python
import os, requests
r = requests.get(
    "https://api.whop.com/api/v5/memberships",
    headers={"Authorization": f"Bearer {os.environ['WHOP_API_KEY']}"},
    params={"access_pass_id": "pass_xxxxxxxxxxxxxx", "per": 50},
    timeout=10,
)
r.raise_for_status()
for m in r.json()["data"]:
    print(m["id"], m["status"])
```

### Webhook receiver (FastAPI / EOS gateway)

```python
from fastapi import APIRouter, Request, HTTPException
import hmac, hashlib, os

router = APIRouter()
SECRET = os.environ["WHOP_WEBHOOK_SECRET"].encode()

@router.post("/webhooks/whop")
async def whop_webhook(req: Request):
    raw = await req.body()
    sig = req.headers.get("Whop-Signature", "")
    expected = hmac.new(SECRET, raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        raise HTTPException(401, "bad signature")
    event = await req.json()
    # event["action"] == "membership.went_valid" | "payment.succeeded" | ...
    # event["data"] == the resource
    return {"ok": True}
```

### ID prefixes (cheat sheet)

| Prefix     | Resource                                       |
|------------|------------------------------------------------|
| `biz_*`    | Company (the whop owner)                       |
| `pass_*`   | Access pass (the SKU)                          |
| `exp_*`    | Experience (course / chat / app instance)      |
| `mem_*`    | Membership (a user's relationship to a pass)   |
| `pay_*`    | Payment                                        |
| `user_*`   | Whop user                                      |
| `prod_*`   | Product (a pricing variant under a pass)       |

## Conceptual Model

**Pass is the SKU. Experience is the deliverable. Membership is the join.**

A Whop is shaped like this:

```
Company (biz_*)
 └── Access Pass (pass_*)         ← what users buy
      ├── Pricing (prod_*)        ← monthly / annual / lifetime variants
      └── Experiences (exp_*)     ← what users get
           ├── Course (drip schedule)
           ├── Chat
           ├── Discord role sync
           └── Custom iframe app
User (user_*)
 └── Membership (mem_*)            ← user × pass, with status
      ├── status: valid | invalid | trialing | past_due
      └── grants access to all experiences attached to the pass
```

Once you internalize this, every API call makes sense:

- "Did this user buy?" → fetch membership by `user_id` and `access_pass_id`,
  check `status == "valid"`
- "Give them course access" → nothing to do; attaching the course
  experience to the pass already grants it
- "Build a custom feature for buyers" → publish a Whop App, attach it as an
  experience to the pass

Whop's design intent is **Shopify for creators**: opinionated defaults, a
hosted storefront, an app ecosystem that compounds. The marketplace
(Discover) is the analog of Shopify's app store but for end customers, not
just creators — you list a whop and Whop drives traffic to it.

## Gotchas

- **3% platform fee is on top of processor fees** — Whop takes 3%, then
  Stripe-equivalent processing is 2.7% + $0.30 domestic. International
  cards add 1.5%, currency conversion adds another 1%. Real total on a US
  $750 sale: ~$48. At $50K/mo Whop costs ~$1,500/mo on top of processing.
  Past ~$30K/mo, a custom Stripe stack starts winning.
- **Discord role sync depends on Whop's Discord bot being healthy** — if
  the bot is down or removed from the server, `membership.went_valid` still
  fires but the role never lands. Always verify the bot has Manage Roles
  and is above the role it assigns in the server hierarchy.
- **Payouts are not instant** — new accounts have a 7-day rolling reserve;
  established accounts settle on a weekly schedule. Do not promise customers
  a same-day refund out of platform balance.
- **Webhook signature header is case-sensitive in some frameworks** — the
  header is `Whop-Signature`. FastAPI lowercases everything; ASGI passes
  the raw header. Always normalize before HMAC compare.
- **Webhooks can fire out of order and be redelivered** — `payment.succeeded`
  may arrive before `membership.went_valid` for a brand-new user. Make
  every handler idempotent on the event ID.
- **Rate limit is 60-second cooldown on hit** — there is no published
  per-minute budget. The SDK auto-retries 429s with backoff. If you are
  doing a bulk backfill, paginate slowly and respect `Retry-After`.
- **`@whop/api` is not the same as `@whop/sdk`** — `@whop/api` is the older
  Apps-SDK adjacent package. The current official server SDK is `@whop/sdk`.
  Don't mix them.
- **Affiliate attribution is cookie-based with a configurable window** —
  default is short. If you run paid ads + affiliates simultaneously, the
  last-touch model can starve affiliates of credit. Set the window
  explicitly per pass.
- **Course drip is per-experience, not per-user-cohort** — everyone on the
  same pass is on the same drip clock from their join date. There is no
  native "cohort starts March 15" mode. Build that in EOS if you need it.
- **Discover listing is not automatic** — you opt in per whop. For
  Initiate Arena the trade-off is reach vs. brand control; default to off
  until the offer is dialed in.
- **API version pin** — the current public version is `v5`. The library
  pins this for you; if you call REST directly, include `/api/v5/` in the
  path explicitly so a future v6 launch does not silently change behavior.
- **Iframe SDK uses `window.postMessage`** — if you build a Whop App, the
  parent frame is whop.com. CSP and `X-Frame-Options` on your app must
  allow that origin or the app will render blank with no console error.

See references/best_practices.md for the full 19-section creator-level
knowledge base, EOS usage patterns, and the complete Gotchas catalog.
