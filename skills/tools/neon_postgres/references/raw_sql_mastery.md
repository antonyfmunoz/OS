# Neon Postgres — Raw SQL Mastery (Postgres Internals Addendum)

Source: Raw SQL / PostgreSQL Internals mastery research
Target: PostgreSQL 16/17 (Neon wire-compat range), psycopg2 / psycopg3
Last Researched: 2026-04-06

Companion to `best_practices.md`. Where that file covers Neon serverless quirks
(compute autosuspend, `-pooler` endpoint, branching) and EOS `get_conn()` patterns,
this addendum covers what a Postgres expert knows that an ORM user doesn't:
planner internals, index selection, MVCC, locking, JSONB/pgvector, EXPLAIN reading.

**EOS context**: multi-tenant AI platform. Tables: `agents`, `skills`,
`memories` (with `embedding vector(1536)`), `feedback_events`, `tenants`.
Org isolation via RLS. Python layer uses psycopg2 with `app.current_org_id`
set per request via `SET LOCAL`.

---

## 1. Raw SQL Patterns Beyond the ORM

### When to drop the ORM

Drop out of Drizzle/SQLAlchemy/psycopg2-helpers when:

- The query needs a window function, CTE, `LATERAL`, `DISTINCT ON`, `FILTER`,
  or `GROUPING SETS`. ORMs either can't express these or generate worse SQL
  than you would.
- The query is a hot path measured in `pg_stat_statements`.
- You're doing bulk DML — `INSERT ... ON CONFLICT` over thousands of rows,
  or `UPDATE ... FROM` joins.
- You need `RETURNING` to atomically read what you just wrote.
- The query touches JSONB operators or arrays.
- You need `FOR UPDATE SKIP LOCKED` (work queue).

Rule: ORM for boring CRUD, raw SQL for anything where the shape of the query
matters.

### Common Table Expressions (CTEs)

```sql
-- Non-recursive: readability over single giant subquery
WITH recent_feedback AS (
  SELECT agent_id, AVG(score) AS avg_score, COUNT(*) AS n
  FROM feedback_events
  WHERE created_at > now() - interval '7 days'
  GROUP BY agent_id
),
ranked AS (
  SELECT a.id, a.name, rf.avg_score, rf.n,
         ROW_NUMBER() OVER (ORDER BY rf.avg_score DESC) AS rk
  FROM agents a
  JOIN recent_feedback rf ON rf.agent_id = a.id
  WHERE rf.n >= 5
)
SELECT * FROM ranked WHERE rk <= 10;
```

**PG 12+ change**: CTEs are now inlined by default (the planner can push
predicates through them). Pre-12 they were always an "optimization fence".
To force the old behavior: `WITH foo AS MATERIALIZED (...)`. To force
inlining when the planner won't: `WITH foo AS NOT MATERIALIZED (...)`.

Use `MATERIALIZED` when:
- The CTE is referenced multiple times and is expensive to compute.
- You're using `WITH ... AS (DELETE ... RETURNING ...)` and need it to
  actually run once.
- A CTE with side effects (`INSERT`/`UPDATE`/`DELETE` inside `WITH`).

Recursive CTE for trees (e.g., EOS agent hierarchy):

```sql
WITH RECURSIVE org_tree AS (
  SELECT id, name, parent_id, 1 AS depth, ARRAY[id] AS path
  FROM agents
  WHERE parent_id IS NULL

  UNION ALL

  SELECT a.id, a.name, a.parent_id, ot.depth + 1, ot.path || a.id
  FROM agents a
  JOIN org_tree ot ON a.parent_id = ot.id
  WHERE NOT a.id = ANY(ot.path)  -- cycle guard
)
SELECT * FROM org_tree ORDER BY path;
```

### Window functions

```sql
-- Latest memory per agent (without GROUP BY gymnastics)
SELECT agent_id, content, created_at
FROM (
  SELECT agent_id, content, created_at,
         ROW_NUMBER() OVER (PARTITION BY agent_id ORDER BY created_at DESC) AS rn
  FROM memories
) t
WHERE rn = 1;
```

`ROW_NUMBER()` always unique. `RANK()` leaves gaps on ties.
`DENSE_RANK()` no gaps on ties.

```sql
-- Day-over-day change in feedback volume
SELECT day, n,
       LAG(n)  OVER (ORDER BY day) AS prev_n,
       n - LAG(n) OVER (ORDER BY day) AS delta
FROM (
  SELECT date_trunc('day', created_at) AS day, COUNT(*) AS n
  FROM feedback_events
  GROUP BY 1
) d;
```

Frame clauses (running totals):

```sql
SELECT day, n,
       SUM(n) OVER (ORDER BY day ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cumulative,
       AVG(n) OVER (ORDER BY day ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)         AS rolling_7d
FROM daily_counts;
```

### LATERAL joins

Like a correlated subquery but readable. Each row of the left side feeds
the right side as a parameter.

```sql
-- Top 3 memories per agent
SELECT a.id, a.name, m.content, m.score
FROM agents a
CROSS JOIN LATERAL (
  SELECT content, score
  FROM memories
  WHERE agent_id = a.id
  ORDER BY score DESC
  LIMIT 3
) m;
```

`LEFT JOIN LATERAL ... ON true` if you want agents with no memories included.

### DISTINCT ON

Postgres-specific. Returns the first row per group as defined by `ORDER BY`.

```sql
-- Latest feedback per agent in one statement
SELECT DISTINCT ON (agent_id) agent_id, score, created_at
FROM feedback_events
ORDER BY agent_id, created_at DESC;
```

The columns in `DISTINCT ON` must be the leftmost columns in `ORDER BY`.

