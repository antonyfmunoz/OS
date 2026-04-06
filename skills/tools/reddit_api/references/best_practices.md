# Reddit API -- Creator-Level Best Practices
Source: https://www.reddit.com/dev/api/ | https://github.com/reddit-archive/reddit/wiki/API
API Version: v1 (oauth.reddit.com)
SDK Version: PRAW 7.7.1
Last Researched: 2026-04-06

---

# Tier 1 -- Technical Mastery

## 1. Authentication

### OAuth2 Script App (single-user, server-side)
Best for EOS. No redirect needed. Direct username/password grant.

**Setup:**
1. https://www.reddit.com/prefs/apps -> "create another app"
2. Select "script" type
3. Redirect URI: `http://localhost:8080` (required but unused for script apps)
4. Note the client_id (14-char string below app name) and secret

**Token request:**
```
POST https://www.reddit.com/api/v1/access_token
Authorization: Basic base64(client_id:client_secret)
Content-Type: application/x-www-form-urlencoded

grant_type=password&username=USER&password=PASS
```

**Response:**
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "expires_in": 86400,
  "scope": "*"
}
```

**Token lifetime:** 24 hours (86400 seconds) for script apps. No refresh token issued --
re-authenticate with password grant. PRAW handles this automatically.

**Scopes (relevant to EOS):**
- `read` -- access posts and comments
- `history` -- access user's post/comment history
- `identity` -- access user's identity
- `submit` -- submit links and comments
- `subscribe` -- manage subreddit subscriptions
- `vote` -- upvote/downvote (not recommended for automation)
- `*` -- script apps get all scopes by default

### OAuth2 Web App (multi-user)
Authorization code flow. User redirects to Reddit, authorizes, returns with code.
Token lifetime: 1 hour. Refresh token issued. Needed for acting on behalf of
multiple Reddit users. Not needed for EOS currently.

### Application-Only Auth (client credentials)
For read-only access without a user context. Cannot access user-specific data.
```
POST https://www.reddit.com/api/v1/access_token
Authorization: Basic base64(client_id:client_secret)
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials
```
Rate limit: same 100 req/min. Useful for anonymous scraping with higher limits
than public JSON.

### Public JSON (no auth)
Append `.json?raw_json=1` to any Reddit URL. No credentials needed.
Rate limit: undocumented, approximately 10-30 req/min.
**This is what EOS currently uses.**

### Env vars (EOS convention):
```
REDDIT_CLIENT_ID=         # eos_ai/.env
REDDIT_CLIENT_SECRET=     # eos_ai/.env
REDDIT_USERNAME=          # eos_ai/.env
REDDIT_PASSWORD=          # eos_ai/.env
REDDIT_USER_AGENT=eos:entrepreneur-os:v1.0 (by /u/eos_bot)
```

---

## 2. Core Operations with Exact Signatures

### Public JSON: Search within subreddit
```
GET https://www.reddit.com/r/{subreddit}/search/.json
Params:
  q: str                    # required -- search query (Lucene-like)
  restrict_sr: str = "on"   # "on" to restrict to subreddit
  sort: str = "relevance"   # relevance, hot, top, new, comments
  t: str = "all"            # hour, day, week, month, year, all
  limit: int = 25           # 1-100
  after: str = None         # fullname for pagination (t3_xxxxx)
  raw_json: int = 1         # 1 to disable HTML encoding
Returns: {"kind": "Listing", "data": {"children": [{"kind": "t3", "data": {...}}], "after": "t3_xxx", "before": null}}
```

### Public JSON: Search all of Reddit
```
GET https://www.reddit.com/search/.json
Params: same as subreddit search minus restrict_sr
Returns: same Listing structure
```

### Public JSON: Fetch thread with comments
```
GET https://www.reddit.com/r/{sub}/comments/{id}/{slug}.json
Params:
  raw_json: int = 1
  sort: str = "confidence"  # confidence, top, new, controversial, old, qa
  limit: int = 200          # max comment count
  depth: int = None         # max reply depth
Returns: [ListingObject, ListingObject]  # [0]=submission, [1]=comments
```

### Public JSON: Subreddit listing
```
GET https://www.reddit.com/r/{subreddit}/{sort}.json
sort: hot, new, rising, top, controversial
Params:
  limit: int = 25           # 1-100
  t: str = "day"            # time filter for top/controversial
  after: str = None         # pagination
  raw_json: int = 1
