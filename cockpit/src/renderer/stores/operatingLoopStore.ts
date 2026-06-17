import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface OperatingLoopState {
  activeLoops: Record<string, unknown>[]
  completedLoops: Record<string, unknown>[]
  snapshot: Record<string, unknown> | null
  selectedLoop: Record<string, unknown> | null
  trace: Record<string, unknown>[]
  loading: boolean

  fetchActiveLoops: () => Promise<void>
  fetchCompletedLoops: (limit?: number) => Promise<void>
  fetchSnapshot: () => Promise<void>
  fetchLoop: (id: string) => Promise<void>
  fetchTrace: (id: string) => Promise<void>
  fetchLineage: (id: string) => Promise<Record<string, unknown>>
  track: (intentText: string, intentId?: string) => Promise<void>
  recordTransition: (loopId: string, toStage: string, subsystem: string, metadata?: Record<string, unknown>) => Promise<void>
}

export const useOperatingLoopStore = create<OperatingLoopState>((set, get) => ({
  activeLoops: [],
  completedLoops: [],
  snapshot: null,
  selectedLoop: null,
  trace: [],
  loading: false,

  fetchActiveLoops: async () => {
    set({ loading: true })
    try {
      const data = await fetchApi<Record<string, unknown>[]>('/operating-loop/active')
      set({ activeLoops: data, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  fetchCompletedLoops: async (limit = 20) => {
    try {
      const data = await fetchApi<Record<string, unknown>[]>(`/operating-loop/completed?limit=${limit}`)
      set({ completedLoops: data })
    } catch {
      set({ completedLoops: [] })
    }
  },

  fetchSnapshot: async () => {
    try {
      const data = await fetchApi<Record<string, unknown>>('/operating-loop/snapshot')
      set({ snapshot: data })
    } catch {
      set({ snapshot: null })
    }
  },

  fetchLoop: async (id: string) => {
    try {
      const data = await fetchApi<Record<string, unknown>>(`/operating-loop/${id}`)
      set({ selectedLoop: data })
    } catch {
      set({ selectedLoop: null })
    }
  },

  fetchTrace: async (id: string) => {
    try {
      const data = await fetchApi<Record<string, unknown>[]>(`/operating-loop/${id}/trace`)
      set({ trace: data })
    } catch {
      set({ trace: [] })
    }
  },

  fetchLineage: async (id: string) => {
    return fetchApi<Record<string, unknown>>(`/operating-loop/${id}/lineage`)
  },

  track: async (intentText: string, intentId = '') => {
    await fetchApi('/operating-loop/track', {
      method: 'POST',
      body: JSON.stringify({ intent_text: intentText, intent_id: intentId }),
    }).catch(() => {})
    get().fetchActiveLoops()
  },

  recordTransition: async (loopId: string, toStage: string, subsystem: string, metadata: Record<string, unknown> = {}) => {
    await fetchApi(`/operating-loop/${loopId}/transition`, {
      method: 'POST',
      body: JSON.stringify({ to_stage: toStage, subsystem, metadata }),
    }).catch(() => {})
    get().fetchActiveLoops()
  },
}))
