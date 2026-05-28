import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface Agent {
  id: string
  name: string
  status: string
  skills: string[]
  role: string
  last_action: string
  last_active: string
}

interface AgentDetail {
  id: string
  name: string
  status: string
  skills: string[]
  role: string
  deliverables: Array<{
    id: string
    description: string
    created_at: string
    status: string
  }>
}

interface AgentState {
  agents: Agent[]
  selectedId: string | null
  detail: AgentDetail | null
  loading: boolean

  fetchAgents: () => Promise<void>
  selectAgent: (id: string | null) => void
  fetchDetail: (id: string) => Promise<void>
  sendSignal: (id: string, signal: string) => Promise<void>
  controlAgent: (action: string, agentId?: string) => Promise<void>
  handoff: (source: string, target: string, task: string) => Promise<Record<string, unknown>>
  executeParallel: (tasks: Array<{ content: string }>) => Promise<Record<string, unknown>>
  checkDelegations: () => Promise<{ followups: unknown[] }>
}

export const useAgentStore = create<AgentState>((set, get) => ({
  agents: [],
  selectedId: null,
  detail: null,
  loading: false,

  fetchAgents: async () => {
    try {
      const [basic, organism] = await Promise.all([
        fetchApi<Agent[]>('/agents').catch(() => []),
        fetchApi<Agent[]>('/organism/agents').catch(() => []),
      ])
      const merged = basic.length > 0 ? basic : organism
      set({ agents: merged })
    } catch {
      set({ agents: [] })
    }
  },

  selectAgent: (id) => {
    set({ selectedId: id, detail: null })
    if (id) get().fetchDetail(id)
  },

  fetchDetail: async (id) => {
    set({ loading: true })
    try {
      const deliverables = await fetchApi<AgentDetail['deliverables']>(
        `/organism/deliverables?agent_id=${id}&limit=20`
      ).catch(() => [])
      const agent = get().agents.find((a) => a.id === id)
      if (agent) {
        set({
          detail: { ...agent, deliverables },
          loading: false,
        })
      }
    } catch {
      set({ loading: false })
    }
  },

  sendSignal: async (id, signal) => {
    await fetchApi(`/agents/${id}/signal`, {
      method: 'POST',
      body: JSON.stringify({ content: signal }),
    }).catch(() => {})
    get().fetchAgents()
  },

  controlAgent: async (action, agentId) => {
    await fetchApi('/organism/control', {
      method: 'POST',
      body: JSON.stringify({ action, agent_id: agentId }),
    }).catch(() => {})
    get().fetchAgents()
  },

  handoff: async (source: string, target: string, task: string) => {
    const result = await fetchApi<Record<string, unknown>>('/organism/handoff', {
      method: 'POST',
      body: JSON.stringify({ source_agent: source, target_agent: target, task }),
    }).catch(() => ({ error: 'handoff failed' }))
    get().fetchAgents()
    return result
  },

  executeParallel: async (tasks: Array<{ content: string }>) => {
    const result = await fetchApi<Record<string, unknown>>('/organism/parallel', {
      method: 'POST',
      body: JSON.stringify({ tasks }),
    }).catch(() => ({ error: 'parallel execution failed' }))
    get().fetchAgents()
    return result
  },

  checkDelegations: async () => {
    return fetchApi<{ followups: unknown[] }>('/organism/delegations').catch(() => ({
      followups: [],
    }))
  },
}))
