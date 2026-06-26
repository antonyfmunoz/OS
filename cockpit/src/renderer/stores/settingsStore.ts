import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface ModelRoute {
  provider: string
  model_id?: string
  priority: number
  quality?: number
  enabled: boolean
  available?: boolean
  role?: string
  status?: string
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
  purpose_routing?: Record<string, string[]>
  role_slots?: Record<string, string>
  role_failover?: Record<string, string>
  provider_keys?: string[]
  persistence_status?: string
  governance: { auto_approve_low: boolean; critical_block: boolean }
}

interface MutationResponse {
  ok: boolean
  warnings: string[]
  audit: Record<string, unknown> | null
  applied_state: Record<string, unknown> | null
  requires_approval?: boolean
  approval_reason?: string
}

interface GovernanceMutationResponse {
  ok: boolean
  applied: Array<{ risk_class: string; authority: string; applied_state?: Record<string, unknown> }>
  warnings: string[]
  errors: string[]
  audits: Array<Record<string, unknown>>
}

interface SettingsState {
  settings: SettingsData | null
  settingsError: string | null
  governance: GovernanceData | null
  governanceError: string | null
  fetchSettings: () => Promise<void>
  fetchGovernance: () => Promise<void>
  patchSettings: (patch: Record<string, unknown>) => Promise<void>
  patchGovernance: (policies: Record<string, string>) => Promise<GovernanceMutationResponse | null>
  toggleProvider: (key: string, enabled: boolean) => Promise<MutationResponse | null>
  setPurposeChain: (purpose: string, roles: string[]) => Promise<MutationResponse | null>
  setRoleSlot: (role: string, key: string) => Promise<MutationResponse | null>
}

export const useSettingsStore = create<SettingsState>((set, get) => ({
  settings: null,
  settingsError: null,
  governance: null,
  governanceError: null,

  fetchSettings: async () => {
    try {
      const data = await fetchApi<SettingsData>('/settings')
      set({ settings: data, settingsError: null })
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Unknown error'
      set({ settingsError: msg })
    }
  },

  fetchGovernance: async () => {
    try {
      const data = await fetchApi<GovernanceData>('/governance')
      if (data && Array.isArray(data.policies)) {
        set({ governance: data, governanceError: null })
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Unknown error'
      set({ governanceError: msg })
    }
  },

  patchSettings: async (patch) => {
    try {
      await fetchApi('/settings', { method: 'PATCH', body: JSON.stringify(patch) })
      await get().fetchSettings()
    } catch { /* handled by refetch */ }
  },

  patchGovernance: async (policies) => {
    try {
      const resp = await fetchApi<GovernanceMutationResponse>('/governance', {
        method: 'PATCH',
        body: JSON.stringify({ policies }),
      })
      await get().fetchGovernance()
      return resp
    } catch {
      return null
    }
  },

  toggleProvider: async (key, enabled) => {
    try {
      const resp = await fetchApi<MutationResponse>('/settings', {
        method: 'PATCH',
        body: JSON.stringify({ action: 'toggle_provider', provider_key: key, enabled }),
      })
      await get().fetchSettings()
      return resp
    } catch {
      return null
    }
  },

  setPurposeChain: async (purpose, roles) => {
    try {
      const resp = await fetchApi<MutationResponse>('/settings', {
        method: 'PATCH',
        body: JSON.stringify({ action: 'set_purpose_chain', purpose, roles }),
      })
      await get().fetchSettings()
      return resp
    } catch {
      return null
    }
  },

  setRoleSlot: async (role, key) => {
    try {
      const resp = await fetchApi<MutationResponse>('/settings', {
        method: 'PATCH',
        body: JSON.stringify({ action: 'set_role_slot', role, provider_key: key }),
      })
      await get().fetchSettings()
      return resp
    } catch {
      return null
    }
  },
}))
