# Drizzle ORM Research — Context7 Method

Research source: Context7 MCP (`/drizzle-team/drizzle-orm-docs`)
Library: Drizzle ORM — TypeScript ORM for SQL databases
Snippets available: 1966 | Source reputation: High | Benchmark: 88.08

---

## Setup & Connection

### Install

```bash
npm i drizzle-orm @neondatabase/serverless
npm i -D drizzle-kit
```

### Connect to Neon (HTTP driver — serverless)

```typescript
// db.ts
import { drizzle } from "drizzle-orm/neon-http";
import { neon } from "@neondatabase/serverless";
import { config } from "dotenv";

config({ path: ".env" });

const sql = neon(process.env.DATABASE_URL!);
export const db = drizzle({ client: sql });
```

### Connect to PostgreSQL (node-postgres — traditional)

```typescript
import { drizzle } from "drizzle-orm/node-postgres";

const db = drizzle(process.env.DATABASE_URL!);
```

### Environment variable

```text
DATABASE_URL=postgres://username:password@ep-cool-darkness-123456.us-east-2.aws.neon.tech/neondb
```

---

## Schema Definition

### Basic table with constraints

```typescript
import { integer, pgTable, varchar } from "drizzle-orm/pg-core";

export const usersTable = pgTable("users", {
  id: integer().primaryKey().generatedAlwaysAsIdentity(),
  name: varchar({ length: 255 }).notNull(),
  age: integer().notNull(),
  email: varchar({ length: 255 }).notNull().unique(),
});
```

### Column types available (pg-core)

From the docs, the following were demonstrated:
- `integer()` — integer column
- `serial('name')` — auto-incrementing integer (legacy, prefer `generatedAlwaysAsIdentity()`)
- `varchar({ length: N })` — variable character with max length
- `text('name')` — unbounded text
- `boolean('name')` — boolean
- `timestamp('name', { withTimezone: true })` — timestamp with timezone support

### Column modifiers

- `.primaryKey()` — marks as PK
- `.notNull()` — NOT NULL constraint
- `.unique()` — UNIQUE constraint
- `.default(value)` — default value
- `.defaultNow()` — default to current timestamp
- `.generatedAlwaysAsIdentity()` — PostgreSQL identity column (replaces serial)
- `.references(() => otherTable.column)` — foreign key reference

### Custom schemas (non-public)

```typescript
import { integer, pgSchema } from "drizzle-orm/pg-core";

export const customSchema = pgSchema('custom');

export const users = customSchema.table('users', {
  id: integer()
});
```

This generates: `CREATE SCHEMA "custom"; CREATE TABLE "custom"."users" (...)`

### Composite primary keys and unique constraints

```typescript
import { pgTable, integer, serial, primaryKey, unique } from "drizzle-orm/pg-core";

export const usersToGroups = pgTable('users_to_groups', {
  id: serial('id').primaryKey(),
  userId: integer('user_id').notNull().references(() => users.id),
  groupId: integer('group_id').notNull().references(() => groups.id),
}, (t) => [
  primaryKey({ columns: [t.userId, t.groupId] })
]);

// Named unique constraint
export const users = pgTable("users", {
  id: integer().primaryKey().generatedAlwaysAsIdentity(),
  email: varchar({ length: 255 }).notNull(),
}, (table) => [
  unique("users_email_unique").on(table.email)
]);
```

### Self-referencing foreign keys

```typescript
import { type AnyPgColumn, integer, pgTable, serial, text } from 'drizzle-orm/pg-core';

export const users = pgTable('users', {
  id: serial('id').primaryKey(),
  name: text('name').notNull(),
  invitedBy: integer('invited_by').references((): AnyPgColumn => users.id),
});
```

Note: Self-references require typing the callback return as `AnyPgColumn` to avoid circular type issues.

---

## Core Operations (Select, Insert, Update, Delete)

### Type inference for inserts

```typescript
// Infer the insert type from the schema
const user: typeof usersTable.$inferInsert = {
  name: 'John',
  age: 30,
  email: 'john@example.com',
};
```

### Insert

```typescript
await db.insert(usersTable).values(user);

// Insert multiple
await db.insert(usersTable).values([user1, user2]);
```

### Select

```typescript
// Select all
const users = await db.select().from(usersTable);
// Return type: { id: number; name: string; age: number; email: string; }[]

// Select with conditions
import { eq } from 'drizzle-orm';
const user = await db.select().from(usersTable).where(eq(usersTable.email, 'john@example.com'));
```

### Update

```typescript
await db
  .update(usersTable)
  .set({ age: 31 })
  .where(eq(usersTable.email, 'john@example.com'));
```

### Delete

```typescript
await db.delete(usersTable).where(eq(usersTable.email, 'john@example.com'));
```

### Filter operators

From the imports shown in docs:
- `eq(column, value)` — equals
- `sql` template tag — raw SQL expressions

Other operators exist (`ne`, `gt`, `lt`, `gte`, `lte`, `like`, `ilike`, `and`, `or`, `not`, `inArray`, `notInArray`, `isNull`, `isNotNull`, `between`) but were not explicitly demonstrated in the retrieved context7 snippets.

---

## Migrations (drizzle-kit)

### drizzle.config.ts

```typescript
import { config } from 'dotenv';
import { defineConfig } from "drizzle-kit";

config({ path: '.env' });

export default defineConfig({
  schema: "./src/schema.ts",
  out: "./migrations",
  dialect: "postgresql",
  dbCredentials: {
    url: process.env.DATABASE_URL!,
  },
});
```

### Key commands

```bash
# Generate migration SQL from schema changes
npx drizzle-kit generate

# Push schema directly to database (no migration files — dev only)
npx drizzle-kit push

# Pull existing database schema into Drizzle schema files
npx drizzle-kit pull
```

