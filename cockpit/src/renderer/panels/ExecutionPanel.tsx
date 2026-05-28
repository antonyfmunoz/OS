import { useOrganismStore } from '../stores/organismStore'
import { useRealtimeStore } from '../stores/realtimeStore'
import { usePolling } from '../hooks/usePolling'
import { formatDuration, relativeTime } from '../lib/time'
import { ExecutionTimeline } from '../components/ExecutionTimeline'
import { EventConsole } from '../components/EventConsole'
import { ConnectionBanner } from '../components/ConnectionBanner'

const RISK_BADGE: Record<string, string> = {
  low: 'text-ok',
  medium: 'text-warn',
  high: 'text-danger',
  critical: 'text-danger',
}

export function ExecutionPanel() {
  const spine = useOrganismStore((s) => s.spine)
  const executionMode = useOrganismStore((s) => s.executionMode)
  const guard = useOrganismStore((s) => s.guard)
  const gateway = useOrganismStore((s) => s.gateway)
  const leverage = useOrganismStore((s) => s.leverage)
  const journal = useOrganismStore((s) => s.journal)

  const realtimeStatus = useRealtimeStore((s) => s.status)
  const fetchAll = useOrganismStore((s) => s.fetchAll)
  const fetchPending = useOrganismStore((s) => s.fetchPending)
  const fetchCompleted = useOrganismStore((s) => s.fetchCompleted)
  const fetchJournalRecent = useOrganismStore((s) => s.fetchJournalRecent)

  usePolling(fetchAll, realtimeStatus === 'connected' ? 15000 : 5000)
  usePolling(() => { fetchPending(); fetchCompleted(); fetchJournalRecent() }, realtimeStatus === 'connected' ? 10000 : 3000)

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <ConnectionBanner />

      {/* Top bar — governance status */}
      <div className="flex items-center gap-4 px-4 py-2 flex-shrink-0 border-b border-border">
        <h2 className="text-sm font-semibold text-text-primary">Governed Execution Spine</h2>
        <StatusChip label="Mode" value={executionMode?.current_mode?.toUpperCase() ?? '—'} />
        <StatusChip label="Guard" value={guard?.mode?.replace('_', ' ')?.toUpperCase() ?? '—'} />
        <StatusChip label="Gateway" value={gateway?.policy?.toUpperCase() ?? '—'} />
        <div className="flex-1" />
        {spine && (
          <div className="flex gap-3 text-[10px]">
            <span className="text-ok">{spine.total_succeeded} ok</span>
            <span className="text-danger">{spine.total_failed} fail</span>
            <span className="text-warn">{spine.total_rejected} reject</span>
            <span className="text-text-secondary">{spine.total_executed} total</span>
            <span className="text-cyan">{((spine.success_rate ?? 0) * 100).toFixed(0)}%</span>
          </div>
        )}
      </div>

      {/* Main content — two-column */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: execution lifecycle timeline */}
        <div className="flex-1 overflow-y-auto p-3">
          <ExecutionTimeline />
        </div>

        {/* Right: event console + leverage sidebar */}
        <div className="w-80 border-l border-border overflow-hidden flex flex-col bg-canvas">
          {/* Leverage */}
          {leverage && (
            <div className="p-3 border-b border-border">
              <h3 className="wv-label mb-2">Leverage</h3>
              <div className="grid grid-cols-2 gap-y-1.5 gap-x-3">
                <StatRow label="Composite" value={leverage.dimensions.composite.toFixed(2)} />
                <StatRow label="Time Saved" value={`${(leverage.totals.operator_seconds_saved / 3600).toFixed(1)}h`} />
                <StatRow label="Autonomous" value={`${leverage.totals.autonomous_resolutions}`} />
                <StatRow label="Autonomy" value={`${(leverage.dimensions.execution_autonomy * 100).toFixed(0)}%`} />
                <StatRow label="Reliability" value={`${(leverage.dimensions.operational_reliability * 100).toFixed(0)}%`} />
                <StatRow label="Tasks" value={`${leverage.totals.tasks}`} />
              </div>
            </div>
          )}

          {/* Execution Mode */}
          {executionMode && (
            <div className="p-3 border-b border-border">
              <h3 className="wv-label mb-2">Execution Mode</h3>
              <div className="grid grid-cols-2 gap-y-1.5 gap-x-3">
                <StatRow label="Mode" value={executionMode.current_mode.toUpperCase()} />
                <StatRow label="Decisions" value={`${executionMode.total_decisions}`} />
                <StatRow label="Successes" value={`${executionMode.success_count}`} />
                <StatRow label="Failures" value={`${executionMode.failure_count}`} />
                <StatRow label="Reliability" value={`${(executionMode.reliability * 100).toFixed(0)}%`} />
                <StatRow label="Transitions" value={`${executionMode.transitions}`} />
              </div>
            </div>
          )}

          {/* Journal stats */}
          {journal && (
            <div className="p-3 border-b border-border">
              <h3 className="wv-label mb-1">Journal</h3>
              <div className="flex gap-3 text-[10px]">
                <span className="text-text-secondary">{journal.total_entries} entries</span>
                <span className="text-text-secondary">{journal.in_memory} in memory</span>
                <span className="text-ok">{((journal.success_rate ?? 0) * 100).toFixed(0)}% success</span>
              </div>
            </div>
          )}

          {/* Compact event console */}
          <div className="flex-1 overflow-hidden p-3">
            <EventConsole maxHeight="100%" compact />
          </div>
        </div>
      </div>
    </div>
  )
}

function StatusChip({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-[10px] text-text-tertiary">{label}:</span>
      <span className="text-[10px] font-mono text-cyan">{value}</span>
    </div>
  )
}

function StatRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-[10px] text-text-tertiary">{label}</span>
      <span className="text-[10px] font-mono text-text-primary">{value}</span>
    </div>
  )
}
