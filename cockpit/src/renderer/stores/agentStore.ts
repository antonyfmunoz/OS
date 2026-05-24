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
}

export const useAgentStore = create<AgentState>((set, get) => ({
  agents: [],
  selectedId: null,
  detail: null,
  loading: false,

  fetchAgents: async () => {
    try {
      const [basic, organism] = await Promise.all([
        fetchApi<Agent[]>('/api/umh/agents').catch(() => []),
        fetchApi<Agent[]>('/api/umh/organism/agents').catch(() => []),
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
        `/api/umh/organism/deliverables?agent_id=${id}&limit=20`
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
    await fetchApi(`/api/umh/agents/${id}/signal`, {
      method: 'POST',
      body: JSON.stringify({ signal }),
    }).catch(() => {})
    get().fetchAgents()
  },

  controlAgent: async (action, agentId) => {
    await fetchApi('/api/umh/organism/control', {
      method: 'POST',
      body: JSON.stringify({ action, agent_id: agentId }),
    }).catch(() => {})
    get().fetchAgents()
  },
}))
