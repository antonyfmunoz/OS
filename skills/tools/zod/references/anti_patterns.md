# Zod — Anti-Patterns

Real failures encountered or widely reported in production TypeScript
codebases. Each entry has the wrong code, the symptom, and the fix.

---

## 1. Using `parse` in a request handler

**Wrong:**
```ts
app.post("/login", (req, res) => {
  const { email, password } = LoginSchema.parse(req.body);
  // ...
});
```
**Symptom:** Any malformed body throws `ZodError`, which hits your
Express error middleware. Clients see 500 (or whatever your error
handler returns) instead of a structured 400. Worse — if you don't
have an error middleware, the request hangs until Express's default
handler catches it.

**Fix:** `safeParse` + explicit 400.
```ts
app.post("/login", (req, res) => {
  const result = LoginSchema.safeParse(req.body);
  if (!result.success) {
    return res.status(400).json({ errors: result.error.flatten().fieldErrors });
  }
  const { email, password } = result.data;
});
```
Reserve `parse` for boot-time invariants (env parsing) and
internal assertions where a throw IS the right outcome.

---

## 2. Sharing schemas across client/server without accounting for transforms

**Wrong:**
```ts
// Shared schema with a transform
export const UserSchema = z.object({
  id: z.string().uuid(),
  createdAt: z.coerce.date(),   // ISO string → Date
});

// Server sends JSON → client parses → now has Date
// Client serializes back to JSON → Date becomes ISO string
// Client re-parses in a test → string → Date again
// Test compares "user === user" by reference → fails
```
**Symptom:** Tests comparing serialized vs parsed values fail.
Date fields don't round-trip identically. `z.input` and `z.output`
differ silently.

**Fix:** Always be explicit about whether you're comparing the
input or output type, and use the matching helper:
```ts
type UserWireFormat = z.input<typeof UserSchema>;   // createdAt: string
type UserRuntime    = z.output<typeof UserSchema>;  // createdAt: Date
```
Or use two schemas — one for the wire, one for the runtime — joined
by `.transform()`.

---

## 3. `z.coerce.number()` accepting garbage input

**Wrong:**
```ts
const Schema = z.object({ age: z.coerce.number() });
Schema.parse({ age: "123abc" }); // → { age: NaN } — passes!
```
**Symptom:** `"123abc"` becomes `NaN`. Downstream code does math
on `NaN` and silently produces wrong results. No error.

**Fix:**
```ts
const Schema = z.object({
  age: z.coerce.number().int().nonnegative().finite(),
});
```
Or, for strict number parsing from untrusted input:
```ts
age: z.string().regex(/^\d+$/).pipe(z.coerce.number().int()),
```

---

## 4. Async refine firing on every keystroke

**Wrong:**
```tsx
const Schema = z.object({
  username: z.string().refine(async (u) => !(await exists(u)), "Taken"),
});
const form = useForm({ resolver: zodResolver(Schema), mode: "onChange" });
```
**Symptom:** Typing "alice" fires a network request for "a", "al",
"ali", "alic", "alice" — five round trips. Backend sees a request
storm. User sees validation jitter.

**Fix:** Use `mode: "onBlur"` (fires once when the field loses
focus), or split the check out of the schema and do it as a
manual effect with a debounce:
```ts
const form = useForm({ resolver: zodResolver(Schema), mode: "onBlur" });
```

---

## 5. Forgetting to export the inferred type

**Wrong:**
```ts
// src/schemas/user.ts
export const UserSchema = z.object({ id: z.string().uuid(), email: z.string().email() });
// ... no type export
```
```ts
// src/handlers/user.ts
import { UserSchema } from "@/schemas/user";
type User = z.infer<typeof UserSchema>;  // boilerplate everywhere
```
**Symptom:** Every consumer re-derives the type inline. When the
schema name changes, dozens of files need updating.

**Fix:**
```ts
export const UserSchema = z.object({ id: z.string().uuid(), email: z.string().email() });
export type User = z.infer<typeof UserSchema>;
```
One import, two values. Convention: co-locate the type export.

---

## 6. Deep `.partial()` on a PATCH endpoint losing invariants

