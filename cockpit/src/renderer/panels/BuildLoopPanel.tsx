import { useEffect, useState, useCallback } from 'react'
import {
  Hammer,
  Send,
  RefreshCw,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Play,
} from 'lucide-react'
import { useBuildLoopStore } from '../stores/buildLoopStore'

type Tab = 'submit' | 'active' | 'history'

const PHASE_COLORS: Record<string, string> = {
  intent_capture: 'text-text-tertiary bg-surface-raised',
  classification: 'text-yellow-400 bg-yellow-400/10',
  planning: 'text-blue-400 bg-blue-400/10',
  assignment: 'text-purple-400 bg-purple-400/10',
  execution: 'text-cyan bg-cyan/10',
  review: 'text-orange-400 bg-orange-400/10',
  merge: 'text-green-400 bg-green-400/10',
  complete: 'text-green-400 bg-green-400/10',
}

export function BuildLoopPanel() {
  const [tab, setTab] = useState<Tab>('submit')
  const [text, setText] = useState('')
  const [target, setTarget] = useState('')
  const { status, activeRequests, history, loading, fetchStatus, fetchActive, fetchHistory, submit } =
    useBuildLoopStore()

  useEffect(() => {
    fetchStatus()
    fetchActive()
    fetchHistory()
  }, [])

  const handleSubmit = useCallback(async () => {
    if (!text.trim()) return
    await submit(text, target || undefined)
    setText('')
    setTarget('')
    setTab('active')
  }, [text, target, submit])

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 h-9 shrink-0">
        <div className="flex items-center gap-2">
          <Hammer size={14} className="text-cyan" />
          <span className="text-[10px] font-mono text-cyan uppercase tracking-wider">Build Loop</span>
        </div>
        <div className="flex items-center gap-3">
          {status && (
            <span className="text-[10px] font-mono text-text-tertiary">
              {(status as Record<string, unknown>).active_requests as number ?? 0} active
            </span>
          )}
          <button
            onClick={() => { fetchStatus(); fetchActive(); fetchHistory() }}
            disabled={loading}
            className="flex items-center gap-1 px-2 py-1 text-[10px] font-mono uppercase bg-cyan/10 text-cyan border border-cyan/30 rounded hover:bg-cyan/20 disabled:opacity-50"
          >
            <RefreshCw size={10} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-border shrink-0">
        {(['submit', 'active', 'history'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-2 text-[10px] font-mono uppercase transition-colors ${
              tab === t ? 'text-cyan border-b-2 border-cyan' : 'text-text-tertiary hover:text-text-secondary'
            }`}
          >
            {t}
            {t === 'active' && activeRequests.length > 0 && (
              <span className="ml-1 px-1 bg-cyan/20 text-cyan rounded text-[9px]">{activeRequests.length}</span>
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {tab === 'submit' && (
          <div className="space-y-4">
            <div>
              <label className="block text-[10px] font-mono text-text-tertiary uppercase mb-1">Build Request</label>
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Describe what to build..."
                className="w-full h-24 bg-surface-raised border border-border rounded p-2 text-xs font-mono text-text-primary placeholder:text-text-tertiary resize-none focus:outline-none focus:border-cyan/50"
              />
            </div>
            <div>
              <label className="block text-[10px] font-mono text-text-tertiary uppercase mb-1">Projection Target (optional)</label>
              <input
                value={target}
                onChange={(e) => setTarget(e.target.value)}
                placeholder="e.g. lyfeos, creatoros, entrepreneuros"
                className="w-full bg-surface-raised border border-border rounded p-2 text-xs font-mono text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-cyan/50"
              />
            </div>
            <button
              onClick={handleSubmit}
              disabled={!text.trim() || loading}
              className="flex items-center gap-2 px-3 py-2 text-[10px] font-mono uppercase bg-cyan/10 text-cyan border border-cyan/30 rounded hover:bg-cyan/20 disabled:opacity-50"
            >
              <Send size={12} />
              Submit Build Request
            </button>
          </div>
        )}

        {tab === 'active' && (
          <div className="space-y-2">
            {activeRequests.map((r, i) => {
              const phase = (r as Record<string, unknown>).phase as string ?? 'unknown'
              return (
                <div key={i} className="bg-surface-raised border border-border rounded p-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-mono text-text-primary truncate max-w-[60%]">
                      {(r as Record<string, unknown>).text as string ?? `Request ${i}`}
                    </span>
                    <span className={`text-[9px] font-mono px-2 py-0.5 rounded ${PHASE_COLORS[phase] ?? 'text-text-tertiary bg-surface-raised'}`}>
                      {phase}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-[10px] font-mono text-text-tertiary">
                    {(r as Record<string, unknown>).projection_target && (
                      <span>Target: {(r as Record<string, unknown>).projection_target as string}</span>
                    )}
                    <span>ID: {((r as Record<string, unknown>).request_id as string ?? '').slice(0, 12)}</span>
                  </div>
                  {(r as Record<string, unknown>).error && (
                    <div className="flex items-center gap-1 mt-2 text-[10px] font-mono text-orange-400">
                      <AlertTriangle size={10} />
                      {(r as Record<string, unknown>).error as string}
                    </div>
                  )}
                </div>
              )
            })}
            {activeRequests.length === 0 && (
              <div className="text-text-tertiary text-xs font-mono">No active build requests</div>
            )}
          </div>
        )}

        {tab === 'history' && (
          <div className="space-y-2">
            {history.map((h, i) => (
              <div key={i} className="bg-surface-raised border border-border rounded p-3 flex items-center justify-between">
                <div>
                  <div className="text-xs font-mono text-text-primary truncate max-w-[70%]">
                    {(h as Record<string, unknown>).text as string ?? `Build ${i}`}
                  </div>
                  <div className="text-[10px] font-mono text-text-tertiary mt-1">
                    {(h as Record<string, unknown>).projection_target && (
                      <span>{(h as Record<string, unknown>).projection_target as string} — </span>
                    )}
                    {(h as Record<string, unknown>).request_id as string ?? ''}
                  </div>
                </div>
                <CheckCircle2 size={14} className="text-green-400 shrink-0" />
              </div>
            ))}
            {history.length === 0 && (
              <div className="text-text-tertiary text-xs font-mono">No completed builds yet</div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
