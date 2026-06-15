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

interface EngineeringState {
  activeTab: 'intent' | 'plan' | 'queue' | 'gaps'
  plans: EngineeringPlan[]
  activePlan: EngineeringPlan | null
  lastReceipt: PlanReceipt | null
  gapAnalysis: GapAnalysis | null
  gapRecommendations: GapRecommendation[]
  queueSummary: Record<string, unknown> | null
  loading: boolean
  error: string | null

  setActiveTab: (tab: 'intent' | 'plan' | 'queue' | 'gaps') => void
  createPlan: (intent: string, desiredEndState?: string, constraints?: string[]) => Promise<void>
  fetchPlans: () => Promise<void>
  approvePlan: (planId: string) => Promise<void>
  rejectPlan: (planId: string) => Promise<void>
  fetchQueue: () => Promise<void>
  fetchGaps: () => Promise<void>
}

export const useEngineeringStore = create<EngineeringState>((set) => ({
  activeTab: 'intent',
  plans: [],
  activePlan: null,
  lastReceipt: null,
  gapAnalysis: null,
  gapRecommendations: [],
  queueSummary: null,
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
}))
