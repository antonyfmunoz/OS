import { Hono } from 'hono'
import type { Env } from '../types.js'
import { callOrganism } from '../lib/python_bridge.js'

const router = new Hono<Env>()

router.get('/observations', async (c) => {
  const result = await callOrganism('organism.snapshot')
  if (!result.success) return c.json([])
  const snap = result.data as Record<string, unknown>
  const objectives = (snap.objectives ?? {}) as Record<string, number>
  const workUnits = (snap.work_units ?? {}) as Record<string, number>
  const bottlenecks = (snap.bottlenecks ?? []) as Array<Record<string, unknown>>

  const observations: Array<Record<string, unknown>> = []

  if (objectives.active > 0 || objectives.completed > 0 || objectives.failed > 0) {
    observations.push({
      id: 'obj-summary',
      label: 'Objective Summary',
      description: `${objectives.active} active, ${objectives.completed} completed, ${objectives.failed} failed`,
      primitive_type: 'state',
      source: 'organism.coordinator',
      evidence: JSON.stringify(objectives),
    })
  }

  if (workUnits.running > 0 || workUnits.pending > 0) {
    observations.push({
      id: 'wu-summary',
      label: 'Work Unit Activity',
      description: `${workUnits.running} running, ${workUnits.pending} pending, ${workUnits.blocked} blocked`,
      primitive_type: 'state',
      source: 'organism.coordinator',
      evidence: JSON.stringify(workUnits),
    })
  }

  observations.push({
    id: 'system-mode',
    label: 'System Mode',
    description: `Organism is in ${snap.system_mode} mode`,
    primitive_type: 'state',
    source: 'organism.homeostasis',
    evidence: String(snap.system_mode),
  })

  for (const bn of bottlenecks) {
    observations.push({
      id: `bn-${bn.subsystem}`,
      label: `Bottleneck: ${bn.subsystem}`,
      description: String(bn.description),
      primitive_type: 'constraint',
      source: 'organism.observer',
      evidence: JSON.stringify(bn),
    })
  }

  return c.json(observations)
})

router.get('/memory', async (c) => {
  const result = await callOrganism('organism.learning', { limit: 50 })
  if (!result.success) return c.json([])
  const signals = (result.data ?? []) as Array<Record<string, unknown>>
  return c.json(signals.map((s, i) => ({
    id: s.id ?? `learning-${i}`,
    label: s.signal_type ?? 'learning_signal',
    content: s.content ?? s.lesson ?? '',
    source: s.source ?? 'organism',
    created_at: s.created_at ?? '',
    type: 'learning_signal',
  })))
})

router.get('/tracking', async (c) => {
  const result = await callOrganism('organism.economy')
  if (!result.success) return c.json([])
  const eco = result.data as Record<string, unknown>
  const entries: Array<Record<string, unknown>> = []

  entries.push({
    id: 'eco-summary',
    label: 'Execution Economy',
    metric: 'total_executions',
    value: eco.total_executions ?? 0,
    detail: `Success rate: ${eco.success_rate ?? 0}, Cost: $${eco.total_cost_usd ?? 0}`,
  })

  const profiles = (eco.runtime_profiles ?? {}) as Record<string, Record<string, unknown>>
  for (const [runtimeId, profile] of Object.entries(profiles)) {
    entries.push({
      id: `rt-${runtimeId}`,
      label: `Runtime: ${runtimeId}`,
      metric: 'leverage_score',
      value: profile.overall_leverage ?? 0,
      detail: `${profile.total_executions ?? 0} executions`,
    })
  }

  return c.json(entries)
})

export default router
