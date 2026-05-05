/**
 * Seed script — Munoz Holdings portfolio architecture.
 *
 * Inserts:
 *   - 1 user (Antony F. Munoz)
 *   - 1 portfolio (Munoz Holdings Portfolio)
 *   - 2 organizations (Empyrean Creative, Lyfe Institute)
 *   - 2 org_members (owner in both)
 *   - 2 ventures (one per org)
 *   - 8 skills (Lyfe Institute org)
 *   - 6 agents (portfolio_advisor, 2 ceos, 3 department)
 *   - 1 workflow (Outreach Pipeline — Lyfe Institute)
 *
 * Writes ORG_ID (Lyfe Institute) and USER_ID to .env after insert.
 * Idempotent — queries before inserting to avoid duplicates.
 *
 * Run: npm run db:seed
 */

import { Pool, neonConfig } from '@neondatabase/serverless'
import { drizzle } from 'drizzle-orm/neon-serverless'
import { sql, and, eq } from 'drizzle-orm'
import { readFileSync, writeFileSync, existsSync } from 'fs'
import ws from 'ws'
import 'dotenv/config'
import {
  users,
  portfolios,
  organizations,
  orgMembers,
  ventures,
  skills,
  agents,
  workflows,
} from './schema.js'

neonConfig.webSocketConstructor = ws

if (!process.env.DATABASE_URL) {
  throw new Error('DATABASE_URL is not set.')
}

const pool = new Pool({ connectionString: process.env.DATABASE_URL })
const db = drizzle(pool)

// ─────────────────────────────────────────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────────────────────────────────────────

async function findOrInsert<T extends { id: string }>(
  findFn: () => Promise<T[]>,
  insertFn: () => Promise<T[]>,
  label: string,
): Promise<T> {
  const existing = await findFn()
  if (existing.length > 0) {
    console.log(`  ↳ ${label}: already exists (${existing[0].id})`)
    return existing[0]
  }
  const [row] = await insertFn()
  console.log(`  ✓ ${label}: ${row.id}`)
  return row
}

// ─────────────────────────────────────────────────────────────────────────────
// SKILLS (Lyfe Institute)
// ─────────────────────────────────────────────────────────────────────────────

