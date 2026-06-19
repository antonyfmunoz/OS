import { useEffect, useState } from 'react'
import { RotateCcw, RefreshCw, CheckCircle2, Clock, AlertTriangle } from 'lucide-react'
import { useOperatingLoopStore } from '../stores/operatingLoopStore'

type Tab = 'active' | 'completed' | 'snapshot'

export function OperatingLoopPanel() {
  const [tab, setTab] = useState<Tab>('active')
  const { activeLoops, completedLoops, snapshot, loading, fetchActiveLoops, fetchCompletedLoops, fetchSnapshot } =
    useOperatingLoopStore()

  useEffect(() => {
    fetchActiveLoops()
    fetchCompletedLoops()
    fetchSnapshot()
  }, [])

  const refresh = () => {
    fetchActiveLoops()
    fetchCompletedLoops()
    fetchSnapshot()
  }

  const stageColor = (stage: string): string => {
    switch (stage) {
      case 'INTENT': return 'bg-blue-400/10 text-blue-400'
      case 'PLANNING': return 'bg-purple-400/10 text-purple-400'
      case 'EXECUTING': return 'bg-cyan/10 text-cyan'
      case 'VERIFYING': return 'bg-yellow-400/10 text-yellow-400'
      case 'COMPLETED': return 'bg-green-400/10 text-green-400'
      case 'FAILED': return 'bg-red-400/10 text-red-400'
      default: return 'bg-text-tertiary/10 text-text-tertiary'
    }
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="flex items-center justify-between border-b border-border px-4 h-9 shrink-0">
        <div className="flex items-center gap-2">
          <RotateCcw size={14} className="text-cyan" />
          <span className="text-[10px] font-mono text-cyan uppercase tracking-wider">Operating Loops</span>
          {activeLoops.length > 0 && (
            <span className="text-[9px] font-mono px-2 py-0.5 rounded bg-cyan/10 text-cyan">
              {activeLoops.length} active
            </span>
          )}
        </div>
        <button
          onClick={refresh}
          disabled={loading}
          className="flex items-center gap-1 px-2 py-1 text-[10px] font-mono uppercase bg-cyan/10 text-cyan border border-cyan/30 rounded hover:bg-cyan/20 disabled:opacity-50"
        >
          <RefreshCw size={10} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      <div className="flex border-b border-border shrink-0">
        {(['active', 'completed', 'snapshot'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-2 text-[10px] font-mono uppercase transition-colors ${
              tab === t ? 'text-cyan border-b-2 border-cyan' : 'text-text-tertiary hover:text-text-secondary'
            }`}
          >
            {t}
            {t === 'active' && activeLoops.length > 0 && (
              <span className="ml-1 px-1 bg-cyan/20 text-cyan rounded text-[9px]">{activeLoops.length}</span>
            )}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {loading && activeLoops.length === 0 && (
          <div className="text-text-tertiary text-xs font-mono">Loading operating loops...</div>
        )}

        {tab === 'active' && (
          <div className="space-y-2">
            {activeLoops.map((loop, i) => {
              const stage = (loop as Record<string, unknown>).stage as string ?? 'UNKNOWN'
              const intent = (loop as Record<string, unknown>).intent_text as string ?? `Loop ${i}`
              const id = (loop as Record<string, unknown>).id as string ?? ''
              return (
                <div key={id || i} className="bg-surface-raised border border-border rounded p-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-mono text-text-primary truncate flex-1">{intent}</span>
                    <span className={`text-[9px] font-mono px-2 py-0.5 rounded ml-2 ${stageColor(stage)}`}>
                      {stage}
                    </span>
                  </div>
                  {id && <div className="text-[9px] font-mono text-text-tertiary">{id}</div>}
                </div>
              )
            })}
            {activeLoops.length === 0 && (
              <div className="flex items-center gap-2 text-text-tertiary text-xs font-mono">
                <Clock size={14} />
                No active loops
              </div>
            )}
          </div>
        )}

        {tab === 'completed' && (
          <div className="space-y-2">
            {completedLoops.map((loop, i) => {
              const stage = (loop as Record<string, unknown>).stage as string ?? 'COMPLETED'
              const intent = (loop as Record<string, unknown>).intent_text as string ?? `Loop ${i}`
              const id = (loop as Record<string, unknown>).id as string ?? ''
              const isFailed = stage === 'FAILED'
              return (
                <div key={id || i} className="bg-surface-raised border border-border rounded p-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      {isFailed ? (
                        <AlertTriangle size={12} className="text-red-400 shrink-0" />
                      ) : (
                        <CheckCircle2 size={12} className="text-green-400 shrink-0" />
                      )}
                      <span className="text-xs font-mono text-text-primary truncate">{intent}</span>
                    </div>
                    <span className={`text-[9px] font-mono px-2 py-0.5 rounded ml-2 ${stageColor(stage)}`}>
                      {stage}
                    </span>
                  </div>
                </div>
              )
            })}
            {completedLoops.length === 0 && (
              <div className="text-text-tertiary text-xs font-mono">No completed loops</div>
            )}
          </div>
        )}

        {tab === 'snapshot' && snapshot && (
          <div className="bg-surface-raised border border-border rounded p-3">
            <div className="text-text-tertiary text-[9px] font-mono uppercase mb-2">Loop Snapshot</div>
            <div className="text-xs font-mono text-text-secondary whitespace-pre-wrap">
              {JSON.stringify(snapshot, null, 2)}
            </div>
          </div>
        )}
        {tab === 'snapshot' && !snapshot && (
          <div className="text-text-tertiary text-xs font-mono">No snapshot data</div>
        )}
      </div>
    </div>
  )
}
