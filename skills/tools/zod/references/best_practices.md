# Zod — Best Practices (Creator-Level, 19 Sections)

Last researched: 2026-04-06
Target: `zod@3.x` (primary), Zod 4 awareness
Primary source: https://zod.dev
Secondary sources: https://github.com/colinhacks/zod, Total TypeScript
(Matt Pocock) Zod patterns, React Hook Form resolvers docs,
drizzle-zod docs.

---

## Authentication

**Not applicable — Zod is a library, not a service.** No keys, no
OAuth, no network calls. It runs entirely inside your JS runtime.

The **schema-based auth analogue**: Zod validates the shape of
decoded credentials (JWTs, API keys, signed URLs) AFTER the
cryptographic verification step. Order matters:

1. `jwt.verify(token, secret)` — proves the token was signed by
   your key. Returns `string | JwtPayload` (TS is loose here).
2. `JwtClaimsSchema.parse(decoded)` — proves the payload is the
   shape you expect. Returns a strict `JwtClaims`.

Skipping step 2 means your handlers trust `JwtPayload` and the
type system can't help you. Always schema-parse decoded claims.

**Where "secrets" live in EOS:** Zod itself has none. The analogue
is that the `EnvSchema` in `src/lib/env.ts` validates EVERY secret
the app needs (JWT_SECRET, DATABASE_URL, STRIPE_SECRET_KEY) at
boot. If a secret is missing or the wrong shape, the process
exits with code 1 before handling any request. This is the single
most valuable use of Zod in EOS.

---

## Core Operations with Exact Signatures

Zod's "operations" are schema constructors and methods. Exact
signatures (from `node_modules/zod/lib/types.d.ts` at 3.23+):

### Primitives

```ts
z.string(params?: RawCreateParams): ZodString
z.number(params?: RawCreateParams): ZodNumber
z.bigint(params?: RawCreateParams): ZodBigInt
z.boolean(params?: RawCreateParams): ZodBoolean
z.date(params?: RawCreateParams): ZodDate
z.undefined(): ZodUndefined
z.null(): ZodNull
z.any(): ZodAny
z.unknown(): ZodUnknown
z.never(): ZodNever
z.void(): ZodVoid
z.literal<T>(value: T): ZodLiteral<T>
z.enum<U extends [string, ...string[]]>(values: U): ZodEnum<U>
z.nativeEnum<T extends EnumLike>(values: T): ZodNativeEnum<T>
```

### String refinements (chainable, return ZodString)

```ts
.min(n, msg?)   .max(n, msg?)   .length(n, msg?)
.email(msg?)    .url(msg?)      .uuid(msg?)
.cuid(msg?)     .cuid2(msg?)    .ulid(msg?)
.regex(re, msg?) .includes(s, opts?) .startsWith(s, msg?)
.endsWith(s, msg?) .datetime(opts?) .ip(opts?) .emoji(msg?)
.trim() .toLowerCase() .toUpperCase()
.nonempty(msg?) // alias for .min(1)
```

### Number refinements

```ts
.gt(n) .gte(n) .lt(n) .lte(n)
.int() .positive() .nonnegative() .negative() .nonpositive()
.multipleOf(n) .finite() .safe()
```

### Object

```ts
z.object<T extends ZodRawShape>(shape: T): ZodObject<T, "strip">

// Instance methods:
.shape                             // the raw shape
.keyof()                           // ZodEnum of keys
.extend(shape)                     // add fields
.merge(otherObject)                // merge two objects
.pick({ a: true, b: true })        // keep only these
.omit({ c: true })                 // remove these
.partial()                         // all fields optional
.partial({ a: true })              // only a optional
.deepPartial()                     // recursive partial
.required()                        // all fields required
.passthrough()                     // keep unknown keys
.strict()                          // error on unknown keys
.strip()                           // drop unknown keys (default)
.catchall(schema)                  // schema for unknown keys
```

### Arrays / tuples / records / maps / sets

```ts
z.array(schema).min(n).max(n).length(n).nonempty()
z.tuple([s1, s2, s3]).rest(schema)  // variadic tail
z.record(keySchema?, valueSchema)
z.map(keySchema, valueSchema)
z.set(schema).min(n).max(n).size(n).nonempty()
```

### Unions

