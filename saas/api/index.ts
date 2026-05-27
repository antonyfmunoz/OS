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
import systemRouter       from './routes/system.js'
import tasksRouter        from './routes/tasks.js'
import agentsRouter       from './routes/agents.js'
import organismRouter     from './routes/organism.js'
import workflowsRouter    from './routes/workflows.js'
import activityRouter     from './routes/activity.js'
import executionRouter    from './routes/execution.js'
import knowledgeRouter    from './routes/knowledge.js'
import settingsRouter     from './routes/settings.js'
import governanceRouter   from './routes/governance.js'
import analyticsRouter    from './routes/analytics.js'
import dexRouter          from './routes/dex.js'

const app = new Hono<Env>()

// ── Health ────────────────────────────────────────────────────────────────────
app.get('/health', (c) => c.json({ status: 'ok', ts: new Date().toISOString() }))

// ── System routes (no auth — runtime telemetry) ─────────────────────────────
app.route('/',             systemRouter)

// ── Auth middleware on all tenant routes ─────────────────────────────────────
app.use('/ventures/*',     authMiddleware)
app.use('/skills/*',       authMiddleware)
app.use('/interactions/*', authMiddleware)
app.use('/outcomes/*',     authMiddleware)
app.use('/approvals/*',    authMiddleware)
app.use('/agent/*',        authMiddleware)
app.use('/events/*',       authMiddleware)
app.use('/tasks/*',        authMiddleware)
app.use('/agents/*',       authMiddleware)
app.use('/organism/*',     authMiddleware)
app.use('/workflows/*',    authMiddleware)
app.use('/activity/*',     authMiddleware)
app.use('/execution/*',    authMiddleware)
app.use('/observations',   authMiddleware)
app.use('/memory',         authMiddleware)
app.use('/tracking',       authMiddleware)
app.use('/settings',       authMiddleware)
app.use('/settings/*',     authMiddleware)
app.use('/governance',     authMiddleware)
app.use('/governance/*',   authMiddleware)
app.use('/analytics',      authMiddleware)
app.use('/analytics/*',    authMiddleware)
app.use('/eos/*',          authMiddleware)
app.use('/dex/*',          authMiddleware)

// ── Routes ────────────────────────────────────────────────────────────────────
app.route('/ventures',     venturesRouter)
app.route('/skills',       skillsRouter)
app.route('/interactions', interactionsRouter)
app.route('/outcomes',     outcomesRouter)
app.route('/approvals',    approvalsRouter)
app.route('/agent',        agentRouter)
app.route('/events',       eventsRouter)
app.route('/tasks',        tasksRouter)
app.route('/agents',       agentsRouter)
app.route('/organism',     organismRouter)
app.route('/workflows',    workflowsRouter)
app.route('/activity',     activityRouter)
app.route('/execution',    executionRouter)
app.route('/',             knowledgeRouter)
app.route('/settings',     settingsRouter)
app.route('/governance',   governanceRouter)
app.route('/analytics',    analyticsRouter)
app.route('/eos',          analyticsRouter)
app.route('/dex',          dexRouter)

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
