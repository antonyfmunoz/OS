import { create } from 'zustand'

interface AllocationRecommendation {
  recommendation_id: string
  resource_type: string
  target_id: string
  target_name: string
  target_type: string
  priority: string
  leverage_score: number
  allocation_confidence: number
  rationale: string
  competing_targets: string[]
  source_signals: string[]
  generated_at: number
}

interface ResourceBudget {
  resource_type: string
  total_capacity: number
  allocated: number
  available: number
  overcommitted: boolean
}

interface DriftWarning {
  drift_type: string
  severity: string
  description: string
  affected_ids: string[]
  recommendation: string
}

interface TradeoffAnalysis {
  analysis_id: string
  chosen: Record<string, unknown>
  displaced: Record<string, unknown>[]
  leverage_delta: number
  impact_delta: number
  risk_delta: number
  severity: string
  recommendation: string
  rationale: string
  source_signals: string[]
  generated_at: number
}

interface ExecutiveOverview {
  executive_health: string
  allocation_health: string
  tradeoff_severity: string
  work_health: string
  prediction_health: string
  learning_health: string
  decision_health: string
  capability_health: string
  goal_alignment_health: string
  drift_warnings: DriftWarning[]
  top_recommendations: AllocationRecommendation[]
  resource_summary: Record<string, unknown>
  focus_score: number
  overcommitment_index: number
  generated_at: number
}

interface ExecutiveStore {
  overview: ExecutiveOverview | null
  allocations: AllocationRecommendation[]
  budgets: ResourceBudget[]
  drift: DriftWarning[]
  contention: Record<string, string[]>
  loading: boolean
  error: string | null
  fetchOverview: () => Promise<void>
  fetchAllocations: () => Promise<void>
  fetchBudgets: () => Promise<void>
  fetchDrift: () => Promise<void>
  fetchContention: () => Promise<void>
  fetchAll: () => Promise<void>
}

const API_BASE = '/api'

export const useExecutiveStore = create<ExecutiveStore>((set) => ({
  overview: null,
  allocations: [],
  budgets: [],
  drift: [],
  contention: {},
  loading: false,
  error: null,

  fetchOverview: async () => {
    try {
      set({ loading: true, error: null })
      const res = await fetch(`${API_BASE}/executive/overview`)
      const data = await res.json()
      set({ overview: data, loading: false })
    } catch (e) {
      set({ error: String(e), loading: false })
    }
  },

  fetchAllocations: async () => {
    try {
      const res = await fetch(`${API_BASE}/executive/allocations`)
      const data = await res.json()
      set({ allocations: data.recommendations || [] })
    } catch (e) {
      set({ error: String(e) })
    }
  },

  fetchBudgets: async () => {
    try {
      const res = await fetch(`${API_BASE}/executive/budgets`)
      const data = await res.json()
      set({ budgets: data.budgets || [] })
    } catch (e) {
      set({ error: String(e) })
    }
  },

  fetchDrift: async () => {
    try {
      const res = await fetch(`${API_BASE}/executive/drift`)
      const data = await res.json()
      set({ drift: data.drift_warnings || [] })
    } catch (e) {
      set({ error: String(e) })
    }
  },

  fetchContention: async () => {
    try {
      const res = await fetch(`${API_BASE}/executive/contention`)
      const data = await res.json()
      set({ contention: data.contention || {} })
    } catch (e) {
      set({ error: String(e) })
    }
  },

  fetchAll: async () => {
    set({ loading: true, error: null })
    try {
      const [overviewRes, allocRes, budgetRes, driftRes, contentionRes] = await Promise.all([
        fetch(`${API_BASE}/executive/overview`),
        fetch(`${API_BASE}/executive/allocations`),
        fetch(`${API_BASE}/executive/budgets`),
        fetch(`${API_BASE}/executive/drift`),
        fetch(`${API_BASE}/executive/contention`),
      ])
      const [overview, alloc, budget, drift, contention] = await Promise.all([
        overviewRes.json(),
        allocRes.json(),
        budgetRes.json(),
        driftRes.json(),
        contentionRes.json(),
      ])
      set({
        overview,
        allocations: alloc.recommendations || [],
        budgets: budget.budgets || [],
        drift: drift.drift_warnings || [],
        contention: contention.contention || {},
        loading: false,
      })
    } catch (e) {
      set({ error: String(e), loading: false })
    }
  },
}))
