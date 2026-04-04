# Neon Postgres — Creator-Level Best Practices
Source: https://neon.tech/docs
API Version: PostgreSQL 16 (Neon supports 14-17)
SDK Version: psycopg2 2.9.11
Last Researched: 2026-04-03

---

# Tier 1 — Technical Mastery

## Authentication

Neon authenticates via standard PostgreSQL connection strings over SSL/TLS.

**Connection string format:**
```
postgresql://<user>:<password>@<endpoint-id>.<region>.aws.neon.tech/<dbname>?sslmode=require
```

**Components:**
- `user` — role name (default: project owner role, e.g. `neondb_owner`)
- `password` — role password (auto-generated, rotatable via console/API)
- `endpoint-id` — globally unique compute endpoint identifier (e.g. `ep-cool-dawn-123456`)
- `region` — AWS region (e.g. `us-east-2`, `eu-central-1`, `ap-southeast-1`)
- `dbname` — database name (default: `neondb`)
- `sslmode=require` — MANDATORY. Neon rejects plaintext connections.

**Pooled endpoint:**
```
postgresql://<user>:<password>@<endpoint-id>-pooler.<region>.aws.neon.tech/<dbname>?sslmode=require
```
The `-pooler` suffix routes through Neon's built-in PgBouncer instance in transaction mode.

**Neon API authentication (management API):**
- Bearer token via `Authorization: Bearer <api-key>`
- API keys generated in Neon console under Account Settings
- Base URL: `https://console.neon.tech/api/v2/`

**psycopg2 connection:**
```python
import psycopg2
conn = psycopg2.connect(os.environ["DATABASE_URL"])
# SSL is handled automatically from the sslmode=require in DSN
```

## Core Operations with Exact Signatures

**psycopg2.connect()** — the only entry point:
```python
psycopg2.connect(
    dsn=None,          # connection string (DATABASE_URL)
    connection_factory=None,
    cursor_factory=None,
    host=None, port=None, user=None, password=None, dbname=None,  # or individual params
    sslmode=None,      # 'require' for Neon
    connect_timeout=10,  # seconds; recommended for serverless
    options=None,      # e.g. '-c statement_timeout=30000'
)
```

**cursor() with RealDictCursor:**
```python
import psycopg2.extras
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
# Returns rows as dict: row['column_name']
```

**execute() — parameterized queries:**
```python
cur.execute("SELECT * FROM t WHERE id = %s AND name = %s", (id_val, name_val))
# %s is the ONLY placeholder. Never use %d, ?, or f-strings.
```

**executemany() — batch operations:**
```python
cur.executemany("INSERT INTO t (a, b) VALUES (%s, %s)", [(1, 'x'), (2, 'y')])
# Note: executemany sends one query per row. For bulk, use execute_values.
```

**execute_values() — true bulk insert (psycopg2.extras):**
```python
from psycopg2.extras import execute_values
execute_values(cur, "INSERT INTO t (a, b) VALUES %s", [(1, 'x'), (2, 'y')], page_size=100)
# Sends single multi-row INSERT. 10-100x faster than executemany for large batches.
```

**fetchone(), fetchall(), fetchmany(n):**
```python
row = cur.fetchone()    # dict or None
rows = cur.fetchall()   # list[dict]
batch = cur.fetchmany(50)  # list[dict], up to 50
```

**RETURNING clause:**
```python
cur.execute("INSERT INTO t (name) VALUES (%s) RETURNING id, created_at", ('foo',))
result = cur.fetchone()  # {'id': uuid, 'created_at': datetime}
```

## Pagination Patterns

**Keyset pagination (recommended for Neon):**
```python
cur.execute("""
    SELECT id, name, created_at FROM items
    WHERE created_at < %s
    ORDER BY created_at DESC
    LIMIT %s
""", (last_seen_timestamp, page_size))
```
Keyset pagination is O(1) regardless of offset. OFFSET/LIMIT degrades as offset grows.

