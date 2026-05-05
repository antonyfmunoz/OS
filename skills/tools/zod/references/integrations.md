# Zod — Integrations (Composition with the EOS Stack)

Zod sits at every trust boundary in the EOS SaaS stack. This file
documents how it composes with every partner library.

---

## TypeScript (strict)

Zod's inference requires `strict: true` in `tsconfig.json`. The
key helpers:

- `z.infer<typeof S>` — the output type (after transforms).
- `z.input<typeof S>` — the input type (before transforms, before
  defaults). Use this for form values and API request bodies when
  the schema contains `.default()` or `.transform()`.
- `z.output<typeof S>` — identical to `z.infer`; used for
  symmetry/clarity when both matter.

**Rule:** the schema is the type. Never declare an `interface`
alongside a schema.

```ts
export const UserSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
});
export type User = z.infer<typeof UserSchema>;
```

---

## React Hook Form (@hookform/resolvers/zod)

`zodResolver(schema)` adapts a Zod schema to RHF's resolver
interface. It:

1. Calls `schema.safeParseAsync(values)` on submit / blur /
   change (depending on `mode`).
2. Converts `ZodError.flatten().fieldErrors` to RHF's
   `FieldErrors` shape.
3. Supports async refines transparently (uses `safeParseAsync`
   under the hood).

```ts
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { LoginSchema } from "@/schemas/auth";

const form = useForm<z.input<typeof LoginSchema>>({
  resolver: zodResolver(LoginSchema),
  defaultValues: { email: "", password: "", remember: false },
  mode: "onBlur",   // "onChange" is expensive with async refines
});
```

**Gotchas:**
- Use `z.input` for `useForm<T>()` when the schema has defaults
  or transforms — `z.infer` may require fields that don't exist
  until parse time.
- `mode: "onChange"` + async refine = request storm. Use
  `"onBlur"` or `"onSubmit"`.
- `defaultValues` must be complete — RHF registers controllers
  from them.

---

## shadcn/ui `<Form>` primitives

shadcn's `<Form>` / `<FormField>` / `<FormItem>` / `<FormLabel>` /
`<FormControl>` / `<FormMessage>` are thin wrappers over RHF's
`<Controller>`. They read the resolver's error object and render
`<FormMessage>` automatically — no per-field error state.

**Zero-boilerplate integration** because:
- `<Form {...form}>` is a `<FormProvider>`.
- `<FormField control={form.control} name="x" render={...}>`
  connects a field to RHF's `<Controller>`.
- `<FormMessage />` reads `fieldState.error?.message`, which
  `zodResolver` populates from the schema's messages.

The canonical pattern (see examples.md section (a)):
```tsx
<FormField name="email" control={form.control} render={({ field }) => (
  <FormItem>
    <FormLabel>Email</FormLabel>
    <FormControl><Input type="email" {...field} /></FormControl>
    <FormMessage />   {/* auto-filled from the Zod error */}
  </FormItem>
)} />
```

**Rule:** the error messages you write in `.email("Enter a valid
email")` show up directly in `<FormMessage>`. Write them with the
user in mind.

---

## React Query (@tanstack/react-query)

Zod parses the RESPONSE before React Query caches it. This
eliminates the "unexpected API shape" crash class entirely.

```ts
import { useQuery, useMutation } from "@tanstack/react-query";
import { UserListResponseSchema } from "@/schemas/user";

export function useUsers() {
  return useQuery({
    queryKey: ["users"],
    queryFn: async () => {
      const res = await fetch("/api/users");
      if (!res.ok) throw new Error("Fetch failed");
      return UserListResponseSchema.parse(await res.json());
      // parse is OK here because we WANT to throw on bad API shapes
      // — React Query catches the throw and puts it in `error`.
    },
  });
}
```

**Why `parse` is OK here (exception to the usual rule):** React
Query's `queryFn` expects throws for failures. A schema parse
failure is, in fact, a fetch failure from the client's POV.

**For mutations:** parse both input and output:
```ts
useMutation({
  mutationFn: async (input: CreateUserRequest) => {
    const body = CreateUserRequest.parse(input);          // pre-flight
    const res = await fetch("/api/users", { method: "POST",
      body: JSON.stringify(body) });
    return CreateUserResponse.parse(await res.json());    // post-flight
  },
});
```

---

## Drizzle ORM (drizzle-zod)

`drizzle-zod` generates Zod schemas from Drizzle table definitions.
Two factories:

```ts
import { createInsertSchema, createSelectSchema } from "drizzle-zod";
import { users } from "@/db/schema";

// Matches what the DB will accept on insert.
const UserInsert = createInsertSchema(users);

// Matches what the DB will return on select.
const UserSelect = createSelectSchema(users);
```

