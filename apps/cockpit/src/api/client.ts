const BASE = '/api/umh'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}

export interface HealthResponse {
  status: string
  started_at: string | null
  signals_processed: number
  laws_loaded: number
  violations_recorded: number
  identity_continuity: number
  active_perspectives: number
  event_bus_history_size: number
}

export interface PulseResponse {
  uptime: number
  cpu_percent: number
  memory_percent: number
  disk_percent: number
  active_agents: number
  pending_tasks: number
  pending_approvals: number
  trace_rate: number
}

export interface ModelResponse {
  id: string
  name: string
  provider: string
  status: 'active' | 'fallback' | 'offline' | 'degraded'
  latency_ms: number
  cost_per_m_token: number
}

export interface ApprovalResponse {
  id: string
  title: string
  agent: string
  risk_level: 'low' | 'medium' | 'high' | 'critical'
  status: 'pending' | 'approved' | 'denied'
  created_at: string
  description: string
}

export interface InfraNodeResponse {
  id: string
  name: string
  type: 'compute' | 'storage' | 'network' | 'service'
  status: 'healthy' | 'degraded' | 'down'
  metrics: {
    cpu?: number
    memory?: number
    disk?: number
    latency?: number
    cost?: number
  }
}

export interface AgentResponse {
  id: string
  name: string
  role: string
  model: string
  status: 'active' | 'idle' | 'offline'
  tier: 'strategic' | 'operational' | 'tactical'
  capabilities: string[]
  last_active: string
  tasks_completed: number
}

export interface MemoryEntryResponse {
  id: string
  label: string
  description: string
  memory_type: string
  authority_tier: string
  source_document: string
  primitive_type: string
  created_at: string
  domain_id?: string
}

export interface SkillResponse {
  id: string
  name: string
  description: string
  trigger: 'scheduled' | 'conversational' | 'both'
  category: 'tool' | 'workflow' | 'agent' | 'system'
  usage_count: number
  last_used: string
  effort: 'low' | 'medium' | 'high' | 'max'
}

export interface ObservationResponse {
  id: string
  label: string
  description: string
  primitive_type: string
  evidence: string
  source_document: string
  relationships: { type: string; target_id: string; target_label: string }[]
  created_at: string
}

export interface WorkflowResponse {
  id: string
  name: string
  schedule: string
  last_run: string | null
  last_status: 'success' | 'failed' | 'running' | 'never'
  run_count: number
  avg_duration_ms: number
}

export interface TaskResponse {
  id: string
  title: string
  status: 'pending' | 'in_progress' | 'completed' | 'blocked'
  agent: string
  priority: 'low' | 'medium' | 'high' | 'critical'
  created_at: string
  updated_at: string
}

export interface CommsMessage {
  id: string
  channel: string
  from_agent: string
  content: string
  timestamp: string
  direction: 'inbound' | 'outbound' | 'internal'
}

export interface TrackingEntity {
  id: string
  name: string
  entity_type: string
  last_changed: string
  change_count: number
  status: 'active' | 'stale' | 'archived'
}

export interface AnalyticsSnapshot {
  model_usage: { model: string; calls: number; tokens: number; cost: number }[]
  daily_traces: { date: string; count: number }[]
  error_rate: number
  avg_latency_ms: number
  total_cost_30d: number
}

export interface SettingsResponse {
  model_routing: { provider: string; priority: number; enabled: boolean }[]
  governance: { auto_approve_low: boolean; critical_block: boolean }
  notifications: { discord: boolean; file: boolean }
}

export interface ProfileResponse {
  identity_id: string
  name: string
  org: string
  ventures: string[]
  stage: string
  continuity_score: number
}

export interface MeshNodeResponse {
  id: string
  name: string
  os: string
  os_version: string
  status: 'connected' | 'degraded' | 'disconnected'
  capabilities: string[]
  metrics: Record<string, number>
  last_heartbeat: string
  tailscale_ip: string
  connected_at: string
  daemon_version: string
}