**OFFSET/LIMIT (acceptable for small datasets):**
```python
cur.execute("SELECT * FROM items ORDER BY id LIMIT %s OFFSET %s", (limit, offset))
```

## Rate Limits

**Neon compute:**
- No query rate limit per se — limited by compute CU allocation
- Free tier: 0.25 CU (0.25 vCPU, 1 GB RAM), 191.9 compute hours/month
- Pro: configurable 0.25-10 CU, autoscaling
- Scale/Business: higher CU ranges

**Connection limits:**
- Direct endpoint: ~100 connections per CU (112 for 0.25 CU on free tier due to overhead)
- Pooled endpoint: 10,000 concurrent connections (PgBouncer), mapped to ~64 server connections
- EOS pattern (open-use-close) means connection count stays at 1-3 concurrent

**Neon Management API:**
- 1,000 requests per second per API key
- 100 branches per project (free), 500+ on paid plans
- 20 compute endpoints per project

**Storage:**
- Free tier: 0.5 GB storage, 5 GB data transfer
- Pro: 10 GB included, billed per GB after
- WAL retention: 24 hours (free), 7 days (pro), 30 days (business)

## Error Codes and Recovery

**Connection errors (psycopg2.OperationalError):**
| Scenario | Error | Recovery |
|----------|-------|----------|
| Cold start timeout | `connection timed out` / `could not connect to server` | Retry after 2s. Compute is waking. |
| Compute suspended | `endpoint is suspended` | Connection auto-wakes it. Retry. |
| SSL required | `SSL connection is required` | Add `sslmode=require` to DSN |
| Auth failed | `password authentication failed for user` | Check credentials in .env |
| Too many connections | `too many connections for role` | Use pooled endpoint. Check for leaks. |
| Project limit | `could not find project` | Verify endpoint ID in connection string |

**Query errors (psycopg2.errors):**
| Code | Class | Error | Cause |
|------|-------|-------|-------|
| 23505 | IntegrityError | `unique_violation` | Duplicate key. Use ON CONFLICT. |
| 23503 | IntegrityError | `foreign_key_violation` | Referenced row missing. |
| 23502 | IntegrityError | `not_null_violation` | NULL in NOT NULL column. |
| 42P01 | ProgrammingError | `undefined_table` | Table doesn't exist or RLS hiding it. |
| 42703 | ProgrammingError | `undefined_column` | Column name typo. |
| 40001 | SerializationError | `serialization_failure` | Concurrent update conflict. Retry. |
| 57014 | QueryCanceledError | `query_canceled` | Statement timeout hit. |
| 53300 | OperationalError | `too_many_connections` | Connection limit exceeded. |

**psycopg2 exception hierarchy:**
```
psycopg2.Error
  ├── DatabaseError
  │     ├── IntegrityError (23xxx)
  │     ├── ProgrammingError (42xxx)
  │     ├── OperationalError (08xxx, 53xxx, 57xxx)
  │     ├── DataError (22xxx)
  │     ├── InternalError (XX000)
  │     └── NotSupportedError
  └── InterfaceError (client-side, no server contact)
```

**Neon-specific: compute wake errors:**
```python
import psycopg2
import time

def connect_with_retry(dsn, max_retries=3):
    """Handle Neon cold start with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return psycopg2.connect(dsn, connect_timeout=10)
        except psycopg2.OperationalError as e:
            if attempt < max_retries - 1 and 'timeout' in str(e).lower():
                time.sleep(2 ** attempt)
                continue
            raise
```

## SDK Idioms

**Context manager pattern (EOS standard):**
```python
@contextmanager
def get_conn(org_id: str = ORG_ID) -> Generator:
    conn = psycopg2.connect(_DATABASE_URL)
    try:
        with conn:  # auto-commit on clean exit, rollback on exception
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SET LOCAL app.current_org_id = %s", (org_id,))
                yield cur
    finally:
        conn.close()
```

