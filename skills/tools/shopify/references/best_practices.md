# Shopify — Creator-Level Best Practices
Source: shopify.dev/docs/api, shopify.dev/changelog, shopify.dev/docs/apps, shopify.dev/docs/storefronts/hydrogen, shopify.engineering, github.com/Shopify
API Version: 2026-04 (Admin GraphQL stable), Storefront 2026-04, Functions Wasm v1
SDK Version: @shopify/shopify-api 11.x (Node), shopify-python-api 12.x, shopify_api 14.x (Ruby), Hydrogen 2026.4
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## Authentication

Shopify exposes four authentication contexts. Mixing them is the most common
integration bug — each token type works against exactly one API surface and
cannot be substituted.

### 1. Custom App admin access token (single-store, no OAuth)

Created in the Shopify Admin under **Settings → Apps and sales channels →
Develop apps → Create app**. Pick the Admin API access scopes (e.g.
`read_products`, `write_inventory`, `read_orders`, `write_orders`,
`read_customers`, `write_metaobjects`), then **Install app**. Shopify
generates a single `shpat_…` token bound to that store.

Properties:
- One token per store. No refresh, no expiry, no rotation API.
- Scopes are frozen at install time. Adding a scope = uninstall + reinstall +
  new token (and any in-flight webhooks must be re-registered).
- Header: `X-Shopify-Access-Token: shpat_…`
- Use this for all EOS backend automation against Lyfe Spectrum.
- Never put it in client-side code, never commit it to git, never log it.
- Revocation: delete the custom app from the admin. There is no per-token
  revoke endpoint.

```bash
curl -sS https://lyfe-spectrum.myshopify.com/admin/api/2026-04/graphql.json \
  -H "X-Shopify-Access-Token: $SHOPIFY_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"{ shop { name myshopifyDomain primaryDomain { url } } }"}'
```

### 2. Public App OAuth (multi-merchant distribution)

Standard OAuth 2.0 authorization code flow. Used when you distribute one
app to many merchants (Shopify App Store or unlisted distribution).

Flow:
1. Merchant clicks install → `https://{shop}/admin/oauth/authorize?client_id=…&scope=read_products,write_orders&redirect_uri=…&state=…&grant_options[]=`
2. Merchant approves → Shopify redirects to your `redirect_uri` with `code`,
   `shop`, `host`, `hmac`, `state`.
3. Verify the HMAC of the query string using your client secret.
4. POST to `https://{shop}/admin/oauth/access_token` with
   `client_id`, `client_secret`, `code` → returns
   `{access_token, scope}`. This is an **offline token** by default
   (no expiry, like the custom app token).
5. For an **online token** (per-staff, ~24h TTL, used for embedded admin
   UI surfaces) include `grant_options[]=per-user`.

Token Exchange (preferred 2024+) replaces the OAuth redirect dance for
embedded apps using App Bridge session tokens — exchange a JWT session
token for an offline access token via
`/admin/oauth/access_token` with `grant_type=urn:ietf:params:oauth:grant-type:token-exchange`.
This is faster and avoids the install redirect for already-installed apps.

### 3. Storefront API access token (public, headless)

Created via `storefrontAccessTokenCreate` mutation in the Admin API or via
the Headless sales channel UI. Public-safe — embed in JavaScript bundles
without leaking customer data because the token only has read access to
public storefront data plus cart and checkout creation.

Header: `X-Shopify-Storefront-Access-Token: <token>`
Endpoint: `https://{shop}/api/2026-04/graphql.json`

Storefront API rate limits are per-IP per-minute (not query cost) for
unauthenticated calls. Authenticated buyer calls (Customer Account API)
use OAuth-issued buyer tokens.

### 4. Webhook HMAC signing (verifying push events)

Webhooks are signed with the **app's API secret** (NOT the access token)
using HMAC-SHA256 over the raw request body, base64-encoded, sent in
`X-Shopify-Hmac-Sha256`. This is the verification mechanism — there is no
mTLS, no JWT, no IP allowlist.

```python
import hmac, hashlib, base64
def verify(raw: bytes, header: str, secret: bytes) -> bool:
    digest = hmac.new(secret, raw, hashlib.sha256).digest()
    return hmac.compare_digest(base64.b64encode(digest).decode(), header)
```

For EventBridge / Pub/Sub delivery, signing is replaced by the cloud
provider's IAM trust — no HMAC.

## Core Operations with Exact Signatures

All examples use Admin GraphQL 2026-04 unless noted. REST is intentionally
omitted — it is legacy.

### Endpoint

```
POST https://{shop}.myshopify.com/admin/api/{version}/graphql.json
Headers:
  X-Shopify-Access-Token: shpat_…
  Content-Type: application/json
  Shopify-GraphQL-Cost-Debug: 1   (optional, returns per-field cost)
Body: {"query": "...", "variables": {...}}
```

### Products

```graphql
# READ — single product by handle
query ProductByHandle($handle: String!) {
  productByHandle(handle: $handle) {
    id title descriptionHtml status vendor productType tags
    options { id name values }
    variants(first: 100) {
      edges { node { id sku title price compareAtPrice
                     inventoryQuantity barcode weight weightUnit
                     selectedOptions { name value } } }
    }
    media(first: 20) { edges { node { mediaContentType alt
      ... on MediaImage { image { url width height } } } } }
    metafields(first: 50) { edges { node { namespace key value type } } }
    seo { title description }
  }
}

# CREATE
mutation ProductCreate($input: ProductInput!, $media: [CreateMediaInput!]) {
  productCreate(input: $input, media: $media) {
    product { id handle }
    userErrors { field message code }
  }
}

# UPDATE
mutation ProductUpdate($input: ProductInput!) {
  productUpdate(input: $input) {
    product { id updatedAt }
    userErrors { field message }
  }
}

# DELETE
mutation ProductDelete($input: ProductDeleteInput!) {
  productDelete(input: $input) {
    deletedProductId
    userErrors { field message }
  }
}
```

### Variants (bulk pattern)

```graphql
mutation ProductVariantsBulkCreate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
  productVariantsBulkCreate(productId: $productId, variants: $variants) {
    productVariants { id sku }
    userErrors { field message }
  }
}
```

Use `productVariantsBulkUpdate` / `productVariantsBulkDelete` for the same.
Single-variant mutations are deprecated — bulk is the only supported path
since 2024-04.

### Orders

```graphql
query OrdersRecent($first: Int!, $query: String) {
  orders(first: $first, query: $query, sortKey: CREATED_AT, reverse: true) {
    edges {
      node {
        id name createdAt processedAt displayFulfillmentStatus
        displayFinancialStatus
        currentTotalPriceSet { shopMoney { amount currencyCode } }
        customer { id email displayName numberOfOrders }
        shippingAddress { address1 city province country zip }
        lineItems(first: 50) {
          edges { node { title sku quantity
                         originalUnitPriceSet { shopMoney { amount } } } }
        }
        fulfillments { id status trackingInfo { number url company } }
      }
    }
    pageInfo { hasNextPage endCursor }
  }
}
```

Search syntax: `created_at:>=2026-01-01 financial_status:paid -tag:test`.
The `query` argument uses Shopify's search query language (same as the admin
search bar). Date filters accept ISO 8601 and relative tokens.

### Inventory

```graphql
mutation InventoryAdjustQuantities($input: InventoryAdjustQuantitiesInput!) {
  inventoryAdjustQuantities(input: $input) {
    inventoryAdjustmentGroup { createdAt reason referenceDocumentUri
      changes { name delta quantityAfterChange location { id name } } }
    userErrors { field message code }
  }
}
```

Variables:
```json
{
  "input": {
    "reason": "correction",
    "name": "available",
    "referenceDocumentUri": "logistics://eos/restock/2026-04-06",
    "changes": [
      {"inventoryItemId": "gid://shopify/InventoryItem/123",
       "locationId": "gid://shopify/Location/456",
       "delta": 24}
    ]
  }
}
```

