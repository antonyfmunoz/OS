import type { Context, Next } from 'hono'
import { eq } from 'drizzle-orm'
import type { Env } from '../types.js'
import { db } from '../../db/client.js'
import { organizations } from '../../db/schema.js'

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
