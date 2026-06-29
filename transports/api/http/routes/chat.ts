import { Hono } from 'hono'
import type { Env } from '../types.js'
import { callOrganism } from '../lib/python_bridge.js'
import { governedMutation } from '../lib/governed_bridge.js'

const router = new Hono<Env>()

router.post('/converse', async (c) => {
  const body = await c.req.json() as { content: string }
  const content = body.content?.trim()
  if (!content) {
    return c.json({ error: 'validation_error', message: 'content is required' }, 400)
  }

  const result = await governedMutation({
    mutation_name: 'conversation_send',
    intent: `converse: ${content.slice(0, 100)}`,
    payload: { content },
  })
  return c.json(result)
})

router.post('/send', async (c) => {
  const body = await c.req.json().catch(() => ({})) as Record<string, unknown>
  const result = await governedMutation({
    mutation_name: 'channel_message_send',
    intent: 'send channel message',
    payload: body,
  })
  return c.json(result)
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
