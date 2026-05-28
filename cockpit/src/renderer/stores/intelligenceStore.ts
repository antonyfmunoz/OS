import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface BottleneckEvidence {
  signal: string
  observed: string
  expected?: string
}

interface Bottleneck {
  bottleneck_id: string
  category: string
  severity: string
  confidence: number
  source: string
  description: string
  metric_value: number
  threshold: number
  evidence: BottleneckEvidence[]
  recommendation: string
  detected_at: number
  recurrence_count: number
}

interface LeverageEvidence {
  source: string
  signal: string
  detail: string
}

interface LeverageOpportunity {
  opportunity_id: string
  action: string
  impact_description: string
  impact_score: number
  confidence: number
  category: string
  evidence: LeverageEvidence[]
  reasoning: string
  detected_at: number
}

interface ActionEvidence {
  source: string
  signal: string
  detail: string
}

interface NextAction {
  action_id: string
  priority: string
  priority_score: number
  action: string
  category: string
  reason: string
  evidence: ActionEvidence[]
  estimated_effort: string
  generated_at: number
}

interface DimensionScore {
  dimension: string
  score: number
  weight: number
  weighted_contribution: number
  factors: Record<string, number>
  gap_factors: string[]
  explanation: string
}

interface ReadinessData {
  composite_score: number
  overall_status: string
  dimensions: Record<string, DimensionScore>
  computed_at: number
  weight_documentation: Record<string, number>
}

interface IntelligenceData {
  bottlenecks: {
    active_count: number
    active: Bottleneck[]
    history_size: number
    recurrence_top: Record<string, number>
    by_severity: Record<string, number>
    by_category: Record<string, number>
  }
  leverage: {
    total_opportunities: number
    last_computed: number
    top_opportunities: LeverageOpportunity[]
  }
  next_actions: {
    total_actions: number
    last_computed: number
    actions: NextAction[]
  }
  readiness: ReadinessData
}

interface IntelligenceState {
  data: IntelligenceData | null
  loading: boolean
  error: string | null
  fetchIntelligence: () => Promise<void>
}

export const useIntelligenceStore = create<IntelligenceState>((set) => ({
  data: null,
  loading: false,
  error: null,

  fetchIntelligence: async () => {
    set({ loading: true })
    try {
      const data = await fetchApi<IntelligenceData>('/organism/intelligence')
      if (data && !('error' in data)) {
        set({ data, error: null })
      }
    } catch {
      set({ error: 'Failed to fetch intelligence data' })
    } finally {
      set({ loading: false })
    }
  },
}))
