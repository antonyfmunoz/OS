import { useOrganismStore } from '../stores/organismStore'
import { useRealtimeStore } from '../stores/realtimeStore'
import { usePolling } from '../hooks/usePolling'
import { relativeTime, formatDuration } from '../lib/time'
import { EventConsole } from '../components/EventConsole'
import { ExecutionTimeline } from '../components/ExecutionTimeline'
import { TopologyMap } from '../components/TopologyMap'
import { ConnectionBanner } from '../components/ConnectionBanner'

const SEVERITY_COLORS: Record<string, string> = {
  low: 'text-ok',
  medium: 'text-warn',
  high: 'text-danger',
  critical: 'text-danger',
}

const RISK_BADGE: Record<string, string> = {
  low: 'wv-badge-ok',
  medium: 'wv-badge-warn',
  high: 'wv-badge-danger',
  critical: 'wv-badge-danger',
}

export function OrganismPanel() {
  const spine = useOrganismStore((s) => s.spine)
  const gateway = useOrganismStore((s) => s.gateway)
  const guard = useOrganismStore((s) => s.guard)
  const bottleneckStatus = useOrganismStore((s) => s.bottleneckStatus)
  const leverage = useOrganismStore((s) => s.leverage)
  const executionMode = useOrganismStore((s) => s.executionMode)
  const workloads = useOrganismStore((s) => s.workloads)
  const mutations = useOrganismStore((s) => s.mutations)
  const organismStatus = useOrganismStore((s) => s.organismStatus)

  const realtimeStatus = useRealtimeStore((s) => s.status)
  const eventsPerMinute = useRealtimeStore((s) => s.eventsPerMinute)
  const eventCount = useRealtimeStore((s) => s.eventCount)
  const cpuPercent = useRealtimeStore((s) => s.cpuPercent)
  const memoryPercent = useRealtimeStore((s) => s.memoryPercent)

  const fetchAll = useOrganismStore((s) => s.fetchAll)
  const fetchGatewayDecisions = useOrganismStore((s) => s.fetchGatewayDecisions)

  usePolling(fetchAll, realtimeStatus === 'connected' ? 15000 : 5000)
  usePolling(fetchGatewayDecisions, 10000)

  const bottlenecks = bottleneckStatus?.active ?? []
  const leverageRatio = leverage?.dimensions?.composite ?? 0
  const timeSaved = (leverage?.totals?.operator_seconds_saved ?? 0) / 3600
  const mutationList = mutations ? Object.values(mutations.mutations) : []

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <ConnectionBanner />

      {/* Header + KPI strip */}
      <div className="px-4 pt-3 pb-2 flex-shrink-0">
        <div className="flex items-center mb-3">
          <h2 className="text-lg font-semibold text-text-primary">Organism</h2>
          <span className="ml-2 text-xs text-text-tertiary">realtime operational cortex</span>
          <div className="ml-auto flex items-center gap-3 text-[10px]">
            <span className={`flex items-center gap-1 ${realtimeStatus === 'connected' ? 'text-ok' : 'text-warn'}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${realtimeStatus === 'connected' ? 'bg-ok' : 'bg-warn'}`} />
              {realtimeStatus.toUpperCase()}
            </span>
            {organismStatus && (
              <span className="text-text-tertiary">
                tick #{organismStatus.tick_count} · {organismStatus.running ? 'alive' : 'stopped'}
              </span>
            )}
            <span className="text-text-tertiary">{eventsPerMinute}/min · {eventCount} events</span>
          </div>
        </div>

        <div className="grid grid-cols-10 gap-1.5">
          <KPI label="MODE" value={executionMode?.current_mode?.toUpperCase() ?? '—'} color="cyan" />
          <KPI label="GUARD" value={guard?.mode?.replace(/_/g, ' ')?.toUpperCase() ?? '—'} color="cyan" />
          <KPI label="GATEWAY" value={gateway?.policy?.toUpperCase() ?? '—'} color="cyan" />
          <KPI label="EXECUTED" value={`${spine?.total_executed ?? 0}`} color="ok" />
          <KPI label="SUCCESS" value={`${((spine?.success_rate ?? 0) * 100).toFixed(0)}%`} color={rateColor(spine?.success_rate)} />
          <KPI label="FAILED" value={`${spine?.total_failed ?? 0}`} color={spine?.total_failed ? 'danger' : 'ok'} />
          <KPI label="COMPOSITE" value={leverageRatio > 0 ? leverageRatio.toFixed(2) : '—'} color="cyan" />
          <KPI label="TIME SAVED" value={timeSaved > 0 ? `${timeSaved.toFixed(1)}h` : '—'} color="ok" />
          <KPI label="CPU" value={`${cpuPercent.toFixed(0)}%`} color={cpuPercent > 90 ? 'danger' : cpuPercent > 70 ? 'warn' : 'ok'} />
          <KPI label="RAM" value={`${memoryPercent.toFixed(0)}%`} color={memoryPercent > 90 ? 'danger' : memoryPercent > 70 ? 'warn' : 'ok'} />
        </div>
      </div>

      {/* Main 3-column layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: Execution Lifecycle */}
        <div className="flex-1 overflow-y-auto p-3 border-r border-border">
          <ExecutionTimeline />

          {/* Mutation Registry */}
          <div className="mt-4">
            <h3 className="wv-label mb-2">Mutation Registry — {mutationList.length}</h3>
            <div className="space-y-1">
              {mutationList.length === 0 && <p className="text-xs text-text-tertiary">No mutations registered</p>}
              {mutationList.slice(0, 12).map((m) => (
                <div key={m.name} className="flex items-center gap-2 py-0.5">
                  <span className={`text-[10px] font-mono ${SEVERITY_COLORS[m.risk_level] ?? 'text-text-tertiary'}`}>
                    {m.risk_level}
                  </span>
                  <span className="text-[11px] text-text-primary truncate flex-1">{m.name.replace(/_/g, ' ')}</span>
                  <span className="text-[10px] text-text-tertiary">{m.blast_radius}</span>
                  {m.requires_approval && <span className="text-[9px] text-warn font-mono">GATE</span>}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Center: EventSpine Console */}
        <div className="flex-1 overflow-hidden p-3 border-r border-border">
          <EventConsole maxHeight="100%" />
        </div>

        {/* Right: Topology + Leverage + Bottlenecks */}
        <div className="w-80 overflow-y-auto p-3 bg-canvas space-y-4">
          <TopologyMap />

          {/* Leverage */}
          <section className="wv-card p-3">
            <h3 className="wv-label mb-2">Leverage</h3>
            {leverage ? (
              <div className="grid grid-cols-2 gap-2">
                <LeverageStat label="Tasks" value={`${leverage.totals.tasks}`} />
                <LeverageStat label="Autonomous" value={`${leverage.totals.autonomous_resolutions}`} />
                <LeverageStat label="Time Saved" value={`${timeSaved.toFixed(1)}h`} />
                <LeverageStat label="Composite" value={leverageRatio.toFixed(2)} />
                <LeverageStat label="Reliability" value={`${(leverage.dimensions.operational_reliability * 100).toFixed(0)}%`} />
                <LeverageStat label="Autonomy" value={`${(leverage.dimensions.execution_autonomy * 100).toFixed(0)}%`} />
                <LeverageStat label="Cognitive" value={`${(leverage.dimensions.cognitive_compression * 100).toFixed(0)}%`} />
                <LeverageStat label="Recovery" value={`${(leverage.dimensions.failure_recovery_speed * 100).toFixed(0)}%`} />
              </div>
            ) : (
              <p className="text-xs text-text-tertiary">No leverage data</p>
            )}
          </section>

          {/* Bottlenecks */}
          <section className="wv-card p-3">
            <h3 className="wv-label mb-2">Bottlenecks — {bottlenecks.length}</h3>
            <div className="space-y-1.5">
              {bottlenecks.length === 0 && <p className="text-xs text-text-tertiary">No bottlenecks detected</p>}
              {bottlenecks.slice(0, 8).map((b, i) => (
                <div key={i} className="p-1.5 rounded bg-surface">
                  <div className="flex items-center gap-2">
                    <span className={`text-[10px] font-mono ${SEVERITY_COLORS[b.severity] ?? 'text-text-tertiary'}`}>
                      {b.severity.toUpperCase()}
                    </span>
                    <span className="text-[11px] text-text-primary truncate flex-1">{b.description}</span>
                    <span className="text-[10px] text-text-tertiary">×{b.recurrence_count}</span>
                  </div>
                  {b.suggested_correction && (
                    <p className="text-[10px] text-text-tertiary mt-0.5 truncate">fix: {b.suggested_correction}</p>
                  )}
                </div>
              ))}
            </div>
          </section>

          {/* Workloads */}
          {workloads && (
            <section className="wv-card p-3">
              <h3 className="wv-label mb-2">
                Workloads — {workloads.total_runs} runs · {(workloads.success_rate * 100).toFixed(0)}%
              </h3>
              <div className="space-y-1">
                {workloads.recent_outcomes.slice(0, 6).map((o, i) => (
                  <div key={i} className="flex items-center gap-2 py-0.5">
                    <span className={`w-1.5 h-1.5 rounded-full ${o.success ? 'bg-ok' : 'bg-danger'}`} />
                    <span className="text-[11px] text-text-primary truncate flex-1">{o.workload_type}</span>
                    <span className="text-[10px] text-text-tertiary font-mono">{o.duration_seconds.toFixed(1)}s</span>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      </div>
    </div>
  )
}

function KPI({ label, value, color }: { label: string; value: string; color: string }) {
  const colorClass = color === 'cyan' ? 'text-cyan'
    : color === 'ok' ? 'text-ok'
    : color === 'warn' ? 'text-warn'
    : color === 'danger' ? 'text-danger'
    : 'text-text-primary'

  return (
    <div className="wv-card px-2 py-1.5 text-center">
      <div className="text-[8px] text-text-tertiary uppercase">{label}</div>
      <div className={`text-xs font-mono font-semibold ${colorClass}`}>{value}</div>
    </div>
  )
}

function LeverageStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="text-center">
      <div className="text-[10px] text-text-tertiary">{label}</div>
      <div className="text-xs font-mono text-text-primary">{value}</div>
    </div>
  )
}

function rateColor(rate: number | undefined): string {
  if (rate === undefined) return 'cyan'
  if (rate > 0.9) return 'ok'
  if (rate > 0.7) return 'warn'
  return 'danger'
}
