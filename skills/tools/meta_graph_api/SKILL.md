---
name: meta_graph_api
description: "Use when working across Meta's unified Graph API surface — Facebook Pages, Messenger Platform, WhatsApp Business Cloud API, Threads API — for auth flows, token exchange, cross-surface publishing, DM automation, webhook subscriptions, app review strategy, or any operation that spans multiple Meta products. For Instagram-specific endpoint depth use the instagram skill; for Meta Ads use the meta_ads skill."
allowed-tools: "Read, Bash, Write, Edit, WebFetch"
version: 1.0
source_url: "https://developers.facebook.com/docs/graph-api"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "v23.0 stable / v24.0 / v25.0 latest (quarterly cadence, ~2yr support)"
sdk_version: "facebook-business 25.0.0 (Python), facebook-nodejs-business-sdk 25.x"
speed_category: stable
trigger: both
effort: low
context: fork
---

# Tool: Meta Graph API

## What This Tool Does

The Meta Graph API is a single HTTP surface (`https://graph.facebook.com/v{N}.0/...`)
that exposes every Meta business product as nodes and edges in one social graph.
A "node" is anything with an ID (a Page, a User, a Post, a WhatsApp phone number,
a Threads user); an "edge" is a relationship you can traverse (`/me/accounts`,
`/{page-id}/feed`, `/{ig-user-id}/media`, `/{phone-number-id}/messages`). Every
Meta surface that is not Ads speaks the same dialect.

What the unified surface covers:

- **Facebook Pages** — feed posts, photos, videos, reels, scheduled posts, page insights, page roles, tagging, mentions, branded content
- **Messenger Platform** — Send API, receive webhooks, quick replies, persistent menu, personas, handover protocol, Human Agent tag (24-hour + 7-day windows)
- **WhatsApp Business Cloud API** — template messages, session messages, media upload, phone-number registration, business profile, message status webhooks, conversation pricing
- **Threads API** — text/media/carousel/poll publishing, reply moderation, insights, public profile lookup, GIF support
- **Instagram Graph API** — business/creator account publishing, DMs (Messenger Platform fork), insights, hashtag search — covered in depth by the **`instagram`** skill
- **Facebook Groups** — heavily deprecated for third parties since 2020; only Workplace and self-owned admin tooling remain
- **Webhooks** — one subscription model for `page`, `instagram`, `messenger`, `whatsapp_business_account`, `threads` topics

What this skill is NOT:

- Meta **Ads** (Marketing API) — campaigns, ad sets, ad creatives, audiences, conversions API → see `meta_ads` skill
- Instagram-specific endpoint detail — see `instagram` skill (cross-references this one for the auth/version/webhook layer)

## EOS Integration

The Meta Graph API is the **organic distribution and DM substrate** for the
personal-brand-as-marketing strategy. It is never the main lead source on its
own — it is the cross-surface plumbing that lets one piece of content land on
four products from one publish call, and lets one inbound DM land in one
queue.

EOS surfaces:

- **Facebook Page (Lyfe Spectrum, Initiate Arena)** — required to exist for
  Meta Business Manager, used as the parent for IG asset linking and Messenger.
  Low organic priority. Used by `eos_ai/world_pulse.py` for cross-posting.
- **Messenger Platform** — DM lead-capture funnel for Initiate Arena. Inbound
  DMs route through `services/discord_bot.py → orchestrator` via webhook so
  the founder sees them in one place. Auto-reply uses Human Agent tag inside
  the 7-day window.
- **WhatsApp Business Cloud API** — staged. Template messages will be the
  international outreach channel after the first $10K/month on Initiate Arena.
- **Threads API** — content distribution. Every Initiate Arena post lands here
  via `eos_ai/orchestrator.py` cross-poster.
- **Instagram** — primary, but the Graph API auth/version layer described
  here is shared. The `instagram` skill owns the endpoint detail.

The single org-level concept that unifies all of this in EOS: a **Page Access
Token + Instagram Business Account ID + WhatsApp Business Account ID +
Threads User ID** bundle, stored encrypted per-tenant in Neon. `eos_ai/tenant.py`
loads the bundle; every Meta-surface module receives it as input. Never read
tokens from `os.environ` inside business code.

## Authentication

Meta Graph auth is the single hardest thing about the API. There are five
token types and each has a different lifecycle, scope, and refresh story.

**1. App Access Token** (`{app-id}|{app-secret}`)
   Server-to-server only. Used for app-scoped reads, debug_token, webhook
   verification. Never put in client code. Never expires (until you reset
   the secret).

**2. Short-lived User Access Token** (1-2 hours)
   Created by the Login dialog or `/oauth/access_token` from a code. Used to
   bootstrap everything else. Always exchange for long-lived immediately.

**3. Long-lived User Access Token** (~60 days)
   Exchange via `GET /oauth/access_token?grant_type=fb_exchange_token`. Cannot
   be refreshed by another long-lived exchange beyond ~60 days unless the user
   re-engages with the app.