```ts
z.union([a, b, c])                 // tries each; first success wins
z.discriminatedUnion("kind", [      // faster, better errors
  z.object({ kind: z.literal("a"), ... }),
  z.object({ kind: z.literal("b"), ... }),
])
z.intersection(a, b)                // allOf — both must pass
a.and(b)                            // equivalent
a.or(b)                             // equivalent to z.union
```

### Refinements / transforms / defaults

```ts
schema.refine(
  check: (val: T) => boolean | Promise<boolean>,
  params?: string | { message?: string; path?: (string|number)[] }
): ZodEffects<schema>

schema.superRefine(
  check: (val: T, ctx: RefinementCtx) => void | Promise<void>
): ZodEffects<schema>

schema.transform<U>(fn: (val: T, ctx: RefinementCtx) => U | Promise<U>)
  : ZodEffects<schema, U, input<schema>>

schema.default(value | () => value)
schema.catch(value | () => value)    // replaces errors with a fallback
schema.optional()                     // T | undefined
schema.nullable()                     // T | null
schema.nullish()                      // T | null | undefined
schema.preprocess(fn, schema)         // run fn BEFORE parsing
schema.pipe(nextSchema)               // chain schemas: A → B
schema.brand<"Name">()                // nominal type
schema.readonly()                     // mark output as readonly
```

### Parse methods

```ts
schema.parse(data: unknown): T                          // throws ZodError
schema.safeParse(data: unknown):
  { success: true; data: T } | { success: false; error: ZodError }
schema.parseAsync(data: unknown): Promise<T>
schema.safeParseAsync(data: unknown): Promise<
  { success: true; data: T } | { success: false; error: ZodError }>
```

### Type inference helpers

```ts
z.infer<typeof schema>    // === z.output<typeof schema>
z.input<typeof schema>    // type ACCEPTED by parse (before transforms)
z.output<typeof schema>   // type RETURNED by parse (after transforms)
```

---

## Pagination Patterns

Zod doesn't paginate — servers do. Zod's job is to model the
response shape consistently. The canonical EOS pattern:

```ts
export function paginated<T extends z.ZodTypeAny>(item: T) {
  return z.object({
    items: z.array(item),
    nextCursor: z.string().nullable(),
    total: z.number().int().nonnegative(),
  });
}

export const UserListResponseSchema = paginated(UserSchema);
export type UserListResponse = z.infer<typeof UserListResponseSchema>;
```

`paginated` is a generic factory — `T extends z.ZodTypeAny` keeps
the inner item type fully inferred. This produces a single shared
shape for every paginated endpoint in the app.

For offset/limit APIs:

```ts
export function offsetPaginated<T extends z.ZodTypeAny>(item: T) {
  return z.object({
    items: z.array(item),
    offset: z.number().int().nonnegative(),
    limit: z.number().int().positive(),
    total: z.number().int().nonnegative(),
  });
}
```

Common pitfall: modeling `nextCursor` as `z.string().optional()`
instead of `z.string().nullable()`. Most APIs return `null` (JSON
distinguishes missing from null). `.nullable()` matches the wire
format. `.nullish()` accepts both.

---

## Rate Limits

**Not applicable in the traditional sense — Zod has no external
rate limits.** But schema validation has a **CPU cost**:

- **Synchronous refines are cheap** — microseconds per refine on
  small objects.
- **Async refines on every keystroke are expensive.** Debounce
  them. The async refine pattern (unique-username check) should
  fire onBlur or with a 300ms+ debounce, never on every render.
- **Large union parsing is O(n × schema_size).** `z.union([A, B, C,
  ..., Z])` tries each in order on every parse. If you have a
  discriminator field, use `z.discriminatedUnion("type", [...])`
  instead — it jumps directly to the matching schema in O(1).
- **Deeply nested `.deepPartial()` traversal** allocates a new
  schema tree every call. Cache the result in a module-level
  constant, not inside a function.

**Rule:** parse at boundaries, not in tight loops. If you find
yourself calling `schema.parse` inside a `.map()` over 10k items,
something is architecturally wrong — parse the outer array once.

---

## Error Codes and Recovery

Zod errors are `ZodError` instances with a structured `issues`
array. Every issue is a `ZodIssue` discriminated by `code`:

