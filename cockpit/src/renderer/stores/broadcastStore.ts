import { create } from 'zustand'

export type BroadcastState = 'idle' | 'starting' | 'live' | 'stopping' | 'error'
export type StatusTier = 'HEALTHY' | 'WARNING' | 'CRITICAL'

export interface BroadcastHealthMetrics {
  frame: number
  fps: number
  bitrate_kbps: number
  drop_frames: number
  out_time_ms: number
  speed: string
  total_size_bytes: number
  uptime_s: number
  drop_percentage: number
  status_tier: StatusTier
}

const INITIAL_HEALTH: BroadcastHealthMetrics = {
  frame: 0,
  fps: 0,
  bitrate_kbps: 0,
  drop_frames: 0,
  out_time_ms: 0,
  speed: '0x',
  total_size_bytes: 0,
  uptime_s: 0,
  drop_percentage: 0,
  status_tier: 'HEALTHY',
}

export interface SceneInfo {
  scene_id: string
  name: string
}

export interface SourceInfo {
  source_id: string
  source_type: string
}

export interface NodeInfo {
  node_id: string
  hostname?: string
  os?: string
  status: string
  local: boolean
}

export interface BroadcastStoreState {
  connected: boolean
  broadcastState: BroadcastState
  health: BroadcastHealthMetrics
  pid: number | null
  config: Record<string, unknown> | null
  error: string | null
  composite: boolean
  activeSceneId: string | null
  scenes: SceneInfo[]
  sources: SourceInfo[]
  activeNode: string
  availableNodes: NodeInfo[]

  setConnected: (v: boolean) => void
  setBroadcastState: (v: BroadcastState) => void
  setHealth: (v: BroadcastHealthMetrics) => void
  setPid: (v: number | null) => void
  setConfig: (v: Record<string, unknown> | null) => void
  setError: (v: string | null) => void
  setComposite: (v: boolean) => void
  setActiveSceneId: (v: string | null) => void
  setScenes: (v: SceneInfo[]) => void
  setSources: (v: SourceInfo[]) => void
  setActiveNode: (v: string) => void
  setAvailableNodes: (v: NodeInfo[]) => void
  reset: () => void
}

export const useBroadcastStore = create<BroadcastStoreState>((set) => ({
  connected: false,
  broadcastState: 'idle',
  health: { ...INITIAL_HEALTH },
  pid: null,
  config: null,
  error: null,
  composite: false,
  activeSceneId: null,
  scenes: [],
  sources: [],
  activeNode: 'local',
  availableNodes: [],

  setConnected: (connected) => set({ connected }),
  setBroadcastState: (broadcastState) => set({ broadcastState }),
  setHealth: (health) => set({ health }),
  setPid: (pid) => set({ pid }),
  setConfig: (config) => set({ config }),
  setError: (error) => set({ error }),
  setComposite: (composite) => set({ composite }),
  setActiveSceneId: (activeSceneId) => set({ activeSceneId }),
  setScenes: (scenes) => set({ scenes }),
  setSources: (sources) => set({ sources }),
  setActiveNode: (activeNode) => set({ activeNode }),
  setAvailableNodes: (availableNodes) => set({ availableNodes }),
  reset: () =>
    set({
      connected: false,
      broadcastState: 'idle',
      health: { ...INITIAL_HEALTH },
      pid: null,
      config: null,
      error: null,
      composite: false,
      activeSceneId: null,
      scenes: [],
      sources: [],
      activeNode: 'local',
      availableNodes: [],
    }),
}))
