# Drizzle ORM — Best Practices Reference

Complete reference following the 19-section Tool Mastery Research Protocol.

---

## Authentication

Drizzle connects to PostgreSQL via a connection string. No API keys, no OAuth — just `DATABASE_URL`.

**EOS pattern — dual pools:**
- `DATABASE_URL` — admin role (`neondb_owner`, BYPASSRLS). Migrations only.
- `DATABASE_APP_URL` — app role (`eos_app`, no BYPASSRLS). All runtime queries. RLS enforced.

Connection setup (Neon WebSocket for Node.js):
```typescript
import { Pool, neonConfig } from '@neondatabase/serverless'
import { drizzle } from 'drizzle-orm/neon-serverless'
import ws from 'ws'

neonConfig.webSocketConstructor = ws
const pool = new Pool({ connectionString: process.env.DATABASE_APP_URL })
const db = drizzle(pool, { schema })
```

For serverless (Vercel/Cloudflare) without transactions, use the HTTP driver:
```typescript
import { drizzle } from 'drizzle-orm/neon-http'
const db = drizzle(process.env.DATABASE_URL!)
```

---

## Core Operations with Exact Signatures

### Select
```typescript
db.select().from(table)                          // → Row[]
db.select({ col: table.col }).from(table)        // → { col: T }[]
db.selectDistinct().from(table)                   // → Row[] (DISTINCT)
db.selectDistinctOn([table.col]).from(table)      // → Row[] (DISTINCT ON)
db.select().from(table).where(predicate)          // filtered
db.select().from(table).orderBy(asc(t.col))       // sorted
db.select().from(table).limit(n).offset(m)        // paginated
db.$count(table)                                  // → number
db.$count(table, predicate)                       // → number (filtered)
```

### Insert
```typescript
db.insert(table).values(row)                      // single
db.insert(table).values([row1, row2])             // batch
db.insert(table).values(row).returning()          // → Row[]
db.insert(table).values(row)
  .onConflictDoNothing()                          // skip on conflict
db.insert(table).values(row)
  .onConflictDoUpdate({ target: t.id, set: {} }) // upsert
```

### Update
```typescript
db.update(table).set({ col: val }).where(pred)               // basic
db.update(table).set({ col: sql`NOW()` }).where(pred)        // SQL expr
db.update(table).set(updates).where(pred).returning()        // → Row[]
```

### Delete
```typescript
db.delete(table).where(pred)                      // basic
db.delete(table).where(pred).returning()          // → Row[]
```

### Filter operators (all from `drizzle-orm`)
`eq`, `ne`, `gt`, `lt`, `gte`, `lte`, `like`, `ilike`, `inArray`, `notInArray`, `isNull`, `isNotNull`, `between`, `and`, `or`, `not`, `exists`, `sql`

### Aggregates
`count`, `sum`, `avg`, `min`, `max`, `countDistinct`, `sumDistinct`, `avgDistinct`

---

## Pagination Patterns

**Offset-based (simple, standard):**
```typescript
const page = 2
const pageSize = 20
await db.select().from(table)
  .orderBy(asc(table.createdAt))
  .limit(pageSize)
  .offset((page - 1) * pageSize)
```

**Cursor-based (performant for large datasets):**
```typescript
await db.select().from(table)
  .where(gt(table.createdAt, lastSeenTimestamp))
  .orderBy(asc(table.createdAt))
  .limit(pageSize)
```

Cursor-based avoids the O(n) skip cost of `OFFSET` on large tables.

---

## Rate Limits

Drizzle itself has no rate limits — it is a client-side ORM. Rate limits come from the database:

- **Neon free tier:** 100 concurrent connections, 3000 compute hours/month
- **Neon paid:** connection limits based on plan (pooled connections via PgBouncer)
- **Connection pool:** set `max` on the Pool to avoid exhausting connections:
  ```typescript
  const pool = new Pool({ connectionString: url, max: 20, idleTimeoutMillis: 30000 })
  ```

---

## Error Codes and Recovery

Drizzle does not wrap database errors. Constraint violations throw the underlying driver's error with PostgreSQL error codes:

