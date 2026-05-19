import { useCockpitStore } from '../stores/cockpitStore.ts'
import { clsx } from 'clsx'

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

export function Infrastructure() {
  const { infraNodes } = useCockpitStore()

  const statusColor = {
    healthy: 'wv-badge-ok',
    degraded: 'wv-badge-warn',
    down: 'wv-badge-danger',
  }

  const typeLabel = {
    compute: 'COMPUTE',
    storage: 'STORAGE',
    network: 'NETWORK',
    service: 'SERVICE',
  }

  const totalCost = infraNodes.reduce((s, n) => s + (n.metrics.cost ?? 0), 0)

  return (
    <div className="h-full flex flex-col p-4 overflow-y-auto">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-[14px] font-mono uppercase tracking-widest text-text-secondary">
          Infrastructure
        </h1>
        <div className="flex items-center gap-3">
          <span className="wv-badge wv-badge-cyan">{infraNodes.length} nodes</span>
          <span className="text-[11px] text-text-tertiary font-mono">${totalCost}/mo</span>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-4 gap-3 mb-4">
        {(['compute', 'storage', 'network', 'service'] as const).map((type) => {
          const nodes = infraNodes.filter((n) => n.type === type)
          const healthy = nodes.filter((n) => n.status === 'healthy').length
          return (
            <div key={type} className="wv-card p-3 text-center">
              <div className="wv-label mb-1">{typeLabel[type]}</div>
              <div className="wv-metric text-text-primary">{nodes.length}</div>
              <div className="text-[10px] text-ok mt-1">{healthy}/{nodes.length} healthy</div>
            </div>
          )
        })}
      </div>

      {/* Node grid */}
      <div className="grid grid-cols-2 gap-3">
        {infraNodes.map((node) => (
          <div key={node.id} className="wv-card p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className="text-[12px] text-text-primary font-mono">{node.name}</span>
                <span className={clsx('wv-badge', statusColor[node.status])}>{node.status}</span>
              </div>
              <span className="text-[9px] text-text-tertiary uppercase font-mono">{typeLabel[node.type]}</span>
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
              {node.metrics.latency != null && (
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
            </div>
          </div>
        ))}
      </div>

      {/* Self-expansion proposals stub */}
      <div className="wv-card p-4 mt-4">
        <div className="wv-label mb-2">SELF-EXPANSION PROPOSALS</div>
        <div className="text-[11px] text-text-tertiary text-center py-4">
          No active proposals. The substrate will surface optimization opportunities here.
        </div>
      </div>
    </div>
  )
}
