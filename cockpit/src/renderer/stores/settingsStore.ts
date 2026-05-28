import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface ModelRoute {
  provider: string
  priority: number
  enabled: boolean
}

interface GovernancePolicy {
  risk_class: string
  risk_level: string
  authority: string
  requires_human: boolean
  is_blocked: boolean
  is_blocking_class: boolean
}

interface GovernanceData {
  policies: GovernancePolicy[]
  safe_roots: string[]
  allowed_shell_prefixes: string[]
}

interface SettingsData {
  model_routing: ModelRoute[]
  governance: { auto_approve_low: boolean; critical_block: boolean }
  notifications: { discord: boolean; file: boolean }
}

interface SettingsState {
  settings: SettingsData | null
  governance: GovernanceData | null
  fetchSettings: () => Promise<void>
  fetchGovernance: () => Promise<void>
  patchSettings: (patch: Record<string, unknown>) => Promise<void>
  patchGovernance: (policies: Record<string, string>) => Promise<void>
}

export const useSettingsStore = create<SettingsState>((set) => ({
  settings: null,
  governance: null,

  fetchSettings: async () => {
    try {
      const data = await fetchApi<SettingsData>('/settings')
      set({ settings: data })
    } catch { /* store stays stale */ }
  },

  fetchGovernance: async () => {
    try {
      const data = await fetchApi<GovernanceData>('/governance')
      if (data && Array.isArray(data.policies)) {
        set({ governance: data })
      }
    } catch { /* store stays stale */ }
  },

  patchSettings: async (patch) => {
    try {
      await fetchApi('/settings', { method: 'PATCH', body: JSON.stringify(patch) })
      const data = await fetchApi<SettingsData>('/settings')
      set({ settings: data })
    } catch { /* surface error in UI later */ }
  },

  patchGovernance: async (policies) => {
    try {
      await fetchApi('/governance', { method: 'PATCH', body: JSON.stringify({ policies }) })
      const data = await fetchApi<GovernanceData>('/governance')
      set({ governance: data })
    } catch { /* surface error in UI later */ }
  },
}))
