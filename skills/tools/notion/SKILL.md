---
name: notion
description: "Use when any agent needs to read or write Notion databases, publish briefs, sync tasks, update CRM pipeline, or create structured pages."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://developers.notion.com/"
last_researched: "2026-04-09"
instantiated_from: templates/tools/_template/
api_version: "Notion API 2022-06-28"
sdk_version: "notion-client 2.x (Python) / REST API direct (EOS)"
speed_category: "fast"
---

# Tool: Notion

## What This Tool Does

The Notion API provides read/write access to pages, databases, blocks, and users. EOS uses Notion as the external delivery layer — morning briefs, pipeline CRM, task databases, meeting records, and all structured content the founder interacts with lives in Notion.

Core capabilities:
- **Database queries** — filter, sort, paginate database entries
- **Page creation** — create pages with properties and block content
- **Page updates** — modify properties on existing pages
- **Block operations** — append, read, update content blocks within pages
- **Search** — full-text search across workspace

## EOS Integration

### Primary: `eos_ai/notion_publisher.py` — Canonical write pattern

**All EOS content → Notion goes through NotionPublisher.** Never build a custom Notion writer.

```python
from eos_ai.notion_publisher import get_publisher

publisher = get_publisher(ctx)
url = publisher.publish_morning_brief(content=brief_dict)
# Returns: https://notion.so/...
# Discord then gets: f'Brief ready → {url}'
```

**Published content types:**
| Method | Content | DB Source |
|--------|---------|-----------|
| `publish_morning_brief()` | Daily brief (binding constraint, objectives, signals) | `NOTION_MORNING_BRIEF_ID` → fallback `DOCUMENTS` |
| `publish_intel_brief()` | Intelligence brief (overnight signals, market, opportunities) | Same as morning brief |
| `publish_constraint_diagnosis()` | Constraint analysis per venture | `NOTION_{VENTURE}_DOCUMENTS_DB` |
| `publish_portfolio_status()` | Multi-venture health report | `NOTION_PERSONAL_BRAND_DOCUMENTS_DB` |
| `publish_eod_sync()` | End-of-day sync (completed, open loops, wins, misses) | Same as morning brief |
| `publish_ceo_delegation()` | CEO agent delegation results | Same as morning brief |

**Block builders:**
```python
_heading(text, level=2)       # heading_1, heading_2, heading_3
_paragraph(text)               # text[:2000] — Notion limit
_divider()                     # horizontal rule
_bulleted(text)                # bulleted list item
_create_page(db_id, title, blocks[:100], extra_properties)  # 100 block limit
```

### Secondary: `scripts/notion_tasks_sync.py` — Task polling

Polls three venture Task databases every 15 minutes, syncs to Neon events table.
```python
DATABASES = {
    'lyfe_institute':    os.getenv('NOTION_YOUR_LIST_LYFE'),
    'empyrean_creative': os.getenv('NOTION_YOUR_LIST_EMPYREAN'),
    'personal_brand':    os.getenv('NOTION_YOUR_LIST_BRAND'),
}
```

### Tertiary: `services/calendly_webhook.py` — CRM updates
Updates lead stage in Notion Pipeline database when calls are booked/canceled.
```python
def update_notion_lead_stage(name, email, new_stage):
    # POST /v1/databases/{db_id}/query → find page by name
    # PATCH /v1/pages/{page_id} → update Stage select + Last Contact date
```

### Other modules that use Notion:
- `eos_ai/orchestrator.py` — morning cycle publishes briefs
- `eos_ai/daily_sync.py` — task sync
- `eos_ai/eod_closing_loop.py` — EOD sync
- `scripts/notion_seed.py` / `notion_seed_all.py` — database seeding
- `scripts/build_notion_databases.py` — workspace setup
- `scripts/notion_outcome_sync.py` — outcome tracking
- `scripts/notion_cleanup.py` — database maintenance

### Environment variables
| Variable | Purpose |
|----------|---------|
| `NOTION_API_KEY` | Integration token (Bearer auth) |
| `NOTION_MORNING_BRIEF_ID` | Brief database ID |
| `NOTION_LYFE_PIPELINE_ID` | CRM Pipeline database |
| `NOTION_YOUR_LIST_LYFE` | Lyfe Institute tasks DB |
| `NOTION_YOUR_LIST_EMPYREAN` | Empyrean Creative tasks DB |
| `NOTION_YOUR_LIST_BRAND` | Personal Brand tasks DB |
| `NOTION_LYFE_INSTITUTE_DOCUMENTS_DB` | Documents DB |
| `NOTION_PERSONAL_BRAND_DOCUMENTS_DB` | Portfolio/brand documents |