### INSERT ... ON CONFLICT (UPSERT)

```sql
INSERT INTO skills (slug, name, description, version)
VALUES ('neon_postgres', 'Neon Postgres', '...', 2)
ON CONFLICT (slug) DO UPDATE SET
  name        = EXCLUDED.name,
  description = EXCLUDED.description,
  version     = EXCLUDED.version,
  updated_at  = now()
WHERE skills.version < EXCLUDED.version  -- only bump if newer
RETURNING id, (xmax = 0) AS inserted;
```

`EXCLUDED.*` is the row that would have been inserted. The `WHERE` clause on
`DO UPDATE` is the killer feature — conditional upsert. The `xmax = 0` trick
tells you whether the row was inserted vs updated.

`DO NOTHING` for "insert if absent":

```sql
INSERT INTO tags (name) VALUES ('ai'), ('llm'), ('rag')
ON CONFLICT (name) DO NOTHING
RETURNING id, name;  -- only returns the actually-inserted rows
```

### MERGE (PG 15+)

More expressive than `ON CONFLICT` because it handles multiple match
conditions and `DELETE`. But `ON CONFLICT` is faster and more atomic for
the common upsert case. Use `MERGE` only when you need its semantics.

```sql
MERGE INTO memories m
USING staging_memories s ON m.id = s.id
WHEN MATCHED AND s.content IS NULL THEN DELETE
WHEN MATCHED THEN UPDATE SET content = s.content, updated_at = now()
WHEN NOT MATCHED THEN INSERT (id, content) VALUES (s.id, s.content);
```

### RETURNING

Works on `INSERT`, `UPDATE`, `DELETE`. Atomic — no second round-trip.

```sql
UPDATE agents SET status = 'archived'
WHERE last_active < now() - interval '90 days'
RETURNING id, name, status;
```

### generate_series

Synthetic data, gap-filling:

```sql
-- Fill missing days with zero
SELECT d::date AS day, COALESCE(c.n, 0) AS n
FROM generate_series(now() - interval '30 days', now(), '1 day') d
LEFT JOIN (
  SELECT date_trunc('day', created_at) AS day, COUNT(*) AS n
  FROM feedback_events
  GROUP BY 1
) c ON c.day = d::date;
```

### JSONB operators

| Op       | Meaning                              |
|----------|--------------------------------------|
| `->`     | Get field as JSONB                   |
| `->>`    | Get field as text                    |
| `#>`     | Get path as JSONB (`'{a,b}'`)        |
| `#>>`    | Get path as text                     |
| `@>`     | Contains (left contains right)       |
| `<@`     | Contained by                         |
| `?`      | Top-level key exists                 |
| `?&`     | All keys exist                       |
| `?\|`    | Any key exists                       |
| `\|\|`   | Concat                               |
| `-`      | Remove key/index                     |
| `#-`     | Remove path                          |

```sql
-- Memories tagged with both 'priority' and 'urgent'
SELECT id, content
FROM memories
WHERE metadata @> '{"tags": ["priority", "urgent"]}'::jsonb;

-- Update one key without rewriting the rest
UPDATE memories
SET metadata = jsonb_set(metadata, '{score}', '0.9'::jsonb, true)
WHERE id = $1;

-- Aggregate keys
SELECT jsonb_object_agg(k, v) FROM (
  SELECT key AS k, value AS v
  FROM memories, jsonb_each_text(metadata)
) t;

-- Expand JSONB array into rows
SELECT id, tag
FROM memories, jsonb_array_elements_text(metadata->'tags') AS tag;
```

### Array operators

```sql
WHERE id = ANY($1::int[])           -- vs huge IN list
WHERE tags && ARRAY['ai','rag']     -- overlap
WHERE tags @> ARRAY['ai']           -- contains
SELECT unnest(tags) FROM memories;  -- array → rows
```

### Full-text search

```sql
ALTER TABLE memories
ADD COLUMN tsv tsvector
GENERATED ALWAYS AS (to_tsvector('english', coalesce(content, ''))) STORED;

CREATE INDEX memories_tsv_idx ON memories USING GIN (tsv);

SELECT id, content,
       ts_rank(tsv, query) AS rank
FROM memories, to_tsquery('english', 'agent & hierarchy') query
WHERE tsv @@ query
ORDER BY rank DESC LIMIT 20;
```

### FILTER on aggregates

Cleaner than `CASE WHEN ... END` inside `SUM`.

```sql
SELECT
  agent_id,
  COUNT(*) AS total,
  COUNT(*) FILTER (WHERE score >= 0.8) AS good,
  COUNT(*) FILTER (WHERE score <  0.4) AS bad,
  AVG(score) FILTER (WHERE created_at > now() - interval '1 day') AS avg_today
FROM feedback_events
GROUP BY agent_id;
```

### GROUPING SETS / ROLLUP / CUBE

Multiple group-bys in one pass.

```sql
SELECT venture, agent_id, COUNT(*)
FROM feedback_events
GROUP BY GROUPING SETS ((venture, agent_id), (venture), ());
-- Returns: per (venture,agent), per venture, and grand total

SELECT venture, agent_id, COUNT(*)
FROM feedback_events
GROUP BY ROLLUP (venture, agent_id);
-- Hierarchical subtotals
```

---

## 2. EXPLAIN and EXPLAIN ANALYZE

### Forms

- `EXPLAIN sql` — planner's estimated plan, no execution.
- `EXPLAIN ANALYZE sql` — actually runs the query (DML included — wrap in
  `BEGIN; ... ROLLBACK;` for safety).