Returns: Listing of t3 (submissions)
```

### PRAW: Search subreddit
```python
reddit.subreddit("entrepreneur").search(
    query: str,                # required
    sort: str = "relevance",   # relevance, hot, top, new, comments
    syntax: str = "lucene",    # lucene, cloudsearch, plain
    time_filter: str = "all",  # hour, day, week, month, year, all
    limit: int = None,         # None=max (1000)
)
# Returns: Generator[Submission]
# Submission attrs: .title, .score, .url, .selftext, .num_comments,
#   .created_utc, .author, .subreddit, .permalink, .upvote_ratio, .id
```

### PRAW: Get subreddit posts
```python
reddit.subreddit("startups").hot(limit=25)     # -> Generator[Submission]
reddit.subreddit("startups").new(limit=25)     # -> Generator[Submission]
reddit.subreddit("startups").top(time_filter="month", limit=25)
reddit.subreddit("startups").rising(limit=25)
```

### PRAW: Get submission with comments
```python
submission = reddit.submission(id="abc123")
# or: reddit.submission(url="https://reddit.com/r/sub/comments/abc123/title/")
submission.comments.replace_more(limit=0)  # flatten; limit=0 discards "more"
all_comments = submission.comments.list()  # flat list
# Comment attrs: .body, .score, .author, .created_utc, .parent_id, .permalink
```

### PRAW: Submit a post
```python
subreddit = reddit.subreddit("test")
# Text post
subreddit.submit(title="My Post", selftext="Body text here")
# Link post
subreddit.submit(title="Check this", url="https://example.com")
```

### PRAW: Submit a comment
```python
submission.reply("My comment text")
comment.reply("My reply to a comment")
```

### OAuth2 REST: Search (authenticated)
```
GET https://oauth.reddit.com/r/{subreddit}/search
Authorization: Bearer {access_token}
User-Agent: eos:entrepreneur-os:v1.0 (by /u/eos_bot)
Params: same as public JSON
Returns: same Listing structure
```

---

## 3. Pagination Patterns

Reddit uses **cursor-based pagination** with `after` and `before` fullnames.

### Fullnames
Every Reddit thing has a fullname: `{type_prefix}_{id}`.
- `t1_abc123` = comment
- `t3_xyz789` = submission/link
- `t5_2qh1i` = subreddit

### Fetch all pattern (public JSON)
```python
results = []
after = None
while True:
    params = {"limit": 100, "raw_json": 1}
    if after:
        params["after"] = after
    resp = requests.get(url, params=params, headers=headers)
    data = resp.json()
    children = data["data"]["children"]
    if not children:
        break
    results.extend(children)
    after = data["data"].get("after")
    if not after:
        break
    time.sleep(2)  # respect rate limits for public JSON
```

### PRAW pagination
PRAW handles pagination automatically via generators:
```python
# This internally paginates -- just iterate
for submission in reddit.subreddit("all").search("topic", limit=500):
    process(submission)
```

### Hard limit
Reddit caps listing pagination at **1000 items** regardless of approach.
You cannot paginate past 1000 results. For deeper access, use Pushshift
(if available) or narrow your search with time filters.

### Search pagination
Search results also use `after` cursor. Same 1000-item hard cap applies.

---

## 4. Rate Limits

### OAuth2 authenticated
- **100 requests per minute** per OAuth2 token
- Applies to all endpoints uniformly
- Headers returned:
  - `X-Ratelimit-Used`: requests used in current window
  - `X-Ratelimit-Remaining`: requests remaining
  - `X-Ratelimit-Reset`: seconds until window resets
- When exceeded: HTTP 429 with `Retry-After` header

### Public JSON (unauthenticated)
- **No official documentation** on limits
- Practical observation: ~10 req/min works reliably
- Aggressive at ~30 req/min: returns 429
- No rate limit headers returned
- User-Agent quality affects throttling (generic UAs get throttled faster)

### PRAW built-in handling
PRAW automatically:
- Tracks rate limit headers
- Sleeps when approaching limits
- Respects `Retry-After` on 429
- Default sleep: waits until rate limit window resets

### Recommended backoff
```python
# For public JSON
import time
def reddit_request(url, headers, max_retries=3):
    for attempt in range(max_retries):
        resp = requests.get(url, headers=headers)
        if resp.status_code == 429:
            wait = min(2 ** attempt * 5, 60)  # 5s, 10s, 20s
            time.sleep(wait)
            continue
        return resp
    raise Exception("Reddit rate limited after retries")
