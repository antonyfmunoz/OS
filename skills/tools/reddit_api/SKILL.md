---
name: reddit_api
description: "Use when mining Reddit discussions for market research, searching subreddits for ICP signals, extracting comment insights, enriching Reddit thread data with engagement metrics, or building any Reddit integration."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://www.reddit.com/dev/api/"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "v1 (oauth.reddit.com)"
sdk_version: "PRAW 7.7.1 (if used), or direct HTTP via .json endpoints"
speed_category: medium
trigger: both
effort: medium
context: fork
---

# Tool: Reddit API

## What This Tool Does

Reddit's API provides programmatic access to submissions, comments, subreddits,
user profiles, and search across the entire platform. Two access methods exist:

1. **OAuth2 API** (`oauth.reddit.com`) -- authenticated, 100 req/min, full CRUD
2. **Public JSON endpoints** (`www.reddit.com/.../.json`) -- unauthenticated, limited,
   read-only, no API key needed

Core capabilities for EOS:
- **Subreddit search** -- find posts matching keywords within specific subreddits
- **Thread enrichment** -- fetch real engagement metrics (score, upvote_ratio, num_comments)
- **Comment extraction** -- pull top comments with scores for sentiment/insight mining
- **Discussion mining** -- surface what real people say about topics, products, competitors
- **Trend detection** -- identify emerging topics by engagement velocity

## EOS Integration

### Primary usage: last30days skill (Phase 2 supplemental search)
`.agents/skills/last30days/scripts/lib/openai_reddit.py` -- `search_subreddits()` function.
Searches specific subreddits via the free `.json` endpoint. No API key needed.
Used after Phase 1 entity extraction discovers relevant subreddits.

### Thread enrichment pipeline
`.agents/skills/last30days/scripts/lib/reddit_enrich.py` -- Full enrichment module:
- `fetch_thread_data(url)` -- fetches thread JSON via `get_reddit_json()`
- `parse_thread_data(data)` -- extracts submission metadata + comments
- `enrich_reddit_item(item)` -- adds real score, upvote_ratio, num_comments
- `extract_comment_insights(comments)` -- heuristic filtering for substantive comments
- `get_top_comments(comments, limit)` -- sorted by score, filtered for deleted

### HTTP layer
`.agents/skills/last30days/scripts/lib/http.py` -- `get_reddit_json(path)` function.
Appends `.json?raw_json=1` to any Reddit path. Uses custom User-Agent header.
Returns parsed JSON. Handles retries and 429 rate limit errors.

### Research agent references
`agents/research_agent.md` -- references Reddit threads as ICP signal source.
`05_Workflows/research/signal_intelligence_workflow/` -- Reddit as capture source.

### Current approach: direct HTTP, not PRAW
EOS does NOT use PRAW. All Reddit access is via direct HTTP to public `.json`
endpoints. This avoids OAuth2 setup overhead and works for read-only research.
PRAW would be needed for: posting, voting, messaging, moderating, or exceeding
public endpoint rate limits.

## Authentication

### Method 1: Public JSON (current EOS approach)
No authentication needed. Append `.json?raw_json=1` to any Reddit URL:
```
https://www.reddit.com/r/entrepreneur/search/.json?q=saas&restrict_sr=on&sort=new&limit=25&raw_json=1
https://www.reddit.com/r/startups/comments/abc123/my_post/.json?raw_json=1
```
Requires a descriptive User-Agent header (Reddit blocks default/empty User-Agents).
Rate limit: ~10 req/min before soft throttling, hard 429 at ~30 req/min.

### Method 2: OAuth2 Script App (for authenticated access)
1. Go to https://www.reddit.com/prefs/apps
2. Create app -> select "script" type
3. Set redirect URI to `http://localhost:8080`
4. Store credentials:
```
REDDIT_CLIENT_ID=       # 14-char string under app name
REDDIT_CLIENT_SECRET=   # "secret" field
REDDIT_USERNAME=        # Reddit account username
REDDIT_PASSWORD=        # Reddit account password
REDDIT_USER_AGENT=      # "platform:app_id:v1.0 (by /u/username)"
```
5. Token endpoint: POST `https://www.reddit.com/api/v1/access_token`
   - Basic auth with client_id:client_secret
   - Body: `grant_type=password&username=X&password=Y`
   - Returns: `{"access_token": "...", "token_type": "bearer", "expires_in": 86400}`
