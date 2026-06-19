import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface OrchestratorAwarenessState {
  context: Record<string, unknown> | null
  snapshot: Record<string, unknown> | null
  healthItems: Record<string, unknown>[]
  score: number | null
  loading: boolean

  fetchContext: () => Promise<void>
  fetchSnapshot: () => Promise<void>
  fetchHealth: () => Promise<void>
  fetchScore: () => Promise<void>
  fetchDomainAwareness: (domain: string) => Promise<Record<string, unknown>>
}

export const useOrchestratorAwarenessStore = create<OrchestratorAwarenessState>((set) => ({
  context: null,
  snapshot: null,
  healthItems: [],
  score: null,
  loading: false,

  fetchContext: async () => {
    set({ loading: true })
    try {
      const data = await fetchApi<Record<string, unknown>>('/orchestrator/context')
      set({ context: data, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  fetchSnapshot: async () => {
    try {
      const data = await fetchApi<Record<string, unknown>>('/orchestrator/snapshot')
      set({ snapshot: data })
    } catch {
      set({ snapshot: null })
    }
  },

  fetchHealth: async () => {
    try {
      const data = await fetchApi<Record<string, unknown>[]>('/orchestrator/health')
      set({ healthItems: data })
    } catch {
      set({ healthItems: [] })
    }
  },

  fetchScore: async () => {
    try {
      const data = await fetchApi<{ awareness_score: number }>('/orchestrator/score')
      set({ score: data.awareness_score })
    } catch {
      set({ score: null })
    }
  },

  fetchDomainAwareness: async (domain: string) => {
    const data = await fetchApi<Record<string, unknown>>(`/orchestrator/awareness/${domain}`)
    return data
  },
}))
