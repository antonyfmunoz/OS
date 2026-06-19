import { create } from 'zustand'

interface ForecastData {
  entity_id: string
  entity_type: string
  current_state: Record<string, unknown>
  projected_state: Record<string, unknown>
  confidence: number
  confidence_reason: string
  status: string
  source_signals: string[]
  contributing_factors: string[]
  forecast_horizon_days: number
  generated_at: number
}

interface ScenarioData {
  scenario_id: string
  scenario_type: string
  title: string
  assumptions: string[]
  projected_outcomes: Record<string, unknown>
  probability: number
  risks: string[]
  opportunities: string[]
  affected_goals: string[]
  source_signals: string[]
  contributing_factors: string[]
  generated_at: number
}

interface DriftWarning {
  drift_type: string
  severity: string
  description: string
  affected_ids: string[]
  recommendation: string
}

interface PredictionOverview {
  forecast_count: number
  scenario_count: number
  prediction_health: string
  average_confidence: number
  uncertainty_index: number
  drift_warnings: DriftWarning[]
  top_forecasts: ForecastData[]
  critical_risks: Array<{ risk: string; source: string }>
  generated_at: number
}

interface PredictionState {
  overview: PredictionOverview | null
  forecasts: ForecastData[]
  scenarios: ScenarioData[]
  drift: DriftWarning[]
  health: string
  uncertainty: number
  loading: boolean
  error: string | null
  fetchOverview: () => Promise<void>
  fetchForecasts: () => Promise<void>
  fetchScenarios: () => Promise<void>
  fetchDrift: () => Promise<void>
  fetchAll: () => Promise<void>
}

const API_BASE = '/api'

export const usePredictionStore = create<PredictionState>((set) => ({
  overview: null,
  forecasts: [],
  scenarios: [],
  drift: [],
  health: 'unknown',
  uncertainty: 1.0,
  loading: false,
  error: null,

  fetchOverview: async () => {
    try {
      const res = await fetch(`${API_BASE}/prediction/overview`)
      const data = await res.json()
      set({
        overview: data,
        health: data.prediction_health || 'unknown',
        uncertainty: data.uncertainty_index ?? 1.0,
      })
    } catch (e) {
      set({ error: String(e) })
    }
  },

  fetchForecasts: async () => {
    try {
      const res = await fetch(`${API_BASE}/prediction/forecasts`)
      const data = await res.json()
      set({ forecasts: data.forecasts || [] })
    } catch (e) {
      set({ error: String(e) })
    }
  },

  fetchScenarios: async () => {
    try {
      const res = await fetch(`${API_BASE}/prediction/scenarios`)
      const data = await res.json()
      set({ scenarios: data.scenarios || [] })
    } catch (e) {
      set({ error: String(e) })
    }
  },

  fetchDrift: async () => {
    try {
      const res = await fetch(`${API_BASE}/prediction/drift`)
      const data = await res.json()
      set({ drift: data.drift_warnings || [] })
    } catch (e) {
      set({ error: String(e) })
    }
  },

  fetchAll: async () => {
    set({ loading: true, error: null })
    try {
      const store = usePredictionStore.getState()
      await Promise.all([
        store.fetchOverview(),
        store.fetchForecasts(),
        store.fetchScenarios(),
        store.fetchDrift(),
      ])
    } finally {
      set({ loading: false })
    }
  },
}))
