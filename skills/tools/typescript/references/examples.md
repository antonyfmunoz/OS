# TypeScript — Executable Examples

Concrete, copy-pasteable patterns. Every example here type-checks under the EOS strict tsconfig.

---

## 1. Strict tsconfig for Vite + React

```jsonc
// saas/frontend/tsconfig.json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noFallthroughCasesInSwitch": true,
    "isolatedModules": true,
    "verbatimModuleSyntax": true,
    "esModuleInterop": true,
    "resolveJsonModule": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "noEmit": true,
    "baseUrl": ".",
    "paths": { "@/*": ["./src/*"] }
  },
  "include": ["src", "vite.config.ts"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

---

## 2. Component Props with ComponentPropsWithoutRef + Omit

```tsx
import type { ComponentPropsWithoutRef } from 'react'
import { cn } from '@/lib/utils'

// Button that wraps <button> but overrides `type` default and adds variant
type ButtonProps = Omit<ComponentPropsWithoutRef<'button'>, 'type'> & {
  variant?: 'primary' | 'secondary' | 'ghost'
  type?: 'button' | 'submit' | 'reset'  // re-add with narrower type + our default
}

export function Button({
  variant = 'primary',
  type = 'button',
  className,
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      className={cn('btn', `btn-${variant}`, className)}
      {...rest}
    />
  )
}
```

---

## 3. Polymorphic `as` Prop Component

```tsx
import type { ElementType, ComponentPropsWithoutRef, ReactNode } from 'react'

type TextProps<C extends ElementType> = {
  as?: C
  children: ReactNode
} & Omit<ComponentPropsWithoutRef<C>, 'as' | 'children'>

export function Text<C extends ElementType = 'span'>({
  as,
  children,
  ...rest
}: TextProps<C>) {
  const Component = (as ?? 'span') as ElementType
  return <Component {...rest}>{children}</Component>
}

// Usage — fully typed:
<Text as="a" href="/home">Home</Text>    // href is allowed (anchor prop)
<Text as="h1">Title</Text>               // no href allowed
<Text>default span</Text>
```

---

## 4. forwardRef (React 18) vs ref-as-prop (React 19)

```tsx
// React 18 pattern — used in EOS saas today
import { forwardRef, type ComponentPropsWithoutRef } from 'react'

type InputProps = ComponentPropsWithoutRef<'input'> & { label: string }

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, id, ...rest }, ref) => (
    <label htmlFor={id}>
      {label}
      <input id={id} ref={ref} {...rest} />
    </label>
  )
)
Input.displayName = 'Input'

// React 19 pattern — migrate to this when upgrading
type InputProps19 = ComponentPropsWithoutRef<'input'> & {
  label: string
  ref?: React.Ref<HTMLInputElement>
}

export function Input19({ label, id, ref, ...rest }: InputProps19) {
  return (
    <label htmlFor={id}>
      {label}
      <input id={id} ref={ref} {...rest} />
    </label>
  )
}
```

---

## 5. `const x = ... satisfies SomeType`

```ts
// Routes config: literal keys preserved, shape validated
const routes = {
  home:    { path: '/',        requiresAuth: false },
  app:     { path: '/app',     requiresAuth: true  },
  billing: { path: '/billing', requiresAuth: true  },
} satisfies Record<string, { path: string; requiresAuth: boolean }>

type RouteKey = keyof typeof routes  // 'home' | 'app' | 'billing'

// Still typed as literal:
routes.home.path  // "/"  — not string
```

---

## 6. Discriminated Union for Async State

```ts
type QueryState<T, E = Error> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: T; fetchedAt: number }
  | { status: 'error'; error: E; retryCount: number }

function render<T>(state: QueryState<T>): string {
  switch (state.status) {
    case 'idle':    return 'waiting'
    case 'loading': return 'loading...'
    case 'success': return `ok: ${String(state.data)}`  // data narrowed
    case 'error':   return `err: ${state.error.message}` // error narrowed
  }
  // exhaustive — TS errors if a new status is added without a case
}
```

---

## 7. z.infer + z.input for Forms and API

```ts
import { z } from 'zod'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'

export const UserFormSchema = z.object({
  email: z.string().email(),
  age:   z.coerce.number().int().min(18),           // input: string, output: number
  role:  z.enum(['admin', 'member']).default('member'),  // input: optional, output: required
})

type FormInput  = z.input<typeof UserFormSchema>   // { email: string; age: string|number; role?: 'admin'|'member' }
type FormOutput = z.infer<typeof UserFormSchema>   // { email: string; age: number; role: 'admin'|'member' }

// Form uses INPUT type — because HTML inputs send strings and defaults are not yet applied
export function UserForm({ onSubmit }: { onSubmit: (data: FormOutput) => void }) {
  const form = useForm<FormInput>({ resolver: zodResolver(UserFormSchema) })
  return (
    <form onSubmit={form.handleSubmit((data) => onSubmit(data as unknown as FormOutput))}>
      <input {...form.register('email')} />
      <input {...form.register('age')} type="number" />
    </form>
  )
}
```

---

## 8. Generic Hook Typing (useQuery<Response>)

```ts
import { useQuery, useMutation, type UseQueryResult } from '@tanstack/react-query'

interface User { id: string; email: string }

