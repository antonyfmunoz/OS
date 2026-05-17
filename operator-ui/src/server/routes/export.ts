/**
 * Export trigger routes for operator-ui.
 * POST /api/export/fire — dispatches export to Windows via bridge.
 * POST /api/export/mfa — routes MFA response to Windows via bridge.
 */

import { Hono } from 'hono'

const AUTH_TOKEN = process.env.CLAUDE_CODE_OAUTH_TOKEN ?? ''

const BRIDGE_IP = process.env.EOS_LOCAL_BRIDGE_IP ?? '100.74.199.102'
const BRIDGE_PORT = process.env.EOS_LOCAL_BRIDGE_PORT ?? '8766'
const BRIDGE_URL = `http://${BRIDGE_IP}:${BRIDGE_PORT}`

export const exportRouter = new Hono()

function authCheck(c: any): boolean {
  if (!AUTH_TOKEN) return true
  const header = c.req.header('x-auth-token') || ''
  return header === AUTH_TOKEN
}

exportRouter.post('/fire', async (c) => {
  if (!authCheck(c)) return c.json({ error: 'unauthorized' }, 401)

  const body = await c.req.json<{ service?: string; dry_run?: boolean }>()
  const service = body.service?.toLowerCase() ?? ''

  if (!['claude', 'chatgpt', 'instagram', 'all'].includes(service)) {
    return c.json({ error: 'invalid service', valid: ['claude', 'chatgpt', 'instagram', 'all'] }, 400)
  }

  try {
    const resp = await fetch(`${BRIDGE_URL}/fire-export`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type: 'fire_export', service, dry_run: body.dry_run ?? false }),
      signal: AbortSignal.timeout(15000),
    })

    const result = await resp.json()
    return c.json(result, resp.ok ? 200 : 502)
  } catch (err: any) {
    return c.json({ error: 'bridge_unreachable', message: err.message }, 502)
  }
})

exportRouter.post('/mfa', async (c) => {
  if (!authCheck(c)) return c.json({ error: 'unauthorized' }, 401)

  const body = await c.req.json<{ service?: string; code?: string; response_type?: string }>()
  const service = body.service?.toLowerCase() ?? ''
  const code = body.code?.trim() ?? ''

  if (!service || !code) {
    return c.json({ error: 'missing service or code' }, 400)
  }

  const responseType = ['approved', 'approve', 'yes'].includes(code.toLowerCase()) ? 'approved' : 'code'

  try {
    const resp = await fetch(`${BRIDGE_URL}/mfa-response`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ service, code, response_type: responseType }),
      signal: AbortSignal.timeout(10000),
    })

    const result = await resp.json()
    return c.json(result, resp.ok ? 200 : 502)
  } catch (err: any) {
    return c.json({ error: 'bridge_unreachable', message: err.message }, 502)
  }
})

exportRouter.get('/status', async (c) => {
  if (!authCheck(c)) return c.json({ error: 'unauthorized' }, 401)

  try {
    const resp = await fetch(`${BRIDGE_URL}/health`, {
      signal: AbortSignal.timeout(3000),
    })
    const data = await resp.json()
    return c.json({ bridge: 'reachable', ...data })
  } catch {
    return c.json({ bridge: 'unreachable' })
  }
})
