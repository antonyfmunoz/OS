import { useOrganismStore } from '../stores/organismStore'
import { usePolling } from '../hooks/usePolling'
import { relativeTime, formatDuration } from '../lib/time'

const SEVERITY_COLORS: Record<string, string> = {
  low: 'text-ok',
  medium: 'text-warn',
  high: 'text-danger',
  critical: 'text-danger',
}

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
  low: 'wv-badge-ok',
  medium: 'wv-badge-warn',
  high: 'wv-badge-danger',
  critical: 'wv-badge-danger',
}

const DOMAIN_COLORS: Record<string, string> = {
  runtime: 'text-cyan',
  governance: 'text-purple',
  advisor: 'text-amber',
  workcell: 'text-ok',
  objective: 'text-blue',
  execution: 'text-ok',
  leverage: 'text-emerald',
  supervisor: 'text-red',
  filesystem: 'text-text-secondary',
  tmux: 'text-text-secondary',
  docker: 'text-blue',
  projection: 'text-purple',
  transport: 'text-cyan',
  recursion: 'text-warn',
  memory: 'text-amber',
  observability: 'text-text-secondary',
}

const PRIORITY_COLORS: Record<string, string> = {
  low: 'text-text-tertiary',
  normal: 'text-text-secondary',
  high: 'text-warn',
  critical: 'text-danger',
}

const RUNTIME_STATUS_COLORS: Record<string, string> = {
  available: 'bg-ok',
  degraded: 'bg-warn',
  unavailable: 'bg-danger',
  unknown: 'bg-text-tertiary',
}

