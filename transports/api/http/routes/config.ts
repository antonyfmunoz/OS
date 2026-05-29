import { Hono } from 'hono'
import type { Env } from '../types.js'
import { callOrganism } from '../lib/python_bridge.js'

const router = new Hono<Env>()

router.get('/', async (c) => {
  const result = await callOrganism('config.get')
  if (!result.success) return c.json({ error: result.error }, 500)
  return c.json(result.data)
})

router.get('/:key', async (c) => {
  const key = c.req.param('key')
  const result = await callOrganism('config.get', { key })
  if (!result.success) return c.json({ error: result.error }, 500)
  return c.json(result.data)
})

router.patch('/', async (c) => {
  const body = await c.req.json().catch(() => ({})) as Record<string, unknown>
  const key = body.key as string | undefined
  const value = body.value
  const layer = (body.layer as string) || 'system'

  if (!key) return c.json({ error: 'key is required' }, 400)
  if (value === undefined) return c.json({ error: 'value is required' }, 400)

  const result = await callOrganism('config.set', { key, value, layer })
  if (!result.success) return c.json({ error: result.error }, 500)
  return c.json(result.data)
})

router.get('/layers/all', async (c) => {
  const result = await callOrganism('config.layers')
  if (!result.success) return c.json({ error: result.error }, 500)
  return c.json(result.data)
})

export default router
