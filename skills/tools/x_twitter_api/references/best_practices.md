# X (Twitter) API — Creator-Level Best Practices
Source: https://developer.x.com/en/docs/x-api
API Version: v2 (October 2022 — current)
SDK Version: tweepy 4.14+ / Bird v0.8.0 (vendored) / xAI Responses API
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## 1. Authentication

### Official X API v2 auth methods

**OAuth 2.0 App-Only (Bearer Token)**
- Scope: read-only endpoints (search, lookup, timelines, counts, streams)
- Single token, no user context
- Token does not expire (until regenerated)
- Header: `Authorization: Bearer {BEARER_TOKEN}`
- Obtain: Developer Portal > Project > Keys and Tokens > Bearer Token

**OAuth 2.0 Authorization Code Flow with PKCE**
- Scope: user-context operations (post, like, retweet, DM, follow)
- Access token expires in 2 hours
- Refresh token valid for 6 months (if `offline.access` scope requested)
- Scopes: `tweet.read`, `tweet.write`, `users.read`, `follows.read`,
  `follows.write`, `like.read`, `like.write`, `offline.access`, `space.read`,
  `mute.read`, `mute.write`, `block.read`, `block.write`, `bookmark.read`,
  `bookmark.write`, `list.read`, `list.write`, `dm.read`, `dm.write`
- Authorization URL: `https://twitter.com/i/oauth2/authorize`
- Token URL: `https://api.twitter.com/2/oauth2/token`
- Revoke URL: `https://api.twitter.com/2/oauth2/revoke`

**OAuth 1.0a (legacy, still supported)**
- Four credentials: consumer key, consumer secret, access token, access token secret
- User-context access, no expiry on access tokens
- Required for some legacy v1.1 endpoints still in use
- Signature: HMAC-SHA1

### EOS auth (Bird + xAI)
- Bird: browser cookies (automatic extraction) or `AUTH_TOKEN` env var
- xAI: `XAI_API_KEY` as bearer token to `https://api.x.ai/v1/responses`
- Both stored in env vars, never hardcoded

### Env var locations in EOS
```
AUTH_TOKEN=              # .agents/skills/last30days/.env or system env
XAI_API_KEY=             # .agents/skills/last30days/.env or system env
# Official API (not used by EOS, reference only):
TWITTER_BEARER_TOKEN=    # Would go in eos_ai/.env if ever used
TWITTER_API_KEY=         # Consumer key
TWITTER_API_SECRET=      # Consumer secret
TWITTER_ACCESS_TOKEN=    # OAuth 1.0a access token
TWITTER_ACCESS_SECRET=   # OAuth 1.0a access token secret
```

---

## 2. Core Operations with Exact Signatures

### Official X API v2 endpoints (reference)

**Search recent tweets (last 7 days)**
```
GET https://api.twitter.com/2/tweets/search/recent
```
```python
# tweepy
client.search_recent_tweets(
    query: str,                    # required — up to 512 chars (Basic), 1024 (Pro/Enterprise)
    start_time: datetime = None,   # optional — oldest UTC datetime (YYYY-MM-DDTHH:mm:ssZ)
    end_time: datetime = None,     # optional — newest UTC datetime
    since_id: str = None,          # optional — tweet ID lower bound (exclusive)
    until_id: str = None,          # optional — tweet ID upper bound (exclusive)
    max_results: int = 10,         # optional — 10-100 per request
    next_token: str = None,        # optional — pagination token
    sort_order: str = None,        # optional — "recency" or "relevancy"
    tweet_fields: list = None,     # optional — created_at, public_metrics, etc.
    expansions: list = None,       # optional — author_id, referenced_tweets.id, etc.
    user_fields: list = None,      # optional — username, public_metrics, etc.
    media_fields: list = None,     # optional — url, preview_image_url, etc.
    place_fields: list = None,     # optional — full_name, country, etc.
    poll_fields: list = None,      # optional — options, voting_status, etc.
)
# Returns: tweepy.Response with .data (list[Tweet]), .includes, .meta, .errors
# .meta = {'newest_id': str, 'oldest_id': str, 'result_count': int, 'next_token': str|None}
```

**Search full archive (all time)**
```
GET https://api.twitter.com/2/tweets/search/all
```
```python
# tweepy — Pro tier ($5,000/month) or Enterprise only
client.search_all_tweets(
    query: str,                    # required — up to 1024 chars
    start_time: datetime = None,   # optional — as early as March 2006
    end_time: datetime = None,
    since_id: str = None,
    until_id: str = None,
    max_results: int = 10,         # 10-500 per request
    next_token: str = None,
    sort_order: str = None,
    tweet_fields: list = None,
    expansions: list = None,
    user_fields: list = None,
    media_fields: list = None,
    place_fields: list = None,
    poll_fields: list = None,
)
# Returns: same Response shape as search_recent_tweets
```

**User lookup by username**
```
GET https://api.twitter.com/2/users/by/username/:username
```
```python
client.get_user(
    id: int = None,                # user ID — mutually exclusive with username
    username: str = None,          # screen name — mutually exclusive with id
    user_fields: list = None,      # created_at, description, public_metrics, etc.
    expansions: list = None,       # pinned_tweet_id
    tweet_fields: list = None,
)
# Returns: Response with .data = User object
# User: id, name, username, created_at, description, public_metrics
#   public_metrics: {followers_count, following_count, tweet_count, listed_count}
```

