import { useCockpitStore } from '../stores/cockpitStore.ts'
import { clsx } from 'clsx'

function MetricCard({ label, value, sub, color }: { label: string; value: string; sub?: string; color?: string }) {
  return (
    <div className="wv-card p-3 text-center">
      <div className={clsx('wv-metric', color ?? 'text-text-primary')}>{value}</div>
      <div className="wv-label mt-1">{label}</div>
      {sub && <div className="text-[9px] text-text-tertiary mt-0.5">{sub}</div>}
    </div>
  )
}

function ModelUsageTable({ usage }: { usage: { model: string; calls: number; tokens: number; cost: number }[] }) {
  return (
    <div className="wv-card overflow-hidden">
      <div className="px-3 py-2 border-b border-border">
        <span className="wv-label">MODEL USAGE (30D)</span>
      </div>
      <div className="divide-y divide-border/50">
        <div className="flex items-center gap-3 px-3 py-2 text-[10px] font-mono text-text-tertiary uppercase tracking-wider">
          <span className="flex-1">MODEL</span><span className="w-16 text-right">CALLS</span><span className="w-20 text-right">TOKENS</span><span className="w-16 text-right">COST</span>
        </div>
        {usage.map((u) => (
          <div key={u.model} className="flex items-center gap-3 px-3 py-2 text-[11px] font-mono">
            <span className="text-cyan flex-1 truncate">{u.model}</span>
            <span className="text-text-secondary w-16 text-right">{u.calls.toLocaleString()}</span>
            <span className="text-text-secondary w-20 text-right">{(u.tokens / 1000).toFixed(1)}k</span>
            <span className="text-text-primary w-16 text-right">${u.cost.toFixed(2)}</span>
          </div>
        ))}
        {usage.length === 0 && <div className="text-center text-text-tertiary text-[11px] py-6">No usage data</div>}
      </div>
    </div>
  )
}

function DailyTracesChart({ data }: { data: { date: string; count: number }[] }) {
  const max = Math.max(...data.map((d) => d.count), 1)

  return (
    <div className="wv-card p-3">
      <div className="wv-label mb-3">DAILY TRACES (30D)</div>
      <div className="flex items-end gap-[2px] h-24">
        {data.map((d) => (
          <div key={d.date} className="flex-1 flex flex-col items-center justify-end h-full" title={`${d.date}: ${d.count}`}>
            <div className="w-full bg-cyan/60 rounded-t-sm transition-all" style={{ height: `${(d.count / max) * 100}%`, minHeight: d.count > 0 ? '2px' : '0' }} />
          </div>
        ))}
        {data.length === 0 && <div className="flex-1 flex items-center justify-center text-text-tertiary text-[10px]">No data</div>}
      </div>
    </div>
  )
}

export function Analytics() {
  const { analytics } = useCockpitStore()

  if (!analytics) {
    return (
      <div className="h-full flex flex-col p-4">
        <h1 className="text-[14px] font-mono uppercase tracking-widest text-text-secondary mb-4">Analytics</h1>
        <div className="flex-1 flex items-center justify-center text-text-tertiary text-[11px]">Loading analytics data...</div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col p-4 overflow-hidden">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-[14px] font-mono uppercase tracking-widest text-text-secondary">Analytics</h1>
      </div>
      <div className="grid grid-cols-4 gap-3 mb-4">
        <MetricCard label="ERROR RATE" value={`${(analytics.error_rate * 100).toFixed(1)}%`} color={analytics.error_rate > 0.05 ? 'text-danger' : 'text-ok'} />
        <MetricCard label="AVG LATENCY" value={`${analytics.avg_latency_ms.toFixed(0)}ms`} color="text-cyan" />
        <MetricCard label="30D COST" value={`$${analytics.total_cost_30d.toFixed(2)}`} color="text-warn" />
        <MetricCard label="MODELS" value={String(analytics.model_usage.length)} color="text-text-primary" />
      </div>
      <div className="grid grid-cols-2 gap-4 flex-1 min-h-0 overflow-y-auto">
        <DailyTracesChart data={analytics.daily_traces} />
        <ModelUsageTable usage={analytics.model_usage} />
      </div>
    </div>
  )
}
