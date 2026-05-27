import { Hono } from 'hono'
import type { Env } from '../types.js'

const router = new Hono<Env>()

router.get('/status', (c) => {
  return c.json({
    slots: [
      { slot: 0, layer: 'native', task: '', status: 'idle', step_count: 0, authority_class: 'operator', risk_class: 'LOW', approval_status: 'none' },
      { slot: 1, layer: 'container', task: '', status: 'idle', step_count: 0, authority_class: 'operator', risk_class: 'LOW', approval_status: 'none' },
      { slot: 2, layer: 'wsl', task: '', status: 'idle', step_count: 0, authority_class: 'operator', risk_class: 'LOW', approval_status: 'none' },
      { slot: 3, layer: 'vm', task: '', status: 'idle', step_count: 0, authority_class: 'operator', risk_class: 'LOW', approval_status: 'none' },
    ],
  })
})

router.get('/log', (c) => {
  const slot = Number(c.req.query('slot') ?? 0)
  return c.json({ slot, log: [] })
})

router.get('/authority', (c) => {
  const layer = c.req.query('layer') ?? 'native'
  return c.json({
    layer,
    authority_class: 'operator',
    risk_class: 'LOW',
    approval_requirement: 'none',
  })
})

router.post('/start', (c) => c.json({ ok: true }))
router.post('/stop', (c) => c.json({ ok: true }))
router.post('/pause', (c) => c.json({ ok: true }))
router.post('/resume', (c) => c.json({ ok: true }))

export default router
