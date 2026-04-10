# Brave Search API — Creator-Level Best Practices
Source: https://api.search.brave.com/app/documentation/web-search/get-started
API Version: v1
SDK Version: REST API (no official Python SDK)
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## Authentication
**Method:** API key via HTTP header.

**Header:** `X-Subscription-Token: {api_key}`

**Key format:** Alphanumeric string, typically prefixed with `BSA`. Obtained from the
Brave Search API dashboard at https://api-dashboard.search.brave.com/.

**Scopes:** No granular scopes. A single key grants access to all endpoints available
on your subscription tier. Free tier keys cannot access summarizer or Data for AI features.

**Token lifecycle:**
- No expiry. Keys are valid until manually revoked.
- No refresh tokens. No OAuth flow.
- One key per subscription. Rotate by generating a new key and deleting the old one
  in the dashboard.

**EOS location:** `BRAVE_API_KEY` in `~/.config/last30days/.env`. Not stored in
`eos_ai/.env` or `services/.env` — only the last30days skill uses Brave currently.

**Multi-tenant:** Not applicable. One key per account. For multi-org use, create
separate Brave accounts per organization.

---

## Core Operations
### Web Search
```
GET https://api.search.brave.com/res/v1/web/search
Headers:
  Accept: application/json
  Accept-Encoding: gzip
  X-Subscription-Token: {api_key}

Parameters:
  q: str                    # REQUIRED — search query, max 400 chars, 50 words
  country: str = ""         # 2-letter country code (US, GB, DE, etc.)
  search_lang: str = ""     # search language (en, fr, de, etc.)
  ui_lang: str = ""         # UI language for Brave chrome
  count: int = 20           # results per page, 1-20
  offset: int = 0           # pagination offset, max 9
  safesearch: str = "moderate"  # off, moderate, strict
  freshness: str = ""       # pd (24h), pw (7d), pm (31d), py (year), or YYYY-MM-DDtoYYYY-MM-DD
  text_decorations: bool = True  # <b> tags around matched terms in snippets
  spellcheck: bool = True   # auto-correct query spelling
  result_filter: str = ""   # comma-separated: web, news, videos, images, infobox, discussions
  goggles_id: str = ""      # Brave Goggles URL for re-ranking
  units: str = ""           # metric or imperial
  extra_snippets: bool = False  # Pro+ only: additional snippet variants
  summary: bool = False     # Pro+ only: AI summary in response

Response shape (200 OK):
{
  "query": {
    "original": str,            # original query
    "show_strict_warning": bool,
    "is_navigational": bool,
    "is_news_breaking": bool,
    "spellcheck_off": bool,
    "country": str,
    "bad_results": bool,
    "should_fallback": bool,
    "language": str
  },
  "mixed": {
    "type": "mixed",
    "main": [                   # ordered list of result type references
      {"type": "web", "index": 0, "all": false},
      {"type": "news", "index": 0, "all": true}
    ]
  },
  "web": {
    "type": "search",
    "results": [
      {
        "title": str,
        "url": str,
        "is_source_local": bool,
        "is_source_both": bool,
        "description": str,         # snippet text
        "page_age": str,            # ISO-ish date or relative
        "age": str,                 # "3 hours ago", "2 days ago"
        "language": str,
        "family_friendly": bool,
        "type": "search_result",
        "subtype": str,             # "generic", "faq", etc.
        "meta_url": {
          "scheme": str,
          "netloc": str,
          "hostname": str,
          "favicon": str,
          "path": str
        },
        "thumbnail": {
          "src": str,
          "original": str,
          "logo": bool
        },
        "extra_snippets": [str]     # Pro+ only
      }
    ]
  },
  "news": {
    "type": "news",
    "results": [
      {
        "title": str,
        "url": str,
        "description": str,
        "age": str,
        "page_age": str,
        "meta_url": {...},
        "thumbnail": {...},
        "source": {
          "name": str,
          "url": str,
          "img": str
        }
      }
    ]
  },
  "videos": {
    "type": "videos",
    "results": [
      {
        "title": str,
        "url": str,
        "description": str,
        "age": str,
        "page_age": str,
        "thumbnail": {"src": str},
        "meta_url": {...}
      }
    ]
  },
  "faq": {
    "type": "faq",
    "results": [
      {
        "title": str,
        "url": str,
        "question": str,
        "answer": str
      }
    ]
  },
  "discussions": {
    "type": "discussions",
    "results": [
      {
        "title": str,
        "url": str,
        "description": str,
        "age": str,
        "data": {
          "forum_name": str,
          "num_answers": int,
          "score": str,
          "question": str,
          "top_comment": str
        }
      }
    ]
  },
  "infobox": {
    "type": "infobox",
    "results": [
      {
        "title": str,
        "url": str,
        "description": str,
        "long_desc": str,
        "attributes": [{"label": str, "value": str}],
        "images": [{"src": str}],
        "ratings": [{"name": str, "score": float, "best_rating": float}]
      }
    ]
  },
  "locations": {
    "type": "locations",
    "results": [
      {
        "id": str,
        "name": str,
        "address": {...},
        "coordinates": {"lat": float, "lng": float},
        "phone": str,
        "rating": float,
        "reviews": int
      }
    ]
  }
}
```

