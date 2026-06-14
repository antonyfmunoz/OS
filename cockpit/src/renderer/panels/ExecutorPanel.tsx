import { useState, useEffect, useCallback } from 'react'
import { useCockpitStore } from '../stores/cockpitStore'

interface ExecutorRequest {
  request_id: string
  execution_plan_id: string
  executor_type: string
  approval_state: string
  risk_class: string
  status: string
  description: string
  profile_id: string
  session_id: string
  priority: string
  created_at: number
  metadata: Record<string, unknown>
}

interface ExecutorResultData {
  result_id: string
  request_id: string
  executor_type: string
  success: boolean
  outcome: string
  artifacts: Array<Record<string, unknown>>
  errors: string[]
  started_at: number
  completed_at: number
  duration_seconds: number
  metadata?: Record<string, unknown>
}

interface LifecycleEvent {
  event_id: string
  request_id: string
  event_type: string
  timestamp: number
  summary: string
}

interface ExecutorState {
  snapshot: {
    total_requests: number
    by_status: Record<string, number>
    active_count: number
    completed_count: number
    failed_count: number
    registered_executors: number
  }
}

type Tab = 'executors' | 'requests' | 'active' | 'results' | 'failures'

function KpiCard({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="bg-surface-2 rounded px-3 py-2 text-center min-w-[100px]">
      <div className="text-xs text-secondary uppercase tracking-wide">{label}</div>
      <div className="text-lg font-mono font-bold text-primary">{String(value)}</div>
    </div>
  )
}

function getStatusColor(status: string): string {
  const map: Record<string, string> = {
    pending: 'text-yellow-400',
    validating: 'text-blue-400',
    preparing: 'text-blue-400',
    ready: 'text-green-400',
    executing: 'text-cyan-400',
    monitoring: 'text-cyan-400',
    completing: 'text-green-400',
    completed: 'text-green-500',
    failed: 'text-red-500',
    cancelled: 'text-gray-500',
    cleaning_up: 'text-yellow-400',
    cleaned_up: 'text-green-600',
  }
  return map[status] || 'text-secondary'
}

function getRiskColor(risk: string): string {
  const map: Record<string, string> = {
    negligible: 'text-gray-400',
    low: 'text-green-400',
    medium: 'text-yellow-400',
    high: 'text-orange-400',
    critical: 'text-red-500',
  }
  return map[risk] || 'text-secondary'
}

function getTargetIcon(type: string): string {
  const map: Record<string, string> = {
    workstation: '\u{1F5A5}',
    agent: '\u{1F916}',
    container: '\u{1F4E6}',
    vps: '\u{2601}',
    browser: '\u{1F310}',
    mobile: '\u{1F4F1}',
    external: '\u{1F517}',
  }
  return map[type] || '\u{2699}'
}

function formatTimestamp(ts: number): string {
  if (!ts) return '-'
  return new Date(ts * 1000).toLocaleTimeString()
}

function RequestCard({
  req,
  onApprove,
  onDeny,
  onRun,
  onCancel,
}: {
  req: ExecutorRequest
  onApprove?: (id: string) => void
  onDeny?: (id: string) => void
  onRun?: (id: string) => void
  onCancel?: (id: string) => void
}) {
  const isPending = req.approval_state === 'pending'
  const isTerminal = ['completed', 'failed', 'cancelled', 'cleaned_up'].includes(req.status)
  const canRun = ['pending', 'ready'].includes(req.status) &&
    ['approved', 'auto_approved'].includes(req.approval_state)

  return (
    <div className="bg-surface-2 rounded p-3 border border-border mb-2">
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2">
          <span>{getTargetIcon(req.executor_type)}</span>
          <span className="font-mono text-sm text-primary">{req.request_id.slice(0, 17)}</span>
          <span className={`text-xs font-bold uppercase ${getStatusColor(req.status)}`}>
            {req.status}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <span className={`text-xs ${getRiskColor(req.risk_class)}`}>{req.risk_class}</span>
          <span className="text-xs text-secondary">{req.priority}</span>
        </div>
      </div>
      {req.description && (
        <div className="text-xs text-secondary mb-1">{req.description}</div>
      )}
      {req.metadata?.operation && (
        <div className="text-xs text-cyan-400 mb-1">
          op: {req.metadata.operation as string}
        </div>
      )}
      <div className="text-xs text-secondary mb-2">
        Plan: {req.execution_plan_id.slice(0, 17) || '-'} |
        Profile: {req.profile_id || '-'} |
        Session: {req.session_id || '-'} |
        {formatTimestamp(req.created_at)}
      </div>
      <div className="flex gap-2">
        {isPending && onApprove && (
          <button
            onClick={() => onApprove(req.request_id)}
            className="text-xs bg-green-700 hover:bg-green-600 text-white px-2 py-1 rounded"
          >
            Approve
          </button>
        )}
        {isPending && onDeny && (
          <button
            onClick={() => onDeny(req.request_id)}
            className="text-xs bg-red-700 hover:bg-red-600 text-white px-2 py-1 rounded"
          >
            Deny
          </button>
        )}
        {canRun && onRun && (
          <button
            onClick={() => onRun(req.request_id)}
            className="text-xs bg-blue-700 hover:bg-blue-600 text-white px-2 py-1 rounded"
          >
            Run
          </button>
        )}
        {!isTerminal && onCancel && (
          <button
            onClick={() => onCancel(req.request_id)}
            className="text-xs bg-gray-700 hover:bg-gray-600 text-white px-2 py-1 rounded"
          >
            Cancel
          </button>
        )}
      </div>
    </div>
  )
}