```

### Per-endpoint nuances
- Search endpoints are rate-limited more aggressively than listing endpoints
- `.json` thread fetches are lighter than search queries
- Cross-subreddit search (`/search/.json`) is heavier than single-subreddit

---

## 5. Error Codes and Recovery

### HTTP status codes
| Code | Meaning | Recovery |
|------|---------|----------|
| 200  | Success | -- |
| 301  | Redirect (old URL format) | Follow redirect |
| 302  | Redirect to login | Auth expired or required |
| 400  | Bad request (malformed params) | Fix parameters |
| 401  | Invalid/expired token | Re-authenticate |
| 403  | Forbidden (banned, private sub) | Check permissions, subreddit status |
| 404  | Not found (deleted post, wrong sub) | Skip item |
| 429  | Rate limited | Backoff, check `Retry-After` header |
| 500  | Server error | Retry with backoff |
| 502  | Bad gateway | Retry (Reddit infra issue) |
| 503  | Service unavailable | Retry (Reddit under load) |

### Reddit-specific error responses
```json
{"message": "Forbidden", "error": 403}
{"reason": "SUBREDDIT_NOTALLOWED", "message": "Forbidden", "error": 403}
{"json": {"errors": [["RATELIMIT", "you are doing that too much. try again in 7 minutes.", "ratelimit"]]}}
```

### Common non-obvious errors
- **302 to login page**: Public JSON returns 302 redirect when subreddit is private
  or quarantined. This looks like a successful response unless you check status.
- **Empty children array**: Not an error -- subreddit exists but search returned
  no results. Check `data.children.length`, not HTTP status.
- **"[Listing]" with 0 children**: Subreddit is empty or heavily moderated.
- **JSON parse error on .json endpoint**: Reddit occasionally returns HTML error
  pages instead of JSON. Always wrap JSON parsing in try/except.

### Retryable vs non-retryable
- **Retry**: 429, 500, 502, 503 (with exponential backoff)
- **Do not retry**: 400, 401, 403, 404 (fix the request or skip)

---

## 6. SDK Idioms

### PRAW initialization
```python
import praw

# Script app (single user) -- preferred for EOS
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    username=os.getenv("REDDIT_USERNAME"),
    password=os.getenv("REDDIT_PASSWORD"),
    user_agent="eos:entrepreneur-os:v1.0 (by /u/eos_bot)",
)

# Read-only (no username/password)
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent="eos:entrepreneur-os:v1.0 (by /u/eos_bot)",
)
# reddit.read_only == True
```

### PRAW is synchronous
PRAW is synchronous only. For async, use `asyncpraw`:
```python
import asyncpraw
reddit = asyncpraw.Reddit(...)
async for submission in reddit.subreddit("test").hot(limit=10):
    print(submission.title)
await reddit.close()
```

### Lazy loading
PRAW objects are lazy. Accessing an attribute triggers an API call:
```python
submission = reddit.submission(id="abc123")
# No API call yet
print(submission.title)  # NOW fetches from API
```

### Comment forest
```python
submission.comments  # -> CommentForest object
submission.comments.replace_more(limit=0)  # Remove MoreComments objects
submission.comments.list()  # Flatten tree to list
# limit=0 discards "more" without fetching. limit=32 fetches up to 32 "more" objects.
```

### Multi-subreddit
```python
reddit.subreddit("entrepreneur+startups+smallbusiness").hot(limit=25)
# Combines multiple subreddits with + separator
```

### Streaming (real-time)
```python
for comment in reddit.subreddit("entrepreneur").stream.comments():
    process(comment)  # infinite generator, yields new comments
```

---

## 7. Anti-Patterns

### WRONG: No User-Agent on public JSON
```python
# BAD -- will get 429 almost immediately
resp = requests.get("https://www.reddit.com/r/test.json")
```
```python
# GOOD
headers = {"User-Agent": "eos:research:v1.0"}
resp = requests.get("https://www.reddit.com/r/test.json", headers=headers)
```

### WRONG: Missing raw_json=1
```python
# BAD -- HTML entities in JSON
url = "https://www.reddit.com/r/test/search/.json?q=test"
# Returns: {"title": "Test &amp; Debug"} -- broken
```
```python
# GOOD
url = "https://www.reddit.com/r/test/search/.json?q=test&raw_json=1"
# Returns: {"title": "Test & Debug"} -- clean
```

### WRONG: Treating thread response as dict
```python
# BAD -- thread response is a list
data = resp.json()
submission = data["data"]["children"][0]  # KeyError!
```
```python
# GOOD
data = resp.json()
submission = data[0]["data"]["children"][0]["data"]
comments = data[1]["data"]["children"]
```

### WRONG: Not handling comment forest depth
```python
# BAD -- only gets top-level comments
for comment in submission.comments:
    print(comment.body)  # Crashes on MoreComments objects