const SKILLS = [
  {
    name: 'analyze_conversation',
    content: `# Skill: Analyze Sales Conversation

## Purpose
Analyze a DM conversation and determine the best next response.
The goal is to move the conversation toward identifying pain and booking a call.

## Analysis
Identify: emotional signals, frustration level, self-awareness, readiness for change.

## Conversation Stage
1. Opening  2. Pain discovery  3. Problem reframing  4. Offer introduction  5. Call invitation

## Generate Response
Provide: recommended next message, follow-up question, conversation strategy.`,
    fitnessFunction: 'Response accepted by user without edits. Conversation advances to next stage.',
  },
  {
    name: 'generate_outreach_from_intel',
    content: `# Skill: Generate Outreach From Market Intelligence

## Purpose
Turn market intelligence insights into high-converting DM outreach messages.

## Generate
- 10 DM openers, 10 follow-up questions, 5 reframes, 5 call invitations.
- Mirror ICP language exactly. Trigger honest conversations.`,
    fitnessFunction: 'Opener reply rate > 30%. Follow-up moves to pain discovery stage.',
  },
  {
    name: 'analyze_icp_signal',
    content: `# Skill: Analyze ICP Signal

## Purpose
Extract customer intelligence from raw signals. Identify pain, language patterns, psychological state.

## Output
Signal Summary | Pain Pattern | Desired Transformation | Language Patterns | Psychological State | ICP Match | Content Opportunities | Outreach Opportunities`,
    fitnessFunction: 'High-match signals produce replies when used in outreach.',
  },
  {
    name: 'detect_icp_patterns',
    content: `# Skill: Detect ICP Patterns

## Purpose
Analyze all ICP insights to identify recurring patterns in psychology, language, and frustrations.

## Output
Top Frustrations | Top Desires | Language Patterns | Psychological States | Messaging Opportunities | Offer Opportunities`,
    fitnessFunction: 'Pattern report used to generate outreach that achieves > 30% reply rate.',
  },
  {
    name: 'generate_market_report',
    content: `# Skill: Generate Market Intelligence Report

## Purpose
Synthesize ICP insights and patterns into a strategic report.

## Report Sections
Top Frustrations | Top Desires | Language to Mirror | Psychological Profile | Content Angles | Outreach Angles | Offer Insights`,
    fitnessFunction: 'Report surfaces at least 3 new outreach angles not previously tested.',
  },
  {
    name: 'process_signal_queue',
    content: `# Skill: Process Signal Queue

## Purpose
Process raw signals from inbox and convert to structured ICP intelligence.

## Process
1. Scan raw_signals  2. Run analyze_icp_signal on each  3. Save insight  4. Archive signal`,
    fitnessFunction: 'All signals in inbox processed. Zero signals left after completion.',
  },
  {
    name: 'qualify_lead',
    content: `# Skill: Qualify Lead

## Purpose
Evaluate a prospect for ICP match with Initiate Arena.

## Criteria
Age 18-25 | Self-awareness | Frustration signal | Execution willingness | Financial readiness ($750)

## Disqualifiers
Victim mindset | Blames others | Wants motivation without execution

## Output
ICP match (High/Medium/Low/Disqualified) | Recommended next action | Key pain signal | Suggested follow-up`,
    fitnessFunction: 'High-match qualification predicts call booking.',
  },
  {
    name: 'summarize_sales_call',
    content: `# Skill: Summarize Sales Call

## Purpose
Convert a sales call transcript into a structured summary.

## Output
Prospect Summary | Core Pain (verbatim) | Desired Transformation | Objections Raised | Buying Signals | Decision Timeline | Agreed Next Step | Recommended Follow-Up`,
    fitnessFunction: 'Summary captures all objections. Follow-up achieves response within 48 hours.',
  },
] as const

// ─────────────────────────────────────────────────────────────────────────────
// VENTURE CONFIGS
// ─────────────────────────────────────────────────────────────────────────────

const EMPYREAN_CONFIG = {
  stage: 'building',
  primary_icp: 'Founder-operators who need brand strategy and/or AI infrastructure',
  core_offer: 'Dual-function entity. INTERNAL: Incubator that builds and validates products. EXTERNAL (B2B): Proven internal systems packaged as offers for founders.',
  price_point: '$1,500–$3,000 per project | recurring AI system licenses (future)',
  positioning: 'A centralized forge that turns philosophy into systems, products, and media. Where Mastery Is Forged.',
  north_star_metric: 'Become the production engine and proof-of-concept lab for all ventures',
  active_blockers: ['Pre-revenue on the external side', 'Initiate Arena is current primary focus'],
}

const LYFE_INSTITUTE_CONFIG = {
  stage: 'building',
  core_offer: 'Initiate Arena — 90-day structured execution program for men 18-25.',
  price_point: '$750 founding rate',
  positioning: 'Not a coaching program — an educational institution that develops sovereign individuals. From Dependence To Sovereignty.',
  primary_icp: {
    one_sentence: 'Ambitious young men (18-25) who feel lost but know they\'re capable of more.',
    for: ['Feels behind in life', 'Knows they\'re capable of more', 'Lacks daily structure', 'Is willing to do uncomfortable work'],
    not_for: ['Victim mindset', 'Blames others', 'Wants motivation without execution'],
  },
  north_star_metric: '$10K/month net profit from Initiate Arena',
  active_blockers: ['Pre-revenue — no sales closed yet', 'Outreach is the only acquisition lever'],
  winning_content_angles: [
    'You don\'t have a discipline problem. You have a structure problem.',
    'Scrolling is the new sedation.',
    'Capable people go broke on potential. Builders go broke on execution.',
  ],
  proven_outreach_openers: {
    warm: 'Yo — quick honest question: do you feel clear and structured about your direction right now?',
    cold: 'Random but real question — do you feel clear about where your life is going right now?',
  },
}

