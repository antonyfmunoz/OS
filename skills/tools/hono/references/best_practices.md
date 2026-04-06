# Hono — Creator-Level Best Practices
Source: https://hono.dev/docs/
API Version: Hono v4.12
SDK Version: hono 4.12.8, @hono/node-server 1.19.11
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## Authentication

Hono provides built-in auth middleware and supports custom patterns:

**Bearer Token:**
```typescript
import { bearerAuth } from 'hono/bearer-auth'
app.use('/api/*', bearerAuth({ token: process.env.API_TOKEN! }))
```

**Basic Auth:**
```typescript
import { basicAuth } from 'hono/basic-auth'
app.use('/admin/*', basicAuth({ username: 'admin', password: process.env.ADMIN_PASS! }))
```

**JWT:**
```typescript
import { jwt } from 'hono/jwt'
app.use('/api/*', jwt({ secret: process.env.JWT_SECRET! }))
// Access payload: const payload = c.get('jwtPayload')
```

**Custom auth (EOS pattern):** Header-based org ID validation with DB lookup.
The middleware sets typed variables on context that downstream handlers consume.
This is the correct pattern for multi-tenant apps where auth is not token-based.

Best practices:
- Always validate auth in middleware, not in individual handlers
- Use `app.use('/path/*', auth)` to cover all sub-routes
- Never trust client-provided org/user IDs from body — only from validated middleware context
- Store auth results in typed context variables via `c.set()` / `c.get()`

## Core Operations

**HTTP Methods:** `app.get()`, `app.post()`, `app.put()`, `app.patch()`, `app.delete()`, `app.options()`, `app.all()`

**Streaming responses:**
```typescript
import { stream, streamSSE } from 'hono/streaming'

app.get('/stream', (c) => {
  return stream(c, async (stream) => {
    await stream.write('chunk 1')
    await stream.write('chunk 2')
  })
})

app.get('/sse', (c) => {
  return streamSSE(c, async (stream) => {
    await stream.writeSSE({ data: JSON.stringify({ msg: 'hello' }), event: 'message' })
  })
})
```

**WebSocket (requires adapter):**
```typescript
import { createNodeWebSocket } from '@hono/node-ws'
const { injectWebSocket, upgradeWebSocket } = createNodeWebSocket({ app })

app.get('/ws', upgradeWebSocket((c) => ({
  onMessage(event, ws) { ws.send('echo: ' + event.data) },
  onClose() { console.log('closed') },
})))
```

**File upload:**
```typescript
app.post('/upload', async (c) => {
  const body = await c.req.parseBody()
  const file = body['file'] as File
  const arrayBuffer = await file.arrayBuffer()
})
```

**Static files (Node.js):**
```typescript
import { serveStatic } from '@hono/node-server/serve-static'
app.use('/static/*', serveStatic({ root: './' }))
```

**Testing without server:**
```typescript
const res = await app.request('/health')
const json = await res.json()
// No HTTP server needed — Hono apps are just fetch handlers
```

## Pagination

Hono has no built-in pagination — implement with query params:

```typescript
router.get('/', async (c) => {
  const page = Number(c.req.query('page') ?? '1')
  const limit = Math.min(Number(c.req.query('limit') ?? '50'), 100)
  const offset = (page - 1) * limit

  const rows = await db.select().from(table).limit(limit).offset(offset)
  const [{ count }] = await db.select({ count: sql`count(*)::int` }).from(table)

  return c.json({
    data: rows,
    pagination: { page, limit, total: count, pages: Math.ceil(count / limit) }
  })
})
```

Best practice: Always cap `limit` to prevent abuse. EOS uses `.limit(50)` or `.limit(100)` as hardcoded caps in interaction and event queries.

## Rate Limits

Hono has a community rate-limit middleware (`hono-rate-limiter`):

```typescript
import { rateLimiter } from 'hono-rate-limiter'

app.use(rateLimiter({
  windowMs: 60_000,     // 1 minute window
  limit: 100,           // max requests per window
  keyGenerator: (c) => c.req.header('x-org-id') ?? c.req.header('x-forwarded-for') ?? '',
  handler: (c) => c.json({ error: 'rate_limited', message: 'Too many requests' }, 429),
}))
```

