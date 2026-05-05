---
name: firecrawl
description: "Use when scraping a single URL, crawling a site async, mapping URLs for fast discovery, extracting structured data via LLM-guided schema, running search/deep-research, batch-scraping, or driving browser actions (click/scroll/wait) against Firecrawl cloud or self-hosted. Returns LLM-ready markdown."
allowed-tools: "Read, Write, Edit, Bash, WebFetch, WebSearch"
version: 1.0
source_url: "https://docs.firecrawl.dev"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "v1"
sdk_version: "firecrawl-py==2.6.0"
speed_category: "medium"
trigger: both
effort: medium
context: fork
---

# Tool: Firecrawl

Web scraping + crawling API built for LLM pipelines. Turns URLs into
clean markdown + normalized metadata, handles JS rendering, proxies,
anti-bot, PDFs, and schema-guided structured extraction server-side.

## What This Tool Does

- **scrape** — one URL → markdown (+ html/links/screenshot/extract)
- **crawl** — async site crawl with path filters + webhook delivery
- **map** — fast URL discovery (sitemaps + link graph), no rendering
- **extract** — LLM-guided JSON matching a JSON Schema / pydantic model
- **search** — web search + auto-scrape each result
- **deep research** — agentic multi-hop research with citations
- **batch scrape** — async bulk scrape of a supplied URL list
- **actions** — click/scroll/wait/write/screenshot/executeJavascript

**The core primitive**: one URL in, clean markdown + metadata out.
Everything else is composition — `crawl = scrape × N + discovery`,
`extract = scrape + LLM schema pass`, `search = web_search + scrape × N`.

## EOS Integration

**Primary consumers:**
- Wiki ingestion — `map` docs site → filter → `batch_scrape_urls` →
  `extract` with `WikiEntry` schema → upsert to Neon `wiki` table.
- Initiate Arena lead research — `search` with ICP query → `extract`
  with `Lead` schema → write to `leads` table.
- Competitor monitoring — weekly `map` → diff URL lists → scrape only
  the new URLs → summarize via `model_router.call_with_fallback`.
- Content research — `deep_research(topic)` → cite sources in draft.
- Site audits — crawl own site → flag non-200 via `metadata.statusCode`.

**Canonical pattern: map first, filter, batch-scrape.** Never
unbounded crawl. Never scrape-then-LLM when extract-with-schema will
do. Never extract without a schema.

**Env**: `FIRECRAWL_API_KEY=fc-...` in `/opt/OS/eos_ai/.env` and
`/opt/OS/services/.env`. Wrapper at `eos_ai/tools/firecrawl_client.py`
adds tenacity retry on 429/5xx and logs credit usage to `cost_ledger`.

## Authentication

- Key format: `fc-` + 32+ char token. Header:
  `Authorization: Bearer fc-...`.
- Cloud: `https://api.firecrawl.dev`, requires real key.
- Self-hosted: `http://localhost:3002`, set `USE_DB_AUTHENTICATION=false`
  in compose env and pass `api_url=` to the SDK. Requires Playwright
  service container + Redis queue. Multi-GB image, 4GB+ RAM.
- Rotate via dashboard → Settings → API Keys. Old key invalidated
  immediately.

## Quick Reference

### Minimal scrape to markdown
```python
import os
from firecrawl import FirecrawlApp

app = FirecrawlApp(api_key=os.getenv("FIRECRAWL_API_KEY"))

r = app.scrape_url(
    "https://www.paulgraham.com/greatwork.html",
    params={"formats": ["markdown"], "onlyMainContent": True, "timeout": 30000},
)
md = r["data"]["markdown"]
status = r["data"]["metadata"]["statusCode"]  # always check — 404 pages still "succeed"
```

### Map + batch scrape (canonical pipeline)
```python
# 1. discover
urls = app.map_url(
    "https://lyfeinstitute.com",
    params={"search": "program", "limit": 1000},
)["links"]

# 2. filter in Python — cheap
blog = [u for u in urls if "/blog/" in u]

# 3. batch scrape async
job = app.batch_scrape_urls(blog, params={"formats": ["markdown"], "onlyMainContent": True})
batch_id = job["id"]
# poll GET /v1/batch/scrape/{id} until status == "completed"
```

### Crawl with webhook
```python
job = app.async_crawl_url(
    "https://lyfeinstitute.com",
    params={
        "limit": 200, "maxDepth": 4,
        "includePaths": ["/blog/.*", "/programs/.*"],
        "excludePaths": ["/admin/.*"],
        "scrapeOptions": {"formats": ["markdown"], "onlyMainContent": True},
        "webhook": {
            "url": "https://eos.munozconglomerate.com/webhooks/firecrawl",
            "headers": {"X-EOS-Auth": os.getenv("EOS_WEBHOOK_SECRET")},
            "metadata": {"venture": "lyfe_institute"},
            "events": ["completed", "failed"],
        },
    },
)
crawl_id = job["id"]  # persist immediately; results expire in 24h
```

### Extract with pydantic schema
```python
from pydantic import BaseModel, Field

class Product(BaseModel):
    name: str = Field(description="Product display name")
    price_usd: float
    sku: str
    in_stock: bool

job = app.extract(
    urls=["https://shop.example.com/p/widget-1", "https://shop.example.com/p/widget-2"],
    params={"prompt": "Pull product details from each page",
            "schema": Product.model_json_schema()},
)
# poll app.get_extract_status(job["id"]) until completed
```

