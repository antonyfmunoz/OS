---
name: notion-api
description: Use when reading from or writing to Notion via the API — pages, databases, blocks, or morning brief publishing.
allowed-tools: Bash, Read
---

# Notion API — Best Practices

## When to use this skill
Any time you are reading from or writing to Notion via the API.

## Key patterns

### Always check connection first
```python
from dotenv import load_dotenv
load_dotenv('/opt/OS/eos_ai/.env')
import os
key = os.getenv('NOTION_API_KEY')
if not key:
    print('NOTION_API_KEY not set')
    return
from notion_client import Client
client = Client(auth=key)
```

### Page IDs
All page IDs stored in `eos_ai/.env` as `NOTION_*_ID` variables.
Always load from env — never hardcode.

```python
ROOT_ID      = os.getenv('NOTION_ROOT_ID')
LYFE_ID      = os.getenv('NOTION_LYFE_INSTITUTE_ID')
EMPYREAN_ID  = os.getenv('NOTION_EMPYREAN_CREATIVE_ID')
BRAND_ID     = os.getenv('NOTION_PERSONAL_BRAND_ID')
BRIEF_ID     = os.getenv('NOTION_MORNING_BRIEF_ID')
ACTIVITY_ID  = os.getenv('NOTION_ACTIVITY_ID')
```

### Rate limits
Notion API: 3 requests/second average.
For bulk operations use `time.sleep(0.35)` between requests to avoid 429 errors.

### Block limits
Max 100 children per append call.
Split large content into chunks of 2000 chars per text block.

### Content blocks
Standard helpers:

```python
def text_block(content):
    return {
        'object': 'block', 'type': 'paragraph',
        'paragraph': {'rich_text': [{'type': 'text',
            'text': {'content': content[:2000]}}]}
    }

def heading_block(content, level=2):
    h = f'heading_{level}'
    return {'object': 'block', 'type': h,
        h: {'rich_text': [{'type': 'text',
            'text': {'content': content}}]}}

def callout_block(content, emoji='💡'):
    return {'object': 'block', 'type': 'callout',
        'callout': {'rich_text': [{'type': 'text',
            'text': {'content': content}}],
            'icon': {'type': 'emoji', 'emoji': emoji}}}

def divider_block():
    return {'object': 'block', 'type': 'divider', 'divider': {}}
```

### Appending to existing pages
Use `blocks.children.append` not `pages.create` when adding to existing content:

```python
client.blocks.children.append(
    block_id=page_id,
    children=[text_block(content)]
)
```

### Creating databases
Always include `type` in parent:

```python
client.databases.create(
    parent={'type': 'page_id', 'page_id': parent_id},
    title=[{'type': 'text', 'text': {'content': title}}],
    properties={...}
)
```

### Finding existing pages before creating
```python
results = client.search(
    query='Page Title',
    filter={'value': 'page', 'property': 'object'}
)
existing = [r for r in results.get('results', [])
    if any(t.get('plain_text') == 'Page Title'
        for t in r.get('properties', {})
            .get('title', {}).get('title', []))]
```

### Updating page title
```python
client.pages.update(
    page_id=page_id,
    properties={'title': [{'type': 'text',
        'text': {'content': 'New Title'}}]}
)
```

### Error handling
All Notion calls can fail silently.
Always wrap in try/except and log with `[Notion]` prefix.

## Auto-update triggers
EOS should update Notion when:
- Stage advances → update Stage Guidance page
- Pipeline moves → update Pipeline DB
- Morning brief fires → append to Morning Brief page
- War room runs → append to War Room page
- Agent activity → append to Activity Log page

## Common mistakes
- Hardcoding page IDs instead of reading from env
- Not rate limiting bulk operations (429 errors)
- Creating duplicate pages instead of finding existing ones first
- Missing `type` in database parent (`'type': 'page_id'`)
- Forgetting to share pages with the integration in Notion UI
- Exceeding 100-block limit in single create/append call
