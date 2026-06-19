import { create } from 'zustand'

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

const API_BASE = '/api'

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
      const res = await fetch(`${API_BASE}/learning/overview`)
      if (!res.ok) throw new Error(`${res.status}`)
      const data = await res.json()
      set({ overview: data })
    } catch (e) {
      set({ error: `Overview fetch failed: ${e}` })
    }
  },

  fetchLessons: async () => {
    try {
      const [allRes, actionableRes] = await Promise.all([
        fetch(`${API_BASE}/learning/lessons`),
        fetch(`${API_BASE}/learning/lessons/actionable`),
      ])
      const all = allRes.ok ? await allRes.json() : { lessons: [] }
      const actionable = actionableRes.ok ? await actionableRes.json() : { lessons: [] }
      set({ lessons: all.lessons, actionableLessons: actionable.lessons })
    } catch (e) {
      set({ error: `Lessons fetch failed: ${e}` })
    }
  },

  fetchPatterns: async () => {
    try {
      const res = await fetch(`${API_BASE}/learning/patterns`)
      if (!res.ok) throw new Error(`${res.status}`)
      const data = await res.json()
      set({ patterns: data.patterns })
    } catch (e) {
      set({ error: `Patterns fetch failed: ${e}` })
    }
  },

  fetchEvolution: async () => {
    try {
      const res = await fetch(`${API_BASE}/learning/evolution`)
      if (!res.ok) throw new Error(`${res.status}`)
      const data = await res.json()
      set({ trajectories: data.trajectories })
    } catch (e) {
      set({ error: `Evolution fetch failed: ${e}` })
    }
  },

  fetchDrift: async () => {
    try {
      const res = await fetch(`${API_BASE}/learning/drift`)
      if (!res.ok) throw new Error(`${res.status}`)
      const data = await res.json()
      set({ driftWarnings: data.warnings })
    } catch (e) {
      set({ error: `Drift fetch failed: ${e}` })
    }
  },

  fetchAll: async () => {
    set({ loading: true, error: null })
    try {
      const [overviewRes, lessonsRes, patternsRes, evoRes, driftRes] = await Promise.all([
        fetch(`${API_BASE}/learning/overview`),
        fetch(`${API_BASE}/learning/lessons`),
        fetch(`${API_BASE}/learning/patterns`),
        fetch(`${API_BASE}/learning/evolution`),
        fetch(`${API_BASE}/learning/drift`),
      ])

      const overview = overviewRes.ok ? await overviewRes.json() : null
      const lessons = lessonsRes.ok ? await lessonsRes.json() : { lessons: [] }
      const patterns = patternsRes.ok ? await patternsRes.json() : { patterns: [] }
      const evo = evoRes.ok ? await evoRes.json() : { trajectories: [] }
      const drift = driftRes.ok ? await driftRes.json() : { warnings: [] }

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
