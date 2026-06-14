import { useState, useEffect, useCallback } from 'react'
import { useCockpitStore } from '../stores/cockpitStore'

interface ExecutionPlan {
  execution_plan_id: string
  source_workpacket_id: string
  profile_id: string
  session_id: string
  target_executor: string
  execution_mode: string
  approval_state: string
  priority: string
  risk_class: string
  status: string
  description: string
  created_at: number
  approved_at: number | null
  dispatched_at: number | null
  started_at: number | null
  completed_at: number | null
  failed_at: number | null
  cancelled_at: number | null
  failure_reason: string
  proof_id: string
}

interface LifecycleEvent {
  event_id: string
  execution_plan_id: string
  event_type: string
  timestamp: number
  summary: string
}

interface ExecutorDef {
  executor_id: string
  executor_type: string
  name: string
  description: string
  capabilities: string[]
  available: boolean
}

interface CoordState {
  snapshot: {
    total_plans: number
    by_status: Record<string, number>
    queue_depth: number
    active_count: number
    executor_count: number
    awaiting_approval: number
  }
  queue: ExecutionPlan[]
  active: ExecutionPlan[]
  awaiting_approval: ExecutionPlan[]
  history: ExecutionPlan[]
  lifecycle: LifecycleEvent[]
  executors: ExecutorDef[]
}

type Tab = 'queue' | 'active' | 'approval' | 'history' | 'executors'

function KpiCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-surface-elevated border border-border rounded px-3 py-2 text-center min-w-[100px]">
      <div className="text-lg font-mono font-bold text-foreground">{value}</div>
      <div className="text-xs text-muted uppercase tracking-wide">{label}</div>
    </div>
  )
}

function getStatusColor(status: string): string {
  switch (status) {
    case 'drafted': return 'text-muted'
    case 'approved': return 'text-blue-400'
    case 'queued': return 'text-yellow-400'
    case 'dispatched': return 'text-cyan-400'
    case 'executing': return 'text-green-400'
    case 'completed': return 'text-emerald-400'
    case 'failed': return 'text-red-400'
    case 'cancelled': return 'text-gray-500'
    default: return 'text-foreground'
  }
}

function getPriorityColor(priority: string): string {
  switch (priority) {
    case 'critical': return 'text-red-400'
    case 'high': return 'text-orange-400'
    case 'normal': return 'text-foreground'
    case 'low': return 'text-muted'
    case 'background': return 'text-gray-600'
    default: return 'text-foreground'
  }
}

function getRiskColor(risk: string): string {
  switch (risk) {
    case 'critical': return 'text-red-500'
    case 'high': return 'text-orange-500'
    case 'medium': return 'text-yellow-500'
    case 'low': return 'text-green-500'
    case 'negligible': return 'text-gray-500'
    default: return 'text-foreground'
  }
}

function formatTimestamp(ts: number | null): string {
  if (!ts) return '—'
  return new Date(ts * 1000).toLocaleString()
}

function getTargetIcon(target: string): string {
  switch (target) {
    case 'workstation': return '[WS]'
    case 'agent': return '[AG]'
    case 'vps': return '[VP]'
    case 'container': return '[CT]'
    case 'browser': return '[BR]'
    case 'mobile': return '[MB]'
    case 'external': return '[EX]'
    default: return '[??]'
  }
}

function PlanCard({ plan, onApprove, onDeny, onEnqueue, onCancel }: {
  plan: ExecutionPlan
  onApprove?: (id: string) => void
  onDeny?: (id: string) => void
  onEnqueue?: (id: string) => void
  onCancel?: (id: string) => void
}) {
  return (
    <div className="bg-surface-elevated border border-border rounded-lg p-3 mb-2">
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs text-muted">{plan.execution_plan_id.slice(0, 16)}</span>
          <span className={`text-xs font-semibold uppercase ${getStatusColor(plan.status)}`}>{plan.status}</span>
          <span className={`text-xs ${getPriorityColor(plan.priority)}`}>{plan.priority}</span>
        </div>
        <span className="font-mono text-xs text-muted">{getTargetIcon(plan.target_executor)} {plan.target_executor}</span>
      </div>
      {plan.description && (
        <div className="text-sm text-foreground mb-1">{plan.description}</div>
      )}
      <div className="flex items-center gap-3 text-xs text-muted mb-1">
        <span>WP: {plan.source_workpacket_id.slice(0, 16)}</span>
        {plan.profile_id && <span>Profile: {plan.profile_id}</span>}
        {plan.session_id && <span>Session: {plan.session_id.slice(0, 16)}</span>}
        <span className={getRiskColor(plan.risk_class)}>Risk: {plan.risk_class}</span>
      </div>
      <div className="text-xs text-muted">
        Created: {formatTimestamp(plan.created_at)}
        {plan.failure_reason && <span className="text-red-400 ml-2">Reason: {plan.failure_reason}</span>}
        {plan.proof_id && <span className="text-emerald-400 ml-2">Proof: {plan.proof_id}</span>}
      </div>
      <div className="flex gap-2 mt-2">
        {plan.approval_state === 'pending' && onApprove && (
          <button onClick={() => onApprove(plan.execution_plan_id)} className="text-xs px-2 py-1 bg-green-700 hover:bg-green-600 text-white rounded">Approve</button>
        )}
        {plan.approval_state === 'pending' && onDeny && (
          <button onClick={() => onDeny(plan.execution_plan_id)} className="text-xs px-2 py-1 bg-red-700 hover:bg-red-600 text-white rounded">Deny</button>
        )}
        {plan.approval_state === 'approved' && plan.status === 'approved' && onEnqueue && (
          <button onClick={() => onEnqueue(plan.execution_plan_id)} className="text-xs px-2 py-1 bg-blue-700 hover:bg-blue-600 text-white rounded">Enqueue</button>
        )}
        {!['completed', 'failed', 'cancelled'].includes(plan.status) && onCancel && (
          <button onClick={() => onCancel(plan.execution_plan_id)} className="text-xs px-2 py-1 bg-gray-700 hover:bg-gray-600 text-white rounded">Cancel</button>
        )}
      </div>
    </div>
  )
}

