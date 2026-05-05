---
name: shopify
description: "Use when querying or mutating Shopify store data via Admin GraphQL API (products, orders, customers, inventory), building Storefront/Hydrogen frontends, managing webhooks, designing theme/app integrations, or making ecommerce architecture decisions for Lyfe Spectrum."
allowed-tools: "Read, Bash, Write, Edit, WebFetch"
version: 1.0
source_url: "https://shopify.dev/docs/api"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "2026-04 (Admin GraphQL stable)"
sdk_version: "@shopify/shopify-api 11.x (Node), shopify-python-api 12.x"
speed_category: stable
trigger: both
effort: low
context: fork
---

# Tool: Shopify

## What This Tool Does

Shopify is a hosted commerce platform exposing a programmable backend through
several distinct APIs. The platform separates authoring (themes, admin) from
data access (Admin API), customer-facing reads (Storefront API), and runtime
extension (Functions, Checkout Extensibility, App Bridge). For agents building
or operating an EOS-managed store, the surface area looks like this:

- **Admin GraphQL API** — canonical read/write for products, variants,
  inventory, orders, customers, fulfillments, metafields, discounts,
  collections, draft orders, locations, B2B companies. REST Admin is
  legacy as of 2024-04 and is being progressively removed; new code is
  GraphQL only.
- **Storefront API** — unauthenticated GraphQL for headless storefronts,
  product listing pages, cart, and checkout creation. Uses Storefront Access
  Tokens, not admin tokens.
- **Shopify Functions** — Wasm modules (Rust/JS) that run in the request
  path for discount logic, cart/checkout validation, delivery customization,
  and payment customization. Replaces the deprecated Shopify Scripts.
- **Webhooks** — push events delivered over HTTPS or EventBridge/PubSub for
  product/order/customer/inventory mutations. HMAC-SHA256 signed.
- **Hydrogen + Oxygen** — React Server Components framework + Shopify-hosted
  edge runtime for headless storefronts. Calls the Storefront API.
- **App Bridge + Polaris** — embedded admin app SDK + design system.

The two non-obvious mental models: (1) Admin GraphQL is **billed by query
cost**, not request count, and (2) **API versions are date-strings** with a
12-month support window — pinning is non-optional.

## EOS Integration

Shopify is the **primary ecommerce engine for Lyfe Spectrum** — the apparel
brand under Lyfe Institute. Agents interact with the store for:

- **Product catalog management** — drafting product copy, creating variants,
  uploading images, organising collections from skill outputs
- **Order sync** — pulling new orders into EOS memory for fulfillment, CRM,
  and revenue dashboards (`world_pulse`, `business_instance`)
- **Inventory automation** — low-stock alerts, restock triggers, multi-location
  rebalancing for drops
- **Launch automation** — Shopify Flow + Functions for limited drop mechanics
  (queue, cart limits, discount stacking rules)
- **Subscription products** — gift cards, recurring tee drops via Shopify
  Subscriptions app
- **Headless consideration** — when conversion data justifies it, migrate
  Lyfe Spectrum frontend to Hydrogen on Oxygen for tactical-luxury performance

Cross-references:
- `skills/tools/stripe/` — Shopify Payments vs Stripe direct: use Shopify
  Payments inside checkout to avoid the 2% transaction fee surcharge; use
  Stripe direct only for off-Shopify products (Initiate Arena cohorts,
  Empyrean invoices). Never duplicate.
- `skills/tools/klaviyo/` — email/SMS marketing wired to Shopify customer
  events via the native integration, not via webhooks
- `skills/tools/google_analytics/` — GA4 ecommerce events configured in the
  theme + Shopify Pixels, not via Tag Manager
- `eos_ai/world_pulse.py` — daily Shopify revenue snapshot ingestion target

## Authentication

Three distinct token types — never confuse them.

**1. Custom App admin access token** (what EOS uses for backend automation)

Created in Shopify Admin → Settings → Apps and sales channels → Develop apps
→ Create app → Configure Admin API scopes → Install. Yields a token starting
with `shpat_`. Single store. No OAuth flow. Granted exact scopes selected at
install time; rotating scopes requires reinstall.