### News Search
```
GET https://api.search.brave.com/res/v1/news/search
Same auth header. Same q, country, search_lang, count, offset, safesearch, freshness params.
Response: {"query": {...}, "results": [{news_result_object}]}
Note: response is flat "results" array, NOT nested under "news" key.
```

### Images Search
```
GET https://api.search.brave.com/res/v1/images/search
Params: q, country, search_lang, count, offset, safesearch, spellcheck
Response: {"query": {...}, "results": [{"title": str, "url": str, "source": str,
  "thumbnail": {"src": str}, "properties": {"url": str, "height": int, "width": int}}]}
```

### Videos Search
```
GET https://api.search.brave.com/res/v1/videos/search
Same pattern as images. Results include "age" and "thumbnail" fields.
```

### Suggest (Autocomplete)
```
GET https://api.search.brave.com/res/v1/suggest/search
Params: q, country, search_lang, count (max 20)
Response: {"query": {...}, "results": [{"query": str, "is_entity": bool}]}
```

---

## Pagination
**Method:** Offset-based pagination, NOT cursor-based.

**Parameters:**
- `offset`: 0-9 (integer). Each offset step skips `count` results.
- `count`: 1-20 results per page.

**Maximum reachable results:** `count * (offset_max + 1)` = 20 * 10 = 200 results.
This is a hard cap. You cannot paginate beyond 200 results for any query.

**Fetch-all pattern:**
```python
all_results = []
for page_offset in range(10):  # 0-9
    response = requests.get(
        "https://api.search.brave.com/res/v1/web/search",
        headers={"X-Subscription-Token": api_key},
        params={"q": query, "count": 20, "offset": page_offset},
    )
    data = response.json()
    web_results = data.get("web", {}).get("results", [])
    if not web_results:
        break
    all_results.extend(web_results)
    time.sleep(1)  # respect rate limits on free tier
```

**Important:** The `offset` parameter is NOT the number of results to skip. It's
a page number (0-indexed). `offset=1` with `count=20` skips the first 20 results,
NOT the first result.

---

## Rate Limits
| Tier           | Requests/second | Requests/month | Rate limit header |
|----------------|-----------------|----------------|-------------------|
| Free           | 1               | 2,000          | Yes               |
| Base           | 5               | 20,000         | Yes               |
| Pro            | 10              | 50,000+        | Yes               |
| Data for AI    | 20+             | Custom         | Yes               |

**Rate limit headers in response:**
```
X-RateLimit-Limit: 1          # max requests per second for your tier
X-RateLimit-Remaining: 0      # requests remaining in current window
X-RateLimit-Reset: 1          # seconds until window resets
```

**When rate limited:**
- HTTP 429 Too Many Requests
- `Retry-After` header with seconds to wait
- Response body: `{"type": "ErrorResponse", "error": {"code": 429, "message": "rate limit exceeded"}}`

**Recommended backoff:**
```python
import time

def search_with_backoff(url, headers, params, max_retries=3):
    for attempt in range(max_retries):
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 429:
            wait = int(response.headers.get("Retry-After", 2 ** attempt))
            time.sleep(wait)
            continue
        return response
    raise Exception("Rate limit exceeded after retries")
```

**Monthly quota:** Once monthly quota is exhausted, all requests return 429 until
the billing cycle resets. There is no overage — the API hard-stops.

---

