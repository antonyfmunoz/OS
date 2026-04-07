---
name: zod
description: "Use when defining, composing, or debugging Zod schemas for form validation, API input/output parsing, env variable parsing, or TypeScript type inference — writing z.object/z.union/z.discriminatedUnion/z.record/z.tuple, wiring zodResolver into React Hook Form + shadcn <Form>, validating Express request bodies via safeParse middleware, bridging Drizzle tables with drizzle-zod (createInsertSchema/createSelectSchema), parsing process.env at boot, using refine/superRefine/transform/brand/pipe, inferring types with z.infer / z.input / z.output, flattening ZodError with .flatten()/.format()/issues, sharing schemas across client and server, choosing parse vs safeParse vs parseAsync, or diagnosing z.coerce surprises and Zod 3→4 migration issues."
allowed-tools: "Read, Write, Edit, Bash, WebFetch, WebSearch"
version: 1.0
source_url: "https://zod.dev"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "3.x"
sdk_version: "zod@3"
speed_category: fast
trigger: both
effort: high
context: fork
---

# Tool: Zod

Zod is the TypeScript-first schema validation library that sits at every
trust boundary in the EOS SaaS stack. Every place runtime data meets
the type system — form submissions, Express request bodies, Express
responses, env vars at boot, LLM JSON outputs, Drizzle rows crossing
the wire — is a place where Zod parses, narrows, and produces a fully
typed value.

It was built by Colin McDonnell (@colinhacks) with one non-negotiable
design goal: **the schema IS the type.** You never declare a TypeScript
interface separately. You write `z.object({...})` once and derive the
type with `z.infer<typeof schema>`. This eliminates the drift between
runtime validators and static types that plagues every other
validation library (Joi, Yup, class-validator).

This skill exists so agents working in `/opt/OS/saas` use Zod the way
Colin designed it — schema-first, parse at boundaries, infer
everywhere, never hand-roll a TypeScript type that a schema could
produce.

## What This Tool Does

Zod is a **parser, not a validator**. The distinction matters:

- A **validator** says yes/no to an `unknown` input and leaves you to
  cast it. The type system is not involved.
- A **parser** takes `unknown` in and returns a typed value out. The
  return type of `schema.parse(data)` is the schema's inferred type.
  You move from `unknown` to `T` with runtime proof.

Core capabilities:

1. **Primitive schemas.** `z.string()`, `z.number()`, `z.bigint()`,
   `z.boolean()`, `z.date()`, `z.symbol()`, `z.undefined()`,
   `z.null()`, `z.void()`, `z.any()`, `z.unknown()`, `z.never()`.
   Each supports chainable refinements: `z.string().min(1).max(255)
   .email().trim().toLowerCase()`.
2. **Object schemas.** `z.object({ key: schema, ... })` — the
   workhorse. Supports `.partial()`, `.required()`, `.pick()`,
   `.omit()`, `.extend()`, `.merge()`, `.deepPartial()`, `.passthrough()`,
   `.strict()`, `.strip()`, `.catchall()`.
3. **Composite schemas.** `z.array()`, `z.tuple()`, `z.record()`,
   `z.map()`, `z.set()`, `z.union([...])`, `z.intersection(a, b)`,
   `z.discriminatedUnion("kind", [...])`, `z.lazy(() => ...)` (for
   recursive schemas).
4. **Refinements.** `.refine(fn, msg)` for single-field custom rules.
   `.superRefine((val, ctx) => ctx.addIssue({...}))` for cross-field
   rules or multiple errors from one check.
5. **Transforms.** `.transform(fn)` runs AFTER parsing succeeds and
   produces a different output type. This is why `z.input<T>` and
   `z.output<T>` exist — before/after the transform.
6. **Coercion.** `z.coerce.number()`, `z.coerce.string()`,
   `z.coerce.boolean()`, `z.coerce.date()` — calls `Number()`,
   `String()`, `Boolean()`, `new Date()` on input before validating.
   Useful for query strings and form data; dangerous for untrusted
   JSON.
7. **Branded types.** `.brand<"UserId">()` produces a nominal type
   `string & z.BRAND<"UserId">` that TypeScript treats as distinct
   from a plain `string`. Strongly-typed ID primitives without a
   class.
