import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface SpineStats {
  total_executed: number
  total_succeeded: number
  total_failed: number
  total_rejected: number
  total_verified: number
  total_rolled_back: number
  success_rate: number
  pending_count: number
  active_count: number
  completed_count: number
  current_mode: string
  registered_mutations: number
}

interface EnvelopeRecord {
  envelope_id: string
  intent: string
  action_type: string
  source: string
  status: string
  risk_level: string
  blast_radius: string
  result_output: string
  result_success: boolean
  started_at: number
  completed_at: number
  approved_by: string
  estimated_manual_seconds: number
  retry_count: number
}

interface JournalEntry {
  envelope_id: string
  phase: string
  source: string
  details: Record<string, unknown>
  timestamp: number
}

interface JournalStats {
  total_entries: number
  in_memory: number
  by_phase: Record<string, number>
  success_rate: number
  total_rollbacks: number
  total_retries: number
}

interface GatewayDecision {
  source: string
  intent: string
  risk_level: string
  action: string
  reason: string
  envelope_id: string
  timestamp: number
}

interface GatewayStatus {
  policy: string
  reliability_threshold: number
  current_mode: string
  current_reliability: number
  total_submitted: number
  total_blocked: number
  total_recommended: number
  total_auto_executed: number
  recent_decisions_count: number
  blocked_attempts_count: number
}

interface GuardStatus {
  mode: string
  total_violations: number
  total_blocked: number
  total_allowed: number
  recent_violations: Array<{
    source: string
    action: string
    reason: string
    timestamp: number
  }>
}

interface Bottleneck {
  category: string
  severity: string
  source: string
  description: string
  metric_value: number
  threshold: number
  suggested_correction: string
  detected_at: number
  recurrence_count: number
}

interface BottleneckStatus {
  active_count: number
  active: Bottleneck[]
  history_size: number
  recurrence_top: Record<string, number>
  by_severity: Record<string, number>
  by_category: Record<string, number>
}

interface LeverageSummary {
  dimensions: {
    time_compression: number
    cognitive_compression: number
    operational_reliability: number
    execution_autonomy: number
    economic_efficiency: number
    failure_recovery_speed: number
    composite: number
  }
  totals: {
    tasks: number
    autonomous_resolutions: number
    interventions: number
    escalations: number
    approvals: number
    failures: number
    retries: number
    operator_seconds_saved: number
    cost_usd: number
  }
  recent_window: {
    tasks: number
    window_seconds: number
  }
}

interface ExecutionModeStatus {
  current_mode: string
  reliability: number
  success_count: number
  failure_count: number
  total_decisions: number
  transitions: number
  last_transition: string | null
}

interface WorkloadStatus {
  total_runs: number
  total_successes: number
  total_failures: number
  success_rate: number
  recent_outcomes: Array<{
    workload_type: string
    success: boolean
    duration_seconds: number
    findings: string[]
    recommendations: string[]
    timestamp: number
  }>
}

interface OrganismEvent {
  event_id: string
  domain: string
  event_type: string
  source: string
  priority: string
  data: Record<string, unknown>
  timestamp: number
  correlation_id: string | null
}

interface MutationSpec {
  name: string
  risk_level: string
  blast_radius: string
  description: string
  requires_approval: boolean
}

interface MutationRegistryStatus {
  total_registered?: number
  total_specs?: number
  mutations?: Record<string, MutationSpec>
  specs?: Record<string, MutationSpec>
}

interface RuntimeNodeInfo {
  runtime_id: string
  runtime_class: string
  capabilities: string[]
  status: string
  score: number
  reliability: { success_rate: number; avg_latency_ms: number; total_calls: number }
  cost: { effective: number; subscription: boolean }
}

interface RuntimeGraphStatus {
  total_runtimes: number
  available: number
  runtimes: Record<string, RuntimeNodeInfo>
}

interface OrganismStatus {
  running: boolean
  tick_count: number
  graph_available: boolean
  supervisor_available: boolean
  runtimes?: RuntimeGraphStatus
  agents: Array<{ agent_id: string; role: string; status: string }>
  total_deliverables: number
  total_learning_signals: number
}