| Code | Name | Cause |
|------|------|-------|
| `23505` | unique_violation | Duplicate key on UNIQUE or PK constraint |
| `23503` | foreign_key_violation | Referenced row does not exist |
| `23502` | not_null_violation | NULL in NOT NULL column |
| `23514` | check_violation | CHECK constraint failed |

```typescript
try {
  await db.insert(users).values({ email: 'dup@x.com' })
} catch (e: any) {
  if (e.code === '23505') {
    // handle duplicate
  }
}
```

Transaction errors: any throw inside `db.transaction()` auto-rolls back. `tx.rollback()` throws `TransactionRollbackError` (importable from `drizzle-orm`).

---

## SDK Idioms

**Type inference from schema:**
```typescript
type User    = typeof users.$inferSelect   // result type
type NewUser = typeof users.$inferInsert   // input type
```

**Type-safe JSON columns:**
```typescript
jsonb().$type<{ foo: string }>()
```

**Prepared statements (serverless optimization):**
```typescript
const getUser = db.select().from(users)
  .where(eq(users.email, sql.placeholder('email')))
  .prepare('getUser')

await getUser.execute({ email: 'dan@x.com' })
```

**Self-referencing FK with AnyPgColumn:**
```typescript
parentId: uuid('parent_id').references((): AnyPgColumn => table.id)
```

**Custom types (pgvector example from EOS):**
```typescript
const vectorType = customType<{ data: number[]; driverData: string; config: { dimensions: number } }>({
  dataType(config) { return `vector(${config?.dimensions ?? 1536})` },
  toDriver(value) { return `[${value.join(',')}]` },
  fromDriver(value) { return value.slice(1, -1).split(',').map(Number) },
})
```

**Table third argument is an array (v0.39+):**
```typescript
pgTable('name', { ...columns }, (t) => [
  index('idx').on(t.col),
  primaryKey({ columns: [t.a, t.b] }),
])
```
Note: EOS schema uses the object syntax `(t) => ({})` which also works but the array form is the newer convention.

---

## Anti-Patterns

1. **Using `push` in production** — skips migration history, can drop+add instead of rename. Always `generate` + `migrate`.
2. **Selecting all columns when you need a few** — `db.select().from(table)` fetches everything. Use partial selects.
3. **Missing indexes on foreign keys** — PostgreSQL does NOT auto-create indexes on FK columns. Add `index()` explicitly.
4. **N+1 queries in loops** — use `db.query.*.findMany({ with: ... })` or joins instead of per-row selects.
5. **Confusing `relations()` with `.references()`** — relations are ORM metadata only. `.references()` creates actual FK constraints.
6. **Using `sql.raw()` with user input** — SQL injection risk. Use parameterized `sql` template tag.
7. **Editing applied migration files** — `__drizzle_migrations` tracks checksums. Tampering breaks deployments.
8. **Creating connections inside request handlers** — in serverless, declare pool + prepared statements outside the handler for reuse.

---

## Data Model

Drizzle schema maps directly to SQL DDL. One TypeScript file → one or more tables.

**EOS schema architecture (from `saas/db/schema.ts`):**
- 14 tables: users, portfolios, organizations, orgMembers, ventures, agents, userAgentSessions, skills, events, skillVersions, workflows, interactions, outcomes, humanProfiles, approvals, embeddings
- 7 enums: orgPlan, memberRole, ventureStage, agentDataTier, autonomyStage, approvalStatus, outcomeType
- 1 custom type: vectorType (pgvector)
- Zod validators co-located with schema (tokensJsonSchema)
- All tables use `uuid().primaryKey().defaultRandom()` for IDs
- All tables use `timestamp('created_at', { withTimezone: true }).notNull().defaultNow()`
- Most tables are org-scoped with RLS via `org_id` column

---

## Webhooks and Events

N/A — Drizzle is a client-side ORM with no webhook or event system. Database-level triggers and notifications are handled at the PostgreSQL layer, not through Drizzle.

---

## Limits

- **Max connections:** determined by PostgreSQL/Neon plan, not Drizzle. Set `max` on Pool.
- **Query size:** no Drizzle limit. PostgreSQL default `max_query_length` is effectively unlimited.
- **Batch insert:** no hard limit on `.values([])` array size, but very large batches should be chunked to avoid memory issues and statement size limits.
- **Migration files:** no limit on count. Each migration is a separate SQL file tracked in `__drizzle_migrations`.

