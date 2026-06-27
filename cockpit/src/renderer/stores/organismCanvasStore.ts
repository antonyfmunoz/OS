import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { fetchApi } from '../api/client'
import { clampZoom } from '../utils/canvasCoords'

export interface TopologyNode {
  id?: string
  node_id?: string
  role?: string
  type: string
  [key: string]: unknown
}

export interface TopologyEdge {
  source: string
  target: string
  type?: string
  [key: string]: unknown
}

interface OrganismCanvasState {
  panX: number
  panY: number
  zoom: number
  activeNodeId: string | null
  topology: { nodes: TopologyNode[]; edges: TopologyEdge[] } | null
  health: Record<string, unknown> | null
  nodeDetail: Record<string, unknown> | null
  loading: boolean

  setPan: (x: number, y: number) => void
  setZoom: (z: number) => void
  fetchTopology: () => Promise<void>
  fetchHealth: () => Promise<void>
  fetchNodeDetail: (id: string) => Promise<void>
  openNode: (id: string) => void
  closeNode: () => void
}

export const useOrganismCanvasStore = create<OrganismCanvasState>()(
  persist(
    (set) => ({
      panX: 0,
      panY: 0,
      zoom: 1,
      activeNodeId: null,
      topology: null,
      health: null,
      nodeDetail: null,
      loading: false,

      setPan: (x, y) => set({ panX: x, panY: y }),

      setZoom: (z) => set({ zoom: clampZoom(z) }),

      fetchTopology: async () => {
        set({ loading: true })
        try {
          const data = await fetchApi<{ nodes?: TopologyNode[]; edges?: TopologyEdge[] }>(
            '/organism-map/topology',
          )
          set({
            topology: {
              nodes: data.nodes ?? [],
              edges: data.edges ?? [],
            },
          })
        } finally {
          set({ loading: false })
        }
      },

      fetchHealth: async () => {
        const data = await fetchApi<Record<string, unknown>>('/organism-map/health')
        set({ health: data })
      },

      fetchNodeDetail: async (id) => {
        const data = await fetchApi<Record<string, unknown>>(
          `/organism-map/node/${encodeURIComponent(id)}`,
        )
        set({ nodeDetail: data })
      },

      openNode: (id) => set({ activeNodeId: id }),

      closeNode: () => set({ activeNodeId: null, nodeDetail: null }),
    }),
    {
      name: 'cockpit:organism-canvas',
      partialize: (state) => ({
        panX: state.panX,
        panY: state.panY,
        zoom: state.zoom,
        activeNodeId: state.activeNodeId,
      }),
    },
  ),
)
