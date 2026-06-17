import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface MvpReadinessState {
  assessment: Record<string, unknown> | null
  score: number | null
  blockers: string[]
  escapePoints: Record<string, unknown>[]
  nextSteps: string[]
  loading: boolean

  fetchAssessment: () => Promise<void>
  fetchScore: () => Promise<void>
  fetchBlockers: () => Promise<void>
  fetchEscapePoints: () => Promise<void>
  fetchNextSteps: (limit?: number) => Promise<void>
  fetchDimension: (name: string) => Promise<Record<string, unknown>>
}

export const useMvpReadinessStore = create<MvpReadinessState>((set) => ({
  assessment: null,
  score: null,
  blockers: [],
  escapePoints: [],
  nextSteps: [],
  loading: false,

  fetchAssessment: async () => {
    set({ loading: true })
    try {
      const data = await fetchApi<Record<string, unknown>>('/mvp-readiness/assess')
      set({ assessment: data, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  fetchScore: async () => {
    try {
      const data = await fetchApi<{ score: number }>('/mvp-readiness/score')
      set({ score: data.score })
    } catch {
      set({ score: null })
    }
  },

  fetchBlockers: async () => {
    try {
      const data = await fetchApi<string[]>('/mvp-readiness/blockers')
      set({ blockers: data })
    } catch {
      set({ blockers: [] })
    }
  },

  fetchEscapePoints: async () => {
    try {
      const data = await fetchApi<Record<string, unknown>[]>('/mvp-readiness/escape-points')
      set({ escapePoints: data })
    } catch {
      set({ escapePoints: [] })
    }
  },

  fetchNextSteps: async (limit = 5) => {
    try {
      const data = await fetchApi<string[]>(`/mvp-readiness/next?limit=${limit}`)
      set({ nextSteps: data })
    } catch {
      set({ nextSteps: [] })
    }
  },

  fetchDimension: async (name: string) => {
    return fetchApi<Record<string, unknown>>(`/mvp-readiness/dimension/${name}`)
  },
}))
