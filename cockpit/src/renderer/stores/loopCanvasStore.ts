import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { clampZoom } from '../utils/canvasCoords'
import { fetchApi } from '../api/client'

export interface PersistentLoopStatus {
  name: string
  domain: string
  state: 'stopped' | 'running' | 'paused' | 'error'
  cycle_count: number
  interval_seconds: number
  error_count: number
  started_at: string | null
  stages: string[]
  description: string
  last_cycle: {
    loop_name: string
    cycle_num: number
    started_at: string
    finished_at: string
    actions_taken: number
    errors: number
    details: Array<Record<string, unknown>>
  } | null
}

export interface LoopDefinition {
  name: string
  domain: string
  interval_seconds: number
  stages: string[]
  description: string
}

export interface LoopCanvasState {
  panX: number
  panY: number
  zoom: number

  activeLoopId: string | null
  activeLoopType: 'persistent' | 'lifecycle' | null

  persistentLoops: Record<string, PersistentLoopStatus>
  availableStages: Record<string, string>
  loading: boolean
  lastDryRun: Record<string, unknown> | null

  setPan: (x: number, y: number) => void
  setZoom: (z: number) => void

  openLoop: (id: string, type: 'persistent' | 'lifecycle') => void
  closeLoop: () => void

  fetchLoops: () => Promise<void>
  fetchStages: () => Promise<void>
  startLoop: (name: string) => Promise<void>
  stopLoop: (name: string) => Promise<void>
  runOnce: (name: string) => Promise<void>
  dryRun: (name: string) => Promise<void>
  createLoop: (def: LoopDefinition) => Promise<void>
  deleteLoop: (name: string) => Promise<void>
  updateLoop: (name: string, updates: Record<string, unknown>) => Promise<void>
}

export const useLoopCanvasStore = create<LoopCanvasState>()(
  persist(
    (set, get) => ({
      panX: 0,
      panY: 0,
      zoom: 1,

      activeLoopId: null,
      activeLoopType: null,

      persistentLoops: {},
      availableStages: {},
      loading: false,
      lastDryRun: null,

      setPan: (x, y) => set({ panX: x, panY: y }),
      setZoom: (z) => set({ zoom: clampZoom(z) }),

      openLoop: (id, type) => set({ activeLoopId: id, activeLoopType: type }),
      closeLoop: () => set({ activeLoopId: null, activeLoopType: null }),

      fetchLoops: async () => {
        set({ loading: true })
        try {
          const data = await fetchApi<Record<string, PersistentLoopStatus>>('/loops')
          set({ persistentLoops: data })
        } finally {
          set({ loading: false })
        }
      },

      fetchStages: async () => {
        const data = await fetchApi<Record<string, string>>('/loops/stages')
        set({ availableStages: data })
      },

      startLoop: async (name) => {
        await fetchApi(`/loops/${name}/start`, { method: 'POST' })
        await get().fetchLoops()
      },

      stopLoop: async (name) => {
        await fetchApi(`/loops/${name}/stop`, { method: 'POST' })
        await get().fetchLoops()
      },

      runOnce: async (name) => {
        await fetchApi(`/loops/${name}/run-once`, { method: 'POST' })
        await get().fetchLoops()
      },

      dryRun: async (name) => {
        const data = await fetchApi<Record<string, unknown>>(`/loops/${name}/dry-run`, {
          method: 'POST',
        })
        set({ lastDryRun: data })
      },

      createLoop: async (def) => {
        await fetchApi('/loops/create', { method: 'POST', body: JSON.stringify(def) })
        await get().fetchLoops()
      },

      deleteLoop: async (name) => {
        await fetchApi(`/loops/${name}`, { method: 'DELETE' })
        await get().fetchLoops()
      },

      updateLoop: async (name, updates) => {
        await fetchApi(`/loops/${name}`, { method: 'PATCH', body: JSON.stringify(updates) })
        await get().fetchLoops()
      },
    }),
    {
      name: 'cockpit:loop-canvas',
      partialize: (s) => ({
        panX: s.panX,
        panY: s.panY,
        zoom: s.zoom,
        activeLoopId: s.activeLoopId,
        activeLoopType: s.activeLoopType,
      }),
    },
  ),
)
