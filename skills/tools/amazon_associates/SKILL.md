---
name: amazon_associates
description: "Use when querying Amazon Product Advertising API (PA-API 5.0) for product research, building affiliate links with an Associate Tag, fetching ASIN metadata/images/offers via SearchItems/GetItems/GetVariations/GetBrowseNodes, signing AWS SigV4 requests to webservices.amazon.com, handling 429 TooManyRequests throttling tied to shipped revenue, or planning the migration to the Creators API before the May 15 2026 PA-API retirement."
allowed-tools: "Read, Bash, Write, Edit, WebFetch"
version: 1.0
source_url: "https://webservices.amazon.com/paapi5/documentation/"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "PA-API 5.0 (com.amazon.paapi5.v1) — RETIRES 2026-05-15, migrate to Creators API"
sdk_version: "python-amazon-paapi 5.0.1 / paapi5-python-sdk 1.1.0 / paapi5-nodejs-sdk 1.0.0"
speed_category: sunset
---

# Tool: amazon_associates (PA-API 5.0)

## What This Tool Does

The Amazon Product Advertising API 5.0 is the official affiliate-revenue data
plane for Amazon Associates. It exposes Amazon's product catalog as five JSON-RPC
operations over an AWS SigV4-signed HTTPS endpoint, scoped to a specific
marketplace (US, UK, DE, JP, etc.) and tied to an Associate Tag that earns
commission on every click that converts.

Core capabilities:

- **SearchItems** — keyword/category search returning ASINs, titles, images, prices, offers
- **GetItems** — batch lookup of up to 10 ASINs at a time with full Resources control
- **GetVariations** — parent ASIN to child variations (size, color, configuration)
- **GetBrowseNodes** — Amazon category tree navigation (browse node IDs)
- **Resources parameter** — opt-in field selection (Images.Primary.Large, Offers.Listings.Price, ItemInfo.Features, BrowseNodeInfo.BrowseNodes, etc.) — only requested fields are returned
- **Affiliate link emission** — every response includes a DetailPageURL already tagged with your PartnerTag, ready to drop into content
- **Per-marketplace endpoints** — webservices.amazon.com (US/us-east-1), .co.uk (eu-west-1), .de, .co.jp, etc., each with its own credentials and Associate Tag

PA-API is request/response only. There are no webhooks, no streams, no
push notifications, no order/earnings data. Earnings reports live in
Associates Central, not the API.

**SUNSET WARNING:** PA-API 5.0 retires **2026-05-15**. Offers V1 already
retired 2026-01-31. Amazon is forcing migration to the **Creators API**
(`https://affiliate-program.amazon.com/creatorsapi/docs/`). New credentials
required — AWS Access Key/Secret will not carry over. Plan migration now.

## EOS Integration

Amazon Associates is a content-monetization revenue stream for the
**Empyrean Studio** content engine and Antony's personal-brand pipeline.
Tactical-luxury product placement is the brand-native use case: gear, tools,
books, supplements that Antony actually uses, surfaced in posts/scripts with
real affiliate links the moment a product is mentioned.

EOS integration points:

- **Affiliate-ready product research** — a content/research agent calls
  `SearchItems` with `Keywords` + `BrowseNodeId` filtering, ranks by rating
  count and price band, and writes ASINs into Neon as candidate placements
  for upcoming scripts. Stored as a `product_card` primitive (title, image,
  price, ASIN, affiliate URL, last refreshed).
- **Link generation in content pipelines** — when the Writer Agent drafts a
  post that mentions a product, a post-processing pass calls `GetItems` for
  any bare ASIN, swaps in the canonical `DetailPageURL` (already tagged with
  the EOS Associate Tag), and refreshes price/availability so nothing ships
  with stale data.
- **Earnings reports ingestion** — PA-API does NOT expose earnings. Pull the
  Associates Central daily CSV via OneTag report or manual export, ingest
  into Neon `affiliate_earnings` so the Portfolio Advisor can attribute
  revenue back to specific posts and ASINs.
- **Stage routing** — pre-revenue, calls are throttled hard (1 TPS / 8640 TPD
  starter quota) so the model_router caches every GetItems result for ≥24h
  and SearchItems results for ≥6h in Neon to stay under quota.

