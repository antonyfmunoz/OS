import { Hono } from 'hono'
import type { Env } from '../types.js'
import { callOrganism } from '../lib/python_bridge.js'
import { governedMutation } from '../lib/governed_bridge.js'

const router = new Hono<Env>()

router.get('/', async (c) => {
  const [runtimes, governor] = await Promise.all([
    callOrganism('organism.runtimes'),
    callOrganism('organism.governor'),
  ])

  const govData = governor.data as Record<string, unknown> | undefined
  const rtData = runtimes.data as Record<string, unknown> | undefined
  const nodes = ((rtData?.nodes ?? []) as Array<Record<string, unknown>>)

  const modelRouting = nodes.length > 0
    ? nodes.map((n, i) => ({
        provider: n.runtime_id ?? `runtime-${i}`,
        priority: i,
        enabled: n.status === 'available',
        runtime_class: n.runtime_class ?? 'unknown',
        capabilities: n.capabilities ?? [],
      }))
    : [
        { provider: 'cc-sdk', priority: 0, enabled: true, runtime_class: 'AI_CLI', capabilities: [] },
        { provider: 'gemini-flash', priority: 1, enabled: true, runtime_class: 'AI_API', capabilities: [] },
        { provider: 'groq', priority: 2, enabled: true, runtime_class: 'AI_API', capabilities: [] },
        { provider: 'ollama', priority: 3, enabled: true, runtime_class: 'LOCAL_MODEL', capabilities: [] },
      ]

  return c.json({
    model_routing: modelRouting,
    governance: govData ? {
      auto_approve_low: (govData.approval_map as Record<string, string>)?.deterministic === 'none',
      critical_block: (govData.approval_map as Record<string, string>)?.production_impact === 'block',
      kill_switch: govData.kill_switch,
      limits: govData.limits,
      approval_map: govData.approval_map,
    } : {
      auto_approve_low: true,
      critical_block: true,
    },
    notifications: { discord: true, file: true },
  })
})

router.patch('/', async (c) => {
  const body = await c.req.json().catch(() => ({})) as Record<string, unknown>
  const result = await governedMutation({
    mutation_name: 'settings_update',
    intent: 'update settings',
    payload: body,
  })
  return c.json(result)
})

export default router
