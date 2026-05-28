import { useState, useRef, useEffect } from 'react'
import { useRealtimeStore, EventDomainFilter, OrganismEvent } from '../stores/realtimeStore'
import { relativeTime } from '../lib/time'

const DOMAIN_COLORS: Record<string, string> = {
  runtime: 'text-cyan',
  governance: 'text-purple',
  advisor: 'text-amber',
  workcell: 'text-ok',
  objective: 'text-blue',
  execution: 'text-ok',
  leverage: 'text-emerald',
  supervisor: 'text-red',
  filesystem: 'text-text-secondary',
  tmux: 'text-text-secondary',
  docker: 'text-blue',
  projection: 'text-purple',
  transport: 'text-cyan',
  recursion: 'text-warn',
  memory: 'text-amber',
  observability: 'text-text-secondary',
}

const PRIORITY_COLORS: Record<string, string> = {
  low: 'text-text-tertiary',
  normal: 'text-text-secondary',
  high: 'text-warn',
  critical: 'text-danger',
}

const FILTER_GROUPS: { label: string; value: EventDomainFilter }[] = [
  { label: 'ALL', value: 'all' },
  { label: 'GOV', value: 'governance' },
  { label: 'EXEC', value: 'execution' },
  { label: 'RUNTIME', value: 'runtime' },
  { label: 'LEVERAGE', value: 'leverage' },
  { label: 'SUPERVISOR', value: 'supervisor' },
  { label: 'OBSERVE', value: 'observability' },
  { label: 'MUTATION', value: 'mutation' },
]

function matchesFilter(event: OrganismEvent, filter: EventDomainFilter): boolean {
  if (filter === 'all') return true
  if (filter === 'mutation') {
    return ['governance', 'execution'].includes(event.domain) &&
      (event.event_type.includes('mutation') || event.event_type.includes('envelope') || event.event_type.includes('spine'))
  }
  if (filter === 'bottleneck') {
    return event.domain === 'observability' && event.event_type.includes('bottleneck')
  }
  return event.domain === filter
}

interface EventConsoleProps {
  maxHeight?: string
  compact?: boolean
}

export function EventConsole({ maxHeight = '400px', compact = false }: EventConsoleProps) {
  const events = useRealtimeStore((s) => s.events)
  const status = useRealtimeStore((s) => s.status)
  const domainFilter = useRealtimeStore((s) => s.domainFilter)
  const setDomainFilter = useRealtimeStore((s) => s.setDomainFilter)
  const eventsPerMinute = useRealtimeStore((s) => s.eventsPerMinute)
  const eventCount = useRealtimeStore((s) => s.eventCount)
  const lastEventTimestamp = useRealtimeStore((s) => s.lastEventTimestamp)

  const [expanded, setExpanded] = useState<string | null>(null)
  const [autoscroll, setAutoscroll] = useState(true)
  const scrollRef = useRef<HTMLDivElement>(null)

  const filtered = events.filter((e) => matchesFilter(e, domainFilter))

  useEffect(() => {
    if (autoscroll && scrollRef.current) {
      scrollRef.current.scrollTop = 0
    }
  }, [events, autoscroll])

  const statusColor = status === 'connected' ? 'bg-ok' : status === 'connecting' ? 'bg-warn animate-pulse' : status === 'fallback' ? 'bg-amber' : 'bg-danger'

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-2 mb-2">
        <span className={`w-2 h-2 rounded-full shrink-0 ${statusColor}`} />
        <h3 className="wv-label">EventSpine</h3>
        <span className="text-[10px] text-text-tertiary">
          {eventCount} total · {eventsPerMinute}/min
        </span>
        {lastEventTimestamp && (
          <span className="text-[10px] text-text-tertiary ml-auto">
            last: {relativeTime(new Date(lastEventTimestamp * 1000).toISOString())}
          </span>
        )}
        <button
          onClick={() => setAutoscroll(!autoscroll)}
          className={`text-[9px] font-mono px-1.5 py-0.5 rounded border ${
            autoscroll ? 'border-ok/30 text-ok' : 'border-border text-text-tertiary'
          }`}
        >
          {autoscroll ? 'LIVE' : 'PAUSED'}
        </button>
      </div>

      {/* Filter bar */}
      <div className="flex gap-1 mb-2 flex-wrap">
        {FILTER_GROUPS.map((f) => (
          <button
            key={f.value}
            onClick={() => setDomainFilter(f.value)}
            className={`text-[9px] font-mono px-1.5 py-0.5 rounded border transition-colors ${
              domainFilter === f.value
                ? 'border-cyan/50 text-cyan bg-cyan/5'
                : 'border-border text-text-tertiary hover:text-text-secondary'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Event stream */}
      <div
        ref={scrollRef}
        className="overflow-y-auto space-y-0"
        style={{ maxHeight }}
      >
        {filtered.length === 0 && (
          <p className="text-xs text-text-tertiary py-2">
            {events.length === 0 ? 'Waiting for events...' : `No ${domainFilter} events`}
          </p>
        )}
        {filtered.slice(0, compact ? 20 : 100).map((ev) => (
          <div key={ev.event_id} className="group">
            <div
              className="flex items-center gap-1.5 py-0.5 px-1 rounded cursor-pointer hover:bg-surface-overlay/30"
              onClick={() => setExpanded(expanded === ev.event_id ? null : ev.event_id)}
            >
              <span
                className={`text-[9px] font-mono w-16 shrink-0 truncate ${DOMAIN_COLORS[ev.domain] ?? 'text-text-tertiary'}`}
              >
                {ev.domain}
              </span>
              <span className="text-[11px] text-text-primary truncate flex-1">
                {ev.event_type}
              </span>
              {ev.priority !== 'normal' && (
                <span className={`text-[9px] font-mono ${PRIORITY_COLORS[ev.priority] ?? 'text-text-tertiary'}`}>
                  {ev.priority}
                </span>
              )}
              <span className="text-[10px] text-text-tertiary shrink-0">{ev.source}</span>
              {ev.correlation_id && (
                <span className="text-[9px] text-text-tertiary font-mono shrink-0" title={ev.correlation_id}>
                  {ev.correlation_id.slice(0, 6)}
                </span>
              )}
              <span className="text-[10px] text-text-tertiary shrink-0">
                {relativeTime(new Date(ev.timestamp * 1000).toISOString())}
              </span>
            </div>

            {expanded === ev.event_id && (
              <div className="ml-4 mb-1 p-2 rounded bg-surface border border-border text-[10px] font-mono text-text-secondary whitespace-pre-wrap">
                {JSON.stringify(ev.data, null, 2)}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