**4. Page Access Token** (long-lived → never-expiring)
   Fetched from `GET /me/accounts` while holding a long-lived USER token. The
   page token inherits the long-lived property and effectively never expires
   as long as the user account stays active and the granted permissions are
   not revoked. **This is the workhorse token for organic publishing.**

**5. System User Access Token** (Business Manager, never expires)
   Created in Business Manager → Users → System Users → Generate New Token.
   Scoped to a Business and to specific assets. The right answer for any
   automated/back-end EOS workload that doesn't require a real user login.
   Use these for production.

WhatsApp Cloud API uses the same Graph version + a System User token bound
to the WhatsApp Business Account. Threads uses its own short-lived → long-lived
exchange at `https://graph.threads.net/oauth/access_token`.

The token dance, in order, for a brand-new Meta integration:

1. App Review approval for the permissions you need (Advanced Access)
2. User logs in via Facebook Login → short-lived USER token
3. Exchange → long-lived USER token (60 days)
4. `GET /me/accounts` with long-lived USER token → Page Access Tokens
5. Store the Page tokens in Neon, encrypted at rest
6. For automation: create a System User in Business Manager, generate a
   permanent token, swap out the user-derived tokens
7. `GET /debug_token?input_token=...&access_token={app-token}` to inspect
   any token's expiry, scopes, app ID, user ID before use

## Quick Reference

```bash
# 0. Resolve the current API version once per script
GV=v23.0

# 1. Exchange short-lived for long-lived USER token
curl -s -G "https://graph.facebook.com/${GV}/oauth/access_token" \
  --data-urlencode "grant_type=fb_exchange_token" \
  --data-urlencode "client_id=${FB_APP_ID}" \
  --data-urlencode "client_secret=${FB_APP_SECRET}" \
  --data-urlencode "fb_exchange_token=${SHORT_LIVED}"

# 2. Fetch page tokens (and their permanence)
curl -s -G "https://graph.facebook.com/${GV}/me/accounts" \
  --data-urlencode "access_token=${LONG_USER_TOKEN}" \
  --data-urlencode "fields=id,name,access_token,tasks"

# 3. Inspect a token (always do this before trusting one)
curl -s -G "https://graph.facebook.com/${GV}/debug_token" \
  --data-urlencode "input_token=${TOKEN_TO_INSPECT}" \
  --data-urlencode "access_token=${FB_APP_ID}|${FB_APP_SECRET}"

# 4. GET a node with field expansion
curl -s -G "https://graph.facebook.com/${GV}/${PAGE_ID}" \
  --data-urlencode "fields=id,name,fan_count,posts.limit(5){message,created_time,permalink_url}" \
  --data-urlencode "access_token=${PAGE_TOKEN}"

# 5. POST to an edge (publish a Page text post)
curl -s -X POST "https://graph.facebook.com/${GV}/${PAGE_ID}/feed" \
  -d "message=Hello from EOS" \
  -d "access_token=${PAGE_TOKEN}"

# 6. Send a Messenger message (Send API)
curl -s -X POST "https://graph.facebook.com/${GV}/${PAGE_ID}/messages" \
  -H "Content-Type: application/json" \
  -d "{
    \"recipient\":{\"id\":\"${PSID}\"},
    \"messaging_type\":\"RESPONSE\",
    \"message\":{\"text\":\"Hi from Initiate Arena\"}
  }" \
  -d "access_token=${PAGE_TOKEN}"

# 7. WhatsApp Cloud — send a template
curl -s -X POST "https://graph.facebook.com/${GV}/${WA_PHONE_ID}/messages" \
  -H "Authorization: Bearer ${WA_SYSTEM_USER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "messaging_product":"whatsapp",
    "to":"15551234567",
    "type":"template",
    "template":{"name":"hello_world","language":{"code":"en_US"}}
  }'

# 8. Publish to Threads (two-step container -> publish)
CID=$(curl -s -X POST "https://graph.threads.net/${GV}/${THREADS_USER_ID}/threads" \
  -d "media_type=TEXT" -d "text=Shipping" -d "access_token=${THREADS_TOKEN}" \
  | jq -r .id)
curl -s -X POST "https://graph.threads.net/${GV}/${THREADS_USER_ID}/threads_publish" \
  -d "creation_id=${CID}" -d "access_token=${THREADS_TOKEN}"

# 9. Subscribe a Page to webhook fields
curl -s -X POST "https://graph.facebook.com/${GV}/${PAGE_ID}/subscribed_apps" \
  -d "subscribed_fields=feed,messages,messaging_postbacks,message_deliveries" \
  -d "access_token=${PAGE_TOKEN}"

# 10. Batch request — up to 50 sub-calls in one HTTP round trip
curl -s -X POST "https://graph.facebook.com/${GV}" \
  -d "access_token=${PAGE_TOKEN}" \
  --data-urlencode 'batch=[
    {"method":"GET","relative_url":"me?fields=id,name"},
    {"method":"GET","relative_url":"me/posts?limit=5"}
  ]'
```

## Conceptual Model