8. **Pipes.** `z.string().pipe(z.coerce.number().int().positive())` —
   chain parsers so the output of one feeds the input of the next.
9. **Error handling.** `schema.parse(data)` throws `z.ZodError` on
   failure. `schema.safeParse(data)` returns
   `{ success: true, data } | { success: false, error }`. Async
   counterparts: `parseAsync`, `safeParseAsync` (required when any
   refine/transform is async).
10. **Error formatting.** `error.issues` (raw list),
    `error.flatten()` (`{formErrors, fieldErrors}`, perfect for
    RHF), `error.format()` (nested object mirroring schema shape).

## EOS Integration

**Where Zod lives:**
- `/opt/OS/saas/*/src/schemas/` — shared schemas consumed by client
  AND server. This is the EOS convention: a schema is authored once,
  imported both places.
- `/opt/OS/saas/*/src/lib/env.ts` — `process.env` parser that runs at
  app boot. Throws on missing or malformed vars so the app fails fast
  instead of at first request.
- `/opt/OS/saas/*/src/components/**` — form components import schemas
  and pass them to `zodResolver(schema)`.
- `/opt/OS/saas/*/server/middleware/validate.ts` — Express middleware
  that takes a schema and returns a handler that `safeParse`s
  `req.body` / `req.query` / `req.params` and 400s on failure.
- `/opt/OS/saas/*/src/db/schema.ts` + `drizzle-zod` — `createInsertSchema`
  and `createSelectSchema` derive Zod schemas from Drizzle table
  definitions so inserts are validated with the same shape the
  database enforces.

**Stack partners (see references/integrations.md):**
- **TypeScript strict** — Zod's inference only works under `strict`.
- **React Hook Form** — `import { zodResolver } from
  "@hookform/resolvers/zod"`, then
  `useForm({ resolver: zodResolver(schema) })`.
- **shadcn/ui `<Form>` primitives** — read `form.formState.errors` and
  map to `<FormMessage />`. Zod's `.flatten().fieldErrors` is the
  shape RHF produces automatically.
- **Express** — validation middleware using `safeParse` on
  `req.body`/`req.query`/`req.params`.
- **React Query** — `useMutation` accepts a `z.infer<typeof schema>`
  as input and parses the response with the same schema used
  server-side.
- **Drizzle ORM** — `drizzle-zod` bridges table definitions to schemas.
- **TanStack Router / URL state** — `z.object({...}).parse(searchParams)`
  to type the query string.

**The rule:** every trust boundary gets a Zod schema. Forms, API
routes, env vars, LLM outputs, webhook payloads — if data is
`unknown`, `safeParse` it before touching it.

## Authentication

**Not applicable — Zod is a library, not a service.** There is no API
key, no account, no network call. It runs fully in your JavaScript
runtime.

The closest analogue to authentication is **schema-based token
validation** at the boundary: when a signed token (JWT, signed URL,
API key) arrives, Zod validates the decoded shape before you trust it.

```ts
import { z } from "zod";

export const JwtClaimsSchema = z.object({
  sub: z.string().uuid(),               // user id
  email: z.string().email(),
  roles: z.array(z.enum(["admin", "user", "viewer"])),
  iat: z.number().int().positive(),
  exp: z.number().int().positive(),
});
export type JwtClaims = z.infer<typeof JwtClaimsSchema>;

// in auth middleware, AFTER jwt.verify():
const decoded = jwt.verify(token, process.env.JWT_SECRET!);
const claims = JwtClaimsSchema.parse(decoded); // throws if shape is wrong
// claims is now fully typed — no `as JwtClaims` cast needed
```

This replaces the common anti-pattern of `as JwtClaims` casts after
`jwt.verify()` returns `string | JwtPayload`.

## Quick Reference

### Install

```bash
npm install zod
npm install @hookform/resolvers react-hook-form   # for form use
npm install drizzle-zod                           # for Drizzle bridge
```

### Login form schema

```ts
import { z } from "zod";

export const LoginSchema = z.object({
  email: z.string().trim().toLowerCase().email("Enter a valid email"),
  password: z
    .string()
    .min(8, "At least 8 characters")
    .max(128, "At most 128 characters"),
  remember: z.boolean().default(false),
});

export type LoginInput = z.input<typeof LoginSchema>;   // before transform
export type LoginValues = z.output<typeof LoginSchema>; // after transform
```

