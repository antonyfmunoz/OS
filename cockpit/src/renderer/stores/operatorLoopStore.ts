import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface LoopStatus {
  queue_summary: Record<string, unknown>
  pending_approval_count: number
  blocked_count: number
  human_required_count: number
  next_best: PacketSummary | null
}

export interface PacketSummary {
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

export interface PacketDetail extends PacketSummary {
  desired_end_state: string
  constraints: string[]
  success_criteria: string[]
  failure_criteria: string[]
  human_required_actions: string[]
  blockers: string[]
  validation_plan: string
  rollback_plan: string
  verification_results: ValidationResult[]
  verification_passed: boolean | null
  linked_sandbox_id: string
  outcome_summary: string
  audit_trail: AuditEntry[]
  sandbox?: SandboxDetail
}

export interface ValidationResult {
  command: string
  label: string
  exit_code: number
  stdout: string
  stderr: string
  passed: boolean
  duration_seconds: number
  timestamp: number
}

export interface SandboxDetail {
  sandbox_id: string
  worktree_path: string
  branch_name: string
  status: string
}

export interface AuditEntry {
  id: string
  event_type: string
  timestamp: number
  data: Record<string, unknown>
}

export interface IntentContract {
  user_intent: string
  desired_end_state?: string
  constraints?: string[]
  non_goals?: string[]
  acceptance_criteria?: string[]
  quality_bar?: string
  allowed_environments?: string[]
  approval_policy?: 'auto' | 'always' | ''
  risk_tolerance?: 'low' | 'medium' | 'high' | 'critical' | ''
  proof_required?: string[]
}

interface SubmitResult {
  success: boolean
  packet: PacketSummary
  needs_approval: boolean
  risk_class: string
  next_action: string
}

interface ExecuteResult {
  success: boolean
  packet_id: string
  sandbox_id: string
  sandbox_path: string
  branch_name: string
  status: string
  all_passed: boolean
  execution_log: ValidationResult[]
  changed_files: string[]
  diff_summary: string
  validation_results: ValidationResult[]
  error?: string
}

interface LoopHealth {
  healthy: boolean
  timestamp: number
  queue_summary: Record<string, unknown>
  latest_audit_event: AuditEntry | null
  sandbox_summary: { total: number; active: number }
  reality_model: string
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
  lastExecuteResult: ExecuteResult | null
  loopHealth: LoopHealth | null
  improvementStatus: ImprovementStatus | null
  loading: boolean
  executing: boolean
  lastError: string | null

  fetchLoopStatus: () => Promise<void>
  fetchPendingApprovals: () => Promise<void>
  fetchActivePackets: () => Promise<void>
  fetchAuditTrail: () => Promise<void>
  fetchImprovementStatus: () => Promise<void>
  fetchLoopHealth: () => Promise<void>
  selectPacket: (id: string) => Promise<void>
  clearSelection: () => void
  submitIntent: (contract: IntentContract) => Promise<SubmitResult | null>
  approvePacket: (id: string) => Promise<boolean>
  rejectPacket: (id: string, reason?: string) => Promise<boolean>
  executePacket: (id: string) => Promise<ExecuteResult | null>
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
  lastExecuteResult: null,
  loopHealth: null,
  improvementStatus: null,
  loading: false,
  executing: false,
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

  fetchLoopHealth: async () => {
    try {
      const data = await fetchApi<LoopHealth>('/operator-loop/health')
      set({ loopHealth: data })
    } catch {
      set({ loopHealth: null })
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

  submitIntent: async (contract: IntentContract) => {
    set({ loading: true, lastError: null })
    try {
      const res = await fetchApi<SubmitResult>('/operator-loop/submit-intent', {
        method: 'POST',
        body: JSON.stringify(contract),
      })
      set({ loading: false })
      if (res.success) {
        get().fetchLoopStatus()
        get().fetchPendingApprovals()
        return res
      }
      return null
    } catch (e) {
      set({ loading: false, lastError: 'Failed to submit intent' })
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
    set({ executing: true, lastError: null })
    try {
      const res = await fetchApi<ExecuteResult>('/operator-loop/execute', {
        method: 'POST',
        body: JSON.stringify({ packet_id: id }),
      })
      set({ executing: false, lastExecuteResult: res })
      if (res.success) {
        get().fetchLoopStatus()
        get().fetchActivePackets()
        if (get().selectedPacket?.packet_id === id) get().selectPacket(id)
      }
      return res
    } catch (e) {
      set({ executing: false, lastError: 'Execution failed' })
      return null
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
