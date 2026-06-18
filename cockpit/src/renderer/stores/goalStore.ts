import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface GoalState {
  goals: Record<string, unknown>[]
  tree: Record<string, unknown> | null
  plans: Record<string, unknown> | null
  alignment: Record<string, unknown> | null
  outcomes: Record<string, unknown> | null
  drift: Record<string, unknown> | null
  hierarchySummary: Record<string, unknown> | null
  loading: boolean
  fetchGoals: () => Promise<void>
  fetchTree: () => Promise<void>
  fetchPlans: () => Promise<void>
  fetchAlignment: () => Promise<void>
  fetchOutcomes: () => Promise<void>
  fetchDrift: () => Promise<void>
  fetchHierarchySummary: () => Promise<void>
}

export const useGoalStore = create<GoalState>((set) => ({
  goals: [],
  tree: null,
  plans: null,
  alignment: null,
  outcomes: null,
  drift: null,
  hierarchySummary: null,
  loading: false,

  fetchGoals: async () => {
    set({ loading: true })
    try {
      const data = await fetchApi<{ goals: Record<string, unknown>[] }>('/goals/active')
      set({ goals: data.goals ?? [], loading: false })
    } catch {
      set({ loading: false })
    }
  },

  fetchTree: async () => {
    try {
      const data = await fetchApi<Record<string, unknown>>('/goals/tree')
      set({ tree: data })
    } catch {
      set({ tree: null })
    }
  },

  fetchPlans: async () => {
    try {
      const data = await fetchApi<Record<string, unknown>>('/goals/plans/roadmap')
      set({ plans: data })
    } catch {
      set({ plans: null })
    }
  },

  fetchAlignment: async () => {
    try {
      const data = await fetchApi<Record<string, unknown>>('/goals/alignment/report')
      set({ alignment: data })
    } catch {
      set({ alignment: null })
    }
  },

  fetchOutcomes: async () => {
    try {
      const data = await fetchApi<Record<string, unknown>>('/goals/outcomes/snapshot')
      set({ outcomes: data })
    } catch {
      set({ outcomes: null })
    }
  },

  fetchDrift: async () => {
    try {
      const data = await fetchApi<Record<string, unknown>>('/goals/drift/summary')
      set({ drift: data })
    } catch {
      set({ drift: null })
    }
  },

  fetchHierarchySummary: async () => {
    try {
      const data = await fetchApi<Record<string, unknown>>('/goals/hierarchy/summary')
      set({ hierarchySummary: data })
    } catch {
      set({ hierarchySummary: null })
    }
  },
}))
