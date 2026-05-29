import { Hono } from 'hono'
import { eq, desc } from 'drizzle-orm'
import { z } from 'zod'
import type { Env } from '../../../transports/api/http/types.js'
import { withOrg } from '../../../transports/api/http/db/client.js'
import { events } from '../../db/schema.js'

const router = new Hono<Env>()

const PublishSchema = z.object({
  event_type:   z.string().min(1),
  payload_json: z.record(z.unknown()).optional(),
  handled_by:   z.string().optional(),
})

router.get('/', async (c) => {
  const orgId = c.get('orgId')
  const rows = await withOrg(orgId, (tx) =>
    tx.select().from(events).where(eq(events.orgId, orgId)).orderBy(desc(events.createdAt)).limit(100)
  )
  return c.json({ events: rows, count: rows.length })
})

router.post('/publish', async (c) => {
  const orgId  = c.get('orgId')
  const parsed = PublishSchema.safeParse(await c.req.json())
  if (!parsed.success) {
    return c.json({ error: 'validation_error', message: parsed.error.flatten() }, 400)
  }

  const [row] = await withOrg(orgId, (tx) =>
    tx.insert(events).values({
      orgId,
      eventType:   parsed.data.event_type,
      payloadJson: parsed.data.payload_json ?? {},
      handledBy:   parsed.data.handled_by,
    }).returning()
  )
  return c.json({ event: row }, 201)
})

export default router
