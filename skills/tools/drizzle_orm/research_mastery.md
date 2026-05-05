# Drizzle ORM Research -- Tool Mastery Engine Method

Research conducted 2026-04-04 via WebSearch + WebFetch against official docs and community sources.

---

## Setup & Connection

### Installation

```bash
# PostgreSQL with node-postgres driver
npm i drizzle-orm pg dotenv
npm i -D drizzle-kit tsx @types/pg

# Neon serverless (HTTP driver)
npm i drizzle-orm @neondatabase/serverless dotenv
npm i -D drizzle-kit
```

Source: [Get Started with Drizzle and PostgreSQL](https://orm.drizzle.team/docs/get-started/postgresql-new)

### Database Connection -- Standard PostgreSQL

```typescript
import 'dotenv/config';
import { drizzle } from 'drizzle-orm/node-postgres';

// Simplest form -- pass connection string directly
const db = drizzle(process.env.DATABASE_URL!);
```

You can also pass a `Pool` instance for connection pooling:

```typescript
import { Pool } from 'pg';
import { drizzle } from 'drizzle-orm/node-postgres';

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  max: 20,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
});
const db = drizzle({ client: pool });
```

Source: [Drizzle ORM PostgreSQL Best Practices Guide](https://gist.github.com/productdevbook/7c9ce3bbeb96b3fabc3c7c2aa2abc717)

### Database Connection -- Neon Serverless

**HTTP driver** (recommended for serverless -- Vercel, Netlify, Cloudflare Workers):

```typescript
import { drizzle } from 'drizzle-orm/neon-http';

const db = drizzle(process.env.DATABASE_URL!);
```

Or with explicit client:

```typescript
import { neon } from '@neondatabase/serverless';
import { drizzle } from 'drizzle-orm/neon-http';

const sql = neon(process.env.DATABASE_URL!);
const db = drizzle({ client: sql });
```

**WebSocket driver** (for sessions/interactive transactions):

```typescript
import { drizzle } from 'drizzle-orm/neon-serverless';

const db = drizzle(process.env.DATABASE_URL!);
```

For Node.js environments, WebSocket driver needs additional packages:

```typescript
import { Pool, neonConfig } from '@neondatabase/serverless';
import { drizzle } from 'drizzle-orm/neon-serverless';
import ws from 'ws';

neonConfig.webSocketConstructor = ws;

const pool = new Pool({ connectionString: process.env.DATABASE_URL });
const db = drizzle({ client: pool });
```

Source: [Drizzle ORM - Neon](https://orm.drizzle.team/docs/connect-neon), [Neon Docs - Drizzle](https://neon.com/docs/guides/drizzle)

### Drizzle Config File

```typescript
// drizzle.config.ts
import 'dotenv/config';
import { defineConfig } from 'drizzle-kit';

export default defineConfig({
  out: './drizzle',
  schema: './src/db/schema.ts',
  dialect: 'postgresql',
  dbCredentials: {
    url: process.env.DATABASE_URL!,
  },
});
```

Source: [Get Started with Drizzle and PostgreSQL](https://orm.drizzle.team/docs/get-started/postgresql-new)

---

## Schema Definition

### Basic Table Definition

```typescript
import { integer, pgTable, varchar, text, boolean, timestamp, uuid, serial, jsonb } from 'drizzle-orm/pg-core';

export const usersTable = pgTable('users', {
  id: integer().primaryKey().generatedAlwaysAsIdentity(),
  name: varchar({ length: 255 }).notNull(),
  age: integer().notNull(),
  email: varchar({ length: 255 }).notNull().unique(),
});
```

Source: [Drizzle ORM - Schema](https://orm.drizzle.team/docs/sql-schema-declaration)

### PostgreSQL Column Types -- Complete Reference

**Numeric types:**

| Function | SQL Type | Notes |
|----------|----------|-------|
| `integer()` | INTEGER | Signed 4-byte |
| `smallint()` | SMALLINT | Signed 2-byte |
| `bigint({ mode: 'number' })` | BIGINT | Returns JS number |
| `bigint({ mode: 'bigint' })` | BIGINT | Returns BigInt |
| `serial()` | SERIAL | Auto-incrementing 4-byte |
| `smallserial()` | SMALLSERIAL | Auto-incrementing 2-byte |
| `bigserial({ mode: 'number' })` | BIGSERIAL | Auto-incrementing 8-byte |
| `numeric()` | NUMERIC | Arbitrary precision |
| `numeric({ precision: 100, scale: 20 })` | NUMERIC(100,20) | With precision/scale |
| `real()` | REAL | Single precision float |
| `doublePrecision()` | DOUBLE PRECISION | Double precision float |

**String types:**

| Function | SQL Type | Notes |
|----------|----------|-------|
| `text()` | TEXT | Unlimited length |
| `text({ enum: ['a', 'b'] })` | TEXT | With enum constraint |
| `varchar()` | VARCHAR | Variable length |
| `varchar({ length: 256 })` | VARCHAR(256) | With max length |
| `char({ length: 10 })` | CHAR(10) | Fixed length, padded |

**Date/time types:**

| Function | SQL Type | Notes |
|----------|----------|-------|
| `timestamp()` | TIMESTAMP | Default mode: 'date' (JS Date) |
| `timestamp({ mode: 'string' })` | TIMESTAMP | Returns string |
| `timestamp({ precision: 6, withTimezone: true })` | TIMESTAMPTZ(6) | With timezone |
| `date()` | DATE | Calendar date |
| `date({ mode: 'date' })` | DATE | Returns JS Date |
| `time()` | TIME | Time of day |
| `time({ withTimezone: true, precision: 6 })` | TIMETZ(6) | With timezone |
| `interval({ fields: 'day' })` | INTERVAL DAY | Time span |

**Other types:**

| Function | SQL Type | Notes |
|----------|----------|-------|
| `boolean()` | BOOLEAN | true/false |
| `json()` | JSON | Text-based JSON |
| `jsonb()` | JSONB | Binary JSON (decomposed, indexable) |
| `uuid()` | UUID | Use `.defaultRandom()` for auto-gen |
| `bytea()` | BYTEA | Binary data |
| `point({ mode: 'xy' })` | POINT | Returns { x, y } |
| `line({ mode: 'abc' })` | LINE | Returns { a, b, c } |

Source: [Drizzle ORM - PostgreSQL column types](https://orm.drizzle.team/docs/column-types/pg)

### Enum Type

```typescript
import { pgEnum } from 'drizzle-orm/pg-core';

export const moodEnum = pgEnum('mood', ['sad', 'ok', 'happy']);

export const entries = pgTable('entries', {
  id: integer().primaryKey().generatedAlwaysAsIdentity(),
  mood: moodEnum().notNull(),
});
```

### Column Modifiers (chaining methods)

All column types support these chainable methods:

- `.notNull()` -- NOT NULL constraint
- `.primaryKey()` -- PRIMARY KEY constraint
- `.unique()` -- UNIQUE constraint
- `.default(value)` -- static default value
- `.defaultRandom()` -- UUID random default (uuid columns)
- `.defaultNow()` -- CURRENT_TIMESTAMP default (timestamp columns)
- `.$type<T>()` -- override TypeScript type inference
- `.$defaultFn(() => value)` -- runtime default function (runs in JS, not SQL)
- `.$onUpdate(() => value)` -- runtime value on update
- `.generatedAlwaysAsIdentity()` -- PostgreSQL identity column (preferred over serial)
- `.references(() => otherTable.column)` -- foreign key reference

### Type-safe JSON columns

```typescript
jsonb().$type<{ foo: string }>()
json().$type<string[]>()
```

### Type Inference Helpers

```typescript
type User = typeof usersTable.$inferSelect;    // SELECT result type
type NewUser = typeof usersTable.$inferInsert;  // INSERT input type
```

Source: [Drizzle ORM - PostgreSQL column types](https://orm.drizzle.team/docs/column-types/pg)

---

## Core Operations (Select, Insert, Update, Delete)

### SELECT

**Basic select -- all columns:**
```typescript
const result = await db.select().from(users);
// Returns: User[] (typed based on schema)
```

**Partial select -- specific columns:**
```typescript
const result = await db.select({
  id: users.id,
  name: users.name,
}).from(users);
// Returns: { id: number; name: string }[]
```

**Distinct:**
```typescript
await db.selectDistinct().from(users);
// PostgreSQL-specific: distinct on specific columns
await db.selectDistinctOn([users.id]).from(users);
```

**Where clause with operators:**
```typescript
import { eq, ne, gt, lt, gte, lte, like, ilike, inArray, notInArray,
         isNull, isNotNull, between, and, or, not, exists, sql } from 'drizzle-orm';

await db.select().from(users).where(eq(users.id, 42));
await db.select().from(users).where(and(eq(users.id, 42), eq(users.name, 'Dan')));
await db.select().from(users).where(or(eq(users.id, 42), eq(users.name, 'Dan')));
await db.select().from(users).where(like(users.name, '%Dan%'));
await db.select().from(users).where(ilike(users.name, '%dan%'));
await db.select().from(users).where(inArray(users.id, [1, 2, 3]));
await db.select().from(users).where(between(users.age, 18, 65));
await db.select().from(users).where(isNull(users.deletedAt));
```

**Order, limit, offset:**
```typescript
import { asc, desc } from 'drizzle-orm';

await db.select().from(users).orderBy(asc(users.name), desc(users.age));
await db.select().from(users).limit(10).offset(20);
```

**Group by, having, aggregates:**
```typescript
import { count, sum, avg, min, max, countDistinct, sumDistinct, avgDistinct } from 'drizzle-orm';

await db.select({
  age: users.age,
  count: count(),
}).from(users).groupBy(users.age).having(({ count }) => gt(count, 1));
```

**Count utility:**
```typescript
const total = await db.$count(users);
const filtered = await db.$count(users, eq(users.name, 'Dan'));
```

**Subqueries:**
```typescript
const sq = db.select().from(users).where(eq(users.id, 42)).as('sq');
const result = await db.select().from(sq);
```

**WITH clause (CTEs):**
```typescript
const sq = db.$with('sq').as(db.select().from(users).where(eq(users.id, 42)));
const result = await db.with(sq).select().from(sq);
```

**Prepared statements:**
```typescript
const getUserByEmail = db.select().from(users)
  .where(eq(users.email, sql.placeholder('email')))
  .prepare('getUserByEmail');

const result = await getUserByEmail.execute({ email: 'dan@example.com' });
```

Source: [Drizzle ORM - Select](https://orm.drizzle.team/docs/select)

### INSERT

**Single row:**
```typescript
await db.insert(users).values({ name: 'Andrew' });
```

**Multiple rows:**
```typescript
await db.insert(users).values([
  { name: 'Andrew' },
  { name: 'Dan' },
]);
```

**Insert with returning (PostgreSQL/SQLite):**
```typescript
const inserted = await db.insert(users).values({ name: 'Dan' }).returning();
// Returns: User[]

// Partial return
const ids = await db.insert(users).values({ name: 'Dan' })
  .returning({ insertedId: users.id });
// Returns: { insertedId: number }[]
```

**Upsert -- onConflictDoNothing:**
```typescript
await db.insert(users)
  .values({ id: 1, name: 'John' })
  .onConflictDoNothing();

// With specific conflict target
await db.insert(users)
  .values({ id: 1, name: 'John' })
  .onConflictDoNothing({ target: users.id });
```

**Upsert -- onConflictDoUpdate:**
```typescript
await db.insert(users)
  .values({ id: 1, name: 'Dan' })
  .onConflictDoUpdate({
    target: users.id,
    set: { name: 'John' },
  });

// Composite key target
await db.insert(users)
  .values({ firstName: 'John', lastName: 'Doe' })
  .onConflictDoUpdate({
    target: [users.firstName, users.lastName],
    set: { firstName: 'John1' },
  });

// With where clause on conflict
await db.insert(employees)
  .values({ employeeId: 123, name: 'John Doe' })
  .onConflictDoUpdate({
    target: employees.employeeId,
    targetWhere: sql`name <> 'John Doe'`,
    set: { name: sql`excluded.name` },
  });
```

**Insert from select:**
```typescript
const inserted = await db
  .insert(employees)
  .select(
    db.select({ name: users.name })
      .from(users)
      .where(eq(users.role, 'employee'))
  )
  .returning({ id: employees.id, name: employees.name });
```

Source: [Drizzle ORM - Insert](https://orm.drizzle.team/docs/insert)

### UPDATE

**Basic update:**
```typescript
await db.update(users)
  .set({ name: 'Mr. Dan' })
  .where(eq(users.name, 'Dan'));
```

**With SQL expressions:**
```typescript
await db.update(users)
  .set({ updatedAt: sql`NOW()` })
  .where(eq(users.name, 'Dan'));
```

**With returning (PostgreSQL/SQLite):**
```typescript
const updated = await db.update(users)
  .set({ name: 'Mr. Dan' })
  .where(eq(users.name, 'Dan'))
  .returning({ updatedId: users.id });
// Returns: { updatedId: number }[]
```

**Update with FROM (join-based update):**
```typescript
await db.update(users)
  .set({ cityId: cities.id })
  .from(cities)
  .where(and(eq(cities.name, 'Seattle'), eq(users.name, 'John')));
```

**Limit:**
```typescript
await db.update(users).set({ verified: true }).limit(2);
```

**Note:** `undefined` values in `.set()` are ignored. Pass `null` explicitly to set a column to NULL.

Source: [Drizzle ORM - Update](https://orm.drizzle.team/docs/update)

### DELETE

**Delete with where:**
```typescript
await db.delete(users).where(eq(users.name, 'Dan'));
```

**Delete all rows:**
```typescript
await db.delete(users);
```

**Delete with returning (PostgreSQL/SQLite):**
```typescript
const deleted = await db.delete(users)
  .where(eq(users.name, 'Dan'))
  .returning();
// Returns: User[]

const deletedIds = await db.delete(users)
  .where(eq(users.name, 'Dan'))
  .returning({ deletedId: users.id });
```

**Delete with limit and order:**
```typescript
await db.delete(users).where(eq(users.name, 'Dan')).limit(2);
await db.delete(users).where(eq(users.name, 'Dan')).orderBy(desc(users.createdAt));
```

**Delete with CTE:**
```typescript
const averageAmount = db.$with('average_amount').as(
  db.select({ value: sql`avg(${orders.amount})`.as('value') }).from(orders)
);

const result = await db
  .with(averageAmount)
  .delete(orders)
  .where(gt(orders.amount, sql`(select * from ${averageAmount})`))
  .returning({ id: orders.id });
```

Source: [Drizzle ORM - Delete](https://orm.drizzle.team/docs/delete)

---

## Migrations (drizzle-kit)

### Overview

Drizzle Kit provides 4 core commands for schema management:

| Command | Purpose | When to use |
|---------|---------|-------------|
| `generate` | Create SQL migration files from schema diff | Production deployments |
| `migrate` | Apply generated migrations to database | Production deployments |
| `push` | Apply schema directly (no SQL files) | Development/prototyping |
| `pull` | Introspect DB and generate schema.ts | Database-first workflow |

### generate

Reads schema files, compares against previous snapshots, produces SQL migration files:

```bash
npx drizzle-kit generate
npx drizzle-kit generate --name=add-users-table
npx drizzle-kit generate --custom --name=seed-data  # empty migration for custom SQL
npx drizzle-kit generate --config=drizzle-prod.config.ts
```

Output structure:
```
drizzle/
  20242409125510_init/
    migration.sql
    snapshot.json
  20242409125511_add_users/
    migration.sql
    snapshot.json
```

### migrate

Applies pending migrations. Tracks applied migrations in `__drizzle_migrations` table:

```bash
npx drizzle-kit migrate
```

### push

Applies schema changes directly to the database without generating SQL files. Reads schema, introspects DB, diffs, and applies:

```bash
npx drizzle-kit push
```

**WARNING:** `push` is for development only. Never use in production -- it skips migration files and can cause data loss on ambiguous changes (e.g., column renames interpreted as drop+add).

### pull

Introspects an existing database and generates a Drizzle schema file:

```bash
npx drizzle-kit pull
```

### Config Options

```typescript
export default defineConfig({
  dialect: 'postgresql',                    // required
  schema: './src/db/schema.ts',             // required -- supports globs
  out: './drizzle',                         // migration output dir (default: ./drizzle)
  dbCredentials: {
    url: process.env.DATABASE_URL!,
  },
  strict: true,                             // prompts on ambiguous changes (ALWAYS USE)
});
```

Schema path supports globs: `'./src/**/schema.ts'` or arrays: `['./src/user/schema.ts', './src/posts/schema.ts']`.

Source: [Drizzle Kit Overview](https://orm.drizzle.team/docs/kit-overview), [drizzle-kit generate](https://orm.drizzle.team/docs/drizzle-kit-generate), [drizzle-kit push](https://orm.drizzle.team/docs/drizzle-kit-push), [drizzle-kit pull](https://orm.drizzle.team/docs/drizzle-kit-pull)

---

## Relations & Joins

### Defining Relations

Relations are application-level abstractions (they do NOT create database constraints). They enable the relational query API (`db.query.*`).

```typescript
import { relations } from 'drizzle-orm';
```

**One-to-one:**
```typescript
export const users = pgTable('users', {
  id: serial('id').primaryKey(),
  name: text('name'),
});

export const profileInfo = pgTable('profile_info', {
  id: serial('id').primaryKey(),
  userId: integer('user_id').references(() => users.id),
  metadata: jsonb('metadata'),
});

export const usersRelations = relations(users, ({ one }) => ({
  profileInfo: one(profileInfo),
}));

export const profileInfoRelations = relations(profileInfo, ({ one }) => ({
  user: one(users, {
    fields: [profileInfo.userId],
    references: [users.id],
  }),
}));
```

**One-to-many:**
```typescript
export const usersRelations = relations(users, ({ many }) => ({
  posts: many(posts),
}));

export const postsRelations = relations(posts, ({ one }) => ({
  author: one(users, {
    fields: [posts.authorId],
    references: [users.id],
  }),
}));
```

**Many-to-many (via junction table):**
```typescript
export const usersToGroups = pgTable('users_to_groups', {
  userId: integer('user_id').references(() => users.id),
  groupId: integer('group_id').references(() => groups.id),
});

export const usersRelations = relations(users, ({ many }) => ({
  usersToGroups: many(usersToGroups),
}));

export const groupsRelations = relations(groups, ({ many }) => ({
  usersToGroups: many(usersToGroups),
}));

export const usersToGroupsRelations = relations(usersToGroups, ({ one }) => ({
  user: one(users, { fields: [usersToGroups.userId], references: [users.id] }),
  group: one(groups, { fields: [usersToGroups.groupId], references: [groups.id] }),
}));
```

**Disambiguating multiple relations between same tables:**
```typescript
export const usersRelations = relations(users, ({ many }) => ({
  authoredPosts: many(posts, { relationName: 'author' }),
  reviewedPosts: many(posts, { relationName: 'reviewer' }),
}));
```

Source: [Drizzle ORM - Relations](https://orm.drizzle.team/docs/relations)

### Querying with Relations (relational query API)

Requires passing `schema` to drizzle():

```typescript
import * as schema from './db/schema';
const db = drizzle(process.env.DATABASE_URL!, { schema });

const result = await db.query.users.findMany({
  with: {
    posts: true,
  },
});
// Returns: { id, name, posts: [...] }[]
```

### SQL-Level Joins

Available join types:

```typescript
// LEFT JOIN
await db.select().from(users)
  .leftJoin(posts, eq(users.id, posts.authorId));

// RIGHT JOIN
await db.select().from(users)
  .rightJoin(posts, eq(users.id, posts.authorId));

// INNER JOIN
await db.select().from(users)
  .innerJoin(posts, eq(users.id, posts.authorId));

// FULL JOIN
await db.select().from(users)
  .fullJoin(posts, eq(users.id, posts.authorId));
```

**Partial select with joins:**
```typescript
const result = await db.select({
  userId: users.id,
  postTitle: posts.title,
}).from(users)
  .leftJoin(posts, eq(users.id, posts.authorId));
```

Source: [Drizzle ORM - Joins](https://orm.drizzle.team/docs/joins), [Drizzle ORM - Relations](https://orm.drizzle.team/docs/relations)

---

## Transactions

### Basic Transaction

```typescript
await db.transaction(async (tx) => {
  await tx.insert(users).values({ name: 'Dan' });
  await tx.update(accounts).set({ balance: sql`balance - 100` }).where(eq(accounts.userId, 1));
});
```

The `tx` object has the same query interface as `db`.

### Return Values from Transactions

```typescript
const newBalance: number = await db.transaction(async (tx) => {
  await tx.update(accounts).set({ balance: sql`balance - 100` }).where(eq(accounts.id, 1));
  const [account] = await tx.select({ balance: accounts.balance }).from(accounts).where(eq(accounts.id, 1));
  return account.balance;
});
```

### Manual Rollback

```typescript
await db.transaction(async (tx) => {
  const [account] = await tx.select().from(accounts).where(eq(accounts.id, 1));

  if (account.balance < 100) {
    tx.rollback();  // throws TransactionRollbackError, rolls back everything
  }

  await tx.update(accounts).set({ balance: sql`balance - 100` }).where(eq(accounts.id, 1));
});
```

### Nested Transactions (Savepoints)

```typescript
await db.transaction(async (tx) => {
  await tx.update(accounts).set({ balance: sql`balance - 100` }).where(eq(accounts.id, 1));

  await tx.transaction(async (tx2) => {
    // This creates a SAVEPOINT. If tx2 fails, only this nested block rolls back.
    await tx2.update(users).set({ name: 'Mr. Dan' }).where(eq(users.id, 1));
  });
});
```

### PostgreSQL Transaction Configuration

```typescript
await db.transaction(async (tx) => {
  // transaction body
}, {
  isolationLevel: 'serializable',      // 'read uncommitted' | 'read committed' | 'repeatable read' | 'serializable'
  accessMode: 'read write',            // 'read only' | 'read write'
  deferrable: true,                    // boolean
});
```

### Relational Queries in Transactions

```typescript
const db = drizzle(process.env.DATABASE_URL!, { schema });

await db.transaction(async (tx) => {
  await tx.query.users.findMany({
    with: { accounts: true },
  });
});
```

Source: [Drizzle ORM - Transactions](https://orm.drizzle.team/docs/transactions)

---

## Error Handling

### Automatic Rollback on Thrown Errors

If any statement inside a transaction callback throws, the entire transaction is rolled back automatically. No explicit catch needed inside the callback:

```typescript
try {
  await db.transaction(async (tx) => {
    await tx.insert(users).values({ name: 'Dan' });
    throw new Error('something went wrong');  // entire transaction rolls back
  });
} catch (e) {
  // handle the error
}
```

### TransactionRollbackError

When using `tx.rollback()`, Drizzle throws `TransactionRollbackError`. You can catch it specifically:

```typescript
import { TransactionRollbackError } from 'drizzle-orm';

try {
  await db.transaction(async (tx) => {
    tx.rollback();
  });
} catch (e) {
  if (e instanceof TransactionRollbackError) {
    // intentional rollback
  } else {
    // unexpected error
  }
}
```

### Database Constraint Errors

Drizzle does not wrap database errors in custom error types. Constraint violations (unique, foreign key, check) throw the underlying driver's error. For node-postgres, these are `DatabaseError` objects with a `code` property:

- `23505` -- unique_violation
- `23503` -- foreign_key_violation
- `23502` -- not_null_violation
- `23514` -- check_violation

```typescript
try {
  await db.insert(users).values({ email: 'duplicate@example.com' });
} catch (e: any) {
  if (e.code === '23505') {
    // handle unique violation
  }
}
```

### Query-Level Error Handling

Non-transaction queries that fail throw the driver's native error. Always wrap in try/catch:

```typescript
try {
  const result = await db.select().from(users).where(eq(users.id, 1));
} catch (e) {
  console.error('Query failed:', e);
}
```

Source: [Drizzle ORM - Transactions](https://orm.drizzle.team/docs/transactions), [GitHub Discussion #916](https://github.com/drizzle-team/drizzle-orm/discussions/916)

---

## Anti-Patterns

### 1. Using `db push` in production
`push` skips migration files and can interpret column renames as drop+add, causing **data loss**. Always use `generate` + `migrate` in production.

### 2. Selecting all columns when you only need a few
```typescript
// BAD -- fetches all columns including large blobs
const users = await db.select().from(usersTable);

// GOOD -- fetch only what you need
const users = await db.select({ id: usersTable.id, name: usersTable.name }).from(usersTable);
```

### 3. Missing indexes on foreign keys
Neither Drizzle nor PostgreSQL auto-create indexes on FK columns. Add them explicitly for any column used in JOINs or WHERE:

```typescript
import { index } from 'drizzle-orm/pg-core';

export const posts = pgTable('posts', {
  id: integer().primaryKey().generatedAlwaysAsIdentity(),
  authorId: integer('author_id').references(() => users.id),
}, (table) => [
  index('posts_author_id_idx').on(table.authorId),
]);
```

### 4. Forgetting to define `relations()` when using relational queries
The `db.query.*` API with `with:` clauses will fail silently or error if you haven't defined corresponding `relations()` for your tables.

### 5. N+1 queries in loops
```typescript
// BAD -- N+1: one query per user
for (const user of users) {
  const posts = await db.select().from(postsTable).where(eq(postsTable.authorId, user.id));
}

// GOOD -- single query with join or relational API
const result = await db.query.users.findMany({ with: { posts: true } });
```

### 6. Manually editing migration files or history
Never delete, reorder, or modify applied migration files. The `__drizzle_migrations` table tracks checksums. Tampering causes schema drift and deployment failures.

### 7. Using raw strings instead of filter operators
```typescript
// BAD -- bypasses type safety and SQL injection protection
.where(sql`name = 'Dan'`)

// GOOD -- type-safe and parameterized
.where(eq(users.name, 'Dan'))
```

### 8. Not skipping prepared statements for repeated queries
```typescript
// BAD -- recompiles on every call
async function getUser(email: string) {
  return db.select().from(users).where(eq(users.email, email));
}

// GOOD -- compiled once, reused
const getUser = db.select().from(users)
  .where(eq(users.email, sql.placeholder('email')))
  .prepare('getUser');
// Then: getUser.execute({ email })
```

Source: [3 Biggest Mistakes with Drizzle ORM](https://medium.com/@lior_amsalem/3-biggest-mistakes-with-drizzle-orm-1327e2531aff), [Drizzle ORM PostgreSQL Best Practices Guide](https://gist.github.com/productdevbook/7c9ce3bbeb96b3fabc3c7c2aa2abc717)

---

## Key Gotchas

### 1. `generatedAlwaysAsIdentity()` vs `serial()`
`serial()` is the old PostgreSQL way. Modern PostgreSQL (10+) recommends identity columns. Drizzle supports both, but prefer `generatedAlwaysAsIdentity()` for new tables.

### 2. Timestamp `mode` matters for performance
`timestamp({ mode: 'date' })` returns JS Date objects (10-15% faster). `timestamp({ mode: 'string' })` returns strings. Default is `'date'`. Always set `withTimezone: true` for cross-region consistency.

### 3. `undefined` vs `null` in `.set()`
Passing `undefined` for a column in `.set()` **ignores** that column (no SQL generated). Pass `null` explicitly to set a column to NULL.

### 4. `strict: true` in drizzle.config.ts is critical
Without it, Drizzle Kit may interpret a column rename as "drop column + add column," destroying data. Always enable `strict: true` so it prompts you on ambiguous changes.

### 5. Relations are NOT database constraints
`relations()` definitions are purely application-level for the relational query API. They do NOT create foreign keys, indexes, or constraints. You must add `.references()` on the column and create indexes separately.

### 6. Neon HTTP driver cannot do interactive transactions
The HTTP driver (`drizzle-orm/neon-http`) is for single, non-interactive queries. If you need transactions, use the WebSocket driver (`drizzle-orm/neon-serverless`) or `node-postgres`.

### 7. leftJoin returns nullable columns
When using `.leftJoin()`, all columns from the joined table become nullable in the TypeScript type. If you don't handle this, you'll get runtime null reference errors.

### 8. `tx.rollback()` throws -- it doesn't return
Calling `tx.rollback()` throws a `TransactionRollbackError`. Code after `tx.rollback()` will never execute. The error propagates out of the transaction callback.

### 9. Schema must be passed to drizzle() for relational queries
`db.query.*` only works if you pass `{ schema }` when creating the drizzle instance:
```typescript
import * as schema from './schema';
const db = drizzle(url, { schema });  // required for db.query.*
```

### 10. Migration snapshots are git-tracked artifacts
The `snapshot.json` files in your migration folders must be committed to git. Drizzle Kit uses them to compute diffs for the next migration. Deleting them breaks future `generate` calls.

Source: [Drizzle ORM PostgreSQL Best Practices Guide](https://gist.github.com/productdevbook/7c9ce3bbeb96b3fabc3c7c2aa2abc717), [Drizzle ORM Docs](https://orm.drizzle.team/docs), [3 Biggest Mistakes with Drizzle ORM](https://medium.com/@lior_amsalem/3-biggest-mistakes-with-drizzle-orm-1327e2531aff)