Canonical EOS pattern:
- Credentials in `eos_ai/.env`: `AMAZON_ACCESS_KEY`, `AMAZON_SECRET_KEY`, `AMAZON_PARTNER_TAG`
- Marketplace pinned: `AMAZON_HOST=webservices.amazon.com`, `AMAZON_REGION=us-east-1`
- Resources lists in `eos_ai/affiliate/paapi_resources.py` (one canonical list per operation, never inlined)
- All calls go through `eos_ai/affiliate/amazon_client.py` enforcing caching, exponential backoff on 429, and Neon audit rows

## Authentication

PA-API 5.0 uses **AWS Signature Version 4** (`AWS4-HMAC-SHA256`) — the same
signing scheme as classic AWS services, but with a non-AWS service name and a
non-AWS credential pair issued from Associates Central, not IAM.

You need three credentials:

1. **Access Key** — issued from Associates Central → Tools → Product Advertising API → Manage Your Credentials
2. **Secret Key** — shown ONCE at credential creation, never retrievable again
3. **Partner Tag** (Associate Tag, e.g. `empyrean-20`) — your tracking ID; sales attribute to whichever tag is in the request

Required headers on every request:

```
host: webservices.amazon.com
content-type: application/json; charset=utf-8
content-encoding: amz-1.0
x-amz-date: 20260406T120000Z
x-amz-target: com.amazon.paapi5.v1.ProductAdvertisingAPIv1.SearchItems
Authorization: AWS4-HMAC-SHA256 Credential=AKIA.../20260406/us-east-1/ProductAdvertisingAPI/aws4_request, SignedHeaders=..., Signature=...
```

Critical SigV4 details specific to PA-API:

- **Service name** is `ProductAdvertisingAPI` (NOT `paapi`, NOT `productadvertisingapiv1`)
- **Region** is locale-specific: `us-east-1` for .com, `eu-west-1` for .co.uk/.de/.fr, `us-west-2` for .co.jp
- **x-amz-target** must match the operation: `...ProductAdvertisingAPIv1.GetItems`, `.SearchItems`, `.GetVariations`, `.GetBrowseNodes`
- **content-encoding: amz-1.0** is mandatory — omit it and you get an opaque signature error

The official SDKs (`paapi5-python-sdk`, `paapi5-nodejs-sdk`, `paapi5-php-sdk`,
`paapi5-java-sdk`) handle SigV4 for you. Hand-rolling SigV4 is possible but
not recommended.

Account requirements:

- Active Amazon Associates account in **good standing** in the target marketplace
- Each marketplace requires its **own** account, **own** credentials, **own** Partner Tag
- Account must have made **at least 3 qualifying sales within 180 days** of credential creation OR PA-API access is revoked
- Continued access requires generating sales — silent accounts are revoked

## Quick Reference

### Install Python SDK

```bash
pip install python-amazon-paapi
# or the lower-level official SDK
pip install paapi5-python-sdk
```

### SearchItems (keyword search)

```python
from amazon_paapi import AmazonApi

amazon = AmazonApi(
    key=os.getenv("AMAZON_ACCESS_KEY"),
    secret=os.getenv("AMAZON_SECRET_KEY"),
    tag=os.getenv("AMAZON_PARTNER_TAG"),
    country="US",
)

results = amazon.search_items(
    keywords="mechanical keyboard tactile",
    search_index="Electronics",
    item_count=10,
    resources=[
        "Images.Primary.Large",
        "ItemInfo.Title",
        "ItemInfo.Features",
        "Offers.Listings.Price",
        "Offers.Listings.Availability.Message",
        "BrowseNodeInfo.BrowseNodes",
    ],
)
for item in results.items:
    print(item.asin, item.item_info.title.display_value, item.detail_page_url)
```

### GetItems (batch ASIN lookup, max 10 per call)

```python
items = amazon.get_items(
    items=["B08N5WRWNW", "B0CHX1W1XY", "B09G9BL5CP"],
    resources=[
        "Images.Primary.Large",
        "ItemInfo.Title",
        "Offers.Listings.Price",
        "ParentASIN",
    ],
)
```

### GetVariations and GetBrowseNodes

```python
variations = amazon.get_variations(asin="B08N5WRWNW",
    resources=["VariationSummary.Price.HighestPrice", "Images.Primary.Medium"])

nodes = amazon.get_browse_nodes(browse_node_ids=["283155"],
    resources=["BrowseNodes.Ancestor", "BrowseNodes.Children"])
```