```ts
ZodIssueCode =
  | "invalid_type"           // wrong type (e.g., string where number expected)
  | "invalid_literal"        // z.literal mismatch
  | "custom"                 // refine/superRefine addIssue
  | "invalid_union"          // z.union — no branch matched
  | "invalid_union_discriminator"  // discriminatedUnion tag missing
  | "invalid_enum_value"     // z.enum mismatch
  | "unrecognized_keys"      // .strict() saw unknown keys
  | "invalid_arguments"      // function arg validation (z.function)
  | "invalid_return_type"    // function return validation
  | "invalid_date"           // z.date got an Invalid Date
  | "invalid_string"         // .email/.url/.uuid/.regex failed
  | "too_small"              // .min / .gt / .gte
  | "too_big"                // .max / .lt / .lte
  | "invalid_intersection_types"
  | "not_multiple_of"
  | "not_finite"
```

Each issue includes:

```ts
{
  code: ZodIssueCode,
  path: (string | number)[],   // dotted path to the offending field
  message: string,
}
```

### Three error consumption methods

```ts
// 1. Raw issues — for logging / custom handling
error.issues
// [{ code: "too_small", path: ["password"], minimum: 8, ... }]

// 2. .flatten() — perfect for form errors / RHF / JSON APIs
error.flatten()
// {
//   formErrors: string[],
//   fieldErrors: { [field: string]: string[] }
// }

// 3. .format() — nested mirror of the schema shape
error.format()
// {
//   _errors: string[],
//   password: { _errors: string[] },
//   address: { street: { _errors: string[] } }
// }
```

**Recovery strategy:**
- At request boundaries: 400 with `error.flatten().fieldErrors`.
- At boot (env): log `error.flatten().fieldErrors`, exit 1.
- In LLM output parsing: catch, retry with the error message fed
  back to the LLM (self-correcting prompt loop).
- In form libs: `zodResolver` auto-converts `.flatten()` to RHF's
  errors object. Zero glue code.

**Retryable?** ZodError is never retryable — the input is wrong,
retrying with the same input yields the same error. The exception
is LLM output: retry with the error as prompt context.

---

## SDK Idioms

### Import style

```ts
import { z } from "zod";                   // canonical
import { z, ZodError, ZodType } from "zod"; // for type guards
```

Avoid `import * as z from "zod"` unless your `moduleResolution`
is old enough to need it. The modern default `import { z }` works
under `"bundler"` and `"nodenext"`.

### Schema composition idiom

```ts
// Author once, compose everywhere.
const Base = z.object({ id: z.string().uuid(), createdAt: z.coerce.date() });
const User = Base.extend({ email: z.string().email(), name: z.string() });
const UserCreateInput = User.omit({ id: true, createdAt: true });
const UserPatch = User.partial().omit({ id: true, createdAt: true });
```

This is the idiomatic alternative to repeating object shapes.

### Type-exporting idiom

```ts
// Always export the inferred type alongside the schema.
export const UserSchema = z.object({ ... });
export type User = z.infer<typeof UserSchema>;

// For schemas with transforms, export both.
export type UserInput = z.input<typeof UserSchema>;
export type UserOutput = z.output<typeof UserSchema>;
```

### Async idiom

```ts
// If ANY refine/transform in the tree is async, use safeParseAsync.
const result = await schema.safeParseAsync(input);
// Using .safeParse instead throws "Synchronous parse encountered Promise".
```

### Error handling idiom

```ts
// Don't try/catch parse — use safeParse.
const result = Schema.safeParse(input);
if (!result.success) {
  return handleError(result.error);
}
const data = result.data; // fully typed
```

### RHF idiom

```ts
const form = useForm<z.infer<typeof Schema>>({
  resolver: zodResolver(Schema),
  defaultValues: { email: "", password: "" },
  mode: "onBlur",
});
```

### Drizzle bridge idiom

```ts
import { createInsertSchema, createSelectSchema } from "drizzle-zod";
import { users } from "./db/schema";

export const UserInsertSchema = createInsertSchema(users, {
  email: (s) => s.email(),
  name: (s) => s.min(1).max(255),
});
export const UserSelectSchema = createSelectSchema(users);
```

---

## Anti-Patterns

