---
name: amazon_seller_central
description: "Use when managing Amazon Seller Central inventory/orders/listings/FBA via SP-API, syncing Shopify→Amazon product catalogs, pulling Amazon orders into EOS, or building Lyfe Spectrum's Amazon channel strategy. For Amazon ads use amazon_ads; for affiliate links use amazon_associates."
allowed-tools: "Read, Bash, Write, Edit, WebFetch"
version: 1.0
source_url: "https://developer-docs.amazon.com/sp-api"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "SP-API (versioned per endpoint: orders/v0, catalog/2022-04-01, listings/2021-08-01, fba/inventory/v1, feeds/2021-06-30, reports/2021-06-30, notifications/v1, tokens/2021-03-01)"
sdk_version: "python-amazon-sp-api 1.9 (saleweaver)"
speed_category: stable
---

# Tool: Amazon Seller Central (SP-API)

## What This Tool Does

Amazon's Selling Partner API (SP-API) is the post-2020 replacement for the
legacy MWS API. It is the only programmatic surface that lets a seller drive
their Amazon business: catalog, listings, inventory, FBA inbound and stock,
orders, pricing, fees, finances, feeds, reports, A+ content, merchant
fulfillment, notifications, and tokens. Every operation is REST/JSON over
HTTPS, scoped to one of three regional endpoints, and authorized by a
Login-with-Amazon (LWA) refresh token bound to a Developer Central app the
seller has explicitly authorized.

Core capabilities:

- **Catalog & Listings** — read Amazon's product catalog (catalog/2022-04-01),
  create/update/patch your own listings (listings/2021-08-01) using JSON Patch
  semantics against Amazon-defined product type schemas
- **Inventory & FBA** — query FBA on-hand and inbound (fba/inventory/v1),
  build inbound shipment plans (fba/inbound/v0 + 2024 inbound v2024-03-20),
  manage removal orders, multi-channel fulfillment
- **Orders** — pull, paginate, and watch orders (orders/v0); request a
  Restricted Data Token (RDT) to read PII fields like shipping address
- **Feeds** — submit bulk JSON feeds (feeds/2021-06-30) to update thousands
  of listings, prices, or inventory levels in one async job
- **Reports** — request 200+ report types (reports/2021-06-30) covering
  sales, inventory, returns, settlements, advertising, brand analytics
- **Notifications** — subscribe to push events over Amazon SQS or
  EventBridge (notifications/v1) for ORDER_CHANGE, ANY_OFFER_CHANGED,
  FEE_PROMOTION, FEED_PROCESSING_FINISHED, REPORT_PROCESSING_FINISHED
- **Pricing & Fees** — competitive prices, Buy Box, fee previews
- **Tokens** — mint short-lived RDTs for any restricted operation

## EOS Integration

Amazon Seller Central is a **secondary sales channel** for Lyfe Spectrum.
Shopify is and remains the primary storefront (see `shopify` skill in this
same wave) — Amazon exists to extend distribution and tap Prime demand once
the Shopify funnel is proven.

Canonical EOS data flows:

- **Shopify → Amazon listing sync**: Lyfe Spectrum apparel SKUs live in
  Shopify as the source of truth. A nightly job reads `products.json` from
  Shopify, transforms each variant into a `JSON_LISTINGS_FEED` message
  (UPDATE op against the APPAREL product type), and submits one feed per
  marketplace via `Feeds().submit_feed()`. Inventory deltas use
  `JSON_LISTINGS_FEED` with `PARTIAL_UPDATE` and only the
  `fulfillment_availability` attribute — keeps the feed under 25k SKUs and
  the 5-feeds-per-5-min budget.
- **Amazon → EOS order pull**: A 15-min cognitive_loop scheduled task calls
  `Orders().get_orders(LastUpdatedAfter=...)`, paginates with the
  `@load_all_pages` decorator, mints an RDT for any order needing PII, and
  writes each `AmazonOrderId` into Neon `memory.orders` with channel='amazon'.
- **FBA inventory monitoring**: Daily `FbaInventory().get_inventory_summary_marketplace()`
  call streams quantities into Neon. The orchestrator alerts the founder if
  any SKU drops below reorder point or if the IPI score (pulled via
  Brand Analytics report) crosses 400.
- **Compliance reporting**: Weekly `GET_MERCHANT_LISTINGS_ALL_DATA` and
  `GET_FBA_INVENTORY_PLANNING_DATA` reports archived to Neon for audit and
  to feed the morning brief.
- **Cross-skill boundaries**: campaign data lives in `amazon_ads`; affiliate
  link generation lives in `amazon_associates`; SQS queue provisioning for
  notifications uses the coarse `aws` skill.

## Authentication

SP-API authentication is **LWA-only** as of October 2, 2023. AWS IAM roles
and AWS Signature V4 are no longer required — Amazon disregards the SigV4
signature on incoming requests and authorizes purely on the LWA bearer token.
Old code that still signs is harmless but wasteful.

Setup (one time, in Seller Central):

1. Register as a developer in Seller Central → Apps & Services → Develop
   Apps. Create a "private" app (self-authorized — covers your own seller
   accounts only) or "public" (listed on the Marketplace Appstore).
