---
name: x_twitter_api
description: "Use when searching X/Twitter for posts, looking up users, monitoring trends, building social intelligence features, or debugging X data ingestion in EOS."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://developer.x.com/en/docs/x-api"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "v2 (October 2022 — current)"
sdk_version: "tweepy 4.14+ / Bird v0.8.0 (vendored) / xAI Responses API"
speed_category: medium
trigger: both
effort: medium
context: fork
---

# Tool: X (Twitter) API

## What This Tool Does

The X API v2 provides programmatic access to tweets, users, spaces, lists, and
direct messages on the X (formerly Twitter) platform. Core capabilities:

- **Tweet search** — recent (7-day) and full-archive search with boolean operators
- **User lookup** — by ID or username, includes profile metadata and public metrics
- **Tweet lookup** — individual or batch tweet retrieval with expansions
- **Timelines** — user tweet timelines and reverse-chronological home timelines
- **Filtered stream** — real-time tweet delivery matching predefined rules
- **Tweet counts** — volume counts matching a query without returning tweet content
- **Spaces** — lookup and search for Twitter Spaces
- **Lists** — create, manage, and query list membership
- **Post tweets** — create, delete, like, retweet, quote, reply

Since Elon Musk's acquisition, the API has undergone major pricing restructuring.
The free tier is extremely limited (post-only, 1,500 tweets/month write).
Read access (search, lookup, timelines) requires the Basic tier ($200/month) minimum.
This economic reality is why EOS does NOT use the official X API directly.

## EOS Integration

EOS accesses X/Twitter data through two alternative paths, neither of which
uses the official X API v2 directly:

### Path 1: Bird GraphQL Search (primary, free)
`/.agents/skills/last30days/scripts/lib/bird_x.py`

Uses a vendored subset of @steipete/bird v0.8.0 (MIT License) that searches X
via Twitter's internal GraphQL API using browser session cookies. No API key needed.

- `search_x(topic, from_date, to_date, depth)` — keyword search with date filter
- `search_handles(handles, topic, from_date, count_per)` — targeted per-handle search
- `parse_bird_response(response)` — normalizes GraphQL response to standard item format
- Authentication: browser cookies (Safari, Chrome, Firefox) or env `AUTH_TOKEN`
- Depth configs: quick (12 results), default (30), deep (60)
- Runs via Node.js subprocess calling vendored `bird-search.mjs`

### Path 2: xAI API with x_search tool (secondary, paid)
`/.agents/skills/last30days/scripts/lib/xai_x.py`

Uses the xAI Responses API (`https://api.x.ai/v1/responses`) with the `x_search`
agent tool. xAI models (Grok) have native access to real-time X data.

- `search_x(api_key, model, topic, from_date, to_date, depth)` — LLM-mediated search
- `parse_x_response(response)` — extracts structured items from LLM output
- Authentication: `XAI_API_KEY` bearer token
- Returns structured JSON with text, url, author_handle, engagement metrics, relevance score
- Depth configs: quick (8-12 items), default (20-30), deep (40-60)

### Source selection logic
`/.agents/skills/last30days/scripts/lib/env.py` — `get_x_source(config)`

Priority: Bird (free) -> xAI (paid). Returns `'bird'`, `'xai'`, or `None`.

### Downstream consumers
- `/last30days` skill — research discovery, trend analysis
- `icp_signal_detection` skill — X/Twitter reply outreach for ICP pain signals
- `analyze_icp_signal` skill — processes X posts as raw signals
- `email_gps.py` — filters x.com/twitter.com URLs from email link extraction

### Normalized output format (both paths)
```python
{
    "id": "X1",                          # Sequential ID
    "text": "Post content...",           # Truncated to 500 chars
    "url": "https://x.com/user/status/123",
    "author_handle": "username",         # Without @
    "date": "2026-04-01",               # YYYY-MM-DD or None
    "engagement": {
        "likes": 100,
        "reposts": 25,
        "replies": 15,
        "quotes": 5
    },
    "why_relevant": "Brief explanation", # xAI only, empty for Bird
    "relevance": 0.85                    # 0.0-1.0, default 0.7 for Bird
}
```

## Authentication

### Official X API v2 (not used by EOS, documented for reference)
Three auth methods exist:
1. **OAuth 2.0 App-Only (Bearer Token)** — read-only access. Single bearer token
   from the Developer Portal. Used for search, lookup, streams.
2. **OAuth 2.0 Authorization Code Flow with PKCE** — user-context access.
   Required for posting, liking, DMs. Uses access + refresh tokens.
3. **OAuth 1.0a** — legacy user-context auth. Still supported, uses
   consumer key/secret + access token/secret (4 credentials).

### Bird GraphQL (EOS Path 1)
- Uses browser session cookies automatically extracted from Safari/Chrome/Firefox
- Alternative: set `AUTH_TOKEN` env var with the `auth_token` cookie value from x.com
- No API key, no developer account needed
- Cookie extraction requires Node.js 22+
- Check auth: `bird_x.is_bird_authenticated()` returns auth source or None

### xAI API (EOS Path 2)
- Bearer token auth: `Authorization: Bearer {XAI_API_KEY}`
- Key stored in `.agents/skills/last30days/.env` or system env
- xAI API key from https://console.x.ai
- No OAuth flow, no refresh tokens

### Env vars used by EOS
```
XAI_API_KEY=           # xAI API key (for Path 2)
AUTH_TOKEN=            # X browser auth_token cookie (for Path 1, optional)
```

## Quick Reference