`name` is `available` (sellable), `incoming`, `committed`, `damaged`, etc.
Each location has independent quantity. The `reason` enum is required.

### Customers

```graphql
mutation CustomerCreate($input: CustomerInput!) {
  customerCreate(input: $input) {
    customer { id email tags }
    userErrors { field message }
  }
}

query Customer($id: ID!) {
  customer(id: $id) {
    id email firstName lastName phone numberOfOrders
    amountSpent { amount currencyCode }
    defaultAddress { address1 city }
    metafields(first: 20) { edges { node { namespace key value } } }
  }
}
```

### Fulfillments

```graphql
mutation FulfillmentCreate($fulfillment: FulfillmentInput!) {
  fulfillmentCreate(fulfillment: $fulfillment) {
    fulfillment { id status trackingInfo { number company url } }
    userErrors { field message }
  }
}
```

Fulfillments are created against a `fulfillmentOrder` (the work order
representing a shippable group), not directly against an `order`. Fetch
`order { fulfillmentOrders(first: 10) { edges { node { id assignedLocation
{ name } lineItems(first: 50) { edges { node { id remainingQuantity } } }
} } } }` first.

### Discounts

```graphql
mutation DiscountCodeBasicCreate($basicCodeDiscount: DiscountCodeBasicInput!) {
  discountCodeBasicCreate(basicCodeDiscount: $basicCodeDiscount) {
    codeDiscountNode { id }
    userErrors { field message }
  }
}
```

Code discounts are entitlement+value+combinesWith trees. Automatic discounts
use `discountAutomaticBasicCreate`. Function-backed discounts use
`discountAutomaticAppCreate` and reference a deployed Function.

### Metafields and Metaobjects

```graphql
mutation MetafieldsSet($metafields: [MetafieldsSetInput!]!) {
  metafieldsSet(metafields: $metafields) {
    metafields { id namespace key value }
    userErrors { field message code }
  }
}

mutation MetaobjectCreate($metaobject: MetaobjectCreateInput!) {
  metaobjectCreate(metaobject: $metaobject) {
    metaobject { id type handle fields { key value } }
    userErrors { field message code }
  }
}
```

Metafields attach typed custom data to existing resources (Product, Variant,
Customer, Order, etc). Metaobjects are first-class custom entities — use
them for content-modeled data like lookbooks, drop campaigns, color
palettes.

## Pagination Patterns

Shopify GraphQL uses Relay-spec connection pagination. Two modes:

### Forward cursor pagination (standard)

```graphql
query Page($after: String) {
  products(first: 50, after: $after, query: "status:active") {
    edges { cursor node { id title } }
    pageInfo { hasNextPage endCursor }
  }
}
```

Loop until `pageInfo.hasNextPage == false`, passing the previous
`endCursor` as `after`. Never use `last`/`before` for forward iteration —
they exist for reverse pagination only and have different cost.

### Bulk Operations (the right way to export everything)

```graphql
mutation {
  bulkOperationRunQuery(query: """
    { products { edges { node { id handle variants { edges { node {
        id sku inventoryQuantity } } } } } } }
  """) {
    bulkOperation { id status }
    userErrors { field message }
  }
}
```

Then poll:
```graphql
{ currentBulkOperation { id status errorCode createdAt completedAt
  objectCount fileSize url partialDataUrl } }
```

When `status == COMPLETED`, download the JSONL from `url` (a 60-second
pre-signed Google Storage URL). Each line is one node; nested connections
appear as additional lines with `__parentId`. Bulk operations:
- Bypass query cost throttling entirely
- One per shop at a time (`ALREADY_RUNNING` if you start a second)
- Cannot use `first`/`after` arguments inside the query
- Cannot use Mutations — use `bulkOperationRunMutation` for write bulk

For writes: `bulkOperationRunMutation` takes a JSONL `stagedUploadUrl` of
input rows and a mutation template, then runs each row through the
mutation. The right pattern for "import 10,000 products."

## Rate Limits

Three rate-limit regimes — pick by API surface.

### Admin GraphQL — calculated query cost (leaky bucket)

- Bucket size: **1000 points** (Standard, Shopify, Advanced) /
  **2000 points** (Plus) / **10,000 points** (Commerce Components / enterprise)
- Restore rate: **50 points/sec** (Standard) / **100/sec** (Plus) /
  **500/sec** (Commerce Components)
- Single query max cost: 1000 points (regardless of plan), even on Plus
- Cost calculation:
  - Scalar fields: 0 points
  - Object fields: 1 point
  - Connections: `2 + (returned_node_count)` points (multiplied by parent cardinality)
  - Mutations: `10 + standard cost` minimum
  - Interface types: counted at the worst-case branch
- `extensions.cost` returns `requestedQueryCost`, `actualQueryCost`,
  `throttleStatus.{maximumAvailable, currentlyAvailable, restoreRate}`
- Throttling: HTTP 200 with `errors[0].extensions.code == "THROTTLED"`,
  NOT HTTP 429 — you must check the body, not the status code

The right backoff is to read `currentlyAvailable` and `restoreRate` from
the previous response and sleep
`max(0, (next_query_cost - currently_available) / restore_rate)`.

### Admin REST — request count leaky bucket (legacy)

- 40 requests bucket, leak 2/sec (Standard)
- 80 / 4 (Plus)
- 429 returned when exhausted, with `Retry-After: 2.0` header
- `X-Shopify-Shop-Api-Call-Limit: 32/40` header on every response
- Listed for completeness only — do not write new code against REST

### Storefront API

- Per-IP, per-minute, unauthenticated
- Specific limit not publicly documented but ~1000 req/min/IP for
  storefront access tokens; bursts up to ~60/sec; throttling returns
  HTTP 430 (yes, 430)
- Hydrogen sites cache aggressively at the Oxygen edge to stay under

## Error Codes and Recovery

GraphQL errors are layered. Always check both layers.

### Top-level `errors` array (transport-level)

```json
{"errors": [
  {"message": "Throttled",
   "extensions": {"code": "THROTTLED",
     "documentation": "https://shopify.dev/api/usage/rate-limits"}}
]}
```

Common codes:
- `THROTTLED` — query cost exhausted; back off and retry with `restoreRate`
- `MAX_COST_EXCEEDED` — single query > 1000 points; redesign query to
  paginate connections; not retryable as-is
- `ACCESS_DENIED` — missing scope; reinstall app with new scope
- `SHOP_INACTIVE` — store frozen, on pause, or fraud-locked
- `INTERNAL_SERVER_ERROR` — Shopify-side; retry with exponential backoff
- `unauthorized` (HTTP 401) — bad/expired token
- `Not Found` (HTTP 404) — bad shop subdomain or deprecated API version

### Mutation `userErrors` (business-level)

```json
{"data": {"productCreate": {
  "product": null,
  "userErrors": [
    {"field": ["input", "handle"],
     "message": "Handle is already taken",
     "code": "TAKEN"}
  ]
}}}
```

Always check `userErrors.length == 0` before treating a mutation as
successful. `userErrors` is HTTP 200 — your error handling will silently
swallow validation failures if you only check the HTTP status.

Common userError codes: `TAKEN`, `INVALID`, `BLANK`, `TOO_LONG`,
`PRODUCT_DOES_NOT_EXIST`, `INVENTORY_ITEM_NOT_FOUND`, `LOCATION_NOT_ACTIVE`.

### Webhook delivery errors

Shopify retries failed webhooks (non-2xx response, timeout >5s) up to
**19 times** over **48 hours** with exponential backoff. After 19 failures
the webhook subscription is automatically removed and an email is sent to
the app owner. Recovery: re-register the webhook via
`webhookSubscriptionCreate` and backfill missed events from the Admin API.

## SDK Idioms

### Node — `@shopify/shopify-api` 11.x

