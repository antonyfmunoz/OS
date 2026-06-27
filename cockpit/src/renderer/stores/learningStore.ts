import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface LessonData {
  id: string
  category: string
  title: string
  description: string
  confidence: number
  confidence_reason: string
  source_count: number
  actionable: boolean
  extracted_at: number
}

interface PatternData {
  id: string
  pattern_type: string
  title: string
  description: string
  occurrences: number
  confidence: number
  recommendation: string
  first_seen: number
  last_seen: number
}

interface TrajectoryData {
  capability_id: string
  capability_name: string
  current_maturity: string
  maturity_trend: string
  predicted_next_level: string
  time_to_next_level_days: number
  events: Array<{
    event_type: string
    timestamp: number
    description: string
  }>
}

interface DriftWarning {
  drift_type: string
  severity: string
  description: string
  recommendation: string
}

interface PortfolioOverview {
  lesson_count: number
  actionable_lesson_count: number
  pattern_count: number
  active_trajectories: number
  advancing_capabilities: number
  declining_capabilities: number
  stalled_capabilities: number
  compounding_score: number
  lesson_velocity: number
  pattern_velocity: number
  evolution_velocity: number
  outcome_loop_health: string
  health: string
  drift_warnings: DriftWarning[]
  top_lessons: Array<Record<string, unknown>>
  top_patterns: Array<Record<string, unknown>>
  top_trajectories: Array<Record<string, unknown>>
}

interface LearningState {
  overview: PortfolioOverview | null
  lessons: LessonData[]
  actionableLessons: LessonData[]
  patterns: PatternData[]
  trajectories: TrajectoryData[]
  driftWarnings: DriftWarning[]
  loading: boolean
  error: string | null
  activeTab: 'overview' | 'lessons' | 'patterns' | 'evolution' | 'drift'

  setActiveTab: (tab: LearningState['activeTab']) => void
  fetchOverview: () => Promise<void>
  fetchLessons: () => Promise<void>
  fetchPatterns: () => Promise<void>
  fetchEvolution: () => Promise<void>
  fetchDrift: () => Promise<void>
  fetchAll: () => Promise<void>
}

export const useLearningStore = create<LearningState>((set) => ({
  overview: null,
  lessons: [],
  actionableLessons: [],
  patterns: [],
  trajectories: [],
  driftWarnings: [],
  loading: false,
  error: null,
  activeTab: 'overview',

  setActiveTab: (tab) => set({ activeTab: tab }),

  fetchOverview: async () => {
    try {
      const data = await fetchApi<PortfolioOverview>('/learning/overview')
      set({ overview: data })
    } catch (e) {
      set({ error: `Overview fetch failed: ${e}` })
    }
  },

  fetchLessons: async () => {
    try {
      const [all, actionable] = await Promise.all([
        fetchApi<{ lessons: LessonData[] }>('/learning/lessons'),
        fetchApi<{ lessons: LessonData[] }>('/learning/lessons/actionable'),
      ])
      set({ lessons: all.lessons, actionableLessons: actionable.lessons })
    } catch (e) {
      set({ error: `Lessons fetch failed: ${e}` })
    }
  },

  fetchPatterns: async () => {
    try {
      const data = await fetchApi<{ patterns: PatternData[] }>('/learning/patterns')
      set({ patterns: data.patterns })
    } catch (e) {
      set({ error: `Patterns fetch failed: ${e}` })
    }
  },

  fetchEvolution: async () => {
    try {
      const data = await fetchApi<{ trajectories: TrajectoryData[] }>('/learning/evolution')
      set({ trajectories: data.trajectories })
    } catch (e) {
      set({ error: `Evolution fetch failed: ${e}` })
    }
  },

  fetchDrift: async () => {
    try {
      const data = await fetchApi<{ warnings: DriftWarning[] }>('/learning/drift')
      set({ driftWarnings: data.warnings })
    } catch (e) {
      set({ error: `Drift fetch failed: ${e}` })
    }
  },

  fetchAll: async () => {
    set({ loading: true, error: null })
    try {
      const [overview, lessons, patterns, evo, drift] = await Promise.all([
        fetchApi<PortfolioOverview>('/learning/overview'),
        fetchApi<{ lessons: LessonData[] }>('/learning/lessons'),
        fetchApi<{ patterns: PatternData[] }>('/learning/patterns'),
        fetchApi<{ trajectories: TrajectoryData[] }>('/learning/evolution'),
        fetchApi<{ warnings: DriftWarning[] }>('/learning/drift'),
      ])

      set({
        overview,
        lessons: lessons.lessons,
        patterns: patterns.patterns,
        trajectories: evo.trajectories,
        driftWarnings: drift.warnings,
        loading: false,
      })
    } catch (e) {
      set({ error: `Fetch failed: ${e}`, loading: false })
    }
  },
}))
