import { useEffect, useState } from 'react'
import { Target, RefreshCw, AlertTriangle, CheckCircle2, ArrowRight } from 'lucide-react'
import { useMvpReadinessStore } from '../stores/mvpReadinessStore'

type Tab = 'overview' | 'blockers' | 'escapepoints' | 'next'

export function MVPReadinessPanel() {
  const [tab, setTab] = useState<Tab>('overview')
  const {
    assessment, score, blockers, escapePoints, nextSteps, loading,
    fetchAssessment, fetchScore, fetchBlockers, fetchEscapePoints, fetchNextSteps,
  } = useMvpReadinessStore()

  useEffect(() => {
    fetchAssessment()
    fetchScore()
    fetchBlockers()
    fetchEscapePoints()
    fetchNextSteps()
  }, [])

  const refresh = () => {
    fetchAssessment()
    fetchScore()
    fetchBlockers()
    fetchEscapePoints()
    fetchNextSteps()
  }

  const scoreColor = score !== null
    ? score >= 0.8 ? 'text-green-400' : score >= 0.5 ? 'text-yellow-400' : 'text-red-400'
    : 'text-text-tertiary'

  const scoreBg = score !== null
    ? score >= 0.8 ? 'bg-green-400' : score >= 0.5 ? 'bg-yellow-400' : 'bg-red-400'
    : 'bg-text-tertiary'

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="flex items-center justify-between border-b border-border px-4 h-9 shrink-0">
        <div className="flex items-center gap-2">
          <Target size={14} className="text-cyan" />
          <span className="text-[10px] font-mono text-cyan uppercase tracking-wider">MVP Readiness</span>
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
        {(['overview', 'blockers', 'escapepoints', 'next'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-2 text-[10px] font-mono uppercase transition-colors ${
              tab === t ? 'text-cyan border-b-2 border-cyan' : 'text-text-tertiary hover:text-text-secondary'
            }`}
          >
            {t === 'escapepoints' ? 'escape' : t}
            {t === 'blockers' && blockers.length > 0 && (
              <span className="ml-1 px-1 bg-red-400/20 text-red-400 rounded text-[9px]">{blockers.length}</span>
            )}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {loading && !assessment && (
          <div className="text-text-tertiary text-xs font-mono">Loading MVP readiness...</div>
        )}

        {tab === 'overview' && (
          <div className="space-y-4">
            <div className="bg-surface-raised border border-border rounded p-4 text-center">
              <div className="text-text-tertiary text-[9px] font-mono uppercase mb-2">Readiness Score</div>
              <div className={`text-3xl font-mono ${scoreColor}`}>
                {score !== null ? `${(score * 100).toFixed(0)}%` : '—'}
              </div>
              {score !== null && (
                <div className="mt-2 h-2 bg-surface rounded-full overflow-hidden">
                  <div className={`h-full rounded-full transition-all ${scoreBg}`} style={{ width: `${score * 100}%` }} />
                </div>
              )}
            </div>

            {assessment && (
              <div className="bg-surface-raised border border-border rounded p-3">
                <div className="text-text-tertiary text-[9px] font-mono uppercase mb-2">Assessment</div>
                <div className="text-xs font-mono text-text-secondary whitespace-pre-wrap">
                  {JSON.stringify(assessment, null, 2)}
                </div>
              </div>
            )}
          </div>
        )}

        {tab === 'blockers' && (
          <div className="space-y-2">
            {blockers.map((blocker, i) => (
              <div key={i} className="bg-surface-raised border border-border rounded p-3 flex items-start gap-3">
                <AlertTriangle size={14} className="text-red-400 shrink-0 mt-0.5" />
                <span className="text-xs font-mono text-text-primary">{blocker}</span>
              </div>
            ))}
            {blockers.length === 0 && (
              <div className="flex items-center gap-2 text-green-400 text-xs font-mono">
                <CheckCircle2 size={14} />
                No blockers — all dimensions passing
              </div>
            )}
          </div>
        )}

        {tab === 'escapepoints' && (
          <div className="space-y-2">
            {escapePoints.map((ep, i) => {
              const name = (ep as Record<string, unknown>).name as string ?? `Escape Point ${i}`
              const desc = (ep as Record<string, unknown>).description as string ?? ''
              return (
                <div key={i} className="bg-surface-raised border border-border rounded p-3">
                  <div className="text-xs font-mono text-text-primary">{name}</div>
                  {desc && <div className="text-[10px] font-mono text-text-tertiary mt-1">{desc}</div>}
                </div>
              )
            })}
            {escapePoints.length === 0 && (
              <div className="text-text-tertiary text-xs font-mono">No escape points identified</div>
            )}
          </div>
        )}

        {tab === 'next' && (
          <div className="space-y-2">
            {nextSteps.map((step, i) => (
              <div key={i} className="bg-surface-raised border border-border rounded p-3 flex items-center gap-3">
                <ArrowRight size={14} className="text-cyan shrink-0" />
                <span className="text-xs font-mono text-text-primary">{step}</span>
              </div>
            ))}
            {nextSteps.length === 0 && (
              <div className="text-text-tertiary text-xs font-mono">No recommended next steps</div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
