import { useState } from 'react'
import { useRealityIntelligenceStore } from '../stores/realityIntelligenceStore'

const SOURCE_TYPE_COLORS: Record<string, string> = {
  instance_observation: 'bg-cyan/20 text-cyan',
  canonical_pattern: 'bg-purple-500/20 text-purple-400',
  memory: 'bg-ok/20 text-ok',
  event: 'bg-warn/20 text-warn',
  priority_ranking: 'bg-blue-500/20 text-blue-400',
}

const SOURCE_TYPE_LABELS: Record<string, string> = {
  instance_observation: 'Instance',
  canonical_pattern: 'Canonical',
  memory: 'Memory',
  event: 'Event',
  priority_ranking: 'Priority',
}

type QueryType = 'why' | 'what_changed' | 'evidence' | 'contradictions' | 'lineage' | 'domain_summary' | 'priorities'

const TABS: { key: QueryType; label: string }[] = [
  { key: 'why', label: 'Why' },
  { key: 'what_changed', label: 'Changes' },
  { key: 'evidence', label: 'Evidence' },
  { key: 'contradictions', label: 'Contradictions' },
  { key: 'lineage', label: 'Lineage' },
  { key: 'priorities', label: 'Priorities' },
  { key: 'domain_summary', label: 'Domain' },
]

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

export function RealityIntelligencePanel() {
  const {
    activeQueryType, result, loading, error,
    setQueryType,
    queryWhy, queryWhatChanged, queryEvidence,
    queryContradictions, queryLineage,
    queryDomainSummary, queryPriorities,
  } = useRealityIntelligenceStore()

  const [inputValue, setInputValue] = useState('')
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const needsEntityInput = ['why', 'evidence', 'lineage'].includes(activeQueryType)
  const needsDomainInput = ['contradictions', 'domain_summary'].includes(activeQueryType)
  const needsNoInput = activeQueryType === 'priorities'
  const needsTimeInput = activeQueryType === 'what_changed'

  const handleSubmit = () => {
    const val = inputValue.trim()
    switch (activeQueryType) {
      case 'why':
        if (val) queryWhy(val)
        break
      case 'what_changed': {
        const since = val ? parseFloat(val) : (Date.now() / 1000) - 86400
        queryWhatChanged(since)
        break
      }
      case 'evidence':
        if (val) queryEvidence(val)
        break
      case 'contradictions':
        queryContradictions(val || undefined)
        break
      case 'lineage':
        if (val) queryLineage(val)
        break
      case 'domain_summary':
        if (val) queryDomainSummary(val)
        break
      case 'priorities':
        queryPriorities()
        break
    }
  }

  return (
    <div className="flex flex-col gap-4 p-4 h-full overflow-auto">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-text-primary">Reality Intelligence</h2>
        {result && (
          <span className="text-xs text-text-secondary">
            {result.evidence.length} results | confidence: {Math.round(result.confidence * 100)}%
          </span>
        )}
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 flex-wrap">
        {TABS.map(tab => (
          <button
            key={tab.key}
            onClick={() => setQueryType(tab.key)}
            className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
              activeQueryType === tab.key
                ? 'bg-accent/20 text-accent'
                : 'bg-surface-overlay text-text-secondary hover:text-text-primary'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Input area */}
      <div className="flex gap-2">
        {!needsNoInput && (
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
            placeholder={
              needsEntityInput ? 'Enter entity name...'
              : needsDomainInput ? 'Enter domain (optional for contradictions)...'
              : needsTimeInput ? 'Hours ago (default: 24)...'
              : ''
            }
            className="flex-1 px-3 py-2 rounded bg-surface-overlay border border-border text-text-primary text-sm placeholder:text-text-secondary"
          />
        )}
        <button
          onClick={handleSubmit}
          disabled={loading || (!needsNoInput && !needsTimeInput && !inputValue.trim() && activeQueryType !== 'contradictions')}
          className="px-4 py-2 rounded bg-accent/20 text-accent text-sm font-medium hover:bg-accent/30 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Querying...' : 'Query'}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="px-3 py-2 rounded bg-danger/10 text-danger text-sm">{error}</div>
      )}

      {/* Reasoning */}
      {result?.reasoning && (
        <div className="px-3 py-2 rounded bg-surface-overlay border border-border">
          <span className="text-xs text-text-secondary">Reasoning: </span>
          <span className="text-xs text-text-primary">{result.reasoning}</span>
          {result.sources_queried.length > 0 && (
            <div className="flex gap-1 mt-1">
              {result.sources_queried.map(s => (
                <span key={s} className="px-1.5 py-0.5 rounded text-[10px] bg-surface-overlay text-text-secondary border border-border">
                  {s}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Results */}
      <div className="flex flex-col gap-2">
        {result?.evidence.map((ev, idx) => {
          const isExpanded = expandedId === `${ev.source_id}-${idx}`
          const colorClass = SOURCE_TYPE_COLORS[ev.source_type] || 'bg-surface-overlay text-text-secondary'
          const label = SOURCE_TYPE_LABELS[ev.source_type] || ev.source_type

          return (
            <div
              key={`${ev.source_id}-${idx}`}
              className="rounded border border-border bg-surface-overlay p-3 cursor-pointer hover:border-border-active"
              onClick={() => setExpandedId(isExpanded ? null : `${ev.source_id}-${idx}`)}
            >
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium shrink-0 ${colorClass}`}>
                    {label}
                  </span>
                  <span className="text-sm text-text-primary truncate">{ev.content}</span>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-[10px] text-text-secondary">{ev.domain}</span>
                  <ConfidenceBar value={ev.confidence} />
                </div>
              </div>

              {isExpanded && (
                <div className="mt-2 pt-2 border-t border-border text-xs text-text-secondary space-y-1">
                  <div><span className="text-text-primary">Source ID:</span> {ev.source_id}</div>
                  <div><span className="text-text-primary">Timestamp:</span> {ev.timestamp}</div>
                  {Object.keys(ev.metadata).length > 0 && (
                    <div>
                      <span className="text-text-primary">Metadata:</span>
                      <pre className="mt-1 text-[11px] whitespace-pre-wrap bg-surface p-2 rounded">
                        {JSON.stringify(ev.metadata, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}

        {result && result.evidence.length === 0 && (
          <div className="text-center py-8 text-text-secondary text-sm">
            No evidence found for this query.
          </div>
        )}

        {!result && !loading && (
          <div className="text-center py-8 text-text-secondary text-sm">
            Select a query type and enter your query above.
          </div>
        )}
      </div>
    </div>
  )
}
