---
name: pinterest
description: "Use when posting/scheduling pins via Pinterest API v5, designing pin/board strategy for Lyfe Spectrum or personal brand, analyzing pin performance, integrating with Shopify product feeds, or planning Pinterest SEO/keyword strategy."
allowed-tools: "Read, Bash, Write, Edit, WebFetch"
version: 1.0
source_url: "https://developers.pinterest.com/docs/api/v5"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "v5"
sdk_version: "pinterest-python-generated 1.x (OpenAPI), or direct REST"
speed_category: stable
trigger: both
effort: low
context: fork
---

# Tool: Pinterest

## What This Tool Does

Pinterest is a visual discovery and search engine — not a social network. Users
arrive with intent (planning a purchase, a project, a wedding, an outfit) and
type queries the way they would in Google. Pins are indexed, ranked, and served
by relevance and freshness for years after posting. The half-life of a pin is
measured in months, not hours.

The Pinterest API for Business (v5) is the programmatic surface over that
graph. With it you can:

- **Create, update, and delete pins** (image, video, multi-image carousels, and
  Idea Pins / "story" style pins) on boards you own
- **Manage boards and board sections** — Pinterest's two-level hierarchy
- **Read analytics** at pin, board, ad, and account level (impressions, saves,
  outbound clicks, video views, audience demographics)
- **Search Pinterest's catalog** for pins, boards, and trends (limited; some
  endpoints gated to ad spenders or partners)
- **Sync product catalogs** for Shopping (`catalogs`, `catalog_products`,
  `catalog_product_groups`) — the bridge from a Shopify feed to Product Pins
- **Manage Rich Pins** indirectly via og: / schema.org markup on the merchant
  domain that Pinterest's crawler validates
- **Run user-account ops** — verify domain, list boards, read business profile

The API does NOT cover: organic feed ranking (read-only via analytics), DM/inbox,
following/followers write actions beyond a basic follow endpoint, or the trends
API for non-business accounts.

## EOS Integration

Pinterest plays two distinct roles in the EOS portfolio. Treat them as separate
playbooks because the audience, intent, and pin design diverge sharply.

**Lyfe Spectrum (apparel) — high-intent visual product discovery.**
Pinterest is the highest-intent free traffic source for ecommerce that exists
outside Google Shopping. Users searching "tactical luxury jacket" or "all-black
outfit men" are actively planning a purchase. The EOS pattern:

- Shopify catalog feed → Pinterest catalog ingestion (daily) → auto-generated
  Product Pins for every SKU with live price, availability, and deep link
- Manually curated "lookbook" boards per drop, per aesthetic, per use case
- Agent drafts pin descriptions optimized for Pinterest SEO (keywords in first
  100 chars, board name keyworded, alt text)
- Antony reviews and posts; agent schedules via API at known peak hours
- Weekly performance pull → top pins by outbound click → those become Meta /
  Google Shopping creative

**Personal brand — long-form content distribution.**
Pinterest is a blog traffic engine. Long-form essays, video transcripts, and
"life maxing" frameworks get repackaged as vertical 1000x1500 pins with text
overlay that drive saves and outbound clicks back to antonyfmunoz.com. A single
viral pin can drive traffic for two years. The EOS pattern:

- Each long-form post → 5-10 pin variants (different hooks, different visuals)
- Pins distributed across niche-specific boards (entrepreneurship, systems,
  Portland, tactical aesthetic)
- Agent monitors `analytics/pins` weekly, kills underperforming variants,
  doubles down on winners

**Why Pinterest is search-engine, not social.** Treat every pin like a blog
post and every board like a category page. Description is body copy. Title is
H1. Image is hero. The algorithm rewards depth (relevance) and freshness (new
pin to existing high-performing board).

## Authentication

Pinterest API v5 requires **OAuth 2.0 with the authorization code flow** (PKCE
recommended for public clients). Steps:

1. Create a Pinterest **business account** (personal accounts cannot use the
   API). Convert at business.pinterest.com — free.
2. Register an app at developers.pinterest.com → "My apps" → "Create app".
   Note the App ID and App Secret.
3. Add a redirect URI exactly matching what your code will send.
4. Define scopes — request only what you need. Common scopes:
   - `boards:read`, `boards:write`
   - `pins:read`, `pins:write`
   - `user_accounts:read`
   - `catalogs:read`, `catalogs:write` (Shopping)
   - `ads:read` (analytics for ad accounts)
5. Send user to:
   `https://www.pinterest.com/oauth/?client_id=...&redirect_uri=...&response_type=code&scope=boards:read,pins:write,...&state=...`
6. Exchange the returned `code` for an access token via
   `POST https://api.pinterest.com/v5/oauth/token` with HTTP Basic Auth
   (`client_id:client_secret`).
7. Persist the **refresh token** — access tokens expire in 30 days; refresh
   tokens last ~60 days and rotate on use.

Sandbox: Pinterest exposes a **trial / sandbox mode** for new apps. Apps start
in trial with limited reach and must be submitted for review for production
scopes (especially `catalogs:write` and `ads:read`).

EOS storage convention: store `PINTEREST_APP_ID`, `PINTEREST_APP_SECRET`,
`PINTEREST_REFRESH_TOKEN` in `eos_ai/.env`. Never hardcode. The token refresher
runs nightly via cron and writes the new access token to a Neon row.

## Quick Reference

### Auth — refresh access token

```bash
curl -s -u "${PINTEREST_APP_ID}:${PINTEREST_APP_SECRET}" \
  -d "grant_type=refresh_token&refresh_token=${PINTEREST_REFRESH_TOKEN}" \
  https://api.pinterest.com/v5/oauth/token
```