**Key idioms:**
- `with conn:` = transaction block. Commits if no exception. Rolls back on exception.
- `with conn.cursor() as cur:` = auto-closes cursor on exit.
- `conn.close()` in finally = always release the connection back.
- `SET LOCAL` = transaction-scoped setting. Resets on commit/rollback. Safe for RLS.
- `%s` parameters = the ONLY safe way. psycopg2 handles escaping and type adaptation.
- Trailing comma in single-value tuple: `(value,)` not `(value)`.
- `cur.description` = column metadata after execute. `None` for non-SELECT.
- `cur.rowcount` = rows affected by last INSERT/UPDATE/DELETE. `-1` for SELECT on some drivers.
- `cur.statusmessage` = e.g. `'INSERT 0 1'`, `'UPDATE 5'`.

**Type adaptation (Python to Postgres):**
```python
# Automatic:
# str → text/varchar
# int → integer/bigint
# float → double precision
# bool → boolean
# None → NULL
# datetime → timestamp
# date → date
# Decimal → numeric
# list → ARRAY (with register_adapter or cast)
# dict → json (must json.dumps() + ::jsonb cast)
# uuid.UUID → uuid

# Manual for JSONB:
import json
cur.execute("INSERT INTO t (data) VALUES (%s::jsonb)", (json.dumps(obj),))
```

**Connection parameter recommendations for Neon:**
```python
conn = psycopg2.connect(
    dsn=DATABASE_URL,           # includes sslmode=require
    connect_timeout=10,         # handle cold start (default: no timeout!)
    options='-c statement_timeout=30000',  # 30s query timeout
)
```

## Anti-Patterns

1. **Holding connections open** — Neon bills for compute time. Open-use-close is the correct pattern. Never keep a global connection alive.
2. **Using f-strings for SQL** — SQL injection. Always parameterized queries with `%s`.
3. **Forgetting `conn.close()`** — connection leak. Use context manager or try/finally.
4. **Using executemany for bulk inserts** — 100x slower than `execute_values`. Use `psycopg2.extras.execute_values()`.
5. **Bypassing `get_conn()`** — skips RLS, skips credential sanitization, skips caching.
6. **OFFSET pagination on large tables** — O(n) scan. Use keyset pagination.
7. **No connect_timeout** — default is infinite. Hangs forever on compute wake failure.
8. **Catching bare Exception** — hides psycopg2 error classes. Catch specific errors.
9. **Manual conn.commit()** — breaks the `with conn:` context manager contract.
10. **SET without LOCAL** — persists beyond the transaction in direct connections; leaks state in pooled connections.

## Data Model

**Neon storage model:**
- Pageserver stores 8KB Postgres pages
- WAL (Write-Ahead Log) is the source of truth
- Pages are reconstructed from WAL on demand
- Branch = pointer to a WAL position (no data copy)
- Storage is compressed and deduplicated across branches

**EOS tables (key subset):**
- `interactions` — every agent conversation (org_id, user_id, channel, raw_input, response)
- `ventures` — business entities (org_id, name, type)
- `skills` — agent skills with content (org_id, name, content, version)
- `agents` — registered agents (org_id, name, type, department, soul_doc_path)
- `memories` — agent memory writes (org_id, user_id, venture_id, memory_type, content)
- `knowledge_graph` — entity relationships (org_id, source, target, relation)
- `events` — event bus entries (org_id, event_type, payload)

All tables have `org_id` column with RLS policy: `current_setting('app.current_org_id')::uuid = org_id`.

## Webhooks and Events

Neon does not have webhook support for database events. Instead:

- **Neon Management API webhooks** — not available. Poll the API for branch/compute status.
- **PostgreSQL LISTEN/NOTIFY** — available on direct (non-pooled) endpoint only.
  ```python
  # Direct endpoint only (no -pooler)
  conn = psycopg2.connect(DIRECT_DATABASE_URL)
  conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
  cur = conn.cursor()
  cur.execute("LISTEN my_channel")
  # Then poll: conn.poll(); conn.notifies
  ```
