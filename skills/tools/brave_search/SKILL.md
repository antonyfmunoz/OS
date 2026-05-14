---
name: brave_search
description: "Use when any agent or script needs to perform web search, news search, or retrieve structured search results via the Brave Search API."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://api.search.brave.com/app/documentation/web-search/get-started"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "v1"
sdk_version: "REST API (no official Python SDK — raw HTTP via requests or urllib)"
speed_category: medium
trigger: both
effort: low
context: fork
---

# Tool: Brave Search API

## What This Tool Does

Brave Search API provides independent, privacy-focused web search results via a
REST API. Unlike Google or Bing wrappers, Brave maintains its own search index.
The API exposes multiple search verticals in a single call.

Core capabilities used by EOS:
- **Web search** — general web results with titles, URLs, descriptions, and age metadata
- **News search** — time-sensitive results from news sources, included in web search response
  via `result_filter=web,news` or standalone via the news endpoint
- **Freshness filtering** — restrict results by recency: `pd` (24h), `pw` (7d), `pm` (31d),
  or explicit date ranges like `2026-01-01to2026-04-06`
- **Safe search** — `off`, `moderate`, `strict` content filtering
- **Spellcheck control** — disable auto-correction for precise technical queries
- **Text decorations** — toggle bold/highlight markup in snippets

Not currently used but available:
- **Images search** — `/res/v1/images/search`
- **Videos search** — `/res/v1/videos/search`
- **Suggest** — `/res/v1/suggest/search` for autocomplete
- **Summarizer** — AI-generated answer summaries (Pro/Data plans)
- **Local/POI results** — places, addresses, ratings (returned in web search when relevant)

## EOS Integration

### Primary consumer
`.agents/skills/last30days/scripts/lib/brave_search.py` — web research backend for the
last30days research skill. Used when `BRAVE_API_KEY` is configured and Parallel AI is
not available (Brave is priority 2 in the web search backend chain).

### Integration pattern
```
last30days.py
  -> env.py::get_web_search_source()  # priority: parallel > brave > openrouter
  -> brave_search.py::search_web(topic, from_date, to_date, api_key, depth)
  -> HTTP GET to api.search.brave.com/res/v1/web/search
  -> _normalize_results() merges news + web results into unified schema
```

### Key design decisions in EOS
- **Auth via header** — `X-Subscription-Token: {api_key}` on every request
- **Merged result types** — news and web results combined in a single list, news first
  (news results tend to be more recent)
- **Excluded domains** — reddit.com and twitter.com/x.com filtered out (handled by
  dedicated Reddit/X search backends)
- **Freshness mapping** — days between date range mapped to Brave freshness codes:
  <=1d=`pd`, <=7d=`pw`, <=31d=`pm`, >31d=explicit date range
- **Fixed relevance score** — Brave doesn't provide relevance scores, so EOS assigns
  a flat 0.6 to all results
- **Date parsing** — Brave returns relative dates ("3 hours ago", "2 days ago") which
  `_parse_brave_date()` converts to YYYY-MM-DD format

### Env var
```
BRAVE_API_KEY=    # stored in ~/.config/last30days/.env or passed via environment
```
Not in `eos_ai/.env` or `services/.env` — the key lives in the last30days skill config.

## Authentication

### API key auth
1. Go to https://brave.com/search/api/ and create an account
2. Subscribe to a plan (Free tier: 2,000 queries/month)
3. Go to API dashboard: https://api-dashboard.search.brave.com/
4. Copy the API key (starts with `BSA...`)
5. Store as `BRAVE_API_KEY` in `~/.config/last30days/.env`

### Header format
Every request must include:
```
X-Subscription-Token: {your_api_key}
```
No OAuth, no refresh tokens, no expiry. The key is permanent until revoked.

### Subscription tiers
| Tier     | Queries/month | Price      | Features                              |
|----------|---------------|------------|---------------------------------------|
| Free     | 2,000         | $0         | Web search, news, 1 req/sec           |
| Base     | 20,000        | ~$5/month  | + images, videos                      |
| Pro      | 50,000+       | ~$9/month  | + AI summaries, data for AI           |
| Data for AI | Custom     | Custom     | Full index access, commercial use     |

## Quick Reference

