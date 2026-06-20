import { useEffect, useState } from 'react'
import { useRealityTimelineStore } from '../stores/realityTimelineStore'
import { usePolling } from '../hooks/usePolling'

const SOURCE_COLORS: Record<string, string> = {
  execution: 'bg-cyan/20 text-cyan',
  governance: 'bg-warn/20 text-warn',
  conversation_memory: 'bg-ok/20 text-ok',
  observation_api: 'bg-purple-500/20 text-purple-400',
  simulation: 'bg-surface-overlay text-text-secondary',
}

const SOURCE_LABELS: Record<string, string> = {
  execution: 'Execution',
  governance: 'Governance',
  conversation_memory: 'Conversation',
  observation_api: 'API',
  simulation: 'Simulation',
}

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100)
  const color = value >= 0.8 ? 'bg-ok' : value >= 0.5 ? 'bg-warn' : 'bg-danger'
  return (
    <div className="flex items-center gap-2 shrink-0">
      <div className="w-16 h-1.5 rounded bg-surface-overlay overflow-hidden">
        <div className={`h-full rounded ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-text-secondary w-8 text-right">{pct}%</span>
    </div>
  )
}

export function RealityTimelinePanel() {
  const {
    observations, domains, sources, loading, error,
    filterDomain, filterSource,
    fetchTimeline, setFilterDomain, setFilterSource,
  } = useRealityTimelineStore()
  const [expandedId, setExpandedId] = useState<string | null>(null)

  usePolling(() => fetchTimeline(), 10_000)

  useEffect(() => {
    fetchTimeline()
  }, [fetchTimeline, filterDomain, filterSource])

  return (
    <div className="flex flex-col gap-4 p-4 h-full overflow-auto">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-text-primary">Reality Timeline</h2>
        <div className="flex items-center gap-2">
          <select
            className="bg-surface-overlay border border-border rounded px-2 py-1 text-sm text-text-primary"
            value={filterDomain}
            onChange={(e) => { setFilterDomain(e.target.value); fetchTimeline() }}
          >
            <option value="">All Domains</option>
            {domains.map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
          <select
            className="bg-surface-overlay border border-border rounded px-2 py-1 text-sm text-text-primary"
            value={filterSource}
            onChange={(e) => { setFilterSource(e.target.value); fetchTimeline() }}
          >
            <option value="">All Sources</option>
            {sources.map((s) => (
              <option key={s} value={s}>{SOURCE_LABELS[s] || s}</option>
            ))}
          </select>
          {loading && (
            <span className="text-xs text-text-secondary animate-pulse">—</span>
          )}
        </div>
      </div>

      {error && (
        <div className="bg-danger/10 border border-danger/30 rounded p-3 text-sm text-danger">
          {error}
        </div>
      )}

      {observations.length === 0 && !loading && (
        <div className="text-text-secondary text-sm text-center py-8">
          No reality observations yet. Governance decisions, promoted memories, and execution outcomes will appear here.
        </div>
      )}

      <div className="flex flex-col gap-2">
        {observations.map((obs) => {
          const isExpanded = expandedId === obs.id
          const colorClass = SOURCE_COLORS[obs.source_system] || 'bg-surface-overlay text-text-secondary'
          const sourceLabel = SOURCE_LABELS[obs.source_system] || obs.source_system || 'Unknown'

          return (
            <div
              key={obs.id}
              className="bg-surface border border-border rounded-lg overflow-hidden"
            >
              <button
                className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-surface-overlay/50 transition-colors"
                onClick={() => setExpandedId(isExpanded ? null : obs.id)}
              >
                <span className={`px-2 py-0.5 rounded text-xs font-medium shrink-0 ${colorClass}`}>
                  {sourceLabel}
                </span>
                <span className="px-1.5 py-0.5 rounded text-xs bg-surface-overlay text-text-secondary shrink-0">
                  {obs.domain}
                </span>
                <span className="text-sm text-text-primary truncate flex-1">
                  {obs.content}
                </span>
                <ConfidenceBar value={obs.effective_confidence} />
                <span className="text-xs text-text-secondary shrink-0">
                  {new Date(obs.observed_at).toLocaleString()}
                </span>
                <span className="text-text-secondary text-xs shrink-0">
                  {isExpanded ? '▲' : '▼'}
                </span>
              </button>

              {isExpanded && (
                <div className="border-t border-border px-4 py-3 bg-surface-overlay/30">
                  <div className="text-xs text-text-secondary mb-2">
                    <span className="font-medium">Raw confidence:</span> {obs.confidence} |{' '}
                    <span className="font-medium">Effective:</span> {obs.effective_confidence.toFixed(3)}
                  </div>
                  {obs.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-2">
                      {obs.tags.map((tag, i) => (
                        <span
                          key={i}
                          className="px-1.5 py-0.5 rounded text-xs bg-surface-overlay text-text-secondary"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                  {Object.keys(obs.evidence).length > 0 && (
                    <pre className="text-xs text-text-secondary whitespace-pre-wrap break-all max-h-48 overflow-auto">
                      {JSON.stringify(obs.evidence, null, 2)}
                    </pre>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>

      <div className="text-xs text-text-secondary text-center">
        {observations.length} observations
      </div>
    </div>
  )
}
