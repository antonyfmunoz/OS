import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface EngineeringPlan {
  plan_id: string
  intent: {
    intent_id: string
    raw_input: string
    intent_type: string
    goal: string
    scope: string[]
    constraints: string[]
    success_criteria: string[]
    affected_repos: string[]
    affected_domains: string[]
    estimated_risk: string
  }
  tasks: Array<{
    task_id: string
    title: string
    description: string
    task_type: string
    dependencies: string[]
    risk_class: string
    validation_requirements: string[]
  }>
  dependency_graph: Record<string, string[]>
  estimated_total_risk: string
  roadmap_context: Record<string, unknown>
  workspace_health: Record<string, unknown>
  engineering_risks: Array<Record<string, unknown>>
  status: string
}

interface PlanReceipt {
  receipt_id: string
  plan_id: string
  work_packet_ids: string[]
  governance_decisions: string[]
  status: string
}

interface GapAnalysis {
  analysis_id: string
  total_phases: number
  completed_phases: number
  blocked_phases: number
  gaps: Array<{
    gap_id: string
    phase_number: string
    phase_title: string
    gap_type: string
    description: string
    priority_score: number
    recommended_action: string
  }>
  completion_percentage: number
}

interface GapRecommendation {
  recommendation_id: string
  gap_id: string
  title: string
  description: string
  intent_text: string
  estimated_risk: string
  priority_score: number
}

interface EngineeringSession {
  session_id: string
  plan_id: string
  packet_ids: string[]
  executor_request_ids: string[]
  status: string
  artifacts: Array<{
    artifact_id: string
    session_id: string
    task_id: string
    file_path: string
    artifact_type: string
    diff_summary: string
    content_hash: string
  }>
  task_results: Record<string, Record<string, unknown>>
  workspace_targets: string[]
  worker_assignments: Record<string, string>
  created_at: number
  updated_at: number
  completed_at: number
  operator_id: string
  errors: string[]
}

interface EngineeringProofPackage {
  proof_id: string
  session_id: string
  plan_id: string
  artifacts: Array<Record<string, unknown>>
  validation_results: Array<Record<string, unknown>>
  risk_summary: Array<Record<string, unknown>>
  diff_summary: Record<string, unknown>
  trace_ids: string[]
  operator_recommendation: string
  recommendation_reasoning: string[]
  review_status: string
  reviewed_at: number
  reviewed_by: string
  rejection_reason: string
}

interface EngineeringState {
  activeTab: 'intent' | 'plan' | 'queue' | 'sessions' | 'review' | 'gaps'
  plans: EngineeringPlan[]
  activePlan: EngineeringPlan | null
  lastReceipt: PlanReceipt | null
  gapAnalysis: GapAnalysis | null
  gapRecommendations: GapRecommendation[]
  queueSummary: Record<string, unknown> | null
  sessions: EngineeringSession[]
  activeSession: EngineeringSession | null
  proofPackage: EngineeringProofPackage | null
  loading: boolean
  error: string | null

  setActiveTab: (tab: 'intent' | 'plan' | 'queue' | 'sessions' | 'review' | 'gaps') => void
  createPlan: (intent: string, desiredEndState?: string, constraints?: string[]) => Promise<void>
  fetchPlans: () => Promise<void>
  approvePlan: (planId: string) => Promise<void>
  rejectPlan: (planId: string) => Promise<void>
  fetchQueue: () => Promise<void>
  fetchGaps: () => Promise<void>
  fetchSessions: () => Promise<void>
  createSession: (planId: string, workspaceTargets?: string[]) => Promise<void>
  executeSession: (sessionId: string) => Promise<void>
  pauseSession: (sessionId: string) => Promise<void>
  cancelSession: (sessionId: string) => Promise<void>
  fetchReviews: () => Promise<void>
  approveReview: (proofId: string) => Promise<void>
  rejectReview: (proofId: string, reason?: string) => Promise<void>
}

