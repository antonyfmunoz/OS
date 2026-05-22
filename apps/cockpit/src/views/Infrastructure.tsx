import { useCockpitStore } from '../stores/cockpitStore.ts'
import { relativeTime } from '../lib/time.ts'
import { clsx } from 'clsx'
import type { InfraNode, MeshNode } from '../types/domain.ts'

function MetricBar({ value, max = 100, color }: { value: number; max?: number; color: string }) {
  const pct = Math.min((value / max) * 100, 100)
  return (
    <div className="h-1.5 bg-border rounded-sm overflow-hidden">
      <div className={clsx('h-full rounded-sm transition-all', color)} style={{ width: `${pct}%` }} />
    </div>
  )
}

function colorForPercent(v: number): string {
  if (v > 80) return 'bg-danger'
  if (v > 60) return 'bg-warn'
  return 'bg-ok'
}

const MESH_STATUS_BADGE: Record<MeshNode['status'], string> = {
  connected: 'wv-badge-ok',
  degraded: 'wv-badge-warn',
  disconnected: 'wv-badge-danger',
}

const MESH_STATUS_DOT: Record<MeshNode['status'], string> = {
  connected: 'bg-ok',
  degraded: 'bg-warn',
  disconnected: 'bg-border',
}

function MeshNodeCard({ node }: { node: MeshNode }) {
  const cpu = node.metrics.cpu
  const memory = node.metrics.memory
  const disk = node.metrics.disk
  const battery = node.metrics.battery

  return (
    <div className="wv-card p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className={clsx('w-2 h-2 rounded-full', MESH_STATUS_DOT[node.status], node.status === 'connected' && 'wv-pulse')} />
          <span className="text-[12px] text-text-primary font-mono">{node.name}</span>
        </div>
        <span className={clsx('wv-badge', MESH_STATUS_BADGE[node.status])}>{node.status}</span>
      </div>

      <div className="flex items-center gap-2 mb-3">
        <span className="text-[10px] text-text-tertiary font-mono uppercase">{node.os}</span>
        {node.osVersion && <span className="text-[9px] text-text-tertiary">{node.osVersion}</span>}
        <span className="text-[9px] text-text-tertiary">v{node.daemonVersion}</span>
      </div>

      <div className="flex flex-wrap gap-1 mb-3">
        {node.capabilities.map((cap) => (
          <span key={cap} className="wv-badge wv-badge-cyan">{cap}</span>
        ))}
      </div>

      <div className="space-y-2 mb-3">
        {cpu != null && (
          <div>
            <div className="flex justify-between text-[10px] mb-0.5">
              <span className="text-text-tertiary">CPU</span>
              <span className="text-text-secondary">{cpu}%</span>
            </div>
            <MetricBar value={cpu} color={colorForPercent(cpu)} />
          </div>
        )}
        {memory != null && (
          <div>
            <div className="flex justify-between text-[10px] mb-0.5">
              <span className="text-text-tertiary">MEM</span>
              <span className="text-text-secondary">{memory}%</span>
            </div>
            <MetricBar value={memory} color={colorForPercent(memory)} />
          </div>
        )}
        {disk != null && (
          <div>
            <div className="flex justify-between text-[10px] mb-0.5">
              <span className="text-text-tertiary">DISK</span>
              <span className="text-text-secondary">{disk}%</span>
            </div>
            <MetricBar value={disk} color={colorForPercent(disk)} />
          </div>
        )}
        {battery != null && (
          <div className="flex justify-between text-[10px]">
            <span className="text-text-tertiary">BATTERY</span>
            <span className={clsx(battery < 20 ? 'text-danger' : 'text-ok')}>{battery}%</span>
          </div>
        )}
      </div>

      <div className="flex items-center justify-between text-[9px] text-text-tertiary pt-2 border-t border-border">
        <span>{node.tailscaleIp}</span>
        <span>{relativeTime(node.lastHeartbeat)}</span>
      </div>
    </div>
  )
}

function MeshSection({ nodes }: { nodes: MeshNode[] }) {
  if (nodes.length === 0) return null
  const connected = nodes.filter((n) => n.status === 'connected').length

  return (
    <div className="mb-6">
      <div className="flex items-center justify-between mb-3">
        <span className="wv-label">MESH NODES</span>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-text-tertiary font-mono">{connected}/{nodes.length} connected</span>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        {nodes.map((node) => <MeshNodeCard key={node.id} node={node} />)}
      </div>
    </div>
  )
}