### Create a pin (image URL source)

```bash
curl -s -X POST https://api.pinterest.com/v5/pins \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "board_id": "1234567890",
    "title": "Tactical luxury all-black outfit",
    "description": "All-black men outfit. Lyfe Spectrum tactical luxury aesthetic. Shop the look.",
    "alt_text": "Man in black bomber, black tee, black trousers, black boots",
    "link": "https://lyfespectrum.com/products/black-bomber-jacket?utm_source=pinterest",
    "media_source": {
      "source_type": "image_url",
      "url": "https://cdn.lyfespectrum.com/imgs/black-bomber-1000x1500.jpg"
    }
  }'
```

### List boards

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://api.pinterest.com/v5/boards?page_size=100"
```

### Get pin analytics (last 30 days)

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://api.pinterest.com/v5/pins/${PIN_ID}/analytics?start_date=2026-03-07&end_date=2026-04-06&metric_types=IMPRESSION,SAVE,PIN_CLICK,OUTBOUND_CLICK"
```

### Python (httpx) idiom

```python
import os, httpx
TOKEN = os.environ["PINTEREST_ACCESS_TOKEN"]
client = httpx.Client(
    base_url="https://api.pinterest.com/v5",
    headers={"Authorization": f"Bearer {TOKEN}"},
    timeout=30,
)
r = client.post("/pins", json={...})
r.raise_for_status()
pin = r.json()
```

### Trigger Shopify catalog ingestion

```bash
curl -s -X POST https://api.pinterest.com/v5/catalogs/feeds \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "lyfe_spectrum_main",
    "format": "XML",
    "location": "https://lyfespectrum.com/admin/feed/pinterest.xml",
    "catalog_type": "RETAIL",
    "default_country": "US",
    "default_locale": "en-US"
  }'
```

## Conceptual Model

**Pinterest is a query-driven knowledge graph, not a follower-driven feed.**
The unit is the pin. Pins live on boards. Boards are owned by users. Every pin
is indexed by its image (visual embedding), its title, its description, its
board name, its destination URL, and the engagement signal it accumulates over
time. When a user types "all black outfit men," Pinterest scores every pin in
its index against that query and returns a ranked feed.

Three implications drive every operational decision:

1. **Pin lifetime is months to years.** A well-keyworded pin that gets a few
   saves in week one keeps surfacing. There is no "post and decay" curve like
   Instagram. This is why pin SEO matters more than pin volume.
2. **Boards are categories, not playlists.** A board called "Outfits" is dead.
   A board called "All Black Tactical Outfits for Men" is a category page that
   ranks. Each board should have 20+ pins in tight semantic alignment.
3. **The destination URL is part of the index.** Outbound clicks and dwell
   time on the destination feed back into ranking. A pin that drives clicks to
   a slow-loading landing page eventually loses ranking even if its visual is
   strong.

**Pin lifecycle:**
draft (manual or API) → published (immediately indexed) → impression-rich
phase (week 1-4 if board is healthy) → long-tail SEO traffic (months 2-24) →
either reignited by a fresh save spike or quietly decays.

**Idea Pins vs standard pins.** Idea Pins (Pinterest's "Story Pin" successor —
multi-page, video-capable, no outbound link in some markets) live in a separate
endpoint shape and serve a different purpose: top-of-funnel discovery, not
direct traffic. Lyfe Spectrum should default to standard image pins with
outbound links. Personal brand can experiment with Idea Pins for repurposed
short-form video.

## Gotchas

- **Personal Pinterest accounts cannot use the API.** You will hit `403` with
  no useful error. Convert to a free business account first.
- **Idea Pins are a different endpoint and a different content shape** from
  regular pins. Don't try to POST `/pins` with multiple pages — use the Idea
  Pin endpoints, and accept that outbound links may be restricted by region.
- **Adding a scope after auth requires re-authorization.** Refresh tokens
  carry the original scope set. If you decide six months later you need
  `catalogs:write`, you must run the auth flow again.
- **Analytics has a 24-48 hour lag.** A pin posted Monday morning will not
  show full impression data until Wednesday. Don't kill pins on day-1 numbers.
- **Image quality is a hard ranking signal.** Pins under 600px on the long
  edge get suppressed. Target 1000x1500 (2:3) minimum, ideally 1600x2400.
- **Video pin requirements** are strict: MP4/MOV/M4V, 2GB max via media upload
  flow, 4s-15min, minimum 240p but 1080p strongly preferred, 9:16 or 1:1.
- **Rate limit ~1000 calls/hour per user token, per app** as of 2026-04. Burst
  is enforced; expect 429 with `Retry-After` header on rapid sequential POSTs.
- **Refresh tokens rotate.** Every refresh returns a NEW refresh token. If you
  don't persist it, you lose auth in ~60 days. EOS persists to Neon on every
  refresh.
- **Catalog ingestion is async.** POST to `/catalogs/feeds` returns
  immediately; actual product processing takes 1-24 hours and is reported via
  `processing_results`.
- **Domain verification is required for Rich Pins** to show price/availability.
  Verify via meta tag, file upload, or DNS TXT at developers.pinterest.com.
- **Trial mode caps reach.** Apps in trial mode have severely limited audience
  reach until reviewed. Submit for review the moment a real production use
  case exists.

See references/best_practices.md for the full 19-section creator-level
knowledge base covering API surface, ranking signals, board strategy,
catalog ingestion, and EOS playbooks.
