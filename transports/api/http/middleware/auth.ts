import type { Context, Next } from 'hono'
import { eq } from 'drizzle-orm'
import type { Env } from '../types.js'
import { db } from '../db/client.js'
import { organizations } from '../db/schema.js'

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

export async function authMiddleware(c: Context<Env>, next: Next) {
  const orgId = c.req.header('x-org-id')

  if (!orgId) {
    return c.json({ error: 'unauthorized', message: 'x-org-id header required' }, 401)
  }

  if (!UUID_RE.test(orgId)) {
    return c.json({ error: 'unauthorized', message: 'x-org-id must be a valid UUID' }, 401)
  }

  // Validate org exists — admin db (neondb_owner bypasses RLS, correct for auth checks)
  const rows = await db
    .select({ id: organizations.id, ownerId: organizations.ownerId })
    .from(organizations)
    .where(eq(organizations.id, orgId))
    .limit(1)

  if (rows.length === 0) {
    return c.json({ error: 'unauthorized', message: 'org not found' }, 401)
  }

  c.set('orgId', rows[0].id)
  c.set('userId', rows[0].ownerId)
  await next()
}
