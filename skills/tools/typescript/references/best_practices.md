# TypeScript — Creator-Level Best Practices
Source: https://www.typescriptlang.org/docs/
API Version: TypeScript 5.4
SDK Version: tsx 4.19.2
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## Authentication

TypeScript itself has no authentication concept, but the EOS saas layer enforces correctness through `tsconfig.json` strict settings — these are the "auth layer" that prevents type-unsafe code from reaching production.

Required strict settings (already in EOS tsconfig):
```json
{
  "strict": true,           // enables ALL strict checks below
  "target": "ES2022",
  "module": "ESNext",
  "moduleResolution": "Bundler",
  "skipLibCheck": true,      // skip .d.ts checking for speed
  "esModuleInterop": true,   // correct CommonJS/ESM interop
  "resolveJsonModule": true  // allow importing .json files
}
```

`strict: true` enables: `strictNullChecks`, `noImplicitAny`, `strictFunctionTypes`, `strictBindCallApply`, `strictPropertyInitialization`, `noImplicitThis`, `alwaysStrict`, `useUnknownInCatchVariables`. Never set `strict: false` or disable individual strict checks.

## Core Operations with Exact Signatures

### Generics — Constrained Type Parameters
```typescript
// Generic function with constraint
function getProperty<T, K extends keyof T>(obj: T, key: K): T[K] {
  return obj[key]
}

// Generic with default
type ApiResponse<T = unknown> = { data: T; status: number }
```

### Utility Types — Built-in Transformations
```typescript
Partial<T>       // All properties optional
Required<T>      // All properties required
Pick<T, K>       // Subset of properties
Omit<T, K>       // All except specified properties
Record<K, V>     // Object with keys K and values V
Readonly<T>      // All properties readonly
ReturnType<F>    // Return type of function F
Parameters<F>    // Tuple of function parameter types
Awaited<T>       // Unwrap Promise type
NonNullable<T>   // Exclude null and undefined
Extract<T, U>    // Members of T assignable to U
Exclude<T, U>    // Members of T not assignable to U
```

### Conditional Types
```typescript
type IsString<T> = T extends string ? true : false
type Flatten<T> = T extends Array<infer U> ? U : T
```

### Template Literal Types
```typescript
type EventName = `on${Capitalize<string>}`  // "onFoo", "onClick", etc.
type Route = `/api/${string}`               // "/api/users", "/api/skills", etc.
```

## Pagination Patterns

Not applicable to TypeScript as a language. For EOS API pagination patterns, see the route files — currently EOS routes return full result sets without pagination (acceptable at current data scale).

## Rate Limits

Not applicable to TypeScript as a language. The Hono framework supports rate limiting middleware, but EOS has not implemented it yet (single-user validation phase).

## Error Codes and Recovery

Common TypeScript compiler errors and what they mean in EOS context:

| Error | Meaning | Fix |
|-------|---------|-----|
| **TS2322** | Type 'X' is not assignable to type 'Y' | Check schema types — Drizzle inferred types may differ from Zod schemas |
| **TS2345** | Argument type mismatch | Verify function signature — common when passing Drizzle query results to functions expecting different shapes |
| **TS7006** | Parameter implicitly has 'any' type | Add type annotation — strict mode requires this |
| **TS2339** | Property does not exist on type | Check if using correct schema table — `ventures.orgId` vs `skills.orgId` |
| **TS2304** | Cannot find name | Missing import — check that `.js` extension is on relative imports |
| **TS2532** | Object is possibly undefined | Add null check before accessing — `const [row] = rows; if (!row) return` |
| **TS18046** | Variable is of type 'unknown' | Narrow with type guard — `useUnknownInCatchVariables` causes this in catch blocks |
| **TS1343** | Top-level await in non-module | Ensure `"type": "module"` is in package.json |
| **TS2307** | Cannot find module | Check path — relative imports need `.js` extension in ESM |
| **TS2554** | Expected N arguments, got M | Check function signature — Drizzle `.where()` and `.set()` are the usual suspects |

## SDK Idioms

### `as const` — Immutable Literal Types
```typescript
const STAGES = ['idea', 'pre_revenue', 'early', 'growth', 'scale'] as const
type Stage = typeof STAGES[number]  // 'idea' | 'pre_revenue' | ...
// Use with pgEnum values to keep enum definitions DRY
```