- **EOS uses event_bus.py** — writes events to the `events` table instead of LISTEN/NOTIFY, avoiding the pooled endpoint limitation.

## Limits

| Resource | Free Tier | Pro | Scale | Business |
|----------|-----------|-----|-------|----------|
| Projects | 1 | 10 | 50 | 100 |
| Branches per project | 10 | 500 | 500 | 500 |
| Compute size | 0.25 CU | 0.25-10 CU | 0.25-10 CU | 0.25-10 CU |
| Storage | 0.5 GB | 10 GB incl. | 50 GB incl. | 500 GB incl. |
| Compute hours/month | 191.9 | 300 incl. | 750 incl. | unlimited |
| WAL retention | 24 hours | 7 days | 7 days | 30 days |
| Max DB size | 0.5 GB | no limit | no limit | no limit |
| Autosuspend | 5 min (fixed) | configurable | configurable | configurable |
| Connection limit (pooled) | 10,000 | 10,000 | 10,000 | 10,000 |
| Connection limit (direct) | ~112 | scales with CU | scales with CU | scales with CU |
| Logical replication | no | yes | yes | yes |
| IP allow list | no | no | yes | yes |

## Cost Model

**Neon pricing dimensions:**
1. **Compute** — billed per CU-hour. Free tier: 191.9 hours/month at 0.25 CU. Pro: $0.102/CU-hour.
2. **Storage** — billed per GiB-month. Pro: $0.000164/GiB-hour (~$0.12/GiB-month).
3. **Data transfer** — 5 GB free, then $0.09/GB.
4. **Written data** — measured in WAL bytes. Included in storage calculation.

**Cost optimization for EOS:**
- Autosuspend aggressively (5 min) in dev/staging. Compute is the main cost.
- Use pooled endpoint to reduce active connection count.
- `get_conn()` open-use-close pattern = minimal compute time per query.
- Avoid long-running transactions — they hold compute alive.
- Branch cleanup: delete stale dev/preview branches (they consume storage for diverged pages).

## Version Pinning

**psycopg2:**
```
psycopg2-binary==2.9.11  # in requirements.txt
```
`psycopg2-binary` includes prebuilt libpq. For production Docker images with custom libpq, use `psycopg2==2.9.11` and install `libpq-dev`.

**Neon Postgres version:**
- Set per project in Neon console (14, 15, 16, or 17).
- EOS uses PostgreSQL 16.
- Major version upgrades require Neon support or branch migration.
- Minor versions auto-updated by Neon (e.g., 16.2 to 16.4).

**Neon API:**
- Version in URL path: `/api/v2/`
- No SDK — use raw HTTP requests or `neonctl` CLI.

---

# Tier 2 — Creator Intelligence

## Design Intent

Neon's core thesis: **Postgres should be serverless.** Traditional Postgres ties compute and storage together — you pay for a running server 24/7 even if it processes 10 queries/day. Neon separates them:

- **Storage is a service** — Neon's custom pageserver replaces the local filesystem. Pages are fetched over the network. This enables branching, point-in-time restore, and scale-to-zero without losing data.
- **Compute is ephemeral** — Postgres processes start and stop on demand. Cold start is the tax for scale-to-zero. The tradeoff is explicit: pay latency on first connection, save 100% cost when idle.
- **Branching is a primitive** — because storage is append-only WAL, creating a branch is O(1) regardless of database size. This makes database branching as cheap as git branching. The intended use: every PR gets a database branch, every migration is tested on a branch first.

The design intent is NOT "cheaper RDS." It is "Postgres with git semantics for data." The branch-per-environment model changes how you think about database changes entirely.

**Tradeoffs accepted by Neon:**
- Cold start latency (500ms-2s) in exchange for zero idle cost
- Network-attached storage (marginally higher read latency) in exchange for branching and instant restore
- PgBouncer as the default path (no session state) in exchange for high connection concurrency
- Smaller maximum compute (10 CU) in exchange for elastic scaling