For production, use a Redis-backed store. The default is in-memory (single process only, resets on restart).

EOS does not currently implement rate limiting. When adding:
- Rate limit per org ID, not per IP (multi-tenant)
- Exempt `/health` endpoint
- Return `Retry-After` header with 429 responses
- Consider separate limits for read vs write operations

## Error Codes

Hono provides `HTTPException` for structured error throwing:

```typescript
import { HTTPException } from 'hono/http-exception'

// Throw from anywhere — caught by app.onError()
throw new HTTPException(400, { message: 'Invalid input' })
throw new HTTPException(401, { message: 'Unauthorized' })
throw new HTTPException(403, { message: 'Forbidden' })
throw new HTTPException(404, { message: 'Not found' })
throw new HTTPException(409, { message: 'Conflict' })
throw new HTTPException(422, { message: 'Unprocessable entity' })
throw new HTTPException(429, { message: 'Rate limited' })
throw new HTTPException(500, { message: 'Internal error' })
throw new HTTPException(502, { message: 'Bad gateway' })
```

The `app.onError()` handler catches both HTTPException and unhandled errors.
EOS uses direct `c.json({ error, message }, status)` returns in routes — valid but less composable.
HTTPException is better when errors originate from helper functions without access to `c`.

**Custom error handler with HTTPException awareness:**
```typescript
app.onError((err, c) => {
  if (err instanceof HTTPException) {
    return err.getResponse()  // preserves the status and message
  }
  console.error('[API error]', err)
  return c.json({ error: 'internal_error', message: err.message }, 500)
})
```

## SDK Idioms

**Factory pattern — reusable app creation:**
```typescript
import { createFactory } from 'hono/factory'

const factory = createFactory<Env>()
const authMiddleware = factory.createMiddleware(async (c, next) => {
  c.set('orgId', 'validated-id')
  await next()
})
```

**RPC mode — end-to-end type safety (no codegen):**
```typescript
// Server: export the route chain type
const routes = app
  .get('/users/:id', async (c) => c.json({ user: { id: c.req.param('id') } }))
  .post('/users', zValidator('json', CreateUserSchema), async (c) => {
    const data = c.req.valid('json')
    return c.json({ user: data }, 201)
  })
export type AppType = typeof routes

// Client: fully typed, autocompleted
import { hc } from 'hono/client'
const client = hc<AppType>('http://localhost:3000')
const res = await client.users[':id'].$get({ param: { id: '1' } })
```

**Zod validator middleware (recommended over manual safeParse):**
```typescript
import { zValidator } from '@hono/zod-validator'

router.post('/', zValidator('json', schema), async (c) => {
  const data = c.req.valid('json')  // fully typed, already validated
})
// Validates: 'json', 'query', 'param', 'header', 'form', 'cookie'
```

**Method chaining for route type inference:**
```typescript
// Chain methods to build the type — required for RPC mode
const app = new Hono()
  .get('/a', handler1)
  .post('/b', handler2)
// typeof app captures all route signatures
```

## Anti-Patterns

1. **Using Express patterns.** `req.body` does not exist. `res.send()` does not exist.
   Everything goes through the Context `c`. Hono is not Express with a different name.

2. **Forgetting `await next()` in middleware.** Without await, downstream middleware and
   handlers may not execute, or may execute out of order. Always `await next()`.

3. **Mutating the request object.** Hono's request is based on Web Standards and is largely
   immutable. Use `c.set()` / `c.get()` for passing data between middleware and handlers.

4. **Importing from `hono/node-server` instead of `@hono/node-server`.** The adapter is a
   separate package. `hono/streaming` is core. `@hono/node-server` is the adapter package.

5. **Using `app.listen()`.** Hono has no `listen()` method. Use `serve()` from the adapter.

6. **Returning nothing from handlers.** Every handler must return a Response. Forgetting
   `return c.json(...)` causes empty responses or hangs.

7. **Double-mounting route prefixes.** `app.route('/api', router)` with `router.get('/api/x')`
   creates path `/api/api/x`. Sub-routers see paths relative to their mount point.

8. **Destructuring Context.** `const { req, res } = c` — there is no `res` on Context.

