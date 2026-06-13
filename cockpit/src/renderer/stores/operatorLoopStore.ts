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
  execution_records?: ExecutionRecordSummary[]
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

export type ExecutionMode = 'validate_only' | 'implement' | 'implement_and_validate'

export interface IntentContract {
  user_intent: string
  desired_end_state?: string
  constraints?: string[]
  non_goals?: string[]
  acceptance_criteria?: string[]
  quality_bar?: string
  approval_policy?: 'auto' | 'always' | ''
  risk_tolerance?: 'low' | 'medium' | 'high' | 'critical' | ''
  proof_required?: string[]
  execution_mode?: ExecutionMode
}

export interface ExecutionPlan {
  plan_id: string
  packet_id: string
  objectives: string[]
  files_expected: string[]
  validation_strategy: string
  rollback_strategy: string
  risk_assessment: string
  created_at: number
  approved: boolean
}

export interface ExecutionRecordSummary {
  record_id: string
  packet_id: string
  sandbox_id: string
  mode: string
  started_at: number
  completed_at: number
  duration_seconds: number
  files_changed: string[]
  diff_summary: string
  commits: string[]
  all_validations_passed: boolean
  success: boolean
  error: string
  agent_output: string
  validation_results: ValidationResult[]
  plan?: ExecutionPlan
}

export interface FailureReport {
  report_id: string
  packet_id: string
  root_cause: string
  failing_command: string
  logs: string
  recommended_action: string
  retry_count: number
  max_retries: number
}

interface SubmitResult {
  success: boolean
  packet: PacketSummary
  needs_approval: boolean
  risk_class: string
  execution_mode: string
  next_action: string
}

interface ExecuteResult {
  success: boolean
  packet_id: string
  record_id: string
  sandbox_id: string
  mode: string
  execution_success: boolean
  files_changed: string[]
  diff_summary: string
  commits: string[]
  validation_results: ValidationResult[]
  all_passed: boolean
  agent_output: string
  duration_seconds: number
  error: string
  plan: ExecutionPlan | null
  failure_report: FailureReport | null
  needs_review: boolean
  next_action: string
}

interface LoopHealth {
  healthy: boolean
  timestamp: number
  queue_summary: Record<string, unknown>
  latest_audit_event: AuditEntry | null
  sandbox_summary: { total: number; active: number }
  execution_records: number
}

interface ImprovementStatus {
  cadence: Record<string, unknown>
  self_build_queue: Record<string, unknown>
  recent_execution_outcomes: number
  loop_active: boolean
  safety: { dry_run_only: boolean; no_auto_merge: boolean; operator_approval_required: boolean }
}

// ── Phase 3: Empire types ──────────────────────────────────

export interface DomainDefinition {
  domain_id: string
  label: string
  description: string
  allowed_actions: string[]
  proof_requirements: ProofRequirement[]
  default_agent_types: string[]
  approval_gates: string[]
  default_risk_class: string
  validation_methods: string[]
  background_eligible: boolean
  escalation_triggers: string[]
}

export interface ProofRequirement {
  proof_type: string
  description: string
  required: boolean
  validation_command?: string
}

export interface AgentTypeDef {
  agent_type_id: string
  label: string
  description: string
  capabilities: string[]
  permissions: string[]
  allowed_domains: string[]
  required_tools: string[]
  max_risk_class: string
  can_auto_execute: boolean
  can_create_subpackets: boolean
}

export interface RoutingResultData {
  routing_id: string
  domain: string
  domain_label: string
  objective: string
  scope: string
  urgency: string
  risk_level: string
  required_approvals: string[]
  suggested_agents: string[]
  proof_requirements: ProofRequirement[]
  work_packets: Record<string, unknown>[]
  suggested_sequence: string[]
  missing_context: string[]
  profile_constraints: Record<string, unknown>
  background_eligible: boolean
  next_action: string
  created_at: number
}

export interface RealitySnapshot {
  active_domains: string[]
  active_loops: Record<string, unknown>[]
  blocked_items: Record<string, unknown>[]
  open_approvals: number
  recent_outcomes: Record<string, unknown>[]
  current_phase: string
  next_best_actions: string[]
}

