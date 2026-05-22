import { useState, useMemo } from 'react'
import { clsx } from 'clsx'
import { useCockpitStore } from '../stores/cockpitStore.ts'
import { relativeTime } from '../lib/time.ts'
import type { ActivityEvent } from '../api/client.ts'

type SourceFilter = ActivityEvent['source'] | 'all'

const SOURCE_OPTIONS: { id: SourceFilter; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'trace', label: 'Traces' },
  { id: 'comms', label: 'Comms' },
  { id: 'approval', label: 'Approvals' },
  { id: 'organism', label: 'Organism' },
]

const SOURCE_BADGE: Record<ActivityEvent['source'], string> = {
  trace: 'wv-badge-cyan',
  comms: 'wv-badge-ok',
  approval: 'wv-badge-warn',
  organism: 'wv-badge-violet',
}

const SOURCE_ICON: Record<ActivityEvent['source'], string> = {
  trace: '⟐',
  comms: '◈',
  approval: '◊',
  organism: '◉',
}

function StatsStrip({ events }: { events: ActivityEvent[] }) {
  const traces = events.filter((e) => e.source === 'trace').length
  const comms = events.filter((e) => e.source === 'comms').length
  const approvals = events.filter((e) => e.source === 'approval').length
  const organism = events.filter((e) => e.source === 'organism').length

  return (
    <div className="grid grid-cols-5 gap-3 mb-4">
      <div className="wv-card p-3 text-center">
        <div className="wv-metric text-text-primary">{events.length}</div>
        <div className="wv-label mt-1">TOTAL</div>
      </div>
      <div className="wv-card p-3 text-center">
        <div className="wv-metric text-cyan">{traces}</div>
        <div className="wv-label mt-1">TRACES</div>
      </div>
      <div className="wv-card p-3 text-center">
        <div className="wv-metric text-ok">{comms}</div>
        <div className="wv-label mt-1">COMMS</div>
      </div>
      <div className="wv-card p-3 text-center">
        <div className="wv-metric text-warn">{approvals}</div>
        <div className="wv-label mt-1">APPROVALS</div>
      </div>
      <div className="wv-card p-3 text-center">
        <div className="wv-metric text-violet">{organism}</div>
        <div className="wv-label mt-1">ORGANISM</div>
      </div>
    </div>
  )
}

function EventRow({
  event,
  selected,
  onClick,
}: {
  event: ActivityEvent
  selected: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        'w-full flex items-center gap-3 py-2 px-3 text-[11px] font-mono border-b border-border/50 transition-colors text-left',
        selected ? 'bg-cyan/5 border-l-2 border-l-cyan' : 'hover:bg-surface-hover',
      )}
    >
      <span className="text-[13px] w-4 text-center">{SOURCE_ICON[event.source]}</span>
      <span className={clsx('wv-badge shrink-0', SOURCE_BADGE[event.source])}>
        {event.source}
      </span>
      <span className="text-text-tertiary w-14 shrink-0 text-[10px]">{relativeTime(event.timestamp)}</span>
      <span className="text-cyan w-20 shrink-0 truncate">{event.agent}</span>
      <span className="text-text-tertiary w-20 shrink-0 truncate text-[10px]">{event.kind}</span>
      <span className="text-text-primary flex-1 truncate">{event.summary}</span>
    </button>
  )
}

