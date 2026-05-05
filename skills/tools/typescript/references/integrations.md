# TypeScript — Integrations with the EOS Stack

How TypeScript composes with every other tool in the EOS frontend and backend. Each section covers the composition pattern, a typed example, and the gotchas.

---

## React 18 / 19

### Component typing (React 18)

Use `forwardRef` for components that need refs, `ComponentPropsWithoutRef<'element'>` to inherit DOM attributes.

```tsx
import { forwardRef, type ComponentPropsWithoutRef } from 'react'

type Props = ComponentPropsWithoutRef<'button'> & { variant?: 'primary' | 'ghost' }
export const Button = forwardRef<HTMLButtonElement, Props>(({ variant = 'primary', ...rest }, ref) =>
  <button ref={ref} data-variant={variant} {...rest} />
)
```

### Hook generics (React 18+)

```tsx
const [user, setUser] = useState<User | null>(null)
const ref = useRef<HTMLInputElement>(null)
const ctx = useContext(UserContext)  // type inferred from createContext
```

### React 19 migration

- `forwardRef` is deprecated, not removed. Existing code keeps working.
- New code: type `ref` as a prop: `ref?: React.Ref<HTMLButtonElement>`.
- Use the React 19 codemod (`npx codemod@latest react/19/remove-forward-ref`) when upgrading — do not hand-edit.
- `useContext` → `use()` for reads inside Suspense boundaries (optional).

**Gotcha:** Mixing `forwardRef` and ref-as-prop in the same component tree works but makes typing inconsistent. Migrate whole features at once.

---

## Zod

TypeScript + Zod is the single source of truth pattern. Schema defines runtime validation AND the TypeScript type.

```ts
import { z } from 'zod'

export const UserSchema = z.object({
  id:    z.string().uuid(),
  email: z.string().email(),
  age:   z.coerce.number().int().min(18),
  role:  z.enum(['admin', 'member']).default('member'),
})

export type User      = z.infer<typeof UserSchema>  // post-parse (output)
export type UserInput = z.input<typeof UserSchema>  // pre-parse (input)
```

### `z.infer` vs `z.input` — the rule

- **`z.output`** (aliased as `z.infer`) = what `.parse()` RETURNS. Defaults filled in. Transforms applied. Coercion done.
- **`z.input`** = what `.parse()` ACCEPTS. Defaults are optional here. Coerced fields accept the pre-coerce type.

**When to use which:**
- **API response on the client** → `z.infer` (already parsed by server).
- **Form state in react-hook-form** → `z.input` (raw DOM input, defaults not yet applied).
- **DB row** → `z.infer` (what comes out).
- **API body received by a route** → use `safeParse` and let the narrowed `.data` be `z.infer` automatically.

**Gotcha:** If you write `useForm<z.infer<...>>` and your schema has `.default()` or `.transform()`, the form type will require fields your form doesn't actually collect, or demand the wrong raw type.

---

## react-hook-form

```tsx
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { UserSchema } from './schemas'
import { z } from 'zod'

type FormInput = z.input<typeof UserSchema>

export function UserForm() {
  const { register, handleSubmit, formState: { errors } } = useForm<FormInput>({
    resolver: zodResolver(UserSchema),
  })

  return (
    <form onSubmit={handleSubmit((data) => {
      // data here is z.output<typeof UserSchema> — resolver has parsed + transformed
    })}>
      <input {...register('email')} />
      {errors.email && <span>{errors.email.message}</span>}
    </form>
  )
}
```

**The rule:** `useForm<z.input<typeof Schema>>()`. See react_hook_form skill references/integrations.md for the full rationale.

---

## @tanstack/react-query

```ts
import { useQuery, useMutation, type UseQueryResult } from '@tanstack/react-query'
import { UserSchema, type User } from './schemas'

export function useUser(id: string): UseQueryResult<User, Error> {
  return useQuery({
    queryKey: ['user', id] as const,
    queryFn: async () => {
      const r = await fetch(`/api/users/${id}`)
      if (!r.ok) throw new Error('fetch failed')
      return UserSchema.parse(await r.json())  // runtime validation + correct type
    },
  })
}

export function useUpdateUser() {
  return useMutation<User, Error, { id: string; email: string }>({
    mutationFn: async (vars) => {
      const r = await fetch(`/api/users/${vars.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ email: vars.email }),
      })
      return UserSchema.parse(await r.json())
    },
  })
}
```

**Gotchas:**
- `queryKey` should be `as const` so it's a readonly tuple — React Query's internal type machinery expects this.
- Always validate the response with Zod. Without it, `queryFn` return type leaks to `any` when you use `r.json()`.
- Mutation generics: `<TData, TError, TVariables>` in that order.

---

## Drizzle ORM

```ts
import { pgTable, uuid, text, numeric } from 'drizzle-orm/pg-core'
import { createInsertSchema, createSelectSchema } from 'drizzle-zod'

