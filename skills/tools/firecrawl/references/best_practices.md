# Firecrawl — Creator-Level Best Practices

Source: docs.firecrawl.dev, github.com/mendableai/firecrawl,
Mendable/Firecrawl founder interviews, firecrawl-py changelog.
API Version: v1 (stable as of 2026)
SDK Version: firecrawl-py 2.6.0
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## Authentication

- API key: prefix `fc-` followed by 32+ char token.
  Example: `fc-1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p`
- Header: `Authorization: Bearer fc-...`
- Cloud base URL: `https://api.firecrawl.dev`
- Self-hosted: `http://localhost:3002` from
  `github.com/mendableai/firecrawl` docker-compose. Set
  `USE_DB_AUTHENTICATION=false` in compose env, then SDK accepts an
  empty key: `FirecrawlApp(api_key="", api_url="http://localhost:3002")`.
- Self-hosted requires Playwright worker + Redis queue. Multi-GB image,
  budget 4GB RAM minimum dev, 8-16GB production.
- Rotate via dashboard → Settings → API Keys. Old key invalidated
  immediately.
- EOS storage: `FIRECRAWL_API_KEY=fc-...` in `/opt/OS/eos_ai/.env` and
  mirrored in `/opt/OS/services/.env`. Always `os.getenv(...)`, never
  hardcoded.

## Core Operations

| Operation     | Endpoint                   | Sync/Async | Credits |
|---------------|----------------------------|------------|---------|
| Scrape        | POST /v1/scrape            | sync       | 1/page  |
| Batch scrape  | POST /v1/batch/scrape      | async      | 1/page  |
| Crawl         | POST /v1/crawl             | async      | 1/page  |
| Crawl status  | GET /v1/crawl/{id}         | sync poll  | free    |
| Map           | POST /v1/map               | sync       | 1/call  |
| Extract       | POST /v1/extract           | async      | 5+/page |
| Extract status| GET /v1/extract/{id}       | sync poll  | free    |
| Search        | POST /v1/search            | sync       | 1/result|
| Deep research | POST /v1/deep-research     | async      | 10+     |
| Screenshot    | format in scrape           | sync       | +1/page |

### POST /v1/scrape
```json
{
  "url": "https://example.com/post",
  "formats": ["markdown", "html", "rawHtml", "links",
              "screenshot", "screenshot@fullPage", "extract"],
  "onlyMainContent": true,
  "includeTags": ["article", "main"],
  "excludeTags": ["nav", "footer", "aside"],
  "headers": {"Cookie": "session=..."},
  "waitFor": 2000,
  "timeout": 30000,
  "mobile": false,
  "skipTlsVerification": false,
  "removeBase64Images": true,
  "blockAds": true,
  "proxy": "auto",
  "location": {"country": "US", "languages": ["en-US"]},
  "actions": [
    {"type": "wait", "milliseconds": 1500},
    {"type": "click", "selector": "#load-more"},
    {"type": "scroll", "direction": "down"},
    {"type": "write", "text": "search query"},
    {"type": "press", "key": "Enter"},
    {"type": "screenshot", "fullPage": true},
    {"type": "executeJavascript",
     "script": "window.scrollTo(0,document.body.scrollHeight)"}
  ],
  "extract": {
    "schema": {"...JSON schema..."},
    "systemPrompt": "Extract only product info",
    "prompt": "Pull title, price, sku"
  }
}
```

### POST /v1/crawl
```json
{
  "url": "https://example.com",
  "limit": 100,
  "maxDepth": 3,
  "includePaths": ["/blog/.*"],
  "excludePaths": ["/admin/.*", "/login"],
  "allowBackwardLinks": false,
  "allowExternalLinks": false,
  "ignoreSitemap": false,
  "scrapeOptions": {
    "formats": ["markdown", "links"],
    "onlyMainContent": true,
    "waitFor": 1000
  },
  "webhook": {
    "url": "https://your.app/webhooks/firecrawl",
    "headers": {"X-Auth": "..."},
    "metadata": {"venture": "lyfe_institute"},
    "events": ["started", "page", "completed", "failed"]
  }
}
```
Response: `{"success": true, "id": "abc-123", "url": "https://api.firecrawl.dev/v1/crawl/abc-123"}`