function DetailPanel({ event, onClose }: { event: ActivityEvent; onClose: () => void }) {
  const detail = event.detail ?? {}

  return (
    <div className="w-80 border-l border-border flex flex-col bg-surface">
      <div className="flex items-center justify-between p-4 border-b border-border">
        <span className="wv-label">EVENT DETAIL</span>
        <button onClick={onClose} className="text-text-tertiary hover:text-text-primary text-[14px] transition-colors">
          ✕
        </button>
      </div>
      <div className="p-4 space-y-4 overflow-y-auto flex-1">
        <div>
          <div className="wv-label mb-1">ID</div>
          <div className="text-[11px] text-text-secondary font-mono break-all">{event.id}</div>
        </div>
        <div className="flex gap-4">
          <div>
            <div className="wv-label mb-1">SOURCE</div>
            <span className={clsx('wv-badge', SOURCE_BADGE[event.source])}>{event.source}</span>
          </div>
          <div>
            <div className="wv-label mb-1">KIND</div>
            <span className="wv-badge wv-badge-cyan">{event.kind}</span>
          </div>
        </div>
        <div>
          <div className="wv-label mb-1">AGENT</div>
          <div className="text-[12px] text-cyan">{event.agent}</div>
        </div>
        <div>
          <div className="wv-label mb-1">SUMMARY</div>
          <div className="text-[11px] text-text-primary leading-relaxed">{event.summary}</div>
        </div>
        <div>
          <div className="wv-label mb-1">TIMESTAMP</div>
          <div className="text-[11px] text-text-secondary">{new Date(event.timestamp).toLocaleString()}</div>
        </div>
        {Object.keys(detail).length > 0 && (
          <div>
            <div className="wv-label mb-1">DETAIL</div>
            <div className="space-y-1">
              {Object.entries(detail).map(([k, v]) =>
                v != null ? (
                  <div key={k} className="flex items-start gap-2 text-[10px]">
                    <span className="text-text-tertiary font-mono shrink-0">{k}:</span>
                    <span className="text-text-secondary break-all">{String(v)}</span>
                  </div>
                ) : null,
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export function Activity() {
  const { activityStream } = useCockpitStore()
  const [sourceFilter, setSourceFilter] = useState<SourceFilter>('all')
  const [search, setSearch] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const filtered = useMemo(() => {
    return activityStream.filter((e) => {
      if (sourceFilter !== 'all' && e.source !== sourceFilter) return false
      if (search) {
        const q = search.toLowerCase()
        return (
          e.summary.toLowerCase().includes(q) ||
          e.agent.toLowerCase().includes(q) ||
          e.kind.toLowerCase().includes(q)
        )
      }
      return true
    })
  }, [activityStream, sourceFilter, search])

  const selectedEvent = filtered.find((e) => e.id === selectedId) ?? null

  return (
    <div className="h-full flex flex-col p-4 overflow-hidden">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-[14px] font-mono uppercase tracking-widest text-text-secondary">
          Activity
        </h1>
        <span className="text-[10px] font-mono text-text-tertiary uppercase">
          {filtered.length} events
        </span>
      </div>

      <StatsStrip events={activityStream} />

      <div className="wv-card p-3 mb-4 flex items-center gap-3 flex-wrap">
        <div className="flex gap-1">
          {SOURCE_OPTIONS.map((opt) => (
            <button
              key={opt.id}
              onClick={() => setSourceFilter(opt.id)}
              className={clsx(
                'px-2 py-1 text-[10px] font-mono uppercase tracking-wider border transition-colors',
                sourceFilter === opt.id
                  ? 'text-cyan bg-cyan-glow border-cyan-dim'
                  : 'text-text-tertiary border-border hover:text-text-secondary hover:border-border-active',
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search events..."
          className="flex-1 min-w-[160px] bg-surface border border-border text-text-primary text-[11px] font-mono px-2 py-1 placeholder:text-text-tertiary focus:border-cyan-dim focus:outline-none"
        />
      </div>

      <div className="flex-1 flex min-h-0">
        <div className="flex-1 wv-card overflow-y-auto">
          <div className="sticky top-0 bg-surface border-b border-border px-3 py-2 flex items-center gap-3 text-[10px] font-mono text-text-tertiary uppercase tracking-wider">
            <span className="w-4" />
            <span className="w-16">SOURCE</span>
            <span className="w-14">TIME</span>
            <span className="w-20">AGENT</span>
            <span className="w-20">KIND</span>
            <span className="flex-1">SUMMARY</span>
          </div>
          {filtered.length === 0 && (
            <div className="text-center text-text-tertiary text-[11px] py-12">
              No events matching current filters
            </div>
          )}
          {filtered.map((e) => (
            <EventRow
              key={e.id}
              event={e}
              selected={e.id === selectedId}
              onClick={() => setSelectedId(e.id === selectedId ? null : e.id)}
            />
          ))}
        </div>

        {selectedEvent && (
          <DetailPanel event={selectedEvent} onClose={() => setSelectedId(null)} />
        )}
      </div>
    </div>
  )
}