export const ventures = pgTable('ventures', {
  id:    uuid('id').primaryKey().defaultRandom(),
  orgId: uuid('org_id').notNull(),
  name:  text('name').notNull(),
  stage: text('stage').notNull(),
  mrr:   numeric('monthly_revenue'),
})

export type Venture    = typeof ventures.$inferSelect
export type NewVenture = typeof ventures.$inferInsert

// drizzle-zod: generate Zod schemas from Drizzle tables
export const InsertVentureSchema = createInsertSchema(ventures).omit({ id: true })
export const SelectVentureSchema = createSelectSchema(ventures)
```

**Gotchas:**
- `numeric()` columns map to `string`, not `number`. Convert manually.
- `$inferInsert` marks columns with defaults as optional.
- `drizzle-zod` generates schemas from DB types — these are your INSERT/SELECT validators. Pair with custom refinements: `createInsertSchema(ventures, { name: (s) => s.min(1) })`.

---

## Hono

```ts
// types.ts
export type Env = {
  Variables: { orgId: string; userId: string }
}

// routes/ventures.ts
import { Hono } from 'hono'
import type { Env } from '../types.js'

const router = new Hono<Env>()
router.get('/', async (c) => {
  const orgId = c.get('orgId')  // string (typed from Env.Variables)
  return c.json({ orgId })
})
```

**Gotchas:**
- Declare `Env` once, pass to every `new Hono<Env>()` so `c.get()` is typed.
- Middleware sets values with `c.set('orgId', value)` — must match `Env.Variables`.
- Hono's `c.req.json()` returns `Promise<unknown>`. Always Zod `safeParse` before use.

---

## Vite + vite-tsconfig-paths

```ts
// vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tsconfigPaths from 'vite-tsconfig-paths'

export default defineConfig({
  plugins: [react(), tsconfigPaths()],
})
```

With `tsconfig.json` `paths`:
```jsonc
"baseUrl": ".",
"paths": { "@/*": ["./src/*"] }
```

Then `import { Button } from '@/components/Button'` works in both TS and Vite.

**Gotchas:**
- `moduleResolution: "bundler"` is required (not `node`, not `nodenext`) to match Vite's resolver.
- `allowImportingTsExtensions: true` is tempting but then you must also set `noEmit: true` — keep extensions off imports under bundler mode.
- `verbatimModuleSyntax: true` + `isolatedModules: true` is the canonical Vite+TS combo.

---

## Tailwind + clsx

```ts
// lib/utils.ts
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}

// Usage — typed ClassValue accepts strings, arrays, conditionals, undefined
<button className={cn('btn', isActive && 'btn-active', className)} />
```

`clsx`'s `ClassValue` type accepts any class-like input; `twMerge` deduplicates conflicting Tailwind classes. This is the shadcn/ui convention.

---

## Shared Zod Schemas Between Client and Server

```
saas/
  src/
    schemas/
      user.ts          ← defined once
  api/
    routes/
      users.ts         ← imports from ../../src/schemas/user.js
  frontend/
    src/
      forms/
        UserForm.tsx   ← imports from @/schemas/user
```

Both sides import the same `UserSchema`. Client validates form input; server validates request body. Types derived from the same source — no drift.

**Gotcha:** The TS and Vite tsconfigs must agree on the `paths` alias (or both use relative imports). Mismatched aliases are the most common "works in dev, breaks in build" bug.

---

## Python Bridge (EOS-specific)

```ts
// saas/api/lib/python_bridge.ts
type BridgeResult<T> =
  | { success: true;  data: T }
  | { success: false; error: string }

export async function callBridge<T>(input: { action: string; payload: unknown }): Promise<BridgeResult<T>> {
  // spawns a Python subprocess, returns discriminated union
}

// Usage
const result = await callBridge<AgentResponse>({ action: 'agent.run', payload })
if (!result.success) return c.json({ error: result.error }, 502)
return c.json(result.data)  // narrowed to AgentResponse
```

**Gotcha:** The existing `BridgeResult` in the codebase uses optional fields (`{ success, data?, error? }`) instead of a proper discriminated union. Refactoring to the union above gives automatic narrowing.