```python
import os, requests
SHOP   = os.environ["SHOPIFY_SHOP"]              # lyfe-spectrum.myshopify.com
TOKEN  = os.environ["SHOPIFY_ADMIN_TOKEN"]       # shpat_xxx
APIVER = "2026-04"

def admin_gql(query: str, variables: dict | None = None) -> dict:
    r = requests.post(
        f"https://{SHOP}/admin/api/{APIVER}/graphql.json",
        headers={
            "X-Shopify-Access-Token": TOKEN,
            "Content-Type": "application/json",
            "Shopify-GraphQL-Cost-Debug": "1",   # include cost breakdown
        },
        json={"query": query, "variables": variables or {}},
        timeout=30,
    )
    r.raise_for_status()
    body = r.json()
    if "errors" in body:
        raise RuntimeError(body["errors"])
    return body
```

**2. Public App OAuth** — for apps distributed to multiple merchants. Uses
the standard OAuth 2.0 authorization code flow against
`https://{shop}/admin/oauth/authorize`. Returns a per-shop offline token.
EOS does not currently use this; only relevant if Lyfe Spectrum becomes a
SaaS for other merchants.

**3. Storefront Access Token** — for unauthenticated client-side calls to
the Storefront API. Created via Admin API or in admin under Headless sales
channel. Public-safe (rate limited per IP). Header
`X-Shopify-Storefront-Access-Token`.

**Webhook HMAC** — webhooks use the app's API secret (NOT the access token)
to sign the raw request body. Verify with `hmac.compare_digest`. See Quick
Reference below.

## Quick Reference

### Fetch products with cost economy

```graphql
query ProductsPage($first: Int!, $after: String) {
  products(first: $first, after: $after, query: "status:active") {
    edges {
      cursor
      node {
        id
        handle
        title
        totalInventory
        priceRangeV2 { minVariantPrice { amount currencyCode } }
        variants(first: 50) {
          edges { node { id sku inventoryQuantity price } }
        }
      }
    }
    pageInfo { hasNextPage endCursor }
  }
}
```

```python
data = admin_gql(QUERY, {"first": 50, "after": None})
print(data["extensions"]["cost"])
# {'requestedQueryCost': 152, 'actualQueryCost': 87,
#  'throttleStatus': {'maximumAvailable': 1000.0,
#                     'currentlyAvailable': 913.0,
#                     'restoreRate': 50.0}}
```

### Create a product (mutation)

```graphql
mutation ProductCreate($input: ProductInput!) {
  productCreate(input: $input) {
    product { id handle }
    userErrors { field message }
  }
}
```

Note `userErrors` — these are validation failures, returned with HTTP 200.
Always check `userErrors` length before treating a mutation as successful.

### Bulk operation (export all orders)

```graphql
mutation {
  bulkOperationRunQuery(query: """
    {
      orders(query: "created_at:>=2026-01-01") {
        edges { node { id name totalPriceSet { shopMoney { amount } }
                       customer { email } lineItems { edges { node { sku
                       quantity } } } } }
      }
    }
  """) {
    bulkOperation { id status }
    userErrors { field message }
  }
}
```

Then poll `currentBulkOperation { status url }` and download the JSONL when
status is `COMPLETED`. Bulk operations bypass query cost limits — the only
correct way to export the entire store.

### Webhook HMAC verification (Python)

```python
import hmac, hashlib, base64, os, json
from flask import request, abort

WEBHOOK_SECRET = os.environ["SHOPIFY_WEBHOOK_SECRET"].encode()

def verify_shopify_webhook(raw_body: bytes, header_hmac: str) -> bool:
    digest = hmac.new(WEBHOOK_SECRET, raw_body, hashlib.sha256).digest()
    computed = base64.b64encode(digest).decode()
    return hmac.compare_digest(computed, header_hmac)

@app.post("/webhooks/shopify/orders-create")
def shopify_orders_create():
    raw = request.get_data()  # MUST be raw, not request.json
    header = request.headers.get("X-Shopify-Hmac-Sha256", "")
    if not verify_shopify_webhook(raw, header):
        abort(401)
    payload = json.loads(raw)
    handle_new_order(payload)
    return "", 200
```

### Inventory adjust