**Batch user lookup**
```
GET https://api.twitter.com/2/users
GET https://api.twitter.com/2/users/by
```
```python
client.get_users(
    ids: list[int] = None,         # up to 100 user IDs
    usernames: list[str] = None,   # up to 100 usernames
    user_fields: list = None,
    expansions: list = None,
    tweet_fields: list = None,
)
```

**Single tweet lookup**
```
GET https://api.twitter.com/2/tweets/:id
```
```python
client.get_tweet(
    id: int,                       # required — tweet ID
    tweet_fields: list = None,
    expansions: list = None,
    user_fields: list = None,
    media_fields: list = None,
    place_fields: list = None,
    poll_fields: list = None,
)
```

**Post a tweet**
```
POST https://api.twitter.com/2/tweets
```
```python
client.create_tweet(
    text: str = None,              # up to 280 chars (or 25,000 for long-form)
    in_reply_to_tweet_id: int = None,
    quote_tweet_id: int = None,
    poll_options: list = None,     # 2-4 options
    poll_duration_minutes: int = None,
    media_ids: list = None,        # up to 4 images or 1 video
    reply_settings: str = None,    # "mentionedUsers" or "following"
    direct_message_deep_link: str = None,
)
# Returns: Response with .data = {'id': str, 'text': str}
```

### EOS Bird GraphQL signatures

```python
# bird_x.py
search_x(
    topic: str,          # search topic (auto-simplified to 2-3 keywords)
    from_date: str,      # YYYY-MM-DD
    to_date: str,        # YYYY-MM-DD (unused but kept for API compat)
    depth: str = "default",  # "quick"|"default"|"deep"
) -> Dict[str, Any]
# Returns: raw Bird JSON or {"error": str, "items": []}

search_handles(
    handles: List[str],  # X handles without @
    topic: str,          # core subject
    from_date: str,      # YYYY-MM-DD
    count_per: int = 5,  # results per handle
) -> List[Dict[str, Any]]
# Returns: list of normalized item dicts

parse_bird_response(response: Dict[str, Any]) -> List[Dict[str, Any]]
# Returns: list of {id, text, url, author_handle, date, engagement, why_relevant, relevance}
```

### EOS xAI signatures

```python
# xai_x.py
search_x(
    api_key: str,        # xAI API key
    model: str,          # e.g. "grok-3-mini"
    topic: str,
    from_date: str,      # YYYY-MM-DD
    to_date: str,        # YYYY-MM-DD
    depth: str = "default",
    mock_response: Optional[Dict] = None,
) -> Dict[str, Any]
# Returns: raw xAI Responses API JSON

parse_x_response(response: Dict[str, Any]) -> List[Dict[str, Any]]
# Returns: list of normalized item dicts (same shape as Bird output)
```

---

## 3. Pagination Patterns

### X API v2 pagination (token-based)
All list/search endpoints use token-based pagination:

```python
# Fetch all pages of recent search results
all_tweets = []
next_token = None

while True:
    response = client.search_recent_tweets(
        query="AI agents",
        max_results=100,
        next_token=next_token,
        tweet_fields=["created_at", "public_metrics"],
    )
    if response.data:
        all_tweets.extend(response.data)
    
    next_token = response.meta.get("next_token") if response.meta else None
    if not next_token:
        break
```

- Response includes `meta.next_token` (string or None)
- Pass `next_token` to next request
- `meta.result_count` tells how many in current page
- Max per page: 100 for search/recent, 500 for search/all, 100 for timelines
- No offset-based pagination — only forward cursoring via tokens
- `since_id` and `until_id` provide ID-based boundaries (not substitutes for pagination)

### Bird pagination
Bird does not paginate. It requests a fixed `--count` of results in a single
call. The count is determined by depth config (12/30/60). No cursor support.

### xAI pagination
xAI does not paginate. It returns all results in a single LLM response.
The min/max item count is specified in the prompt. No cursor support.

---

## 4. Rate Limits

### X API v2 rate limits by tier

**Free tier ($0/month)**
| Endpoint | Limit |
|---|---|
| POST /2/tweets | 1,500 tweets/month |
| DELETE /2/tweets/:id | 50 per 15 min (app) |
| All read endpoints | NOT AVAILABLE |

**Basic tier ($200/month)**
| Endpoint | Limit per 15 min |
|---|---|
| GET /2/tweets/search/recent | 60 (app), 60 (user) |
| GET /2/tweets/:id | 300 (app), 900 (user) |
| GET /2/users/by/username/:username | 300 (app), 900 (user) |
| GET /2/users/:id | 300 (app), 900 (user) |
| GET /2/users/:id/tweets | 1,500 (app), 900 (user) |
| POST /2/tweets | 100 per 24 hours (user) |
| Monthly tweet read cap | 10,000 tweets/month |

**Pro tier ($5,000/month)**
| Endpoint | Limit per 15 min |
|---|---|
| GET /2/tweets/search/recent | 300 (app), 300 (user) |
| GET /2/tweets/search/all | 300 (app), 1 (user) |
| GET /2/tweets/:id | 300 (app), 900 (user) |
| GET /2/users/by/username/:username | 300 (app), 900 (user) |
| POST /2/tweets | 100 per 24 hours (user) |
| Monthly tweet read cap | 1,000,000 tweets/month |

**Enterprise (custom pricing)**
- All endpoints available
- Custom rate limits negotiated per contract
- Full-archive search included
- Monthly tweet cap: 10,000,000+ tweets/month