// ─────────────────────────────────────────────────────────────────────────────
// ENV WRITER
// ─────────────────────────────────────────────────────────────────────────────

function writeEnvVars(orgId: string, userId: string) {
  const envPath = new URL('../.env', import.meta.url).pathname
  let content = existsSync(envPath) ? readFileSync(envPath, 'utf-8') : ''
  const upsert = (key: string, value: string) => {
    const regex = new RegExp(`^${key}=.*$`, 'm')
    const line = `${key}=${value}`
    content = regex.test(content) ? content.replace(regex, line) : content + `\n${line}`
  }
  upsert('ORG_ID', orgId)
  upsert('USER_ID', userId)
  writeFileSync(envPath, content.trim() + '\n')
  console.log(`  ✓ wrote ORG_ID=${orgId}`)
  console.log(`  ✓ wrote USER_ID=${userId}`)
}

// ─────────────────────────────────────────────────────────────────────────────
// SEED
// ─────────────────────────────────────────────────────────────────────────────

async function main() {
  // ── [1/9] User ───────────────────────────────────────────────────────────
  console.log('\n[1/9] Inserting user...')
  const [user] = await db
    .insert(users)
    .values({ email: 'antonyfm@empyreanstudios.co', name: 'Antony F. Munoz' })
    .onConflictDoUpdate({ target: users.email, set: { name: 'Antony F. Munoz' } })
    .returning()
  console.log(`  ✓ user: ${user.id} (${user.email})`)

  // ── [2/9] Portfolio ──────────────────────────────────────────────────────
  console.log('\n[2/9] Inserting portfolio...')
  const portfolio = await findOrInsert(
    () => db.select().from(portfolios).where(
      and(eq(portfolios.userId, user.id), eq(portfolios.name, 'Munoz Holdings Portfolio'))
    ).limit(1),
    () => db.insert(portfolios).values({
      userId: user.id,
      name: 'Munoz Holdings Portfolio',
      northStar: '$100K/month net profit across portfolio',
    }).returning(),
    'portfolio: Munoz Holdings Portfolio',
  )

  // ── [3/9] Organizations ──────────────────────────────────────────────────
  console.log('\n[3/9] Inserting organizations...')

  const empyreanOrg = await findOrInsert(
    () => db.select().from(organizations).where(
      and(eq(organizations.name, 'Empyrean Creative'), eq(organizations.ownerId, user.id))
    ).limit(1),
    () => db.insert(organizations).values({
      name: 'Empyrean Creative',
      ownerId: user.id,
      plan: 'growth',
      portfolioId: portfolio.id,
      autonomyStage: 'manual',
    }).returning(),
    'org: Empyrean Creative',
  )

  const lyfeOrg = await findOrInsert(
    () => db.select().from(organizations).where(
      and(eq(organizations.name, 'Lyfe Institute'), eq(organizations.ownerId, user.id))
    ).limit(1),
    () => db.insert(organizations).values({
      name: 'Lyfe Institute',
      ownerId: user.id,
      plan: 'growth',
      portfolioId: portfolio.id,
      autonomyStage: 'manual',
    }).returning(),
    'org: Lyfe Institute',
  )

  // Link existing orgs that may not have portfolio_id yet
  await db.execute(sql`
    UPDATE organizations SET portfolio_id = ${portfolio.id}
    WHERE id IN (${empyreanOrg.id}, ${lyfeOrg.id}) AND portfolio_id IS NULL
  `)

  // ── [4/9] Org members ────────────────────────────────────────────────────
  console.log('\n[4/9] Inserting org members...')
  await db.insert(orgMembers)
    .values({ orgId: empyreanOrg.id, userId: user.id, role: 'owner', accessLevel: 'owner' })
    .onConflictDoNothing()
  await db.insert(orgMembers)
    .values({ orgId: lyfeOrg.id, userId: user.id, role: 'owner', accessLevel: 'owner' })
    .onConflictDoNothing()
  console.log(`  ✓ org_member: owner in both orgs`)

  // ── [5/9] Ventures ───────────────────────────────────────────────────────
  console.log('\n[5/9] Inserting ventures...')

  const empyreanVenture = await findOrInsert(
    () => db.select().from(ventures).where(
      and(eq(ventures.orgId, empyreanOrg.id), eq(ventures.name, 'Empyrean Creative'))
    ).limit(1),
    () => db.insert(ventures).values({
      orgId: empyreanOrg.id, name: 'Empyrean Creative',
      stage: 'pre_revenue', configJson: EMPYREAN_CONFIG,
      monthlyRevenue: '0', monthlyTarget: '0',
    }).returning(),
    'venture: Empyrean Creative',
  )

  const lyfeVenture = await findOrInsert(
    () => db.select().from(ventures).where(
      and(eq(ventures.orgId, lyfeOrg.id), eq(ventures.name, 'Lyfe Institute'))
    ).limit(1),
    () => db.insert(ventures).values({
      orgId: lyfeOrg.id, name: 'Lyfe Institute',
      stage: 'pre_revenue', configJson: LYFE_INSTITUTE_CONFIG,
      monthlyRevenue: '0', monthlyTarget: '10000',
    }).returning(),
    'venture: Lyfe Institute',
  )

  console.log(`  ✓ ventures linked: ${empyreanVenture.id} | ${lyfeVenture.id}`)

  // ── [6/9] Skills ─────────────────────────────────────────────────────────
  console.log('\n[6/9] Inserting skills (Lyfe Institute)...')
  for (const skill of SKILLS) {
    await db.insert(skills)
      .values({ orgId: lyfeOrg.id, name: skill.name, content: skill.content,
                version: 1, fitnessFunction: skill.fitnessFunction })
      .onConflictDoNothing()
    console.log(`  ✓ skill: ${skill.name}`)
  }

  // ── [7/9] Agents ─────────────────────────────────────────────────────────
  console.log('\n[7/9] Inserting agents...')

  // a. Portfolio Advisor — cross-company, no orgId
  const portfolioAdvisor = await findOrInsert(
    () => db.select().from(agents).where(
      and(eq(agents.portfolioId, portfolio.id), eq(agents.agentType, 'portfolio_advisor'))
    ).limit(1),
    () => db.insert(agents).values({
      portfolioId: portfolio.id,
      name: 'Portfolio Advisor',
      agentType: 'portfolio_advisor',
      soul: {
        description: 'Board-level advisor across all portfolio companies. Sees full portfolio KPIs. Advises founder on capital allocation and cross-company patterns. Does not execute — advises only.',
        tone: 'Strategic, direct, data-driven. Speaks in terms of constraints, leverage points, and allocation decisions.',
      },
      domainRules: {},
      tools: [],
      dataTier: 'internal',
      isActive: true,
    }).returning(),
    'agent: Portfolio Advisor',
  )

  // b. CEO Agent — Empyrean Creative
  const empyreanCeo = await findOrInsert(
    () => db.select().from(agents).where(
      and(eq(agents.orgId, empyreanOrg.id), eq(agents.agentType, 'ceo'))
    ).limit(1),
    () => db.insert(agents).values({
      orgId: empyreanOrg.id,
      portfolioId: portfolio.id,
      name: 'Empyrean CEO',
      agentType: 'ceo',
      soul: {
        description: 'Orchestrator for Empyrean Creative. Reads all company KPIs, spins up department agents, coordinates execution.',
        tone: 'Builder-operator. Focused on systems, clients, and proof of concept.',
      },
      domainRules: { company: 'Empyrean Creative', focus: 'B2B AI infrastructure and brand systems' },
      tools: [],
      dataTier: 'internal',
      isActive: true,
    }).returning(),
    'agent: Empyrean CEO',
  )

  // c. CEO Agent — Lyfe Institute
  const lyfeCeo = await findOrInsert(
    () => db.select().from(agents).where(
      and(eq(agents.orgId, lyfeOrg.id), eq(agents.agentType, 'ceo'))
    ).limit(1),
    () => db.insert(agents).values({
      orgId: lyfeOrg.id,
      portfolioId: portfolio.id,
      name: 'Lyfe Institute CEO',
      agentType: 'ceo',
      soul: {
        description: 'Orchestrator for Lyfe Institute. Focused on Initiate Arena. Reads pipeline, outreach metrics, revenue vs $10K/mo target.',
        tone: 'Revenue-obsessed operator. Every decision traces back to the $10K/mo north star.',
      },
      domainRules: { company: 'Lyfe Institute', north_star: '$10K/month net profit from Initiate Arena' },
      tools: [],
      dataTier: 'internal',
      isActive: true,
    }).returning(),
    'agent: Lyfe Institute CEO',
  )

  // d. Sales Agent — Lyfe Institute
  const salesAgent = await findOrInsert(
    () => db.select().from(agents).where(
      and(eq(agents.orgId, lyfeOrg.id), eq(agents.department, 'sales'))
    ).limit(1),
    () => db.insert(agents).values({
      orgId: lyfeOrg.id,
      portfolioId: portfolio.id,
      name: 'Sales Agent',
      agentType: 'department',
      department: 'sales',
      parentAgentId: lyfeCeo.id,
      soul: {
        description: 'Handles outreach qualification, conversation analysis, lead scoring, and DM strategy for Initiate Arena.',
        tone: 'Direct, empathetic, ICP-obsessed.',
      },
      domainRules: { primary_skill: 'analyze_conversation', icp: 'Ambitious men 18-25, pre-revenue personal development' },
      tools: ['analyze_conversation', 'qualify_lead', 'generate_outreach_from_intel', 'summarize_sales_call'],
      dataTier: 'internal',
      isActive: true,
    }).returning(),
    'agent: Sales Agent',
  )

  // e. Research Agent — Lyfe Institute
  const researchAgent = await findOrInsert(
    () => db.select().from(agents).where(
      and(eq(agents.orgId, lyfeOrg.id), eq(agents.department, 'research'))
    ).limit(1),
    () => db.insert(agents).values({
      orgId: lyfeOrg.id,
      portfolioId: portfolio.id,
      name: 'Research Agent',
      agentType: 'department',
      department: 'research',
      parentAgentId: lyfeCeo.id,
      soul: {
        description: 'Processes signal queue, analyzes ICP data, detects patterns, generates market reports.',
        tone: 'Analytical, precise, pattern-focused.',
      },
      domainRules: { primary_skill: 'analyze_icp_signal' },
      tools: ['analyze_icp_signal', 'detect_icp_patterns', 'generate_market_report', 'process_signal_queue'],
      dataTier: 'internal',
      isActive: true,
    }).returning(),
    'agent: Research Agent',
  )

  // f. Content Agent — Lyfe Institute
  const contentAgent = await findOrInsert(
    () => db.select().from(agents).where(
      and(eq(agents.orgId, lyfeOrg.id), eq(agents.department, 'content'))
    ).limit(1),
    () => db.insert(agents).values({
      orgId: lyfeOrg.id,
      portfolioId: portfolio.id,
      name: 'Content Agent',
      agentType: 'department',
      department: 'content',
      parentAgentId: lyfeCeo.id,
      soul: {
        description: 'Generates content from market intelligence. Translates ICP patterns into hooks, scripts, and post angles.',
        tone: 'Cinematic, visceral, polarizing. Matches AFM personal brand voice exactly.',
      },
      domainRules: { primary_skill: 'generate_outreach_from_intel', brand_voice: 'tactical luxury, anti-hustle-bro' },
      tools: ['generate_outreach_from_intel', 'generate_content_from_intel'],
      dataTier: 'internal',
      isActive: true,
    }).returning(),
    'agent: Content Agent',
  )

  console.log(`  ✓ hierarchy: Portfolio Advisor → [Empyrean CEO | Lyfe CEO → Sales, Research, Content]`)

  // ── [8/9] Workflow ────────────────────────────────────────────────────────
  console.log('\n[8/9] Inserting workflow...')

  const outreachWorkflow = await findOrInsert(
    () => db.select().from(workflows).where(
      and(eq(workflows.orgId, lyfeOrg.id), eq(workflows.name, 'Outreach Pipeline'))
    ).limit(1),
    () => db.insert(workflows).values({
      orgId: lyfeOrg.id,
      name: 'Outreach Pipeline',
      description: 'End-to-end outreach cycle: signal scraping → ICP scoring → opener generation → DM send → outcome logging.',
      executorType: 'hybrid',
      autonomyStage: 'manual',
      triggerType: 'manual',
      isActive: true,
      steps: [
        { step: 1, name: 'Scrape signals',    executor: 'ai',    agentId: researchAgent.id },
        { step: 2, name: 'Score ICP',         executor: 'ai',    agentId: salesAgent.id },
        { step: 3, name: 'Generate opener',   executor: 'ai',    agentId: salesAgent.id,   requiresApproval: true },
        { step: 4, name: 'Send DM',           executor: 'human', assignedRole: 'founder' },
        { step: 5, name: 'Log outcome',       executor: 'ai',    agentId: salesAgent.id },
      ],
    }).returning(),
    'workflow: Outreach Pipeline',
  )

  console.log(`  ✓ workflow: ${outreachWorkflow.id} — ${outreachWorkflow.name}`)

  // ── [9/9] Write .env ─────────────────────────────────────────────────────
  console.log('\nWriting ORG_ID and USER_ID to .env...')
  writeEnvVars(lyfeOrg.id, user.id)

  // ─────────────────────────────────────────────────────────────────────────
  // RLS FIREWALL PROOF
  // ─────────────────────────────────────────────────────────────────────────

  console.log('\n─────────────────────────────────────────')
  console.log('RLS FIREWALL PROOF (as eos_app role)')
  console.log('─────────────────────────────────────────')

  const noOrgResult = await db.transaction(async (tx) => {
    await tx.execute(sql`SET LOCAL ROLE eos_app`)
    return tx.execute(sql`SELECT id, name FROM ventures`)
  })
  const test1Pass = noOrgResult.rows.length === 0
  console.log(`\nTest 1 — eos_app, no org_id: rows=${noOrgResult.rows.length} ${test1Pass ? '✓ PASS' : '✗ FAIL'}`)

  const withOrgResult = await db.transaction(async (tx) => {
    await tx.execute(sql`SET LOCAL ROLE eos_app`)
    await tx.execute(sql`SELECT set_config('app.current_org_id', ${lyfeOrg.id}, true)`)
    return tx.execute(sql`SELECT id, name FROM ventures ORDER BY name`)
  })
  const test2Pass = withOrgResult.rows.length >= 1
  console.log(`\nTest 2 — eos_app + org_id (Lyfe): rows=${withOrgResult.rows.length} ${test2Pass ? '✓ PASS' : '✗ FAIL'}`)
  withOrgResult.rows.forEach((r: any) => console.log(`  → ${r.name}`))

  const skillsResult = await db.transaction(async (tx) => {
    await tx.execute(sql`SET LOCAL ROLE eos_app`)
    await tx.execute(sql`SELECT set_config('app.current_org_id', ${lyfeOrg.id}, true)`)
    return tx.execute(sql`SELECT name FROM skills ORDER BY name`)
  })
  const test3Pass = skillsResult.rows.length === SKILLS.length
  console.log(`\nTest 3 — eos_app + org_id, skills: rows=${skillsResult.rows.length} ${test3Pass ? `✓ PASS (${SKILLS.length} skills)` : `✗ FAIL (expected ${SKILLS.length})`}`)

  console.log('\n─────────────────────────────────────────')
  const allPass = test1Pass && test2Pass && test3Pass
  console.log(allPass ? '✓ All RLS tests passed.' : '✗ One or more RLS tests failed.')
  console.log('─────────────────────────────────────────\n')

  await pool.end()
  process.exit(allPass ? 0 : 1)
}

main().catch(async (err) => {
  console.error('\n✗ Seed failed:', err)
  await pool.end()
  process.exit(1)
})