1. **`parse` at a request boundary.**
   ```ts
   // WRONG — throws ZodError, becomes a 500
   app.post("/login", (req, res) => {
     const { email, password } = LoginSchema.parse(req.body);
   });
   // RIGHT
   app.post("/login", (req, res) => {
     const result = LoginSchema.safeParse(req.body);
     if (!result.success) {
       return res.status(400).json({ errors: result.error.flatten().fieldErrors });
     }
     const { email, password } = result.data;
   });
   ```

2. **`z.coerce.number()` on user input without `.finite()`.**
   ```ts
   // WRONG — "123abc" → NaN, passes validation
   const Schema = z.object({ age: z.coerce.number() });
   // RIGHT
   const Schema = z.object({ age: z.coerce.number().int().nonnegative().finite() });
   ```

3. **Re-declaring the TypeScript type separately from the schema.**
   ```ts
   // WRONG — two sources of truth, guaranteed drift
   interface User { id: string; email: string; }
   const UserSchema = z.object({ id: z.string(), email: z.string() });
   // RIGHT
   const UserSchema = z.object({ id: z.string().uuid(), email: z.string().email() });
   type User = z.infer<typeof UserSchema>;
   ```

4. **Async refine on every keystroke.**
   ```ts
   // WRONG — fires a network request on every onChange
   const Schema = z.object({
     username: z.string().refine(async (u) => !(await exists(u)), "Taken"),
   });
   // + useForm({ mode: "onChange" })
   // RIGHT — fire on blur with a debounced check, or validate on submit only
   ```

5. **`.partial()` for PATCH endpoints without re-asserting invariants.**

6. **Refine on parent that belongs on a child field.**
   ```ts
   // WRONG — error shows as form-level, not on the field
   const Schema = z.object({ password: z.string(), confirm: z.string() })
     .refine((o) => o.password === o.confirm, "Mismatch");
   // RIGHT — attach to the child via superRefine + path
   const Schema = z.object({ password: z.string(), confirm: z.string() })
     .superRefine((val, ctx) => {
       if (val.password !== val.confirm) {
         ctx.addIssue({
           code: z.ZodIssueCode.custom,
           path: ["confirm"],
           message: "Passwords must match",
         });
       }
     });
   ```

7. **`z.any()` / `z.unknown()` as laziness.** Using `z.any()` to
   "get it working" defeats the entire purpose of Zod. Prefer
   `z.unknown()` (forces you to narrow) or model the real shape.

---

## Data Model

Zod's "data model" is its schema type hierarchy:

```
ZodType<Output, Def, Input>
├── ZodString, ZodNumber, ZodBigInt, ZodBoolean, ZodDate
├── ZodUndefined, ZodNull, ZodAny, ZodUnknown, ZodNever, ZodVoid
├── ZodLiteral, ZodEnum, ZodNativeEnum
├── ZodArray, ZodTuple, ZodRecord, ZodMap, ZodSet
├── ZodObject (with shape, passthrough/strict/strip modes)
├── ZodUnion, ZodDiscriminatedUnion, ZodIntersection
├── ZodOptional, ZodNullable
├── ZodEffects (refine/transform/superRefine wrap the inner)
├── ZodDefault, ZodCatch, ZodBranded, ZodReadonly
├── ZodPipeline (pipe)
├── ZodLazy (recursive self-reference)
├── ZodPromise, ZodFunction
```

Every constructor returns a subclass of `ZodType`. Chainable
methods return a wrapped schema (refine → `ZodEffects`, optional →
`ZodOptional`, default → `ZodDefault`). This wrapping is why
method order matters for type inference:

```ts
z.string().optional().default("")    // output: string
z.string().default("").optional()    // output: string | undefined
```

Object modes:
- `.strip()` (default) — drops unknown keys silently.
- `.strict()` — throws `unrecognized_keys` on unknown keys.
- `.passthrough()` — keeps unknown keys in the output.
- `.catchall(schema)` — validates unknown keys against a schema.

---

## Webhooks and Events

**Not applicable — Zod is a library.** But Zod is the RIGHT tool
for validating webhook payloads FROM other services. The canonical
EOS pattern for a webhook receiver:

