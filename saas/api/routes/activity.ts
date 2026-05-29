import { Hono } from 'hono'
import { eq, desc } from 'drizzle-orm'
import type { Env } from '../../../transports/api/http/types.js'
import { withOrg } from '../../../transports/api/http/db/client.js'
import { events } from '../../db/schema.js'

const router = new Hono<Env>()

router.get('/stream', async (c) => {
  const orgId = c.get('orgId')
  const limit = Math.min(Number(c.req.query('limit') ?? 100), 500)

  const rows = await withOrg(orgId, (tx) =>
    tx.select().from(events)
      .where(eq(events.orgId, orgId))
      .orderBy(desc(events.createdAt))
      .limit(limit)
  )

  return c.json(rows.map((e) => ({
    id: e.id,
    type: e.eventType,
    source: e.handledBy ?? 'system',
    summary: e.eventType,
    timestamp: e.createdAt?.toISOString() ?? new Date().toISOString(),
    severity: 'info' as const,
    payload: e.payloadJson,
  })))
})

export default router
