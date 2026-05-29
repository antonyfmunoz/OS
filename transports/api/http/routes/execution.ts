import { Hono } from 'hono'
import type { Env } from '../types.js'
import { callOrganism } from '../lib/python_bridge.js'

const router = new Hono<Env>()

router.get('/status', async (c) => {
  const [workcells, governor, snapshot] = await Promise.all([
    callOrganism('organism.workcells'),
    callOrganism('organism.governor'),
    callOrganism('organism.snapshot'),
  ])

  const govData = governor.data as Record<string, unknown> | undefined
  const snapData = snapshot.data as Record<string, unknown> | undefined
  const workUnits = (snapData?.work_units ?? {}) as Record<string, number>

  const slots = [
    {
      slot: 0,
      layer: 'native',
      task: workUnits.running > 0 ? `${workUnits.running} work unit(s) running` : '',
      status: workUnits.running > 0 ? 'running' : 'idle',
      step_count: (workUnits.completed ?? 0) + (workUnits.running ?? 0),
      authority_class: 'operator',
      risk_class: 'LOW',
      approval_status: 'none',
    },
    {
      slot: 1,
      layer: 'container',
      task: '',
      status: 'idle',
      step_count: 0,
      authority_class: 'operator',
      risk_class: 'LOW',
      approval_status: 'none',
    },
    {
      slot: 2,
      layer: 'wsl',
      task: '',
      status: 'unavailable',
      step_count: 0,
      authority_class: 'operator',
      risk_class: 'LOW',
      approval_status: 'none',
    },
    {
      slot: 3,
      layer: 'vm',
      task: '',
      status: 'unavailable',
      step_count: 0,
      authority_class: 'operator',
      risk_class: 'LOW',
      approval_status: 'none',
    },
  ]

  return c.json({
    slots,
    workcells: workcells.success ? workcells.data : null,
    governor: govData ? {
      kill_switch: (govData as Record<string, unknown>).kill_switch,
      state: (govData as Record<string, unknown>).state,
      limits: (govData as Record<string, unknown>).limits,
    } : null,
    work_units: workUnits,
  })
})

router.get('/log', async (c) => {
  const slot = Number(c.req.query('slot') ?? 0)
  const result = await callOrganism('organism.economy.records', { limit: 20 })
  return c.json({
    slot,
    log: result.success ? result.data : [],
  })
})

router.get('/authority', async (c) => {
  const result = await callOrganism('organism.governor')
  if (!result.success) {
    return c.json({
      layer: c.req.query('layer') ?? 'native',
      authority_class: 'operator',
      risk_class: 'LOW',
      approval_requirement: 'none',
    })
  }
  const gov = result.data as Record<string, unknown>
  const approvalMap = (gov.approval_map ?? {}) as Record<string, string>
  return c.json({
    layer: c.req.query('layer') ?? 'native',
    authority_class: 'governed',
    risk_class: (gov.kill_switch as boolean) ? 'CRITICAL' : 'MEDIUM',
    approval_requirement: approvalMap.agent ?? 'notify',
    kill_switch: gov.kill_switch,
    limits: gov.limits,
    state: gov.state,
  })
})

router.post('/start', async (c) => {
  const result = await callOrganism('organism.resume')
  return c.json(result.success ? result.data : { ok: false, error: result.error })
})

router.post('/stop', async (c) => {
  const result = await callOrganism('organism.kill')
  return c.json(result.success ? result.data : { ok: false, error: result.error })
})

router.post('/pause', async (c) => {
  const result = await callOrganism('organism.kill')
  return c.json(result.success ? result.data : { ok: false, error: result.error })
})

router.post('/resume', async (c) => {
  const result = await callOrganism('organism.resume')
  return c.json(result.success ? result.data : { ok: false, error: result.error })
})

export default router
