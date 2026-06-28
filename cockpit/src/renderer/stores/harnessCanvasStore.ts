import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { fetchApi } from '../api/client'
import { clampZoom } from '../utils/canvasCoords'

export interface RuntimeNode {
  runtime_id: string
  runtime_class: 'AI_CLI' | 'AI_API' | 'LOCAL_MODEL' | 'CONTAINER' | 'PROCESS' | 'REMOTE_NODE'
  capabilities: string[]
  available: boolean
  cost: {
    is_subscription?: boolean
    cost_per_1k_input?: number
    cost_per_1k_output?: number
  }
  metadata: Record<string, unknown>
}

interface RuntimesResponse {
  runtimes: RuntimeNode[]
  count: number
  available: number
}

export interface HarnessCanvasState {
  panX: number
  panY: number
  zoom: number

  activeHarnessId: string | null
  runtimes: RuntimeNode[]
  loading: boolean

  setPan: (x: number, y: number) => void
  setZoom: (z: number) => void
  openHarness: (id: string) => void
  closeHarness: () => void
  fetchRuntimes: () => Promise<void>
}

export const useHarnessCanvasStore = create<HarnessCanvasState>()(
  persist(
    (set) => ({
      panX: 0,
      panY: 0,
      zoom: 1,

      activeHarnessId: null,
      runtimes: [],
      loading: false,

      setPan: (x, y) => set({ panX: x, panY: y }),

      setZoom: (z) => set({ zoom: clampZoom(z) }),

      openHarness: (id) => set({ activeHarnessId: id }),

      closeHarness: () => set({ activeHarnessId: null }),

      fetchRuntimes: async () => {
        set({ loading: true })
        try {
          const data = await fetchApi<RuntimesResponse>('/organism/runtimes')
          set({ runtimes: data.runtimes, loading: false })
        } catch {
          set({ loading: false })
        }
      },
    }),
    {
      name: 'cockpit:harness-canvas',
      partialize: (s) => ({
        panX: s.panX,
        panY: s.panY,
        zoom: s.zoom,
        activeHarnessId: s.activeHarnessId,
      }),
    },
  ),
)