- Full form:
  ```sql
  EXPLAIN (ANALYZE, BUFFERS, COSTS, VERBOSE, TIMING, SETTINGS, WAL, FORMAT TEXT) sql;
  ```

Always run with `BUFFERS` — it tells you how much I/O happened, which matters
more than wall-clock time on a shared system.

### Reading a plan

- The plan is a tree. Root is the **last** step. Indentation = parent/child.
- Read leaves first, then up.
- Each node shows:
  `cost=startup..total rows=estimated width=bytes (actual time=startup..total rows=actual loops=N)`.
- `cost` is in arbitrary planner units, not ms. Don't compare to time.
- `actual rows × loops = total rows produced` for that node.

### Key node types

| Node | What it means |
|---|---|
| **Seq Scan** | Full table read. Fine for small tables; bad on large filtered queries. |
| **Index Scan** | Walks an index then fetches heap rows. Good for selective filters. |
| **Index Only Scan** | Answer fully in the index — no heap fetch. Requires `INCLUDE` columns or covering index, and a recent VACUUM (visibility map). |
| **Bitmap Heap Scan** | Builds bitmap of matching rows from one or more indexes, then reads heap pages in order. Good when matching many rows. |
| **Nested Loop** | For each outer row, look up inner. Great for small outer × indexed inner. Disaster otherwise. |
| **Hash Join** | Build hash on smaller side, probe with larger. Good for big × big with no useful index. |
| **Merge Join** | Both sides sorted on join key. Good when sort already exists. |
| **Sort** | Watch for `Sort Method: external merge Disk: ...kB` — work_mem too small. |
| **Hash Aggregate** | Group by hashing. Watch for spill to disk. |
| **GroupAggregate** | Group by sort. Used when input already sorted. |
| **Gather / Gather Merge** | Parallel workers feeding into a leader. |

### What rows= and actual rows= tell you

If `rows=10` (estimated) but `actual rows=10000` — the planner has bad stats.
Run `ANALYZE`. If still off, `ALTER TABLE ... ALTER COLUMN x SET STATISTICS 1000;`
and re-ANALYZE. For correlated columns, use extended statistics.

A 10x mis-estimate at any node usually leads to a wrong join algorithm choice
further up.

### Buffers

```
Buffers: shared hit=12 read=388 dirtied=2
```
- `shared hit` — page already in PG cache.
- `read` — page fetched from OS (which might be its cache or disk).
- `dirtied` — page modified.
- `written` — page evicted.

Optimization target: minimize `read`. If `read` is high but `time` is low,
you're getting lucky on OS cache; on a cold cache it'll be slow.

### loops= matters on Nested Loop inner

```
->  Nested Loop  (rows=1000)
      ->  Seq Scan on a  (actual rows=1000 loops=1)
      ->  Index Scan on b  (actual rows=1 loops=1000)
```

The inner index scan ran **1000 times**. If you saw `actual rows=1` and
forgot `loops=`, you'd think it was cheap. It's `1 × 1000 = 1000` lookups.

### The 3 classic problems

1. **Missing index** → Seq Scan on a big table with selective WHERE.
2. **Bad row estimate** → estimated vs actual differ by >10x → Nested Loop
   chosen wrongly.
3. **Unexpected Seq Scan** despite an index → planner thinks Seq Scan is
   cheaper (often correct on small tables, sometimes wrong because of stale
   stats or unindexable expression like `WHERE lower(email) = ...` without an
   expression index).

### Visualizers

- https://explain.depesz.com — colored bottlenecks, easiest to read.
- https://explain.dalibo.com — interactive flame-graph, requires `FORMAT JSON`.
- pev2 (self-host).

### Worked example (EOS-shaped)

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT m.id, m.content
FROM memories m
JOIN agents a ON a.id = m.agent_id
WHERE a.org_id = 'org_123'
  AND m.created_at > now() - interval '7 days'
ORDER BY m.created_at DESC LIMIT 50;
```

Bad plan signal:

```
Limit  (cost=... rows=50)
  ->  Sort  (rows=120000)
        Sort Key: m.created_at DESC
        Sort Method: external merge  Disk: 14MB
        ->  Hash Join
              ->  Seq Scan on memories m
              ->  Hash
                    ->  Seq Scan on agents a  Filter: org_id = ...