```
```python
# GOOD
submission.comments.replace_more(limit=0)
for comment in submission.comments.list():
    print(comment.body)
```

### WRONG: Iterating past 1000 results
```python
# BAD -- silently stops at 1000
all_posts = list(reddit.subreddit("test").new(limit=5000))
# len(all_posts) will be ~1000
```
```python
# GOOD -- use time windows to get more
for time_filter in ["day", "week", "month"]:
    posts = reddit.subreddit("test").top(time_filter=time_filter, limit=100)
```

### WRONG: Hammering public JSON
```python
# BAD -- no delay between requests
for sub in subreddits:
    resp = requests.get(f"https://www.reddit.com/r/{sub}.json")
```
```python
# GOOD -- respect rate limits
for sub in subreddits:
    resp = requests.get(f"https://www.reddit.com/r/{sub}.json", headers=headers)
    time.sleep(2)
```

### WRONG: Not checking kind field
```python
# BAD -- "more" objects don't have "body"
for child in data[1]["data"]["children"]:
    print(child["data"]["body"])  # KeyError on kind="more"
```
```python
# GOOD
for child in data[1]["data"]["children"]:
    if child["kind"] == "t1":
        print(child["data"]["body"])
```

---

## 8. Data Model

### Entity hierarchy
```
Reddit
  +-- Subreddit (t5)
  |     +-- Submission/Link (t3)
  |     |     +-- Comment (t1)
  |     |     |     +-- Comment (t1)  [nested replies]
  |     |     |     +-- MoreComments  [collapsed threads]
  |     |     +-- Award (t6)
  |     +-- Rules
  |     +-- Wiki pages
  +-- Account (t2)
  |     +-- Submissions
  |     +-- Comments
  |     +-- Trophies
  +-- Message (t4)
        +-- Inbox
        +-- Sent
