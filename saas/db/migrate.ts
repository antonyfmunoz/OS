/**
 * Migration runner.
 *
 * Steps:
 *   1. Enable pgvector + pgcrypto extensions (must precede schema)
 *   2. Run drizzle-kit generated migrations (schema + indexes)
 *   3. Enable RLS + FORCE ROW LEVEL SECURITY on all tenant tables
 *   4. Create/replace RLS policies keyed to app.current_org_id
 *   5. Create eos_app role (no BYPASSRLS) + grant table permissions
 *
 * Run: npm run db:migrate
 * Idempotent — safe to run multiple times.
 *
 * Role architecture:
 *   neondb_owner — BYPASSRLS admin. Migrations, seeds, emergency access.
 *   eos_app      — application role. No BYPASSRLS. RLS is enforced.
 *                  App connects via DATABASE_APP_URL (eos_app creds).
 */

import { Pool, neonConfig } from '@neondatabase/serverless'
import { drizzle } from 'drizzle-orm/neon-serverless'
import { migrate } from 'drizzle-orm/neon-serverless/migrator'
import { sql } from 'drizzle-orm'
import ws from 'ws'
import 'dotenv/config'

neonConfig.webSocketConstructor = ws

if (!process.env.DATABASE_URL) {
  throw new Error('DATABASE_URL is not set.')
}

const pool = new Pool({ connectionString: process.env.DATABASE_URL })
const db = drizzle(pool)

// ─────────────────────────────────────────────────────────────────────────────
// Tables that require tenant isolation
// ─────────────────────────────────────────────────────────────────────────────

const TENANT_TABLES = [
  'organizations',
  'org_members',
  'ventures',
  'agents',
  'skills',
  'events',
  'skill_versions',
  'workflows',
  'interactions',
  'outcomes',
  'human_profiles',
  'approvals',
  'embeddings',
  'user_agent_sessions',
] as const

const ORG_ISOLATION_EXPR = (table: string) =>
  table === 'organizations'
    ? `id = current_setting('app.current_org_id', true)::uuid`
    : `org_id = current_setting('app.current_org_id', true)::uuid`

// ─────────────────────────────────────────────────────────────────────────────
// Steps
// ─────────────────────────────────────────────────────────────────────────────

async function applyExtensions() {
  console.log('  → enabling extensions...')
  await db.execute(sql.raw(`CREATE EXTENSION IF NOT EXISTS "pgcrypto"`))
  await db.execute(sql.raw(`CREATE EXTENSION IF NOT EXISTS "vector"`))
}

async function applyRLS() {
  console.log('  → applying RLS policies...')

  for (const table of TENANT_TABLES) {
    await db.execute(sql.raw(`ALTER TABLE ${table} ENABLE ROW LEVEL SECURITY`))

    // FORCE ROW LEVEL SECURITY — applies even to table owners.
    // Does NOT apply to BYPASSRLS roles (neondb_owner in Neon).
    // That is correct behavior: admin bypasses, app role enforced.
    await db.execute(sql.raw(`ALTER TABLE ${table} FORCE ROW LEVEL SECURITY`))

    await db.execute(sql.raw(`DROP POLICY IF EXISTS ${table}_isolation ON ${table}`))

    await db.execute(sql.raw(
      `CREATE POLICY ${table}_isolation ON ${table}
         USING (${ORG_ISOLATION_EXPR(table)})`
    ))

    console.log(`     ✓ ${table}`)
  }
}

async function applyAppRole() {
  console.log('  → creating eos_app role...')

  // Create role if it doesn't exist — idempotent
  await db.execute(sql.raw(`
    DO $$
    BEGIN
      IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'eos_app') THEN
        CREATE ROLE eos_app LOGIN PASSWORD 'REPLACE_WITH_STRONG_PASSWORD';
      END IF;
    END
    $$
  `))

  // Grant CONNECT on database
  await db.execute(sql.raw(`GRANT CONNECT ON DATABASE neondb TO eos_app`))

  // Grant USAGE on schema
  await db.execute(sql.raw(`GRANT USAGE ON SCHEMA public TO eos_app`))

  // Grant table permissions — SELECT, INSERT, UPDATE, DELETE
  // No TRUNCATE, no DROP, no DDL — app role is data-only
  await db.execute(sql.raw(`
    GRANT SELECT, INSERT, UPDATE, DELETE
    ON ALL TABLES IN SCHEMA public
    TO eos_app
  `))

  // Ensure future tables also get granted
  await db.execute(sql.raw(`
    ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO eos_app
  `))

  // Grant usage on all sequences
  await db.execute(sql.raw(`
    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO eos_app
  `))

  // Grant eos_app to neondb_owner so it can SET ROLE eos_app for testing
  await db.execute(sql.raw(`GRANT eos_app TO neondb_owner`))

  console.log(`     ✓ eos_app role ready`)
  console.log(`     ⚠  Set a real password: ALTER ROLE eos_app PASSWORD 'your-password'`)
  console.log(`     ⚠  Add DATABASE_APP_URL to .env using eos_app credentials`)
}

async function main() {
  console.log('\n[1/4] Enabling extensions...')
  await applyExtensions()
  console.log('  ✓ extensions ready')

  console.log('\n[2/4] Running schema migrations...')
  await migrate(db, { migrationsFolder: './db/migrations' })
  console.log('  ✓ schema applied')

  console.log('\n[3/4] Applying RLS policies...')
  await applyRLS()
  console.log('  ✓ tenant firewall active')

  console.log('\n[4/4] Setting up eos_app role...')
  await applyAppRole()
  console.log('  ✓ app role ready')

  console.log('\n✓ Migration complete.\n')
  await pool.end()
  process.exit(0)
}

main().catch(async (err) => {
  console.error('\n✗ Migration failed:', err)
  await pool.end()
  process.exit(1)
})
