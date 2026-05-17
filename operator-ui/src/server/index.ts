/**
 * Operator UI Backend
 * Serves /api/code endpoints: read, write, execute, list
 * Delegates to filesystem operations within the mounted /app volume.
 */

import { Hono } from 'hono'
import { serve } from '@hono/node-server'
import { cors } from 'hono/cors'
import { codeRouter } from './routes/code.js'
import { exportRouter } from './routes/export.js'

const app = new Hono()

// CORS for Vite dev server
app.use('*', cors({ origin: ['http://localhost:5173', 'http://localhost:8091'] }))

// Health check
app.get('/api/health', (c) => c.json({ status: 'ok', service: 'operator-ui', ts: new Date().toISOString() }))

// Code engine routes
app.route('/api/code', codeRouter)

// Export trigger routes
app.route('/api/export', exportRouter)

// 404
app.notFound((c) => c.json({ error: 'not_found', path: c.req.path }, 404))

// Error handler
app.onError((err, c) => {
  console.error('[operator-ui]', err)
  return c.json({ error: 'internal_error', message: err.message }, 500)
})

const PORT = Number(process.env.PORT ?? 8091)

serve({ fetch: app.fetch, port: PORT }, () => {
  console.log(`[operator-ui] API server running on http://localhost:${PORT}`)
})
