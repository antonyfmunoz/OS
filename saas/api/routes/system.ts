import { Hono } from 'hono'
import { execFileSync } from 'child_process'
import os from 'os'
import type { Env } from '../types.js'
import { callOrganism } from '../lib/python_bridge.js'

const router = new Hono<Env>()

function safeExecFile(cmd: string, args: string[], fallback = ''): string {
  try {
    return execFileSync(cmd, args, { timeout: 3000, encoding: 'utf-8' }).trim()
  } catch {
    return fallback
  }
}

router.get('/pulse', async (c) => {
  const cpus = os.cpus()
  const cpuIdle = cpus.reduce((sum, cpu) => sum + cpu.times.idle, 0)
  const cpuTotal = cpus.reduce(
    (sum, cpu) => sum + cpu.times.user + cpu.times.nice + cpu.times.sys + cpu.times.idle + cpu.times.irq,
    0,
  )
  const cpuPercent = cpuTotal > 0 ? ((1 - cpuIdle / cpuTotal) * 100) : 0

  const totalMem = os.totalmem()
  const freeMem = os.freemem()
  const memPercent = totalMem > 0 ? ((1 - freeMem / totalMem) * 100) : 0

  const diskRaw = safeExecFile('df', ['/', '--output=pcent'])
  const diskLine = diskRaw.split('\n').pop() ?? ''
  const diskPercent = parseFloat(diskLine.replace('%', '').trim()) || 0

  const uptime = os.uptime()

  const dockerPs = safeExecFile('docker', ['ps', '--format', '{{.Names}}'])
  const activeContainers = dockerPs ? dockerPs.split('\n').filter(Boolean).length : 0

  let pendingTasks = 0
  let pendingApprovals = 0
  let traceRate = 0
  let systemMode = 'healthy'

  const [snapResult, approvalResult] = await Promise.all([
    callOrganism('organism.snapshot').catch(() => ({ success: false, data: null })),
    callOrganism('organism.approvals.count').catch(() => ({ success: false, data: null })),
  ])

  if (snapResult.success && snapResult.data) {
    const snap = snapResult.data as Record<string, unknown>
    const workUnits = (snap.work_units ?? {}) as Record<string, number>
    pendingTasks = (workUnits.pending ?? 0) + (workUnits.running ?? 0)
    const daemon = (snap.daemon ?? {}) as Record<string, number>
    traceRate = daemon.throughput_per_min ?? 0
    systemMode = (snap.system_mode as string) ?? 'healthy'
  }
  if (approvalResult.success && approvalResult.data) {
    pendingApprovals = (approvalResult.data as Record<string, number>).pending ?? 0
  }

  return c.json({
    cpu_percent: Math.round(cpuPercent * 10) / 10,
    memory_percent: Math.round(memPercent * 10) / 10,
    disk_percent: diskPercent,
    uptime,
    active_agents: activeContainers,
    pending_tasks: pendingTasks,
    pending_approvals: pendingApprovals,
    trace_rate: traceRate,
    system_mode: systemMode,
  })
})

router.get('/mesh/nodes', (c) => {
  const raw = safeExecFile('tailscale', ['status', '--json'])
  if (!raw.startsWith('{')) {
    return c.json([{
      node_id: 'vps-primary',
      hostname: os.hostname(),
      role: 'orchestrator',
      status: 'online',
      os: 'linux',
      ip: '',
      last_seen: new Date().toISOString(),
    }])
  }

  const ts = JSON.parse(raw)

  const roleMap: Record<string, string> = {
    'srv1500858': 'orchestrator',
    'desktop-lvguiq9': 'gpu-workhorse',
  }
  const nameMap: Record<string, string> = {
    'desktop-lvguiq9': 'Beast PC',
    'ipad-pro-12-9-gen-5': 'iPad Pro',
    'iphone-15-pro-max': 'iPhone 15 Pro Max',
  }

  interface TsNode {
    HostName: string
    DNSName?: string
    OS: string
    Online: boolean
    TailscaleIPs?: string[]
    LastSeen?: string
  }

  function mapNode(n: TsNode): { key: string; node: object } | null {
    const dns = n.DNSName?.split('.')[0] ?? ''
    const display = (n.HostName.toLowerCase() === 'localhost' || !n.HostName) && dns ? dns : n.HostName
    const key = display.toLowerCase()
    if (key.startsWith('umh-cockpit')) return null
    return {
      key,
      node: {
        node_id: key,
        hostname: nameMap[key] ?? display,
        role: roleMap[key] ?? (n.OS === 'iOS' ? 'mobile' : 'node'),
        status: n.Online ? 'online' : 'offline',
        os: n.OS,
        ip: n.TailscaleIPs?.[0] ?? '',
        last_seen: n.LastSeen && n.LastSeen !== '0001-01-01T00:00:00Z'
          ? n.LastSeen
          : n.Online ? new Date().toISOString() : '',
      },
    }
  }

  const nodes: object[] = []
  const seen = new Set<string>()

  if (ts.Self) {
    const mapped = mapNode(ts.Self)
    if (mapped && !seen.has(mapped.key)) {
      nodes.push(mapped.node)
      seen.add(mapped.key)
    }
  }

  if (ts.Peer) {
    for (const p of Object.values(ts.Peer) as TsNode[]) {
      const mapped = mapNode(p)
      if (!mapped || seen.has(mapped.key)) continue
      seen.add(mapped.key)
      nodes.push(mapped.node)
    }
  }

  return c.json(nodes)
})