function NodeCard({ node }: { node: InfraNode }) {
  const statusColor = { healthy: 'wv-badge-ok', degraded: 'wv-badge-warn', down: 'wv-badge-danger' }

  return (
    <div className="wv-card p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-[12px] text-text-primary font-mono">{node.name}</span>
          <span className={clsx('wv-badge', statusColor[node.status])}>{node.status}</span>
        </div>
      </div>
      <div className="space-y-2">
        {node.metrics.cpu != null && (
          <div>
            <div className="flex justify-between text-[10px] mb-0.5">
              <span className="text-text-tertiary">CPU</span>
              <span className="text-text-secondary">{node.metrics.cpu}%</span>
            </div>
            <MetricBar value={node.metrics.cpu} color={colorForPercent(node.metrics.cpu)} />
          </div>
        )}
        {node.metrics.memory != null && (
          <div>
            <div className="flex justify-between text-[10px] mb-0.5">
              <span className="text-text-tertiary">MEM</span>
              <span className="text-text-secondary">{node.metrics.memory}%</span>
            </div>
            <MetricBar value={node.metrics.memory} color={colorForPercent(node.metrics.memory)} />
          </div>
        )}
        {node.metrics.disk != null && (
          <div>
            <div className="flex justify-between text-[10px] mb-0.5">
              <span className="text-text-tertiary">DISK</span>
              <span className="text-text-secondary">{node.metrics.disk}%</span>
            </div>
            <MetricBar value={node.metrics.disk} color={colorForPercent(node.metrics.disk)} />
          </div>
        )}
        {node.metrics.latency != null && node.metrics.latency > 0 && (
          <div className="flex justify-between text-[10px]">
            <span className="text-text-tertiary">LATENCY</span>
            <span className={clsx(node.metrics.latency > 100 ? 'text-warn' : 'text-ok')}>
              {node.metrics.latency}ms
            </span>
          </div>
        )}
        {node.metrics.cost != null && (
          <div className="flex justify-between text-[10px]">
            <span className="text-text-tertiary">COST</span>
            <span className="text-text-secondary">${node.metrics.cost}/mo</span>
          </div>
        )}
        {Object.keys(node.metrics).length === 0 && (
          <div className="text-[10px] text-text-tertiary">Running</div>
        )}
      </div>
    </div>
  )
}

function NodeSection({ title, nodes }: { title: string; nodes: InfraNode[] }) {
  if (nodes.length === 0) return null
  const healthy = nodes.filter((n) => n.status === 'healthy').length
  return (
    <div className="mb-6">
      <div className="flex items-center justify-between mb-3">
        <span className="wv-label">{title}</span>
        <span className="text-[10px] text-text-tertiary font-mono">{healthy}/{nodes.length} healthy</span>
      </div>
      <div className="grid grid-cols-2 gap-3">
        {nodes.map((node) => <NodeCard key={node.id} node={node} />)}
      </div>
    </div>
  )
}

export function Infrastructure() {
  const { infraNodes, meshNodes } = useCockpitStore()

  const nonMeshInfra = infraNodes.filter((n) => !n.id.startsWith('mesh-'))
  const compute = nonMeshInfra.filter((n) => n.type === 'compute')
  const network = nonMeshInfra.filter((n) => n.type === 'network')
  const services = nonMeshInfra.filter((n) => n.type === 'service')
  const storage = nonMeshInfra.filter((n) => n.type === 'storage')

  const totalCost = infraNodes.reduce((s, n) => s + (n.metrics.cost ?? 0), 0)

  return (
    <div className="h-full flex flex-col p-4 overflow-y-auto">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-[14px] font-mono uppercase tracking-widest text-text-secondary">Infrastructure</h1>
        <div className="flex items-center gap-3">
          <span className="wv-badge wv-badge-cyan">{infraNodes.length + meshNodes.length} nodes</span>
          {meshNodes.length > 0 && <span className="wv-badge wv-badge-violet">{meshNodes.length} mesh</span>}
          {totalCost > 0 && <span className="text-[11px] text-text-tertiary font-mono">${totalCost}/mo</span>}
        </div>
      </div>

      <div className="grid grid-cols-5 gap-3 mb-6">
        {([
          ['compute', 'DEVICES', compute],
          ['mesh', 'MESH', meshNodes],
          ['network', 'NETWORK', network],
          ['service', 'SERVICES', services],
          ['storage', 'STORAGE', storage],
        ] as const).map(([_type, label, nodes]) => {
          const count = nodes.length
          const upCount = nodes.filter((n: any) =>
            'status' in n && (n.status === 'healthy' || n.status === 'connected'),
          ).length
          return (
            <div key={label} className="wv-card p-3 text-center">
              <div className="wv-label mb-1">{label}</div>
              <div className="wv-metric text-text-primary">{count}</div>
              <div className="text-[10px] text-ok mt-1">{upCount}/{count} up</div>
            </div>
          )
        })}
      </div>

      <MeshSection nodes={meshNodes} />
      <NodeSection title="DEVICES" nodes={compute} />
      <NodeSection title="NETWORK" nodes={network} />
      <NodeSection title="SERVICES" nodes={services} />
      <NodeSection title="STORAGE" nodes={storage} />
    </div>
  )
}