```

Fix: `CREATE INDEX ON memories (agent_id, created_at DESC);` and
`CREATE INDEX ON agents (org_id);`. Re-run; expect Nested Loop with
Index Scan, no Sort, no Disk.

---

## 3. Indexing Strategy

### Types

| Type | Use for |
|---|---|
| **B-tree** | Default. Equality + range + ORDER BY + IS NULL. |
| **Hash** | Equality only. Rarely beats B-tree. Skip. |
| **GIN** | Multi-value: arrays, JSONB, tsvector, trgm. Slow writes, fast contains. |
| **GiST** | Geometric, ranges, exclusion constraints, trigram. |
| **SP-GiST** | Non-balanced trees: phone numbers, IPs. Niche. |
| **BRIN** | Massive, naturally-ordered (time-series append). Tiny index, coarse. |
| **HNSW** (pgvector) | Vector similarity. PG 16 + pgvector 0.5+. |
| **IVFFlat** (pgvector) | Older vector index. HNSW usually wins now. |

### Multi-column order

PG B-tree supports a leftmost-prefix rule similar to MySQL but with twists:

- An index on `(a, b, c)` can serve `WHERE a=?`, `WHERE a=? AND b=?`,
  `WHERE a=? AND b=? AND c=?`.
- It can also serve `WHERE a=? AND c=?` (skips `b` via in-index filter,
  less efficient).
- It generally **cannot** serve `WHERE b=?` alone.
- Order: equality columns first, then the range/ORDER BY column. Selectivity
  matters less than access pattern.

Example: query is `WHERE org_id=? AND created_at > ? ORDER BY created_at DESC`.
Index = `(org_id, created_at DESC)`. The DESC matters if you scan in reverse
a lot.

### Covering indexes (INCLUDE)

PG 11+. Adds non-key columns to the leaf so an Index Only Scan can return
them without heap fetch.

```sql
CREATE INDEX memories_agent_created_idx
ON memories (agent_id, created_at DESC) INCLUDE (content);
```

Now `SELECT content FROM memories WHERE agent_id=? ORDER BY created_at DESC LIMIT 10`
is index-only.

### Partial indexes

Index only the rows that matter. Cheaper to maintain, smaller, faster.

```sql
CREATE INDEX active_agents_idx ON agents (org_id) WHERE status = 'active';
CREATE INDEX pending_jobs_idx  ON jobs (created_at) WHERE state = 'pending';
```

### Expression indexes

Index a function of a column. Required if your WHERE clause wraps the column
in a function.

```sql
CREATE INDEX users_lower_email_idx ON users (lower(email));
-- Now: WHERE lower(email) = lower($1)  → index used.
```

### CREATE INDEX CONCURRENTLY

No `ACCESS EXCLUSIVE` lock — production-safe. Caveats:

- Cannot run inside a transaction.
- Takes 2 table scans, slower.
- If it fails partway you get an `INVALID` index — drop it
  (`DROP INDEX CONCURRENTLY`) and retry.
- Check status:
  `SELECT indexrelid::regclass, indisvalid FROM pg_index WHERE NOT indisvalid;`
- On Neon: works, but uses compute time; consider running during off-peak.

### Unique indexes vs unique constraints

A unique constraint is implemented as a unique index under the hood.
Constraints can be referenced by FKs, indexes can have `WHERE` (partial).
For soft-delete:

```sql
CREATE UNIQUE INDEX users_email_unique
ON users (email) WHERE deleted_at IS NULL;
```

A unique constraint can't do that.

### Bloat and REINDEX

B-tree indexes bloat after heavy updates/deletes. Symptoms: index size >>
expected, slow scans. Fix:

```sql
REINDEX INDEX CONCURRENTLY memories_agent_idx;
```

PG 12+ supports `CONCURRENTLY`. On Neon, `pg_repack` extension is the cleaner
alternative for tables.

### Unused indexes

```sql
SELECT schemaname, relname AS table, indexrelname AS index,
       idx_scan, pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND indexrelname NOT LIKE '%_pkey'
ORDER BY pg_relation_size(indexrelid) DESC;
```

Drop them. Each index costs writes.

### Duplicate indexes

```sql
SELECT indrelid::regclass, array_agg(indexrelid::regclass)
FROM pg_index
GROUP BY indrelid, indkey
HAVING COUNT(*) > 1;
```

### JSONB indexing

```sql
-- Full GIN: every key + value indexed
CREATE INDEX memories_meta_gin ON memories USING GIN (metadata);

-- Smaller GIN, only @> queries supported
CREATE INDEX memories_meta_gin_ops ON memories USING GIN (metadata jsonb_path_ops);

-- Expression index for hot key
CREATE INDEX memories_meta_priority ON memories ((metadata->>'priority'));
```

### Rule of thumb

Index every FK. Index every column appearing in slow-query
`WHERE`/`JOIN`/`ORDER BY`. Then drop unused indexes monthly.

---

## 4. Transactions and Locking

### Isolation levels

- **READ UNCOMMITTED** — Postgres treats as READ COMMITTED. Doesn't exist.
- **READ COMMITTED** (default) — each statement sees a fresh snapshot.
- **REPEATABLE READ** — entire transaction sees one snapshot. Detects
  write-write conflicts.
- **SERIALIZABLE** — full serializability via SSI (Serializable Snapshot
  Isolation). May raise `serialization_failure`; you must retry.

```sql
BEGIN ISOLATION LEVEL SERIALIZABLE;
-- ... queries ...
COMMIT;
```

### Row locks

| Mode | Blocks | Use |
|---|---|---|
| `FOR UPDATE` | other writers and locks | classic "select then update" |
| `FOR NO KEY UPDATE` | weaker, doesn't block FK checks | UPDATE that doesn't change PK |
| `FOR SHARE` | other writers | reads that need stability |
| `FOR KEY SHARE` | only key updates | FK checks use this |

Modifiers:

- `NOWAIT` — fail immediately if can't lock.
- `SKIP LOCKED` — skip locked rows. **The work-queue pattern.**

```sql
-- Atomic claim of next job
WITH next AS (
  SELECT id FROM jobs
  WHERE state = 'pending'
  ORDER BY created_at
  FOR UPDATE SKIP LOCKED
  LIMIT 1
)
UPDATE jobs j SET state = 'running', started_at = now()
FROM next WHERE j.id = next.id
RETURNING j.*;
```

Multiple workers run this concurrently and never collide. No deadlocks.

### Table locks

`LOCK TABLE x IN <mode>`. Modes (least to most restrictive):

1. ACCESS SHARE — `SELECT`
2. ROW SHARE — `SELECT FOR UPDATE`
3. ROW EXCLUSIVE — `INSERT/UPDATE/DELETE`
4. SHARE UPDATE EXCLUSIVE — `VACUUM`, `CREATE INDEX CONCURRENTLY`, `ANALYZE`
5. SHARE — `CREATE INDEX` (non-concurrent)
6. SHARE ROW EXCLUSIVE — rare
7. EXCLUSIVE — rare
8. ACCESS EXCLUSIVE — `DROP TABLE`, `TRUNCATE`, most `ALTER TABLE`,
   non-concurrent `REINDEX`

Most production "the database froze for 30 seconds" incidents are an
`ALTER TABLE` taking ACCESS EXCLUSIVE behind a long query. Mitigate with
`lock_timeout = '2s'` on the migration session.

### Advisory locks

Application-defined mutex stored in PG. Two namespaces (single bigint or
two ints).

```sql
SELECT pg_try_advisory_lock(42);          -- session-level, non-blocking
SELECT pg_advisory_xact_lock(42);          -- transaction-level, blocks
SELECT pg_advisory_unlock(42);
```

Use for "only one cron worker should run this job at a time" without a
dedicated locks table.

### Deadlock detection

PG detects cycles after `deadlock_timeout` (1s default) and aborts one
transaction. Inspect:

```sql
SELECT pid, state, wait_event_type, wait_event, query
FROM pg_stat_activity
WHERE wait_event_type = 'Lock';