### Rate limit headers
```
x-rate-limit-limit: 300        # max requests in window
x-rate-limit-remaining: 299    # requests left in window
x-rate-limit-reset: 1714000000 # UTC epoch when window resets
```

### Bird rate limits
No formal rate limits — uses browser session. However, aggressive automated
searching triggers X's anti-bot detection. EOS uses single sequential requests
with natural timing. No rate limit headers available.

### xAI rate limits
Standard xAI API limits apply (token-based, not X-specific). The `x_search`
tool within xAI has no separately documented rate limit.

---

## 5. Error Codes and Recovery

### X API v2 HTTP status codes
| Code | Meaning | Retryable | Recovery |
|---|---|---|---|
| 200 | Success | n/a | n/a |
| 201 | Created (tweet posted) | n/a | n/a |
| 400 | Bad request (invalid params) | No | Fix query/params |
| 401 | Unauthorized (bad/expired token) | No | Refresh token or regenerate |
| 403 | Forbidden (insufficient tier/scope) | No | Upgrade tier or add scope |
| 404 | Not found (deleted tweet/user) | No | Handle gracefully |
| 429 | Rate limited | Yes | Wait for `x-rate-limit-reset` epoch |
| 500 | Internal server error | Yes | Exponential backoff, max 3 retries |
| 503 | Service unavailable | Yes | Exponential backoff |

### X API v2 error response shape
```json
{
  "errors": [
    {
      "message": "Invalid Request: One or more parameters to your request was invalid.",
      "parameters": { "query": ["too long"] },
      "type": "https://api.twitter.com/2/problems/invalid-request",
      "title": "Invalid Request",
      "detail": "Query length exceeds maximum (512 characters)",
      "status": 400
    }
  ]
}
```

### Common non-obvious errors
- **403 with valid token** — your tier doesn't include this endpoint. Free tier
  gets 403 on all read endpoints. Basic gets 403 on `search/all`.
- **401 after working fine** — OAuth 2.0 PKCE access token expired (2-hour lifetime).
  Must use refresh token to get new access token.
- **200 with empty data** — not an error. Query matched zero tweets.
  `response.data` is None (not empty list) in tweepy.
- **400 "query too long"** — Basic tier limited to 512 char queries,
  Pro allows 1024. Trim operators or split queries.

### Bird error handling
Bird errors surface as `{"error": "message", "items": []}`. Common:
- Timeout after 30-60s — search query too broad or X GraphQL slow
- "Bird search failed" — cookie expired or X blocked the request
- Invalid JSON — X returned HTML error page instead of JSON

### xAI error handling
xAI errors appear in `response["error"]` dict. Common:
- Authentication error — invalid or expired `XAI_API_KEY`
- Rate limit — xAI token/request limits exceeded
- Empty output — Grok couldn't find relevant posts (not an error)

---

## 6. SDK Idioms

### tweepy v4 (official Python SDK for X API v2)
```python
import tweepy

# App-only auth (bearer token, read-only)
client = tweepy.Client(bearer_token="BEARER_TOKEN")

# User auth (OAuth 2.0 PKCE)
client = tweepy.Client(
    bearer_token="BEARER_TOKEN",
    access_token="ACCESS_TOKEN",
    access_token_secret="ACCESS_TOKEN_SECRET",
    consumer_key="API_KEY",
    consumer_secret="API_SECRET",
)

# OAuth 2.0 PKCE flow handler
oauth2_handler = tweepy.OAuth2UserHandler(
    client_id="CLIENT_ID",
    redirect_uri="https://your-app.com/callback",
    scope=["tweet.read", "tweet.write", "users.read", "offline.access"],
    client_secret="CLIENT_SECRET",  # confidential clients only
)
auth_url = oauth2_handler.get_authorization_url()
# After user authorizes, exchange code for tokens:
tokens = oauth2_handler.fetch_token(response_url)
# tokens = {'access_token': ..., 'refresh_token': ..., 'expires_at': ...}
```

### tweepy response handling
```python
response = client.search_recent_tweets(query="test", tweet_fields=["public_metrics"])

# response.data is None if no results (NOT empty list)
if response.data:
    for tweet in response.data:
        print(tweet.id, tweet.text, tweet.public_metrics)

# Expanded objects in response.includes
if response.includes and "users" in response.includes:
    users = {u.id: u for u in response.includes["users"]}

# Errors for individual items (partial failures)
if response.errors:
    for error in response.errors:
        print(error["detail"])
```

### Bird SDK idiom (EOS)
```python
from lib.bird_x import search_x, parse_bird_response, is_bird_authenticated

# Always check auth before searching
if not is_bird_authenticated():
    print("Bird not authenticated — skipping X search")
else:
    response = search_x("AI agents", "2026-03-01", "2026-04-01")
    items = parse_bird_response(response)
```

### xAI SDK idiom (EOS)
```python
from lib.xai_x import search_x, parse_x_response
from lib import http  # EOS HTTP helper

response = search_x(
    api_key=config["XAI_API_KEY"],
    model="grok-3-mini",
    topic="topic",
    from_date="2026-03-01",
    to_date="2026-04-01",
)
items = parse_x_response(response)
```

---

## 7. Anti-Patterns

### Anti-pattern 1: Assuming response.data is always a list
```python
# WRONG
for tweet in response.data:  # TypeError if None
    print(tweet.text)

# CORRECT
if response.data:
    for tweet in response.data:
        print(tweet.text)
```

