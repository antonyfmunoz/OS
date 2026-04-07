# Amazon Associates / PA-API 5.0 — Creator-Level Best Practices

Source: https://webservices.amazon.com/paapi5/documentation/
Last researched: 2026-04-06
API version: PA-API 5.0 (`com.amazon.paapi5.v1`) — RETIRES 2026-05-15
Successor: Amazon Creators API (https://affiliate-program.amazon.com/creatorsapi/docs/)

This document is the deep reference for the `amazon_associates` skill. The
skill's SKILL.md is the operator-level summary; this is the engineering-level
ground truth. Read this before building anything against PA-API.

---

## Authentication

PA-API 5.0 uses **AWS Signature Version 4** (`AWS4-HMAC-SHA256`), the same
signing scheme as classic AWS services, but with three twists that trip up
every first-time integrator:

1. The **service name** in the credential scope and string-to-sign is
   `ProductAdvertisingAPI` — NOT `paapi`, NOT `productadvertisingapiv1`,
   NOT `paapi5`. Get it wrong and you get an opaque `Signature does not
   match` 403 with no further information.
2. The credentials are **not IAM credentials**. They are issued from
   Associates Central → Tools → Product Advertising API → Manage Your
   Credentials. The Access Key looks like an IAM key (`AKIA...`) but it
   only works against `webservices.amazon.*` and only for the marketplace
   it was issued in.
3. Every request must include `content-encoding: amz-1.0` as a signed
   header. The SDKs include it; hand-rolled clients usually forget it
   and produce another opaque signature error.

The credential triple is:
- **Access Key** (`AMAZON_ACCESS_KEY`) — public identifier, ~20 chars
- **Secret Key** (`AMAZON_SECRET_KEY`) — shown ONCE at creation, never
  retrievable. Lose it, generate new credentials.
- **Partner Tag** (`AMAZON_PARTNER_TAG`) — your Associate Tag, e.g.
  `empyrean-20`. The suffix encodes the marketplace: `-20` US, `-21` UK,
  `-22` DE, `-23` FR, etc.

PartnerTag is not part of the signature. It is a body parameter of every
request and the only thing Amazon uses to attribute sales. Sign correctly
with the wrong tag and you authenticate fine but earn nothing.

Account requirements that block the API even when signing is correct:
- Active Amazon Associates account in good standing
- At least 3 qualifying sales within 180 days of credential issuance, or
  the credentials are revoked silently (next call returns 401)
- Continued sales activity — long silent periods trigger revocation
- Each marketplace is a separate account: a US Associates account cannot
  query `webservices.amazon.co.uk`. To go multi-region you sign up for
  every marketplace separately and maintain separate credentials and tags.

The Creators API (the successor) uses different credentials issued from
the Creators API section of Associates Central. Existing PA-API access keys
will NOT work against the Creators API endpoint. Plan a parallel-credentials
period during migration.

---

## Core Operations with Exact Signatures

PA-API 5.0 exposes exactly five operations. All are POST to
`https://{host}/paapi5/{operation-slug}` with a JSON body, an
`x-amz-target` header naming the operation, and SigV4 signing.

### SearchItems

Endpoint: `POST https://webservices.amazon.com/paapi5/searchitems`
Target: `com.amazon.paapi5.v1.ProductAdvertisingAPIv1.SearchItems`

Request body shape (canonical fields):

```json
{
  "Keywords": "mechanical keyboard",
  "SearchIndex": "Electronics",
  "ItemCount": 10,
  "ItemPage": 1,
  "Resources": [
    "Images.Primary.Large",
    "ItemInfo.Title",
    "ItemInfo.Features",
    "Offers.Listings.Price"
  ],
  "PartnerTag": "empyrean-20",
  "PartnerType": "Associates",
  "Marketplace": "www.amazon.com"
}
```

Optional filters: `Brand`, `BrowseNodeId`, `Condition` (`New|Used|Collectible|Refurbished|Any`),
`DeliveryFlags`, `MaxPrice`, `MinPrice`, `MinReviewsRating`, `MinSavingPercent`,
`Title`, `Author`, `Actor`, `Artist`, `Availability`, `CurrencyOfPreference`,
`LanguagesOfPreference`, `Merchant` (`All|Amazon`), `OfferCount`, `SortBy`
(`AvgCustomerReviews|Featured|NewestArrivals|Price:HighToLow|Price:LowToHigh|Relevance`).

Returns up to 10 items per call. Maximum reachable depth is 10 pages × 10
items = 100 items per query, regardless of total result count. Beyond
ItemPage=10 you get an `InvalidParameterValue` error.

Python SDK signature (`python-amazon-paapi`):

```python
search_items(
    keywords: str | None = None,
    actor: str | None = None,
    artist: str | None = None,
    author: str | None = None,
    brand: str | None = None,
    title: str | None = None,
    availability: str | None = None,
    browse_node_id: str | None = None,
    condition: str | None = None,
    delivery_flags: list[str] | None = None,
    max_price: int | None = None,    # in cents
    min_price: int | None = None,
    min_reviews_rating: int | None = None,
    min_saving_percent: int | None = None,
    offer_count: int | None = None,
    search_index: str = "All",
    sort_by: str | None = None,
    item_count: int = 10,
    item_page: int = 1,
    resources: list[str] | None = None,
) -> SearchResult
```

### GetItems

Endpoint: `POST https://webservices.amazon.com/paapi5/getitems`
Target: `com.amazon.paapi5.v1.ProductAdvertisingAPIv1.GetItems`

Body:

```json
{
  "ItemIds": ["B08N5WRWNW", "B0CHX1W1XY"],
  "ItemIdType": "ASIN",
  "Resources": [
    "Images.Primary.Large",
    "ItemInfo.Title",
    "Offers.Listings.Price"
  ],
  "PartnerTag": "empyrean-20",
  "PartnerType": "Associates",
  "Marketplace": "www.amazon.com"
}
```

`ItemIdType` is always `ASIN` in PA-API 5.0 (UPC/EAN/ISBN as primary keys
were removed in the migration from PA-API 4). Maximum 10 ItemIds per call.
Larger batches return `InvalidParameterValue`.

Python SDK:

```python
get_items(
    items: list[str],     # 1-10 ASINs
    condition: str | None = None,
    currency_of_preference: str | None = None,
    languages_of_preference: list[str] | None = None,
    merchant: str | None = None,
    offer_count: int | None = None,
    resources: list[str] | None = None,
) -> list[Item]
```

### GetVariations

Endpoint: `POST https://webservices.amazon.com/paapi5/getvariations`
Target: `com.amazon.paapi5.v1.ProductAdvertisingAPIv1.GetVariations`

Body:

```json
{
  "ASIN": "B08N5WRWNW",
  "VariationCount": 10,
  "VariationPage": 1,
  "Resources": ["VariationSummary.Price.HighestPrice", "Images.Primary.Medium"],
  "PartnerTag": "empyrean-20",
  "PartnerType": "Associates",
  "Marketplace": "www.amazon.com"
}
```

Returns up to 10 variations per page. The input ASIN can be either parent
or child; PA-API resolves to the parent and returns siblings. There is a
`VariationSummary` resource that returns aggregate price ranges across all
variations without enumerating them.

### GetBrowseNodes

Endpoint: `POST https://webservices.amazon.com/paapi5/getbrowsenodes`
Target: `com.amazon.paapi5.v1.ProductAdvertisingAPIv1.GetBrowseNodes`

Body:

```json
{
  "BrowseNodeIds": ["283155"],
  "Resources": ["BrowseNodes.Ancestor", "BrowseNodes.Children"],
  "LanguagesOfPreference": ["en_US"],
  "PartnerTag": "empyrean-20",
  "PartnerType": "Associates",
  "Marketplace": "www.amazon.com"
}
```

Up to 10 browse node IDs per call. Use this to walk the category tree —
start at a known root (Books = 283155 in US), expand `BrowseNodes.Children`
to descend, `BrowseNodes.Ancestor` to ascend.

### Resources Parameter (the most important parameter in PA-API)

Resources is a list of dotted strings naming exactly which fields to
return. Field paths are hierarchical and case-sensitive. Common ones:

```
BrowseNodeInfo.BrowseNodes
BrowseNodeInfo.BrowseNodes.Ancestor
BrowseNodeInfo.BrowseNodes.SalesRank
BrowseNodeInfo.WebsiteSalesRank
CustomerReviews.Count
CustomerReviews.StarRating
Images.Primary.Small
Images.Primary.Medium
Images.Primary.Large
Images.Variants.Small
Images.Variants.Medium
Images.Variants.Large
ItemInfo.ByLineInfo
ItemInfo.ContentInfo
ItemInfo.ContentRating
ItemInfo.Classifications
ItemInfo.ExternalIds
ItemInfo.Features
ItemInfo.ManufactureInfo
ItemInfo.ProductInfo
ItemInfo.TechnicalInfo
ItemInfo.Title
ItemInfo.TradeInInfo
Offers.Listings.Availability.MaxOrderQuantity
Offers.Listings.Availability.Message
Offers.Listings.Availability.MinOrderQuantity
Offers.Listings.Availability.Type
Offers.Listings.Condition
Offers.Listings.DeliveryInfo.IsAmazonFulfilled
Offers.Listings.DeliveryInfo.IsFreeShippingEligible
Offers.Listings.DeliveryInfo.IsPrimeEligible
Offers.Listings.IsBuyBoxWinner
Offers.Listings.LoyaltyPoints.Points
Offers.Listings.MerchantInfo
Offers.Listings.Price
Offers.Listings.ProgramEligibility.IsPrimeExclusive
Offers.Listings.ProgramEligibility.IsPrimePantry
Offers.Listings.Promotions
Offers.Listings.SavingBasis
Offers.Summaries.HighestPrice
Offers.Summaries.LowestPrice
Offers.Summaries.OfferCount
ParentASIN
RentalOffers.Listings.Availability.Message
SearchRefinements
VariationSummary.Price.HighestPrice
VariationSummary.Price.LowestPrice
VariationSummary.VariationDimension
```

Maintain a canonical list per operation in code. Inlining different
Resources lists in different call sites is the #1 cause of "missing data"
bugs in PA-API integrations.

---

## Pagination Patterns

PA-API pagination is severely limited and you should design around it.

- **SearchItems**: `ItemPage` 1..10, `ItemCount` 1..10. Maximum reachable
  depth is 100 items per query. There is no cursor, no continuation token,
  no way to go beyond page 10. If the result set is larger than 100, you
  must narrow with filters (BrowseNodeId, MinPrice/MaxPrice, Brand) and
  re-query each shard.
- **GetVariations**: `VariationPage` 1..10, `VariationCount` 1..10. Same
  100-item ceiling.
- **GetItems**: not paginated — you batch 10 ASINs per call yourself.
- **GetBrowseNodes**: not paginated — 10 node IDs per call.

Idiomatic SearchItems pagination:

```python
all_items = []
for page in range(1, 11):
    result = amazon.search_items(
        keywords="tactical luxury watch",
        item_count=10,
        item_page=page,
        resources=RESOURCES_SEARCH,
    )
    if not result.items:
        break
    all_items.extend(result.items)
    time.sleep(1.1)  # respect 1 TPS starter quota
```

To go beyond 100 results, shard by price band, brand, or browse node and
union the results yourself.

---

## Rate Limits

- Starter quota on credential issuance: **1 TPS, 8640 TPD** for the first
  30 days.
- After 30 days, quota is recalculated **daily** based on shipped item
  revenue from PA-API-tagged sales in the trailing 30 days:
  - **+1 TPD per 5¢ of shipped revenue**
  - **+1 TPS per $4320 of shipped revenue**, capped at **10 TPS**
- TPS and TPD are independent throttles. You can be under TPS and still
  get throttled because TPD is exhausted. The 429 error message does not
  distinguish.
- The throttle is **per-account**, not per-credential. Rotating keys does
  not reset quota.
- The Creators API has its own rate limit table — different from PA-API.

The practical reality for pre-revenue accounts: you have ~6 calls per
minute averaged across the day, no burst, and TPD exhaustion is the
binding constraint. Cache everything.

---

## Error Codes and Recovery

PA-API returns HTTP status + a JSON `Errors` array. The interesting codes:

- **400 InvalidParameterValue** — bad ASIN format, batch >10, ItemPage>10,
  unrecognized SearchIndex, malformed Resources entry. NOT retryable —
  fix the request.
- **400 InvalidPartnerTag** — PartnerTag does not match an active tracking
  ID for this account/marketplace. NOT retryable.
- **400 InvalidAssociate** — account is not approved for the marketplace
  you're querying, or has been revoked for inactivity. NOT retryable —
  fix the account.
- **401 UnrecognizedClient** — bad Access Key or signing failure. Check
  service name, region, content-encoding header.
- **403 IncompleteSignature / SignatureDoesNotMatch** — SigV4 canonical
  request hash mismatch. Almost always: wrong service name, wrong region,
  missing `content-encoding: amz-1.0`, body whitespace differences between
  signing and sending. NOT retryable until you fix the client.
- **404 ItemNotAccessible** — item exists but is not available in this
  marketplace, or has been delisted, or is restricted. NOT retryable —
  remove the ASIN.
- **429 TooManyRequests** — TPS or TPD throttle. Retry with exponential
  backoff: 1s, 2s, 4s, 8s, then drop the request and let it retry on
  the next cron pass. Do NOT hammer.
- **500 InternalFailure** — Amazon side. Retry once after 2s, then drop.
- **503 ServiceUnavailable** — extended outage. Drop and retry next cron.

The Errors array can contain multiple entries per response — a partial
GetItems batch can succeed for 8 ASINs and fail with `ItemNotAccessible`
for 2. Always iterate `Errors`, do not assume one error per response.

Recovery pattern (Python):

```python
def call_with_retry(fn, *args, **kwargs):
    for attempt in range(4):
        try:
            return fn(*args, **kwargs)
        except AmazonException as e:
            if "TooManyRequests" in str(e):
                time.sleep(2 ** attempt)
                continue
            raise
    raise RuntimeError("PA-API throttled, gave up after 4 attempts")
```

---

## SDK Idioms

Recommended SDKs:

- **Python**: `python-amazon-paapi` (high-level wrapper, country=enum,
  pythonic). Lower-level: `paapi5-python-sdk` (Amazon's official, generated
  from OpenAPI, verbose).
- **Node.js**: `paapi5-nodejs-sdk` (official, on npm via community fork
  `tobias7an/paapi5-nodejs-sdk` because Amazon's distribution is broken).
- **PHP**: `paapi5-php-sdk` (official) or community wrappers.
- **Java**: `paapi5-java-sdk` (official, used in Amazon's docs examples).

Idiomatic Python (`python-amazon-paapi`):

```python
from amazon_paapi import AmazonApi
from amazon_paapi.models import Country

amazon = AmazonApi(
    key=os.getenv("AMAZON_ACCESS_KEY"),
    secret=os.getenv("AMAZON_SECRET_KEY"),
    tag=os.getenv("AMAZON_PARTNER_TAG"),
    country=Country.US,
    throttling=1.1,    # seconds between calls, client-side rate limiter
)

# Single ASIN
item = amazon.get_items(items="B08N5WRWNW", resources=RESOURCES_ITEM)[0]

# Batch
items = amazon.get_items(
    items=["B08N5WRWNW", "B0CHX1W1XY", "B09G9BL5CP"],
    resources=RESOURCES_ITEM,
)
```

The `throttling` parameter is a client-side sleep, not a real rate
limiter. It does not coordinate across processes. For multi-process
safety, put a Postgres-backed semaphore in front of the client.

Lower-level (`paapi5-python-sdk`) requires constructing a
`DefaultApi` instance, building `SearchItemsRequest` / `GetItemsRequest`
objects with explicit Resources enums, and handling the
`ApiException` class. Verbose but lets you set custom retry policy.

---

## Anti-Patterns

- **Hand-rolling SigV4**. Every PA-API blog post that fails fails on the
  canonical request hash. Use an SDK.
- **Inlining Resources lists in every call site**. You will forget
  `Offers.Listings.Price` somewhere and ship a "free product" bug.
- **Stripping or rewriting `DetailPageURL`**. The URL contains
  `tag=`, `linkCode=`, `ref_=` parameters that all contribute to
  attribution. Use it as-is.
- **Constructing affiliate links by hand without the `tag` query
  parameter**. Untracked clicks earn nothing.
- **Caching `Offers.Listings.Price` for >24h**. Amazon's TOS forbids
  displaying stale prices. Refresh on read or write a TTL of ≤24h.
- **Using one Associate Tag across marketplaces**. The marketplace
  suffix encodes the locale; cross-marketplace tags don't track.
- **Polling for price changes**. PA-API has no diff API, no webhooks.
  Polling burns TPD with no benefit. Cache + scheduled refresh instead.
- **Treating PA-API as a search engine for the whole catalog**. The
  100-item ceiling per query makes deep search impossible. Use it for
  shallow research and known-ASIN hydration.
- **Building anything new on PA-API in Q2 2026.** Sunset is May 15.
  Build against the Creators API.
- **Catching `Exception` around the SDK**. PA-API throws specific error
  types and you need to distinguish 429-retry from 400-fix.
- **Storing the Secret Key in code, settings.json, or git**. It's shown
  once. Put it in `eos_ai/.env` immediately and never anywhere else.

---

## Data Model

The fundamental object is the **Item**, keyed by 10-character **ASIN**
(Amazon Standard Identification Number). ASINs are alphanumeric, mostly
`B0` prefixed for products created since ~2000, ISBN-10 for books.

Item structure (when all Resources are requested):

```
Item
├── ASIN                     str (10 chars)
├── ParentASIN               str | null
├── DetailPageURL            str (already includes ?tag=...&linkCode=...)
├── ItemInfo
│   ├── Title.DisplayValue
│   ├── ByLineInfo (Brand, Manufacturer, Contributors)
│   ├── Features.DisplayValues   list[str]
│   ├── ContentInfo (Edition, Languages, PagesCount, PublicationDate)
│   ├── ContentRating
│   ├── ExternalIds (EANs, ISBNs, UPCs)
│   ├── ManufactureInfo (ItemPartNumber, Model, Warranty)
│   ├── ProductInfo (Color, IsAdultProduct, ItemDimensions, ReleaseDate, Size, UnitCount)
│   ├── TechnicalInfo (Formats, EnergyEfficiencyClass)
│   └── Classifications (Binding, ProductGroup)
├── Images
│   ├── Primary
│   │   ├── Small.URL  (75px)
│   │   ├── Medium.URL (160px)
│   │   └── Large.URL  (500px)
│   └── Variants[]    (alt-angle and lifestyle shots, same dimensions)
├── Offers
│   ├── Listings[]    (current buy box and merchant offers)
│   │   ├── Id
│   │   ├── Price.Amount, Price.Currency, Price.DisplayAmount
│   │   ├── SavingBasis (was-price)
│   │   ├── Availability (Type, Message, MinOrderQuantity, MaxOrderQuantity)
│   │   ├── Condition (New|Used|Collectible|Refurbished)
│   │   ├── DeliveryInfo (IsAmazonFulfilled, IsPrimeEligible, IsFreeShippingEligible)
│   │   ├── IsBuyBoxWinner
│   │   ├── LoyaltyPoints.Points
│   │   ├── MerchantInfo (Id, Name, FeedbackCount, FeedbackRating)
│   │   ├── ProgramEligibility (IsPrimeExclusive, IsPrimePantry)
│   │   └── Promotions[]
│   └── Summaries[]   (aggregated min/max/count by Condition)
├── BrowseNodeInfo
│   ├── BrowseNodes[]   (the category leaves this item belongs to)
│   │   ├── Id
│   │   ├── DisplayName
│   │   ├── ContextFreeName
│   │   ├── IsRoot
│   │   ├── Ancestor   (parent node, recursive)
│   │   └── SalesRank  (rank within this node)
│   └── WebsiteSalesRank (overall site rank, often most useful)
├── CustomerReviews
│   ├── Count
│   └── StarRating.Value (0.0 - 5.0)
└── VariationAttributes[]   (only on child ASINs — Color, Size, Style)
```

Images are served from Amazon's `m.media-amazon.com` CDN, no auth, no
expiration, hot-linkable in content. Use the canonical URL Amazon
returns; do not rewrite the size token (`._SL500_`) by hand because
Amazon may change image hashing.

Currency in `Price.Amount` is **integer cents in the marketplace currency**
(US: USD cents, UK: GBP pence, JP: JPY whole-yen-as-integer because JPY
has no subunit). Always use `DisplayAmount` for rendering — it's
locale-formatted with the right currency symbol.

There is no Order, no Customer, no Cart object in PA-API 5.0. Cart
operations were removed in the migration from PA-API 4 (the `RemoteCart`
endpoint died with v4).

---

## Webhooks and Events

**N/A — PA-API is a request/response API only.** There are no webhooks,
no event streams, no push notifications, no SNS/SQS integration. If you
need to detect price or availability changes you must poll. The Creators
API does not add webhooks either.

---

## Limits

| Resource                        | Limit                                  |
|---------------------------------|----------------------------------------|
| ASINs per GetItems              | 10                                     |
| Browse node IDs per GetBrowseNodes | 10                                  |
| ItemCount per SearchItems page  | 10                                     |
| ItemPage range for SearchItems  | 1–10 (100 items max per query)         |
| VariationPage range             | 1–10                                   |
| Resources per request           | no documented hard limit (~50 sane)    |
| Starter TPS                     | 1                                      |
| Starter TPD                     | 8640                                   |
| Maximum TPS (any account)       | 10                                     |
| Marketplaces per credential     | 1                                      |
| ASIN length                     | 10 characters, alphanumeric            |
| PartnerTag format               | `name-NN` where NN is locale code      |
| Image sizes (Primary/Variants)  | Small 75px, Medium 160px, Large 500px  |
| Title display length            | up to ~500 chars                       |
| Features bullet count           | up to ~10                              |
| Offers.Listings count           | typically 1 (buy box winner)           |
| Cache freshness for prices      | ≤24h per Amazon TOS                    |

---

## Cost Model

**The API is free.** There is no per-call charge, no subscription, no tier.
The cost is structural:

- **Time**: every call costs ~1s of TPS quota
- **Quota debt**: every call costs 1 TPD against your daily allowance
- **Account risk**: failure to drive 3 sales in 180 days revokes access
- **Maintenance**: PA-API sunsets 2026-05-15, so any code is throwaway
  unless you migrate to Creators API

The economic model is reciprocal: Amazon gives you the catalog, you drive
sales, Amazon pays commission, Amazon gives you more quota. Pre-revenue
accounts are second-class citizens by design.

---

## Version Pinning

- API version: **PA-API 5.0** — there is no 5.1 or 6.0; the next thing is
  the Creators API which is a different product.
- Service version in target header: `com.amazon.paapi5.v1.ProductAdvertisingAPIv1`
- Python SDK pins (recommended for EOS):
  - `python-amazon-paapi==5.0.1`
  - `paapi5-python-sdk==1.1.0`  (lower-level fallback)
- Node.js: `paapi5-nodejs-sdk@1.0.0` from the `tobias7an` fork on npm
  (official Amazon distribution is unreliable)
- PHP: `paapi5-php-sdk` from packagist via `rossjcooper/paapiphpsdk`
- Java: official Amazon JAR from the docs page

Sunset calendar:
- **2026-01-31** — Offers V1 retired (DONE)
- **2026-04-30** — PA-API officially deprecated
- **2026-05-15** — PA-API endpoint shut down, all calls return 410/connection refused

After 2026-05-15, every line of PA-API code is dead. EOS migration to
the Creators API must complete before then.

---

## Design Intent and Tradeoffs

PA-API 5.0 was designed in 2019 as the successor to PA-API 4 (which had
been the de facto Amazon affiliate API since ~2005). The design goals
behind 5.0 were:

1. **JSON-RPC over SigV4** instead of XML-over-query-string. Brought
   the API in line with classic AWS services and let Amazon reuse
   internal AWS infrastructure.
2. **Resources as opt-in projection**. PA-API 4 returned giant XML blobs
   by default, hammering the catalog backend. Resources lets the client
   declare exactly what it needs, which let Amazon shrink response sizes
   and reduce backend cost dramatically.
3. **ASIN as the only primary key**. PA-API 4 supported UPC/EAN/ISBN
   primary lookups which created joins on every call. Forcing ASIN
   collapses the lookup to a single index hit.
4. **Hard 100-item search ceiling**. Designed to discourage catalog
   scraping and push affiliates toward known-ASIN hydration patterns.
   The ceiling is not a bug; it is an intentional product decision.
5. **No webhooks, no push, no diff**. Amazon does not want affiliates
   replicating the catalog. You can hydrate ASINs you already know
   about, but you cannot maintain a mirror.
6. **Quota tied to shipped revenue**. Affiliates who actually drive
   sales get more capacity; affiliates who scrape get throttled out.
   This is the central economic incentive of the API.

The tradeoffs are:

- **Easy to integrate, hard to scale**. The 1 TPS starter and 100-item
  search ceiling make broad catalog work impossible.
- **Strong attribution guarantee**. PartnerTag baked into every
  DetailPageURL means commission tracking Just Works as long as you
  don't rewrite URLs.
- **No real-time signals**. Price changes, availability changes, and
  new releases all require polling. Affiliates who need real-time
  signals (deal sites, price trackers) hit the quota wall instantly.
- **Locale fragmentation**. One marketplace per credential is painful
  for multi-region brands; five marketplaces means five sets of
  credentials and five caches.

The Creators API (the successor) keeps most of these design choices but
splits Offers into a richer V2 schema and changes the credential model
to be tighter to the creator's content profile. Same JSON-RPC pattern.

---

## Problem-Solution Map and Hidden Capabilities

**Problem: I need to monetize a content post that mentions a specific product.**
Solution: `GetItems(items=[asin], resources=[Title, Image, Price])`, drop
`item.detail_page_url` into the post. One call, one ASIN, fully tagged.

**Problem: I need to find candidate products for an upcoming "tactical luxury
gear" post.** Solution: `SearchItems(keywords="tactical luxury watch",
search_index="Watches", min_reviews_rating=4, sort_by="AvgCustomerReviews",
item_count=10)`. Repeat across keyword variations, dedupe ASINs, rank by
review count + price band.

**Problem: I have a parent ASIN and want all colors/sizes.** Solution:
`GetVariations(asin=parent, resources=[VariationSummary, Images])`.
Returns up to 10 children per page; iterate `variation_page` to 10.

**Problem: I want products in a specific Amazon category.** Solution: walk
`GetBrowseNodes` from a known root to find the leaf node ID, then use
`SearchItems(browse_node_id=...)` instead of keywords.

**Problem: Prices in my content are stale.** Solution: schedule a nightly
GetItems batch refresh of every ASIN published in the last 30 days. Batch
in groups of 10, sleep 1.1s between batches, write back to Neon.

**Problem: I want sales rank for ranking products in research.** Solution:
add `BrowseNodeInfo.WebsiteSalesRank` to your Resources. Lower numbers
are better. Combine with CustomerReviews.Count for a "popularity" metric
that filters out new / no-data products.

**Problem: I want to detect when a product is in stock again.** Solution:
poll `GetItems` with `Offers.Listings.Availability.Type` and check for
`Now` vs `IncludeOutOfStock`. There is no push — you have to poll.

**Hidden capability: SearchRefinements.** Adding `SearchRefinements` to
SearchItems Resources returns a list of refinement facets (brand counts,
price band counts, feature counts) that Amazon's own UI uses to build
its left-rail filter. Useful for understanding what dimensions exist in
a category before you commit to specific filters.

**Hidden capability: SortBy=NewestArrivals.** Surfaces recent SKUs in a
category — useful for trend research without keyword bias.

**Hidden capability: BrowseNodes.SalesRank vs WebsiteSalesRank.** Two
different rankings. SalesRank is per-leaf (rank #1 in "Mechanical
Keyboards"), WebsiteSalesRank is overall (#5482 in Electronics). Use
SalesRank for niche dominance, WebsiteSalesRank for absolute volume.

**Hidden capability: VariationSummary without enumerating variations.**
You can get the full price range across all variations of a parent
without making a GetVariations call by adding `VariationSummary.Price.*`
to a GetItems request. Saves a quota call.

**Hidden capability: MerchantInfo.FeedbackRating.** Distinguishes
fulfillment quality between buy box winners. Useful for filtering out
low-quality 3P sellers in product research.

---

## Operational Behavior and Edge Cases

- **Same ASIN, different prices on consecutive calls**: normal. Buy box
  rotates. Don't display "price changed" to users on every refresh.
- **Same ASIN, different DetailPageURL formats**: normal. Amazon may
  return short or long URL forms; both track. Don't normalize.
- **Item in SearchItems response, missing in GetItems response**: the
  item was delisted between calls. Treat GetItems as ground truth.
- **GetItems batch returns 7 items + 3 errors**: partial success is the
  norm. Iterate the Errors array, drop bad ASINs, keep good ones.
- **`Offers` field is null**: forgotten in Resources, OR the item has no
  active offers (unavailable, restricted). Check both before deciding.
- **`Images.Primary` is null**: rare but happens for some media items
  (audiobooks, MP3 downloads, Kindle without cover). Handle gracefully.
- **`item.item_info.title.display_value` is None**: forgot
  `ItemInfo.Title` in Resources. The Python SDK does not warn, just
  returns a hollow object.
- **Price in JPY**: `Price.Amount` is a whole yen integer, not cents.
  JPY has no subunit. Hardcoding `/100` will produce 100x prices.
- **DST and `x-amz-date`**: must be UTC ISO basic format
  (`20260406T120000Z`), not local time. SDKs handle this; hand-rolled
  clients hit signature errors at 5 PM Pacific.
- **Body whitespace and signing**: the canonical request hashes the
  exact bytes you send. If you sign a JSON body and then re-serialize
  it before sending (different key order, different spacing) the
  signature breaks. Always sign the bytes you send.
- **Region drift**: a request to `webservices.amazon.co.uk` signed with
  `us-east-1` fails. Region must match the endpoint host.
- **Long-tail ASINs (10 chars all alphanumeric)**: Amazon issues new
  ASINs with `B0` prefix but legacy book ASINs are ISBN-10 (10 digits
  with check digit). Both are valid; don't filter on `B0`.
- **Throttle behavior under burst**: Amazon does not allow bursts. Two
  calls in the same second always 429s the second one even if you've
  been silent for an hour. The bucket is 1 token, refilled at 1/s.

---

## Ecosystem Position and Composition

PA-API sits between three external systems:

- **Upstream: Amazon catalog**. PA-API is the read-only public face of
  the master catalog. The catalog itself is updated by Vendor Central
  (1P sellers), Seller Central (3P sellers), and internal Amazon
  cataloging tools. Affiliates have zero write access.
- **Downstream: affiliate content systems**. WordPress plugins
  (AAWP, AmaLinks Pro, Lasso), static-site generators, custom content
  pipelines (EOS), and price-comparison tools all sit on PA-API. Most
  WordPress affiliate plugins are 90% PA-API call wrappers + caching.
- **Sideways: Associates Central**. The web dashboard for managing
  Tracking IDs, viewing earnings, downloading reports, and (until
  2026-05-15) issuing PA-API credentials.

Composition with EOS:

- **Neon Postgres**: cache for ASIN hydration results, durable store
  for `product_card` primitives, audit log for every API call.
- **Empyrean Studio content pipeline**: consumer of `product_card`
  primitives. Writer agents reference ASINs by tag (`{{asin:B08N5WRWNW}}`)
  and a render pass replaces them with full DetailPageURL + image.
- **OneTag CSV ingestion**: bridges PA-API (catalog data) and
  Associates Central (revenue data). Without it you cannot attribute
  revenue back to specific posts.
- **Cron + tmux**: nightly refresh of stale ASINs, daily TPD budget
  reset at 00:00 UTC, weekly product research sweeps for upcoming
  content series.
- **Future: Creators API**: drop-in replacement at the credential and
  endpoint layer; client wrapper isolates the difference so most
  consumers don't notice.

---

## Trajectory and Evolution

- **2005–2019**: PA-API 4 (XML, query-string signing, REST-ish).
  Long stable but creaky.
- **2019**: PA-API 5.0 launches. JSON-RPC, SigV4, Resources projection,
  ASIN-only primary key. Cart endpoints removed.
- **2020–2024**: incremental feature additions — OffersV2, SortBy
  variations, additional Resources entries, more locales added.
- **2025-Q4**: Amazon announces Creators API as the successor and
  begins migration warnings.
- **2026-01-31**: Offers V1 retired. Affiliates relying on the V1
  Offers schema break and migrate to OffersV2 or Creators API.
- **2026-04-30**: PA-API officially deprecated. Documentation site
  freezes, support tickets redirected to Creators API team.
- **2026-05-15**: PA-API endpoint hard-shutdown. Calls return 410 or
  connection refused.

**Direction of travel**: Amazon is consolidating affiliate APIs under
the "Creators" brand, which encompasses Associates affiliates plus
Influencer Program participants plus Amazon Live creators. The Creators
API is designed around content profiles and richer offer data, not
generic catalog access. Amazon is also tightening the link between
affiliate content and creator identity — generic spam-affiliate sites
are progressively de-prioritized in commission rates and access tiers.

For EOS, the implication is: invest in the content pipeline, not in
the API wrapper. The API will change again. The brand-native
product-placement strategy will keep working.

---

## Conceptual Model and Solution Recipes

The conceptual model is **ASIN as primary key, Resources as projection,
PartnerTag as attribution**. Internalize this and every PA-API behavior
follows.

### Recipe: hydrate a known ASIN for a content post

```python
RESOURCES_HYDRATE = [
    "Images.Primary.Large",
    "ItemInfo.Title",
    "ItemInfo.Features",
    "ItemInfo.ByLineInfo",
    "Offers.Listings.Price",
    "Offers.Listings.Availability.Message",
    "CustomerReviews.StarRating",
    "CustomerReviews.Count",
]

def hydrate(asin: str) -> dict:
    cached = neon.fetch_one(
        "SELECT data, refreshed_at FROM amazon_product_cache WHERE asin=%s",
        (asin,),
    )
    if cached and cached["refreshed_at"] > datetime.utcnow() - timedelta(hours=24):
        return cached["data"]

    item = call_with_retry(
        amazon.get_items, items=[asin], resources=RESOURCES_HYDRATE
    )[0]
    data = {
        "asin": item.asin,
        "title": item.item_info.title.display_value,
        "image": item.images.primary.large.url,
        "features": item.item_info.features.display_values if item.item_info.features else [],
        "brand": item.item_info.by_line_info.brand.display_value if item.item_info.by_line_info else None,
        "price_display": item.offers.listings[0].price.display_amount if item.offers else None,
        "availability": item.offers.listings[0].availability.message if item.offers else "Unavailable",
        "rating": item.customer_reviews.star_rating.value if item.customer_reviews else None,
        "review_count": item.customer_reviews.count if item.customer_reviews else 0,
        "url": item.detail_page_url,
    }
    neon.execute(
        "INSERT INTO amazon_product_cache (asin, data, refreshed_at) VALUES (%s, %s, NOW()) "
        "ON CONFLICT (asin) DO UPDATE SET data=EXCLUDED.data, refreshed_at=NOW()",
        (asin, json.dumps(data)),
    )
    return data
```

### Recipe: research candidate products for an upcoming post

```python
def research(keywords: str, browse_node: str | None = None,
             min_rating: int = 4, max_price_cents: int = 50000) -> list[dict]:
    candidates = []
    for page in range(1, 6):  # 50 items max, plenty for a single post
        result = call_with_retry(
            amazon.search_items,
            keywords=keywords,
            browse_node_id=browse_node,
            min_reviews_rating=min_rating,
            max_price=max_price_cents,
            sort_by="AvgCustomerReviews",
            item_count=10,
            item_page=page,
            resources=RESOURCES_HYDRATE,
        )
        if not result.items:
            break
        candidates.extend(result.items)
        time.sleep(1.1)

    # Rank by review count * rating
    return sorted(
        candidates,
        key=lambda i: (i.customer_reviews.count if i.customer_reviews else 0)
                      * (i.customer_reviews.star_rating.value if i.customer_reviews else 0),
        reverse=True,
    )[:10]
```

### Recipe: nightly stale-cache refresh

```python
def refresh_stale_products():
    stale = neon.fetch_all(
        "SELECT asin FROM amazon_product_cache "
        "WHERE refreshed_at < NOW() - INTERVAL '24 hours' "
        "ORDER BY refreshed_at LIMIT 200"   # ~200 calls / night fits TPD
    )
    for batch in chunked([row["asin"] for row in stale], 10):
        items = call_with_retry(amazon.get_items, items=batch, resources=RESOURCES_HYDRATE)
        for item in items:
            write_back(item)
        time.sleep(1.1)
```

### Recipe: walk a category tree

```python
def walk_category(root_id: str, max_depth: int = 3):
    queue = [(root_id, 0)]
    seen = set()
    while queue:
        node_id, depth = queue.pop(0)
        if node_id in seen or depth > max_depth:
            continue
        seen.add(node_id)
        result = call_with_retry(
            amazon.get_browse_nodes,
            browse_node_ids=[node_id],
            resources=["BrowseNodes.Children", "BrowseNodes.Ancestor"],
        )
        for node in result.browse_nodes:
            yield (depth, node.id, node.display_name)
            for child in (node.children or []):
                queue.append((child.id, depth + 1))
        time.sleep(1.1)
```

---

## Industry Expert and Cutting-Edge Usage

What experienced affiliate developers do that beginners don't:

- **Maintain a single canonical Resources list per operation in code**,
  versioned. Every change to the list is a code change, never inline.
- **Treat PA-API as a hydration cache, not a query engine**. Discovery
  happens elsewhere (browsing Amazon manually, OneTag clicks, social
  signals); PA-API just hydrates known ASINs.
- **Front the SDK with a Postgres-backed semaphore** so multi-process
  workers don't collectively exceed 1 TPS. Local sleep is not enough.
- **Log every call with request hash, response status, and quota
  used** to a Postgres audit table. When you eventually hit 429 the
  log tells you exactly which feature is the offender.
- **Separate "high-frequency" Resources (Offers, Availability) from
  "low-frequency" Resources (Title, Features, Images)** into two
  different cache tables with different TTLs. Most fields are static
  for weeks; only Offers needs hourly refresh.
- **Generate fallback affiliate URLs** even when PA-API fails:
  `https://www.amazon.com/dp/{asin}?tag={partner_tag}` is a worse link
  but a working link. Never publish content with broken Amazon links.
- **Store the PartnerTag at the venue level**, not the call level —
  one Empyrean Studio venue, one tag, one cache namespace. Multi-tenant
  affiliate systems where one tag leaks into another venue's content
  are an attribution nightmare.
- **Pre-compute "evergreen" product cards** for top-100 SKUs across
  the brand and refresh nightly. Render is then static, no PA-API
  calls in the hot path.
- **Use OneTag report download as the source of truth for revenue**,
  reconcile against `amazon_product_cache.asin` joined to
  `posts.asin_mentions` to attribute revenue to specific posts.
- **Run two Associate Tags per marketplace in parallel** (e.g.
  `empyrean-20` and `empyreanlab-20`) to A/B test placement strategies.
  Amazon allows multiple tags per account.
- **Plan the Creators API migration as a wrapper-level swap**: keep
  `amazon_client.py` as the only code that knows which API is in use.
  Every consumer continues to call `client.get_items(asins, resources)`.
- **Subscribe to the Associates Central blog** for sunset and
  deprecation announcements. Amazon does not email API changes; you
  have to poll the blog.
- **Test signing locally with a known-good request from the SDK**
  before debugging your own signer. Verify byte-for-byte equality
  including header order before suspecting Amazon's side.

---

## EOS Usage Patterns

The EOS-specific patterns layered on top of best practices:

- **Single client wrapper at `eos_ai/affiliate/amazon_client.py`**.
  Loads credentials from `eos_ai/.env`, exposes `get_items`,
  `search_items`, `get_variations`, `get_browse_nodes`. Every consumer
  goes through this one module.
- **Resources lists at `eos_ai/affiliate/paapi_resources.py`** as
  module-level constants: `RESOURCES_HYDRATE`, `RESOURCES_SEARCH`,
  `RESOURCES_VARIATIONS`, `RESOURCES_NODES`. Never inline.
- **Neon tables**:
  - `amazon_product_cache(asin PRIMARY KEY, data JSONB, refreshed_at TIMESTAMPTZ)`
  - `amazon_api_audit(id, called_at, operation, request_hash, status, quota_used, error)`
  - `affiliate_earnings(date, asin, clicks, items_ordered, items_shipped, revenue_cents, source)`
  - `post_asin_mentions(post_id, asin, position, rendered_at)`
- **Stage-aware throttling**: `pre_revenue` stage forces caching with
  ≥24h TTL on hydrate calls and ≥6h on search calls. Higher stages
  reduce TTL.
- **Cron schedule**:
  - `00:30 UTC` — refresh stale Offers (top 200 ASINs)
  - `02:00 UTC` — full hydrate refresh of any ASIN published last 7 days
  - `04:00 UTC` — OneTag CSV ingest into `affiliate_earnings`
  - `Sunday 06:00 UTC` — research sweep for next week's content series
- **Writer Agent integration**: post drafts contain bare ASINs in
  `{{asin:B08N5WRWNW}}` placeholders. Render pass calls `hydrate(asin)`
  for each placeholder, replaces with title + image + DetailPageURL.
- **Portfolio Advisor integration**: weekly report joins
  `affiliate_earnings` against `post_asin_mentions` to surface top-
  earning posts and underperforming product placements.
- **Quota budget enforcement**: `amazon_client.py` tracks today's
  call count in Neon and refuses non-essential calls when within 10%
  of TPD ceiling. Writer Agent renders fall back to manual affiliate
  URL when budget is exhausted.
- **Sunset countdown**: `eos_ai/affiliate/sunset.py` exposes
  `days_until_paapi_shutdown()` and the Developer Agent surfaces this
  in `/morning-brief` if <30 days. Migration tracker lives in
  `docs/creators-api-migration.md`.

---

## Gotchas

- **2026-05-15 hard shutdown.** The biggest gotcha. Every line of
  PA-API 5.0 code dies that day. Migrate to Creators API before then.
- **Offers V1 already gone (2026-01-31).** If you're reading this and
  your Resources list still contains `Offers.Listings.Price` from a
  2024 tutorial, it actually maps to OffersV2 under the hood now —
  most SDKs handle this transparently but some older SDK versions
  break. Pin SDK versions, test before deploying.
- **3 sales in 180 days or you lose access.** Pre-revenue accounts
  built today are revoked silently in October 2026. The first sign is
  a 401 on what was a 200 yesterday.
- **Starter quota is 1 TPS / 8640 TPD, full stop.** Burst is zero.
  Two calls in the same second 429s the second one. Cache aggressively.
- **TPD throttles even when TPS has headroom.** A burst of 100 calls
  at midnight followed by silence still 429s near the end of the day.
- **SigV4 service name is `ProductAdvertisingAPI` exactly.** Wrong
  service name → opaque signature error.
- **`content-encoding: amz-1.0` header is mandatory** and must be in
  the SignedHeaders list. Forgetting it produces the same signature
  error as the wrong service name.
- **Resources omissions silently null fields.** Forgetting
  `Offers.Listings.Price` makes every product look free. There is no
  warning. Maintain canonical Resources lists per operation.
- **GetItems max 10 ASINs.** Larger batches return InvalidParameterValue.
- **SearchItems max 100 results per query.** ItemPage>10 errors.
  Shard with filters to go deeper.
- **Each marketplace = separate account, credentials, tag.** No global mode.
- **PartnerTag suffix encodes locale.** `-20` US, `-21` UK, `-22` DE.
  Cross-locale tags break attribution silently.
- **DetailPageURL is the canonical commission link.** Hand-built
  `dp/ASIN?tag=` works but loses ref/linkCode tracking.
- **Cache Offers ≤24h.** Amazon TOS forbids stale price display.
- **No earnings/orders endpoint.** Only OneTag CSV export.
- **No webhooks.** Polling is the only option.
- **JPY is whole yen, not cents.** Hardcoding `/100` in price display
  produces 100x JPY values.
- **`x-amz-date` must be UTC.** Local time → signature error.
- **Body whitespace matters for signing.** Sign the exact bytes you
  send; never re-serialize between sign and send.
- **Region must match endpoint host.** `us-east-1` for .com,
  `eu-west-1` for .co.uk and EU, `us-west-2` for .co.jp.
- **Documentation site is no longer maintained** (Amazon's own
  statement). Outdated examples will not be fixed.
- **Python SDK's `throttling=` is local sleep, not real rate limiting.**
  Multi-process workers need a Neon-backed semaphore.
- **`item.offers is None` is ambiguous** — could be missing Resources
  entry or unavailable item. Check Resources first.
- **Sunset tracking is YOUR job.** Amazon will not email you when
  PA-API shuts down. Subscribe to the Associates Central blog and put
  the date in your calendar.
