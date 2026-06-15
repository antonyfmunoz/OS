import { useEffect, useState } from 'react'
import { useOperatorTimelineStore } from '../stores/operatorTimelineStore'
import { usePolling } from '../hooks/usePolling'

const TYPE_COLORS: Record<string, string> = {
  intent_receipt: 'bg-cyan/20 text-cyan',
  event: 'bg-surface-overlay text-text-secondary',
  governance: 'bg-warn/20 text-warn',
  work_packet: 'bg-ok/20 text-ok',
  memory_write: 'bg-purple-500/20 text-purple-400',
}

const TYPE_LABELS: Record<string, string> = {
  intent_receipt: 'Intent',
  event: 'Event',
  governance: 'Governance',
  work_packet: 'Work Packet',
  memory_write: 'Memory',
}

function formatTs(ts: number): string {
  return new Date(ts * 1000).toLocaleString()
}

export function OperatorTimelinePanel() {
  const { entries, loading, error, selectedIntentId, fetchTimeline, selectIntent } =
    useOperatorTimelineStore()
  const [filterType, setFilterType] = useState<string>('')
  const [expandedId, setExpandedId] = useState<string | null>(null)

  usePolling(fetchTimeline, 10_000)

  useEffect(() => {
    fetchTimeline()
  }, [fetchTimeline])

  const filtered = filterType
    ? entries.filter((e) => e.entry_type === filterType)
    : entries

  return (
    <div className="flex flex-col gap-4 p-4 h-full overflow-auto">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-text-primary">Operator Timeline</h2>
        <div className="flex items-center gap-2">
          <select
            className="bg-surface-overlay border border-border rounded px-2 py-1 text-sm text-text-primary"
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
          >
            <option value="">All Types</option>
            <option value="intent_receipt">Intents</option>
            <option value="work_packet">Work Packets</option>
            <option value="event">Events</option>
            <option value="governance">Governance</option>
            <option value="memory_write">Memory</option>
          </select>
          {loading && (
            <span className="text-xs text-text-secondary animate-pulse">Loading...</span>
          )}
        </div>
      </div>

      {error && (
        <div className="bg-danger/10 border border-danger/30 rounded p-3 text-sm text-danger">
          {error}
        </div>
      )}

      {filtered.length === 0 && !loading && (
        <div className="text-text-secondary text-sm text-center py-8">
          No timeline entries yet. Operator intents will appear here.
        </div>
      )}

      <div className="flex flex-col gap-2">
        {filtered.map((entry) => {
          const isExpanded = expandedId === entry.entry_id
          const colorClass = TYPE_COLORS[entry.entry_type] || 'bg-surface-overlay text-text-secondary'
          const typeLabel = TYPE_LABELS[entry.entry_type] || entry.entry_type

          return (
            <div
              key={entry.entry_id}
              className="bg-surface border border-border rounded-lg overflow-hidden"
            >
              <button
                className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-surface-overlay/50 transition-colors"
                onClick={() => setExpandedId(isExpanded ? null : entry.entry_id)}
              >
                <span
                  className={`px-2 py-0.5 rounded text-xs font-medium shrink-0 ${colorClass}`}
                >
                  {typeLabel}
                </span>
                <span className="text-sm text-text-primary truncate flex-1">
                  {entry.summary}
                </span>
                <span className="text-xs text-text-secondary shrink-0">
                  {formatTs(entry.timestamp)}
                </span>
                <span className="text-text-secondary text-xs shrink-0">
                  {isExpanded ? '▲' : '▼'}
                </span>
              </button>

              {isExpanded && (
                <div className="border-t border-border px-4 py-3 bg-surface-overlay/30">
                  <pre className="text-xs text-text-secondary whitespace-pre-wrap break-all max-h-64 overflow-auto">
                    {JSON.stringify(entry.details, null, 2)}
                  </pre>
                  {entry.intent_id && (
                    <div className="mt-2 text-xs text-text-secondary">
                      Intent ID: <span className="text-cyan font-mono">{entry.intent_id}</span>
                    </div>
                  )}
                  {entry.correlation_id && entry.correlation_id !== entry.intent_id && (
                    <div className="text-xs text-text-secondary">
                      Correlation: <span className="font-mono">{entry.correlation_id}</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>

      <div className="text-xs text-text-secondary text-center">
        {filtered.length} entries
        {filtered.length !== entries.length && ` (${entries.length} total)`}
      </div>
    </div>
  )
}
