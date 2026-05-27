import { Hono } from 'hono'
import { eq, desc } from 'drizzle-orm'
import type { Env } from '../types.js'
import { withOrg } from '../../db/client.js'
import { interactions } from '../../db/schema.js'

const router = new Hono<Env>()

router.get('/', async (c) => {
  const orgId = c.get('orgId')
  const rows = await withOrg(orgId, (tx) =>
    tx.select({
      id: interactions.id,
      title: interactions.taskType,
      status: interactions.taskType,
      agent: interactions.modelUsed,
      priority: interactions.taskType,
      created_at: interactions.createdAt,
      updated_at: interactions.createdAt,
    }).from(interactions)
      .where(eq(interactions.orgId, orgId))
      .orderBy(desc(interactions.createdAt))
      .limit(50)
  )

  const tasks = rows.map((r) => ({
    id: r.id,
    title: r.title ?? 'task',
    status: 'completed' as const,
    agent: r.agent ?? 'system',
    priority: 'normal',
    created_at: r.created_at?.toISOString() ?? new Date().toISOString(),
    updated_at: r.updated_at?.toISOString() ?? new Date().toISOString(),
  }))

  return c.json(tasks)
})

export default router
