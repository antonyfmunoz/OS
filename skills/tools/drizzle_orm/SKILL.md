---
name: drizzle_orm
description: "Use when defining, querying, or migrating PostgreSQL database schemas via Drizzle ORM, or when building type-safe SQL queries in the TypeScript saas layer."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://orm.drizzle.team/docs"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "drizzle-orm 0.39.3"
sdk_version: "drizzle-kit 0.30.4"
speed_category: medium
trigger: both
effort: medium
context: fork
---

# Drizzle ORM — Tool Mastery Skill

## What This Tool Does

Drizzle ORM is a TypeScript-first SQL ORM that generates zero-abstraction, type-safe queries. It maps TypeScript schema definitions directly to SQL DDL and provides both a SQL-like query builder and a relational query API. Drizzle Kit handles migrations via `generate` + `migrate` (production) or `push` (dev). Unlike Prisma, Drizzle has no query engine runtime — it compiles to raw SQL at build time, producing minimal overhead.

Key capabilities:
- Schema-as-code with full PostgreSQL type coverage (uuid, jsonb, vector, enums, identity columns)
- Type-safe select/insert/update/delete with `$inferSelect` and `$inferInsert`
- Relational query builder (`db.query.*.findMany({ with: ... })`)
- SQL-level joins (inner, left, right, full)
- Upserts via `onConflictDoUpdate` / `onConflictDoNothing`
- Prepared statements for serverless performance
- Transaction support with isolation levels and savepoints
- Custom types (e.g., pgvector via `customType`)

## EOS Integration

### Files that use Drizzle

| File | Purpose |
|------|---------|
| `saas/db/schema.ts` | All table definitions, enums, custom types (vectorType), Zod validators |
| `saas/db/client.ts` | Neon WebSocket pool connection, dual-pool (admin + app), `withOrg()` RLS wrapper |
| `saas/api/routes/*.ts` | All CRUD routes use `withOrg()` + Drizzle query builder |
| `saas/drizzle.config.ts` | Migration config pointing to schema and Neon DATABASE_URL |

### Connection architecture

EOS uses the **Neon WebSocket driver** (not HTTP) because RLS requires `SET LOCAL` inside transactions:

```typescript
import { Pool, neonConfig } from '@neondatabase/serverless'
import { drizzle } from 'drizzle-orm/neon-serverless'
import ws from 'ws'

neonConfig.webSocketConstructor = ws
const pool = new Pool({ connectionString: process.env.DATABASE_APP_URL })
export const appDb = drizzle(pool, { schema })
```

### RLS pattern — withOrg()

Every tenant-scoped query MUST use `withOrg()`. It opens a transaction, sets `app.current_org_id` via `set_config()`, then executes the callback. Queries outside `withOrg()` on `appDb` return zero rows (fail-closed).

```typescript
const rows = await withOrg(orgId, (tx) =>
  tx.select().from(ventures).where(eq(ventures.orgId, orgId))
)
```

### Dual-pool roles

- `db` (admin pool) — `neondb_owner` with BYPASSRLS. Migrations and seeds only.
- `appDb` (app pool) — `eos_app` role, no BYPASSRLS. All application queries.

## Authentication

Connection string in `.env`:

```
DATABASE_URL=postgres://neondb_owner:***@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require
DATABASE_APP_URL=postgres://eos_app:***@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require
```

Both loaded via `dotenv/config`. Never hardcode. The app pool (`DATABASE_APP_URL`) enforces RLS; the admin pool (`DATABASE_URL`) bypasses it.

## Quick Reference

### Select

```typescript
// All rows (typed)
const rows = await db.select().from(users)

// Partial select
const names = await db.select({ id: users.id, name: users.name }).from(users)

// Where with operators
import { eq, and, or, ilike, inArray, between, isNull } from 'drizzle-orm'
await db.select().from(users).where(eq(users.id, id))
await db.select().from(users).where(and(eq(users.orgId, orgId), ilike(users.name, '%dan%')))

// Order, limit, offset
import { asc, desc } from 'drizzle-orm'
await db.select().from(users).orderBy(desc(users.createdAt)).limit(10).offset(20)

// Count
const total = await db.$count(users)
const filtered = await db.$count(users, eq(users.orgId, orgId))
```

### Insert

```typescript
// Single
await db.insert(users).values({ name: 'Dan', email: 'dan@example.com' })

// Multiple
await db.insert(users).values([{ name: 'A' }, { name: 'B' }])

// With returning
const [inserted] = await db.insert(users).values({ name: 'Dan' }).returning()

// Upsert
await db.insert(users).values({ id, name: 'Dan' })
  .onConflictDoUpdate({ target: users.id, set: { name: 'Dan' } })
```