**Wrong:**
```ts
const UserSchema = z.object({
  email: z.string().email(),
  age: z.number().int().min(13),
}).refine((u) => u.age >= 18 || u.email.endsWith("@company.com"),
  "Minors must use a company email");

const UserPatch = UserSchema.partial();
// .refine is GONE from UserPatch
```
**Symptom:** Cross-field rules silently vanish when you
`.partial()` a schema, because refines on `.partial()` schemas
can't assume fields are present.

**Fix:** Re-attach invariants at the PATCH layer, conditional on
field presence:
```ts
const UserPatch = UserSchema.partial().superRefine((val, ctx) => {
  if (val.age !== undefined && val.email !== undefined) {
    if (val.age < 18 && !val.email.endsWith("@company.com")) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["email"],
        message: "Minors must use a company email",
      });
    }
  }
});
```

---

## 7. `.refine` on a parent that should be on a child field

**Wrong:**
```ts
const Schema = z.object({
  password: z.string(),
  confirm: z.string(),
}).refine((o) => o.password === o.confirm, "Passwords must match");
```
**Symptom:** The error's `path` is `[]`. In RHF, this shows as a
top-level form error (`formState.errors.root`), not on the
`confirm` field. Users see a generic error and can't find the
offending field.

**Fix:** Use `superRefine` with an explicit `path`.
```ts
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

---

## 8. Declaring a TS interface AND a Zod schema

**Wrong:**
```ts
interface User {
  id: string;
  email: string;
}

const UserSchema = z.object({
  id: z.string(),
  email: z.string(),   // no .email() — drift!
});
```
**Symptom:** The interface and schema drift over time. Someone
adds `name: string` to the interface, forgets the schema. Runtime
data is valid, but TS still allows `user.name` → undefined.

**Fix:** Schema is the single source of truth.
```ts
export const UserSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
});
export type User = z.infer<typeof UserSchema>;
```

---

## 9. `z.any()` as a shortcut

**Wrong:**
```ts
const Schema = z.object({
  data: z.any(),  // "I'll figure it out later"
});
```
**Symptom:** `data` is typed as `any`. TypeScript gives you zero
help. The entire point of Zod is defeated.

**Fix:** If you genuinely don't know the shape, use `z.unknown()`.
It forces the caller to narrow before using the value. For LLM
output or dynamic data, model the expected shape as a
discriminated union with a catch-all branch:
```ts
const Schema = z.object({
  data: z.unknown(),  // forces runtime checks before use
});
```

---

## 10. Not `.max()`-ing strings from untrusted input

**Wrong:**
```ts
const Schema = z.object({
  bio: z.string(),  // no max length!
});
```
**Symptom:** A 100MB JSON body with a 100MB string passes validation.
Your app allocates a 100MB string. Repeated requests crash the process.

**Fix:** ALWAYS set `.max()` on user-supplied strings.
```ts
const Schema = z.object({
  bio: z.string().max(2000),
});
```

---

## 11. Mixing `zod@3` and `zod@4` in the same workspace

**Wrong:** One package at `zod@3.23`, another at `zod@4.0`. The two
module instances create different TypeScript brand identities, so
schemas from one can't be passed to the resolver of the other.

**Symptom:** `Type 'ZodObject<...>' is not assignable to type
'ZodType<...>'` errors that make no sense. Solving by casting with
`as any` silently breaks the type guarantees.

**Fix:** Enforce a single version via `resolutions` (Yarn) or
`overrides` (npm) in the root `package.json`. EOS pins to
`zod@3.23.x`.

---

## 12. Relying on `.brand` as runtime protection

**Wrong:**
```ts
const UserId = z.string().uuid().brand<"UserId">();
type UserId = z.infer<typeof UserId>;

// elsewhere:
const id = req.params.id as UserId;  // bypasses the parse!
loadUser(id);
```
**Symptom:** The `as UserId` cast defeats the brand. At runtime,
`id` is a plain string that may not even be a UUID. You get
database errors or security holes.

**Fix:** The ONLY way to produce a branded type should be through
`.parse()` / `.safeParse()`. Ban `as UserId` casts via ESLint rule
or code review. Branded types are a contract — honor it.
