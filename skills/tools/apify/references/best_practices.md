# Apify — Best Practices (Creator-Level Reference)

Source: Apify API v2 documentation + EOS production experience
Version: Apify API v2
Last Researched: 2026-04-04

---

## 1. Authentication

### API token
```python
# Single token for all API operations
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")

# Token passed as query parameter (not header)
url = f"https://api.apify.com/v2/acts/{actor_id}/runs?token={token}"

# Or as Bearer token in header (alternative)
headers = {"Authorization": f"Bearer {token}"}
```

Token generated at: console.apify.com > Settings > Integrations.
One token per Apify account. Full access to all actors, datasets, and storage.

### Proxy authentication
```python
# Apify proxy uses username-password auth
proxy = {
    'server': 'http://proxy.apify.com:8000',
    'username': f'groups-RESIDENTIAL,session-{session_id},country-US',
    'password': os.getenv('APIFY_PROXY_PASSWORD'),
}
```

Proxy password is separate from API token. Found in console.apify.com > Proxy.

### Python SDK auth
```python
from apify_client import ApifyClient

client = ApifyClient(token=os.getenv("APIFY_API_TOKEN"))
# Or set APIFY_TOKEN env var and omit token parameter
```

---

## 2. Core Operations with Exact Signatures

### Start actor run (REST API — EOS pattern)
```
POST https://api.apify.com/v2/acts/{actorId}/runs?token={token}

Request body:
{
    "directUrls": ["https://..."],     // actor-specific input
    "resultsLimit": 100,                // max items to return
    "hashtags": ["discipline"],         // for hashtag scraper
    "usernames": ["hormozi"],           // for profile scraper
    "resultsType": "posts",             // for profile scraper
    "maxConcurrency": 5,                // parallel browser instances
}

Response:
{
    "data": {
        "id": "run_abc123",              // run ID for polling
        "actId": "actor_id",
        "status": "RUNNING",
        "startedAt": "2026-04-04T...",
        "defaultDatasetId": "dataset_id",
        "defaultKeyValueStoreId": "kvs_id"
    }
}
```

### Poll run status
```
GET https://api.apify.com/v2/actor-runs/{runId}?token={token}

Response:
{
    "data": {
        "id": "run_abc123",
        "status": "SUCCEEDED",           // READY | RUNNING | SUCCEEDED | FAILED | ABORTED | TIMED-OUT
        "finishedAt": "2026-04-04T...",
        "stats": {
            "inputBodyLen": 200,
            "runTimeSecs": 45.2,
            "computeUnits": 0.05,
            "datasetItems": 150
        }
    }
}
```

### Get dataset items
```
GET https://api.apify.com/v2/actor-runs/{runId}/dataset/items?token={token}

Query parameters:
  format=json        (default) | csv | xml | xlsx | html | rss
  limit=100          max items per page
  offset=0           pagination offset
  fields=text,username  only include specific fields
  unwind=comments    flatten nested arrays
  clean=true         remove hidden fields

Response: JSON array of items (actor-specific schema)
[
    {
        "ownerUsername": "john_doe",
        "text": "I feel so stuck...",
        "timestamp": "2026-04-03T...",
        "likesCount": 5,
        ...
    }
]
```

### Alternative: Python SDK
```python
from apify_client import ApifyClient

client = ApifyClient(os.getenv("APIFY_API_TOKEN"))

# Start run
run = client.actor("apify/instagram-comment-scraper").call(
    run_input={"postUrls": [...], "resultsLimit": 100},
    timeout_secs=300,
    memory_mbytes=256,
)

# Get results (streaming iterator)
for item in client.dataset(run["defaultDatasetId"]).iterate_items():
    print(item)

# Or get all at once
items = client.dataset(run["defaultDatasetId"]).list_items().items
```

### Actor management
```
GET  /v2/acts?token={token}                         # list actors
GET  /v2/acts/{actorId}?token={token}                # actor details
GET  /v2/acts/{actorId}/versions?token={token}       # version history
POST /v2/acts/{actorId}/runs?token={token}           # start run
GET  /v2/actor-runs/{runId}/log?token={token}        # run logs
DELETE /v2/actor-runs/{runId}?token={token}           # abort run
```

