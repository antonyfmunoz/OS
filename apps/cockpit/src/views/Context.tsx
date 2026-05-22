import { useState, useMemo } from 'react'
import { clsx } from 'clsx'
import { useCockpitStore } from '../stores/cockpitStore.ts'
import { relativeTime } from '../lib/time.ts'
import type { ObservationResponse } from '../api/client.ts'

const PRIMITIVE_COLOR: Record<string, string> = {
  state: 'wv-badge-cyan', change: 'wv-badge-ok', constraint: 'wv-badge-danger', resource: 'wv-badge-ok',
  signal: 'wv-badge-warn', action: 'wv-badge-violet', outcome: 'wv-badge-ok', feedback: 'wv-badge-warn',
  goal: 'wv-badge-violet', time: 'wv-badge-cyan',
}

const PRIMITIVES = ['state', 'change', 'constraint', 'resource', 'signal', 'action', 'outcome', 'feedback', 'goal', 'time']

function PrimitiveDistribution({ observations }: { observations: ObservationResponse[] }) {
  const counts = useMemo(() => {
    const map: Record<string, number> = {}
    for (const o of observations) map[o.primitive_type] = (map[o.primitive_type] ?? 0) + 1
    return Object.entries(map).sort((a, b) => b[1] - a[1])
  }, [observations])

  return (
    <div className="wv-card p-3 mb-4">
      <div className="wv-label mb-2">PRIMITIVE DISTRIBUTION</div>
      <div className="flex flex-wrap gap-2">
        {counts.map(([type, count]) => (
          <div key={type} className="flex items-center gap-1.5">
            <span className={clsx('wv-badge', PRIMITIVE_COLOR[type] ?? 'wv-badge-cyan')}>{type}</span>
            <span className="text-[10px] text-text-secondary font-mono">{count}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function ObservationRow({ obs, selected, onClick }: { obs: ObservationResponse; selected: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} className={clsx('w-full text-left flex items-center gap-3 py-3 px-3 text-[11px] font-mono border-b border-border/50 transition-colors', selected ? 'bg-cyan/5 border-l-2 border-l-cyan' : 'hover:bg-surface-hover')}>
      <span className={clsx('wv-badge shrink-0', PRIMITIVE_COLOR[obs.primitive_type] ?? 'wv-badge-cyan')}>{obs.primitive_type}</span>
      <span className="text-text-primary flex-1 truncate">{obs.label}</span>
      <span className="text-text-tertiary shrink-0 text-[10px]">{obs.relationships.length > 0 && `${obs.relationships.length} rel`}</span>
      <span className="text-text-tertiary shrink-0 w-14 text-right text-[10px]">{relativeTime(obs.created_at)}</span>
    </button>
  )
}

function DetailPanel({ obs, onClose }: { obs: ObservationResponse; onClose: () => void }) {
  return (
    <div className="w-[420px] border-l border-border flex flex-col bg-surface">
      <div className="flex items-center justify-between p-4 border-b border-border">
        <span className="wv-label">OBSERVATION</span>
        <button onClick={onClose} className="text-text-tertiary hover:text-text-primary text-[14px] transition-colors">✕</button>
      </div>
      <div className="p-4 space-y-4 overflow-y-auto flex-1">
        <div><div className="wv-label mb-1">LABEL</div><div className="text-[12px] text-text-primary">{obs.label}</div></div>
        <div><div className="wv-label mb-1">DESCRIPTION</div><div className="text-[11px] text-text-secondary leading-relaxed">{obs.description}</div></div>
        <div><div className="wv-label mb-1">PRIMITIVE TYPE</div><span className={clsx('wv-badge', PRIMITIVE_COLOR[obs.primitive_type] ?? 'wv-badge-cyan')}>{obs.primitive_type}</span></div>
        <div><div className="wv-label mb-1">EVIDENCE</div><div className="wv-card p-3 text-[10px] text-text-secondary font-mono leading-relaxed italic">{obs.evidence}</div></div>
        <div><div className="wv-label mb-1">SOURCE</div><div className="text-[11px] text-text-secondary font-mono">{obs.source_document}</div></div>
        {obs.relationships.length > 0 && (
          <div><div className="wv-label mb-2">RELATIONSHIPS</div><div className="space-y-2">
            {obs.relationships.map((rel, i) => (
              <div key={i} className="wv-card p-2 flex items-center gap-2">
                <span className="wv-badge wv-badge-cyan text-[9px]">{rel.type}</span>
                <span className="text-[10px] text-text-secondary flex-1 truncate">{rel.target_label}</span>
              </div>
            ))}
          </div></div>
        )}
        <div><div className="wv-label mb-1">CREATED</div><div className="text-[11px] text-text-secondary">{new Date(obs.created_at).toLocaleString()}</div></div>
      </div>
    </div>
  )
}

export function Context() {
  const { observations } = useCockpitStore()
  const [primitiveFilter, setPrimitiveFilter] = useState<string>('all')
  const [search, setSearch] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const filtered = useMemo(() => {
    return observations.filter((o) => {
      if (primitiveFilter !== 'all' && o.primitive_type !== primitiveFilter) return false
      if (search) { const q = search.toLowerCase(); return o.label.toLowerCase().includes(q) || o.description.toLowerCase().includes(q) || o.evidence.toLowerCase().includes(q) }
      return true
    })
  }, [observations, primitiveFilter, search])

  const selectedObs = observations.find((o) => o.id === selectedId) ?? null

  return (
    <div className="h-full flex flex-col p-4 overflow-hidden">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-[14px] font-mono uppercase tracking-widest text-text-secondary">Context</h1>
        <span className="text-[10px] font-mono text-text-tertiary uppercase">{observations.length} observations</span>
      </div>
      <PrimitiveDistribution observations={observations} />
      <div className="wv-card p-3 mb-4 flex items-center gap-3 flex-wrap">
        <div className="flex gap-1 flex-wrap">
          <button onClick={() => setPrimitiveFilter('all')} className={clsx('px-2 py-1 text-[10px] font-mono uppercase tracking-wider border transition-colors', primitiveFilter === 'all' ? 'text-cyan bg-cyan-glow border-cyan-dim' : 'text-text-tertiary border-border hover:text-text-secondary hover:border-border-active')}>All</button>
          {PRIMITIVES.map((pt) => (
            <button key={pt} onClick={() => setPrimitiveFilter(pt)} className={clsx('px-2 py-1 text-[10px] font-mono uppercase tracking-wider border transition-colors', primitiveFilter === pt ? 'text-cyan bg-cyan-glow border-cyan-dim' : 'text-text-tertiary border-border hover:text-text-secondary hover:border-border-active')}>{pt}</button>
          ))}
        </div>
        <input type="text" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search observations..." className="flex-1 min-w-[160px] bg-surface border border-border text-text-primary text-[11px] font-mono px-2 py-1 placeholder:text-text-tertiary focus:border-cyan-dim focus:outline-none" />
      </div>
      <div className="flex-1 flex min-h-0">
        <div className="flex-1 wv-card overflow-y-auto">
          <div className="sticky top-0 bg-surface border-b border-border px-3 py-2 flex items-center gap-3 text-[10px] font-mono text-text-tertiary uppercase tracking-wider">
            <span className="w-20">TYPE</span><span className="flex-1">LABEL</span><span className="w-12">RELS</span><span className="w-14 text-right">AGE</span>
          </div>
          {filtered.length === 0 && <div className="text-center text-text-tertiary text-[11px] py-12">No observations matching current filters</div>}
          {filtered.map((obs) => <ObservationRow key={obs.id} obs={obs} selected={obs.id === selectedId} onClick={() => setSelectedId(obs.id === selectedId ? null : obs.id)} />)}
        </div>
        {selectedObs && <DetailPanel obs={selectedObs} onClose={() => setSelectedId(null)} />}
      </div>
    </div>
  )
}