## Error Codes
| Code | Meaning                      | Retryable | Recovery                              |
|------|------------------------------|-----------|---------------------------------------|
| 200  | Success                      | N/A       | Parse response                        |
| 400  | Bad request                  | No        | Fix query params (too long, invalid)  |
| 401  | Unauthorized                 | No        | Check API key, check header name      |
| 403  | Forbidden                    | No        | Plan doesn't include this endpoint    |
| 404  | Endpoint not found           | No        | Check URL path                        |
| 422  | Unprocessable entity         | No        | Invalid parameter value               |
| 429  | Rate limited                 | Yes       | Wait for Retry-After, then retry      |
| 500  | Internal server error        | Yes       | Retry with exponential backoff        |
| 502  | Bad gateway                  | Yes       | Retry after 2-5 seconds              |
| 503  | Service unavailable          | Yes       | Retry after 5-10 seconds             |

**Error response shape:**
```json
{
  "type": "ErrorResponse",
  "error": {
    "id": "unique-error-id",
    "status": 429,
    "code": "RATE_LIMITED",
    "detail": "You have exceeded the rate limit for your subscription."
  }
}
```

**Non-obvious errors:**
- 401 with valid key: Header must be `X-Subscription-Token`, NOT `Authorization: Bearer`.
  This is the most common auth mistake because every other API uses Bearer tokens.
- 403 on summarizer endpoint: Free and Base tiers cannot use AI summaries. Upgrade to Pro.
- 422 on freshness: Date format must be `YYYY-MM-DDtoYYYY-MM-DD` (no spaces, no `T`, literal `to`).

---

## SDK Idioms
**No official Python SDK.** Brave Search is a pure REST API. Use `requests` or `urllib`.

**EOS pattern (from brave_search.py):**
```python
import requests
from urllib.parse import urlencode

ENDPOINT = "https://api.search.brave.com/res/v1/web/search"

def search(query: str, api_key: str, count: int = 20, freshness: str = "") -> dict:
    params = {"q": query, "count": count, "safesearch": "strict", "text_decorations": 0}
    if freshness:
        params["freshness"] = freshness
    url = f"{ENDPOINT}?{urlencode(params)}"
    response = requests.get(url, headers={"X-Subscription-Token": api_key}, timeout=15)
    response.raise_for_status()
    return response.json()
```

**EOS uses `urllib`-based HTTP** (custom `http.request()` in the last30days skill lib),
not `requests`. This avoids adding requests as a dependency for the skill.

**Async pattern (if needed):**
```python
import aiohttp

async def search_async(query: str, api_key: str) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={"X-Subscription-Token": api_key},
            params={"q": query, "count": 20},
        ) as resp:
            return await resp.json()
```

**Third-party wrappers exist** (`brave-search`, `brave-search-python` on PyPI) but none
are official. For EOS, raw HTTP is preferred — fewer dependencies, full control.

---

## Anti-Patterns
### Anti-pattern 1: Using Authorization Bearer header
```python
# WRONG — Brave uses a custom header, not Bearer
headers = {"Authorization": f"Bearer {api_key}"}

# CORRECT
headers = {"X-Subscription-Token": api_key}
```

### Anti-pattern 2: Assuming all result type keys exist
```python
# WRONG — news key may not exist if no news results
news_results = data["news"]["results"]

# CORRECT
news_results = data.get("news", {}).get("results", [])
```

### Anti-pattern 3: Not disabling text decorations
```python
# WRONG — snippets contain <b>matched</b> HTML tags
params = {"q": "AI agents"}

# CORRECT — clean text for downstream processing
params = {"q": "AI agents", "text_decorations": 0}
```

### Anti-pattern 4: Treating offset as result skip count
```python
# WRONG — offset=20 means page 20, not skip 20 results
params = {"q": "query", "count": 20, "offset": 20}  # ERROR: offset max is 9

# CORRECT — offset is page number (0-9)
params = {"q": "query", "count": 20, "offset": 1}  # page 2, results 21-40
```

### Anti-pattern 5: Ignoring the freshness date format
```python
# WRONG — ISO format with dashes between components
params = {"freshness": "2026-01-01 to 2026-04-06"}

# CORRECT — no spaces, literal "to" separator
params = {"freshness": "2026-01-01to2026-04-06"}
```

### Anti-pattern 6: Requesting 100 results in one call
```python
# WRONG — max count is 20
params = {"q": "query", "count": 100}

# CORRECT — paginate
for offset in range(5):
    params = {"q": "query", "count": 20, "offset": offset}
```

