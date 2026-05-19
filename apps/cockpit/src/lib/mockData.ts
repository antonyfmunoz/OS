import type { SystemPulse, ModelBadge, TraceEvent, ApprovalItem, InfraNode } from '../types/domain.ts'
import type { GlobalEvent, AISynthesis } from '../types/awareness.ts'

export const MOCK_PULSE: SystemPulse = {
  uptime: 864000,
  cpuPercent: 34,
  memoryPercent: 61,
  activeAgents: 4,
  pendingTasks: 12,
  pendingApprovals: 3,
  traceRate: 2.4,
  wsConnected: true,
}

export const MOCK_MODELS: ModelBadge[] = [
  { id: 'opus', name: 'Opus 4.6', provider: 'Anthropic', status: 'active', latencyMs: 2400, costPerMToken: 15 },
  { id: 'gemini', name: 'Gemini 2.5 Flash', provider: 'Google', status: 'active', latencyMs: 890, costPerMToken: 0.15 },
  { id: 'groq', name: 'Llama 3.3 70B', provider: 'Groq', status: 'fallback', latencyMs: 340, costPerMToken: 0.59 },
  { id: 'ollama', name: 'Gemma 3 4B', provider: 'Ollama', status: 'fallback', latencyMs: 1200, costPerMToken: 0 },
]

export const MOCK_TRACES: TraceEvent[] = [
  { id: 't-001', timestamp: '2026-05-18T20:14:00Z', agent: 'developer', action: 'build cockpit shell', status: 'running', detail: 'Session A — React scaffold' },
  { id: 't-002', timestamp: '2026-05-18T20:12:00Z', agent: 'monitor', action: 'health check', status: 'completed', durationMs: 340 },
  { id: 't-003', timestamp: '2026-05-18T20:10:00Z', agent: 'ingestion', action: 'process gws document', status: 'completed', durationMs: 4200 },
  { id: 't-004', timestamp: '2026-05-18T20:08:00Z', agent: 'governance', action: 'evaluate risk: deploy', status: 'completed', durationMs: 120 },
  { id: 't-005', timestamp: '2026-05-18T20:05:00Z', agent: 'ceo', action: 'strategic review', status: 'pending' },
  { id: 't-006', timestamp: '2026-05-18T20:02:00Z', agent: 'outreach', action: 'send sequence batch', status: 'failed', durationMs: 8900, detail: 'MX record failure on 2/15 targets' },
  { id: 't-007', timestamp: '2026-05-18T19:58:00Z', agent: 'memory', action: 'persist observations', status: 'completed', durationMs: 560 },
  { id: 't-008', timestamp: '2026-05-18T19:55:00Z', agent: 'developer', action: 'verify ingestion pipeline', status: 'completed', durationMs: 12400 },
]

export const MOCK_APPROVALS: ApprovalItem[] = [
  { id: 'a-001', title: 'Deploy cockpit to production', agent: 'developer', riskLevel: 'high', status: 'pending', createdAt: '2026-05-18T20:15:00Z', description: 'First deployment of UMH cockpit shell to VPS nginx.' },
  { id: 'a-002', title: 'Ingest 50 GWS documents', agent: 'ingestion', riskLevel: 'medium', status: 'pending', createdAt: '2026-05-18T20:10:00Z', description: 'Batch ingest of Google Workspace documents via GWSSource.' },
  { id: 'a-003', title: 'Scale Ollama to 8B model', agent: 'infra', riskLevel: 'medium', status: 'pending', createdAt: '2026-05-18T19:45:00Z', description: 'Upgrade from gemma3:4b to gemma3:8b. Requires 6.5 GiB RAM.' },
]

export const MOCK_INFRA: InfraNode[] = [
  { id: 'n-vps', name: 'VPS Primary', type: 'compute', status: 'healthy', metrics: { cpu: 34, memory: 61, disk: 42, cost: 24 } },
  { id: 'n-neon', name: 'Neon Postgres', type: 'storage', status: 'healthy', metrics: { latency: 12, disk: 18, cost: 0 } },
  { id: 'n-discord', name: 'os-discord', type: 'service', status: 'healthy', metrics: { cpu: 8, memory: 12 } },
  { id: 'n-monitor', name: 'os-monitor', type: 'service', status: 'healthy', metrics: { cpu: 3, memory: 6 } },
  { id: 'n-bot', name: 'os-bot', type: 'service', status: 'degraded', metrics: { cpu: 2, memory: 4, latency: 45 } },
  { id: 'n-webhook', name: 'os-webhook', type: 'service', status: 'healthy', metrics: { cpu: 1, memory: 3 } },
  { id: 'n-ollama', name: 'Ollama Local', type: 'compute', status: 'healthy', metrics: { cpu: 15, memory: 28, cost: 0 } },
  { id: 'n-tailscale', name: 'Tailscale Mesh', type: 'network', status: 'healthy', metrics: { latency: 4 } },
]

