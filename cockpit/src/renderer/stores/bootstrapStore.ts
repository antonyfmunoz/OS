import { create } from 'zustand'
import { fetchApi } from '../api/client'
import { useConfigStore } from './configStore'
import { useSystemStore } from './systemStore'

interface BootstrapResponse {
  ok: boolean
  ts: string
  config: Record<string, unknown>
  pulse: Record<string, unknown>
  organism: { running: boolean; agent_count?: number; workcell_count?: number }
  mode_composite: Record<string, unknown>
  continuity: Record<string, unknown>
  command_center: Record<string, unknown>
  overnight: Record<string, unknown>
  mesh: { node_count: number }
  dex_available: boolean
  chat_available: boolean
  _errors: string[]
}

interface BootstrapState {
  loaded: boolean
  loading: boolean
  errors: string[]
  chatAvailable: boolean
  dexAvailable: boolean
  degraded: boolean

  boot: () => Promise<void>
}

export const useBootstrapStore = create<BootstrapState>((set) => ({
  loaded: false,
  loading: false,
  errors: [],
  chatAvailable: false,
  dexAvailable: false,
  degraded: false,

  boot: async () => {
    set({ loading: true })
    try {
      const data = await fetchApi<BootstrapResponse>('/bootstrap')

      if (data.config && Object.keys(data.config).length > 0) {
        const aiName = (data.config.ai_name as string) || import.meta.env.VITE_AI_NAME || 'Assistant'
        useConfigStore.setState({
          config: { ai_name: aiName, timezone: 'UTC', locale: 'en', theme: 'dark', founder_name: '', org_name: '', ...data.config },
          loaded: true,
          aiName,
        })
      }

      if (data.pulse && Object.keys(data.pulse).length > 0) {
        useSystemStore.getState().setPulse({
          cpu_percent: (data.pulse.cpu_percent as number) || 0,
          memory_percent: (data.pulse.memory_percent as number) || 0,
          disk_percent: (data.pulse.disk_percent as number) || 0,
          uptime: (data.pulse.uptime as number) || 0,
          active_agents: (data.pulse.active_agents as number) || 0,
          pending_tasks: (data.pulse.pending_tasks as number) || 0,
          pending_approvals: (data.pulse.pending_approvals as number) || 0,
          trace_rate: (data.pulse.trace_rate as number) || 0,
        })
      }

      set({
        loaded: true,
        loading: false,
        chatAvailable: data.chat_available ?? false,
        dexAvailable: data.dex_available ?? false,
        errors: data._errors ?? [],
        degraded: (data._errors?.length ?? 0) > 0,
      })
    } catch (err) {
      console.error('[bootstrap] failed:', err)
      set({ loaded: true, loading: false, degraded: true, errors: [String(err)] })
    }
  },
}))
