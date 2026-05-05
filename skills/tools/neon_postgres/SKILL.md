<<<<<<< Updated upstream
---
name: neon_postgres
description: "Use when any agent reads or writes persistent data, registers agents/skills, stores memory, or queries business state via Neon Postgres."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://neon.tech/docs"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "PostgreSQL 16"
sdk_version: "psycopg2 2.9.11"
speed_category: medium
trigger: both
effort: medium
context: fork
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

Raw-SQL / Postgres-internals mastery (planner, indexes, JSONB, pgvector,
locking, EXPLAIN) is documented separately in
`references/raw_sql_mastery.md` — consult it when a query is on a hot path,
touches vectors, uses window/CTE/LATERAL constructs, or misbehaves under
`EXPLAIN ANALYZE`.

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

### psycopg2 Patterns in EOS

**How `get_conn()` works internally:**
`get_conn()` is a `@contextmanager` that does five things in order:
1. `psycopg2.connect(_DATABASE_URL)` — opens a new connection (credentials from .env)
2. `with conn:` — enters transaction block (auto-commit on clean exit, rollback on exception)
3. `conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)` — all rows are dicts
4. `SET LOCAL app.current_org_id = %s` — enables RLS for the tenant
5. `conn.close()` in `finally` — always releases the connection

This means: one connection per `with get_conn()` block. No pooling in Python — Neon's PgBouncer handles that server-side.

**Cursor lifecycle:**
The cursor yielded by `get_conn()` is managed by two nested context managers. You never need to close it manually. The cursor is valid only inside the `with` block — accessing it after the block raises `InterfaceError`.

**Multiple queries in one transaction:**
```python
with get_conn() as cur:
    cur.execute("INSERT INTO events (...) VALUES (%s, %s) RETURNING id", (ORG_ID, etype))
    event_id = cur.fetchone()['id']
    cur.execute("INSERT INTO event_links (...) VALUES (%s, %s)", (event_id, target_id))
    # Both inserts commit together or roll back together
```

**Raw psycopg2 (bypassing get_conn):**
Three EOS modules bypass `get_conn()` for specific reasons:
- `system_health.py` — health checks use `connect_timeout=3` and plain cursor (no RLS needed for `SELECT COUNT(*)`)
- `portfolio_advisor.py` — cross-org portfolio queries that intentionally skip RLS
- `session_start_context.py`, `check_stop_condition.py` — lightweight scripts that import psycopg2 directly to avoid loading the full eos_ai module tree

When bypassing `get_conn()`, always:
```python
conn = psycopg2.connect(db_url, connect_timeout=5)
try:
    cur = conn.cursor()
    cur.execute("SELECT ...")
    result = cur.fetchone()
finally:
    conn.close()  # ALWAYS in finally block
```

**Parameterized queries — the only safe pattern:**
```python
# psycopg2 uses %s for ALL types — never %d, %f, or ?
cur.execute("SELECT * FROM t WHERE id = %s", (uuid_val,))           # UUID
cur.execute("SELECT * FROM t WHERE name = %s", (string_val,))       # text
cur.execute("SELECT * FROM t WHERE count > %s", (42,))              # integer
cur.execute("SELECT * FROM t WHERE active = %s", (True,))           # boolean
cur.execute("SELECT * FROM t WHERE data @> %s::jsonb", (json.dumps({"k": "v"}),))  # JSONB
```

**Bulk operations — execute_values vs executemany:**
```python
from psycopg2.extras import execute_values

# FAST — single multi-row INSERT (use this)
execute_values(cur, "INSERT INTO t (a, b) VALUES %s", [(1, 'x'), (2, 'y')], page_size=100)

# SLOW — sends N separate INSERTs (avoid for >10 rows)
cur.executemany("INSERT INTO t (a, b) VALUES (%s, %s)", [(1, 'x'), (2, 'y')])
```

**Error handling pattern used in EOS:**
```python
try:
    with get_conn() as cur:
        cur.execute("INSERT INTO ...")
except psycopg2.errors.UniqueViolation:
    print("Duplicate key — use ON CONFLICT instead")
except psycopg2.OperationalError as e:
    print(f"Connection failed: {e}")
    # Retry logic if needed
```