### GET /v1/crawl/{id}
```json
{
  "status": "scraping",
  "total": 100,
  "completed": 47,
  "creditsUsed": 47,
  "expiresAt": "2026-04-07T12:00:00Z",
  "next": "https://api.firecrawl.dev/v1/crawl/abc-123?skip=10",
  "data": [{"markdown": "...", "metadata": {}}]
}
```
States: `scraping`, `completed`, `failed`, `cancelled`.

### POST /v1/map
```json
{"url":"https://example.com","search":"pricing","ignoreSitemap":false,"includeSubdomains":false,"limit":5000}
```
Response: `{"success": true, "links": ["https://...", ...]}`

### POST /v1/extract
```json
{
  "urls": ["https://a.com/p1", "https://a.com/p2"],
  "prompt": "Get product name and price",
  "schema": {"type":"object","properties":{
    "name":{"type":"string"},"price":{"type":"number"}
  },"required":["name","price"]},
  "enableWebSearch": false
}
```
Returns `{"success": true, "id": "ext-..."}`. Poll `GET /v1/extract/{id}`.

### POST /v1/search
```json
{"query":"best LLM scraping APIs 2026","limit":10,"lang":"en","country":"us","tbs":"qdr:m","scrapeOptions":{"formats":["markdown"]}}
```

### POST /v1/batch/scrape
Same shape as scrape but accepts a URL list. Async — returns job id;
poll `GET /v1/batch/scrape/{id}`.

### POST /v1/deep-research
```json
{"query":"competitors of X","maxDepth":5,"maxUrls":40,"timeLimit":180}
```

## Pagination

- Crawl: poll `GET /v1/crawl/{id}` every 2-5s. `data` is paginated ~10
  pages per response; walk `next` cursor.
- Batch scrape: `GET /v1/batch/scrape/{id}`, same pattern.
- Extract: `GET /v1/extract/{id}`, `processing` → `completed`.
- Crawl results expire after 24h — persist immediately.

## Rate Limits

| Plan       | Scrape /min | Crawls concurrent | Map /min | Extract /min |
|------------|-------------|-------------------|----------|--------------|
| Free       | 10          | 1                 | 10       | 5            |
| Hobby      | 20          | 3                 | 20       | 10           |
| Standard   | 100         | 50                | 100      | 50           |
| Growth     | 1000        | 100               | 1000     | 500          |
| Enterprise | custom      | custom            | custom   | custom       |

429 responses include `Retry-After` in seconds. SDK does NOT retry
automatically — wrap in tenacity or manual backoff. Rate limits are
per-API-key, not per-IP — parallelizing across processes shares the
bucket. Use batch scrape for high throughput.

## Error Codes

| Code | Meaning                           | Action                           |
|------|-----------------------------------|----------------------------------|
| 400  | Bad request / invalid schema      | Inspect `error`, fix payload     |
| 401  | Missing / invalid API key         | Rotate                           |
| 402  | Insufficient credits              | Top up plan                      |
| 403  | URL blocked / robots disallow     | Use different URL or override    |
| 404  | Job id not found / expired        | Re-submit (24h expiry)           |
| 408  | Page timeout                      | Increase `timeout` + `waitFor`   |
| 429  | Rate limited                      | Honor `Retry-After`              |
| 500  | Internal                          | Retry with backoff               |
| 502  | Upstream proxy failure            | Retry, escalate `proxy:"stealth"`|
| 504  | Gateway timeout                   | Reduce complexity                |

Error shape: `{"success": false, "error": "msg", "code": "ERR_TIMEOUT"}`.

**Critical**: a scrape of a page returning HTTP 404 is a *successful*
Firecrawl call. Check `data.metadata.statusCode` before trusting the
content.

## SDK Idioms

### firecrawl-py 2.6.0

```
pip install firecrawl-py==2.6.0
```
Node equivalent: `@mendable/firecrawl-js@^1.20.0`.

```python
import os
from firecrawl import FirecrawlApp

app = FirecrawlApp(api_key=os.getenv("FIRECRAWL_API_KEY"))
# self-hosted:
# app = FirecrawlApp(api_key="", api_url="http://localhost:3002")
```

