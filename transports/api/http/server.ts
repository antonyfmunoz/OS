import { Hono } from 'hono'
import { serve } from '@hono/node-server'
import 'dotenv/config'
import type { Env } from './types.js'
import { authMiddleware } from './middleware/auth.js'
import systemRouter     from './routes/system.js'
import organismRouter   from './routes/organism.js'
import governanceRouter from './routes/governance.js'
import chatRouter       from './routes/chat.js'
import knowledgeRouter  from './routes/knowledge.js'
import executionRouter  from './routes/execution.js'
import settingsRouter   from './routes/settings.js'

const app = new Hono<Env>()

app.get('/health', (c) => c.json({ status: 'ok', ts: new Date().toISOString() }))
app.route('/', systemRouter)

app.use('/organism/*',   authMiddleware)
app.use('/governance',   authMiddleware)
app.use('/governance/*', authMiddleware)
app.use('/chat/*',       authMiddleware)
app.use('/ide/*',        authMiddleware)
app.use('/observations', authMiddleware)
app.use('/memory',       authMiddleware)
app.use('/tracking',     authMiddleware)

app.route('/organism',   organismRouter)
app.route('/governance', governanceRouter)
app.route('/chat',       chatRouter)
app.route('/',           knowledgeRouter)
app.route('/execution',  executionRouter)
app.route('/settings',   settingsRouter)

app.notFound((c) =>
  c.json({ error: 'not_found', message: `${c.req.method} ${c.req.path}` }, 404)
)

app.onError((err, c) => {
  console.error('[UMH API error]', err)
  return c.json({ error: 'internal_error', message: err.message }, 500)
})

const PORT = Number(process.env.UMH_API_PORT ?? process.env.PORT ?? 3000)

serve({ fetch: app.fetch, port: PORT }, () => {
  console.log(`UMH API running on http://localhost:${PORT}`)
})

export { app }
