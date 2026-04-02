/**
 * Database client for eos-saas.
 *
 * Driver: @neondatabase/serverless WebSocket pool — supports real transactions.
 * The HTTP driver is stateless and cannot run SET LOCAL inside a transaction.
 *
 * Two layers:
 *   db          — raw Drizzle instance. Admin/migration use only.
 *   withOrg()   — MANDATORY for every tenant-scoped query. Opens a transaction,
 *                 executes SET LOCAL app.current_org_id, hands tx to callback.
 *                 RLS is live for everything inside fn.
 *
 * Rule: if the table has org_id, use withOrg(). No exceptions.
 *
 * Role architecture:
 *   neondb_owner — admin role (BYPASSRLS). For migrations and seeds only.
 *   eos_app      — application role. No BYPASSRLS. RLS is enforced.
 *                  Set DATABASE_APP_URL to the eos_app connection string.
 */

import { Pool, neonConfig } from '@neondatabase/serverless'
import { drizzle } from 'drizzle-orm/neon-serverless'
import { sql } from 'drizzle-orm'
import ws from 'ws'
import 'dotenv/config'
import * as schema from './schema.js'

// WebSocket constructor required for Node.js (not needed in edge/Deno)
neonConfig.webSocketConstructor = ws

// ─────────────────────────────────────────────────────────────────────────────
// Connections
//
//   DATABASE_URL         — neondb_owner (admin). Used here for migrations.
//   DATABASE_APP_URL     — eos_app role (no BYPASSRLS). Use for all app queries.
//
// The app should always connect via DATABASE_APP_URL so RLS is enforced.
// ─────────────────────────────────────────────────────────────────────────────

const adminUrl = process.env.DATABASE_URL
const appUrl   = process.env.DATABASE_APP_URL ?? process.env.DATABASE_URL

if (!adminUrl) throw new Error('DATABASE_URL is not set.')

// Admin pool — neondb_owner, BYPASSRLS. Migrations and seeds only.
const adminPool = new Pool({ connectionString: adminUrl })
export const db = drizzle(adminPool, { schema })

// App pool — eos_app role, no BYPASSRLS. All application queries go here.
const appPool = new Pool({ connectionString: appUrl })
export const appDb = drizzle(appPool, { schema })

// ─────────────────────────────────────────────────────────────────────────────
// withOrg — tenant-scoped query wrapper
//
// Usage:
//   const result = await withOrg(orgId, async (tx) => {
//     return tx.select().from(schema.ventures)
//   })
//
// What happens:
//   1. Opens a transaction on the app pool (eos_app role — RLS enforced)
//   2. SET LOCAL app.current_org_id = orgId  ← transaction-scoped only
//   3. Calls fn(tx) — all queries filtered to this org by RLS
//   4. Commits on success, rolls back on throw
//
// Queries outside withOrg() on appDb return zero rows. Fail-closed by design.
// ─────────────────────────────────────────────────────────────────────────────

export async function withOrg<T>(
  orgId: string,
  fn: (tx: typeof appDb) => Promise<T>,
): Promise<T> {
  return appDb.transaction(async (tx) => {
    // set_config() accepts parameters; SET LOCAL only takes literals.
    // Third arg true = LOCAL (transaction-scoped, never bleeds to next request).
    await tx.execute(sql`SELECT set_config('app.current_org_id', ${orgId}, true)`)
    return fn(tx as unknown as typeof appDb)
  })
}

// ─────────────────────────────────────────────────────────────────────────────
// Cleanup — call on process exit in long-running servers
// ─────────────────────────────────────────────────────────────────────────────

export async function closeDb() {
  await adminPool.end()
  await appPool.end()
}

export type Db = typeof appDb