Methods:
```python
app.scrape_url(url, params=None) -> dict                     # sync
app.batch_scrape_urls(urls, params=None) -> dict             # async, {"id"}
app.crawl_url(url, params=None, poll_interval=2,
              idempotency_key=None) -> dict                  # blocks until done
app.async_crawl_url(url, params=None) -> dict                # returns {"id"}
app.check_crawl_status(crawl_id) -> dict
app.cancel_crawl(crawl_id) -> dict
app.map_url(url, params=None) -> dict
app.extract(urls, params=None) -> dict                       # async
app.get_extract_status(extract_id) -> dict
app.search(query, params=None) -> dict
app.deep_research(query, params=None) -> dict
```

### Code snippets

Basic scrape:
```python
r = app.scrape_url("https://www.paulgraham.com/greatwork.html",
    params={"formats":["markdown"],"onlyMainContent":True,"timeout":30000})
md = r["data"]["markdown"]
assert r["data"]["metadata"]["statusCode"] == 200
```

JS-heavy SPA with actions + screenshot:
```python
r = app.scrape_url("https://app.example.com/dashboard", params={
    "formats":["markdown","screenshot@fullPage"],
    "waitFor":2000,
    "actions":[
        {"type":"wait","selector":".article-body","milliseconds":5000},
        {"type":"click","selector":"button#accept-cookies"},
        {"type":"scroll","direction":"down"},
        {"type":"executeJavascript",
         "script":"window.scrollTo(0,document.body.scrollHeight)"},
        {"type":"wait","milliseconds":1000},
        {"type":"screenshot","fullPage":True}],
    "proxy":"stealth"})
```

Crawl with webhook:
```python
job = app.async_crawl_url("https://lyfeinstitute.com", params={
    "limit":200,"maxDepth":4,
    "includePaths":["/blog/.*","/programs/.*"],
    "excludePaths":["/admin/.*"],
    "scrapeOptions":{"formats":["markdown","links"],"onlyMainContent":True},
    "webhook":{
        "url":"https://eos.example.com/webhooks/firecrawl",
        "headers":{"X-EOS-Auth":os.getenv("EOS_WEBHOOK_SECRET")},
        "metadata":{"venture":"lyfe_institute","purpose":"wiki_ingest"},
        "events":["completed","failed"]}})
```

Extract with pydantic schema:
```python
from pydantic import BaseModel, Field
import time

class Product(BaseModel):
    name: str = Field(description="Product display name")
    price_usd: float
    sku: str
    in_stock: bool

job = app.extract(
    urls=["https://shop.example.com/p/1","https://shop.example.com/p/2"],
    params={"prompt":"Pull product details","schema":Product.model_json_schema()})
eid = job["id"]
while True:
    s = app.get_extract_status(eid)
    if s["status"] == "completed":
        rows = [Product(**r) for r in s["data"]]; break
    if s["status"] == "failed": raise RuntimeError(s.get("error"))
    time.sleep(3)
```

Batch scrape:
```python
job = app.batch_scrape_urls(["https://a.com","https://b.com","https://c.com"],
    params={"formats":["markdown"],"onlyMainContent":True})
# poll GET /v1/batch/scrape/{job["id"]} until status == "completed"
```

Map → filter → batch (canonical):
```python
urls = app.map_url("https://lyfeinstitute.com",
    params={"search":"program","limit":1000})["links"]
blog = [u for u in urls if "/blog/" in u]
job = app.batch_scrape_urls(blog,
    params={"formats":["markdown"],"onlyMainContent":True})
```

## Anti-Patterns

1. Crawling without `limit` — burns credits, hits plan caps.
2. `scrape_url` in a Python loop instead of `batch_scrape_urls`.
3. Expecting JS-heavy SPAs to render without `actions`/`waitFor`.
4. Polling crawl status faster than every 2s.
5. Requesting `html` when you want LLM context — markdown cheaper.
6. Forgetting `onlyMainContent: true`.
7. Lazy-persisting crawl results — expire in 24h.
8. Hardcoding `fc-...` keys.
9. Using v0 endpoints — gone.
10. Treating `extract` or `batch/scrape` as sync.
11. Skipping `Retry-After` on 429.
12. Self-hosting without Playwright service.
13. Assuming robots.txt honored on self-hosted by default.
14. Sending >100 URLs to `/v1/extract` — silently truncated.
15. Sending >1000 URLs to `/v1/batch/scrape` — rejected.
16. Not checking `statusCode` in metadata.
17. Asking for every format — pay per format.
18. Extract without a schema — fragile, expensive, unvalidated.

