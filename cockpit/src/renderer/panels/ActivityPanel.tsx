import { useRef, useEffect } from 'react'
import { useActivityStore } from '../stores/activityStore'
import { usePolling } from '../hooks/usePolling'

const SEVERITY_COLORS: Record<string, string> = {
  info: 'text-cyan',
  warning: 'text-warn',
  error: 'text-danger',
}

const SEVERITY_BG: Record<string, string> = {
  info: 'bg-cyan',
  warning: 'bg-warn',
  error: 'bg-danger',
}

export function ActivityPanel() {
  const events = useActivityStore((s) => s.events)
  const filter = useActivityStore((s) => s.filter)
  const autoScroll = useActivityStore((s) => s.autoScroll)
  const fetchEvents = useActivityStore((s) => s.fetchEvents)
  const setAutoScroll = useActivityStore((s) => s.setAutoScroll)
  const scrollRef = useRef<HTMLDivElement>(null)

  usePolling(fetchEvents, 3000)

  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [events, autoScroll])

  const filtered = events.filter((e) => {
    if (filter.source && e.source !== filter.source) return false
    if (filter.type && e.type !== filter.type) return false
    if (filter.severity && e.severity !== filter.severity) return false
    return true
  })

  const sources = [...new Set(events.map((e) => e.source))].sort()

  return (
    <div className="flex flex-col h-full">
      {/* Filter bar */}
      <div className="flex items-center gap-3 px-4 h-10 shrink-0 border-b border-border">
        <span className="wv-label">Event Intelligence</span>
        <span className="wv-label">·</span>
        <span className="wv-label">
          <span className="text-cyan">{filtered.length}</span> events
        </span>

        <div className="flex-1" />

        {/* Source filter */}
        <select
          value={filter.source || ''}
          onChange={(e) =>
            useActivityStore.getState().setFilter('source', e.target.value || null)
          }
          className="text-xs px-2 py-1 rounded bg-transparent text-text-secondary border border-border outline-none"
        >
          <option value="">All sources</option>
          {sources.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>

        {/* Auto-scroll */}
        <button
          onClick={() => setAutoScroll(!autoScroll)}
          className={`text-xs px-2 py-1 rounded border border-border transition-colors ${
            autoScroll ? 'text-cyan bg-cyan-glow' : 'text-text-tertiary'
          }`}
        >
          {autoScroll ? '⏬ auto' : '⏸ paused'}
        </button>
      </div>

      {/* Event stream */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto font-mono text-xs"
        onMouseEnter={() => setAutoScroll(false)}
        onMouseLeave={() => setAutoScroll(true)}
      >
        {filtered.map((event) => (
          <div
            key={event.id}
            className="flex items-start gap-2 px-4 py-1.5 border-b border-border hover:bg-surface-raised transition-colors"
          >
            <span className="w-14 shrink-0 text-text-tertiary">
              {new Date(event.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
            </span>
            <span className={`w-1.5 h-1.5 rounded-full mt-1.5 shrink-0 ${SEVERITY_BG[event.severity] || 'bg-cyan'}`} />
            <span className="w-16 shrink-0 truncate text-text-tertiary">{event.source}</span>
            <span className="flex-1 text-text-secondary">{event.summary}</span>
          </div>
        ))}
        {filtered.length === 0 && (
          <p className="text-center py-8 text-text-tertiary font-sans">No events to display</p>
        )}
      </div>
    </div>
  )
}