```

### Submission (t3) key fields
| Field | Type | Notes |
|-------|------|-------|
| id | str | Base-36 ID (e.g., "abc123") |
| name | str | Fullname "t3_abc123" |
| title | str | Max 300 chars |
| selftext | str | Body text (empty for link posts) |
| url | str | Link URL or self URL |
| permalink | str | Reddit path (no domain) |
| score | int | Net upvotes (upvotes - downvotes, fuzzy) |
| upvote_ratio | float | 0.0 to 1.0 |
| num_comments | int | Total comment count |
| created_utc | float | Unix timestamp |
| author | str | Username or "[deleted]" |
| subreddit | str | Subreddit name (no r/) |
| is_self | bool | True for text posts |
| over_18 | bool | NSFW flag |
| spoiler | bool | Spoiler flag |
| stickied | bool | Pinned by moderator |
| distinguished | str/null | "moderator", "admin", or null |
| link_flair_text | str/null | Post flair |

### Comment (t1) key fields
| Field | Type | Notes |
|-------|------|-------|
| id | str | Base-36 ID |
| name | str | Fullname "t1_xxx" |
| body | str | Markdown text |
| body_html | str | Rendered HTML |
| score | int | Net upvotes |
| created_utc | float | Unix timestamp |
| author | str | Username or "[deleted]" |
| parent_id | str | Fullname of parent (t3_ or t1_) |
| permalink | str | Reddit path |
| is_submitter | bool | True if OP |
| stickied | bool | Pinned by mod |
| replies | Listing/str | Nested comments or empty string |

### Subreddit (t5) key fields
| Field | Type | Notes |
|-------|------|-------|
| display_name | str | Name without r/ |
| subscribers | int | Subscriber count |
| active_user_count | int | Currently online |
| public_description | str | Sidebar blurb |
| over18 | bool | NSFW subreddit |
| subreddit_type | str | public, private, restricted |

---

## 9. Webhooks and Events

**N/A for standard Reddit API.**

Reddit does not provide webhook or push notification support.
All data access is pull-based (polling).

### Alternatives for real-time:
- **PRAW streaming**: `subreddit.stream.comments()` and `subreddit.stream.submissions()`
  poll Reddit every ~few seconds and yield new items. Not true push.
- **Reddit Chat WebSocket**: Undocumented, internal use only. Not stable.
- **Third-party**: Pushshift (historical data), Reddit RSS feeds (`/.rss` suffix).

### EOS approach
EOS uses on-demand search and enrichment, not streaming.
Polling is unnecessary for the research/intelligence use case.

---

## 10. Limits

### Request limits
| Limit | Value |
|-------|-------|
| OAuth2 rate limit | 100 requests/minute/token |
| Public JSON rate limit | ~10-30 requests/minute (undocumented) |
| Search results max | 1000 items per query (pagination cap) |
| Listing page size | 100 items max per request |
| Multi-subreddit combine | No documented limit, but 100+ is unreliable |

### Content limits
| Limit | Value |
|-------|-------|
| Post title | 300 characters |
| Self-text body | 40,000 characters |
| Comment body | 10,000 characters |
| Username | 3-20 characters |
| Subreddit name | 3-21 characters |
| Flair text | 64 characters |
| Search query | 512 characters |

### Account limits (for posting)
| Limit | Value |
|-------|-------|
| New account posting | Karma/age restrictions per subreddit |
| Comment cooldown | "You are doing that too much" -- varies |
| Cross-post limit | 100 cross-posts per post |
| Subreddit creation | Account must be 30+ days old |

---

## 11. Cost Model

### Current pricing (post-June 2023 changes)

**Free tier:**
- Research, personal, and non-commercial use
- Apps making fewer than 100 queries per minute via OAuth2
- Script apps (single-user automation)
- Public JSON endpoints (no auth, lower rate limits)
- PRAW with script app credentials

**Enterprise tier ($0.24 per 1K API calls):**
- Commercial apps accessing Reddit data at scale
- Third-party Reddit client apps
- Data licensing for AI/ML training
- Required for apps with 100M+ data requests/month

**What triggered the pricing change:**
In April 2023, Reddit announced API pricing effective July 1, 2023.
This killed most third-party Reddit clients (Apollo, Reddit is Fun, etc.)
because their usage would cost millions per year. The change was primarily
aimed at AI companies scraping Reddit for LLM training data.

**EOS impact:** None. EOS uses public JSON endpoints for low-volume research
(well under 100 queries/minute). If migrating to OAuth2, script apps remain
free. No cost unless building a commercial Reddit client or bulk data pipeline.

**Monitoring:** No usage dashboard for free tier. PRAW logs rate limit headers.
For public JSON, monitor 429 response frequency as a proxy.

---

## 12. Version Pinning

### API versioning
Reddit API does not use explicit version numbers in URLs. `oauth.reddit.com`
is the only endpoint. Breaking changes are rare and announced on r/redditdev.
There is no `api-version` header or URL prefix like `/v2/`.

### PRAW versioning
```
Current: PRAW 7.7.1 (pip install praw)
Python: 3.8+
Async: asyncpraw 7.7.1 (separate package)
```

Pin in requirements.txt:
```
praw==7.7.1
```

### Known deprecations
- **Old OAuth endpoint** (`/api/v1/authorize`) still works but documentation
  emphasizes the compact flow for mobile
- **Pushshift API** (third-party historical archive) was taken down and
  replaced with Reddit's official archive access in 2023
- **Reddit RSS** (`.rss` suffix) still works but is not officially supported
- `json` legacy endpoints (no `.json` suffix, using `?format=json`) are
  deprecated in favor of `.json` suffix

### Breaking changes to watch
- Reddit has not announced a v2 API
- PRAW 8.0 has been discussed but not released as of early 2025
- Reddit's data API agreement may restrict certain automated uses

---

# Tier 2 -- Creator Intelligence

## 13. Design Intent and Tradeoffs

Reddit was built as a link aggregator with community-driven curation.
The core design philosophy: **communities self-govern, content rises
or falls by vote.** This shapes everything about the API:

**Why the API is read-biased:** Reddit's value is in consumption and
discovery, not programmatic content creation. Write operations (posting,
commenting) have intentionally higher friction (karma requirements,
rate limits, captchas) to prevent spam. Read operations are relatively
open because Reddit wants its content indexed and discoverable.

**Why scores are "fuzzed":** Reddit intentionally fuzzes vote counts
to make vote manipulation harder to detect. The `score` field is
approximate, not exact. `upvote_ratio` is more reliable for sentiment.

**Why the comment tree exists:** Reddit chose a nested comment model
(like Usenet) over flat comments (like forums) because it enables
nuanced discussion. This makes the API harder to consume but matches
Reddit's identity as a discussion platform, not a broadcast platform.

**What Reddit is NOT:** Reddit is not a social network (no "follow"
as primary action), not a content management system (no structured
data), not a search engine (search is famously poor). It's a
community-driven discussion aggregator.

**The 1000-item cap tradeoff:** Reddit caps pagination at 1000 items
to protect infrastructure. This is a conscious choice -- deep
historical access is pushed to the data licensing program.

---

## 14. Problem-Solution Map and Hidden Capabilities

### Problem: Find what real people think about a topic
**Solution:** Search relevant subreddits, sort by `top` with `t=month`,
extract top comments. Reddit comments are uniquely honest compared to
other platforms because anonymity + voting surfaces genuine opinions.

### Problem: Identify emerging trends before they go mainstream
**Solution:** Monitor `rising` in relevant subreddits. Rising posts have
unusual upvote velocity. Cross-reference with `new` to find posts gaining
traction faster than normal.

### Problem: Competitor intelligence
**Solution:** Search `site:competitor.com` in relevant subreddits. Reddit
users frequently discuss tools they use, including complaints and feature
requests. The comment section is more valuable than the post itself.

### Hidden capabilities
- **Lucene search syntax:** `title:"exact phrase"`, `selftext:keyword`,
  `author:username`, `flair:name`, `site:domain.com`, `nsfw:no`,
  `self:yes` (text posts only). Most users don't know these exist.
- **Multi-subreddit search:** `r/sub1+sub2+sub3/search` searches all
  three simultaneously.
- **Duplicate detection:** `/api/info?url=https://example.com` returns
  all submissions linking to a specific URL across all of Reddit.