9. **Not typing the Env.** `new Hono()` without `<Env>` loses type safety on `c.get()`/`c.set()`.

10. **Calling `c.req.json()` on GET requests.** GET requests have no body — this throws.

## Data Model

Hono's type system has three key generic parameters on the Env type:

```typescript
type Env = {
  Bindings: {}    // Platform bindings (Cloudflare KV, D1, R2) — unused in Node.js
  Variables: {     // Per-request variables via c.set() / c.get()
    orgId: string
    userId: string
  }
}
```

EOS uses only `Variables` since it runs on Node.js. The `Variables` type ensures that
auth middleware output is consumed correctly by every handler without runtime checks.
`c.get('orgId')` returns `string`, not `string | undefined`. `c.set('orgId', 123)` is
a compile-time type error.

## Webhooks

Receiving webhooks in Hono:

```typescript
app.post('/webhooks/stripe', async (c) => {
  const rawBody = await c.req.text()  // raw body for signature verification
  const sig = c.req.header('stripe-signature')
  const event = stripe.webhooks.constructEvent(rawBody, sig!, webhookSecret)
  return c.json({ received: true })
})
```

Key points:
- Use `c.req.text()` for raw body when signature verification is needed
- Do NOT call `c.req.json()` first — it consumes the body stream (single-read)
- Webhook endpoints should be excluded from auth middleware
- Return 200 quickly, process heavy logic asynchronously

## Limits

- **Request body size:** No built-in limit in Hono core. Node.js adapter inherits Node's default (~1MB). Use `bodyLimit` middleware:
  ```typescript
  import { bodyLimit } from 'hono/body-limit'
  app.use(bodyLimit({ maxSize: 5 * 1024 * 1024 }))  // 5MB
  ```
- **Header size:** Node.js HTTP parser default ~16KB
- **URL length:** Runtime-dependent, no Hono-specific limit
- **Concurrent connections:** OS and Node.js limits, not Hono
- **Route count:** No practical limit — trie-based routing handles thousands

## Cost Model

Hono is fully open source (MIT license). Zero cost for the framework.

Costs come from infrastructure:
- VPS hosting (EOS pattern)
- Serverless invocations (if deployed to Workers/Lambda)
- Dependencies (`@hono/zod-validator`, `@hono/node-server`) are also MIT

No API keys, no usage-based pricing, no vendor lock-in.

## Version Pinning

EOS pins: `"hono": "^4.12.8"`, `"@hono/node-server": "^1.19.11"`

Hono v4 is stable. Breaking changes from v3 to v4:
- `app.fire()` removed — use `app.fetch` directly
- `c.req.parseBody()` returns `File` objects instead of `ArrayBuffer`
- Some middleware moved from core to separate packages

Within v4.x, semver is followed. Minor/patch updates are safe.
Lock to `^4` — never use `*` or `latest`.
Adapter versions should match Hono major version.

---

# Tier 2 — Creator Intelligence

## Design Intent

Yusuke Wada created Hono with a clear philosophy:

1. **Web Standards first.** Hono uses Web Standard `Request` and `Response` objects.
   No proprietary abstractions. Any runtime implementing the Fetch API can run Hono.

2. **Multi-runtime by design.** Unlike Express (Node-only) or Elysia (Bun-only), Hono
   targets all JavaScript runtimes. Write once, deploy anywhere.

3. **Zero dependencies.** The core framework has zero npm dependencies. No supply chain
   risk, no transitive vulnerabilities, minimal bundle size.

4. **TypeScript-native.** Not "TypeScript-compatible" — the type system is a first-class
   feature. Route params, middleware variables, validator outputs are all inferred.

5. **Composable middleware.** Onion model (like Koa, unlike Express). Each middleware wraps
   the next, enabling clean before/after patterns.

6. **Developer experience.** Small API surface. Minimal boilerplate. The hello-world is
   4 lines. A full production API is not dramatically more.

The name "Hono" means "flame" in Japanese — reflecting speed and intensity.

## Problem-Solution Map

