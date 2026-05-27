import { useSystemStore } from '../stores/systemStore'
import { useApprovalStore } from '../stores/approvalStore'
import { usePolling } from '../hooks/usePolling'
import { useCockpitStore } from '../stores/cockpitStore'
import { relativeTime, formatUptime, formatDuration } from '../lib/time'

export function DashboardPanel() {
  const pulse = useSystemStore((s) => s.pulse)
  const meshNodes = useSystemStore((s) => s.meshNodes)
  const models = useSystemStore((s) => s.models)
  const traces = useSystemStore((s) => s.traces)
  const infraNodes = useSystemStore((s) => s.infraNodes)
  const fetchPulse = useSystemStore((s) => s.fetchPulse)
  const fetchMeshNodes = useSystemStore((s) => s.fetchMeshNodes)
  const fetchModels = useSystemStore((s) => s.fetchModels)
  const fetchTraces = useSystemStore((s) => s.fetchTraces)
  const fetchInfra = useSystemStore((s) => s.fetchInfra)
  const approvals = useApprovalStore((s) => s.approvals)
  const fetchApprovals = useApprovalStore((s) => s.fetchApprovals)
  const approve = useApprovalStore((s) => s.approve)
  const deny = useApprovalStore((s) => s.deny)
  const setApiStatus = useCockpitStore((s) => s.setApiStatus)

  usePolling(async () => {
    try {
      await fetchPulse()
      setApiStatus('connected')
    } catch {
      setApiStatus('disconnected')
    }
  }, 3000)

  usePolling(() => { fetchMeshNodes(); fetchModels(); fetchInfra() }, 10000)
  usePolling(() => { fetchTraces(); fetchApprovals() }, 5000)

  const pendingApprovals = approvals.filter((a) => a.status === 'pending')

  return (
    <div className="flex flex-col h-full overflow-y-auto p-4">
      {/* Header */}
      <div className="flex items-center mb-4">
        <h2 className="text-lg font-semibold text-text-primary">Command Center</h2>
        <span className="ml-2 text-xs text-text-tertiary">system intelligence overview</span>
      </div>

      {/* Pulse Panel — 7-column KPI strip */}
      <section className="mb-6">
        <h3 className="wv-label mb-3">System Pulse</h3>
        <div className="grid grid-cols-7 gap-2">
          <PulseMetric label="CPU" value={`${pulse?.cpu_percent?.toFixed(0) ?? '—'}%`} severity={pulseSeverity(pulse?.cpu_percent)} />
          <PulseMetric label="RAM" value={`${pulse?.memory_percent?.toFixed(0) ?? '—'}%`} severity={pulseSeverity(pulse?.memory_percent)} />
          <PulseMetric label="DISK" value={`${pulse?.disk_percent?.toFixed(0) ?? '—'}%`} severity={pulseSeverity(pulse?.disk_percent)} />
          <PulseMetric label="AGENTS" value={`${pulse?.active_agents ?? 0}`} severity="cyan" />
          <PulseMetric label="PENDING" value={`${pulse?.pending_tasks ?? 0}`} severity="warn" />
          <PulseMetric label="APPROVALS" value={`${pulse?.pending_approvals ?? 0}`} severity={pendingApprovals.length > 0 ? 'danger' : 'ok'} />
          <PulseMetric label="UPTIME" value={pulse?.uptime ? formatUptime(pulse.uptime) : '—'} severity="cyan" />
        </div>
      </section>

      {/* Two-column grid: Models + Traces | Approvals + Infra */}
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

          {/* Trace Stream */}
          <section className="wv-card p-3">
            <h3 className="wv-label mb-2">Recent Traces</h3>
            <div className="space-y-1">
              {traces.length === 0 && <p className="text-xs text-text-tertiary">No traces recorded</p>}
              {traces.slice(0, 8).map((t) => (
                <div key={t.id} className="flex items-center gap-2 py-0.5">
                  <span className={`w-1.5 h-1.5 rounded-full ${traceStatusColor(t.status)}`} />
                  <span className="text-[11px] text-text-primary truncate flex-1">{t.action}</span>
                  <span className="text-[10px] text-text-tertiary">{t.agent}</span>
                  {t.durationMs && <span className="text-[10px] text-text-secondary font-mono">{formatDuration(t.durationMs)}</span>}
                  <span className="text-[10px] text-text-tertiary">{relativeTime(t.timestamp)}</span>
                </div>
              ))}
            </div>
          </section>
        </div>

        {/* Right column */}
        <div className="space-y-4">
          {/* Approval Queue */}
          <section className="wv-card p-3">
            <h3 className="wv-label mb-2">Approval Queue — {pendingApprovals.length} pending</h3>
            <div className="space-y-2">
              {pendingApprovals.length === 0 && <p className="text-xs text-text-tertiary">All clear</p>}
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

          {/* Infrastructure Quick */}
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

function traceStatusColor(status: string): string {
  return status === 'running' ? 'bg-cyan'
    : status === 'completed' ? 'bg-ok'
    : status === 'failed' ? 'bg-danger'
    : 'bg-text-tertiary'
}

function riskColor(level: string): string {
  return level === 'CRITICAL' ? 'danger'
    : level === 'HIGH' ? 'danger'
    : level === 'MEDIUM' ? 'warn'
    : 'ok'
}
