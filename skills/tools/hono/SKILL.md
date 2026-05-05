---
name: hono
description: "Use when building, modifying, or debugging API routes in the EOS saas layer — covers Hono routing, middleware, validation, error handling, and Node.js adapter patterns."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://hono.dev/docs/"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "Hono v4.12"
sdk_version: "hono 4.12.8, @hono/node-server 1.19.11"
speed_category: medium
trigger: both
effort: medium
context: fork
---

# Tool: Hono

## What This Tool Does

Hono is an ultrafast, lightweight web framework built on Web Standards (Request/Response/fetch).
Created by Yusuke Wada, it targets multi-runtime compatibility — the same code runs on
Cloudflare Workers, Deno, Bun, Node.js, AWS Lambda, and Vercel Edge with zero modification.

Key characteristics:
- Zero dependencies in core — the framework itself adds ~14KB
- TypeScript-first with full inference — route params, body schemas, and middleware variables
  are all type-safe without manual annotation
- Middleware is composable and follows an onion model (before handler, after handler)
- Performance comparable to raw `fetch` handlers — Hono adds negligible overhead
- RPC mode enables end-to-end type safety between client and server without codegen

EOS chose Hono because:
1. It is the modern standard for TypeScript API servers — Express is legacy
2. Type-safe middleware variables (Env) eliminate an entire class of runtime errors
3. The Node.js adapter (`@hono/node-server`) makes it production-ready on VPS
4. Drizzle ORM + Zod + Hono is the canonical modern TypeScript API stack
5. When EOS deploys edge functions later, the same code works without rewrite

## EOS Integration

Hono powers the `saas/api/` layer — the REST API for the EOS SaaS product.

**App entry:** `saas/api/index.ts`
- Creates `new Hono<Env>()` with typed environment variables
- Registers auth middleware on all tenant routes via `app.use('/path/*', authMiddleware)`
- Mounts sub-routers with `app.route('/path', router)`
- Registers `app.notFound()` and `app.onError()` global handlers
- Starts server via `@hono/node-server` `serve()` on PORT 3000

**Route files:** `saas/api/routes/`
- `ventures.ts` — GET list, GET by id, PATCH update (Zod validated)
- `skills.ts` — GET list, GET by id, PATCH update with version archiving, POST improve (AI bridge)
- `interactions.ts` — GET list with query filter, GET stats (raw SQL aggregation)
- `outcomes.ts` — POST create, GET skill-performance (raw SQL aggregation)
- `approvals.ts` — GET pending, POST approve, POST reject
- `agent.ts` — POST run, POST team, POST brief (all bridge to Python AI layer)
- `events.ts` — GET list, POST publish

**Middleware:** `saas/api/middleware/auth.ts`
- Validates `x-org-id` header (UUID format check + DB lookup)
- Sets `orgId` and `userId` on Hono context via `c.set()`

**Type definitions:** `saas/api/types.ts`
- Exports `Env` type with `Variables: { orgId: string; userId: string }`
- Every router and middleware imports this for type safety

**Python bridge:** `saas/api/lib/python_bridge.ts`
- Spawns `bridge/agent_bridge.py` as child process
- Sends JSON payload via stdin, reads JSON result from stdout
- Used by `agent.ts` and `skills.ts` routes to invoke EOS AI layer

## Authentication

EOS uses header-based org authentication:

```typescript
// middleware/auth.ts pattern
export async function authMiddleware(c: Context<Env>, next: Next) {
  const orgId = c.req.header('x-org-id')
  if (!orgId) return c.json({ error: 'unauthorized' }, 401)

  // Validate UUID format
  if (!UUID_RE.test(orgId)) return c.json({ error: 'unauthorized' }, 401)

  // Validate org exists in DB
  const rows = await db.select().from(organizations).where(eq(organizations.id, orgId)).limit(1)
  if (rows.length === 0) return c.json({ error: 'unauthorized' }, 401)

  // Set typed variables on context
  c.set('orgId', rows[0].id)
  c.set('userId', rows[0].ownerId)
  await next()
}
```

Applied via `app.use('/path/*', authMiddleware)` — not per-route.
Health check at `/health` is intentionally unprotected.

All downstream routes access auth context via `c.get('orgId')` and `c.get('userId')`.

## Quick Reference

### App creation with Node.js adapter
```typescript
import { Hono } from 'hono'
import { serve } from '@hono/node-server'
import type { Env } from './types.js'

const app = new Hono<Env>()

serve({ fetch: app.fetch, port: 3000 }, () => {
  console.log('Server running on http://localhost:3000')
})
```

### Route definition
```typescript
const router = new Hono<Env>()

router.get('/', async (c) => { ... })
router.get('/:id', async (c) => { ... })
router.post('/', async (c) => { ... })
router.patch('/:id', async (c) => { ... })
router.put('/:id', async (c) => { ... })
router.delete('/:id', async (c) => { ... })

// Mount in main app
app.route('/ventures', router)
```

### Middleware usage
```typescript
// Apply to route group
app.use('/api/*', authMiddleware)

// Apply globally
app.use('*', logger())

// Custom middleware
const timing: MiddlewareHandler = async (c, next) => {
  const start = Date.now()
  await next()
  c.header('X-Response-Time', `${Date.now() - start}ms`)
}
```