Note: `z.input` and `z.output` differ because `.trim().toLowerCase()`
and `.default(false)` are transforms. Input type allows
`remember?: boolean` (optional because of default). Output type is
`remember: boolean` (default applied). Use `z.infer` as a shortcut for
`z.output`.

### API response schema (shared client + server)

```ts
// src/schemas/user.ts
import { z } from "zod";

export const UserSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  name: z.string().min(1),
  createdAt: z.coerce.date(),  // accepts ISO string OR Date
  role: z.enum(["admin", "user", "viewer"]),
});
export type User = z.infer<typeof UserSchema>;

export const UserListResponseSchema = z.object({
  items: z.array(UserSchema),
  nextCursor: z.string().nullable(),
  total: z.number().int().nonnegative(),
});
export type UserListResponse = z.infer<typeof UserListResponseSchema>;
```

### Env parser (run at app boot)

```ts
// src/lib/env.ts
import { z } from "zod";

const EnvSchema = z.object({
  NODE_ENV: z.enum(["development", "test", "production"]),
  DATABASE_URL: z.string().url(),
  JWT_SECRET: z.string().min(32, "JWT_SECRET must be at least 32 chars"),
  PORT: z.coerce.number().int().positive().default(3000),
  STRIPE_SECRET_KEY: z.string().startsWith("sk_"),
  LOG_LEVEL: z.enum(["debug", "info", "warn", "error"]).default("info"),
});

const parsed = EnvSchema.safeParse(process.env);
if (!parsed.success) {
  console.error(
    "Invalid environment variables:",
    parsed.error.flatten().fieldErrors
  );
  process.exit(1);
}
export const env = parsed.data;
```

### Discriminated union (polymorphic DTO)

```ts
export const EventSchema = z.discriminatedUnion("type", [
  z.object({
    type: z.literal("user.created"),
    userId: z.string().uuid(),
    email: z.string().email(),
  }),
  z.object({
    type: z.literal("payment.succeeded"),
    paymentId: z.string(),
    amountCents: z.number().int().nonnegative(),
  }),
  z.object({
    type: z.literal("subscription.canceled"),
    subscriptionId: z.string(),
    reason: z.string().optional(),
  }),
]);
export type Event = z.infer<typeof EventSchema>;

// Exhaustiveness check for free:
function handle(e: Event) {
  switch (e.type) {
    case "user.created":         return e.email;
    case "payment.succeeded":    return e.amountCents;
    case "subscription.canceled":return e.reason;
    // TS errors if any case is missed.
  }
}
```

### Refine and superRefine

```ts
// Single-field custom rule
const StrongPassword = z.string().refine(
  (s) => /[A-Z]/.test(s) && /[0-9]/.test(s),
  { message: "Needs uppercase and a number" }
);

// Cross-field rule — must use superRefine on the parent object
const SignupSchema = z
  .object({
    password: StrongPassword,
    confirmPassword: z.string(),
  })
  .superRefine((val, ctx) => {
    if (val.password !== val.confirmPassword) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["confirmPassword"],   // attaches error to field
        message: "Passwords do not match",
      });
    }
  });
```

### Transform + brand (strongly typed IDs)

```ts
export const UserId = z.string().uuid().brand<"UserId">();
export type UserId = z.infer<typeof UserId>;

export const OrgId = z.string().uuid().brand<"OrgId">();
export type OrgId = z.infer<typeof OrgId>;

function loadUser(id: UserId) { /* ... */ }
loadUser("abc");                    // TS error — plain string
loadUser(UserId.parse("abc"));      // Runtime + type check pass together
```

### Parse vs safeParse

```ts
// parse — throws ZodError. Use only where you control the input
// and want to crash loudly (e.g., app-boot env parsing).
const env = EnvSchema.parse(process.env);

// safeParse — never throws. Use at every request/user boundary.
const result = LoginSchema.safeParse(req.body);
if (!result.success) {
  return res.status(400).json({ errors: result.error.flatten().fieldErrors });
}
const { email, password } = result.data;  // fully typed
```

## Conceptual Model

Think of Zod as **a compiler from `unknown` to `T`**.

