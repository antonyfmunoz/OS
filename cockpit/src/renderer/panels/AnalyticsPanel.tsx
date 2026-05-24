import { useAnalyticsStore } from '../stores/analyticsStore'
import { usePolling } from '../hooks/usePolling'
import { RingGauge } from '../components/RingGauge'

function MiniChart({ data }: { data: { date: string; count: number }[] }) {
  if (data.length === 0) return null
  const max = Math.max(...data.map((d) => d.count), 1)
  const w = 600
  const h = 120
  const points = data.map((d, i) => {
    const x = (i / Math.max(data.length - 1, 1)) * w
    const y = h - (d.count / max) * (h - 10)
    return `${x},${y}`
  })

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full" style={{ height: 140 }}>
      <defs>
        <linearGradient id="chartGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--accent-cyan)" stopOpacity="0.3" />
          <stop offset="100%" stopColor="var(--accent-cyan)" stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon
        points={`0,${h} ${points.join(' ')} ${w},${h}`}
        fill="url(#chartGrad)"
      />
      <polyline
        points={points.join(' ')}
        fill="none"
        stroke="var(--accent-cyan)"
        strokeWidth="2"
      />
      {data.map((d, i) => {
        const x = (i / Math.max(data.length - 1, 1)) * w
        const y = h - (d.count / max) * (h - 10)
        return (
          <circle
            key={i}
            cx={x}
            cy={y}
            r="3"
            fill="var(--accent-cyan)"
            opacity="0.6"
          >
            <title>{d.date}: {d.count} traces</title>
          </circle>
        )
      })}
    </svg>
  )
}

export function AnalyticsPanel() {
  const data = useAnalyticsStore((s) => s.data)
  const fetchAnalytics = useAnalyticsStore((s) => s.fetchAnalytics)

  usePolling(fetchAnalytics, 15000)

  if (!data) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="hud-text">Loading analytics...</p>
      </div>
    )
  }

  return (
    <div className="h-full overflow-y-auto p-4 space-y-6">
      {/* KPI row */}
      <div className="grid grid-cols-4 gap-4">
        <div
          className="px-4 py-3 rounded"
          style={{ background: 'var(--surface-2)', border: '1px solid var(--border)' }}
        >
          <p className="hud-text mb-2">Error Rate</p>
          <RingGauge
            value={data.error_rate * 100}
            max={100}
            size={80}
            label={`${(data.error_rate * 100).toFixed(1)}%`}
          />
        </div>
        <div
          className="px-4 py-3 rounded"
          style={{ background: 'var(--surface-2)', border: '1px solid var(--border)' }}
        >
          <p className="hud-text mb-2">Avg Latency</p>
          <p className="text-2xl font-mono" style={{ color: 'var(--accent-cyan)' }}>
            {data.avg_latency_ms}
            <span className="text-xs ml-1" style={{ color: 'var(--text-tertiary)' }}>ms</span>
          </p>
        </div>
        <div
          className="px-4 py-3 rounded"
          style={{ background: 'var(--surface-2)', border: '1px solid var(--border)' }}
        >
          <p className="hud-text mb-2">30d Cost</p>
          <p className="text-2xl font-mono" style={{ color: 'var(--accent-green)' }}>
            ${data.total_cost_30d.toFixed(2)}
          </p>
        </div>
        <div
          className="px-4 py-3 rounded"
          style={{ background: 'var(--surface-2)', border: '1px solid var(--border)' }}
        >
          <p className="hud-text mb-2">Daily Traces</p>
          <p className="text-2xl font-mono" style={{ color: 'var(--accent-cyan)' }}>
            {data.daily_traces.length > 0 ? data.daily_traces[data.daily_traces.length - 1].count : 0}
          </p>
        </div>
      </div>

      {/* Throughput chart */}
      <div
        className="px-4 py-3 rounded"
        style={{ background: 'var(--surface-2)', border: '1px solid var(--border)' }}
      >
        <p className="hud-text mb-3">Execution Throughput (30d)</p>
        <MiniChart data={data.daily_traces} />
        {data.daily_traces.length > 0 && (
          <div className="flex justify-between mt-2">
            <span className="text-xs font-mono" style={{ color: 'var(--text-tertiary)' }}>
              {data.daily_traces[0].date}
            </span>
            <span className="text-xs font-mono" style={{ color: 'var(--text-tertiary)' }}>
              {data.daily_traces[data.daily_traces.length - 1].date}
            </span>
          </div>
        )}
      </div>

      {/* Model usage */}
      <div
        className="px-4 py-3 rounded"
        style={{ background: 'var(--surface-2)', border: '1px solid var(--border)' }}
      >
        <p className="hud-text mb-3">Model Routing</p>
        <div className="space-y-2">
          {data.model_usage.map((m) => (
            <div
              key={m.model}
              className="flex items-center gap-3 px-3 py-2 rounded"
              style={{ background: 'var(--surface-1)' }}
            >
              <span className="text-sm flex-1">{m.model}</span>
              <span className="font-mono text-xs" style={{ color: 'var(--accent-cyan)' }}>
                {m.calls} calls
              </span>
              <span className="font-mono text-xs" style={{ color: 'var(--text-tertiary)' }}>
                {(m.tokens / 1000).toFixed(0)}k tokens
              </span>
              <span className="font-mono text-xs" style={{ color: 'var(--accent-green)' }}>
                ${m.cost.toFixed(2)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