2. Choose data roles (Product Listing, Inventory, Orders, Pricing, etc.).
   Restricted PII roles require a separate compliance review.
3. Self-authorize the app on each marketplace you sell on. Capture the
   `refresh_token` (long-lived) and the LWA app's `client_id` + `client_secret`.

Per request:

```python
# python-amazon-sp-api handles the full token dance for you
from sp_api.api import Orders
from sp_api.base import Marketplaces

creds = dict(
    refresh_token=os.environ['SP_API_REFRESH_TOKEN'],
    lwa_app_id=os.environ['LWA_APP_ID'],
    lwa_client_secret=os.environ['LWA_CLIENT_SECRET'],
)
orders = Orders(credentials=creds, marketplace=Marketplaces.US)
```

Behind the scenes the library POSTs to `https://api.amazon.com/auth/o2/token`
with `grant_type=refresh_token`, gets a 1-hour LWA access token, and sets
`x-amz-access-token: Atza|...` on every SP-API call. Tokens are cached in
process memory until expiry.

**Grantless operations** (no seller refresh token needed): notifications
`createDestination`, applications `getAuthorizationCode`. These use a
client-credentials LWA grant with scope `sellingpartnerapi::notifications`
or `sellingpartnerapi::migration`.

**Restricted operations** (PII): mint a Restricted Data Token first.

```python
from sp_api.api import Tokens
rdt = Tokens(credentials=creds).create_restricted_data_token(
    restrictedResources=[{
        "method": "GET",
        "path": f"/orders/v0/orders/{order_id}",
        "dataElements": ["buyerInfo", "shippingAddress"],
    }]
).payload['restrictedDataToken']
# Pass rdt as restricted_data_token to subsequent get_order call
```

## Quick Reference

### List recent orders (with pagination + retry)

```python
from sp_api.api import Orders
from sp_api.util import throttle_retry, load_all_pages
from datetime import datetime, timedelta, timezone

@throttle_retry()
@load_all_pages()
def iter_orders(**kwargs):
    return Orders(credentials=creds).get_orders(**kwargs)

since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
for page in iter_orders(LastUpdatedAfter=since, MarketplaceIds=['ATVPDKIKX0DER']):
    for o in page.payload.get('Orders', []):
        print(o['AmazonOrderId'], o['OrderStatus'], o['OrderTotal'])
```

### Update inventory via JSON_LISTINGS_FEED

```python
from sp_api.api import Feeds
import json, io

feed = {
    "header": {"sellerId": SELLER_ID, "version": "2.0", "issueLocale": "en_US"},
    "messages": [
        {
            "messageId": i + 1,
            "sku": sku,
            "operationType": "PARTIAL_UPDATE",
            "productType": "SHIRT",
            "attributes": {
                "fulfillment_availability": [
                    {"fulfillment_channel_code": "DEFAULT", "quantity": qty}
                ],
            },
        }
        for i, (sku, qty) in enumerate(inventory_deltas.items())
    ],
}

f = Feeds(credentials=creds)
doc = f.create_feed_document(content_type="application/json").payload
f.upload(doc['url'], io.BytesIO(json.dumps(feed).encode()), content_type="application/json")
res = f.create_feed(
    feedType="JSON_LISTINGS_FEED",
    marketplaceIds=['ATVPDKIKX0DER'],
    inputFeedDocumentId=doc['feedDocumentId'],
)
print("feedId:", res.payload['feedId'])
```

### Poll a feed to completion

```python
import time
feed_id = res.payload['feedId']
while True:
    status = f.get_feed(feedId=feed_id).payload
    if status['processingStatus'] in ('DONE', 'CANCELLED', 'FATAL'):
        break
    time.sleep(30)
result_doc_id = status.get('resultFeedDocumentId')
if result_doc_id:
    result = f.get_feed_document(feedDocumentId=result_doc_id).payload
    # Download and parse the processing report (JSON, contains per-message issues)
```

### Request a report and download it

```python
from sp_api.api import ReportsV2
from sp_api.base.reportTypes import ReportType

r = ReportsV2(credentials=creds)
created = r.create_report(
    reportType=ReportType.GET_FBA_MYI_UNSUPPRESSED_INVENTORY_DATA,
    marketplaceIds=['ATVPDKIKX0DER'],
).payload
report_id = created['reportId']

while True:
    s = r.get_report(reportId=report_id).payload
    if s['processingStatus'] in ('DONE', 'CANCELLED', 'FATAL'):
        break
    time.sleep(30)

doc = r.get_report_document(reportDocumentId=s['reportDocumentId']).payload
# doc['url'] is a presigned S3 URL valid for 5 minutes; download with requests.get
```

### FBA inventory snapshot

```python
from sp_api.api import FbaInventory
inv = FbaInventory(credentials=creds).get_inventory_summary_marketplace(
    granularityType='Marketplace',
    granularityId='ATVPDKIKX0DER',
    marketplaceIds=['ATVPDKIKX0DER'],
    details=True,
).payload
for item in inv['inventorySummaries']:
    print(item['sellerSku'], item['totalQuantity'])
```

