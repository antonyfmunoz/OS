# Notion API — Best Practices (Creator-Level Reference)

Source: Notion API documentation + EOS production experience
Version: Notion API 2022-06-28
Last Researched: 2026-04-04

---

## 1. Authentication

### Integration token
```python
# Internal integration token (starts with ntn_)
NOTION_API_KEY = os.getenv("NOTION_API_KEY")

# HTTP headers — required on every request
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}
```

Token generated at: notion.so/my-integrations.
Each integration must be explicitly shared with pages/databases in Notion UI.

### Python SDK
```python
from notion_client import Client

notion = Client(auth=os.getenv("NOTION_API_KEY"))
# Automatically sets Content-Type and Notion-Version headers
```

### Scoping
Integrations only access pages/databases explicitly shared with them.
Sharing is done in Notion UI: page/database > Share > Invite > select integration.
Child pages of shared parents are automatically accessible.

---

## 2. Core Operations with Exact Signatures

### Query database
```
POST https://api.notion.com/v1/databases/{database_id}/query

Request body:
{
    "filter": {
        "property": "Status",
        "select": {"equals": "Active"}
    },
    "sorts": [
        {"property": "Created", "direction": "descending"}
    ],
    "page_size": 100,           // max 100
    "start_cursor": "cursor..."  // for pagination
}

Response:
{
    "object": "list",
    "results": [
        {
            "object": "page",
            "id": "page-uuid",
            "created_time": "2026-04-04T...",
            "last_edited_time": "2026-04-04T...",
            "properties": { ... }
        }
    ],
    "has_more": true,
    "next_cursor": "cursor-string"
}
```

### Create page
```
POST https://api.notion.com/v1/pages

Request body:
{
    "parent": {"database_id": "db-uuid"},
    "properties": {
        "title": {"title": [{"text": {"content": "Page Title"}}]},
        "Status": {"select": {"name": "Active"}},
        "Priority": {"select": {"name": "High"}},
        "Due Date": {"date": {"start": "2026-04-05"}},
        "Tags": {"multi_select": [{"name": "urgent"}, {"name": "sales"}]},
        "URL": {"url": "https://example.com"},
        "Email": {"email": "user@example.com"},
        "Number": {"number": 42},
        "Checkbox": {"checkbox": true}
    },
    "children": [
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "Section Title"}}]
            }
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": "Body text here..."}}]
            }
        }
    ]  // max 100 blocks per create
}

Response:
{
    "object": "page",
    "id": "new-page-uuid",
    "url": "https://www.notion.so/..."
}
```

### Update page properties
```
PATCH https://api.notion.com/v1/pages/{page_id}

Request body:
{
    "properties": {
        "Stage": {"select": {"name": "Booked"}},
        "Last Contact": {"date": {"start": "2026-04-04"}},
        "Notes": {"rich_text": [{"text": {"content": "Updated notes"}}]}
    }
}
```

### Append blocks to page
```
PATCH https://api.notion.com/v1/blocks/{block_id}/children

Request body:
{
    "children": [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": "New content"}}]
            }
        }
    ]
}
```

### Retrieve page
```
GET https://api.notion.com/v1/pages/{page_id}

Response includes properties but NOT block content.
Use GET /v1/blocks/{page_id}/children to get content blocks.
```

### Search
```
POST https://api.notion.com/v1/search

Request body:
{
    "query": "search term",
    "filter": {"value": "page", "property": "object"},
    "sort": {"direction": "descending", "timestamp": "last_edited_time"},
    "page_size": 10
}
```

---

## 3. Pagination Patterns

### Cursor-based pagination
```python
all_results = []
start_cursor = None

while True:
    payload = {"page_size": 100}
    if start_cursor:
        payload["start_cursor"] = start_cursor
    
    resp = requests.post(
        f"https://api.notion.com/v1/databases/{db_id}/query",
        headers=headers,
        json=payload,
        timeout=15,
    )
    data = resp.json()
    all_results.extend(data.get("results", []))
    
    if not data.get("has_more"):
        break
    start_cursor = data.get("next_cursor")
```

