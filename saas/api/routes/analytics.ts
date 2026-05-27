import { Hono } from 'hono'
import { eq, sql, desc } from 'drizzle-orm'
import type { Env } from '../types.js'
import { withOrg } from '../../db/client.js'
import { interactions, clients, transactions } from '../../db/schema.js'
import { callOrganism } from '../lib/python_bridge.js'

const router = new Hono<Env>()

router.get('/', async (c) => {
  const orgId = c.get('orgId')

  const rows = await withOrg(orgId, (tx) =>
    tx.select({
      model: interactions.modelUsed,
      count: sql<number>`count(*)::int`,
      tokens: sql<number>`coalesce(sum((${interactions.tokensJson}->>'total')::int), 0)::int`,
      cost: sql<number>`coalesce(sum((${interactions.tokensJson}->>'cost_usd')::numeric), 0)::numeric`,
    }).from(interactions)
      .where(eq(interactions.orgId, orgId))
      .groupBy(interactions.modelUsed)
  )

  return c.json({
    model_usage: rows.map((r) => ({
      model: r.model,
      calls: r.count,
      tokens: r.tokens,
      cost: Number(r.cost),
    })),
    daily_traces: [],
    error_rate: 0,
    avg_latency_ms: 0,
    total_cost_30d: rows.reduce((sum, r) => sum + Number(r.cost), 0),
  })
})

router.get('/kpis', async (c) => {
  const orgId = c.get('orgId')

  const clientCount = await withOrg(orgId, (tx) =>
    tx.select({ count: sql<number>`count(*)::int` }).from(clients)
  )

  const txData = await withOrg(orgId, (tx) =>
    tx.select({
      total: sql<number>`coalesce(sum(${transactions.amountCents}), 0)::int`,
      count: sql<number>`count(*)::int`,
    }).from(transactions)
  )

  return c.json({
    cards: [
      { name: 'Total Leads', value: clientCount[0]?.count ?? 0, unit: '', trend: '', period: 'all-time' },
      { name: 'Revenue', value: ((txData[0]?.total ?? 0) / 100).toFixed(2), unit: 'USD', trend: '', period: '30d' },
      { name: 'Transactions', value: txData[0]?.count ?? 0, unit: '', trend: '', period: '30d' },
    ],
  })
})

router.get('/pipeline', async (c) => {
  const orgId = c.get('orgId')

  const stages = await withOrg(orgId, (tx) =>
    tx.select({
      status: clients.status,
      count: sql<number>`count(*)::int`,
    }).from(clients)
      .groupBy(clients.status)
  )

  const total = stages.reduce((s, r) => s + r.count, 0)

  return c.json({
    stages: stages.map((s) => ({ name: s.status, count: s.count, value: 0 })),
    total_leads: total,
    total_value: 0,
    conversion_rate: 0,
  })
})

router.get('/accountability', async (c) => {
  const result = await callOrganism('organism.economy')
  if (!result.success) {
    return c.json({ fulfillment_rate: 0, current_streak: 0, pending_follow_ups: 0, period_stats: {} })
  }
  const eco = result.data as Record<string, unknown>
  return c.json({
    fulfillment_rate: eco.success_rate ?? 0,
    current_streak: eco.total_executions ?? 0,
    pending_follow_ups: 0,
    total_cost_usd: eco.total_cost_usd ?? 0,
    time_saved_minutes: eco.total_time_saved_minutes ?? 0,
    avg_leverage: eco.avg_leverage_score ?? 0,
    period_stats: eco.runtime_profiles ?? {},
  })
})

router.get('/intelligence', async (c) => {
  const [healthResult, govResult] = await Promise.all([
    callOrganism('organism.health').catch(() => ({ success: false, data: null })),
    callOrganism('organism.governor').catch(() => ({ success: false, data: null })),
  ])

  const health = healthResult.success ? healthResult.data as Record<string, unknown> : {}
  const gov = govResult.success ? govResult.data as Record<string, unknown> : {}

  return c.json({
    system_mode: health.mode ?? 'unknown',
    dimensions: health.dimensions ?? [],
    governance: {
      kill_switch: gov.kill_switch ?? false,
      escalation_count: gov.escalation_count ?? 0,
      limits: gov.limits ?? {},
      state: gov.state ?? {},
    },
  })
})

export default router
