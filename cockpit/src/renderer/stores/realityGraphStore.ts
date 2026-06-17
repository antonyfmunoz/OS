import { create } from 'zustand'

interface RealityEntity {
  entity_id: string
  entity_type: string
  name: string
  status: string
  properties: Record<string, unknown>
  source_system: string
  source_id: string
  last_observed: number
}

interface GraphSummary {
  entity_count: number
  relation_count: number
  entities_by_type: Record<string, number>
  relations_by_type: Record<string, number>
  built_at: number
}

interface ResolvedContext {
  project_id: string
  project_name: string
  repository_id: string
  repository_name: string
  workspace_id: string
  workspace_name: string
  device_id: string
  active_device: string
  projection: string
  documents: Array<Record<string, unknown>>
  infrastructure: Array<Record<string, unknown>>
  unresolved_references: string[]
  resolution_chain: Array<Record<string, string>>
  confidence: number
  strategy: string
  resolved_at: number
}

interface RealityGraphState {
  summary: GraphSummary | null
  entities: RealityEntity[]
  selectedEntity: RealityEntity | null
  neighbors: RealityEntity[]
  resolvedContext: ResolvedContext | null
  loading: boolean
  fetchSummary: () => Promise<void>
  fetchEntities: (entityType?: string) => Promise<void>
  fetchEntity: (entityId: string) => Promise<void>
  fetchNeighbors: (entityId: string) => Promise<void>
  resolveContext: (text: string) => Promise<void>
  searchEntities: (q: string) => Promise<void>
}

const API = '/api/umh'

export const useRealityGraphStore = create<RealityGraphState>((set) => ({
  summary: null,
  entities: [],
  selectedEntity: null,
  neighbors: [],
  resolvedContext: null,
  loading: false,

  fetchSummary: async () => {
    set({ loading: true })
    try {
      const res = await fetch(`${API}/reality-graph/summary`)
      if (res.ok) set({ summary: await res.json() })
    } catch { /* ignore */ }
    set({ loading: false })
  },

  fetchEntities: async (entityType?: string) => {
    set({ loading: true })
    try {
      const url = entityType
        ? `${API}/reality-graph/entities?entity_type=${entityType}`
        : `${API}/reality-graph/entities`
      const res = await fetch(url)
      if (res.ok) {
        const data = await res.json()
        set({ entities: data.entities || [] })
      }
    } catch { /* ignore */ }
    set({ loading: false })
  },

  fetchEntity: async (entityId: string) => {
    set({ loading: true })
    try {
      const res = await fetch(`${API}/reality-graph/entity/${entityId}`)
      if (res.ok) set({ selectedEntity: await res.json() })
    } catch { /* ignore */ }
    set({ loading: false })
  },

  fetchNeighbors: async (entityId: string) => {
    try {
      const res = await fetch(`${API}/reality-graph/neighbors/${entityId}`)
      if (res.ok) {
        const data = await res.json()
        set({ neighbors: data.neighbors || [] })
      }
    } catch { /* ignore */ }
  },

  resolveContext: async (text: string) => {
    set({ loading: true })
    try {
      const res = await fetch(`${API}/context-resolution/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      })
      if (res.ok) set({ resolvedContext: await res.json() })
    } catch { /* ignore */ }
    set({ loading: false })
  },

  searchEntities: async (q: string) => {
    set({ loading: true })
    try {
      const res = await fetch(`${API}/reality-graph/search?q=${encodeURIComponent(q)}`)
      if (res.ok) {
        const data = await res.json()
        set({ entities: data.results || [] })
      }
    } catch { /* ignore */ }
    set({ loading: false })
  },
}))