### Anti-pattern 7: Not handling empty query results
```python
# WRONG — assumes web key always has results
results = data["web"]["results"]

# CORRECT — query.bad_results flag indicates poor matches
if data.get("query", {}).get("bad_results"):
    # Consider rephrasing query
    pass
results = data.get("web", {}).get("results", [])
```

---

## Data Model
```
SearchResponse
  |-- query: QueryInfo
  |     |-- original: str
  |     |-- is_navigational: bool
  |     |-- is_news_breaking: bool
  |     |-- bad_results: bool
  |     +-- country, language: str
  |
  |-- mixed: MixedResponse
  |     +-- main: [TypeReference]  # ordered display hints
  |
  |-- web: WebSearchResponse
  |     +-- results: [SearchResult]
  |           |-- title: str
  |           |-- url: str (canonical)
  |           |-- description: str (snippet)
  |           |-- age: str (relative, e.g. "2 days ago")
  |           |-- page_age: str (absolute-ish date)
  |           |-- language: str
  |           |-- family_friendly: bool
  |           |-- meta_url: MetaUrl (scheme, netloc, hostname, favicon, path)
  |           +-- thumbnail: Thumbnail (src, original, logo)
  |
  |-- news: NewsSearchResponse
  |     +-- results: [NewsResult]
  |           |-- (same as SearchResult)
  |           +-- source: {name, url, img}
  |
  |-- videos: VideoSearchResponse
  |-- faq: FAQResponse
  |-- discussions: DiscussionResponse
  |-- infobox: InfoboxResponse
  +-- locations: LocationResponse
```

**Key relationships:**
- `mixed.main` defines the recommended display order of result types
- Each result type is independent — any can be absent from the response
- `meta_url.hostname` is the clean domain name (no www prefix)
- `thumbnail` may be null/absent on any result
- `age` and `page_age` are both optional; `age` is human-readable, `page_age` is
  closer to machine-parseable but still inconsistent

**Immutable:** All fields are read-only. The API is search-only — no write operations,
no entity creation, no state mutation.

---

## Webhooks
**N/A.** Brave Search API is a stateless query API. There are no webhooks, no event
subscriptions, no push notifications. All interactions are request-response.

---

## Limits
| Limit                        | Value           |
|------------------------------|-----------------|
| Query length                 | 400 characters  |
| Query word count             | 50 words        |
| Results per request (count)  | 20 max          |
| Pagination offset            | 0-9 (10 pages)  |
| Max reachable results        | 200             |
| Request timeout (recommended)| 15 seconds      |
| Response size                | ~50-200 KB      |
| Concurrent requests (Free)   | 1               |
| Concurrent requests (Pro)    | 10              |

**Undocumented but observed:**
- Queries under 2 characters sometimes return empty results
- Very long queries (near 400 chars) may be silently truncated
- The `extra_snippets` field (Pro+) returns up to 5 additional snippet variants

---

## Cost Model
| Plan           | Monthly cost | Queries/month | Cost per query | Overage     |
|----------------|-------------|---------------|----------------|-------------|
| Free           | $0          | 2,000         | $0             | Hard stop   |
| Base           | ~$5         | 20,000        | ~$0.00025      | Hard stop   |
| Pro            | ~$9         | 50,000        | ~$0.00018      | Contact     |
| Data for AI    | Custom      | Custom        | Negotiated     | Negotiated  |

**Key cost facts:**
- No overage charges on Free/Base — API returns 429 when quota exhausted
- Pro and Data for AI tiers have additional query packs available for purchase
- Brave does not charge per result type — a single query returning web + news + videos
  counts as 1 query
- The Summarizer feature (Pro+) does not cost extra per use — included in plan
- Usage dashboard at https://api-dashboard.search.brave.com/ shows real-time query counts

**EOS cost profile:** At 2,000 free queries/month, the last30days skill can run
roughly 66 research sessions (assuming ~30 queries each). For heavier use, Base tier
at $5/month provides 10x headroom.

---

## Version Pinning
**Current API version:** v1 (in the URL path: `/res/v1/`)

**Versioning strategy:** Path-based. The version is part of the URL, not a header.
There is currently only v1. Brave has not announced a v2.

**SDK versioning:** N/A — no official SDK. Pin the response parsing to known field names.