export const MOCK_GLOBAL_EVENTS: GlobalEvent[] = [
  { id: 'ge-001', layer: 'cyber', title: 'CDN outage detected — Cloudflare edge nodes', summary: 'Multiple reports of 502s from CF edge pops in US-WEST and EU-CENTRAL. Monitoring for propagation.', severity: 'warning', timestamp: '2026-05-18T20:10:00Z', source: 'Cloudflare Status', relevance: 0.82 },
  { id: 'ge-002', layer: 'markets', title: 'NVDA +4.2% pre-market on AI chip guidance', summary: 'Nvidia raised Q3 guidance citing continued AI infrastructure demand. Broader semiconductor index up 1.8%.', severity: 'info', timestamp: '2026-05-18T19:30:00Z', source: 'Reuters', relevance: 0.65 },
  { id: 'ge-003', layer: 'geopolitical', title: 'EU Digital Services Act enforcement wave', summary: 'EC announced 12 new investigations into US tech platforms under DSA Article 34. Compliance deadline June 1.', severity: 'info', timestamp: '2026-05-18T18:00:00Z', source: 'EC Press', relevance: 0.45 },
  { id: 'ge-004', layer: 'news', title: 'AI agent frameworks consolidating', summary: 'Three major open-source agent frameworks announced merger into unified protocol. MCP adoption accelerating.', severity: 'info', timestamp: '2026-05-18T17:00:00Z', source: 'TechCrunch', relevance: 0.71 },
  { id: 'ge-005', layer: 'infrastructure', title: 'AWS US-EAST-1 latency spike', summary: 'P99 latency for DynamoDB in us-east-1 elevated to 340ms (normal: 8ms). No official incident yet.', severity: 'critical', timestamp: '2026-05-18T20:05:00Z', source: 'AWS Health', relevance: 0.88 },
  { id: 'ge-006', layer: 'weather', title: 'Heat advisory — Portland metro', summary: 'NWS issued heat advisory for Portland metro area. High of 98°F expected Tuesday. Plan accordingly.', severity: 'warning', timestamp: '2026-05-18T16:00:00Z', source: 'NWS', relevance: 0.55, coordinates: { lat: 45.52, lng: -122.68 } },
  { id: 'ge-007', layer: 'scientific', title: 'New protein folding benchmark', summary: 'DeepMind published AlphaFold 4 results showing 97.2% accuracy on novel protein targets.', severity: 'info', timestamp: '2026-05-18T14:00:00Z', source: 'Nature', relevance: 0.32 },
  { id: 'ge-008', layer: 'cyber', title: 'npm supply chain alert', summary: 'Compromised package detected in @solana/web3.js v2.1.4. Backdoor exfiltrates private keys. Update immediately.', severity: 'critical', timestamp: '2026-05-18T19:45:00Z', source: 'Socket Security', relevance: 0.91 },
]

export const MOCK_SYNTHESES: AISynthesis[] = [
  { id: 'syn-001', title: 'Infrastructure risk elevated', body: 'Cloudflare and AWS incidents correlating within 30min window. Low probability of shared root cause but monitoring for cascade. Recommend delaying non-critical deploys.', relatedEvents: ['ge-001', 'ge-005'], confidence: 0.74, timestamp: '2026-05-18T20:12:00Z' },
  { id: 'syn-002', title: 'Supply chain threat — actionable', body: 'npm compromise in @solana/web3.js is live. UMH does not depend on this package. No action required, but monitoring for broader npm registry attacks.', relatedEvents: ['ge-008'], confidence: 0.95, timestamp: '2026-05-18T19:48:00Z' },
  { id: 'syn-003', title: 'Market signal — AI infrastructure spend', body: 'NVDA guidance raise + agent framework consolidation suggest continued tailwind for AI infrastructure plays. Relevant to Empyrean Studio positioning.', relatedEvents: ['ge-002', 'ge-004'], confidence: 0.61, timestamp: '2026-05-18T19:35:00Z' },
]