export interface NextActionsData {
  next_actions: string[]
  open_approvals: number
  blocked_count: number
  active_domains: string[]
}

// ── Phase 4: Strategic Gap types ──────────────────────────────────

export interface SuccessCriterionData {
  description: string
  measurable: boolean
  current_value: string
  target_value: string
  met: boolean
}

export interface GoalData {
  goal_id: string
  title: string
  description: string
  goal_type: string
  status: string
  domain: string
  parent_goal_id: string
  child_goal_ids: string[]
  success_criteria: SuccessCriterionData[]
  required_capabilities: string[]
  required_milestones: string[]
  dependencies: string[]
  target_date: string
  priority: number
  created_at: number
  updated_at: number
}

export interface GapData {
  gap_id: string
  goal_id: string
  title: string
  description: string
  gap_type: string
  severity: string
  domain: string
  current_state: string
  required_state: string
  blocking_goals: string[]
  dependencies: string[]
  estimated_effort: string
  priority_score: number
  created_at: number
}

export interface RecommendationData {
  recommendation_id: string
  gap_id: string
  title: string
  rationale: string
  impact_estimate: string
  risk_estimate: string
  suggested_domain: string
  suggested_agents: string[]
  dependency_chain: string[]
  priority_score: number
  status: string
  converted_packet_id: string
  decision_reason: string
  created_at: number
  decided_at: number
}

export interface DecisionData {
  decision_id: string
  recommendation_id: string
  gap_id: string
  goal_id: string
  action: string
  reason: string
  outcome_packet_id: string
  outcome_summary: string
  was_effective: boolean | null
  created_at: number
}

export interface AnalysisResult {
  reality: RealitySnapshot
  goals: GoalData[]
  gaps: GapData[]
  gap_count: number
  recommendations: RecommendationData[]
  recommendation_count: number
  top_recommendation: RecommendationData | null
  analyzed_at: number
}

// ── Phase 5: Tick Loop types ──────────────────────────────────

export interface TickStatusData {
  running: boolean
  paused: boolean
  frequency: string
  cycle_count: number
  last_tick_at: number | null
  last_change_detected: boolean | null
  pending_candidates: number
  drift_warning_count: number
  active_profiles: string[]
  operator_present: boolean
}

export interface TickRecord {
  tick_id: string
  cycle_number: number
  timestamp: number
  change_detected: boolean
  analysis_ran: boolean
  gaps_found: number
  recommendations_generated: number
  candidates_added: number
  drift_warnings: number
  expired_candidates: number
  operator_present: boolean
  active_profiles: string[]
  elapsed_ms: number
  skipped_reason: string
}

export interface CandidateItem {
  candidate_id: string
  recommendation_id: string
  title: string
  domain: string
  priority_score: number
  impact: string
  risk: string
  dependencies: string[]
  lifecycle: string
  proposed_at: number
  expires_at: number
  decided_at: number
}

export interface DriftWarningData {
  warning_id: string
  goal_id: string
  goal_title: string
  domain: string
  severity: string
  days_stagnant: number
  last_activity: number
  completion_ratio: number
  message: string
  created_at: number
}

export interface TickStrategicState {
  tick: {
    running: boolean
    paused: boolean
    frequency: string
    cycle_count: number
    last_tick: TickRecord | null
    next_tick_in: number | null
  }
  last_analysis: Record<string, unknown> | null
  last_delta: {
    has_meaningful_change: boolean
    new_outcomes: Record<string, unknown>[]
    new_failures: Record<string, unknown>[]
    new_approvals: number
    new_packets: Record<string, unknown>[]
    goal_changes: string[]
    domain_changes: string[]
  } | null
  candidate_queue: {
    total: number
    pending: number
    items: CandidateItem[]
  }
  drift_warnings: DriftWarningData[]
  active_profiles: string[]
  operator_present: boolean
  recent_ticks: TickRecord[]
}

