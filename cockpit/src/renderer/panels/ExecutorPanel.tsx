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

interface TelemetryEvent {
  event_id: string
  execution_id: string
  request_id: string
  executor_type: string
  operation: string
  event_type: string
  timestamp: number
  status: string
  sequence_number: number
  payload: Record<string, unknown>
}

interface ApprovalIntercept {
  approval_id: string
  execution_id: string
  request_id: string
  executor_type: string
  operation: string
  risk_class: string
  reason: string
  details: Record<string, unknown>
  requested_at: number
  expires_at: number
  status: string
  decided_by: string
  decided_at: number
  rejection_reason: string
}

interface WorktreeData {
  worktree_id: string
  path: string
  branch: string
  is_bare: boolean
  executor_owner: string
}

interface ProcessData {
  pid: number
  command: string
  started_at: number
  cpu_percent: number
  memory_mb: number
  executor_owner: string
}

interface ContainerData {
  container_id: string
  name: string
  status: string
  image: string
}

interface RuntimeExecution {
  execution_id: string
  status: string
  executor_type: string
  started_at: number
  duration_seconds: number
}

interface RuntimeSummary {
  worktree_count: number
  process_count: number
  container_count: number
  execution_count: number
}

type Tab = 'workspace' | 'executors' | 'requests' | 'active' | 'results' | 'failures' | 'live' | 'approvals'

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

function getEventColor(eventType: string): string {
  const map: Record<string, string> = {
    execution_requested: 'text-blue-400',
    execution_validating: 'text-blue-300',
    execution_approved: 'text-green-400',
    execution_preparing: 'text-yellow-400',
    execution_started: 'text-cyan-400',
    command_started: 'text-purple-400',
    stdout_chunk: 'text-gray-300',
    stderr_chunk: 'text-orange-400',
    command_completed: 'text-purple-300',
    proof_generated: 'text-emerald-400',
    execution_cleaning_up: 'text-yellow-300',
    execution_completed: 'text-green-500',
    execution_failed: 'text-red-500',
    execution_cancelled: 'text-gray-500',
    approval_requested: 'text-amber-400',
    approval_viewed: 'text-amber-300',
    approval_granted: 'text-green-400',
    approval_rejected: 'text-red-400',
    approval_expired: 'text-gray-400',
    execution_paused: 'text-amber-500',
    execution_resumed: 'text-cyan-400',
  }
  return map[eventType] || 'text-secondary'
}

function TelemetryEventRow({ event }: { event: TelemetryEvent }) {
  const ts = new Date(event.timestamp * 1000).toLocaleTimeString()
  const isOutput = event.event_type === 'stdout_chunk' || event.event_type === 'stderr_chunk'
  const output = isOutput ? (event.payload.data as string || '') : null
  const proofId = event.event_type === 'proof_generated'
    ? (event.payload.proof_id as string || '') : null

  return (
    <div className="bg-surface-2 rounded px-3 py-1.5 mb-1 border border-border/50 text-xs">
      <div className="flex items-center gap-2">
        <span className="text-secondary font-mono w-[70px] shrink-0">{ts}</span>
        <span className="text-secondary font-mono w-[30px] shrink-0">#{event.sequence_number}</span>
        <span className={`font-bold uppercase w-[160px] shrink-0 ${getEventColor(event.event_type)}`}>
          {event.event_type}
        </span>
        <span className="text-secondary font-mono truncate">{event.execution_id.slice(0, 17)}</span>
        {event.executor_type && (
          <span className="text-cyan-400 ml-auto">{event.executor_type}</span>
        )}
      </div>
      {output && (
        <pre className="mt-1 text-[11px] bg-surface-3 p-1.5 rounded font-mono whitespace-pre-wrap max-h-[80px] overflow-auto">
          {output.slice(0, 500)}{output.length > 500 ? '...' : ''}
        </pre>
      )}
      {proofId && (
        <div className="mt-1 text-emerald-400 font-mono">proof: {proofId.slice(0, 20)}</div>
      )}
      {event.payload.exit_code !== undefined && (
        <span className="ml-2 text-secondary">exit: {String(event.payload.exit_code)}</span>
      )}
      {event.payload.duration_ms !== undefined && (
        <span className="ml-2 text-secondary">{String(event.payload.duration_ms)}ms</span>
      )}
      {event.payload.error && (
        <div className="mt-1 text-red-400 font-mono text-[11px]">{String(event.payload.error).slice(0, 300)}</div>
      )}
    </div>
  )
}