**One graph, many products, one version dial.** Internalize this and every
Meta surface stops feeling like a different API:

1. **Everything is a node.** Pages, Users, Posts, Comments, IG accounts,
   Threads users, WhatsApp phone numbers, ad accounts. Every node has a
   stable ID and a `/{id}` endpoint that accepts `?fields=...`.

2. **Edges are relationships.** `/{node}/{edge}` lists or creates connected
   nodes (`/me/accounts`, `/{page}/feed`, `/{ig-user}/media`,
   `/{wa-phone}/messages`). POST creates, GET lists, DELETE removes.

3. **Versioning is a contract.** `v{N}.0` in the URL pins the schema. Meta
   ships a new version every ~3 months and supports each one for ~2 years.
   `v23.0` (May 2025) is the current stable; `v24.0` (Oct 2025) and `v25.0`
   are newer. Old versions auto-redirect to the next stable when sunset
   (with breakage). Pin the version in EVERY call.

4. **Permissions gate edges, not products.** You don't "enable Messenger" —
   you request `pages_messaging`, get app review, and the edge starts
   accepting your requests. Same model for `pages_manage_posts`,
   `whatsapp_business_messaging`, `threads_basic`, etc.

5. **Tokens scope the graph.** A Page Token can see what that Page can see.
   A System User Token can see what its Business Manager assets allow. A
   USER token can see what the user authorized AND nothing more.

6. **Webhooks are the inverse of GET.** Same node/edge model, pushed to
   your callback URL when state changes. One subscription per topic per
   Meta App, with field-level subscription per asset.

The **product divisions you see in the Meta for Developers UI** (Facebook
Login, Pages API, Messenger, Instagram, WhatsApp, Threads) are organizational —
all of them are the same HTTP surface differentiated by node type, edge name,
and required permission.

## Gotchas

- **Token type confusion.** Sending a User Token to `/{page}/feed` POST
  returns `(#200) Permissions error` even though the user is the page admin.
  Pages publish with **Page** tokens. Always.
- **App review timeline is multi-week.** Plan for 2-6 weeks for Advanced
  Access on `pages_manage_posts`, `pages_messaging`, `whatsapp_business_messaging`,
  `threads_content_publish`. Standard Access works for self-owned assets only.
- **Version pinning matters.** Omitting `/v{N}.0/` defaults to oldest
  supported, which Meta sunsets quarterly. Hardcode + bump deliberately.
- **Page tokens expire if you derive them from a USER token that wasn't
  long-lived.** Always do the long-lived exchange BEFORE `/me/accounts`.
- **Messenger 24-hour window.** Outside the standard messaging window you
  cannot send a free-form message — you need a `MESSAGE_TAG`, `HUMAN_AGENT`
  (7-day window, requires extra perm), or a `NON_PROMOTIONAL_SUBSCRIPTION`.
- **WhatsApp template approval.** Marketing/utility/auth templates need
  Meta approval per language. Edits trigger re-review. Mismatched variables
  in payload vs template = silent fail with status `failed`.
- **WhatsApp pricing model changed.** Since July 2025, Meta charges
  per-delivered-template-message, not per 24-hour conversation. Service
  messages and utility messages inside the customer service window are
  free. Budget accordingly.
- **Webhook duplicate delivery.** Meta retries on any non-200, and sometimes
  sends duplicates anyway. Idempotency key on `entry[].id` + `time`.
- **Webhook signature validation is mandatory.** Compute
  `HMAC-SHA256(body, app_secret)` and compare to `X-Hub-Signature-256`.
  Skip this and anyone can spoof your callback.
- **Error subcodes matter more than codes.** `error.code=190` covers
  every OAuth issue; the `error_subcode` (458 password changed, 460 checkpoint,
  463 expired, 467 invalid) tells you what to actually do.
- **Rate limit headers.** `X-App-Usage`, `X-Page-Usage`, `X-Business-Use-Case-Usage`
  return JSON with `call_count`, `total_cputime`, `total_time` percentages.
  At 100% you get blocked for an hour. Read these every response.
- **Field expansion has a depth/limit cap.** `posts.limit(5){comments.limit(3){from}}`
  works; nesting 4 deep or asking for `limit(500)` silently truncates.
- **Instagram vs Page tokens.** IG Graph endpoints accept the **Page** token
  of the Page that the IG Business Account is linked to — not a separate
  IG token. The `instagram` skill expands this.
- **Threads runs on its own host.** `graph.threads.net`, not `graph.facebook.com`.
  Same auth model, different base URL. Don't hardcode the FB host.
- **Facebook Groups API is mostly dead.** Since April 2024 third-party
  group write access requires the Group admin to install the app and the
  scopes are vestigial. Don't promise anyone Group automation.
- **System User tokens leak forever.** They don't expire. Treat them like
  AWS root keys. Vault them.

See `references/best_practices.md` for the full creator-level knowledge base
covering all 19 sections (auth deep-dive, every surface's edges, webhooks,
limits, error catalog, EOS recipes).