**Deprecation policy:** No formal deprecation policy published. Brave has maintained
backward compatibility within v1 since launch. New fields are added additively
(e.g., `extra_snippets`, `summary`) without removing existing ones.

**Known upcoming changes:** None announced as of April 2026. The Summarizer API and
Data for AI endpoints are the newest additions.

**Recommendation:** Always use `/res/v1/` explicitly in URLs. Never omit the version
segment. If Brave ships v2, v1 will likely continue working for an extended period
given their conservative approach.

---

# Tier 2 — Creator Intelligence

## Design Intent
**Why Brave Search exists:** Brave built its own search index to provide an alternative
to Google/Bing that doesn't track users. The API monetizes this index for developers
who need search results without privacy violations or Google/Bing dependencies.

**Core design philosophy:**
- **Independence over completeness** — Brave's index is smaller than Google's but is
  entirely their own. No proxy to another engine. This means some long-tail queries
  return fewer results, but there's no dependency risk.
- **Simplicity over flexibility** — One auth method, one endpoint per vertical,
  straightforward parameters. No complex query DSL, no search operators beyond basic
  quotes and minus signs.
- **Privacy as architecture** — No user tracking, no personalization based on history,
  no cookies. This means results are consistent across users (good for reproducibility)
  but not personalized (no "more like this" learning).

**Conscious tradeoffs:**
- Smaller index = fewer results for niche queries, but zero Big Tech dependency
- No query operators = simpler API, but less power-user control than Google
- No personalization = reproducible results, but no relevance learning
- Flat pricing = predictable costs, but no granular per-feature billing

**What Brave Search explicitly is NOT:**
- Not a Google/Bing proxy (like SerpAPI or Serper)
- Not a web scraper (it returns search results, not page content)
- Not a knowledge graph (infobox data is surface-level compared to Google KG)

---

## Problem-Solution Map
**Problems Brave Search actually solves:**
1. **Vendor-independent web search** — No Google/Bing API key dependency
2. **AI training data** — Data for AI tier explicitly licenses results for LLM use
3. **Privacy-compliant search** — No user data leaks to Big Tech
4. **Cost-effective research** — 2,000 free queries vs Google's $5/1000 queries
5. **Fresh content discovery** — Freshness filters are first-class, not afterthought

**Hidden/underdocumented capabilities:**
- **Goggles** — Community-created re-ranking filters. Pass a Goggles URL via
  `goggles_id` to completely reorder results (e.g., filter out SEO spam,
  prioritize indie blogs, only show .edu domains). This is Brave's most
  underused power feature.
- **`is_navigational` flag** — The `query.is_navigational` response field tells you
  if the user is searching for a specific site (e.g., "facebook login"). Useful for
  routing: navigational queries need 1 result, research queries need 20.
- **`is_news_breaking` flag** — Real-time signal that the query matches breaking news.
  Use this to automatically switch from web to news-priority display.
- **Discussions type** — Returns forum/community results with `num_answers`, `score`,
  and `top_comment` — structured discussion data without scraping Reddit/HN.
- **`mixed.main` ordering** — Brave's suggested display order for result types. Most
  users ignore this, but it encodes Brave's relevance judgment about which result
  type matters most for the query.

---

## Operational Behavior
**Eventual consistency:** Not applicable — Brave Search is a stateless query engine
with no write operations. Results may vary as the index updates, but there's no
consistency model to worry about.

**Performance characteristics:**
- Typical response time: 200-800ms from US servers
- VPS location matters — Brave's servers are US/EU. Asia-Pacific queries add 100-300ms
- News results load faster than web results (smaller index)
- Queries with `freshness` filters are slightly slower (~50-100ms overhead)

**Behavioral quirks:**
- **Empty queries return 400**, not empty results
- **Quoted phrases work** ("exact match") but advanced operators (site:, filetype:)
  are not supported in the API (only in the browser search)
- **Minus operator works** — `-reddit` excludes Reddit results at the API level
- **Language detection is aggressive** — a query like "pytorch einsum" may return
  results in the detected language of the server IP, not English. Always pass
  `search_lang=en` explicitly when you want English results.
- **Duplicate URLs across types** — The same URL can appear in both `web.results`
  and `news.results`. Deduplicate by URL if merging.
- **`age` field inconsistency** — Some results have `age` (relative), some have
  `page_age` (absolute-ish), some have both, some have neither. Never rely on
  a single date field.

