import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface UnifiedExecutionState {
  snapshot: Record<string, unknown> | null
  activeStreams: Record<string, unknown>[]
  pendingApprovals: Record<string, unknown>[]
  loading: boolean
  fetchSnapshot: () => Promise<void>
  fetchActive: () => Promise<void>
  fetchPendingApprovals: () => Promise<void>
  approve: (id: string, source: string) => Promise<void>
  reject: (id: string, source: string, reason: string) => Promise<void>
}

export const useUnifiedExecutionStore = create<UnifiedExecutionState>((set, get) => ({
  snapshot: null,
  activeStreams: [],
  pendingApprovals: [],
  loading: false,

  fetchSnapshot: async () => {
    set({ loading: true })
    try {
      const data = await fetchApi<Record<string, unknown>>('/unified-execution/snapshot')
      set({ snapshot: data, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  fetchActive: async () => {
    try {
      const data = await fetchApi<Record<string, unknown>[]>('/unified-execution/streams/active')
      set({ activeStreams: data })
    } catch {
      set({ activeStreams: [] })
    }
  },

  fetchPendingApprovals: async () => {
    try {
      const data = await fetchApi<Record<string, unknown>[]>('/unified-execution/approvals/pending')
      set({ pendingApprovals: data })
    } catch {
      set({ pendingApprovals: [] })
    }
  },

  approve: async (id: string, source: string) => {
    try {
      await fetchApi(`/unified-execution/approvals/${id}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source }),
      })
      await get().fetchPendingApprovals()
    } catch { /* noop */ }
  },

  reject: async (id: string, source: string, reason: string) => {
    try {
      await fetchApi(`/unified-execution/approvals/${id}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source, reason }),
      })
      await get().fetchPendingApprovals()
    } catch { /* noop */ }
  },
}))