### Manual affiliate link fallback

```python
url = f"https://www.amazon.com/dp/{asin}?tag={os.getenv('AMAZON_PARTNER_TAG')}"
```

### Marketplace endpoints

```
US  webservices.amazon.com         us-east-1
UK  webservices.amazon.co.uk       eu-west-1
DE  webservices.amazon.de          eu-west-1
FR  webservices.amazon.fr          eu-west-1
JP  webservices.amazon.co.jp       us-west-2
CA  webservices.amazon.ca          us-east-1
IN  webservices.amazon.in          eu-west-1
```

## Conceptual Model

**ASIN is the primary key. Resources is the projection. PartnerTag is the
attribution.** Everything in PA-API revolves around the 10-character ASIN —
SearchItems returns ASINs, GetItems hydrates ASINs, GetVariations expands an
ASIN into children, GetBrowseNodes scopes ASINs to a category. There is no
SKU concept, no UPC primary lookup (UPC works as a search term, not a key),
no order concept.

Resources is opt-in projection: you pay (in TPS quota) for the call, not for
the fields, but unrequested fields are silently absent — an `item.offers` of
`None` does not mean the item is out of stock, it means you forgot to ask for
`Offers.Listings.Price`. Every PA-API integration bug looks like missing data
and is actually a missing Resources entry.

PartnerTag is the only thing Amazon tracks for revenue. Use the wrong tag,
your sales attribute to someone else. Use no tag, the click is unattributed
and you earn nothing. Every `DetailPageURL` PA-API returns already has the
PartnerTag baked in — never strip it, never rewrite it.

If you internalize ASIN-as-key, Resources-as-projection, Tag-as-attribution,
every PA-API behavior follows:
- "Why is offers null?" → not in Resources
- "Why is the price stale?" → you cached the GetItems response too long
- "Why no commission on a sale I drove?" → wrong PartnerTag in DetailPageURL
- "Why 429 immediately?" → starter quota is 1 TPS, not 1 RPS-burst

## Gotchas

- **PA-API retires 2026-05-15.** This skill has a known sunset. Build new
  features against the **Creators API**. Offers V1 ALREADY retired 2026-01-31.
- **3-sales-in-180-days requirement** — credentials issued today are revoked
  in 180 days if you haven't driven 3 qualifying sales. Pre-revenue accounts
  silently lose API access and only find out via 401.
- **Starter quota is 1 TPS / 8640 TPD** — and TPD exhaustion 429s you even if
  you're under TPS. Quota grows with shipped revenue: +1 TPD per 5¢ shipped,
  +1 TPS per $4320 shipped (trailing 30d), max 10 TPS.
- **Resources parameter is opt-in** — forgetting `Offers.Listings.Price` makes
  every item look free. Forgetting `Images.Primary.Large` makes every item
  look imageless. Maintain a canonical Resources list per operation.
- **GetItems batches max 10 ASINs** — passing 50 returns InvalidParameterValue.
  Chunk on the client side.
- **Each marketplace is a separate account, separate credentials, separate
  PartnerTag.** US credentials cannot query .co.uk. There is no global mode.
- **SigV4 service name is `ProductAdvertisingAPI`** — not `paapi`, not
  `paapi5`. Wrong service name → opaque `Signature does not match` error.
- **`content-encoding: amz-1.0` header is mandatory** — omit it and you get
  the same opaque signature error.
- **PartnerTag suffix encodes marketplace**: `-20` US, `-21` UK, `-22` DE.
  Mixing across marketplaces silently breaks attribution.
- **DetailPageURL is the only commission-attributed link.** Hand-built
  `amazon.com/dp/ASIN?tag=...` works but loses ref/linkCode tracking.
- **Cache aggressively, but not Offers.** Title/Image/Features stable for
  weeks. Offers.Listings.Price changes hourly and Amazon's TOS forbids
  displaying stale prices for >24h.
- **PA-API 5.0 has NO earnings/orders endpoint.** Earnings come from
  Associates Central reports. There is no `GetEarnings` operation.
- **Documentation site is no longer actively maintained** — Amazon directs
  all docs effort to Creators API.

See references/best_practices.md for the full 19-section creator-level knowledge base.