```ts
// 1. Verify signature (service-specific — Stripe, GitHub, etc.)
const event = stripe.webhooks.constructEvent(rawBody, sig, secret);
// 2. Parse the decoded payload through a Zod schema
const result = StripeEventSchema.safeParse(event);
if (!result.success) {
  // Log and ack — do NOT 400; webhook senders will retry forever.
  logger.error("Unexpected webhook shape", result.error.flatten());
  return res.sendStatus(200);
}
// 3. Handle the typed event
switch (result.data.type) { ... }
```

Key insight: **always ack webhooks (200), even on shape errors.**
400s trigger retry storms. Log + 200 + investigate.

For dispatching internal events, `z.discriminatedUnion` on a `type`
field is the canonical pattern.

---

## Limits

Zod has no API quotas. The practical limits to be aware of:

- **Object key count.** No hard limit, but `ZodObject` builds a TS
  type with every key. The TypeScript compiler slows down around
  200+ keys in a single object. Compose instead.
- **Union branch count.** `z.union` tries each branch in order.
  Past ~20 branches, prefer `z.discriminatedUnion`.
- **Recursion depth.** TS has a recursion limit (~50 levels).
  Recursive schemas via `z.lazy` need a type annotation:
  ```ts
  type Category = { name: string; sub: Category[] };
  const Category: z.ZodType<Category> = z.lazy(() =>
    z.object({ name: z.string(), sub: z.array(Category) })
  );
  ```
- **String length.** No built-in max. Enforce with `.max(n)`.
  For untrusted input, ALWAYS set `.max()` to prevent DoS via
  giant strings (1GB JSON body → 1GB validated string).
- **Error issue count.** `.flatten()` includes ALL issues, not
  just the first. A bad input can produce hundreds. At API
  boundaries, consider truncating.

---

## Cost Model

Zod is free, open-source, MIT-licensed. The "cost" is:

- **Bundle size.** `zod@3.23` is ~13KB min+gzip as a dependency.
  Tree-shaking is limited because most users import `{ z }` and
  touch the entire namespace. Zod 4 introduces `@zod/mini` which
  is smaller and fully tree-shakeable at the cost of a slightly
  different API surface.
- **Runtime CPU.** Parsing a typical object (5-10 fields) is
  microseconds. Async refines add a network round trip. Don't
  parse the same value twice; cache if the schema is a pure
  function of the input.
- **TypeScript compile time.** Zod types are recursive and can
  slow down the compiler on very large schemas (100+ fields in a
  single object, or deeply nested generics). Split into smaller
  schemas composed with `.extend`/`.merge`.
- **Developer time saved.** The real "cost model" is that Zod
  pays for itself by eliminating type/runtime drift. A shared
  schema across client and server is worth more than 13KB.

---

## Version Pinning

- **Current stable (EOS):** `zod@3.23.x` (3.24 is backwards-compatible).
- **Zod 4:** released mid-2025 alongside Zod 3 maintenance. Major
  API shift in places but ~95% backward compatible. Not the EOS
  default yet.
- **Pin in package.json:**
  ```json
  "dependencies": {
    "zod": "^3.23.8"
  }
  ```
- **Never mix `zod@3` and `zod@4`** in the same workspace. The
  branded type identities differ — a schema produced by one cannot
  be passed to a resolver from the other without `as any` casts
  that defeat the point.
- **Peer packages that depend on Zod:**
  - `@hookform/resolvers` — tracks Zod 3 and Zod 4 via separate
    entry points.
  - `drizzle-zod` — pins to a specific Zod major.
  - Any tRPC or Hono usage — audit before upgrading.
- **Deprecation signals in Zod 3 → 4:**
  - `z.string().email()` → `z.email()` at top level.
  - `.refine({ message })` → `.refine({ error })` in some paths.
  - Stricter `z.date()` (no longer coerces strings implicitly).
  - `z.record(value)` without a key schema is deprecated — use
    `z.record(z.string(), value)`.

---

# Tier 2 — Creator Intelligence (Sections 13-19)

---

## Design Intent and Tradeoffs

Colin McDonnell built Zod to solve one specific pain: **"TypeScript
interfaces don't exist at runtime, and every validation library
forces you to declare your type twice."** Joi, Yup, io-ts, ajv —
all of them require either a JSON Schema + a TS interface, or a
validator + a TS interface, or a class with decorators. Zod said:
write the validator and the type falls out.

**Core design decisions:**

1. **Schema = type.** `z.infer<typeof S>` is the whole product.
   This single design choice is why Zod dominated: no drift.
