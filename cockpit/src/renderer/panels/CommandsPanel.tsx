import { useEffect, useState, useCallback } from 'react'
import { fetchApi } from '../api/client'

interface CommandData {
  command_id: string
  source: string
  raw_input: string
  action_type: string
  status: string
  timestamp: number
  confidence: number
  target_domain: string
  approval_required: boolean
  workpacket_id: string
  routing_result: Record<string, unknown>
  outcome: Record<string, unknown>
  error: string
}

interface CommandStatus {
  phase: string
  total_commands: number
  pending: number
  completed: number
  failed: number
  pending_approvals: number
}

interface TimelineEvent {
  event_id: string
  event_type: string
  command_id: string
  timestamp: number
  summary: string
}

type Tab = 'submit' | 'active' | 'pending' | 'timeline' | 'history'

function KpiCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-surface-alt rounded-lg p-3 border border-border">
      <div className="text-xs text-muted uppercase tracking-wide">{label}</div>
      <div className="text-xl font-mono font-bold mt-1">{value}</div>
      {sub && <div className="text-xs text-muted mt-1">{sub}</div>}
    </div>
  )
}

function getStatusColor(status: string): string {
  switch (status) {
    case 'completed': return 'text-green-400'
    case 'failed': return 'text-red-400'
    case 'pending_approval': return 'text-yellow-400'
    case 'executing': return 'text-blue-400'
    case 'rejected': return 'text-red-300'
    case 'cancelled': return 'text-gray-400'
    default: return 'text-muted'
  }
}

function getActionBadge(action: string): string {
  switch (action) {
    case 'query': return 'bg-blue-900/50 text-blue-300'
    case 'execute': return 'bg-orange-900/50 text-orange-300'
    case 'review': return 'bg-purple-900/50 text-purple-300'
    case 'approve': return 'bg-green-900/50 text-green-300'
    case 'reject': return 'bg-red-900/50 text-red-300'
    case 'schedule': return 'bg-cyan-900/50 text-cyan-300'
    case 'switch_profile': return 'bg-indigo-900/50 text-indigo-300'
    case 'create_objective': return 'bg-amber-900/50 text-amber-300'
    case 'create_workpacket': return 'bg-teal-900/50 text-teal-300'
    default: return 'bg-surface-alt text-muted'
  }
}