---

## Ecosystem Position
**Where Brave Search sits in a data architecture:**
- **Research layer** — Sits alongside Google Custom Search, Serper, SerpAPI, and Bing
  as a web search provider. Used to discover URLs, not to fetch content.
- **Not a content fetcher** — Returns titles, URLs, and snippets. For full page
  content, pair with a scraper (Apify, Firecrawl, or simple requests+BeautifulSoup).

**Natural complements:**
- **Apify/Firecrawl** — Brave finds URLs, scraper fetches full content
- **LLM summarizer** — Feed Brave snippets to an LLM for synthesis (or use Pro tier's
  built-in summarizer)
- **EOS last30days** — Brave is one of three web search backends alongside Parallel AI
  and OpenRouter/Perplexity Sonar

**Integration anti-patterns:**
- **Brave + Google Custom Search redundancy** — Using both is wasteful. Pick one.
  Brave is cheaper and privacy-focused. Google is more comprehensive for niche queries.
- **Brave as a scraper** — Don't try to extract full article content from Brave snippets.
  They're 200-char summaries, not full text.
- **Brave for real-time monitoring** — Brave's index updates hourly-to-daily, not in
  real-time. For live monitoring, use Twitter/X API or RSS feeds.

**Data handoff patterns:**
```
Brave Search -> URL list -> Apify scraper -> full text -> LLM summarization
Brave Search -> snippets -> LLM synthesis (quick, loses detail)
Brave Search -> news results -> Discord webhook notification
```

---

## Trajectory
**Where Brave Search is heading (as of 2026):**
- **AI-first search** — The Summarizer API and "Data for AI" tier signal Brave's bet
  that AI agents will be major API consumers. Expect more AI-focused features.
- **Goggles expansion** — Community re-ranking is being expanded. Expect a marketplace
  or featured Goggles in the API response.
- **CodeSearch** — Brave has signaled interest in code-specific search, competing with
  GitHub search and Sourcegraph.

**What's getting increased investment:**
- AI summarization capabilities
- Data licensing for LLM training
- Index freshness (closing the gap with Google for recent content)

**What's stable and safe to build on:**
- `/res/v1/web/search` — core endpoint, not changing
- `X-Subscription-Token` auth — no migration planned
- Response shape — additive changes only (new fields, not removed fields)

**Deprecation signals:** None currently. Brave has not deprecated any API feature
since launch. The v1 API appears stable for the foreseeable future.

---

## Conceptual Model
**Mental model:** Think of Brave Search API as a **multi-vertical query router**. You
send one query, and Brave routes it across web, news, video, FAQ, discussion, location,
and infobox indexes. The `mixed.main` field tells you which verticals matter most for
that specific query.

**Primitives:**
- **Query** — the input search string
- **Vertical** — the type of result (web, news, video, etc.)
- **Freshness** — temporal filter on results
- **Goggles** — re-ranking overlay that changes result order
- **Result** — a single item with title, url, description, age

**Recipe 1: AI-Powered Research Pipeline**
```python
# 1. Search for topic across web + news
results = search(query="AI agent frameworks 2026", freshness="pm", count=20)
# 2. Check if breaking news
if results["query"]["is_news_breaking"]:
    news = results.get("news", {}).get("results", [])
    # Prioritize news results
# 3. Merge and deduplicate by URL
all_results = merge_and_dedup(results)
# 4. Feed snippets to LLM for synthesis
summary = llm_summarize([r["description"] for r in all_results])
```

**Recipe 2: Competitive Intelligence Monitor**
```python
# 1. Search competitor names weekly
for competitor in ["Competitor A", "Competitor B"]:
    results = search(query=f'"{competitor}" announcement', freshness="pw")
    # 2. Filter for actual news (not just mentions)
    news = [r for r in results.get("news", {}).get("results", [])
            if competitor.lower() in r["title"].lower()]
    # 3. Post to Discord if new mentions found
    if news:
        post_to_webhook(format_competitive_alert(news))
```

**Recipe 3: Content Gap Finder**
```python
# 1. Search for your topic
results = search(query="solopreneur AI tools guide", count=20)
# 2. Analyze existing content
existing_angles = [r["title"] for r in results.get("web", {}).get("results", [])]
# 3. Identify gaps (angles not covered)
gaps = llm_find_gaps(existing_angles, your_planned_content)
```

