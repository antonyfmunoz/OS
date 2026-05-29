import { Hono } from 'hono'
import { eq, and } from 'drizzle-orm'
import { z } from 'zod'
import type { Env } from '../../../transports/api/http/types.js'
import { withOrg } from '../../../transports/api/http/db/client.js'
import { skills, skillVersions } from '../../db/schema.js'
import { callBridge } from '../../../transports/api/http/lib/python_bridge.js'

const router = new Hono<Env>()

const PatchSchema = z.object({
  content:          z.string().min(1).optional(),
  fitness_function: z.string().optional(),
}).strict()

// GET /skills
router.get('/', async (c) => {
  const orgId = c.get('orgId')
  const rows = await withOrg(orgId, (tx) =>
    tx.select({
      id: skills.id, name: skills.name,
      version: skills.version, fitnessFunction: skills.fitnessFunction,
      createdAt: skills.createdAt,
    }).from(skills).where(eq(skills.orgId, orgId)).orderBy(skills.name)
  )
  return c.json({ skills: rows })
})

// GET /skills/:id
router.get('/:id', async (c) => {
  const orgId = c.get('orgId')
  const [row] = await withOrg(orgId, (tx) =>
    tx.select().from(skills).where(and(eq(skills.id, c.req.param('id')), eq(skills.orgId, orgId))).limit(1)
  )
  if (!row) return c.json({ error: 'not_found', message: 'skill not found' }, 404)
  return c.json({ skill: row })
})

// PATCH /skills/:id — update content, bump version, archive old version
router.patch('/:id', async (c) => {
  const orgId = c.get('orgId')
  const id    = c.req.param('id')

  const parsed = PatchSchema.safeParse(await c.req.json())
  if (!parsed.success) {
    return c.json({ error: 'validation_error', message: parsed.error.flatten() }, 400)
  }

  const updated = await withOrg(orgId, async (tx) => {
    const [current] = await tx.select().from(skills).where(and(eq(skills.id, id), eq(skills.orgId, orgId))).limit(1)
    if (!current) return null

    const newVersion = current.version + 1
    const updates: Record<string, unknown> = { version: newVersion }
    if (parsed.data.content)          updates.content         = parsed.data.content
    if (parsed.data.fitness_function) updates.fitnessFunction = parsed.data.fitness_function

    const [out] = await tx.update(skills).set(updates).where(and(eq(skills.id, id), eq(skills.orgId, orgId))).returning()

    // Archive previous version
    await tx.insert(skillVersions).values({
      skillId: id, orgId,
      content: parsed.data.content ?? current.content,
      version: newVersion,
    })

    return out
  })

  if (!updated) return c.json({ error: 'not_found', message: 'skill not found' }, 404)
  return c.json({ skill: updated })
})

// POST /skills/:id/improve — AI suggests an improvement to the skill content
router.post('/:id/improve', async (c) => {
  const orgId = c.get('orgId')
  const id    = c.req.param('id')

  const [skill] = await withOrg(orgId, (tx) =>
    tx.select().from(skills).where(and(eq(skills.id, id), eq(skills.orgId, orgId))).limit(1)
  )
  if (!skill) return c.json({ error: 'not_found', message: 'skill not found' }, 404)

  const result = await callBridge({
    action: 'agent.run',
    payload: {
      task_type:  'ANALYZE',
      prompt:     `Analyze this skill and suggest specific improvements to make it more effective. Current version v${skill.version}.\n\n${skill.content}`,
      agent:      'skill_improver',
    },
  })

  if (!result.success) {
    return c.json({ error: 'bridge_error', message: result.error }, 502)
  }

  return c.json({
    skill_id:    id,
    skill_name:  skill.name,
    current_version: skill.version,
    suggestion:  (result.data as any).output,
    model_used:  (result.data as any).model_used,
  })
})

export default router
