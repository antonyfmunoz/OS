import { useEffect, useState, useCallback } from 'react'
import {
  Merge,
  Play,
  Pause,
  XCircle,
  CheckCircle2,
  ShieldCheck,
  RefreshCw,
  Clock,
} from 'lucide-react'
import { useUnifiedExecutionStore } from '../stores/unifiedExecutionStore'
import { ExecutorBadge } from '../components/ExecutorBadge'

type Tab = 'active' | 'approvals' | 'history'

const STATUS_COLORS: Record<string, string> = {
  running: 'text-cyan bg-cyan/10',
  queued: 'text-yellow-400 bg-yellow-400/10',
  blocked: 'text-red-400 bg-red-400/10',
  completed: 'text-green-400 bg-green-400/10',
  failed: 'text-red-400 bg-red-400/10',
}

export function UnifiedExecutionPanel() {
  const [tab, setTab] = useState<Tab>('active')
  const {
    snapshot, activeStreams, pendingApprovals, loading,
    fetchSnapshot, fetchActive, fetchPendingApprovals,
    approve, reject,
  } = useUnifiedExecutionStore()

  useEffect(() => {
    fetchSnapshot()
    fetchActive()
    fetchPendingApprovals()
  }, [])

  const handleRefresh = useCallback(() => {
    fetchSnapshot()
    fetchActive()
    fetchPendingApprovals()
  }, [fetchSnapshot, fetchActive, fetchPendingApprovals])

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 h-9 shrink-0">
        <div className="flex items-center gap-2">
          <Merge size={14} className="text-cyan" />
          <span className="text-[10px] font-mono text-cyan uppercase tracking-wider">Unified Execution</span>
        </div>
        <button
          onClick={handleRefresh}
          disabled={loading}
          className="flex items-center gap-1 px-2 py-1 text-[10px] font-mono uppercase bg-cyan/10 text-cyan border border-cyan/30 rounded hover:bg-cyan/20 disabled:opacity-50"
        >
          <RefreshCw size={10} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Summary bar */}
      {snapshot && (
        <div className="flex gap-4 px-4 py-2 border-b border-border shrink-0">
          {(['active_count', 'queued_count', 'blocked_count'] as const).map((k) => (
            <div key={k} className="text-[10px] font-mono">
              <span className="text-text-tertiary uppercase">{k.replace('_count', '')}: </span>
              <span className="text-text-primary">{(snapshot as Record<string, unknown>)[k] as number ?? 0}</span>
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-border shrink-0">
        {(['active', 'approvals', 'history'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-2 text-[10px] font-mono uppercase transition-colors ${
              tab === t ? 'text-cyan border-b-2 border-cyan' : 'text-text-tertiary hover:text-text-secondary'
            }`}
          >
            {t}
            {t === 'approvals' && pendingApprovals.length > 0 && (
              <span className="ml-1 px-1 bg-orange-400/20 text-orange-400 rounded text-[9px]">{pendingApprovals.length}</span>
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {loading && activeStreams.length === 0 && (
          <div className="text-text-tertiary text-xs font-mono">Loading execution streams...</div>
        )}

        {tab === 'active' && (
          <div className="space-y-2">
            {activeStreams.map((s, i) => {
              const status = (s as Record<string, unknown>).status as string ?? 'unknown'
              return (
                <div key={i} className="bg-surface-raised border border-border rounded p-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {status === 'running' ? <Play size={12} className="text-cyan" /> :
                       status === 'blocked' ? <Pause size={12} className="text-red-400" /> :
                       <Clock size={12} className="text-yellow-400" />}
                      <span className="text-xs font-mono text-text-primary">
                        {(s as Record<string, unknown>).label as string ?? `Stream ${i}`}
                        <ExecutorBadge executorType={(s as Record<string, unknown>).executor_type as string} targetMachine={(s as Record<string, unknown>).target_machine as string} />
                      </span>
                    </div>
                    <span className={`text-[9px] font-mono px-2 py-0.5 rounded ${STATUS_COLORS[status] ?? 'text-text-tertiary bg-surface-raised'}`}>
                      {status}
                    </span>
                  </div>
                  <div className="text-[10px] font-mono text-text-tertiary mt-1">
                    {(s as Record<string, unknown>).source as string ?? ''} — {(s as Record<string, unknown>).type as string ?? ''}
                  </div>
                </div>
              )
            })}
            {activeStreams.length === 0 && !loading && (
              <div className="text-text-tertiary text-xs font-mono">No active execution streams</div>
            )}
          </div>
        )}

        {tab === 'approvals' && (
          <div className="space-y-2">
            {pendingApprovals.map((a, i) => (
              <div key={i} className="bg-surface-raised border border-border rounded p-3">
                <div className="flex items-center gap-2 mb-2">
                  <ShieldCheck size={12} className="text-orange-400" />
                  <span className="text-xs font-mono text-text-primary">
                    {(a as Record<string, unknown>).label as string ?? `Approval ${i}`}
                  </span>
                </div>
                <div className="text-[10px] font-mono text-text-tertiary mb-3">
                  Risk: {(a as Record<string, unknown>).risk_level as string ?? 'unknown'} — Source: {(a as Record<string, unknown>).source as string ?? ''}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => approve(
                      (a as Record<string, unknown>).id as string ?? '',
                      (a as Record<string, unknown>).source as string ?? '',
                    )}
                    className="flex items-center gap-1 px-2 py-1 text-[10px] font-mono bg-green-400/10 text-green-400 border border-green-400/30 rounded hover:bg-green-400/20"
                  >
                    <CheckCircle2 size={10} /> Approve
                  </button>
                  <button
                    onClick={() => reject(
                      (a as Record<string, unknown>).id as string ?? '',
                      (a as Record<string, unknown>).source as string ?? '',
                      'Rejected from cockpit',
                    )}
                    className="flex items-center gap-1 px-2 py-1 text-[10px] font-mono bg-red-400/10 text-red-400 border border-red-400/30 rounded hover:bg-red-400/20"
                  >
                    <XCircle size={10} /> Reject
                  </button>
                </div>
              </div>
            ))}
            {pendingApprovals.length === 0 && (
              <div className="flex items-center gap-2 text-green-400 text-xs font-mono">
                <CheckCircle2 size={14} />
                No pending approvals
              </div>
            )}
          </div>
        )}

        {tab === 'history' && snapshot && (
          <div className="space-y-2">
            {(((snapshot as Record<string, unknown>).recent_completions as Record<string, unknown>[]) ?? []).map((h, i) => (
              <div key={i} className="bg-surface-raised border border-border rounded p-3 flex items-center justify-between">
                <div>
                  <div className="text-xs font-mono text-text-primary">{(h as Record<string, unknown>).label as string ?? `Execution ${i}`}</div>
                  <div className="text-[10px] font-mono text-text-tertiary mt-1">{(h as Record<string, unknown>).completed_at as string ?? ''}</div>
                </div>
                <span className={`text-[9px] font-mono px-2 py-0.5 rounded ${
                  (h as Record<string, unknown>).outcome === 'success' ? 'bg-green-400/10 text-green-400' : 'bg-red-400/10 text-red-400'
                }`}>
                  {(h as Record<string, unknown>).outcome as string ?? 'unknown'}
                </span>
              </div>
            ))}
            {(((snapshot as Record<string, unknown>).recent_completions as unknown[]) ?? []).length === 0 && (
              <div className="text-text-tertiary text-xs font-mono">No completed executions yet</div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