```javascript
import {shopifyApi, ApiVersion, LATEST_API_VERSION} from '@shopify/shopify-api';
import '@shopify/shopify-api/adapters/node';

const shopify = shopifyApi({
  apiKey: process.env.SHOPIFY_API_KEY,
  apiSecretKey: process.env.SHOPIFY_API_SECRET,
  scopes: ['read_products', 'write_orders'],
  hostName: 'lyfe-spectrum.myshopify.com',
  apiVersion: ApiVersion.April26,    // or LATEST_API_VERSION
  isEmbeddedApp: false,
});

const session = shopify.session.customAppSession('lyfe-spectrum.myshopify.com');
session.accessToken = process.env.SHOPIFY_ADMIN_TOKEN;

const client = new shopify.clients.Graphql({session});
const res = await client.query({
  data: {query: `{ shop { name } }`},
});
console.log(res.body.data);
```

### Python — direct requests (recommended for EOS)

The official `shopify-python-api` (`ShopifyAPI/shopify_python_api`) wraps
REST primarily and is showing its age. For GraphQL workloads in EOS, use
`requests` directly with the helper from SKILL.md. It's 30 lines and
sidesteps the SDK's REST baggage.

```python
class ShopifyClient:
    def __init__(self, shop: str, token: str, version: str = "2026-04"):
        self.url = f"https://{shop}/admin/api/{version}/graphql.json"
        self.session = requests.Session()
        self.session.headers.update({
            "X-Shopify-Access-Token": token,
            "Content-Type": "application/json",
        })

    def gql(self, query: str, variables: dict | None = None,
            cost_debug: bool = False) -> dict:
        headers = {"Shopify-GraphQL-Cost-Debug": "1"} if cost_debug else {}
        for attempt in range(5):
            r = self.session.post(self.url, headers=headers,
                json={"query": query, "variables": variables or {}}, timeout=30)
            body = r.json()
            errs = body.get("errors") or []
            if errs and errs[0].get("extensions", {}).get("code") == "THROTTLED":
                cost = body["extensions"]["cost"]
                wait = (cost["requestedQueryCost"] -
                        cost["throttleStatus"]["currentlyAvailable"]) \
                       / cost["throttleStatus"]["restoreRate"]
                time.sleep(max(0.5, wait))
                continue
            if errs:
                raise RuntimeError(errs)
            return body
        raise RuntimeError("throttled after 5 retries")
```

### Ruby — `shopify_api` 14.x

The "first-class" SDK; powers the Rails reference app. Uses
`ShopifyAPI::Context.activate_session(session)` then
`ShopifyAPI::Clients::Graphql::Admin.new(session: session).query(query: ...)`.
Mostly relevant if maintaining a Rails-based Shopify app.

### CLI

```bash
# Install
npm install -g @shopify/cli @shopify/theme

# Theme dev with hot reload
shopify theme dev --store lyfe-spectrum

# App scaffold
shopify app init

# Function scaffold
shopify app generate extension --type=product_discounts --template=rust

# Deploy app + functions + extensions
shopify app deploy
```

The CLI is the only blessed way to develop Functions and Theme Extensions —
attempting to write Wasm modules by hand is unsupported.

## Anti-Patterns

- **REST for new code.** REST Admin is in long-tail deprecation. Every
  resource will eventually be GraphQL-only. Don't invest in REST clients
  for code being written today.
- **Unbounded `first: 250`.** The hard limit is 250 nodes per connection,
  but the cost ceiling will throttle you long before then for nested
  connections. Use 50 + cursor pagination.
- **Polling instead of webhooks.** "Get new orders every minute" wastes
  the entire query cost bucket. Subscribe to `orders/create` webhook +
  `orders/updated`, store cursor, reconcile nightly.
- **One mutation per node.** Bulk mutate. `productVariantsBulkCreate`
  takes 100 variants in one call at the cost of one mutation, not 100.
- **No retry on THROTTLED.** Throttling is normal, not exceptional.
  Every client must handle it.
- **Storing GIDs as integers.** `gid://shopify/Product/123` is opaque.
  Strip the prefix only at the very edge if a downstream system requires
  the numeric ID; never use the numeric form internally.
- **Theme code calling Admin API.** Themes are public. Embedding an admin
  token in Liquid leaks it to every visitor. Use the Storefront API or
  proxy through your app.
- **Mutating from a webhook handler synchronously.** Webhooks have a 5s
  timeout. Push to a queue (SQS, Pub/Sub, Redis) and 200 immediately.
- **Skipping `userErrors`.** A successful HTTP 200 with empty
  `data.productCreate.product` and a `userErrors` payload is a failure.
- **Hard-coded API version `latest`.** Never deploy with `latest`. Pin a
  date string and migrate intentionally.
- **Reading `metafield` by `key` without `namespace`.** Two apps, same
  key, different namespaces, silent collision. Always include namespace.
- **Storing customer PII in metafields.** Metafields are not GDPR-aware
  and don't get included in customer redaction webhooks. Use customer
  fields or a side store with proper redaction handling.

## Data Model

### Resource hierarchy (admin domain)

```
Shop
├── Locations (multi-location inventory)
├── Products
│   ├── Options (size, color)
│   ├── Variants
│   │   └── InventoryItem ─┐
│   └── Media               │
├── InventoryLevels         │ — many-to-many: InventoryItem × Location
│   └── available, incoming, committed, reserved, damaged, safety_stock
├── Collections (manual or smart, rule-based)
├── Customers
│   ├── Addresses
│   ├── Orders
│   └── Companies (B2B)
├── Orders
│   ├── LineItems → ProductVariant
│   ├── ShippingLines
│   ├── Transactions
│   ├── Fulfillments
│   └── FulfillmentOrders → assignedLocation
├── DraftOrders (admin-created carts)
├── Discounts (code, automatic, app)
├── PriceLists (B2B, market-specific)
├── Markets (region/currency configuration)
├── Metaobjects (custom typed entities)
└── Files (uploads, images, videos, generic files)
```

### Storefront vs Admin domain split

The Storefront API exposes a **buyer-safe** projection of the same data:
`product`, `productByHandle`, `collection`, `cart`, `checkoutCreate`,
plus the shop's `localization` (markets, languages, currencies). It does
NOT expose: orders, customer PII (without buyer auth), inventory across
locations, financial data, fulfillment, or admin-only metafields.

The Customer Account API (formerly Customer API) lets logged-in buyers
read their own orders and update their own profile via a separate OAuth
flow.

### Identifiers

- **GID** (Global ID): `gid://shopify/{Type}/{numeric}`. Used everywhere
  in GraphQL. Opaque — treat as a string.
- **Handle**: URL-safe slug. Stable for products and collections, used in
  storefront URLs. Unique within type.
- **Legacy ID**: bare numeric, used in REST URLs. Convert via
  `node(id: "gid://...") { id ... on Product { legacyResourceId } }`.

### Money

Money is always returned as a `MoneyV2` `{ amount: Decimal!, currencyCode }`
or paired in a `MoneyBag` `{ shopMoney, presentmentMoney }` for stores
with multi-currency. Always read both — `presentmentMoney` is what the
buyer saw, `shopMoney` is what hits your books.

## Webhooks and Events

### Subscription model

Webhooks are subscribed per-app. Two delivery methods:

- **HTTPS (default)** — POST to your URL with HMAC-SHA256 signature
- **EventBridge / Pub/Sub** — direct push to AWS or Google Cloud, no HMAC
  (cloud IAM trust)

Subscribe via mutation:

```graphql
mutation WebhookSubscriptionCreate($topic: WebhookSubscriptionTopic!,
                                    $webhookSubscription: WebhookSubscriptionInput!) {
  webhookSubscriptionCreate(topic: $topic, webhookSubscription: $webhookSubscription) {
    webhookSubscription { id endpoint { __typename ... on WebhookHttpEndpoint { callbackUrl } } }
    userErrors { field message }
  }
}
```

