import { Hono } from 'hono'
import type { Env } from '../types.js'
import { callBridge } from '../lib/python_bridge.js'

const router = new Hono<Env>()

router.post('/converse', async (c) => {
  const body = await c.req.json() as { content: string }
  const content = body.content?.trim()
  if (!content) {
    return c.json({ error: 'validation_error', message: 'content is required' }, 400)
  }

  const result = await callBridge({
    action: 'agent.run',
    payload: {
      prompt: content,
      task_type: 'GENERATE',
      channel: 'cockpit_chat',
    },
  })

  return c.json({
    message_id: `dex-${Date.now()}`,
    response: result.success
      ? (result.data as Record<string, unknown>)?.output ?? 'No response'
      : `Error: ${result.error}`,
    timestamp: new Date().toISOString(),
  })
})

router.get('/history', (c) => {
  return c.json([])
})

export default router