interface ExecutionGraphStep {
  id: string
  composition_step_id: string
  description: string
  action: string
  risk_level: string
  governance_mode: string
  requires_approval: boolean
  status: string
  envelope_id: string
  result_output: string
  result_success: boolean
  error: string
}

interface ExecutionGraphPlan {
  summary: {
    id: string
    source_plan_id: string
    intent: string
    status: string
    total_steps: number
    step_status: Record<string, number>
    overall_risk: string
    governance_required: string
  }
  steps: ExecutionGraphStep[]
}

interface OrganismState {
  spine: SpineStats | null
  pendingEnvelopes: EnvelopeRecord[]
  activeEnvelopes: EnvelopeRecord[]
  completedEnvelopes: EnvelopeRecord[]
  journal: JournalStats | null
  journalRecent: JournalEntry[]
  gateway: GatewayStatus | null
  gatewayDecisions: GatewayDecision[]
  guard: GuardStatus | null
  bottleneckStatus: BottleneckStatus | null
  leverage: LeverageSummary | null
  executionMode: ExecutionModeStatus | null
  workloads: WorkloadStatus | null
  events: OrganismEvent[]
  mutations: MutationRegistryStatus | null
  runtimeGraph: RuntimeGraphStatus | null
  organismStatus: OrganismStatus | null
  executionGraphPlan: ExecutionGraphPlan | null
  executingPlan: boolean
  loading: boolean
  error: string | null

  fetchSpine: () => Promise<void>
  fetchPending: () => Promise<void>
  fetchCompleted: () => Promise<void>
  fetchJournal: () => Promise<void>
  fetchJournalRecent: () => Promise<void>
  fetchGateway: () => Promise<void>
  fetchGatewayDecisions: () => Promise<void>
  fetchGuard: () => Promise<void>
  fetchBottlenecks: () => Promise<void>
  fetchLeverage: () => Promise<void>
  fetchExecutionMode: () => Promise<void>
  fetchWorkloads: () => Promise<void>
  fetchEvents: () => Promise<void>
  fetchMutations: () => Promise<void>
  fetchOrganismStatus: () => Promise<void>
  fetchAll: () => Promise<void>
  approveEnvelope: (id: string) => Promise<void>
  rejectEnvelope: (id: string, reason?: string) => Promise<void>
  executePlan: (intent: string) => Promise<void>
}

