import { Hono } from 'hono'
import { eq } from 'drizzle-orm'
import type { Env } from '../types.js'
import { withOrg } from '../../db/client.js'
import { agents } from '../../db/schema.js'

const router = new Hono<Env>()

router.get('/agents', async (c) => {
  const orgId = c.get('orgId')
  const rows = await withOrg(orgId, (tx) =>
    tx.select().from(agents).where(eq(agents.orgId, orgId))
  )

  return c.json(rows.map((a) => ({
    id: a.id,
    name: a.name,
    status: a.isActive ? 'active' : 'inactive',
    skills: Array.isArray(a.tools) ? (a.tools as string[]) : [],
    role: a.agentType,
    last_action: '',
    last_active: a.createdAt?.toISOString() ?? '',
  })))
})

router.get('/deliverables', async (c) => {
  return c.json([])
})

router.post('/control', async (c) => {
  return c.json({ ok: true })
})

router.post('/handoff', async (c) => {
  return c.json({ ok: true, handoff: 'completed' })
})

router.post('/parallel', async (c) => {
  return c.json({ ok: true, results: [] })
})

router.get('/delegations', (c) => {
  return c.json({ followups: [] })
})

export default router
