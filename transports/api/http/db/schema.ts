import {
  pgTable,
  pgEnum,
  uuid,
  text,
  boolean,
  timestamp,
  integer,
  numeric,
  jsonb,
  primaryKey,
  index,
  uniqueIndex,
  customType,
  type AnyPgColumn,
} from 'drizzle-orm/pg-core'
import { z } from 'zod'

// ─────────────────────────────────────────────────────────────────────────────
// UMH PLATFORM ENUMS
// ─────────────────────────────────────────────────────────────────────────────

export const orgPlanEnum = pgEnum('org_plan', [
  'free', 'starter', 'growth', 'enterprise',
])

export const memberRoleEnum = pgEnum('member_role', [
  'owner', 'admin', 'member',
])

export const approvalStatusEnum = pgEnum('approval_status', [
  'pending', 'approved', 'rejected', 'expired',
])

// ─────────────────────────────────────────────────────────────────────────────
// CUSTOM TYPE: pgvector
// ─────────────────────────────────────────────────────────────────────────────

export const vectorType = customType<{
  data: number[]
  driverData: string
  config: { dimensions: number }
}>({
  dataType(config) {
    return `vector(${config?.dimensions ?? 1536})`
  },
  toDriver(value: number[]): string {
    return `[${value.join(',')}]`
  },
  fromDriver(value: string): number[] {
    return value
      .slice(1, -1)
      .split(',')
      .map(Number)
  },
})

// ─────────────────────────────────────────────────────────────────────────────
// ZOD VALIDATORS
// ─────────────────────────────────────────────────────────────────────────────

export const tokensJsonSchema = z.object({
  prompt:     z.number().int().nonnegative(),
  completion: z.number().int().nonnegative(),
  total:      z.number().int().nonnegative(),
  cost_usd:   z.number().nonnegative(),
})

export type TokensJson = z.infer<typeof tokensJsonSchema>

// ─────────────────────────────────────────────────────────────────────────────
// USERS
// ─────────────────────────────────────────────────────────────────────────────

export const users = pgTable('users', {
  id:        uuid('id').primaryKey().defaultRandom(),
  email:     text('email').notNull().unique(),
  name:      text('name').notNull(),
  createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
})

export type User    = typeof users.$inferSelect
export type NewUser = typeof users.$inferInsert

// ─────────────────────────────────────────────────────────────────────────────
// PORTFOLIOS
// ─────────────────────────────────────────────────────────────────────────────

export const portfolios = pgTable('portfolios', {
  id:        uuid('id').primaryKey().defaultRandom(),
  userId:    uuid('user_id').references(() => users.id, { onDelete: 'set null' }),
  name:      text('name').notNull(),
  northStar: text('north_star'),
  createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
}, (t) => ({
  userIdx: index('idx_portfolios_user_id').on(t.userId),
}))

export type Portfolio    = typeof portfolios.$inferSelect
export type NewPortfolio = typeof portfolios.$inferInsert

// ─────────────────────────────────────────────────────────────────────────────
// ORGANIZATIONS
// ─────────────────────────────────────────────────────────────────────────────

export const organizations = pgTable('organizations', {
  id:            uuid('id').primaryKey().defaultRandom(),
  name:          text('name').notNull(),
  ownerId:       uuid('owner_id').notNull().references(() => users.id, { onDelete: 'restrict' }),
  plan:          orgPlanEnum('plan').notNull().default('free'),
  portfolioId:   uuid('portfolio_id').references(() => portfolios.id, { onDelete: 'set null' }),
  autonomyStage: text('autonomy_stage').notNull().default('manual'),
  createdAt:     timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
}, (t) => ({
  ownerIdx:     index('idx_organizations_owner_id').on(t.ownerId),
  portfolioIdx: index('idx_organizations_portfolio_id').on(t.portfolioId),
}))

export type Organization    = typeof organizations.$inferSelect
export type NewOrganization = typeof organizations.$inferInsert

// ─────────────────────────────────────────────────────────────────────────────
// ORG MEMBERS
// ─────────────────────────────────────────────────────────────────────────────

export const orgMembers = pgTable('org_members', {
  orgId:       uuid('org_id').notNull().references(() => organizations.id, { onDelete: 'cascade' }),
  userId:      uuid('user_id').notNull().references(() => users.id, { onDelete: 'cascade' }),
  role:        memberRoleEnum('role').notNull().default('member'),
  accessLevel: text('access_level').notNull().default('member'),
}, (t) => ({
  pk:      primaryKey({ columns: [t.orgId, t.userId] }),
  userIdx: index('idx_org_members_user_id').on(t.userId),
}))