### Anti-pattern 2: Passing verbose queries to Bird search
```python
# WRONG — X GraphQL does literal AND matching, all words must appear
search_x("what are the best AI agent frameworks for startups in 2026", ...)
# Returns 0 results

# CORRECT — Bird auto-simplifies, but explicit is better
search_x("AI agent frameworks", ...)
```

### Anti-pattern 3: Using free tier for read operations
```python
# WRONG — Free tier has no read access
client = tweepy.Client(bearer_token=os.getenv("TWITTER_BEARER_TOKEN"))
client.search_recent_tweets(query="test")
# Returns 403 Forbidden

# CORRECT — Use Bird (free) or upgrade to Basic ($200/month)
```

### Anti-pattern 4: Not requesting expansions for related data
```python
# WRONG — author_id is an opaque number without expansion
response = client.search_recent_tweets(query="test")
# tweet.author_id = "123456" but no way to get username

# CORRECT — request expansions and user_fields
response = client.search_recent_tweets(
    query="test",
    expansions=["author_id"],
    user_fields=["username", "public_metrics"],
)
users = {u.id: u for u in response.includes.get("users", [])}
for tweet in response.data:
    author = users.get(tweet.author_id)
    print(f"@{author.username}: {tweet.text}")
```

### Anti-pattern 5: Ignoring the monthly tweet read cap
```python
# WRONG — paging through all results without counting
all_tweets = []
next_token = "start"
while next_token:
    resp = client.search_recent_tweets(query="AI", max_results=100, next_token=next_token)
    all_tweets.extend(resp.data or [])
    next_token = resp.meta.get("next_token")
# Could burn through 10,000 monthly cap in minutes on Basic tier

# CORRECT — track cumulative count, stop at budget
MAX_TWEETS = 5000  # Leave headroom
total = 0
while next_token and total < MAX_TWEETS:
    resp = client.search_recent_tweets(query="AI", max_results=100, next_token=next_token)
    batch = resp.data or []
    all_tweets.extend(batch)
    total += len(batch)
    next_token = resp.meta.get("next_token")
```

### Anti-pattern 6: Not handling xAI non-JSON output
```python
# WRONG — assuming xAI always returns clean JSON
data = json.loads(response["output"][0]["content"][0]["text"])

# CORRECT — regex extract JSON from potentially wrapped output
json_match = re.search(r'\{[\s\S]*"items"[\s\S]*\}', output_text)
if json_match:
    try:
        data = json.loads(json_match.group())
    except json.JSONDecodeError:
        data = {"items": []}
```

---

## 8. Data Model

### Tweet object (X API v2)
```
Tweet
  |-- id: str (snowflake ID)
  |-- text: str (up to 280 chars, or 25,000 for long-form)
  |-- author_id: str (references User.id)
  |-- created_at: datetime (ISO 8601)
  |-- conversation_id: str (root tweet of thread)
  |-- in_reply_to_user_id: str
  |-- referenced_tweets: [{type: "replied_to"|"quoted"|"retweeted", id: str}]
  |-- public_metrics: {retweet_count, reply_count, like_count, quote_count, impression_count}
  |-- entities: {urls: [], mentions: [], hashtags: [], cashtags: [], annotations: []}
  |-- attachments: {media_keys: [], poll_ids: []}
  |-- geo: {place_id: str, coordinates: {type, coordinates}}
  |-- lang: str (BCP47)
  |-- source: str (app name)
  |-- edit_history_tweet_ids: [str]
  +-- possibly_sensitive: bool
```

### User object
```
User
  |-- id: str (snowflake ID, immutable)
  |-- name: str (display name, mutable)
  |-- username: str (handle without @, mutable)
  |-- created_at: datetime
  |-- description: str (bio)
  |-- profile_image_url: str
  |-- public_metrics: {followers_count, following_count, tweet_count, listed_count}
  |-- verified: bool (legacy blue check — deprecated)
  |-- verified_type: str ("blue", "business", "government", or None)
  |-- protected: bool (private account)
  |-- url: str (profile URL)
  +-- pinned_tweet_id: str
```

### Entity relationships
```
Tweet --author_id--> User
Tweet --referenced_tweets--> Tweet (reply, quote, retweet)
Tweet --conversation_id--> Tweet (thread root)
Tweet --attachments.media_keys--> Media
Tweet --attachments.poll_ids--> Poll
Tweet --entities.mentions--> User (by username)
User --pinned_tweet_id--> Tweet
List --owner_id--> User
List --member--> User (many-to-many)
Space --host_ids--> User
Space --speaker_ids--> User
```

### EOS normalized item (Bird + xAI output)
```
Item
  |-- id: str ("X1", "X2", ...)
  |-- text: str (truncated to 500 chars)
  |-- url: str (https://x.com/{handle}/status/{id})
  |-- author_handle: str (without @)
  |-- date: str|None (YYYY-MM-DD)
  |-- engagement: {likes, reposts, replies, quotes} | None
  |-- why_relevant: str (xAI only, empty for Bird)
  +-- relevance: float (0.0-1.0, default 0.7 for Bird)
```

---

## 9. Webhooks and Events