## Data Model

### Scrape response
```json
{
  "success": true,
  "data": {
    "markdown": "# Title\n\nBody...",
    "html": "<html>...</html>",
    "rawHtml": "<!doctype html>...",
    "links": ["https://...", "..."],
    "screenshot": "https://service.firecrawl.dev/screenshots/xyz.png",
    "metadata": {
      "title": "Page Title",
      "description": "...",
      "language": "en",
      "sourceURL": "https://example.com/post",
      "statusCode": 200,
      "ogTitle": "...",
      "ogImage": "https://...",
      "publishedTime": "2026-01-01T00:00:00Z"
    },
    "extract": {}
  }
}
```

### Crawl status
`{status, total, completed, creditsUsed, expiresAt, next, data[]}`

### Extract schema format
JSON Schema draft-07 subset. Supported: `string`, `number`, `integer`,
`boolean`, `array`, `object`. `enum` + `required` honored. Nested
objects allowed. Pydantic compiles via `Model.model_json_schema()`.

## Webhooks

Configured per crawl via `webhook` param.

Events:
- `crawl.started`
- `crawl.page` (fired per page)
- `crawl.completed`
- `crawl.failed`

Payload:
```json
{
  "type": "crawl.page",
  "id": "abc-123",
  "data": [{"markdown": "...", "metadata": {"sourceURL": "...", "statusCode": 200}}],
  "metadata": {"venture": "lyfe_institute"},
  "error": null
}
```

**At-least-once delivery.** Handler must be idempotent — dedupe on
`jobId + sequence number`. Retries: 3 attempts with 2s/8s/32s
exponential backoff, then dropped. No native HMAC signing as of
2026-Q1 — use a shared secret in `headers` and reconcile via
`GET /v1/crawl/{id}` on `crawl.completed` if authenticity matters.

## Limits

| Limit                      | Value                              |
|----------------------------|------------------------------------|
| Max pages per crawl        | 50,000 (Growth), 10,000 (Standard) |
| Max concurrent crawls      | per-plan (see rate limits)         |
| Max URL length             | 2,048 chars                        |
| Default timeout            | 30,000 ms                          |
| Max timeout                | 120,000 ms                         |
| Max actions per scrape     | 50                                 |
| Max URLs per batch scrape  | 1,000                              |
| Max URLs per extract call  | 100                                |
| Map result cap             | 5,000 URLs                         |
| Crawl result retention     | 24 hours                           |
| Screenshot max size        | 8 MB                               |

## Cost Model

Credit pricing:
- Scrape: 1/page
- Scrape + screenshot: 2
- Scrape + extract: 5
- Crawl: 1/page
- Map: 1/call
- Extract: 5/page base, +5 if `enableWebSearch`
- Search: 1/result
- Deep research: 10 minimum, scales with depth/URLs
- Residential proxy: extra credits

Tiers:
| Plan       | $/mo     | Credits/mo |
|------------|----------|------------|
| Free       | $0       | 500        |
| Hobby      | $19      | 3,000      |
| Standard   | $99      | 100,000    |
| Growth     | $399     | 500,000    |
| Enterprise | custom   | custom     |

Overages billed at the plan's marginal rate. Profile top callers — the
biggest spenders are usually crawl (replace with map + batch) and
extract (keep schema tight to minimize tokens).

## Version Pinning

```
# /opt/OS/requirements.txt
firecrawl-py==2.6.0
```
- API: `v1`
- Node SDK: `@mendable/firecrawl-js@1.20.0`
- Self-hosted image: `ghcr.io/mendableai/firecrawl:v1.20.0`

Verify:
```python
import firecrawl
print(firecrawl.__version__)  # 2.6.0
```

---

# Tier 2 — Creator Intelligence

## Design Intent

Firecrawl was built by **Caleb Peffer** and **Nicolas Camara**, founders
of **Mendable.ai** (YC S22), a chat-with-your-docs SaaS. While running
Mendable they hit the same wall every RAG team hits: **the hardest part
of an LLM pipeline is not the LLM — it is getting clean text into it.**
Customers wanted to point Mendable at a website and "just work." In
practice that meant crawling thousands of pages, bypassing anti-bot,
rendering SPAs, stripping chrome, and normalizing to something an LLM
could chunk and embed.

