---
name: apify
description: "Use when any agent needs web scraping, Instagram comment extraction, competitor monitoring, or lead signal harvesting via cloud actors."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://docs.apify.com/api/v2"
last_researched: "2026-04-04"
instantiated_from: templates/tools/_template/
api_version: "Apify API v2"
sdk_version: "apify-client (Python) / REST API direct (EOS)"
speed_category: "slow"
trigger: both
effort: medium
context: fork
---

# Tool: Apify

## What This Tool Does

Apify is a cloud web scraping and automation platform. It runs pre-built or custom "actors" (serverless functions) that scrape websites, extract structured data, and return results via datasets. EOS uses it as the primary Instagram scraping engine for lead signal extraction and competitor monitoring.

Core capabilities:
- **Actor execution** — run pre-built scrapers via REST API
- **Dataset retrieval** — paginated access to scrape results
- **Proxy infrastructure** — RESIDENTIAL and DATACENTER proxy groups
- **Scheduling** — cron-like actor scheduling (not used by EOS — EOS uses own cron)
- **Webhooks** — notify on run completion (not used by EOS — EOS polls)

## EOS Integration

### Primary: `services/apify_scraper.py` (os-scraper container)

**What it does:**
1. Rotates through hashtag groups (A/B testing) and competitor accounts
2. Runs Apify actors to find posts and scrape comments
3. Filters comments through bot/spam detection pipeline
4. Classifies priority signals (buyer language: "stuck", "struggling", "wasted potential")
5. Saves qualified signals as markdown files to `01_Inbox/raw_signals/`
6. Auto-promotes/blacklists hashtags based on qualified lead rate
7. Weekly AI-powered hashtag suggestions via Claude Haiku

**Architecture:**
```
os-scraper container (cron)
  └── apify_scraper.py
        ├── scrape_hashtag()
        │     └── run_actor("reGe1ST3OBgYZSsZJ", hashtags=[...])  # Instagram Hashtag Scraper
        │           → poll_run() → get_run_results()
        │             → is_icp_relevant_post() [Whisper + Claude + keyword]
        │               → scrape_comments_for_post()
        │                   └── run_actor("SbK00X0JYCPblD2wp", directUrls=[...])  # Comment Scraper
        │                         → is_human_comment() → is_priority_comment()
        │                           → save_signal()
        ├── scrape_competitor()
        │     └── run_actor("shu8hvrXbJbY3Eb9W", usernames=[...])  # Instagram Profile Scraper
        └── auto_suggest_hashtags() [Sundays only]
              └── Claude Haiku → suggest 5 new hashtags
```

**Three Apify actors in use:**
| Actor ID | Purpose | Input |
|----------|---------|-------|
| `reGe1ST3OBgYZSsZJ` | Instagram Hashtag Scraper | `{hashtags: [...], resultsLimit: N}` |
| `SbK00X0JYCPblD2wp` | Instagram Comment Scraper | `{directUrls: [...], resultsLimit: N}` |
| `shu8hvrXbJbY3Eb9W` | Instagram Profile Scraper | `{usernames: [...], resultsLimit: N, resultsType: "posts"}` |

**Rate limiting:**
```python
apify_limiter = RateLimiter(calls_per_minute=10)  # Conservative (free tier ~100/min)
API_DELAY = 2       # seconds between API calls
POLL_INTERVAL = 5   # seconds between status polls
MAX_RETRIES = 5     # with exponential backoff (base=2)
```

### Secondary: Apify Proxy for DM Monitor
```python
# dm_monitor.py — proxy for Instagram login from VPS
proxy={
    'server': 'http://proxy.apify.com:8000',
    'username': f'groups-RESIDENTIAL,session-{sticky_id},country-US',
    'password': os.getenv('APIFY_PROXY_PASSWORD'),
}
```
Enabled when `INSTAGRAM_USE_PROXY=true`. Default is direct (no proxy).

### Agents that use it
- Scraper Service (directly — `apify_scraper.py`)
- DM Monitor (indirectly — proxy infrastructure)
- Cost Tracker (logs scraper costs per run)

## Authentication

```python
# Single API token — stored in services/.env
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")

# All API calls include token as query parameter
url = f"https://api.apify.com/v2/acts/{actor_id}/runs?token={APIFY_API_TOKEN}"

# Proxy auth uses separate password
APIFY_PROXY_PASSWORD = os.getenv("APIFY_PROXY_PASSWORD")
```

Token generated at console.apify.com > Settings > Integrations.
One token per Apify account. Scoped to all actors and datasets.

## Quick Reference

### Start actor run
```python
import requests

url = f"https://api.apify.com/v2/acts/{actor_id}/runs?token={token}"
response = requests.post(url, json=input_data, timeout=30)
run_id = response.json()["data"]["id"]
```

### Poll run status
```python
url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={token}"
response = requests.get(url, timeout=30)
status = response.json()["data"]["status"]
# Statuses: READY, RUNNING, SUCCEEDED, FAILED, ABORTED, TIMED-OUT
```

### Get results
```python
url = f"https://api.apify.com/v2/actor-runs/{run_id}/dataset/items?token={token}"
response = requests.get(url, timeout=30)
items = response.json()  # list of dicts
```

### Comment filtering pipeline (EOS-specific)
```python
# Bot detection: username patterns (._., community, official, coach, etc.)
# Spam detection: short (<20 chars), all caps, spam phrases, URLs, emoji flood
# Deduplication: seen_usernames set, seen_comment_texts set
# Priority classification: buyer-signal keywords (stuck, struggling, wasted, etc.)
human, reason = is_human_comment(username, text, seen_comment_texts)
priority = is_priority_comment(text)
```

## Gotchas

### RESIDENTIAL proxy returns 403 when credits depleted (ACTIVE)
Apify RESIDENTIAL proxy group has separate credit pool from compute units.
When exhausted, all proxy requests return 403.
**Fix:** Set `INSTAGRAM_USE_PROXY=false` in services/.env until credits refill.

### Actor run returns TIMED-OUT for large scrapes (ACTIVE)
Default Apify actor timeout is 60 seconds for free tier.
Large hashtag scrapes with high `resultsLimit` can exceed this.
**Fix:** Keep `resultsLimit` under 100, or use `maxConcurrency` input parameter.

### Comment scraper returns different field names (ACTIVE)
Some actors use `ownerUsername`, others use `username`.
Some use `text`, others use `commentText`.
**EOS handles this:**
```python
username = comment.get("ownerUsername") or comment.get("username") or "unknown"
text = comment.get("text") or comment.get("commentText") or ""
```

### Rate limit 429 during burst scraping (RESOLVED)
Rapid sequential API calls triggered 429 responses.
**Fix:** `RateLimiter(calls_per_minute=10)` with exponential backoff on 429/5xx.

### Scraped posts cache grows unbounded (RESOLVED)
`scraped_posts.json` tracked all scraped URLs without cleanup.
**Fix:** Capped to last 100 URLs per source: `scraped_urls[-100:]`.

### Actor version changes break field names (INTERMITTENT)
Apify actors update independently. A version bump can change response schema.
**Detection:** Empty results despite successful run status.
**Fix:** Check actor version notes, update field name fallbacks.

See references/best_practices.md for full API reference, pricing, and anti-patterns.
