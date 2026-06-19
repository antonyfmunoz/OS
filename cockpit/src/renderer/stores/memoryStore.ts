import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface MemoryState {
  decisions: Record<string, unknown>[]
  assumptions: Record<string, unknown>[]
  invalidatedAssumptions: Record<string, unknown>[]
  snapshot: Record<string, unknown> | null
  timeline: Record<string, unknown>[]
  history: Record<string, unknown>[]
  summary: Record<string, unknown> | null
  health: Record<string, unknown> | null
  selectedDecision: Record<string, unknown> | null
  lineage: Record<string, unknown> | null
  validity: Record<string, unknown> | null
  impact: Record<string, unknown> | null
  loading: boolean
  fetchDecisions: (status?: string) => Promise<void>
  fetchAssumptions: (status?: string) => Promise<void>
  fetchInvalidatedAssumptions: () => Promise<void>
  fetchSnapshot: () => Promise<void>
  fetchTimeline: () => Promise<void>
  fetchHistory: () => Promise<void>
  fetchSummary: () => Promise<void>
  fetchHealth: () => Promise<void>
  fetchDecisionDetail: (id: string) => Promise<void>
  fetchLineage: (id: string) => Promise<void>
  fetchValidity: (id: string) => Promise<void>
  fetchImpact: (id: string) => Promise<void>
}

export const useMemoryStore = create<MemoryState>((set) => ({
  decisions: [],
  assumptions: [],
  invalidatedAssumptions: [],
  snapshot: null,
  timeline: [],
  history: [],
  summary: null,
  health: null,
  selectedDecision: null,
  lineage: null,
  validity: null,
  impact: null,
  loading: false,

  fetchDecisions: async (status?: string) => {
    set({ loading: true })
    try {
      const url = status ? `/memory/decisions?status=${status}` : '/memory/decisions'
      const data = await fetchApi<{ decisions: Record<string, unknown>[] }>(url)
      set({ decisions: data.decisions ?? [], loading: false })
    } catch {
      set({ loading: false })
    }
  },

  fetchAssumptions: async (status?: string) => {
    try {
      const url = status ? `/memory/assumptions?status=${status}` : '/memory/assumptions'
      const data = await fetchApi<{ assumptions: Record<string, unknown>[] }>(url)
      set({ assumptions: data.assumptions ?? [] })
    } catch { /* silent */ }
  },

  fetchInvalidatedAssumptions: async () => {
    try {
      const data = await fetchApi<{ assumptions: Record<string, unknown>[] }>('/memory/assumptions/invalidated')
      set({ invalidatedAssumptions: data.assumptions ?? [] })
    } catch { /* silent */ }
  },

  fetchSnapshot: async () => {
    try {
      const data = await fetchApi<{ snapshot: Record<string, unknown> | null }>('/memory/snapshot')
      set({ snapshot: data.snapshot ?? null })
    } catch { /* silent */ }
  },

  fetchTimeline: async () => {
    try {
      const data = await fetchApi<{ events: Record<string, unknown>[] }>('/memory/timeline')
      set({ timeline: data.events ?? [] })
    } catch { /* silent */ }
  },

  fetchHistory: async () => {
    try {
      const data = await fetchApi<{ snapshots: Record<string, unknown>[] }>('/memory/history')
      set({ history: data.snapshots ?? [] })
    } catch { /* silent */ }
  },

  fetchSummary: async () => {
    try {
      const data = await fetchApi<Record<string, unknown>>('/memory/summary')
      set({ summary: data })
    } catch { /* silent */ }
  },

  fetchHealth: async () => {
    try {
      const data = await fetchApi<Record<string, unknown>>('/memory/health')
      set({ health: data })
    } catch { /* silent */ }
  },

  fetchDecisionDetail: async (id: string) => {
    try {
      const data = await fetchApi<{ decision: Record<string, unknown> }>(`/memory/decisions/${id}`)
      set({ selectedDecision: data.decision ?? null })
    } catch { /* silent */ }
  },

  fetchLineage: async (id: string) => {
    try {
      const data = await fetchApi<{ lineage: Record<string, unknown> }>(`/memory/decisions/${id}/lineage`)
      set({ lineage: data.lineage ?? null })
    } catch { /* silent */ }
  },

  fetchValidity: async (id: string) => {
    try {
      const data = await fetchApi<{ validity: Record<string, unknown> }>(`/memory/decisions/${id}/validity`)
      set({ validity: data.validity ?? null })
    } catch { /* silent */ }
  },

  fetchImpact: async (id: string) => {
    try {
      const data = await fetchApi<{ impact: Record<string, unknown> }>(`/memory/decisions/${id}/impact`)
      set({ impact: data.impact ?? null })
    } catch { /* silent */ }
  },
}))
