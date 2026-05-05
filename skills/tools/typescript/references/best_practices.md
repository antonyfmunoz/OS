# TypeScript — Creator-Level Best Practices
Source: https://www.typescriptlang.org/docs/ + https://react.dev/learn/typescript
API Version: TypeScript 5.8 (GA Feb 2025)
SDK Version: typescript@5.8, tsx 4.19.2
Last Researched: 2026-04-06

Scope: Both the frontend (React 18/19 + Vite) and backend (Hono + Drizzle + Zod) layers of EOS. This file covers the language itself and its composition with the EOS stack.

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

---

# Frontend Expansion — React + Vite TypeScript

This section covers the frontend half of the EOS TypeScript surface: React 18/19 component typing, hook generics, Zod-driven forms, and the modern Vite tsconfig.

## TypeScript 5.5 → 5.8 Highlights (what actually changed for app code)

- **5.5 — Inferred type predicates.** `arr.filter(Boolean)` now narrows correctly; no more `filter((x): x is T => !!x)`. Also regex literal syntax checking at compile time.
- **5.5 — Isolated declarations.** A new mode that requires explicit return types on exports so declaration files can be emitted file-by-file in parallel (enables the native Go port's speed).
- **5.6 — Disallowed nullish and truthy checks.** Flags `if (x ?? true)` and similar always-truthy expressions at compile time.
- **5.6 — Iterator helper methods** in the standard lib (map/filter/take on iterators).
- **5.7 — Path rewriting for relative paths.** `--rewriteRelativeImportExtensions` — allows `.ts` imports in source that get rewritten to `.js` on emit. Useful for Node ESM without bundlers.
- **5.7 — Checks for never-initialized variables.** `let x: string` then read before write is now an error.
- **5.8 — `--erasableSyntaxOnly`.** Targets Node.js's native TypeScript execution: forbids `enum`, namespaces with values, parameter properties, etc. — anything that can't be erased. Pair with Node 22+ `--experimental-strip-types`.
- **5.8 — `require()` of ESM under `--module nodenext`.** No longer errors.
- **5.8 — Granular checks for branches in return expressions.** Each branch of a conditional `return` is checked against the declared return type.

## The Native Go Compiler (tsc-go / "TypeScript 7")

- Announced March 2025 by Anders Hejlsberg. Rewrites the TS compiler in Go.
- ~10x faster type-checking (VS Code's 1.5M LOC dropped from 77s to 7.5s).
- Mid-2025: CLI typecheck preview. End-2025: feature-complete builds + language service. Will ship as "TypeScript 7" alongside the existing JS-based "TypeScript 6" during transition.
- **Impact on EOS:** monitor. No code changes required — the Go compiler targets the same language, same tsconfig. When GA, swap the `typescript` package for `@typescript/native` and enjoy. Editor starts instantly. `tsc --noEmit` in CI becomes a 1-2s check instead of 10-30s.

## React Component Typing (the modern patterns)

### The four legitimate ways to type a component

```tsx
// 1. Inline — for one-off local components
function Greeting({ name }: { name: string }) { return <h1>Hi {name}</h1> }

// 2. Named type — for reusable components
type GreetingProps = { name: string; excited?: boolean }
function Greeting({ name, excited }: GreetingProps) { /* ... */ }

// 3. Extend an HTML element's props (MOST COMMON)
import type { ComponentPropsWithoutRef } from 'react'
type ButtonProps = ComponentPropsWithoutRef<'button'> & { variant?: 'primary' | 'ghost' }
function Button({ variant = 'primary', ...rest }: ButtonProps) {
  return <button data-variant={variant} {...rest} />
}

// 4. Generic component — must be `function`, not arrow + React.FC
function List<T>({ items, render }: { items: T[]; render: (item: T) => React.ReactNode }) {
  return <ul>{items.map((it, i) => <li key={i}>{render(it)}</li>)}</ul>
}
```

`React.FC` is officially discouraged. Why: implicit `children`, broken generics, nothing you gain.

### Event handlers

```tsx
// Prefer the dedicated event type:
function onChange(e: React.ChangeEvent<HTMLInputElement>) { /* ... */ }
function onClick(e: React.MouseEvent<HTMLButtonElement>)  { /* ... */ }

// Or let JSX infer inline — usually cleaner:
<input onChange={(e) => setValue(e.currentTarget.value)} />
```

### Hooks

```tsx
// useState — prefer inference
const [count, setCount] = useState(0)               // number
const [user, setUser]   = useState<User | null>(null) // when initial is null

// useState with discriminated union (best for async)
type LoadState<T> = { kind: 'idle' } | { kind: 'loading' } | { kind: 'ok'; data: T } | { kind: 'err'; error: Error }
const [s, setS] = useState<LoadState<User>>({ kind: 'idle' })

// useReducer
type Action = { type: 'inc' } | { type: 'set'; value: number }
function reducer(state: { count: number }, action: Action) {
  switch (action.type) {
    case 'inc': return { count: state.count + 1 }
    case 'set': return { count: action.value }
  }
}
const [state, dispatch] = useReducer(reducer, { count: 0 })

// useContext with null default (avoid silent bugs)
const UserContext = createContext<User | null>(null)
function useUser(): User {
  const u = useContext(UserContext)
  if (!u) throw new Error('useUser must be inside UserProvider')
  return u
}

// useRef
const inputRef = useRef<HTMLInputElement>(null)
inputRef.current?.focus()
```

### forwardRef (React 18) vs ref-as-prop (React 19)

```tsx
// React 18 — forwardRef with ComponentPropsWithoutRef
import { forwardRef, ComponentPropsWithoutRef } from 'react'
type InputProps = ComponentPropsWithoutRef<'input'>
const Input = forwardRef<HTMLInputElement, InputProps>((props, ref) =>
  <input ref={ref} {...props} />
)

// React 19 — ref is a normal prop
type InputProps19 = ComponentPropsWithoutRef<'input'> & { ref?: React.Ref<HTMLInputElement> }
function Input19({ ref, ...rest }: InputProps19) {
  return <input ref={ref} {...rest} />
}
```

`forwardRef` will be deprecated (not removed) in a future React release. For EOS saas frontend (React 18), keep `forwardRef`. When upgrading to React 19, run the React codemod rather than hand-editing.

## Inference-First Typing

TypeScript's type system is designed for inference. Annotate at boundaries (function parameters, public API returns, module exports, hook state initialized with `null`), let inference do the rest.

```ts
// Bad — over-typed, noisy, breaks on refactor
const users: User[] = data.map((d: RawUser): User => ({ id: d.id, name: d.name }))

// Good — infer everything internal
const users = data.map((d) => ({ id: d.id, name: d.name }))
//    ^? { id: string; name: string }[]
```

Rule of thumb:
- Explicit types at **boundaries** (exported functions, public props, API inputs/outputs).
- Inferred types **everywhere else**.
- Use `satisfies` when you want validation without widening.

## `satisfies` — The Modern Alternative to Type Annotations

```ts
// Matt Pocock's canonical example
const routes = {
  home: { path: '/',      auth: false },
  admin:{ path: '/admin', auth: true  },
} satisfies Record<string, { path: string; auth: boolean }>

routes.home.path  // string literal preserved, still validated against the shape
// Without `satisfies`, a plain annotation would widen `path` to string and `auth` to boolean,
// losing the literal types. With `as const` alone, you get literals but no shape validation.
```

Three places `satisfies` is essential:
1. Config objects where you want literal inference AND shape validation.
2. Tuples that would otherwise be `T[]`: `[1, 2, 3] satisfies [number, number, number]`.
3. Typing the return value of a factory without widening the internal shape.

## Zod as the Single Source of Truth

```ts
import { z } from 'zod'

export const UserSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  role: z.enum(['admin', 'member']).default('member'),
  createdAt: z.coerce.date(),
})

export type User      = z.infer<typeof UserSchema>   // post-parse OUTPUT
export type UserInput = z.input<typeof UserSchema>   // pre-parse INPUT
```

- `z.infer` = `z.output` = what you get **after** `.parse()` runs. Defaults applied, transforms applied, coercion done.
- `z.input` = what the raw input must satisfy **before** parse. Fields with `.default()` are optional here; `z.coerce.date()` accepts strings here but produces `Date` in output.

**The rule:** `useForm<z.input<typeof Schema>>()` for react-hook-form, `z.infer<typeof Schema>` for anything working with already-parsed data (DB rows, API responses returned to the client after server validation).

## Discriminated Unions for State

The single most impactful TS pattern for frontend:

```ts
type Query<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: T; fetchedAt: number }
  | { status: 'error'; error: Error; retryCount: number }
```

Benefits:
- Impossible states are impossible: `{ status: 'success', error: new Error() }` won't type-check.
- Exhaustive handling in switches (combined with `never` in default).
- TypeScript narrows inside `if (q.status === 'success')` so `q.data` is accessible.

## Generic Hook Typing

```ts
// useQuery — typed response
function useQuery<TData>(url: string): { data: TData | undefined; loading: boolean } { /* ... */ }
const { data } = useQuery<User>('/api/me')

// useMutation — TData, TError, TVariables
function useMutation<TData, TError, TVariables>(
  fn: (vars: TVariables) => Promise<TData>
): { mutate: (vars: TVariables) => void; data?: TData; error?: TError } { /* ... */ }

const { mutate } = useMutation<User, ApiError, { email: string }>(
  (vars) => api.createUser(vars)
)
```

When wrapping `@tanstack/react-query`, the library already handles this — don't re-type. See references/integrations.md.

## Template Literal Types for Routes

```ts
type HttpMethod = 'GET' | 'POST' | 'PATCH' | 'DELETE'
type ApiPath   = `/api/${string}`
type Endpoint  = `${HttpMethod} ${ApiPath}`

function request(endpoint: Endpoint): Promise<Response> { /* ... */ }
request('GET /api/users')   // ok
request('FOO /api/users')   // error
```

## `as const` — the Enum Alternative

```ts
export const STAGES = ['idea', 'pre_revenue', 'early', 'growth', 'scale'] as const
export type Stage = typeof STAGES[number]
```

Why not `enum`?
- `enum` has runtime behavior (generates an object).
- `enum` values can't be used in template literal types.
- `const enum` is banned by `isolatedModules` and `verbatimModuleSyntax`.
- `as const` arrays are erased, literal-typed, and play nicely with `zod.enum(STAGES)`.

## Vite + React tsconfig Reference

```jsonc
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",      // the Vite/esbuild lookup mode
    "jsx": "react-jsx",                  // automatic JSX runtime
    "strict": true,
    "noUncheckedIndexedAccess": true,    // arr[0] is T | undefined — the correct default
    "noFallthroughCasesInSwitch": true,
    "isolatedModules": true,             // every file must be independently transpilable
    "verbatimModuleSyntax": true,        // forces `import type` for type-only imports
    "esModuleInterop": true,
    "resolveJsonModule": true,
    "skipLibCheck": true,
    "allowSyntheticDefaultImports": true,
    "forceConsistentCasingInFileNames": true,
    "noEmit": true
  },
  "include": ["src"]
}
```

Why each flag:
- `moduleResolution: "bundler"` — lets you omit `.js` extensions on relative imports (Vite/esbuild resolves them). The Node ESM `nodenext` mode forces extensions; bundler mode does not.
- `isolatedModules` — required when a bundler transpiles each file independently (Vite/esbuild/swc). Disallows const enums, non-exported ambient consts, and certain re-exports.
- `verbatimModuleSyntax` — replaced `importsNotUsedAsValues` and `preserveValueImports`. Simple rule: anything with `type` is erased, anything without is kept. Forces you to write `import type { Foo }` when Foo is only used in type positions. Keeps tree-shaking honest.
- `noUncheckedIndexedAccess` — the single most impactful strict flag after `strict: true`. Makes `arr[i]` and `obj[key]` return `T | undefined`.

## Branded Types for IDs

```ts
type Brand<T, B> = T & { readonly __brand: B }
type OrgId     = Brand<string, 'OrgId'>
type VentureId = Brand<string, 'VentureId'>

function asOrgId(s: string): OrgId { return s as OrgId }

function loadVenture(orgId: OrgId, ventureId: VentureId) { /* ... */ }
// loadVenture(ventureId, orgId) — type error, can't swap
```

EOS should adopt this for `orgId`/`userId`/`ventureId`/`skillId` to prevent accidental argument swaps.

---

# Updated Anti-Pattern Notes (Frontend)

- **`React.FC`** — breaks generics, implicit `children`, no benefit. Never use.
- **Over-typing internals** — annotating every local `const` hurts refactor ergonomics. Let inference work.
- **Under-typing boundaries** — exported functions without return types cause cascading `any`. Always annotate exported return types.
- **`as any`** — it's the nuclear option. Use `unknown` + narrowing, or Zod at the boundary.
- **`@ts-ignore` without a comment** — if you must suppress, use `@ts-expect-error` with a reason. `@ts-expect-error` fails if the error goes away, preventing stale suppressions.
- **Non-null assertion (`foo!`) in hot paths** — defer to `if (!foo) throw` at the top, then inference handles the rest.
- **`{}` as a type** — means "anything non-null/undefined", not "empty object". Use `Record<string, never>` for truly empty, or `object` for object-ish.
- **Re-declaring Zod-derived types** — if you have a schema, use `z.infer`. Having both a hand-written type and a schema guarantees they will drift.

See references/anti_patterns.md for the full list with before/after code.