| Problem | Hono Solution |
|---------|---------------|
| File upload | `c.req.parseBody()` returns `File` objects, `file.arrayBuffer()` for content |
| Server-Sent Events | `streamSSE()` from `hono/streaming` — zero extra deps |
| WebSocket | `@hono/node-ws` for Node.js, native `upgradeWebSocket()` for Workers |
| Middleware composition | `app.use()` chaining or `factory.createMiddleware()` |
| Input validation | `@hono/zod-validator` declarative, or manual `safeParse` |
| CORS | `cors()` from `hono/cors` — built-in |
| Static files (Node) | `serveStatic()` from `@hono/node-server/serve-static` |
| Request logging | `logger()` from `hono/logger` — built-in |
| ETag / caching | `etag()` from `hono/etag`, `cache()` from `hono/cache` |
| Compression | `compress()` from `hono/compress` — gzip/brotli |
| Request timeout | `timeout()` from `hono/timeout` — per-route or global |
| Secure headers | `secureHeaders()` from `hono/secure-headers` — HSTS, CSP, X-Frame |
| Testing | `app.request('/path')` — returns Response, no HTTP server needed |
| Multi-tenant isolation | Typed Env variables + auth middleware (EOS pattern) |
| OpenAPI spec generation | `@hono/swagger-ui` + `@hono/zod-openapi` |
| GraphQL | Mount GraphQL server as middleware via `graphqlServer()` |

## Operational Behavior

**Cold start:** Hono adds <1ms initialization overhead. On Node.js with `tsx`, cold start
is dominated by TypeScript compilation (~200-500ms). Pre-compile for production.

**Memory:** Framework footprint is ~2-5MB. Application code, DB connection pools, and
request payloads dominate actual usage.

**Connection handling:** Node.js adapter uses Node's HTTP server. Keep-alive enabled by
default. For high-concurrency, tune `server.maxConnections` and `server.keepAliveTimeout`.

**Graceful shutdown:**
```typescript
const server = serve({ fetch: app.fetch, port: 3000 })
process.on('SIGTERM', () => server.close(() => process.exit(0)))
```

**Hot reload:** `tsx watch` (EOS dev script). No Hono-specific HMR needed.

**Error isolation:** Unhandled promise rejections in handlers are caught by `app.onError()`.
One bad request does not crash the server. This is better than Express's default behavior.

## Ecosystem Position

| Framework | Runtime | TypeScript | Performance | Deps | Maturity |
|-----------|---------|------------|-------------|------|----------|
| **Hono** | All | Native | Excellent | 0 | Stable v4 |
| Express | Node | Bolted on | Good | Many | Legacy |
| Fastify | Node | Plugin | Excellent | Some | Mature |
| Elysia | Bun | Native | Excellent | Few | Growing |
| Nitro/H3 | All | Native | Good | Many | Nuxt-tied |

**Hono wins:** Multi-runtime, zero deps, TypeScript inference, Web Standards.
**Express wins:** Ecosystem size (legacy), familiarity, existing middleware.
**Fastify wins:** Plugin system, JSON serialization speed, schema validation.
**Elysia wins:** Bun-native performance, end-to-end type safety with Eden.

For EOS: Hono is correct. Modern standard. Multi-runtime future-proofs the API layer.

## Trajectory

Hono v4 is current stable. Actively maintained with weekly patch/minor releases.

Key trends:
- Default framework for Cloudflare Workers/Pages
- Recommended by Vercel for edge functions
- `@hono/zod-validator` becoming the standard validation pattern
- RPC mode gaining traction for full-stack TypeScript
- Community middleware ecosystem expanding rapidly
- Becoming the de facto Express replacement for new TypeScript projects
- OpenAPI/Swagger integration maturing via `@hono/zod-openapi`

v5 expectations:
- No major breaking changes announced — stability-first philosophy
- Enhanced OpenAPI integration
- Improved testing utilities
- Continued middleware ecosystem growth

## Conceptual Model

```
                    ┌─────────────────────────────────┐
                    │         Hono Application         │
                    │                                   │
  Request ──────>  │  Middleware 1 (CORS)               │
                    │    ├── before next()              │
                    │    │                              │
                    │  Middleware 2 (auth)              │
                    │    ├── before next() / early ret  │
                    │    │                              │
                    │  Route Handler                    │
                    │    └── return c.json(data)        │
                    │    │                              │
                    │  Middleware 2 (after)             │
                    │    └── post-processing            │
                    │    │                              │
                    │  Middleware 1 (after)             │
                    │    └── add headers, log           │
                    │                                   │
  Response <─────  │  Final Response                    │
                    └─────────────────────────────────┘
```

