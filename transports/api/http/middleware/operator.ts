import type { Context, Next } from 'hono'
import { eq } from 'drizzle-orm'
import type { Env } from '../types.js'
import { db } from '../db/client.js'
import { organizations } from '../db/schema.js'

/**
 * Operator guard — restricts routes to the org owner.
 *
 * Current auth model (solo-founder phase): authMiddleware derives userId
 * from the org's ownerId, so this guard primarily ensures auth context
 * is populated and re-validates ownership. When a real user-auth layer
 * is added (signed sessions, bearer tokens mapping to distinct user
 * rows), this guard will check the independently-authenticated user
 * against the org owner — no code change needed here, only in
 * authMiddleware's identity source.
 */
export async function operatorGuard(c: Context<Env>, next: Next) {
  const orgId = c.get('orgId')
  const userId = c.get('userId')

  if (!orgId || !userId) {
    return c.json({ error: 'forbidden', message: 'authentication required' }, 403)
  }

  const rows = await db
    .select({ ownerId: organizations.ownerId })
    .from(organizations)
    .where(eq(organizations.id, orgId))
    .limit(1)

  if (rows.length === 0 || rows[0].ownerId !== userId) {
    return c.json({ error: 'forbidden', message: 'operator access required' }, 403)
  }

  await next()
}