### X API v2: Account Activity API (Premium/Enterprise only)
- Webhook-based delivery of account events: tweets, DMs, follows, likes, mentions
- Register webhook URL via `POST /1.1/account_activity/all/:env_name/webhooks.json`
- X sends CRC challenge (HMAC-SHA256 of `crc_token` with consumer secret)
- Must respond within 3 seconds with `{"response_token": "sha256=..."}`
- Events delivered as POST requests with JSON payload
- Retry: 3 attempts with exponential backoff (5 min, 10 min, 20 min)
- Delivery: at-least-once (may receive duplicates)

### X API v2: Filtered Stream (alternative to webhooks)
```python
# Real-time tweet delivery via streaming connection
stream_rules = client.get_stream_rules()
client.add_stream_rules(tweepy.StreamRule(value="AI agents lang:en", tag="ai"))

# Streaming client (subclass StreamingClient)
class MyStream(tweepy.StreamingClient):
    def on_tweet(self, tweet):
        print(tweet.text)
    def on_errors(self, errors):
        print(errors)

stream = MyStream(bearer_token="BEARER_TOKEN")
stream.filter(
    tweet_fields=["created_at", "public_metrics"],
    expansions=["author_id"],
)
```

- Up to 5 rules on Basic tier, 25 on Pro, 1,000 on Enterprise
- Rules use X query syntax (operators, boolean logic)
- Connection: long-lived HTTPS streaming (chunked transfer encoding)
- Must reconnect on disconnect (exponential backoff)
- Only 1 connection per app on Basic/Pro

### EOS webhook usage
EOS does not use X webhooks or filtered stream. All X data access is pull-based
(Bird search or xAI search on demand). Mark as not currently applicable for EOS.

---

## 10. Limits

### X API v2 hard limits
| Limit | Value |
|---|---|
| Tweet text length | 280 chars (standard), 25,000 (X Premium subscribers) |
| Query length (search) | 512 chars (Basic), 1,024 chars (Pro/Enterprise) |
| max_results per request (search/recent) | 100 |
| max_results per request (search/all) | 500 |
| max_results per request (timeline) | 100 |
| Batch tweet lookup | 100 tweet IDs per request |
| Batch user lookup | 100 user IDs or usernames per request |
| Media per tweet | 4 images OR 1 video OR 1 GIF |
| Poll options | 2-4 per poll |
| Poll duration | 5 minutes to 7 days |
| Stream rules (Basic) | 5 rules |
| Stream rules (Pro) | 25 rules |
| Stream rules (Enterprise) | 1,000 rules |
| Stream rule length | 512 chars (Basic), 1,024 chars (Pro/Enterprise) |
| Lists per user | 1,000 owned |
| List members | 5,000 per list |
| DM text length | 10,000 chars |
| Monthly tweet read cap (Basic) | 10,000 tweets |
| Monthly tweet read cap (Pro) | 1,000,000 tweets |
| Monthly tweet post cap (Free) | 1,500 tweets |

### Bird limits
| Limit | Value |
|---|---|
| Results per search (quick) | 12 |
| Results per search (default) | 30 |
| Results per search (deep) | 60 |
| Results per handle search | 5 (default) |
| Search timeout (quick) | 30 seconds |
| Search timeout (default) | 45 seconds |
| Search timeout (deep) | 60 seconds |
| Query auto-simplification | 3 words max |
| Text truncation | 500 chars per item |

### xAI limits
| Limit | Value |
|---|---|
| Items per search (quick) | 8-12 |
| Items per search (default) | 20-30 |
| Items per search (deep) | 40-60 |
| Search timeout (quick) | 90 seconds |
| Search timeout (default) | 120 seconds |
| Search timeout (deep) | 180 seconds |
| Text truncation | 500 chars per item |

---

## 11. Cost Model

### X API v2 pricing (as of 2025)
| Tier | Monthly cost | Read access | Write access | Key limits |
|---|---|---|---|---|
| Free | $0 | None | 1,500 tweets/month post, delete only | No search, no lookup |
| Basic | $200 | 10,000 tweets/month read | 3,000 tweets/month post | 2 app environments |
| Pro | $5,000 | 1,000,000 tweets/month read | 300,000 tweets/month post | Full-archive search |
| Enterprise | Custom ($42k-$210k+) | 10M-50M+ tweets/month | Custom | Dedicated support |

### Cost per operation (Basic tier)
- 1 search request (100 tweets) = 100 of your 10,000 monthly read cap
- 100 search requests = entire monthly cap exhausted
- Effectively $0.02 per tweet read on Basic
- On Pro: $0.005 per tweet read

### EOS cost model
- **Bird**: $0. Uses browser cookies. No API charges. Cost = Node.js runtime only.
- **xAI**: Per-token pricing via xAI API. `grok-3-mini` is the cheapest model.
  Approximate: $0.01-0.05 per search depending on depth and output length.
- **Total EOS X cost**: Near-zero when Bird is authenticated. xAI fallback only.

### Cost monitoring
- X API: Developer Portal > Dashboard > Usage tab
- xAI: console.x.ai > Usage
- EOS: no automated X cost tracking. Bird usage is free. xAI usage tracked
  via general xAI API monitoring.

---

## 12. Version Pinning

### X API versions
- **v2** — current (launched October 2022). All new features here.
- **v1.1** — legacy. Most endpoints deprecated but some still required
  (media upload, Account Activity webhooks). No date announced for shutdown.
- API version is in the URL path: `/2/tweets/search/recent` vs `/1.1/statuses/lookup.json`
- No header-based versioning. No way to pin beyond URL path.