**Credential sanitization:**
`get_conn()` catches connection errors and strips credentials from the error message using `re.sub(r'://[^@]+@', '://***:***@', str(e))` before re-raising. This prevents database passwords from leaking into logs or tracebacks.

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

### psycopg2 cursor attributes (after execute)
```python
cur.rowcount    # rows affected by INSERT/UPDATE/DELETE (-1 for SELECT on some configs)
cur.statusmessage  # e.g. 'INSERT 0 1', 'UPDATE 5', 'DELETE 3'
cur.description    # column metadata tuple — None for non-SELECT
cur.query          # the last executed query as bytes (useful for debugging)
```

### Conditional insert (check-then-insert)
```python
with get_conn() as cur:
    cur.execute("SELECT 1 FROM agents WHERE name = %s", (name,))
    if cur.fetchone():
        print("Already exists")
    else:
        cur.execute("INSERT INTO agents (...) VALUES (%s, ...)", (name, ...))
```

### JSONB query patterns
```python
# Extract field from JSONB column
cur.execute("SELECT payload_json->>'status' FROM events WHERE id = %s", (event_id,))

# Filter by JSONB key value
cur.execute("SELECT * FROM tasks WHERE metadata->>'keep_running' = %s", ('true',))

# JSONB containment operator (@>)
cur.execute("SELECT * FROM events WHERE payload_json @> %s::jsonb",
            (json.dumps({"event_type": "lead_created"}),))
```

### Transaction isolation with multiple reads
```python
with get_conn() as cur:
    # All reads in the same transaction see a consistent snapshot
    cur.execute("SELECT SUM(amount) FROM expenses WHERE venture_id = %s", (vid,))
    total = cur.fetchone()['sum']
    cur.execute("SELECT budget FROM ventures WHERE id = %s", (vid,))
    budget = cur.fetchone()['budget']
    # total and budget are guaranteed consistent — no other transaction can change them mid-read
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

### psycopg2-specific gotchas

**Cursor used outside `with` block:**
```python
# WRONG — cursor is closed after the with block exits
with get_conn() as cur:
    cur.execute("SELECT * FROM t")
rows = cur.fetchall()  # InterfaceError: cursor already closed

# CORRECT — fetch inside the block
with get_conn() as cur:
    cur.execute("SELECT * FROM t")
    rows = cur.fetchall()
```

**None vs empty result confusion:**
```python
row = cur.fetchone()
# row is None if no rows match — NOT an empty dict
# Always check: if row: before accessing row['column']
```

**psycopg2.errors requires explicit import:**
```python
# WRONG — psycopg2.errors is not auto-imported
import psycopg2
try:
    cur.execute(...)
except psycopg2.errors.UniqueViolation:  # AttributeError: module has no attribute 'errors'
    pass

# CORRECT — import the errors module explicitly
import psycopg2.errors
# OR catch the parent class:
except psycopg2.IntegrityError:  # works without importing psycopg2.errors
    pass
