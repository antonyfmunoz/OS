---
name: typescript
description: "Use when writing, modifying, or debugging TypeScript code in the EOS saas layer — covers Hono routing, Drizzle schema types, Zod validation, module patterns, and strict-mode conventions."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://www.typescriptlang.org/docs/"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "TypeScript 5.4"
sdk_version: "tsx 4.19.2"
speed_category: medium
trigger: both
effort: medium
context: fork
---

# Tool: TypeScript

## What This Tool Does

TypeScript is the language for the EOS SaaS API layer (`/opt/OS/saas/`). It provides:

- **Type-safe API routes** via Hono with typed context variables (`Env`)
- **Type-safe database access** via Drizzle ORM with schema-inferred types (`$inferSelect`, `$inferInsert`)
- **Runtime validation** via Zod schemas that gate every mutation endpoint
- **Python bridge** to call into the `eos_ai` intelligence layer from TypeScript routes

TypeScript does NOT run agents, cognitive loops, or LLM calls directly. Those stay in the Python `eos_ai` layer. TypeScript owns the HTTP surface and data access.

## EOS Integration

### Directory Structure

```
saas/
  api/
    index.ts            — Hono app setup, middleware mounting, server start
    types.ts            — Shared Env type (orgId, userId in context)
    middleware/
      auth.ts           — x-org-id header extraction and org validation
    routes/
      ventures.ts       — CRUD for ventures (withOrg RLS wrapper)
      skills.ts         — CRUD + AI improve endpoint
      interactions.ts   — Interaction logging
      outcomes.ts       — Outcome tracking
      approvals.ts      — Approval workflow
      agent.ts          — Bridge to Python agent runtime
      events.ts         — Event log
    lib/
      python_bridge.ts  — spawn Python subprocess, JSON stdin/stdout
  db/
    schema.ts           — Drizzle table definitions, Zod validators, type exports
    client.ts           — Neon WebSocket pool, withOrg() RLS wrapper
    migrate.ts          — Migration runner (extensions, RLS, eos_app role)
    migrations/         — drizzle-kit generated SQL
  package.json          — ESM, tsx runner, drizzle-kit scripts
  tsconfig.json         — strict: true, ES2022, Bundler resolution
```

### How It Compiles and Runs

- **Dev**: `npx tsx watch api/index.ts` — tsx executes TypeScript directly via esbuild transforms, no `tsc` compile step needed
- **Type checking**: `npx tsc --noEmit` — validates types without emitting JS
- **Migrations**: `npx tsx db/migrate.ts` — runs through tsx, not compiled
- **No build step**: EOS does not compile to JS for deployment. tsx runs `.ts` files directly.

### Connection to Neon

Two pools in `db/client.ts`:
- `adminPool` (neondb_owner, BYPASSRLS) — migrations and seeds only
- `appPool` (eos_app role, RLS enforced) — all application queries

The `withOrg(orgId, fn)` wrapper opens a transaction on `appPool`, sets `app.current_org_id` via `set_config()`, then runs `fn(tx)`. This is the RLS enforcement point. Every tenant-scoped query MUST use `withOrg()`.

## Authentication

The saas layer uses header-based org authentication (pre-JWT phase):

```typescript
// middleware/auth.ts pattern
export async function authMiddleware(c: Context<Env>, next: Next) {
  const orgId = c.req.header('x-org-id')
  if (!orgId) return c.json({ error: 'unauthorized' }, 401)
  if (!UUID_RE.test(orgId)) return c.json({ error: 'unauthorized' }, 401)

  // Validate org exists via admin db (bypasses RLS for auth check)
  const rows = await db.select({ id: organizations.id, ownerId: organizations.ownerId })
    .from(organizations).where(eq(organizations.id, orgId)).limit(1)

  if (rows.length === 0) return c.json({ error: 'unauthorized' }, 401)

  c.set('orgId', rows[0].id)
  c.set('userId', rows[0].ownerId)
  await next()
}
```

Context variables are typed via the `Env` type:
```typescript
export type Env = {
  Variables: {
    orgId:  string
    userId: string
  }
}
```

## Quick Reference

### Hono Route Definition Pattern

```typescript
import { Hono } from 'hono'
import type { Env } from '../types.js'

const router = new Hono<Env>()

router.get('/', async (c) => {
  const orgId = c.get('orgId')  // typed string, set by auth middleware
  // ...
  return c.json({ data: rows })
})

export default router
```

### Drizzle Schema Type Inference

```typescript
// In schema.ts — define table, export inferred types
export const ventures = pgTable('ventures', { /* columns */ })
export type Venture    = typeof ventures.$inferSelect  // row from DB
export type NewVenture = typeof ventures.$inferInsert   // insert payload
```

### Zod Validation Pattern

