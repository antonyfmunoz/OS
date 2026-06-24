import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface WhatIsHappening {
  continuity_state: string
  active_agents: number
  idle_agents: number
  total_agents: number
  executing_packets: number
}

interface BlockedItem {
  id: string
  title: string
  blockers: string[]
}

interface WhatIsBlocked {
  count: number
  items: BlockedItem[]
}

interface WhatFinished {
  recent_completed: number
  latest: string
}

interface WhatFailed {
  recent_failed: number
  latest: string
}

interface ResumeCandidate {
  packet_id: string
  title: string
  status: string
  leverage_score: number
}

interface Blocker {
  type: string
  description: string
}

interface ExecutionSummary {
  ok: boolean
  state: string
  health: string
  ready_count: number
  blocked_count: number
  pending_approval_count: number
  top_blockers: Blocker[]
  delegation_coverage: number
  active_tradeoffs: number
  resource_health: string
  what_is_happening: WhatIsHappening
  who_is_working: { agent_id: string; role: string; status: string }[]
  what_is_blocked: WhatIsBlocked
  what_needs_approval: { count: number }
  what_finished: WhatFinished
  what_failed: WhatFailed
  what_should_resume_next: ResumeCandidate | null
  packets_by_status: Record<string, number>
  total_packets: number
}

const EMPTY: ExecutionSummary = {
  ok: false,
  state: 'idle',
  health: 'offline',
  ready_count: 0,
  blocked_count: 0,
  pending_approval_count: 0,
  top_blockers: [],
  delegation_coverage: 0,
  active_tradeoffs: 0,
  resource_health: 'unknown',
  what_is_happening: { continuity_state: '—', active_agents: 0, idle_agents: 0, total_agents: 0, executing_packets: 0 },
  who_is_working: [],
  what_is_blocked: { count: 0, items: [] },
  what_needs_approval: { count: 0 },
  what_finished: { recent_completed: 0, latest: '' },
  what_failed: { recent_failed: 0, latest: '' },
  what_should_resume_next: null,
  packets_by_status: {},
  total_packets: 0,
}

interface ExecutionSummaryState {
  summary: ExecutionSummary
  fetchSummary: () => Promise<void>
}

export const useExecutionSummaryStore = create<ExecutionSummaryState>((set) => ({
  summary: EMPTY,

  fetchSummary: async () => {
    try {
      const data = await fetchApi<ExecutionSummary>('/command-center-mvp/execution-summary')
      set({ summary: data })
    } catch {
      // non-critical — stale data is acceptable
    }
  },
}))