## Problem-Solution Map

| Problem | Neon Solution | EOS Application |
|---------|---------------|-----------------|
| Connection overhead per request | Built-in PgBouncer (pooled endpoint) | `get_conn()` opens per-transaction, pooler reuses server connections |
| Multi-tenant data isolation | Standard Postgres RLS | `SET LOCAL app.current_org_id` on every transaction via db.py |
| Database for testing/staging | Instant branching (O(1), no data copy) | Not yet used — future: branch per PR |
| Schema migration risk | Branch + migrate + validate + merge | Not yet used — future: safe migration workflow |
| Cold start on serverless | Keep-alive ping or always-on compute | EOS services run continuously; cron scripts accept cold start |
| Connection string management | Single DSN with all params | `DATABASE_URL` in .env, loaded once at module level |
| Credential rotation | Neon console role management | Manual rotation via console, update .env |
| Query performance debugging | Neon SQL Editor + `EXPLAIN ANALYZE` | Ad-hoc via psycopg2: `cur.execute("EXPLAIN ANALYZE " + query)` |
| Bulk data loading | `execute_values` + larger page_size | Available via `psycopg2.extras.execute_values` |
| Point-in-time recovery | WAL-based restore to any second within retention | Available via Neon console/API |

**Hidden capabilities:**
- `pg_stat_statements` extension is available — query performance tracking without external tooling.
- `pgvector` extension is available — vector similarity search for embeddings (EOS uses `embedding_engine.py`).
- Branch reset — reset a branch to match its parent without recreating it.
- Time Travel — query data at a past point in time using Neon's LSN-based storage.

## Operational Behavior

**Cold start sequence:**
1. Client sends TCP SYN to Neon proxy
2. Neon proxy reads the SNI header to identify the endpoint
3. If compute is suspended: proxy triggers compute activation
4. Compute starts Postgres process (~500ms for 0.25 CU)
5. Pageserver loads most recent page versions from WAL
6. Postgres ready, proxy forwards the connection
7. Total: 500ms-2s for first connection, <5ms for subsequent

**Autosuspend behavior:**
- Timer resets on every query
- After idle timeout (default 5 min, configurable 1 min to 7 days): compute suspends
- Suspended compute = zero cost
- PgBouncer on pooled endpoint does NOT keep compute alive — it forwards to suspended compute which then wakes

**Connection lifecycle on pooled endpoint:**
1. Client connects to PgBouncer (fast, no cold start for this step)
2. Client sends first query
3. PgBouncer assigns a server connection (may trigger cold start here)
4. Query executes
5. Transaction ends → PgBouncer reclaims server connection
6. Client connection stays open but has no server connection

**Failure modes in production:**
- Compute OOM: queries on 0.25 CU with large sorts/joins can OOM. Solution: increase CU or optimize query.
- Storage quota: free tier at 0.5 GB. Inserts silently succeed until quota enforced (usually within minutes). Then: `ERROR: could not extend file: No space left on device`.
- Region outage: single-region deployment. No automatic failover on free/pro. Business tier has read replicas.

## Ecosystem Position

**Neon vs alternatives:**
| Feature | Neon | Supabase | PlanetScale | Aurora Serverless |
|---------|------|----------|-------------|-------------------|
| Engine | Postgres | Postgres | MySQL (Vitess) | MySQL or Postgres |
| Scale to zero | Yes | No (always on) | Yes (v2) | Yes (v2) |
| Branching | Native, O(1) | No | No | No |
| Connection pooling | Built-in PgBouncer | Built-in PgBouncer | Built-in | Built-in |
| Open source | Yes (storage layer) | Yes | No | No |
| psycopg2 compatible | Full | Full | N/A (MySQL) | Full |
| RLS | Full Postgres RLS | Full Postgres RLS | N/A | Limited |
| Cold start | 500ms-2s | N/A | ~1s | 15-30s |