```typescript
const PatchSchema = z.object({
  monthly_revenue: z.coerce.number().nonnegative().optional(),
  stage: z.enum(['idea', 'pre_revenue', 'early', 'growth', 'scale']).optional(),
}).strict()  // .strict() rejects unknown keys

// In route handler — always safeParse, never parse
const parsed = PatchSchema.safeParse(await c.req.json())
if (!parsed.success) {
  return c.json({ error: 'validation_error', message: parsed.error.flatten() }, 400)
}
// parsed.data is fully typed from here
```

### Database Query Patterns

```typescript
// SELECT with RLS
const rows = await withOrg(orgId, (tx) =>
  tx.select().from(ventures).where(eq(ventures.orgId, orgId))
)

// SELECT specific columns
const rows = await withOrg(orgId, (tx) =>
  tx.select({ id: skills.id, name: skills.name }).from(skills)
)

// UPDATE with .returning()
const [updated] = await withOrg(orgId, (tx) =>
  tx.update(ventures).set(updates).where(eq(ventures.id, id)).returning()
)

// INSERT with version archiving (multi-statement in single withOrg)
const result = await withOrg(orgId, async (tx) => {
  const [current] = await tx.select().from(skills).where(eq(skills.id, id)).limit(1)
  await tx.insert(skillVersions).values({ skillId: id, orgId, content, version: newVersion })
  const [out] = await tx.update(skills).set({ version: newVersion }).where(eq(skills.id, id)).returning()
  return out
})
```

### Python Bridge Call

```typescript
import { callBridge } from '../lib/python_bridge.js'

const result = await callBridge({ action: 'agent.run', payload: parsed.data })
if (!result.success) return c.json({ error: 'bridge_error', message: result.error }, 502)
return c.json(result.data)
```

### Running

```bash
# Dev server with hot reload
npx tsx watch api/index.ts

# One-off run
npx tsx api/index.ts

# Type check only (no emit)
npx tsc --noEmit

# Generate migration SQL
npm run db:generate

# Run migrations
npm run db:migrate
```

## Conceptual Model

The EOS architecture has two runtimes that complement each other:

| Layer | Language | Responsibility |
|-------|----------|----------------|
| `eos_ai/` | Python | Intelligence: agents, cognitive loop, LLM routing, memory |
| `saas/` | TypeScript | Interface: HTTP API, type-safe DB access, validation |

The bridge between them is `python_bridge.ts`, which spawns a Python subprocess with JSON on stdin/stdout. TypeScript never calls LLMs directly. Python never serves HTTP directly.

This separation means:
- TypeScript handles request validation, auth, and data access
- Python handles reasoning, generation, and agent orchestration
- The two layers share a database (Neon Postgres) but access it independently

## Gotchas

1. **Two separate runtimes** — Python (`eos_ai`) and TypeScript (`saas`) are completely separate processes. Do not import Python modules in TS or vice versa. The bridge is the only connection.

2. **Drizzle RLS requires `withOrg()`** — Every query on a tenant-scoped table MUST go through `withOrg(orgId, fn)`. Queries on `appDb` outside `withOrg()` return zero rows (fail-closed by design). Only `db` (admin pool) bypasses RLS, and that is for auth checks and migrations only.

3. **Neon HTTP driver cannot do transactions** — EOS uses the WebSocket driver (`@neondatabase/serverless` with `ws` polyfill) specifically because `SET LOCAL` requires a real transaction. The HTTP driver is stateless and would not maintain the RLS session variable.

4. **Zod: always `safeParse`, never `parse`** — `parse()` throws on invalid input, which would bubble up as a 500 error. `safeParse()` returns `{ success, data, error }` so you can return a proper 400 with `parsed.error.flatten()`. Every route in EOS uses `safeParse`.

5. **Type narrowing with discriminated unions** — When using `safeParse`, TypeScript narrows `parsed.data` only after checking `parsed.success`. Do not access `.data` before the guard. The Zod types handle this automatically if you follow the `if (!parsed.success) return` pattern.

6. **tsx vs tsc** — `tsx` (via esbuild) executes TypeScript directly without type checking. It is fast but will not catch type errors. `tsc --noEmit` is the type checker. EOS uses tsx for running, tsc for verification. Always run `tsc --noEmit` before declaring a TypeScript change complete.

7. **ESM imports require `.js` extension** — The tsconfig uses `module: "ESNext"` with `moduleResolution: "Bundler"`. All relative imports use `.js` extensions (e.g., `import type { Env } from '../types.js'`) even though the source files are `.ts`. This is the ESM standard that tsx and Node.js require.

8. **`as any` is a code smell** — The codebase has one instance of `(result.data as any).output` in the skills improve route. This is a known tech debt item. New code should define proper types for bridge responses rather than using type assertions.

See references/best_practices.md for TypeScript language patterns, type system mental models, and anti-patterns.
