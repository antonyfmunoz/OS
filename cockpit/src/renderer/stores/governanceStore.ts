import { create } from 'zustand'

/* ── Interfaces ─────────────────────────────────────────────────── */

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

/* ── Store ───────────────────────────────────────────────────────── */

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

const API_BASE = '/api'

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
      const res = await fetch(`${API_BASE}/governance/overview`)
      const data = await res.json()
      set({ overview: data, loading: false })
    } catch (e) {
      set({ error: String(e), loading: false })
    }
  },

  fetchConflicts: async () => {
    try {
      const res = await fetch(`${API_BASE}/governance/conflicts`)
      const data = await res.json()
      set({ conflicts: data.conflicts || [] })
    } catch (e) {
      set({ error: String(e) })
    }
  },

  fetchPolicies: async () => {
    try {
      const res = await fetch(`${API_BASE}/governance/policies`)
      const data = await res.json()
      set({ policies: data.policies || [] })
    } catch (e) {
      set({ error: String(e) })
    }
  },

  fetchCoordination: async () => {
    try {
      const res = await fetch(`${API_BASE}/governance/coordination`)
      const data = await res.json()
      set({ coordination: data })
    } catch (e) {
      set({ error: String(e) })
    }
  },

  fetchInstitutionalMemory: async () => {
    try {
      const res = await fetch(`${API_BASE}/governance/institutional-memory`)
      const data = await res.json()
      set({ institutionalMemory: data })
    } catch (e) {
      set({ error: String(e) })
    }
  },

  fetchDrift: async () => {
    try {
      const res = await fetch(`${API_BASE}/governance/drift`)
      const data = await res.json()
      set({ drift: data.drift_warnings || [] })
    } catch (e) {
      set({ error: String(e) })
    }
  },

  fetchAll: async () => {
    set({ loading: true, error: null })
    try {
      const [r1, r2, r3, r4, r5, r6] = await Promise.all([
        fetch(`${API_BASE}/governance/overview`),
        fetch(`${API_BASE}/governance/conflicts`),
        fetch(`${API_BASE}/governance/policies`),
        fetch(`${API_BASE}/governance/coordination`),
        fetch(`${API_BASE}/governance/institutional-memory`),
        fetch(`${API_BASE}/governance/drift`),
      ])
      const [d1, d2, d3, d4, d5, d6] = await Promise.all([
        r1.json(), r2.json(), r3.json(), r4.json(), r5.json(), r6.json(),
      ])
      set({
        overview: d1,
        conflicts: d2.conflicts || [],
        policies: d3.policies || [],
        coordination: d4,
        institutionalMemory: d5,
        drift: d6.drift_warnings || [],
        loading: false,
      })
    } catch (e) {
      set({ error: String(e), loading: false })
    }
  },
}))