### Basic web search
```python
import requests

response = requests.get(
    "https://api.search.brave.com/res/v1/web/search",
    headers={"X-Subscription-Token": api_key},
    params={
        "q": "entrepreneurOS AI business automation",
        "count": 10,
    },
)
data = response.json()
for result in data.get("web", {}).get("results", []):
    print(result["title"], result["url"])
```

### Search with freshness filter
```python
params = {
    "q": "AI agents startup funding",
    "count": 20,
    "freshness": "pw",           # last 7 days
    "safesearch": "moderate",
    "text_decorations": 0,       # no <b> tags in snippets
}
```

### Date range search
```python
params = {
    "q": "solopreneur revenue milestones",
    "freshness": "2026-03-01to2026-04-06",  # explicit range
    "count": 20,
}
```

### News-only search
```python
response = requests.get(
    "https://api.search.brave.com/res/v1/news/search",
    headers={"X-Subscription-Token": api_key},
    params={"q": "AI startup funding", "count": 20, "freshness": "pw"},
)
news = response.json().get("results", [])
```

### Parse results (EOS pattern)
```python
raw = data.get("news", {}).get("results", []) + data.get("web", {}).get("results", [])
for r in raw:
    title = r.get("title", "")
    url = r.get("url", "")
    snippet = r.get("description", "")
    age = r.get("age", "")          # "3 hours ago", "2 days ago"
    page_age = r.get("page_age", "")  # ISO-ish timestamp
```

## Conceptual Model

```
Brave Search API v1
  |
  +-- Web Search (/res/v1/web/search)
  |     |-- Returns: web, news, videos, faq, infobox, discussions, locations
  |     |-- Params: q, count, offset, freshness, safesearch, country, search_lang
  |     |-- Result filter: "web", "news", "web,news", "videos", etc.
  |     +-- Max 20 results per request (offset for pagination)
  |
  +-- News Search (/res/v1/news/search)
  |     |-- Dedicated news endpoint
  |     +-- Same auth, similar params
  |
  +-- Images Search (/res/v1/images/search)
  +-- Videos Search (/res/v1/videos/search)
  +-- Suggest (/res/v1/suggest/search)
  +-- Summarizer (Pro+ plans)
  |
  +-- Authentication
        |-- Single API key via X-Subscription-Token header
        |-- No OAuth, no token rotation
        +-- Rate limited per plan tier
```

See references/best_practices.md for rate limits, error codes, and anti-patterns.

## Gotchas

### Brave doesn't return relevance scores
Unlike Google Custom Search or Bing, Brave provides no relevance/confidence score
per result. EOS assigns a flat 0.6. If you need ranking, you must implement your
own scoring based on title/snippet keyword matching.

### `age` field is relative, not absolute
Brave returns `"3 hours ago"`, `"2 days ago"` — not ISO timestamps. The
`_parse_brave_date()` function in EOS handles conversion but can lose precision
for older results (e.g., "January 2026" has no day).

### Freshness filter is coarse for short periods
`pd` = past 24h, `pw` = past week, `pm` = past month. There's no "past 3 days"
shorthand. For precise ranges, use explicit `YYYY-MM-DDtoYYYY-MM-DD` format.

### Free tier is 1 request per second
Exceeding this returns 429. The free tier is 2,000 queries/month with a 1 req/sec
rate limit. No burst allowance.

### `result_filter` silently drops types
If you request `result_filter=web,news` but there are no news results, the `news`
key is simply absent from the response (not an empty array). Always use
`.get("news", {}).get("results", [])` — never assume the key exists.

### News endpoint vs web endpoint news results
`/res/v1/news/search` returns a flat list of news articles. `/res/v1/web/search`
with `result_filter=web,news` returns news in a nested `news.results` array
alongside web results. The response shapes are different.

### Text decorations enabled by default
Brave wraps matched terms in `<b>` tags by default. Set `text_decorations=0` to
get clean text, which is what EOS does. Forgetting this means your snippets
contain HTML markup that breaks plain text rendering.

### Country/language affects result set significantly
The `country` parameter (e.g., `US`, `GB`) and `search_lang` parameter change
which results appear. Omitting them defaults to the API's geo-inference from
the server IP, which on a VPS may not be the intended locale.
