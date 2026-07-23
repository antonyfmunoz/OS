import { useState, useCallback, useEffect } from 'react'
import { useOrganismStore } from '../stores/organismStore'
import { useViewContextStore } from '../stores/viewContextStore'
import { useRealtimeStore } from '../stores/realtimeStore'
import { usePolling } from '../hooks/usePolling'
import { fetchApi } from '../api/client'
import { formatDuration, relativeTime } from '../lib/time'
import { ExecutionTimeline } from '../components/ExecutionTimeline'
import { EventConsole } from '../components/EventConsole'
import { ConnectionBanner } from '../components/ConnectionBanner'
import { ExecutorBadge } from '../components/ExecutorBadge'
import { AttemptsView } from '../components/execution/AttemptsView'

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

  const setViewContext = useViewContextStore((s) => s.setContext)
  const realtimeStatus = useRealtimeStore((s) => s.status)

  useEffect(() => {
    setViewContext({ active_route: 'execution', visible_context_summary: 'Governed Execution Spine' })
  }, [setViewContext])
  const fetchAll = useOrganismStore((s) => s.fetchAll)
  const fetchPending = useOrganismStore((s) => s.fetchPending)
  const fetchCompleted = useOrganismStore((s) => s.fetchCompleted)
  const fetchJournalRecent = useOrganismStore((s) => s.fetchJournalRecent)

  usePolling(fetchAll, realtimeStatus === 'connected' ? 15000 : 5000)
  usePolling(() => { fetchPending(); fetchCompleted(); fetchJournalRecent() }, realtimeStatus === 'connected' ? 10000 : 3000)

  const [tab, setTab] = useState<'attempts' | 'runtime'>('attempts')

  return (
    <div data-testid="w2-execution-root" className="flex flex-col h-full overflow-hidden">
      <ConnectionBanner />

      {/* Tab switcher — Attempts (the canonical execution view) / Runtime diagnostics */}
      <div className="flex items-center gap-1 px-3 py-1 flex-shrink-0 border-b border-border">
        {(['attempts', 'runtime'] as const).map((t) => (
          <button
            key={t}
            data-testid={`w2-execution-tab-${t}`}
            onClick={() => setTab(t)}
            className={`text-[10px] font-mono px-2 py-0.5 rounded uppercase ${tab === t ? 'bg-cyan/10 text-cyan' : 'text-text-tertiary hover:text-text-secondary'}`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === 'attempts' ? (
        <AttemptsView />
      ) : (
        <RuntimeDiagnostics
          spine={spine}
          executionMode={executionMode}
          guard={guard}
          gateway={gateway}
          leverage={leverage}
          journal={journal}
        />
      )}
    </div>
  )
}

/* eslint-disable @typescript-eslint/no-explicit-any */
function RuntimeDiagnostics({ spine, executionMode, guard, gateway, leverage, journal }: any) {
  return (
    <div className="flex flex-col h-full overflow-hidden">

      {/* Top bar — governance status */}
      <div className="flex items-center gap-4 px-4 py-2 flex-shrink-0 border-b border-border">
        <h2 className="text-sm font-semibold text-text-primary">Governed Execution Spine</h2>
        <StatusChip label="Mode" value={executionMode?.current_mode?.toUpperCase() ?? '—'} />
        <StatusChip label="Guard" value={guard?.mode?.replace('_', ' ')?.toUpperCase() ?? '—'} />
        <StatusChip label="Gateway" value={gateway?.policy?.toUpperCase() ?? '—'} />
        <ExecutorBadge executorType={executionMode?.default_executor ?? 'simulation'} targetMachine={executionMode?.target_machine} />
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
        {/* Left: execution lifecycle timeline + trace */}
        <div className="flex-1 overflow-y-auto p-3 space-y-4">
          <ExecutionTimeline />
          <TraceTimeline />
        </div>

        {/* Right: event console + leverage sidebar */}
        <div className="w-80 border-l border-border overflow-hidden flex flex-col bg-canvas">
          {/* Leverage */}
          {leverage && (
            <div className="p-3 border-b border-border">
              <h3 className="wv-label mb-2">Leverage</h3>
              <div className="grid grid-cols-2 gap-y-1.5 gap-x-3">
                <StatRow label="Composite" value={(leverage.dimensions?.composite ?? 0).toFixed(2)} />
                <StatRow label="Time Saved" value={`${((leverage.totals?.operator_seconds_saved ?? 0) / 3600).toFixed(1)}h`} />
                <StatRow label="Autonomous" value={`${leverage.totals?.autonomous_resolutions ?? 0}`} />
                <StatRow label="Autonomy" value={`${((leverage.dimensions?.execution_autonomy ?? 0) * 100).toFixed(0)}%`} />
                <StatRow label="Reliability" value={`${((leverage.dimensions?.operational_reliability ?? 0) * 100).toFixed(0)}%`} />
                <StatRow label="Tasks" value={`${leverage.totals?.tasks ?? 0}`} />
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

function TraceTimeline() {
  const [events, setEvents] = useState<any[]>([])

  const fetchEvents = useCallback(async () => {
    try {
      const data = await fetchApi<any>('/organism/runtime-surface/sessions')
      if (data.sessions) {
        const recent = data.sessions
          .filter((s: any) => s.runtime_status !== 'drafted')
          .slice(-10)
          .reverse()
        setEvents(recent)
      }
    } catch { /* silent */ }
  }, [])

  usePolling(fetchEvents, 5000)

  if (events.length === 0) return null

  return (
    <section>
      <h3 className="wv-label mb-2">Runtime Trace</h3>
      <div className="space-y-1">
        {events.map((e: any) => (
          <div key={e.session_id} className="flex items-center gap-2 py-1">
            <span className={`w-1.5 h-1.5 rounded-full ${
              e.runtime_status === 'completed' ? 'bg-ok' :
              e.runtime_status === 'failed' ? 'bg-danger' :
              e.runtime_status === 'running' ? 'bg-cyan' :
              e.runtime_status === 'blocked' ? 'bg-warn' :
              'bg-text-tertiary'
            }`} />
            <span className="text-[10px] font-mono text-text-primary truncate flex-1">
              {e.session_id?.slice(0, 16)}
            </span>
            <span className="text-[10px] text-text-tertiary">{e.runtime_type}</span>
            <span className="text-[10px] font-mono text-text-secondary">{e.runtime_status}</span>
          </div>
        ))}
      </div>
    </section>
  )
}

function StatusChip({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center gap-2">
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
