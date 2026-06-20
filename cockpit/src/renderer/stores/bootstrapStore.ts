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
  command_center_summary?: Record<string, unknown>
  approvals?: Array<Record<string, unknown>>
  mesh_nodes?: Array<Record<string, unknown>>
  workstation_nodes?: Record<string, unknown>
  vps_files?: { ok?: boolean; entries?: Array<{ name: string; path: string; type: string }> }
}

interface BootstrapState {
  loaded: boolean
  loading: boolean
  errors: string[]
  chatAvailable: boolean
  dexAvailable: boolean
  degraded: boolean
  cache: Partial<BootstrapResponse>

  boot: () => Promise<void>
}

export const useBootstrapStore = create<BootstrapState>((set) => ({
  loaded: false,
  loading: false,
  errors: [],
  chatAvailable: false,
  dexAvailable: false,
  degraded: false,
  cache: {},

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

      if (data.mesh_nodes && Array.isArray(data.mesh_nodes)) {
        useSystemStore.getState().setMeshNodes(data.mesh_nodes)
      }

      set({
        loaded: true,
        loading: false,
        chatAvailable: data.chat_available ?? false,
        dexAvailable: data.dex_available ?? false,
        errors: data._errors ?? [],
        degraded: (data._errors?.length ?? 0) > 0,
        cache: {
          command_center_summary: data.command_center_summary,
          approvals: data.approvals,
          mesh_nodes: data.mesh_nodes,
          workstation_nodes: data.workstation_nodes,
          vps_files: data.vps_files,
          mode_composite: data.mode_composite,
          continuity: data.continuity,
          overnight: data.overnight,
        },
      })
    } catch (err) {
      console.error('[bootstrap] failed:', err)
      set({ loaded: true, loading: false, degraded: true, errors: [String(err)] })
    }
  },
}))