### `satisfies` — Validate Without Widening (TS 5.0+)
```typescript
const config = {
  port: 3000,
  host: 'localhost',
} satisfies Record<string, string | number>
// config.port is still number (not string | number)
```

### `using` — Explicit Resource Management (TS 5.2+)
```typescript
// Future pattern for database connections:
await using db = await getConnection()
// db is automatically disposed when scope exits
```

### Import Type — Type-Only Imports
```typescript
import type { Env } from '../types.js'           // type-only, erased at runtime
import { type Agent, agents } from '../schema.js' // inline type modifier
```

### Const Type Parameters (TS 5.0+)
```typescript
function createRoute<const T extends string>(path: T) { /* ... */ }
// Infers literal type instead of widening to string
```

## Anti-Patterns

1. **`any` abuse** — Using `any` defeats the entire purpose of TypeScript. Use `unknown` when you genuinely do not know the type, then narrow with type guards. The `(result.data as any).output` pattern in the EOS codebase is a known anti-pattern to fix.

2. **Type assertions (`as`)** — `value as Type` tells the compiler to trust you, but you might be wrong. Prefer type guards: `if ('output' in result)` or Zod `.parse()`.

3. **Ignoring strict null checks** — Never add `!` (non-null assertion) to silence null errors. Handle the null case explicitly: `if (!row) return c.json({ error: 'not_found' }, 404)`.

4. **`@ts-ignore` / `@ts-expect-error`** — These suppress compiler errors. If you need them, the type design is wrong. Fix the types.

5. **Enum keyword** — TypeScript `enum` has runtime behavior that is confusing. Use `as const` arrays with `typeof ARRAY[number]` union types, or Drizzle's `pgEnum()` which generates both the DB enum and TS type.

6. **Exporting mutable state** — Never `export let` or `export const obj = {}` where mutations are expected. Module-level state creates hidden coupling. In EOS, the `db` and `appDb` exports are the only acceptable module-level state (they are connection pools, not application state).

7. **Implicit return types on public functions** — Always annotate return types on exported functions. TypeScript can infer them, but explicit types serve as documentation and catch refactoring errors.

## Data Model

### Type System Fundamentals

TypeScript's type system is **structural**, not nominal. Two types with the same shape are assignable regardless of name:

```typescript
interface User { id: string; name: string }
interface Agent { id: string; name: string }
// Agent is assignable to User and vice versa — same shape
```

This matters in EOS because many tables share `id`, `orgId`, `createdAt` shapes. To distinguish them, use branded types (see Industry Expert section).

### Interfaces vs Types

- `interface` — Use for object shapes that may be extended. Supports declaration merging.
- `type` — Use for unions, intersections, mapped types, conditional types. More flexible.
- EOS convention: Drizzle generates `type` aliases (`type Venture = ...`). Follow that pattern.

### Generics and Mapped Types

```typescript
// Mapped type — transform all properties
type Nullable<T> = { [K in keyof T]: T[K] | null }

// Indexed access
type VentureName = Venture['name']  // string

// keyof
type VentureKeys = keyof Venture  // 'id' | 'orgId' | 'name' | ...
```

## Webhooks and Events

Not applicable to TypeScript as a language. EOS has an `events` table and route for event logging, but does not currently implement outbound webhooks.

## Limits

- **Type complexity**: TypeScript has a max instantiation depth (~50 levels). Deeply nested generics or recursive conditional types can hit this. Drizzle queries occasionally trigger this with complex joins — simplify the query or use intermediate type aliases.
- **Bundle size**: Not a concern for EOS since we run server-side via tsx. No client-side bundling.
- **Compilation speed**: `skipLibCheck: true` in tsconfig significantly improves `tsc` speed by skipping `.d.ts` validation. Already enabled in EOS.

## Cost Model

TypeScript is open source and free. No API costs, no usage charges. The only cost is developer time learning the type system.

## Version Pinning