export const useOrganismStore = create<OrganismState>((set, get) => ({
  spine: null,
  pendingEnvelopes: [],
  activeEnvelopes: [],
  completedEnvelopes: [],
  journal: null,
  journalRecent: [],
  gateway: null,
  gatewayDecisions: [],
  guard: null,
  bottleneckStatus: null,
  leverage: null,
  executionMode: null,
  workloads: null,
  events: [],
  mutations: null,
  runtimeGraph: null,
  organismStatus: null,
  executionGraphPlan: null,
  executingPlan: false,
  loading: false,
  error: null,

  fetchSpine: async () => {
    try {
      const data = await fetchApi<SpineStats>('/organism/spine')
      set({ spine: data })
    } catch { set({ spine: null }) }
  },

  fetchPending: async () => {
    try {
      const data = await fetchApi<EnvelopeRecord[]>('/organism/spine/pending')
      set({ pendingEnvelopes: data })
    } catch { set({ pendingEnvelopes: [] }) }
  },

  fetchCompleted: async () => {
    try {
      const [active, completed] = await Promise.all([
        fetchApi<EnvelopeRecord[]>('/organism/spine/active').catch(() => []),
        fetchApi<EnvelopeRecord[]>('/organism/spine/completed?limit=30').catch(() => []),
      ])
      set({ activeEnvelopes: active, completedEnvelopes: completed })
    } catch { /* noop */ }
  },

  fetchJournal: async () => {
    try {
      const data = await fetchApi<JournalStats>('/organism/journal/statistics')
      set({ journal: data })
    } catch { set({ journal: null }) }
  },

  fetchJournalRecent: async () => {
    try {
      const data = await fetchApi<JournalEntry[]>('/organism/journal/recent?limit=30')
      set({ journalRecent: data })
    } catch { set({ journalRecent: [] }) }
  },

  fetchGateway: async () => {
    try {
      const data = await fetchApi<GatewayStatus>('/organism/autonomous-gateway')
      set({ gateway: data })
    } catch { set({ gateway: null }) }
  },

  fetchGatewayDecisions: async () => {
    try {
      const data = await fetchApi<GatewayDecision[]>('/organism/autonomous-gateway/decisions')
      set({ gatewayDecisions: data })
    } catch { set({ gatewayDecisions: [] }) }
  },

  fetchGuard: async () => {
    try {
      const data = await fetchApi<GuardStatus>('/organism/spine-guard')
      set({ guard: data })
    } catch { set({ guard: null }) }
  },

  fetchBottlenecks: async () => {
    try {
      const data = await fetchApi<BottleneckStatus>('/organism/bottlenecks')
      set({ bottleneckStatus: data })
    } catch { set({ bottleneckStatus: null }) }
  },

  fetchLeverage: async () => {
    try {
      const data = await fetchApi<LeverageSummary>('/organism/leverage')
      set({ leverage: data })
    } catch { set({ leverage: null }) }
  },

  fetchExecutionMode: async () => {
    try {
      const data = await fetchApi<ExecutionModeStatus>('/organism/execution-mode')
      set({ executionMode: data })
    } catch { set({ executionMode: null }) }
  },

  fetchWorkloads: async () => {
    try {
      const data = await fetchApi<WorkloadStatus>('/organism/workloads')
      set({ workloads: data })
    } catch { set({ workloads: null }) }
  },

  fetchEvents: async () => {
    try {
      const data = await fetchApi<{ events: OrganismEvent[]; count: number }>('/organism/events?limit=50')
      set({ events: data.events ?? [] })
    } catch { set({ events: [] }) }
  },

  fetchMutations: async () => {
    try {
      const data = await fetchApi<MutationRegistryStatus>('/organism/mutations')
      set({ mutations: data })
    } catch { set({ mutations: null }) }
  },

  fetchOrganismStatus: async () => {
    try {
      const data = await fetchApi<OrganismStatus>('/organism/status')
      set({ organismStatus: data, runtimeGraph: data.runtimes ?? null })
    } catch { set({ organismStatus: null }) }
  },

  fetchAll: async () => {
    set({ loading: true })
    await Promise.all([
      get().fetchSpine(),
      get().fetchPending(),
      get().fetchCompleted(),
      get().fetchJournal(),
      get().fetchJournalRecent(),
      get().fetchGateway(),
      get().fetchGuard(),
      get().fetchBottlenecks(),
      get().fetchLeverage(),
      get().fetchExecutionMode(),
      get().fetchWorkloads(),
      get().fetchEvents(),
      get().fetchMutations(),
      get().fetchOrganismStatus(),
    ])
    set({ loading: false })
  },

  approveEnvelope: async (id) => {
    try {
      await fetchApi(`/organism/spine/approve/${id}`, { method: 'POST' })
      get().fetchPending()
      get().fetchCompleted()
    } catch { /* noop */ }
  },

  rejectEnvelope: async (id, reason) => {
    try {
      await fetchApi(`/organism/spine/reject/${id}`, {
        method: 'POST',
        body: JSON.stringify({ reason: reason ?? 'operator_rejected' }),
      })
      get().fetchPending()
      get().fetchCompleted()
    } catch { /* noop */ }
  },

  executePlan: async (intent) => {
    set({ executingPlan: true, executionGraphPlan: null })
    try {
      const data = await fetchApi<ExecutionGraphPlan>('/organism/execute-plan', {
        method: 'POST',
        body: JSON.stringify({ intent }),
      })
      set({ executionGraphPlan: data, executingPlan: false })
      get().fetchSpine()
      get().fetchCompleted()
    } catch {
      set({ executingPlan: false })
    }
  },
}))