### Config fields

- `schema` — path to your schema file(s)
- `out` — output directory for migration SQL files
- `dialect` — `"postgresql"` | `"mysql"` | `"sqlite"`
- `dbCredentials.url` — connection string

---

## Relations & Joins

### Defining relations (for relational query builder)

Relations are defined separately from table schemas using the `relations()` function. They do NOT create foreign keys in the database — they are metadata for the relational query API.

```typescript
import { relations } from 'drizzle-orm';

export const usersRelations = relations(users, ({ one, many }) => ({
  invitee: one(users, { fields: [users.invitedBy], references: [users.id] }),
  posts: many(posts),
  usersToGroups: many(usersToGroups),
}));

export const postsRelations = relations(posts, ({ one, many }) => ({
  author: one(users, { fields: [posts.authorId], references: [users.id] }),
  comments: many(comments),
}));

export const commentsRelations = relations(comments, ({ one, many }) => ({
  post: one(posts, { fields: [comments.postId], references: [posts.id] }),
  author: one(users, { fields: [comments.creator], references: [users.id] }),
  likes: many(commentLikes),
}));
```

### Relation types

- `one(targetTable, { fields: [sourceColumn], references: [targetColumn] })` — one-to-one or many-to-one
- `many(targetTable)` — one-to-many (no fields/references needed on the "many" side)

### Many-to-many (junction table pattern)

```typescript
export const usersToGroups = pgTable('users_to_groups', {
  id: serial('id').primaryKey(),
  userId: integer('user_id').notNull().references(() => users.id),
  groupId: integer('group_id').notNull().references(() => groups.id),
}, (t) => [
  primaryKey({ columns: [t.userId, t.groupId] })
]);

export const usersToGroupsRelations = relations(usersToGroups, ({ one }) => ({
  group: one(groups, { fields: [usersToGroups.groupId], references: [groups.id] }),
  user: one(users, { fields: [usersToGroups.userId], references: [users.id] }),
}));
```

### SQL-level joins

Not covered in the context7 snippets retrieved. The relational query builder (`db.query.users.findMany({ with: { posts: true } })`) is the documented approach for loading related data, but the exact `db.select().from().innerJoin()` / `.leftJoin()` API was not in these results.

---

## Transactions

Not covered in context7 docs retrieved. The transaction API typically looks like:

```typescript
// Expected API (not from context7 — verify against official docs)
await db.transaction(async (tx) => {
  await tx.insert(usersTable).values(user);
  await tx.update(accountsTable).set({ balance: 0 }).where(eq(accountsTable.userId, id));
  // throw to rollback
});
```

**Status: Not covered in context7 docs.** The above is an expected pattern — verify against official Drizzle documentation before relying on it.

---

## Error Handling

Not covered in context7 docs retrieved. Drizzle ORM throws standard JavaScript errors. PostgreSQL constraint violations surface as errors from the underlying driver (node-postgres or Neon serverless).

**Status: Not covered in context7 docs.**

---

## Prepared Statements

### Serverless optimization pattern

```typescript
// Declare outside handler for connection reuse
const databaseConnection = ...;
const db = drizzle({ client: databaseConnection });
const prepared = db.select().from(...).prepare();

// AWS Lambda / serverless handler
export const handler = async (event: APIGatewayProxyEvent) => {
  return prepared.execute();
};
```

Key insight: Declaring `db` and prepared statements outside the handler scope enables connection and statement reuse across invocations in serverless environments.

---

## Anti-Patterns

Based on patterns observed in context7 docs:

1. **Using `serial()` instead of `generatedAlwaysAsIdentity()`** — The newer identity column syntax (`integer().primaryKey().generatedAlwaysAsIdentity()`) is preferred over `serial('id').primaryKey()` for PostgreSQL.

2. **Creating database connections inside request handlers** — In serverless environments, connection and prepared statement declarations should be outside the handler to enable reuse.

3. **Confusing `relations()` with foreign keys** — Relations defined via `relations()` are metadata for the relational query API only. They do NOT create database-level foreign keys. Use `.references()` on column definitions for actual FK constraints.

4. **Using `sql.raw()` for user input** — The `sql.raw()` template is shown for tenant ID injection but should never be used with untrusted user input. Use parameterized queries via the `sql` template tag instead.

---

## Key Gotchas

1. **Self-referencing columns need `AnyPgColumn` type annotation.** Without it, TypeScript circular reference errors occur:
   ```typescript
   invitedBy: integer('invited_by').references((): AnyPgColumn => users.id)
   ```

2. **`relations()` and `.references()` serve different purposes.** `.references()` = database FK constraint. `relations()` = ORM-level metadata for relational queries. You typically need both.

3. **Schema third argument is an array now.** Constraints like `primaryKey()` and `unique()` are returned as array elements in the third argument to `pgTable()`:
   ```typescript
   pgTable('name', { ...columns }, (t) => [
     primaryKey({ columns: [t.col1, t.col2] })
   ])
   ```

4. **`pgSchema` tables use `.table()` method, not `pgTable()`.** When working with non-public schemas, define tables via `customSchema.table('name', { ... })`.

5. **Environment variable pattern varies by driver.** Neon HTTP uses `neon(process.env.DATABASE_URL!)` then passes to `drizzle({ client: sql })`. Node-postgres uses `drizzle(process.env.DATABASE_URL!)` directly.

6. **`$inferInsert` for type-safe inserts.** Use `typeof table.$inferInsert` to get the insert type. This ensures optional columns (those with defaults or nullable) are properly typed as optional in the insert object.

7. **drizzle-kit `push` vs `generate`.** `push` applies schema directly (dev/prototyping). `generate` creates SQL migration files (production). Using `push` in production skips migration history and is dangerous.