They solved it internally with brittle Playwright + Scrapy + custom
HTML-to-markdown code, then carved the scraper out as its own product,
open-sourced it, and re-applied to YC. **Firecrawl went through YC
W24.** Mendable still exists but Firecrawl is the headline business.

**Why a scraper specifically for LLM pipelines.** Legacy scrapers were
designed pre-LLM. Unit of output is HTML or a DOM tree. User writes
XPath/CSS and post-processes into rows. LLM pipelines flip every
assumption:
- Consumer is a model, not a SQL table.
- Ideal format is **markdown** (native to LLMs, tokens cheap,
  structure preserved).
- Want **content**, not chrome.
- Want it **per URL**, idempotent, with normalized metadata.
- Want a **single function call**, not a Scrapy project.

Tagline "Turn websites into LLM-ready data" is the design intent in six
words. Every endpoint is shaped to it.

**Apache 2.0 open-source** at `github.com/mendableai/firecrawl`.
Hosted API at `api.firecrawl.dev` is the commercial offering; engine is
open and self-hostable. Deliberate trust-building — OSS repo is the
top-of-funnel for the SaaS.

## Problem-Solution Map

| Endpoint    | Problem                                           |
|-------------|---------------------------------------------------|
| scrape      | One URL → clean markdown + metadata               |
| crawl       | Entire site (or subtree) scraped async            |
| map         | Fast URL discovery without rendering (100× crawl) |
| extract     | LLM schema-guided JSON from one or many URLs      |
| search      | Web search + auto-scrape each result              |
| deep research | Multi-hop research agent with citations         |
| actions     | Clicks/scrolls/waits before the final scrape     |
| batch scrape| 1000-URL bulk async without writing a loop        |
| self-hosted | Data residency, compliance, air-gapped, cost      |

## Operational Behavior

### Under the hood
Playwright + Chromium workers behind Redis/BullMQ. Thin TypeScript API
server validates + enqueues + serves results.

Per scrape:
1. Smart proxy layer — direct first, residential on retry if blocked.
2. Reuse or spin a Playwright context.
3. Navigate with configurable timeout (default 30s).
4. Wait for `networkidle` or custom `waitFor` selector.
5. Execute any `actions`.
6. Extract rendered HTML.
7. Mozilla Readability + heuristics strip boilerplate.
8. Convert to markdown via tuned turndown-style converter.
9. Capture metadata.
10. Return requested formats.

### Anti-bot strategies
Transparent, not configured:
- Stealth Playwright (patches `navigator.webdriver`, fingerprint spoofing)
- Residential proxy fallback on datacenter block
- CAPTCHA detection — fails fast with typed error
- Cloudflare challenge handling
- UA rotation + realistic headers

Residential proxy requests cost more credits.

### How `extract` uses LLMs
Routed across **GPT-4o-mini, Claude Haiku, Gemini Flash** based on load
and content size. Contract: schema in → JSON out matching schema.
Firecrawl handles retries, validation, reformatting. **Always provide a
schema** — cheaper, more reliable, validated. Prompt-only is free-form
and fragile.

### Crawl state machine
`scraping → completed | failed | cancelled`. Poll returns
`{status, total, completed, data[]}`. `data` paginated — follow `next`.

### Webhook delivery semantics
**At-least-once**. Idempotent handler required. Dedupe on
`jobId + sequence`. 3 retries, exponential backoff 2s/8s/32s. No
built-in HMAC as of 2026-Q1 — use shared-secret header and reconcile
via `GET /v1/crawl/{id}` on completion if authenticity is load-bearing.

## Ecosystem Position

**vs Apify** — Apify is a marketplace of pre-built Actors. Wins on
breadth for specific platforms (Instagram, TikTok, LinkedIn).
Firecrawl wins when target is a normal website consumed by an LLM.

**vs Scrapy** — Pre-LLM framework. Maximum control, maximum boilerplate.
Wins when you need fine-grained crawl logic. Firecrawl is the "one
afternoon, prod" answer.

**vs Playwright/Puppeteer direct** — DIY. Full control, zero abstraction
tax. Firecrawl wins when you never want to think about browser
management.

**vs Browserless** — Playwright-as-a-service at a lower level — you
write Playwright, they run it. Firecrawl wins when you don't want to
write Playwright at all.

