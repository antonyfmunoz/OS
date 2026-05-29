import { Hono } from 'hono'
import { eq, and } from 'drizzle-orm'
import { z } from 'zod'
import type { Env } from '../../../transports/api/http/types.js'
import { withOrg } from '../../../transports/api/http/db/client.js'
import { ventures } from '../../db/schema.js'

const router = new Hono<Env>()

const PatchSchema = z.object({
  monthly_revenue: z.coerce.number().nonnegative().optional(),
  monthly_target:  z.coerce.number().nonnegative().optional(),
  stage:           z.enum(['idea', 'pre_revenue', 'early', 'growth', 'scale']).optional(),
  config_json:     z.record(z.unknown()).optional(),
}).strict()

// GET /ventures
router.get('/', async (c) => {
  const orgId = c.get('orgId')
  const rows = await withOrg(orgId, (tx) =>
    tx.select().from(ventures).where(eq(ventures.orgId, orgId)).orderBy(ventures.createdAt)
  )
  return c.json({ ventures: rows })
})

// GET /ventures/:id
router.get('/:id', async (c) => {
  const orgId = c.get('orgId')
  const id    = c.req.param('id')
  const [row] = await withOrg(orgId, (tx) =>
    tx.select().from(ventures).where(and(eq(ventures.id, id), eq(ventures.orgId, orgId))).limit(1)
  )
  if (!row) return c.json({ error: 'not_found', message: 'venture not found' }, 404)
  return c.json({ venture: row })
})

// PATCH /ventures/:id
router.patch('/:id', async (c) => {
  const orgId = c.get('orgId')
  const id    = c.req.param('id')

  const parsed = PatchSchema.safeParse(await c.req.json())
  if (!parsed.success) {
    return c.json({ error: 'validation_error', message: parsed.error.flatten() }, 400)
  }

  const updates: Record<string, unknown> = {}
  if (parsed.data.monthly_revenue !== undefined) updates.monthlyRevenue = String(parsed.data.monthly_revenue)
  if (parsed.data.monthly_target  !== undefined) updates.monthlyTarget  = String(parsed.data.monthly_target)
  if (parsed.data.stage           !== undefined) updates.stage          = parsed.data.stage
  if (parsed.data.config_json     !== undefined) updates.configJson     = parsed.data.config_json

  if (Object.keys(updates).length === 0) {
    return c.json({ error: 'validation_error', message: 'no fields to update' }, 400)
  }

  const [updated] = await withOrg(orgId, (tx) =>
    tx.update(ventures).set(updates).where(eq(ventures.id, id)).returning()
  )
  if (!updated) return c.json({ error: 'not_found', message: 'venture not found' }, 404)
  return c.json({ venture: updated })
})

export default router