SELECT blocked.pid AS blocked_pid, blocking.pid AS blocking_pid,
       blocked.query AS blocked_query, blocking.query AS blocking_query
FROM pg_stat_activity blocked
JOIN pg_stat_activity blocking ON blocking.pid = ANY(pg_blocking_pids(blocked.pid))
WHERE blocked.wait_event_type = 'Lock';
```

### `idle in transaction`

The #1 cause of pool death. App opens BEGIN, runs a SELECT, then... waits
for Redis... then crashes. PG row locks held the whole time. Other writers
wait. Vacuum can't reclaim dead tuples. Bloat explodes.

Mitigations on Neon/PG:

```sql
ALTER ROLE app SET idle_in_transaction_session_timeout = '30s';
ALTER ROLE app SET statement_timeout = '30s';
ALTER ROLE app SET lock_timeout = '5s';
```

**EOS rule**: every BEGIN must be in a `with conn:` block, no I/O between
BEGIN and COMMIT except DB. `get_conn()` already enforces this shape.

### Long transactions block VACUUM

A 24h transaction means VACUUM cannot remove any dead tuple created after
it started, across the whole database. Bloat compounds. Watch:

```sql
SELECT pid, now() - xact_start AS age, state, query
FROM pg_stat_activity
WHERE xact_start IS NOT NULL ORDER BY age DESC;
```

Kill anything older than your tolerance: `SELECT pg_terminate_backend(pid);`

### SERIALIZABLE retry pattern

```python
import psycopg2.errors
for attempt in range(5):
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("BEGIN ISOLATION LEVEL SERIALIZABLE")
                # ... work ...
        break
    except psycopg2.errors.SerializationFailure:
        time.sleep(0.05 * (2 ** attempt))
else:
    raise RuntimeError("too many retries")
```

### Savepoints

```sql
BEGIN;
INSERT ...;
SAVEPOINT s1;
INSERT ...;  -- might fail
ROLLBACK TO s1;  -- only undo since savepoint
COMMIT;
```

psycopg2: `with conn.cursor() as cur: ...` doesn't auto-savepoint. Use
`conn.cursor()` and explicit savepoints, or psycopg3's
`with conn.transaction(): with conn.transaction(): ...` (nested = savepoints).

### Two-phase commit

`PREPARE TRANSACTION 'name'` then `COMMIT PREPARED 'name'`. For distributed
transactions across DBs. Almost never needed; if you think you need it you
probably want an outbox table.

---

## 5. Query Planning

### What the planner does

For each query, generate candidate plans, estimate cost (I/O + CPU units),
pick the cheapest. Cost estimation uses statistics in `pg_statistic`
(visible via `pg_stats`).

### Statistics

```sql
SELECT attname, null_frac, n_distinct, most_common_vals, most_common_freqs, histogram_bounds
FROM pg_stats WHERE tablename = 'memories';
```

- `n_distinct` — number of distinct values. Negative means fraction
  (-0.5 = half are distinct).
- `most_common_vals` (MCVs) — top N values and their frequencies. PG uses
  these for selectivity on `=`.
- `histogram_bounds` — buckets for range estimation.

### ANALYZE

Statistics are gathered by `ANALYZE` (manual) and `autovacuum` (automatic,
after enough changes). After a bulk load, **always** `ANALYZE` manually.
The planner uses zero stats until ANALYZE runs.

```sql
ANALYZE memories;
ANALYZE memories (content, agent_id);  -- specific columns
```

### Bad stats → bad plans

If `EXPLAIN` shows estimated rows wildly different from actual rows, that's
a stats problem. Fixes:

1. `ANALYZE` the table.
2. Increase sample size:
   `ALTER TABLE memories ALTER COLUMN agent_id SET STATISTICS 1000;`
   (default is `default_statistics_target = 100`, max 10000).
3. For correlated columns, extended stats:

```sql
CREATE STATISTICS memories_corr (dependencies, ndistinct)
ON agent_id, venture FROM memories;
ANALYZE memories;
```

### Cost parameters

| Param | Default | Tune to |
|---|---|---|
| `seq_page_cost` | 1.0 | leave |
| `random_page_cost` | 4.0 | **1.1 on SSD** (Neon default already ~1.1) |
| `effective_cache_size` | 4GB | ~75% of RAM |
| `work_mem` | 4MB | per-sort allocation; raise for analytics |
| `shared_buffers` | 128MB | 25% of RAM (Neon-managed) |

`random_page_cost` matters: too high and the planner avoids index scans on
big tables.

### Join order

Planner explores `join_collapse_limit` (default 8) join orderings
exhaustively. Beyond that it uses GEQO (genetic). For 12+ table joins, set
`from_collapse_limit` and `join_collapse_limit` to keep exhaustive search if
planning time isn't a concern.

### OFFSET is slow

`OFFSET 10000 LIMIT 50` reads and discards 10000 rows. Always. Use keyset:

```sql
SELECT id, content FROM memories
WHERE (created_at, id) < ($cursor_ts, $cursor_id)
ORDER BY created_at DESC, id DESC
LIMIT 50;
```

### Hints

Vanilla PG has no planner hints (deliberately). The `pg_hint_plan` extension
exists but Neon doesn't ship it. Workarounds: rewrite the query, add stats,
use CTEs as `MATERIALIZED` to fence, or `SET LOCAL enable_seqscan = off` as
a last resort.

### Prepared statement gotcha

psycopg2 doesn't auto-prepare. psycopg3 can. JDBC and asyncpg do. PG runs
the first 5 executions of a prepared statement with custom plans
(parameter-aware), then switches to a generic plan. If the parameter
distribution is skewed, the generic plan can be 100x slower.

To force custom plans: `SET plan_cache_mode = force_custom_plan;` in the
session. Or don't reuse the prepared statement across very different
parameter values.

---

## 6. Slow Query Debugging

### pg_stat_statements

The single most valuable extension. Tracks every query (normalized with
`$1, $2`) with cumulative time, calls, rows, IO.

```sql
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