---

## Cost Model

Drizzle ORM and Drizzle Kit are fully open source (Apache 2.0). Zero cost.

Drizzle Studio (visual browser) is free for local use. Cloud hosted version has a paid tier.

Cost is driven entirely by the underlying database (Neon billing: compute hours, storage, data transfer).

---

## Version Pinning

```json
{
  "dependencies": {
    "drizzle-orm": "0.39.3"
  },
  "devDependencies": {
    "drizzle-kit": "0.30.4"
  }
}
```

drizzle-orm and drizzle-kit versions must be compatible. Always update them together. Check the [Drizzle changelog](https://orm.drizzle.team/docs/changelog) before upgrading.

Breaking changes to watch:
- v0.29 → v0.30: table third argument changed from object to array form
- Schema push behavior changes between minor versions — always test with `strict: true`

---

## Design Intent and Tradeoffs

Drizzle's core design philosophy: **"If you know SQL, you know Drizzle."**

**Tradeoffs vs Prisma:**
- No query engine runtime (Prisma ships a Rust binary). Drizzle compiles to raw SQL.
- No schema.prisma DSL — schema is TypeScript, so you get IDE autocomplete and refactoring.
- No automatic migrations — you control when to generate and apply.
- Relations are opt-in metadata, not the primary API. SQL joins are first-class.
- Smaller bundle, faster cold starts (critical for serverless).

**Tradeoffs vs raw SQL:**
- Adds type safety at the cost of learning the query builder API.
- Schema changes are tracked via TypeScript diffs, not hand-written ALTER statements.
- Some complex queries (recursive CTEs, window functions) still need `sql` template tag.

**Why EOS chose Drizzle:**
- TypeScript-native (matches the saas stack)
- Neon driver support with WebSocket pooling
- RLS-compatible (can run `SET LOCAL` in transactions)
- No runtime overhead (important for the serverless API layer)

---

## Problem-Solution Map and Hidden Capabilities

| Problem | Solution |
|---------|----------|
| Need RLS with Neon | WebSocket driver + `set_config()` in transaction |
| Column rename in migration | Enable `strict: true` — Kit prompts instead of drop+add |
| Type-safe JSON columns | `jsonb().$type<MyInterface>()` |
| pgvector support | `customType()` with `toDriver`/`fromDriver` |
| Prepared statements for serverless | `.prepare('name')` + `.execute({ params })` |
| Self-referencing FK | `(): AnyPgColumn => table.id` return type |
| Multiple FKs to same table | `relationName` parameter in `relations()` |
| Seed data in migrations | `npx drizzle-kit generate --custom --name=seed` creates empty migration |
| Database introspection | `npx drizzle-kit pull` generates schema.ts from live DB |
| Non-public schemas | `pgSchema('name').table(...)` instead of `pgTable(...)` |
| Composite primary keys | `primaryKey({ columns: [t.a, t.b] })` in table third arg |
| Conditional updates | `sql` template in `.set()` for SQL expressions like `NOW()` |

---

## Operational Behavior and Edge Cases

- **`undefined` in `.set()` is silently ignored.** The column is excluded from the UPDATE statement. Only `null` sets a column to NULL.
- **`leftJoin` makes all right-side columns nullable** in TypeScript types. Must handle `null` even if the data logically always exists.
- **`tx.rollback()` throws `TransactionRollbackError`.** Code after it never runs. The error propagates out of the transaction callback.
- **Neon HTTP driver is single-query only.** No `SET LOCAL`, no multi-statement transactions. Use WebSocket driver for transactional RLS.
- **`generatedAlwaysAsIdentity()` columns cannot be inserted into.** PostgreSQL raises an error if you try to provide a value. Use `generatedByDefaultAsIdentity()` if you need to override.
- **Migration checksum tracking:** `__drizzle_migrations` stores hashes. If you edit a migration file after applying it, future runs may error or re-apply.
- **Empty `.values([])` array** — behavior is undefined. Always check array length before batch insert.

---

## Ecosystem Position and Composition

Drizzle sits in the TypeScript ORM space alongside:
- **Prisma** — more mature, larger community, but heavier runtime (Rust engine), slower cold starts
- **Kysely** — query builder only (no schema management), very lightweight
- **TypeORM** — decorator-based, older patterns, less type-safe
- **MikroORM** — full-featured but smaller community

Drizzle's position: **the SQL-native TypeScript ORM.** Appeals to developers who want type safety without abstracting away SQL.

Composition in EOS:
- **Drizzle ORM** — schema + queries
- **Drizzle Kit** — migrations
- **@neondatabase/serverless** — WebSocket/HTTP drivers
- **Zod** — runtime validation (co-located with schema)
- **Hono** — HTTP framework (routes call Drizzle queries)

---

## Trajectory and Evolution

- **v0.39.x (current):** Stable. Table third argument array form. Identity columns preferred over serial.
- **Drizzle Studio:** Visual database browser. Available as CLI (`npx drizzle-kit studio`) or web.
- **Drizzle Seed:** New package for deterministic test data generation (early stage).
- **Multi-dialect:** PostgreSQL, MySQL, SQLite, SingleStore, Gel. Adding more.
- **Edge-first:** Designed for serverless/edge runtimes (Cloudflare Workers, Vercel Edge, Deno).
- **Direction:** Moving toward more relational query capabilities, better error messages, and tighter Neon integration.

The team ships fast — expect minor breaking changes between 0.x versions. Pin versions and read changelogs.

---

## Conceptual Model and Solution Recipes

### Recipe: Add a new table to EOS

1. Define table in `saas/db/schema.ts` with `pgTable()`, add indexes, export types
2. If org-scoped, add `orgId` column with `.references(() => organizations.id, { onDelete: 'cascade' })`
3. Add `index()` on `orgId` (PostgreSQL does not auto-index FKs)
4. Run `npx drizzle-kit generate --name=add-table-name`
5. Review generated SQL in `drizzle/` output directory
6. Run `npx drizzle-kit migrate`
7. Add RLS policy manually in a custom migration if org-scoped

### Recipe: Add a column to existing table

1. Add column definition in schema.ts (with `.default()` for existing rows or `.notNull()` with a default)
2. Run `npx drizzle-kit generate --name=add-column-name` with `strict: true` in config
3. Verify the generated SQL is ALTER ADD, not DROP+ADD
4. Apply with `npx drizzle-kit migrate`

### Recipe: Query with RLS in EOS

```typescript
import { withOrg } from '../../db/client.js'
import { ventures } from '../../db/schema.js'
import { eq } from 'drizzle-orm'

const rows = await withOrg(orgId, (tx) =>
  tx.select().from(ventures).where(eq(ventures.orgId, orgId))
)
```

---

## Industry Expert and Cutting-Edge Usage

**Prepared statements for serverless cold starts:**
Declare `db` and prepared queries outside the handler function. In AWS Lambda / Vercel Functions, the module scope persists across warm invocations. This eliminates repeated connection and query compilation overhead.

**RLS via Drizzle transactions (EOS pattern):**
Using `set_config('app.current_org_id', orgId, true)` inside a Drizzle transaction is the cleanest way to implement row-level security with Neon. The third parameter (`true` = LOCAL) ensures the setting is transaction-scoped and never bleeds to other requests. This pattern is used by Neon's own documentation.

**Custom types for pgvector:**
EOS implements a `customType()` for pgvector that handles serialization (`[1,2,3]` format) and deserialization. This is the recommended approach until Drizzle adds native vector support. The `dimensions` config parameter maps to `vector(N)` in DDL.

**Partial selects for API responses:**
Always use partial selects in API routes. Fetching all columns wastes bandwidth and can leak sensitive fields. EOS routes use `db.select({ id: t.id, name: t.name }).from(t)` pattern.

**Upsert with `excluded` reference:**
For conflict resolution that references the incoming row's values:
```typescript
.onConflictDoUpdate({
  target: table.id,
  set: { name: sql`excluded.name`, updatedAt: sql`NOW()` },
})
```
`excluded` is PostgreSQL's keyword for the row that would have been inserted.
