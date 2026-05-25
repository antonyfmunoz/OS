import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface ModelUsage {
  model: string
  calls: number
  tokens: number
  cost: number
}

interface DailyTrace {
  date: string
  count: number
}

interface AnalyticsData {
  model_usage: ModelUsage[]
  daily_traces: DailyTrace[]
  error_rate: number
  avg_latency_ms: number
  total_cost_30d: number
}

interface KPICard {
  name: string
  value: number | string
  unit: string
  trend: string
  period: string
}

interface PipelineStage {
  name: string
  count: number
  value: number
}

interface PipelineData {
  stages: PipelineStage[]
  total_leads: number
  total_value: number
  conversion_rate: number
}

interface AccountabilityData {
  fulfillment_rate: number
  current_streak: number
  pending_follow_ups: number
  period_stats: Record<string, unknown>
}

interface IntelligenceData {
  pattern_stats: Record<string, unknown>
  decision_stats: Record<string, unknown>
}

interface AnalyticsState {
  data: AnalyticsData | null
  kpis: KPICard[]
  pipeline: PipelineData | null
  accountability: AccountabilityData | null
  intelligence: IntelligenceData | null
  fetchAnalytics: () => Promise<void>
  fetchKPIs: () => Promise<void>
  fetchPipeline: () => Promise<void>
  fetchAccountability: () => Promise<void>
  fetchIntelligence: () => Promise<void>
  fetchAll: () => Promise<void>
}

export const useAnalyticsStore = create<AnalyticsState>((set) => ({
  data: null,
  kpis: [],
  pipeline: null,
  accountability: null,
  intelligence: null,

  fetchAnalytics: async () => {
    try {
      const data = await fetchApi<AnalyticsData>('/analytics')
      set({ data })
    } catch { /* store stays stale */ }
  },

  fetchKPIs: async () => {
    try {
      const res = await fetchApi<{ cards: KPICard[] }>('/eos/kpis')
      set({ kpis: res.cards || [] })
    } catch { /* store stays stale */ }
  },

  fetchPipeline: async () => {
    try {
      const data = await fetchApi<PipelineData>('/eos/pipeline')
      set({ pipeline: data })
    } catch { /* store stays stale */ }
  },

  fetchAccountability: async () => {
    try {
      const data = await fetchApi<AccountabilityData>('/eos/accountability')
      set({ accountability: data })
    } catch { /* store stays stale */ }
  },

  fetchIntelligence: async () => {
    try {
      const data = await fetchApi<IntelligenceData>('/eos/intelligence')
      set({ intelligence: data })
    } catch { /* store stays stale */ }
  },

  fetchAll: async () => {
    const store = useAnalyticsStore.getState()
    await Promise.all([
      store.fetchAnalytics(),
      store.fetchKPIs(),
      store.fetchPipeline(),
      store.fetchAccountability(),
      store.fetchIntelligence(),
    ])
  },
}))