2. **Parse, don't validate.** Borrowing from Alexis King's essay
   "Parse, Don't Validate," Zod pushes the boundary at which
   `unknown` becomes `T` to a single explicit call. You never
   have "validated but still untyped" data.
3. **Immutable, chainable API.** Every method returns a new
   schema. You can safely extend `BaseSchema` in 10 places
   without any of them affecting each other.
4. **No codegen.** Unlike tRPC's output or OpenAPI-to-TS,
   Zod produces types at the TS level directly. No build step,
   no watch task.
5. **Runtime-first, docs-last.** The library should Just Work at
   runtime and the docs can catch up. This is why zod.dev is a
   single long page — it's the README rendered as a website.

**Tradeoffs consciously made:**

- **Verbosity over brevity.** `z.string().email().min(5)` is longer
  than `string().email().min(5)` would be. Explicit namespace for
  clarity and IDE autocomplete.
- **Runtime cost over zero-cost.** Unlike ts-pattern or pure TS
  utilities, Zod has runtime cost. Tradeoff: runtime safety.
- **No code generation.** You can't generate OpenAPI from a Zod
  schema without a 3rd-party library. That's not Zod's job.
- **Single-package design.** Everything is in `zod`. Zod 4's
  `@zod/mini` is a concession to tree-shaking.

**What Zod is NOT:**
- Not a form library. RHF and others USE Zod.
- Not an ORM. drizzle-zod bridges.
- Not a JSON Schema library. `zod-to-json-schema` exists separately.
- Not OpenAPI. Use `zod-openapi` or similar.

---

## Problem-Solution Map and Hidden Capabilities

**Stated problem:** validate unknown data at runtime.
**Actual problem Zod solves:** eliminate the drift between runtime
validation and static TypeScript types across a codebase.

**Hidden capabilities most users miss:**

1. **`.pipe()` for multi-stage parsing.** Chain a string parser
   into a number parser: `z.string().regex(/^\d+$/).pipe(z.coerce.number().int())`.
   The first stage validates shape, the second transforms + re-validates.
2. **`.preprocess()` for legacy data.** Runs a function BEFORE
   parsing. Useful for normalizing gnarly input:
   `z.preprocess((v) => (v === "" ? undefined : v), z.string().optional())`
   converts empty strings from HTML forms to `undefined`.
3. **`.catch()` for graceful fallbacks.** `z.string().catch("default")`
   never fails — returns `"default"` on any parse error. Use for
   LLM outputs where a fallback is better than an exception.
4. **`z.function()` for validated function signatures.**
   `z.function().args(z.string(), z.number()).returns(z.boolean())`
   produces a runtime-validated wrapper.
5. **Recursive schemas with `z.lazy` + a type annotation.**
6. **`.brand()` for phantom types.** Free nominal typing without
   runtime cost.
7. **`z.ZodType<...>` as a generic constraint.** Lets you write
   factories like `paginated<T extends z.ZodTypeAny>(item: T)`.
8. **`schema._def`** gives you access to the internal definition.
   Useful for building a schema introspector.
9. **Error maps.** `z.setErrorMap(customMap)` lets you i18n all
   errors without touching individual `.refine` calls.
10. **`z.NEVER`** — used in `superRefine` to short-circuit:
    `ctx.addIssue(...); return z.NEVER;`.

**Non-obvious compositions:**

- **Schema + `.refine` + `.transform` chain.** Validate shape,
  then cross-field rules, then normalize the output.
- **`z.object({ ... }).strict().brand<"ApiRequest">()`** — strict
  mode for unknown-key detection + branding.
- **Discriminated unions with branded discriminators.**

---

## Operational Behavior and Edge Cases

**Behavioral quirks:**

1. **`z.coerce.date()` accepts `Invalid Date`.** `new Date("abc")`
   returns an Invalid Date. Add `.refine((d) => !isNaN(d.getTime()),
   "Invalid date")`.
2. **`z.coerce.boolean()` is surprising.** It calls `Boolean(input)`.
   `Boolean("false")` is `true` (non-empty string). Use
   `z.preprocess((v) => v === "true" || v === true, z.boolean())`.
3. **`.default()` + `.optional()` ordering matters.**
   `.optional().default(v)` — default fires when input is undefined.
   `.default(v).optional()` — optional wrapper means output can be undefined.
