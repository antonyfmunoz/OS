export interface SystemPulse {
  uptime: number
  cpuPercent: number
  memoryPercent: number
  activeAgents: number
  pendingTasks: number
  pendingApprovals: number
  traceRate: number
  wsConnected: boolean
}

export interface ModelBadge {
  id: string
  name: string
  provider: string
  status: 'active' | 'fallback' | 'offline' | 'degraded'
  latencyMs: number
  costPerMToken: number
}

export interface TraceEvent {
  id: string
  timestamp: string
  agent: string
  action: string
  status: 'running' | 'completed' | 'failed' | 'pending'
  durationMs?: number
  detail?: string
}

export interface ApprovalItem {
  id: string
  title: string
  agent: string
  riskLevel: 'low' | 'medium' | 'high' | 'critical'
  status: 'pending' | 'approved' | 'denied'
  createdAt: string
  description: string
}

export interface InfraNode {
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

export interface MeshNode {
  id: string
  name: string
  os: string
  osVersion: string
  status: 'connected' | 'degraded' | 'disconnected'
  capabilities: string[]
  metrics: Record<string, number>
  lastHeartbeat: string
  tailscaleIp: string
  connectedAt: string
  daemonVersion: string
}