### EOS pattern (no pagination needed)
```python
# EOS queries use page_size=50-100, which covers all current databases
# No pagination logic in notion_publisher.py or notion_tasks_sync.py
resp = requests.post(url, headers=headers, json={"page_size": 50}, timeout=15)
pages = resp.json().get("results", [])
```

---

## 4. Rate Limits

### API rate limit
```
3 requests per second per integration

429 Too Many Requests response when exceeded.
Retry-After header may be included.
```

### EOS rate patterns
```python
# notion_publisher.py: 1-5 API calls per brief publish
#   - Find existing page (1 call)
#   - Create page (1 call)
#   - Fallback: try second DB (1-2 calls)
# Total: 2-5 calls per publish, well under 3/s

# notion_tasks_sync.py: 3 databases × 1 query each
# Runs every 15 minutes — 3 calls per 15 min cycle

# calendly_webhook.py: 2 calls per booking
#   - Query database to find lead (1 call)
#   - Update page properties (1 call)
```

### Retry strategy (not implemented in EOS)
```python
# Recommended but not currently in EOS code:
import time

def notion_request(method, url, **kwargs):
    for attempt in range(3):
        resp = requests.request(method, url, headers=headers, **kwargs)
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 1))
            time.sleep(retry_after)
            continue
        return resp
    return resp
```

---

## 5. Error Codes and Recovery

### HTTP status codes
| Code | Meaning | Recovery |
|------|---------|----------|
| 200 | Success | — |
| 400 | Bad request (invalid property, schema mismatch) | Check property names and types |
| 401 | Unauthorized (invalid/expired token) | Regenerate token at notion.so/my-integrations |
| 403 | Forbidden (integration not shared with page) | Share page with integration in Notion UI |
| 404 | Not found (wrong ID or integration not shared) | Verify database/page ID |
| 409 | Conflict (concurrent edit) | Retry after delay |
| 429 | Rate limited | Wait and retry (respect Retry-After header) |
| 500 | Internal server error | Retry after delay |
| 502 | Bad gateway | Retry after delay |
| 503 | Service unavailable | Retry after delay |

### Error response format
```json
{
    "object": "error",
    "status": 400,
    "code": "validation_error",
    "message": "Could not find property with name or id: status"
}
```

### Common error codes
| code | Meaning |
|------|---------|
| `validation_error` | Invalid property name, type mismatch, or schema error |
| `object_not_found` | Page/database ID not found or not shared |
| `unauthorized` | Invalid integration token |
| `restricted_resource` | Integration lacks permission |
| `rate_limited` | Too many requests |
| `internal_server_error` | Notion server issue |

### EOS error handling
```python
# notion_publisher.py — silent failure with fallback
result = _api_call("POST", "/pages", payload)
page_id = result.get("id", "")
if not page_id:
    # Primary DB failed — try fallback
    logger.warning(f"[NotionPublisher] Page creation failed for DB {parent_db_id}")
    fallback_db = _get_db_id(venture_id, "DOCUMENTS")
    if fallback_db:
        result = _api_call("POST", "/pages", payload_with_fallback_db)

# calendly_webhook.py — log and continue
if resp.status_code != 200:
    return False
```

---

## 6. SDK Idioms

### EOS uses raw HTTP (urllib.request), not notion-client SDK
```python
# notion_publisher.py — uses urllib.request directly
def _api_call(method, endpoint, payload=None):
    url = f"https://api.notion.com/v1{endpoint}"
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())

# calendly_webhook.py and notion_tasks_sync.py — use requests library
resp = requests.post(url, headers=headers, json=payload, timeout=15)
```

**Why two HTTP libraries?**
- `notion_publisher.py` uses `urllib.request` to avoid an extra import
- Other modules already have `requests` imported for other HTTP calls
- Both work identically for Notion's REST API