- **Gilded filter:** `/r/subreddit/gilded` shows awarded content --
  proxy for "community thinks this is exceptionally valuable."
- **Wiki pages:** Many subreddits have extensive wikis accessible via
  API (`/r/sub/wiki/page`) containing curated community knowledge.
- **User overlap:** Analyzing subscribers of related subreddits reveals
  ICP demographics. A user active in r/entrepreneur + r/saas +
  r/indiehackers is a strong signal.

---

## 15. Operational Behavior and Edge Cases

### Eventual consistency
- New posts may take 1-5 minutes to appear in search results
- Score updates are near-real-time but fuzzy (anti-manipulation)
- Deleted content may still appear in search for minutes to hours
- Subreddit subscriber counts cache and update periodically

### Silent failures
- Private subreddits return 302 redirect to login, not 403
- Quarantined subreddits return 403 without the `quarantine` field
  unless you pass `?include_quarantined=true` header
- Banned users can still read (GET) but writes silently fail or
  return generic errors without "you are banned" message
- Shadowbanned users' content returns normally to them but 404s
  for everyone else

### Timezone handling
- All timestamps are UTC Unix floats (`created_utc`)
- Reddit's internal display uses the user's timezone setting
- API always returns UTC regardless of user settings
- Day boundaries for "today's top" are midnight UTC

### Unicode and encoding
- Reddit supports full Unicode in posts and comments
- `raw_json=1` prevents HTML entity encoding
- Emoji in titles/comments work but some old Reddit apps render
  them as squares
- Markdown is the native format -- `body` is Markdown, `body_html`
  is rendered HTML

### Concurrent access
- Multiple OAuth2 tokens can be used in parallel (each has its own
  100 req/min limit)
- Public JSON is tracked by IP, not by token
- Running multiple processes from one IP against public JSON will
  share the rate limit and hit 429s faster

---

## 16. Ecosystem Position and Composition

### Where Reddit sits in the data architecture
Reddit is a **signal source** -- it generates qualitative data about
what people think, want, and complain about. It is NOT a system of
record or a processing layer.

### Natural complements
- **OpenAI/Anthropic API** -- synthesize Reddit discussions into
  insights (the EOS pattern via last30days)
- **Notion/Airtable** -- store curated Reddit signals as structured data
- **Discord** -- relay relevant Reddit discussions to team channels
- **Apify** -- when Reddit rate limits are too restrictive, use Apify
  Reddit scrapers as a proxy layer