function ResultCard({ result }: { result: ExecutorResultData }) {
  const proof = result.metadata?.proof as Record<string, unknown> | undefined
  const exitCode = (proof?.outputs as Record<string, unknown>)?.exit_code as number | undefined

  return (
    <div className="bg-surface-2 rounded p-3 border border-border mb-2">
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2">
          <span>{getTargetIcon(result.executor_type)}</span>
          <span className="font-mono text-sm text-primary">{result.result_id.slice(0, 17)}</span>
          <span className={`text-xs font-bold ${result.success ? 'text-green-500' : 'text-red-500'}`}>
            {result.success ? 'SUCCESS' : 'FAILED'}
          </span>
        </div>
        <span className="text-xs text-secondary">{result.duration_seconds.toFixed(2)}s</span>
      </div>
      <div className="text-xs text-secondary mb-1">{result.outcome}</div>
      {proof && (
        <div className="text-xs text-cyan-400 mb-1">
          {proof.operation as string}
          {exitCode !== undefined && <span className="ml-2">exit: {exitCode}</span>}
          {proof.duration_ms !== undefined && (
            <span className="ml-2">{(proof.duration_ms as number).toFixed(0)}ms</span>
          )}
        </div>
      )}
      <div className="text-xs text-secondary">
        Req: {result.request_id.slice(0, 17)} |
        Artifacts: {result.artifacts.length} |
        {result.errors.length > 0 ? `Errors: ${result.errors.length}` : 'No errors'}
        {proof && <span className="ml-1">| Proof: {(proof.proof_id as string)?.slice(0, 15)}</span>}
      </div>
    </div>
  )
}