1. **Schema-first, never type-first.** You write the schema. The type
   falls out via `z.infer`. Never write
   `interface User {}; const UserSchema = z.object({...})` — the two
   will drift. Instead: `const UserSchema = z.object({...}); type
   User = z.infer<typeof UserSchema>`. Single source of truth.

2. **Parse at boundaries, trust inside.** `unknown` enters your
   system from 4 places: network (request/response), storage
   (database rows, cache), environment (`process.env`), and external
   code (LLM JSON, webhooks). Every boundary gets a schema. Once
   parsed, values are typed — no more `as` casts, no more runtime
   surprises.

3. **`safeParse` is the default at request boundaries; `parse` is
   for boot.** `parse` throws. At a request boundary a thrown
   `ZodError` becomes a 500. You want a 400. Use `safeParse` and
   translate `result.error.flatten()` to a 400 response. `parse` is
   correct ONLY where a failure SHOULD crash (env parsing on
   startup, internal assertions).

4. **`z.input` vs `z.output` — transforms split the type.** If a
   schema has `.transform()`, `.default()`, `.coerce`, or
   `.preprocess()`, the type going IN is different from the type
   coming OUT. `z.input<typeof S>` is the permissive input type.
   `z.output<typeof S>` (and `z.infer`) is the strict output type.
   For RHF: use `z.input` for `useForm<z.input<typeof S>>()` if
   your schema has transforms; the form holds input values until
   submit.

5. **Refinements run AFTER type parsing.** `z.string().refine(...)`
   only fires if the value was a string. This is why you don't need
   to guard against `typeof value === "string"` in the refine — Zod
   already did.

6. **Errors are issues, plural.** A single `ZodError` contains
   `issues: ZodIssue[]`. One parse can produce many issues
   (every field that failed). `.flatten()` groups them by field;
   `.format()` nests them by path. RHF consumes `.flatten()`
   automatically via `zodResolver`.

7. **Shared schemas are the architecture.** The highest-leverage
   pattern in EOS is a `src/schemas/` folder imported by both the
   React app and the Express server. The same schema produces the
   form types, the API request types, the API response types, and
   the validation runtime on both ends. When the schema changes,
   TypeScript errors light up both sides simultaneously. No drift
   possible.

8. **Zod 4 is coming — design for it.** Zod 4 (released mid-2025, in
   parallel with Zod 3's maintenance) is smaller (~13KB gz core,
   "@zod/mini" even smaller), faster, and has a stricter error
   model. The public API is 95% backward compatible. The changes
   that matter: `z.string().email()` moves to `z.email()`, error
   customization moves from `{ message }` to `{ error }` in some
   paths, and `.refine` type-narrows output more aggressively.
   Pin `zod@3` for EOS until a coordinated migration.

## Gotchas

- **`parse` in a request handler throws 500, not 400.** The most
  common Zod anti-pattern. If you write
  `const data = Schema.parse(req.body)` in an Express handler and
  the body is malformed, `ZodError` bubbles to your error middleware
  and clients see 500 (or whatever your error handler does). ALWAYS
  use `safeParse` at request boundaries and translate
  `result.error.flatten().fieldErrors` into a 400. Reserve `parse`
  for boot-time / internal invariants.

- **`z.coerce.number()` accepts nonsense like `"123abc"`.** `z.coerce`
  calls `Number(input)` internally. `Number("123abc")` is `NaN`.
  `z.coerce.number()` does NOT reject NaN — you need
  `z.coerce.number().finite()` (or `.int()`) to catch it. For user
  input, prefer `z.string().regex(/^\d+$/).transform(Number)` or
  `z.string().pipe(z.coerce.number().finite())`.

- **`.default(value)` makes the input optional but the output
  required.** `z.object({ x: z.number().default(0) })` has
  `z.input = { x?: number }` and `z.output = { x: number }`. If you
  use `z.infer` in a RHF `useForm` call, the form type has `x:
  number`, and TypeScript will complain if your `defaultValues`
  doesn't include `x`. Either supply `defaultValues` explicitly or
  use `useForm<z.input<typeof Schema>>()`.

