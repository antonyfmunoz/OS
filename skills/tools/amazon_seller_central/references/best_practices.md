# Amazon Seller Central (SP-API) — Creator-Level Best Practices
Source: developer-docs.amazon.com/sp-api, github.com/amzn/selling-partner-api-models, github.com/amzn/selling-partner-api-docs, github.com/saleweaver/python-amazon-sp-api, Amazon Seller Central Help, github.com/amzn/selling-partner-api-samples
API Version: SP-API (per-endpoint: orders/v0, catalog/2022-04-01, listings/2021-08-01, fba/inventory/v1, fba/inbound/2024-03-20, feeds/2021-06-30, reports/2021-06-30, notifications/v1, tokens/2021-03-01, productPricing/v0, productFees/v0, finances/v0, sellers/v1, merchantFulfillment/v0, aplusContent/2020-11-01)
SDK Version: python-amazon-sp-api 1.9 (saleweaver) / amazon-sp-api 1.x (amz-tools, JS) / Java SDK v2.0 / C# SDK v2.0
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## Authentication

SP-API authentication is **LWA (Login with Amazon) only** as of October 2,
2023. Before that date you also had to AWS-SigV4-sign every request using an
IAM role assumed via STS; that requirement was retired. The SP-API gateway
still accepts a SigV4 header — it ignores it.

### LWA app registration

