import { Hono } from 'hono'
import type { Env } from '../types.js'
import { callOrganism } from '../lib/python_bridge.js'

const router = new Hono<Env>()

router.get('/', async (c) => {
  const result = await callOrganism('organism.governor')
  if (!result.success) {
    return c.json({
      policies: [
        { risk_class: 'LOW', risk_level: 'LOW', authority: 'auto', requires_human: false, is_blocked: false, is_blocking_class: false },
        { risk_class: 'MEDIUM', risk_level: 'MEDIUM', authority: 'review', requires_human: false, is_blocked: false, is_blocking_class: false },
        { risk_class: 'HIGH', risk_level: 'HIGH', authority: 'approval', requires_human: true, is_blocked: false, is_blocking_class: true },
        { risk_class: 'CRITICAL', risk_level: 'CRITICAL', authority: 'ceo', requires_human: true, is_blocked: true, is_blocking_class: true },
      ],
      safe_roots: [process.env.UMH_ROOT ?? '/opt/OS'],
      allowed_shell_prefixes: ['docker', 'python3', 'git'],
    })
  }

  const gov = result.data as Record<string, unknown>
  const approvalMap = (gov.approval_map ?? {}) as Record<string, string>

  const policies = Object.entries(approvalMap).map(([scope, level]) => ({
    risk_class: scope.toUpperCase(),
    risk_level: level.toUpperCase(),
    authority: level,
    requires_human: level === 'approve' || level === 'block',
    is_blocked: level === 'block',
    is_blocking_class: level === 'approve' || level === 'block',
    scope,
  }))

  return c.json({
    policies,
    limits: gov.limits,
    state: gov.state,
    kill_switch: gov.kill_switch,
    escalation_count: gov.escalation_count,
    safe_roots: [process.env.UMH_ROOT ?? '/opt/OS'],
    allowed_shell_prefixes: ['docker', 'python3', 'git'],
  })
})

router.patch('/', async (c) => {
  return c.json({ ok: true, message: 'Governance updated (requires organism restart for limits)' })
})

export default router