**vs ScrapingBee** — Older, less LLM-native (HTML default, no extract
endpoint, no crawl job model). Firecrawl is materially better for LLM
pipelines.

**vs Bright Data** — Enterprise heavyweight. Best residential proxies,
scraping browser, dataset marketplace. Wins at massive scale, hostile
targets, geo IP diversity. Firecrawl wins on DX; graduate to Bright
Data when Firecrawl hits walls.

**vs Jina Reader** (`r.jina.ai`) — Closest sibling. Prepend
`r.jina.ai/` to a URL, get markdown. Free, dead simple, no SDK. Jina
wins on zero-friction one-offs. Firecrawl wins on everything else.
Jina is a feature; Firecrawl is a platform.

**vs Exa** — Search engine for LLMs, not a scraper. Overlaps with
Firecrawl's `search` endpoint. Use Exa when search quality matters
more than scrape control. Many stacks use **both**: Exa for discovery,
Firecrawl for heavy scrape + extract.

**Where Firecrawl loses**: Apify platform scrapers, Bright Data
residential proxies at scale, Scrapy-tier control, Browserless raw
Playwright, Jina's free unlimited one-offs.

**Where Firecrawl wins**: LLM-native markdown output, simplest API in
category, schema-guided extract in one call, open-source self-hosting
with identical code as SaaS, one vendor for scrape + crawl + map +
extract + search + deep research.

## Trajectory

**Recently shipped** (2025-2026):
- Extract v2 — better schema validation, multi-URL, prompt-only mode
- Deep research endpoint — agentic multi-step with citations
- Actions — click/write/scroll/wait/screenshot/executeJavaScript
- Self-hosted open source — full docker-compose, Apache 2.0
- Batch scrape — async bulk
- Search endpoint — web search + auto-scrape
- Map endpoint — fast URL discovery
- Webhooks for crawl jobs
- Stealth mode + residential proxy routing

**2026 direction**:
- **Agentic scraping** — natural-language goal, Firecrawl navigates
  and synthesizes. Deep research is v1; more abstractions coming.
- **Bigger action fleet** — full "browser as a service" competing
  with Browserless on capability while keeping LLM-native output.
- **More LLM-native abstractions** — RAG-shaped endpoints, first-class
  "ingest this site into a vector store."
- **Better self-hosting** — slimmer footprint, optional GPU for extract
  LLM, observability.
- **Tighter extract pricing** as small specialized models get cheaper.

## Conceptual Model

**The core primitive is: one URL in, clean markdown + metadata out.**

Everything else is composition:
- **crawl** = `scrape × N` with automatic URL discovery
- **map** = URL discovery only, no content (cheap half of crawl)
- **extract** = `scrape + LLM pass guided by a schema`
- **search** = `web_search + scrape × N` on results
- **deep research** = `search + extract + reason` in a loop
- **batch scrape** = `scrape × N` without discovery (you supply list)
- **actions** = `browser_interaction* + scrape` at the end

The API surface stops feeling like a list of unrelated endpoints —
it's one primitive plus a small algebra of combinators.

**The canonical pattern** is `map → filter → batch_scrape`. Map walks
sitemaps and link graphs in seconds. Filter in Python. Then batch
scrape the filtered list. Dramatically cheaper than naive crawl.

## Industry Expert

- **JS-heavy SPAs need `waitFor` with a selector.** Default waits for
  `networkidle` — post-networkidle skeleton loaders render as empty
  markdown. Fix: `actions:[{type:"wait",selector:".article-body",milliseconds:5000}]`.
- **Crawl respects robots.txt by default.** Override with
  `ignoreRobotsTxt: true` ONLY with explicit permission — legal +
  reputational risk. Self-hosted doesn't honor it unless
  `RESPECT_ROBOTS_TXT=true`.
- **Extract with schema is 5-10× cheaper** than scrape + your own
  Claude pass. Extraction-tuned small models, batched, validated.
  Always collapse the two steps into one `extract` call.
- **Dynamic content behind auth** — (1) custom `headers` with
  bearer/cookie, (2) login flow via `actions`, (3) enterprise stored
  browser sessions. MFA kills all three.
- **`map` is 100× faster than `crawl` for discovery.** Always
  `map → filter → batch_scrape`, never crawl when you only need URLs.
