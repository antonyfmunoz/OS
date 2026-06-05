import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface CanonicalPattern {
  id: string
  name: string
  domain: string
  description: string
  evidence_count: number
  confidence: number
  effective_confidence: number
  promoted_at: string
  last_confirmed: string
  tags: string[]
}

interface PatternDetail extends CanonicalPattern {
  metadata: Record<string, unknown>
  relationships: PatternRelationship[]
}

interface PatternRelationship {
  name: string
  type: string
  strength: number
}

interface CanonicalStats {
  pattern_count: number
  relationship_count: number
  domains: string[]
  avg_confidence: number
  avg_evidence_count: number
}

interface InstanceStats {
  observation_count: number
  domains: string[]
  avg_effective_confidence: number
  oldest: string | null
  newest: string | null
}

interface RealityModelStatus {
  canonical: CanonicalStats
  instance: InstanceStats
  layers: string[]
}

interface InstanceObservation {
  id: string
  content: string
  domain: string
  confidence: number
  effective_confidence: number
  observed_at: string
  tags: string[]
}

interface DomainCount {
  domain: string
  pattern_count?: number
  observation_count?: number
}

interface SearchResult {
  id: string
  name?: string
  domain: string
  description?: string
  content?: string
  effective_confidence: number
  observed_at?: string
}

interface SimulationResult {
  simulation_id: string
  hypothesis: string
  step_count: number
  overall_confidence: number
  duration_ms: number
  safe_to_execute: boolean
  predicted_outcome: string
  risk_factors: string[]
  ai_risk_analysis: Record<string, unknown>
  new_observations: number
  matched_patterns: string[]
}

type Tab = 'world' | 'graph' | 'contradictions' | 'compose' | 'outcomes' | 'memory'

interface WorldModelState {
  tab: Tab
  status: RealityModelStatus | null
  patterns: CanonicalPattern[]
  selectedPattern: PatternDetail | null
  relationships: PatternRelationship[]
  recentObservations: InstanceObservation[]
  instanceStats: InstanceStats | null
  canonicalDomains: DomainCount[]
  instanceDomains: DomainCount[]
  searchResults: SearchResult[]
  simulation: SimulationResult | null
  composing: boolean
  loading: boolean
  error: string | null

  setTab: (tab: Tab) => void
  fetchStatus: () => Promise<void>
  fetchPatterns: (domain?: string) => Promise<void>
  fetchPatternDetail: (name: string) => Promise<void>
  fetchRelationships: (name: string) => Promise<void>
  fetchRecentObservations: () => Promise<void>
  fetchInstanceStats: () => Promise<void>
  fetchDomains: () => Promise<void>
  searchCanonical: (q: string) => Promise<void>
  simulate: (hypothesis: string) => Promise<void>
  fetchAll: () => Promise<void>
}

export const useWorldModelStore = create<WorldModelState>((set, get) => ({
  tab: 'world',
  status: null,
  patterns: [],
  selectedPattern: null,
  relationships: [],
  recentObservations: [],
  instanceStats: null,
  canonicalDomains: [],
  instanceDomains: [],
  searchResults: [],
  simulation: null,
  composing: false,
  loading: false,
  error: null,

  setTab: (tab) => set({ tab }),

  fetchStatus: async () => {
    try {
      const data = await fetchApi<RealityModelStatus>('/reality-model/status')
      set({ status: data })
    } catch {
      set({ error: 'Failed to fetch reality model status' })
    }
  },

  fetchPatterns: async (domain?: string) => {
    try {
      const path = domain
        ? `/reality-model/canonical/patterns?domain=${encodeURIComponent(domain)}`
        : '/reality-model/canonical/patterns'
      const data = await fetchApi<CanonicalPattern[]>(path)
      set({ patterns: data })
    } catch {
      set({ error: 'Failed to fetch canonical patterns' })
    }
  },

  fetchPatternDetail: async (name: string) => {
    try {
      const data = await fetchApi<PatternDetail>(
        `/reality-model/canonical/pattern/${encodeURIComponent(name)}`
      )
      set({ selectedPattern: data })
    } catch {
      set({ error: 'Failed to fetch pattern detail' })
    }
  },

  fetchRelationships: async (name: string) => {
    try {
      const data = await fetchApi<PatternRelationship[]>(
        `/reality-model/canonical/relationships/${encodeURIComponent(name)}`
      )
      set({ relationships: data })
    } catch {
      set({ error: 'Failed to fetch relationships' })
    }
  },

  fetchRecentObservations: async () => {
    try {
      const data = await fetchApi<InstanceObservation[]>('/reality-model/instance/recent')
      set({ recentObservations: data })
    } catch {
      set({ error: 'Failed to fetch recent observations' })
    }
  },

  fetchInstanceStats: async () => {
    try {
      const data = await fetchApi<InstanceStats>('/reality-model/instance/stats')
      set({ instanceStats: data })
    } catch {
      set({ error: 'Failed to fetch instance stats' })
    }
  },

  fetchDomains: async () => {
    try {
      const [canonical, instance] = await Promise.all([
        fetchApi<DomainCount[]>('/reality-model/canonical/domains'),
        fetchApi<DomainCount[]>('/reality-model/instance/domains'),
      ])
      set({ canonicalDomains: canonical, instanceDomains: instance })
    } catch {
      set({ error: 'Failed to fetch domains' })
    }
  },

  searchCanonical: async (q: string) => {
    try {
      const data = await fetchApi<SearchResult[]>(
        `/reality-model/canonical/search?q=${encodeURIComponent(q)}`
      )
      set({ searchResults: data })
    } catch {
      set({ error: 'Failed to search canonical patterns' })
    }
  },

  simulate: async (hypothesis: string) => {
    set({ composing: true, error: null })
    try {
      const resp = await fetchApi<{ success: boolean; result: SimulationResult }>(
        '/reality-model/simulate',
        { method: 'POST', body: JSON.stringify({ hypothesis }) }
      )
      set({ simulation: resp.result, composing: false, tab: 'compose' })
    } catch {
      set({ composing: false, error: 'Simulation failed' })
    }
  },

  fetchAll: async () => {
    set({ loading: true })
    const s = get()
    await Promise.all([
      s.fetchStatus(),
      s.fetchPatterns(),
      s.fetchRecentObservations(),
      s.fetchInstanceStats(),
      s.fetchDomains(),
    ])
    set({ loading: false })
  },
}))
