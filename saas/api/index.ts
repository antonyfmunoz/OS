import { Hono } from 'hono'
import { serve } from '@hono/node-server'
import 'dotenv/config'

// ── UMH platform infrastructure (from transports/api/http) ──────────────────
import type { Env } from '../../transports/api/http/types.js'
import { authMiddleware } from '../../transports/api/http/middleware/auth.js'
import systemRouter       from '../../transports/api/http/routes/system.js'
import organismRouter     from '../../transports/api/http/routes/organism.js'
import governanceRouter   from '../../transports/api/http/routes/governance.js'
import chatRouter         from '../../transports/api/http/routes/chat.js'
import knowledgeRouter    from '../../transports/api/http/routes/knowledge.js'
import executionRouter    from '../../transports/api/http/routes/execution.js'
import settingsRouter     from '../../transports/api/http/routes/settings.js'
import configRouter       from '../../transports/api/http/routes/config.js'

// ── EOS projection routes ───────────────────────────────────────────────────
import venturesRouter     from './routes/ventures.js'
import skillsRouter       from './routes/skills.js'
import interactionsRouter from './routes/interactions.js'
import outcomesRouter     from './routes/outcomes.js'
import approvalsRouter    from './routes/approvals.js'
import agentRouter        from './routes/agent.js'
import eventsRouter       from './routes/events.js'
import tasksRouter        from './routes/tasks.js'
import agentsRouter       from './routes/agents.js'
import workflowsRouter    from './routes/workflows.js'
import activityRouter     from './routes/activity.js'
import analyticsRouter    from './routes/analytics.js'

const app = new Hono<Env>()

// ── Health ────────────────────────────────────────────────────────────────────
app.get('/health', (c) => c.json({ status: 'ok', ts: new Date().toISOString() }))

// ── System routes (no auth — runtime telemetry) ─────────────────────────────
app.route('/',             systemRouter)

// ── Auth middleware ──────────────────────────────────────────────────────────
// UMH substrate routes
app.use('/organism/*',     authMiddleware)
app.use('/governance',     authMiddleware)
app.use('/governance/*',   authMiddleware)
app.use('/chat/*',         authMiddleware)
app.use('/config',         authMiddleware)
app.use('/config/*',       authMiddleware)
app.use('/ide/*',          authMiddleware)
app.use('/observations',   authMiddleware)
app.use('/memory',         authMiddleware)
app.use('/tracking',       authMiddleware)

// EOS projection routes
app.use('/eos/*',          authMiddleware)
app.use('/ventures/*',     authMiddleware)
app.use('/skills/*',       authMiddleware)
app.use('/interactions/*', authMiddleware)
app.use('/outcomes/*',     authMiddleware)
app.use('/approvals/*',    authMiddleware)
app.use('/agent/*',        authMiddleware)
app.use('/events/*',       authMiddleware)
app.use('/tasks/*',        authMiddleware)
app.use('/agents/*',       authMiddleware)
app.use('/workflows/*',    authMiddleware)
app.use('/activity/*',     authMiddleware)
app.use('/execution/*',    authMiddleware)
app.use('/settings',       authMiddleware)
app.use('/settings/*',     authMiddleware)
app.use('/analytics',      authMiddleware)
app.use('/analytics/*',    authMiddleware)

// ── UMH substrate routes ─────────────────────────────────────────────────────
app.route('/organism',     organismRouter)
app.route('/governance',   governanceRouter)
app.route('/chat',         chatRouter)
app.route('/',             knowledgeRouter)
app.route('/execution',    executionRouter)
app.route('/settings',     settingsRouter)
app.route('/config',       configRouter)

// ── EOS projection routes — canonical /eos/ prefix ───────────────────────────
const eos = new Hono<Env>()
eos.route('/ventures',     venturesRouter)
eos.route('/skills',       skillsRouter)
eos.route('/interactions', interactionsRouter)
eos.route('/outcomes',     outcomesRouter)
eos.route('/approvals',    approvalsRouter)
eos.route('/agent',        agentRouter)
eos.route('/events',       eventsRouter)
eos.route('/tasks',        tasksRouter)
eos.route('/agents',       agentsRouter)
eos.route('/workflows',    workflowsRouter)
eos.route('/activity',     activityRouter)
eos.route('/analytics',    analyticsRouter)
app.route('/eos',          eos)

// ── EOS projection routes — flat paths (backward compat) ────────────────────
app.route('/ventures',     venturesRouter)
app.route('/skills',       skillsRouter)
app.route('/interactions', interactionsRouter)
app.route('/outcomes',     outcomesRouter)
app.route('/approvals',    approvalsRouter)
app.route('/agent',        agentRouter)
app.route('/events',       eventsRouter)
app.route('/tasks',        tasksRouter)
app.route('/agents',       agentsRouter)
app.route('/workflows',    workflowsRouter)
app.route('/activity',     activityRouter)
app.route('/analytics',    analyticsRouter)

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
  console.log(`UMH API running on http://localhost:${PORT}`)
})
