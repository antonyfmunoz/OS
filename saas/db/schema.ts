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
  index,
  uniqueIndex,
  type AnyPgColumn,
} from 'drizzle-orm/pg-core'

// ─────────────────────────────────────────────────────────────────────────────
// RE-EXPORT UMH PLATFORM TABLES
// EOS projection depends on platform identity (users, orgs, portfolios).
// Re-exported so existing EOS route imports don't break.
// ─────────────────────────────────────────────────────────────────────────────

export {
  orgPlanEnum,
  memberRoleEnum,
  approvalStatusEnum,
  vectorType,
  tokensJsonSchema,
  type TokensJson,
  users,
  type User,
  type NewUser,
  portfolios,
  type Portfolio,
  type NewPortfolio,
  organizations,
  type Organization,
  type NewOrganization,
  orgMembers,
  type OrgMember,
  type NewOrgMember,
  userAgentSessions,
  type UserAgentSession,
  type NewUserAgentSession,
  approvals,
  type Approval,
  type NewApproval,
  umhOutcomes,
  type UmhOutcome,
  type NewUmhOutcome,
  embeddings,
  type Embedding,
  type NewEmbedding,
} from '../../transports/api/http/db/schema.js'

// Re-import for FK references in EOS tables
import { users, organizations, portfolios } from '../../transports/api/http/db/schema.js'

// ─────────────────────────────────────────────────────────────────────────────
// EOS PROJECTION ENUMS
// ─────────────────────────────────────────────────────────────────────────────

export const ventureStageEnum = pgEnum('venture_stage', [
  'idea', 'pre_revenue', 'early', 'growth', 'scale',
])

export const agentDataTierEnum = pgEnum('agent_data_tier', [
  'standard', 'premium', 'isolated',
])

export const autonomyStageEnum = pgEnum('autonomy_stage', [
  'supervised', 'semi_autonomous', 'autonomous',
])

export const outcomeTypeEnum = pgEnum('outcome_type', [
  'positive', 'negative', 'neutral', 'skipped',
])

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
  umhStatus:      text('umh_status'),
  createdAt:      timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
}, (t) => ({
  orgIdx: index('idx_ventures_org_id').on(t.orgId),
}))

export type Venture    = typeof ventures.$inferSelect
export type NewVenture = typeof ventures.$inferInsert

// ─────────────────────────────────────────────────────────────────────────────
// AGENTS
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
  umhStatus:   text('umh_status'),
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
// CLIENTS
// ─────────────────────────────────────────────────────────────────────────────

export const clients = pgTable('clients', {
  id:        uuid('id').primaryKey().defaultRandom(),
  orgId:     text('org_id').notNull(),
  ventureId: text('venture_id').notNull(),
  name:      text('name').notNull(),
  email:     text('email').notNull(),
  phone:     text('phone'),
  status:    text('status').notNull().default('lead'),
  source:    text('source').notNull().default('unknown'),
  notes:     text('notes').default(''),
  umhStatus: text('umh_status'),
  createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).notNull().defaultNow(),
}, (t) => ({
  orgIdx:     index('idx_clients_org_id').on(t.orgId),
  ventureIdx: index('idx_clients_venture_id').on(t.ventureId),
  statusIdx:  index('idx_clients_status').on(t.orgId, t.status),
}))

export type Client    = typeof clients.$inferSelect
export type NewClient = typeof clients.$inferInsert

// ─────────────────────────────────────────────────────────────────────────────
// TRANSACTIONS
// ─────────────────────────────────────────────────────────────────────────────

export const transactions = pgTable('transactions', {
  id:                  uuid('id').primaryKey().defaultRandom(),
  orgId:               text('org_id').notNull(),
  ventureId:           text('venture_id').notNull(),
  clientId:            uuid('client_id').notNull().references(() => clients.id, { onDelete: 'cascade' }),
  productName:         text('product_name').notNull(),
  amountCents:         integer('amount_cents').notNull(),
  currency:            text('currency').notNull().default('USD'),
  status:              text('status').notNull().default('pending'),
  paymentDate:         timestamp('payment_date', { withTimezone: true }),
  fulfillmentStatus:   text('fulfillment_status').notNull().default('not_started'),
  templateInstanceId:  text('template_instance_id'),
  notes:               text('notes').default(''),
  createdAt:           timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
}, (t) => ({
  orgIdx:     index('idx_transactions_org_id').on(t.orgId),
  ventureIdx: index('idx_transactions_venture_id').on(t.ventureId),
  clientIdx:  index('idx_transactions_client_id').on(t.clientId),
  statusIdx:  index('idx_transactions_status').on(t.orgId, t.status),
}))

export type Transaction    = typeof transactions.$inferSelect
export type NewTransaction = typeof transactions.$inferInsert

// ─────────────────────────────────────────────────────────────────────────────
// FULFILLMENT EVENTS
// ─────────────────────────────────────────────────────────────────────────────

export const fulfillmentEvents = pgTable('fulfillment_events', {
  id:            uuid('id').primaryKey().defaultRandom(),
  transactionId: uuid('transaction_id').notNull().references(() => transactions.id, { onDelete: 'cascade' }),
  orgId:         text('org_id').notNull(),
  ventureId:     text('venture_id').notNull(),
  description:   text('description').notNull(),
  completedAt:   timestamp('completed_at', { withTimezone: true }).notNull().defaultNow(),
  completedBy:   text('completed_by').notNull(),
  evidenceUrl:   text('evidence_url'),
  notes:         text('notes').default(''),
}, (t) => ({
  txIdx:      index('idx_fulfillment_events_tx_id').on(t.transactionId),
  orgIdx:     index('idx_fulfillment_events_org_id').on(t.orgId),
  ventureIdx: index('idx_fulfillment_events_venture_id').on(t.ventureId),
}))

export type FulfillmentEvent    = typeof fulfillmentEvents.$inferSelect
export type NewFulfillmentEvent = typeof fulfillmentEvents.$inferInsert

// ─────────────────────────────────────────────────────────────────────────────
// OFFERS
// ─────────────────────────────────────────────────────────────────────────────

export const offers = pgTable('offers', {
  id:               uuid('id').primaryKey().defaultRandom(),
  orgId:            text('org_id').notNull(),
  ventureId:        text('venture_id').notNull(),
  name:             text('name').notNull(),
  positionInLadder: integer('position_in_ladder').notNull().default(1),
  priceCents:       integer('price_cents').notNull(),
  currency:         text('currency').notNull().default('USD'),
  offerType:        text('offer_type').notNull(),
  description:      text('description').default(''),
  validated:        boolean('validated').notNull().default(false),
  createdAt:        timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
}, (t) => ({
  orgIdx:     index('idx_offers_org_id').on(t.orgId),
  ventureIdx: index('idx_offers_venture_id').on(t.ventureId),
  ladderIdx:  index('idx_offers_ladder').on(t.ventureId, t.positionInLadder),
}))

export type Offer    = typeof offers.$inferSelect
export type NewOffer = typeof offers.$inferInsert
