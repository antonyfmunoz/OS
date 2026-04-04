---
name: neon_postgres
description: "Use when any agent reads or writes persistent data, registers agents/skills, stores memory, or queries business state via Neon Postgres."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://neon.tech/docs"
last_researched: "2026-04-03"
instantiated_from: templates/tools/_template/
api_version: "PostgreSQL 16"
sdk_version: "psycopg2 2.9.11"
speed_category: fast
---

# Tool: Neon Postgres

## What This Tool Does

Neon is serverless Postgres. It separates storage and compute, enabling:

- **Autosuspend/autoscale** — compute spins down after inactivity (default 5 min), scales to zero cost, wakes on first connection (cold start ~500ms-2s).
- **Branching** — instant copy-on-write branches of the entire database for dev/test/preview without duplicating storage.
- **Point-in-time restore** — storage is append-only with WAL-based history, enabling restore to any point within the retention window.
- **Connection pooling** — built-in PgBouncer via `-pooler` endpoint (port 5432 pooled, port 5432 direct varies by region).
- **Standard Postgres** — wire-compatible PostgreSQL 14-17. All extensions, all SQL, all psycopg2 features work.

The driver is **psycopg2 2.9.11** (C-based, synchronous). Not asyncpg, not SQLAlchemy.

## EOS Integration

Neon is the ENTIRE persistence layer for EOS. Every module that stores or reads state goes through `eos_ai/db.py`.

### Connection module: `eos_ai/db.py`
- Single `get_conn(org_id)` context manager — opens connection, sets RLS, yields cursor, commits/closes
- RLS enforced via `SET LOCAL app.current_org_id = %s` on every transaction
- Uses `RealDictCursor` — all rows returned as dicts
- Caches venture and skill UUID lookups once per process
- Credentials stripped from error messages before logging

### Modules that use Neon (60+ files):
- **Core loop**: `cognitive_loop.py`, `gateway.py`, `agent_runtime.py`
- **Memory**: `memory.py` — all writes go to Neon (resolve_venture, resolve_skill, ORG_ID, USER_ID)
- **Business state**: `business_instance.py`, `strategy_engine.py`, `portfolio_advisor.py`, `execution_engine.py`
- **Agent system**: `agent_hierarchy.py`, `skill_registry.py`, `skill_improvement.py`, `agent_messages.py`
- **Knowledge**: `knowledge_integrator.py`, `knowledge_graph.py`, `knowledge_domains.py`, `embedding_engine.py`
- **Services**: `discord_bot.py`, `telegram_control.py`, `calendly_webhook.py`
- **Tracking**: `okr_tracker.py`, `delegation_tracker.py`, `expense_tracker.py`, `accountability.py`
- **Intelligence**: `ceo_intelligence.py`, `ceo_agent.py`, `competitive_intel.py`, `research_engine.py`

### Import pattern (universal across EOS):
```python
from eos_ai.db import get_conn, resolve_venture, resolve_skill, ORG_ID, USER_ID
```

### Usage pattern (universal across EOS):
```python
with get_conn() as cur:
    cur.execute("SELECT id, name FROM skills WHERE org_id = %s", (ORG_ID,))
    rows = cur.fetchall()
    # rows is list[dict] due to RealDictCursor
```

## Authentication

### Connection string
```
DATABASE_URL=postgresql://<user>:<password>@<project-id>.us-east-2.aws.neon.tech/<dbname>?sslmode=require
```

- **sslmode=require** — mandatory for Neon. Connections without SSL are rejected.
- **Pooled endpoint** — hostname contains `-pooler` suffix. Uses PgBouncer in transaction mode.
- **Direct endpoint** — no `-pooler`. Direct to compute. Required for: LISTEN/NOTIFY, prepared statements, session-level settings.
- Credentials stored in `/opt/OS/eos_ai/.env` as `DATABASE_URL`. Never hardcoded.

### RLS (Row Level Security)
Every transaction begins with:
```sql
SET LOCAL app.current_org_id = '<org_uuid>';
```
This scopes ALL queries to the tenant's data. The `SET LOCAL` is transaction-scoped — it resets on commit/rollback. RLS policies on every table enforce `current_setting('app.current_org_id') = org_id`.

### Environment variables
- `DATABASE_URL` — Neon connection string
- `EOS_ORG_ID` — default org UUID for RLS
- `EOS_USER_ID` — default user UUID for audit trails

## Quick Reference

### Insert with RETURNING
```python
with get_conn() as cur:
    cur.execute("""
        INSERT INTO interactions (org_id, user_id, channel, raw_input, agent_used, response)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (ORG_ID, USER_ID, 'discord', message, 'ceo', response))
    row = cur.fetchone()
    interaction_id = row['id']
```

