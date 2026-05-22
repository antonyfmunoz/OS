import { useState } from 'react'
import { useCockpitStore } from '../stores/cockpitStore.ts'
import { api } from '../api/client.ts'
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

function SignalInput() {
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [lastResult, setLastResult] = useState<{ delegated_to: string; trace_id: string | null } | null>(null)

  const handleSubmit = async () => {
    if (!input.trim() || sending) return
    setSending(true)
    try {
      const res = await api.organismSignal(input.trim())
      setLastResult({ delegated_to: res.delegated_to, trace_id: res.trace_id })
      setInput('')
      useCockpitStore.getState().fetchAll()
    } catch {
      setLastResult(null)
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="wv-card p-4">
      <div className="wv-label mb-2">SIGNAL INPUT</div>
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
          placeholder="Send a signal to DEX..."
          className="flex-1 bg-surface border border-border text-text-primary text-[12px] font-mono px-3 py-2 focus:outline-none focus:border-cyan"
          disabled={sending}
        />
        <button
          onClick={handleSubmit}
          disabled={sending || !input.trim()}
          className="px-4 py-2 text-[10px] font-mono uppercase tracking-wider bg-cyan/10 text-cyan border border-cyan-dim hover:bg-cyan/20 transition-colors disabled:opacity-40"
        >
          {sending ? 'Sending...' : 'Send'}
        </button>
      </div>
      {lastResult && (
        <div className="mt-2 text-[10px] text-text-tertiary">
          Delegated to <span className="text-cyan">{lastResult.delegated_to}</span>
          {lastResult.trace_id && <span> (trace: {lastResult.trace_id.slice(0, 8)}...)</span>}
        </div>
      )}
    </div>
  )
}

function AgentActivity() {
  const { organismAgents, organismDeliverables, organismRunning } = useCockpitStore()

  const statusDot: Record<string, string> = {
    idle: 'bg-text-tertiary',
    working: 'bg-cyan wv-pulse',
    critiquing: 'bg-warn wv-pulse',
    blocked: 'bg-danger',
    offline: 'bg-border',
  }

  const statusBadge: Record<string, string> = {
    idle: 'wv-badge-ok',
    working: 'wv-badge-cyan',
    critiquing: 'wv-badge-warn',
    blocked: 'wv-badge-danger',
    offline: 'wv-badge-danger',
  }

  return (
    <div className="wv-card p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="wv-label">ORGANISM</span>
        <span className={clsx('wv-badge', organismRunning ? 'wv-badge-ok' : 'wv-badge-danger')}>
          {organismRunning ? 'running' : 'stopped'}
        </span>
      </div>
      <div className="space-y-2 mb-4">
        {organismAgents.map((a) => (
          <div key={a.agent_id} className="flex items-center justify-between py-1">
            <div className="flex items-center gap-2">
              <span className={clsx('w-2 h-2 rounded-full', statusDot[a.status] ?? 'bg-border')} />
              <span className="text-[12px] text-text-primary font-mono">{a.agent_name}</span>
              <span className={clsx('wv-badge', statusBadge[a.status] ?? 'wv-badge-danger')}>{a.status}</span>
            </div>
            <span className="text-[10px] text-text-tertiary">{a.tasks_completed} tasks</span>
          </div>
        ))}
        {organismAgents.length === 0 && (
          <div className="text-[10px] text-text-tertiary text-center py-2">No agents registered</div>
        )}
      </div>
      {organismDeliverables.length > 0 && (
        <>
          <div className="wv-label mb-2">RECENT DELIVERABLES</div>
          <div className="space-y-2">
            {organismDeliverables.slice(-3).reverse().map((d) => (
              <div key={d.id} className="wv-card-raised p-2">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[10px] text-cyan font-mono">{d.agent_id}</span>
                  <span className={clsx('wv-badge', d.self_critique?.passed ? 'wv-badge-ok' : 'wv-badge-warn')}>
                    {d.self_critique?.score ?? '?'}/10
                  </span>
                </div>
                <div className="text-[11px] text-text-secondary truncate">{d.content}</div>
              </div>
            ))}
          </div>
        </>
      )}
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
      <SignalInput />
      <PulsePanel />
      <div className="grid grid-cols-2 gap-4 flex-1 min-h-0">
        <div className="flex flex-col gap-4">
          <AgentActivity />
          <ModelBadges />
        </div>
        <div className="flex flex-col gap-4">
          <ApprovalQueue />
          <TraceStream />
        </div>
      </div>
    </div>
  )
}
