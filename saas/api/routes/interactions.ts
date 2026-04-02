import { Hono } from 'hono'
import { eq, and, desc } from 'drizzle-orm'
import { sql } from 'drizzle-orm'
import type { Env } from '../types.js'
import { withOrg } from '../../db/client.js'
import { interactions } from '../../db/schema.js'

const router = new Hono<Env>()

// GET /interactions?venture_id=xxx  — recent 50, optionally filtered
router.get('/', async (c) => {
  const orgId     = c.get('orgId')
  const ventureId = c.req.query('venture_id')

  const rows = await withOrg(orgId, (tx) => {
    const q = tx.select().from(interactions).orderBy(desc(interactions.createdAt)).limit(50)
    return ventureId
      ? q.where(and(eq(interactions.orgId, orgId), eq(interactions.ventureId, ventureId)))
      : q.where(eq(interactions.orgId, orgId))
  })

  return c.json({ interactions: rows, count: rows.length })
})

// GET /interactions/stats — aggregate by venture + skill
router.get('/stats', async (c) => {
  const orgId = c.get('orgId')

  const rows = await withOrg(orgId, (tx) => tx.execute(sql`
    SELECT
      i.venture_id,
      i.skill_id,
      COUNT(*)::int                                             AS total_calls,
      COALESCE(SUM((i.tokens_json->>'total')::int), 0)::int    AS total_tokens,
      COALESCE(SUM((i.tokens_json->>'cost_usd')::float), 0)    AS total_cost_usd,
      MAX(i.created_at)                                         AS last_run
    FROM interactions i
    WHERE i.org_id = ${orgId}
    GROUP BY i.venture_id, i.skill_id
    ORDER BY total_calls DESC
  `))

  return c.json({ stats: rows.rows })
})

export default router
