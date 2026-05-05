# Meta Graph API — Creator-Level Best Practices
Source: developers.facebook.com/docs/graph-api, developers.facebook.com/docs/messenger-platform, developers.facebook.com/docs/whatsapp/cloud-api, developers.facebook.com/docs/threads, github.com/facebook/facebook-python-business-sdk
API Version: v23.0 stable (May 2025) / v24.0 (Oct 2025) / v25.0 latest. Minimum supported v22.0 (since Sept 2025).
SDK Version: facebook-business 25.0.0 (Python), facebook-nodejs-business-sdk 25.x
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## Authentication

This section is the longest in this document on purpose. The single most
common reason a Meta integration breaks in production is that the wrong
token type is being used against the wrong edge, OR a token expired and
nothing was watching for it. If you internalize this section you will
debug 80% of "why is my Graph call returning 200 errors" tickets in
under 30 seconds.

### The five token types in detail

**1. App Access Token**

Format: literally `{app-id}|{app-secret}`. No HTTP exchange needed; you
can construct it client-side from secrets you already have. Used for:

- `GET /debug_token` (the canonical way to inspect any other token)
- App-scoped reads (public Page metadata, oEmbed)
- Webhook subscription management (`/{app-id}/subscriptions`)
- Account deletion / data deletion callbacks

NEVER ship this to a browser, mobile app, or anything you don't control
the binary of. Anyone with this token IS your app. If it leaks, rotate
the App Secret in the App Dashboard immediately — every existing App
Access Token instantly becomes invalid.

**2. Short-lived User Access Token**

Lifetime: ~1-2 hours. Source: Facebook Login dialog (web/iOS/Android SDK)
returns this after the user grants permissions. Server-side OAuth flow
returns this from `GET /v{N}/oauth/access_token?code=...`.

You should treat this token as a single-use bootstrap. As soon as you
have it, immediately exchange it for a long-lived token. There are zero
reasons to store a short-lived token.

```python
import requests

def exchange_code_for_short_lived(code: str, redirect_uri: str) -> str:
    r = requests.get(
        "https://graph.facebook.com/v23.0/oauth/access_token",
        params={
            "client_id":     APP_ID,
            "client_secret": APP_SECRET,
            "redirect_uri":  redirect_uri,
            "code":          code,
        },
        timeout=10,
    )
    r.raise_for_status()
    return r.json()["access_token"]
```

**3. Long-lived User Access Token**

Lifetime: ~60 days. Source: exchange a short-lived USER token via
`grant_type=fb_exchange_token`. Cannot be created from nothing — the
user must have logged in recently. After ~60 days, the token expires
and the user must re-authenticate via the Login dialog (you cannot
silently refresh).

```python
def exchange_to_long_lived(short_token: str) -> dict:
    r = requests.get(
        "https://graph.facebook.com/v23.0/oauth/access_token",
        params={
            "grant_type":         "fb_exchange_token",
            "client_id":          APP_ID,
            "client_secret":      APP_SECRET,
            "fb_exchange_token":  short_token,
        },
        timeout=10,
    )
    r.raise_for_status()
    return r.json()  # {access_token, token_type, expires_in}
```

**4. Page Access Token**

Lifetime: long-lived if derived from a long-lived USER token; short-lived
otherwise. Source: `GET /me/accounts` (or `GET /{user-id}/accounts`) while
holding a long-lived USER token returns one Page Access Token per Page
the user manages.

A Page Access Token derived this way is described by the docs as
"never expires" but the practical truth is more nuanced:

- The token survives indefinitely as long as the underlying user account
  remains active and has not revoked the granted permissions
- If the user changes their password, the token is invalidated
  (subcode 458)
- If the user is removed as a Page admin, the token is revoked
- If Meta deems the account suspicious, the token enters checkpoint
  state (subcode 460) until the user re-verifies

