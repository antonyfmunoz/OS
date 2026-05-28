import { Hono } from 'hono'
import type { Env } from '../types.js'
import { callOrganism } from '../lib/python_bridge.js'
import { operatorGuard } from '../middleware/operator.js'

const router = new Hono<Env>()

router.get('/snapshot', async (c) => {
  const result = await callOrganism('organism.snapshot')
  if (!result.success) return c.json({ error: result.error }, 502)
  return c.json(result.data)
})

router.get('/status', async (c) => {
  const result = await callOrganism('organism.status')
  if (!result.success) return c.json({ error: result.error }, 502)
  return c.json(result.data)
})

router.get('/health', async (c) => {
  const result = await callOrganism('organism.health')
  if (!result.success) return c.json({ error: result.error }, 502)
  return c.json(result.data)
})

router.get('/agents', async (c) => {
  const result = await callOrganism('organism.agents')
  if (!result.success) return c.json({ error: result.error }, 502)
  return c.json(result.data)
})

router.get('/deliverables', async (c) => {
  const agentId = c.req.query('agent_id')
  const limit = Number(c.req.query('limit') ?? 50)
  const result = await callOrganism('organism.deliverables', { agent_id: agentId, limit })
  if (!result.success) return c.json({ error: result.error }, 502)
  return c.json(result.data)
})

router.get('/learning', async (c) => {
  const limit = Number(c.req.query('limit') ?? 50)
  const result = await callOrganism('organism.learning', { limit })
  if (!result.success) return c.json({ error: result.error }, 502)
  return c.json(result.data)
})

router.get('/objectives', async (c) => {
  const result = await callOrganism('organism.objectives')
  if (!result.success) return c.json({ error: result.error }, 502)
  return c.json(result.data)
})

router.get('/objectives/:id', async (c) => {
  const result = await callOrganism('organism.objective', { objective_id: c.req.param('id') })
  if (!result.success) return c.json({ error: result.error }, 404)
  return c.json(result.data)
})

router.get('/economy', async (c) => {
  const result = await callOrganism('organism.economy')
  if (!result.success) return c.json({ error: result.error }, 502)
  return c.json(result.data)
})

router.get('/economy/records', async (c) => {
  const limit = Number(c.req.query('limit') ?? 20)
  const result = await callOrganism('organism.economy.records', { limit })
  if (!result.success) return c.json({ error: result.error }, 502)
  return c.json(result.data)
})

router.get('/runtimes', async (c) => {
  const result = await callOrganism('organism.runtimes')
  if (!result.success) return c.json({ error: result.error }, 502)
  return c.json(result.data)
})

router.get('/supervisor', async (c) => {
  const result = await callOrganism('organism.supervisor')
  if (!result.success) return c.json({ error: result.error }, 502)
  return c.json(result.data)
})

router.get('/governor', async (c) => {
  const result = await callOrganism('organism.governor')
  if (!result.success) return c.json({ error: result.error }, 502)
  return c.json(result.data)
})

router.get('/governor/escalations', async (c) => {
  const limit = Number(c.req.query('limit') ?? 20)
  const result = await callOrganism('organism.governor.escalations', { limit })
  if (!result.success) return c.json({ error: result.error }, 502)
  return c.json(result.data)
})

router.get('/advisors', async (c) => {
  const result = await callOrganism('organism.advisors')
  if (!result.success) return c.json({ error: result.error }, 502)
  return c.json(result.data)
})

router.get('/advisors/tree', async (c) => {
  const result = await callOrganism('organism.advisors.tree')
  if (!result.success) return c.json({ error: result.error }, 502)
  return c.json(result.data)
})

router.get('/approvals', async (c) => {
  const status = c.req.query('status')
  const limit = Number(c.req.query('limit') ?? 50)
  const result = await callOrganism('organism.approvals', { status, limit })
  if (!result.success) return c.json({ error: result.error }, 502)
  return c.json(result.data)
})

router.get('/approvals/count', async (c) => {
  const result = await callOrganism('organism.approvals.count')
  if (!result.success) return c.json({ error: result.error }, 502)
  return c.json(result.data)
})

router.get('/handoffs', async (c) => {
  const result = await callOrganism('organism.handoffs')
  if (!result.success) return c.json({ error: result.error }, 502)
  return c.json(result.data)
})

router.get('/leverage', async (c) => {
  const result = await callOrganism('organism.leverage')
  if (!result.success) return c.json({ error: result.error }, 502)
  return c.json(result.data)
})

// ── Phase 8: substrate-level intelligence (operator-only) ──────
router.get('/world-model', operatorGuard, async (c) => {
  const result = await callOrganism('organism.world_model')
  if (!result.success) return c.json({ error: result.error }, 502)
  return c.json(result.data)
})

router.get('/dependency-graph', operatorGuard, async (c) => {
  const result = await callOrganism('organism.dependency_graph')
  if (!result.success) return c.json({ error: result.error }, 502)
  return c.json(result.data)
})

router.get('/contradictions', operatorGuard, async (c) => {
  const result = await callOrganism('organism.contradictions')
  if (!result.success) return c.json({ error: result.error }, 502)
  return c.json(result.data)
})

router.get('/learning-loop', operatorGuard, async (c) => {
  const result = await callOrganism('organism.learning_loop')
  if (!result.success) return c.json({ error: result.error }, 502)
  return c.json(result.data)
})