### Search X via Bird (free, primary)
```python
from lib.bird_x import search_x, parse_bird_response

response = search_x(
    topic="AI agents startup",
    from_date="2026-03-01",
    to_date="2026-04-01",
    depth="default",  # quick|default|deep
)
items = parse_bird_response(response)
for item in items:
    print(f"@{item['author_handle']}: {item['text'][:80]}")
```

### Search X via xAI (paid, secondary)
```python
from lib.xai_x import search_x, parse_x_response

response = search_x(
    api_key=os.getenv("XAI_API_KEY"),
    model="grok-3-mini",
    topic="solopreneur SaaS",
    from_date="2026-03-01",
    to_date="2026-04-01",
    depth="default",
)
items = parse_x_response(response)
```

### Check X source availability
```python
from lib.env import get_x_source, get_config
config = get_config()
source = get_x_source(config)  # 'bird', 'xai', or None
```

### Search specific handles
```python
from lib.bird_x import search_handles

items = search_handles(
    handles=["pmarca", "elonmusk", "sama"],
    topic="AI regulation",
    from_date="2026-03-01",
    count_per=5,
)
```

### Official X API v2 (reference, not used by EOS)
```python
import tweepy

client = tweepy.Client(bearer_token="BEARER_TOKEN")

# Search recent tweets (last 7 days)
response = client.search_recent_tweets(
    query="AI agents -is:retweet lang:en",
    max_results=100,            # 10-100
    tweet_fields=["created_at", "public_metrics", "author_id"],
    expansions=["author_id"],
    user_fields=["username", "public_metrics"],
)

# User lookup
user = client.get_user(username="elonmusk", user_fields=["public_metrics", "description"])
```

## Conceptual Model

```
X/Twitter Data Access Landscape (2026)
  |
  +-- Official X API v2 ($200+/month for read)
  |     |-- OAuth 2.0 Bearer Token (app-only, read)
  |     |-- OAuth 2.0 PKCE (user-context, read+write)
  |     |-- Endpoints: search, lookup, timelines, stream, counts
  |     +-- Tiers: Free (write-only) | Basic ($200) | Pro ($5,000) | Enterprise
  |
  +-- Alternative: Bird GraphQL (free, EOS primary)
  |     |-- Uses Twitter's internal GraphQL endpoints
  |     |-- Auth via browser cookies (no API key)
  |     |-- Keyword search with date filters
  |     |-- Returns: text, URL, author, engagement, dates
  |     +-- Risk: depends on internal API stability
  |
  +-- Alternative: xAI API with x_search (paid, EOS secondary)
  |     |-- Grok models have native X data access
  |     |-- LLM-mediated search (semantic, not just keyword)
  |     |-- Returns structured JSON via prompt engineering
  |     +-- Cost: xAI API pricing (per-token)
  |
  +-- Alternative: Apify Twitter Scrapers
        |-- apify/twitter-scraper, apify/tweet-scraper-v2
        |-- Pay-per-compute-unit via Apify platform
        +-- EOS has Apify integration but not currently wired for X
```

See references/best_practices.md for official API rate limits, error codes, and anti-patterns.

## Gotchas

### Bird authentication expires with browser sessions
Bird relies on browser cookies. If the browser session expires or cookies are
cleared, `is_bird_authenticated()` returns None and X search silently produces
no results. EOS falls back to xAI, but if `XAI_API_KEY` is also missing, X
data is completely unavailable with no error — just empty results.

### Bird search is literal keyword AND matching
X's internal search requires ALL words to appear in the tweet. A verbose query
like "what are the best AI agent frameworks" returns zero results. Bird's
`_extract_core_subject()` aggressively strips noise words down to 2-3 core
terms. If you bypass this and pass raw queries, expect empty results.

### Bird retries with fewer keywords on zero results
If the initial search returns 0 items and the query has 3+ words, Bird
automatically retries with only the first 2 words. This is intentional
behavior, not a bug. The retry query may be broader than intended.

### xAI response parsing is fragile
The xAI path asks Grok to return JSON, then regex-extracts it from the LLM
output. If Grok wraps the JSON in markdown code fences or adds commentary,
the regex `r'\{[\s\S]*"items"[\s\S]*\}'` may fail or capture garbage.
The parse function handles this gracefully (returns empty list), but data loss
is possible.

### X API v2 free tier is write-only
The free tier ($0) only allows posting tweets (1,500/month) and deleting tweets.
No search, no lookup, no timelines, no streams. Any read operation requires
Basic ($200/month) minimum. This is why EOS uses Bird/xAI instead.

### Rate limits are per-15-minute window, not per-second
X API v2 uses 15-minute sliding windows. A burst of requests that stays under
the window limit is fine. But hitting the limit means waiting up to 15 minutes.
Headers: `x-rate-limit-limit`, `x-rate-limit-remaining`, `x-rate-limit-reset`.

### Tweet search only returns 7 days of data on Basic tier
`search/recent` returns tweets from the last 7 days only. Full-archive search
(`search/all`) requires Pro tier ($5,000/month) or Enterprise. There is no
way to search older tweets on Basic.

### Bird subprocess timeout kills silently
Bird runs as a Node.js subprocess with process group management. On timeout,
it kills the entire process group via `SIGTERM`. If the process group kill
fails, it falls back to `proc.kill()`. Zombie processes are possible if
neither cleanup path succeeds.

### Engagement metrics may be null
Both Bird and xAI paths can return null for any engagement metric (likes,
reposts, replies, quotes). Code consuming these items must handle None values
for every engagement field. Bird defaults relevance to 0.7; xAI provides
LLM-estimated relevance (less reliable for exact numbers).