**DB ID resolution pattern:**
```python
# Venture-specific: NOTION_{VENTURE}_{TYPE}_DB
# Generic fallback: NOTION_{TYPE}_DB
db_id = os.getenv(f"{prefix}_{db_type}_DB") or os.getenv(f"NOTION_{db_type}_DB")
```

### Agents that use it
- DEX (via NotionPublisher — briefs, syncs)
- CEO Agent (via delegation reports)
- EA Agent (task sync, meeting records)
- Pipeline Handler (CRM updates)
- All agents indirectly (data lives in Notion)

## Authentication

```python
# Integration token in eos_ai/.env
NOTION_API_KEY=ntn_...   # Notion integration token

# HTTP headers (used by notion_publisher.py)
headers = {
    'Authorization': f'Bearer {token}',
    'Notion-Version': '2022-06-28',
    'Content-Type': 'application/json',
}

# Or via notion-client SDK
from notion_client import Client
notion = Client(auth=os.getenv("NOTION_API_KEY"))
```

Integration must be explicitly added to each database/page in Notion UI.
Token starts with `ntn_` prefix. Generated at notion.so/my-integrations.

## Quick Reference

### Query database
```python
resp = requests.post(
    f'https://api.notion.com/v1/databases/{db_id}/query',
    headers=headers,
    json={
        'filter': {'property': 'Status', 'select': {'equals': 'Active'}},
        'sorts': [{'property': 'Created', 'direction': 'descending'}],
        'page_size': 50,
    },
    timeout=15,
)
pages = resp.json().get('results', [])
```

### Create page with blocks
```python
payload = {
    'parent': {'database_id': db_id},
    'properties': {
        'title': {'title': [{'text': {'content': 'Page Title'}}]},
        'Status': {'select': {'name': 'Active'}},
    },
    'children': blocks[:100],  # Max 100 blocks per create
}
resp = requests.post('https://api.notion.com/v1/pages', headers=headers, json=payload)
page_url = f"https://notion.so/{resp.json()['id'].replace('-', '')}"
```

### Update page properties
```python
requests.patch(
    f'https://api.notion.com/v1/pages/{page_id}',
    headers=headers,
    json={
        'properties': {
            'Stage': {'select': {'name': 'Booked'}},
            'Last Contact': {'date': {'start': '2026-04-04'}},
        }
    },
)
```

## Gotchas

### NOTION_MORNING_BRIEF_ID points to dead DB (ACTIVE)
The primary brief database ID is invalid/deleted. NotionPublisher falls back to
the venture Documents DB (`NOTION_LYFE_INSTITUTE_DOCUMENTS_DB`).
**Symptom:** Warning log about primary DB failed, then brief appears in Documents DB.

### Integration not added to database returns 404 (COMMON)
Creating a Notion integration token doesn't automatically grant access to databases.
Each database must be shared with the integration via Notion UI (Share > Invite).
**Symptom:** 404 on database query despite valid token.

### Property names are case-sensitive (ACTIVE)
`'Status'` and `'status'` are different properties. Mismatched case returns 400.
**Fix:** Check exact property names in Notion database schema before API calls.

### 100 blocks per create limit (BY DESIGN)
`_create_page()` uses `blocks[:100]`. If content exceeds 100 blocks, remainder is silently dropped.
**Impact:** Very long briefs may be truncated. Not currently an issue (briefs are <30 blocks).

### 2000 character limit per rich_text content (BY DESIGN)
`_paragraph(text[:2000])` enforces the Notion API limit. Longer text is truncated.
**Impact:** Detailed analysis sections may lose content.

### Rate limit: 3 requests/second per integration (ACTIVE)
Sustained burst above 3 req/s triggers 429. No explicit backoff in `notion_publisher.py`.
**Mitigation:** EOS's usage pattern is bursty but low-volume (one brief = ~3 API calls).

### No native webhooks (BY DESIGN)
Notion has no webhook system. EOS polls task databases every 15 minutes via cron.
**Impact:** Task changes take up to 15 minutes to appear in Neon.

See references/best_practices.md for full API reference, property types, and anti-patterns.