interface OperatorLoopState {
  loopStatus: LoopStatus | null
  pendingApprovals: PacketSummary[]
  activePackets: PacketSummary[]
  auditTrail: AuditEntry[]
  selectedPacket: PacketDetail | null
  lastExecuteResult: ExecuteResult | null
  lastPlan: ExecutionPlan | null
  loopHealth: LoopHealth | null
  improvementStatus: ImprovementStatus | null
  loading: boolean
  executing: boolean
  lastError: string | null

  // Phase 3: Empire state
  domains: DomainDefinition[]
  agentTypes: AgentTypeDef[]
  lastRouting: RoutingResultData | null
  realitySnapshot: RealitySnapshot | null
  nextActions: NextActionsData | null
  packetsByDomain: Record<string, Record<string, unknown>[]>
  domainFilter: string

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
  generatePlan: (packetId: string) => Promise<ExecutionPlan | null>
  approvePlan: (planId: string) => Promise<boolean>
  executePacket: (id: string, mode?: ExecutionMode, planId?: string) => Promise<ExecuteResult | null>
  completePacket: (id: string, outcome: string, success: boolean) => Promise<boolean>
  recordOutcome: (packetId: string, outcome: string, domain?: string) => Promise<boolean>
  verifyOutcome: (packetId: string, claimedOutcome: string, domain?: string) => Promise<Record<string, unknown> | null>
  generateFollowUp: (packetId: string, outcome: string, suggestedIntent?: string) => Promise<PacketSummary | null>

  // Phase 3: Empire actions
  routeIntent: (intent: string, opts?: { desired_end_state?: string; constraints?: string[]; profile_mode?: string }) => Promise<RoutingResultData | null>
  fetchDomains: () => Promise<void>
  fetchAgentTypes: () => Promise<void>
  fetchReality: () => Promise<void>
  fetchNextActions: () => Promise<void>
  fetchPacketsByDomain: () => Promise<void>
  setDomainFilter: (domain: string) => void

  // Phase 4: Strategic Gap state
  goals: GoalData[]
  gaps: GapData[]
  recommendations: RecommendationData[]
  decisions: DecisionData[]
  lastAnalysis: AnalysisResult | null
  strategyLoading: boolean

  // Phase 5: Tick Loop state
  tickStatus: TickStatusData | null
  tickStrategicState: TickStrategicState | null
  tickCandidates: CandidateItem[]
  tickDriftWarnings: DriftWarningData[]
  tickHistory: TickRecord[]
  tickLoading: boolean

  // Phase 5: Tick Loop actions
  fetchTickStatus: () => Promise<void>
  fetchTickState: () => Promise<void>
  executeTick: () => Promise<TickRecord | null>
  startTick: (frequency?: string) => Promise<void>
  stopTick: () => Promise<void>
  pauseTick: () => Promise<void>
  resumeTick: () => Promise<void>
  setTickFrequency: (frequency: string) => Promise<void>
  setTickProfiles: (profiles: string[]) => Promise<void>
  fetchTickCandidates: () => Promise<void>
  acceptCandidate: (candidateId: string) => Promise<boolean>
  rejectCandidate: (candidateId: string) => Promise<boolean>
  fetchTickDrift: () => Promise<void>
  fetchTickHistory: () => Promise<void>

  // Phase 4: Strategic Gap actions
  runAnalysis: () => Promise<AnalysisResult | null>
  fetchGoals: () => Promise<void>
  addGoal: (goal: Partial<GoalData>) => Promise<GoalData | null>
  updateGoal: (goalId: string, updates: Partial<GoalData>) => Promise<GoalData | null>
  deleteGoal: (goalId: string) => Promise<boolean>
  fetchGaps: () => Promise<void>
  fetchRecommendations: () => Promise<void>
  approveRecommendation: (recId: string, reason?: string) => Promise<Record<string, unknown> | null>
  rejectRecommendation: (recId: string, reason?: string) => Promise<boolean>
  fetchDecisions: () => Promise<void>
  recordDecisionOutcome: (decisionId: string, wasEffective: boolean, summary?: string) => Promise<boolean>
}