SELECT round(total_exec_time::numeric, 0) AS total_ms,
       calls,
       round((total_exec_time / calls)::numeric, 2) AS avg_ms,
       round((100 * total_exec_time / sum(total_exec_time) OVER ())::numeric, 1) AS pct,
       left(query, 120) AS query
FROM pg_stat_statements
ORDER BY total_exec_time DESC LIMIT 20;

-- Reset after a change to see new behavior
SELECT pg_stat_statements_reset();
```

Neon ships this enabled. Query it weekly; the top 5 by `total_exec_time` is
your optimization queue.

### Slow query log

```sql
ALTER DATABASE eos SET log_min_duration_statement = '1000';  -- ms
```

On Neon, view logs via Console.

### auto_explain

```sql
LOAD 'auto_explain';
SET auto_explain.log_min_duration = '1000';
SET auto_explain.log_analyze = on;
SET auto_explain.log_buffers = on;
```

Plans of slow queries appear in the log automatically.

### pg_stat_activity

```sql
SELECT pid, usename, application_name, state,
       wait_event_type, wait_event,
       now() - query_start AS runtime,
       left(query, 200) AS query
FROM pg_stat_activity
WHERE state != 'idle' AND pid != pg_backend_pid()
ORDER BY runtime DESC;
```

`wait_event_type` tells you what it's stuck on: `Lock`, `IO`, `LWLock`,
`Client`, `Extension`.

### Cancel vs terminate

- `pg_cancel_backend(pid)` — sends SIGINT, cancels current query, keeps
  connection.
- `pg_terminate_backend(pid)` — sends SIGTERM, kills the connection.

Cancel first, terminate if it doesn't respond.

### Lock waits

```sql
SELECT a.pid AS waiter_pid, a.query AS waiter_query,
       b.pid AS holder_pid, b.query AS holder_query,
       l.mode, l.relation::regclass
FROM pg_locks l
JOIN pg_stat_activity a ON a.pid = l.pid AND NOT l.granted
JOIN pg_locks lh ON lh.relation = l.relation AND lh.granted
JOIN pg_stat_activity b ON b.pid = lh.pid;
```

### Bloat detection

```sql
CREATE EXTENSION IF NOT EXISTS pgstattuple;
SELECT * FROM pgstattuple('memories');
-- dead_tuple_percent > 20%? VACUUM time.
```

### Missing index hints

```sql
SELECT relname, seq_scan, seq_tup_read,
       idx_scan, n_live_tup,
       seq_tup_read / NULLIF(seq_scan, 0) AS avg_seq_read
FROM pg_stat_user_tables
WHERE seq_scan > 100 AND n_live_tup > 10000
ORDER BY seq_tup_read DESC;
```

High `seq_scan` + high `seq_tup_read` on a big table = missing index
probable.

### Neon-specific

- Cold start adds latency to the first query after autosuspend
  (~500ms-2s).
- `pg_stat_statements` survives compute restart (backed in shared catalogs).
- Use the `-pooler` endpoint for short-lived workloads; the direct endpoint
  for long-running ones (the pooler is in transaction mode and breaks
  `LISTEN/NOTIFY`, prepared statements, session `SET`).

---

## 7. Postgres Optimization Patterns Relevant to EOS

### Keyset pagination

Already covered. Always use it for memory lists, feedback timelines, agent
activity feeds.

### Avoid `SELECT *`

- Forces more columns through the network.
- Breaks Index Only Scan if the index doesn't cover all columns.
- Brittle: schema changes silently change result shape.

### JSONB strategy

Hot read-path columns: extract to real columns. JSONB for variable schema
(per-tenant configs, agent metadata).

### timestamptz, always

`timestamp` (without tz) silently drops timezone, causing 8h bugs. Always
`timestamptz`. Store UTC. PG converts on display per session `TIME ZONE`.

### UUIDs

Use the `uuid` type, not `text`. Half the bytes, faster compares, native gen.

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;
SELECT gen_random_uuid();
```

For time-ordered (better B-tree locality), UUID v7. PG 18 will ship it
natively; until then, generate in app or use the `pg_uuidv7` extension if
available.

### Soft-delete with partial unique index

