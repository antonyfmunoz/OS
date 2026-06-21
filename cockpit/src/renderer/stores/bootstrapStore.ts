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
  hydrated: boolean
  errors: string[]
  chatAvailable: boolean
  dexAvailable: boolean
  degraded: boolean
  cache: Partial<BootstrapResponse>

  boot: () => Promise<void>
  bootSlow: () => Promise<void>
}

function seedDownstreamStores(cache: Partial<BootstrapResponse>) {
  if (cache.config && Object.keys(cache.config).length > 0) {
    const aiName = (cache.config.ai_name as string) || import.meta.env.VITE_AI_NAME || 'Assistant'
    useConfigStore.setState({
      config: { ai_name: aiName, timezone: 'UTC', locale: 'en', theme: 'dark', founder_name: '', org_name: '', ...cache.config },
      loaded: true,
      aiName,
    })
  }
  if (cache.pulse && Object.keys(cache.pulse).length > 0) {
    useSystemStore.getState().setPulse({
      cpu_percent: (cache.pulse.cpu_percent as number) || 0,
      memory_percent: (cache.pulse.memory_percent as number) || 0,
      disk_percent: (cache.pulse.disk_percent as number) || 0,
      uptime: (cache.pulse.uptime as number) || 0,
      active_agents: (cache.pulse.active_agents as number) || 0,
      pending_tasks: (cache.pulse.pending_tasks as number) || 0,
      pending_approvals: (cache.pulse.pending_approvals as number) || 0,
      trace_rate: (cache.pulse.trace_rate as number) || 0,
    })
  }
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
  if (cache.vps_files?.entries?.length) {
    useMetaIDEStore.getState().setVpsTree(
      cache.vps_files.entries.map((e) => ({ name: e.name, path: e.path, type: e.type as 'file' | 'directory' })),
    )
  }
  if (cache.windows_files?.entries?.length) {
    useMetaIDEStore.getState().setWindowsTree(
      cache.windows_files.entries.map((e) => ({ name: e.name, path: e.path, type: e.type as 'file' | 'directory' })),
    )
  }
}

export function waitForHydration(): Promise<void> {
  if (useBootstrapStore.getState().hydrated) return Promise.resolve()
  return new Promise((resolve) => {
    const unsub = useBootstrapStore.subscribe((s) => {
      if (s.hydrated) { unsub(); resolve() }
    })
  })
}

export const useBootstrapStore = create<BootstrapState>()(
  persist(
    (set, get) => ({
      loaded: false,
      loading: false,
      slowLoading: false,
      hydrated: false,
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

          const mergedCache = {
            ...get().cache,
            config: data.config,
            pulse: data.pulse,
            command_center_summary: data.command_center_summary,
            approvals: data.approvals,
            mesh_nodes: data.mesh_nodes,
            workstation_nodes: data.workstation_nodes,
            mode_composite: data.mode_composite,
            continuity: data.continuity,
            overnight: data.overnight,
          }

          seedDownstreamStores(mergedCache)

          set({
            loaded: true,
            loading: false,
            chatAvailable: data.chat_available ?? false,
            dexAvailable: data.dex_available ?? false,
            errors: data._errors ?? [],
            degraded: (data._errors?.length ?? 0) > 0,
            cache: mergedCache,
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

          if (data.vps_files?.entries?.length) {
            useMetaIDEStore.getState().setVpsTree(
              data.vps_files.entries.map((e) => ({ name: e.name, path: e.path, type: e.type as 'file' | 'directory' })),
            )
          }
          if (data.windows_files?.entries?.length) {
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

          set((prev) => ({
            slowLoading: false,
            cache: {
              ...prev.cache,
              ...(data.vps_files?.entries?.length ? { vps_files: data.vps_files } : {}),
              ...(data.windows_files?.entries?.length ? { windows_files: data.windows_files } : {}),
              ...(data.workstation_nodes ? { workstation_nodes: data.workstation_nodes } : {}),
            },
          }))
        } catch (err) {
          console.error('[bootstrap:slow] failed:', err)
          set({ slowLoading: false })
        }
      },
    }),
    {
      name: 'cockpit:bootstrap-cache',
      partialize: (state) => ({ cache: state.cache }),
      onRehydrateStorage: () => (state, error) => {
        if (!error && state?.cache && Object.keys(state.cache).length > 0) {
          seedDownstreamStores(state.cache)
          useBootstrapStore.setState({ loaded: true, hydrated: true })
        } else {
          useBootstrapStore.setState({ hydrated: true })
        }
      },
    },
  ),
)