### Integration patterns that work well
- Reddit search -> LLM summarization -> structured insight storage
- Reddit monitoring -> Discord webhook alerts for keyword mentions
- Reddit thread enrichment -> engagement scoring for content strategy

### Anti-pattern integrations
- **Reddit as CRM source** -- Reddit usernames rarely map to real identities.
  Don't try to build lead lists from Reddit posters.
- **Reddit for content distribution** -- posting links to your own content
  triggers spam filters and community backlash. Reddit punishes self-promotion.
- **Reddit as real-time data** -- Reddit's API is not designed for sub-second
  latency. Use Twitter/X for real-time monitoring.

---

## 17. Trajectory and Evolution

### Where Reddit API is heading
- **Increased restriction:** The trend since 2023 is toward less free access,
  not more. Expect further tightening of public JSON endpoints.
- **Data licensing:** Reddit signed deals with Google and OpenAI for
  training data access. This is now a revenue stream they protect.
- **Developer Program:** Reddit launched a developer platform in 2024
  with more structured app review. Future apps may require approval.

### Features being de-emphasized
- **Pushshift/third-party archives:** Reddit actively shut down Pushshift
  and similar services. Historical data access is now Reddit-controlled.
- **Third-party clients:** The 2023 pricing change made third-party Reddit
  apps economically unviable. Reddit wants users in the official app.
- **RSS feeds:** Still work but receive no updates or documentation love.

### What's getting investment
- **Reddit's own AI features:** Reddit is building AI-powered search and
  summarization into the official product.
- **Developer platform:** Structured app development with official tools.
- **Ads API:** Reddit's advertising API is getting significant investment
  as they scale ad revenue post-IPO (March 2024).

### Build implications for EOS
- Public JSON endpoints may be restricted or require auth in the future.
  Plan for OAuth2 migration path.
- Don't depend on third-party Reddit data services -- they keep getting
  shut down.
- Reddit's own search improvements may eventually make external NLP
  less necessary, but currently Reddit search remains notoriously poor.

---

## 18. Conceptual Model and Solution Recipes

### Mental model: Reddit as structured human signal
Think of Reddit as a database of human opinions, organized by topic
(subreddit), ranked by consensus (votes), and enriched by debate
(comment threads). The API lets you query this database.

**Primitives:**
- Subreddit = topic namespace
- Submission = signal event (question, link, discussion)
- Comment = response/opinion with consensus score
- Score = crowd-validated relevance
- Time = recency filter

**Verbs:**
- Search = find signals by keyword
- List = browse signals by ranking algorithm
- Fetch = get full signal with responses
- Enrich = add real engagement data to a reference

### Recipe 1: ICP Pain Point Mining
```
1. Identify 3-5 subreddits where ICP congregates
   (r/entrepreneur, r/startups, r/saas, r/smallbusiness)
2. Search each for pain-point keywords:
   "struggling with", "frustrated", "anyone else", "help with"
3. Sort by top/month for validated pain points
4. For top 10 results, fetch full thread with comments
5. Extract top 5 comments from each -- these contain
   specific complaints, workarounds, and unmet needs
6. Feed to LLM: "Synthesize the top pain points from these
   discussions. Rank by frequency and emotional intensity."
```

### Recipe 2: Competitor Intelligence Dashboard
```
1. Search Reddit for competitor name + "review", "alternative",
   "vs", "switched from", "switched to"
2. Time filter: month (for recency)
3. Enrich each thread with engagement metrics
4. High upvote_ratio + high score = community consensus
5. Extract comment insights for sentiment analysis
6. Store in Notion with: competitor, sentiment, key_complaints,
   feature_requests, date_range
```

### Recipe 3: Content Topic Validation
```
1. Before creating content, search Reddit for the topic
2. Sort by top/month -- if high-scoring posts exist, topic is validated
3. Read top comments for angle differentiation
4. Check "new" for the topic -- if lots of recent posts with low scores,
   topic is saturated (many people posting, no one engaging)
5. Ideal: topic has engagement but few recent authoritative posts
```

### Recipe 4: Market Research Signal Capture
```
1. Define keyword list: product category + modifiers
   ("saas onboarding", "onboarding tool", "onboarding software")
2. Search across 10+ relevant subreddits
3. Filter: score > 5, num_comments > 3 (eliminates noise)
4. For qualifying posts, get thread + top 10 comments
5. Run through LLM for entity extraction:
   - Tools mentioned (competitor landscape)
   - Features requested (product roadmap input)
   - Price sensitivity signals
   - Buying triggers ("we switched when...")
```