1. Log in to Seller Central with the seller account that will own the app.
2. Apps & Services → Develop Apps → Add new app client.
3. Choose **public** (listed on Marketplace Appstore, multi-seller) or
   **private** / **self-authorized** (your own seller accounts only — fine
   for Lyfe Spectrum's own brand).
4. Select API roles. Each role gates a family of endpoints:
   - Product Listing — listings, catalog
   - Inventory and Order Tracking — fba inventory, orders
   - Pricing — product pricing, fees
   - Amazon Fulfillment — fba inbound, MCF
   - Tax Invoicing / Tax Remittance — restricted PII
   - Direct-to-Consumer Shipping (PII) — restricted
   - Brand Analytics — restricted reports
5. Save. Amazon issues an `LWA app ID` (Client Identifier, starts with
   `amzn1.application-oa2-client.`) and an `LWA client secret`.
6. Click **Authorize** next to your private app row → Amazon redirects to
   itself, returns a `spapi_oauth_code`. The SDK exchanges that one-time
   code for a `refresh_token` (long-lived, no fixed expiry).

### Token dance (per request)

```
POST https://api.amazon.com/auth/o2/token
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token
&refresh_token=Atzr|...
&client_id=amzn1.application-oa2-client.xxxxxxxx
&client_secret=amzn1.oa2-cs.v1.xxxxxxxx
```

Response:

```json
{
  "access_token": "Atza|IwEBI...",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "Atzr|..."
}
```

Then for every SP-API call:

```
GET https://sellingpartnerapi-na.amazon.com/orders/v0/orders?...
x-amz-access-token: Atza|IwEBI...
host: sellingpartnerapi-na.amazon.com
user-agent: my-app/1.0 (Language=Python/3.12)
```

That's it. No SigV4. No IAM. No STS AssumeRole. No `aws4-hmac-sha256`
canonical string.

### Grantless operations

Three categories that authorize via LWA **client credentials** (no seller
context required):

```
POST https://api.amazon.com/auth/o2/token
grant_type=client_credentials
&scope=sellingpartnerapi::notifications     # for createDestination
&client_id=...
&client_secret=...
```

Or `sellingpartnerapi::migration` (for the legacy MWS migration helpers).
The returned access token only unlocks grantless paths (createDestination,
listMarketparticipations for own seller).

### Restricted Data Token (RDT)

Operations that touch PII (buyer name, shipping address, buyer email,
giftWrapping notes) require a **Restricted Data Token** that you mint per
call by listing the exact `(method, path, dataElements)` tuple.

```python
from sp_api.api import Tokens
rdt = Tokens(credentials=creds).create_restricted_data_token(
    restrictedResources=[{
        "method": "GET",
        "path": "/orders/v0/orders/123-1234567-1234567",
        "dataElements": ["buyerInfo", "shippingAddress"],
    }]
).payload['restrictedDataToken']
```

The RDT replaces the normal `x-amz-access-token` header value for **just
that one path**, lifetime 1 hour. You cannot mint a wildcard RDT. For batch
order pulls, mint one RDT covering the `/orders/v0/orders` collection plus
each child resource path you intend to call.

### Credential storage in EOS

```bash
# /opt/OS/eos_ai/.env
LWA_APP_ID=amzn1.application-oa2-client.XXXX
LWA_CLIENT_SECRET=amzn1.oa2-cs.v1.XXXX
SP_API_REFRESH_TOKEN=Atzr|XXXX
SP_API_SELLER_ID=A2EXAMPLE
SP_API_MARKETPLACE_ID=ATVPDKIKX0DER  # US
```

Never check refresh tokens into git. Rotate by re-authorizing the app from
Seller Central — the new authorization invalidates the old refresh token.

## Core Operations with Exact Signatures

All endpoints below assume the NA region base URL
`https://sellingpartnerapi-na.amazon.com`. Replace with `-eu` or `-fe` for
other regions. Every request requires `x-amz-access-token` header.

### Orders API (orders/v0)

```
GET  /orders/v0/orders
     ?MarketplaceIds=ATVPDKIKX0DER
     &CreatedAfter=2026-04-01T00:00:00Z       # OR LastUpdatedAfter
     &OrderStatuses=Unshipped,PartiallyShipped
     &MaxResultsPerPage=100
     &NextToken=...                            # opaque, from previous page

GET  /orders/v0/orders/{orderId}
GET  /orders/v0/orders/{orderId}/orderItems
GET  /orders/v0/orders/{orderId}/address       # restricted (RDT)
GET  /orders/v0/orders/{orderId}/buyerInfo     # restricted (RDT)
POST /orders/v0/orders/{orderId}/shipment
POST /orders/v0/orders/{orderId}/shipmentConfirmation
POST /orders/v0/orders/{orderId}/regulatedInfo
GET  /orders/v0/orders/{orderId}/approvals     # for B2B
```

### Catalog Items API (catalog/2022-04-01)

```
GET  /catalog/2022-04-01/items
     ?identifiers=B07XJ8C8F5,B08K1J2H3M
     &identifiersType=ASIN
     &marketplaceIds=ATVPDKIKX0DER
     &includedData=summaries,attributes,images,productTypes,salesRanks,relationships
     &locale=en_US

GET  /catalog/2022-04-01/items/{asin}
     ?marketplaceIds=ATVPDKIKX0DER
     &includedData=summaries,attributes,classifications

GET  /catalog/2022-04-01/items/search
     ?keywords=shirt
     &marketplaceIds=ATVPDKIKX0DER
     &brandNames=LyfeSpectrum
     &pageSize=10
```

### Listings Items API (listings/2021-08-01)

```
GET    /listings/2021-08-01/items/{sellerId}/{sku}
       ?marketplaceIds=ATVPDKIKX0DER
       &includedData=summaries,attributes,issues,offers,fulfillmentAvailability

PUT    /listings/2021-08-01/items/{sellerId}/{sku}
       ?marketplaceIds=ATVPDKIKX0DER
       Body: { "productType": "SHIRT", "requirements": "LISTING",
               "attributes": { ... } }

PATCH  /listings/2021-08-01/items/{sellerId}/{sku}
       ?marketplaceIds=ATVPDKIKX0DER
       Body: { "productType": "SHIRT",
               "patches": [ { "op": "replace", "path": "/attributes/list_price",
                              "value": [{"Amount": 29.99, "CurrencyCode": "USD"}] } ] }

DELETE /listings/2021-08-01/items/{sellerId}/{sku}
       ?marketplaceIds=ATVPDKIKX0DER
```

The PUT body must satisfy the full JSON-Schema for that productType
(retrieved from Product Type Definitions API:
`/definitions/2020-09-01/productTypes/{productType}`). PATCH uses RFC 6902
JSON Patch.

### Listings Restrictions API

```
GET /listings/2021-08-01/restrictions
    ?asin=B07XJ8C8F5
    &sellerId=A2EXAMPLE
    &marketplaceIds=ATVPDKIKX0DER
    &conditionType=new_new
```

### FBA Inventory API (fba/inventory/v1)

```
GET /fba/inventory/v1/summaries
    ?details=true
    &granularityType=Marketplace
    &granularityId=ATVPDKIKX0DER
    &marketplaceIds=ATVPDKIKX0DER
    &startDateTime=2026-04-01T00:00:00Z
    &sellerSkus=SKU-A,SKU-B
    &nextToken=...
```

### FBA Inbound v2024-03-20 (current — old fba/inbound/v0 deprecated)

```
POST /inbound/fba/2024-03-20/inboundPlans       # create plan
GET  /inbound/fba/2024-03-20/inboundPlans/{inboundPlanId}
POST /inbound/fba/2024-03-20/inboundPlans/{id}/packingOptions
POST /inbound/fba/2024-03-20/inboundPlans/{id}/placementOptions
POST /inbound/fba/2024-03-20/inboundPlans/{id}/placementOptions/{placementId}/confirmation
POST /inbound/fba/2024-03-20/inboundPlans/{id}/transportationOptions
GET  /inbound/fba/2024-03-20/inboundPlans/{id}/shipments
GET  /inbound/fba/2024-03-20/inboundPlans/{id}/shipments/{shipmentId}/labels
```

### Feeds API (feeds/2021-06-30)

```
POST /feeds/2021-06-30/documents              # body: { contentType }
     -> { feedDocumentId, url }               # url is presigned S3 PUT
                                              # PUT raw feed body to that url
POST /feeds/2021-06-30/feeds                  # body: { feedType, marketplaceIds,
                                              #         inputFeedDocumentId }
     -> { feedId }
GET  /feeds/2021-06-30/feeds/{feedId}         # status
GET  /feeds/2021-06-30/feeds                  # list with filters
DEL  /feeds/2021-06-30/feeds/{feedId}         # cancel (only IN_QUEUE)
GET  /feeds/2021-06-30/documents/{feedDocumentId}
     -> { url }                               # presigned GET, 5-min TTL
```

Common feed types:
- `JSON_LISTINGS_FEED` — the modern bulk listings/inventory/price/image
  feed (replaces POST_PRODUCT_DATA, POST_INVENTORY_AVAILABILITY_DATA,
  POST_PRODUCT_PRICING_DATA, POST_PRODUCT_IMAGE_DATA, POST_PRODUCT_RELATIONSHIP_DATA)
- `POST_ORDER_ACKNOWLEDGEMENT_DATA` — XML, FBM order ack
- `POST_ORDER_FULFILLMENT_DATA` — XML, ship confirm
- `POST_INVOICE_DATA` — XML invoice upload (regulated marketplaces)
- `POST_PRODUCT_PRICING_DATA` — flat file, deprecated, use JSON_LISTINGS_FEED

### Reports API (reports/2021-06-30)

```
POST /reports/2021-06-30/reports
     Body: { reportType, marketplaceIds, dataStartTime, dataEndTime, reportOptions }
     -> { reportId }
GET  /reports/2021-06-30/reports/{reportId}
     -> { processingStatus, reportDocumentId, ... }
GET  /reports/2021-06-30/documents/{reportDocumentId}
     -> { url, compressionAlgorithm }         # presigned GET, 5 min
GET  /reports/2021-06-30/reports              # list/filter
POST /reports/2021-06-30/schedules            # recurring report
DEL  /reports/2021-06-30/schedules/{scheduleId}
```

High-value report types for an apparel seller:
- `GET_FLAT_FILE_ALL_ORDERS_DATA_BY_LAST_UPDATE_GENERAL`
- `GET_MERCHANT_LISTINGS_ALL_DATA`
- `GET_MERCHANT_LISTINGS_DEFECT_DATA`
- `GET_FBA_MYI_UNSUPPRESSED_INVENTORY_DATA`
- `GET_FBA_INVENTORY_PLANNING_DATA`
- `GET_AFN_INVENTORY_DATA_BY_COUNTRY`
- `GET_FBA_REIMBURSEMENTS_DATA`
- `GET_FBA_FULFILLMENT_REMOVAL_ORDER_DETAIL_DATA`
- `GET_BRAND_ANALYTICS_SEARCH_TERMS_REPORT` (Brand Registry only)
- `GET_VENDOR_SALES_REPORT` (1P only)

### Product Pricing v0

```
GET /products/pricing/v0/price
    ?MarketplaceId=ATVPDKIKX0DER
    &Asins=B07XJ8C8F5
    &ItemType=Asin
    &CustomerType=Consumer
GET /products/pricing/v0/competitivePrice
GET /products/pricing/v0/listings/{sellerSku}/offers
GET /products/pricing/v0/items/{asin}/offers
```

There is also a v2022-05-01 batch endpoint:
`POST /batches/products/pricing/2022-05-01/itemOffers`.

### Product Fees v0

```
POST /products/fees/v0/listings/{sellerSku}/feesEstimate
POST /products/fees/v0/items/{asin}/feesEstimate
POST /products/fees/v0/feesEstimate
     Body: array of FeesEstimateRequest objects
```

### Notifications API v1

```
POST /notifications/v1/destinations
     Body: { name, resourceSpecification: { sqs: { arn } } }
     # OR resourceSpecification: { eventBridge: { region, accountId } }
     -> { destinationId }
GET  /notifications/v1/destinations
DEL  /notifications/v1/destinations/{destinationId}
POST /notifications/v1/subscriptions/{notificationType}
     Body: { payloadVersion, destinationId, processingDirective }
GET  /notifications/v1/subscriptions/{notificationType}
DEL  /notifications/v1/subscriptions/{notificationType}/{subscriptionId}
```

Notification types: `ANY_OFFER_CHANGED`, `ORDER_CHANGE`, `ORDER_STATUS_CHANGE`,
`FBA_OUTBOUND_SHIPMENT_STATUS`, `FEED_PROCESSING_FINISHED`,
`REPORT_PROCESSING_FINISHED`, `BRANDED_ITEM_CONTENT_CHANGE`,
`ITEM_PRODUCT_TYPE_CHANGE`, `LISTINGS_ITEM_STATUS_CHANGE`,
`LISTINGS_ITEM_ISSUES_CHANGE`, `MFN_ORDER_STATUS_CHANGE`,
`B2B_ANY_OFFER_CHANGED`, `ACCOUNT_STATUS_CHANGED`,
`PRODUCT_TYPE_DEFINITIONS_CHANGE`, `FEE_PROMOTION`.

### Tokens API (tokens/2021-03-01)

```
POST /tokens/2021-03-01/restrictedDataToken
     Body: { restrictedResources: [
              { method: "GET", path: "/orders/v0/orders/{id}",
                dataElements: ["buyerInfo","shippingAddress"] } ] }
     -> { restrictedDataToken, expiresIn }
```

### Sellers / Finances / Merchant Fulfillment / A+ Content

```
GET  /sellers/v1/marketplaceParticipations
GET  /finances/v0/financialEvents
POST /mfn/v0/eligibleShippingServices
POST /mfn/v0/shipments
GET  /aplus/2020-11-01/contentDocuments
POST /aplus/2020-11-01/contentDocuments
POST /aplus/2020-11-01/contentDocuments/{contentReferenceKey}/asins
```

## Pagination Patterns

SP-API uses **opaque NextToken pagination** on every list endpoint. There
is no offset/limit cursor exposed to clients. Always:

```python
next_token = None
while True:
    params = {"MarketplaceIds": [MP], "CreatedAfter": since}
    if next_token:
        params = {"NextToken": next_token, "MarketplaceIds": [MP]}
        # WARNING: when paging, you must DROP the original filters and pass
        # ONLY NextToken + MarketplaceIds. Including filters errors out.
    page = orders.get_orders(**params)
    yield page
    next_token = page.payload.get('NextToken')
    if not next_token:
        break
```

The python-amazon-sp-api library wraps this with `@load_all_pages()`. Use it.

Catalog search returns `pagination.nextToken` (camelCase, in body) instead
of the legacy XML-style `NextToken`. Each endpoint family has its own
pagination shape — read the spec for the exact key.

Reports list and Feeds list have **createdSince/createdUntil** with a hard
90-day window — you can't list older than that. Archive your own reportIds.

## Rate Limits

SP-API uses **per-operation token buckets** scoped to (sellerId, app, operation).
Each bucket has:
- **rate** — refill in tokens per second (sustained throughput)
- **burst** — bucket capacity (max sudden requests)

Throttle responses come back as `429 QuotaExceeded` with headers:
- `x-amzn-RateLimit-Limit: 0.5` — current rate refill per second
- `x-amzn-RequestId: ...`

Sample published limits (always re-verify against the per-endpoint table):

| Operation | Rate (TPS) | Burst |
|---|---|---|
| getOrders | 0.0167 | 20 |
| getOrder | 0.5 | 30 |
| getOrderItems | 0.5 | 30 |
| getOrderAddress | 0.5 | 30 |
| getOrderBuyerInfo | 0.5 | 30 |
| getCatalogItem | 2 | 2 |
| searchCatalogItems | 2 | 2 |
| getListingsItem | 5 | 10 |
| putListingsItem | 5 | 10 |
| patchListingsItem | 5 | 10 |
| deleteListingsItem | 5 | 10 |
| getInventorySummaries | 2 | 2 |
| createFeed | 0.0083 | 15 |
| getFeed | 2 | 15 |
| createFeedDocument | 0.5 | 10 |
| getFeedDocument | 0.0222 | 10 |
| createReport | 0.0167 | 15 |
| getReport | 2 | 15 |
| getReportDocument | 0.0222 | 10 |
| getCompetitivePricing | 0.5 | 1 |
| getItemOffers | 1 | 2 |
| getMyFeesEstimateForSKU | 1 | 2 |
| getFinancialEvents | 0.5 | 30 |
| createDestination | 1 | 5 |
| createSubscription | 1 | 5 |

Two enforcement tiers exist:
- **Application-level** rate limits — across all sellers using your app.
- **Per-seller** rate limits — your app per individual seller account.

Some endpoints (`patchListingsItem` with parent/child relationships) have
**data-type-level** sub-limits — e.g., 5 TPS for items containing
`child_parent_sku_relationship` even if the per-operation limit is higher.

**Always read `x-amzn-RateLimit-Limit` from the response** — Amazon
dynamically lowers your bucket if you abuse it, and the published table is
the ceiling not the floor.

Practical strategy:
1. Use Reports API for any bulk read instead of looping sync calls.
2. Use Feeds API for any bulk write.
3. Subscribe to Notifications instead of polling.
4. Honor `Retry-After` if present (some endpoints set it; orders does not).
5. Exponential backoff with jitter on 429 — start at 1s, cap at 60s.
6. Keep one in-flight call per operation per seller; serialize via a
   per-operation lock.

## Error Codes and Recovery

Standard HTTP semantics layered with Amazon error envelopes:

```json
{
  "errors": [
    {
      "code": "InvalidInput",
      "message": "MarketplaceIds query parameter is required.",
      "details": ""
    }
  ]
}
```

Status code map:

| Code | Meaning | Recovery |
|---|---|---|
| 200 | OK | — |
| 202 | Accepted (async create) | Poll the resource id |
| 400 | InvalidInput | Don't retry. Fix payload. |
| 401 | Unauthorized | Re-mint LWA access token (or re-onboard if refresh token revoked) |
| 403 | Access to resource forbidden / Unauthorized | Missing API role; re-authorize app with the right scope |
| 404 | NotFound | Resource truly absent — but also returned for sandbox typos |
| 410 | Gone | Old endpoint version; migrate |
| 413 | RequestEntityTooLarge | Feed/document over size limit (150MB feeds) |
| 415 | Unsupported MediaType | Wrong contentType for feed document |
| 429 | QuotaExceeded | Backoff with jitter, respect rate limit header |
| 500 | InternalFailure | Retry with backoff |
| 503 | Unavailable | Retry with longer backoff |

LWA token endpoint errors:
- `invalid_grant` — refresh token revoked or wrong client
- `invalid_client` — wrong client_id/secret
- `invalid_scope` — grantless scope mismatch

Common per-operation error codes:
- `InvalidParameterValue` — bad enum, bad ISO date format
- `MissingMarketplaceIds` — every list endpoint needs it
- `ResourceNotFound` — order id, sku, feed id, report id wrong
- `MediaTypeNotSupported` — feed contentType mismatch
- `RestrictedResourceNotAvailable` — RDT path didn't match call path
- `Throttled` (sub-form of 429)

Recovery library pattern:

```python
import time, random
from sp_api.base.exceptions import SellingApiRequestThrottledException

def with_retry(fn, *args, max_attempts=6, **kwargs):
    delay = 1.0
    for attempt in range(max_attempts):
        try:
            return fn(*args, **kwargs)
        except SellingApiRequestThrottledException:
            sleep = delay * (2 ** attempt) + random.uniform(0, 0.5)
            time.sleep(min(sleep, 60))
    raise RuntimeError("max retries exhausted")
```

## SDK Idioms

### python-amazon-sp-api (saleweaver) — recommended

Install: `pip install python-amazon-sp-api`

```python
from sp_api.api import Orders, Catalog, ListingsItems, FbaInventory, Feeds, ReportsV2, Tokens, ProductPricing
from sp_api.base import Marketplaces, SellingApiException
from sp_api.base.reportTypes import ReportType
from sp_api.util import throttle_retry, load_all_pages

creds = dict(
    refresh_token=os.environ['SP_API_REFRESH_TOKEN'],
    lwa_app_id=os.environ['LWA_APP_ID'],
    lwa_client_secret=os.environ['LWA_CLIENT_SECRET'],
)

@throttle_retry()                       # auto-retry 429 with backoff
@load_all_pages()                       # auto-paginate NextToken
def all_orders(**kw):
    return Orders(credentials=creds, marketplace=Marketplaces.US).get_orders(**kw)
```

The `@load_all_pages` decorator transforms the function into a generator
yielding response objects. Each yielded object exposes `.payload` (parsed
JSON dict), `.errors`, `.next_token`, `.rate_limit`, `.headers`.

To target a non-default marketplace per call, instantiate the client with
`marketplace=Marketplaces.DE`. Marketplaces enum maps endpoint region too.

### amazon-sp-api (amz-tools) — Node.js

```javascript
const SellingPartnerAPI = require('amazon-sp-api');
const sp = new SellingPartnerAPI({
  region: 'na',
  refresh_token: process.env.SP_API_REFRESH_TOKEN,
  credentials: {
    SELLING_PARTNER_APP_CLIENT_ID: process.env.LWA_APP_ID,
    SELLING_PARTNER_APP_CLIENT_SECRET: process.env.LWA_CLIENT_SECRET,
  },
});

const orders = await sp.callAPI({
  operation: 'getOrders',
  endpoint: 'orders',
  query: { MarketplaceIds: ['ATVPDKIKX0DER'], CreatedAfter: '2026-04-01' },
});
```

### Official Java/C# SDKs

Amazon publishes Swagger-generated SDKs at github.com/amzn/selling-partner-api-models.
Java v2.0 (October 2023+) drops the IAM signing layer entirely. Use them
when you need Amazon support; community SDKs are faster-moving.

### Sandbox

Every endpoint has a sandbox alias at `sandbox.sellingpartnerapi-na.amazon.com`.
Sandbox returns canned static responses keyed by specific marker values
(e.g., `TEST_CASE_200`). It does NOT replay your own data. Use for shape
validation only — production smoke testing requires real credentials.

## Anti-Patterns

- **Polling getOrders every minute** — burns the 0.0167 TPS bucket and
  misses cancellations. Subscribe to ORDER_CHANGE notifications instead.
- **Looping getCatalogItem to refresh prices** — use Pricing API batch
  endpoints or `GET_AFN_INVENTORY_DATA_BY_COUNTRY` reports.
- **One feed per SKU update** — feeds limit is 1/5min. Batch into a single
  JSON_LISTINGS_FEED with up to 25k messages.
- **Storing the LWA access token in a database** — it expires in 60 min and
  multi-process workers can race on refresh. Mint per-process, cache in
  memory.
- **Re-signing requests with SigV4 in 2026** — wasted CPU; SP-API ignores
  the signature. Strip it.
- **Using the legacy `POST_INVENTORY_AVAILABILITY_DATA` flat file** —
  deprecated 2024. Migrate to JSON_LISTINGS_FEED PARTIAL_UPDATE on
  `fulfillment_availability`.
- **Calling restricted endpoints without RDT** — returns 403 with
  unhelpful "missing scope" error. Always mint RDT first for PII paths.
- **Treating `processingStatus=DONE` as success** — always download the
  result document and parse for per-message issues.
- **Hardcoding `marketplace=US`** — code that never runs in CA breaks the
  day you expand. Pass marketplace through every call site.
- **Using Catalog Items API as a price feed** — it returns the buy box
  offer at request time, not your price. Use Pricing or Listings.
- **Skipping the Tokens API for buyer email** — buyer email is PII even
  if it looks like a marketplace-relay address.
- **Publishing a public app without rotating refresh tokens after dev** —
  the dev refresh token works in production and is a security hole.

## Data Model

The SP-API exposes a graph of resources rooted at the **selling partner**
(your seller account). The principal entities:

```
SellingPartner (sellerId)
 └── MarketplaceParticipation (sellerId × marketplaceId)
      ├── Listings (sellerId × marketplaceId × sku)
      │    └── attributes (per productType schema)
      │    └── offers (price, quantity, fulfillmentChannel)
      │    └── issues (errors, warnings, suppressions)
      ├── Inventory
      │    ├── FBA InventorySummary (sellerSku × asin × granularity)
      │    │    └── inventoryDetails (fulfillable, unfulfillable, reserved, researching)
      │    └── FBM (in listings.fulfillment_availability)
      ├── Orders (amazonOrderId)
      │    ├── orderItems (orderItemId × asin × sku × quantity)
      │    ├── shippingAddress (PII, RDT-gated)
      │    ├── buyerInfo (PII, RDT-gated)
      │    └── shipments
      ├── Feeds (feedId)            ── async job graph
      ├── Reports (reportId)        ── async job graph
      ├── Subscriptions (subscriptionId)
      └── FinancialEvents (eventGroupId)

Catalog (global, not seller-scoped)
 └── Item (asin) — productType, salesRanks, attributes, images, relationships
```

Key opaque identifiers:
- **sellerId** (`A2EXAMPLE`) — 14-char alphanumeric, your merchant token
- **asin** (`B07XJ8C8F5`) — 10-char Amazon Standard Identification Number,
  Amazon's product key, globally unique per region
- **sku** — your seller SKU, free-form, unique per (seller, marketplace)
- **amazonOrderId** (`123-1234567-1234567`) — formatted with dashes
- **marketplaceId** — opaque 14-char id (US=ATVPDKIKX0DER, CA=A2EUQ1WTGCTBG2)
- **feedId / reportId / inboundPlanId / shipmentId** — opaque strings
- **fnsku** — Amazon-assigned FBA barcode SKU per seller's FBA inventory

The catalog is a separate graph (one ASIN → one product across all
sellers) intersecting with your listings via shared `asin`. You **own**
your listing for an ASIN; you do **not** own the ASIN.

## Webhooks and Events

SP-API "webhooks" are delivered through the Notifications API to either
**Amazon SQS** or **EventBridge** — never directly to an HTTPS URL.

### SQS path (most common)

1. Create an SQS queue in your AWS account (use the `aws` skill).
2. Attach a queue policy granting principal
   `arn:aws:iam::437568002678:root` (Amazon's notification service account)
   `sqs:SendMessage` permission.
3. Call SP-API `createDestination` with the queue ARN — this is **grantless**.
4. Call `createSubscription` for each notificationType you want, referencing
   the destinationId.
5. Long-poll the queue from your worker; ack with DeleteMessage.

### EventBridge path

1. Call grantless `createDestination` with `eventBridge: { region, accountId }`.
2. Amazon creates a partner event source in your AWS account named
   `aws.partner/sellingpartnerapi.amazon.com/...`.
3. Activate it in EventBridge; route via rules to Lambda/SQS/etc.

### Notification envelope

```json
{
  "NotificationVersion": "1.0",
  "NotificationType": "ANY_OFFER_CHANGED",
  "PayloadVersion": "1.0",
  "EventTime": "2026-04-06T12:00:00.000Z",
  "Payload": { /* type-specific */ },
  "NotificationMetadata": {
    "ApplicationId": "amzn1.sellerapps.app...",
    "SubscriptionId": "...",
    "PublishTime": "2026-04-06T12:00:00.123Z",
    "NotificationId": "..."
  }
}
```

### Notification types worth subscribing

- `ANY_OFFER_CHANGED` — Buy Box winner/price changes for ASINs you sell
- `ORDER_CHANGE` / `ORDER_STATUS_CHANGE` — replaces polling getOrders
- `FEED_PROCESSING_FINISHED` — fan out result-document parsing
- `REPORT_PROCESSING_FINISHED` — same for reports
- `LISTINGS_ITEM_ISSUES_CHANGE` — Amazon flagged something on your listing
- `FBA_OUTBOUND_SHIPMENT_STATUS` — for MCF
- `BRANDED_ITEM_CONTENT_CHANGE` — competitor edited your A+ content (Brand Registry)

There is **no HTTP webhook delivery option**. EOS must run an SQS poller
(or EventBridge rule → Lambda → POST EOS gateway).

## Limits

| Limit | Value |
|---|---|
| Feeds: max messages per JSON_LISTINGS_FEED | 25,000 |
| Feeds: max feed body size | 150 MB (uncompressed) |
| Feeds: max feeds per 5 minutes | ~1 sustained, 15 burst |
| Reports: report retention (downloadable) | 90 days |
| Reports: max reportType per createReport | 1 |
| Listings: SKU length | 40 chars |
| Listings: title length | 200 chars (most categories), 80 recommended |
| Listings: bullet points | 5 max, 500 chars each |
| Listings: images | 9 max (1 main + 8 additional) |
| Listings: product description HTML | 2000 chars (allowed tags only) |
| Catalog: identifiers per call | 20 ASINs per /items batch |
| Pricing: ASINs per call | 20 |
| FBA Inventory: max SKUs per call | 50 (sellerSkus query param) |
| FBA Inventory: granularity | Marketplace only (not warehouse) |
| Orders: max date range | 30 days for CreatedAfter window |
| Orders: max page size | 100 |
| RDT lifetime | 1 hour |
| LWA access token lifetime | 1 hour |
| LWA refresh token lifetime | indefinite (until revoked/re-auth) |
| FBA inbound: max SKUs per shipment plan | 200 |
| Notifications: subscriptions per type | 1 destination per app per type |
| Notifications: SQS message size | 256 KB |
| FBA storage utilization surcharge threshold | 26 weeks of forward inventory |
| FBA long-term storage age threshold | 271 days (lowered from 365 in 2025) |
| IPI minimum threshold | 400 |
| FBA capacity calculation horizon | 5 months (lowered from 6 in May 2025) |

## Cost Model

SP-API itself is **free** — no per-call charge. The costs are everything around it:

| Cost | Amount (US, 2026) |
|---|---|
| Professional Selling Plan | $39.99 / month (required for SP-API) |
| Individual Selling Plan | $0.99 / item sold (no SP-API access) |
| Referral fee | 8–17% of item price (varies by category, apparel ~17%) |
| FBA fulfillment fee | $3.06–$8.30+ per unit (size/weight tiered) |
| FBA monthly storage (Jan–Sep) | $0.87 / cu ft standard, $0.56 / cu ft oversize |
| FBA monthly storage (Oct–Dec) | $2.40 / cu ft standard, $1.40 / cu ft oversize |
| FBA storage utilization surcharge | $0.69+ / cu ft when > 26 weeks of inventory |
| FBA long-term storage fee | $6.90 / cu ft or $0.15 / unit (whichever greater), >271 days |
| FBA aged inventory surcharge | tiered, 181+ days |
| FBA inbound placement service | $0.21–$1.58+ / unit (depends on placement option) |
| FBA removal order | $0.97–$5.10+ / unit |
| FBA disposal order | $0.30–$2.07+ / unit |
| Brand Registry | free (Brand Registry 2.0) |
| Subscribe & Save discount | 5% or 10% (paid by seller) |
| AWD (Amazon Warehousing & Distribution) | separate per cu ft + transfer fees |
| AWS SQS for notifications | $0.40 per million requests (effectively free) |

There is also a **Refund Administration Fee** ($5.00 or 20% of the
referral fee) when a customer is refunded.

## Version Pinning

SP-API endpoints are versioned per family. Live versions as of 2026-04:

| Family | Live version | Status |
|---|---|---|
| orders | v0 | stable, unchanged since 2020 |
| catalog | 2022-04-01 | stable; 2020-12-01 deprecated, v0 retired |
| listings | 2021-08-01 | stable; LSv1 (2020-09-01) deprecated |
| productTypeDefinitions | 2020-09-01 | stable |
| fba/inventory | v1 | stable |
| fba/inbound | 2024-03-20 | current; v0 deprecated 2024 |
| feeds | 2021-06-30 | stable; pre-2021 retired |
| reports | 2021-06-30 | stable; pre-2021 retired |
| notifications | v1 | stable |
| tokens | 2021-03-01 | stable |
| productPricing | v0 + 2022-05-01 batch | both live |
| productFees | v0 | stable |
| finances | v0 | stable |
| sellers | v1 | stable |
| merchantFulfillment | v0 | stable |
| aplusContent | 2020-11-01 | stable |
| sales | v1 | stable |
| services | v1 | stable |
| shipping | v2 | stable |
| supplySources | 2020-07-01 | stable |
| uploads | 2020-11-01 | stable |
| vendor | many sub-families (vendorOrders, vendorShipments, etc.) | 1P only |

Deprecation policy: Amazon announces deprecation 12 months ahead via
developer-docs changelog and the Developer Central announcements feed.
Subscribe to the SP-API release notes RSS.

SDK pinning: `python-amazon-sp-api==1.9.*` for stability; bump quarterly.
Lock the SDK version in `requirements.txt` because saleweaver occasionally
ships breaking renames between minor versions.

---

# Tier 2 — Domain Mastery

## Design Intent and Tradeoffs

SP-API exists to give sellers **programmatic parity with Seller Central**.
Every action a human can take in the web UI should be doable through the
API; in practice, parity is ~90%, with a long tail of UI-only flows
(advanced Brand Registry actions, some account-health adjustments, video
content uploads, A+ premium templates).

Amazon designed SP-API after watching what went wrong with MWS:

- **MWS used a per-account access key + AWS SigV2 signing** — leaked keys
  were a constant problem. SP-API moved to OAuth so sellers can revoke
  access without rotating keys.
- **MWS was monolithic and versioned globally** — one breaking change
  forced everyone to migrate. SP-API versioned per endpoint, so the
  Catalog team can ship 2022-04-01 without disturbing Orders v0.
- **MWS rate limits were app-wide** — one bad actor throttled all your
  sellers. SP-API throttles per (seller, app, operation).
- **MWS had no real-time push** — everyone polled. SP-API ships
  Notifications v1 with SQS as the canonical low-latency channel.
- **MWS authentication required AWS knowledge** — most sellers don't have
  AWS accounts. SP-API moved to LWA-only in 2023 to eliminate that hurdle.

The tradeoffs:
- **Async-document model adds latency.** A bulk inventory update through
  Feeds takes 2–10 minutes vs MWS's old synchronous bulk endpoints. Amazon
  bet on durability over speed.
- **Per-operation rate limits punish naive code.** Devs used to firing
  off MWS calls in parallel get throttled fast. SP-API forces you to
  think about call patterns.
- **Restricted Data Tokens add friction for PII.** A second round-trip
  per shipping address pull. Amazon traded developer convenience for
  GDPR/CCPA compliance — and won (multiple regulators have praised it).
- **Schemas are huge.** A SHIRT productType JSON Schema is ~3000 lines.
  Building a generic listing creator means consuming Product Type
  Definitions API and dynamically validating — non-trivial.
- **No GraphQL, no streaming.** REST + polling + push. Amazon never built
  the unified query layer some integrators wanted.

## Problem-Solution Map and Hidden Capabilities

| Problem | SP-API solution |
|---|---|
| "Sync 50,000 SKUs from my ERP nightly" | JSON_LISTINGS_FEED, batched 25k per feed, two feeds spaced 5 min |
| "Update inventory in real time" | JSON_LISTINGS_FEED PARTIAL_UPDATE on `fulfillment_availability`, accept 5-min latency, OR direct patchListingsItem (5 TPS budget) |
| "React to a sale within seconds" | ORDER_CHANGE notification → SQS → worker (sub-second p50) |
| "Track Buy Box loss" | ANY_OFFER_CHANGED notification on every ASIN you sell |
| "Re-price competitively" | getCompetitivePricing + patchListingsItem; or use a managed repricer |
| "Fulfill via FBA" | Inbound v2024-03-20 plan workflow; then ship to Amazon |
| "Fulfill via Multi-Channel Fulfillment for off-Amazon orders" | createFulfillmentOrder in /mfn/ — Amazon ships from FBA stock |
| "Reconcile finances" | Finances v0 listFinancialEvents — every fee, refund, reserve |
| "Pull a 90-day order history" | GET_FLAT_FILE_ALL_ORDERS_DATA_BY_LAST_UPDATE_GENERAL report |
| "Identify suppressed listings" | GET_MERCHANT_LISTINGS_DEFECT_DATA report |
| "Get search-term insights" | Brand Analytics search terms report (Brand Registry only) |
| "A/B test product images" | Manage Your Experiments (Brand Registry, partial API) |
| "Estimate fees before listing" | Product Fees getMyFeesEstimate |

Hidden / under-used capabilities:

- **Brand Registry** — Once enrolled (free), unlocks A+ Content API,
  Sponsored Brands eligibility, IP enforcement (Project Zero), Amazon Vine
  reviews program, Transparency anti-counterfeit codes, Brand Analytics
  reports, video uploads.
- **Amazon Vine** — for Brand-Registered sellers, get up to 30 reviews
  per ASIN by giving units to vetted reviewers. Mostly Seller Central UI;
  some API in `services/v1`.
- **FBA Small and Light** (now called Low-Price FBA Rate) — discounted
  fulfillment fee for items under $10 and under 12 oz. Enrolment in
  Seller Central, status visible via FBA Inventory API.
- **Subscribe & Save** — recurring delivery program; eligibility set per
  ASIN, discount levied on seller. Manage via listings attributes.
- **AWD** — Amazon Warehousing & Distribution. Cheaper bulk storage that
  feeds FBA on demand. Separate API surface (`/awd/`).
- **Multi-Channel Fulfillment (MCF)** — use FBA stock to fulfill Shopify
  / DTC orders. `/mfn/v0/` endpoints.
- **Buy with Prime** — separate program letting your DTC site checkout
  with Prime. Has its own API; surfaces in MCF flows.
- **Transparency** — anti-counterfeit serialization. Print Amazon-issued
  Transparency codes per unit; Amazon scans on receipt.
- **Project Zero** — Brand Registry feature letting you takedown
  counterfeit listings without Amazon review.
- **Manage Your Experiments** — Brand Registry A/B testing of titles,
  bullet points, images, A+ content.

## Operational Behavior and Edge Cases

- **Order edge cases**: An order can be `Pending` for hours while Amazon
  pre-authorizes the buyer's card; you cannot fulfill until `Unshipped`.
  Cancellation can come up to 30 minutes after `Shipped`. Replacement
  orders look like new orders with a `ReplacedOrderId` reference.
- **Inventory desync**: FBA inventory pulled from `/fba/inventory/v1/summaries`
  is **delayed up to 30 minutes** vs reality. Reports
  (`GET_FBA_MYI_UNSUPPRESSED_INVENTORY_DATA`) are even more delayed but
  more authoritative. For real-time, listen to FBA inventory change
  notifications.
- **Stranded inventory**: FBA stock with no active listing — happens when
  a listing is suppressed, deleted, or buy-box-suppressed but units are
  still in the warehouse. Generates storage fees for nothing. Fix via
  Seller Central → Inventory → Fix Stranded Inventory.
- **Suppressed listings**: A listing can be live, search-suppressed
  (won't show in customer search), or fully suppressed (no buy box).
  Causes: missing required attributes, image quality issues, restricted
  category, brand mismatch. Pull `GET_MERCHANT_LISTINGS_DEFECT_DATA`.
- **IPI score quirks**: Updated weekly Tuesday morning PT, reflects
  trailing 90 days. Components: excess inventory percentage, sell-through
  rate, stranded percentage, in-stock rate. Below 400 → restock cuts.
- **ASIN-level restock limits**: As of 2025, Amazon caps inbound per ASIN
  even when account-wide cap allows more. Returned in response headers as
  `x-amzn-RateLimit-*`-style hints; surfaced in `/inbound/fba/2024-03-20/inboundPlans/{id}/placementOptions`.
- **Storage Utilization Surcharge**: Effective April 1, 2025. If you hold
  >26 weeks of forward inventory, monthly surcharge applies on top of
  storage fees. Pull `GET_FBA_STORAGE_FEE_CHARGES_DATA`.
- **Long-term storage**: kicks in at **271 days** as of 2025 (was 365).
- **Inbound Placement Service**: Amazon may split your inbound across
  multiple FCs ("split shipments"). You can opt for "Minimal shipment
  splits" placement option in inbound v2024-03-20 — costs more, simplifies.
- **Marketplace participation can change** — A seller can deactivate a
  marketplace and lose access mid-day. Always handle 403 on a previously
  working marketplaceId.
- **Time zones are subtle**: All API timestamps are ISO 8601 UTC. Reports
  date filters are in **PT** (Pacific Time, Amazon HQ). Mismatch is the #1
  cause of "missing orders" bug reports.
- **Cancellation grace**: Buyers can cancel within 30 minutes of placing
  the order with no seller intervention. Don't ship `Unshipped` orders
  in the first 30 minutes.
- **Returns**: Customer-initiated returns hit `MFN_RETURN_REQUESTED`
  notification (FBM) or just appear in `Returns` reports (FBA). FBA
  returns are managed by Amazon; you see them after the fact.
- **A+ Content review**: Submitting A+ content via API enters a 3–7 day
  Amazon review queue. Status via `getContentDocument`.
- **Brand Registry mismatches**: Even with Brand Registry, listings can
  go through "brand drift" where Amazon assigns the wrong brand. Fix via
  Brand Registry case, not API.

## Ecosystem Position and Composition

Where SP-API sits in the ecommerce stack:

```
Source of truth (PIM/ERP)
    │
    ├── shopify ──► Shopify storefront (DTC, primary for Lyfe Spectrum)
    ├── amazon_seller_central ──► Amazon (secondary channel)
    ├── walmart_marketplace
    ├── etsy / ebay
    └── tiktok shop
```

vs other ecommerce APIs:

| Channel | API maturity | Key tradeoff vs SP-API |
|---|---|---|
| **Shopify** | Excellent (REST + GraphQL + webhooks) | True real-time, no per-op throttle, but no marketplace demand |
| **Walmart Marketplace** | Good | Smaller catalog, slower review, fewer fulfillment options |
| **eBay** | Mature, complex | Listing-format model not catalog-format |
| **Etsy** | Limited | No bulk feeds; per-listing API only |
| **TikTok Shop** | Young | Fast-moving spec, fewer SDKs |
| **Faire** (B2B wholesale) | Decent | Different buyer model entirely |

Composition partners (third-party tools every Amazon seller eventually integrates):

- **Helium 10 / Jungle Scout / Viral Launch** — keyword research, ASIN
  scout. Read-only consumers of Amazon scrape data, not SP-API.
- **Keepa / CamelCamelCamel** — historical price tracking. Build their
  own data lake by polling.
- **Seller Labs / SellerApp / DataHawk** — analytics dashboards on
  SP-API + ads.
- **InventoryLab / SoStocked** — replenishment forecasting; pulls FBA
  inventory + sales velocity from SP-API.
- **Repricer.com / RepricerExpress / Aura** — managed repricers; consume
  ANY_OFFER_CHANGED notifications.
- **Linnworks / ChannelAdvisor / Sellercloud / Skubana / Sellbrite /
  Codisto** — multi-channel listing managers (the "Shopify ↔ Amazon ↔
  Walmart sync" middleware EOS could replace).
- **Refund Genie / Seller Investigators** — FBA reimbursement claims
  automation.
- **ManageByStats / Sellerise / Helium 10's Profits** — P&L from
  Finances API + cost data.
- **A2X / Link My Books** — Finances API → Xero/QuickBooks for accounting.

EOS competes (eventually) with the multi-channel listing manager category
by owning the Shopify-as-source-of-truth → Amazon sync workflow natively.

## Trajectory and Evolution

- **2009** — Amazon Marketplace Web Service (MWS) launches.
- **2020** — SP-API GA at re:Invent, MWS deprecation announced.
- **2021** — MWS endpoints start getting rate-limited harder; SP-API
  becomes mandatory for new apps.
- **2022** — Catalog 2022-04-01 ships with classification + relationships
  redesign. JSON_LISTINGS_FEED introduced as preview.
- **Oct 2023** — AWS SigV4 / IAM dropped. LWA-only authentication.
  Java/C# SDK v2.0 ships.
- **2024** — fba/inbound v2024-03-20 ships, deprecating v0. JSON_LISTINGS_FEED
  v2.0 GA, replacing flat-file feeds. AWD (Amazon Warehousing &
  Distribution) API surfaces.
- **2025** — IPI threshold enforcement immediate (no quarterly grace).
  FBA capacity horizon cut from 6 to 5 months. Storage Utilization
  Surcharge introduced. Long-term storage threshold lowered to 271 days.
  Inbound Placement Service tiers expanded.
- **2025-2026** — Rufus (buyer-side AI shopping assistant) starts
  influencing search results; sellers ranked partly on conversational
  signals. AI-generated listing copy tooling ships in Seller Central
  (with API hints). Buy with Prime expands integration with Shopify
  natively (lessening MCF API friction).
- **What's coming**: deeper EventBridge / GraphQL pilots, regional
  marketplace consolidation (less divergence between EU sub-marketplaces),
  more PII gating, AI-driven listing quality scores surfaced via API.

The honest read: SP-API is **stable, mature, and grinding**. Amazon ships
incremental improvements quarterly but the underlying model (REST + LWA +
async docs + per-op throttle) is set for the next 5+ years. Build
infrastructure assuming SP-API is here for the long run.

## Conceptual Model and Solution Recipes

### Recipe: bulletproof Shopify → Amazon listing sync

```
1. Read Shopify products + variants (source of truth)
2. Diff against last-synced state (stored in Neon)
3. Group changes by type:
   - new SKUs ──► JSON_LISTINGS_FEED with operationType=UPDATE,
                  full LISTING requirements (productType schema validated)
   - price/inventory only ──► PARTIAL_UPDATE on attributes:
                  list_price, fulfillment_availability
   - delete ──► operationType=DELETE
4. Chunk into ≤25,000 messages per feed.
5. For each chunk: createFeedDocument → upload → createFeed.
6. Subscribe to FEED_PROCESSING_FINISHED notification (don't poll).
7. On notification: getFeedDocument → parse result → write per-message
   issues to Neon.
8. Mark Shopify variants with their Amazon `submissionId`.
9. Subscribe to LISTINGS_ITEM_ISSUES_CHANGE for ongoing health monitoring.
```

### Recipe: bulletproof order pull

```
1. Subscribe to ORDER_CHANGE notification → SQS queue.
2. Worker long-polls SQS, reads notification.
3. For each AmazonOrderId: mint RDT for
   /orders/v0/orders/{id} + /orders/v0/orders/{id}/orderItems
   + /orders/v0/orders/{id}/address (with buyerInfo + shippingAddress).
4. GET each path with the RDT, store in Neon.
5. Reconcile nightly with GET_FLAT_FILE_ALL_ORDERS_DATA report (90-day
   window) — catch any missed notifications.
```

### Recipe: FBA replenishment trigger

```
1. Daily report: GET_FBA_INVENTORY_PLANNING_DATA
2. Compute days-of-cover per SKU using last 30-day sales velocity from
   GET_SALES_AND_TRAFFIC_REPORT.
3. If days-of-cover < lead-time + safety-stock, queue replenishment.
4. Build inbound plan via /inbound/fba/2024-03-20/inboundPlans.
5. Generate packing options, pick cheapest placement option.
6. Confirm placement, generate shipment labels, hand to warehouse.
```

### Recipe: Buy Box loss alerting

```
1. Subscribe to ANY_OFFER_CHANGED for every ASIN you sell.
2. On notification, check if your sellerId still owns the buy box.
3. If lost: log + alert + (optionally) auto-reprice via patchListingsItem.
```

### Recipe: weekly P&L reconciliation

```
1. /finances/v0/financialEventGroups → list groups for last 7 days.
2. For each group, /financialEvents → all fees/refunds/reserves.
3. Sum by event type into Neon.
4. Cross-check with GET_VENDOR_REAL_TIME_INVENTORY_REPORT (1P) or
   GET_FBA_REIMBURSEMENTS_DATA.
5. Push P&L row to dashboard.
```

## Industry Expert and Cutting-Edge Usage

- **Top sellers run notifications-first, never poll.** Polling is for dev
  scripts. Production architecture is ORDER_CHANGE → SQS → worker fan-out
  for everything that can be event-driven.
- **Repricers use ANY_OFFER_CHANGED + getCompetitivePricing batching** to
  re-price every 30 seconds across millions of ASINs while respecting
  per-operation throttles. They shard by (seller, ASIN-prefix) across
  worker fleets.
- **Listing-quality optimization**: top brands run Brand Registry
  Manage Your Experiments to A/B test titles and images, then promote
  the winner via patchListingsItem.
- **Multi-marketplace expansion strategy**: launch in US first, prove
  velocity, replicate listing JSON to CA + MX (NA region, same RDT) via
  identical feeds. EU expansion is harder — separate VAT, separate
  language requirements, often separate Brand Registry enrollment.
- **AWD + FBA pipeline**: serious sellers warehouse bulk in AWD (cheap
  per cu ft), trickle into FBA on demand. SP-API exposes this via the
  AWD endpoints; treat AWD as an upstream warehouse to FBA.
- **Inventory placement gaming**: opting for "Amazon-Optimized Shipment
  Splits" is cheaper but spreads stock; "Minimal Shipment Splits" pays
  the placement service fee but consolidates. Top sellers compute the
  break-even per shipment.
- **Brand Analytics is gold**: search frequency rank by keyword,
  click-share by ASIN. Pull weekly via Brand Registry reports and feed
  into Sponsored Products keyword strategy (handled by `amazon_ads`).
- **Custom catalog enrichment**: instead of trusting Amazon's catalog,
  some brands maintain their own image/copy library and re-push via
  feeds whenever Amazon "auto-improves" their listings (a real thing
  Amazon does). LISTINGS_ITEM_ISSUES_CHANGE notifications surface drift.
- **Reimbursement hunting**: FBA loses ~1-3% of inbound units. Bots
  cross-check inbound shipped quantities against received quantities and
  file SAFE-T claims for the diff. Pulls
  `GET_FBA_FULFILLMENT_INBOUND_NONCOMPLIANCE_DATA` and
  `GET_FBA_REIMBURSEMENTS_DATA`.
- **Velocity throttling for product launches**: new ASINs get a 10-30
  unit-per-day cap until Amazon trusts them. The right move is to push
  organic + Sponsored Products together, not flood with PPC.

---

## EOS Usage Patterns

### Lyfe Spectrum Amazon channel launch plan

EOS treats Amazon as a **secondary channel** behind Shopify. The launch
sequence:

**Phase 0 — Pre-flight (weeks -2 to 0)**
- Enroll Lyfe Spectrum LLC as Amazon Professional Seller ($39.99/mo).
- Apply for Brand Registry (need an active USPTO trademark — Lyfe
  Spectrum's wordmark is filed, monitor status).
- Register a private SP-API app via Seller Central → Develop Apps. Save
  refresh token to `eos_ai/.env` as `SP_API_REFRESH_TOKEN`.
- Pin SDK: `python-amazon-sp-api==1.9.*` in `requirements.txt`.
- Create Neon tables: `amazon_listings`, `amazon_orders`,
  `amazon_inventory_snapshots`, `amazon_feed_log`, `amazon_report_log`.

**Phase 1 — Catalog seed (week 1)**
- Build `eos_ai/integrations/amazon_listing_sync.py` that reads Shopify
  products via the `shopify` skill, transforms each variant into a
  `JSON_LISTINGS_FEED` UPDATE message against productType=SHIRT (or
  PANTS, JACKET, etc.), and submits one feed per marketplace.
- Run for US marketplace only first (ATVPDKIKX0DER).
- Subscribe to `LISTINGS_ITEM_ISSUES_CHANGE` and parse issues into
  `amazon_listings.issues` for the morning brief.
- Manually fix any required-attribute gaps in Seller Central, then
  reflect them back into Shopify metafields so the next sync stays clean.

**Phase 2 — FBA inbound (week 2-3)**
- Pick 3 hero SKUs to send into FBA (start small to limit risk).
- Build `scripts/amazon_fba_replenish.py` wrapping the
  `/inbound/fba/2024-03-20/` flow.
- Print box labels, hand to fulfillment partner.
- Wait for receive event; verify via FBA Inventory API.

**Phase 3 — Order automation (week 3-4)**
- Provision SQS queue (use `aws` skill) named `eos-amazon-orders`.
- Call grantless `createDestination` then `createSubscription` for
  `ORDER_CHANGE`, `LISTINGS_ITEM_ISSUES_CHANGE`,
  `FEED_PROCESSING_FINISHED`, `REPORT_PROCESSING_FINISHED`,
  `ANY_OFFER_CHANGED`, `FBA_OUTBOUND_SHIPMENT_STATUS`.
- Build `services/amazon_sqs_worker.py` long-polling the queue, routing
  each notification through `eos_ai/event_manager.py` to the right
  handler.

**Phase 4 — Multi-marketplace + ads (week 5+)**
- Replicate listings to CA + MX via the same feed pipeline (one feed per
  marketplace).
- Hand off Sponsored Products / Sponsored Brands launch to the
  `amazon_ads` skill.
- EU expansion deferred until VAT registration complete.

### Shopify ↔ Amazon inventory sync architecture

```
┌─────────────┐    nightly      ┌────────────────────┐    JSON_LISTINGS_FEED   ┌────────┐
│  Shopify    │ ──read──► EOS ──┤ amazon_listing_sync├──── PARTIAL_UPDATE ────►│ SP-API │
│ (truth)     │                 │  (Neon diff)       │   fulfillment_avail.    │ Feeds  │
└─────────────┘                 └────────────────────┘                         └────────┘
                                          │                                         │
                                          │                                  FEED_PROCESSING_FINISHED
                                          ▼                                         │
                                  Neon amazon_feed_log ◄──── parse result doc ◄────┘

┌─────────────┐ ANY_OFFER_CHANGED  ┌──────────┐                ┌────────┐
│   Buyer     │ ──────► SP-API ───►│ SQS queue│──► EOS worker ─►│ alert  │
│  activity   │                    └──────────┘                 └────────┘
└─────────────┘
       │
       │ purchase
       ▼
   ORDER_CHANGE ──► SQS ──► EOS worker ──► RDT ──► getOrder + items + address
                                                       │
                                                       ▼
                                              Neon memory.orders
                                                       │
                                                       ▼
                                            cognitive_loop revenue update
```

### Weekly report cadence

EOS schedules these reports as recurring via Reports API `createSchedule`:

| Day | Report | Use |
|---|---|---|
| Mon | GET_MERCHANT_LISTINGS_DEFECT_DATA | Surface suppression issues to morning brief |
| Mon | GET_FBA_MYI_UNSUPPRESSED_INVENTORY_DATA | True FBA inventory snapshot |
| Tue | GET_FBA_INVENTORY_PLANNING_DATA | IPI score + planning |
| Wed | GET_SALES_AND_TRAFFIC_REPORT | Velocity per SKU |
| Thu | GET_FBA_REIMBURSEMENTS_DATA | Reimbursement claims feed |
| Fri | GET_VENDOR_REAL_TIME_INVENTORY_REPORT (if 1P) | n/a Lyfe Spectrum |
| Sat | GET_FLAT_FILE_ALL_ORDERS_DATA_BY_LAST_UPDATE_GENERAL | Order reconciliation backstop |
| Sun | GET_BRAND_ANALYTICS_SEARCH_TERMS_REPORT | Keyword strategy feed for amazon_ads |

Each report finishes → REPORT_PROCESSING_FINISHED → SQS → worker
downloads document → writes parsed rows to Neon → Sunday night
consolidation job rolls up into the morning brief.

### FBA vs FBM decision matrix

EOS defaults SKUs to FBM until proven, then promotes to FBA. The
promotion criteria:

| Condition | FBM | FBA |
|---|---|---|
| Sales velocity | <10 / month | ≥10 / month |
| Margin after fees | <30% | ≥30% |
| Item weight | >5 lbs (oversize) | ≤5 lbs |
| Shelf life | >12 months | any |
| Brand-Registry enrolled | optional | required for Prime badge ROI |
| IPI score | n/a | must be >400 to keep replenishment |
| Cash flow | tight (FBA storage fees compound) | healthy |

Rule of thumb: **launch in FBM, switch to FBA when a SKU clears 10/month
for two consecutive months** AND the founder is willing to commit cash
to FBA storage. Lyfe Spectrum apparel is light, high-margin → FBA-friendly
once velocity clears the bar.

### Module placement

```
eos_ai/
  integrations/
    amazon/
      __init__.py
      client.py                  # creds, marketplace map, RDT helper
      listings_sync.py           # Shopify → JSON_LISTINGS_FEED
      orders_pull.py             # SQS-driven order ingestion
      inventory_monitor.py       # daily FBA snapshot + IPI alert
      reports_loop.py            # weekly report scheduler/downloader
      notifications_setup.py     # one-shot SQS destination + subs
services/
  amazon_sqs_worker.py           # long-poll SQS, route to event_manager
scripts/
  amazon_fba_replenish.py        # manual replenishment trigger
  amazon_listing_audit.py        # one-shot defect report parser
```

All Amazon code passes through `eos_ai/integrations/amazon/client.py`
which loads creds from `.env`, instantiates per-marketplace clients, and
exposes a single `amazon_call(operation, **kwargs)` that wraps
`@throttle_retry` and Neon-backed feed/report logging.

## Gotchas

(Comprehensive — see also the abbreviated list in SKILL.md.)

- **AWS SigV4 deprecation confusion** — Most tutorials and SDK READMEs
  still document the old IAM/STS/SigV4 path. As of Oct 2, 2023 it is
  fully optional; Amazon ignores the signature. For new builds, skip IAM
  entirely and use LWA only. Old code that signs is harmless but wastes
  CPU and adds a dependency on `boto3`/STS that you can drop.
- **LWA refresh token revocation** — Refresh tokens have no fixed
  expiry but get invalidated when the seller revokes the app, when you
  re-authorize the same app, or in rare security-event flows. Treat any
  401 from `/auth/o2/token` as "re-onboard." Wrap with a circuit breaker
  so EOS doesn't pound the LWA endpoint.
- **LWA access token caching across processes** — Tokens are 1-hour
  bearer tokens. The SDK caches in process memory. If you fork workers,
  each gets its own. Don't share via Redis without a distributed lock —
  concurrent refreshes can race and you'll get `invalid_grant` errors.
- **Per-operation rate limits, not per-app** — `getOrders` is ~0.0167 TPS
  / 20 burst; `patchListingsItem` is 5 TPS / 10 burst; `createFeed` is
  ~0.0083 TPS / 15 burst. Hitting one operation's limit doesn't affect
  others. Read the rate limit table for every endpoint you use.
- **Application + selling-partner + operation + data-type tiers** —
  Listings throttling specifically has four tiers. Submitting a feed
  with `child_parent_sku_relationship` data triggers a 5 TPS data-type
  cap even if your operation cap is higher.
- **Feeds API cadence** — 1 feed per 5 minutes sustained, 25,000
  messages per JSON_LISTINGS_FEED, 150 MB max body. If you have 100k
  SKUs to update, that's a minimum 20 minutes wall-clock. Plan windows
  accordingly; don't try to push during business hours.
- **JSON_LISTINGS_FEED is the only modern bulk feed** — XML and TSV
  feeds (POST_PRODUCT_DATA, POST_INVENTORY_AVAILABILITY_DATA,
  POST_PRODUCT_PRICING_DATA, POST_PRODUCT_IMAGE_DATA) still work but are
  deprecated. Build new code on JSON_LISTINGS_FEED v2.0 only.
- **Feed status vs feed result** — `getFeed` returns processing status
  (IN_QUEUE, IN_PROGRESS, DONE, CANCELLED, FATAL). `getFeedDocument`
  returns a presigned URL to the **result document**, which contains
  per-message success/failure JSON. Always download and parse the
  result; a "DONE" feed can have every message rejected.
- **Feed result documents are gzipped** — The presigned URL serves
  gzip-compressed JSON. Decompress before parsing. The SDK does this
  for you if you use the helpers.
- **Listings vs Catalog** — Catalog Items API is read-only over Amazon's
  global product database. Listings Items API is read/write but only
  against your seller account's offer for an existing or new ASIN.
  Confusing the two is the #1 listing-creation bug.
- **Product Type Definitions are massive and required** — Creating a
  new listing means satisfying the JSON Schema for that productType
  (e.g., SHIRT) — often 50+ required attributes. Pull the schema with
  Product Type Definitions API and validate locally before submission.
- **Marketplace isolation** — Every call needs `marketplaceIds`. A
  successful putListingsItem in US does NOT propagate to CA, MX, or
  anywhere. Submit per marketplace, even within the same NA region.
- **Pagination drops filters** — When you pass `NextToken` on a
  follow-up getOrders, you must pass ONLY `NextToken` and
  `MarketplaceIds`. Including the original filters (CreatedAfter etc.)
  errors out.
- **Reports are dated in PT, not UTC** — `dataStartTime` and
  `dataEndTime` are interpreted in Pacific Time. UTC mismatch is the #1
  cause of "missing rows" bug reports.
- **Reports retention is 90 days** — You cannot list reports older than
  90 days through the API. Archive your own reportIds.
- **Restricted Data Tokens are per-resource** — One RDT authorizes
  exactly the path you specified, for 1 hour. Mint per call or per
  small batch. You cannot mint a wildcard "PII access for the next hour"
  token.
- **Notifications are SQS or EventBridge only** — There is NO HTTP
  webhook delivery option. You must run an SQS poller or wire up
  EventBridge → Lambda → your endpoint.
- **createDestination is grantless** — It uses LWA client_credentials
  with `scope=sellingpartnerapi::notifications`, NOT a refresh token.
  Grantless calls are easy to misroute through the wrong code path.
- **SQS notifications can duplicate** — At-least-once delivery. Idempotent
  worker, dedupe on `NotificationId`.
- **FIFO SQS queues unsupported** — Notifications only deliver to
  Standard SQS queues.
- **FBA inventory delay** — `/fba/inventory/v1/summaries` is up to 30 min
  behind reality. For real-time, use FBA inventory change notifications.
- **Stranded inventory** — FBA stock with no active listing accrues
  storage fees. Resolve via Seller Central → Inventory → Fix Stranded
  Inventory. The `GET_STRANDED_INVENTORY_UI_DATA` report surfaces it.
- **Suppression states** — Live, search-suppressed, buy-box-suppressed,
  fully suppressed. Causes: missing required attributes, image quality,
  brand mismatch, restricted category. `GET_MERCHANT_LISTINGS_DEFECT_DATA`
  is authoritative.
- **IPI score below 400** — Triggers immediate restock-limit cuts as of
  2025 (no quarterly grace period). Stranded inventory + slow movers
  drive IPI down.
- **Storage Utilization Surcharge (April 2025+)** — Holding > 26 weeks of
  forward inventory triggers monthly surcharge. Plan reorder rhythm.
- **Long-term storage at 271 days** — Was 365 until 2025. Trim aged
  inventory via removal/disposal orders before it crosses 271 days.
- **Inbound Placement Service fees** — Cheaper "Amazon-Optimized" splits
  spread stock across multiple FCs; "Minimal Splits" costs more but
  consolidates. Both are real money — choose deliberately per shipment.
- **`fba/inbound/v0` is deprecated** — Use `inbound/fba/2024-03-20`. Old
  v0 still works for now but new shipment plans should be on the new
  endpoints.
- **`Pending` order trap** — Orders sit in `Pending` while Amazon
  pre-authorizes the buyer's card; you cannot fulfill until `Unshipped`.
  Don't error on Pending — wait for the next ORDER_CHANGE notification.
- **30-min cancellation grace** — Buyers can cancel any order in the
  first 30 minutes with no seller action. Don't ship Unshipped orders
  in their first 30 minutes; you'll eat the return.
- **Order date filters: CreatedAfter vs LastUpdatedAfter** —
  `LastUpdatedAfter` catches status changes; `CreatedAfter` does not.
  For incremental sync, always use `LastUpdatedAfter`.
- **Brand Registry vs trademark mismatches** — Brand Registry requires
  an active registered trademark. Pending applications via Amazon IP
  Accelerator can also enroll, but with reduced capabilities. Lyfe
  Spectrum wordmark filing status drives Brand Registry timing.
- **Professional plan required** — Programmatic SP-API access requires
  the $39.99/mo Professional Selling Plan. Individuals cannot use SP-API.
- **Sandbox does not replay your data** — Sandbox returns canned static
  responses keyed by marker values. Useful for shape validation only;
  always smoke-test against production with throwaway SKUs.
- **EU + UK split post-Brexit** — UK is EU endpoint but separate
  marketplace; selling in EU and UK requires two listing workflows and
  often two VAT setups.
- **A+ Content has a 3-7 day review queue** — Submitting via API doesn't
  publish immediately; status via `getContentDocument`.
- **Buy with Prime + Shopify** — Now natively integrated, but cross
  reference with `shopify` skill to avoid duplicate fulfillment paths.
- **Time-to-first-revenue** — Amazon listing approval, Brand Registry
  enrollment, FBA inbound transit time stack to ~2-4 weeks from "submit
  app" to "first FBA sale." Plan launch timeline accordingly.