### Block builder pattern (EOS)
```python
# notion_publisher.py defines helper functions for building blocks:

def _heading(text, level=2):
    h_type = f"heading_{min(max(level, 1), 3)}"
    return {
        "object": "block",
        "type": h_type,
        h_type: {"rich_text": [{"type": "text", "text": {"content": text[:100]}}]},
    }

def _paragraph(text):
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": text[:2000]}}]
        },
    }

def _divider():
    return {"object": "block", "type": "divider", "divider": {}}

def _bulleted(text):
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [{"type": "text", "text": {"content": text[:2000]}}]
        },
    }
```

### DB ID resolution pattern
```python
# Venture-specific → generic fallback
_VENTURE_PREFIXES = {
    "personal_brand": "NOTION_PERSONAL_BRAND",
    "lyfe_institute": "NOTION_LYFE_INSTITUTE",
    "empyrean_creative": "NOTION_EMPYREAN_CREATIVE",
}

def _get_db_id(venture_id, db_type):
    prefix = _VENTURE_PREFIXES.get(venture_id, "")
    if prefix:
        db_id = os.getenv(f"{prefix}_{db_type.upper()}_DB")
        if db_id:
            return db_id
    return os.getenv(f"NOTION_{db_type.upper()}_DB", "")
```

---

## 7. Anti-Patterns

### 1. Property name case mismatch
```python
# WRONG — Notion properties are case-sensitive
{"properties": {"status": {"select": {"name": "Active"}}}}

# RIGHT — match exact case from database schema
{"properties": {"Status": {"select": {"name": "Active"}}}}
```

### 2. Exceeding 100 blocks per create
```python
# WRONG — silently drops blocks after 100
_create_page(db_id, title, blocks)  # blocks has 150 items

# RIGHT — slice to limit, or use append for overflow
_create_page(db_id, title, blocks[:100])
# Then append remaining:
# PATCH /v1/blocks/{page_id}/children with blocks[100:200]
```

### 3. Rich text over 2000 characters
```python
# WRONG — API returns 400
{"rich_text": [{"text": {"content": long_string}}]}

# RIGHT — truncate to limit
{"rich_text": [{"text": {"content": text[:2000]}}]}
# EOS: _paragraph(text) already handles this
```

### 4. Polling without backoff
```python
# WRONG — hammers API checking for changes
while True:
    changes = query_database(db_id)
    process(changes)
    time.sleep(1)

# RIGHT — reasonable poll interval
# EOS: 15-minute cron cycle for task sync
```

### 5. Not sharing integration with database
```python
# WRONG — creates integration, immediately calls API
notion = Client(auth=new_token)
notion.databases.query(database_id=db_id)  # 404!

# RIGHT — must share in Notion UI first
# Database > Share > Invite > select integration name
```

### 6. Building custom Notion writers
```python
# WRONG — duplicating NotionPublisher functionality
def my_custom_notion_write(db_id, content):
    requests.post("https://api.notion.com/v1/pages", ...)

# RIGHT — use the canonical publisher
from eos_ai.notion_publisher import get_publisher
publisher = get_publisher(ctx)
url = publisher.publish_morning_brief(content)
```

---

## 8. Data Model

### Property types
| Type | JSON Shape | Example |
|------|-----------|---------|
| `title` | `{"title": [{"text": {"content": "..."}}]}` | Page name |
| `rich_text` | `{"rich_text": [{"text": {"content": "..."}}]}` | Text fields |
| `select` | `{"select": {"name": "Option"}}` | Single choice |
| `multi_select` | `{"multi_select": [{"name": "Tag1"}, ...]}` | Multiple tags |
| `date` | `{"date": {"start": "2026-04-04", "end": null}}` | Date/range |
| `number` | `{"number": 42}` | Numeric value |
| `checkbox` | `{"checkbox": true}` | Boolean |
| `url` | `{"url": "https://..."}` | URL |
| `email` | `{"email": "user@example.com"}` | Email |
| `phone_number` | `{"phone_number": "+1234567890"}` | Phone |
| `people` | `{"people": [{"id": "user-uuid"}]}` | Notion users |
| `files` | `{"files": [{"name": "file.pdf", "external": {"url": "..."}}]}` | Attachments |
| `relation` | `{"relation": [{"id": "page-uuid"}]}` | Cross-DB links |
| `formula` | (read-only) | Computed values |
| `rollup` | (read-only) | Aggregated values |
| `status` | `{"status": {"name": "In Progress"}}` | Status field |