4. **`.transform()` type is `(val: T) => U`** — returning a Promise
   forces parseAsync. No warning at build time; runtime error only.
5. **`.refine` does NOT narrow the output type** in Zod 3. Zod 4
   changes this.
6. **Object `.strict()` error is not field-level.** It produces
   an `unrecognized_keys` issue with the key list.
7. **`z.record(z.string(), z.number())` requires BOTH args in Zod
   4.** Single-arg `z.record(value)` is deprecated.
8. **Inferring types through `z.lazy` without annotation** produces
   `any`. You MUST write `const Foo: z.ZodType<Foo> = z.lazy(...)`.
9. **`.partial()` is shallow.** Use `.deepPartial()` for recursive
   partial.
10. **`z.enum` values must be a const array**, not a computed one.

**Silent-failure modes:**

- **Missing `.finite()`** on coerced numbers lets NaN through.
- **`.passthrough()`** silently keeps unknown keys — they enter
  the output but are not typed.
- **Transforms that throw** become runtime exceptions, not
  ZodErrors. Wrap untrusted transform logic or use `.catch()`.

---

## Ecosystem Position and Composition

Zod sits at **every trust boundary** in a modern TypeScript stack.

```
┌─────────────────────── Client ───────────────────────┐
│ React Hook Form ← zodResolver(Schema) ← src/schemas/ │
│ React Query mutate/query parses with shared schema   │
└───────────────────────┬──────────────────────────────┘
                        │  shared schema
┌───────────────────────┴──────────────────────────────┐
│ Express middleware ← safeParse(req.body) ← src/schemas/
│ Drizzle ORM       ← createInsertSchema(users)        │
└──────────────────────────────────────────────────────┘
                        │
                        ↓ process.env
                  EnvSchema.parse(...) at app boot
```

**Natural complements:**
- **React Hook Form** — canonical form integration.
- **shadcn/ui `<Form>`** — reads RHF errors, maps to `<FormMessage>`.
- **React Query** — parses responses in `queryFn`/`mutationFn`.
- **Drizzle ORM** — `drizzle-zod` bridges table → schema.
- **tRPC** — uses Zod as default input validator.
- **Hono** — `@hono/zod-validator` middleware.
- **Next.js** — Server Actions accept Zod schemas via formData.
- **zod-to-openapi** — generates OpenAPI specs from schemas.
- **Valibot / ArkType** — competitors with smaller bundles but
  smaller ecosystems.

**Forced integrations (avoid):**
- **Zod + Mongoose.** Two schema systems fighting.
- **Zod + class-validator.** Decorator approach conflicts with
  schema-first thinking.
- **Manual validation + Zod.** Zod is the full stack.

**Integration anti-patterns:**
- Validating the same data twice with different schemas.
- Parsing in the render path of a React component. Parse at
  boundaries, not in `useMemo`.

---

## Trajectory and Evolution

**Where Zod is heading:**

1. **Zod 4 is the focus.** Released mid-2025. Key goals:
   - **Smaller bundle** (13KB → significantly less).
   - **Faster parsing** (reported ~3x improvements on some paths).
   - **`@zod/mini`** — a tree-shakeable subset.
   - **Stricter error model.**
   - **Better type inference for refines** — refines can narrow.
   - **Top-level string helpers** — `z.email()`, `z.url()`, `z.uuid()`.
2. **Zod 3 maintenance continues** in parallel.
3. **Deepening AI integration.** Zod is the de facto standard for
   validating LLM JSON outputs. Expect more official tooling.
4. **Registry / metadata system.** Zod 4 adds a way to attach
   arbitrary metadata to schemas — unlocking better OpenAPI
   generation and form builders.

**Dead-end signals:**
- `z.function()` is de-emphasized.
- `.deepPartial()` is being reconsidered — may change in Zod 4.
- Single-argument `z.record(value)` is deprecated in Zod 4.
- `z.string().email()` etc. supported but top-level preferred.

**What to adopt early:**
- Top-level `z.email()`, `z.url()`, `z.uuid()` style (Zod 4).
- `@zod/mini` when bundle size matters.
- LLM output parsing with `.catch()` for fallbacks.