**Neon's open-source strategy:** The storage layer (pageserver, safekeeper, WAL service) is Apache 2.0 licensed. This means Neon's innovation is the storage engine, not the Postgres interface. If Neon the company disappears, the data is standard Postgres — `pg_dump` works.

**Composition with EOS:**
- psycopg2 is the driver — battle-tested, C-accelerated, synchronous
- Neon is the host — serverless scaling, branching
- RLS is the isolation — multi-tenant without schema separation
- `db.py` is the glue — one module, one pattern, every module uses it

## Trajectory

**Where Neon is heading (based on public roadmap and releases through early 2026):**
- **Autoscaling improvements** — finer-grained CU steps, faster scale-up
- **Schema migration tooling** — branch-based migration workflows built into console
- **Neon Auth** — Postgres-native auth integrated with identity providers (Clerk, Auth0)
- **Read replicas** — cross-region read replicas for latency-sensitive reads
- **Larger compute** — beyond 10 CU for analytics workloads
- **pg_embedding / pgvector integration** — deeper vector search support
- **Vercel/Netlify integrations** — branch-per-preview-deployment as first-class

**Implications for EOS:**
- Branch-per-PR workflow will become practical when schema migration tooling matures
- Read replicas enable multi-region EOS deployment
- Neon Auth could replace `SET LOCAL` RLS pattern with native row ownership
- Vector search improvements benefit `embedding_engine.py` directly

## Conceptual Model

**Mental model: "Postgres with git semantics"**

```
                    ┌─────────────────────────┐
                    │     Neon Project         │
                    │  (= git repository)      │
                    └────────────┬────────────┘
                                 │
                    ┌────────────┼────────────┐
                    │            │            │
               ┌────┴───┐  ┌────┴───┐  ┌────┴───┐
               │ main   │  │ dev    │  │ pr-42  │
               │ branch │  │ branch │  │ branch │
               └────┬───┘  └────┬───┘  └────┬───┘
                    │            │            │
               ┌────┴───┐  ┌────┴───┐  ┌────┴───┐
               │Compute │  │Compute │  │  (off) │
               │ (on)   │  │ (susp) │  │        │
               └────────┘  └────────┘  └────────┘
                    │            │            │
               ─────────────────────────────────
               │         Shared Pageserver         │
               │    (append-only, WAL-based)       │
               ─────────────────────────────────────
```

**Key insight:** Branches share all pages up to the fork point. Only divergent pages are stored separately. Creating a 100 GB branch costs ~0 bytes until you write to it.

**Solution recipes:**

1. **Safe migration:** Create branch from main → run migration on branch → validate → merge (or recreate main from branch)
2. **Load testing:** Branch main → run load test against branch compute → delete branch. Zero impact on production.
3. **Data recovery:** Time travel to before the bad query → branch at that point → extract corrected data → apply to main.
4. **Dev environment:** Each developer gets a branch. Full production data, zero extra storage cost until writes diverge.

## Industry Expert

**psycopg2 mastery patterns for Neon:**

**1. Connection resilience with retry:**
```python
import psycopg2
from psycopg2 import OperationalError
import time

def resilient_query(dsn, query, params=None, max_retries=3):
    for attempt in range(max_retries):
        try:
            conn = psycopg2.connect(dsn, connect_timeout=10)
            try:
                with conn:
                    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                        cur.execute(query, params)
                        return cur.fetchall() if cur.description else None
            finally:
                conn.close()
        except OperationalError:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)
```

**2. Monitoring connection health:**
```python
def check_neon_health(dsn):
    try:
        conn = psycopg2.connect(dsn, connect_timeout=5)
        cur = conn.cursor()
        cur.execute("SELECT 1")
        conn.close()
        return True
    except Exception:
        return False
```

