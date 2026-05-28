import { useOrganismStore } from '../stores/organismStore'
import { usePolling } from '../hooks/usePolling'
import { formatDuration } from '../lib/time'

const STATUS_COLORS: Record<string, string> = {
  completed: 'bg-ok',
  verified: 'bg-ok',
  executing: 'bg-cyan',
  approved: 'bg-cyan',
  proposed: 'bg-warn',
  failed: 'bg-danger',
  rejected: 'bg-danger',
  rolled_back: 'bg-warn',
  verification_failed: 'bg-danger',
}

const RISK_BADGE: Record<string, string> = {
  low: 'text-ok',
  medium: 'text-warn',
  high: 'text-danger',
  critical: 'text-danger',
}

export function ExecutionPanel() {
  const spine = useOrganismStore((s) => s.spine)
  const pending = useOrganismStore((s) => s.pendingEnvelopes)
  const active = useOrganismStore((s) => s.activeEnvelopes)
  const completed = useOrganismStore((s) => s.completedEnvelopes)
  const executionMode = useOrganismStore((s) => s.executionMode)
  const guard = useOrganismStore((s) => s.guard)
  const gateway = useOrganismStore((s) => s.gateway)
  const leverage = useOrganismStore((s) => s.leverage)
  const journalRecent = useOrganismStore((s) => s.journalRecent)
  const approveEnvelope = useOrganismStore((s) => s.approveEnvelope)
  const rejectEnvelope = useOrganismStore((s) => s.rejectEnvelope)

  const fetchAll = useOrganismStore((s) => s.fetchAll)
  const fetchPending = useOrganismStore((s) => s.fetchPending)
  const fetchCompleted = useOrganismStore((s) => s.fetchCompleted)
  const fetchJournalRecent = useOrganismStore((s) => s.fetchJournalRecent)

  usePolling(fetchAll, 5000)
  usePolling(() => { fetchPending(); fetchCompleted(); fetchJournalRecent() }, 3000)

  return (
    <div className="flex flex-col h-full overflow-hidden">
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
        {/* Left: envelope lifecycle */}
        <div className="flex-1 overflow-y-auto p-3 space-y-4">
          {/* Active executions */}
          {active.length > 0 && (
            <section>
              <h3 className="wv-label mb-2">Active — {active.length}</h3>
              <div className="space-y-1.5">
                {active.map((e) => (
                  <EnvelopeCard key={e.envelope_id} env={e} />
                ))}
              </div>
            </section>
          )}

          {/* Pending approval */}
          <section>
            <h3 className="wv-label mb-2">Pending Approval — {pending.length}</h3>
            {pending.length === 0 ? (
              <p className="text-xs text-text-tertiary">No pending envelopes</p>
            ) : (
              <div className="space-y-1.5">
                {pending.map((e) => (
                  <div key={e.envelope_id} className="wv-card p-3">
                    <div className="flex items-start gap-2 mb-2">
                      <span className={`text-[10px] font-mono ${RISK_BADGE[e.risk_level] ?? 'text-text-tertiary'}`}>
                        {e.risk_level.toUpperCase()}
                      </span>
                      <span className="text-[11px] text-text-primary flex-1">{e.intent}</span>
                      <span className="text-[10px] text-text-tertiary">{e.source}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-text-tertiary flex-1">
                        {e.action_type} · {e.blast_radius}
                      </span>
                      <button
                        onClick={() => approveEnvelope(e.envelope_id)}
                        className="px-2 py-0.5 text-[10px] font-mono rounded bg-ok/10 text-ok border border-ok/30"
                      >
                        approve
                      </button>
                      <button
                        onClick={() => rejectEnvelope(e.envelope_id)}
                        className="px-2 py-0.5 text-[10px] font-mono rounded bg-danger/10 text-danger border border-danger/30"
                      >
                        reject
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Completed */}
          <section>
            <h3 className="wv-label mb-2">Completed — {completed.length}</h3>
            <div className="space-y-1">
              {completed.length === 0 && <p className="text-xs text-text-tertiary">No completed envelopes</p>}
              {completed.slice(0, 20).map((e) => (
                <EnvelopeCard key={e.envelope_id} env={e} />
              ))}
            </div>
          </section>
        </div>

        {/* Right: journal + leverage sidebar */}
        <div className="w-80 border-l border-border overflow-y-auto p-3 space-y-4 bg-canvas">
          {/* Leverage */}
          {leverage && (
            <section className="wv-card p-3">
              <h3 className="wv-label mb-2">Leverage</h3>
              <div className="grid grid-cols-2 gap-y-1.5 gap-x-3">
                <StatRow label="Composite" value={leverage.dimensions.composite.toFixed(2)} />
                <StatRow label="Time Saved" value={`${(leverage.totals.operator_seconds_saved / 3600).toFixed(1)}h`} />
                <StatRow label="Autonomous" value={`${leverage.totals.autonomous_resolutions}`} />
                <StatRow label="Autonomy" value={`${(leverage.dimensions.execution_autonomy * 100).toFixed(0)}%`} />
                <StatRow label="Reliability" value={`${(leverage.dimensions.operational_reliability * 100).toFixed(0)}%`} />
                <StatRow label="Tasks" value={`${leverage.totals.tasks}`} />
              </div>
            </section>
          )}

          {/* Execution Mode */}
          {executionMode && (
            <section className="wv-card p-3">
              <h3 className="wv-label mb-2">Execution Mode</h3>
              <div className="grid grid-cols-2 gap-y-1.5 gap-x-3">
                <StatRow label="Mode" value={executionMode.current_mode.toUpperCase()} />
                <StatRow label="Decisions" value={`${executionMode.total_decisions}`} />
                <StatRow label="Successes" value={`${executionMode.success_count}`} />
                <StatRow label="Failures" value={`${executionMode.failure_count}`} />
                <StatRow label="Reliability" value={`${(executionMode.reliability * 100).toFixed(0)}%`} />
                <StatRow label="Transitions" value={`${executionMode.transitions}`} />
              </div>
            </section>
          )}

          {/* Journal stream */}
          <section className="wv-card p-3">
            <h3 className="wv-label mb-2">Journal Stream</h3>
            <div className="space-y-0.5">
              {journalRecent.length === 0 && <p className="text-xs text-text-tertiary">No entries</p>}
              {journalRecent.slice(0, 20).map((e, i) => (
                <div key={i} className="flex items-center gap-1.5 py-0.5 text-[10px]">
                  <span className="font-mono text-text-tertiary w-14 shrink-0 truncate">{e.phase}</span>
                  <span className="text-text-primary truncate flex-1">{e.envelope_id.slice(0, 8)}</span>
                  <span className="text-text-tertiary">{e.source}</span>
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}

function EnvelopeCard({ env }: { env: { envelope_id: string; intent: string; source: string; status: string; risk_level: string; result_success: boolean; started_at: number; completed_at: number; action_type: string } }) {
  const duration = env.completed_at > 0 && env.started_at > 0
    ? (env.completed_at - env.started_at) * 1000
    : 0

  return (
    <div className="flex items-center gap-2 py-1 px-2 rounded bg-surface">
      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${STATUS_COLORS[env.status] ?? 'bg-text-tertiary'}`} />
      <span className="text-[11px] text-text-primary truncate flex-1">{env.intent}</span>
      <span className={`text-[10px] font-mono ${RISK_BADGE[env.risk_level] ?? 'text-text-tertiary'}`}>
        {env.risk_level}
      </span>
      <span className={`text-[10px] ${env.result_success ? 'text-ok' : env.status === 'rejected' ? 'text-warn' : 'text-danger'}`}>
        {env.status}
      </span>
      {duration > 0 && (
        <span className="text-[10px] text-text-tertiary font-mono">{formatDuration(duration)}</span>
      )}
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
