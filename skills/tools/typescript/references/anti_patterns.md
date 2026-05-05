# TypeScript — Anti-Patterns

Real failures observed in production codebases. Each entry has the wrong code, why it's wrong, and the correct replacement.

---

## 1. `any` as Escape Hatch

```ts
// WRONG
function parseConfig(raw: any) {
  return raw.database.url  // no check, no narrowing, will crash at runtime
}
```

`any` disables the type system silently. Every property access compiles.

```ts
// RIGHT — use unknown + Zod at the boundary
const ConfigSchema = z.object({ database: z.object({ url: z.string() }) })
function parseConfig(raw: unknown) {
  return ConfigSchema.parse(raw).database.url
}
```

---

## 2. `as X` Hiding Real Bugs

```ts
// WRONG
const user = (await res.json()) as User
user.email  // could be undefined at runtime, TS thinks it's string
```

Type assertions tell the compiler to trust you. The compiler complies. Your users find the bug.

```ts
// RIGHT
const user = UserSchema.parse(await res.json())  // runtime-validated
// or:
const raw: unknown = await res.json()
if (!isUser(raw)) throw new Error('bad response')
```

---

## 3. `React.FC` — Loses Generics, Implicit children

```tsx
// WRONG
import type { FC } from 'react'
const Button: FC<{ label: string }> = ({ label }) => <button>{label}</button>
```

`React.FC` implicitly adds `children` (though React 18 removed it from the base type, habits linger) and cannot be generic.

```tsx
// RIGHT
function Button({ label }: { label: string }) {
  return <button>{label}</button>
}

// RIGHT — generic component (impossible with FC)
function List<T>({ items, render }: { items: T[]; render: (it: T) => React.ReactNode }) {
  return <ul>{items.map((it, i) => <li key={i}>{render(it)}</li>)}</ul>
}
```

---

## 4. Re-Declaring Types That Should Be `z.infer`'d

```ts
// WRONG — two sources of truth that will drift
const UserSchema = z.object({ id: z.string(), email: z.string().email() })
type User = { id: string; email: string }  // will drift the moment schema gains a field
```

```ts
// RIGHT
const UserSchema = z.object({ id: z.string(), email: z.string().email() })
type User = z.infer<typeof UserSchema>
```

---

## 5. `enum` vs `as const` Object

```ts
// WRONG — runtime object, reverse mappings, not tree-shakeable, banned under isolatedModules with const
enum Stage { Idea = 'idea', Early = 'early', Growth = 'growth' }
```

```ts
// RIGHT
export const STAGES = ['idea', 'early', 'growth'] as const
export type Stage = typeof STAGES[number]
```

Benefits: erased at runtime, works with template literal types, works with `isolatedModules`/`verbatimModuleSyntax`, plays with `z.enum(STAGES)`.

---

## 6. Over-Typing Internals, Under-Typing Boundaries

```ts
// WRONG — annotates every local but not the exported function
export function processUsers(users) {  // implicit any!
  const names: string[] = users.map((u: { name: string }): string => u.name)
  const upper: string[] = names.map((n: string): string => n.toUpperCase())
  return upper
}
```

```ts
// RIGHT — annotate the boundary, infer the rest
export function processUsers(users: User[]): string[] {
  const names = users.map((u) => u.name)
  return names.map((n) => n.toUpperCase())
}
```

---

## 7. `@ts-ignore` Without a Comment

```ts
// WRONG
// @ts-ignore
doSomething(brokenValue)
```

`@ts-ignore` persists forever and blocks refactors silently.

```ts
// RIGHT
// @ts-expect-error — upstream lib's types are wrong, issue #1234, remove after v2.1
doSomething(brokenValue)
```

`@ts-expect-error` fails compilation if the error goes away, so suppressions can't become stale.

---

## 8. Non-Null Assertion `!` in Hot Paths

```ts
// WRONG
const first = users.find(u => u.active)!
console.log(first.email)  // crashes if nobody is active
```

```ts
// RIGHT
const first = users.find(u => u.active)
if (!first) throw new Error('no active users')
console.log(first.email)
```

One assertion at the top, narrowed for the rest of the scope.

---

## 9. `{}` Thinking It Means Empty Object

```ts
// WRONG — {} actually means "any non-null, non-undefined value"
function f(x: {}) { /* x can be a number, string, anything */ }
f(42)      // ok
f('hi')    // ok
```

```ts
// RIGHT
function empty(x: Record<string, never>) { /* truly empty object */ }
function obj(x: Record<string, unknown>) { /* object with unknown values */ }
```

---

## 10. Interface Declaration Merging Surprises

```ts
// WRONG — interface can merge globally, causing hidden surprises
interface Window { myApi: Api }  // this REOPENS lib.dom's Window interface
```

The merge is implicit and can collide with third-party augmentations.

```ts
// RIGHT — scope augmentations explicitly
declare global {
  interface Window {
    myApi: Api
  }
}
export {}
```

Or use `type` which does not merge:
```ts
type LocalConfig = { ... }  // never merges
```

---

## 11. `Partial<T>` Losing Invariants

```ts
// WRONG — allows empty update that changes nothing
function updateUser(id: string, patch: Partial<User>) { /* ... */ }
updateUser('123', {})  // no-op, type-checks
```

```ts
// RIGHT — require at least one field
type NonEmpty<T> = { [K in keyof T]: Pick<Required<T>, K> }[keyof T]
function updateUser(id: string, patch: NonEmpty<User>) { /* ... */ }
updateUser('123', {})            // error
updateUser('123', { email: 'x' }) // ok
```

---

## 12. `parse` Instead of `safeParse` in Route Handlers

```ts
// WRONG
router.post('/users', async (c) => {
  const data = UserSchema.parse(await c.req.json())  // throws → 500
  // ...
})
```

```ts
// RIGHT
router.post('/users', async (c) => {
  const parsed = UserSchema.safeParse(await c.req.json())
  if (!parsed.success) {
    return c.json({ error: 'validation_error', issues: parsed.error.flatten() }, 400)
  }
  // parsed.data is narrowed and fully typed
})
```

---

## 13. Using `z.infer` Where `z.input` Is Needed (RHF)

```tsx
// WRONG — schema has .default('member'), so z.infer makes role required
// but the form has no role field yet → TypeScript complains or you over-submit
const form = useForm<z.infer<typeof UserSchema>>({ resolver: zodResolver(UserSchema) })
```

```tsx
// RIGHT
const form = useForm<z.input<typeof UserSchema>>({ resolver: zodResolver(UserSchema) })
```

See skills/tools/react_hook_form/references/integrations.md for the full rule.

---

## 14. Forgetting `withOrg()` in EOS Backend

```ts
// WRONG — appDb without withOrg returns zero rows silently (RLS enforced)
const rows = await appDb.select().from(ventures)
```

```ts
// RIGHT
const rows = await withOrg(orgId, (tx) => tx.select().from(ventures))
```

No error, just empty results. The worst kind of bug.

---

## 15. `import` Instead of `import type` Under `verbatimModuleSyntax`

```ts
// WRONG — with verbatimModuleSyntax: true, this imports the runtime module
// even though Env is only used as a type
import { Env } from '../types.js'
```

```ts
// RIGHT
import type { Env } from '../types.js'
// or inline:
import { type Env, someValue } from '../types.js'
```