export function ExecutorPanel() {
  const [tab, setTab] = useState<Tab>('executors')
  const [state, setState] = useState<ExecutorState | null>(null)
  const [requests, setRequests] = useState<ExecutorRequest[]>([])
  const [active, setActive] = useState<ExecutorRequest[]>([])
  const [results, setResults] = useState<ExecutorResultData[]>([])
  const [failures, setFailures] = useState<ExecutorRequest[]>([])
  const [executorTypes, setExecutorTypes] = useState<string[]>([])

  const apiBase = useCockpitStore((s) => s.apiBase)

  const fetchData = useCallback(async () => {
    try {
      const base = apiBase || ''
      const [stateRes, reqRes, activeRes, resultRes, failRes, typeRes] = await Promise.all([
        fetch(`${base}/executor/state`).then(r => r.json()).catch(() => null),
        fetch(`${base}/executor/requests`).then(r => r.json()).catch(() => ({ requests: [] })),
        fetch(`${base}/executor/active`).then(r => r.json()).catch(() => ({ active: [] })),
        fetch(`${base}/executor/results`).then(r => r.json()).catch(() => ({ results: [] })),
        fetch(`${base}/executor/failures`).then(r => r.json()).catch(() => ({ failures: [] })),
        fetch(`${base}/executor/types`).then(r => r.json()).catch(() => ({ executor_types: [] })),
      ])
      if (stateRes) setState({ snapshot: stateRes })
      setRequests(reqRes.requests || [])
      setActive(activeRes.active || [])
      setResults(resultRes.results || [])
      setFailures(failRes.failures || [])
      setExecutorTypes(typeRes.executor_types || [])
    } catch {
      // silent
    }
  }, [apiBase])

  useEffect(() => {
    fetchData()
    const iv = setInterval(fetchData, 15000)
    return () => clearInterval(iv)
  }, [fetchData])

  const doAction = async (endpoint: string, body: Record<string, string>) => {
    try {
      const base = apiBase || ''
      await fetch(`${base}/executor/${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      fetchData()
    } catch {
      // silent
    }
  }

  const snap = state?.snapshot

  const tabs: { key: Tab; label: string; badge?: number }[] = [
    { key: 'executors', label: 'Executors', badge: executorTypes.length },
    { key: 'requests', label: 'Requests', badge: requests.length },
    { key: 'active', label: 'Active', badge: active.length },
    { key: 'results', label: 'Results', badge: results.length },
    { key: 'failures', label: 'Failures', badge: failures.length },
  ]

  return (
    <div className="h-full flex flex-col p-4 overflow-auto">
      <h2 className="text-lg font-bold text-primary mb-3">Executor Runtime</h2>

      {snap && (
        <div className="flex gap-2 mb-4 flex-wrap">
          <KpiCard label="Total" value={snap.total_requests} />
          <KpiCard label="Active" value={snap.active_count} />
          <KpiCard label="Completed" value={snap.completed_count} />
          <KpiCard label="Failed" value={snap.failed_count} />
          <KpiCard label="Executors" value={snap.registered_executors} />
        </div>
      )}

      <div className="flex gap-1 mb-4 border-b border-border">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-3 py-1.5 text-sm font-medium border-b-2 transition-colors ${
              tab === t.key
                ? 'border-accent text-primary'
                : 'border-transparent text-secondary hover:text-primary'
            }`}
          >
            {t.label}
            {t.badge !== undefined && t.badge > 0 && (
              <span className="ml-1 text-xs bg-surface-3 px-1.5 rounded-full">{t.badge}</span>
            )}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-auto">
        {tab === 'executors' && (
          <div>
            <h3 className="text-sm font-bold text-secondary mb-2 uppercase">Registered Executor Types</h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {executorTypes.map(t => {
                const isReal = t === 'workstation'
                return (
                  <div key={t} className="bg-surface-2 rounded p-3 border border-border text-center">
                    <div className="text-2xl mb-1">{getTargetIcon(t)}</div>
                    <div className="text-sm font-mono text-primary">{t}</div>
                    <div className={`text-xs ${isReal ? 'text-cyan-400' : 'text-green-400'}`}>
                      {isReal ? 'production' : 'simulation'}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {tab === 'requests' && (
          <div>
            {requests.length === 0 ? (
              <div className="text-secondary text-sm">No requests</div>
            ) : (
              requests.map(r => (
                <RequestCard
                  key={r.request_id}
                  req={r}
                  onApprove={(id) => doAction('approve', { request_id: id })}
                  onDeny={(id) => doAction('deny', { request_id: id, reason: 'Denied via cockpit' })}
                  onRun={(id) => doAction('run', { request_id: id })}
                  onCancel={(id) => doAction('cancel', { request_id: id })}
                />
              ))
            )}
          </div>
        )}

        {tab === 'active' && (
          <div>
            {active.length === 0 ? (
              <div className="text-secondary text-sm">No active requests</div>
            ) : (
              active.map(r => (
                <RequestCard
                  key={r.request_id}
                  req={r}
                  onCancel={(id) => doAction('cancel', { request_id: id })}
                />
              ))
            )}
          </div>
        )}

        {tab === 'results' && (
          <div>
            {results.length === 0 ? (
              <div className="text-secondary text-sm">No results</div>
            ) : (
              results.map(r => (
                <ResultCard key={r.result_id} result={r} />
              ))
            )}
          </div>
        )}

        {tab === 'failures' && (
          <div>
            {failures.length === 0 ? (
              <div className="text-secondary text-sm">No failures</div>
            ) : (
              failures.map(r => (
                <RequestCard key={r.request_id} req={r} />
              ))
            )}
          </div>
        )}
      </div>
    </div>
  )
}
