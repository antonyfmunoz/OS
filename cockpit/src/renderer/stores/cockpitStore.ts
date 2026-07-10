import { create } from 'zustand'
import { persist } from 'zustand/middleware'

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
  | 'skills'
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
  | 'browser'
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
  | 'capabilities'
  | 'workintelligence'
  | 'learning'
  | 'prediction'
  | 'executive'
  | 'governance'
  | 'operations'
  | 'actions'
  | 'distributedruntime'
  | 'operatorcontinuity'
  | 'operatorhome'
  | 'screenawareness'
  | 'servicegraph'
  | 'stateauthority'
  | 'umhnode'
  | 'workspacetopology'
  | 'canvas'
  | 'proofinspector'
  | 'recoverydashboard'
  | 'projectionmirrors'
  | 'intentloop'

export type WindowMode = 'maximized' | 'large-fab' | 'medium-fab' | 'small-fab' | 'invisible'

export type ConnectionStatus = 'connected' | 'connecting' | 'disconnected'

export type RightPanelView = 'chat' | 'context' | 'execution'

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
  leftDrawerOpen: boolean
  rightDrawerOpen: boolean
  rightPanelView: RightPanelView
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
  toggleLeftDrawer: () => void
  toggleRightDrawer: () => void
  setRightPanelView: (view: RightPanelView) => void
  setApiStatus: (status: ConnectionStatus) => void
  setWsStatus: (status: ConnectionStatus) => void
  setVoiceStatus: (status: ConnectionStatus) => void
  setConnectionStatus: (channel: 'api' | 'ws' | 'voice', status: ConnectionStatus) => void
}

export const useCockpitStore = create<CockpitState>()(
  persist(
    (set) => ({
      activePanel: 'commandcenter' as Panel,
      chatOpen: false,
      splitPanel: null,
      mode: 'EXECUTE' as const,
      windowMode: 'maximized' as WindowMode,
      railCollapsed: true,
      rightRailCollapsed: true,
      controlPanelExpanded: false,
      leftDrawerOpen: false,
      rightDrawerOpen: false,
      rightPanelView: 'chat' as RightPanelView,
      apiStatus: 'disconnected' as ConnectionStatus,
      wsStatus: 'disconnected' as ConnectionStatus,
      voiceStatus: 'disconnected' as ConnectionStatus,

      setPanel: (panel) => {
        const redirects: Partial<Record<Panel, Panel>> = {
          dashboard: 'commandcenter',
          tasks: 'work',
          universalwork: 'work',
          runtime: 'execution',
          skills: 'knowledge',
          infrastructure: 'organismmap',
          agents: 'canvas',
          workflows: 'canvas',
        }
        const modeMap: Partial<Record<Panel, string>> = {
          agents: 'agents',
          workflows: 'workflows',
        }
        if (modeMap[panel]) {
          import('./unifiedCanvasStore').then(({ useUnifiedCanvasStore }) => {
            useUnifiedCanvasStore.getState().setMode(modeMap[panel] as 'agents' | 'workflows')
          })
        }
        const resolved = redirects[panel] ?? panel
        set({ activePanel: resolved })
        // Keep the assistant's view-context in sync with the ACTUAL active panel.
        // Previously only ~3 panels set active_route themselves, so the chat rail's
        // "Viewing:" label (and the context the assistant receives) was stale on
        // every other panel. Sync it centrally here — one source of truth — and
        // clear any stale per-panel object selection on navigation.
        import('./viewContextStore').then(({ useViewContextStore }) => {
          useViewContextStore.getState().setRoute(resolved)
        })
      },
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
      toggleLeftDrawer: () => set((s) => ({ leftDrawerOpen: !s.leftDrawerOpen })),
      toggleRightDrawer: () => set((s) => ({ rightDrawerOpen: !s.rightDrawerOpen })),
      setRightPanelView: (view) => set({ rightPanelView: view, rightDrawerOpen: true }),
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
    }),
    {
      name: 'cockpit:shell',
      partialize: (state) => ({
        activePanel: state.activePanel,
        railCollapsed: state.railCollapsed,
        rightRailCollapsed: state.rightRailCollapsed,
        leftDrawerOpen: state.leftDrawerOpen,
        rightDrawerOpen: state.rightDrawerOpen,
        rightPanelView: state.rightPanelView,
      }),
    },
  ),
)