---

## 3. Pagination Patterns

### Dataset pagination
```python
# REST API pagination
offset = 0
limit = 100
all_items = []

while True:
    url = (
        f"https://api.apify.com/v2/actor-runs/{run_id}/dataset/items"
        f"?token={token}&limit={limit}&offset={offset}"
    )
    response = requests.get(url, timeout=30)
    items = response.json()
    if not items:
        break
    all_items.extend(items)
    offset += limit
```

### Python SDK streaming (preferred for large datasets)
```python
# iterate_items() handles pagination internally
for item in client.dataset(dataset_id).iterate_items():
    process(item)

# With filters
for item in client.dataset(dataset_id).iterate_items(
    fields=["username", "text"],
    limit=500,
):
    process(item)
```

### EOS pattern: no pagination needed
EOS uses `resultsLimit` in actor input (max 100-200 items per run),
so dataset results fit in a single response. Pagination not currently needed.

---

## 4. Rate Limits

### API rate limits
| Tier | Limit | Notes |
|------|-------|-------|
| Free | ~100 requests/minute | Soft limit, varies |
| Personal | 100 requests/minute | Per API token |
| Business | 300+ requests/minute | Negotiable |

### EOS rate limiting
```python
class RateLimiter:
    def __init__(self, calls_per_minute):
        self.min_interval = 60.0 / calls_per_minute
        self.last_call_time = 0

    def wait(self):
        elapsed = time.time() - self.last_call_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_call_time = time.time()

# Conservative: 10 calls/min (6-second interval)
apify_limiter = RateLimiter(calls_per_minute=10)
```

### Retry strategy
```python
MAX_RETRIES = 5
BASE_BACKOFF = 2  # seconds

for attempt in range(MAX_RETRIES):
    response = requests.post(url, json=input_data, timeout=30)
    if response.status_code == 429 or response.status_code >= 500:
        wait = BASE_BACKOFF ** attempt  # 2, 4, 8, 16, 32 seconds
        time.sleep(wait)
        continue
    response.raise_for_status()
    return response.json()["data"]["id"]
```

---

## 5. Error Codes and Recovery

### HTTP status codes
| Code | Meaning | Recovery |
|------|---------|----------|
| 200 | Success | — |
| 201 | Created (run started) | — |
| 400 | Invalid input | Check actor input schema |
| 401 | Invalid token | Regenerate API token |
| 403 | Forbidden (proxy credits depleted) | Disable proxy or buy credits |
| 404 | Actor/run not found | Check actor ID spelling |
| 408 | Timeout | Increase timeout or reduce scope |
| 429 | Rate limited | Exponential backoff |
| 500 | Server error | Retry with backoff |
| 502 | Bad gateway | Retry after delay |

### Run failure statuses
| Status | Meaning | Recovery |
|--------|---------|----------|
| `SUCCEEDED` | Run completed | Get dataset items |
| `FAILED` | Actor error | Check run logs |
| `ABORTED` | User or system abort | Check if timeout |
| `TIMED-OUT` | Exceeded max runtime | Reduce `resultsLimit` or increase timeout |

### EOS error handling
```python
def run_actor(actor_id, input_data, retries=MAX_RETRIES):
    last_exc = None
    for attempt in range(retries):
        apify_limiter.wait()
        try:
            response = requests.post(url, json=input_data, timeout=30)
            if response.status_code == 429 or response.status_code >= 500:
                wait = BASE_BACKOFF ** attempt
                time.sleep(wait)
                continue
            response.raise_for_status()
            return response.json()["data"]["id"]
        except requests.RequestException as e:
            last_exc = e
            if attempt == retries - 1:
                raise
            time.sleep(BASE_BACKOFF ** attempt)
    raise RuntimeError(f"run_actor failed after {retries} retries") from last_exc
```

---

## 6. SDK Idioms

### REST API direct (EOS pattern — preferred)
EOS uses `requests` directly rather than the `apify-client` SDK.
This avoids an extra dependency and gives full control over retry logic.

