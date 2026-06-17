import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface TopologyNode {
  id?: string
  type: string
  [key: string]: unknown
}

interface TopologyEdge {
  [key: string]: unknown
}

interface OrganismMapState {
  topology: { nodes: TopologyNode[]; edges: TopologyEdge[] } | null
  health: Record<string, unknown> | null
  selectedNode: Record<string, unknown> | null
  loading: boolean
  error: string | null
  fetchTopology: () => Promise<void>
  fetchHealth: () => Promise<void>
  fetchNodeDetail: (nodeId: string) => Promise<void>
  clearSelection: () => void
}

export const useOrganismMapStore = create<OrganismMapState>((set) => ({
  topology: null,
  health: null,
  selectedNode: null,
  loading: false,
  error: null,

  fetchTopology: async () => {
    set({ loading: true, error: null })
    try {
      const data = await fetchApi('/api/umh/organism-map/topology')
      set({
        topology: {
          nodes: data.nodes ?? [],
          edges: data.edges ?? [],
        },
        loading: false,
      })
    } catch (e) {
      set({ error: String(e), loading: false })
    }
  },

  fetchHealth: async () => {
    try {
      const data = await fetchApi('/api/umh/organism-map/health')
      set({ health: data })
    } catch (e) {
      set({ error: String(e) })
    }
  },

  fetchNodeDetail: async (nodeId: string) => {
    set({ loading: true })
    try {
      const data = await fetchApi(`/api/umh/organism-map/node/${encodeURIComponent(nodeId)}`)
      set({ selectedNode: data, loading: false })
    } catch (e) {
      set({ error: String(e), loading: false })
    }
  },

  clearSelection: () => set({ selectedNode: null }),
}))