export interface OrganismStatusResponse {
  running: boolean
  agents: { agent_id: string; agent_name: string; status: string; tasks_completed: number }[]
  total_deliverables: number
  total_learning_signals: number
  recent_deliverables: Record<string, unknown>[]
  timestamp: string
}

export interface OrganismSignalResponse {
  signal: string
  delegated_to: string
  deliverable: Record<string, unknown> | null
  trace_id: string | null
  timestamp: string
}

export const api = {
  health: () => request<HealthResponse>('/health'),
  pulse: () => request<PulseResponse>('/pulse'),
  models: () => request<ModelResponse[]>('/models'),
  traces: () => request<{ traces: unknown[] }>('/traces'),
  infra: () => request<InfraNodeResponse[]>('/infra'),
  meshNodes: () => request<MeshNodeResponse[]>('/mesh/nodes'),

  approvals: () => request<ApprovalResponse[]>('/approvals'),
  approveItem: (id: string) =>
    request<{ ok: boolean }>(`/approvals/${id}/approve`, { method: 'POST' }),
  denyItem: (id: string, rationale?: string) =>
    request<{ ok: boolean }>(`/approvals/${id}/deny`, {
      method: 'POST',
      body: JSON.stringify({ rationale }),
    }),

  agents: () => request<AgentResponse[]>('/agents'),
  memory: () => request<MemoryEntryResponse[]>('/memory'),
  skills: () => request<SkillResponse[]>('/skills'),
  observations: () => request<ObservationResponse[]>('/observations'),
  workflows: () => request<WorkflowResponse[]>('/workflows'),
  tasks: () => request<TaskResponse[]>('/tasks'),
  comms: (limit?: number) => request<CommsMessage[]>(`/comms${limit ? `?limit=${limit}` : ''}`),
  tracking: () => request<TrackingEntity[]>('/tracking'),
  analytics: () => request<AnalyticsSnapshot>('/analytics'),
  settings: () => request<SettingsResponse>('/settings'),
  profile: () => request<ProfileResponse>('/profile'),

  organismStatus: () => request<OrganismStatusResponse>('/organism/status'),
  organismAgents: () => request<OrganismStatusResponse['agents']>('/organism/agents'),
  organismSignal: (content: string) =>
    request<OrganismSignalResponse>('/organism/signal', {
      method: 'POST',
      body: JSON.stringify({ content }),
    }),

  submitSignal: (payload: { content: string; risk?: string }) =>
    request<{ id: string }>('/signal', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  pipelineSubmit: (payload: {
    content: string
    risk_class?: string
    adapter?: string
    operation?: string
    params?: Record<string, unknown>
    pre_approved?: boolean
  }) =>
    request<{
      trace_id: string
      signal_id: string
      governance_approved: boolean
      governance_rationale: string
      executed: boolean
      success: boolean | null
      outcome_type: string | null
    }>('/pipeline/submit', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  commsSend: (recipient: string, content: string, intent?: string) =>
    request<{ ok: boolean; message_id: string }>('/comms/send', {
      method: 'POST',
      body: JSON.stringify({ recipient, content, intent }),
    }),

  workflowTrigger: (workflowId: string, params?: Record<string, unknown>) =>
    request<{ ok: boolean; trace_id: string; success: boolean | null }>(`/workflows/${workflowId}/trigger`, {
      method: 'POST',
      body: JSON.stringify({ params }),
    }),

  organismControl: (action: 'start' | 'stop' | 'status') =>
    request<{ ok?: boolean; running: boolean }>('/organism/control', {
      method: 'POST',
      body: JSON.stringify({ action }),
    }),

  agentSignal: (agentId: string, content: string) =>
    request<OrganismSignalResponse>(`/agents/${agentId}/signal`, {
      method: 'POST',
      body: JSON.stringify({ content }),
    }),

  updateSettings: (patch: Partial<SettingsResponse>) =>
    request<{ ok: boolean }>('/settings', {
      method: 'PATCH',
      body: JSON.stringify(patch),
    }),
}
