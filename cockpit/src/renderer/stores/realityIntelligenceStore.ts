import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface RealityEvidence {
  source_type: string
  source_id: string
  content: string
  confidence: number
  domain: string
  timestamp: string
  metadata: Record<string, unknown>
}

interface RealityQueryResult {
  query_id: string
  query_type: string
  evidence: RealityEvidence[]
  confidence: number
  reasoning: string
  generated_at: number
  sources_queried: string[]
}

type QueryType = 'why' | 'what_changed' | 'evidence' | 'contradictions' | 'lineage' | 'domain_summary' | 'priorities'

interface RealityIntelligenceState {
  activeQueryType: QueryType
  result: RealityQueryResult | null
  loading: boolean
  error: string | null

  setQueryType: (type: QueryType) => void
  queryWhy: (entity: string) => Promise<void>
  queryWhatChanged: (since: number) => Promise<void>
  queryEvidence: (entity: string) => Promise<void>
  queryContradictions: (domain?: string) => Promise<void>
  queryLineage: (entity: string) => Promise<void>
  queryDomainSummary: (domain: string) => Promise<void>
  queryPriorities: () => Promise<void>
}

export const useRealityIntelligenceStore = create<RealityIntelligenceState>((set) => ({
  activeQueryType: 'why',
  result: null,
  loading: false,
  error: null,

  setQueryType: (type) => set({ activeQueryType: type }),

  queryWhy: async (entity) => {
    set({ loading: true, error: null })
    try {
      const data = await fetchApi<RealityQueryResult>(
        `/reality-intelligence/why/${encodeURIComponent(entity)}`
      )
      set({ result: data, loading: false })
    } catch {
      set({ error: 'Failed to query why', loading: false })
    }
  },

  queryWhatChanged: async (since) => {
    set({ loading: true, error: null })
    try {
      const data = await fetchApi<RealityQueryResult>(
        `/reality-intelligence/what-changed?since=${since}`
      )
      set({ result: data, loading: false })
    } catch {
      set({ error: 'Failed to query changes', loading: false })
    }
  },

  queryEvidence: async (entity) => {
    set({ loading: true, error: null })
    try {
      const data = await fetchApi<RealityQueryResult>(
        `/reality-intelligence/evidence/${encodeURIComponent(entity)}`
      )
      set({ result: data, loading: false })
    } catch {
      set({ error: 'Failed to query evidence', loading: false })
    }
  },

  queryContradictions: async (domain) => {
    set({ loading: true, error: null })
    try {
      const params = domain ? `?domain=${encodeURIComponent(domain)}` : ''
      const data = await fetchApi<RealityQueryResult>(
        `/reality-intelligence/contradictions${params}`
      )
      set({ result: data, loading: false })
    } catch {
      set({ error: 'Failed to query contradictions', loading: false })
    }
  },

  queryLineage: async (entity) => {
    set({ loading: true, error: null })
    try {
      const data = await fetchApi<RealityQueryResult>(
        `/reality-intelligence/lineage/${encodeURIComponent(entity)}`
      )
      set({ result: data, loading: false })
    } catch {
      set({ error: 'Failed to trace lineage', loading: false })
    }
  },

  queryDomainSummary: async (domain) => {
    set({ loading: true, error: null })
    try {
      const data = await fetchApi<RealityQueryResult>(
        `/reality-intelligence/domain/${encodeURIComponent(domain)}`
      )
      set({ result: data, loading: false })
    } catch {
      set({ error: 'Failed to summarize domain', loading: false })
    }
  },

  queryPriorities: async () => {
    set({ loading: true, error: null })
    try {
      const data = await fetchApi<RealityQueryResult>(
        '/reality-intelligence/priorities'
      )
      set({ result: data, loading: false })
    } catch {
      set({ error: 'Failed to query priorities', loading: false })
    }
  },
}))
