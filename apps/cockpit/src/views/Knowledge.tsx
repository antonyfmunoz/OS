import { useState, useMemo } from 'react'
import { clsx } from 'clsx'
import { useCockpitStore } from '../stores/cockpitStore.ts'
import { relativeTime } from '../lib/time.ts'
import type { MemoryEntryResponse } from '../api/client.ts'

const TIER_LABEL: Record<string, string> = {
  T1: 'Canonical', T2: 'Verified', T3: 'Curated', T4: 'Analyzed', T5: 'Default',
  T6: 'Inferred', T7: 'External', T8: 'Conversational', T9: 'Old Chats',
}

const TIER_COLOR: Record<string, string> = {
  T1: 'wv-badge-violet', T2: 'wv-badge-ok', T3: 'wv-badge-ok', T4: 'wv-badge-cyan',
  T5: 'wv-badge-cyan', T6: 'wv-badge-warn', T7: 'wv-badge-warn', T8: 'wv-badge-danger', T9: 'wv-badge-danger',
}

const TYPE_COLOR: Record<string, string> = {
  STRUCTURED: 'wv-badge-ok', PARTIAL: 'wv-badge-warn', TEXT_BLOB: 'wv-badge-danger', DOMAIN_PROJECTION: 'wv-badge-violet',
}

function StatsBar({ entries }: { entries: MemoryEntryResponse[] }) {
  const structured = entries.filter((e) => e.memory_type === 'STRUCTURED').length
  const projections = entries.filter((e) => e.memory_type === 'DOMAIN_PROJECTION').length
  const partial = entries.filter((e) => e.memory_type === 'PARTIAL').length
  const blobs = entries.filter((e) => e.memory_type === 'TEXT_BLOB').length

  return (
    <div className="grid grid-cols-4 gap-3 mb-4">
      <div className="wv-card p-3 text-center"><div className="wv-metric text-ok">{structured}</div><div className="wv-label mt-1">STRUCTURED</div></div>
      <div className="wv-card p-3 text-center"><div className="wv-metric text-violet">{projections}</div><div className="wv-label mt-1">PROJECTIONS</div></div>
      <div className="wv-card p-3 text-center"><div className="wv-metric text-warn">{partial}</div><div className="wv-label mt-1">PARTIAL</div></div>
      <div className="wv-card p-3 text-center"><div className="wv-metric text-danger">{blobs}</div><div className="wv-label mt-1">TEXT BLOB</div></div>
    </div>
  )
}

function EntryRow({ entry, selected, onClick }: { entry: MemoryEntryResponse; selected: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} className={clsx('w-full text-left flex items-center gap-3 py-3 px-3 text-[11px] font-mono border-b border-border/50 transition-colors', selected ? 'bg-cyan/5 border-l-2 border-l-cyan' : 'hover:bg-surface-hover')}>
      <span className={clsx('wv-badge shrink-0', TIER_COLOR[entry.authority_tier] ?? 'wv-badge-cyan')}>{entry.authority_tier}</span>
      <span className={clsx('wv-badge shrink-0', TYPE_COLOR[entry.memory_type] ?? 'wv-badge-cyan')}>{entry.memory_type === 'DOMAIN_PROJECTION' ? 'PROJ' : entry.memory_type.slice(0, 4)}</span>
      <span className="text-text-primary flex-1 truncate">{entry.label}</span>
      <span className="text-text-tertiary shrink-0 text-[10px]">{entry.primitive_type}</span>
      <span className="text-text-tertiary shrink-0 w-14 text-right text-[10px]">{relativeTime(entry.created_at)}</span>
    </button>
  )
}