export const useOperatorLoopStore = create<OperatorLoopState>((set, get) => ({
  loopStatus: null,
  pendingApprovals: [],
  activePackets: [],
  auditTrail: [],
  // Phase 3 initial state
  domains: [],
  agentTypes: [],
  lastRouting: null,
  realitySnapshot: null,
  nextActions: null,
  packetsByDomain: {},
  domainFilter: '',
  // Phase 5 initial state
  tickStatus: null,
  tickStrategicState: null,
  tickCandidates: [],
  tickDriftWarnings: [],
  tickHistory: [],
  tickLoading: false,
  // Phase 4 initial state
  goals: [],
  gaps: [],
  recommendations: [],
  decisions: [],
  lastAnalysis: null,
  strategyLoading: false,
  selectedPacket: null,
  lastExecuteResult: null,
  lastPlan: null,
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

  generatePlan: async (packetId: string) => {
    set({ loading: true, lastError: null })
    try {
      const res = await fetchApi<{ success: boolean; plan: ExecutionPlan }>('/operator-loop/generate-plan', {
        method: 'POST',
        body: JSON.stringify({ packet_id: packetId }),
      })
      set({ loading: false })
      if (res.success) {
        set({ lastPlan: res.plan })
        return res.plan
      }
      return null
    } catch {
      set({ loading: false, lastError: 'Failed to generate plan' })
      return null
    }
  },

  approvePlan: async (planId: string) => {
    try {
      const res = await fetchApi<{ success: boolean }>('/operator-loop/approve-plan', {
        method: 'POST',
        body: JSON.stringify({ plan_id: planId }),
      })
      if (res.success && get().lastPlan?.plan_id === planId) {
        set({ lastPlan: { ...get().lastPlan!, approved: true } })
      }
      return res.success
    } catch {
      return false
    }
  },

  executePacket: async (id, mode = 'validate_only', planId) => {
    set({ executing: true, lastError: null })
    try {
      const body: Record<string, string> = { packet_id: id, mode }
      if (planId) body.plan_id = planId
      const res = await fetchApi<ExecuteResult>('/operator-loop/execute', {
        method: 'POST',
        body: JSON.stringify(body),
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
      const res = await fetchApi<{ success: boolean }>('/operator-loop/record-outcome', {
        method: 'POST',
        body: JSON.stringify({ packet_id: packetId, outcome, domain, confidence: 0.8 }),
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

  // ── Phase 3: Empire actions ──────────────────────────────

  routeIntent: async (intent, opts = {}) => {
    set({ loading: true, lastError: null })
    try {
      const res = await fetchApi<{ success: boolean; routing: RoutingResultData }>('/empire/route', {
        method: 'POST',
        body: JSON.stringify({
          intent,
          desired_end_state: opts.desired_end_state ?? '',
          constraints: opts.constraints ?? [],
          profile_mode: opts.profile_mode ?? '',
        }),
      })
      set({ loading: false })
      if (res.success) {
        set({ lastRouting: res.routing })
        get().fetchLoopStatus()
        get().fetchActivePackets()
        get().fetchPendingApprovals()
        return res.routing
      }
      return null
    } catch (e) {
      set({ loading: false, lastError: 'Failed to route intent' })
      return null
    }
  },

  fetchDomains: async () => {
    try {
      const data = await fetchApi<DomainDefinition[]>('/empire/domains')
      set({ domains: data })
    } catch {
      set({ domains: [] })
    }
  },

  fetchAgentTypes: async () => {
    try {
      const data = await fetchApi<AgentTypeDef[]>('/empire/agents')
      set({ agentTypes: data })
    } catch {
      set({ agentTypes: [] })
    }
  },

  fetchReality: async () => {
    try {
      const res = await fetchApi<{ success: boolean; reality: RealitySnapshot }>('/empire/reality')
      if (res.success) set({ realitySnapshot: res.reality })
    } catch {
      set({ realitySnapshot: null })
    }
  },

  fetchNextActions: async () => {
    try {
      const res = await fetchApi<NextActionsData>('/empire/next-actions')
      if (res.next_actions) set({ nextActions: res })
    } catch {
      set({ nextActions: null })
    }
  },

  fetchPacketsByDomain: async () => {
    try {
      const res = await fetchApi<{ success: boolean; domains: Record<string, Record<string, unknown>[]> }>('/empire/packets-by-domain')
      if (res.success) set({ packetsByDomain: res.domains })
    } catch {
      set({ packetsByDomain: {} })
    }
  },

  setDomainFilter: (domain: string) => set({ domainFilter: domain }),

  // ── Phase 5: Tick Loop actions ──────────────────────────────

  fetchTickStatus: async () => {
    try {
      const res = await fetchApi<{ success: boolean } & TickStatusData>('/tick/status')
      if (res.success) set({ tickStatus: res })
    } catch {
      set({ tickStatus: null })
    }
  },

  fetchTickState: async () => {
    try {
      const res = await fetchApi<{ success: boolean } & TickStrategicState>('/tick/state')
      if (res.success) set({ tickStrategicState: res })
    } catch {
      set({ tickStrategicState: null })
    }
  },

  executeTick: async () => {
    set({ tickLoading: true })
    try {
      const res = await fetchApi<{ success: boolean; tick: TickRecord }>('/tick/execute', { method: 'POST' })
      set({ tickLoading: false })
      if (res.success) {
        get().fetchTickStatus()
        get().fetchTickState()
        get().fetchTickCandidates()
        get().fetchTickDrift()
        get().fetchTickHistory()
        return res.tick
      }
      return null
    } catch {
      set({ tickLoading: false })
      return null
    }
  },

  startTick: async (frequency = '1m') => {
    try {
      await fetchApi<{ success: boolean }>('/tick/start', {
        method: 'POST',
        body: JSON.stringify({ frequency }),
      })
      get().fetchTickStatus()
    } catch {
      // silent
    }
  },

  stopTick: async () => {
    try {
      await fetchApi<{ success: boolean }>('/tick/stop', { method: 'POST' })
      get().fetchTickStatus()
    } catch {
      // silent
    }
  },

  pauseTick: async () => {
    try {
      await fetchApi<{ success: boolean }>('/tick/pause', { method: 'POST' })
      get().fetchTickStatus()
    } catch {
      // silent
    }
  },

  resumeTick: async () => {
    try {
      await fetchApi<{ success: boolean }>('/tick/resume', { method: 'POST' })
      get().fetchTickStatus()
    } catch {
      // silent
    }
  },

  setTickFrequency: async (frequency: string) => {
    try {
      await fetchApi<{ success: boolean }>('/tick/frequency', {
        method: 'POST',
        body: JSON.stringify({ frequency }),
      })
      get().fetchTickStatus()
    } catch {
      // silent
    }
  },

  setTickProfiles: async (profiles: string[]) => {
    try {
      await fetchApi<{ success: boolean }>('/tick/profiles', {
        method: 'POST',
        body: JSON.stringify({ profiles }),
      })
      get().fetchTickStatus()
    } catch {
      // silent
    }
  },

  fetchTickCandidates: async () => {
    try {
      const res = await fetchApi<{ success: boolean; all: CandidateItem[] }>('/tick/candidates')
      if (res.success) set({ tickCandidates: res.all })
    } catch {
      set({ tickCandidates: [] })
    }
  },

  acceptCandidate: async (candidateId: string) => {
    try {
      const res = await fetchApi<{ success: boolean }>(`/tick/candidates/${candidateId}/accept`, { method: 'POST' })
      if (res.success) get().fetchTickCandidates()
      return res.success ?? false
    } catch {
      return false
    }
  },

  rejectCandidate: async (candidateId: string) => {
    try {
      const res = await fetchApi<{ success: boolean }>(`/tick/candidates/${candidateId}/reject`, { method: 'POST' })
      if (res.success) get().fetchTickCandidates()
      return res.success ?? false
    } catch {
      return false
    }
  },

  fetchTickDrift: async () => {
    try {
      const res = await fetchApi<{ success: boolean; warnings: DriftWarningData[] }>('/tick/drift')
      if (res.success) set({ tickDriftWarnings: res.warnings })
    } catch {
      set({ tickDriftWarnings: [] })
    }
  },

  fetchTickHistory: async () => {
    try {
      const res = await fetchApi<{ success: boolean; ticks: TickRecord[] }>('/tick/history')
      if (res.success) set({ tickHistory: res.ticks })
    } catch {
      set({ tickHistory: [] })
    }
  },

  // ── Phase 4: Strategic Gap actions ──────────────────────────────

  runAnalysis: async () => {
    set({ strategyLoading: true })
    try {
      const res = await fetchApi<{ success: boolean } & AnalysisResult>('/strategy/analyze', { method: 'POST' })
      set({ strategyLoading: false })
      if (res.success) {
        set({
          lastAnalysis: res,
          goals: res.goals,
          gaps: res.gaps,
          recommendations: res.recommendations,
        })
        return res
      }
      return null
    } catch {
      set({ strategyLoading: false, lastError: 'Failed to run analysis' })
      return null
    }
  },

  fetchGoals: async () => {
    try {
      const res = await fetchApi<{ success: boolean; goals: GoalData[] }>('/strategy/goals')
      if (res.success) set({ goals: res.goals })
    } catch {
      set({ goals: [] })
    }
  },

  addGoal: async (goal) => {
    try {
      const res = await fetchApi<{ success: boolean; goal: GoalData }>('/strategy/goals/add', {
        method: 'POST',
        body: JSON.stringify(goal),
      })
      if (res.success) {
        get().fetchGoals()
        return res.goal
      }
      return null
    } catch {
      set({ lastError: 'Failed to add goal' })
      return null
    }
  },

  updateGoal: async (goalId, updates) => {
    try {
      const res = await fetchApi<{ success: boolean; goal: GoalData }>(`/strategy/goals/${goalId}`, {
        method: 'PUT',
        body: JSON.stringify(updates),
      })
      if (res.success) {
        get().fetchGoals()
        return res.goal
      }
      return null
    } catch {
      set({ lastError: 'Failed to update goal' })
      return null
    }
  },

  deleteGoal: async (goalId) => {
    try {
      const res = await fetchApi<{ success: boolean }>(`/strategy/goals/${goalId}`, { method: 'DELETE' })
      if (res.success) get().fetchGoals()
      return res.success ?? false
    } catch {
      return false
    }
  },

  fetchGaps: async () => {
    try {
      const res = await fetchApi<{ success: boolean; gaps: GapData[] }>('/strategy/gaps')
      if (res.success) set({ gaps: res.gaps })
    } catch {
      set({ gaps: [] })
    }
  },

  fetchRecommendations: async () => {
    try {
      const res = await fetchApi<{ success: boolean; recommendations: RecommendationData[] }>('/strategy/recommendations')
      if (res.success) set({ recommendations: res.recommendations })
    } catch {
      set({ recommendations: [] })
    }
  },

  approveRecommendation: async (recId, reason = '') => {
    try {
      const res = await fetchApi<{ success: boolean; routing?: unknown; packet_id?: string }>(`/strategy/recommendations/${recId}/approve`, {
        method: 'POST',
        body: JSON.stringify({ reason }),
      })
      if (res.success) {
        get().fetchRecommendations()
        get().fetchActivePackets()
        get().fetchPendingApprovals()
      }
      return res.success ? (res as Record<string, unknown>) : null
    } catch {
      return null
    }
  },

  rejectRecommendation: async (recId, reason = '') => {
    try {
      const res = await fetchApi<{ success: boolean }>(`/strategy/recommendations/${recId}/reject`, {
        method: 'POST',
        body: JSON.stringify({ reason }),
      })
      if (res.success) get().fetchRecommendations()
      return res.success ?? false
    } catch {
      return false
    }
  },

  fetchDecisions: async () => {
    try {
      const res = await fetchApi<{ success: boolean; decisions: DecisionData[] }>('/strategy/decisions')
      if (res.success) set({ decisions: res.decisions })
    } catch {
      set({ decisions: [] })
    }
  },

  recordDecisionOutcome: async (decisionId, wasEffective, summary = '') => {
    try {
      const res = await fetchApi<{ success: boolean }>(`/strategy/decisions/${decisionId}/outcome`, {
        method: 'POST',
        body: JSON.stringify({ was_effective: wasEffective, summary }),
      })
      if (res.success) get().fetchDecisions()
      return res.success ?? false
    } catch {
      return false
    }
  },
}))