- **Screenshots are full-page by default.** Long pages = 5MB+ PNGs.
  Set `fullPage: false` or accept storage cost.
- **Batch scrape is async.** Don't assume sync returns scraped content.
- **Self-hosting is heavy.** Multi-GB image, 1-2 GB RAM per concurrent
  context, 4 GB minimum dev, 8-16 GB production.
- **Credit costs vary** — actions > basic, residential > datacenter,
  extract > scrape, deep research is expensive. Profile top callers.
- **`formats` is pay-per-item** — ask only for what you need.
- **Crawl `limit` is a hard cap with no warning.** Check `total` vs
  `limit` to know if you hit the ceiling.
- **Status codes are in metadata, not errors.** 404 page = successful
  scrape. Always check `metadata.statusCode`.
- **Markdown degrades on complex tables, syntax-highlighted code,
  KaTeX/MathJax.** Request `html` alongside if downstream cares.
- **`excludePaths` is glob-like, not full regex.** Test on a small
  crawl first.
- **SDK drift is real** — pin versions, upgrade SDK before assuming a
  feature is missing.
- **Rate limits are per-API-key, not per-IP.** Parallelizing shares
  the bucket — use batch endpoints.
- **Webhooks are at-least-once.** Handler must be idempotent.
- **Self-hosted does NOT bundle extract LLM.** Provide `OPENAI_API_KEY`
  (or equivalent) in compose env. Scrape/crawl/map work without it.
- **Use `onlyMainContent: true` aggressively** — strips nav/sidebar/
  footer/cookie banners.

---

## EOS Usage Patterns

- **Wiki ingestion**: `map` docs site → filter → `batch_scrape_urls` →
  `extract` with `WikiEntry` pydantic schema → upsert to Neon `wiki`.
- **Lead research**: `search` ICP query → `extract` with `Lead` schema
  (`name`, `company`, `title`, `email`, `pain`, `icebreaker`) → write
  to `leads` table.
- **Competitor monitoring**: weekly `map` → diff URL lists vs stored
  snapshot → scrape only the new URLs → summarize via
  `model_router.call_with_fallback(TaskType.FAST_RESPONSE)`.
- **Content research**: `deep_research(topic)` → cite sources in draft.
- **Site audits**: crawl own site → flag non-200 status codes via
  Discord webhook.
- **Wrapper module**: `eos_ai/tools/firecrawl_client.py` adds tenacity
  backoff on 429/5xx, logs credit usage to `cost_ledger` for tier
  monitoring. Default `proxy:"auto"`; escalate to `"stealth"` on 403
  or empty body.
- **Webhook receiver**: `services/webhook_server.py` validates the
  shared-secret header and dedupes on `jobId + sequence` before
  queuing into Neon.

## Gotchas (Compounds Over Time)

- **`metadata.statusCode` check mandatory** — 404 pages are "successful"
  scrapes.
- **Crawl results expire 24h** — persist immediately.
- **`batch/scrape` and `extract` are async** — must poll.
- **SPAs need `actions` with wait-for-selector** — networkidle returns
  skeleton HTML.
- **Canonical pipeline is `map → filter → batch_scrape`**, not crawl.
- **Crawl `limit` is a silent hard cap** — check `total` vs limit.
- **Never `extract` without a schema**.
- **`formats` is pay-per-item** — request only what you need.
- **`excludePaths` is glob, not regex** — test on small crawl.
- **Webhooks are at-least-once, no HMAC** — handler idempotent +
  shared secret + reconcile on completion.
- **Rate limits per key** — batch beats parallel single calls.
- **Self-hosted needs `OPENAI_API_KEY`** for extract.
- **Self-hosted image multi-GB** — 4 GB RAM minimum dev.
- **Residential proxy costs more credits** — escalate only on 403/
  empty body.
- **v0 endpoints gone** — always `/v1`.
- **Pin `firecrawl-py==2.6.0`** — SDK drift breaks new endpoints.
- **Max 100 URLs/extract, 1000/batch scrape** — silently truncated /
  rejected above.
- **Full-page screenshot default** — huge PNGs on long pages.
- **Markdown breaks on complex tables, highlighted code, KaTeX** —
  request `html` if it matters.
- **Robots.txt honored on cloud by default** — override only with
  explicit permission; self-hosted doesn't honor unless opted in.