```sql
CREATE UNIQUE INDEX users_email_active
ON users (email) WHERE deleted_at IS NULL;
```

### Materialized views

```sql
CREATE MATERIALIZED VIEW mv_agent_stats AS
SELECT agent_id, COUNT(*) AS n, AVG(score) AS avg_score
FROM feedback_events GROUP BY agent_id;

CREATE UNIQUE INDEX ON mv_agent_stats (agent_id);  -- required for CONCURRENTLY

REFRESH MATERIALIZED VIEW CONCURRENTLY mv_agent_stats;
```

`CONCURRENTLY` requires a unique index. Without it, refresh takes
ACCESS EXCLUSIVE.

### Triggers

Good for: audit logs, derived columns (`updated_at`), denormalization.
Bad for: business logic, side effects, cross-table cascades that should be
explicit. Triggers fire silently — debugging is brutal.

### Row-Level Security (EOS uses this)

```sql
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;

CREATE POLICY memories_org_isolation ON memories
USING (org_id = current_setting('app.current_org_id')::uuid);

CREATE POLICY memories_org_insert ON memories FOR INSERT
WITH CHECK (org_id = current_setting('app.current_org_id')::uuid);

-- In application, per request:
SET LOCAL app.current_org_id = 'org_abc123';
```

Use `SET LOCAL` (transaction-scoped) not `SET` (session-scoped) — session
pooling will leak the value across requests otherwise. EOS `get_conn()`
already does this correctly.

Performance: RLS adds the policy expression to every query as a WHERE
clause. Make sure the column it filters on is indexed. The planner can
usually push the predicate down.

Bypass: `BYPASSRLS` role attribute, or owner of table (unless
`FORCE ROW LEVEL SECURITY`).

### Connection pooling

Neon `-pooler` = pgbouncer in **transaction mode**.