export function ExecCoordPanel() {
  const apiBase = useCockpitStore(s => s.apiBase)
  const [tab, setTab] = useState<Tab>('queue')
  const [state, setState] = useState<CoordState | null>(null)
  const [error, setError] = useState<string | null>(null)

  const fetchState = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/execcoord/state`)
      if (!res.ok) throw new Error(`${res.status}`)
      const data = await res.json()
      setState(data)
      setError(null)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'fetch failed')
    }
  }, [apiBase])

  useEffect(() => {
    fetchState()
    const id = setInterval(fetchState, 15000)
    return () => clearInterval(id)
  }, [fetchState])

  const postAction = async (path: string, body: Record<string, string> = {}) => {
    try {
      await fetch(`${apiBase}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      await fetchState()
    } catch {}
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: 'queue', label: 'Queue' },
    { key: 'active', label: 'Active' },
    { key: 'approval', label: 'Waiting Approval' },
    { key: 'history', label: 'History' },
    { key: 'executors', label: 'Executors' },
  ]

  if (error) {
    return <div className="p-4 text-red-400">Execution Coordinator: {error}</div>
  }

  const snap = state?.snapshot

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <div className="p-3 border-b border-border">
        <h2 className="text-sm font-semibold text-foreground mb-2 uppercase tracking-wide">Execution Coordinator</h2>
        {snap && (
          <div className="flex gap-2 flex-wrap">
            <KpiCard label="Total Plans" value={snap.total_plans} />
            <KpiCard label="Queue" value={snap.queue_depth} />
            <KpiCard label="Active" value={snap.active_count} />
            <KpiCard label="Awaiting" value={snap.awaiting_approval} />
            <KpiCard label="Executors" value={snap.executor_count} />
          </div>
        )}
      </div>

      <div className="flex border-b border-border">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-3 py-2 text-xs font-medium transition-colors ${
              tab === t.key
                ? 'text-foreground border-b-2 border-accent'
                : 'text-muted hover:text-foreground'
            }`}
          >
            {t.label}
            {t.key === 'approval' && snap && snap.awaiting_approval > 0 && (
              <span className="ml-1 bg-yellow-600 text-white rounded-full px-1.5 text-[10px]">{snap.awaiting_approval}</span>
            )}
            {t.key === 'queue' && snap && snap.queue_depth > 0 && (
              <span className="ml-1 bg-blue-600 text-white rounded-full px-1.5 text-[10px]">{snap.queue_depth}</span>
            )}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-3">
        {tab === 'queue' && (
          <div>
            {(!state?.queue || state.queue.length === 0) ? (
              <div className="text-muted text-sm">Queue empty</div>
            ) : (
              state.queue.map(p => (
                <PlanCard key={p.execution_plan_id} plan={p}
                  onCancel={id => postAction('/execcoord/cancel', { execution_plan_id: id })} />
              ))
            )}
          </div>
        )}

        {tab === 'active' && (
          <div>
            {(!state?.active || state.active.length === 0) ? (
              <div className="text-muted text-sm">No active executions</div>
            ) : (
              state.active.map(p => (
                <PlanCard key={p.execution_plan_id} plan={p}
                  onCancel={id => postAction('/execcoord/cancel', { execution_plan_id: id })} />
              ))
            )}
          </div>
        )}

        {tab === 'approval' && (
          <div>
            {(!state?.awaiting_approval || state.awaiting_approval.length === 0) ? (
              <div className="text-muted text-sm">No plans awaiting approval</div>
            ) : (
              state.awaiting_approval.map(p => (
                <PlanCard key={p.execution_plan_id} plan={p}
                  onApprove={id => postAction('/execcoord/approve', { execution_plan_id: id })}
                  onDeny={id => postAction('/execcoord/deny', { execution_plan_id: id })}
                  onEnqueue={id => postAction('/execcoord/enqueue', { execution_plan_id: id })} />
              ))
            )}
          </div>
        )}

        {tab === 'history' && (
          <div>
            {(!state?.history || state.history.length === 0) ? (
              <div className="text-muted text-sm">No execution history</div>
            ) : (
              state.history.map(p => (
                <PlanCard key={p.execution_plan_id} plan={p} />
              ))
            )}
          </div>
        )}

        {tab === 'executors' && (
          <div>
            {(!state?.executors || state.executors.length === 0) ? (
              <div className="text-muted text-sm">No executors registered</div>
            ) : (
              state.executors.map(ex => (
                <div key={ex.executor_id} className="bg-surface-elevated border border-border rounded-lg p-3 mb-2">
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs">{getTargetIcon(ex.executor_type)}</span>
                      <span className="text-sm font-semibold text-foreground">{ex.name}</span>
                    </div>
                    <span className={`text-xs ${ex.available ? 'text-green-400' : 'text-red-400'}`}>
                      {ex.available ? 'AVAILABLE' : 'OFFLINE'}
                    </span>
                  </div>
                  <div className="text-xs text-muted mb-1">{ex.description}</div>
                  <div className="flex gap-1 flex-wrap">
                    {ex.capabilities.map(cap => (
                      <span key={cap} className="text-[10px] bg-surface px-1.5 py-0.5 rounded border border-border text-muted">{cap}</span>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  )
}
