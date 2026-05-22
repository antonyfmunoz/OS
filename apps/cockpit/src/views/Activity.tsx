import { useState, useMemo } from 'react'
import { clsx } from 'clsx'
import { useCockpitStore } from '../stores/cockpitStore.ts'
import { relativeTime, formatDuration } from '../lib/time.ts'
import type { TraceEvent } from '../types/domain.ts'

type StatusFilter = TraceEvent['status'] | 'all'

const STATUS_OPTIONS: { id: StatusFilter; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'running', label: 'Running' },
  { id: 'completed', label: 'Completed' },
  { id: 'failed', label: 'Failed' },
  { id: 'pending', label: 'Pending' },
]

const STATUS_ICON: Record<TraceEvent['status'], string> = {
  running: '◉',
  completed: '✓',
  failed: '✗',
  pending: '○',
}

const STATUS_COLOR: Record<TraceEvent['status'], string> = {
  running: 'text-cyan',
  completed: 'text-ok',
  failed: 'text-danger',
  pending: 'text-text-tertiary',
}

function StatsStrip({ traces }: { traces: TraceEvent[] }) {
  const running = traces.filter((t) => t.status === 'running').length
  const failed = traces.filter((t) => t.status === 'failed').length
  const completed = traces.filter((t) => t.status === 'completed').length
  const withDuration = traces.filter((t) => t.durationMs != null)
  const avgMs =
    withDuration.length > 0
      ? withDuration.reduce((s, t) => s + (t.durationMs ?? 0), 0) / withDuration.length
      : 0

  return (
    <div className="grid grid-cols-5 gap-3 mb-4">
      <div className="wv-card p-3 text-center">
        <div className="wv-metric text-text-primary">{traces.length}</div>
        <div className="wv-label mt-1">TOTAL</div>
      </div>
      <div className="wv-card p-3 text-center">
        <div className="wv-metric text-cyan">{running}</div>
        <div className="wv-label mt-1">RUNNING</div>
      </div>
      <div className="wv-card p-3 text-center">
        <div className="wv-metric text-ok">{completed}</div>
        <div className="wv-label mt-1">COMPLETED</div>
      </div>
      <div className="wv-card p-3 text-center">
        <div className="wv-metric text-danger">{failed}</div>
        <div className="wv-label mt-1">FAILED</div>
      </div>
      <div className="wv-card p-3 text-center">
        <div className="wv-metric text-text-primary">{formatDuration(Math.round(avgMs))}</div>
        <div className="wv-label mt-1">AVG DURATION</div>
      </div>
    </div>
  )
}

