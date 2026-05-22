import { create } from 'zustand'
import type { RouteId } from '../types/routes.ts'
import type { PresenceMode } from '../types/presence.ts'
import type { AwarenessTier, GlobalLayer } from '../types/awareness.ts'
import type { SystemPulse, ModelBadge, TraceEvent, ApprovalItem, InfraNode, MeshNode, OrganismAgent, OrganismDeliverable } from '../types/domain.ts'
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
  type ActivityEvent,
  type GovernanceResponse,
  type DexExchange,
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
  meshNodes: MeshNode[]
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
  organismAgents: OrganismAgent[]
  organismDeliverables: OrganismDeliverable[]
  organismRunning: boolean
  activityStream: ActivityEvent[]
  governance: GovernanceResponse | null
  dexHistory: DexExchange[]

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

  setMeshNodes: (nodes: MeshNode[]) => void
  upsertMeshNode: (node: MeshNode) => void
  removeMeshNode: (id: string) => void

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
  meshNodes: [],
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
  organismAgents: [],
  organismDeliverables: [],
  organismRunning: false,
  activityStream: [],
  governance: null,
  dexHistory: [],

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

  setMeshNodes: (meshNodes) => set({ meshNodes }),
  upsertMeshNode: (node) =>
    set((s) => {
      const idx = s.meshNodes.findIndex((n) => n.id === node.id)
      if (idx >= 0) {
        const next = [...s.meshNodes]
        next[idx] = node
        return { meshNodes: next }
      }
      return { meshNodes: [...s.meshNodes, node] }
    }),
  removeMeshNode: (id) =>
    set((s) => ({
      meshNodes: s.meshNodes.filter((n) => n.id !== id),
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
        meshRes,
        orgStatusRes,
        activityRes,
        governanceRes,
        dexHistoryRes,
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
        api.meshNodes(),
        api.organismStatus(),
        api.activityStream(200),
        api.governance(),
        api.dexHistory(50),
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

      const meshNodesRaw = unwrap(meshRes, [])
      const statusMap: Record<string, 'healthy' | 'degraded' | 'down'> = {
        connected: 'healthy',
        degraded: 'degraded',
        disconnected: 'down',
      }
      const meshInfra: InfraNode[] = (meshNodesRaw || []).map((n) => ({
        id: `mesh-${n.id}`,
        name: `${n.name} (${n.os})`,
        type: 'compute' as const,
        status: statusMap[n.status] ?? 'down',
        metrics: n.metrics,
      }))
      mappedInfra.push(...meshInfra)

      const mappedMesh: MeshNode[] = (meshNodesRaw || []).map((n) => ({
        id: n.id,
        name: n.name,
        os: n.os,
        osVersion: n.os_version,
        status: n.status,
        capabilities: n.capabilities,
        metrics: n.metrics,
        lastHeartbeat: n.last_heartbeat,
        tailscaleIp: n.tailscale_ip,
        connectedAt: n.connected_at,
        daemonVersion: n.daemon_version,
      }))

      const orgStatus = unwrap(orgStatusRes, null)
      const organismAgents: OrganismAgent[] = orgStatus?.agents?.map((a: any) => ({
        agent_id: a.agent_id,
        agent_name: a.agent_name,
        status: a.status,
        tasks_completed: a.tasks_completed,
      })) ?? []

      const organismDeliverables: OrganismDeliverable[] = orgStatus?.recent_deliverables?.map((d: any) => ({
        id: d.id,
        agent_id: d.agent_id,
        task_id: d.task_id,
        content: d.content,
        self_critique: d.self_critique,
        parent_trace_id: d.parent_trace_id,
        created_at: d.created_at,
      })) ?? []

      set({
        loading: false,
        pulse: mappedPulse,
        models: mappedModels,
        approvals: mappedApprovals,
        infraNodes: mappedInfra,
        meshNodes: mappedMesh,
        organismAgents,
        organismDeliverables,
        organismRunning: orgStatus?.running ?? false,
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
        activityStream: unwrap(activityRes, []),
        governance: unwrap(governanceRes, null),
        dexHistory: unwrap(dexHistoryRes, []),
      })
    } catch (err) {
      set({ loading: false, error: String(err) })
    }
  },
}))
