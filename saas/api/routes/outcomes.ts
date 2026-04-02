import { Hono } from 'hono'
import { sql } from 'drizzle-orm'
import { z } from 'zod'
import type { Env } from '../types.js'
import { withOrg } from '../../db/client.js'
import { outcomes } from '../../db/schema.js'

const router = new Hono<Env>()

const OutcomeSchema = z.object({
  interaction_id: z.string().uuid(),
  outcome_type:   z.enum(['positive', 'negative', 'neutral', 'skipped']),
  score:          z.number().min(0).max(10).optional(),
  notes:          z.string().optional(),
})

// POST /outcomes — log an outcome for an interaction
router.post('/', async (c) => {
  const orgId  = c.get('orgId')
  const parsed = OutcomeSchema.safeParse(await c.req.json())
  if (!parsed.success) {
    return c.json({ error: 'validation_error', message: parsed.error.flatten() }, 400)
  }

  const [row] = await withOrg(orgId, (tx) =>
    tx.insert(outcomes).values({
      orgId,
      interactionId: parsed.data.interaction_id,
      outcomeType:   parsed.data.outcome_type,
      score:         parsed.data.score !== undefined ? String(parsed.data.score) : undefined,
      notes:         parsed.data.notes,
    }).returning()
  )

  return c.json({ outcome: row }, 201)
})

// GET /outcomes/skill-performance — success rate per skill
router.get('/skill-performance', async (c) => {
  const orgId = c.get('orgId')
  const rows = await withOrg(orgId, (tx) => tx.execute(sql`
    SELECT
      i.skill_id,
      s.name                                                         AS skill_name,
      COUNT(o.id)::int                                               AS total_outcomes,
      COUNT(CASE WHEN o.outcome_type = 'positive' THEN 1 END)::int  AS positive,
      COUNT(CASE WHEN o.outcome_type = 'negative' THEN 1 END)::int  AS negative,
      ROUND(
        COUNT(CASE WHEN o.outcome_type = 'positive' THEN 1 END)::numeric
        / NULLIF(COUNT(o.id), 0) * 100, 1
      )::float                                                       AS success_rate_pct
    FROM interactions i
    INNER JOIN outcomes o ON o.interaction_id = i.id
    LEFT  JOIN skills   s ON s.id = i.skill_id
    WHERE i.org_id = ${orgId}
      AND i.skill_id IS NOT NULL
    GROUP BY i.skill_id, s.name
    ORDER BY success_rate_pct DESC NULLS LAST
  `))

  return c.json({ skill_performance: rows.rows })
})

export default router