router.post('/outcome', operatorGuard, async (c) => {
  const body = await c.req.json().catch(() => ({}))
  const result = await callOrganism('organism.outcome_capture', body as Record<string, unknown>)
  if (!result.success) return c.json({ error: result.error }, 400)
  return c.json(result.data)
})

router.get('/memory-promotion', operatorGuard, async (c) => {
  const result = await callOrganism('organism.memory_promotion')
  if (!result.success) return c.json({ error: result.error }, 502)
  return c.json(result.data)
})

router.post('/memory-promotion/:id/approve', operatorGuard, async (c) => {
  const result = await callOrganism('organism.memory_promotion.approve', { id: c.req.param('id') })
  if (!result.success) return c.json({ error: result.error }, 400)
  return c.json(result.data)
})

router.post('/memory-promotion/:id/reject', operatorGuard, async (c) => {
  const body = await c.req.json().catch(() => ({}))
  const reason = (body as Record<string, unknown>).reason as string
  const result = await callOrganism('organism.memory_promotion.reject', { id: c.req.param('id'), reason })
  if (!result.success) return c.json({ error: result.error }, 400)
  return c.json(result.data)
})

router.post('/compose', operatorGuard, async (c) => {
  const body = await c.req.json().catch(() => ({}))
  const intent = (body as Record<string, unknown>).intent as string
  const result = await callOrganism('organism.compose', { intent })
  if (!result.success) return c.json({ error: result.error }, 400)
  return c.json(result.data)
})

// ── Phase 9.1: Plan Execution Adapter ────────────────────────
router.post('/execute-plan', operatorGuard, async (c) => {
  const body = await c.req.json().catch(() => ({}))
  const intent = (body as Record<string, unknown>).intent as string
  const result = await callOrganism('organism.execute_plan', { intent })
  if (!result.success) return c.json({ error: result.error }, 400)
  return c.json(result.data)
})

router.get('/execution-graph', operatorGuard, async (c) => {
  const result = await callOrganism('organism.execution_graph')
  if (!result.success) return c.json({ error: result.error }, 502)
  return c.json(result.data)
})

router.get('/execution-graph/:id', operatorGuard, async (c) => {
  const result = await callOrganism('organism.execution_graph.detail', {
    plan_id: c.req.param('id'),
  })
  if (!result.success) return c.json({ error: result.error }, 404)
  return c.json(result.data)
})

router.post('/execute-plan/:planId/approve/:stepId', operatorGuard, async (c) => {
  const result = await callOrganism('organism.execute_plan.approve_step', {
    plan_id: c.req.param('planId'),
    step_id: c.req.param('stepId'),
  })
  if (!result.success) return c.json({ error: result.error }, 400)
  return c.json(result.data)
})

router.get('/execute-plan/:planId/pending', operatorGuard, async (c) => {
  const result = await callOrganism('organism.execute_plan.pending', {
    plan_id: c.req.param('planId'),
  })
  if (!result.success) return c.json({ error: result.error }, 502)
  return c.json(result.data)
})

router.get('/workcells', async (c) => {
  const result = await callOrganism('organism.workcells')
  if (!result.success) return c.json({ error: result.error }, 502)
  return c.json(result.data)
})

// ── Phase 9.2: Self-improvement trial surface ────────────────
router.get('/trial-status', operatorGuard, async (c) => {
  const result = await callOrganism('organism.trial_status')
  if (!result.success) return c.json({ error: result.error }, 502)
  return c.json(result.data)
})

// ── Governed mutations (operator-only) ─────────────────────────
router.post('/approve/:id', operatorGuard, async (c) => {
  const result = await callOrganism('organism.approve', {
    approval_id: c.req.param('id'),
    decided_by: 'cockpit',
  })
  if (!result.success) return c.json({ error: result.error }, 400)
  return c.json(result.data)
})

router.post('/deny/:id', operatorGuard, async (c) => {
  const result = await callOrganism('organism.deny', {
    approval_id: c.req.param('id'),
    decided_by: 'cockpit',
  })
  if (!result.success) return c.json({ error: result.error }, 400)
  return c.json(result.data)
})

router.post('/kill', operatorGuard, async (c) => {
  const result = await callOrganism('organism.kill')
  if (!result.success) return c.json({ error: result.error }, 500)
  return c.json(result.data)
})

router.post('/resume', operatorGuard, async (c) => {
  const result = await callOrganism('organism.resume')
  if (!result.success) return c.json({ error: result.error }, 500)
  return c.json(result.data)
})

router.post('/governor/reset', operatorGuard, async (c) => {
  const result = await callOrganism('organism.governor.reset')
  if (!result.success) return c.json({ error: result.error }, 500)
  return c.json(result.data)
})

router.post('/refresh', async (c) => {
  const result = await callOrganism('organism.refresh')
  if (!result.success) return c.json({ error: result.error }, 502)
  return c.json(result.data)
})

router.get('/delegations', async (c) => {
  const result = await callOrganism('organism.handoffs')
  if (!result.success) return c.json({ followups: [] })
  return c.json({ followups: result.data })
})

router.post('/control', async (c) => {
  const body = await c.req.json().catch(() => ({}))
  const action = (body as Record<string, unknown>).action as string
  if (action === 'kill') return c.json((await callOrganism('organism.kill')).data)
  if (action === 'resume') return c.json((await callOrganism('organism.resume')).data)
  return c.json({ ok: true, action })
})

router.post('/handoff', async (c) => {
  return c.json({ ok: true, handoff: 'queued' })
})

router.post('/parallel', async (c) => {
  return c.json({ ok: true, results: [] })
})

export default router