**3. Advisory locking for distributed coordination (direct endpoint only):**
```python
# Acquire: cur.execute("SELECT pg_advisory_lock(%s)", (lock_id,))
# Try:     cur.execute("SELECT pg_try_advisory_lock(%s)", (lock_id,))
# Release: cur.execute("SELECT pg_advisory_unlock(%s)", (lock_id,))
# NOTE: Does NOT work on pooled endpoint (PgBouncer transaction mode).
```

**4. JSONB querying patterns:**
```python
# Extract field:
cur.execute("SELECT data->>'name' FROM t WHERE data->>'type' = %s", ('lead',))
# Contains operator:
cur.execute("SELECT * FROM t WHERE data @> %s::jsonb", (json.dumps({"status": "active"}),))
# Array in JSONB:
cur.execute("SELECT * FROM t WHERE data->'tags' ? %s", ('vip',))
```

**5. Batch upsert with execute_values:**
```python
from psycopg2.extras import execute_values
execute_values(cur, """
    INSERT INTO metrics (org_id, key, value, ts)
    VALUES %s
    ON CONFLICT (org_id, key) DO UPDATE SET value = EXCLUDED.value, ts = EXCLUDED.ts
""", rows, template="(%s, %s, %s, %s)")
```

**6. Schema introspection:**
```python
# List tables:
cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
# List columns:
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = %s", ('interactions',))
# Check RLS enabled:
cur.execute("SELECT relname, relrowsecurity FROM pg_class WHERE relname = %s", ('interactions',))
```

**Expert-level Neon awareness:**
- Neon proxy uses SNI (Server Name Indication) to route connections. If your client strips SNI (some corporate proxies do), connections fail silently.
- `pg_stat_statements` on Neon tracks query patterns across compute restarts — the stats persist in storage, not compute memory.
- Neon's pageserver prefetches pages for sequential scans. Random I/O is costlier than on local SSD. Index usage matters more on Neon than on traditional Postgres.
- Branch creation via API is sub-second regardless of DB size. The CLI command: `neonctl branches create --name dev`
- Compute restart clears `pg_stat_activity` — do not rely on it for long-term connection monitoring.

---

## EOS Usage Patterns

**Standard pattern (used in 60+ modules):**
```python
from eos_ai.db import get_conn, resolve_venture, ORG_ID, USER_ID

with get_conn() as cur:
    cur.execute("INSERT INTO ... VALUES (%s, ...) RETURNING id", (ORG_ID, ...))
    result = cur.fetchone()
```

**Venture-scoped query:**
```python
venture_id = resolve_venture('lyfe_institute')
with get_conn() as cur:
    cur.execute("SELECT * FROM tasks WHERE venture_id = %s", (venture_id,))
```

**Skill registration (used in new-skill workflow):**
```python
with get_conn() as cur:
    cur.execute("""
        INSERT INTO skills (id, org_id, name, content, version)
        VALUES (%s, %s, %s, %s, 1)
        ON CONFLICT (org_id, name) DO UPDATE SET content = EXCLUDED.content
    """, (str(uuid.uuid4()), ORG_ID, name, content))
```

## Gotchas

- Cold start after overnight idle: first morning query takes 1-2s. Not a bug.
- `SET LOCAL` is invisible: if RLS blocks data, the query returns empty — no error. Check `app.current_org_id` if queries unexpectedly return nothing.
- psycopg2 tuple trap: `(value)` is not a tuple, `(value,)` is. Missing comma causes `TypeError: not all arguments converted`.
- `RealDictCursor` rows are dicts — `row['id']` works, `row[0]` does not.
- `executemany` is slow for bulk — use `execute_values` from `psycopg2.extras`.
- Connection string with wrong project ID connects to wrong database silently (auth succeeds if creds match).
- Pooled endpoint (-pooler) does not support LISTEN/NOTIFY, prepared statements, or session-level SET.
- Free tier storage quota (0.5 GB) causes hard failure on insert when exceeded.
- `conn.autocommit = True` breaks the `with conn:` transaction context manager — never set it inside `get_conn()`.
- Neon proxy requires SNI — connections from clients that strip TLS SNI will fail.
