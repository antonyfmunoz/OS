import { create } from 'zustand'
import type { RouteId } from '../types/routes.ts'
import type { PresenceMode } from '../types/presence.ts'
import type { AwarenessTier, GlobalLayer } from '../types/awareness.ts'
import type { SystemPulse, ModelBadge, TraceEvent, ApprovalItem, InfraNode } from '../types/domain.ts'
import { MOCK_PULSE, MOCK_MODELS, MOCK_TRACES, MOCK_APPROVALS, MOCK_INFRA } from '../lib/mockData.ts'

interface CockpitState {
  route: RouteId
  railCollapsed: boolean
  presenceMode: PresenceMode
  wsConnected: boolean
  personaName: string

  awarenessTier: AwarenessTier
  globalLayers: Set<GlobalLayer>

  pulse: SystemPulse
  models: ModelBadge[]
  traces: TraceEvent[]
  approvals: ApprovalItem[]
  infraNodes: InfraNode[]

  setPersonaName: (name: string) => void
  setRoute: (route: RouteId) => void
  toggleRail: () => void
  setPresenceMode: (mode: PresenceMode) => void
  setWsConnected: (connected: boolean) => void

  setAwarenessTier: (tier: AwarenessTier) => void
  toggleGlobalLayer: (layer: GlobalLayer) => void

  setPulse: (pulse: SystemPulse) => void
  setModels: (models: ModelBadge[]) => void
  addTrace: (trace: TraceEvent) => void
  setApprovals: (approvals: ApprovalItem[]) => void
  updateApproval: (id: string, status: ApprovalItem['status']) => void
}

export const useCockpitStore = create<CockpitState>((set) => ({
  route: 'command-center',
  railCollapsed: false,
  presenceMode: 'full-screen',
  wsConnected: false,
  personaName: '',

  awarenessTier: 'global',
  globalLayers: new Set<GlobalLayer>(['news', 'markets', 'cyber']),

  pulse: MOCK_PULSE,
  models: MOCK_MODELS,
  traces: MOCK_TRACES,
  approvals: MOCK_APPROVALS,
  infraNodes: MOCK_INFRA,

  setPersonaName: (personaName) => set({ personaName }),
  setRoute: (route) => set({ route }),
  toggleRail: () => set((s) => ({ railCollapsed: !s.railCollapsed })),
  setPresenceMode: (presenceMode) => set({ presenceMode }),
  setWsConnected: (wsConnected) => set({ wsConnected }),

  setAwarenessTier: (awarenessTier) => set({ awarenessTier }),
  toggleGlobalLayer: (layer) =>
    set((s) => {
      const next = new Set(s.globalLayers)
      if (next.has(layer)) next.delete(layer)
      else next.add(layer)
      return { globalLayers: next }
    }),

  setPulse: (pulse) => set({ pulse }),
  setModels: (models) => set({ models }),
  addTrace: (trace) =>
    set((s) => ({ traces: [trace, ...s.traces].slice(0, 200) })),
  setApprovals: (approvals) => set({ approvals }),
  updateApproval: (id, status) =>
    set((s) => ({
      approvals: s.approvals.map((a) =>
        a.id === id ? { ...a, status } : a,
      ),
    })),
}))
