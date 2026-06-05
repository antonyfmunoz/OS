import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface LoopStatus {
  queue_summary: Record<string, unknown>
  pending_approval_count: number
  blocked_count: number
  human_required_count: number
  next_best: PacketSummary | null
}

interface PacketSummary {
  packet_id: string
  title: string
  user_intent: string
  domain: string
  status: string
  risk_class: string
  approval_gates: string[]
  leverage_score: number
  created_at: number
}

interface PacketDetail extends PacketSummary {
  desired_end_state: string
  constraints: string[]
  success_criteria: string[]
  human_required_actions: string[]
  blockers: string[]
  validation_plan: string
  rollback_plan: string
  audit_trail: Array<{ id: string; event_type: string; timestamp: number; data: Record<string, unknown> }>
}

interface AuditEntry {
  id: string
  event_type: string
  timestamp: number
  data: Record<string, unknown>
}

interface ImprovementStatus {
  cadence: Record<string, unknown>
  self_build_queue: Record<string, unknown>
  recent_execution_outcomes: number
  loop_active: boolean
  safety: { dry_run_only: boolean; no_auto_merge: boolean; operator_approval_required: boolean }
}

interface OperatorLoopState {
  loopStatus: LoopStatus | null
  pendingApprovals: PacketSummary[]
  activePackets: PacketSummary[]
  auditTrail: AuditEntry[]
  selectedPacket: PacketDetail | null
  improvementStatus: ImprovementStatus | null
  loading: boolean
  lastError: string | null

  fetchLoopStatus: () => Promise<void>
  fetchPendingApprovals: () => Promise<void>
  fetchActivePackets: () => Promise<void>
  fetchAuditTrail: () => Promise<void>
  fetchImprovementStatus: () => Promise<void>
  selectPacket: (id: string) => Promise<void>
  clearSelection: () => void
  submitIntent: (intent: string, desiredEndState?: string, constraints?: string[]) => Promise<PacketSummary | null>
  approvePacket: (id: string) => Promise<boolean>
  rejectPacket: (id: string, reason?: string) => Promise<boolean>
  executePacket: (id: string) => Promise<boolean>
  completePacket: (id: string, outcome: string, success: boolean) => Promise<boolean>
  recordOutcome: (packetId: string, outcome: string, domain?: string) => Promise<boolean>
  verifyOutcome: (packetId: string, claimedOutcome: string, domain?: string) => Promise<Record<string, unknown> | null>
  generateFollowUp: (packetId: string, outcome: string, suggestedIntent?: string) => Promise<PacketSummary | null>
}