```python
# All Apify calls in EOS follow this pattern:
# 1. rate_limiter.wait()
# 2. requests.post/get with timeout=30
# 3. Check for 429/5xx → retry with exponential backoff
# 4. response.raise_for_status()
# 5. Parse JSON
```

### Actor ID naming
```
# Public actors: "apify/{actor-name}"
# Community actors: "{username}/{actor-name}"
# EOS uses community actors by their internal ID:
"reGe1ST3OBgYZSsZJ"  # Instagram Hashtag Scraper
"SbK00X0JYCPblD2wp"  # Instagram Comment Scraper
"shu8hvrXbJbY3Eb9W"  # Instagram Profile Scraper
```

### Result field normalization
Different actors use different field names for the same data:
```python
# Normalize across actors
username = comment.get("ownerUsername") or comment.get("username") or "unknown"
text = comment.get("text") or comment.get("commentText") or ""
url = post.get("url") or (f"https://www.instagram.com/p/{post.get('shortCode')}/" if post.get("shortCode") else None)
```

---

## 7. Anti-Patterns

### 1. Running actors without credit check
```python
# WRONG — run will fail mid-scrape if credits deplete
run_actor(actor_id, input_data)

# RIGHT — check balance first (or at least handle 403)
# EOS relies on error handling rather than pre-checking
# The retry logic catches 403 and propagates the error
```

### 2. Large resultsLimit without engagement filtering
```python
# WRONG — scrapes 500 posts, most irrelevant
run_actor(scraper_id, {"hashtags": ["gym"], "resultsLimit": 500})

# RIGHT — small limit + post-filtering
run_actor(scraper_id, {"hashtags": ["stuckinyour20s"], "resultsLimit": 50})
# Then: is_icp_relevant_post() filters by content relevance
```

### 3. Not caching scraped URLs
```python
# WRONG — re-scrapes same posts every run
for post in all_posts:
    scrape_comments(post.url)

# RIGHT — track scraped URLs, only process new
known_urls = set(scraped_posts.get(key, {}).get("scraped_urls", []))
new_posts = [p for p in posts if get_post_url(p) not in known_urls]
```

### 4. Tight polling loop
```python
# WRONG — hammers API while waiting
while True:
    status = check_run(run_id)
    if status == "SUCCEEDED": break

# RIGHT — poll with interval
while True:
    apify_limiter.wait()
    status = check_run(run_id)
    if status in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
        break
    time.sleep(POLL_INTERVAL)  # 5 seconds
```

### 5. Ignoring actor version changes
```python
# WRONG — assumes field names never change
username = comment["ownerUsername"]

# RIGHT — defensive field access with fallbacks
username = comment.get("ownerUsername") or comment.get("username") or "unknown"
```

---

## 8. Data Model

### Actor run lifecycle
```
API Token → POST /acts/{id}/runs
  → Run created (status: READY)
    → Run starts (status: RUNNING)
      → Actor executes in Apify cloud
        → Results written to default dataset
          → Run completes (status: SUCCEEDED | FAILED | TIMED-OUT | ABORTED)
            → GET /actor-runs/{id}/dataset/items
              → JSON array of results
```

### EOS data flow
```
Cron trigger
  → apify_scraper.py
    → run_actor() → Apify cloud actor
      → poll_run() → wait for completion
        → get_run_results() → raw items
          → is_human_comment() filter
            → is_priority_comment() classify
              → save_signal() → 01_Inbox/raw_signals/signal_*.md
                → update_hashtag_performance() → hashtag_config.json
```

### Signal file format
```markdown
---
username: john_doe
source: #stuckinyour20s
post_url: https://www.instagram.com/p/ABC123/
timestamp: 2026-04-04_09-30-00
priority: true
---

# Raw Signal  [PRIORITY]

**Username:** @john_doe
**Source:** #stuckinyour20s
**Post URL:** https://www.instagram.com/p/ABC123/
**Timestamp:** 2026-04-04_09-30-00

**Comment:**
I feel like I've been wasting my potential for years...
```

