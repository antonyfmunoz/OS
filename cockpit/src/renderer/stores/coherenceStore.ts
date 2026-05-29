import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface TemplateSummary {
  template_id: string
  template_type: string
  status: string
  confidence: number
  observed_success_count: number
  observed_failure_count: number
  created_at: number
}

interface TemplateData {
  summary: {
    total_candidates: number
    by_status: Record<string, number>
    promoted_count: number
    pending_approvals: number
    total_decisions: number
  }
  candidates: TemplateSummary[]
  promoted: TemplateSummary[]
  pending_approvals: number
}

interface CapabilityDetail {
  confidence: number
  attempts: number
  successes: number
  failures: number
}

interface AgentProfile {
  overall_reliability: number
  total_attempts: number
  capabilities: Record<string, CapabilityDetail>
}

interface AgentCapabilityData {
  summary: {
    total_profiles: number
    total_records: number
    profiles: Record<string, { overall_reliability: number; capabilities_tracked: number; total_attempts: number }>
  }
  profiles: Record<string, AgentProfile>
}

interface PropagationEventSummary {
  event_id: string
  outcome_event_id: string
  status: string
  total_targets: number
  succeeded_targets: number
  failed_targets: number
  started_at: number
  completed_at: number
}

interface PropagationData {
  summary: {
    total_events: number
    total_targets_processed: number
    total_succeeded: number
    total_failed: number
    registered_targets: number
  }
  recent_events: PropagationEventSummary[]
  registered_targets: Array<{ name: string; primitive_relationship: string; wave: number }>
}

interface CoherenceState {
  templates: TemplateData | null
  agentCapabilities: AgentCapabilityData | null
  propagation: PropagationData | null
  loading: boolean
  error: string | null
  fetchAll: () => Promise<void>
  approveTemplate: (id: string) => Promise<boolean>
  rejectTemplate: (id: string, reason: string) => Promise<boolean>
}

export const useCoherenceStore = create<CoherenceState>((set, get) => ({
  templates: null,
  agentCapabilities: null,
  propagation: null,
  loading: false,
  error: null,

  fetchAll: async () => {
    set({ loading: true })
    try {
      const [templates, capabilities, propagation] = await Promise.all([
        fetchApi<TemplateData>('/organism/templates').catch(() => null),
        fetchApi<AgentCapabilityData>('/organism/agent-capabilities').catch(() => null),
        fetchApi<PropagationData>('/organism/propagation').catch(() => null),
      ])
      set({
        templates: templates && !('error' in templates) ? templates : null,
        agentCapabilities: capabilities && !('error' in capabilities) ? capabilities : null,
        propagation: propagation && !('error' in propagation) ? propagation : null,
        error: null,
      })
    } catch {
      set({ error: 'Failed to fetch coherence data' })
    } finally {
      set({ loading: false })
    }
  },

  approveTemplate: async (id: string) => {
    try {
      await fetchApi(`/organism/template-candidates/${id}/approve`, { method: 'POST' })
      await get().fetchAll()
      return true
    } catch {
      return false
    }
  },

  rejectTemplate: async (id: string, reason: string) => {
    try {
      await fetchApi(`/organism/template-candidates/${id}/reject`, {
        method: 'POST',
        body: JSON.stringify({ reason }),
      })
      await get().fetchAll()
      return true
    } catch {
      return false
    }
  },
}))
