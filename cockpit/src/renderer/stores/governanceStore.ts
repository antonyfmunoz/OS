import { create } from 'zustand'
import { fetchApi } from '../api/client'

/* -- Interfaces --------------------------------------------------------- */

interface SubsystemConflict {
  conflict_id: string
  source_authority: string
  target_authority: string
  source_recommendation: string
  target_recommendation: string
  conflict_type: string
  severity: string
  resolution: string
  winning_authority: string
  losing_authority: string
  rationale: string
  detected_at: number
  status: string
}

interface GovernancePolicy {
  policy_id: string
  name: string
  authority: string
  description: string
  active: boolean
}

interface SubsystemHealthEntry {
  subsystem: string
  health: string
  drift_count: number
  score: number
}

interface OrganismDriftWarning {
  drift_type: string
  severity: string
  description: string
  affected_ids: string[]
  recommendation: string
}

interface OrganismOverview {
  organism_health: string
  coherence_score: number
  subsystem_health: SubsystemHealthEntry[]
  governance_health: string
  coordination_health: string
  institutional_memory_health: string
  executive_health: string
  prediction_health: string
  learning_health: string
  work_health: string
  capability_health: string
  drift_warnings: OrganismDriftWarning[]
  total_drift_count: number
  generated_at: number
}

interface CoordinationSnapshot {
  coordination_health: string
  issues: Record<string, unknown>[]
  subsystem_alignment: Record<string, string>
  synchronization_score: number
  bottleneck_count: number
  generated_at: number
}

interface InstitutionalMemorySnapshot {
  memory_health: string
  knowledge_by_state: Record<string, number>
  total_knowledge: number
  canonical_count: number
  validation_rate: number
  drift_warnings: Record<string, unknown>[]
  recent_promotions: Record<string, unknown>[]
  generated_at: number
}

/* -- Store -------------------------------------------------------------- */

interface GovernanceStore {
  overview: OrganismOverview | null
  conflicts: SubsystemConflict[]
  policies: GovernancePolicy[]
  coordination: CoordinationSnapshot | null
  institutionalMemory: InstitutionalMemorySnapshot | null
  drift: OrganismDriftWarning[]
  loading: boolean
  error: string | null
  fetchOverview: () => Promise<void>
  fetchConflicts: () => Promise<void>
  fetchPolicies: () => Promise<void>
  fetchCoordination: () => Promise<void>
  fetchInstitutionalMemory: () => Promise<void>
  fetchDrift: () => Promise<void>
  fetchAll: () => Promise<void>
}

export const useGovernanceStore = create<GovernanceStore>((set) => ({
  overview: null,
  conflicts: [],
  policies: [],
  coordination: null,
  institutionalMemory: null,
  drift: [],
  loading: false,
  error: null,

  fetchOverview: async () => {
    try {
      set({ loading: true, error: null })
      const data = await fetchApi<OrganismOverview>('/governance/overview')
      set({ overview: data, loading: false })
    } catch (e) {
      set({ error: String(e), loading: false })
    }
  },

  fetchConflicts: async () => {
    try {
      const data = await fetchApi<{ conflicts: SubsystemConflict[] }>('/governance/conflicts')
      set({ conflicts: data.conflicts || [] })
    } catch (e) {
      set({ error: String(e) })
    }
  },

  fetchPolicies: async () => {
    try {
      const data = await fetchApi<{ policies: GovernancePolicy[] }>('/governance/policies')
      set({ policies: data.policies || [] })
    } catch (e) {
      set({ error: String(e) })
    }
  },

  fetchCoordination: async () => {
    try {
      const data = await fetchApi<CoordinationSnapshot>('/governance/coordination')
      set({ coordination: data })
    } catch (e) {
      set({ error: String(e) })
    }
  },

  fetchInstitutionalMemory: async () => {
    try {
      const data = await fetchApi<InstitutionalMemorySnapshot>('/governance/institutional-memory')
      set({ institutionalMemory: data })
    } catch (e) {
      set({ error: String(e) })
    }
  },

  fetchDrift: async () => {
    try {
      const data = await fetchApi<{ drift_warnings: OrganismDriftWarning[] }>('/governance/drift')
      set({ drift: data.drift_warnings || [] })
    } catch (e) {
      set({ error: String(e) })
    }
  },

  fetchAll: async () => {
    set({ loading: true, error: null })
    try {
      const [overview, conflicts, policies, coordination, memory, drift] = await Promise.all([
        fetchApi<OrganismOverview>('/governance/overview'),
        fetchApi<{ conflicts: SubsystemConflict[] }>('/governance/conflicts'),
        fetchApi<{ policies: GovernancePolicy[] }>('/governance/policies'),
        fetchApi<CoordinationSnapshot>('/governance/coordination'),
        fetchApi<InstitutionalMemorySnapshot>('/governance/institutional-memory'),
        fetchApi<{ drift_warnings: OrganismDriftWarning[] }>('/governance/drift'),
      ])
      set({
        overview,
        conflicts: conflicts.conflicts || [],
        policies: policies.policies || [],
        coordination,
        institutionalMemory: memory,
        drift: drift.drift_warnings || [],
        loading: false,
      })
    } catch (e) {
      set({ error: String(e), loading: false })
    }
  },
}))
