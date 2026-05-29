import { Hono } from 'hono'
import type { Env } from '../types.js'
import { callOrganism } from '../lib/python_bridge.js'

const router = new Hono<Env>()

router.post('/converse', async (c) => {
  const body = await c.req.json() as { content: string }
  const content = body.content?.trim()
  if (!content) {
    return c.json({ error: 'validation_error', message: 'content is required' }, 400)
  }

  const result = await callOrganism('organism.converse', { content })

  const data = result.data as Record<string, unknown> | undefined
  return c.json({
    message_id: data?.message_id ?? `dex-${Date.now()}`,
    response: result.success
      ? (data?.response ?? 'No response')
      : `Error: ${result.error}`,
    timestamp: data?.timestamp ?? new Date().toISOString(),
  })
})

router.post('/send', async (c) => {
  const body = await c.req.json().catch(() => ({})) as Record<string, unknown>
  const result = await callOrganism('organism.send_channel_message', body)
  if (!result.success) return c.json({ error: result.error }, 400)
  return c.json(result.data)
})

router.get('/history', async (c) => {
  const result = await callOrganism('organism.chat_history', { limit: 50 })
  if (!result.success) return c.json([])
  const messages = (result.data as Array<Record<string, unknown>>) ?? []
  return c.json(messages.map((m) => ({
    id: m.id,
    sender: m.sender,
    content: m.intent === 'report'
      ? `**${(m.payload as Record<string, unknown>)?.title ?? 'Report'}**\n${(m.payload as Record<string, unknown>)?.summary ?? ''}`
      : (m.payload as Record<string, unknown>)?.content ?? m.intent ?? '',
    response: m.sender === 'system' ? null : undefined,
    timestamp: m.created_at,
  })))
})

export default router