Current EOS versions (from `package.json`):
```
typescript:               ^5.4.0
tsx:                      ^4.19.2
hono:                     ^4.12.8
@hono/node-server:        ^1.19.11
drizzle-orm:              ^0.39.3
drizzle-kit:              ^0.30.4
@neondatabase/serverless: ^0.10.4
zod:                      ^3.23.8
ws:                       ^8.20.0
```

Pin major versions. Minor/patch updates are generally safe. Watch for:
- `drizzle-orm` breaking changes in query builder API between 0.x versions
- `hono` v4 → v5 migration (not yet released)
- `zod` v3 → v4 migration (in development)

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

TypeScript's core design philosophy:

1. **Gradual typing** — You can add types incrementally. You do not need to type everything at once. This is why `strict: true` is important — it removes the escape hatches that gradual typing leaves open.

2. **Structural typing** — Types are compatible based on shape, not declaration. This is intentional: it makes TypeScript work with JavaScript's duck-typing culture. The tradeoff is that you cannot distinguish structurally identical types without branding.

3. **Erasure** — All types are erased at runtime. TypeScript adds zero runtime overhead. The tradeoff: you cannot do `instanceof` checks on interfaces or type aliases. Use Zod for runtime validation.

4. **Soundness tradeoffs** — TypeScript is intentionally unsound in specific places (bivariant function parameters in methods, `any` type, enum reverse mappings). The TypeScript team chose pragmatism over theoretical purity. Know where the holes are.

5. **Expression-level type inference** — TypeScript infers types bottom-up from expressions, not top-down from annotations. This means `const x = [1, 2, 3]` infers `number[]`, not `[1, 2, 3]`. Use `as const` when you need the literal type.

## Problem-Solution Map and Hidden Capabilities

### EOS Pattern: Typed API Route with Full Validation

```typescript
// Problem: ensure route handler has typed context + validated body + RLS-scoped DB access
// Solution: Hono<Env> + Zod safeParse + withOrg

router.patch('/:id', async (c) => {
  const orgId = c.get('orgId')                        // typed from Env
  const parsed = PatchSchema.safeParse(await c.req.json()) // validated
  if (!parsed.success) return c.json({ error: 'validation_error', message: parsed.error.flatten() }, 400)

  const [updated] = await withOrg(orgId, (tx) =>       // RLS-scoped
    tx.update(table).set(updates).where(eq(table.id, id)).returning()
  )
  if (!updated) return c.json({ error: 'not_found' }, 404)
  return c.json({ item: updated })
})
```

### EOS Pattern: Drizzle Schema as Single Source of Truth

```typescript
// Problem: keep DB types, API response types, and validation in sync
// Solution: schema.ts defines everything, routes import types

// schema.ts
export const ventures = pgTable('ventures', { /* ... */ })
export type Venture    = typeof ventures.$inferSelect
export type NewVenture = typeof ventures.$inferInsert

// route uses Venture type implicitly via Drizzle query return type
```

### EOS Pattern: Bridge to Python

```typescript
// Problem: TypeScript needs agent intelligence but should not call LLMs directly
// Solution: python_bridge.ts spawns subprocess, JSON on stdin/stdout

const result = await callBridge({ action: 'agent.run', payload: data })
// result: BridgeResult = { success: boolean; data?: unknown; error?: string }
```

### Hidden: Drizzle Custom Types for pgvector

```typescript
// schema.ts defines a custom vectorType for pgvector columns
export const vectorType = customType<{
  data: number[]
  driverData: string
  config: { dimensions: number }
}>({ /* serialization logic */ })

// Usage: embedding: vectorType('embedding', { dimensions: 768 })
```

## Operational Behavior and Edge Cases

1. **Type erasure at runtime** — TypeScript types do not exist at runtime. `typeof` in JavaScript returns `"string"`, `"number"`, `"object"` — not TypeScript types. For runtime type checking, use Zod.

2. **ESM module resolution** — With `moduleResolution: "Bundler"`, TypeScript resolves `.js` imports to `.ts` source files during type checking. At runtime, tsx handles the same resolution. Always use `.js` extensions in imports.

3. **Async error handling** — In Hono, unhandled rejections in route handlers are caught by `app.onError()`. But `withOrg()` transactions roll back automatically on throw, so errors in database operations are contained.