function DetailPanel({ entry, onClose }: { entry: MemoryEntryResponse; onClose: () => void }) {
  return (
    <div className="w-96 border-l border-border flex flex-col bg-surface">
      <div className="flex items-center justify-between p-4 border-b border-border">
        <span className="wv-label">MEMORY DETAIL</span>
        <button onClick={onClose} className="text-text-tertiary hover:text-text-primary text-[14px] transition-colors">✕</button>
      </div>
      <div className="p-4 space-y-4 overflow-y-auto flex-1">
        <div><div className="wv-label mb-1">LABEL</div><div className="text-[12px] text-text-primary">{entry.label}</div></div>
        <div><div className="wv-label mb-1">DESCRIPTION</div><div className="text-[11px] text-text-secondary leading-relaxed">{entry.description}</div></div>
        <div className="flex gap-4">
          <div><div className="wv-label mb-1">TYPE</div><span className={clsx('wv-badge', TYPE_COLOR[entry.memory_type] ?? 'wv-badge-cyan')}>{entry.memory_type}</span></div>
          <div><div className="wv-label mb-1">AUTHORITY</div><div className="flex items-center gap-1.5"><span className={clsx('wv-badge', TIER_COLOR[entry.authority_tier] ?? 'wv-badge-cyan')}>{entry.authority_tier}</span><span className="text-[10px] text-text-tertiary">{TIER_LABEL[entry.authority_tier] ?? ''}</span></div></div>
        </div>
        <div><div className="wv-label mb-1">PRIMITIVE TYPE</div><span className="wv-badge wv-badge-cyan">{entry.primitive_type}</span></div>
        <div><div className="wv-label mb-1">SOURCE DOCUMENT</div><div className="text-[11px] text-text-secondary font-mono">{entry.source_document}</div></div>
        {entry.domain_id && <div><div className="wv-label mb-1">DOMAIN</div><span className="wv-badge wv-badge-violet">{entry.domain_id}</span></div>}
        <div><div className="wv-label mb-1">CREATED</div><div className="text-[11px] text-text-secondary">{new Date(entry.created_at).toLocaleString()}</div></div>
      </div>
    </div>
  )
}

export function Knowledge() {
  const { memory } = useCockpitStore()
  const [typeFilter, setTypeFilter] = useState<string>('all')
  const [search, setSearch] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const filtered = useMemo(() => {
    return memory.filter((e) => {
      if (typeFilter !== 'all' && e.memory_type !== typeFilter) return false
      if (search) {
        const q = search.toLowerCase()
        return e.label.toLowerCase().includes(q) || e.description.toLowerCase().includes(q)
      }
      return true
    })
  }, [memory, typeFilter, search])

  const selectedEntry = memory.find((e) => e.id === selectedId) ?? null

  return (
    <div className="h-full flex flex-col p-4 overflow-hidden">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-[14px] font-mono uppercase tracking-widest text-text-secondary">Knowledge</h1>
        <span className="text-[10px] font-mono text-text-tertiary uppercase">{memory.length} entries</span>
      </div>
      <StatsBar entries={memory} />
      <div className="wv-card p-3 mb-4 flex items-center gap-3 flex-wrap">
        <div className="flex gap-1">
          {['all', 'STRUCTURED', 'DOMAIN_PROJECTION', 'PARTIAL', 'TEXT_BLOB'].map((t) => (
            <button key={t} onClick={() => setTypeFilter(t)} className={clsx('px-2 py-1 text-[10px] font-mono uppercase tracking-wider border transition-colors', typeFilter === t ? 'text-cyan bg-cyan-glow border-cyan-dim' : 'text-text-tertiary border-border hover:text-text-secondary hover:border-border-active')}>{t === 'all' ? 'All' : t === 'DOMAIN_PROJECTION' ? 'Proj' : t.slice(0, 6)}</button>
          ))}
        </div>
        <input type="text" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search memory..." className="flex-1 min-w-[160px] bg-surface border border-border text-text-primary text-[11px] font-mono px-2 py-1 placeholder:text-text-tertiary focus:border-cyan-dim focus:outline-none" />
      </div>
      <div className="flex-1 flex min-h-0">
        <div className="flex-1 wv-card overflow-y-auto">
          <div className="sticky top-0 bg-surface border-b border-border px-3 py-2 flex items-center gap-3 text-[10px] font-mono text-text-tertiary uppercase tracking-wider">
            <span className="w-8">TIER</span><span className="w-10">TYPE</span><span className="flex-1">LABEL</span><span className="w-16">PRIM</span><span className="w-14 text-right">AGE</span>
          </div>
          {filtered.length === 0 && <div className="text-center text-text-tertiary text-[11px] py-12">No entries matching current filters</div>}
          {filtered.map((entry) => <EntryRow key={entry.id} entry={entry} selected={entry.id === selectedId} onClick={() => setSelectedId(entry.id === selectedId ? null : entry.id)} />)}
        </div>
        {selectedEntry && <DetailPanel entry={selectedEntry} onClose={() => setSelectedId(null)} />}
      </div>
    </div>
  )
}
