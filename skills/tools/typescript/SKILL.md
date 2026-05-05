---
name: typescript
description: "Use when writing, modifying, or debugging TypeScript in the EOS stack — covers React 18/19 component and hook typing, Zod-derived types, discriminated unions, satisfies/as const, tsconfig for Vite, AND backend Hono routing + Drizzle schema types + RLS patterns."
allowed-tools: "Read, Bash"
version: 2.0
source_url: "https://www.typescriptlang.org/docs/"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "5.8"
sdk_version: "typescript@5.8"
speed_category: medium
trigger: both
effort: medium
context: fork
sources:
  - "https://www.typescriptlang.org/docs/"
  - "https://react.dev/learn/typescript"
  - "https://devblogs.microsoft.com/typescript/announcing-typescript-5-8/"
  - "https://devblogs.microsoft.com/typescript/typescript-native-port/"
  - "https://www.totaltypescript.com/clarifying-the-satisfies-operator"
  - "https://www.totaltypescript.com/tsconfig-cheat-sheet"
  - "https://react.dev/reference/react/forwardRef"
  - "https://www.typescriptlang.org/tsconfig/verbatimModuleSyntax.html"
  - "https://www.typescriptlang.org/docs/handbook/modules/guides/choosing-compiler-options.html"
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

## Frontend Quick Reference (React 18/19 + Vite)

### Strict tsconfig for Vite+React

```jsonc
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "isolatedModules": true,
    "verbatimModuleSyntax": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "resolveJsonModule": true,
    "allowImportingTsExtensions": false,
    "noEmit": true
  },
  "include": ["src"]
}
```

### Component Props (preferred patterns)

```tsx
// 1. Inline for simple local components
function Badge({ label }: { label: string }) { return <span>{label}</span> }

// 2. Named type for reusable — extend native element props
import type { ComponentPropsWithoutRef } from 'react'
type ButtonProps = ComponentPropsWithoutRef<'button'> & {
  variant?: 'primary' | 'ghost'
}
function Button({ variant = 'primary', className, ...rest }: ButtonProps) {
  return <button data-variant={variant} className={className} {...rest} />
}
```

Never use `React.FC` — it loses generics and implicitly adds `children`.

### Hook Typing — Discriminated Union State

```tsx
type AsyncState<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: T }
  | { status: 'error'; error: Error }

const [state, setState] = useState<AsyncState<User>>({ status: 'idle' })
if (state.status === 'success') state.data // narrowed
```

### Zod-Derived Types (single source of truth)

```ts
const UserSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  role: z.enum(['admin', 'member']).default('member'),
})
type User      = z.infer<typeof UserSchema>   // output — has role
type UserInput = z.input<typeof UserSchema>   // input  — role optional
```

Never re-declare a type that can be `z.infer`'d. For `react-hook-form` use `useForm<z.input<typeof Schema>>()` — the input type matches the raw form fields before defaults/transforms apply.

### `satisfies` vs type annotation

```ts
// Bad: widens config.port to string | number
const config: Record<string, string | number> = { port: 3000, host: 'localhost' }

// Good: validates shape AND preserves literal inference
const config = { port: 3000, host: 'localhost' } satisfies Record<string, string | number>
config.port // number (not string | number)
```

### `as const` for enum-like unions

```ts
const STAGES = ['idea', 'early', 'growth', 'scale'] as const
type Stage = typeof STAGES[number]
```

### Template literal types for routes

```ts
type ApiRoute = `/api/${string}`
type Method   = 'GET' | 'POST' | 'PATCH' | 'DELETE'
type Endpoint = `${Method} ${ApiRoute}`
```

## Gotchas

1. **Two separate runtimes** — Python (`eos_ai`) and TypeScript (`saas`) are completely separate processes. The bridge is the only connection.

2. **Drizzle RLS requires `withOrg()`** — Every query on a tenant-scoped table MUST go through `withOrg(orgId, fn)`. Queries outside `withOrg()` return zero rows silently.

3. **Neon HTTP driver cannot do transactions** — EOS uses the WebSocket driver because `SET LOCAL` requires a real transaction.

4. **Zod: always `safeParse`, never `parse`** — `parse()` throws and bubbles to 500. `safeParse()` lets you return a proper 400.

5. **tsx does not type-check** — Always run `npx tsc --noEmit` before declaring a change complete.

6. **ESM imports need `.js` extensions** — Even though source is `.ts`, relative imports use `.js` under `moduleResolution: "bundler"` / ESM.

7. **`React.FC` is an anti-pattern** — Prefer `function Comp(props: Props)`. `React.FC` breaks generic components and implicitly injects `children`, which you rarely want.

8. **`useForm<z.infer<...>>` is wrong when the schema has `.default()` or `.transform()`** — Use `z.input<typeof Schema>` for the form type. `z.infer` (alias of `z.output`) is post-transform and will make fields required that are still optional in the DOM.

9. **`noUncheckedIndexedAccess` changes everything** — With it enabled, `arr[0]` is `T | undefined`. This is the correct behavior but requires narrowing before use. Worth the pain.

10. **`verbatimModuleSyntax` enforces `import type`** — Any import used only as a type must be `import type`. The compiler no longer erases unused value imports. Pairs well with `isolatedModules` and bundlers like Vite/esbuild.

11. **React 19 deprecates `forwardRef`** — `ref` is now a normal prop. For React 18 codebases keep `forwardRef`; for new React 19 code, type `ref` as `React.Ref<HTMLButtonElement>` directly in props. Do not mix the two patterns in one component.

12. **`as SomeType` assertions hide bugs** — They silence the compiler without proving anything. Prefer type guards, `in` checks, or Zod runtime validation at boundaries.

13. **Drizzle numeric columns return strings** — `numeric()` columns are `string` in TS, not `number`. Convert with `Number()` when doing math.

14. **`as const` position matters** — `['a','b'] as const` → `readonly ['a','b']`. `['a' as const, 'b']` → `['a', string]`. Put `as const` at the end of the full expression.

See references/best_practices.md for full 19-section research, references/examples.md for executable patterns, references/anti_patterns.md for real failures, and references/integrations.md for composition with React/Zod/RHF/React Query/Drizzle/Hono/Vite.