4. **`process.env` is `string | undefined`** — Every env var access needs a null check. The pattern `process.env.DATABASE_URL` returns `string | undefined`. Use `if (!url) throw new Error(...)` at module load time (as `client.ts` does).

5. **Drizzle `.returning()` is Postgres-specific** — Not portable to MySQL/SQLite. Acceptable for EOS since Neon is always Postgres.

6. **WebSocket lifecycle** — The Neon serverless driver requires `neonConfig.webSocketConstructor = ws` in Node.js. This is set once at module load in `client.ts`. If forgotten, all queries fail silently.

## Ecosystem Position and Composition

TypeScript in the EOS architecture occupies the **interface layer**:

```
User -> HTTP Request -> [TypeScript: Hono API]
                            |
                            v
                        [Neon Postgres] <-- [Python: eos_ai agents]
                            |
                            v
                        [TypeScript: python_bridge.ts] --> [Python subprocess]
```

The composition stack:
- **Hono** — HTTP framework (lightweight, Web Standard API based)
- **Drizzle** — SQL query builder and ORM (type-safe, no heavy abstraction)
- **Zod** — Runtime validation (schema-first, composable)
- **Neon Serverless** — Postgres driver (WebSocket-based, supports transactions)
- **tsx** — TypeScript runner (esbuild-based, fast)

Each dependency was chosen for minimal abstraction overhead. Hono is ~14KB. Drizzle generates SQL you can read. Zod schemas map 1:1 to TypeScript types. This is intentional — EOS values transparency over magic.

## Trajectory and Evolution

### TypeScript 5.5+ Features to Watch

- **Inferred type predicates** (5.5) — `filter(Boolean)` correctly narrows arrays. No more `.filter((x): x is NonNullable<T> => !!x)`.
- **Regular expression syntax checking** (5.5) — Regex literals get compile-time validation.
- **`using` declarations** (5.2+, stage 3) — Explicit resource management. Future pattern for DB connections: `await using conn = pool.connect()`.
- **Decorator metadata** (5.2+) — Standard decorators with metadata API. May replace some Drizzle patterns.

### Drizzle ORM Evolution

- Drizzle is still 0.x — API stability not guaranteed between minor versions
- Relational queries API is maturing (joins, subqueries)
- Watch for Drizzle v1.0 which will lock the API

### Zod 4

- Major rewrite in progress (2025-2026)
- Will be faster, smaller, but may have breaking API changes
- `z.object().strict()` behavior may change — test after upgrade

### Hono Evolution

- v5 not yet released — v4 is stable
- Server Components integration being explored
- RPC mode (`hono/client`) enables end-to-end type safety without code generation

## Conceptual Model and Solution Recipes

### How to Think About TypeScript's Type System

TypeScript's type system is a **set-theoretic language** layered on top of JavaScript:

- **Every type is a set** of possible values. `string` is the set of all strings. `"hello"` is a set with one member.
- **Union (`|`)** is set union. `string | number` = all strings and all numbers.
- **Intersection (`&`)** is set intersection. `A & B` = values that satisfy both A and B.
- **`never`** is the empty set. No value satisfies `never`.
- **`unknown`** is the universal set. Every value satisfies `unknown`.
- **`any`** breaks the set theory — it is both a subset and superset of every type. It is the escape hatch from the type system.

### Mental Model for Drizzle + TypeScript

Think of Drizzle schema definitions as **type-level database documentation**:
- `pgTable()` defines both the SQL table AND the TypeScript type
- `$inferSelect` extracts what a SELECT returns
- `$inferInsert` extracts what an INSERT accepts (optionals for defaults)
- The schema file IS the single source of truth for both layers

### Mental Model for Zod + TypeScript

Zod bridges the compile-time/runtime gap:
- TypeScript types exist only at compile time (erased)
- Zod schemas exist at runtime (validated)
- `z.infer<typeof schema>` generates the TypeScript type FROM the Zod schema
- In EOS: Drizzle defines DB types, Zod defines API input types — they are NOT the same

## Industry Expert and Cutting-Edge Usage

### Branded Types (Nominal Typing in Structural Land)