export const useOperatorLoopStore = create<OperatorLoopState>((set, get) => ({
  loopStatus: null,
  pendingApprovals: [],
  activePackets: [],
  auditTrail: [],
  selectedPacket: null,
  improvementStatus: null,
  loading: false,
  lastError: null,

  fetchLoopStatus: async () => {
    try {
      const data = await fetchApi<LoopStatus>('/operator-loop/status')
      set({ loopStatus: data, lastError: null })
    } catch (e) {
      set({ lastError: 'Failed to fetch loop status' })
    }
  },

  fetchPendingApprovals: async () => {
    try {
      const data = await fetchApi<PacketSummary[]>('/operator-loop/pending-approvals')
      set({ pendingApprovals: data })
    } catch {
      set({ pendingApprovals: [] })
    }
  },

  fetchActivePackets: async () => {
    try {
      const data = await fetchApi<PacketSummary[]>('/operator-loop/active-packets')
      set({ activePackets: data })
    } catch {
      set({ activePackets: [] })
    }
  },

  fetchAuditTrail: async () => {
    try {
      const data = await fetchApi<AuditEntry[]>('/operator-loop/audit-trail')
      set({ auditTrail: data })
    } catch {
      set({ auditTrail: [] })
    }
  },

  fetchImprovementStatus: async () => {
    try {
      const data = await fetchApi<ImprovementStatus>('/self-improvement/status')
      set({ improvementStatus: data })
    } catch {
      set({ improvementStatus: null })
    }
  },

  selectPacket: async (id: string) => {
    set({ loading: true })
    try {
      const data = await fetchApi<PacketDetail>(`/operator-loop/packet/${id}`)
      set({ selectedPacket: data, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  clearSelection: () => set({ selectedPacket: null }),

  submitIntent: async (intent, desiredEndState = '', constraints = []) => {
    try {
      const res = await fetchApi<{ success: boolean; packet: PacketSummary }>('/operator-loop/submit-intent', {
        method: 'POST',
        body: JSON.stringify({ user_intent: intent, desired_end_state: desiredEndState, constraints }),
      })
      if (res.success) {
        get().fetchLoopStatus()
        get().fetchPendingApprovals()
        return res.packet
      }
      return null
    } catch {
      return null
    }
  },

  approvePacket: async (id) => {
    try {
      const res = await fetchApi<{ success: boolean }>('/operator-loop/approve', {
        method: 'POST',
        body: JSON.stringify({ packet_id: id }),
      })
      if (res.success) {
        get().fetchLoopStatus()
        get().fetchPendingApprovals()
        if (get().selectedPacket?.packet_id === id) get().selectPacket(id)
      }
      return res.success
    } catch {
      return false
    }
  },

  rejectPacket: async (id, reason = 'operator rejected') => {
    try {
      const res = await fetchApi<{ success: boolean }>('/operator-loop/reject', {
        method: 'POST',
        body: JSON.stringify({ packet_id: id, reason }),
      })
      if (res.success) {
        get().fetchLoopStatus()
        get().fetchPendingApprovals()
      }
      return res.success
    } catch {
      return false
    }
  },

  executePacket: async (id) => {
    try {
      const res = await fetchApi<{ success: boolean }>('/operator-loop/execute', {
        method: 'POST',
        body: JSON.stringify({ packet_id: id }),
      })
      if (res.success) {
        get().fetchLoopStatus()
        get().fetchActivePackets()
      }
      return res.success
    } catch {
      return false
    }
  },

  completePacket: async (id, outcome, success) => {
    try {
      const res = await fetchApi<{ success: boolean }>('/operator-loop/complete', {
        method: 'POST',
        body: JSON.stringify({ packet_id: id, outcome, success }),
      })
      if (res.success) {
        get().fetchLoopStatus()
        get().fetchActivePackets()
      }
      return res.success
    } catch {
      return false
    }
  },

  recordOutcome: async (packetId, outcome, domain = 'execution') => {
    try {
      const res = await fetchApi<{ success: boolean }>('/self-improvement/assimilate-outcome', {
        method: 'POST',
        body: JSON.stringify({ packet_id: packetId, outcome, domain, confidence: 0.8, create_follow_up: false }),
      })
      return res.success
    } catch {
      return false
    }
  },

  verifyOutcome: async (packetId, claimedOutcome, domain = '') => {
    try {
      const res = await fetchApi<{ success: boolean; verification: Record<string, unknown> }>('/self-improvement/verify-outcome', {
        method: 'POST',
        body: JSON.stringify({ packet_id: packetId, claimed_outcome: claimedOutcome, domain }),
      })
      return res.success ? res.verification : null
    } catch {
      return null
    }
  },

  generateFollowUp: async (packetId, outcome, suggestedIntent = '') => {
    try {
      const res = await fetchApi<{ success: boolean; new_packet: PacketSummary }>('/self-improvement/generate-follow-up', {
        method: 'POST',
        body: JSON.stringify({ packet_id: packetId, outcome, suggested_intent: suggestedIntent }),
      })
      if (res.success) {
        get().fetchLoopStatus()
        return res.new_packet
      }
      return null
    } catch {
      return null
    }
  },
}))