// Typed query
export function useUser(id: string): UseQueryResult<User, Error> {
  return useQuery({
    queryKey: ['user', id] as const,
    queryFn: async (): Promise<User> => {
      const r = await fetch(`/api/users/${id}`)
      if (!r.ok) throw new Error('fetch failed')
      return r.json() as Promise<User>
    },
  })
}

// Typed mutation — <TData, TError, TVariables>
export function useUpdateUser() {
  return useMutation<User, Error, { id: string; email: string }>({
    mutationFn: async (vars) => {
      const r = await fetch(`/api/users/${vars.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ email: vars.email }),
      })
      if (!r.ok) throw new Error('update failed')
      return r.json() as Promise<User>
    },
  })
}
```

---

## 9. Template Literal Types for Route Strings

```ts
type Method = 'GET' | 'POST' | 'PATCH' | 'DELETE'
type Path   = `/api/${string}`
type Endpoint = `${Method} ${Path}`

async function request<T>(endpoint: Endpoint, body?: unknown): Promise<T> {
  const [method, path] = endpoint.split(' ') as [Method, Path]
  const r = await fetch(path, {
    method,
    headers: { 'content-type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!r.ok) throw new Error(`${method} ${path} -> ${r.status}`)
  return r.json() as Promise<T>
}

await request<User>('GET /api/users/123')
await request('FOO /api/x')  // compile error
```

---

## 10. `as const` Enum Alternative

```ts
export const VENTURE_STAGES = [
  'idea',
  'pre_revenue',
  'early',
  'growth',
  'scale',
] as const

export type VentureStage = typeof VENTURE_STAGES[number]

// Plays nice with Zod:
import { z } from 'zod'
export const VentureStageSchema = z.enum(VENTURE_STAGES)

// Exhaustive handling:
function stageLabel(s: VentureStage): string {
  switch (s) {
    case 'idea':        return 'Ideation'
    case 'pre_revenue': return 'Pre-revenue'
    case 'early':       return 'Early'
    case 'growth':      return 'Growth'
    case 'scale':       return 'At scale'
  }
}
```

---

## 11. Branded Types for IDs

```ts
type Brand<T, B extends string> = T & { readonly __brand: B }

export type OrgId     = Brand<string, 'OrgId'>
export type UserId    = Brand<string, 'UserId'>
export type VentureId = Brand<string, 'VentureId'>

// Constructors validate once at the boundary:
export function asOrgId(s: string): OrgId {
  if (!/^[0-9a-f-]{36}$/i.test(s)) throw new Error('invalid org id')
  return s as OrgId
}

function loadVenture(orgId: OrgId, ventureId: VentureId) { /* ... */ }

// loadVenture(ventureId, orgId)  // compile error — swap prevented
```

---

## 12. Drizzle $inferSelect / $inferInsert

```ts
// saas/db/schema.ts
import { pgTable, uuid, text, numeric, timestamp } from 'drizzle-orm/pg-core'

export const ventures = pgTable('ventures', {
  id:             uuid('id').primaryKey().defaultRandom(),
  orgId:          uuid('org_id').notNull(),
  name:           text('name').notNull(),
  stage:          text('stage').notNull(),
  monthlyRevenue: numeric('monthly_revenue'),
  createdAt:      timestamp('created_at').defaultNow().notNull(),
})

export type Venture    = typeof ventures.$inferSelect  // row as returned by SELECT
export type NewVenture = typeof ventures.$inferInsert  // shape accepted by INSERT
// Note: monthlyRevenue is `string | null` because Drizzle maps numeric → string.
```

---

## 13. Zod + Drizzle via drizzle-zod

```ts
import { createInsertSchema, createSelectSchema } from 'drizzle-zod'
import { ventures } from './schema'
import { z } from 'zod'

export const InsertVentureSchema = createInsertSchema(ventures, {
  // refine auto-generated fields
  name: (s) => s.min(1).max(120),
  stage: z.enum(['idea', 'pre_revenue', 'early', 'growth', 'scale']),
}).omit({ id: true, createdAt: true })

export type InsertVenture = z.infer<typeof InsertVentureSchema>
```

---

## 14. Hono Typed Env + Route

```ts
// saas/api/types.ts
export type Env = {
  Variables: {
    orgId:  string
    userId: string
  }
}

// saas/api/routes/ventures.ts
import { Hono } from 'hono'
import { z } from 'zod'
import type { Env } from '../types.js'
import { withOrg } from '../../db/client.js'
import { ventures } from '../../db/schema.js'
import { eq } from 'drizzle-orm'

const router = new Hono<Env>()

const PatchSchema = z.object({
  name: z.string().min(1).optional(),
  stage: z.enum(['idea', 'pre_revenue', 'early', 'growth', 'scale']).optional(),
}).strict()

router.patch('/:id', async (c) => {
  const orgId = c.get('orgId')  // typed as string
  const id = c.req.param('id')
  const parsed = PatchSchema.safeParse(await c.req.json())
  if (!parsed.success) {
    return c.json({ error: 'validation_error', issues: parsed.error.flatten() }, 400)
  }
  const [updated] = await withOrg(orgId, (tx) =>
    tx.update(ventures).set(parsed.data).where(eq(ventures.id, id)).returning()
  )
  if (!updated) return c.json({ error: 'not_found' }, 404)
  return c.json({ venture: updated })
})

export default router
```
