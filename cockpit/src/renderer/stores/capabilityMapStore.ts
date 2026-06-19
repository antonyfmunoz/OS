import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface CapabilityMapState {
  snapshot: Record<string, unknown> | null
  mvpGaps: Record<string, unknown>[]
  duplications: Record<string, unknown>[]
  loading: boolean
  fetchSnapshot: () => Promise<void>
  fetchMvpGaps: () => Promise<void>
  fetchDuplications: () => Promise<void>
}

export const useCapabilityMapStore = create<CapabilityMapState>((set) => ({
  snapshot: null,
  mvpGaps: [],
  duplications: [],
  loading: false,

  fetchSnapshot: async () => {
    set({ loading: true })
    try {
      const data = await fetchApi<Record<string, unknown>>('/capability-map/snapshot')
      set({ snapshot: data, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  fetchMvpGaps: async () => {
    try {
      const data = await fetchApi<Record<string, unknown>[]>('/capability-map/mvp-gaps')
      set({ mvpGaps: data })
    } catch {
      set({ mvpGaps: [] })
    }
  },

  fetchDuplications: async () => {
    try {
      const data = await fetchApi<Record<string, unknown>[]>('/capability-map/duplications')
      set({ duplications: data })
    } catch {
      set({ duplications: [] })
    }
  },
}))
