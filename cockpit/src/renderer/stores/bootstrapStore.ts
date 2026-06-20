import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { fetchApi } from '../api/client'
import { useConfigStore } from './configStore'
import { useSystemStore } from './systemStore'
import { useMetaIDEStore } from './metaIDEStore'

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
  windows_files?: { ok?: boolean; entries?: Array<{ name: string; path: string; type: string }> }
}

interface SlowBootstrapResponse {
  ok: boolean
  workstation_nodes?: Record<string, unknown>
  vps_files?: { ok?: boolean; entries?: Array<{ name: string; path: string; type: string }> }
  windows_files?: { ok?: boolean; entries?: Array<{ name: string; path: string; type: string }> }
  _errors?: string[]
}

interface BootstrapState {
  loaded: boolean
  loading: boolean
  slowLoading: boolean
  errors: string[]
  chatAvailable: boolean
  dexAvailable: boolean
  degraded: boolean
  cache: Partial<BootstrapResponse>

  boot: () => Promise<void>
  bootSlow: () => Promise<void>
}

function seedDownstreamStores(cache: Partial<BootstrapResponse>) {
  if (cache.mesh_nodes && Array.isArray(cache.mesh_nodes)) {
    useSystemStore.getState().setMeshNodes(cache.mesh_nodes)
    useMetaIDEStore.getState().setFileMeshNodes(cache.mesh_nodes.map((n) => ({
      id: (n.id ?? '') as string,
      name: (n.name ?? '') as string,
      os: (n.os ?? '') as string,
      status: (n.status ?? 'offline') as string,
      ip: (n.ip ?? '') as string,
      device_type: (n.device_type ?? '') as string,
    })))
  }
  if (cache.vps_files?.ok && cache.vps_files.entries?.length) {
    useMetaIDEStore.getState().setVpsTree(
      cache.vps_files.entries.map((e) => ({ name: e.name, path: e.path, type: e.type as 'file' | 'directory' })),
    )
  }
  if (cache.windows_files?.ok && cache.windows_files.entries?.length) {
    useMetaIDEStore.getState().setWindowsTree(
      cache.windows_files.entries.map((e) => ({ name: e.name, path: e.path, type: e.type as 'file' | 'directory' })),
    )
  }
}

export const useBootstrapStore = create<BootstrapState>()(
  persist(
    (set, get) => ({
      loaded: false,
      loading: false,
      slowLoading: false,
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

          const newCache = {
            command_center_summary: data.command_center_summary,
            approvals: data.approvals,
            mesh_nodes: data.mesh_nodes,
            workstation_nodes: data.workstation_nodes,
            vps_files: get().cache.vps_files,
            windows_files: get().cache.windows_files,
            mode_composite: data.mode_composite,
            continuity: data.continuity,
            overnight: data.overnight,
          }

          seedDownstreamStores(newCache)

          set({
            loaded: true,
            loading: false,
            chatAvailable: data.chat_available ?? false,
            dexAvailable: data.dex_available ?? false,
            errors: data._errors ?? [],
            degraded: (data._errors?.length ?? 0) > 0,
            cache: newCache,
          })
        } catch (err) {
          console.error('[bootstrap] failed:', err)
          set({ loaded: true, loading: false, degraded: true, errors: [String(err)] })
        }
      },

      bootSlow: async () => {
        set({ slowLoading: true })
        try {
          const data = await fetchApi<SlowBootstrapResponse>('/bootstrap/slow')
          const prev = get().cache

          if (data.vps_files?.ok && data.vps_files.entries?.length) {
            useMetaIDEStore.getState().setVpsTree(
              data.vps_files.entries.map((e) => ({ name: e.name, path: e.path, type: e.type as 'file' | 'directory' })),
            )
          }
          if (data.windows_files?.ok && data.windows_files.entries?.length) {
            useMetaIDEStore.getState().setWindowsTree(
              data.windows_files.entries.map((e) => ({ name: e.name, path: e.path, type: e.type as 'file' | 'directory' })),
            )
          }
          if (data.workstation_nodes) {
            const nodes = (data.workstation_nodes as Record<string, unknown>).nodes as Array<Record<string, unknown>> | undefined
            if (nodes && Array.isArray(nodes)) {
              useSystemStore.getState().setMeshNodes(nodes)
            }
          }

          set({
            slowLoading: false,
            cache: {
              ...prev,
              vps_files: data.vps_files ?? prev.vps_files,
              windows_files: data.windows_files ?? prev.windows_files,
              workstation_nodes: data.workstation_nodes ?? prev.workstation_nodes,
            },
          })
        } catch (err) {
          console.error('[bootstrap:slow] failed:', err)
          set({ slowLoading: false })
        }
      },
    }),
    {
      name: 'cockpit:bootstrap-cache',
      partialize: (state) => ({ cache: state.cache }),
      onRehydrateStorage: () => (state) => {
        if (state?.cache && Object.keys(state.cache).length > 0) {
          seedDownstreamStores(state.cache)
        }
      },
    },
  ),
)