Or declaratively in `shopify.app.toml` for embedded apps (preferred since
2024 — survives reinstalls and is checked into the repo).

### Key topics

- `PRODUCTS_CREATE`, `PRODUCTS_UPDATE`, `PRODUCTS_DELETE`
- `ORDERS_CREATE`, `ORDERS_UPDATED`, `ORDERS_PAID`, `ORDERS_CANCELLED`,
  `ORDERS_FULFILLED`, `ORDERS_PARTIALLY_FULFILLED`, `ORDERS_REFUNDED`
- `CUSTOMERS_CREATE`, `CUSTOMERS_UPDATE`, `CUSTOMERS_DELETE`,
  `CUSTOMERS_DATA_REQUEST`, `CUSTOMERS_REDACT` (GDPR)
- `INVENTORY_LEVELS_UPDATE`, `INVENTORY_ITEMS_UPDATE`
- `FULFILLMENTS_CREATE`, `FULFILLMENTS_UPDATE`
- `APP_UNINSTALLED` — MUST handle to clean up your DB
- `SHOP_REDACT` — GDPR shop data deletion 48h after uninstall
- `BULK_OPERATIONS_FINISH` — your bulk export is ready

### Mandatory GDPR webhooks

Public apps MUST implement and respond to:
1. `customers/data_request` — within 30 days, return all data you hold
   on the customer
2. `customers/redact` — within 30 days, delete the customer's data
3. `shop/redact` — 48h after uninstall, delete all shop data

Failure to handle these is grounds for App Store removal.

### Headers on every webhook

- `X-Shopify-Topic` — e.g. `orders/create`
- `X-Shopify-Hmac-Sha256` — HMAC of raw body with API secret
- `X-Shopify-Shop-Domain` — `lyfe-spectrum.myshopify.com`
- `X-Shopify-API-Version` — version the payload was serialized at
- `X-Shopify-Webhook-Id` — unique per delivery (use for idempotency)
- `X-Shopify-Triggered-At` — when the event happened in Shopify

### Idempotency

Shopify can deliver the same webhook more than once (network retries,
infrastructure events). Always dedupe on `X-Shopify-Webhook-Id`. Store
seen IDs for 48h.

## Limits

- **GraphQL query max cost**: 1000 points (single query)
- **GraphQL bucket**: 1000 (Standard) / 2000 (Plus) points
- **Connection page size**: 250 nodes max (`first: 250`)
- **Bulk operations**: 1 concurrent per shop
- **Mutation minimum cost**: 10 points
- **Webhook payload max**: 1 MB
- **Webhook timeout**: 5 seconds (return 2xx within 5s or it counts as failed)
- **Webhook retries**: 19 attempts over 48 hours
- **Webhook subscription max**: 1000 per shop per app
- **File upload max**: 20 MB per file (images), 1 GB per video
- **Product max variants**: 2,048 (since 2024-04, was 100 before)
- **Product max options**: 3
- **Product max images**: 250
- **Tag max length**: 255 chars; max tags per resource: 250
- **Metafield value max**: 1 MB (JSON), 5 MB (file_reference references)
- **Metafield key/namespace**: 3-64 chars, alphanumeric + underscore
- **Order line items max**: 500 per order
- **Discount codes per discount**: 100 (single-use codes can use bulk
  generation up to 100k via `discountCodeBulkAdd`)
- **Theme file max**: 256 KB per Liquid file; 100 sections per template
- **Customer accounts per store**: unlimited
- **Storefront API GraphQL response size**: ~10 MB
- **API version support window**: 12 months minimum, 9 months overlap
- **App charge max**: $1,000,000 USD per merchant per 30 days

## Cost Model

### Merchant pricing (your store)

- **Basic**: $39/mo — 2% transaction fee on non-Shopify-Payments,
  online store + POS Lite
- **Shopify**: $105/mo — 1% non-SP fee, 5 staff accounts
- **Advanced**: $399/mo — 0.5% non-SP fee, advanced reports
- **Plus**: $2,000+/mo (variable rate at $4M+ revenue) — Functions, B2B,
  Checkout Extensibility full access, Flow advanced, 100 staff,
  9 expansion stores, custom checkout, Hydrogen + Oxygen included
- **Commerce Components**: enterprise, custom, $$$

Shopify Payments rate: 2.4% + 30¢ (Basic) → 2.7% + 30¢ in person, scales
down to 2.4% + 30¢ (Advanced), card-not-present transactions 0.6% lower
on Plus. International cards +1.5%.

### Developer cost

- **Custom apps**: free
- **Public apps**: free to build, Shopify takes 0% commission on first
  $1M of app revenue, 15% above (changed 2021). App charges billed
  through Shopify Billing API.
- **Shopify Functions**: free to deploy; included in Plus, available
  on lower tiers with limits (e.g. discount Functions on all plans
  since 2024)
- **Hydrogen + Oxygen**: free hosting for Plus stores; non-Plus pay for
  Oxygen via separate plan

### API cost

- **Admin API**: free; throttled by query cost
- **Storefront API**: free; rate limited per IP
- **Bulk operations**: free; 1 concurrent
- **Webhook delivery**: free; 19 retries

## Version Pinning

API versions are date strings: `YYYY-MM`, released **quarterly** on the
first day of January, April, July, October.

### Stability guarantees

- Each version is supported for **12 months minimum**
- Versions overlap by **9 months** (so you have a 9-month migration window
  whenever you upgrade)
- Within a stable version, breaking changes are NEVER introduced
- Within a release candidate (`unstable`), anything can change
- New fields can appear in any version (additive)
- Deprecation warnings appear in `extensions.deprecations` on every query
  that touches a deprecated field — log these in CI

### Pinning rules

```
GOOD: /admin/api/2026-04/graphql.json
BAD:  /admin/api/unstable/graphql.json     # only for active development
BAD:  /admin/api/2024-04/graphql.json      # past sunset → 404
```

The header version `X-Shopify-API-Version` returned in a webhook tells
you which version Shopify used to serialize the payload. If you pin your
client to 2026-04 and a webhook arrives serialized in 2025-10, your code
must handle the older shape OR you re-create the webhook subscription
with `apiVersion: "2026-04"` to force resubscription on the new version.

### Migration discipline

1. Read the release notes on `shopify.dev/docs/api/release-notes/{version}`
2. Run the `apiVersion` query against the new version in staging:
   `{ shop { name } }` — verifies the endpoint is alive
3. Run your existing query suite under the new version, capturing any
   `extensions.deprecations`
4. Update queries that use deprecated fields
5. Bump the pinned version in one PR; deploy
6. Re-register webhooks with the new `apiVersion`
7. Calendar reminder for the sunset date (12 months later)

Skipping a quarterly migration is fine — you have 4 quarters to act.
Skipping all four is an outage.

---

# Tier 2 — Strategic Mastery

## Design Intent and Tradeoffs

Shopify's founding thesis (Tobi Lütke, 2006) is **"make commerce better
for everyone"** by collapsing the distance between an entrepreneur having
an idea and that idea being a transactable product on the internet. Every
architectural choice flows from this:

- **Hosted, opinionated stack** — you don't run servers, configure SSL,
  or manage payment compliance. The tradeoff: you accept Shopify's data
  model and extension surfaces. You cannot, e.g., write a custom Postgres
  schema for your products.
- **Liquid as the templating language** (created at Shopify, now its own
  open-source project) — server-rendered, sandboxed, designer-friendly.
  Tradeoff: no arbitrary code in themes. Logic that needs Turing
  completeness goes into apps or Functions.
- **Webhooks + GraphQL over WebSocket-first** — Shopify chose a pull/push
  hybrid over real-time subscriptions because merchants integrate with
  legacy systems (ERPs, POS, accounting) that batch-process events.