6. Use token: `Authorization: Bearer {token}` on `oauth.reddit.com`

### Method 3: OAuth2 Web App (for multi-user)
Uses authorization code flow with redirect. Needed if EOS ever
acts on behalf of multiple Reddit users. Not currently required.

### Env vars (if OAuth2 is added)
Would go in `eos_ai/.env`:
```
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USERNAME=
REDDIT_PASSWORD=
REDDIT_USER_AGENT=eos:entrepreneur-os:v1.0 (by /u/eos_bot)
```

## Quick Reference

### Search a subreddit (public JSON, no auth)
```python
import requests

url = "https://www.reddit.com/r/entrepreneur/search/.json"
params = {
    "q": "saas pricing",
    "restrict_sr": "on",     # search only this subreddit
    "sort": "new",           # new, hot, relevance, top, comments
    "limit": 25,             # max 100
    "raw_json": 1,           # disable HTML entity encoding
    "t": "month",            # hour, day, week, month, year, all
}
headers = {"User-Agent": "eos:research:v1.0"}
resp = requests.get(url, params=params, headers=headers)
data = resp.json()

for child in data["data"]["children"]:
    post = child["data"]
    print(f'{post["title"]} | score:{post["score"]} | r/{post["subreddit"]}')
```

### Fetch thread with comments (public JSON)
```python
path = "/r/startups/comments/abc123/my_post"
url = f"https://www.reddit.com{path}.json?raw_json=1"
headers = {"User-Agent": "eos:research:v1.0"}
resp = requests.get(url, headers=headers)
data = resp.json()

# data[0] = submission listing, data[1] = comments listing
submission = data[0]["data"]["children"][0]["data"]
comments = data[1]["data"]["children"]

print(f'Score: {submission["score"]}, Ratio: {submission["upvote_ratio"]}')
for c in comments:
    if c["kind"] == "t1":  # t1 = comment
        print(f'  {c["data"]["score"]}pts: {c["data"]["body"][:100]}')
```

### Search all of Reddit (public JSON)
```python
url = "https://www.reddit.com/search/.json"
params = {
    "q": "entrepreneur OS automation",
    "sort": "relevance",
    "limit": 25,
    "raw_json": 1,
    "t": "month",
}
headers = {"User-Agent": "eos:research:v1.0"}
resp = requests.get(url, params=params, headers=headers)
```

### EOS pattern: subreddit search from last30days
```python
# From .agents/skills/last30days/scripts/lib/openai_reddit.py
from last30days.scripts.lib import http

url = f"https://www.reddit.com/r/{subreddit}/search/.json"
params = f"q={query}&restrict_sr=on&sort=new&limit=5&raw_json=1"
data = http.get(f"{url}?{params}", headers={"User-Agent": http.USER_AGENT})

for child in data.get("data", {}).get("children", []):
    if child.get("kind") == "t3":  # t3 = link/submission
        post = child["data"]
        # Extract title, permalink, subreddit, created_utc, score
```

### EOS pattern: thread enrichment
```python
# From .agents/skills/last30days/scripts/lib/reddit_enrich.py
from reddit_enrich import enrich_reddit_item, RedditRateLimitError

item = {"url": "https://www.reddit.com/r/startups/comments/abc123/post/"}
try:
    enriched = enrich_reddit_item(item, timeout=10, retries=1)
    # enriched now has: engagement.score, engagement.num_comments,
    # engagement.upvote_ratio, top_comments[], comment_insights[]
except RedditRateLimitError:
    # Bail on remaining items -- Reddit is throttling
    pass
```

### PRAW quick start (if migrating to authenticated)
```python
import praw

reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    username=os.getenv("REDDIT_USERNAME"),
    password=os.getenv("REDDIT_PASSWORD"),
    user_agent=os.getenv("REDDIT_USER_AGENT"),
)

# Search subreddit
for submission in reddit.subreddit("entrepreneur").search("saas pricing", limit=25):
    print(f"{submission.title} | {submission.score} | {submission.num_comments}")

# Get hot posts
for submission in reddit.subreddit("startups").hot(limit=10):
    print(submission.title)

# Get comments from a submission
submission = reddit.submission(id="abc123")
submission.comments.replace_more(limit=0)  # flatten comment forest
for comment in submission.comments.list():
    print(f"{comment.score}: {comment.body[:100]}")
```

## Conceptual Model