## Conceptual Model

**SP-API is a federation of versioned, throttled microservices behind one
LWA gate.** There is no single "API version" — every endpoint family is
independently versioned (orders/v0, catalog/2022-04-01, listings/2021-08-01,
feeds/2021-06-30, reports/2021-06-30) and has its own rate-limit bucket
(token bucket: rate refill per second, burst ceiling). One global LWA token
unlocks all of them, but throttling is per-operation per-seller.

**Bulk = async, single = sync.** Two completely separate paradigms:
- **Sync REST**: getOrder, patchListingsItem, getInventorySummaries — call,
  get JSON back, throttled tightly (often <1 TPS sustained).
- **Async document**: feeds and reports — submit a job, poll for terminal
  status, download a presigned S3 document. This is how you do bulk: one
  feed can carry 25,000 messages and replaces 25,000 sync calls.

**Three regions, opaque marketplaces.** NA / EU / FE endpoints. Each region
holds its own marketplaces (US ATVPDKIKX0DER, CA, MX, BR in NA; UK, DE, FR,
IT, ES, NL, SE, PL, BE, IN, AE, SA, EG, TR in EU; JP, AU, SG in FE). A
single LWA token can talk to all marketplaces in the regions it was
authorized for, but every call must specify `marketplaceIds`.

**Buy Box, Brand Registry, Prime — gated outside the API.** SP-API exposes
them once you qualify but does not grant qualification. Brand Registry
unlocks A+ content, Sponsored Brands, IP enforcement; Prime eligibility is
a function of FBA + IPI score. The API tells you whether you have them;
getting them is a Seller Central account flow.

## Gotchas

- **AWS SigV4 deprecation confusion** — As of Oct 2, 2023 SigV4 is no
  longer required, but tutorials and old SDKs still show IAM role setup.
  Skip the IAM steps entirely. If you already have an IAM role, ignore it.
- **LWA refresh token revocation** — Refresh tokens do NOT expire on a
  timer but DO get invalidated if the seller revokes the app or
  re-authorizes. Treat 401 from `/auth/o2/token` as "re-onboard the seller."
- **LWA access token = 1 hour, do not cache across processes** — Mint
  per-process. The SDK caches in memory; if you fork workers, each gets
  its own token. Don't share via Redis without locking.
- **Rate limit per operation, NOT per app** — getOrders is ~0.0167 TPS
  sustained / 20 burst; patchListingsItem is 5 TPS / 10 burst; createFeed
  is ~0.0083 TPS (1 per 5 min) / 15 burst. Hitting one operation's limit
  does not affect others. Always read the per-endpoint table.
- **Feeds API limit is brutal** — 1 feed per 5 min sustained, max 25,000
  messages per JSON_LISTINGS_FEED. If you have 100k SKUs you cannot push
  more than ~300k SKU updates per hour. Plan around this.
- **FBA vs FBM is a per-listing attribute, not a per-account flag** —
  `fulfillment_availability.fulfillment_channel_code = DEFAULT` means
  merchant-fulfilled (FBM); `AMAZON_NA` (or regional equivalent) means
  Amazon-fulfilled (FBA). Same SKU can't be both at the same time.
- **Listings vs Catalog confusion** — Catalog Items API is read-only over
  Amazon's global product database (every ASIN). Listings Items API is
  read/write but only against your seller account's offers. To "create a
  listing on an existing ASIN" use Listings PATCH; to "create a brand new
  product" requires the full LISTING productType schema with all required
  attributes for that category.
- **Marketplace isolation** — Every call needs `marketplaceIds`. A
  successful putListingsItem in US does NOT propagate to CA or MX. You
  must submit per marketplace, even within the same NA region.
- **Professional plan required** — Programmatic SP-API access requires the
  $39.99/mo Professional Selling Plan. Individual sellers cannot use SP-API.
- **JSON_LISTINGS_FEED replaced flat-file feeds in 2024** — Old XML and TSV
  feed types still exist but are deprecated. Build new code on
  JSON_LISTINGS_FEED v2.0 only.
- **Feed processing report is not the feed status** — `getFeed` returns
  job status; `getFeedDocument` returns the result document with per-message
  success/failure. Always parse the result doc — a "DONE" feed can have
  every message rejected.
- **IPI score gotcha** — Drops below 400 trigger immediate restock limit
  cuts (no quarterly grace as of 2025). Stranded inventory is the #1 IPI
  killer; resolve via Seller Central → Inventory → Fix Stranded Inventory.
- **Suppression dance** — A listing can be live, search-suppressed,
  buy-box suppressed, or fully suppressed.
  `GET_MERCHANT_LISTINGS_DEFECT_DATA` is the authoritative report.
- **Restricted Data Tokens are per-resource** — One RDT authorizes exactly
  the path you specified. Mint per-call or per-batch.
- **EU + UK split post-Brexit** — UK is EU endpoint but separate
  marketplace; selling in EU and UK requires two listing workflows and
  often two VAT setups.

See references/best_practices.md for the full 19-section creator-level knowledge base.