### SDK versions
- **tweepy**: v4.14+ for full X API v2 support. Pin in requirements:
  `tweepy>=4.14,<5.0`. Major breaking changes between tweepy 3.x (v1.1 only)
  and 4.x (v2 support).
- **Bird**: v0.8.0 vendored in EOS. Pinned by vendoring (no external dependency).
  Located at `/.agents/skills/last30days/scripts/lib/vendor/bird-search/`.
- **xAI API**: version in URL path (`/v1/responses`). No SDK — raw HTTP.

### Deprecation timeline
- v1.1 Standard endpoints: deprecated, no shutdown date announced
- v1.1 Premium search: replaced by v2 search (Basic/Pro tiers)
- v1.1 Account Activity: still only available in v1.1
- labs/v2 early access endpoints: graduated to production v2
- `statuses/filter` (v1.1 streaming): replaced by v2 filtered stream

### Known upcoming changes
- X continues to restrict free-tier access. Pricing has only increased since 2023.
- GraphQL internal API (used by Bird) changes without notice — breakage possible.
- xAI regularly adds new models (Grok iterations) that improve x_search quality.

---

# Tier 2 — Creator Intelligence

## 13. Design Intent and Tradeoffs

X (Twitter) API v2 was redesigned under Jack Dorsey's tenure to fix the
chaotic v1.1 endpoint structure. The core design philosophy:

**Object-centric with field selection.** Instead of v1.1's endpoint-per-action
approach (different endpoints returning different subsets of the same object),
v2 uses a consistent pattern: request an object type, specify which fields you
want via `tweet_fields`, `user_fields`, etc. This is closer to GraphQL thinking
applied to REST.

**Expansions replace nested objects.** In v1.1, a tweet response included the
full user object inline. In v2, you get `author_id` and must request
`expansions=["author_id"]` to get the user object in `includes`. This reduces
payload size but increases code complexity.

**Tradeoff: consistency over convenience.** Every v2 endpoint follows the same
response pattern (`data`, `includes`, `meta`, `errors`), but simple operations
that were one call in v1.1 (get tweet with author info) now require understanding
expansions and field selection.

**Post-acquisition shift (Elon Musk, October 2022).** The API was repositioned
from a developer platform to a revenue product. Free tier gutted to write-only.
Read access priced at $200/month minimum. This fundamentally changed the
ecosystem — most small developers, researchers, and bots migrated to scrapers,
Mastodon, or Bluesky. The API is now primarily used by enterprises and
funded companies.

**What X API is NOT:** It is not a data warehouse. The 7-day search window on
Basic, the 10,000 tweet/month read cap, and the $5,000 price for full-archive
make it clear: X wants you to pay significantly for historical data access.
Real-time (filtered stream) is the intended use case for the lower tiers.

---

## 14. Problem-Solution Map and Hidden Capabilities

### Problem: Monitor brand mentions in real-time
**Solution:** Filtered stream with rules matching brand keywords. More efficient
than polling search endpoint. Single persistent connection, instant delivery.
On Basic tier, limited to 5 rules — combine with OR operators.

### Problem: Find influencers in a niche
**Solution:** Search for niche keywords, then use the `public_metrics` on
expanded author objects to sort by `followers_count`. The user lookup endpoint
returns `tweet_count` and `listed_count` which are better engagement indicators
than raw follower count.