- **Functions over Scripts (2024 sunset)** — Scripts were Ruby, ran in a
  proprietary sandbox, only available on Plus. Functions are Wasm, run
  in Rust/JS, available on all plans for some types, run at the edge.
  Tradeoff: more complex DX, but vastly more portable and secure.
- **Checkout Extensibility over checkout.liquid** (2024 sunset of
  checkout.liquid for Plus) — the legacy approach allowed full Liquid
  customization of checkout, which produced a maintenance and security
  nightmare. The new model uses Checkout UI Extensions (declarative
  React components rendered in iframes) + Functions for logic. Tradeoff:
  less freedom, vastly higher conversion safety.
- **Multi-location by default** — since 2018, every store has at least
  one location and inventory is per-location. Single-location stores are
  a degenerate case, not the primary model. Tradeoff: every inventory
  query needs a `locationId`.
- **GraphQL over REST as canonical** — because the catalog graph
  (Product → Variants → InventoryItem → InventoryLevels → Location) is
  inherently graph-shaped, and REST forced N+1 round trips. Tradeoff:
  query cost economy is harder for new developers than counting requests.

What Shopify is NOT trying to be: a self-hosted platform (that's
WooCommerce), an enterprise composable suite (that's commercetools), a
website builder with commerce bolted on (that's Wix/Squarespace), or a
marketplace (that's Amazon Seller). When you find yourself fighting the
platform, check whether you're trying to make it be one of those things.

## Problem-Solution Map and Hidden Capabilities

| Problem | Wrong solution | Right solution |
|---|---|---|
| "Show different prices to wholesale customers" | Two products | B2B + Catalogs (price lists per Company Location) |
| "Custom field on products" | Hidden tags | Metafield with definition |
| "Custom entity (e.g., lookbook)" | Custom database | Metaobject |
| "Discount $5 off when 3 tees in cart" | Theme JS | Function (product discount) |
| "Block checkout if shipping to Hawaii" | Theme JS | Function (delivery customization) |
| "Add gift wrap option to checkout" | Liquid hack | Checkout UI Extension |
| "Send order to fulfillment partner" | Polling | Webhook + fulfillment service app |
| "Subscribe customer to email" | Custom form | Klaviyo native integration |
| "Tag orders by customer cohort" | Manual | Shopify Flow |
| "Bulk update 5,000 prices" | Loop of mutations | bulkOperationRunMutation |
| "Multi-currency" | Multiple stores | Markets |
| "Multi-region SKUs" | Multiple stores | Markets + per-market product publication |
| "Track abandoned carts" | Custom JS | Abandoned Checkouts API + Klaviyo |
| "Show stock level on PDP" | Theme polling | Liquid `{{ product.variants.first.inventory_quantity }}` (already exposed) |
| "Custom checkout logic" | checkout.liquid | Functions + Checkout UI Extensions |

### Hidden capabilities you'd never find without reading source

- **Metaobject Definitions can be referenced as fields on other resources**
  via the `metaobject_reference` metafield type. Build relational data
  inside Shopify without an external DB.
- **Shopify Flow** runs entirely server-side, can call your webhook URLs,
  HTTP request actions, and call your custom app's actions. Can replace
  90% of "I need to do X when Y happens" automation requests without
  shipping any code.
- **Hydrogen's `createStorefrontClient`** automatically generates a
  query cache key from the GraphQL document, so identical queries from
  different React Server Components dedupe at the edge.
- **`@inContext(country: US, language: EN)`** directive on Storefront
  queries pulls market-specific pricing, currency, and translations
  in one query.
- **Bulk operations support fragments**, so you can keep your normal
  query files and re-use them in bulk mode.
- **`tags` on Product/Customer/Order are queryable** via the search
  query language: `tag:vip` or `-tag:test`. Use tags as cheap indexed
  labels for cohorts.
- **Draft orders** can be converted to invoices and sent to customers;
  the customer pays at a hosted URL. The right way to handle quotes,
  custom orders, B2B one-offs without leaving Shopify.
- **`customerSegmentMembersQuery`** lets you query customers by
  segment (e.g., "spent >$500 last 90 days") via GraphQL — the same
  segment language as the admin's Customers tab.
- **Shopify Functions can target specific products, collections, or
  customer segments** via the `targets` declaration in the function's
  config — no runtime conditional needed.
- **Pixels API** lets you write privacy-aware tracking pixels that run
  in a sandbox with explicit consent gates, replacing Tag Manager for
  GA4/Meta tracking. Required since 2024 for any new tracking.
- **App proxies** route public URLs (`/apps/your-app/...`) on the
  storefront domain through your app server with HMAC signing — the
  right way to expose app endpoints from a public storefront.

## Operational Behavior and Edge Cases

- **Inventory commits at order creation**, not at fulfillment. If a
  customer places an order, the variant's `available` drops by the
  ordered quantity and `committed` rises. Cancellations restock.
  Refunds with `restock: true` restock; without, do not.
- **Order numbers (`name`)** start at `#1001` by default, but the
  numeric part is allocated at creation time, not at payment. Test
  orders increment the counter — there are gaps in production.
- **Order edits** create a new "order edit" object that mutates line
  items and totals; the original is preserved in the audit log. Webhook
  consumers must handle `orders/updated` and re-read the full order.
- **Fulfillment service apps** are a special class of app: Shopify treats
  the app as the location for inventory and routes fulfillment requests
  to it. Required for 3PL integrations.
- **Draft orders bypass discounts and inventory checks** — they are
  manual carts. Do not rely on draft order behavior to test customer-
  facing discount rules.
- **Customer email is not unique** by default in Shopify — two customers
  can have the same email if they were imported from different sources.
  The `customers` connection's email filter returns multiple matches.
- **Markets and currency**: a product's price in `priceRangeV2` is in the
  shop's primary currency. Use `@inContext(country: ...)` to get the
  buyer's local price including market overrides.
- **Soft-deleted products** linger in some queries for 30 days then
  vanish. Hard delete via `productDelete` is irreversible.
- **App uninstalled state**: when a merchant uninstalls your app, your
  webhooks stop firing immediately. The `app/uninstalled` webhook is
  best-effort — sometimes it doesn't fire at all (e.g., if the merchant
  closes their store entirely). You must reconcile via periodic
  "is my app still installed?" checks.
- **The Plus admin has `superuser` features** (e.g., wholesale channel,
  scripts editor in legacy stores) that don't exist on lower plans —
  if a workflow only works for the merchant in admin, check what plan
  they're on.
- **Theme inspector and Lighthouse audits** are run automatically on
  theme changes; large performance regressions can block theme
  publishing on Plus.
- **Liquid is render-time only**. There is no Liquid in customer emails
  except via the Notifications template editor, and that uses a slightly
  different Liquid dialect with different available variables.
- **Checkout has three eras**: legacy `checkout.liquid` (deprecated, gone
  for Plus 2024-08, gone for everyone 2025-08), Checkout Extensibility
  era (current), and the upcoming One Page Checkout (default 2024+).
  Code from each era is mostly incompatible.

## Ecosystem Position and Composition

### Direct competitors

- **WooCommerce** (Automattic, WordPress plugin) — self-hosted, infinite
  flexibility, you own infrastructure. Shopify wins on operational
  burden and conversion polish; Woo wins on customization and zero
  recurring fees. Used by Lyfe Spectrum? No — too much operational
  overhead for a solo founder.
- **BigCommerce** — closest 1:1 alternative; stronger headless story
  pre-Hydrogen. Shopify won the developer ecosystem by ~5x.
- **Magento / Adobe Commerce** — enterprise, PHP, on-prem or Adobe-hosted.
  Outclassed by Shopify Plus on TCO and time-to-launch for under-$50M
  brands.
- **Squarespace Commerce / Wix / Webflow Ecommerce** — website builders
  with commerce as a feature. Win on initial design freedom; lose on
  scale, app ecosystem, multi-channel.
- **commercetools / Saleor / Medusa** — composable/headless-first.
  Win on developer freedom; lose on out-of-box completeness.
- **Amazon Seller** — different business model entirely. Marketplace
  vs DTC. Many brands run both (Shopify for brand/DTC, Amazon for
  reach/volume).
- **Stripe Atlas + Stripe Checkout** — Stripe is now circling commerce
  with Stripe Tax, Radar, Atlas, Sigma. Not a direct competitor yet but
  the moats overlap.

### Composition partners (the Shopify app stack Lyfe Spectrum likely needs)

- **Klaviyo** — email + SMS. Native integration, syncs customers, orders,
  product views, abandoned carts. The default for DTC over $10K/mo.
- **Loox / Judge.me** — product reviews with photo + video. Loox is
  the design-forward choice for tactical-luxury brands.
- **Gorgias** — customer support helpdesk with native Shopify order
  context in every ticket.
- **Shipstation / ShipBob / EasyPost** — fulfillment + shipping label
  printing. Shipstation for self-fulfillment, ShipBob for 3PL.
- **Rewind** — daily backup of products, themes, settings. Insurance
  against bad imports. $9-39/mo, indispensable.
- **Shopify Shipping** — built-in carrier rates (USPS, UPS, DHL, Canada
  Post) discounted by Shopify volume. Use unless ShipBob or 3PL handles it.
- **Recharge / Bold Subscriptions** — subscription billing for recurring
  products. Shopify Subscriptions native is also viable for simple cases.
- **Bundles & Upsell apps** — Rebuy, Bold Bundles, Shopify Bundles
  (native, free, simpler).
- **Tapcart / Shop app** — mobile app generation. Shop app is free and
  Shopify-built.
- **Hydrogen + Oxygen** — Shopify's own headless React framework + edge
  hosting. Use when conversion data justifies the build cost.
- **Shopify Audiences** (Plus only) — first-party audience signals for
  Meta/Google ad targeting, derived from cross-merchant Plus data.

### Where Shopify sits in the data flow

```
Inbound:
  Merchant catalog → Shopify Admin → Admin DB
  Buyer browse → Storefront / Theme / Hydrogen → Shopify CDN
  Buyer checkout → Shop Pay / Shopify Payments → Payment processor
  Buyer cart → Cart API → Order
Outbound:
  Webhooks → Customer code, Klaviyo, ShipStation, Gorgias, EOS
  Bulk exports → Custom analytics, accounting
  Pixels → GA4, Meta, TikTok (consent-gated)
  Hydrogen RSC → Oxygen edge → Buyer browser
```

## Trajectory and Evolution

Watching Shopify's roadmap:

- **2024-2025: REST sunset acceleration.** Each quarterly release removes
  more REST resources. New apps must be GraphQL-first.
- **Functions everywhere.** Functions started as "discount only" (2022),
  expanded to delivery customization, payment customization, cart
  validation (2023), checkout validation (2024). The trajectory is
  Functions for every behavioral extension point.
- **Checkout Extensibility universal.** checkout.liquid for Plus sunsets
  2024-08, for all stores 2025-08. By 2026, every store is on the new
  checkout. UI Extensions are React-only going forward.
- **Hydrogen + Oxygen as first-class headless.** Shopify acquired Remix
  (2022), bet Hydrogen on React Server Components, integrated tightly
  with Oxygen. Headless is no longer a "you're on your own" path —
  it's a supported product.
- **Sidekick (AI assistant in admin)** + **Magic (AI product copy,
  image generation)** rolled out 2023-2024. Shopify is investing
  heavily in AI for merchants; expect more in admin and developer
  surfaces (e.g., AI-suggested Functions).
- **Shop Pay Installments** (BNPL via Affirm) is now the default
  installment option in checkout. Conversion lift on tactical-luxury
  apparel is meaningful.
- **B2B convergence.** B2B features that used to be Plus-only (Companies,
  Catalogs, NET payment terms) are spreading down to Advanced.
- **Markets Pro** (managed merchant of record for international sales)
  is in expansion — Shopify acts as the legal seller in foreign markets,
  handling tax, duties, fraud. Reduces cross-border friction massively.
- **Shop app as a marketplace play.** The Shop app started as
  order-tracking and is becoming a discovery channel (Shop Cash rewards,
  Shop AI, personalized feeds). Eventually a Shopify-flavored Amazon.
- **Edge-everywhere.** Oxygen, Pixels, Functions all run at the edge.
  The Shopify mental model is increasingly "your code runs near the
  buyer, not in your datacenter."

What this means for Lyfe Spectrum: build on GraphQL Admin + Functions +
Checkout Extensibility from day one. Plan for a Hydrogen migration if
the brand outgrows the OS 2.0 theme stack. Use Markets for international
expansion before considering a second store.

## Conceptual Model and Solution Recipes

### Recipe 1: Daily order sync into EOS

```python
# Run nightly via cron / orchestrator
def sync_orders_since(cursor_iso: str) -> tuple[list[dict], str]:
    query = """
    query($q: String!, $after: String) {
      orders(first: 100, after: $after, query: $q,
             sortKey: UPDATED_AT, reverse: false) {
        edges { cursor node {
          id name updatedAt processedAt displayFinancialStatus
          displayFulfillmentStatus
          currentTotalPriceSet { shopMoney { amount currencyCode } }
          customer { id email }
          lineItems(first: 50) { edges { node {
            sku quantity title
            originalUnitPriceSet { shopMoney { amount } } } } }
        } }
        pageInfo { hasNextPage endCursor }
      }
    }
    """
    out, after = [], None
    while True:
        body = client.gql(query, {
            "q": f"updated_at:>={cursor_iso}",
            "after": after,
        })
        page = body["data"]["orders"]
        out.extend(e["node"] for e in page["edges"])
        if not page["pageInfo"]["hasNextPage"]:
            break
        after = page["pageInfo"]["endCursor"]
    new_cursor = max((o["updatedAt"] for o in out), default=cursor_iso)
    return out, new_cursor
```

Store the cursor in EOS memory; pass it back next run. Webhooks get
real-time, this catches anything missed.

### Recipe 2: Low-stock alert

```graphql
query LowStock($threshold: Int!) {
  productVariants(first: 100, query: "inventory_quantity:<10") {
    edges { node {
      id sku title
      inventoryQuantity
      product { id title handle }
      inventoryItem { id tracked
        inventoryLevels(first: 5) {
          edges { node { available location { id name } } }
        }
      }
    } }
  }
}
```

Run hourly during drops, daily otherwise. Push to EOS event bus, trigger
restock workflow.

### Recipe 3: Drop-launch automation

Pattern for a Lyfe Spectrum limited drop:

1. **Pre-launch**: create products with `status: DRAFT`, schedule
   `publishablePublish` for the launch time via a Function-backed
   automation, set inventory at the warehouse location.
2. **Launch**: Function (cart_transform) limits cart to N units per SKU,
   prevents stacking discount codes.
3. **In-stream**: Klaviyo flow on `orders/create` sends fulfillment ETA;
   metafield on customer flagged `vip:true` if order > $X.
4. **Post-launch**: bulk export sales report via bulk operation; Flow
   tags abandoned-cart customers for re-marketing.
5. **Inventory**: webhook on `inventory_levels/update` triggers EOS to
   re-rank waitlist customers and notify next-up tier.

### Recipe 4: Hydrogen storefront skeleton

```typescript
// app/routes/products.$handle.tsx
import {useLoaderData} from '@remix-run/react';
import type {LoaderArgs} from '@shopify/remix-oxygen';

export async function loader({params, context}: LoaderArgs) {
  const {handle} = params;
  const {product} = await context.storefront.query(PRODUCT_QUERY, {
    variables: {handle},
    cache: context.storefront.CacheLong(),
  });
  if (!product) throw new Response(null, {status: 404});
  return {product};
}

const PRODUCT_QUERY = `#graphql
  query Product($handle: String!) {
    product(handle: $handle) {
      id title descriptionHtml
      images(first: 5) { nodes { url altText width height } }
      variants(first: 100) {
        nodes { id title availableForSale price { amount currencyCode } }
      }
    }
  }
`;
```

Hydrogen wraps the Storefront API client (`context.storefront.query`)
with edge caching, GraphQL fragments, and Oxygen-aware deployment. Use
`CacheLong()` for catalog data, `CacheNone()` for cart, `CacheCustom()`
for personalized.

### Recipe 5: Webhook handler with idempotency

```python
@app.post("/webhooks/shopify/<topic>")
def handler(topic):
    raw = request.get_data()
    if not verify_shopify_webhook(raw, request.headers["X-Shopify-Hmac-Sha256"]):
        abort(401)
    webhook_id = request.headers["X-Shopify-Webhook-Id"]
    if redis.set(f"shopify:wh:{webhook_id}", "1", ex=172800, nx=True) is None:
        return "", 200  # already processed
    queue.enqueue("shopify.process", topic, raw, request.headers["X-Shopify-Shop-Domain"])
    return "", 200    # respond fast — 5s timeout
```

Verify → dedupe → enqueue → 200. Process in a worker.

## Industry Expert and Cutting-Edge Usage

What top Shopify Plus stores actually do (Allbirds, Gymshark, Kith,
Fashion Nova, Death Wish Coffee, Bombas, etc.):

- **Headless on Hydrogen** (Allbirds was the launch case study) for
  millisecond TTFB and design freedom; Oxygen for edge hosting.
- **Personalization via metafields + Klaviyo + Nosto** — every product,
  every customer, every order tagged with first-party signals; checkout
  decisions made by Functions referencing those tags.
- **Bulk operation pipelines** for nightly catalog → BigQuery /
  Snowflake → marketing operations. The bulk operation JSONL is dumped
  to Cloud Storage and pipelined.
- **Functions for everything** — every conversion-affecting rule runs
  as a Function, not in theme JS or app callbacks. JS is reserved for
  visual polish.
- **Pixels API + server-side conversion APIs** for ad attribution that
  survives iOS 14.5+ tracking restrictions.
- **B2B + DTC in one store** using Companies, Catalogs, and per-customer
  pricing. Plus stores are increasingly hybrid.
- **Preorders via Functions** instead of preorder apps — a Function
  blocks normal inventory commit and a metafield tracks the preorder
  queue.
- **Custom checkout extensions** for upsell, gift options, custom fields
  (engraving), accessibility — all via React-based Checkout UI Extensions
  with strict sandbox.
- **Shopify Markets for international** instead of multiple stores.
  Sub-domain or path-based localization with `@inContext` queries.
- **Performance: aggressive image policies** — `image_url(width: 1200)`
  in Liquid generates the right size on demand; never load original
  resolution. Hydrogen does the same with `<Image>`.
- **CI for theme + app code** — Shopify CLI's `theme push --json` and
  `app deploy` plugged into GitHub Actions with environment-per-branch.
- **Source of truth split**: catalog and inventory live in Shopify;
  CRM lives in Klaviyo or HubSpot; OMS lives in NetSuite or Brightpearl.
  Webhooks fan out from Shopify to each.

The pattern across all of them: **Shopify is the commerce engine, not
the system of record for everything**. Use it for what it's designed for
(catalog, checkout, payments, fulfillment surface), and integrate
elsewhere for what it isn't (CRM, OMS, ERP, BI).

---

## EOS Usage Patterns

How EOS agents actually call Shopify for Lyfe Spectrum.

### Pattern: Catalog management agent

The EOS catalog agent owns product creation, copy refinement, and
metafield updates for Lyfe Spectrum. Triggered by:
- Slack/Discord message: "Add product: Tactical Luxury Tee, sizes S-XXL,
  $48, drop date 2026-05-01"
- Founder voice memo via `services/voice_session.py`
- Scheduled drop preparation script

Flow:
1. Agent drafts copy using founder-voice prompt + brand-identity.md
2. Calls `productCreate` with `status: DRAFT`
3. Calls `productVariantsBulkCreate` for size variants
4. Calls `productCreateMedia` to attach renders from S3
5. Sets metafields: `lyfe_spectrum.drop_date`, `lyfe_spectrum.collection_tier`
6. Returns the admin URL to the founder for review

```python
def create_lyfe_spectrum_drop_product(spec: dict) -> str:
    res = client.gql(PRODUCT_CREATE, {"input": {
        "title": spec["title"],
        "descriptionHtml": spec["copy"],
        "vendor": "Lyfe Spectrum",
        "productType": spec["category"],
        "tags": ["drop:" + spec["drop_id"], "tactical-luxury"],
        "status": "DRAFT",
        "seo": {"title": spec["title"], "description": spec["copy"][:160]},
    }})
    product = res["data"]["productCreate"]["product"]
    if res["data"]["productCreate"]["userErrors"]:
        raise RuntimeError(res["data"]["productCreate"]["userErrors"])
    return product["id"]
```

### Pattern: Order ingestion into EOS memory

Webhook handler in `services/shopify_webhook.py` (to be built):

```python
@app.post("/webhooks/shopify/orders-create")
def orders_create():
    raw = request.get_data()
    if not verify_shopify_webhook(raw, request.headers["X-Shopify-Hmac-Sha256"]):
        abort(401)
    payload = json.loads(raw)
    memory.write(
        kind="commerce_event",
        source="shopify",
        venture="lyfe_spectrum",
        payload={
            "order_id": payload["id"],
            "name": payload["name"],
            "total": payload["total_price"],
            "currency": payload["currency"],
            "customer_email": payload.get("email"),
            "line_items": [{"sku": li["sku"], "qty": li["quantity"],
                            "title": li["title"]} for li in payload["line_items"]],
        },
    )
    return "", 200
```

This feeds `world_pulse` daily revenue snapshots and `business_instance`
metrics for Lyfe Spectrum.

### Pattern: Inventory low-stock alert via orchestrator

`orchestrator/scheduled/shopify_inventory_check.py` runs every 4h during
active drops, daily otherwise:

1. Bulk operation query for all variants with `inventory_quantity:<10`
2. Group by `product.handle`
3. Push event to EOS event bus → triggers Discord alert in #lyfe-spectrum
4. If `tag:reorder-auto` on the product, draft a PO for the supplier
   (placeholder until supplier API integration ships)

### Pattern: Drop-day Function-backed cart limit

A Shopify Function (`functions/cart-limit-tee/`) enforces "max 2 of any
SKU per cart during drop window." Deployed via `shopify app deploy`,
targets `purchase.cart-transform.run`. The Function reads a metafield
on the product to determine the limit, so the catalog agent can adjust
limits without redeploying the Function.

### Pattern: Hydrogen migration evaluation

Trigger: Lyfe Spectrum monthly revenue clears $50K AND theme Lighthouse
score < 70. Decision agent loads:
- Current OS 2.0 theme metrics from Shopify Web Performance dashboard
- Conversion data from Shop Pay Insights
- Estimated dev cost from Empyrean Studio time logs
- Hydrogen template best practices

Outputs a recommendation report. If GO: scaffold via
`npm create @shopify/hydrogen@latest`, deploy to Oxygen, dual-run for
2 weeks, switch DNS.

### Pattern: B2B price list for wholesale

When a wholesale lead converts (via Initiate Arena cohort): create a
Company in Shopify, attach the customer as a Company Location contact,
assign the `Wholesale 40% Off` PriceList. All future orders from that
customer apply the wholesale price automatically.

```graphql
mutation {
  companyCreate(input: {
    company: {name: "Acme Studio LLC", externalId: "lyfe-w-001"}
    companyContact: {email: "buyer@acme.studio"}
    companyLocation: {name: "HQ"
                      shippingAddress: {address1: "..." countryCode: US}}
  }) {
    company { id }
    userErrors { field message }
  }
}
```

### Pattern: Daily revenue snapshot for world_pulse

Bulk operation runs at 02:00 UTC, exports orders from previous day,
JSONL written to S3, `world_pulse.py` ingests and writes one row per
venture per day to Neon. Powers the founder's morning brief.

### Cross-tool composition

- **Klaviyo** receives customer + order events directly via native
  integration; EOS does NOT need to forward.
- **Stripe** is only used for non-Shopify products (Initiate Arena
  cohorts, Empyrean Studio invoices, Game of Lyfe). Shopify Payments
  handles all Lyfe Spectrum transactions to keep Shopify's transaction
  fee at 0%.
- **Notion** receives drop launch checklists generated from Shopify
  product metafields (drop date, collection tier).
- **Discord** receives real-time webhook alerts (new order, low stock,
  customer support escalation via Gorgias) via the EOS webhook handler.

## Gotchas

Operational failure modes Claude has hit (or will hit) when working
with Shopify in EOS. Add to this list whenever a real bug surfaces.

- **HMAC verification fails after middleware parsed body.** Flask
  `request.json`, FastAPI `await request.json()`, Express `body-parser`
  all consume the raw body. The HMAC is computed against the raw bytes
  before parsing. Capture `request.get_data(cache=True)` first, then
  parse.
- **`Shopify-GraphQL-Cost-Debug` typo.** Header name is exactly
  `Shopify-GraphQL-Cost-Debug` with that capitalization (HTTP headers
  are case-insensitive but some HTTP libs are picky). Value `1`, not
  `true`.
- **THROTTLED is HTTP 200.** `r.raise_for_status()` will not raise.
  Always inspect `body["errors"]`.
- **Cost debug header is per-request.** It does not persist across a
  client session — must be on every call.
- **`first` argument is mandatory** on every connection. Forgetting it
  is a GraphQL syntax error, not a runtime error — caught at parse time.
- **Bulk operation with `first`/`after` fails.** Bulk operations cannot
  use connection pagination arguments. Strip them from your bulk query.
- **Bulk operation URL expires in 60 seconds.** Download immediately
  when status flips to `COMPLETED`, do not stash the URL in a queue.
- **`productCreate` does not create variants.** It creates a default
  variant. To create real variants, follow up with
  `productVariantsBulkCreate`.
- **Variant `sku` is not unique.** Two products can share a SKU.
  Two variants on the same product can share a SKU. Shopify does not
  enforce. If you rely on SKU as a key, enforce it yourself.
- **Image upload via `productCreateMedia`** requires the image to be
  publicly fetchable by Shopify's servers (for `originalSource`). Local
  files must first be uploaded via `stagedUploadsCreate` → upload to
  the returned URL → reference the staged URL.
- **Webhook payloads include legacy IDs**, not GIDs. The webhook for
  `orders/create` has `"id": 5234567890` (number), not
  `gid://shopify/Order/...`. Convert with
  `gid://shopify/Order/{id}` if you need to call the GraphQL API
  with the resulting ID.
- **Webhook field set is fixed at the API version of subscription.**
  Re-create the subscription on version bump or you'll be missing fields
  added in newer versions.
- **The `orders/updated` webhook fires for every internal Shopify
  state change**, not just merchant edits. Filter by `updated_at` delta
  vs. last seen to avoid loops.
- **`customer.email` can be null** for guest checkouts. Always
  null-check.
- **Tags are stored as a comma-separated string** in webhook payloads
  but as an array in GraphQL responses. Pick one shape and normalize.
- **GraphQL error messages can include the full failing query** in dev
  mode — log carefully so you don't write secrets to logs if you ever
  parameterize a query with a token.
- **`metafieldsSet` overwrites without merging.** If you set
  `lyfe_spectrum.tags = "vip"` and the existing value was `"vip,wholesale"`,
  you've lost data. Read-modify-write or use `metafieldsDelete` + set.
- **`status: ARCHIVED` products** disappear from default product
  searches. Use `query: "status:active OR status:archived"` if you
  need to find them.
- **Inventory `available` going negative** is allowed if "Continue
  selling when out of stock" is on. Do not assume `available >= 0`.
- **Locations cannot be deleted** if they have inventory. Move
  inventory off first via `inventoryMoveQuantities`.
- **Discount codes are case-insensitive in checkout** but case-sensitive
  in API queries. Normalize to upper before comparing.
- **Theme assets cache aggressively at the CDN.** A Liquid file edit
  takes up to 60s to propagate. Use `?v=hash` query strings or the
  `--ignore-cache` flag in CLI dev.
- **`shopify theme dev` watches files but does not push CSS changes
  for compiled stylesheets** (e.g., Tailwind built outside the theme
  directory). Either build into the theme dir or use `theme push`.
- **App Bridge requires HTTPS even in dev** — use ngrok or
  Cloudflare Tunnel; localhost is not allowed.
- **Custom apps cannot use App Bridge** — App Bridge requires the
  embedded app context, which only public OAuth apps have.
- **Functions deploy is global per app version.** You cannot ship a
  Function to one merchant and not another with a single app version.
  Use a metafield-driven kill switch inside the Function.
- **Function logs are not real-time** — they show up in Shopify Partners
  with a 1-2 minute delay and are heavily sampled. Test logic locally
  with `shopify app function run`.
- **Storefront API caches at the edge** — a price update via Admin API
  takes 30-60s to be visible in Storefront API responses unless you
  bust the cache.
- **Markets and `@inContext` change cost.** Querying with
  `@inContext(country: US)` is slightly more expensive than the default
  shop currency. Account for it in cost budgets.
- **`productByHandle` is deprecated in 2025-04+** in favor of
  `productByIdentifier(identifier: {handle: ...})`. Both work in
  2026-04 but the deprecation notice appears in `extensions.deprecations`.
- **`bulkOperationRunMutation` requires staged upload of input.jsonl**
  before it can run. The flow is `stagedUploadsCreate` → upload JSONL
  → `bulkOperationRunMutation` referencing the staged upload's path.
- **Custom app token rotation has no API.** To rotate, you must
  regenerate the app credentials in admin (which invalidates the old
  token immediately) and redeploy. Schedule maintenance windows.
- **`country_code` vs `country` field.** Some inputs want
  `countryCode: US` (enum), others want `country: "United States"`
  (string). Read the schema; do not guess.
- **`weight` is grams in REST, but `weight` + `weightUnit` in GraphQL.**
  Migrating REST → GraphQL: re-derive units.
- **Long-running orchestrator scripts must be idempotent** because
  Shopify webhook retries can re-trigger the same event after the
  script started, producing duplicate writes. Always use the
  `X-Shopify-Webhook-Id` for dedupe.
- **OAuth `state` parameter is not optional in production** — Shopify
  doesn't require it but you should, to prevent CSRF on the install
  callback.
- **App Store review will reject** any app that doesn't handle the
  three GDPR webhooks (`customers/data_request`, `customers/redact`,
  `shop/redact`) within 30 days.
- **Pixels API code is sandboxed** — `window`, `document`, and most
  globals are absent. Use the provided `analytics.subscribe` API and
  `browser.cookie.set/get`.
- **`X-Shopify-API-Version` on webhook != your subscribed version**
  during the migration window. Two webhook subscriptions to the same
  topic at different versions is a deliberate pattern for migration.
- **Plus-only features fail with `ACCESS_DENIED`** on lower tiers
  (e.g., `Company` mutations on Basic). Catch and degrade.
- **`shopify_api` Python SDK uses REST under the hood** — its
  `Product.find()` is REST, not GraphQL. To stay GraphQL-pure, use
  `requests` directly.
- **Drop-launch race condition**: scheduling `productPublish` via Flow
  for an exact second is best-effort, not guaranteed. For exact-time
  drops use a Function-backed gate that reads a metafield with the
  unlock time, plus client-side countdown.
