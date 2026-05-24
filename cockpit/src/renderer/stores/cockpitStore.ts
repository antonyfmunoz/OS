import { create } from 'zustand'

export type Panel =
  | 'dashboard'
  | 'agents'
  | 'tasks'
  | 'approvals'
  | 'knowledge'
  | 'analytics'
  | 'editor'
  | 'settings'
  | 'activity'

export type ConnectionStatus = 'connected' | 'connecting' | 'disconnected'

interface CockpitState {
  activePanel: Panel
  chatOpen: boolean
  splitPanel: Panel | null
  mode: 'EXECUTE' | 'PLAN' | 'REVIEW'
  apiStatus: ConnectionStatus
  wsStatus: ConnectionStatus
  voiceStatus: ConnectionStatus

  setPanel: (panel: Panel) => void
  toggleChat: () => void
  setChatOpen: (open: boolean) => void
  setSplitPanel: (panel: Panel | null) => void
  setMode: (mode: 'EXECUTE' | 'PLAN' | 'REVIEW') => void
  setApiStatus: (status: ConnectionStatus) => void
  setWsStatus: (status: ConnectionStatus) => void
  setVoiceStatus: (status: ConnectionStatus) => void
}

export const useCockpitStore = create<CockpitState>((set) => ({
  activePanel: 'dashboard',
  chatOpen: false,
  splitPanel: null,
  mode: 'EXECUTE',
  apiStatus: 'disconnected',
  wsStatus: 'disconnected',
  voiceStatus: 'disconnected',

  setPanel: (panel) => set({ activePanel: panel }),
  toggleChat: () => set((s) => ({ chatOpen: !s.chatOpen })),
  setChatOpen: (open) => set({ chatOpen: open }),
  setSplitPanel: (panel) => set({ splitPanel: panel }),
  setMode: (mode) => set({ mode }),
  setApiStatus: (status) => set({ apiStatus: status }),
  setWsStatus: (status) => set({ wsStatus: status }),
  setVoiceStatus: (status) => set({ voiceStatus: status }),
}))