### Hashtag config format (`services/hashtag_config.json`)
```json
{
    "groups": {
        "A": ["stuckinyour20s", "discipline", "wastedpotential"],
        "B": ["grindset", "selfimprovement", "accountability"]
    },
    "current_group": "A",
    "blacklist": ["fitness", "motivation"],
    "suggested": ["aspiringentrepreneur"],
    "performance": {
        "#stuckinyour20s": {
            "runs": 5,
            "total_scanned": 500,
            "total_qualified": 25,
            "total_priority": 8,
            "avg_qualified_rate": 0.05,
            "last_run": "2026-04-04"
        }
    }
}
```

---

## 9. Webhooks and Events

### Apify webhooks (not used by EOS)
Apify supports webhooks for run completion events.
EOS uses polling instead — simpler and sufficient for batch scraping.

```
# Apify webhook configuration (reference only)
POST https://api.apify.com/v2/webhooks?token={token}

{
    "eventTypes": ["ACTOR.RUN.SUCCEEDED", "ACTOR.RUN.FAILED"],
    "condition": {"actorId": "actor_id"},
    "requestUrl": "https://your-server.com/webhook",
    "payloadTemplate": "{\"runId\": {{resource.id}}}"
}

Event types:
  ACTOR.RUN.CREATED
  ACTOR.RUN.SUCCEEDED
  ACTOR.RUN.FAILED
  ACTOR.RUN.TIMED_OUT
  ACTOR.RUN.ABORTED
```

### EOS event flow (internal)
```
apify_scraper.py completes
  → save_signal() writes markdown files
    → Files consumed by downstream scripts
    → Telegram notification for auto-blacklist/promote events
    → Cost logged via cost_tracker.py
```

---

## 10. Limits

### Platform limits
| Resource | Free Tier | Paid |
|----------|-----------|------|
| Compute units/month | 5 CU | depends on plan |
| Storage | 1 GB | 5+ GB |
| Concurrent runs | 5 | 25+ |
| Max run time | 60s (free actors) | configurable |
| Dataset item size | 1 MB per item | same |
| API calls | ~100/min | 100-300/min |

### Proxy limits (separate credit pool)
| Proxy Type | Price | Notes |
|------------|-------|-------|
| DATACENTER | $0.10/GB | Fast, detected by some sites |
| RESIDENTIAL | $10/GB | Real ISP IPs, harder to detect |
| Session sticky | same | Same IP for duration of session |

### EOS-specific limits
```python
resultsLimit = 50     # first run per hashtag
resultsLimit = 10     # incremental updates
resultsLimit = 100    # comment scraping per post
resultsLimit = 200    # competitor post comments

scraped_urls[-100:]   # max 100 cached URLs per source
```

---

## 11. Cost Model

### Compute units
Apify charges by compute units (CU). 1 CU = 1 GB memory for 1 hour.
Most scraper actors use 256-512 MB and run for 30-120 seconds.

**Typical EOS costs per run:**
```
Hashtag scraper (50 posts):    ~0.02-0.05 CU
Comment scraper (100 comments): ~0.01-0.03 CU
Profile scraper (50 posts):    ~0.03-0.05 CU
Full daily scrape:             ~0.20-0.50 CU
Monthly (daily runs):          ~6-15 CU
```

### EOS cost tracking
```python
# cost_tracker.py logs per-run costs
from cost_tracker import log_scraper_costs

cost = log_scraper_costs(
    apify_results=counters["scanned"],
    haiku_calls=haiku_calls,           # Claude calls for relevance filtering
    haiku_input_tokens=haiku_calls * 500,
    haiku_output_tokens=haiku_calls * 150,
)
```

### Proxy costs (separate from compute)
RESIDENTIAL proxy: ~$10/GB. A full scrape session uses ~50-200 MB.
EOS proxy is optional (`INSTAGRAM_USE_PROXY=true`) — default is direct.

---

## 12. Version Pinning

### Actor versioning
```
# Actors can be pinned to specific versions
# EOS uses community actors by internal ID (auto-latest)
# No explicit version pinning — risk: breaking changes

# To pin (recommended for production):
POST /v2/acts/{actorId}/runs?version=1.2.3&token={token}

# Check current version:
GET /v2/acts/{actorId}?token={token}
→ response.data.versions[].versionNumber
```