```graphql
mutation InventoryAdjust($input: InventoryAdjustQuantitiesInput!) {
  inventoryAdjustQuantities(input: $input) {
    inventoryAdjustmentGroup { createdAt reason }
    userErrors { field message }
  }
}
```

## Conceptual Model

**Three economies overlap in every Shopify integration: query cost, version
stability, and extension surface.**

1. **Query cost economy.** Admin GraphQL is metered by *calculated cost*,
   not request count. Each call has a requested cost (estimated from the
   query shape) and an actual cost (after execution). Your app holds a
   1,000-point bucket that refills at 50 points/second (Standard) or
   2,000-point bucket at 100/sec (Plus). Connections cost
   `2 + objects_returned`, scalar fields cost 0, mutations cost 10 minimum.
   Optimization is therefore not "fewer requests" — it is "smaller queries
   per request and pagination over depth." Bulk operations bypass the
   bucket entirely.

2. **API version stability.** Versions are date strings (`2026-04`).
   A new stable version ships quarterly. Each version is supported for
   12 months minimum, so you have ~9 months of overlap to migrate. Pin
   explicitly in every URL — never use `unstable` or `latest` in production.
   Track Shopify's changelog quarterly; if you skip migration windows
   your endpoint silently 404s.

3. **Extension surface.** There are three ways to change Shopify behaviour:
   - **Themes (Liquid + OS 2.0 sections)** for presentation
   - **Apps (App Bridge + Polaris)** for admin UI and integrations
   - **Functions (Wasm)** for in-checkout business logic
   Picking the wrong layer is the #1 source of pain. Discount logic →
   Function, not theme. Bulk product edits → Admin API, not theme.
   Custom checkout fields → Checkout UI Extension, not Liquid.

If you internalize these three, every Shopify integration decision is
mechanical: where does the data live, what does it cost to query, what
version am I pinned to, which extension surface owns the change?

## Gotchas

- **REST is a trap for new code.** REST Admin is legacy and several
  resources (products, variants, inventory) lose features each release.
  Use GraphQL Admin only — every example online from 2020-2023 is REST
  and is now wrong.
- **`Shopify-GraphQL-Cost-Debug: 1`** must be set as a request header to
  see per-field cost breakdown. Without it you only see totals and will
  misdiagnose throttling.
- **Webhook HMAC fails silently** if you parse the body before verifying
  (Flask `request.json`, Express `bodyParser.json()`). The signature is
  computed against the raw bytes. ALWAYS capture raw body first.
- **`userErrors` are 200 OK.** A `productCreate` returning
  `{userErrors: [{message: "Handle is already taken"}]}` is HTTP 200.
  Mutation success requires both `errors == None` AND
  `len(userErrors) == 0`.
- **Metafield namespaces collide silently.** Two apps writing to
  `custom.color` will overwrite each other. Use a vendor-prefixed
  namespace (`lyfe_spectrum.color`) and the `metafieldDefinitionCreate`
  mutation to claim it.
- **API version deprecation 404s.** A pinned URL like
  `/admin/api/2024-07/graphql.json` returns 404 the day after sunset, not
  a deprecation warning. Set a calendar reminder per quarterly release.
- **Shopify Payments is country-locked.** Not available in many markets.
  If Lyfe Spectrum expands internationally, plan around third-party
  gateways and the 2% surcharge.
- **Flow vs Functions confusion.** Flow is admin-side automation
  (no-code, async, "if order tagged X, send Slack"). Functions are
  in-request runtime extensions (Wasm, sync, "discount $5 if cart has
  3 tees"). They are NOT alternatives — they solve different problems.
- **Bulk operations are not parallel.** Only one bulk operation per shop
  at a time. Starting a second cancels the first with `ALREADY_RUNNING`.
- **Storefront tokens are public.** Never reuse an admin token in
  client-side code. Storefront tokens cannot read orders or customer PII.
- **GraphQL `id` fields are GIDs**, not numbers:
  `gid://shopify/Product/1234567890`. REST IDs and GraphQL GIDs are not
  interchangeable in URLs or filters.
- **Inventory mutations require `inventoryItemId` + `locationId`.**
  Shopify is multi-location by default since 2023. There is no "shop
  inventory" — there is per-location inventory.

See `references/best_practices.md` for the full 19-section creator-level
knowledge base, EOS usage patterns, and the failure catalog.
