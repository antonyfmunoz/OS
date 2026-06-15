import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface RealityObservation {
  id: string
  content: string
  domain: string
  confidence: number
  effective_confidence: number
  source_system: string
  observed_at: string
  tags: string[]
  evidence: Record<string, unknown>
}

interface RealityTimelineState {
  observations: RealityObservation[]
  domains: string[]
  sources: string[]
  loading: boolean
  error: string | null
  filterDomain: string
  filterSource: string

  fetchTimeline: (limit?: number) => Promise<void>
  setFilterDomain: (domain: string) => void
  setFilterSource: (source: string) => void
}

export const useRealityTimelineStore = create<RealityTimelineState>((set, get) => ({
  observations: [],
  domains: [],
  sources: [],
  loading: false,
  error: null,
  filterDomain: '',
  filterSource: '',

  fetchTimeline: async (limit = 50) => {
    set({ loading: true, error: null })
    try {
      const { filterDomain, filterSource } = get()
      const params = new URLSearchParams()
      params.set('limit', String(limit))
      if (filterDomain) params.set('domain', filterDomain)
      if (filterSource) params.set('source', filterSource)

      const data = await fetchApi<{
        observations: RealityObservation[]
        filters: { domains: string[]; sources: string[] }
        total: number
      }>(`/reality-model/timeline?${params}`)
      set({
        observations: data.observations,
        domains: data.filters.domains,
        sources: data.filters.sources,
        loading: false,
      })
    } catch {
      set({ error: 'Failed to fetch reality timeline', loading: false })
    }
  },

  setFilterDomain: (domain) => set({ filterDomain: domain }),
  setFilterSource: (source) => set({ filterSource: source }),
}))