**Extend with business rules the DB can't enforce:**
```ts
const UserInsert = createInsertSchema(users, {
  email: (s) => s.email().toLowerCase(),
  name: (s) => s.min(1).max(255),
}).omit({ id: true, createdAt: true });
```

**Gotchas:**
- `drizzle-zod` does NOT know about uniqueness, foreign keys, or
  custom constraints. Those are DB-level and must be enforced by
  catching the insert error, not by Zod.
- Keep the generated schemas close to the table — a shared
  `src/schemas/` file that imports from `src/db/schema.ts`.
- `createInsertSchema` makes auto-generated columns (defaults,
  serial IDs) optional. `.omit()` them from the request schema
  if the server fills them in.

---

## Express (middleware pattern)

The canonical EOS validation middleware:

```ts
// server/middleware/validate.ts
import type { Request, Response, NextFunction } from "express";
import type { ZodSchema } from "zod";

export function validate(schema: ZodSchema, target: "body" | "query" | "params" = "body") {
  return (req: Request, res: Response, next: NextFunction) => {
    const result = schema.safeParse(req[target]);
    if (!result.success) {
      return res.status(400).json({ errors: result.error.flatten().fieldErrors });
    }
    (req as any)[target] = result.data; // replace with typed, transformed value
    next();
  };
}
```

**Usage:**
```ts
usersRouter.post("/users", validate(CreateUserRequest), (req, res) => {
  // req.body is now the parsed, typed data
});
```

**Pattern:** one middleware per route, schema imported from
`src/schemas/`. Same schemas the client uses.

---

## tRPC (awareness, even though EOS doesn't use it)

tRPC uses Zod as its default input validator. The pattern is
identical to the EOS Express-middleware pattern, just wrapped in
a procedure builder:

```ts
// t3 pattern — not used in EOS, but shown for conceptual parallel
export const userRouter = router({
  create: publicProcedure
    .input(CreateUserRequest)   // Zod schema = tRPC input
    .mutation(async ({ input }) => {
      // input is fully typed — tRPC handled safeParse for us
      return await db.insert(users).values(input).returning();
    }),
});
```

**The lesson for EOS:** even without tRPC, the pattern is the
same — schema at the boundary, typed value inside. tRPC just
automates the `safeParse + 400 on failure` boilerplate. The EOS
`validate()` middleware achieves the same outcome.

---

## Env variable parsing at boot

Every EOS service starts with:

```ts
// src/lib/env.ts
import { z } from "zod";

const EnvSchema = z.object({
  NODE_ENV: z.enum(["development", "test", "production"]),
  DATABASE_URL: z.string().url(),
  JWT_SECRET: z.string().min(32),
  PORT: z.coerce.number().int().positive().default(3000),
});

const parsed = EnvSchema.safeParse(process.env);
if (!parsed.success) {
  console.error("Invalid env:", parsed.error.flatten().fieldErrors);
  process.exit(1);
}
export const env = parsed.data;
```

**Rule:** never reference `process.env.X` directly outside this
file. Always import `env` from `@/lib/env`. The type system then
enforces that every env var you use is declared in the schema.

---

## LLM output parsing (Anthropic, OpenAI, Vercel AI SDK)

Zod is the de facto standard for parsing LLM JSON outputs:

```ts
const OutputSchema = z.object({
  summary: z.string(),
  tags: z.array(z.string()).max(10),
  sentiment: z.enum(["positive", "neutral", "negative"]),
});

const response = await anthropic.messages.create({ /* ... */ });
const raw = response.content[0].type === "text" ? response.content[0].text : "";
const json = JSON.parse(raw);
const result = OutputSchema.safeParse(json);

if (!result.success) {
  // Self-correcting prompt loop — feed the error back to the LLM
  const retry = await anthropic.messages.create({
    messages: [
      { role: "user", content: prompt },
      { role: "assistant", content: raw },
      { role: "user", content: `Your output failed validation: ${JSON.stringify(result.error.flatten())}. Fix and return valid JSON.` },
    ],
  });
  // retry once more, then fall back
}
```

**Frontier pattern:** Vercel's AI SDK has `streamObject({ schema:
MySchema })` that streams AND validates incrementally.

---

## Composition rules (summary)

1. **Schemas live in `src/schemas/`.** One folder, imported by
   client and server.
2. **`src/lib/env.ts`** parses `process.env` at boot. Everywhere
   else imports `env`, not `process.env`.
3. **Client boundaries:** RHF forms use `zodResolver`; React
   Query queries/mutations parse responses.
4. **Server boundaries:** `validate(Schema)` middleware on every
   route that accepts input.
5. **Database boundary:** `drizzle-zod` for insert/select
   schemas, extended with business rules.
6. **LLM boundary:** `safeParse` outputs, retry with error as
   feedback.
7. **Never declare TS types separately from schemas.**
8. **Never mix `zod@3` and `zod@4` in the same workspace.**