```

**datetime timezone awareness:**
psycopg2 returns `timestamp with time zone` columns as timezone-aware `datetime` objects and `timestamp without time zone` as naive `datetime` objects. Comparing aware and naive datetimes raises `TypeError`. EOS Neon tables use `timestamptz` — always compare with timezone-aware Python datetimes.

**Large fetchall() on big tables:**
`cur.fetchall()` loads the entire result set into memory. For tables with millions of rows, use `cur.fetchmany(batch_size)` in a loop or add `LIMIT` to the query. EOS tables are small enough that `fetchall()` is fine for all current use cases.

**Connection object is not thread-safe:**
A single `psycopg2` connection must not be shared across threads. Each thread needs its own `get_conn()` call. EOS is single-threaded per service, so this is not currently an issue — but it will matter if any service adds threading.

**Decimal vs float for numeric columns:**
psycopg2 returns Postgres `numeric`/`decimal` columns as Python `Decimal` objects, not `float`. `json.dumps()` cannot serialize `Decimal` — use `str(val)` or `float(val)` before serializing. EOS uses `monthly_revenue numeric` in the ventures table — watch for this.

See references/best_practices.md for connection parameters, error codes, and anti-patterns.
See references/raw_sql_mastery.md for Postgres-internals-level expertise (planner, indexes, JSONB, pgvector HNSW vs IVFFlat, locking, MVCC, EXPLAIN ANALYZE reading, CTEs, window functions, SKIP LOCKED work queues).
=======
---
name: neon_postgres
description: "Use when any agent reads or writes persistent data, registers agents/skills, stores memory, or queries business state via Neon Postgres."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://neon.tech/docs"
last_researched: "2026-04-06"
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

Raw-SQL / Postgres-internals mastery (planner, indexes, JSONB, pgvector,
locking, EXPLAIN) is documented separately in
`references/raw_sql_mastery.md` — consult it when a query is on a hot path,
touches vectors, uses window/CTE/LATERAL constructs, or misbehaves under
`EXPLAIN ANALYZE`.

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

### psycopg2 Patterns in EOS

**How `get_conn()` works internally:**
`get_conn()` is a `@contextmanager` that does five things in order:
1. `psycopg2.connect(_DATABASE_URL)` — opens a new connection (credentials from .env)
2. `with conn:` — enters transaction block (auto-commit on clean exit, rollback on exception)
3. `conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)` — all rows are dicts
4. `SET LOCAL app.current_org_id = %s` — enables RLS for the tenant
5. `conn.close()` in `finally` — always releases the connection

This means: one connection per `with get_conn()` block. No pooling in Python — Neon's PgBouncer handles that server-side.

**Cursor lifecycle:**
The cursor yielded by `get_conn()` is managed by two nested context managers. You never need to close it manually. The cursor is valid only inside the `with` block — accessing it after the block raises `InterfaceError`.

**Multiple queries in one transaction:**
```python
with get_conn() as cur:
    cur.execute("INSERT INTO events (...) VALUES (%s, %s) RETURNING id", (ORG_ID, etype))
    event_id = cur.fetchone()['id']
    cur.execute("INSERT INTO event_links (...) VALUES (%s, %s)", (event_id, target_id))
    # Both inserts commit together or roll back together
```

**Raw psycopg2 (bypassing get_conn):**
Three EOS modules bypass `get_conn()` for specific reasons:
- `system_health.py` — health checks use `connect_timeout=3` and plain cursor (no RLS needed for `SELECT COUNT(*)`)
- `portfolio_advisor.py` — cross-org portfolio queries that intentionally skip RLS
- `session_start_context.py`, `check_stop_condition.py` — lightweight scripts that import psycopg2 directly to avoid loading the full eos_ai module tree

When bypassing `get_conn()`, always:
```python
conn = psycopg2.connect(db_url, connect_timeout=5)
try:
    cur = conn.cursor()
    cur.execute("SELECT ...")
    result = cur.fetchone()
finally:
    conn.close()  # ALWAYS in finally block
```

**Parameterized queries — the only safe pattern:**
```python
# psycopg2 uses %s for ALL types — never %d, %f, or ?
cur.execute("SELECT * FROM t WHERE id = %s", (uuid_val,))           # UUID
cur.execute("SELECT * FROM t WHERE name = %s", (string_val,))       # text
cur.execute("SELECT * FROM t WHERE count > %s", (42,))              # integer
cur.execute("SELECT * FROM t WHERE active = %s", (True,))           # boolean
cur.execute("SELECT * FROM t WHERE data @> %s::jsonb", (json.dumps({"k": "v"}),))  # JSONB
```

**Bulk operations — execute_values vs executemany:**
```python
from psycopg2.extras import execute_values

# FAST — single multi-row INSERT (use this)
execute_values(cur, "INSERT INTO t (a, b) VALUES %s", [(1, 'x'), (2, 'y')], page_size=100)

# SLOW — sends N separate INSERTs (avoid for >10 rows)
cur.executemany("INSERT INTO t (a, b) VALUES (%s, %s)", [(1, 'x'), (2, 'y')])
```

**Error handling pattern used in EOS:**
```python
try:
    with get_conn() as cur:
        cur.execute("INSERT INTO ...")
except psycopg2.errors.UniqueViolation:
    print("Duplicate key — use ON CONFLICT instead")
except psycopg2.OperationalError as e:
    print(f"Connection failed: {e}")
    # Retry logic if needed