### Update

```typescript
const [updated] = await db.update(users)
  .set({ name: 'Mr. Dan' })
  .where(eq(users.id, id))
  .returning()

// undefined in .set() is IGNORED — use null to set NULL
await db.update(users).set({ deletedAt: null }).where(eq(users.id, id))
```

### Delete

```typescript
const deleted = await db.delete(users).where(eq(users.id, id)).returning()
```

### Relations

```typescript
// Define (application-level, not DB constraints)
export const usersRelations = relations(users, ({ many }) => ({
  posts: many(posts),
}))

// Query (requires schema passed to drizzle())
const result = await db.query.users.findMany({ with: { posts: true } })
```

### Migrations

```bash
npx drizzle-kit generate              # create SQL migration files
npx drizzle-kit generate --name=init  # with custom name
npx drizzle-kit migrate               # apply pending migrations
npx drizzle-kit push                  # dev only — direct apply, no files
npx drizzle-kit pull                  # introspect existing DB → schema.ts
```

## Conceptual Model

```
┌──────────────────────────────────────────────────┐
│  saas/db/schema.ts                               │
│  pgTable() + pgEnum() + customType()             │
│  ── defines tables, columns, constraints ──      │
└──────────────────┬───────────────────────────────┘
                   │ imported by
                   ▼
┌──────────────────────────────────────────────────┐
│  saas/db/client.ts                               │
│  Neon WebSocket Pool → drizzle(pool, { schema }) │
│  adminPool (BYPASSRLS) │ appPool (RLS enforced)  │
│  withOrg(orgId, fn) — SET LOCAL + transaction    │
└──────────────────┬───────────────────────────────┘
                   │ used by
                   ▼
┌──────────────────────────────────────────────────┐
│  saas/api/routes/*.ts                            │
│  Hono handlers → withOrg(orgId, tx => ...)       │
│  tx.select / tx.insert / tx.update / tx.delete   │
└──────────────────┬───────────────────────────────┘
                   │ connects to
                   ▼
┌──────────────────────────────────────────────────┐
│  Neon PostgreSQL                                 │
│  RLS policies: org_id = app.current_org_id       │
│  __drizzle_migrations tracks applied migrations  │
└──────────────────────────────────────────────────┘
```

## Gotchas

### 1. `strict: true` in drizzle.config.ts is critical
Without it, Drizzle Kit may interpret a column rename as "drop column + add column," destroying data. Always enable `strict: true` so it prompts on ambiguous changes.

### 2. `push` is dev-only — never production
`push` skips migration files entirely. It diffs schema vs live DB and applies directly. Column renames can be misinterpreted as drop+add, causing data loss. Production must use `generate` + `migrate`.

### 3. `relations()` are NOT database constraints
`relations()` definitions are purely application-level metadata for `db.query.*` relational queries. They do NOT create foreign keys or indexes. You must add `.references()` on the column definition for actual FK constraints and `index()` separately.

### 4. Neon HTTP driver cannot do interactive transactions
The HTTP driver (`drizzle-orm/neon-http`) is stateless single-query only. EOS uses the WebSocket driver (`drizzle-orm/neon-serverless`) specifically because `withOrg()` requires `SET LOCAL` inside a transaction. If you see `neon-http` in EOS code, it is wrong.

### 5. `leftJoin` makes all joined columns nullable
When using `.leftJoin()`, TypeScript marks every column from the joined table as `T | null`. Forgetting to handle the null case causes runtime crashes.

### 6. `undefined` vs `null` in `.set()` — different behavior
Passing `undefined` for a column in `.set()` silently ignores that column (no SQL generated). To set a column to NULL, you must pass `null` explicitly.

### 7. Schema must be passed to `drizzle()` for relational queries
`db.query.*` only works if `{ schema }` was passed when creating the drizzle instance. Without it, `db.query` is undefined. EOS already does this in `client.ts`.

### 8. Self-referencing columns need `AnyPgColumn`
Self-referential foreign keys (like `agents.parentAgentId → agents.id`) require `(): AnyPgColumn => agents.id` return type annotation to avoid TypeScript circular reference errors. EOS already uses this pattern.

### 9. Migration snapshots are git-tracked artifacts
The `snapshot.json` files inside migration folders must be committed. Drizzle Kit uses them to compute diffs for the next `generate`. Deleting them breaks future migrations.

### 10. `tx.rollback()` throws — does not return
`tx.rollback()` throws `TransactionRollbackError`. Code after it never executes. Catch it with `instanceof TransactionRollbackError` if you need to distinguish intentional rollbacks from errors.
