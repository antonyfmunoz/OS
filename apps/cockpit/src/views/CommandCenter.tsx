import { useCockpitStore } from '../stores/cockpitStore.ts'
import { relativeTime, formatDuration, formatUptime } from '../lib/time.ts'
import { clsx } from 'clsx'

function PulsePanel() {
  const { pulse } = useCockpitStore()
  const metrics = [
    { label: 'UPTIME', value: formatUptime(pulse.uptime), color: 'text-text-primary' },
    { label: 'CPU', value: `${pulse.cpuPercent}%`, color: pulse.cpuPercent > 80 ? 'text-danger' : pulse.cpuPercent > 60 ? 'text-warn' : 'text-ok' },
    { label: 'MEMORY', value: `${pulse.memoryPercent}%`, color: pulse.memoryPercent > 80 ? 'text-danger' : pulse.memoryPercent > 60 ? 'text-warn' : 'text-ok' },
    { label: 'AGENTS', value: String(pulse.activeAgents), color: 'text-cyan' },
    { label: 'TASKS', value: String(pulse.pendingTasks), color: 'text-text-primary' },
    { label: 'APPROVALS', value: String(pulse.pendingApprovals), color: pulse.pendingApprovals > 0 ? 'text-warn' : 'text-ok' },
    { label: 'TRACE/s', value: pulse.traceRate.toFixed(1), color: 'text-cyan' },
  ]

  return (
    <div className="wv-card p-4">
      <div className="wv-label mb-3">SYSTEM PULSE</div>
      <div className="grid grid-cols-7 gap-4">
        {metrics.map((m) => (
          <div key={m.label} className="text-center">
            <div className={clsx('wv-metric', m.color)}>{m.value}</div>
            <div className="wv-label mt-1">{m.label}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

function ModelBadges() {
  const { models } = useCockpitStore()
  const statusColor = {
    active: 'wv-badge-ok',
    fallback: 'wv-badge-warn',
    offline: 'wv-badge-danger',
    degraded: 'wv-badge-danger',
  }

  return (
    <div className="wv-card p-4">
      <div className="wv-label mb-3">MODEL ROSTER</div>
      <div className="space-y-2">
        {models.map((m) => (
          <div key={m.id} className="flex items-center justify-between py-1">
            <div className="flex items-center gap-3">
              <span className={clsx('wv-badge', statusColor[m.status])}>
                {m.status}
              </span>
              <span className="text-text-primary text-[12px]">{m.name}</span>
              <span className="text-text-tertiary text-[10px]">{m.provider}</span>
            </div>
            <div className="flex items-center gap-4 text-[11px] text-text-secondary">
              <span>{m.latencyMs}ms</span>
              <span>${m.costPerMToken}/MT</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function TraceStream() {
  const { traces } = useCockpitStore()
  const statusIcon = {
    running: '◉',
    completed: '✓',
    failed: '✗',
    pending: '○',
  }
  const statusColor = {
    running: 'text-cyan',
    completed: 'text-ok',
    failed: 'text-danger',
    pending: 'text-text-tertiary',
  }

  return (
    <div className="wv-card p-4 flex-1 overflow-hidden flex flex-col">
      <div className="wv-label mb-3">TRACE STREAM</div>
      <div className="flex-1 overflow-y-auto space-y-1">
        {traces.map((t) => (
          <div key={t.id} className="flex items-center gap-3 py-1 text-[11px] font-mono border-b border-border/50">
            <span className={clsx('w-4 text-center', statusColor[t.status])}>
              {statusIcon[t.status]}
            </span>
            <span className="text-text-tertiary w-12 shrink-0">{relativeTime(t.timestamp)}</span>
            <span className="text-cyan w-20 shrink-0 truncate">{t.agent}</span>
            <span className="text-text-primary flex-1 truncate">{t.action}</span>
            {t.durationMs != null && (
              <span className="text-text-tertiary shrink-0">{formatDuration(t.durationMs)}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function ApprovalQueue() {
  const { approvals, updateApproval } = useCockpitStore()
  const pending = approvals.filter((a) => a.status === 'pending')
  const riskColor = {
    low: 'wv-badge-ok',
    medium: 'wv-badge-warn',
    high: 'wv-badge-danger',
    critical: 'wv-badge-violet',
  }

  return (
    <div className="wv-card p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="wv-label">APPROVAL QUEUE</span>
        {pending.length > 0 && (
          <span className="wv-badge wv-badge-warn">{pending.length} pending</span>
        )}
      </div>
      <div className="space-y-2">
        {pending.length === 0 && (
          <div className="text-text-tertiary text-[11px] text-center py-4">No pending approvals</div>
        )}
        {pending.map((a) => (
          <div key={a.id} className="wv-card-raised p-3">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[12px] text-text-primary">{a.title}</span>
              <span className={clsx('wv-badge', riskColor[a.riskLevel])}>{a.riskLevel}</span>
            </div>
            <div className="text-[10px] text-text-tertiary mb-2">
              {a.agent} · {relativeTime(a.createdAt)}
            </div>
            <div className="text-[11px] text-text-secondary mb-3">{a.description}</div>
            <div className="flex gap-2">
              <button
                onClick={() => updateApproval(a.id, 'approved')}
                className="px-3 py-1 text-[10px] font-mono uppercase tracking-wider bg-ok/10 text-ok border border-ok-dim hover:bg-ok/20 transition-colors"
              >
                Approve
              </button>
              <button
                onClick={() => updateApproval(a.id, 'denied')}
                className="px-3 py-1 text-[10px] font-mono uppercase tracking-wider bg-danger/10 text-danger border border-danger-dim hover:bg-danger/20 transition-colors"
              >
                Deny
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export function CommandCenter() {
  return (
    <div className="h-full flex flex-col gap-4 p-4 overflow-y-auto">
      <div className="flex items-center justify-between">
        <h1 className="text-[14px] font-mono uppercase tracking-widest text-text-secondary">
          Command Center
        </h1>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-ok wv-pulse" />
          <span className="text-[10px] font-mono text-text-tertiary uppercase">Live</span>
        </div>
      </div>
      <PulsePanel />
      <div className="grid grid-cols-2 gap-4 flex-1 min-h-0">
        <div className="flex flex-col gap-4">
          <ModelBadges />
          <TraceStream />
        </div>
        <div className="flex flex-col gap-4">
          <ApprovalQueue />
        </div>
      </div>
    </div>
  )
}
