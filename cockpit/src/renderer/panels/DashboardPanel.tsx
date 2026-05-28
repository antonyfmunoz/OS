import { useSystemStore } from '../stores/systemStore'
import { useApprovalStore } from '../stores/approvalStore'
import { useOrganismStore } from '../stores/organismStore'
import { usePolling } from '../hooks/usePolling'
import { useCockpitStore } from '../stores/cockpitStore'
import { relativeTime, formatUptime, formatDuration } from '../lib/time'

export function DashboardPanel() {
  const pulse = useSystemStore((s) => s.pulse)
  const meshNodes = useSystemStore((s) => s.meshNodes)
  const models = useSystemStore((s) => s.models)
  const infraNodes = useSystemStore((s) => s.infraNodes)
  const fetchPulse = useSystemStore((s) => s.fetchPulse)
  const fetchMeshNodes = useSystemStore((s) => s.fetchMeshNodes)
  const fetchModels = useSystemStore((s) => s.fetchModels)
  const fetchInfra = useSystemStore((s) => s.fetchInfra)
  const approvals = useApprovalStore((s) => s.approvals)
  const fetchApprovals = useApprovalStore((s) => s.fetchApprovals)
  const approve = useApprovalStore((s) => s.approve)
  const deny = useApprovalStore((s) => s.deny)
  const setApiStatus = useCockpitStore((s) => s.setApiStatus)

  const spine = useOrganismStore((s) => s.spine)
  const pending = useOrganismStore((s) => s.pendingEnvelopes)
  const completed = useOrganismStore((s) => s.completedEnvelopes)
  const guard = useOrganismStore((s) => s.guard)
  const gateway = useOrganismStore((s) => s.gateway)
  const leverage = useOrganismStore((s) => s.leverage)
  const executionMode = useOrganismStore((s) => s.executionMode)
  const bottleneckStatus = useOrganismStore((s) => s.bottleneckStatus)
  const workloads = useOrganismStore((s) => s.workloads)
  const fetchAll = useOrganismStore((s) => s.fetchAll)
  const approveEnvelope = useOrganismStore((s) => s.approveEnvelope)
  const rejectEnvelope = useOrganismStore((s) => s.rejectEnvelope)

  usePolling(async () => {
    try {
      await fetchPulse()
      setApiStatus('connected')
    } catch {
      setApiStatus('disconnected')
    }
  }, 3000)

  usePolling(() => { fetchMeshNodes(); fetchModels(); fetchInfra() }, 10000)
  usePolling(() => { fetchApprovals(); fetchAll() }, 5000)

  const pendingApprovals = approvals.filter((a) => a.status === 'pending')
  const totalPending = pendingApprovals.length + pending.length

  return (
    <div className="flex flex-col h-full overflow-y-auto p-4">
      <div className="flex items-center mb-4">
        <h2 className="text-lg font-semibold text-text-primary">Command Center</h2>
        <span className="ml-2 text-xs text-text-tertiary">system intelligence overview</span>
      </div>

      {/* Pulse Panel — 8-column KPI strip with organism data */}
      <section className="mb-5">
        <h3 className="wv-label mb-3">System Pulse</h3>
        <div className="grid grid-cols-8 gap-2">
          <PulseMetric label="CPU" value={`${pulse?.cpu_percent?.toFixed(0) ?? '—'}%`} severity={pulseSeverity(pulse?.cpu_percent)} />
          <PulseMetric label="RAM" value={`${pulse?.memory_percent?.toFixed(0) ?? '—'}%`} severity={pulseSeverity(pulse?.memory_percent)} />
          <PulseMetric label="DISK" value={`${pulse?.disk_percent?.toFixed(0) ?? '—'}%`} severity={pulseSeverity(pulse?.disk_percent)} />
          <PulseMetric label="MODE" value={executionMode?.current_mode?.toUpperCase() ?? 'OBSERVE'} severity="cyan" />
          <PulseMetric label="GUARD" value={guard?.mode?.replace('_', ' ')?.toUpperCase() ?? '—'} severity="cyan" />
          <PulseMetric label="SUCCESS" value={spine ? `${((spine.success_rate ?? 0) * 100).toFixed(0)}%` : '—'} severity={spine && spine.success_rate > 0.9 ? 'ok' : spine && spine.success_rate > 0.7 ? 'warn' : 'cyan'} />
          <PulseMetric label="PENDING" value={`${totalPending}`} severity={totalPending > 0 ? 'danger' : 'ok'} />
          <PulseMetric label="UPTIME" value={pulse?.uptime ? formatUptime(pulse.uptime) : '—'} severity="cyan" />
        </div>
      </section>

      {/* Organism status strip */}
      {(spine || leverage) && (
        <section className="mb-5">
          <div className="grid grid-cols-6 gap-2">
            <MiniStat label="Executed" value={`${spine?.total_executed ?? 0}`} />
            <MiniStat label="Succeeded" value={`${spine?.total_succeeded ?? 0}`} />
            <MiniStat label="Failed" value={`${spine?.total_failed ?? 0}`} />
            <MiniStat label="Composite" value={leverage ? leverage.dimensions.composite.toFixed(2) : '—'} />
            <MiniStat label="Time Saved" value={leverage ? `${(leverage.totals.operator_seconds_saved / 3600).toFixed(1)}h` : '—'} />
            <MiniStat label="Gateway" value={gateway?.policy?.toUpperCase() ?? '—'} />
          </div>
        </section>
      )}

      <div className="grid grid-cols-2 gap-4 flex-1">
        {/* Left column */}
        <div className="space-y-4">
          {/* Model Badges */}
          <section className="wv-card p-3">
            <h3 className="wv-label mb-2">Intelligence Models</h3>
            <div className="space-y-1.5">
              {models.length === 0 && <p className="text-xs text-text-tertiary">No models registered</p>}
              {models.map((m) => (
                <div key={m.id} className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${modelStatusColor(m.status)}`} />
                  <span className="text-xs text-text-primary font-mono flex-1 truncate">{m.name}</span>
                  <span className="text-[10px] text-text-tertiary">{m.provider}</span>
                  <span className="text-[10px] text-text-secondary font-mono">{m.latency_ms}ms</span>
                </div>
              ))}
            </div>
          </section>

          {/* Recent Spine Completions (replaces empty traces) */}
          <section className="wv-card p-3">
            <h3 className="wv-label mb-2">Recent Executions</h3>
            <div className="space-y-1">
              {completed.length === 0 && <p className="text-xs text-text-tertiary">No executions recorded</p>}
              {completed.slice(0, 8).map((e) => (
                <div key={e.envelope_id} className="flex items-center gap-2 py-0.5">
                  <span className={`w-1.5 h-1.5 rounded-full ${e.result_success ? 'bg-ok' : 'bg-danger'}`} />
                  <span className="text-[11px] text-text-primary truncate flex-1">{e.intent}</span>
                  <span className="text-[10px] text-text-tertiary">{e.source}</span>
                  {e.completed_at > 0 && e.started_at > 0 && (
                    <span className="text-[10px] text-text-secondary font-mono">
                      {formatDuration((e.completed_at - e.started_at) * 1000)}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </section>

          {/* Bottlenecks */}
          {(bottleneckStatus?.active?.length ?? 0) > 0 && (
            <section className="wv-card p-3">
              <h3 className="wv-label mb-2">Bottlenecks — {bottleneckStatus!.active.length}</h3>
              <div className="space-y-1.5">
                {bottleneckStatus!.active.slice(0, 5).map((b, i) => (
                  <div key={i} className="flex items-center gap-2 py-0.5">
                    <span className={`text-[10px] font-mono ${
                      b.severity === 'critical' || b.severity === 'high' ? 'text-danger' : 'text-warn'
                    }`}>
                      {b.severity.toUpperCase()}
                    </span>
                    <span className="text-[11px] text-text-primary truncate flex-1">{b.description}</span>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>

        {/* Right column */}
        <div className="space-y-4">
          {/* Unified Approval Queue: legacy approvals + spine pending */}
          <section className="wv-card p-3">
            <h3 className="wv-label mb-2">Approval Queue — {totalPending} pending</h3>
            <div className="space-y-2">
              {totalPending === 0 && <p className="text-xs text-text-tertiary">All clear</p>}

              {/* Spine pending envelopes */}
              {pending.slice(0, 5).map((e) => (
                <div key={e.envelope_id} className="p-2 rounded bg-surface border border-border">
                  <div className="flex items-start gap-2">
                    <span className={`wv-badge ${riskBadge(e.risk_level)} shrink-0`}>
                      {e.risk_level.toUpperCase()}
                    </span>
                    <p className="text-[11px] text-text-primary flex-1">{e.intent}</p>
                  </div>
                  <div className="flex items-center mt-1.5 gap-2">
                    <span className="text-[10px] text-text-tertiary flex-1">{e.source} · {e.action_type}</span>
                    <button onClick={() => approveEnvelope(e.envelope_id)} className="px-2 py-0.5 text-[10px] font-mono rounded bg-ok/10 text-ok border border-ok/30">
                      approve
                    </button>
                    <button onClick={() => rejectEnvelope(e.envelope_id)} className="px-2 py-0.5 text-[10px] font-mono rounded bg-danger/10 text-danger border border-danger/30">
                      reject
                    </button>
                  </div>
                </div>
              ))}

              {/* Legacy approvals */}
              {pendingApprovals.slice(0, 5).map((a) => (
                <div key={a.id} className="p-2 rounded bg-surface border border-border">
                  <div className="flex items-start gap-2">
                    <span className={`wv-badge wv-badge-${riskColor(a.risk_level)} shrink-0`}>
                      {a.risk_level}
                    </span>
                    <p className="text-[11px] text-text-primary flex-1">{a.description}</p>
                  </div>
                  <div className="flex items-center mt-1.5 gap-2">
                    <span className="text-[10px] text-text-tertiary flex-1">{a.agent} · {relativeTime(a.created_at)}</span>
                    <button onClick={() => approve(a.id)} className="px-2 py-0.5 text-[10px] font-mono rounded bg-ok/10 text-ok border border-ok/30">
                      approve
                    </button>
                    <button onClick={() => deny(a.id)} className="px-2 py-0.5 text-[10px] font-mono rounded bg-danger/10 text-danger border border-danger/30">
                      deny
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Infrastructure + Workloads */}
          <section className="wv-card p-3">
            <h3 className="wv-label mb-2">Infrastructure — {meshNodes.length + infraNodes.length} nodes</h3>
            <div className="space-y-1.5">
              {meshNodes.map((n) => (
                <div key={n.node_id} className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${n.status === 'online' ? 'bg-ok' : 'bg-danger'}`} />
                  <span className="text-xs text-text-primary font-mono truncate flex-1">{n.hostname}</span>
                  <span className="text-[10px] text-text-tertiary">{n.role}</span>
                </div>
              ))}
              {infraNodes.slice(0, 4).map((s) => (
                <div key={s.id} className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${
                    s.status === 'healthy' ? 'bg-ok' : s.status === 'degraded' ? 'bg-warn' : 'bg-danger'
                  }`} />
                  <span className="text-xs text-text-primary font-mono truncate flex-1">{s.name}</span>
                  <span className="text-[10px] text-text-tertiary">{s.type}</span>
                </div>
              ))}
              {meshNodes.length === 0 && infraNodes.length === 0 && (
                <p className="text-xs text-text-tertiary">No infrastructure connected</p>
              )}
            </div>
          </section>

          {/* Workload quick */}
          {workloads && workloads.total_runs > 0 && (
            <section className="wv-card p-3">
              <h3 className="wv-label mb-2">
                Workloads — {workloads.total_runs} runs · {(workloads.success_rate * 100).toFixed(0)}% success
              </h3>
              <div className="space-y-1">
                {workloads.recent_outcomes.slice(0, 5).map((o, i) => (
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

function PulseMetric({ label, value, severity }: { label: string; value: string; severity: string }) {
  const colorClass = severity === 'cyan' ? 'text-cyan'
    : severity === 'ok' ? 'text-ok'
    : severity === 'warn' ? 'text-warn'
    : severity === 'danger' ? 'text-danger'
    : 'text-text-primary'

  return (
    <div className="wv-card px-3 py-2 text-center">
      <div className="wv-label mb-1">{label}</div>
      <div className={`text-sm font-mono font-semibold ${colorClass}`}>{value}</div>
    </div>
  )
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="wv-card px-2 py-1.5 text-center">
      <div className="text-[9px] text-text-tertiary uppercase">{label}</div>
      <div className="text-xs font-mono text-text-primary">{value}</div>
    </div>
  )
}

function pulseSeverity(v: number | undefined): string {
  if (v === undefined) return 'cyan'
  if (v > 90) return 'danger'
  if (v > 70) return 'warn'
  return 'ok'
}

function modelStatusColor(status: string): string {
  return status === 'active' ? 'bg-ok'
    : status === 'fallback' ? 'bg-warn'
    : status === 'degraded' ? 'bg-warn'
    : 'bg-danger'
}

function riskBadge(level: string): string {
  return level === 'critical' || level === 'high' ? 'wv-badge-danger'
    : level === 'medium' ? 'wv-badge-warn'
    : 'wv-badge-ok'
}

function riskColor(level: string): string {
  return level === 'CRITICAL' ? 'danger'
    : level === 'HIGH' ? 'danger'
    : level === 'MEDIUM' ? 'warn'
    : 'ok'
}
