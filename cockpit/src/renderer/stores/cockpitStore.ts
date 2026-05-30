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

export const useCockpitStore = create<CockpitState>((set) => ({
  activePanel: 'dashboard',
  chatOpen: false,
  splitPanel: null,
  mode: 'EXECUTE',
  windowMode: 'maximized',
  railCollapsed: false,
  rightRailCollapsed: false,
  controlPanelExpanded: false,
  apiStatus: 'disconnected',
  wsStatus: 'disconnected',
  voiceStatus: 'disconnected',

  setPanel: (panel) => set({ activePanel: panel }),
  toggleChat: () => set((s) => ({ chatOpen: !s.chatOpen })),
  setChatOpen: (open) => set({ chatOpen: open }),
  setSplitPanel: (panel) => set({ splitPanel: panel }),
  setMode: (mode) => set({ mode }),
  setWindowMode: (windowMode) => {
    set({ windowMode })
    window.cockpit?.window?.setMode?.(windowMode)
  },
  toggleRail: () => set((s) => ({ railCollapsed: !s.railCollapsed })),
  toggleRightRail: () => set((s) => ({ rightRailCollapsed: !s.rightRailCollapsed })),
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