- **`.refine` on a parent object cannot attach the error to a child
  field without `path`.** Writing `.refine((o) => o.a === o.b,
  "mismatch")` produces an issue with `path: []`, which RHF shows as
  a form-level error, not a field error. To attach to a child:
  `.superRefine((val, ctx) => ctx.addIssue({ code:
  z.ZodIssueCode.custom, path: ["b"], message: "mismatch" }))`.

- **Async refine forces `parseAsync`.** Any `.refine(async ...)` or
  `.transform(async ...)` on a schema means `schema.parse()` THROWS
  `Error("Synchronous parse encountered Promise")` at runtime.
  You must use `parseAsync` / `safeParseAsync`. `zodResolver`
  handles this automatically IF the async refine exists when the
  resolver is created — but caching schemas with conditional async
  refines is a footgun.

- **Brand types are erased at runtime.** `z.string().brand<"UserId">`
  produces a type-only distinction. At runtime it's a plain string.
  You cannot `instanceof` a brand. The type safety only holds if
  the only way to produce a `UserId` is through `UserId.parse(...)` —
  if you cast with `as UserId` elsewhere, you bypass it.

- **Deep `.partial()` loses invariants.** `Schema.partial()` makes all
  top-level fields optional; `Schema.deepPartial()` recurses. Both
  also strip `.refine`/`.superRefine` that depended on cross-field
  presence. PATCH endpoints usually want `.partial()` plus a re-add
  of business invariants, NOT a naked `.partial()`.

- **Re-using schemas across client/server without accounting for
  transforms.** If the server's response is parsed with a schema
  that has `z.coerce.date()`, the server-generated JSON sends a
  string, the client parses to `Date`. If you then `JSON.stringify`
  that parsed object, the Date becomes an ISO string again — fine.
  But if a test uses the raw server type and compares to the
  client-parsed type, they differ. Remember: `z.input` ≠ `z.output`
  when transforms exist.

- **ESM resolution with `zod`.** Zod ships dual CJS + ESM. In
  TypeScript strict ESM projects (`"type": "module"`,
  `"moduleResolution": "bundler"` or `"nodenext"`), `import { z }
  from "zod"` works. In older `"moduleResolution": "node"` with
  `"esModuleInterop": false`, you may need
  `import * as z from "zod"`. The Vite + TS default in EOS Just
  Works; Node-only tooling sometimes doesn't.

- **Forgetting to export the inferred type.** You write
  `const UserSchema = z.object({...})` and stop. Now every consumer
  writes `z.infer<typeof UserSchema>` inline. Always export the
  type next to the schema: `export type User = z.infer<typeof
  UserSchema>`. One import, two values.

- **Zod 4 migration surprises.** `z.string().email()` → `z.email()`
  in Zod 4, along with `z.url()`, `z.uuid()`, `z.cuid()` as
  top-level helpers. Error message customization signature
  changed in places. Do NOT mix `zod@3` and `zod@4` in the same
  workspace — type identities differ and schemas don't compose.
  EOS is pinned to `zod@3.x` until a coordinated migration.

- **`drizzle-zod` schemas don't include refinements.** The schemas
  `createInsertSchema` and `createSelectSchema` produce pure
  shape validators derived from the Drizzle table. They do NOT
  know about business invariants ("email must be unique",
  "price must be > 0"). Extend them:
  `createInsertSchema(users, { email: (s) => s.email() })`.

## References

- `references/best_practices.md` — full 19-section creator-level protocol.
- `references/examples.md` — EOS-aligned login form, env parser, discriminated union, drizzle-zod bridge, async refine, brand IDs.
- `references/anti_patterns.md` — real failure modes and fixes.
- `references/integrations.md` — TypeScript / RHF / shadcn Form / React Query / Drizzle / Express / env boot composition.

## Source

- https://zod.dev (authoritative docs)
- https://zod.dev/?id=basic-usage
- https://zod.dev/?id=objects
- https://zod.dev/?id=unions (including discriminatedUnion)
- https://zod.dev/?id=refinements
- https://zod.dev/?id=transforms
- https://zod.dev/?id=branded-types
- https://zod.dev/?id=error-handling
- https://github.com/colinhacks/zod (source + discussions)
- https://github.com/colinhacks/zod/releases (changelog + Zod 4 notes)
- https://react-hook-form.com/docs/useform#resolver
- https://github.com/react-hook-form/resolvers#zod
- https://orm.drizzle.team/docs/zod