function formatTimestamp(ts: number): string {
  if (!ts) return '—'
  return new Date(ts * 1000).toLocaleString()
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`
  return `${Math.round(seconds / 3600)}h`
}

export function CommandsPanel() {
  const [tab, setTab] = useState<Tab>('submit')
  const [status, setStatus] = useState<CommandStatus | null>(null)
  const [commands, setCommands] = useState<CommandData[]>([])
  const [pending, setPending] = useState<CommandData[]>([])
  const [timeline, setTimeline] = useState<TimelineEvent[]>([])
  const [commandInput, setCommandInput] = useState('')
  const [submitResult, setSubmitResult] = useState<CommandData | null>(null)
  const [loading, setLoading] = useState(false)

  const refresh = useCallback(async () => {
    try {
      const [statusRes, historyRes, pendingRes, timelineRes] = await Promise.all([
        fetchApi('/command/status'),
        fetchApi('/command/history?limit=50'),
        fetchApi('/command/pending'),
        fetchApi('/command/timeline?limit=50'),
      ])
      if (statusRes.success) setStatus(statusRes as unknown as CommandStatus)
      if (historyRes.success) setCommands(historyRes.commands || [])
      if (pendingRes.success) setPending(pendingRes.pending || [])
      if (timelineRes.success) setTimeline(timelineRes.events || [])
    } catch (e) {
      console.error('command refresh failed:', e)
    }
  }, [])

  useEffect(() => { refresh() }, [refresh])
  useEffect(() => { const id = setInterval(refresh, 10000); return () => clearInterval(id) }, [refresh])

  const handleSubmit = async () => {
    if (!commandInput.trim()) return
    setLoading(true)
    setSubmitResult(null)
    try {
      const res = await fetchApi('/command/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ raw_input: commandInput, source: 'cockpit' }),
      })
      if (res.success && res.command) {
        setSubmitResult(res.command as CommandData)
        setCommandInput('')
        refresh()
      }
    } catch (e) {
      console.error('submit failed:', e)
    } finally {
      setLoading(false)
    }
  }

  const handleApprove = async (commandId: string) => {
    try {
      await fetchApi(`/command/${commandId}/approve`, { method: 'POST' })
      refresh()
    } catch (e) {
      console.error('approve failed:', e)
    }
  }

  const handleReject = async (commandId: string) => {
    try {
      await fetchApi(`/command/${commandId}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: 'Rejected via cockpit' }),
      })
      refresh()
    } catch (e) {
      console.error('reject failed:', e)
    }
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: 'submit', label: 'Submit' },
    { key: 'active', label: `Active (${commands.filter(c => !['completed', 'failed', 'cancelled', 'rejected'].includes(c.status)).length})` },
    { key: 'pending', label: `Pending (${pending.length})` },
    { key: 'timeline', label: 'Timeline' },
    { key: 'history', label: 'History' },
  ]

  return (
    <div className="h-full flex flex-col p-4 space-y-4 overflow-auto">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold">Command Center</h2>
        <button onClick={refresh} className="text-xs px-3 py-1 rounded bg-surface-alt hover:bg-surface-hover border border-border">
          Refresh
        </button>
      </div>

      {status && (
        <div className="grid grid-cols-5 gap-3">
          <KpiCard label="Total" value={String(status.total_commands)} />
          <KpiCard label="Pending" value={String(status.pending)} />
          <KpiCard label="Approvals" value={String(status.pending_approvals)} />
          <KpiCard label="Completed" value={String(status.completed)} />
          <KpiCard label="Failed" value={String(status.failed)} />
        </div>
      )}

      <div className="flex gap-1 border-b border-border">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-3 py-2 text-sm border-b-2 transition-colors ${
              tab === t.key ? 'border-accent text-accent' : 'border-transparent text-muted hover:text-primary'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-auto">
        {tab === 'submit' && (
          <div className="space-y-4">
            <div className="flex gap-2">
              <input
                type="text"
                value={commandInput}
                onChange={(e) => setCommandInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
                placeholder="Enter command... (e.g., 'review operator roadmap', 'switch to developer')"
                className="flex-1 px-3 py-2 bg-surface-alt border border-border rounded text-sm font-mono focus:border-accent outline-none"
                disabled={loading}
              />
              <button
                onClick={handleSubmit}
                disabled={loading || !commandInput.trim()}
                className="px-4 py-2 bg-accent text-accent-foreground rounded text-sm font-medium hover:opacity-90 disabled:opacity-50"
              >
                {loading ? 'Processing...' : 'Submit'}
              </button>
            </div>

            {submitResult && (
              <div className="bg-surface-alt rounded-lg border border-border p-4 space-y-3">
                <div className="flex items-center gap-2">
                  <span className={`text-xs px-2 py-0.5 rounded font-mono ${getActionBadge(submitResult.action_type)}`}>
                    {submitResult.action_type}
                  </span>
                  <span className={`text-xs font-mono ${getStatusColor(submitResult.status)}`}>
                    {submitResult.status}
                  </span>
                  <span className="text-xs text-muted">
                    confidence: {(submitResult.confidence * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="text-sm font-mono">{submitResult.raw_input}</div>
                {submitResult.target_domain && (
                  <div className="text-xs text-muted">Domain: {submitResult.target_domain}</div>
                )}
                {submitResult.routing_result && (
                  <details className="text-xs">
                    <summary className="cursor-pointer text-muted hover:text-primary">Routing Decision</summary>
                    <pre className="mt-2 p-2 bg-surface rounded text-xs overflow-auto max-h-40">
                      {JSON.stringify(submitResult.routing_result, null, 2)}
                    </pre>
                  </details>
                )}
                {submitResult.outcome && Object.keys(submitResult.outcome).length > 0 && (
                  <details className="text-xs">
                    <summary className="cursor-pointer text-muted hover:text-primary">Outcome</summary>
                    <pre className="mt-2 p-2 bg-surface rounded text-xs overflow-auto max-h-40">
                      {JSON.stringify(submitResult.outcome, null, 2)}
                    </pre>
                  </details>
                )}
              </div>
            )}

            <div className="text-xs text-muted space-y-1">
              <div className="font-medium">Example commands:</div>
              <div className="grid grid-cols-2 gap-1">
                <div><code className="text-accent">"review operator roadmap"</code> → review</div>
                <div><code className="text-accent">"switch to engineer"</code> → switch profile</div>
                <div><code className="text-accent">"create objective: ship voice"</code> → create objective</div>
                <div><code className="text-accent">"approve packet wp-123"</code> → approve</div>
                <div><code className="text-accent">"what changed while I was gone?"</code> → query continuity</div>
                <div><code className="text-accent">"deploy the cockpit"</code> → execute via Empire Router</div>
              </div>
            </div>
          </div>
        )}

        {tab === 'active' && (
          <div className="space-y-2">
            {commands.filter(c => !['completed', 'failed', 'cancelled', 'rejected'].includes(c.status)).length === 0 ? (
              <div className="text-sm text-muted text-center py-8">No active commands</div>
            ) : (
              commands.filter(c => !['completed', 'failed', 'cancelled', 'rejected'].includes(c.status)).map(cmd => (
                <div key={cmd.command_id} className="bg-surface-alt rounded-lg border border-border p-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className={`text-xs px-2 py-0.5 rounded font-mono ${getActionBadge(cmd.action_type)}`}>
                        {cmd.action_type}
                      </span>
                      <span className={`text-xs font-mono ${getStatusColor(cmd.status)}`}>{cmd.status}</span>
                    </div>
                    <span className="text-xs text-muted font-mono">{cmd.command_id}</span>
                  </div>
                  <div className="text-sm mt-1">{cmd.raw_input}</div>
                  <div className="text-xs text-muted mt-1">{formatTimestamp(cmd.timestamp)} · {cmd.source}</div>
                </div>
              ))
            )}
          </div>
        )}

        {tab === 'pending' && (
          <div className="space-y-2">
            {pending.length === 0 ? (
              <div className="text-sm text-muted text-center py-8">No pending approvals</div>
            ) : (
              pending.filter(c => c.status === 'pending_approval').map(cmd => (
                <div key={cmd.command_id} className="bg-surface-alt rounded-lg border border-border p-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className={`text-xs px-2 py-0.5 rounded font-mono ${getActionBadge(cmd.action_type)}`}>
                        {cmd.action_type}
                      </span>
                      <span className="text-xs text-yellow-400 font-mono">pending approval</span>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleApprove(cmd.command_id)}
                        className="text-xs px-2 py-1 rounded bg-green-900/50 text-green-300 hover:bg-green-800/50"
                      >
                        Approve
                      </button>
                      <button
                        onClick={() => handleReject(cmd.command_id)}
                        className="text-xs px-2 py-1 rounded bg-red-900/50 text-red-300 hover:bg-red-800/50"
                      >
                        Reject
                      </button>
                    </div>
                  </div>
                  <div className="text-sm mt-1">{cmd.raw_input}</div>
                  <div className="text-xs text-muted mt-1">
                    {formatTimestamp(cmd.timestamp)} · {cmd.source} · {cmd.target_domain || 'general'}
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {tab === 'timeline' && (
          <div className="space-y-1">
            {timeline.length === 0 ? (
              <div className="text-sm text-muted text-center py-8">No timeline events</div>
            ) : (
              timeline.map(evt => (
                <div key={evt.event_id} className="flex items-start gap-3 py-2 border-b border-border/50">
                  <span className="text-xs text-muted font-mono w-36 shrink-0">
                    {formatTimestamp(evt.timestamp)}
                  </span>
                  <span className={`text-xs px-2 py-0.5 rounded font-mono shrink-0 ${
                    evt.event_type.includes('completed') ? 'bg-green-900/50 text-green-300' :
                    evt.event_type.includes('failed') ? 'bg-red-900/50 text-red-300' :
                    evt.event_type.includes('approved') ? 'bg-green-900/50 text-green-300' :
                    evt.event_type.includes('rejected') ? 'bg-red-900/50 text-red-300' :
                    'bg-surface-alt text-muted'
                  }`}>
                    {evt.event_type}
                  </span>
                  <span className="text-sm">{evt.summary}</span>
                </div>
              ))
            )}
          </div>
        )}

        {tab === 'history' && (
          <div className="space-y-2">
            {commands.length === 0 ? (
              <div className="text-sm text-muted text-center py-8">No command history</div>
            ) : (
              commands.map(cmd => (
                <div key={cmd.command_id} className="bg-surface-alt rounded-lg border border-border p-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className={`text-xs px-2 py-0.5 rounded font-mono ${getActionBadge(cmd.action_type)}`}>
                        {cmd.action_type}
                      </span>
                      <span className={`text-xs font-mono ${getStatusColor(cmd.status)}`}>{cmd.status}</span>
                      {cmd.target_domain && (
                        <span className="text-xs text-muted">{cmd.target_domain}</span>
                      )}
                    </div>
                    <span className="text-xs text-muted font-mono">{cmd.command_id}</span>
                  </div>
                  <div className="text-sm mt-1 font-mono">{cmd.raw_input}</div>
                  <div className="text-xs text-muted mt-1">
                    {formatTimestamp(cmd.timestamp)} · {cmd.source} · confidence: {(cmd.confidence * 100).toFixed(0)}%
                  </div>
                  {cmd.error && <div className="text-xs text-red-400 mt-1">{cmd.error}</div>}
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  )
}
