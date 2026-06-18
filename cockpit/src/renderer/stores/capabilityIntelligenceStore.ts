import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface CapabilityIntelligenceState {
  portfolio: Record<string, unknown> | null
  gaps: Record<string, unknown>[]
  criticalGaps: Record<string, unknown>[]
  graph: { edges: Record<string, unknown>[]; summary: Record<string, unknown> }
  compounding: Record<string, unknown> | null
  bottlenecks: Record<string, unknown>[]
  loading: boolean
  fetchPortfolio: () => Promise<void>
  fetchGaps: () => Promise<void>
  fetchCriticalGaps: () => Promise<void>
  fetchGraph: () => Promise<void>
  fetchCompounding: () => Promise<void>
  fetchBottlenecks: () => Promise<void>
  fetchCompositionTree: (id: string) => Promise<Record<string, unknown> | null>
}

export const useCapabilityIntelligenceStore = create<CapabilityIntelligenceState>((set) => ({
  portfolio: null,
  gaps: [],
  criticalGaps: [],
  graph: { edges: [], summary: {} },
  compounding: null,
  bottlenecks: [],
  loading: false,

  fetchPortfolio: async () => {
    set({ loading: true })
    try {
      const data = await fetchApi<{ portfolio: Record<string, unknown> }>('/capability-intelligence/portfolio')
      set({ portfolio: data.portfolio ?? null, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  fetchGaps: async () => {
    try {
      const data = await fetchApi<{ gaps: Record<string, unknown>[] }>('/capability-intelligence/gaps')
      set({ gaps: data.gaps ?? [] })
    } catch { /* silent */ }
  },

  fetchCriticalGaps: async () => {
    try {
      const data = await fetchApi<{ gaps: Record<string, unknown>[] }>('/capability-intelligence/gaps/critical')
      set({ criticalGaps: data.gaps ?? [] })
    } catch { /* silent */ }
  },

  fetchGraph: async () => {
    try {
      const data = await fetchApi<{ edges: Record<string, unknown>[]; summary: Record<string, unknown> }>('/capability-intelligence/graph')
      set({ graph: { edges: data.edges ?? [], summary: data.summary ?? {} } })
    } catch { /* silent */ }
  },

  fetchCompounding: async () => {
    try {
      const data = await fetchApi<Record<string, unknown>>('/capability-intelligence/compounding')
      set({ compounding: data ?? null })
    } catch { /* silent */ }
  },

  fetchBottlenecks: async () => {
    try {
      const data = await fetchApi<{ bottlenecks: Record<string, unknown>[] }>('/capability-intelligence/bottlenecks')
      set({ bottlenecks: data.bottlenecks ?? [] })
    } catch { /* silent */ }
  },

  fetchCompositionTree: async (id: string) => {
    try {
      const data = await fetchApi<{ tree: Record<string, unknown> }>(`/capability-intelligence/graph/${id}/tree`)
      return data.tree ?? null
    } catch {
      return null
    }
  },
}))