### Problem: Track conversation threads
**Solution:** Use `conversation_id` field on tweets. All tweets in a thread share
the same `conversation_id` (the root tweet's ID). Search with
`conversation_id:{id}` operator to get the full thread.

### Problem: Free X data access for research/monitoring
**Solution (EOS approach):** Use Bird GraphQL (browser cookies) for keyword search.
Use xAI API for semantic search (Grok with x_search tool). Avoid the official
API entirely unless posting tweets is required.

### Hidden capabilities
- **Tweet counts endpoint** (`/2/tweets/counts/recent`) — returns volume over time
  without consuming tweet read cap. Useful for trend detection before committing
  to full search.
- **Conversation threading** via `conversation_id` operator — not prominently
  documented but allows reconstructing entire threads.
- **Annotation entities** — tweets are auto-annotated with entity types
  (person, place, product, organization) and confidence scores.
  Useful for NER without running your own model.
- **Context annotations** — domain/entity classification (e.g., "Technology",
  "Brand:Tesla"). Up to 30 domains. Available in `tweet_fields`.
- **Edit history** — `edit_history_tweet_ids` shows all versions of an edited tweet.
  Can detect if content was modified after engagement was gained.

---

## 15. Operational Behavior and Edge Cases

### Eventual consistency
- Tweet search index has a 10-30 second delay after posting. A tweet created
  via API won't appear in search results immediately.
- `public_metrics` are cached and may lag by minutes. Real-time counts are
  not available via API.
- Deleted tweets may appear in search results for up to 15 minutes after deletion.

### Snowflake ID ordering
- Tweet IDs are Twitter Snowflake IDs (64-bit integers). They are roughly
  time-ordered but NOT strictly sequential. Two tweets created at the same
  millisecond may have different IDs. Using `since_id`/`until_id` is reliable
  for pagination but not for exact time filtering.

### Protected (private) accounts
- Tweets from protected accounts never appear in search results.
- User lookup returns the user but `public_metrics` may be zeroed.
- Following relationships with protected accounts require user-context auth.

### Retweet vs quote tweet behavior
- Retweets are separate tweet objects with `referenced_tweets: [{type: "retweeted"}]`.
  The `text` field contains `RT @username: ...` truncated at 280 chars.
- `-is:retweet` operator excludes retweets from search. Almost always wanted.
- Quote tweets include the full text of the quoting tweet. The quoted tweet
  must be fetched separately via expansion.

### Unicode and emoji handling
- Tweet length is measured in Unicode code points, not bytes.
- URLs always count as exactly 23 characters regardless of actual length
  (t.co shortening).
- Emoji count as 1-2 characters depending on the emoji (some are composed
  of multiple code points with ZWJ).

### Bird-specific edge cases
- Browser cookie sessions have variable lifetimes. Safari cookies tend to last
  longer than Chrome. Firefox profiles in containers work well for persistent auth.
- X's GraphQL schema changes without notice. Bird v0.8.0 handles known response
  formats but new fields or restructured responses will be silently ignored
  (not crash, but missing data).
- Rate limiting on GraphQL is IP-based and opaque. Heavy usage from a single VPS
  IP may trigger soft blocks (responses succeed but return fewer results).

### xAI-specific edge cases
- Grok's x_search tool may return tweets older than `from_date` if it considers
  them relevant. The date filter is a hint, not a hard constraint.
- Engagement numbers from xAI are LLM-estimated, not API-sourced. They may be
  inaccurate, especially for smaller accounts.
- If Grok can't find relevant posts, it may fabricate plausible-looking tweets
  rather than returning empty results. Validate URLs before trusting content.

---

## 16. Ecosystem Position and Composition

### Where X API sits
X is a **social signal source** — not a system of record, not a processing layer.
Data flows FROM X into other systems (CRM, analytics, content pipeline).
Very rarely does data flow INTO X via API (automated posting, bot replies).

### Natural complements
- **Apify** — scraping fallback when API is too expensive or limited.
  Actors: `apify/twitter-scraper`, `quacker/twitter-scraper`.
- **xAI** — Grok models have native X data access via `x_search` tool.
  Semantic search vs. keyword search.
- **Brave Search / Perplexity** — exclude x.com from web search results
  (EOS already does this) and use dedicated X search for social data.
- **Discord/Slack** — post X discoveries to team channels for awareness.
- **Notion** — store curated X finds as database items for reference.
- **CRM (HubSpot, Neon)** — attach social signals to contact records.

### Integration anti-patterns
- **X API + Zapier for high-volume monitoring** — Zapier polling + API rate limits
  = expensive and unreliable. Use filtered stream or Bird instead.
- **X API for historical research on Basic tier** — 7-day window and 10K cap
  make this impractical. Use Bird or Apify for historical data.
- **Storing raw tweet JSON long-term** — X Developer Agreement requires deleting
  tweets from your storage if they're deleted on X ("content compliance").
  Store tweet IDs and re-fetch, or accept compliance risk.

### EOS ecosystem position
```
Bird (free) ──┐
              ├──> Normalized Items ──> /last30days ──> Research Reports
xAI (paid) ──┘                                         ──> ICP Signals
                                                        ──> Discord Alerts
```

---

## 17. Trajectory and Evolution

### Where X API is heading (2025-2026)
- **Pricing only goes up.** Free tier was gutted in 2023. Basic went from $100 to $200.
  No indication of price reduction.
- **Enterprise focus.** X is positioning the API as an enterprise product.
  Self-serve tiers are deliberately hostile to small developers.
- **xAI integration deepening.** Grok models gaining better real-time X access.
  Long-term, xAI may become the preferred programmatic access path for X data.
- **GraphQL internal API instability.** Bird and similar scrapers depend on internal
  endpoints that X can change or break at any time. Not a stable foundation
  for mission-critical features.

### Deprecation signals
- v1.1 Premium search (30-day and full-archive) — replaced by v2 search tiers.
  Still functional but no longer documented prominently.
- v1.1 Standard endpoints — deprecated in docs, still working. No shutdown date.
- Free tier read access — gone. Not coming back.
- Academic Research tier — eliminated in 2023. Was the best value ($0 for
  10M tweets/month full-archive).

### What to build on
- **Safe:** Bird for non-critical research (free, works today, replaceable).
- **Safe:** xAI for semantic X search (paid, stable API, improving models).
- **Risky:** Official X API v2 at $200/month for features Bird covers for free.
- **Avoid:** Building features that depend on v1.1 endpoints.
- **Avoid:** Relying on GraphQL internal API for production-critical features.

---

## 18. Conceptual Model and Solution Recipes

### Mental model: X as a signal river
Think of X as a continuous river of signals. You can:
1. **Dip in** — search for what's flowing now (search/recent, Bird)
2. **Set a net** — catch specific patterns in real-time (filtered stream)
3. **Examine a fish** — look at one tweet/user in detail (lookup endpoints)
4. **Count the fish** — measure volume without reading content (counts endpoint)
5. **Drop a lure** — post content and see what bites (create tweet, monitor engagement)

### Recipe 1: Competitive intelligence monitoring
```
1. Identify competitor X handles
2. bird_x.search_handles(handles, topic, from_date) — daily cron
3. Parse items, filter by engagement > threshold
4. Post summary to Discord #competitive-intel channel
5. Store notable items in Neon for trend tracking
```

### Recipe 2: ICP signal detection on X
```
1. Define ICP pain-point keywords (from icp_signal_detection skill)
2. bird_x.search_x(pain_keywords, last_7_days) — daily
3. Filter: engagement.replies > 5 (active discussion)
4. Score relevance against ICP profile
5. Route high-scoring signals to outreach queue
6. Craft contextual reply (reference their pain point)
```

### Recipe 3: Trend validation before content creation
```
1. Pick candidate content topic
2. bird_x.search_x(topic, last_30_days, depth="deep")
3. Count results — if < 5, topic has low conversation volume
4. If > 20, examine top items for angles already covered
5. Use xai_x for semantic analysis: "What angles are NOT covered?"
6. Create content filling the identified gap
```

### Recipe 4: Social proof aggregation
```
1. Search for brand mentions: bird_x.search_x(brand_name, last_30_days)
2. Filter for positive sentiment (engagement ratio, text analysis)
3. Compile top 5-10 mentions as social proof
4. Format for website testimonials section or pitch deck
5. Re-verify URLs are still live before publishing
```

### Recipe 5: Event/launch monitoring
```
1. Set Bird search for event hashtag + brand names
2. Run every 30 minutes during event window
3. Surface any mention of your brand by influencers (followers > 10K)
4. Alert via Discord for real-time response opportunity
5. Track engagement metrics over event duration for ROI
```

---

## 19. Industry Expert and Cutting-Edge Usage

### Scraper-first architecture (industry norm for small teams)
The $200/month Basic tier with 10K tweet/month cap pushed the entire indie
developer and small startup ecosystem to scrapers. Bird, Nitter (now dead),
and Apify actors are the standard approach for teams under $1M ARR. The
official API is economically viable only for companies where X data is core
to the product (social listening SaaS, brand monitoring platforms).

### xAI as the new X API
The most significant shift in X data access: xAI's Grok models with native
`x_search` capability effectively provide semantic search over X's full
corpus — something the official API doesn't offer at any price tier. Expert
pattern: use xAI for discovery (find what's relevant) and Bird/API for
extraction (get exact data). This two-layer approach gives better results
than either alone.

### AI-powered social listening
Cutting-edge teams are combining X data with LLMs for:
- **Sentiment classification** at scale (not just positive/negative — nuanced
  brand perception analysis)
- **Emerging topic detection** — LLMs identify when a new theme starts appearing
  in X conversations before it trends
- **Automated response drafting** — LLM generates contextual replies to brand
  mentions, reviewed by human before posting
- **Thread synthesis** — reconstructing and summarizing long X threads into
  actionable intelligence briefs

### Content-led growth on X (relevant to EOS/Initiate Arena)
Expert practitioners (Justin Welsh, Sahil Bloom, Dan Koe) use X as the top
of a content funnel:
1. Short-form X posts drive impressions (400K+ monthly for top practitioners)
2. Threads provide depth and get bookmarked (long-tail discovery)
3. Profile link routes to newsletter or landing page
4. DM automation handles high-intent replies
5. API monitoring of engagement informs next content topics

For EOS/Initiate Arena, the pattern would be:
- Post content via X API (free tier allows 1,500/month)
- Monitor engagement via Bird (free)
- Route high-intent replies to DM conversation
- Track which topics drive most profile visits

### Multi-platform triangulation
Expert research teams don't rely on X alone. The /last30days skill already
implements this: X data is combined with web search (Brave), YouTube, and
Reddit for triangulated insights. X's unique value: real-time velocity.
A topic trending on X 48 hours before it appears in blog posts or YouTube
videos is a signal to act on.

---

## EOS Usage Patterns

### Current integration points
1. `/last30days` skill — primary consumer. Uses Bird (primary) or xAI (fallback)
   for X discovery in research reports.
2. `icp_signal_detection` skill — identifies ICP pain signals on X for outreach.
3. `analyze_icp_signal` skill — processes raw X posts as signal inputs.
4. `email_gps.py` — filters x.com/twitter.com URLs from email link extraction.

### Source priority
Bird (free, browser cookies) > xAI (paid, API key) > None.
Configured in `env.py:get_x_source()`.

### Output normalization
Both Bird and xAI produce identical output format: `{id, text, url,
author_handle, date, engagement, why_relevant, relevance}`. Downstream
consumers don't know or care which source produced the data.

### Monitoring
`env.py:get_x_source_status()` returns detailed status dict with
bird_installed, bird_authenticated, bird_username, xai_available, can_install_bird.
Used by the `/last30days` UI to show source availability.

---

## Gotchas

### WebSearch and WebFetch denied during research
Web research tools were unavailable during skill creation. All X API v2 data
(pricing, rate limits, endpoints) is from training knowledge current to early
2025. Verify pricing tiers and rate limits against
https://developer.x.com/en/docs/x-api before making purchasing decisions.

### Bird vendored, not npm-installed
Bird v0.8.0 is vendored in EOS at
`/.agents/skills/last30days/scripts/lib/vendor/bird-search/bird-search.mjs`.
Do NOT run `npm install bird` or similar. The vendored version is the correct one.

### No tweepy in EOS requirements
EOS does not have tweepy installed (`services/requirements.txt` has no tweepy
entry). The tweepy examples in this skill are reference documentation for when/if
direct API access is needed. Current EOS X access is exclusively Bird + xAI.

### X search excludes in web search
EOS web search modules (Brave, OpenRouter, parallel_search, websearch) all
explicitly exclude twitter.com and x.com from web results. X data is handled
separately through the Bird/xAI path. Don't try to get X data through web search.
