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
  last_seen: string
}

interface SystemState {
  pulse: PulseData | null
  meshNodes: MeshNode[]
  loading: boolean
  error: string | null

  fetchPulse: () => Promise<void>
  fetchMeshNodes: () => Promise<void>
  setPulse: (data: PulseData) => void
}

export const useSystemStore = create<SystemState>((set) => ({
  pulse: null,
  meshNodes: [],
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
      const data = await fetchApi<MeshNode[]>('/mesh/nodes')
      set({ meshNodes: data, error: null })
    } catch {
      set({ meshNodes: [] })
    }
  },
}))