**EOS posture:** stay on Zod 3.23+ until a coordinated migration.
The ecosystem (RHF, drizzle-zod, resolvers) needs to be ready
simultaneously.

---

## Conceptual Model and Solution Recipes

**The Zod mental model in one sentence:**
> A schema is a parser from `unknown` to `T`, and the type falls
> out of the parser definition.

**Primitives:** schemas, methods, type helpers.
**Verbs:** define, infer, parse, compose, narrow, transform,
handle errors.

### Recipe 1: Full-stack form with shared validation

```
1. Author LoginSchema in src/schemas/auth.ts
2. Client: useForm({ resolver: zodResolver(LoginSchema) })
3. On submit: POST /api/login with validated values
4. Server: LoginSchema.safeParse(req.body) in middleware
5. On failure: 400 with error.flatten().fieldErrors
6. On success: process the typed login attempt
7. Server response parsed by a separate LoginResponseSchema
```

### Recipe 2: Fail-fast env parsing

```
1. Author EnvSchema in src/lib/env.ts with every required key
2. Call EnvSchema.safeParse(process.env) at module top level
3. On failure: console.error(flatten().fieldErrors); process.exit(1)
4. Export env.data as `env` — now every import is typed
5. Never reference process.env elsewhere — always `env`
```

### Recipe 3: LLM JSON output parsing with self-correction

```
1. Author OutputSchema matching the expected LLM shape
2. Call LLM with a prompt that includes the schema
3. const result = OutputSchema.safeParse(JSON.parse(llmText))
4. On failure: re-prompt with the error as context
5. Cap retries at 3; after 3, fall back to .catch() default
```

### Recipe 4: Drizzle insert with extended validation

```
1. Define Drizzle table: users
2. Generate base schema: createInsertSchema(users)
3. Extend with business rules: .extend({ email: z.string().email() })
4. Use as the body parser for POST /users
5. On parse success, forward to db.insert(users).values(data)
```

### Recipe 5: Typed query string state

```
1. Define SearchParamsSchema with z.coerce for number/date params
2. On route change, SearchParamsSchema.safeParse(searchParams)
3. Render state from the parsed, typed result
```

---

## Industry Expert and Cutting-Edge Usage

**How top practitioners use Zod in 2025-2026:**

1. **Matt Pocock (Total TypeScript) — `z.infer` as the single
   source of truth pattern.** Every DTO starts as a schema.
2. **Theo (t3.gg / Ping) — Zod for tRPC router inputs.** Every
   tRPC procedure takes a Zod schema as `.input(Schema)`. The EOS
   equivalent is validated Express middleware.
3. **Vercel AI SDK — `streamObject({ schema: ZodSchema })`.** The
   AI SDK streams LLM output AND validates it against a Zod
   schema in real time. Structured LLM output with runtime
   guarantees.
4. **Colin McDonnell himself — `.catch()` for resilient LLM
   parsing.** Production LLM pipelines use this.
5. **OpenAI and Anthropic tool-use patterns.** Both SDKs accept
   Zod schemas as tool parameter definitions. The schema becomes
   the JSON Schema sent to the model AND the validator for the
   model's response.
6. **Form builders from schemas.** `@autoform/react` consumes a
   Zod schema and generates a form UI.
7. **Server Actions in Next.js 15** — Zod is the default form
   validator.
8. **Shared schemas across microservices.** Instead of OpenAPI or
   Protobuf, teams publish `@company/schemas` packages.
9. **Schema-first API testing.** Contract tests parse API
   responses with the same schema the client uses.
10. **Zod + React Query + shared schemas — the "trifecta".** The
    EOS default. Every query result is runtime-validated AND
    typed. The client can never crash on unexpected API shapes.

**Frontier patterns:**

- **Streaming parse.** Parse JSON as it streams in (LLM token
  streams).
- **Schema diffing for backwards compatibility.** Compare two
  versions of a schema to detect breaking changes in CI.
- **LLM-generated schemas.** Ask an LLM to write a Zod schema
  from a natural-language description.

**The creator-level insight:**

Zod's real power is not validation. It's that **the schema becomes
the only thing you have to maintain.** Types, validation, form
structure, API contracts, OpenAPI specs, form UIs — all derived.
When everything flows from the schema, changing the schema
propagates everywhere at compile time. Teams that internalize
this ship faster and break less.
