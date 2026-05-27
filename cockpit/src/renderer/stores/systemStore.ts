import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface PulseData {
  cpu_percent: number
  memory_percent: number
  disk_percent: number
  uptime: number
  active_agents: number
  pending_tasks: number
  pending_approvals: number
  trace_rate: number
}

interface MeshNode {
  node_id: string
  hostname: string
  role: string
  status: string
  os: string
  ip: string
  last_seen: string
}

export interface ModelBadge {
  id: string
  name: string
  provider: string
  status: 'active' | 'fallback' | 'offline' | 'degraded'
  latency_ms: number
  cost_per_m_token: number
}

export interface TraceEvent {
  id: string
  timestamp: string
  agent: string
  action: string
  status: 'running' | 'completed' | 'failed' | 'pending'
  durationMs?: number
}

export interface InfraNode {
  id: string
  name: string
  type: 'compute' | 'storage' | 'network' | 'service'
  status: 'healthy' | 'degraded' | 'down'
  metrics: { cpu?: number; memory?: number; disk?: number; latency?: number; cost?: number }
}

interface RawTask {
  id: string
  title: string
  agent: string
  status: string
  created_at?: string
  updated_at?: string
  duration_ms?: number
}

const TASK_STATUS_MAP: Record<string, TraceEvent['status']> = {
  in_progress: 'running',
  blocked: 'failed',
  failed: 'failed',
  completed: 'completed',
  pending: 'pending',
}

interface SystemState {
  pulse: PulseData | null
  meshNodes: MeshNode[]
  models: ModelBadge[]
  traces: TraceEvent[]
  infraNodes: InfraNode[]
  loading: boolean
  error: string | null

  fetchPulse: () => Promise<void>
  fetchMeshNodes: () => Promise<void>
  fetchModels: () => Promise<void>
  fetchTraces: () => Promise<void>
  fetchInfra: () => Promise<void>
  setPulse: (data: PulseData) => void
}

export const useSystemStore = create<SystemState>((set) => ({
  pulse: null,
  meshNodes: [],
  models: [],
  traces: [],
  infraNodes: [],
  loading: false,
  error: null,

  setPulse: (data) => set({ pulse: data, error: null }),

  fetchPulse: async () => {
    try {
      const data = await fetchApi<PulseData>('/pulse')
      set({ pulse: data, error: null })
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to fetch pulse' })
    }
  },

  fetchMeshNodes: async () => {
    try {
      const raw = await fetchApi<Array<Record<string, unknown>>>('/mesh/nodes')
      const nodes: MeshNode[] = raw.map((n) => ({
        node_id: (n.node_id ?? n.id ?? '') as string,
        hostname: (n.hostname ?? n.name ?? '') as string,
        role: (n.role ?? 'node') as string,
        status: String(n.status) === 'connected' || String(n.status) === 'online' ? 'online' : String(n.status),
        os: (n.os ?? '') as string,
        ip: (n.ip ?? '') as string,
        last_seen: (n.last_seen ?? n.last_heartbeat ?? '') as string,
      }))
      set({ meshNodes: nodes, error: null })
    } catch {
      set({ meshNodes: [] })
    }
  },

  fetchModels: async () => {
    try {
      const data = await fetchApi<ModelBadge[]>('/models')
      set({ models: data })
    } catch {
      set({ models: [] })
    }
  },

  fetchTraces: async () => {
    try {
      const data = await fetchApi<RawTask[]>('/tasks')
      const traces: TraceEvent[] = data.map((t) => ({
        id: t.id,
        timestamp: t.updated_at ?? t.created_at ?? new Date().toISOString(),
        agent: t.agent,
        action: t.title,
        status: TASK_STATUS_MAP[t.status] ?? 'pending',
        durationMs: t.duration_ms,
      }))
      set({ traces })
    } catch {
      set({ traces: [] })
    }
  },

  fetchInfra: async () => {
    try {
      const data = await fetchApi<InfraNode[]>('/infra')
      set({ infraNodes: data })
    } catch {
      set({ infraNodes: [] })
    }
  },
}))
