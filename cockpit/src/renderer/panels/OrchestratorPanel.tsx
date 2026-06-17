import { useEffect, useState } from 'react'
import { Brain, RefreshCw, Activity, Shield } from 'lucide-react'
import { useOrchestratorAwarenessStore } from '../stores/orchestratorAwarenessStore'

type Tab = 'context' | 'health' | 'score'

export function OrchestratorPanel() {
  const [tab, setTab] = useState<Tab>('context')
  const { context, snapshot, healthItems, score, loading, fetchContext, fetchSnapshot, fetchHealth, fetchScore } =
    useOrchestratorAwarenessStore()

  useEffect(() => {
    fetchContext()
    fetchSnapshot()
    fetchHealth()
    fetchScore()
  }, [])

  const refresh = () => {
    fetchContext()
    fetchSnapshot()
    fetchHealth()
    fetchScore()
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="flex items-center justify-between border-b border-border px-4 h-9 shrink-0">
        <div className="flex items-center gap-2">
          <Brain size={14} className="text-cyan" />
          <span className="text-[10px] font-mono text-cyan uppercase tracking-wider">Orchestrator Awareness</span>
          {score !== null && (
            <span className={`text-[9px] font-mono px-2 py-0.5 rounded ${
              score >= 0.8 ? 'bg-green-400/10 text-green-400' : score >= 0.5 ? 'bg-yellow-400/10 text-yellow-400' : 'bg-red-400/10 text-red-400'
            }`}>
              {(score * 100).toFixed(0)}%
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
        {(['context', 'health', 'score'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-2 text-[10px] font-mono uppercase transition-colors ${
              tab === t ? 'text-cyan border-b-2 border-cyan' : 'text-text-tertiary hover:text-text-secondary'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {loading && !context && (
          <div className="text-text-tertiary text-xs font-mono">Loading orchestrator awareness...</div>
        )}

        {tab === 'context' && context && (
          <div className="space-y-3">
            {Object.entries(context).map(([key, value]) => (
              <div key={key} className="bg-surface-raised border border-border rounded p-3">
                <div className="text-text-tertiary text-[9px] font-mono uppercase">{key.replace(/_/g, ' ')}</div>
                <div className="text-xs font-mono text-text-secondary mt-1 whitespace-pre-wrap">
                  {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                </div>
              </div>
            ))}
          </div>
        )}

        {tab === 'health' && (
          <div className="space-y-2">
            {healthItems.map((item, i) => {
              const status = (item as Record<string, unknown>).status as string ?? 'unknown'
              const domain = (item as Record<string, unknown>).domain as string ?? `Domain ${i}`
              return (
                <div key={i} className="bg-surface-raised border border-border rounded p-3 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {status === 'healthy' ? (
                      <Activity size={14} className="text-green-400" />
                    ) : (
                      <Shield size={14} className="text-orange-400" />
                    )}
                    <span className="text-xs font-mono text-text-primary">{domain}</span>
                  </div>
                  <span className={`text-[9px] font-mono px-2 py-0.5 rounded ${
                    status === 'healthy' ? 'bg-green-400/10 text-green-400' : 'bg-orange-400/10 text-orange-400'
                  }`}>
                    {status}
                  </span>
                </div>
              )
            })}
            {healthItems.length === 0 && (
              <div className="text-text-tertiary text-xs font-mono">No domain health data</div>
            )}
          </div>
        )}

        {tab === 'score' && (
          <div className="space-y-4">
            <div className="bg-surface-raised border border-border rounded p-4 text-center">
              <div className="text-text-tertiary text-[9px] font-mono uppercase mb-2">Awareness Score</div>
              <div className={`text-3xl font-mono ${
                score !== null && score >= 0.8 ? 'text-green-400' : score !== null && score >= 0.5 ? 'text-yellow-400' : 'text-red-400'
              }`}>
                {score !== null ? `${(score * 100).toFixed(0)}%` : '—'}
              </div>
            </div>
            {snapshot && (
              <div className="bg-surface-raised border border-border rounded p-3">
                <div className="text-text-tertiary text-[9px] font-mono uppercase mb-2">Snapshot</div>
                <div className="text-xs font-mono text-text-secondary whitespace-pre-wrap">
                  {JSON.stringify(snapshot, null, 2)}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