export function OrganismPanel() {
  const spine = useOrganismStore((s) => s.spine)
  const pending = useOrganismStore((s) => s.pendingEnvelopes)
  const active = useOrganismStore((s) => s.activeEnvelopes)
  const completed = useOrganismStore((s) => s.completedEnvelopes)
  const journal = useOrganismStore((s) => s.journal)
  const journalRecent = useOrganismStore((s) => s.journalRecent)
  const gateway = useOrganismStore((s) => s.gateway)
  const gatewayDecisions = useOrganismStore((s) => s.gatewayDecisions)
  const guard = useOrganismStore((s) => s.guard)
  const bottleneckStatus = useOrganismStore((s) => s.bottleneckStatus)
  const leverage = useOrganismStore((s) => s.leverage)
  const executionMode = useOrganismStore((s) => s.executionMode)
  const workloads = useOrganismStore((s) => s.workloads)
  const events = useOrganismStore((s) => s.events)
  const mutations = useOrganismStore((s) => s.mutations)
  const runtimeGraph = useOrganismStore((s) => s.runtimeGraph)
  const organismStatus = useOrganismStore((s) => s.organismStatus)
  const approveEnvelope = useOrganismStore((s) => s.approveEnvelope)
  const rejectEnvelope = useOrganismStore((s) => s.rejectEnvelope)

  const fetchAll = useOrganismStore((s) => s.fetchAll)
  const fetchPending = useOrganismStore((s) => s.fetchPending)
  const fetchCompleted = useOrganismStore((s) => s.fetchCompleted)
  const fetchGatewayDecisions = useOrganismStore((s) => s.fetchGatewayDecisions)
  const fetchJournalRecent = useOrganismStore((s) => s.fetchJournalRecent)
  const fetchEvents = useOrganismStore((s) => s.fetchEvents)

  usePolling(fetchAll, 5000)
  usePolling(() => { fetchPending(); fetchCompleted(); fetchGatewayDecisions(); fetchJournalRecent(); fetchEvents() }, 3000)

  const bottlenecks = bottleneckStatus?.active ?? []
  const leverageRatio = leverage?.dimensions?.composite ?? 0
  const timeSaved = (leverage?.totals?.operator_seconds_saved ?? 0) / 3600
  const totalTasks = leverage?.totals?.tasks ?? 0
  const autonomousTasks = leverage?.totals?.autonomous_resolutions ?? 0
  const runtimes = runtimeGraph ? Object.values(runtimeGraph.runtimes) : []
  const mutationList = mutations ? Object.values(mutations.mutations) : []

  return (
    <div className="flex flex-col h-full overflow-y-auto p-4">
      <div className="flex items-center mb-4">
        <h2 className="text-lg font-semibold text-text-primary">Organism</h2>
        <span className="ml-2 text-xs text-text-tertiary">governed execution lifecycle</span>
        {organismStatus && (
          <span className="ml-auto text-[10px] text-text-tertiary">
            tick #{organismStatus.tick_count} · {organismStatus.running ? 'running' : 'stopped'}
            {organismStatus.total_deliverables > 0 && ` · ${organismStatus.total_deliverables} deliverables`}
            {organismStatus.total_learning_signals > 0 && ` · ${organismStatus.total_learning_signals} signals`}
          </span>
        )}
      </div>

      {/* Top KPI strip */}
      <section className="mb-5">
        <div className="grid grid-cols-8 gap-2">
          <KPI label="MODE" value={executionMode?.current_mode?.toUpperCase() ?? '—'} color="cyan" />
          <KPI label="GUARD" value={guard?.mode?.replace(/_/g, ' ')?.toUpperCase() ?? '—'} color="cyan" />
          <KPI label="GATEWAY" value={gateway?.policy?.toUpperCase() ?? '—'} color="cyan" />
          <KPI label="EXECUTED" value={`${spine?.total_executed ?? 0}`} color="ok" />
          <KPI label="SUCCESS" value={`${((spine?.success_rate ?? 0) * 100).toFixed(0)}%`} color={rateColor(spine?.success_rate)} />
          <KPI label="REJECTED" value={`${spine?.total_rejected ?? 0}`} color={spine?.total_rejected ? 'warn' : 'ok'} />
          <KPI label="FAILED" value={`${spine?.total_failed ?? 0}`} color={spine?.total_failed ? 'danger' : 'ok'} />
          <KPI label="COMPOSITE" value={leverageRatio > 0 ? leverageRatio.toFixed(2) : '—'} color="cyan" />
        </div>
      </section>

      <div className="grid grid-cols-3 gap-4 flex-1">
        {/* Column 1: Spine Lifecycle */}
        <div className="space-y-4">
          <section className="wv-card p-3">
            <h3 className="wv-label mb-2">Pending Approval — {pending.length}</h3>
            <div className="space-y-1.5">
              {pending.length === 0 && <p className="text-xs text-text-tertiary">No pending envelopes</p>}
              {pending.slice(0, 8).map((e) => (
                <div key={e.envelope_id} className="p-2 rounded bg-surface border border-border">
                  <div className="flex items-start gap-2">
                    <span className={`wv-badge ${RISK_BADGE[e.risk_level] ?? 'wv-badge-ok'} shrink-0 text-[9px]`}>
                      {e.risk_level}
                    </span>
                    <p className="text-[11px] text-text-primary flex-1 truncate">{e.intent}</p>
                  </div>
                  <div className="flex items-center mt-1.5 gap-2">
                    <span className="text-[10px] text-text-tertiary flex-1">{e.source} · {e.action_type}</span>
                    <button onClick={() => approveEnvelope(e.envelope_id)} className="px-2 py-0.5 text-[10px] font-mono rounded bg-ok/10 text-ok border border-ok/30">approve</button>
                    <button onClick={() => rejectEnvelope(e.envelope_id)} className="px-2 py-0.5 text-[10px] font-mono rounded bg-danger/10 text-danger border border-danger/30">reject</button>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="wv-card p-3">
            <h3 className="wv-label mb-2">Active — {active.length}</h3>
            <div className="space-y-1">
              {active.length === 0 && <p className="text-xs text-text-tertiary">No active executions</p>}
              {active.map((e) => (
                <div key={e.envelope_id} className="flex items-center gap-2 py-0.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan animate-pulse" />
                  <span className="text-[11px] text-text-primary truncate flex-1">{e.intent}</span>
                  <span className="text-[10px] text-text-tertiary">{e.source}</span>
                </div>
              ))}
            </div>
          </section>

          <section className="wv-card p-3">
            <h3 className="wv-label mb-2">Completed — {completed.length}</h3>
            <div className="space-y-1">
              {completed.length === 0 && <p className="text-xs text-text-tertiary">No completed envelopes</p>}
              {completed.slice(0, 12).map((e) => (
                <div key={e.envelope_id} className="flex items-center gap-2 py-0.5">
                  <span className={`w-1.5 h-1.5 rounded-full ${STATUS_COLORS[e.status] ?? 'bg-text-tertiary'}`} />
                  <span className="text-[11px] text-text-primary truncate flex-1">{e.intent}</span>
                  <span className={`text-[10px] ${e.result_success ? 'text-ok' : 'text-danger'}`}>{e.status}</span>
                  {e.completed_at > 0 && e.started_at > 0 && (
                    <span className="text-[10px] text-text-tertiary font-mono">{formatDuration((e.completed_at - e.started_at) * 1000)}</span>
                  )}
                </div>
              ))}
            </div>
          </section>

          {/* Mutation Registry */}
          <section className="wv-card p-3">
            <h3 className="wv-label mb-2">Mutation Registry — {mutationList.length}</h3>
            <div className="space-y-1">
              {mutationList.length === 0 && <p className="text-xs text-text-tertiary">No mutations registered</p>}
              {mutationList.map((m) => (
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
          </section>
        </div>

        {/* Column 2: Gateway + Journal + EventSpine */}
        <div className="space-y-4">
          <section className="wv-card p-3">
            <h3 className="wv-label mb-2">Gateway Decisions</h3>
            {gateway && (
              <div className="flex gap-3 mb-2 text-[10px]">
                <span className="text-ok">{gateway.total_auto_executed} auto</span>
                <span className="text-danger">{gateway.total_blocked} blocked</span>
                <span className="text-warn">{gateway.total_recommended} recommend</span>
              </div>
            )}
            <div className="space-y-1">
              {gatewayDecisions.length === 0 && <p className="text-xs text-text-tertiary">No decisions recorded</p>}
              {gatewayDecisions.slice(0, 10).map((d, i) => (
                <div key={i} className="flex items-center gap-2 py-0.5">
                  <span className={`w-1.5 h-1.5 rounded-full ${d.action === 'allowed' ? 'bg-ok' : d.action === 'blocked' ? 'bg-danger' : 'bg-warn'}`} />
                  <span className="text-[11px] text-text-primary truncate flex-1">{d.intent}</span>
                  <span className={`text-[10px] ${SEVERITY_COLORS[d.risk_level] ?? 'text-text-tertiary'}`}>{d.risk_level}</span>
                  <span className="text-[10px] text-text-tertiary">{d.action}</span>
                </div>
              ))}
            </div>
          </section>

          <section className="wv-card p-3">
            <h3 className="wv-label mb-2">Execution Journal</h3>
            {journal && (
              <div className="flex gap-3 mb-2 text-[10px]">
                <span className="text-text-secondary">{journal.total_entries} entries</span>
                <span className="text-text-secondary">{journal.in_memory} in memory</span>
              </div>
            )}
            <div className="space-y-1">
              {journalRecent.length === 0 && <p className="text-xs text-text-tertiary">No journal entries</p>}
              {journalRecent.slice(0, 12).map((e, i) => (
                <div key={i} className="flex items-center gap-2 py-0.5">
                  <span className="text-[9px] font-mono text-text-tertiary w-16 shrink-0 truncate">{e.phase}</span>
                  <span className="text-[11px] text-text-primary truncate flex-1">{e.envelope_id.slice(0, 8)}</span>
                  <span className="text-[10px] text-text-tertiary">{e.source}</span>
                  <span className="text-[10px] text-text-tertiary">{relativeTime(new Date(e.timestamp * 1000).toISOString())}</span>
                </div>
              ))}
            </div>
          </section>

          {/* EventSpine Live Stream */}
          <section className="wv-card p-3">
            <h3 className="wv-label mb-2">Event Spine — {events.length} events</h3>
            <div className="space-y-0.5 max-h-64 overflow-y-auto">
              {events.length === 0 && <p className="text-xs text-text-tertiary">No events</p>}
              {events.slice(0, 30).map((ev) => (
                <div key={ev.event_id} className="flex items-center gap-1.5 py-0.5">
                  <span className={`text-[9px] font-mono w-16 shrink-0 truncate ${DOMAIN_COLORS[ev.domain] ?? 'text-text-tertiary'}`}>
                    {ev.domain}
                  </span>
                  <span className="text-[11px] text-text-primary truncate flex-1">
                    {ev.event_type}
                  </span>
                  <span className={`text-[9px] ${PRIORITY_COLORS[ev.priority] ?? 'text-text-tertiary'}`}>
                    {ev.priority !== 'normal' ? ev.priority : ''}
                  </span>
                  <span className="text-[10px] text-text-tertiary shrink-0">{ev.source}</span>
                  <span className="text-[10px] text-text-tertiary shrink-0">{relativeTime(new Date(ev.timestamp * 1000).toISOString())}</span>
                </div>
              ))}
            </div>
          </section>

          <section className="wv-card p-3">
            <h3 className="wv-label mb-2">Spine Guard</h3>
            {guard ? (
              <>
                <div className="flex gap-3 mb-2 text-[10px]">
                  <span className="text-cyan font-mono">{guard.mode.replace(/_/g, ' ').toUpperCase()}</span>
                  <span className="text-text-secondary">{guard.total_allowed} allowed</span>
                  <span className="text-danger">{guard.total_blocked} blocked</span>
                </div>
                <div className="space-y-1">
                  {guard.recent_violations.length === 0 && <p className="text-xs text-text-tertiary">No violations</p>}
                  {guard.recent_violations.slice(0, 5).map((v, i) => (
                    <div key={i} className="text-[10px] text-danger/80 truncate">{v.source}: {v.reason}</div>
                  ))}
                </div>
              </>
            ) : (
              <p className="text-xs text-text-tertiary">Guard not initialized</p>
            )}
          </section>
        </div>

        {/* Column 3: Topology + Leverage + Bottlenecks + Workloads */}
        <div className="space-y-4">
          {/* Runtime Topology */}
          <section className="wv-card p-3">
            <h3 className="wv-label mb-2">
              Runtime Topology — {runtimeGraph?.total_runtimes ?? 0} nodes · {runtimeGraph?.available ?? 0} available
            </h3>
            <div className="space-y-1.5">
              {runtimes.length === 0 && <p className="text-xs text-text-tertiary">No runtimes registered</p>}
              {runtimes.map((r) => (
                <div key={r.runtime_id} className="p-1.5 rounded bg-surface">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full shrink-0 ${RUNTIME_STATUS_COLORS[r.status] ?? 'bg-text-tertiary'}`} />
                    <span className="text-[11px] text-text-primary font-mono truncate flex-1">{r.runtime_id}</span>
                    <span className="text-[10px] text-text-tertiary">{r.runtime_class}</span>
                    <span className="text-[10px] font-mono text-cyan">{r.score.toFixed(3)}</span>
                  </div>
                  <div className="flex gap-2 mt-0.5 text-[9px] text-text-tertiary">
                    <span>{(r.reliability.success_rate * 100).toFixed(0)}% reliability</span>
                    <span>{r.reliability.avg_latency_ms.toFixed(0)}ms avg</span>
                    <span>{r.reliability.total_calls} calls</span>
                    {r.cost.subscription && <span className="text-ok">subscription</span>}
                  </div>
                  {r.capabilities.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1">
                      {r.capabilities.slice(0, 8).map((c) => (
                        <span key={c} className="text-[8px] font-mono px-1 py-0.5 rounded bg-canvas text-text-tertiary">{c}</span>
                      ))}
                      {r.capabilities.length > 8 && (
                        <span className="text-[8px] text-text-tertiary">+{r.capabilities.length - 8}</span>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </section>

          <section className="wv-card p-3">
            <h3 className="wv-label mb-2">Leverage</h3>
            {leverage ? (
              <div className="grid grid-cols-2 gap-2">
                <LeverageStat label="Tasks" value={`${totalTasks}`} />
                <LeverageStat label="Autonomous" value={`${autonomousTasks}`} />
                <LeverageStat label="Time Saved" value={`${timeSaved.toFixed(1)}h`} />
                <LeverageStat label="Composite" value={leverageRatio.toFixed(2)} />
                <LeverageStat label="Reliability" value={`${(leverage.dimensions.operational_reliability * 100).toFixed(0)}%`} />
                <LeverageStat label="Autonomy" value={`${(leverage.dimensions.execution_autonomy * 100).toFixed(0)}%`} />
              </div>
            ) : (
              <p className="text-xs text-text-tertiary">No leverage data</p>
            )}
          </section>

          <section className="wv-card p-3">
            <h3 className="wv-label mb-2">Bottlenecks — {bottlenecks.length}</h3>
            <div className="space-y-1.5">
              {bottlenecks.length === 0 && <p className="text-xs text-text-tertiary">No bottlenecks detected</p>}
              {bottlenecks.slice(0, 8).map((b, i) => (
                <div key={i} className="p-1.5 rounded bg-surface">
                  <div className="flex items-center gap-2">
                    <span className={`text-[10px] font-mono ${SEVERITY_COLORS[b.severity] ?? 'text-text-tertiary'}`}>{b.severity.toUpperCase()}</span>
                    <span className="text-[11px] text-text-primary truncate flex-1">{b.description}</span>
                  </div>
                  {b.suggested_correction && (
                    <p className="text-[10px] text-text-tertiary mt-0.5 truncate">fix: {b.suggested_correction}</p>
                  )}
                </div>
              ))}
            </div>
          </section>

          <section className="wv-card p-3">
            <h3 className="wv-label mb-2">Workloads</h3>
            {workloads ? (
              <>
                <div className="flex gap-3 mb-2 text-[10px]">
                  <span className="text-ok">{workloads.total_successes} ok</span>
                  <span className="text-danger">{workloads.total_failures} fail</span>
                  <span className="text-text-secondary">{workloads.total_runs} total</span>
                </div>
                <div className="space-y-1">
                  {workloads.recent_outcomes.map((o, i) => (
                    <div key={i} className="flex items-center gap-2 py-0.5">
                      <span className={`w-1.5 h-1.5 rounded-full ${o.success ? 'bg-ok' : 'bg-danger'}`} />
                      <span className="text-[11px] text-text-primary truncate flex-1">{o.workload_type}</span>
                      <span className="text-[10px] text-text-tertiary font-mono">{o.duration_seconds.toFixed(1)}s</span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <p className="text-xs text-text-tertiary">No workload data</p>
            )}
          </section>
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
    <div className="wv-card px-2.5 py-2 text-center">
      <div className="wv-label mb-1">{label}</div>
      <div className={`text-sm font-mono font-semibold ${colorClass}`}>{value}</div>
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