- Each transaction gets a backend, returned on COMMIT.
- Massive client count (tens of thousands).
- No prepared statements (psycopg3 has a workaround; psycopg2 fine if you
  don't use `prepare=True`).
- No `LISTEN/NOTIFY` (notification arrives on a different backend).
- No session `SET` — only `SET LOCAL` inside a transaction.
- No advisory session locks — only `pg_advisory_xact_lock`.
- No cursors that span transactions.

Pool modes:

- **session**: client owns backend until disconnect. Compatible but doesn't
  multiplex.
- **transaction**: backend per transaction. Default for Neon pooler.
- **statement**: backend per statement. Breaks anything multi-statement.
  Avoid.

EOS rule: app always connects via `-pooler` for short queries. For
migrations, batch jobs, or anything with `LISTEN/NOTIFY`, connect to the
direct endpoint.

### Vacuum

- Autovacuum runs when dead tuples exceed
  `autovacuum_vacuum_threshold + autovacuum_vacuum_scale_factor * n_live_tup`
  (default scale 0.2 = 20%).
- For high-churn tables, lower the scale:
  `ALTER TABLE jobs SET (autovacuum_vacuum_scale_factor = 0.05);`
- `VACUUM` reclaims dead tuples for reuse. `VACUUM FULL` rewrites the table
  — takes ACCESS EXCLUSIVE, never run on production. Use `pg_repack`
  instead.
- `VACUUM ANALYZE` does both.

### pgvector (EOS embeddings)

```sql
CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE memories ADD COLUMN embedding vector(1536);

-- HNSW (PG 16, pgvector 0.5+)
CREATE INDEX memories_embedding_hnsw
ON memories USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Query
SELECT id, content, 1 - (embedding <=> $1) AS similarity
FROM memories
WHERE org_id = $2  -- RLS or explicit
ORDER BY embedding <=> $1
LIMIT 10;
```

Operators: `<->` L2, `<#>` negative inner product, `<=>` cosine distance.

`SET hnsw.ef_search = 100;` for higher recall at query time.

**EOS memories table** uses `embedding vector(1536)` (OpenAI ada-002 /
small-3 dimensionality). HNSW is the preferred index on Neon — faster recall
than IVFFlat for the sizes EOS operates at. Build index with elevated
`maintenance_work_mem` on huge tables; scale Neon compute up temporarily
for the build.

### Bulk write patterns

- Multi-row INSERT: `INSERT INTO t (a,b) VALUES ($1,$2),($3,$4),...` — 10x
  faster than per-row.
- `COPY` — 100x faster for large loads.
- `INSERT ... SELECT FROM unnest($1::int[], $2::text[])` — array unpacking,
  also fast.

---

## 8. Raw SQL via psycopg2 / psycopg3

### Parameterized queries (NEVER format strings)

```python
# RIGHT
cur.execute("SELECT * FROM agents WHERE id = %s AND org_id = %s", (agent_id, org_id))

# RIGHT (named)
cur.execute(
    "SELECT * FROM agents WHERE id = %(id)s AND org_id = %(org)s",
    {"id": agent_id, "org": org_id},
)

# WRONG — SQL injection
cur.execute(f"SELECT * FROM agents WHERE id = '{agent_id}'")
```

`psycopg2.sql.SQL` and `Identifier` for dynamic table/column names:

```python
from psycopg2 import sql
cur.execute(
    sql.SQL("SELECT * FROM {tbl} WHERE id = %s").format(tbl=sql.Identifier("agents")),
    (agent_id,),
)
```

### Bulk inserts

```python
from psycopg2.extras import execute_values

execute_values(
    cur,
    "INSERT INTO memories (agent_id, content, metadata) VALUES %s",
    [(a, c, json.dumps(m)) for a, c, m in rows],
    template="(%s, %s, %s::jsonb)",
    page_size=1000,
)
```

Vastly faster than calling `cur.execute` in a loop.

### COPY (fastest bulk load)

```python
import io
buf = io.StringIO()
for row in rows:
    buf.write(f"{row[0]}\t{row[1]}\n")
buf.seek(0)
cur.copy_expert("COPY memories (agent_id, content) FROM STDIN", buf)
```

psycopg3 cleaner:

```python
with cur.copy("COPY memories (agent_id, content) FROM STDIN") as copy:
    for row in rows:
        copy.write_row(row)
```

### Server-side cursors (huge results)

```python
with conn.cursor(name="big_query") as cur:  # named = server-side
    cur.itersize = 10000
    cur.execute("SELECT * FROM memories")
    for row in cur:
        process(row)
```

Without a name, psycopg2 fetches the entire result into memory.

### Connection pooling

- psycopg2: `psycopg2.pool.ThreadedConnectionPool` (basic) or pgbouncer in
  front of it.
- psycopg3: `psycopg_pool.ConnectionPool` or `AsyncConnectionPool`
  (better, async-aware).

EOS pattern: pool in app, pgbouncer (Neon `-pooler`) on the wire. Two layers.

### `with conn:` semantics

```python
with conn:                # transaction; commits on success, rolls back on exception
    with conn.cursor() as cur:
        cur.execute(...)
# conn is NOT closed here — only the transaction ended.
```

psycopg3: `with conn.transaction(): ...` is the preferred form, supports
nesting via savepoints.

To actually close: `conn.close()` or `with closing(conn):`.

### JSONB round-trip

psycopg2 auto-decodes JSONB to dict (via `register_default_jsonb`, default
since 2.5). Pass dicts through `json.dumps` then cast `::jsonb` in SQL, or
use `psycopg2.extras.Json`:

```python
from psycopg2.extras import Json
cur.execute("INSERT INTO memories (metadata) VALUES (%s)", (Json({"k": "v"}),))
```

psycopg3 handles dicts natively.

### Setting RLS context per request

```python
@contextmanager
def org_scoped_conn(org_id):
    conn = pool.getconn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SET LOCAL app.current_org_id = %s", (str(org_id),))
            yield conn
    finally:
        pool.putconn(conn)
```

`SET LOCAL` is critical — it dies with the transaction, so the pooler
can't leak it. This is exactly what EOS `get_conn()` does.

---

## 9. Gotchas (the ones that bite in production)

- `idle in transaction` from app code holding a BEGIN open across HTTP I/O
  → row locks held → pool exhaustion.
- `OFFSET 10000` queries that look fast in dev (small table) and die in prod.
- Forgetting `ANALYZE` after bulk load → planner has zero stats → all
  Nested Loops.
- `CREATE INDEX` (without CONCURRENTLY) on a production table
  → ACCESS EXCLUSIVE → outage.
- `ALTER TABLE ... ADD COLUMN ... DEFAULT <volatile>` rewrites the whole
  table. PG 11+ made constant defaults instant; volatile ones (`now()`)
  still rewrite.
- Using `timestamp` instead of `timestamptz` → 8h drift after deploy region
  change.
- Putting prepared statements behind a transaction-mode pooler
  → "prepared statement does not exist".
- `SET` (not `SET LOCAL`) behind a pooler → setting leaks across unrelated
  requests; in EOS this would mean cross-org RLS leaks.
- `jsonb_path_ops` GIN index used by query that needs `?` operator → not
  used (only `@>` works on path_ops).
- B-tree index on a low-cardinality boolean → useless. Use a partial index
  instead.
- `CREATE INDEX CONCURRENTLY` failing silently — leaves an `INVALID` index
  that consumes writes but answers nothing.
- `SELECT count(*) FROM big_table` is slow in PG (no count cache like
  MyISAM). Use `pg_class.reltuples` for an estimate, or maintain a counter
  table.
- Nested Loop with high `loops=` looks cheap per loop but costs
  `time × loops`.
- `REPEATABLE READ` does not detect read-only anomalies — only write-write.
  Use `SERIALIZABLE` if you need true serializability.
- Long pgbouncer transaction-mode session that does `LISTEN` will receive
  no notifications. Use the direct endpoint.
- pgvector HNSW build is slow and memory-heavy on huge tables. Build with
  elevated `maintenance_work_mem`. On Neon, scale compute up temporarily.
- RLS policies without indexes on the policy column = full table scan per
  query.
- `EXPLAIN ANALYZE` on `INSERT/UPDATE/DELETE` actually executes — wrap in
  `BEGIN; ... ROLLBACK;`.
- `pg_stat_statements` normalizes constants but not arrays —
  `WHERE id = ANY(ARRAY[1,2,3])` and `ANY(ARRAY[4,5])` are different rows.
  Use parameterized `ANY($1::int[])` instead.

---

## 10. Verification

After applying any change in this addendum:

```sql
-- Confirm extension and stats are alive
SELECT extname FROM pg_extension WHERE extname IN ('pg_stat_statements','vector','pgcrypto');

-- Top slow queries
SELECT round(total_exec_time::numeric,0) AS ms, calls, left(query,100)
FROM pg_stat_statements ORDER BY total_exec_time DESC LIMIT 10;

-- No invalid indexes
SELECT indexrelid::regclass FROM pg_index WHERE NOT indisvalid;

-- No long-running transactions
SELECT pid, now()-xact_start AS age, state FROM pg_stat_activity
WHERE xact_start IS NOT NULL AND now()-xact_start > interval '5 min';
```

All four queries should return what you expect (extensions present, hot
queries identifiable, no invalid indexes, no zombie transactions).