function ApprovalCard({
  approval,
  onApprove,
  onReject,
}: {
  approval: ApprovalIntercept
  onApprove?: (id: string) => void
  onReject?: (id: string) => void
}) {
  const isPending = approval.status === 'pending'
  const age = Math.round((Date.now() / 1000 - approval.requested_at))
  const ageStr = age < 60 ? `${age}s` : `${Math.floor(age / 60)}m ${age % 60}s`
  const expiresIn = Math.max(0, Math.round(approval.expires_at - Date.now() / 1000))
  const expiresStr = expiresIn < 60 ? `${expiresIn}s` : `${Math.floor(expiresIn / 60)}m`

  return (
    <div className={`bg-surface-2 rounded p-3 border mb-2 ${
      isPending ? 'border-amber-500/50' : 'border-border'
    }`}>
      {isPending && (
        <div className="text-xs font-bold text-amber-400 uppercase tracking-wider mb-2">
          Approval Required
        </div>
      )}
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2">
          <span>{getTargetIcon(approval.executor_type)}</span>
          <span className="font-mono text-sm text-primary">{approval.approval_id.slice(0, 17)}</span>
          <span className={`text-xs font-bold uppercase ${
            approval.status === 'approved' ? 'text-green-400' :
            approval.status === 'rejected' ? 'text-red-400' :
            approval.status === 'expired' ? 'text-gray-400' :
            'text-amber-400'
          }`}>
            {approval.status}
          </span>
        </div>
        <span className={`text-xs ${getRiskColor(approval.risk_class)} font-bold uppercase`}>
          {approval.risk_class}
        </span>
      </div>
      <div className="text-xs text-secondary mb-1">{approval.reason}</div>
      {approval.operation && (
        <div className="text-xs text-cyan-400 mb-1">op: {approval.operation}</div>
      )}
      <div className="text-xs text-secondary mb-2">
        Exec: {approval.execution_id.slice(0, 17)} |
        Age: {ageStr}
        {isPending && <span className="text-amber-400 ml-1">| Expires: {expiresStr}</span>}
        {approval.decided_by && <span> | By: {approval.decided_by}</span>}
      </div>
      {approval.rejection_reason && (
        <div className="text-xs text-red-400 mb-2">Reason: {approval.rejection_reason}</div>
      )}
      {isPending && (
        <div className="flex gap-2">
          {onApprove && (
            <button
              onClick={() => onApprove(approval.approval_id)}
              className="text-xs bg-green-700 hover:bg-green-600 text-white px-3 py-1.5 rounded font-bold"
            >
              Approve
            </button>
          )}
          {onReject && (
            <button
              onClick={() => onReject(approval.approval_id)}
              className="text-xs bg-red-700 hover:bg-red-600 text-white px-3 py-1.5 rounded font-bold"
            >
              Reject
            </button>
          )}
        </div>
      )}
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
  const [tab, setTab] = useState<Tab>('workspace')
  const [state, setState] = useState<ExecutorState | null>(null)
  const [requests, setRequests] = useState<ExecutorRequest[]>([])
  const [active, setActive] = useState<ExecutorRequest[]>([])
  const [results, setResults] = useState<ExecutorResultData[]>([])
  const [failures, setFailures] = useState<ExecutorRequest[]>([])
  const [executorTypes, setExecutorTypes] = useState<string[]>([])
  const [telemetryEvents, setTelemetryEvents] = useState<TelemetryEvent[]>([])
  const [telemetrySeq, setTelemetrySeq] = useState(0)
  const [approvals, setApprovals] = useState<ApprovalIntercept[]>([])
  const [worktrees, setWorktrees] = useState<WorktreeData[]>([])
  const [runtimeProcesses, setRuntimeProcesses] = useState<ProcessData[]>([])
  const [runtimeContainers, setRuntimeContainers] = useState<ContainerData[]>([])
  const [runtimeExecutions, setRuntimeExecutions] = useState<RuntimeExecution[]>([])
  const [runtimeSummary, setRuntimeSummary] = useState<RuntimeSummary | null>(null)

  const apiBase = useCockpitStore((s) => s.apiBase)

  const fetchWorkspace = useCallback(async () => {
    try {
      const base = apiBase || ''
      const res = await fetch(`${base}/runtime/state`).then(r => r.json()).catch(() => null)
      if (res?.success) {
        setWorktrees(res.worktrees || [])
        setRuntimeProcesses(res.processes || [])
        setRuntimeContainers(res.containers || [])
        setRuntimeExecutions(res.executions || [])
        setRuntimeSummary(res.summary || null)
      }
    } catch {
      // silent
    }
  }, [apiBase])

  const fetchApprovals = useCallback(async () => {
    try {
      const base = apiBase || ''
      const res = await fetch(`${base}/approvals/pending`).then(r => r.json()).catch(() => null)
      if (res?.success && res.approvals) {
        setApprovals(res.approvals)
      }
    } catch {
      // silent
    }
  }, [apiBase])

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

  const fetchTelemetry = useCallback(async () => {
    try {
      const base = apiBase || ''
      const res = await fetch(`${base}/executor/telemetry/latest?limit=100`).then(r => r.json()).catch(() => null)
      if (res?.success && res.events) {
        setTelemetryEvents(res.events)
        setTelemetrySeq(res.sequence || 0)
      }
    } catch {
      // silent
    }
  }, [apiBase])

  useEffect(() => {
    fetchData()
    const iv = setInterval(fetchData, 15000)
    return () => clearInterval(iv)
  }, [fetchData])

  useEffect(() => {
    if (tab !== 'workspace') return
    fetchWorkspace()
    const iv = setInterval(fetchWorkspace, 5000)
    return () => clearInterval(iv)
  }, [tab, fetchWorkspace])

  useEffect(() => {
    if (tab !== 'live') return
    fetchTelemetry()
    const iv = setInterval(fetchTelemetry, 3000)
    return () => clearInterval(iv)
  }, [tab, fetchTelemetry])

  useEffect(() => {
    if (tab !== 'approvals') return
    fetchApprovals()
    const iv = setInterval(fetchApprovals, 2000)
    return () => clearInterval(iv)
  }, [tab, fetchApprovals])

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

  const doApprovalAction = async (approval_id: string, action: 'approve' | 'reject') => {
    try {
      const base = apiBase || ''
      await fetch(`${base}/approvals/${approval_id}/${action}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      })
      fetchApprovals()
    } catch {
      // silent
    }
  }

  const snap = state?.snapshot

  const tabs: { key: Tab; label: string; badge?: number }[] = [
    { key: 'workspace', label: 'Workspace', badge: runtimeSummary ? runtimeSummary.process_count + runtimeSummary.container_count : undefined },
    { key: 'executors', label: 'Executors', badge: executorTypes.length },
    { key: 'requests', label: 'Requests', badge: requests.length },
    { key: 'active', label: 'Active', badge: active.length },
    { key: 'results', label: 'Results', badge: results.length },
    { key: 'failures', label: 'Failures', badge: failures.length },
    { key: 'approvals', label: 'Approvals', badge: approvals.length },
    { key: 'live', label: 'Live', badge: telemetryEvents.length },
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
        {tab === 'workspace' && (
          <div className="space-y-4">
            {runtimeSummary && (
              <div className="flex gap-2 flex-wrap">
                <KpiCard label="Worktrees" value={runtimeSummary.worktree_count} />
                <KpiCard label="Processes" value={runtimeSummary.process_count} />
                <KpiCard label="Containers" value={runtimeSummary.container_count} />
                <KpiCard label="Executions" value={runtimeSummary.execution_count} />
              </div>
            )}

            <div>
              <h3 className="text-sm font-bold text-secondary mb-2 uppercase">Worktrees</h3>
              {worktrees.length === 0 ? (
                <div className="text-secondary text-sm">No worktrees</div>
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs text-secondary uppercase border-b border-border">
                      <th className="py-1 pr-2">Branch</th>
                      <th className="py-1 pr-2">Path</th>
                    </tr>
                  </thead>
                  <tbody>
                    {worktrees.map(w => (
                      <tr key={w.worktree_id} className="border-b border-border/50">
                        <td className="py-1.5 pr-2 font-mono text-cyan-400">{w.branch}</td>
                        <td className="py-1.5 pr-2 font-mono text-xs text-secondary truncate max-w-[400px]">{w.path}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            <div>
              <h3 className="text-sm font-bold text-secondary mb-2 uppercase">Containers</h3>
              {runtimeContainers.length === 0 ? (
                <div className="text-secondary text-sm">No containers</div>
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs text-secondary uppercase border-b border-border">
                      <th className="py-1 pr-2">Name</th>
                      <th className="py-1 pr-2">Status</th>
                      <th className="py-1 pr-2">Image</th>
                    </tr>
                  </thead>
                  <tbody>
                    {runtimeContainers.map(c => (
                      <tr key={c.container_id} className="border-b border-border/50">
                        <td className="py-1.5 pr-2 font-mono text-primary">{c.name}</td>
                        <td className={`py-1.5 pr-2 text-xs ${c.status.toLowerCase().includes('up') ? 'text-green-400' : 'text-yellow-400'}`}>{c.status}</td>
                        <td className="py-1.5 pr-2 font-mono text-xs text-secondary truncate max-w-[300px]">{c.image}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            <div>
              <h3 className="text-sm font-bold text-secondary mb-2 uppercase">Processes</h3>
              {runtimeProcesses.length === 0 ? (
                <div className="text-secondary text-sm">No relevant processes</div>
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs text-secondary uppercase border-b border-border">
                      <th className="py-1 pr-2">PID</th>
                      <th className="py-1 pr-2">CPU%</th>
                      <th className="py-1 pr-2">MEM</th>
                      <th className="py-1 pr-2">Command</th>
                    </tr>
                  </thead>
                  <tbody>
                    {runtimeProcesses.map(p => (
                      <tr key={p.pid} className="border-b border-border/50">
                        <td className="py-1.5 pr-2 font-mono text-xs">{p.pid}</td>
                        <td className={`py-1.5 pr-2 font-mono text-xs ${p.cpu_percent > 50 ? 'text-red-400' : p.cpu_percent > 10 ? 'text-yellow-400' : 'text-green-400'}`}>{p.cpu_percent.toFixed(1)}%</td>
                        <td className="py-1.5 pr-2 font-mono text-xs">{p.memory_mb.toFixed(0)}MB</td>
                        <td className="py-1.5 pr-2 font-mono text-xs text-secondary truncate max-w-[400px]">{p.command}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            <div>
              <h3 className="text-sm font-bold text-secondary mb-2 uppercase">Active Executions</h3>
              {runtimeExecutions.length === 0 ? (
                <div className="text-secondary text-sm">No active executions</div>
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs text-secondary uppercase border-b border-border">
                      <th className="py-1 pr-2">ID</th>
                      <th className="py-1 pr-2">Type</th>
                      <th className="py-1 pr-2">Status</th>
                      <th className="py-1 pr-2">Duration</th>
                    </tr>
                  </thead>
                  <tbody>
                    {runtimeExecutions.map(e => (
                      <tr key={e.execution_id} className="border-b border-border/50">
                        <td className="py-1.5 pr-2 font-mono text-xs">{e.execution_id.slice(0, 12)}</td>
                        <td className="py-1.5 pr-2 text-xs text-primary">{e.executor_type}</td>
                        <td className={`py-1.5 pr-2 text-xs ${getStatusColor(e.status)}`}>{e.status}</td>
                        <td className="py-1.5 pr-2 font-mono text-xs">{e.duration_seconds.toFixed(1)}s</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        )}

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

        {tab === 'approvals' && (
          <div>
            <h3 className="text-sm font-bold text-secondary mb-2 uppercase">Pending Approval Intercepts</h3>
            {approvals.length === 0 ? (
              <div className="text-secondary text-sm">No pending approvals</div>
            ) : (
              approvals.map(a => (
                <ApprovalCard
                  key={a.approval_id}
                  approval={a}
                  onApprove={(id) => doApprovalAction(id, 'approve')}
                  onReject={(id) => doApprovalAction(id, 'reject')}
                />
              ))
            )}
          </div>
        )}

        {tab === 'live' && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-bold text-secondary uppercase">Execution Telemetry</h3>
              <span className="text-xs text-secondary font-mono">seq: {telemetrySeq}</span>
            </div>
            {telemetryEvents.length === 0 ? (
              <div className="text-secondary text-sm">No telemetry events yet</div>
            ) : (
              [...telemetryEvents].reverse().map(e => (
                <TelemetryEventRow key={e.event_id} event={e} />
              ))
            )}
          </div>
        )}
      </div>
    </div>
  )
}
