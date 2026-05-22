import { create } from 'zustand'
import type { RouteId } from '../types/routes.ts'
import type { PresenceMode } from '../types/presence.ts'
import type { AwarenessTier, GlobalLayer } from '../types/awareness.ts'
import type { SystemPulse, ModelBadge, TraceEvent, ApprovalItem, InfraNode } from '../types/domain.ts'
import {
  api,
  type AgentResponse,
  type MemoryEntryResponse,
  type SkillResponse,
  type ObservationResponse,
  type WorkflowResponse,
  type TaskResponse,
  type CommsMessage,
  type TrackingEntity,
  type AnalyticsSnapshot,
  type SettingsResponse,
  type ProfileResponse,
} from '../api/client.ts'

interface CockpitState {
  route: RouteId
  railCollapsed: boolean
  presenceMode: PresenceMode
  wsConnected: boolean
  personaName: string
  loading: boolean
  error: string | null

  awarenessTier: AwarenessTier
  globalLayers: Set<GlobalLayer>

  pulse: SystemPulse
  models: ModelBadge[]
  traces: TraceEvent[]
  approvals: ApprovalItem[]
  infraNodes: InfraNode[]
  agents: AgentResponse[]
  memory: MemoryEntryResponse[]
  skills: SkillResponse[]
  observations: ObservationResponse[]
  workflows: WorkflowResponse[]
  tasks: TaskResponse[]
  comms: CommsMessage[]
  tracking: TrackingEntity[]
  analytics: AnalyticsSnapshot | null
  settings: SettingsResponse | null
  profile: ProfileResponse | null

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

  fetchAll: () => Promise<void>
}

const EMPTY_PULSE: SystemPulse = {
  uptime: 0,
  cpuPercent: 0,
  memoryPercent: 0,
  activeAgents: 0,
  pendingTasks: 0,
  pendingApprovals: 0,
  traceRate: 0,
  wsConnected: false,
}

export const useCockpitStore = create<CockpitState>((set, get) => ({
  route: 'command-center',
  railCollapsed: false,
  presenceMode: 'full-screen',
  wsConnected: false,
  personaName: '',
  loading: true,
  error: null,

  awarenessTier: 'global',
  globalLayers: new Set<GlobalLayer>(['news', 'markets', 'cyber']),

  pulse: EMPTY_PULSE,
  models: [],
  traces: [],
  approvals: [],
  infraNodes: [],
  agents: [],
  memory: [],
  skills: [],
  observations: [],
  workflows: [],
  tasks: [],
  comms: [],
  tracking: [],
  analytics: null,
  settings: null,
  profile: null,

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

  fetchAll: async () => {
    set({ loading: true, error: null })
    try {
      const [
        pulseRes,
        modelsRes,
        infraRes,
        approvalsRes,
        agentsRes,
        memoryRes,
        skillsRes,
        obsRes,
        workflowsRes,
        tasksRes,
        commsRes,
        trackingRes,
        analyticsRes,
        settingsRes,
        profileRes,
      ] = await Promise.allSettled([
        api.pulse(),
        api.models(),
        api.infra(),
        api.approvals(),
        api.agents(),
        api.memory(),
        api.skills(),
        api.observations(),
        api.workflows(),
        api.tasks(),
        api.comms(100),
        api.tracking(),
        api.analytics(),
        api.settings(),
        api.profile(),
      ])

      const unwrap = <T>(r: PromiseSettledResult<T>, fallback: T): T =>
        r.status === 'fulfilled' ? r.value : fallback

      const pulse = unwrap(pulseRes, null)
      const mappedPulse: SystemPulse = pulse
        ? {
            uptime: pulse.uptime,
            cpuPercent: pulse.cpu_percent,
            memoryPercent: pulse.memory_percent,
            activeAgents: pulse.active_agents,
            pendingTasks: pulse.pending_tasks,
            pendingApprovals: pulse.pending_approvals,
            traceRate: pulse.trace_rate,
            wsConnected: get().wsConnected,
          }
        : EMPTY_PULSE

      const models = unwrap(modelsRes, [] as typeof modelsRes extends PromiseSettledResult<infer T> ? T : never)
      const mappedModels: ModelBadge[] = (models || []).map((m) => ({
        id: m.id,
        name: m.name,
        provider: m.provider,
        status: m.status,
        latencyMs: m.latency_ms,
        costPerMToken: m.cost_per_m_token,
      }))

      const approvals = unwrap(approvalsRes, [])
      const mappedApprovals: ApprovalItem[] = (approvals || []).map((a) => ({
        id: a.id,
        title: a.title,
        agent: a.agent,
        riskLevel: a.risk_level,
        status: a.status,
        createdAt: a.created_at,
        description: a.description,
      }))

      const infra = unwrap(infraRes, [])
      const mappedInfra: InfraNode[] = (infra || []).map((n) => ({
        id: n.id,
        name: n.name,
        type: n.type,
        status: n.status,
        metrics: n.metrics,
      }))

      set({
        loading: false,
        pulse: mappedPulse,
        models: mappedModels,
        approvals: mappedApprovals,
        infraNodes: mappedInfra,
        agents: unwrap(agentsRes, []),
        memory: unwrap(memoryRes, []),
        skills: unwrap(skillsRes, []),
        observations: unwrap(obsRes, []),
        workflows: unwrap(workflowsRes, []),
        tasks: unwrap(tasksRes, []),
        comms: unwrap(commsRes, []),
        tracking: unwrap(trackingRes, []),
        analytics: unwrap(analyticsRes, null),
        settings: unwrap(settingsRes, null),
        profile: unwrap(profileRes, null),
      })
    } catch (err) {
      set({ loading: false, error: String(err) })
    }
  },
}))