For a solo founder running their own pages this is essentially permanent.
For multi-tenant SaaS the right answer is a System User token (#5 below)
created in the customer's Business Manager.

```python
def fetch_page_tokens(long_user_token: str) -> list[dict]:
    r = requests.get(
        "https://graph.facebook.com/v23.0/me/accounts",
        params={
            "access_token": long_user_token,
            "fields":       "id,name,access_token,tasks,category",
        },
        timeout=10,
    )
    r.raise_for_status()
    return r.json()["data"]
```

The `tasks` field tells you exactly what the token can do
(`['ANALYZE','ADVERTISE','MESSAGING','MODERATE','CREATE_CONTENT','MANAGE']`).
Match the task to the operation: `CREATE_CONTENT` for posting,
`MESSAGING` for Send API, `ANALYZE` for insights.

**5. System User Access Token (Business Manager)**

Lifetime: configurable — 60 days OR never-expire. Source: Meta Business
Manager → Settings → Users → System Users → Create System User → Generate
New Token. You select the App and the permissions; the token is bound to
the assets that the System User has been granted access to (Pages, IG
accounts, WhatsApp Business Accounts, ad accounts).

This is the **correct** token for any production EOS workload that does
not require a real human to be logged in:

- Scheduled cross-posting from `eos_ai/orchestrator.py`
- Webhook callback responses
- WhatsApp Cloud API (the Cloud API is documented to use a System User
  token bound to the WhatsApp Business Account)
- Daily insights pulls

The trade-off: System User tokens are extremely sensitive. They have no
expiry, they can be very broadly scoped, and they cannot be revoked
"by accident" the way a user-derived token can. Treat them like AWS root
keys. Store encrypted at rest. Rotate on schedule. Audit usage with the
Meta App Dashboard's Activity Log.

### The token dance for a brand-new EOS Meta integration

1. Create the App in developers.facebook.com (Business type)
2. Add Products: Facebook Login, Pages, Messenger, WhatsApp, Instagram
   Graph API, Threads (whichever apply)
3. Configure OAuth Redirect URIs
4. Submit for App Review for the permissions you actually need
   (see Permissions section below for the realistic list)
5. While waiting for review, build with Standard Access against
   self-owned assets (the founder's own Page, IG, WhatsApp number)
6. Real user logs in via Login dialog → short-lived USER token
7. Exchange for long-lived USER token immediately
8. `GET /me/accounts` → Page Access Tokens
9. For each page, `GET /{page-id}?fields=instagram_business_account`
   to find the linked IG asset
10. For WhatsApp: `GET /{business-id}/owned_whatsapp_business_accounts`
    then `GET /{wba-id}/phone_numbers`
11. Store the entire bundle in Neon, encrypted, keyed by tenant_id
12. For automation: create a System User in BM, generate a permanent
    token, replace the user-derived tokens in storage
13. Set up a daily job that calls `GET /debug_token` against every
    stored token and alerts on `is_valid=false` or `expires_at` < 7 days

### Token inspection — `debug_token`

The single most useful auth endpoint. Always run this against any token
you didn't just generate yourself:

```bash
curl -s -G "https://graph.facebook.com/v23.0/debug_token" \
  --data-urlencode "input_token=${TOKEN}" \
  --data-urlencode "access_token=${APP_ID}|${APP_SECRET}"
```

Returns:

```json
{
  "data": {
    "app_id": "1234567890",
    "type": "PAGE",
    "application": "EOS",
    "data_access_expires_at": 1768224000,
    "expires_at": 0,
    "is_valid": true,
    "scopes": ["pages_show_list","pages_manage_posts","pages_messaging",...],
    "user_id": "10000000000",
    "profile_id": "999999999",
    "granular_scopes": [...]
  }
}
```

`expires_at: 0` means never expires. `is_valid: false` with a `error`
sub-object tells you exactly why. `data_access_expires_at` is the
90-day "data use" timer that Meta enforces independently of token
expiry — the user must re-engage with the app within 90 days or you
lose data access regardless of token validity. This catches teams
constantly.

### Permissions — the realistic Advanced Access list

Standard Access works for assets the developer/admins own. Advanced
Access (post-review) is needed for any third-party or production use.

| Permission | Surface | What it unlocks |
|---|---|---|
| `pages_show_list` | Pages | List of pages a user manages |
| `pages_read_engagement` | Pages | Read posts, comments, reactions |
| `pages_manage_posts` | Pages | Publish + edit + delete posts |
| `pages_manage_engagement` | Pages | Comment + react as Page |
| `pages_messaging` | Messenger | Send API |
| `pages_messaging_subscriptions` | Messenger | NON_PROMOTIONAL_SUBSCRIPTION tag |
| `pages_read_user_content` | Pages | User-generated content (UGC) on Page |
| `pages_manage_metadata` | Pages | Subscribe to webhooks, edit Page settings |
| `instagram_basic` | Instagram | Read IG account |
| `instagram_content_publish` | Instagram | Publish to IG via container API |
| `instagram_manage_messages` | Instagram | DM API |
| `instagram_manage_insights` | Instagram | Insights endpoint |
| `whatsapp_business_management` | WhatsApp | Manage WBA, phone numbers, templates |
| `whatsapp_business_messaging` | WhatsApp | Send messages |
| `business_management` | BM | Manage Business Manager assets |
| `threads_basic` | Threads | Read profile + posts |
| `threads_content_publish` | Threads | Publish |
| `threads_manage_insights` | Threads | Insights |
| `threads_manage_replies` | Threads | Reply moderation |

App Review for any of these requires: a screencast of the in-app flow
that triggers the permission, a written explanation, and (sometimes)
test credentials. Plan 2-6 weeks. Reviewers are thorough.

## Core Operations with Exact Signatures

All paths assume the host `https://graph.facebook.com/v23.0` unless noted.
Threads uses `https://graph.threads.net/v23.0`.

### Generic node operations

```
GET    /{node-id}                    Read a node
GET    /{node-id}?fields=a,b,c       Field expansion
GET    /{node-id}?fields=edge.limit(N){sub_a,sub_b}   Edge expansion
POST   /{node-id}                    Update fields on a node
DELETE /{node-id}                    Delete a node
GET    /{node-id}/{edge}             List connected nodes
POST   /{node-id}/{edge}             Create new node on an edge
```

### Pages — Publishing

```
POST /{page-id}/feed
  message=...                        text post
  link=https://...                   link post (preview auto-generated)
  published=false                    save as draft
  scheduled_publish_time=UNIX_TS     schedule (must be 10 min - 6 months out)
  targeting={...}                    audience targeting JSON

POST /{page-id}/photos
  url=https://...                    OR source=@local.jpg multipart
  caption=...
  published=true|false

POST /{page-id}/videos
  file_url=...                       OR source=@local.mp4 multipart resumable
  description=...
  title=...

POST /{page-id}/video_reels
  upload_phase=start                 then upload, then finish
```

### Pages — Reading

```
GET /{page-id}?fields=id,name,about,fan_count,followers_count,
                     instagram_business_account{id,username},
                     connected_instagram_account
GET /{page-id}/feed?fields=id,message,created_time,permalink_url,
                          insights.metric(post_impressions,post_engaged_users)
GET /{page-id}/insights?metric=page_impressions,page_engaged_users&period=day
GET /{page-id}/conversations           Messenger conversations
GET /{page-id}/subscribed_apps         Webhook subscriptions
```

### Messenger Platform — Send API

```
POST /{page-id}/messages
{
  "recipient": {"id": "<PSID>"},
  "messaging_type": "RESPONSE" | "UPDATE" | "MESSAGE_TAG",
  "tag": "ACCOUNT_UPDATE" | "CONFIRMED_EVENT_UPDATE" | "POST_PURCHASE_UPDATE" | "HUMAN_AGENT",
  "message": {
    "text": "...",
    "quick_replies": [{"content_type":"text","title":"Yes","payload":"YES"}],
    "attachment": {"type":"template","payload":{...}}
  }
}
```

`messaging_type=RESPONSE` is the default for messages sent within the
24-hour standard messaging window. After 24h, you need a tag. The
`HUMAN_AGENT` tag (requires `human_agent` permission, separate review)
extends the window to 7 days and is the only realistic option for
"a human will get back to you within a day or two" workflows.

### WhatsApp Cloud API

```
POST /{phone-number-id}/messages       (Authorization: Bearer <SYSTEM_USER_TOKEN>)

# Template message (initiating a conversation)
{
  "messaging_product": "whatsapp",
  "to": "15551234567",
  "type": "template",
  "template": {
    "name": "appointment_reminder",
    "language": {"code": "en_US"},
    "components": [
      {"type":"body","parameters":[{"type":"text","text":"Tuesday 3pm"}]}
    ]
  }
}

# Free-form text (only inside customer service window or after user replies)
{
  "messaging_product": "whatsapp",
  "to": "15551234567",
  "type": "text",
  "text": {"body": "Got it, see you then."}
}

# Media
{
  "messaging_product": "whatsapp",
  "to": "15551234567",
  "type": "image",
  "image": {"link":"https://...","caption":"..."}
}
```

```
POST /{wba-id}/message_templates       Create template (needs review)
GET  /{wba-id}/message_templates       List templates
DELETE /{wba-id}/message_templates?name=foo
GET  /{phone-number-id}                Quality rating, status
POST /{phone-number-id}/register       Register a phone number to Cloud API
```

### Threads API (host: `graph.threads.net`)

```
POST /{ig-user-id}/threads             Create media container
  media_type=TEXT|IMAGE|VIDEO|CAROUSEL
  text=...
  image_url=... | video_url=...
  is_carousel_item=true   (for items in a carousel)
  reply_to_id=...         (reply to another thread)
  reply_control=everyone|accounts_you_follow|mentioned_only

POST /{ig-user-id}/threads_publish
  creation_id={CONTAINER_ID}

GET /{thread-id}?fields=id,media_type,text,permalink,timestamp,
                       insights.metric(views,likes,replies,reposts,quotes)
GET /{ig-user-id}/threads               List my threads
GET /{ig-user-id}/replies               Replies to my threads
GET /{ig-user-id}/threads_insights      Account-level insights
```

Threads tokens come from the Threads-specific OAuth flow at
`https://threads.net/oauth/authorize` (NOT `facebook.com`). Exchange
short-lived → long-lived against `graph.threads.net/access_token` with
`grant_type=th_exchange_token`. Threads tokens cannot be obtained from
the Facebook OAuth flow.

### Webhook subscription management

```
POST /{app-id}/subscriptions             (App access token)
  object=page|instagram|whatsapp_business_account|threads
  callback_url=https://eos/webhook
  fields=feed,messages,messaging_postbacks,...
  verify_token=<random secret you choose>
  include_values=true

GET  /{app-id}/subscriptions
DELETE /{app-id}/subscriptions?object=page

POST /{page-id}/subscribed_apps          (Page token — per-asset opt-in)
  subscribed_fields=feed,messages,...

DELETE /{page-id}/subscribed_apps
GET    /{page-id}/subscribed_apps
```

### Batch and field expansion

```
POST /
  access_token={token}
  batch=[
    {"method":"GET", "relative_url":"me?fields=id,name"},
    {"method":"GET", "relative_url":"me/accounts"},
    {"method":"POST","relative_url":"{page-id}/feed","body":"message=hi"}
  ]
```

Up to 50 sub-requests. Each gets its own status code. JSONpath chaining
lets a later sub-request reference an earlier one's output:

```json
{"name":"get-page","method":"GET","relative_url":"me/accounts"},
{"method":"POST","relative_url":"{result=get-page:$.data.0.id}/feed",
 "body":"message=using_chained_id"}
```

## Pagination Patterns

Meta uses three pagination styles. You will encounter all three.

**1. Cursor-based** (default, preferred)

```json
{
  "data": [...],
  "paging": {
    "cursors": {"before":"QVF...", "after":"QVF..."},
    "next": "https://graph.facebook.com/v23.0/...&after=QVF..."
  }
}
```

Just follow `paging.next` until it's absent. If you want backward, use
`paging.previous`. Cursor pagination is stable across inserts/deletes
(unlike offset).

**2. Time-based** (Page feed, conversations)

```
GET /{page-id}/feed?since=2026-01-01&until=2026-04-01&limit=100
```

`since` and `until` accept Unix timestamps OR `strtotime`-style strings.
`paging.next` will use the underlying cursor format.

**3. Offset** (legacy, avoid)

```
GET /{node}/edge?limit=25&offset=0
```

Returns inconsistent results when the underlying collection mutates
mid-pagination. Only use against truly static collections.

**SDK pattern (Python):**

```python
def all_pages(start_url: str, token: str):
    url = start_url
    while url:
        r = requests.get(url, params={"access_token": token}, timeout=15)
        r.raise_for_status()
        body = r.json()
        for item in body.get("data", []):
            yield item
        url = body.get("paging", {}).get("next")
```

`paging.next` already includes all the query params (including the
access token if it was in the URL — strip it before logging).

## Rate Limits

Meta runs four overlapping rate-limit systems. You need to understand all
four because hitting any one of them blocks you.

**1. App-level rate limits.**
`X-App-Usage` header in every response:

```
X-App-Usage: {"call_count":35,"total_cputime":12,"total_time":18}
```

Each value is a percentage 0-100. At 100% the app is blocked for ~1 hour.
The window is rolling, ~1 hour wide. Limit is calculated per app per hour
as `200 * monthly_active_users` calls (yes, it scales with adoption).

**2. User-level rate limits.**
`X-Ad-Account-Usage` (ads only) and per-user limits enforced silently.
Generally not the binding constraint outside of Marketing API.

**3. Page-level rate limits.**
`X-Page-Usage` header. Enforced per Page per hour. Limit is roughly
`4800 * impression_count_per_24h / 4800` — basically scales with how
active the page is. Small pages have very low limits.

**4. Business Use Case rate limits.**
`X-Business-Use-Case-Usage` header. JSON keyed by business id, with
`call_count`, `total_cputime`, `total_time` AND `estimated_time_to_regain_access`
in minutes. This is the modern unified system for cross-product limits
and is what Cloud-API-style products (WhatsApp) use.

```json
X-Business-Use-Case-Usage: {
  "999999999": [{
    "type":"messenger",
    "call_count":78,
    "total_cputime":12,
    "total_time":15,
    "estimated_time_to_regain_access":0
  }]
}
```

WhatsApp has its own messaging tier that throttles the **rate of unique
recipients** (Tier 1: 1k/24h, Tier 2: 10k, Tier 3: 100k, Tier 4: unlimited).
You climb tiers automatically based on quality rating.

**Defensive pattern.** Read the headers on EVERY response, log them, and
back off proactively at 80%:

```python
def check_rate_limits(response):
    app = json.loads(response.headers.get("X-App-Usage", "{}"))
    page = json.loads(response.headers.get("X-Page-Usage", "{}"))
    biz = json.loads(response.headers.get("X-Business-Use-Case-Usage", "{}"))
    worst = max(
        app.get("call_count", 0),
        app.get("total_cputime", 0),
        app.get("total_time", 0),
        page.get("call_count", 0),
        page.get("total_cputime", 0),
        page.get("total_time", 0),
    )
    if worst >= 80:
        log.warning(f"meta_rate_limit worst={worst} app={app} page={page} biz={biz}")
    if worst >= 95:
        time.sleep(60)
    return worst
```

## Error Codes and Recovery

Meta returns errors with both `code` and `error_subcode`. The subcode is
where the actionable information lives.

| code | subcode | Meaning | Recovery |
|---|---|---|---|
| 1 | — | Unknown error | Retry with backoff |
| 2 | — | Service temporarily unavailable | Retry with backoff |
| 4 | — | App-level throttling | Sleep until X-App-Usage resets |
| 17 | — | User-level throttling | Sleep, reduce concurrency |
| 32 | — | Page-level throttling | Sleep, reduce per-page concurrency |
| 100 | — | Invalid parameter | Fix the request |
| 102 | — | Session key invalid (auth) | Re-auth |
| 190 | 458 | User changed password | Re-auth required |
| 190 | 459 | User checkpointed | Re-auth required |
| 190 | 460 | Password changed | Re-auth required |
| 190 | 463 | Token expired | Re-auth or refresh |
| 190 | 464 | Sessions invalidated | Re-auth |
| 190 | 467 | Token invalid | Re-auth |
| 200 | — | Permissions error | App review or scope mismatch |
| 230 | — | Permission denied (Messenger 24h window) | Use a tag |
| 368 | — | Spam — temporarily blocked for policy | Wait, file appeal |
| 506 | — | Duplicate post | Idempotent retry, ignore |
| 613 | — | Calls to this api have exceeded the rate limit | Backoff |
| 803 | — | Some of the aliases you requested do not exist | Bad ID |
| 1487 | — | Image / video upload failed | Re-upload |
| 2018012 | — | Image too large | Resize |
| 2061006 | — | (WhatsApp) Recipient not opted in / no template | Send template first |

**Defensive parsing:**

```python
def parse_meta_error(response):
    try:
        body = response.json()
    except Exception:
        return None
    err = body.get("error")
    if not err:
        return None
    return {
        "code":     err.get("code"),
        "subcode":  err.get("error_subcode"),
        "type":     err.get("type"),
        "message":  err.get("message"),
        "fbtrace":  err.get("fbtrace_id"),
        "is_transient": err.get("is_transient", False),
    }
```

`fbtrace_id` is the magic field — include it in any support request and
Meta engineers can look up the exact request server-side.

## SDK Idioms

The official Python SDK is `facebook-business` (currently v25.0.0). It
auto-generates from the Marketing API schema, so it's most useful for ads
and less useful for organic Pages/Messenger/WhatsApp/Threads, where most
EOS code uses raw HTTP.

```python
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.page import Page
from facebook_business.adobjects.user import User

FacebookAdsApi.init(APP_ID, APP_SECRET, USER_ACCESS_TOKEN, api_version="v23.0")

me = User(fbid="me")
pages = me.get_accounts(fields=["id","name","access_token"])
for p in pages:
    print(p["id"], p["name"])
```

For Pages/Messenger/WhatsApp/Threads, the EOS-recommended pattern is a
thin requests wrapper:

```python
import requests

class GraphClient:
    BASE = "https://graph.facebook.com/v23.0"

    def __init__(self, token: str, base: str | None = None):
        self.token = token
        self.base = base or self.BASE
        self.s = requests.Session()

    def _req(self, method, path, **kw):
        url = f"{self.base}/{path.lstrip('/')}"
        params = kw.pop("params", {}) or {}
        params.setdefault("access_token", self.token)
        r = self.s.request(method, url, params=params, timeout=15, **kw)
        # always parse rate limits even on success
        check_rate_limits(r)
        if r.status_code >= 400:
            err = parse_meta_error(r)
            raise GraphError(err, r.status_code, r.text)
        return r.json()

    def get(self, path, **kw):  return self._req("GET", path, **kw)
    def post(self, path, **kw): return self._req("POST", path, **kw)
    def delete(self, path, **kw): return self._req("DELETE", path, **kw)

class GraphError(Exception):
    def __init__(self, err, status, text):
        self.err = err
        self.status = status
        self.text = text
```

Threads needs a separate instance:

```python
threads = GraphClient(THREADS_TOKEN, base="https://graph.threads.net/v23.0")
```

## Anti-Patterns

- **Hardcoding tokens in source.** Always Neon-encrypted, loaded via
  `eos_ai/tenant.py`.
- **Calling `/me` from a server-side cron.** `/me` resolves against the
  token's owner — fine, but unclear. Always use the explicit ID
  (`/{page-id}`) so logs are debuggable.
- **Skipping `debug_token` in cron.** Daily token health check is one
  HTTP call per token. Run it.
- **Treating `error.code` as the error.** Subcode tells the real story.
- **One-request-per-resource for batch reads.** Use field expansion or
  `?ids=a,b,c` to fetch many in one call.
- **Polling Page feed every minute.** Subscribe to the `feed` webhook
  and react to push.
- **Re-uploading the same image for every Page post.** Upload once with
  `published=false` to get a `media_fbid`, then attach to multiple posts.
- **Sending Messenger messages with no `messaging_type`.** Default works
  inside the 24h window but is ambiguous; always set explicitly.
- **WhatsApp templates with placeholders mismatched to component params.**
  Returns `failed` status async via webhook, not in the POST response.
- **Catching `requests.HTTPError` and retrying without checking
  `is_transient`.** Permanent errors (190, 200) will never recover.
- **Forgetting to verify webhook signatures.** Anyone can POST to your
  callback URL. Compute HMAC, compare in constant time.
- **Sharing one System User token across tenants.** Rotation becomes
  impossible. One System User per tenant.
- **Building against `graph.facebook.com` for Threads.** Wrong host.

## Data Model

The graph is genuinely a graph — not a tree, not a REST resource tree.
Every node has stable IDs that survive renames, edge migrations, and
even Page restructures.

### IDs

- App ID: numeric, app-wide
- User ID (FBID): numeric, app-scoped (different per app — same user
  has different IDs in different apps; this is by design for privacy)
- Page ID: numeric, global
- Page-Scoped ID (PSID): numeric, the user's ID *as seen by a specific
  Page* — used in Messenger so a user has different PSIDs across
  different brands' pages
- Instagram Business Account ID: numeric, parented under a Page
- WhatsApp Business Account (WBA) ID: numeric, parented under a Business
- Phone Number ID: numeric, parented under a WBA
- Threads User ID: numeric, parented under an Instagram account
- Post ID: `{page-id}_{post-id}` compound — both halves are needed
- Comment ID: `{post-id}_{comment-id}` compound
- Conversation ID: `t_{conversation-id}` (Messenger), with the `t_` prefix
- Message ID: opaque, returned by Send API

### Stable cross-references

```
Page  --(field: instagram_business_account)-->  IG Business Account
Page  --(field: connected_instagram_account)-->  IG Personal Account (legacy)
Business --(edge: owned_pages)-->  Pages
Business --(edge: owned_whatsapp_business_accounts)-->  WBAs
WBA --(edge: phone_numbers)-->  Phone Number IDs
IG Business Account --(field: threads_user)-->  Threads User
```

### Versioning fields

Every node has hidden meta fields you can request:

```
?fields=id,name,metadata{type,fields,connections}
```

This returns the entire schema for that node — what fields exist, what
edges connect, what Graph version they were introduced in. Useful for
generating up-to-date code at build time.

## Webhooks and Events

Webhooks are how Meta pushes events to you. The model:

1. Your App registers a callback URL and a verify_token with Meta
2. Meta does a GET handshake to your URL with `hub.mode=subscribe`,
   `hub.verify_token`, `hub.challenge`. You echo `hub.challenge` back if
   the verify_token matches
3. From then on, Meta POSTs JSON to your URL whenever subscribed events
   occur, signed with `X-Hub-Signature-256: sha256=<hex>`

```python
import hmac, hashlib

def verify_signature(body: bytes, header: str, app_secret: str) -> bool:
    if not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(
        app_secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, header.split("=", 1)[1])
```

**Subscription objects:**

| object | per-asset opt-in? | example fields |
|---|---|---|
| `page` | yes — `/{page-id}/subscribed_apps` | `feed`, `messages`, `messaging_postbacks`, `message_deliveries`, `message_reads`, `mention`, `messaging_handovers` |
| `instagram` | yes — via Page subscribed_apps | `comments`, `mentions`, `messages`, `story_insights`, `live_comments` |
| `whatsapp_business_account` | yes — `/{wba-id}/subscribed_apps` | `messages`, `message_template_status_update`, `phone_number_quality_update`, `account_review_update` |
| `threads` | yes | `replies`, `mentions`, `quotes`, `reposts` |
| `user` | n/a, app-wide | `email`, `feed` (deprecated, mostly broken) |

**Payload shape (universal):**

```json
{
  "object":"page",
  "entry":[{
    "id":"<page-id>",
    "time":1701000000,
    "changes":[{
      "field":"feed",
      "value":{"item":"comment","verb":"add","comment_id":"...","post_id":"..."}
    }],
    "messaging":[{...}]   // for messenger events
  }]
}
```

`changes` is for content events; `messaging` is for Messenger Send/Receive
events. You'll often see both in one POST. Always iterate `entry` and
within each, both arrays.

**Reliability rules:**

- Respond `200 OK` within 10 seconds. If you can't, hand off to a queue
  immediately and return 200.
- Meta retries on any non-200 with exponential backoff for ~36 hours.
- Duplicates happen even on success. Idempotency on
  `(entry.id, time, change.value.message_id)`.
- Order is NOT guaranteed for high-throughput pages.
- During mass events (a viral post), Meta will batch hundreds of
  `changes` into one POST. Be ready.

## Limits

Per-surface limits as of v23.0:

**Pages**
- Max post text: 63,206 chars
- Max scheduled posts pending: 75
- Max bulk insights metrics per call: 25
- Max field expansion depth: 4 levels
- Max `?ids=` batch lookup: 50

**Messenger**
- Standard messaging window: 24h from last user message
- Human Agent window: 7 days from last user message (with permission)
- Max message text: 2000 chars
- Max quick replies: 13
- Max generic template elements: 10
- Max button texts per element: 3

**WhatsApp Cloud API**
- Tiered messaging: Tier 1 (1k unique recipients/24h), Tier 2 (10k),
  Tier 3 (100k), Tier 4 (unlimited). Promotion automatic on quality.
- Max template body: 1024 chars
- Max template variables: 10 per component
- Max media: 100MB video, 16MB image, 16MB audio, 100MB document
- Customer service window: 24h from last user message (free)
- Marketing/utility/auth templates need approval per language

**Threads**
- 250 API-published posts per 24h
- 1000 replies per 24h
- Max post: 500 chars
- Max images per carousel: 20
- Insights backfill: 90 days

**Batch**
- Max sub-requests per batch: 50
- Max combined batch payload: 10MB

## Cost Model

The Graph API itself is **free** for organic surfaces. Cost shows up
only on WhatsApp messaging, and that pricing changed materially in 2025.

**Pre-July 2025 model (deprecated):** charged per 24-hour conversation
window, by category (marketing/utility/auth/service).

**Current model (since July 1, 2025):** charged **per delivered template
message**, by category and country. Free messages:

- All service messages
- All utility messages sent inside the 24-hour customer service window
- Free entry-point window: 72 hours after a user clicks a "click to
  WhatsApp" ad or a Page CTA button — all messages free in that window

Approximate per-message ranges (US, 2026):

| Category | Range |
|---|---|
| Marketing | up to $0.024 |
| Utility | $0.004-$0.0456 |
| Authentication | $0.004-$0.0456 |
| Service | $0 |

Prices vary 100x by country (India is much cheaper, Egypt cheaper, US
mid-tier, AU/UK higher). As of January 2026 marketing fees lowered for
France and Egypt, raised for India; utility/auth fees lowered for North
America. Local billing now supported in 16 currencies, INR direct
billing since January 2026.

For EOS the practical implication: WhatsApp is **not** a free DM channel
the way Messenger is. Budget per-message and prefer service-window
messages where possible.

The Graph API does have a soft "compute cost" — `total_cputime` in
`X-App-Usage` is a fraction of your hourly compute budget. Heavy field
expansion + insights queries burn cputime fast even though there's no
dollar cost.

## Version Pinning

Meta releases a new Graph API version every ~3 months. Each version is
supported for ~2 years from release. Past the support window, the
version starts auto-redirecting to the next supported version (with
breaking changes). Past 2 years it's fully removed.

**Current state (April 2026):**

- v22.0 — minimum supported (older versions blocked since Sept 9, 2025)
- v23.0 — released May 29, 2025, supported until ~June 2027
- v24.0 — released October 8, 2025, supported until ~Oct 2027
- v25.0 — released early 2026, latest

**EOS pinning rule:**

Pin to the second-newest stable version. Right now that's `v23.0`. This
gives you ~12 months of stability before the next forced bump. Bump
deliberately, not reactively. Read the changelog for the new version,
audit affected fields, then change the constant in one place
(`eos_ai/meta_constants.py`).

```python
# eos_ai/meta_constants.py
META_GRAPH_VERSION = "v23.0"   # bumped 2026-04-06; review at 2027-01
META_FB_BASE = f"https://graph.facebook.com/{META_GRAPH_VERSION}"
META_THREADS_BASE = f"https://graph.threads.net/{META_GRAPH_VERSION}"
```

**Deprecation watching.** Meta posts to `developers.facebook.com/blog`
on the second Tuesday of every month with the upcoming deprecations.
Subscribe with a Notion-watching cron, or set a `world_pulse` source
on the blog feed.

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

Meta built the Graph API in 2010 as the public face of the Open Graph
project: the bet was that the social graph was a queryable database, not
a feed. Everything that has happened since is a consequence of that
bet. The API is shaped like a graph because Facebook internally is a
graph; the version-on-the-URL discipline exists because Facebook learned
the hard way (~2013-2015) that breaking changes without versioning
destroys developer trust.

The biggest tradeoffs Meta makes:

**Permission gating over feature flags.** Other APIs ship a feature and
let you call it. Meta makes you go through App Review. The cost is
weeks of latency on every new permission. The benefit is that the
permission is meaningfully scoped — when you have `pages_messaging` on
a real production app, you have it for everyone, not just the test
account. This is the explicit privacy posture that came out of the
Cambridge Analytica fallout.

**Versioned schema over evolving schema.** Meta could have done a "v1"
that grew over time. Instead they version everything quarterly. This
makes deprecations slow and predictable, and it makes the API surface
self-documenting (you can `GET /{node}?metadata=1` and get the schema).
The cost: you have to bump versions actively.

**Unified surface over per-product APIs.** Instagram, WhatsApp, Threads
could each have had their own dialect. Instead they all live under
`graph.facebook.com` (with Threads as the one exception, on its own
host but the same shape). The cost: WhatsApp Cloud API users have to
learn the Facebook auth model. The benefit: cross-product workflows
are trivial.

**System User tokens over service accounts.** Most APIs (Google, Slack)
have a service account concept. Meta has System Users in Business
Manager, which are user-shaped but never log in. This is awkward for
small projects (you must have a Business Manager) but powerful for
enterprise (the same audit log captures human users and automation).

**Webhooks over polling.** The push model is heavily preferred —
many feed-style endpoints rate-limit aggressively but webhooks have no
delivery cost.

The thing Meta got wrong, and is still paying for: making `/me` mean
"the token's owner" everywhere. It saved a few characters in 2010 and
has cost engineers years of debugging since (you call `/me/feed` and
get someone else's feed because the cron picked up a different token).

## Problem-Solution Map and Hidden Capabilities

| Problem | Solution |
|---|---|
| "I need to publish the same image to FB Page + IG + Threads" | Upload once, store the URL on a CDN, POST to all three creation endpoints in parallel. Don't try to share `media_fbid`. |
| "I need to schedule a Page post for next Tuesday at 9am" | `POST /{page}/feed` with `published=false&scheduled_publish_time={unix-ts}`. Range: 10 minutes to 6 months out. |
| "I want to draft a post and publish later" | Same — `published=false` with no scheduled time creates a draft. POST to `/{post-id}` later with `is_published=true`. |
| "I need to know who reacted to a post" | `/{post-id}/reactions?fields=name,type` (requires `pages_read_user_content`). |
| "I want to read DMs in a unified inbox across IG + FB" | Both IG and FB DMs flow through the Messenger Send API + webhooks. Same `messages` field, same payload shape. The `messaging_product` field tells you which platform. |
| "I want to know if a user is online" | You can't. Removed years ago. |
| "I want to send a Messenger message 5 days after the user last replied" | `messaging_type=MESSAGE_TAG` with `tag=HUMAN_AGENT` (requires `human_agent` permission). 7-day window. |
| "I want to send Messenger broadcasts" | Broadcasts API was deprecated in 2020. The replacement is `NON_PROMOTIONAL_SUBSCRIPTION` tag — heavy gating, news/productivity/personal-tracking only. |
| "I want to read Page Insights for last 30 days" | `/{page}/insights?metric=page_impressions,page_engaged_users&period=day&since=...&until=...`. Multi-metric in one call. |
| "I want to know which posts a user has seen" | You can't. Privacy-restricted. |
| "I want to delete a Page post" | `DELETE /{post-id}` with the Page token. |
| "I want to comment on my own Page post as the Page" | `POST /{post-id}/comments` with the Page token. As a user: requires `pages_manage_engagement` and the user must be a Page admin. |
| "I want to upload a video larger than 1GB" | Use the resumable upload protocol: `POST /{page}/videos?upload_phase=start` → `transfer` → `finish`. |
| "I want to publish a Reel" | `POST /{page}/video_reels` with the resumable protocol. Same for IG. |
| "I want to know the conversion rate of a Click-to-WhatsApp ad" | Cross with the Marketing API; the ad object has a `click_to_messenger_id` linking to the resulting conversation. |

**Hidden capabilities:**

- **Page metadata expansion.** `?fields=metadata{type,fields,connections}` self-describes the schema.
- **`?ids=` parameter** for batch lookup of up to 50 nodes in one call.
- **`fields=...as=...` aliasing** for renaming fields in the response.
- **`since`/`until` on insights** accepts strtotime strings (`yesterday`, `today-30d`).
- **`pretty=1` query param** indents responses (debugging).
- **`access_token` in body** instead of query string (avoid leaking in logs).
- **`appsecret_proof`** — HMAC of token+secret, sent as a parameter. Add to all server-side calls for an extra layer of leak protection. Configure in App Settings → require for server-side calls.

## Operational Behavior and Edge Cases

The hard-earned operational realities:

- **Token revocation is silent.** When a user revokes app permission,
  your existing tokens become invalid but you get no callback. You only
  find out on the next API call. Run `debug_token` daily.
- **Webhook delivery is at-least-once, sometimes many times.** Build
  idempotent handlers. The retry window is ~36 hours.
- **Webhooks arrive out of order during high traffic.** A `comment.add`
  for a post can arrive before the `feed.add` for the post itself.
  Don't assume causal ordering.
- **Page Insights have a delay.** Most metrics update in ~1 hour but
  some (organic_reach, fan demographics) lag 1-3 days.
- **`/me/accounts` lists every Page the user manages, including ones
  the app wasn't authorized for.** Filter on `tasks` to know what you
  can actually do.
- **`/{page}/feed` excludes posts published as a draft.** Add
  `is_published=false` filter to see drafts.
- **Image uploads are stored on Meta's CDN forever.** Even if you
  delete the post, the underlying media URL remains accessible
  (security via obscurity).
- **Messenger PSIDs are stable per (user, page) pair forever.** Use
  them as the canonical key in CRM.
- **WhatsApp phone numbers can be migrated between WBAs once per 7
  days.** Plan migrations carefully.
- **WhatsApp templates' approval state is async.** Polling
  `/{wba}/message_templates` returns the current state, but the better
  pattern is to subscribe to `message_template_status_update` webhook.
- **Threads handles deleted accounts oddly.** The account ID returns
  404 but cached webhook subscriptions still fire empty events.
- **The Cloud API replaced the On-Premise WhatsApp API in 2024.** Any
  old documentation referencing self-hosted Docker for WhatsApp is
  obsolete.
- **`graph.video.facebook.com`** is a separate host for video uploads,
  used by the resumable upload protocol. Same auth, same versioning.
- **Browser network tools strip `Authorization` headers from copy-as-curl**
  on Meta domains. Pull from server logs, not browser.
- **`appsecret_proof`** mismatches return error 100 with subcode
  "Invalid appsecret_proof provided in the API argument," not an auth
  error — easy to misdiagnose.

## Ecosystem Position and Composition

Meta Graph API sits in a competitive landscape with:

- **X (Twitter) API v2** — paid, restrictive (since 2023), much smaller
  ecosystem. Free tier is read-mostly with a 1500-tweet/month write
  cap. Enterprise tier costs $5k+/month.
- **TikTok Display + Content Posting API** — newer (2023+), more
  restricted (manual review for posting), separate auth flow. EOS has
  a separate `tiktok` skill in this wave.
- **LinkedIn Marketing API** — bureaucratic, requires Marketing Developer
  Platform approval, only really useful for ads. Personal posting via API
  exists but is rate-limited to ~25 posts/day per member.
- **YouTube Data API** — free, generous quotas, but separate from any
  social DM/inbox model.
- **Bluesky AT Protocol** — open and free, but tiny audience.

**Where Meta wins:** unified inbox across FB Messenger + IG DMs + WhatsApp,
mature webhook system, free tier with no message volume cap (organic),
the largest install base of any non-Chinese social platform.

**Where Meta loses:** App Review friction, the auth model complexity,
WhatsApp pricing surprise, and the fact that organic Page reach has
collapsed since ~2014 making FB Page publishing low-leverage.

**Composition with EOS tools:**

- **Apify** — used to scrape Instagram and Facebook data the Graph API
  can't return (competitor pages, hashtag walls, public Reels). The two
  layers are complementary: official API for owned assets, scraping for
  market intelligence.
- **Zapier / Make** — useful for prototyping cross-Meta workflows
  before EOS native code exists. They handle the OAuth + token refresh
  for you. Migrate to native code as soon as the workflow stabilizes.
- **ManyChat / Chatfuel** — Messenger flow builders. Useful for visual
  conversation design without code, but they own the bot identity, so
  their PSIDs are theirs. EOS native Messenger integration is preferred
  for any flow that touches CRM.
- **Notion / Airtable** — content scheduling DBs. EOS pattern: write
  the content schedule in Notion, EOS reads it via the Notion API,
  publishes via Meta Graph at the right time.

## Trajectory and Evolution

Where Meta is taking the Graph API:

**Cross-product convergence accelerating.** Meta is investing heavily in
unifying Messenger + IG + WhatsApp into a single messaging surface
("Meta Messaging"). The Send API already accepts a `messaging_product`
field for Messenger vs Instagram. WhatsApp inbox unification with the
others is the next step (announced 2024, in progress).

**AI on WhatsApp.** Meta is rolling out native AI chatbots on WhatsApp
Business Cloud API. The pattern: businesses set up an LLM-backed
assistant that can be invoked inside the customer service window for
free, with marketing templates priced normally.

**Threads API expansion.** Threads launched its API in mid-2024 with
basic publishing; July 2025 added polls, location tagging, real-time
webhooks, click metrics, GIF media, search, public profile access,
reply restrictions. February 2026 added GIPHY GIFs and app ads. The
trajectory is clearly to be a peer of the Instagram API by ~2027.

**Webhook mTLS.** Meta is migrating webhook mTLS certificates to a new
Meta-owned CA starting March 31, 2026. Anyone using mTLS for webhook
delivery validation needs to update their trust stores.

**Insights metric churn.** Several legacy metrics (Page Reach, Page
Impressions, 3-second Viewers) are being deprecated in June 2026 in
favor of new Media Views and Media Viewers metrics. Audit insights
queries.

**App Review automation.** Meta is using AI to triage simple permission
requests. Standard self-owned use cases now sometimes get auto-approved
in hours instead of weeks.

**Marketing API divergence.** The Marketing API is increasingly its
own product with its own version cadence. Don't assume Graph API and
Marketing API ship in lockstep.

## Conceptual Model and Solution Recipes

The mental model that makes everything click: **the API is a graph
DSL, not a REST service.** Every request is "give me this node and
these connected nodes, projected to these fields." Once you see the
projection model, even insights queries become obvious — they're just
a connected node with metric/period parameters.

### Recipe A — One-call Page+IG+Threads cross-poster

```python
def cross_post(text: str, image_url: str, tenant: dict):
    fb = GraphClient(tenant["page_token"])
    th = GraphClient(tenant["threads_token"], base="https://graph.threads.net/v23.0")

    # FB Page photo
    fb_post = fb.post(
        f"{tenant['page_id']}/photos",
        params={"url": image_url, "caption": text, "published": "true"},
    )

    # IG (covered by instagram skill — included for completeness)
    ig_container = fb.post(
        f"{tenant['ig_user_id']}/media",
        params={"image_url": image_url, "caption": text},
    )
    ig_publish = fb.post(
        f"{tenant['ig_user_id']}/media_publish",
        params={"creation_id": ig_container["id"]},
    )

    # Threads
    th_container = th.post(
        f"{tenant['threads_user_id']}/threads",
        params={"media_type": "IMAGE", "image_url": image_url, "text": text},
    )
    th_publish = th.post(
        f"{tenant['threads_user_id']}/threads_publish",
        params={"creation_id": th_container["id"]},
    )

    return {
        "fb_post_id":      fb_post["id"],
        "ig_post_id":      ig_publish["id"],
        "threads_post_id": th_publish["id"],
    }
```

### Recipe B — Daily token health check

```python
def check_all_tenant_tokens():
    for tenant in load_all_tenants():
        token = tenant["page_token"]
        try:
            r = requests.get(
                "https://graph.facebook.com/v23.0/debug_token",
                params={
                    "input_token": token,
                    "access_token": f"{APP_ID}|{APP_SECRET}",
                },
                timeout=10,
            )
            data = r.json()["data"]
            if not data["is_valid"]:
                alert(tenant, f"token invalid: {data.get('error',{}).get('message')}")
                continue
            if data.get("expires_at") and data["expires_at"] - time.time() < 7*86400:
                alert(tenant, f"token expires in <7d at {data['expires_at']}")
            if data.get("data_access_expires_at") - time.time() < 7*86400:
                alert(tenant, "data access expires <7d — user must re-engage")
        except Exception as e:
            alert(tenant, f"debug_token failed: {e}")
```

### Recipe C — Webhook handler skeleton

```python
from flask import Flask, request, abort
import json, hmac, hashlib

app = Flask(__name__)
APP_SECRET = os.environ["FB_APP_SECRET"]
VERIFY_TOKEN = os.environ["FB_WEBHOOK_VERIFY_TOKEN"]

@app.route("/webhook", methods=["GET"])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    abort(403)

@app.route("/webhook", methods=["POST"])
def receive():
    sig = request.headers.get("X-Hub-Signature-256", "")
    if not verify_signature(request.data, sig, APP_SECRET):
        abort(403)
    payload = request.get_json()
    # respond fast — defer real work to a queue
    queue.put(payload)
    return "ok", 200

def worker():
    while True:
        payload = queue.get()
        for entry in payload.get("entry", []):
            page_id = entry.get("id")
            for change in entry.get("changes", []):
                handle_change(page_id, change)
            for messaging in entry.get("messaging", []):
                handle_messaging(page_id, messaging)
```

### Recipe D — Messenger reply with Human Agent tag

```python
def reply_messenger(page_id: str, page_token: str, psid: str, text: str,
                    inside_24h: bool):
    body = {
        "recipient": {"id": psid},
        "messaging_type": "RESPONSE" if inside_24h else "MESSAGE_TAG",
        "message": {"text": text},
    }
    if not inside_24h:
        body["tag"] = "HUMAN_AGENT"   # requires human_agent permission
    r = requests.post(
        f"https://graph.facebook.com/v23.0/{page_id}/messages",
        params={"access_token": page_token},
        json=body, timeout=10,
    )
    return r.json()
```

### Recipe E — WhatsApp template send + status webhook

```python
def send_wa_template(phone_id: str, sys_token: str, to: str,
                     template_name: str, lang: str, body_vars: list[str]):
    components = []
    if body_vars:
        components.append({
            "type": "body",
            "parameters": [{"type":"text","text":v} for v in body_vars],
        })
    r = requests.post(
        f"https://graph.facebook.com/v23.0/{phone_id}/messages",
        headers={"Authorization": f"Bearer {sys_token}"},
        json={
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": lang},
                "components": components,
            },
        }, timeout=10,
    )
    return r.json()  # message goes "accepted" -> webhook "sent" -> "delivered" -> "read"
```

### Recipe F — Reading Page Insights for the EOS dashboard

```python
def page_insights(page_id, page_token, days=30):
    metrics = [
        "page_impressions",
        "page_post_engagements",
        "page_actions_post_reactions_total",
        "page_video_views",
        "page_fans",
    ]
    r = requests.get(
        f"https://graph.facebook.com/v23.0/{page_id}/insights",
        params={
            "metric": ",".join(metrics),
            "period": "day",
            "since": f"-{days} days",
            "until": "today",
            "access_token": page_token,
        }, timeout=15,
    )
    out = {}
    for m in r.json().get("data", []):
        out[m["name"]] = [(v["end_time"], v["value"]) for v in m["values"]]
    return out
```

## Industry Expert and Cutting-Edge Usage

What world-class teams do that average teams don't:

**1. Treat the App Secret like an SSH key.** Rotate quarterly. Store in
a real secrets manager. Never commit it. Configure App Settings to
**require** `appsecret_proof` on all server-side calls, so a leaked
access token alone can't be used without also leaking the secret.

**2. Use System Users exclusively for production.** User-derived tokens
are for local dev and onboarding flows only. Never run a cron against
a user-derived token in production.

**3. Webhook-first, polling-second.** If a webhook field exists for the
data you want, use it. Polling exists as a fallback for catching missed
events, not as the primary read path.

**4. One token per tenant per surface.** Don't reuse tokens across
tenants even if they technically work — the principle of least privilege
applies, and rotation becomes a nightmare otherwise.

**5. Always pass `fbtrace_id` in support tickets.** Internal Meta
engineers can look up the exact request from this ID. Tickets without
it get triaged to bottom.

**6. Track `data_access_expires_at` separately from `expires_at`.** This
is the 90-day "user must re-engage" timer. It bites teams that have
a working token but the user hasn't logged in for 90 days.

**7. Use `?ids=a,b,c,d` for batch reads.** Field expansion + multi-id
lookup is faster than batch endpoint for read-heavy workloads.

**8. Pin the Graph version in one constant, bump it deliberately.**
Spread `v23.0` across 50 files = 50 places to update on the next bump.

**9. Build a token vault layer that other code can't bypass.**
`tenant.get_meta_token(scope='messenger')` — never read tokens from
config in business code. This makes rotation, encryption, and audit
all solvable in one place.

**10. Treat WhatsApp pricing as a budget line.** Marketing templates
at $0.024 each scale fast. Build a pre-flight check that estimates
cost before any bulk send and short-circuits if over budget.

**11. Subscribe to `message_template_status_update`** so you find out
about template approvals/rejections in real time, not by polling.

**12. Use the **conversations** API (`/{page}/conversations`) for
inbox views** rather than reconstructing them from `messages` webhooks.
Way fewer API calls.

**13. For Threads, use `field=insights{views,likes,replies,reposts,quotes}`**
in a single request rather than separate insights calls per post.

**14. Capture `X-FB-Debug` and `X-FB-Rev` headers in your error logs.**
These give Meta enough info to find the exact server that handled your
request, which dramatically speeds up support tickets.

---

## EOS Usage Patterns

### Pattern 1 — Initiate Arena Messenger lead capture funnel

The Initiate Arena outreach strategy uses Instagram Reels and Threads
posts to drive interested users to DM "INITIATE" to the brand's IG/FB
inbox. EOS handles those DMs end-to-end:

1. User DMs "INITIATE" from an IG Reel CTA
2. Meta delivers the inbound to the EOS webhook endpoint
3. `services/discord_bot.py` (which doubles as the inbound DM router)
   parses the `messaging` event and writes a row to Neon
   `meta_dm_inbox` keyed by PSID
4. The auto-reply primitive (`eos_ai/primitives.py:reply_to_dm`) sends
   a `messaging_type=RESPONSE` message inside the 24h window with the
   founder-style intro and a calendly-style booking link
5. The qualification primitive checks the user's IG public profile for
   follower count, bio keywords, country
6. Inbound messages older than 24h fall back to `HUMAN_AGENT` tag
   (requires the `human_agent` permission, separately reviewed)
7. All conversation history syncs to the EOS CRM in `03_CRM/`

The crucial design choices:

- **PSID is the primary key**, not the user's name (which can change)
- **Token loaded from Neon at request time**, never from env
- **Auto-replies are tagged as automated** in the CRM so the founder
  knows what was machine vs hand-crafted

### Pattern 2 — Cross-platform organic publishing pipeline

Antony writes one post in Notion (the canonical source). EOS picks it
up, adapts it per platform, and publishes to FB Page + IG + Threads in
parallel:

1. `eos_ai/orchestrator.py` polls the Notion content DB every 5 min
   for rows with `status=ready_to_publish`
2. The post text and media URLs are pulled into a `Publication` record
3. The `world_pulse` cross-poster forks one task per surface
4. Each fork uses the appropriate creation endpoint (see Recipe A)
5. Result IDs (FB post ID, IG post ID, Threads post ID) are written
   back to Notion
6. Webhook events arriving later (likes, comments, replies) hydrate
   into the Notion row's `engagement` field for the founder's morning
   brief

The crucial design choices:

- **One source of truth (Notion)**, multiple projections (each Meta surface)
- **Idempotent on re-runs** — the publish call is wrapped in a check
  for existing post IDs in Notion
- **Failures don't block the other surfaces** — Threads going down
  doesn't stop the FB+IG publish
- **Version pinned in `eos_ai/meta_constants.py`**, never inline

### Pattern 3 — WhatsApp Business international outreach (staged)

Reserved for after Initiate Arena hits $10K/month. The plan:

1. Register a dedicated WhatsApp Business phone number under the
   Lyfe Institute Business Manager
2. Create a System User with `whatsapp_business_messaging`
3. Submit 3-5 utility templates for approval (booking confirmation,
   onboarding info, session reminder)
4. Build an outreach pipeline that imports leads from the Initiate
   Arena CRM, sends a single utility template ("hi, here's your
   onboarding info"), then drops into the 24h customer service window
   for free conversation
5. Pre-flight cost check on every batch (max $X/day budget enforced
   in `eos_ai/budget.py`)
6. Quality rating monitored daily — drop below GREEN and the pipeline
   pauses automatically

WhatsApp is **not** the bootstrapping channel. It's the international
expansion lever once US English DMs are working.

### Pattern 4 — Daily token health cron

```bash
# /opt/OS/scripts/scheduled/meta_token_health.sh
#!/bin/bash
cd /opt/OS && python3 -c "
from eos_ai.meta_health import check_all_tenant_tokens
check_all_tenant_tokens()
"
```

Runs at 6am UTC daily. Calls `debug_token` against every stored Meta
token (Page tokens + System User tokens + Threads tokens), alerts to
Discord if any are within 7 days of expiry, invalid, or have a
`data_access_expires_at` < 7 days.

### Pattern 5 — Webhook shock absorber

Meta webhooks bursts are spiky — a viral post can deliver hundreds of
events per second. EOS pattern:

- Webhook handler does ONE thing: validate signature, push raw payload
  to a Postgres `meta_webhook_inbox` table, return 200
- A separate worker process drains the inbox, deduplicates on
  `(entry.id, time, change)`, and dispatches to handlers
- Worker is the only thing that can fail — webhook endpoint is
  near-zero-latency and never returns non-200 unless the signature
  fails

This pattern is the canonical "responding fast to async bursts"
pattern in EOS and is the same shape as the Discord bot's event handler.

---

## Gotchas

(Real failures observed by EOS or documented in the Meta forums.)

- **`/me/accounts` returns empty even though the user is a Page admin.**
  The user must have `pages_show_list` granted. Standard Login dialog
  doesn't request this by default. Add it to the scope list.
- **Page token works for `/me` but not for `/{page}/feed`.** The token
  has `pages_show_list` but not `pages_manage_posts`. Re-auth with the
  publishing scope and re-fetch via `/me/accounts`.
- **A token that worked yesterday returns subcode 458 today.** The user
  changed their Facebook password. Re-auth required, no way around it.
- **Webhook never fires for Page feed events.** You subscribed the App
  to the `page` object via `/{app-id}/subscriptions` but forgot to also
  POST to `/{page-id}/subscribed_apps` — the per-asset opt-in. Both
  layers required.
- **Webhook fires twice for the same event.** Always. Meta retries on
  any non-200 AND sometimes sends duplicates anyway. Idempotent
  handlers are mandatory.
- **`error.code=10` "permission denied"** on a Page edge — the Page
  is in restricted/published-page state. Check Page Settings → General →
  Page Visibility.
- **Send API returns 200 but the message never arrives in Messenger.**
  The 24-hour window expired. The 200 means the API accepted the
  request, not that delivery succeeded. Watch the `message_deliveries`
  webhook field.
- **WhatsApp template POST returns 200 but webhook reports `failed`.**
  Variable count in `components.parameters` doesn't match the template
  body. Templates are strict.
- **WhatsApp `messages` webhook never fires.** You forgot to subscribe
  the WBA to the `messages` field via
  `/{wba-id}/subscribed_apps?subscribed_fields=messages`.
- **Threads `creation_id` returns "media not ready"** when you publish
  too fast. Threads needs ~1-3 seconds to process the container. Sleep
  or poll `/{creation-id}?fields=status` until `FINISHED`.
- **Threads token from Facebook Login dialog doesn't work.** Threads
  uses its own OAuth flow at `threads.net`. Facebook tokens are
  different scope.
- **`?fields=...{nested.limit(100)}`** silently truncates to ~25.
  Field-expanded edges have lower default limits than top-level lists.
- **`access_token` URL param shows up in webhook server access logs.**
  Strip it before logging. Better: pass in body for POSTs.
- **Insights metric returns empty array even though the data should
  exist.** The metric was deprecated in your pinned API version. Check
  the changelog for the version.
- **`/me` resolves to a different account in cron than in interactive
  use.** Cron has a different stored token. Always use explicit IDs.
- **`X-App-Usage` says 0% but you're getting 613 errors.** Per-page or
  per-business limits are independent of per-app. Check
  `X-Page-Usage` and `X-Business-Use-Case-Usage` too.
- **Batch request returns 200 with sub-requests showing 500.** The
  batch endpoint always returns 200; you must inspect each sub-request's
  `code` field.
- **WhatsApp Cloud API rejects all messages with "phone number not
  registered."** You forgot the `POST /{phone-number-id}/register`
  one-time setup step after migrating from a test number.
- **`appsecret_proof` mismatch returns confusing 100 error.** Generate
  it as `hmac_sha256(access_token, app_secret)` hex. Common bug:
  encoding the wrong half.
- **App Review screencast rejected for "showing too much / too little."**
  Reviewers want to see EXACTLY the user-facing flow that triggers the
  permission. Record on a real device, narrate, keep under 2 minutes.
- **A Page admin removed the app and webhooks stopped silently.** No
  callback for app removal — you find out when calls start failing
  with subcode 467. Check `debug_token` daily.
- **`graph.threads.net` rejected your token with "OAuthException."**
  You sent a Facebook token to the Threads host. Different host =
  different token issuer.
- **System User token leaked in a screenshot for support.** Rotate
  immediately. Never expires = forever-valid attack surface.
- **Meta Business Manager UI logged you out of the Test Users console.**
  Test users live under the App Dashboard → Roles → Test Users, not BM.
  Easy to look in the wrong place.
- **Page Insights `page_fans` returns yesterday's value at 6am.** The
  metric updates ~once per day, not in real time. Use
  `followers_count` on the Page node for live numbers.
- **A working integration broke after September 9, 2025.** You were
  pinned to v21.0 or earlier; Meta blocks anything below v22.0 since
  that date. Bump to v23.0 minimum.
- **Webhook callback URL must be HTTPS with a valid cert.** Self-signed
  certs are rejected. Let's Encrypt or commercial.
- **`POST /{wba-id}/message_templates` returns 200 but the template
  is in PENDING forever.** Some categories require additional business
  verification (display name verification, business verification).
  Check Business Manager → Security Center.
- **Threads insights metrics appear with 0 values for the first ~24h
  after publishing.** Backfill is delayed. Wait, then re-query.
