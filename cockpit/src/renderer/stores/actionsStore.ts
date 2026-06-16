import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface ActionParameter {
  name: string
  param_type: string
  required: boolean
  default: string
  choices: string[]
  description: string
}

interface ActionPrecondition {
  check_type: string
  target: string
  expected: boolean
  description: string
}

interface PreconditionResult {
  check_type: string
  passed: boolean
  reason: string
}

export interface ActionDefinition {
  action_id: string
  name: string
  description: string
  category: string
  risk_level: string
  executor_type: string
  operation: string
  command_template: string
  parameters: ActionParameter[]
  preconditions: ActionPrecondition[]
  tags: string[]
  enabled: boolean
  precondition_state?: PreconditionResult[]
}

export interface ActionResult {
  request_id: string
  action_id: string
  status: string
  execution_plan_id: string
  precondition_results: PreconditionResult[]
  executor_result: Record<string, unknown>
  started_at: number
  completed_at: number
  error: string
}

interface ActionsState {
  actions: ActionDefinition[]
  history: ActionResult[]
  loading: boolean
  executing: string | null
  error: string | null
  fetchCatalog: (category?: string) => Promise<void>
  executeAction: (actionId: string, params: Record<string, string>) => Promise<ActionResult | null>
  approveAction: (planId: string) => Promise<ActionResult | null>
  fetchHistory: (limit?: number) => Promise<void>
}

export const useActionsStore = create<ActionsState>((set, get) => ({
  actions: [],
  history: [],
  loading: false,
  executing: null,
  error: null,

  fetchCatalog: async (category?: string) => {
    set({ loading: true, error: null })
    try {
      const url = category
        ? `/api/umh/actions/catalog?category=${category}`
        : '/api/umh/actions/catalog'
      const data = await fetchApi(url)
      set({ actions: data.actions ?? [], loading: false })
    } catch (e) {
      set({ error: String(e), loading: false })
    }
  },

  executeAction: async (actionId: string, params: Record<string, string>) => {
    set({ executing: actionId, error: null })
    try {
      const data = await fetchApi('/api/umh/actions/execute', {
        method: 'POST',
        body: JSON.stringify({ action_id: actionId, parameters: params }),
      })
      set({ executing: null })
      get().fetchHistory()
      return data as ActionResult
    } catch (e) {
      set({ executing: null, error: String(e) })
      return null
    }
  },

  approveAction: async (planId: string) => {
    try {
      const data = await fetchApi(`/api/umh/actions/${planId}/approve`, {
        method: 'POST',
      })
      get().fetchHistory()
      return data as ActionResult
    } catch (e) {
      set({ error: String(e) })
      return null
    }
  },

  fetchHistory: async (limit = 20) => {
    try {
      const data = await fetchApi(`/api/umh/actions/history?limit=${limit}`)
      set({ history: data.history ?? [] })
    } catch {
      // silent — history is non-critical
    }
  },
}))
