import { Hono } from 'hono'
import { z } from 'zod'
import type { Env } from '../../../transports/api/http/types.js'
import { callBridge } from '../../../transports/api/http/lib/python_bridge.js'

const router = new Hono<Env>()

const RunSchema = z.object({
  task_type:  z.enum(['SCORE', 'CLASSIFY', 'ANALYZE', 'GENERATE', 'SUMMARIZE']),
  prompt:     z.string().min(1),
  venture_id: z.string().optional(),
  skill_name: z.string().optional(),
  agent:      z.string().optional(),
})

const TeamSchema = z.object({
  team:       z.enum(['sales', 'research', 'content']),
  sub_agent:  z.string().min(1),
  prompt:     z.string().min(1),
  venture_id: z.string(),
  username:   z.string().optional(),
})

// POST /agent/run
router.post('/run', async (c) => {
  const parsed = RunSchema.safeParse(await c.req.json())
  if (!parsed.success) {
    return c.json({ error: 'validation_error', message: parsed.error.flatten() }, 400)
  }

  const result = await callBridge({ action: 'agent.run', payload: parsed.data })
  if (!result.success) return c.json({ error: 'bridge_error', message: result.error }, 502)
  return c.json(result.data)
})

// POST /agent/team
router.post('/team', async (c) => {
  const parsed = TeamSchema.safeParse(await c.req.json())
  if (!parsed.success) {
    return c.json({ error: 'validation_error', message: parsed.error.flatten() }, 400)
  }

  const result = await callBridge({ action: 'agent.team', payload: parsed.data })
  if (!result.success) return c.json({ error: 'bridge_error', message: result.error }, 502)
  return c.json(result.data)
})

// POST /agent/brief
router.post('/brief', async (c) => {
  const result = await callBridge({ action: 'orchestrator.brief', payload: {} })
  if (!result.success) return c.json({ error: 'bridge_error', message: result.error }, 502)
  return c.json(result.data)
})

export default router