router.get('/models', (c) => {
  type ModelStatus = 'active' | 'fallback' | 'offline' | 'degraded'
  const models: Array<{ id: string; name: string; provider: string; status: ModelStatus; latency_ms: number; cost_per_m_token: number }> = [
    { id: 'cc-sdk', name: 'Claude Opus 4.6', provider: 'anthropic', status: 'active', latency_ms: 60000, cost_per_m_token: 0 },
    { id: 'gemini-flash', name: 'Gemini 2.5 Flash', provider: 'google', status: 'active', latency_ms: 2000, cost_per_m_token: 0.15 },
    { id: 'groq-llama', name: 'Groq Llama', provider: 'groq', status: 'fallback', latency_ms: 500, cost_per_m_token: 0 },
  ]

  const ollamaUp = safeExecFile('curl', ['-s', '--max-time', '1', 'http://localhost:11434/api/tags'])
  if (ollamaUp) {
    models.push({ id: 'ollama-local', name: 'Ollama (local)', provider: 'ollama', status: 'fallback', latency_ms: 1000, cost_per_m_token: 0 })
  } else {
    models.push({ id: 'ollama-local', name: 'Ollama (local)', provider: 'ollama', status: 'offline', latency_ms: 0, cost_per_m_token: 0 })
  }

  return c.json(models)
})

router.get('/infra', (c) => {
  const services: Array<{
    id: string
    name: string
    type: 'compute' | 'storage' | 'network' | 'service'
    status: 'healthy' | 'degraded' | 'down'
    metrics: Record<string, number>
  }> = []

  const dockerPs = safeExecFile('docker', ['ps', '-a', '--format', '{{.Names}}|{{.Status}}'])
  if (dockerPs) {
    for (const line of dockerPs.split('\n').filter(Boolean)) {
      const [name, rawStatus] = line.split('|')
      const isUp = rawStatus?.startsWith('Up') ?? false
      services.push({
        id: `docker-${name}`,
        name,
        type: 'service',
        status: isUp ? 'healthy' : 'down',
        metrics: {},
      })
    }
  }

  services.push({
    id: 'neon-postgres',
    name: 'Neon Postgres',
    type: 'storage',
    status: process.env.DATABASE_URL ? 'healthy' : 'down',
    metrics: {},
  })

  services.push({
    id: 'tailscale-mesh',
    name: 'Tailscale',
    type: 'network',
    status: safeExecFile('tailscale', ['status', '--json']).startsWith('{') ? 'healthy' : 'degraded',
    metrics: {},
  })

  return c.json(services)
})

router.get('/sessions', async (c) => {
  const result = await callOrganism('organism.sessions')
  return c.json(result.success ? result.data : [])
})

router.get('/docker', async (c) => {
  const result = await callOrganism('organism.docker')
  return c.json(result.success ? result.data : [])
})

router.get('/workspaces', async (c) => {
  const result = await callOrganism('organism.workspaces')
  return c.json(result.success ? result.data : [])
})

router.get('/files', async (c) => {
  const path = c.req.query('path')
  if (!path) return c.json({ error: 'path query parameter required' }, 400)
  const result = await callOrganism('organism.files', { path })
  if (!result.success) return c.json({ error: result.error }, 400)
  return c.json(result.data)
})

router.get('/file', async (c) => {
  const path = c.req.query('path')
  if (!path) return c.json({ error: 'path query parameter required' }, 400)
  const result = await callOrganism('organism.file.read', { path })
  if (!result.success) return c.json({ error: result.error }, 400)
  return c.json(result.data)
})

export default router
