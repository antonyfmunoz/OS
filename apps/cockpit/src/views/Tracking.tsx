import { useState, useMemo } from 'react'
import { clsx } from 'clsx'
import { useCockpitStore } from '../stores/cockpitStore.ts'
import { relativeTime } from '../lib/time.ts'
import type { TrackingEntity } from '../api/client.ts'

const STATUS_COLOR: Record<TrackingEntity['status'], string> = {
  active: 'wv-badge-ok',
  stale: 'wv-badge-warn',
  archived: 'wv-badge-danger',
}

type StatusFilter = TrackingEntity['status'] | 'all'

function StatsBar({ entities }: { entities: TrackingEntity[] }) {
  const active = entities.filter((e) => e.status === 'active').length
  const stale = entities.filter((e) => e.status === 'stale').length
  const types = new Set(entities.map((e) => e.entity_type)).size
  const totalChanges = entities.reduce((s, e) => s + e.change_count, 0)

  return (
    <div className="grid grid-cols-4 gap-3 mb-4">
      <div className="wv-card p-3 text-center"><div className="wv-metric text-ok">{active}</div><div className="wv-label mt-1">ACTIVE</div></div>
      <div className="wv-card p-3 text-center"><div className="wv-metric text-warn">{stale}</div><div className="wv-label mt-1">STALE</div></div>
      <div className="wv-card p-3 text-center"><div className="wv-metric text-text-primary">{types}</div><div className="wv-label mt-1">TYPES</div></div>
      <div className="wv-card p-3 text-center"><div className="wv-metric text-cyan">{totalChanges}</div><div className="wv-label mt-1">CHANGES</div></div>
    </div>
  )
}

function EntityRow({ entity, selected, onClick }: { entity: TrackingEntity; selected: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} className={clsx('w-full text-left flex items-center gap-3 py-3 px-3 text-[11px] font-mono border-b border-border/50 transition-colors', selected ? 'bg-cyan/5 border-l-2 border-l-cyan' : 'hover:bg-surface-hover')}>
      <span className={clsx('wv-badge shrink-0', STATUS_COLOR[entity.status])}>{entity.status}</span>
      <span className="text-text-tertiary shrink-0 w-20 truncate">{entity.entity_type}</span>
      <span className="text-text-primary flex-1 truncate">{entity.name}</span>
      <span className="text-text-tertiary shrink-0 text-[10px]">{entity.change_count} chg</span>
      <span className="text-text-tertiary shrink-0 w-14 text-right text-[10px]">{relativeTime(entity.last_changed)}</span>
    </button>
  )
}

function DetailPanel({ entity, onClose }: { entity: TrackingEntity; onClose: () => void }) {
  return (
    <div className="w-96 border-l border-border flex flex-col bg-surface">
      <div className="flex items-center justify-between p-4 border-b border-border">
        <span className="wv-label">ENTITY DETAIL</span>
        <button onClick={onClose} className="text-text-tertiary hover:text-text-primary text-[14px] transition-colors">✕</button>
      </div>
      <div className="p-4 space-y-4 overflow-y-auto flex-1">
        <div><div className="wv-label mb-1">NAME</div><div className="text-[14px] text-text-primary font-mono">{entity.name}</div></div>
        <div className="flex gap-4">
          <div><div className="wv-label mb-1">TYPE</div><span className="wv-badge wv-badge-cyan">{entity.entity_type}</span></div>
          <div><div className="wv-label mb-1">STATUS</div><span className={clsx('wv-badge', STATUS_COLOR[entity.status])}>{entity.status}</span></div>
        </div>
        <div><div className="wv-label mb-1">CHANGES</div><div className="wv-metric text-cyan">{entity.change_count}</div></div>
        <div><div className="wv-label mb-1">LAST CHANGED</div><div className="text-[11px] text-text-secondary">{new Date(entity.last_changed).toLocaleString()}</div></div>
      </div>
    </div>
  )
}

export function Tracking() {
  const { tracking } = useCockpitStore()
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [search, setSearch] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const filtered = useMemo(() => {
    return tracking.filter((e) => {
      if (statusFilter !== 'all' && e.status !== statusFilter) return false
      if (search) { const q = search.toLowerCase(); return e.name.toLowerCase().includes(q) || e.entity_type.toLowerCase().includes(q) }
      return true
    })
  }, [tracking, statusFilter, search])

  const selectedEntity = tracking.find((e) => e.id === selectedId) ?? null

  return (
    <div className="h-full flex flex-col p-4 overflow-hidden">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-[14px] font-mono uppercase tracking-widest text-text-secondary">Tracking</h1>
        <span className="text-[10px] font-mono text-text-tertiary uppercase">{tracking.length} entities</span>
      </div>
      <StatsBar entities={tracking} />
      <div className="wv-card p-3 mb-4 flex items-center gap-3 flex-wrap">
        <div className="flex gap-1">
          {(['all', 'active', 'stale', 'archived'] as const).map((s) => (
            <button key={s} onClick={() => setStatusFilter(s)} className={clsx('px-2 py-1 text-[10px] font-mono uppercase tracking-wider border transition-colors', statusFilter === s ? 'text-cyan bg-cyan-glow border-cyan-dim' : 'text-text-tertiary border-border hover:text-text-secondary hover:border-border-active')}>{s}</button>
          ))}
        </div>
        <input type="text" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search entities..." className="flex-1 min-w-[160px] bg-surface border border-border text-text-primary text-[11px] font-mono px-2 py-1 placeholder:text-text-tertiary focus:border-cyan-dim focus:outline-none" />
      </div>
      <div className="flex-1 flex min-h-0">
        <div className="flex-1 wv-card overflow-y-auto">
          <div className="sticky top-0 bg-surface border-b border-border px-3 py-2 flex items-center gap-3 text-[10px] font-mono text-text-tertiary uppercase tracking-wider">
            <span className="w-16">STATUS</span><span className="w-20">TYPE</span><span className="flex-1">NAME</span><span className="w-14">CHG</span><span className="w-14 text-right">AGE</span>
          </div>
          {filtered.length === 0 && <div className="text-center text-text-tertiary text-[11px] py-12">No entities matching current filters</div>}
          {filtered.map((entity) => <EntityRow key={entity.id} entity={entity} selected={entity.id === selectedId} onClick={() => setSelectedId(entity.id === selectedId ? null : entity.id)} />)}
        </div>
        {selectedEntity && <DetailPanel entity={selectedEntity} onClose={() => setSelectedId(null)} />}
      </div>
    </div>
  )
}
