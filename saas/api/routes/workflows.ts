import { Hono } from 'hono'
import { eq } from 'drizzle-orm'
import type { Env } from '../../../transports/api/http/types.js'
import { withOrg } from '../../../transports/api/http/db/client.js'
import { workflows } from '../../db/schema.js'

const router = new Hono<Env>()

router.get('/', async (c) => {
  const orgId = c.get('orgId')
  const rows = await withOrg(orgId, (tx) =>
    tx.select().from(workflows).where(eq(workflows.orgId, orgId))
  )

  return c.json(rows.map((w) => ({
    id: w.id,
    name: w.name,
    schedule: w.triggerType,
    last_run: null,
    last_status: w.isActive ? 'active' : 'inactive',
    run_count: 0,
    avg_duration_ms: 0,
  })))
})

router.post('/:id/trigger', async (c) => {
  return c.json({ ok: true, triggered: c.req.param('id') })
})

export default router