```

**Credential sanitization:**
`get_conn()` catches connection errors and strips credentials from the error message using `re.sub(r'://[^@]+@', '://***:***@', str(e))` before re-raising. This prevents database passwords from leaking into logs or tracebacks.

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

### psycopg2 cursor attributes (after execute)
```python
cur.rowcount    # rows affected by INSERT/UPDATE/DELETE (-1 for SELECT on some configs)
cur.statusmessage  # e.g. 'INSERT 0 1', 'UPDATE 5', 'DELETE 3'
cur.description    # column metadata tuple — None for non-SELECT
cur.query          # the last executed query as bytes (useful for debugging)
```

### Conditional insert (check-then-insert)
```python
with get_conn() as cur:
    cur.execute("SELECT 1 FROM agents WHERE name = %s", (name,))
    if cur.fetchone():
        print("Already exists")
    else:
        cur.execute("INSERT INTO agents (...) VALUES (%s, ...)", (name, ...))
```

### JSONB query patterns
```python
# Extract field from JSONB column
cur.execute("SELECT payload_json->>'status' FROM events WHERE id = %s", (event_id,))

# Filter by JSONB key value
cur.execute("SELECT * FROM tasks WHERE metadata->>'keep_running' = %s", ('true',))

# JSONB containment operator (@>)
cur.execute("SELECT * FROM events WHERE payload_json @> %s::jsonb",
            (json.dumps({"event_type": "lead_created"}),))
```

### Transaction isolation with multiple reads
```python
with get_conn() as cur:
    # All reads in the same transaction see a consistent snapshot
    cur.execute("SELECT SUM(amount) FROM expenses WHERE venture_id = %s", (vid,))
    total = cur.fetchone()['sum']
    cur.execute("SELECT budget FROM ventures WHERE id = %s", (vid,))
    budget = cur.fetchone()['budget']
    # total and budget are guaranteed consistent — no other transaction can change them mid-read
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

### psycopg2-specific gotchas

**Cursor used outside `with` block:**
```python
# WRONG — cursor is closed after the with block exits
with get_conn() as cur:
    cur.execute("SELECT * FROM t")
rows = cur.fetchall()  # InterfaceError: cursor already closed

# CORRECT — fetch inside the block
with get_conn() as cur:
    cur.execute("SELECT * FROM t")
    rows = cur.fetchall()
```

**None vs empty result confusion:**
```python
row = cur.fetchone()
# row is None if no rows match — NOT an empty dict
# Always check: if row: before accessing row['column']
```

**psycopg2.errors requires explicit import:**
```python
# WRONG — psycopg2.errors is not auto-imported
import psycopg2
try:
    cur.execute(...)
except psycopg2.errors.UniqueViolation:  # AttributeError: module has no attribute 'errors'
    pass

# CORRECT — import the errors module explicitly
import psycopg2.errors
# OR catch the parent class:
except psycopg2.IntegrityError:  # works without importing psycopg2.errors
    pass
```

**datetime timezone awareness:**
psycopg2 returns `timestamp with time zone` columns as timezone-aware `datetime` objects and `timestamp without time zone` as naive `datetime` objects. Comparing aware and naive datetimes raises `TypeError`. EOS Neon tables use `timestamptz` — always compare with timezone-aware Python datetimes.

**Large fetchall() on big tables:**
`cur.fetchall()` loads the entire result set into memory. For tables with millions of rows, use `cur.fetchmany(batch_size)` in a loop or add `LIMIT` to the query. EOS tables are small enough that `fetchall()` is fine for all current use cases.

**Connection object is not thread-safe:**
A single `psycopg2` connection must not be shared across threads. Each thread needs its own `get_conn()` call. EOS is single-threaded per service, so this is not currently an issue — but it will matter if any service adds threading.

**Decimal vs float for numeric columns:**
psycopg2 returns Postgres `numeric`/`decimal` columns as Python `Decimal` objects, not `float`. `json.dumps()` cannot serialize `Decimal` — use `str(val)` or `float(val)` before serializing. EOS uses `monthly_revenue numeric` in the ventures table — watch for this.

See references/best_practices.md for connection parameters, error codes, and anti-patterns.
See references/raw_sql_mastery.md for Postgres-internals-level expertise (planner, indexes, JSONB, pgvector HNSW vs IVFFlat, locking, MVCC, EXPLAIN ANALYZE reading, CTEs, window functions, SKIP LOCKED work queues).
>>>>>>> Stashed changes