### Parameterized query (NEVER use f-strings)
```python
# CORRECT — parameterized
cur.execute("SELECT * FROM ventures WHERE name = %s", (name,))

# WRONG — SQL injection risk
cur.execute(f"SELECT * FROM ventures WHERE name = '{name}'")
```

### Upsert (ON CONFLICT)
```python
cur.execute("""
    INSERT INTO skills (id, org_id, name, content, version)
    VALUES (%s, %s, %s, %s, 1)
    ON CONFLICT (org_id, name)
    DO UPDATE SET content = EXCLUDED.content, version = skills.version + 1
""", (str(uuid.uuid4()), ORG_ID, skill_name, content))
```

### Resolve venture slug to UUID
```python
from eos_ai.db import resolve_venture
venture_id = resolve_venture('lyfe_institute')  # returns UUID string or None
```

### Batch insert with executemany
```python
cur.executemany("""
    INSERT INTO events (org_id, event_type, payload)
    VALUES (%s, %s, %s)
""", [(ORG_ID, etype, json.dumps(p)) for etype, p in events])
```

### JSON columns
```python
import json
cur.execute("""
    INSERT INTO agent_tasks (org_id, agent_id, task_data)
    VALUES (%s, %s, %s::jsonb)
""", (ORG_ID, agent_id, json.dumps(task_dict)))
```

## Conceptual Model

### Neon Architecture
```
Project
  └── Branch (main, dev, preview/*)
        └── Compute Endpoint (autosuspend, autoscale)
              └── PostgreSQL (14-17, full extension support)
        └── Storage (shared, append-only, WAL-based)
```

- **Project** = one Neon project per environment. Contains all branches.
- **Branch** = copy-on-write fork of the database at a point in time. Main branch is production.
- **Compute** = the Postgres process. Scales 0.25-10 CU. Suspends after idle timeout. Cold start wakes it.
- **Storage** = Neon's custom pageserver. Shared across branches. Only changed pages are stored per branch.

### EOS maps to this as:
- One Neon project for all EOS data
- Main branch = production (single-user phase)
- RLS provides multi-tenant isolation within a single branch
- All connections go through the pooled endpoint for connection reuse

## Gotchas

### Cold start latency
Neon suspends compute after 5 minutes of inactivity (configurable). First connection after suspend takes 500ms-2s to wake. For EOS: services run continuously so this rarely triggers, but cron scripts and one-off commands will hit it. Not a bug — expected behavior.

### Connection limits
- **Free tier**: 100 concurrent connections (pooled), ~20 direct
- **Pro/Scale**: configurable, but PgBouncer pooled endpoint is always recommended
- EOS pattern of open-use-close via `get_conn()` context manager keeps connection count low

### RLS requires SET LOCAL on every transaction
If you forget `SET LOCAL app.current_org_id`, queries return empty results (not errors). The `get_conn()` context manager handles this automatically. Never bypass it with raw `psycopg2.connect()`.

### Pooled endpoint limitations (PgBouncer transaction mode)
- No `LISTEN`/`NOTIFY`
- No `PREPARE`/`DEALLOCATE` (server-side prepared statements)
- No `SET` without `LOCAL` (session settings reset between transactions)
- No advisory locks that span transactions
- `DISCARD ALL` is injected between transactions by PgBouncer

### psycopg2 tuple trap
```python
# WRONG — psycopg2 sees a string, not a tuple
cur.execute("SELECT * FROM t WHERE id = %s", (some_id))
# CORRECT — trailing comma makes it a tuple
cur.execute("SELECT * FROM t WHERE id = %s", (some_id,))
```

### RealDictCursor means dict access only
All EOS queries return dicts: `row['column_name']`, never `row[0]`. If you use `cursor_factory=None` by accident, index-based access will silently return wrong data.

### Neon connection string has project ID in hostname
The hostname encodes the project: `ep-cool-name-123456.us-east-2.aws.neon.tech`. If you copy a connection string from another project, it connects to the wrong database entirely. Always use `DATABASE_URL` from `.env`.

### SSL is mandatory
`sslmode=require` must be in the connection string. Neon rejects plaintext connections. psycopg2 respects this from the DSN automatically.

### Transaction auto-commit is OFF by default
psycopg2 opens an implicit transaction on the first query. EOS uses `with conn:` context manager which commits on clean exit and rolls back on exception. Never call `conn.commit()` manually inside `get_conn()` — the context manager handles it.

### UUID columns
Neon stores UUIDs as `uuid` type. psycopg2 returns them as `uuid.UUID` objects, but EOS casts to `str()` in the caches. Always `str(row['id'])` when storing UUIDs in Python dicts.

See references/best_practices.md for connection parameters, error codes, and anti-patterns.
