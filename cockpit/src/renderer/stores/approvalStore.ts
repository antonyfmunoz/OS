import { create } from 'zustand'
import { fetchApi } from '../api/client'

export interface Approval {
  id: string
  description: string
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  agent: string
  created_at: string
  status: 'pending' | 'approved' | 'denied'
  operation?: string
  details?: Record<string, unknown>
}

interface ApprovalState {
  approvals: Approval[]
  loading: boolean

  fetchApprovals: () => Promise<void>
  approve: (id: string, metadata?: Record<string, unknown>) => Promise<void>
  deny: (id: string, note?: string) => Promise<void>
}

export const useApprovalStore = create<ApprovalState>((set, get) => ({
  approvals: [],
  loading: false,

  fetchApprovals: async () => {
    try {
      const data = await fetchApi<Approval[]>('/approvals')
      set({ approvals: data })
    } catch {
      set({ approvals: [] })
    }
  },

  approve: async (id, metadata) => {
    await fetchApi(`/approvals/${id}/approve`, {
      method: 'POST',
      body: metadata ? JSON.stringify({ metadata }) : undefined,
    }).catch(() => {})
    get().fetchApprovals()
  },

  deny: async (id, note) => {
    await fetchApi(`/approvals/${id}/deny`, {
      method: 'POST',
      body: JSON.stringify({ note }),
    }).catch(() => {})
    get().fetchApprovals()
  },
}))