### API version
Apify API v2 is the current and only supported version.
No version header required — v2 is the default.

### Python SDK
```bash
pip install apify-client  # Latest
pip install apify-client==1.7.0  # Pinned

# EOS does not use the SDK — uses requests directly
```

---

## 13. Design Intent and Tradeoffs

### Why Apify for Instagram scraping
Instagram has no public comment API. The official Graph API requires
approved Instagram Messaging/Content permissions (not available for EOS's use case).
Apify actors run headless browsers in the cloud, bypassing API restrictions.

**Tradeoff:** Cloud actors are slower and more expensive than API calls,
but they access data that APIs don't expose.

### Why REST API over Python SDK
EOS uses `requests` directly instead of `apify-client` because:
1. Full control over retry logic and rate limiting
2. No extra dependency to manage
3. Transparent — every HTTP call is visible
4. Consistent with EOS's direct-API-call pattern

### Why A/B hashtag rotation
EOS rotates between hashtag groups to:
1. Avoid scraping the same posts repeatedly
2. A/B test which hashtags produce the best leads
3. Auto-blacklist low-performing hashtags
4. Auto-promote high performers

### Why comment-level filtering instead of post-level
Posts with high engagement can have 90%+ bot/spam comments.
Filtering at the comment level (not post level) extracts the
genuine buyer signals from the noise.

---

## 14. Problem-Solution Map and Hidden Capabilities

### Finding high-value leads in noisy data
**Problem:** Instagram comments are 80%+ bots and spam.
**Solution:** Multi-layer filtering pipeline:
1. Bot username patterns (community, official, coach, trailing numbers)
2. Spam text detection (short, all caps, link, emoji flood, spam phrases)
3. Deduplication (username + text sets)
4. Priority classification (buyer-signal keywords)
5. Post-level relevance (ICP-relevant by comments sample)

### Incremental scraping without re-processing
**Problem:** Don't want to re-scrape posts from yesterday.
**Solution:** `scraped_posts.json` tracks URLs per source.
New runs only process posts not in the cache (last 100 per source).
First runs get 50 posts (top by engagement). Updates get 10.

### Self-optimizing hashtag selection
**Problem:** Which hashtags produce the best leads?
**Solution:** Auto-blacklist and auto-promote based on qualified rate:
```python
def should_blacklist(perf_data):
    return perf_data["runs"] >= 3 and perf_data["avg_qualified_rate"] < 0.005

def should_promote(perf_data):
    return perf_data["runs"] >= 2 and perf_data["avg_qualified_rate"] > 0.05
```

### AI-powered content relevance
**Problem:** Not all posts under a hashtag are relevant to ICP.
**Solution:** Three-method relevance check:
1. Whisper transcription of video content → Claude Haiku YES/NO
2. Caption analysis via Claude Haiku
3. Keyword fallback (cheapest, least accurate)

---

## 15. Operational Behavior and Edge Cases

### Actor run can succeed with empty dataset
A successful run doesn't guarantee results. The target page may have changed,
selectors may be broken, or all results may have been filtered by the actor.
Always check `len(results) > 0` after getting dataset items.

### Proxy session stickiness
Apify RESIDENTIAL proxy supports sticky sessions (same IP for the session).
EOS uses `session-{random_id}` in the proxy username for DM Monitor.
Session expires after ~10 minutes of inactivity.

### Credit depletion is per-pool
Compute credits and proxy credits are separate pools.
Running out of RESIDENTIAL proxy credits doesn't affect actor runs.
Running out of compute credits doesn't affect proxy.

### Actor timeout vs API timeout
- Actor timeout: how long the actor can run in Apify cloud (60s free, configurable paid)
- API timeout: how long your HTTP request waits (requests timeout=30)
- EOS polls separately, so API timeout only affects the poll/result calls

### Rate limiter state is per-process
`apify_limiter` is a module-level singleton. It tracks timing within one process.
If multiple scraper processes run simultaneously, they don't share rate limiting.
EOS runs one scraper process at a time via cron — no issue.

---

## 16. Ecosystem Position and Composition

### Where Apify fits in EOS
```
Lead Generation Pipeline:
  Instagram posts ← Apify Hashtag Scraper
    └── Comments ← Apify Comment Scraper
          └── Filter (bot/spam/dedup/priority) ← apify_scraper.py
                └── Raw signals ← 01_Inbox/raw_signals/
                      └── Lead qualification ← downstream AI processing

DM Monitoring:
  Instagram login ← Playwright + Apify RESIDENTIAL proxy
    └── DM inbox ← Playwright DOM scraping
```

### Interfaces
- **With Instagram:** Apify actors use headless browsers to access Instagram
- **With Claude:** Haiku classifies post/comment relevance
- **With Whisper:** Transcribes video content for relevance analysis
- **With cost_tracker:** Logs per-run costs to daily summary
- **With Telegram:** Sends auto-blacklist/promote notifications
- **With Playwright:** Proxy infrastructure for DM Monitor

---

## 17. Trajectory and Evolution

### Current state (2026-04)
- Three community actors for Instagram (hashtags, comments, profiles)
- REST API direct (no SDK)
- Conservative rate limiting (10/min)
- A/B hashtag rotation with auto-optimization
- AI-powered content relevance filtering

### Potential improvements
- **SDK migration:** apify-client SDK would simplify code but add dependency
- **Webhook notifications:** Replace polling with webhooks for faster processing
- **Actor version pinning:** Pin to specific versions to prevent breaking changes
- **Multi-platform:** Extend scraping to TikTok, Twitter, YouTube comments
- **Scheduled runs:** Move from EOS cron to Apify scheduler for reliability

### Dependencies
- Actor availability: community actors can be deprecated or removed
- Instagram DOM: selectors change without notice
- Proxy credits: RESIDENTIAL credits are finite and expensive

---

## 18. Conceptual Model and Solution Recipes

### Mental model: Apify as cloud-browser-as-a-service
Think of Apify as a fleet of headless browsers in the cloud.
You tell an actor "scrape this URL" and it launches a browser,
navigates, extracts data, and returns structured results.
You pay for compute time, not per-page.

### Recipe: Add a new competitor to monitoring
```python
# 1. Add to COMPETITOR_ACCOUNTS list in apify_scraper.py
COMPETITOR_ACCOUNTS = [..., "new_account"]

# 2. First run will scrape top 3 posts by engagement
# 3. Subsequent runs scrape 10 most recent posts
# 4. Comments filtered through existing pipeline
# 5. Deploy: docker restart os-scraper
```

### Recipe: Add a new hashtag
```bash
# Via Telegram command (if wired):
/addhashtag newhashtag

# Or edit hashtag_config.json directly:
# Add to groups.A or groups.B array
# Deploy: docker restart os-scraper
```

### Recipe: Debug empty scrape results
```python
# 1. Check run status
status = poll_run(run_id)
# SUCCEEDED but empty? → Actor found no matching content
# FAILED? → Check actor version and input format
# TIMED-OUT? → Reduce resultsLimit

# 2. Check actor logs
url = f"https://api.apify.com/v2/actor-runs/{run_id}/log?token={token}"

# 3. Check if all results were filtered
# Run with is_human_comment() logging to see filter reasons
```

---

## 19. Industry Expert and Cutting-Edge Usage

### Multi-layer signal extraction pipeline
EOS's scraper is not a simple "scrape and save" — it's a signal intelligence pipeline:

```
Raw Instagram data (thousands of comments)
  → Bot detection (username pattern matching)
    → Spam filtering (content analysis)
      → Deduplication (username + text sets)
        → ICP relevance scoring (AI + keywords)
          → Priority classification (buyer signals)
            → Structured markdown signals
              → Downstream lead qualification
```

This reduces thousands of raw comments to dozens of qualified leads
with priority classification. The qualified rate metric tracks pipeline efficiency.

### Self-optimizing source selection
The auto-blacklist/promote system creates a feedback loop:
```
Hashtag → Scrape → Filter → Qualified rate → Decision
  ├── Rate < 0.5% after 3 runs → BLACKLIST (remove from rotation)
  ├── Rate > 5% after 2 runs → PROMOTE (add to Group A)
  └── Between → Continue monitoring
```

Combined with weekly AI hashtag suggestions (Claude Haiku),
the system continuously evolves its source selection without human intervention.

### Cost-efficient relevance filtering
Three-tier relevance approach optimizes cost vs accuracy:
1. **Keyword matching** — free, catches obvious matches
2. **Caption analysis** (Claude Haiku) — $0.00025/call, good accuracy
3. **Video transcription** (Whisper local + Claude Haiku) — free compute + API call, highest accuracy

Cheaper methods run first. Expensive methods only for ambiguous cases.

---

## 20. EOS Usage Patterns

### Daily scraping cycle
```
Cron trigger (e.g., 6 AM daily)
  → get_todays_hashtags() [A/B rotation]
  → For each hashtag:
      → scrape_hashtag() [50 first run, 10 updates]
        → For each new post:
            → is_icp_relevant_post() [Whisper/Claude/keywords]
            → scrape_comments_for_post() [100 per post]
            → Filter and save signals
  → For each competitor (5 accounts):
      → scrape_competitor() [50 first run, 10 updates]
        → Same filter pipeline
  → update_hashtag_performance() [track qualified rates]
  → If Sunday: auto_suggest_hashtags() [Claude Haiku]
  → log_scraper_costs() [cost tracking]
```

### Competitor accounts
```python
COMPETITOR_ACCOUNTS = [
    "robthebank",
    "imangadzhi",
    "hormozi",
    "noah.rolette",
    "zackkravits",
]
```

### Comment filter constants
```python
BOT_USERNAME_SUBSTRINGS = [
    "._.", "community", "official", "coach", "motivat", "fitness",
    "health", "store", "shop", "business", "marketing", "growth", "agency",
]

SPAM_PHRASES = [
    "follow", "check my", "link in bio", "dm me", "click",
    "visit my", "gain followers", "promo", "discount", "shop now",
]

PRIORITY_SIGNALS = [
    "wast", "stuck", "struggle", "can't", "need", "help",
    "feel like", "trying", "failed", "failing", "potential",
    "discipline", "lazy", "procrastinat", "lost", "behind",
]
```

---

## 21. Gotchas (Real EOS Production Issues)

### RESIDENTIAL proxy returns 403 when credits depleted (ACTIVE)
Proxy credits are separate from compute credits. When RESIDENTIAL pool is empty,
all proxy requests return 403 Forbidden.
**Symptom:** DM Monitor login fails, proxy-routed scrapes fail.
**Fix:** Set `INSTAGRAM_USE_PROXY=false` or purchase more proxy credits.

### Actor version changes break field names (INTERMITTENT)
Community actors update without notice. Field names can change
(`ownerUsername` → `username`, `text` → `commentText`).
**Symptom:** Empty results despite SUCCEEDED status.
**Fix:** Use `.get()` with fallback chains. Check actor changelog on Apify console.

### Scraped posts cache grows unbounded (RESOLVED)
Without cleanup, `scraped_posts.json` accumulated thousands of URLs.
**Fix:** `scraped_urls[-100:]` caps at 100 URLs per source.

### Hashtag auto-blacklist too aggressive (POTENTIAL)
A hashtag with legitimately low comment quality (early runs) may get blacklisted
before it has a chance to produce results.
**Mitigation:** Requires 3 runs minimum before blacklisting. Blacklisted hashtags
can be manually moved back via editing `hashtag_config.json`.

### Cost tracking counts filtered comments (BY DESIGN)
`log_scraper_costs()` uses `counters["scanned"]` (total comments processed),
not just qualified ones. This overcounts actual "useful" API usage
but accurately reflects Apify compute consumption.

### TIMED-OUT runs leave partial datasets (ACTIVE)
If an actor times out, the dataset may contain partial results.
EOS treats TIMED-OUT same as FAILED (returns empty).
**Impact:** Some scraped data is lost. Not a problem at current scale.