export type OrgMember    = typeof orgMembers.$inferSelect
export type NewOrgMember = typeof orgMembers.$inferInsert

// ─────────────────────────────────────────────────────────────────────────────
// USER AGENT SESSIONS
// ─────────────────────────────────────────────────────────────────────────────

export const userAgentSessions = pgTable('user_agent_sessions', {
  id:            uuid('id').primaryKey().defaultRandom(),
  userId:        uuid('user_id').references(() => users.id, { onDelete: 'cascade' }),
  orgId:         uuid('org_id').references(() => organizations.id, { onDelete: 'cascade' }),
  activeAgentId: uuid('active_agent_id'),
  updatedAt:     timestamp('updated_at', { withTimezone: true }).notNull().defaultNow(),
}, (t) => ({
  userOrgIdx: index('idx_user_agent_sessions_user_org').on(t.userId, t.orgId),
  orgIdx:     index('idx_user_agent_sessions_org_id').on(t.orgId),
}))

export type UserAgentSession    = typeof userAgentSessions.$inferSelect
export type NewUserAgentSession = typeof userAgentSessions.$inferInsert

// ─────────────────────────────────────────────────────────────────────────────
// APPROVALS
// ─────────────────────────────────────────────────────────────────────────────

export const approvals = pgTable('approvals', {
  id:          uuid('id').primaryKey().defaultRandom(),
  orgId:       uuid('org_id').notNull().references(() => organizations.id, { onDelete: 'cascade' }),
  requestJson: jsonb('request_json').notNull().default({}),
  status:      approvalStatusEnum('status').notNull().default('pending'),
  createdAt:   timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
  resolvedAt:  timestamp('resolved_at', { withTimezone: true }),
  resolvedBy:  uuid('resolved_by').references(() => users.id, { onDelete: 'set null' }),
}, (t) => ({
  orgIdx:      index('idx_approvals_org_id').on(t.orgId),
  orgStatus:   index('idx_approvals_org_status').on(t.orgId, t.status),
  resolvedIdx: index('idx_approvals_resolved').on(t.resolvedBy),
}))

export type Approval    = typeof approvals.$inferSelect
export type NewApproval = typeof approvals.$inferInsert

// ─────────────────────────────────────────────────────────────────────────────
// UMH OUTCOMES
// ─────────────────────────────────────────────────────────────────────────────

export const umhOutcomes = pgTable('umh_outcomes', {
  id:            uuid('id').primaryKey().defaultRandom(),
  orgId:         uuid('org_id').notNull().references(() => organizations.id, { onDelete: 'cascade' }),
  traceId:       text('trace_id').notNull(),
  sourceTable:   text('source_table').notNull(),
  sourceRowId:   uuid('source_row_id'),
  outcomeType:   text('outcome_type').notNull(),
  severity:      integer('severity').notNull(),
  payload:       jsonb('payload').notNull().default({}),
  createdAt:     timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
}, (t) => ({
  orgIdx:     index('idx_umh_outcomes_org_id').on(t.orgId),
  traceIdx:   index('idx_umh_outcomes_trace_id').on(t.traceId),
  sourceIdx:  index('idx_umh_outcomes_source').on(t.sourceTable, t.sourceRowId),
  orgCreated: index('idx_umh_outcomes_org_created').on(t.orgId, t.createdAt),
  typeIdx:    index('idx_umh_outcomes_type').on(t.outcomeType),
}))

export type UmhOutcome    = typeof umhOutcomes.$inferSelect
export type NewUmhOutcome = typeof umhOutcomes.$inferInsert

// ─────────────────────────────────────────────────────────────────────────────
// EMBEDDINGS
// ─────────────────────────────────────────────────────────────────────────────

export const embeddings = pgTable('embeddings', {
  id:             uuid('id').primaryKey().defaultRandom(),
  interactionId:  uuid('interaction_id'),
  orgId:          uuid('org_id').notNull().references(() => organizations.id, { onDelete: 'cascade' }),
  embedding:      vectorType('embedding', { dimensions: 384 }),
  contentPreview: text('content_preview'),
  embeddingModel: text('embedding_model').default('BAAI/bge-small-en-v1.5'),
  createdAt:      timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
}, (t) => ({
  interactionIdx: index('idx_embeddings_interaction_id').on(t.interactionId),
  orgIdx:         index('idx_embeddings_org_id').on(t.orgId),
}))

export type Embedding    = typeof embeddings.$inferSelect
export type NewEmbedding = typeof embeddings.$inferInsert