### Block types
| Type | Structure |
|------|-----------|
| `paragraph` | `{"rich_text": [...]}` |
| `heading_1/2/3` | `{"rich_text": [...]}` |
| `bulleted_list_item` | `{"rich_text": [...]}` |
| `numbered_list_item` | `{"rich_text": [...]}` |
| `to_do` | `{"rich_text": [...], "checked": false}` |
| `toggle` | `{"rich_text": [...]}` |
| `code` | `{"rich_text": [...], "language": "python"}` |
| `divider` | `{}` |
| `callout` | `{"rich_text": [...], "icon": {"emoji": "..."}}` |
| `quote` | `{"rich_text": [...]}` |
| `image` | `{"external": {"url": "..."}}` |
| `bookmark` | `{"url": "..."}` |
| `table_of_contents` | `{}` |

### EOS database schema (typical)
```
Tasks DB:
  Name (title) | Status (select) | Priority (select) | Type (select) |
  Due Date (date) | Assignee (people) | Notes (rich_text)

Pipeline CRM DB:
  Name (title) | Stage (select) | Email (email) | Source (select) |
  Last Contact (date) | Notes (rich_text) | Score (number)

Documents DB:
  Name (title) | Type (select) | Date (date) | Content (rich_text)
```

---

## 9. Webhooks and Events

### Notion has no native webhooks
Notion does not provide webhook functionality.
To detect changes, you must poll databases.

### EOS polling pattern
```python
# scripts/notion_tasks_sync.py — runs every 15 minutes via cron
# Polls 3 venture task databases
# Compares against last sync state (stored in notion_tasks_sync_state.json)
# New/updated tasks → write to Neon events table

STATE_FILE = Path("/opt/OS/scripts/notion_tasks_sync_state.json")

def load_state():
    return json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {"synced": {}}

# State tracks which page IDs have been synced and their last_edited_time
```

### Third-party alternatives (not used by EOS)
- **Notion API webhooks (beta):** May be available in future Notion API versions
- **Pipedream/Zapier:** Can poll Notion and trigger webhooks
- **Make.com:** Can watch Notion databases and trigger actions

---

## 10. Limits

### API limits
| Resource | Limit |
|----------|-------|
| Rate limit | 3 requests/second per integration |
| Page size (query) | 100 results max per request |
| Blocks per create | 100 blocks max per page creation |
| Rich text content | 2000 characters per text block |
| Heading content | 100 characters per heading |
| Title content | 2000 characters |
| Nested blocks | 2 levels deep in create |
| File upload | No direct upload — external URLs only |
| Search results | 100 per request |
| Database items | No hard limit (millions supported) |

### EOS usage (well within limits)
```
Morning brief: ~15-25 blocks, 2-3 API calls
Task sync: 3 databases × 1 query = 3 API calls per 15 min
CRM update: 2 API calls per booking event
Total daily: ~50-100 API calls (vs 259,200 allowed at 3/s)
```

---

## 11. Cost Model

### Notion API pricing
**Free.** The Notion API is free for all Notion plans.
No per-call charges, no usage-based pricing.
Rate limit (3/s) is the only constraint.

### Notion workspace pricing
| Plan | Price | API Access |
|------|-------|------------|
| Free | $0 | Yes, 3 req/s |
| Plus | $10/user/month | Yes, 3 req/s |
| Business | $18/user/month | Yes, 3 req/s |
| Enterprise | Custom | Yes, higher limits possible |

EOS uses a single Notion workspace (likely Plus or Free tier).

---

## 12. Version Pinning

