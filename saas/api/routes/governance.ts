import { Hono } from 'hono'
import type { Env } from '../types.js'

const router = new Hono<Env>()

router.get('/', (c) => {
  return c.json({
    policies: [
      { risk_class: 'LOW', risk_level: 'LOW', authority: 'auto', requires_human: false, is_blocked: false, is_blocking_class: false },
      { risk_class: 'MEDIUM', risk_level: 'MEDIUM', authority: 'review', requires_human: false, is_blocked: false, is_blocking_class: false },
      { risk_class: 'HIGH', risk_level: 'HIGH', authority: 'approval', requires_human: true, is_blocked: false, is_blocking_class: true },
      { risk_class: 'CRITICAL', risk_level: 'CRITICAL', authority: 'ceo', requires_human: true, is_blocked: true, is_blocking_class: true },
    ],
    safe_roots: ['/opt/OS'],
    allowed_shell_prefixes: ['docker', 'python3', 'git'],
  })
})

router.patch('/', async (c) => {
  return c.json({ ok: true })
})

export default router
