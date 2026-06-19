import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface UnifiedApprovalState {
  pending: Record<string, unknown>[]
  byUrgency: Record<string, unknown>[]
  snapshot: Record<string, unknown> | null
  decisions: Record<string, unknown>[]
  loading: boolean

  fetchPending: (sourceType?: string) => Promise<void>
  fetchByUrgency: (limit?: number) => Promise<void>
  fetchSnapshot: () => Promise<void>
  fetchDecisions: (limit?: number) => Promise<void>
  approve: (approvalId: string, sourceType: string, decidedBy?: string) => Promise<void>
  reject: (approvalId: string, sourceType: string, reason?: string, decidedBy?: string) => Promise<void>
}

export const useUnifiedApprovalStore = create<UnifiedApprovalState>((set, get) => ({
  pending: [],
  byUrgency: [],
  snapshot: null,
  decisions: [],
  loading: false,

  fetchPending: async (sourceType = '') => {
    set({ loading: true })
    try {
      const q = sourceType ? `?source_type=${sourceType}` : ''
      const data = await fetchApi<Record<string, unknown>[]>(`/unified-approval/pending${q}`)
      set({ pending: data, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  fetchByUrgency: async (limit = 10) => {
    try {
      const data = await fetchApi<Record<string, unknown>[]>(`/unified-approval/by-urgency?limit=${limit}`)
      set({ byUrgency: data })
    } catch {
      set({ byUrgency: [] })
    }
  },

  fetchSnapshot: async () => {
    try {
      const data = await fetchApi<Record<string, unknown>>('/unified-approval/snapshot')
      set({ snapshot: data })
    } catch {
      set({ snapshot: null })
    }
  },

  fetchDecisions: async (limit = 20) => {
    try {
      const data = await fetchApi<Record<string, unknown>[]>(`/unified-approval/decisions?limit=${limit}`)
      set({ decisions: data })
    } catch {
      set({ decisions: [] })
    }
  },

  approve: async (approvalId: string, sourceType: string, decidedBy = 'operator') => {
    await fetchApi('/unified-approval/approve', {
      method: 'POST',
      body: JSON.stringify({ approval_id: approvalId, source_type: sourceType, decided_by: decidedBy }),
    }).catch(() => {})
    get().fetchPending()
    get().fetchByUrgency()
  },

  reject: async (approvalId: string, sourceType: string, reason = '', decidedBy = 'operator') => {
    await fetchApi('/unified-approval/reject', {
      method: 'POST',
      body: JSON.stringify({ approval_id: approvalId, source_type: sourceType, reason, decided_by: decidedBy }),
    }).catch(() => {})
    get().fetchPending()
    get().fetchByUrgency()
  },
}))
