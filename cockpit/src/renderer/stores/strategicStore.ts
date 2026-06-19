import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface StrategicState {
  context: Record<string, unknown> | null
  priorities: Record<string, unknown>[]
  risks: Record<string, unknown>[]
  recommendations: Record<string, unknown>[]
  driftWarnings: Record<string, unknown>[]
  brief: Record<string, unknown> | null
  loading: boolean
  fetchContext: () => Promise<void>
  fetchPriorities: () => Promise<void>
  fetchRisks: () => Promise<void>
  fetchRecommendations: () => Promise<void>
  fetchDrift: () => Promise<void>
  fetchBrief: () => Promise<void>
}

export const useStrategicStore = create<StrategicState>((set) => ({
  context: null,
  priorities: [],
  risks: [],
  recommendations: [],
  driftWarnings: [],
  brief: null,
  loading: false,

  fetchContext: async () => {
    set({ loading: true })
    try {
      const data = await fetchApi<Record<string, unknown>>('/strategic/context')
      set({ context: data, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  fetchPriorities: async () => {
    try {
      const data = await fetchApi<{ priorities: Record<string, unknown>[] }>('/strategic/priorities/top?limit=10')
      set({ priorities: data.priorities ?? [] })
    } catch {
      set({ priorities: [] })
    }
  },

  fetchRisks: async () => {
    try {
      const data = await fetchApi<{ risks: Record<string, unknown>[] }>('/strategic/risks')
      set({ risks: data.risks ?? [] })
    } catch {
      set({ risks: [] })
    }
  },

  fetchRecommendations: async () => {
    try {
      const data = await fetchApi<{ recommendations: Record<string, unknown>[] }>('/strategic/recommendations')
      set({ recommendations: data.recommendations ?? [] })
    } catch {
      set({ recommendations: [] })
    }
  },

  fetchDrift: async () => {
    try {
      const data = await fetchApi<{ drift_warnings: Record<string, unknown>[] }>('/strategic/drift')
      set({ driftWarnings: data.drift_warnings ?? [] })
    } catch {
      set({ driftWarnings: [] })
    }
  },

  fetchBrief: async () => {
    set({ loading: true })
    try {
      const data = await fetchApi<Record<string, unknown>>('/strategic/brief')
      set({ brief: data, loading: false })
    } catch {
      set({ loading: false })
    }
  },
}))