### JS-heavy SPA with actions
```python
r = app.scrape_url(
    "https://app.example.com/dashboard",
    params={
        "formats": ["markdown", "screenshot@fullPage"],
        "waitFor": 2000,
        "actions": [
            {"type": "wait", "selector": ".article-body", "milliseconds": 5000},
            {"type": "click", "selector": "button#accept-cookies"},
            {"type": "scroll", "direction": "down"},
            {"type": "wait", "milliseconds": 1000},
            {"type": "screenshot", "fullPage": True},
        ],
        "proxy": "stealth",  # escalate on 403/empty body
    },
)
```

### Search with auto-scrape
```python
r = app.search("best LLM scraping APIs 2026",
               params={"limit": 10, "scrapeOptions": {"formats": ["markdown"]}})
```

### Deep research
```python
r = app.deep_research("competitors of Lyfe Institute in life coaching",
                      params={"maxDepth": 5, "maxUrls": 40, "timeLimit": 180})
```

## Gotchas

- **`statusCode` lives in metadata — a 404 page is a "successful"
  scrape.** Always check `data.metadata.statusCode` before trusting
  markdown. The content is whatever the 404 page rendered.
- **Crawl results expire in 24 hours.** Persist to Neon immediately on
  receipt; do NOT rely on the Firecrawl cache.
- **`batch/scrape` is async and must be polled.** Unlike single
  `scrape`, it returns `{id}` — code that assumes sync returns job
  metadata as "content" and silently corrupts downstream.
- **`extract` is async too.** Poll `get_extract_status(id)`.
- **JS-heavy SPAs** default to `networkidle` — post-`networkidle`
  skeleton loaders render as empty markdown. Add an `actions` array
  with `{type:"wait", selector:".article-body", milliseconds:5000}`.
- **Always prefer `map` → filter → `batch_scrape` over `crawl`.** Map
  walks sitemaps in seconds; crawl spins Playwright per page. 100×
  cost difference.
- **Always set `limit` and `maxDepth` on crawl.** Crawl `limit` is a
  hard cap with no warning — check `total` against your `limit` to
  know if you hit the ceiling.
- **Never `extract` without a `schema`.** Prompt-only extract is
  free-form and fragile; schema extract is cheaper, validated, and
  batched. It is materially cheaper than scrape + your own Claude pass.
- **`onlyMainContent: true`** is almost always right for LLM ingestion
  — strips nav/footer/sidebar/cookie banners. Turn off only when you
  need page chrome structure.
- **Screenshots default to full-page** — long pages = 5MB+ PNGs. Use
  `fullPage: false` for viewport-only.
- **`formats` is pay-per-item.** Don't request everything; ask for
  what you actually need downstream.
- **`excludePaths` uses glob-like patterns, not regex.** Test on a
  small crawl first — wrong exclude is the #1 reason a crawl scrapes
  10× the intended pages.
- **Max 100 URLs per `/v1/extract` call** — silently truncated.
- **Max 1000 URLs per `/v1/batch/scrape` call.**
- **Webhook delivery is at-least-once.** Handler must be idempotent;
  dedupe on `jobId + sequence`. No native HMAC signing — use a shared
  secret in `headers` and reconcile via `GET /v1/crawl/{id}` on
  `crawl.completed` if authenticity matters.
- **Webhook retries**: 3 attempts, 2s/8s/32s backoff, then dropped.
- **Rate limits are per API key.** Parallelizing across processes on
  the same key shares the bucket — use `batch_scrape_urls` instead of
  parallel single scrapes.
- **Crawl respects robots.txt by default.** Override with
  `ignoreRobotsTxt: true` ONLY with explicit permission — legal +
  reputational risk otherwise.
- **Self-hosted does NOT bundle an LLM** — extract calls fail without
  `OPENAI_API_KEY` (or equivalent) in compose env. Scrape/crawl/map
  work without.
- **Self-hosted image is multi-GB** — Playwright browsers, 1-2 GB RAM
  per concurrent context. Don't run on a 1GB VPS.
- **Markdown conversion degrades on complex tables, syntax-highlighted
  code, and KaTeX/MathJax.** Also request `html` and post-process if
  downstream cares.
- **Residential proxy requests cost more credits** — profile top
  callers if running tight.
- **v0 endpoints are gone** — always `/v1/...`.
- **SDK drift** — new features (deep research, extract v2, actions)
  only exist in recent SDK versions. Pin `firecrawl-py==2.6.0`; when
  a method is missing, upgrade SDK before assuming the API lacks it.

## Verification

```bash
python3 -c "
toolname='firecrawl'
c=open(f'/opt/OS/skills/tools/{toolname}/SKILL.md').read()
b=open(f'/opt/OS/skills/tools/{toolname}/references/best_practices.md').read()
assert len(c)>500 and '## Authentication' in c and '## Gotchas' in c
assert len(b)>2000
for s in ['Authentication','Core Operations','Pagination','Rate Limits',
          'Error Codes','SDK Idioms','Anti-Patterns','Data Model','Webhooks',
          'Limits','Cost Model','Version Pinning','Design Intent',
          'Problem-Solution Map','Operational Behavior','Ecosystem Position',
          'Trajectory','Conceptual Model','Industry Expert']:
    assert f'## {s}' in b, f'Missing {s}'
print('PASS')
"
```

See `references/best_practices.md` for the full 19-section reference.
