import { create } from 'zustand'
import { fetchApi } from '../api/client'

export interface UnifiedApproval {
  id: string
  approval_id?: string
  description: string
  title?: string
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  agent: string
  source_type: string
  created_at: string
  status: 'pending' | 'approved' | 'denied' | 'rejected'
  operation?: string
  details?: Record<string, unknown>
  urgency?: number
}

export interface ApprovalSnapshot {
  total_pending: number
  total_approved: number
  total_denied: number
  by_source: Record<string, number>
}

export interface ApprovalDecision {
  approval_id: string
  decision: 'approved' | 'rejected'
  decided_by: string
  decided_at: string
  source_type: string
  reason?: string
}

interface ClaimResult {
  claimed: boolean
  error?: string
}

interface ResolveResult {
  resolved: boolean
  error?: string
}

interface UnifiedApprovalState {
  pending: UnifiedApproval[]
  byUrgency: UnifiedApproval[]
  snapshot: ApprovalSnapshot | null
  decisions: ApprovalDecision[]
  loading: boolean

  fetchPending: (sourceType?: string) => Promise<void>
  fetchByUrgency: (limit?: number) => Promise<void>
  fetchSnapshot: () => Promise<void>
  fetchDecisions: (limit?: number) => Promise<void>
  approve: (approvalId: string, sourceType: string, decidedBy?: string) => Promise<void>
  reject: (approvalId: string, sourceType: string, reason?: string, decidedBy?: string) => Promise<void>
  claimAndResolve: (approvalId: string, decision: string, inputText?: string, decidedBy?: string) => Promise<ResolveResult>
  pollStatus: (approvalId: string) => Promise<Record<string, unknown> | null>
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
      const data = await fetchApi<UnifiedApproval[]>(`/unified-approval/pending${q}`)
      set({ pending: data, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  fetchByUrgency: async (limit = 10) => {
    try {
      const data = await fetchApi<UnifiedApproval[]>(`/unified-approval/by-urgency?limit=${limit}`)
      set({ byUrgency: data })
    } catch {
      set({ byUrgency: [] })
    }
  },

  fetchSnapshot: async () => {
    try {
      const data = await fetchApi<ApprovalSnapshot>('/unified-approval/snapshot')
      set({ snapshot: data })
    } catch {
      set({ snapshot: null })
    }
  },

  fetchDecisions: async (limit = 20) => {
    try {
      const data = await fetchApi<ApprovalDecision[]>(`/unified-approval/decisions?limit=${limit}`)
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

  claimAndResolve: async (approvalId: string, decision: string, inputText = '', decidedBy = 'operator') => {
    const claimRes = await fetchApi<ClaimResult>('/unified-approval/claim', {
      method: 'POST',
      body: JSON.stringify({ approval_id: approvalId, surface: 'cockpit' }),
    }).catch(() => ({ claimed: false, error: 'network' } as ClaimResult))

    if (!claimRes.claimed) {
      return { resolved: false, error: claimRes.error || 'claim_failed' }
    }

    const resolveRes = await fetchApi<ResolveResult>('/unified-approval/resolve', {
      method: 'POST',
      body: JSON.stringify({
        approval_id: approvalId,
        decision,
        surface: 'cockpit',
        input_text: inputText,
        decided_by: decidedBy,
      }),
    }).catch(() => ({ resolved: false, error: 'network' } as ResolveResult))

    get().fetchPending()
    get().fetchByUrgency()
    return resolveRes
  },

  pollStatus: async (approvalId: string) => {
    try {
      return await fetchApi<Record<string, unknown>>(`/unified-approval/status/${approvalId}`)
    } catch {
      return null
    }
  },
}))