```typescript
// Problem: UserId and OrgId are both strings, but should not be interchangeable
type UserId = string & { readonly __brand: 'UserId' }
type OrgId  = string & { readonly __brand: 'OrgId' }

function getUser(id: UserId): User { /* ... */ }
getUser(orgId) // Error: OrgId is not assignable to UserId
```

EOS does not use branded types yet, but should consider them for `orgId` vs `userId` vs `ventureId` to prevent accidental swaps at the type level.

### Discriminated Union Pattern for API Responses

```typescript
type ApiResult<T> =
  | { success: true; data: T }
  | { success: false; error: string }

// TypeScript narrows automatically:
if (result.success) {
  result.data  // T — accessible
} else {
  result.error // string — accessible
}
```

The `BridgeResult` interface in EOS approximates this but uses optional fields instead of a proper discriminated union. A refactor to discriminated unions would give better type narrowing.

### `NoInfer<T>` Utility (TS 5.4)

```typescript
// Prevents inference from a specific position
function createFSM<S extends string>(config: {
  initial: NoInfer<S>
  states: S[]
}) { /* ... */ }
// initial must be one of states, but doesn't influence what S is inferred as
```

### Const Assertions for Exhaustive Checks

```typescript
const VENTURE_STAGES = ['idea', 'pre_revenue', 'early', 'growth', 'scale'] as const
type Stage = typeof VENTURE_STAGES[number]

function handleStage(stage: Stage): string {
  switch (stage) {
    case 'idea': return 'Ideation phase'
    case 'pre_revenue': return 'Pre-revenue'
    case 'early': return 'Early revenue'
    case 'growth': return 'Growth'
    case 'scale': return 'At scale'
    // No default needed — TypeScript verifies exhaustiveness
    // Adding a new stage to the array causes a compile error here
  }
}
```

### Effect-TS Pattern (Emerging)

Effect-TS is an emerging pattern for typed error handling and dependency injection. Not in EOS today, but worth monitoring for the saas layer as it grows:
```typescript
// Effect encodes success type, error type, and dependencies in the type signature
// Effect<Success, Error, Requirements>
// Eliminates try/catch in favor of typed error channels
```

---

## EOS Usage Patterns

Current EOS TypeScript patterns that are confirmed working:

1. **Hono<Env> typed context** — All routes use `Hono<Env>` for typed `orgId`/`userId` access
2. **withOrg() RLS wrapper** — Every tenant-scoped query goes through `withOrg(orgId, fn)`
3. **Zod safeParse on all mutations** — GET routes do not validate, PATCH/POST routes always safeParse
4. **Drizzle `.returning()` on mutations** — UPDATE and INSERT always return the modified row
5. **Admin DB for auth checks** — Auth middleware uses `db` (admin pool) to validate org existence
6. **Python bridge for intelligence** — Agent routes call `callBridge()` to reach eos_ai layer
7. **ESM with .js extensions** — All relative imports use `.js` extension per ESM standard
8. **No build step** — tsx runs TypeScript directly, no compilation to JS

## Gotchas

1. **withOrg() is mandatory** — Forgetting `withOrg()` on a tenant table query returns zero rows silently. No error, no warning, just empty results.

2. **Drizzle numeric columns return strings** — `numeric()` columns in Drizzle return `string` in TypeScript (not `number`). The `monthlyRevenue` field is `string`. Convert with `Number()` or `parseFloat()` when doing math.

3. **Zod `.strict()` rejects unknown keys** — Without `.strict()`, Zod silently strips unknown keys. EOS uses `.strict()` on all input schemas to catch typos in API requests.

4. **tsx does not type-check** — `npx tsx file.ts` runs the file but does not verify types. A file with type errors will execute if the JavaScript is valid. Always run `npx tsc --noEmit` separately.

5. **WebSocket constructor must be set before any queries** — `neonConfig.webSocketConstructor = ws` must execute before the first `Pool` connection. In EOS this is at the top of `client.ts`.

6. **`as const` assertion position matters** — `['a', 'b'] as const` gives `readonly ['a', 'b']`. `['a' as const, 'b']` gives `['a', string]`. Always put `as const` at the end of the full expression.

7. **Drizzle pgEnum values must match exactly** — The values in `pgEnum()` must match the Postgres enum exactly. A mismatch causes runtime INSERT/UPDATE failures, not compile-time errors.
