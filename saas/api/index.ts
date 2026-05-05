import { Hono } from 'hono'
import { serve } from '@hono/node-server'
import 'dotenv/config'
import type { Env } from './types.js'
import { authMiddleware } from './middleware/auth.js'
import venturesRouter     from './routes/ventures.js'
import skillsRouter       from './routes/skills.js'
import interactionsRouter from './routes/interactions.js'
import outcomesRouter     from './routes/outcomes.js'
import approvalsRouter    from './routes/approvals.js'
import agentRouter        from './routes/agent.js'
import eventsRouter       from './routes/events.js'

const app = new Hono<Env>()

// ── Health ────────────────────────────────────────────────────────────────────
app.get('/health', (c) => c.json({ status: 'ok', ts: new Date().toISOString() }))

// ── Auth middleware on all tenant routes ─────────────────────────────────────
app.use('/ventures/*',     authMiddleware)
app.use('/skills/*',       authMiddleware)
app.use('/interactions/*', authMiddleware)
app.use('/outcomes/*',     authMiddleware)
app.use('/approvals/*',    authMiddleware)
app.use('/agent/*',        authMiddleware)
app.use('/events/*',       authMiddleware)

// ── Routes ────────────────────────────────────────────────────────────────────
app.route('/ventures',     venturesRouter)
app.route('/skills',       skillsRouter)
app.route('/interactions', interactionsRouter)
app.route('/outcomes',     outcomesRouter)
app.route('/approvals',    approvalsRouter)
app.route('/agent',        agentRouter)
app.route('/events',       eventsRouter)

// ── Error handlers ────────────────────────────────────────────────────────────
app.notFound((c) =>
  c.json({ error: 'not_found', message: `${c.req.method} ${c.req.path}` }, 404)
)

app.onError((err, c) => {
  console.error('[API error]', err)
  return c.json({ error: 'internal_error', message: err.message }, 500)
})

// ── Server ────────────────────────────────────────────────────────────────────
const PORT = Number(process.env.PORT ?? 3000)

serve({ fetch: app.fetch, port: PORT }, () => {
  console.log(`eos-saas API running on http://localhost:${PORT}`)
})