### API version
```
# Set via header on every request
Notion-Version: 2022-06-28

# This is the current stable version
# Notion announces breaking changes well in advance
# EOS hardcodes this version — no need to update frequently
```

### Python SDK
```bash
pip install notion-client  # Latest
pip install notion-client==2.2.0  # Pinned

# EOS does not use the SDK — uses urllib/requests directly
```

### Database schema versioning
Notion databases have no explicit versioning.
Adding/removing/renaming properties is immediate and can break API calls.
**Best practice:** Document expected property names in SKILL.md/comments.

---

## 13. Design Intent and Tradeoffs

### Why Notion for EOS content delivery
Notion provides a rich, formatted, shareable interface that the founder already uses daily.
Rather than building a custom dashboard, EOS writes content to Notion where it's naturally consumed.

**Tradeoffs:**
- Pro: Rich formatting (headings, lists, dividers), shareable URLs, mobile access
- Pro: No custom UI needed — Notion IS the UI
- Con: No webhooks — must poll for changes
- Con: 100 blocks per create limit
- Con: Integration must be manually shared with each database

### Why raw HTTP over notion-client SDK
EOS uses urllib/requests for Notion calls because:
1. Fewer dependencies
2. Consistent error handling pattern across all EOS HTTP calls
3. Full visibility into request/response
4. NotionPublisher is simple enough not to need SDK abstractions

### Why NotionPublisher as singleton pattern
All Notion writes go through one module (`notion_publisher.py`).
This prevents scattered Notion API calls across the codebase and ensures
consistent block building, error handling, and DB ID resolution.

---

## 14. Problem-Solution Map and Hidden Capabilities

### DB ID becomes invalid
**Problem:** Database deleted or integration unshared in Notion.
**Solution:** `_create_page()` logs warning and returns "". NotionPublisher
has fallback logic — tries `DOCUMENTS` DB if primary fails.

### Content too long for single page create
**Problem:** 100 block limit per create call.
**Solution:** EOS briefs are typically <30 blocks. For longer content,
would need to create page first, then append blocks in batches.
```python
# Not currently needed, but pattern:
_create_page(db_id, title, blocks[:100])
# Then: PATCH /v1/blocks/{page_id}/children with blocks[100:200]
```

### Finding existing page to avoid duplicates
**Problem:** Don't want duplicate briefs for the same date.
**Solution:** `_find_page_by_title()` queries by exact title match before creating.
```python
existing = _find_page_by_title(db_id, f"Daily Brief — {today}")
if existing:
    return existing  # Return URL of existing page
```

### Notion page URL from page ID
```python
def _page_url(page_id):
    return f"https://notion.so/{page_id.replace('-', '')}"
```

---

## 15. Operational Behavior and Edge Cases

### Properties are returned differently than set
When reading a page, properties come back in their full type envelope.
For example, a title property returns:
```json
{"title": [{"type": "text", "text": {"content": "My Title"}, "plain_text": "My Title"}]}
```
You need to traverse `properties["Name"]["title"][0]["text"]["content"]` to get the text.

### Empty rich_text arrays
If a text property has no content, it returns `{"rich_text": []}`, not `null`.
Always check `len(rich_text) > 0` before accessing `[0]`.

### Notion-Version header is required
Omitting the `Notion-Version` header returns 400. Must be on every request.
Current version: `2022-06-28`.

### Database query returns all pages (including archived)
By default, queries return archived pages too. Filter with:
```json
{"filter": {"property": "object", "value": "page"}}
```
Or check `page.get("archived") == False` in results.

### Select options must exist
When setting a `select` property, the option must already exist in the database.
Creating a page with a non-existent select value returns 400.
**Exception:** If the option name matches an existing one case-insensitively.

---

## 16. Ecosystem Position and Composition