function FilterBar({
  agents,
  selectedAgent,
  setSelectedAgent,
  statusFilter,
  setStatusFilter,
  search,
  setSearch,
  paused,
  setPaused,
}: {
  agents: string[]
  selectedAgent: string
  setSelectedAgent: (a: string) => void
  statusFilter: StatusFilter
  setStatusFilter: (s: StatusFilter) => void
  search: string
  setSearch: (s: string) => void
  paused: boolean
  setPaused: (p: boolean) => void
}) {
  return (
    <div className="wv-card p-3 mb-4 flex items-center gap-3 flex-wrap">
      <select
        value={selectedAgent}
        onChange={(e) => setSelectedAgent(e.target.value)}
        className="bg-surface border border-border text-text-primary text-[11px] font-mono px-2 py-1 focus:border-cyan-dim focus:outline-none"
      >
        <option value="all">ALL AGENTS</option>
        {agents.map((a) => (
          <option key={a} value={a}>
            {a.toUpperCase()}
          </option>
        ))}
      </select>

      <div className="flex gap-1">
        {STATUS_OPTIONS.map((opt) => (
          <button
            key={opt.id}
            onClick={() => setStatusFilter(opt.id)}
            className={clsx(
              'px-2 py-1 text-[10px] font-mono uppercase tracking-wider border transition-colors',
              statusFilter === opt.id
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
        placeholder="Search actions..."
        className="flex-1 min-w-[160px] bg-surface border border-border text-text-primary text-[11px] font-mono px-2 py-1 placeholder:text-text-tertiary focus:border-cyan-dim focus:outline-none"
      />

      <button
        onClick={() => setPaused(!paused)}
        className={clsx(
          'px-3 py-1 text-[10px] font-mono uppercase tracking-wider border transition-colors flex items-center gap-1.5',
          paused
            ? 'text-warn border-warn-dim bg-warn/10'
            : 'text-ok border-ok-dim bg-ok/10',
        )}
      >
        <span className={clsx('w-1.5 h-1.5 rounded-full', paused ? 'bg-warn' : 'bg-ok wv-pulse')} />
        {paused ? 'Paused' : 'Live'}
      </button>
    </div>
  )
}

function TraceRow({
  trace,
  selected,
  onClick,
}: {
  trace: TraceEvent
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
      <span className={clsx('w-4 text-center text-[13px]', STATUS_COLOR[trace.status])}>
        {STATUS_ICON[trace.status]}
      </span>
      <span className="text-text-tertiary w-16 shrink-0 truncate">{relativeTime(trace.timestamp)}</span>
      <span className="text-cyan w-24 shrink-0 truncate">{trace.agent}</span>
      <span className="text-text-primary flex-1 truncate">{trace.action}</span>
      {trace.durationMs != null && (
        <span className="text-text-tertiary shrink-0 w-16 text-right">{formatDuration(trace.durationMs)}</span>
      )}
    </button>
  )
}

function DetailPanel({ trace, onClose }: { trace: TraceEvent; onClose: () => void }) {
  return (
    <div className="w-80 border-l border-border flex flex-col bg-surface">
      <div className="flex items-center justify-between p-4 border-b border-border">
        <span className="wv-label">TRACE DETAIL</span>
        <button
          onClick={onClose}
          className="text-text-tertiary hover:text-text-primary text-[14px] transition-colors"
        >
          ✕
        </button>
      </div>
      <div className="p-4 space-y-4 overflow-y-auto flex-1">
        <div>
          <div className="wv-label mb-1">ID</div>
          <div className="text-[11px] text-text-secondary font-mono break-all">{trace.id}</div>
        </div>
        <div>
          <div className="wv-label mb-1">STATUS</div>
          <span className={clsx('wv-badge', {
            'wv-badge-cyan': trace.status === 'running',
            'wv-badge-ok': trace.status === 'completed',
            'wv-badge-danger': trace.status === 'failed',
            'wv-badge-warn': trace.status === 'pending',
          })}>
            {trace.status}
          </span>
        </div>
        <div>
          <div className="wv-label mb-1">AGENT</div>
          <div className="text-[12px] text-cyan">{trace.agent}</div>
        </div>
        <div>
          <div className="wv-label mb-1">ACTION</div>
          <div className="text-[11px] text-text-primary">{trace.action}</div>
        </div>
        <div>
          <div className="wv-label mb-1">TIMESTAMP</div>
          <div className="text-[11px] text-text-secondary">{new Date(trace.timestamp).toLocaleString()}</div>
        </div>
        {trace.durationMs != null && (
          <div>
            <div className="wv-label mb-1">DURATION</div>
            <div className="text-[11px] text-text-secondary">{formatDuration(trace.durationMs)}</div>
          </div>
        )}
        {trace.detail && (
          <div>
            <div className="wv-label mb-1">DETAIL</div>
            <div className="text-[11px] text-text-secondary leading-relaxed">{trace.detail}</div>
          </div>
        )}
      </div>
    </div>
  )
}

export function Activity() {
  const { traces } = useCockpitStore()

  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [selectedAgent, setSelectedAgent] = useState('all')
  const [search, setSearch] = useState('')
  const [paused, setPaused] = useState(false)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [frozenTraces, setFrozenTraces] = useState<TraceEvent[]>([])

  const displayTraces = paused ? frozenTraces : traces

  const agents = useMemo(() => {
    const set = new Set(displayTraces.map((t) => t.agent))
    return [...set].sort()
  }, [displayTraces])

  const filtered = useMemo(() => {
    return displayTraces.filter((t) => {
      if (statusFilter !== 'all' && t.status !== statusFilter) return false
      if (selectedAgent !== 'all' && t.agent !== selectedAgent) return false
      if (search && !t.action.toLowerCase().includes(search.toLowerCase())) return false
      return true
    })
  }, [displayTraces, statusFilter, selectedAgent, search])

  const selectedTrace = filtered.find((t) => t.id === selectedId) ?? null

  const handlePauseToggle = (next: boolean) => {
    if (next) setFrozenTraces([...traces])
    setPaused(next)
  }

  return (
    <div className="h-full flex flex-col p-4 overflow-hidden">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-[14px] font-mono uppercase tracking-widest text-text-secondary">
          Activity
        </h1>
        <div className="flex items-center gap-2">
          <span className={clsx('w-2 h-2 rounded-full', paused ? 'bg-warn' : 'bg-ok wv-pulse')} />
          <span className="text-[10px] font-mono text-text-tertiary uppercase">
            {paused ? 'Paused' : 'Live'} &middot; {filtered.length} traces
          </span>
        </div>
      </div>

      <StatsStrip traces={displayTraces} />

      <FilterBar
        agents={agents}
        selectedAgent={selectedAgent}
        setSelectedAgent={setSelectedAgent}
        statusFilter={statusFilter}
        setStatusFilter={setStatusFilter}
        search={search}
        setSearch={setSearch}
        paused={paused}
        setPaused={handlePauseToggle}
      />

      <div className="flex-1 flex min-h-0">
        <div className="flex-1 wv-card overflow-y-auto">
          <div className="sticky top-0 bg-surface border-b border-border px-3 py-2 flex items-center gap-3 text-[10px] font-mono text-text-tertiary uppercase tracking-wider">
            <span className="w-4" />
            <span className="w-16">TIME</span>
            <span className="w-24">AGENT</span>
            <span className="flex-1">ACTION</span>
            <span className="w-16 text-right">DURATION</span>
          </div>
          {filtered.length === 0 && (
            <div className="text-center text-text-tertiary text-[11px] py-12">
              No traces matching current filters
            </div>
          )}
          {filtered.map((t) => (
            <TraceRow
              key={t.id}
              trace={t}
              selected={t.id === selectedId}
              onClick={() => setSelectedId(t.id === selectedId ? null : t.id)}
            />
          ))}
        </div>

        {selectedTrace && (
          <DetailPanel trace={selectedTrace} onClose={() => setSelectedId(null)} />
        )}
      </div>
    </div>
  )
}
