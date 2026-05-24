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

interface AnalyticsState {
  data: AnalyticsData | null
  fetchAnalytics: () => Promise<void>
}

export const useAnalyticsStore = create<AnalyticsState>((set) => ({
  data: null,

  fetchAnalytics: async () => {
    try {
      const data = await fetchApi<AnalyticsData>('/analytics')
      set({ data })
    } catch { /* store stays stale */ }
  },
}))