export const useEngineeringStore = create<EngineeringState>((set) => ({
  activeTab: 'intent',
  plans: [],
  activePlan: null,
  lastReceipt: null,
  gapAnalysis: null,
  gapRecommendations: [],
  queueSummary: null,
  sessions: [],
  activeSession: null,
  proofPackage: null,
  loading: false,
  error: null,

  setActiveTab: (tab) => set({ activeTab: tab }),

  createPlan: async (intent, desiredEndState = '', constraints = []) => {
    set({ loading: true, error: null })
    try {
      const plan = await fetchApi<EngineeringPlan>('/engineering/plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ intent, desired_end_state: desiredEndState, constraints }),
      })
      set((s) => ({
        activePlan: plan,
        plans: [...s.plans, plan],
        activeTab: 'plan',
        loading: false,
      }))
    } catch {
      set({ error: 'Failed to create plan', loading: false })
    }
  },

  fetchPlans: async () => {
    set({ loading: true, error: null })
    try {
      const data = await fetchApi<{ plans: EngineeringPlan[] }>('/engineering/plans')
      set({ plans: data.plans, loading: false })
    } catch {
      set({ error: 'Failed to fetch plans', loading: false })
    }
  },

  approvePlan: async (planId) => {
    set({ loading: true, error: null })
    try {
      const receipt = await fetchApi<PlanReceipt>(`/engineering/plans/${encodeURIComponent(planId)}/approve`, {
        method: 'POST',
      })
      set((s) => ({
        lastReceipt: receipt,
        activePlan: s.activePlan ? { ...s.activePlan, status: 'approved' } : null,
        loading: false,
      }))
    } catch {
      set({ error: 'Failed to approve plan', loading: false })
    }
  },

  rejectPlan: async (planId) => {
    set({ loading: true, error: null })
    try {
      await fetchApi(`/engineering/plans/${encodeURIComponent(planId)}/reject`, {
        method: 'POST',
      })
      set((s) => ({
        activePlan: s.activePlan ? { ...s.activePlan, status: 'rejected' } : null,
        loading: false,
      }))
    } catch {
      set({ error: 'Failed to reject plan', loading: false })
    }
  },

  fetchQueue: async () => {
    set({ loading: true, error: null })
    try {
      const data = await fetchApi<Record<string, unknown>>('/engineering/queue')
      set({ queueSummary: data, loading: false })
    } catch {
      set({ error: 'Failed to fetch queue', loading: false })
    }
  },

  fetchGaps: async () => {
    set({ loading: true, error: null })
    try {
      const data = await fetchApi<{
        analysis: GapAnalysis
        recommendations: GapRecommendation[]
      }>('/engineering/gaps')
      set({
        gapAnalysis: data.analysis,
        gapRecommendations: data.recommendations,
        loading: false,
      })
    } catch {
      set({ error: 'Failed to fetch gaps', loading: false })
    }
  },

  fetchSessions: async () => {
    set({ loading: true, error: null })
    try {
      const data = await fetchApi<{ sessions: EngineeringSession[] }>('/engineering/sessions')
      set({ sessions: data.sessions, loading: false })
    } catch {
      set({ error: 'Failed to fetch sessions', loading: false })
    }
  },

  createSession: async (planId, workspaceTargets = []) => {
    set({ loading: true, error: null })
    try {
      const session = await fetchApi<EngineeringSession>('/engineering/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ plan_id: planId, workspace_targets: workspaceTargets }),
      })
      set((s) => ({
        activeSession: session,
        sessions: [...s.sessions, session],
        activeTab: 'sessions' as const,
        loading: false,
      }))
    } catch {
      set({ error: 'Failed to create session', loading: false })
    }
  },

  executeSession: async (sessionId) => {
    set({ loading: true, error: null })
    try {
      const data = await fetchApi<{ session: EngineeringSession; proof_package?: EngineeringProofPackage }>(
        `/engineering/sessions/${encodeURIComponent(sessionId)}/execute`,
        { method: 'POST' },
      )
      set((s) => ({
        activeSession: data.session,
        proofPackage: data.proof_package || null,
        sessions: s.sessions.map((ses) => ses.session_id === sessionId ? data.session : ses),
        loading: false,
      }))
    } catch {
      set({ error: 'Failed to execute session', loading: false })
    }
  },

  pauseSession: async (sessionId) => {
    set({ loading: true, error: null })
    try {
      const session = await fetchApi<EngineeringSession>(
        `/engineering/sessions/${encodeURIComponent(sessionId)}/pause`,
        { method: 'POST' },
      )
      set((s) => ({
        activeSession: session,
        sessions: s.sessions.map((ses) => ses.session_id === sessionId ? session : ses),
        loading: false,
      }))
    } catch {
      set({ error: 'Failed to pause session', loading: false })
    }
  },

  cancelSession: async (sessionId) => {
    set({ loading: true, error: null })
    try {
      const session = await fetchApi<EngineeringSession>(
        `/engineering/sessions/${encodeURIComponent(sessionId)}/cancel`,
        { method: 'POST' },
      )
      set((s) => ({
        activeSession: session,
        sessions: s.sessions.map((ses) => ses.session_id === sessionId ? session : ses),
        loading: false,
      }))
    } catch {
      set({ error: 'Failed to cancel session', loading: false })
    }
  },

  fetchReviews: async () => {
    set({ loading: true, error: null })
    try {
      const data = await fetchApi<{ reviews: EngineeringProofPackage[] }>('/engineering/reviews')
      const pending = data.reviews.find((r) => r.review_status === 'pending')
      set({ proofPackage: pending || null, loading: false })
    } catch {
      set({ error: 'Failed to fetch reviews', loading: false })
    }
  },

  approveReview: async (proofId) => {
    set({ loading: true, error: null })
    try {
      const pkg = await fetchApi<EngineeringProofPackage>(
        `/engineering/reviews/${encodeURIComponent(proofId)}/approve`,
        { method: 'POST' },
      )
      set({ proofPackage: pkg, loading: false })
    } catch {
      set({ error: 'Failed to approve review', loading: false })
    }
  },

  rejectReview: async (proofId, reason = '') => {
    set({ loading: true, error: null })
    try {
      const pkg = await fetchApi<EngineeringProofPackage>(
        `/engineering/reviews/${encodeURIComponent(proofId)}/reject`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ reason }),
        },
      )
      set({ proofPackage: pkg, loading: false })
    } catch {
      set({ error: 'Failed to reject review', loading: false })
    }
  },
}))