### Where Notion fits in EOS
```
EOS Intelligence Layer
  └── NotionPublisher (write)
        ├── Morning brief → Brief DB
        ├── Intel brief → Brief DB
        ├── Constraint diagnosis → Documents DB
        ├── Portfolio status → Documents DB
        ├── EOD sync → Brief DB
        └── CEO delegation → Brief DB

  └── notion_tasks_sync.py (read)
        └── 3 venture Task DBs → Neon events table

  └── calendly_webhook.py (read/write)
        └── Pipeline CRM DB → update lead stage

Founder → Notion UI → reads briefs, manages tasks, reviews CRM
```

### Interfaces
- **With Neon:** Task sync writes to Neon events table
- **With Discord:** Brief URLs posted to Discord channels
- **With Calendly:** Webhook handler updates CRM pipeline
- **With orchestrator:** Morning cycle triggers brief publish
- **With model_router:** AI generates brief content, NotionPublisher formats and delivers

---

## 17. Trajectory and Evolution

### Current state (2026-04)
- NotionPublisher: canonical write pattern for 6 content types
- Task sync: 3-database polling every 15 minutes
- CRM updates: webhook-triggered via Calendly
- No webhooks (polling only)

### Potential improvements
- **Notion API webhooks:** When available, replace polling with real-time sync
- **Richer content:** Use callouts, code blocks, toggles for more structured briefs
- **Two-way sync:** Currently one-directional (EOS → Notion). Could sync Notion edits back to Neon
- **notion-client SDK:** Would simplify error handling and pagination
- **Block append:** For content exceeding 100 blocks

### Dependencies
- Notion API stability (version 2022-06-28)
- Integration sharing (manual step per database)
- Workspace plan (API access on all plans)

---

## 18. Conceptual Model and Solution Recipes

### Mental model: Notion as EOS's user interface
Think of Notion not as a database but as EOS's primary UI for the founder.
Every brief, every CRM update, every task sync — the founder consumes it in Notion.
EOS writes structured content. The founder reads it in a rich, formatted view.

### Recipe: Add a new content type to NotionPublisher
```python
# 1. Add env var for target database
# In eos_ai/.env:
NOTION_NEW_TYPE_DB=database_uuid

# 2. Add method to NotionPublisher
class NotionPublisher:
    def publish_new_type(self, content: dict) -> str:
        today = date.today()
        title = f"New Type — {today}"
        db_id = os.getenv("NOTION_NEW_TYPE_DB", "")
        if not db_id:
            db_id = _get_db_id("lyfe_institute", "DOCUMENTS")
        if not db_id:
            return ""
        
        existing = _find_page_by_title(db_id, title)
        if existing:
            return existing
        
        blocks = [
            _heading(title, level=1),
            _divider(),
            _paragraph(content.get("body", "")),
        ]
        return _create_page(db_id, title, blocks)

# 3. Share the database with the integration in Notion UI
# 4. Test: publisher.publish_new_type({"body": "test"})
```

### Recipe: Debug "404 on database query"
```bash
# 1. Verify database ID is correct
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv('/opt/OS/eos_ai/.env')
print('DB ID:', os.getenv('NOTION_MORNING_BRIEF_ID'))
"

# 2. Test API call
curl -s 'https://api.notion.com/v1/databases/DB_ID' \
  -H 'Authorization: Bearer ntn_...' \
  -H 'Notion-Version: 2022-06-28' | python3 -m json.tool

# 3. If 404: integration not shared with database
# Go to Notion > Database > Share > Invite > select integration

# 4. If 401: token invalid or expired
# Regenerate at notion.so/my-integrations
```

---

## 19. Industry Expert and Cutting-Edge Usage

### Notion as zero-UI application layer
EOS uses Notion as its entire frontend for the founder.
No custom web app, no dashboard, no mobile app — just Notion.
This is a deliberate choice: the founder already uses Notion daily,
so delivering content there has zero adoption friction.

### Multi-venture database architecture
```python
# Each venture has its own set of databases
_VENTURE_PREFIXES = {
    "personal_brand": "NOTION_PERSONAL_BRAND",
    "lyfe_institute": "NOTION_LYFE_INSTITUTE",
    "empyrean_creative": "NOTION_EMPYREAN_CREATIVE",
}

# DB ID resolution: venture-specific → generic fallback
# This allows per-venture content isolation with shared infrastructure
```

