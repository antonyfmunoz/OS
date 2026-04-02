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
// ENUMS
// Note: agentDataTierEnum and autonomyStageEnum remain defined here for
// backwards compatibility with the DB type (still exists, unused by new columns).
// ─────────────────────────────────────────────────────────────────────────────

export const orgPlanEnum = pgEnum('org_plan', [
  'free', 'starter', 'growth', 'enterprise',
])

export const memberRoleEnum = pgEnum('member_role', [
  'owner', 'admin', 'member',
])

export const ventureStageEnum = pgEnum('venture_stage', [
  'idea', 'pre_revenue', 'early', 'growth', 'scale',
])

export const agentDataTierEnum = pgEnum('agent_data_tier', [
  'standard', 'premium', 'isolated',
])

export const autonomyStageEnum = pgEnum('autonomy_stage', [
  'supervised', 'semi_autonomous', 'autonomous',
])

export const approvalStatusEnum = pgEnum('approval_status', [
  'pending', 'approved', 'rejected', 'expired',
])

export const outcomeTypeEnum = pgEnum('outcome_type', [
  'positive', 'negative', 'neutral', 'skipped',
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
// Global identity table — not org-scoped, no RLS.
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
// Top-level grouping for a founder's companies. No RLS — app layer controls
// access based on user_id. Declared before organizations (FK dependency).
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
// A company (operating entity) within a portfolio.
// portfolioId: which founder portfolio this org belongs to.
// autonomyStage: 'manual' | 'hybrid' | 'autonomous' — controls agent delegation.
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
// accessLevel: 'owner' | 'admin' | 'member' | 'viewer' — UI permission gate.
// role: enum kept for backwards compatibility.
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
// VENTURES
// ─────────────────────────────────────────────────────────────────────────────

export const ventures = pgTable('ventures', {
  id:             uuid('id').primaryKey().defaultRandom(),
  orgId:          uuid('org_id').notNull().references(() => organizations.id, { onDelete: 'cascade' }),
  name:           text('name').notNull(),
  stage:          ventureStageEnum('stage').notNull().default('idea'),
  configJson:     jsonb('config_json').notNull().default({}),
  monthlyRevenue: numeric('monthly_revenue', { precision: 12, scale: 2 }).notNull().default('0'),
  monthlyTarget:  numeric('monthly_target', { precision: 12, scale: 2 }).notNull().default('0'),
  createdAt:      timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
}, (t) => ({
  orgIdx: index('idx_ventures_org_id').on(t.orgId),
}))

export type Venture    = typeof ventures.$inferSelect
export type NewVenture = typeof ventures.$inferInsert

// ─────────────────────────────────────────────────────────────────────────────
// AGENTS
// Hierarchical agent architecture:
//   portfolio_advisor — portfolioId only, no orgId (board-level, cross-company)
//   ceo              — orgId, no department, no parent
//   department       — orgId, department name, parentAgentId → ceo
//   sub_agent        — orgId, department name, parentAgentId → department agent
//
// RLS: org_id = current_setting('app.current_org_id') — portfolio advisors
// (org_id IS NULL) are invisible to org-scoped queries by design.
// ─────────────────────────────────────────────────────────────────────────────

export const agents = pgTable('agents', {
  id:            uuid('id').primaryKey().defaultRandom(),
  orgId:         uuid('org_id').references(() => organizations.id, { onDelete: 'cascade' }),
  portfolioId:   uuid('portfolio_id').references(() => portfolios.id, { onDelete: 'set null' }),
  name:          text('name').notNull(),
  agentType:     text('agent_type').notNull(),
  department:    text('department'),
  parentAgentId: uuid('parent_agent_id').references((): AnyPgColumn => agents.id, { onDelete: 'set null' }),
  soul:          jsonb('soul').notNull().default({}),
  domainRules:   jsonb('domain_rules').notNull().default({}),
  tools:         jsonb('tools').notNull().default([]),
  dataTier:      text('data_tier').notNull().default('internal'),
  isActive:      boolean('is_active').notNull().default(true),
  createdAt:     timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
}, (t) => ({
  orgIdx:       index('idx_agents_org_id').on(t.orgId),
  portfolioIdx: index('idx_agents_portfolio_id').on(t.portfolioId),
  parentIdx:    index('idx_agents_parent_id').on(t.parentAgentId),
}))

export type Agent    = typeof agents.$inferSelect
export type NewAgent = typeof agents.$inferInsert

// ─────────────────────────────────────────────────────────────────────────────
// USER AGENT SESSIONS
// Tracks which agent each user is currently talking to per org.
// RLS: org_id scoped.
// ─────────────────────────────────────────────────────────────────────────────

export const userAgentSessions = pgTable('user_agent_sessions', {
  id:            uuid('id').primaryKey().defaultRandom(),
  userId:        uuid('user_id').references(() => users.id, { onDelete: 'cascade' }),
  orgId:         uuid('org_id').references(() => organizations.id, { onDelete: 'cascade' }),
  activeAgentId: uuid('active_agent_id').references(() => agents.id, { onDelete: 'set null' }),
  updatedAt:     timestamp('updated_at', { withTimezone: true }).notNull().defaultNow(),
}, (t) => ({
  userOrgIdx: index('idx_user_agent_sessions_user_org').on(t.userId, t.orgId),
  orgIdx:     index('idx_user_agent_sessions_org_id').on(t.orgId),
}))

export type UserAgentSession    = typeof userAgentSessions.$inferSelect
export type NewUserAgentSession = typeof userAgentSessions.$inferInsert

// ─────────────────────────────────────────────────────────────────────────────
// SKILLS
// ─────────────────────────────────────────────────────────────────────────────

export const skills = pgTable('skills', {
  id:              uuid('id').primaryKey().defaultRandom(),
  orgId:           uuid('org_id').notNull().references(() => organizations.id, { onDelete: 'cascade' }),
  name:            text('name').notNull(),
  content:         text('content').notNull(),
  version:         integer('version').notNull().default(1),
  fitnessFunction: text('fitness_function'),
  createdAt:       timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
}, (t) => ({
  orgIdx:        index('idx_skills_org_id').on(t.orgId),
  orgNameUnique: uniqueIndex('idx_skills_org_name').on(t.orgId, t.name),
}))

export type Skill    = typeof skills.$inferSelect
export type NewSkill = typeof skills.$inferInsert

// ─────────────────────────────────────────────────────────────────────────────
// EVENTS
// ─────────────────────────────────────────────────────────────────────────────

export const events = pgTable('events', {
  id:          uuid('id').primaryKey().defaultRandom(),
  orgId:       uuid('org_id').notNull().references(() => organizations.id, { onDelete: 'cascade' }),
  eventType:   text('event_type').notNull(),
  payloadJson: jsonb('payload_json').notNull().default({}),
  handledBy:   text('handled_by'),
  createdAt:   timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
}, (t) => ({
  orgIdx:     index('idx_events_org_id').on(t.orgId),
  orgType:    index('idx_events_org_type').on(t.orgId, t.eventType),
  orgCreated: index('idx_events_org_created').on(t.orgId, t.createdAt),
}))

export type Event    = typeof events.$inferSelect
export type NewEvent = typeof events.$inferInsert

// ─────────────────────────────────────────────────────────────────────────────
// SKILL VERSIONS
// ─────────────────────────────────────────────────────────────────────────────

export const skillVersions = pgTable('skill_versions', {
  id:                 uuid('id').primaryKey().defaultRandom(),
  skillId:            uuid('skill_id').notNull().references(() => skills.id, { onDelete: 'cascade' }),
  orgId:              uuid('org_id').notNull().references(() => organizations.id, { onDelete: 'cascade' }),
  content:            text('content').notNull(),
  version:            integer('version').notNull(),
  createdAt:          timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
  improvementEventId: uuid('improvement_event_id').references(() => events.id, { onDelete: 'set null' }),
}, (t) => ({
  skillIdx:      index('idx_skill_versions_skill_id').on(t.skillId),
  orgIdx:        index('idx_skill_versions_org_id').on(t.orgId),
  skillVersionU: uniqueIndex('idx_skill_versions_skill_v').on(t.skillId, t.version),
}))

export type SkillVersion    = typeof skillVersions.$inferSelect
export type NewSkillVersion = typeof skillVersions.$inferInsert

// ─────────────────────────────────────────────────────────────────────────────
// WORKFLOWS
// executorType: 'human' | 'ai' | 'hybrid'
// autonomyStage: 'manual' | 'hybrid' | 'autonomous'
// triggerType: 'manual' | 'scheduled' | 'event'
// ─────────────────────────────────────────────────────────────────────────────

export const workflows = pgTable('workflows', {
  id:            uuid('id').primaryKey().defaultRandom(),
  orgId:         uuid('org_id').notNull().references(() => organizations.id, { onDelete: 'cascade' }),
  name:          text('name').notNull(),
  description:   text('description'),
  executorType:  text('executor_type').notNull(),
  autonomyStage: text('autonomy_stage').notNull().default('manual'),
  steps:         jsonb('steps').notNull().default([]),
  triggerType:   text('trigger_type').notNull().default('manual'),
  isActive:      boolean('is_active').notNull().default(true),
  createdAt:     timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
}, (t) => ({
  orgIdx: index('idx_workflows_org_id').on(t.orgId),
}))

export type Workflow    = typeof workflows.$inferSelect
export type NewWorkflow = typeof workflows.$inferInsert

// ─────────────────────────────────────────────────────────────────────────────
// INTERACTIONS
// ─────────────────────────────────────────────────────────────────────────────

export const interactions = pgTable('interactions', {
  id:            uuid('id').primaryKey().defaultRandom(),
  orgId:         uuid('org_id').notNull().references(() => organizations.id, { onDelete: 'cascade' }),
  userId:        uuid('user_id').references(() => users.id, { onDelete: 'set null' }),
  ventureId:     uuid('venture_id').references(() => ventures.id, { onDelete: 'set null' }),
  agentId:       uuid('agent_id').references(() => agents.id, { onDelete: 'set null' }),
  skillId:       uuid('skill_id').references(() => skills.id, { onDelete: 'set null' }),
  taskType:      text('task_type').notNull(),
  modelUsed:     text('model_used').notNull(),
  inputSummary:  text('input_summary'),
  outputSummary: text('output_summary'),
  tokensJson:    jsonb('tokens_json').notNull().default({ prompt: 0, completion: 0, total: 0, cost_usd: 0 }),
  createdAt:     timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
}, (t) => ({
  orgIdx:     index('idx_interactions_org_id').on(t.orgId),
  orgCreated: index('idx_interactions_org_created').on(t.orgId, t.createdAt),
  orgAgent:   index('idx_interactions_org_agent').on(t.orgId, t.agentId),
  orgVenture: index('idx_interactions_org_venture').on(t.orgId, t.ventureId),
  orgSkill:   index('idx_interactions_org_skill').on(t.orgId, t.skillId),
  userIdx:    index('idx_interactions_user_id').on(t.userId),
}))

export type Interaction    = typeof interactions.$inferSelect
export type NewInteraction = typeof interactions.$inferInsert

// ─────────────────────────────────────────────────────────────────────────────
// OUTCOMES
// ─────────────────────────────────────────────────────────────────────────────

export const outcomes = pgTable('outcomes', {
  id:            uuid('id').primaryKey().defaultRandom(),
  interactionId: uuid('interaction_id').notNull().references(() => interactions.id, { onDelete: 'cascade' }),
  orgId:         uuid('org_id').notNull().references(() => organizations.id, { onDelete: 'cascade' }),
  outcomeType:   outcomeTypeEnum('outcome_type').notNull(),
  score:         numeric('score', { precision: 5, scale: 2 }),
  notes:         text('notes'),
  createdAt:     timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
}, (t) => ({
  interactionIdx: index('idx_outcomes_interaction_id').on(t.interactionId),
  orgIdx:         index('idx_outcomes_org_id').on(t.orgId),
  orgType:        index('idx_outcomes_org_type').on(t.orgId, t.outcomeType),
}))

export type Outcome    = typeof outcomes.$inferSelect
export type NewOutcome = typeof outcomes.$inferInsert

// ─────────────────────────────────────────────────────────────────────────────
// HUMAN PROFILES
// ─────────────────────────────────────────────────────────────────────────────

export const humanProfiles = pgTable('human_profiles', {
  id:          uuid('id').primaryKey().defaultRandom(),
  orgId:       uuid('org_id').notNull().references(() => organizations.id, { onDelete: 'cascade' }),
  username:    text('username').notNull(),
  ventureId:   uuid('venture_id').references(() => ventures.id, { onDelete: 'set null' }),
  profileJson: jsonb('profile_json').notNull().default({}),
  updatedAt:   timestamp('updated_at', { withTimezone: true }).notNull().defaultNow(),
}, (t) => ({
  orgUsernameUnique: uniqueIndex('idx_human_profiles_org_username').on(t.orgId, t.username),
  orgIdx:            index('idx_human_profiles_org_id').on(t.orgId),
  ventureIdx:        index('idx_human_profiles_venture_id').on(t.ventureId),
}))

export type HumanProfile    = typeof humanProfiles.$inferSelect
export type NewHumanProfile = typeof humanProfiles.$inferInsert

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
// EMBEDDINGS
// ─────────────────────────────────────────────────────────────────────────────

export const embeddings = pgTable('embeddings', {
  id:             uuid('id').primaryKey().defaultRandom(),
  interactionId:  uuid('interaction_id').notNull().references(() => interactions.id, { onDelete: 'cascade' }),
  orgId:          uuid('org_id').notNull().references(() => organizations.id, { onDelete: 'cascade' }),
  embedding:      vectorType('embedding', { dimensions: 768 }),
  contentPreview: text('content_preview'),
  embeddingModel: text('embedding_model').default('text-embedding-004'),
  createdAt:      timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
}, (t) => ({
  interactionIdx: index('idx_embeddings_interaction_id').on(t.interactionId),
  orgIdx:         index('idx_embeddings_org_id').on(t.orgId),
}))

export type Embedding    = typeof embeddings.$inferSelect
export type NewEmbedding = typeof embeddings.$inferInsert
