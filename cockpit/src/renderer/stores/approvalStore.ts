import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface Approval {
  id: string
  description: string
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  agent: string
  created_at: string
  status: 'pending' | 'approved' | 'denied'
}

interface ApprovalState {
  approvals: Approval[]
  loading: boolean

  fetchApprovals: () => Promise<void>
  approve: (id: string) => Promise<void>
  deny: (id: string, note?: string) => Promise<void>
}

export const useApprovalStore = create<ApprovalState>((set, get) => ({
  approvals: [],
  loading: false,

  fetchApprovals: async () => {
    try {
      const data = await fetchApi<Approval[]>('/api/umh/approvals')
      set({ approvals: data })
    } catch {
      set({ approvals: [] })
    }
  },

  approve: async (id) => {
    await fetchApi(`/api/umh/approvals/${id}/approve`, {
      method: 'POST',
    }).catch(() => {})
    get().fetchApprovals()
  },

  deny: async (id, note) => {
    await fetchApi(`/api/umh/approvals/${id}/deny`, {
      method: 'POST',
      body: JSON.stringify({ note }),
    }).catch(() => {})
    get().fetchApprovals()
  },
}))