### Deduplication by title
NotionPublisher checks for existing pages with the same title before creating.
This prevents duplicate briefs when the morning cycle runs multiple times
(e.g., manual trigger after automatic cron).

### Fallback database chain
```python
# Primary: NOTION_MORNING_BRIEF_ID
# Fallback: NOTION_LYFE_INSTITUTE_DOCUMENTS_DB
# This handles the known issue where primary DB ID is dead
```

---

## 20. EOS Usage Patterns

### Database inventory
| Purpose | Env Variable | Used By |
|---------|-------------|---------|
| Morning Brief | `NOTION_MORNING_BRIEF_ID` | NotionPublisher |
| CRM Pipeline | `NOTION_LYFE_PIPELINE_ID` | calendly_webhook.py |
| Lyfe Tasks | `NOTION_YOUR_LIST_LYFE` | notion_tasks_sync.py |
| Empyrean Tasks | `NOTION_YOUR_LIST_EMPYREAN` | notion_tasks_sync.py |
| Brand Tasks | `NOTION_YOUR_LIST_BRAND` | notion_tasks_sync.py |
| LI Documents | `NOTION_LYFE_INSTITUTE_DOCUMENTS_DB` | NotionPublisher fallback |
| PB Documents | `NOTION_PERSONAL_BRAND_DOCUMENTS_DB` | Portfolio status |

### Daily Notion API usage
```
6:00 AM — Morning brief publish (~3 API calls)
6:00 AM — Task sync (#1 of 96/day, ~3 calls each)
Throughout day — Calendly webhook CRM updates (~2 calls per booking)
6:00 PM — EOD sync publish (~3 API calls)
Total: ~300-400 API calls/day
```

### Content flow
```
AI generates content (model_router)
  → NotionPublisher formats as blocks
    → Creates page in Notion DB
      → Returns page URL
        → URL posted to Discord
          → Founder reads in Notion
```

---

## 21. Gotchas (Real EOS Production Issues)

### NOTION_MORNING_BRIEF_ID points to dead database (ACTIVE)
The primary brief database ID is invalid or deleted.
**Symptom:** Warning log about page creation failure, brief appears in Documents DB.
**Fix:** Update `NOTION_MORNING_BRIEF_ID` in eos_ai/.env with valid database ID.
**Workaround:** Fallback to Documents DB works automatically.

### Integration not shared with database (COMMON)
Creating a Notion integration doesn't grant access to any database.
Each database must be shared manually in Notion UI.
**Symptom:** 404 on database query despite valid token.
**Fix:** Notion UI > Database > Share > Invite > select integration.

### Property names are case-sensitive (ACTIVE)
`Status` vs `status` — different properties. API returns 400 for wrong case.
**Fix:** Check exact property names in the Notion database before coding.

### 100 blocks per page create (BY DESIGN)
`_create_page()` uses `blocks[:100]`. Content beyond 100 blocks is dropped.
**Impact:** Extremely long briefs could be truncated. Currently not an issue.

### 2000 char limit per rich_text (BY DESIGN)
`_paragraph(text[:2000])` enforces the limit. Longer text is truncated.
**Impact:** Detailed analysis sections in briefs may lose tail content.

### No native webhooks (BY DESIGN)
Notion has no webhook system. EOS polls every 15 minutes.
**Impact:** Task changes in Notion take up to 15 minutes to appear in morning brief.

### urllib vs requests inconsistency (BY DESIGN)
`notion_publisher.py` uses `urllib.request`. Other modules use `requests`.
Both work but error handling differs. Not a bug — just architectural debt.

### Select option must exist in database (ACTIVE)
Setting a select property to a value that doesn't exist in the database
returns 400. Options must be pre-created in Notion UI or via API.
**Impact:** calendly_webhook.py's `update_notion_lead_stage()` may fail
if the stage name doesn't match an existing select option.