```
Reddit API
  |
  +-- Public JSON (www.reddit.com/.../.json)
  |     |-- No auth needed
  |     |-- Read-only: listings, threads, comments, search
  |     |-- ~10 req/min soft limit, 429 at ~30 req/min
  |     |-- raw_json=1 disables HTML entity encoding
  |     +-- EOS currently uses ONLY this path
  |
  +-- OAuth2 API (oauth.reddit.com)
  |     |-- 100 requests per minute per token
  |     |-- Full CRUD: submit, comment, vote, moderate
  |     |-- Script app (single user) or Web app (multi-user)
  |     |-- Tokens expire in 24 hours (3600s for web apps)
  |     +-- Required for posting, voting, messaging
  |
  +-- Thing Types (Reddit's type system)
  |     |-- t1 = Comment
  |     |-- t2 = Account
  |     |-- t3 = Link (submission/post)
  |     |-- t4 = Message
  |     |-- t5 = Subreddit
  |     +-- t6 = Award
  |
  +-- Listing Structure (universal response format)
  |     |-- {"kind": "Listing", "data": {"children": [...], "after": "t3_xxx"}}
  |     |-- Each child: {"kind": "t3", "data": {...fields...}}
  |     +-- Pagination via "after" fullname token
  |
  +-- Search
  |     |-- /r/{sub}/search/.json -- within subreddit
  |     |-- /search/.json -- all of Reddit
  |     |-- Params: q, sort, t (time), limit, restrict_sr
  |     +-- Lucene-like syntax: title:keyword, self:yes, flair:name
  |
  +-- PRAW (Python SDK layer)
        |-- reddit.subreddit("name") -> Subreddit object
        |-- subreddit.search(query) -> generator of Submissions
        |-- reddit.submission(id=) -> Submission with comments
        |-- submission.comments -> CommentForest (tree structure)
        +-- Handles auth, rate limits, pagination automatically
```

See references/best_practices.md for rate limits, error codes, and anti-patterns.

## Gotchas

### User-Agent is mandatory for public JSON
Reddit silently blocks or heavily throttles requests with default/empty User-Agent
headers. Always set a descriptive User-Agent like `eos:research:v1.0`. Without it,
you get 429s almost immediately or empty responses.

### Public JSON rate limit is undocumented and aggressive
Reddit's public `.json` endpoints have no official rate limit documentation.
In practice, ~10 requests/minute works reliably. Above ~30 req/min, expect 429s.
The EOS last30days skill handles this with `RedditRateLimitError` propagation --
on first 429, bail on all remaining Reddit items.

### raw_json=1 is essential
Without `?raw_json=1`, Reddit HTML-encodes characters in JSON responses.
`&amp;` instead of `&`, `&lt;` instead of `<`. This breaks URL parsing
and text display. Always include this parameter.

### Thread JSON returns array, not object
A thread URL `.json` returns a JSON array, not an object:
- `data[0]` = submission listing
- `data[1]` = comments listing
Code that expects `data["kind"]` at the top level will crash.
Always check `isinstance(data, list)` first.

### Comment forest is a tree, not a flat list
Reddit comments are nested. `children` within comments contain replies.
"More" objects (`kind: "more"`) represent collapsed comment threads.
PRAW has `replace_more()` to flatten. With raw JSON, you must recurse
or accept only top-level comments (which is what EOS does).

### Search time filter parameter is "t", not "time"
The time filter parameter is `t=month`, not `time=month` or `timeframe=month`.
Valid values: `hour`, `day`, `week`, `month`, `year`, `all`.
Only applies when `sort=top` or `sort=relevance`.

### Reddit API pricing changes (June 2023)
Reddit moved from free unlimited API access to a paid model for high-volume
commercial use. Free tier remains for: non-commercial use, research, and
apps making <100 queries/min via OAuth. The public JSON endpoints remain
free and unauthenticated. PRAW works with the free tier for script apps.
The pricing change primarily affects third-party Reddit client apps.

### created_utc is a float, not an integer
`created_utc` is a Unix timestamp as a float (e.g., `1711234567.0`).
Some JSON parsers handle this fine, but if you do integer division or
comparison, cast to int first. EOS uses `dates.timestamp_to_date()`.

### Deleted content shows as [deleted] or [removed]
- `[deleted]` = user deleted their own content
- `[removed]` = moderator removed it
Author field becomes `[deleted]` in both cases. Always filter these
out before extracting insights. EOS filters in `get_top_comments()`.
