import { create } from 'zustand'

export type Panel =
  | 'dashboard'
  | 'portfolio'
  | 'company'
  | 'agents'
  | 'tasks'
  | 'approvals'
  | 'knowledge'
  | 'analytics'
  | 'editor'
  | 'settings'
  | 'activity'
  | 'execution'
  | 'comms'
  | 'workflows'
  | 'tracking'
  | 'skills'
  | 'experiments'
  | 'infrastructure'
  | 'profile'
  | 'organism'
  | 'intelligence'
  | 'worldmodel'
  | 'selfbuild'
  | 'universalwork'
  | 'propagation'
  | 'operator'
  | 'runtime'
  | 'tmux'
  | 'workspace'
  | 'commandcenter'
  | 'work'
  | 'vision'
  | 'rooms'
  | 'broadcast'
  | 'strategy'
  | 'tickloop'
  | 'projections'
  | 'continuity'
  | 'presence'
  | 'commands'
  | 'workstation'
  | 'sessions'
  | 'execcoord'
  | 'executor'
  | 'organismloop'
  | 'operatortimeline'
  | 'realitytimeline'
  | 'realityintelligence'
  | 'metaide'
  | 'engineering'
  | 'organismmap'
  | 'intent'
  | 'capabilitymap'
  | 'unifiedexecution'
  | 'buildloop'
  | 'projectionintegration'
  | 'orchestratorawareness'
  | 'operatingloopview'
  | 'sessionresume'
  | 'mvpreadiness'
  | 'delegation'
  | 'strategic'
  | 'goals'
  | 'realitygraph'
  | 'memory'

export type WindowMode = 'maximized' | 'large-fab' | 'medium-fab' | 'small-fab' | 'invisible'

export type ConnectionStatus = 'connected' | 'connecting' | 'disconnected'

const WINDOW_MODE_ORDER: WindowMode[] = ['maximized', 'large-fab', 'medium-fab', 'small-fab', 'invisible']

interface CockpitState {
  activePanel: Panel
  chatOpen: boolean
  splitPanel: Panel | null
  mode: 'EXECUTE' | 'PLAN' | 'REVIEW'
  windowMode: WindowMode
  railCollapsed: boolean
  rightRailCollapsed: boolean
  controlPanelExpanded: boolean
  apiStatus: ConnectionStatus
  wsStatus: ConnectionStatus
  voiceStatus: ConnectionStatus

  setPanel: (panel: Panel) => void
  toggleChat: () => void
  setChatOpen: (open: boolean) => void
  setSplitPanel: (panel: Panel | null) => void
  setMode: (mode: 'EXECUTE' | 'PLAN' | 'REVIEW') => void
  setWindowMode: (mode: WindowMode) => void
  cycleWindowMode: (direction: 'shrink' | 'expand') => void
  toggleRail: () => void
  toggleRightRail: () => void
  toggleControlPanel: () => void
  setApiStatus: (status: ConnectionStatus) => void
  setWsStatus: (status: ConnectionStatus) => void
  setVoiceStatus: (status: ConnectionStatus) => void
  setConnectionStatus: (channel: 'api' | 'ws' | 'voice', status: ConnectionStatus) => void
}

const RAIL_STORAGE_KEY = 'cockpit:railCollapsed'
const RIGHT_RAIL_STORAGE_KEY = 'cockpit:rightRailCollapsed'

function loadBool(key: string, fallback: boolean): boolean {
  try {
    const v = localStorage.getItem(key)
    if (v === null) return fallback
    return v === 'true'
  } catch { return fallback }
}

export const useCockpitStore = create<CockpitState>((set) => ({
  activePanel: 'commandcenter',
  chatOpen: false,
  splitPanel: null,
  mode: 'EXECUTE',
  windowMode: 'maximized',
  railCollapsed: loadBool(RAIL_STORAGE_KEY, true),
  rightRailCollapsed: loadBool(RIGHT_RAIL_STORAGE_KEY, true),
  controlPanelExpanded: false,
  apiStatus: 'disconnected',
  wsStatus: 'disconnected',
  voiceStatus: 'disconnected',

  setPanel: (panel) => {
    const redirects: Partial<Record<Panel, Panel>> = {
      dashboard: 'commandcenter',
      tasks: 'work',
      workflows: 'work',
      universalwork: 'work',
      runtime: 'execution',
      skills: 'knowledge',
      workspace: 'editor',
      infrastructure: 'organismmap',
    }
    set({ activePanel: redirects[panel] ?? panel })
  },
  toggleChat: () => set((s) => ({ chatOpen: !s.chatOpen })),
  setChatOpen: (open) => set({ chatOpen: open }),
  setSplitPanel: (panel) => set({ splitPanel: panel }),
  setMode: (mode) => set({ mode }),
  setWindowMode: (windowMode) => {
    set({ windowMode })
    window.cockpit?.window?.setMode?.(windowMode)
  },
  toggleRail: () => set((s) => {
    const next = !s.railCollapsed
    try { localStorage.setItem(RAIL_STORAGE_KEY, String(next)) } catch {}
    return { railCollapsed: next }
  }),
  toggleRightRail: () => set((s) => {
    const next = !s.rightRailCollapsed
    try { localStorage.setItem(RIGHT_RAIL_STORAGE_KEY, String(next)) } catch {}
    return { rightRailCollapsed: next }
  }),
  toggleControlPanel: () => set((s) => ({ controlPanelExpanded: !s.controlPanelExpanded })),
  cycleWindowMode: (direction) =>
    set((s) => {
      const idx = WINDOW_MODE_ORDER.indexOf(s.windowMode)
      const next = direction === 'shrink'
        ? Math.min(idx + 1, WINDOW_MODE_ORDER.length - 1)
        : Math.max(idx - 1, 0)
      const windowMode = WINDOW_MODE_ORDER[next]
      window.cockpit?.window?.setMode?.(windowMode)
      return { windowMode }
    }),
  setApiStatus: (status) => set({ apiStatus: status }),
  setWsStatus: (status) => set({ wsStatus: status }),
  setVoiceStatus: (status) => set({ voiceStatus: status }),
  setConnectionStatus: (channel, status) => {
    if (channel === 'api') set({ apiStatus: status })
    else if (channel === 'ws') set({ wsStatus: status })
    else if (channel === 'voice') set({ voiceStatus: status })
  },
}))
