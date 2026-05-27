import { Hono } from 'hono'
import type { Env } from '../types.js'

const router = new Hono<Env>()

router.get('/', (c) => {
  return c.json({
    model_routing: [
      { provider: 'anthropic', priority: 0, enabled: true },
      { provider: 'google', priority: 1, enabled: true },
      { provider: 'groq', priority: 2, enabled: true },
      { provider: 'ollama', priority: 3, enabled: true },
    ],
    governance: { auto_approve_low: true, critical_block: true },
    notifications: { discord: true, file: true },
  })
})

router.patch('/', async (c) => {
  return c.json({ ok: true })
})

export default router