**Recipe 4: Fresh Source Discovery**
```python
# 1. Find recent discussions
results = search(query="best CRM for solopreneurs", freshness="pm", count=20)
# 2. Extract discussion data
discussions = results.get("discussions", {}).get("results", [])
# 3. Rank by engagement
discussions.sort(key=lambda d: int(d.get("data", {}).get("num_answers", 0)), reverse=True)
# 4. Use top discussions as content research
```

---

## Industry Expert Usage
**How AI agent builders use Brave Search (2026):**
- **Tool-use agents** — Brave is the go-to search tool for LLM agents that need web
  search without Google/Bing API overhead. Its simple auth (single header) and
  predictable response shape make it ideal for function-calling agents.
- **RAG pipelines** — Brave Search as the retrieval step: query -> Brave -> top 5 URLs
  -> scrape -> chunk -> embed -> answer. Cheaper than maintaining your own crawler.
- **Multi-source research** — Combine Brave web results with Brave news results with
  discussions results for 360-degree topic coverage in a single API call.

**Frontier patterns:**
- **Goggles for domain-specific search** — Create a custom Goggle that only returns
  results from trusted sources in your domain (e.g., only .gov and .edu for policy
  research, only HN/Reddit/GitHub for dev tools research). This effectively creates
  a curated search engine via the API.
- **Freshness-aware caching** — Cache results keyed by `(query, freshness)`. A
  `freshness=pm` query cached for 24h is still valid. A `freshness=pd` query
  cached for 1h is fine. This cuts API usage 50-80% for recurring research.
- **Breaking news detection** — Poll Brave every 15 minutes with key queries. When
  `is_news_breaking` flips to true, trigger an alert pipeline. Cheaper than
  dedicated news APIs for low-frequency monitoring.
- **Discussion mining** — The `discussions` result type returns structured forum data
  (question, top_comment, score) without scraping. Use this for sentiment analysis
  and community opinion extraction without Reddit/HN API dependencies.

**What separates expert usage from beginner:**
1. Always pass `text_decorations=0` and `spellcheck=0` for programmatic use
2. Always check `query.bad_results` before processing results
3. Use `mixed.main` to determine which result vertical to prioritize
4. Implement freshness-aware caching to stay within free tier
5. Use Goggles for domain-specific result quality — this is Brave's killer feature
   that most developers never discover

---

## EOS Usage Patterns

**Current integration:** Single consumer — `.agents/skills/last30days/scripts/lib/brave_search.py`.
Brave is the second-priority web search backend (after Parallel AI, before OpenRouter).

**How results flow:**
```
last30days.py -> brave_search.search_web() -> HTTP GET -> _normalize_results()
  -> Merged list of {id, title, url, source_domain, snippet, date, date_confidence, relevance}
```

**EOS-specific decisions:**
- Reddit and X domains excluded (handled by dedicated backends)
- `safesearch=strict` always (business context)
- `text_decorations=0` always (clean text for LLM processing)
- `spellcheck=0` (preserve exact technical terms)
- Freshness mapped from date range: <=1d=pd, <=7d=pw, <=31d=pm, >31d=explicit range
- Flat 0.6 relevance score (no Brave-native relevance available)

## Gotchas

### Auth header name is unique
Brave uses `X-Subscription-Token`, not `Authorization: Bearer`. Every other API in
EOS uses Bearer tokens. This is the most likely mistake when adding Brave support
to a new module.

### Response shape varies by query type
Navigational queries ("facebook login") return minimal web results and may include
an infobox. Research queries ("best CRM 2026") return full web + news + discussions.
Never assume a fixed set of result types in the response.

### Free tier hard-stops at 2,000/month
No overage, no degraded service — just 429 errors for the rest of the billing cycle.
If EOS depends on Brave for critical research, monitor usage via the dashboard and
upgrade before hitting the cap.

### Date parsing is fragile
Brave's `age` field uses inconsistent relative formats: "3 hours ago", "2 days ago",
"January 24, 2026", sometimes just "2026". The EOS `_parse_brave_date()` handles
common patterns but drops uncommon ones to None. Always treat date as optional.

### VPS IP affects country detection
Running from a US VPS returns US-centric results. Running from EU returns EU results.
Always pass `country=US` (or your target market) explicitly to get consistent results
regardless of server location.