### Recipe 5: Real-Time Discussion Monitoring
```
1. Set up PRAW streaming on target subreddits
2. Filter submissions by keywords
3. For matches: post to Discord webhook with title, score, URL
4. Schedule daily summary: top posts from monitored subs
5. Weekly: trend analysis of keyword frequency over time
```

---

## 19. Industry Expert and Cutting-Edge Usage

### AI + Reddit for market intelligence
The frontier pattern is Reddit-as-training-data for domain-specific intelligence.
Top practitioners use Reddit discussions to:
- Train sentiment classifiers on community reactions
- Build "voice of customer" datasets from subreddit comments
- Generate marketing copy that matches how the ICP actually talks
  (Reddit language is raw and authentic vs polished marketing speak)

### The "Reddit as focus group" pattern
Companies like Gong, Loom, and Notion monitor their brand mentions on Reddit
not just for sentiment but for feature prioritization. A Reddit complaint with
500 upvotes is a stronger signal than a support ticket -- it means hundreds of
people validated the pain point.

### Advanced search composition
Expert users combine Lucene operators for precision:
```
site:producthunt.com OR selftext:"product hunt" subreddit:startups
title:"vs" (competitor1 OR competitor2) self:yes
author:known_expert_username subreddit:relevant_sub
```

### Reddit + LLM synthesis pipeline
The most sophisticated pattern (which EOS approximates via last30days):
1. Broad search across relevant subreddits
2. Entity extraction from results (people, products, subreddits mentioned)
3. Targeted follow-up searches on extracted entities
4. Thread enrichment with real engagement data
5. LLM synthesis into structured insights
6. Storage in knowledge base for longitudinal analysis

This two-phase search-then-drill pattern catches signals that single-pass
keyword search misses entirely. The last30days skill implements this with
`search_subreddits()` in Phase 2 after Phase 1 entity extraction.

### Reddit data for content creation
Expert content creators mine Reddit for:
- Exact language their audience uses (for SEO and ad copy)
- Questions being asked repeatedly (content topic validation)
- Objections to their product category (for landing page copy)
- Success stories from users (for case study leads)

### The anonymity advantage
Reddit's anonymity produces qualitatively different data than LinkedIn,
Twitter, or public reviews. People share failures, real numbers, honest
opinions about tools, and genuine frustrations they would never post
under their real name. For market research, this is higher-fidelity
signal than any other social platform.

---

## EOS Usage Patterns

### Current: Public JSON via last30days
EOS accesses Reddit exclusively through the last30days skill's HTTP layer.
No PRAW, no OAuth2, no API key. Three functions handle all Reddit interaction:

1. `openai_reddit.search_subreddits()` -- Phase 2 supplemental search
2. `reddit_enrich.enrich_reddit_item()` -- engagement metric enrichment
3. `http.get_reddit_json()` -- low-level `.json` endpoint fetcher

### Rate limit handling
EOS uses fail-fast on 429: `RedditRateLimitError` propagates up and
the caller bails on remaining Reddit items. No retry loop -- the
research continues with data already collected.

### Data flow
```
OpenAI web_search (Phase 1) -> Reddit URLs discovered
  -> Entity extraction finds subreddit names
  -> search_subreddits() hits discovered subs (Phase 2)
  -> enrich_reddit_item() adds engagement metrics
  -> extract_comment_insights() pulls top comments
  -> LLM synthesizes into final research output
```

### Future: potential OAuth2 migration
If Reddit restricts public JSON endpoints, EOS would need:
1. Script app credentials in `eos_ai/.env`
2. PRAW or direct OAuth2 token management
3. Rate limit header tracking (currently not needed)
4. Token refresh handling (24h expiry for script apps)

## Gotchas

### WebSearch denied during research
This skill was researched from training data knowledge (through May 2025)
and extensive EOS codebase analysis. Reddit API is well-documented in
training data. Real-time verification of any 2026 API changes should
be done when WebSearch is available.

### Public JSON may be restricted without notice
Reddit has progressively tightened API access since 2023. The public
`.json` endpoints could be rate-limited further or require authentication
at any time. Monitor for increased 429 frequency as an early warning.

### PRAW not in requirements.txt
EOS does not currently use PRAW. If adding it, install with `pip install praw`
and add `praw==7.7.1` to requirements.txt. PRAW pulls in `websocket-client`
and `update-checker` as dependencies.
