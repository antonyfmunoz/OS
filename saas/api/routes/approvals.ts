import { Hono } from 'hono'
import { eq, and, sql } from 'drizzle-orm'
import type { Env } from '../types.js'
import { withOrg } from '../../db/client.js'
import { approvals } from '../../db/schema.js'

const router = new Hono<Env>()

router.get('/', async (c) => {
  const orgId = c.get('orgId')
  const rows = await withOrg(orgId, (tx) =>
    tx.select().from(approvals)
      .where(eq(approvals.orgId, orgId))
      .orderBy(approvals.createdAt)
  )
  return c.json(rows.map((r) => ({
    id: r.id,
    description: JSON.stringify(r.requestJson),
    risk_level: 'MEDIUM' as const,
    agent: 'system',
    created_at: r.createdAt?.toISOString() ?? '',
    status: r.status,
  })))
})

router.get('/pending', async (c) => {
  const orgId = c.get('orgId')
  const rows = await withOrg(orgId, (tx) =>
    tx.select().from(approvals)
      .where(and(eq(approvals.orgId, orgId), eq(approvals.status, 'pending')))
      .orderBy(approvals.createdAt)
  )
  return c.json({ approvals: rows, count: rows.length })
})

router.post('/:id/approve', async (c) => {
  const orgId  = c.get('orgId')
  const userId = c.get('userId')
  const [row]  = await withOrg(orgId, (tx) =>
    tx.update(approvals)
      .set({ status: 'approved', resolvedAt: sql`now()`, resolvedBy: userId })
      .where(and(eq(approvals.id, c.req.param('id')), eq(approvals.orgId, orgId)))
      .returning()
  )
  if (!row) return c.json({ error: 'not_found', message: 'approval not found' }, 404)
  return c.json({ approval: row })
})

router.post('/:id/reject', async (c) => {
  const orgId  = c.get('orgId')
  const userId = c.get('userId')
  const [row]  = await withOrg(orgId, (tx) =>
    tx.update(approvals)
      .set({ status: 'rejected', resolvedAt: sql`now()`, resolvedBy: userId })
      .where(and(eq(approvals.id, c.req.param('id')), eq(approvals.orgId, orgId)))
      .returning()
  )
  if (!row) return c.json({ error: 'not_found', message: 'approval not found' }, 404)
  return c.json({ approval: row })
})

router.post('/:id/deny', async (c) => {
  const orgId  = c.get('orgId')
  const userId = c.get('userId')
  const [row]  = await withOrg(orgId, (tx) =>
    tx.update(approvals)
      .set({ status: 'rejected', resolvedAt: sql`now()`, resolvedBy: userId })
      .where(and(eq(approvals.id, c.req.param('id')), eq(approvals.orgId, orgId)))
      .returning()
  )
  if (!row) return c.json({ error: 'not_found', message: 'approval not found' }, 404)
  return c.json({ approval: row })
})

export default router
