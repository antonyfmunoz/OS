import { Hono } from 'hono'
import type { Env } from '../types.js'

const router = new Hono<Env>()

router.get('/observations', (c) => {
  return c.json([])
})

router.get('/memory', (c) => {
  return c.json([])
})

router.get('/tracking', (c) => {
  return c.json([])
})

export default router