The onion model means every middleware acts twice:
1. **Before `await next()`** — validate, transform, short-circuit (auth returns 401)
2. **After `await next()`** — modify response headers, log timing, compress

This differs from Express's linear chain where middleware only acts before the handler.

**Route matching:** Trie-based (tree structure). O(path length) lookup, not O(route count).
This means 1000 routes perform identically to 10 routes for matching speed.

**Context lifecycle:** One `Context` object per request. Created fresh. Not pooled.
Variables set via `c.set()` are request-scoped and garbage-collected after response.

## Industry Expert

**Production deployment on Node.js (EOS pattern):**
```typescript
import { serve } from '@hono/node-server'
const server = serve({
  fetch: app.fetch,
  port: Number(process.env.PORT ?? 3000),
}, (info) => console.log(`Running on :${info.port}`))
```

**Structured error response convention (EOS):**
All error responses follow `{ error: string, message: string | object }`.
`error` is machine-readable (`'not_found'`, `'validation_error'`, `'unauthorized'`).
`message` is human-readable or Zod flatten output.

**Multi-tenant RLS pattern (EOS-specific):**
1. Auth middleware validates org via header, sets `c.set('orgId', ...)`
2. Route handler reads `c.get('orgId')` — never from request body
3. DB queries use `withOrg(orgId, tx => ...)` for RLS-scoped transactions
4. Never mix admin DB and tenant DB in the same handler

**Performance tuning:**
- Use `c.json()` over `new Response(JSON.stringify(...))` — Hono optimizes serialization
- Never call `c.req.json()` on GET routes — throws on empty body
- For large payloads, use `stream()` instead of buffering entire response
- Register `/health` before auth middleware to avoid unnecessary DB lookups
- Pre-compile TypeScript for production (`tsc` then `node dist/index.js`)

**Cloudflare Workers deployment (future EOS capability):**
```typescript
// Same app code, just change the export
export default app  // Workers/Pages
// No adapter needed — Hono IS a fetch handler
```

**Testing patterns:**
```typescript
// Unit test routes without HTTP
const res = await app.request('/health')
expect(res.status).toBe(200)

// Test with headers (auth)
const res = await app.request('/ventures', {
  headers: { 'x-org-id': 'valid-uuid-here' }
})

// Test POST with body
const res = await app.request('/outcomes', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'x-org-id': 'uuid' },
  body: JSON.stringify({ interaction_id: 'uuid', outcome_type: 'positive' })
})
```

---

## EOS Usage Patterns

- 7 route files under `saas/api/routes/` covering ventures, skills, interactions, outcomes, approvals, agent (AI bridge), and events
- Custom auth middleware using `x-org-id` header with UUID validation and DB lookup
- Manual Zod `safeParse` for input validation (could migrate to `@hono/zod-validator`)
- Python bridge (`saas/api/lib/python_bridge.ts`) spawns child process for AI operations
- All DB queries use `withOrg()` for Neon RLS scoping
- `tsx watch` for development, `tsx` for production start
- Health check endpoint exempt from auth

## Gotchas

1. **Body stream is single-read.** Calling `c.req.json()` then `c.req.text()` on the same request fails — the body is consumed on first read. If you need both parsed and raw body (e.g., webhooks), read `text()` first and `JSON.parse()` manually.

2. **`tsx` is not production-optimized.** EOS uses `tsx api/index.ts` for production start. For better cold start and memory, pre-compile with `tsc` and run `node dist/index.js`.

3. **Middleware registered after routes does not apply.** If you add `app.use('/x/*', auth)` after `app.route('/x', router)`, auth will not run. EOS correctly registers all `app.use()` before `app.route()`.

4. **`withOrg()` failures inside route handlers.** If the Neon connection drops, the error propagates to `app.onError()`. Make sure the global error handler logs enough context to debug DB issues.

5. **`c.req.param()` returns empty string for missing optional params.** Use `c.req.param('id') || null` if you need to distinguish missing from empty.
