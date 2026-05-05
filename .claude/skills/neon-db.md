---
name: neon-db
description: Use when writing database queries, creating tables, or debugging Neon PostgreSQL issues in EOS.
allowed-tools: Bash, Read
---

# Neon PostgreSQL — Best Practices

## When to use
All database operations in EOS. Always use `get_conn()` from `eos_ai/db.py`.

## Connection pattern
```python
import sys
sys.path.insert(0, '/opt/OS')
from eos_ai.db import get_conn
from eos_ai.context import load_context_from_env

ctx = load_context_from_env()
with get_conn(ctx.org_id) as cur:
    cur.execute(query, params)
    results = cur.fetchall()
```

`get_conn()` yields a cursor — not a connection. The context manager handles commit and close.

## Critical: resolve_venture() must run inside get_conn() block
```python
# WRONG — venture cache loads inside get_conn, not outside
vid = resolve_venture(slug)
with get_conn(org_id) as cur:
    cur.execute('SELECT * FROM x WHERE venture_id=%s', (vid,))

# RIGHT
with get_conn(org_id) as cur:
    vid = resolve_venture(slug)
    cur.execute('SELECT * FROM x WHERE venture_id=%s', (vid,))
```

## Always use parameterized queries
```python
# WRONG — SQL injection risk
cur.execute(f"SELECT * FROM x WHERE id='{id}'")

# RIGHT
cur.execute("SELECT * FROM x WHERE id=%s", (id,))
cur.execute("SELECT * FROM x WHERE org_id=%s AND name=%s", (org_id, name))
```

## Multi-tenant isolation
Every query MUST include `org_id` filter — RLS enforces this at the DB level:
```python
cur.execute(
    "SELECT * FROM agents WHERE org_id = %s",
    (ctx.org_id,)
)
```

## Upsert pattern
```python
import uuid
cur.execute('''
    INSERT INTO table (id, org_id, field)
    VALUES (%s, %s, %s)
    ON CONFLICT (org_id, field)
    DO UPDATE SET field = EXCLUDED.field
''', (str(uuid.uuid4()), org_id, value))
```

## Key tables and their schemas

| Table | Key columns |
|---|---|
| `interactions` | id, org_id, venture_id, input, output, model, tokens |
| `agents` | id, org_id, name, type, department, soul_doc_path, is_active |
| `skills` | id, org_id, name, content, version |
| `human_profiles` | id, org_id, platform_id, platform, name, icp_score |
| `ventures` | id, org_id, name, slug, config_json |
| `events` | id, org_id, type, payload, created_at |
| `tasks` | id, org_id, venture_id, title, status, priority |
| `embeddings` | id, org_id, interaction_id, vector (768-dim) |

## Tables that do NOT exist
- `knowledge_domains` — in-memory only, do not query
- No `file_path` column on `skills` table

## JSON parsing from AI output
```python
import json
try:
    data = json.loads(text, strict=False)
except json.JSONDecodeError:
    # try extracting JSON from text
    import re
    m = re.search(r'\{.*\}', text, re.DOTALL)
    data = json.loads(m.group()) if m else {}
```

## Common mistakes
- Forgetting `org_id` in every query (RLS will block it)
- Using f-strings instead of parameterized queries
- Calling `resolve_venture()` outside `get_conn()` block
- Referencing `knowledge_domains` table (doesn't exist)
- Referencing `skills.file_path` column (doesn't exist)