### Request body parsing
```typescript
// JSON body — MUST await
const body = await c.req.json()

// With Zod validation (EOS pattern)
const parsed = Schema.safeParse(await c.req.json())
if (!parsed.success) {
  return c.json({ error: 'validation_error', message: parsed.error.flatten() }, 400)
}
```

### Response patterns
```typescript
c.json({ data: rows })              // 200 + application/json
c.json({ item: row }, 201)          // 201 Created
c.json({ error: 'not_found' }, 404) // 404
c.text('OK')                        // 200 + text/plain
c.html('<h1>Hello</h1>')            // 200 + text/html
c.redirect('/new-path')             // 302
c.body(null, 204)                   // 204 No Content
```

### Error handling
```typescript
// Global error handler (registered once in index.ts)
app.onError((err, c) => {
  console.error('[API error]', err)
  return c.json({ error: 'internal_error', message: err.message }, 500)
})

// Global 404 handler
app.notFound((c) =>
  c.json({ error: 'not_found', message: `${c.req.method} ${c.req.path}` }, 404)
)

// HTTPException for structured errors
import { HTTPException } from 'hono/http-exception'
throw new HTTPException(403, { message: 'Forbidden' })
```

### Zod validator middleware (built-in)
```typescript
import { zValidator } from '@hono/zod-validator'

router.post('/',
  zValidator('json', CreateSchema),
  async (c) => {
    const data = c.req.valid('json')  // fully typed
    // ...
  }
)
```
Note: EOS currently uses manual `safeParse` instead of `zValidator` middleware.
Consider migrating to `zValidator` for cleaner route definitions.

### Path parameters
```typescript
router.get('/:id', async (c) => {
  const id = c.req.param('id')       // string
})

router.get('/:org/:repo', async (c) => {
  const { org, repo } = c.req.param() // all params
})
```

### Query parameters
```typescript
router.get('/', async (c) => {
  const ventureId = c.req.query('venture_id')  // string | undefined
  const page = c.req.query('page')
  const queries = c.req.queries('tag')         // string[] | undefined (repeated params)
})
```

### Context variables (typed)
```typescript
// Set in middleware
c.set('orgId', 'uuid-here')

// Read in handler — type-safe via Env
const orgId = c.get('orgId')  // string (not string | undefined)
```

## Conceptual Model

Hono's request lifecycle:

```
Incoming Request (Web Standard Request object)
  |
  v
Middleware Stack (onion model — runs in registration order)
  |-- Middleware 1: before next() → handler → after next()
  |-- Middleware 2: before next() → handler → after next()
  |-- ...
  v
Route Handler (matched by method + path)
  |
  v
Response (Web Standard Response object)
```

Key mental model differences from Express:
- There is no `req` and `res` — there is `c` (Context) which wraps both
- Middleware calls `await next()` — not `next()` without await
- The response is returned, not mutated — `return c.json()` not `res.json()`
- Route matching is trie-based (fast) not linear scan
- Sub-apps are mounted with `app.route()` not `app.use()`

## Gotchas

1. **`c.req.json()` is async — must await.** Forgetting `await` gives you a Promise object
   instead of parsed JSON. The Zod parse will fail with cryptic errors. Every EOS route
   correctly uses `await c.req.json()`.

2. **Middleware order matters — auth before routes.** In `index.ts`, all `app.use()` calls
   are registered before `app.route()` calls. If you register a route before its middleware,
   the middleware will not run for that route. This is registration-order dependent.

3. **Node.js adapter required for server mode.** Hono core has no built-in server — it only
   exports a fetch handler. `@hono/node-server` wraps it in a Node HTTP server. The serve
   call is `serve({ fetch: app.fetch, port })` — note `app.fetch` not `app.callback()`.

4. **`c.json()` sets Content-Type automatically.** Do not manually set `Content-Type: application/json`
   when using `c.json()` — it is done for you. Setting it manually can cause duplicate headers.

5. **Error handler must use `app.onError()`, not try/catch in routes.** While try/catch works,
   unhandled errors (e.g., from middleware, async failures) only get caught by `app.onError()`.
   EOS registers a global error handler in `index.ts`. Always let errors propagate to it
   rather than swallowing them in individual routes.

6. **Hono Context (`c`) is NOT Express `req`/`res`.** Do not destructure `c` into separate
   request/response objects. The Context is a unified object. `c.req` is a Hono-specific
   wrapper around the Web Standard Request — it is not the Node.js IncomingMessage.
   `c.req.raw` gives you the actual Web Standard Request if needed.

7. **Sub-router path stripping.** When you mount `app.route('/ventures', venturesRouter)`,
   the router's handlers see paths relative to the mount point. A handler registered as
   `router.get('/:id')` matches `/ventures/:id`. Do not include the prefix in the sub-router.

8. **`app.use()` path matching includes sub-paths.** `app.use('/api/*', middleware)` runs
   on `/api/anything`. But `app.use('/api', middleware)` only matches `/api` exactly.
   EOS correctly uses `'/ventures/*'` pattern for auth middleware.

9. **`withOrg()` pattern for RLS.** EOS routes use `withOrg(orgId, (tx) => ...)` to execute
   queries within an RLS-scoped transaction. Always pass `orgId` from `c.get('orgId')` —
   never from request body or params. The auth middleware is the single source of truth.

See references/best_practices.md for official documentation, rate limits, and anti-patterns.
